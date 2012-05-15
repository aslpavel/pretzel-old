# -*- coding: utf-8 -*-
from .. import event

__all__ = ('GEvent',)
#------------------------------------------------------------------------------#
# GObject Event                                                                #
#------------------------------------------------------------------------------#
class GEvent (event.BaseEvent):
    __slots__ = ('source', 'name')

    def __init__ (self, source, name):
        self.source = source
        self.name   = name

    #--------------------------------------------------------------------------#
    # Add | Remove                                                             #
    #--------------------------------------------------------------------------#
    def Add (self, handler):
        return self.source.connect (self.name, handler)

    def Remove (self, handler_id):
        return self.source.disconnect (handler_id)

# vim: nu ft=python columns=120 :
