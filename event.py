# -*- coding: utf-8 -*-
from .async import Async, FutureSource, FutureCanceled

__all__ = ('Event', 'AsyncEvent', 'DelegatedEvent')
#------------------------------------------------------------------------------#
# Base Event                                                                   #
#------------------------------------------------------------------------------#
class BaseEvent (object):
    __slots__ = tuple ()

    #--------------------------------------------------------------------------#
    # Fire                                                                     #
    #--------------------------------------------------------------------------#
    def __call__ (self, *args):
        raise NotImplementedError ()

    #--------------------------------------------------------------------------#
    # Add                                                                      #
    #--------------------------------------------------------------------------#
    def Add (self, handler):
        raise NotImplementedError ()

    def __iadd__ (self, handler):
        self.Add (handler)
        return self

    #--------------------------------------------------------------------------#
    # Remove                                                                   #
    #--------------------------------------------------------------------------#
    def Remove (self, handler_id):
        raise NotImplementedError ()

    def __isub__ (self, handler_id):
        self.Remove (handler_id)
        return self

    #--------------------------------------------------------------------------#
    # Await                                                                    #
    #--------------------------------------------------------------------------#
    def Await (self, cancel = None):
        source = FutureSource ()

        # handler
        def handler (*args):
            self.Remove (handler_id)
            source.ResultSet (args)

        handler_id = self.Add (handler)

        # cancel
        if cancel:
            def cancel_continuation (future):
                self.Remove (handler_id)
                source.ErrorRaise (FutureCanceled ())

            cancel.Continue (cancel_continuation)

        return source.Future

#------------------------------------------------------------------------------#
# Event                                                                        #
#------------------------------------------------------------------------------#
class Event (BaseEvent):
    __slots__ = ('handlers',)

    def __init__ (self):
        self.handlers = []

    #--------------------------------------------------------------------------#
    # Fire                                                                     #
    #--------------------------------------------------------------------------#
    def __call__ (self, *args, **keys):
        for handler in tuple (self.handlers):
            handler (*args, **keys)

    #--------------------------------------------------------------------------#
    # Add | Remove                                                             #
    #--------------------------------------------------------------------------#
    def Add (self, handler):
        self.handlers.append (handler)
        return handler

    def Remove (self, handler_id):
        try:
            self.handlers.remove (handler_id)
            return True
        except ValueError: pass
        return False

#------------------------------------------------------------------------------#
# Async Event                                                                  #
#------------------------------------------------------------------------------#
class AsyncEvent (Event):
    __slots__ = Event.__slots__

    #--------------------------------------------------------------------------#
    # Fire                                                                     #
    #--------------------------------------------------------------------------#
    @Async
    def __call__ (self, *args, **keys):
        for handler in tuple (self.handlers):
            future = handler (*args, **keys)
            if isinstance (future, BaseFuture):
                yield future

#------------------------------------------------------------------------------#
# Delegated Event                                                              #
#------------------------------------------------------------------------------#
class DelegatedEvent (BaseEvent):
    __slots__ = ('add', 'remove')

    def __init__ (self, add, remove):
        self.add    = add
        self.remove = remove

    #--------------------------------------------------------------------------#
    # Add | Remove                                                             #
    #--------------------------------------------------------------------------#
    def Add (self, handler):
        return self.add (handler)

    def Remove (self, handler_id):
        return self.remove (handler_id)
# vim: nu ft=python columns=120 :
