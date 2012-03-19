# -*- coding: utf-8 -*-
from ...disposable import *

__all__ = ('BindPool',)
#------------------------------------------------------------------------------#
# Bind Pool                                                                    #
#------------------------------------------------------------------------------#
class BindPool (dict):
    """Bind key to value and return unbinder (Disposable)"""

    def Bind (self, key, value):
        if self.get (key) is not None:
            raise ValueError ('\'{0}\' has already been bound'.format (key))
        self [key] = value
        return Disposable (lambda : self.pop (key))

# vim: nu ft=python columns=120 :
