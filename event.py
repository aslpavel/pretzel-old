# -*- coding: utf-8 -*-
from .async import Future, FutureSource, FutureCanceled, Async

__all__ = ('Event', 'AsyncEvent', 'DelegatedEvent', 'AccumulativeEvent',)
#------------------------------------------------------------------------------#
# Base Event                                                                   #
#------------------------------------------------------------------------------#
class BaseEvent (object):
    """Base Event Type
    """
    __slots__ = tuple ()

    #--------------------------------------------------------------------------#
    # Fire                                                                     #
    #--------------------------------------------------------------------------#
    def __call__ (self, *args):
        """Fire event
        """
        return self.Fire (*args)

    def Fire (self, *args):
        """Fire event
        """
        raise NotImplementedError ()

    #--------------------------------------------------------------------------#
    # Add                                                                      #
    #--------------------------------------------------------------------------#
    def Add (self, handler):
        """Add new event handler

        Returns event handler identifier.
        """
        raise NotImplementedError ()

    def __iadd__ (self, handler):
        """Add new event handler

        Returns event handler identifier. If handler returns False it will be
        automatically unsubscribe
        """
        self.Add (handler)
        return self

    #--------------------------------------------------------------------------#
    # Remove                                                                   #
    #--------------------------------------------------------------------------#
    def Remove (self, handler_id):
        """Remove existing event handler by its identifier
        """
        raise NotImplementedError ()

    def __isub__ (self, handler_id):
        """Remove existing event handler by its identifier
        """
        self.Remove (handler_id)
        return self

    #--------------------------------------------------------------------------#
    # Await                                                                    #
    #--------------------------------------------------------------------------#
    def Await (self, cancel = None):
        """Asynchronously await next event
        """
        source     = FutureSource ()
        handler_id = None

        # handler
        def handler (*args):
            source.ResultSet (args)
            return False
        handler_id = self.Add (handler)

        # cancel
        if cancel:
            def cancel_continuation (result, error):
                self.Remove (handler_id)
                source.ErrorRaise (FutureCanceled ())

            cancel.Continue (cancel_continuation)

        return source.Future

#------------------------------------------------------------------------------#
# Event                                                                        #
#------------------------------------------------------------------------------#
class Event (BaseEvent):
    """List based event
    """
    __slots__ = ('handlers',)

    def __init__ (self):
        self.handlers = []

    #--------------------------------------------------------------------------#
    # Fire                                                                     #
    #--------------------------------------------------------------------------#

    def Fire (self, *args):
        for handler in tuple (self.handlers):
            if handler (*args):
                continue
            self.Remove (handler)

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
# Asynchronous Event                                                           #
#------------------------------------------------------------------------------#
class AsyncEvent (Event):
    """Asynchronous list based event
    """
    __slots__ = Event.__slots__

    #--------------------------------------------------------------------------#
    # Fire                                                                     #
    #--------------------------------------------------------------------------#
    @Async
    def Fire (self, *args):
        """Fire asynchronous event

        New handler won't be executed unless previous is completed.
        """
        for handler in tuple (self.handlers):
            result = handler (*args)
            if isinstance (result, Future):
                if (yield result):
                    continue
            elif result:
                continue
            self.Remove (handler)

#------------------------------------------------------------------------------#
# Delegated Event                                                              #
#------------------------------------------------------------------------------#
class DelegatedEvent (BaseEvent):
    """Delegated event
    """
    __slots__ = ('add', 'remove')

    def __init__ (self, add, remove):
        self.add    = add
        self.remove = remove

    #--------------------------------------------------------------------------#
    # Add | Remove                                                             #
    #--------------------------------------------------------------------------#

    def Add (self, handler):
        def handler_wrapper (*args):
            result = handler (*args)
            if not result:
                self.Remove (handler_id)
            return result

        handler_wrapper.__name__ = handler.__name__
        handler_wrapper.__doc__ = handler.__doc__

        handler_id = self.add (handler_wrapper)
        return handler_id

    def Remove (self, handler_id):
        return self.remove (handler_id)

#------------------------------------------------------------------------------#
# Accumulative Event                                                           #
#------------------------------------------------------------------------------#
class AccumulativeEvent (Event):
    """Accumulative event

    Accumulate events and fire them all for newly added handlers
    """
    __slots__ = Event.__slots__ + ('values',)

    def __init__ (self):
        Event.__init__ (self)
        self.values = []

    #--------------------------------------------------------------------------#
    # Fire                                                                     #
    #--------------------------------------------------------------------------#

    def Fire (self, *args):
        Event.Fire (self, *args)
        self.values.append (args)

    #--------------------------------------------------------------------------#
    # Add | Remove                                                             #
    #--------------------------------------------------------------------------#

    def Add (self, handler):
        for args in self.values:
            if handler (*args):
                continue
            self.Remove (handler)
        return Event.Add (self, handler)

# vim: nu ft=python columns=120 :
