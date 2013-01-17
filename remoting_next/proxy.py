# -*- coding: utf-8 -*-

from .hub import ReceiverSenderPair
from .result import ResultSender
from ..async import Async, LazyFuture

__all__ = ('Proxify',)
#------------------------------------------------------------------------------#
# Proxy Constants                                                              #
#------------------------------------------------------------------------------#
PROXY_CALL    = 0x01
PROXY_GETATTR = 0x02
PROXY_SETATTR = 0x04
PROXY_AWAIT   = 0x08
PROXY_DISPOSE = 0x10
PROXY_MUTATORS = {'Proxy', 'Yield', 'Null'}

#------------------------------------------------------------------------------#
# Proxy                                                                        #
#------------------------------------------------------------------------------#
class Proxy (object):
    """Proxy object
    """
    __slots__  = ('sender',)

    def __init__ (self, sender):
        object.__setattr__ (self, 'sender', sender)

    #--------------------------------------------------------------------------#
    # Call                                                                     #
    #--------------------------------------------------------------------------#
    def __call__ (self, *args, **keys):
        """Call proxy
        """
        if self.sender is None:
            raise RuntimeError ('Proxy is disposed')
        return self.sender.Request ((PROXY_CALL, None, (args, keys), None))

    #--------------------------------------------------------------------------#
    # Attributes                                                               #
    #--------------------------------------------------------------------------#
    def __getattr__ (self, name):
        """Get attribute
        """
        if self.sender is None:
            raise RuntimeError ('Proxy is disposed')

        if name in PROXY_MUTATORS:
            return ProxyAttribute (self.sender, None, (name,))
        else:
            return ProxyAttribute (self.sender, name, None)

    def __setattr__ (self, name, value):
        """Set attribute
        """
        if self.sender is None:
            raise RuntimeError ('Proxy is disposed')
        return self.sender.Request ((PROXY_SETATTR, name, value, None))

    #--------------------------------------------------------------------------#
    # Awaitable                                                                #
    #--------------------------------------------------------------------------#
    def Await (self):
        """Get awaiter
        """
        if self.sender is None:
            raise RuntimeError ('Proxy is disposed')
        return self.sender.Request ((PROXY_AWAIT, None, None, None))

    #--------------------------------------------------------------------------#
    # Proxify                                                                  #
    #--------------------------------------------------------------------------#
    def Proxify (self):
        """Get proxy to the object
        """
        return self

    #--------------------------------------------------------------------------#
    # Reduce                                                                   #
    #--------------------------------------------------------------------------#
    def __reduce__ (self):
        """Reduce protocol
        """
        return Proxy, (self.sender,)

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self, deep = None):
        """Dispose proxy
        """
        if self.sender is not None:
            self.sender.Send ((PROXY_DISPOSE, None, deep, None))
            object.__setattr__ (self, 'sender', None)

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
        return '<{} at {}>'.format (type (self).__name__,
            None if self.sender is None else self.sender.dst)

    def __repr__ (self):
        """String representation
        """
        return str (self)


#------------------------------------------------------------------------------#
# Proxy Attribute                                                              #
#------------------------------------------------------------------------------#
class ProxyAttribute (LazyFuture):
    """Proxy attribute object
    """
    __slots__ = LazyFuture.__slots__ + ('sender', 'name', 'mutators')

    def __init__ (self, sender, name, mutators):
        LazyFuture.__init__ (self, lambda: sender.Request ((PROXY_GETATTR, name, None, mutators)))

        self.sender = sender
        self.name = name
        self.mutators = mutators

    #--------------------------------------------------------------------------#
    # Call                                                                     #
    #--------------------------------------------------------------------------#
    def __call__ (self, *args, **keys):
        """Call method
        """
        return self.sender.Request ((PROXY_CALL, self.name, (args, keys), self.mutators))

    #--------------------------------------------------------------------------#
    # Mutators                                                                 #
    #--------------------------------------------------------------------------#
    def __getattr__ (self, mutator):
        """Return mutated attribute
        """
        if mutator not in PROXY_MUTATORS:
            raise AttributeError ('Unknown mutator \'{}\''.format (mutator))

        return ProxyAttribute (self.sender, self.name,
            self.mutators + (mutator,) if self.mutators else (mutator,))

    #--------------------------------------------------------------------------#
    # Reduce                                                                   #
    #--------------------------------------------------------------------------#
    def __reduce__ (self):
        """Reduce protocol
        """
        return ProxyAttribute, (self.sender, self.name, self.mutators,)

    #--------------------------------------------------------------------------#
    # To String                                                                #
    #--------------------------------------------------------------------------#
    def __str__ (self):
        """String representation
        """
        return '<{0} [name:{2} addr:{3} mutators:{4}] at {1}>'.format (
            type (self).__name__, id (self), self.name, self.sender.dst,
            ','.join (self.mutators) if self.mutators else None)

    def __repr__ (self):
        """String representation
        """
        return str (self)

#------------------------------------------------------------------------------#
# Proxify                                                                      #
#------------------------------------------------------------------------------#
def Proxify (target, hub = None):
    """Create proxy object for specified target object
    """
    proxy = getattr (target, 'Proxify', None)
    if proxy is not None:
        return proxy ()

    receiver, sender = ReceiverSenderPair (hub = hub)

    @Async
    def proxy_handler_coro (msg, src):
        """Proxy handler coroutine
        """
        with ResultSender (src) as send:
            action, name, value, mutators = msg
            if   action == PROXY_SETATTR: result = setattr (target, name, value)
            elif action == PROXY_GETATTR: result = getattr (target, name)
            elif action == PROXY_CALL:    result = (target (*value [0], **value [1]) if name is None else
                                                    getattr (target, name) (*value [0], **value [1]))
            elif action == PROXY_AWAIT:   result = yield target.Await ()
            elif action == PROXY_DISPOSE:
                # Postpone handler removal as otherwise it will be re-subscribed
                # when proxy_handler returns True
                yield receiver.hub
                receiver.Off (proxy_handler)
                if value:
                    target.Dispose ()
                return
            else:
                raise ValueError ('Unknown action: {}'.format (action))

            if mutators:
                for mutator in mutators:
                    if   mutator == 'Proxy': result = Proxify (result)
                    elif mutator == 'Yield': result = yield result.Await ()
                    elif mutator == 'Null' : result = None
                    else:
                        raise ValueError ('Invalid mutator: {}'.format (mutator))

            send (result)

    def proxy_handler (msg, src, dst):
        """Proxy handler
        """
        proxy_handler_coro (msg, src)
        return True

    receiver.On (proxy_handler)
    return Proxy (sender)

# vim: nu ft=python columns=120 :
