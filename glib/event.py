# -*- coding: utf-8 -*-
from ..event import BaseEvent

__all__ = ('GEvent',)
#------------------------------------------------------------------------------#
# GObject Event                                                                #
#------------------------------------------------------------------------------#
class GEvent (BaseEvent):
    __slots__ = ('source', 'name', 'args',)

    def __init__ (self, source, name, *args):
        self.source = source
        self.name   = name
        self.args   = args

    #--------------------------------------------------------------------------#
    # Add | Remove                                                             #
    #--------------------------------------------------------------------------#
    def Add (self, handler):
        return self.source.connect (self.name, handler, *self.args)

    def Remove (self, handler_id):
        return self.source.disconnect (handler_id, *self.args)

# vim: nu ft=python columns=120 :
