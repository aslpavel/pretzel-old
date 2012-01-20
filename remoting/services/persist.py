# -*- coding: utf-8 -*-
from .service import *

__all__ = ('PersistService',)

#------------------------------------------------------------------------------#
# Ports                                                                        #
#------------------------------------------------------------------------------#
PERSISTENCE_PERSIST = 2

#------------------------------------------------------------------------------#
# Object Persistence Service                                                   #
#------------------------------------------------------------------------------#
class PersistService (Service):
    """Maps arbitrary objects between peers

    Remark: Both remote and local instances of this client
        must register persistent objects in the same order
    """
    def __init__ (self):
        Service.__init__ (self, persistence = [
            (PERSISTENCE_PERSIST, self.save_OBJ, self.restore_OBJ)
        ])

        self.i2t, self.t2i = {}, {}
        self.Add (self)

    def Add (self, target):
        if target is None:
            raise ValueError ('None can not be added as persistent')

        index = len (self.i2t)
        self.i2t [index], self.t2i [target] = target, index

    def __iadd__ (self, target):
        self.Add (target)
        return self

    def save_OBJ (self, target):
        if target.__hash__ is not None and not isinstance (target, tuple):
            return self.t2i.get (target)

    def restore_OBJ (self, state):
        return self.i2t [state]

# vim: nu ft=python columns=120 :
