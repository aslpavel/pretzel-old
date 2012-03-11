# -*- coding: utf-8 -*-

__all__ = ('Event',)
#-----------------------------------------------------------------------------#
# Event                                                                       #
#-----------------------------------------------------------------------------#
class Event (object):
    """Event"""
    __slots__ = ('handlers',)

    def __init__ (self):
        self.handlers = set ()

    def __call__ (self, *args, **keys):
        """Fire event"""
        for handler in self.handlers:
            handler (*args, **keys)

    #--------------------------------------------------------------------------#
    # Add Handler                                                              #
    #--------------------------------------------------------------------------#
    def Add (self, handler):
        """Add handler"""
        self.handlers.add (handler)

    def __iadd__ (self, handler):
        self.Add (handler)
        return self

    #--------------------------------------------------------------------------#
    # Remove Handler                                                           #
    #--------------------------------------------------------------------------#
    def Remove (self, handler):
        """Remove handler"""
        self.handlers.discard (handler)

    def __isub__ (self, handler):
        self.Remove (handler)
        return self

# vim: nu ft=python columns=120 :
