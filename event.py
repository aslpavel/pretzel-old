# -*- coding: utf-8 -*-
from .async import *

__all__ = ('Event', 'AsyncEvent')
#------------------------------------------------------------------------------#
# Event                                                                        #
#------------------------------------------------------------------------------#
class Event (object):
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
    # Add Handler                                                              #
    #--------------------------------------------------------------------------#
    def Add (self, handler):
        """Add handler"""
        self.handlers.append (handler)

    def __iadd__ (self, handler):
        self.Add (handler)
        return self

    #--------------------------------------------------------------------------#
    # Remove Handler                                                           #
    #--------------------------------------------------------------------------#
    def Remove (self, handler):
        """Remove handler"""
        self.handlers.remove (handler)

    def __isub__ (self, handler):
        self.Remove (handler)
        return self

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
            yield handler (*args, **keys)

# vim: nu ft=python columns=120 :
