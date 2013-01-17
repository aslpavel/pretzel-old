# -*- coding: utf-8 -*-

from ...async import Async, AsyncReturn, Event

__all__ = ('Remote', 'RemoteError',)
#------------------------------------------------------------------------------#
# Remote                                                                       #
#------------------------------------------------------------------------------#
class RemoteError (Exception):
    pass

class Remote (object):
    def __init__ (self, value):
        self.value = value
        self.event = Event ()

    #--------------------------------------------------------------------------#
    # Value                                                                    #
    #--------------------------------------------------------------------------#
    def Value (self, value = None):
        if value is None:
            return self.value
        else:
            value, self.value = self.value, value
            return value

    @Async
    def ValueAsync (self, value = None):
        yield self.event
        AsyncReturn (self.Value (value))

    #--------------------------------------------------------------------------#
    # Error                                                                    #
    #--------------------------------------------------------------------------#
    def Error (self, error):
        raise error

    #--------------------------------------------------------------------------#
    # Await                                                                    #
    #--------------------------------------------------------------------------#
    def __call__ (self, value = None):
        self.event (value)
        return value

    def Await (self):
        return self.event.Await ().ChainResult (lambda r: r [0])

# vim: nu ft=python columns=120 :
