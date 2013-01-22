# -*- coding: utf-8 -*-

from .hub import ReceiverSenderPair
from .result import Result, ResultPrintException
from .expr import (LoadArgExpr, LoadConstExpr, CallExpr, GetAttrExpr, SetAttrExpr,
                   GetItemExpr, SetItemExpr, AwaitExpr, Code)

__all__ = ('Proxy', 'Proxify',)
#------------------------------------------------------------------------------#
# Proxy                                                                        #
#------------------------------------------------------------------------------#
class Proxy (object):
    """Proxy object
    """
    __slots__ = ('sender', 'expr', 'code',)

    def __init__ (self, sender, expr):
        object.__setattr__ (self, 'sender', sender)
        object.__setattr__ (self, 'expr', expr)
        object.__setattr__ (self, 'code', None)

    #--------------------------------------------------------------------------#
    # Awaitable                                                                #
    #--------------------------------------------------------------------------#
    def Await (self):
        """Get awaitable

        Resolves to result of expression execution.
        """
        if self.code is None:
            code = Code ()
            self.expr.Compile (code)
            object.__setattr__ (self, 'code', code)
        return self.sender.Request (self.code)

    #--------------------------------------------------------------------------#
    # Proxy                                                                    #
    #--------------------------------------------------------------------------#
    def Proxy (self):
        """Get proxy
        """
        return self

    #--------------------------------------------------------------------------#
    # Pickle                                                                   #
    #--------------------------------------------------------------------------#
    def __reduce__ (self):
        """Reduce proxy
        """
        return Proxy, (self.sender, self.expr)

    #--------------------------------------------------------------------------#
    # Operations                                                               #
    #--------------------------------------------------------------------------#
    def __call__ (self, *args, **keys):
        """Call
        """
        return Proxy (self.sender, CallExpr (self.expr, *args, **keys))

    def __getattr__ (self, name):
        """Get attribute
        """
        return Proxy (self.sender, GetAttrExpr (self.expr, name))

    def __setattr__ (self, name, value):
        """Set attribute
        """
        code = Code ()
        SetAttrExpr (self.expr, name, value).Compile (code)
        self.sender.Send (code)

    def __getitem__ (self, item):
        """Get item
        """
        return Proxy (self.sender, GetItemExpr (self.expr, item))

    def __setitem__ (self, item, value):
        """Set item
        """
        code = Code ()
        SetItemExpr (self.expr, item, value).Compile (code)
        self.sender.Send (code)

    def __invert__ (self):
        """Await
        """
        return Proxy (self.sender, AwaitExpr (self.expr))

    def __pos__ (self):
        """Proxify
        """
        return Proxy (self.sender, CallExpr (LoadConstExpr (Proxify), self.expr))

    #--------------------------------------------------------------------------#
    # To String                                                                #
    #--------------------------------------------------------------------------#
    def __str__ (self):
        """String representation
        """
        return '<Proxy [addr:{} expr:{}]>'.format (
            self.sender.dst if self.sender else None, self.expr)

    def __repr__ (self):
        """String representation
        """
        return str (self)

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    def __enter__ (self):
        """Enter proxy scope
        """
        return self

    def __exit__ (self, et, eo, tb):
        """Leave proxy scope

        Proxy will be disposed and want won't reply to any further request.
        """
        if self.sender is not None:
            self.sender.Send (None)
            object.__setattr__ (self, 'sender', None)
        return False

#------------------------------------------------------------------------------#
# Proxify                                                                      #
#------------------------------------------------------------------------------#
def Proxify (target, hub = None):
    proxy = getattr (target, 'Proxy', None)
    if proxy is not None:
        return proxy ()

    receiver, sender = ReceiverSenderPair (hub = hub)

    def proxy_handler (msg, src, dst):
        if msg is None:
            # Unsubscribe proxy handler
            return False

        def proxy_cont (result, error):
            if src is not None:
                if error is None:
                    src.Send (Result ().SetResult (result))
                else:
                    src.Send (Result ().SetError (error))
            elif error is not None:
                # Print exception there is no reply port is provided and
                # exception has happened.
                ResultPrintException (*error)

        msg (target).Then (proxy_cont)
        return True

    receiver.On (proxy_handler)
    return Proxy (sender, LoadArgExpr (0))

# vim: nu ft=python columns=120 :
