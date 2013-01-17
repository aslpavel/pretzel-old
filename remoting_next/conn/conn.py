# -*- coding: utf-8 -*-
import io
import pickle

from ..hub import Hub, Sender, ReceiverSenderPair
from ..result import ResultSender
from ..proxy import Proxify
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

        self.receiver, self.sender = ReceiverSenderPair (hub = self.hub)
        self.dispose = CompositeDisposable ()
        self.state   = StateMachine (self.STATE_GRAPH)

        class pickler_type (pickle.Pickler):
            def persistent_id (this, target):
                return self.pack (target)
        self.pickler_type = pickler_type

        class unpickler_type (pickle.Unpickler):
            def persistent_load (this, state):
                return self.unpack (state)
        self.unpickler_type = unpickler_type

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

       AsyncReturn (self.Proxify ())

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
            proxify = getattr (target, 'Proxify', None)
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
        stream = io.BytesIO ()
        self.pickler_type (stream, -1).dump ((msg, src, dst))
        return stream.getvalue ()

    @Async
    def dispatch (self, msg):
        """Dispatch incoming (packed) message
        """

        # Detachment from  current coroutine is vital here because if handler
        # tries to create nested core loop to resolve future synchronously
        # (i.g. importer proxy) it can stop dispatching coroutine
        yield self.core.Idle ()

        msg, src, dst = self.unpickler_type (io.BytesIO (msg)).load ()
        dst = dst - 1 # strip remote connection address

        if dst:
            # After striping remote connection address, destination is not empty
            # so it needs to be routed.
            self.hub.Send (dst, msg, src)

        else:
            # Message target is connection itself, execute action
            with ResultSender (src) as send:
                # dispose
                if msg is None:
                    self.Dispose ()
                    return

                # call
                func, args, keys, mutators = msg
                result = func (*args, **keys)

                # mutate
                if mutators:
                    for mutator in mutators:
                        if mutator == 'Proxy':
                            result = Proxify (result)
                        elif mutator == 'Yield':
                            result = yield result.Await ()
                        elif mutator == 'Null':
                            result = None
                        else:
                            raise ValueError ('Invalid mutator: {}'.format (mutator))

                send (result)

    #--------------------------------------------------------------------------#
    # Awaitable                                                                #
    #--------------------------------------------------------------------------#
    @Async
    def Await (self, target = None):
        """Get awaiter
        """
        if not self.Connected:
            yield self.Connect (target)
        AsyncReturn (self.Proxify ())

    #--------------------------------------------------------------------------#
    # Proxify                                                                  #
    #--------------------------------------------------------------------------#
    def Proxify (self):
        """Get proxy
        """
        return ConnectionProxy (self.sender)

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
class ConnectionProxy (object):
    """Connection proxy object
    """
    __slots__ = ('sender', 'mutators',)

    def __init__ (self, sender, mutators = None):
        self.sender = sender
        self.mutators = mutators

    #--------------------------------------------------------------------------#
    # Call                                                                     #
    #--------------------------------------------------------------------------#
    def __call__ (self, func, *args, **keys):
        """Call connection and unwrap returned result
        """
        if self.sender is None:
            raise ValueError ('Connection is disposed')
        return self.sender.Request ((func, args, keys, self.mutators))

    def __getattr__ (self, mutator):
        """Return mutated proxy
        """
        return ConnectionProxy (self.sender, self.mutators + (mutator,)
            if self.mutators else (mutator,))

    #--------------------------------------------------------------------------#
    # Proxify                                                                  #
    #--------------------------------------------------------------------------#
    def Proxify (self):
        """Get proxy
        """
        return self

    #--------------------------------------------------------------------------#
    # Reduce                                                                   #
    #--------------------------------------------------------------------------#
    def __reduce__ (self):
        """Reduce protocol
        """
        return ConnectionProxy, (self.sender, self.mutators,)

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        """Dispose connection
        """
        sender, self.sender = self.sender, None
        if sender is not None:
            sender.Send (None)

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
        return '<{0} [addr:{2}] at {1}>'.format (type (self).__name__, id (self),
            self.sender.dst if self.sender else None)

    def __repr__ (self):
        """String representation
        """
        return str (self)

# vim: nu ft=python columns=120 :
