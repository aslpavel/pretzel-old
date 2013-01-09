# -*- coding: utf-8 -*-
from ..async import Event

__all__ = ('GEvent',)
#------------------------------------------------------------------------------#
# GObject Event                                                                #
#------------------------------------------------------------------------------#
class GEvent (Event):
    __slots__ = ('source', 'name', 'args',)

    def __init__ (self, source, name, *args):
        self.source = source
        self.name   = name
        self.args   = args

    #--------------------------------------------------------------------------#
    # On | Off                                                                 #
    #--------------------------------------------------------------------------#
    def On (self, handler):
        return self.source.connect (self.name, handler, *self.args)

    def Off (self, handler_id):
        return self.source.disconnect (handler_id, *self.args)

# vim: nu ft=python columns=120 :
