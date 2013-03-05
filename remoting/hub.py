# -*- coding: utf-8 -*-
import sys
import threading
import itertools

from .result import ResultSender
from ..async import Event, FutureSourcePair
from ..async.future.compat import Raise

__all__ = ('Hub', 'HubError', 'Receiver', 'Sender', 'ReceiverSenderPair',)
#------------------------------------------------------------------------------#
# Hub Errors                                                                   #
#------------------------------------------------------------------------------#
class HubError (Exception):
    """Hub specific error
    """

#------------------------------------------------------------------------------#
# Hub                                                                          #
#------------------------------------------------------------------------------#
class Hub (object):
    """Message hub
    """
    instance_lock = threading.Lock ()
    instance      = None

    def __init__ (self):
        self.addr = itertools.count (1)
        self.handlers = {}
        self.any = Event ()

    #--------------------------------------------------------------------------#
    # Instance                                                                 #
    #--------------------------------------------------------------------------#
    @classmethod
    def Instance (cls, instance = None):
        """Global hub instance

        If ``instance`` is provided sets current global instance to ``instance``,
        otherwise returns current global instance, creates it if needed.
        """
        try:
            with cls.instance_lock:
                if instance is None:
                    if cls.instance is None:
                        cls.instance = Hub ()
                else:
                    if instance is cls.instance:
                        return instance
                    instance, cls.instance = cls.instance, instance
                return cls.instance
        finally:
            if instance:
                instance.Dispose ()

    #--------------------------------------------------------------------------#
    # Address                                                                  #
    #--------------------------------------------------------------------------#
    def Address (self):
        """Allocate new address
        """
        return Address ((next (self.addr),))

    #--------------------------------------------------------------------------#
    # Sender                                                                   #
    #--------------------------------------------------------------------------#
    def Send (self, dst, msg, src):
        handlers = self.handlers.get (dst, None)
        if not handlers:
            raise HubError ('No receiver: src:{} dst:{} msg:{}'.format (src, dst, msg))

        error = None
        for handler in tuple (handlers):
            try:
                if not handler (msg, src, dst):
                    handlers.discard (handler)
            except Exception:
                error = sys.exc_info ()

        if not handlers:
            self.handlers.pop (dst, None)

        self.any (msg, src, dst)
        if error:
            Raise (*error)

    #--------------------------------------------------------------------------#
    # Receiver                                                                 #
    #--------------------------------------------------------------------------#
    def On (self, dst, handler):
        """Subscribe handler on messages with specified destination
        """
        if dst is None:
            return self.any.On (handler)

        handlers = self.handlers.get (dst)
        if handlers is None:
            handlers = set ()
            self.handlers [dst] = handlers
        handlers.add (handler)
        return handler

    def Off (self, dst, handler):
        """Unsubscribe handler from message with specified destination
        """
        if dst is None:
            return self.any.Off (handler)

        handlers = self.handlers.get (dst)
        if handlers is None:
            return False

        try:
            handlers.remove (handler)
            if not handlers:
                del self.handlers [dst]
            return True
        except KeyError:
            return False

    #--------------------------------------------------------------------------#
    # Awaitable                                                                #
    #--------------------------------------------------------------------------#
    def Await (self):
        """Get awaiter

        Wait for the end of processing next message (or current message if
        awaiter is created inside current message handler) to any destination.
        """
        return self.any.Await ()

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        """Dispose hub
        """
        # reset global instance if needed
        with self.instance_lock:
            if self is self.instance:
                Hub.instance = None

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

#------------------------------------------------------------------------------#
# Address                                                                      #
#------------------------------------------------------------------------------#
class Address (tuple):
    """Address
    """
    __slots__ = tuple ()

    #--------------------------------------------------------------------------#
    # Operations                                                               #
    #--------------------------------------------------------------------------#
    def __add__ (self, addr):
        """Add peer to address
        """
        return Address (tuple.__add__ (self, addr))

    def __sub__ (self, count):
        """Strip count peers from address
        """
        return Address (self [:-count])

    #--------------------------------------------------------------------------#
    # Equality                                                                 #
    #--------------------------------------------------------------------------#
    def __eq__ (self, addr):
        """Equality check

        Addresses are equal when closes peer is equal.
        """
        return self [-1] == addr [-1]

    def __hash__ (self):
        """Hash

        Hashes of two equal addresses must be equal
        """
        return hash (self [-1])

    #--------------------------------------------------------------------------#
    # To String                                                                #
    #--------------------------------------------------------------------------#
    def __str__ (self):
        """String representation
        """
        return '<Address:{}>'.format ('.'.join (str (peer) for peer in reversed (self)))

    def __repr__ (self):
        """String representation
        """
        return str (self)

#------------------------------------------------------------------------------#
# Sender                                                                       #
#------------------------------------------------------------------------------#
class Sender (object):
    """Sender
    """
    __slots__ = ('hub', 'dst',)

    def __init__ (self, hub, dst, ):
        self.hub = hub
        self.dst = dst

    #--------------------------------------------------------------------------#
    # Send                                                                     #
    #--------------------------------------------------------------------------#
    def Send (self, msg, src = None):
        """Send message
        """
        self.hub.Send (self.dst, msg, src)

    #--------------------------------------------------------------------------#
    # Call                                                                     #
    #--------------------------------------------------------------------------#
    def __call__ (self, msg):
        """Call sender

        Return future object for returned message.
        """
        future, source = FutureSourcePair ()
        src = self.hub.Address ()

        def call_handler (msg, src, dst):
            source.SetResult (msg)
            return False
        self.hub.On (src, call_handler)

        self.Send (msg, Sender (self.hub, src))
        return future

    #--------------------------------------------------------------------------#
    # Request | Response                                                       #
    #--------------------------------------------------------------------------#
    def Request (self, msg):
        """Request
        """
        future, source = FutureSourcePair ()
        src = self.hub.Address ()

        def request_handler (result, src, dst):
            try:
                source.SetResult (result ())
            except Exception:
                source.SetCurrentError ()
            return False
        self.hub.On (src, request_handler)

        self.Send (msg, Sender (self.hub, src))
        return future

    def Response (self):
        """Response
        """
        return ResultSender (self)

    #--------------------------------------------------------------------------#
    # Equality                                                                 #
    #--------------------------------------------------------------------------#
    def __eq__ (self, other):
        """Equality
        """
        return self.dst == other.dst

    def __hash__ (self):
        """Hash
        """
        return hash (self.dst)

    #--------------------------------------------------------------------------#
    # To String                                                                #
    #--------------------------------------------------------------------------#
    def __str__ (self):
        """String representation
        """
        return '<{} [dst:{}]>'.format (type (self).__name__, self.dst)

    def __repr__ (self):
        """String representation
        """
        return str (self)

#------------------------------------------------------------------------------#
# Receiver                                                                     #
#------------------------------------------------------------------------------#
class Receiver (object):
    """Receiver
    """
    __slots__ = ('hub', 'dst',)

    def __init__ (self, hub, dst):
        if len (dst) > 1:
            raise ValueError ('Non local address: {}'.format (dst))

        self.hub = hub
        self.dst = dst

    #--------------------------------------------------------------------------#
    # Receive                                                                  #
    #--------------------------------------------------------------------------#
    def On (self, handler):
        """Subscribe handler
        """
        return self.hub.On (self.dst, handler)

    def Off (self, handler):
        """Unsubscribe handler
        """
        return self.hub.Off (self.dst, handler)

    #--------------------------------------------------------------------------#
    # Awaitable                                                                #
    #--------------------------------------------------------------------------#
    def Await (self):
        """Get awaiter

        Return future object for message-sender pair.
        """
        future, source = FutureSourcePair ()

        def handler (msg, src, dst):
            source.SetResult ((msg, src))
            return False
        self.hub.On (self.dst, handler)

        return future

    #--------------------------------------------------------------------------#
    # Equality                                                                 #
    #--------------------------------------------------------------------------#
    def __eq__ (self, other):
        """Equality
        """
        return self.dst == other.dst

    def __hash__ (self):
        """Hash
        """
        return hash (self.dst)

    #--------------------------------------------------------------------------#
    # To String                                                                #
    #--------------------------------------------------------------------------#
    def __str__ (self):
        """String representation
        """
        return '<{} [dst:{}]>'.format (type (self).__name__, self.dst)

    def __repr__ (self):
        """String representation
        """
        return str (self)

#------------------------------------------------------------------------------#
# Receiver Sender Pair                                                         #
#------------------------------------------------------------------------------#
def ReceiverSenderPair (addr = None, hub = None):
    """Receiver-sender pair
    """
    hub  = hub or Hub.Instance ()
    addr = addr or hub.Address ()

    return Receiver (hub, addr), Sender (hub, addr)

# vim: nu ft=python columns=120 :
