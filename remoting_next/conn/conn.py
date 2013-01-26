# -*- coding: utf-8 -*-
import io
import sys
from pickle import Pickler, Unpickler

from ..hub import Hub, Sender, ReceiverSenderPair
from ..result import Result, ResultPrintException
from ..proxy import Proxy
from ..expr import LoadConstExpr, LoadArgExpr
from ...async import Async, AsyncReturn, DummyAsync, Core, StateMachine, StateMachineGraph
from ...disposable import CompositeDisposable

__all__ = ('Connection',)
#------------------------------------------------------------------------------#
# Connection                                                                   #
#------------------------------------------------------------------------------#
class Connection (object):
    """Connection
    """

    STATE_INIT     = 'not-connected'
    STATE_CONNING  = 'connecting'
    STATE_CONNED   = 'connected'
    STATE_DISPOSED = 'disposed'

    STATE_GRAPH = StateMachineGraph (STATE_INIT, {
        STATE_INIT:     (STATE_CONNING, STATE_DISPOSED),
        STATE_CONNING:  (STATE_CONNED, STATE_DISPOSED),
        STATE_CONNED:   (STATE_DISPOSED,)
    })

    def __init__ (self, hub = None, core = None):
        self.hub  = hub or Hub.Instance ()
        self.core = core or Core.Instance ()
        self.module_map = {}

        self.receiver, self.sender = ReceiverSenderPair (hub = self.hub)
        self.dispose = CompositeDisposable ()
        self.state   = StateMachine (self.STATE_GRAPH)

        class pickler_type (Pickler):
            def persistent_id (this, target):
                return self.pack (target)
        self.pickler_type = pickler_type

        class unpickler_type (Unpickler):
            def persistent_load (this, state):
                return self.unpack (state)
            def find_class (this, modname, name):
                modname = self.module_map.get (modname, modname)
                module = sys.modules.get (modname, None)
                if module is None:
                    __import__ (modname)
                    module = sys.modules [modname]
                if getattr (module, '__initializing__', False):
                    # Module is being imported. Interrupt unpickling.
                    raise InterruptError ()
                return getattr (module, name)
        self.unpickler_type = unpickler_type

    #--------------------------------------------------------------------------#
    # Call                                                                     #
    #--------------------------------------------------------------------------#
    def __call__ (self, target):
        """Create proxy object from provided pickle-able constant.
        """
        return Proxy (self.sender, LoadConstExpr (target))

    #--------------------------------------------------------------------------#
    # Connect                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def Connect (self, target = None):
       """Connect
        """
       if not self.state (self.STATE_CONNING):
           raise ValueError ('Connection is in progress')

       try:
           self.receiver.On (self.handle)
           yield self.connect (target)
           self.state (self.STATE_CONNED)
       except Exception:
           self.Dispose ()
           raise
       AsyncReturn (self)

    @property
    def Connected (self):
        """Is connected
        """
        return self.state.State == self.STATE_CONNED

    @DummyAsync
    def connect (self, target):
        """Connect implementation
        """

    def disconnect (self):
        """Disconnect implementation
        """

    #--------------------------------------------------------------------------#
    # Marshal                                                                  #
    #--------------------------------------------------------------------------#
    PACK_ROUTE   = 0x1
    PACK_UNROUTE = 0x2
    PACK_PROXY   = 0x4

    def pack (self, target):
        """Pack target object
        """
        if isinstance (target, Sender):
            if target.dst == self.sender.dst:
                # This sender was previously received from this connection
                # so it must not be routed again.
                return self.PACK_UNROUTE, target.dst - 1
            else:
                # Sender must be routed
                return self.PACK_ROUTE, target.dst

        elif not isinstance (target, type):
            proxify = getattr (target, 'Proxy', None)
            if proxify is not None:
                proxy = proxify ()
                if proxy is not target:
                    # Target object implements proxify interface, send proxy
                    # instead of target object.
                    return self.PACK_PROXY, proxy

    def unpack (self, state):
        """Unpack target object from state
        """
        pack, args =  state
        if pack == self.PACK_ROUTE:
            return Sender (self.hub, args + self.sender.dst)
        elif pack == self.PACK_UNROUTE:
            return Sender (self.hub, args if args else self.sender.dst)
        elif pack == self.PACK_PROXY:
            return args
        else:
            raise ValueError ('Unknown pack type: {}'.format (pack))

    #--------------------------------------------------------------------------#
    # Messaging                                                                #
    #--------------------------------------------------------------------------#
    def handle (self, msg, src, dst):
        """Handle message
        """
        # just send it to remote peer
        stream = io.BytesIO ()
        self.pickler_type (stream, -1).dump ((msg, src, dst))
        return stream.getvalue ()

    def dispatch (self, msg):
        """Dispatch incoming (packed) message
        """

        try:
            msg, src, dst = self.unpickler_type (io.BytesIO (msg)).load ()
            dst = dst - 1 # strip remote connection address

            if dst:
                # After striping remote connection address, destination is not empty
                # so it needs to be routed.
                self.hub.Send (dst, msg, src)

            else:
                # Message target is connection itself, execute code object
                if msg is None:
                    self.Dispose ()
                    return

                def conn_cont (result, error):
                    if src is not None:
                        if error is None:
                            src.Send (Result ().SetResult (result))
                        else:
                            src.Send (Result ().SetError (error))
                    elif error is not None:
                        ResultPrintException (*error)

                msg (self).Then (conn_cont)

        except InterruptError:
            # Required module is being imported. Postpone message dispatch.
            self.hub.Await ().Then (lambda r, e: self.dispatch (msg))

        except Exception:
            ResultPrintException (*sys.exc_info ())

    #--------------------------------------------------------------------------#
    # Awaitable                                                                #
    #--------------------------------------------------------------------------#
    def Await (self, target = None):
        """Get awaiter
        """
        return self.Connect (target)

    #--------------------------------------------------------------------------#
    # Proxy                                                                    #
    #--------------------------------------------------------------------------#
    def Proxy (self):
        """Get proxy
        """
        return ConnectionProxy (self.sender, LoadArgExpr (0))

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        """Dispose connection
        """
        if self.state (self.STATE_DISPOSED):
            self.receiver.Off (self.handle)
            self.disconnect ()
            self.dispose.Dispose ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

    #--------------------------------------------------------------------------#
    # To String                                                                #
    #--------------------------------------------------------------------------#
    def __str__ (self):
        """String representation
        """
        return "<{} [state:{} addr:{}] at {}>".format (type (self).__name__,
            self.state.State, self.sender.dst, id (self))

    def __repr__  (self):
        """String representation
        """
        return str (self)

#------------------------------------------------------------------------------#
# Connection Proxy                                                             #
#------------------------------------------------------------------------------#
class ConnectionProxy (Proxy):
    """Connection proxy
    """

    def __call__ (self, target):
        """Create proxy object from provided pickle-able constant.
        """
        return Proxy (self.sender, LoadConstExpr (target))

#------------------------------------------------------------------------------#
# Interrupt Error                                                              #
#------------------------------------------------------------------------------#
class InterruptError (BaseException):
    """Interrupt helper exception type
    """

# vim: nu ft=python columns=120 :
