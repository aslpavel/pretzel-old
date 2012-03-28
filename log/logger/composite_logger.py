# -*- coding: utf-8 -*-
from ...disposable import *
from ...observer import *

__all__ = ('CompositeLogger',)
#------------------------------------------------------------------------------#
# Composite Logger                                                             #
#------------------------------------------------------------------------------#
class CompositeLogger (Observer, Observable):
    def __init__ (self, *loggers):
        self.loggers = list (loggers)

    #--------------------------------------------------------------------------#
    # Observer Interface                                                       #
    #--------------------------------------------------------------------------#
    def OnNext (self, value):
        for logger in self.loggers:
            try: logger.OnNext (value)
            except Exception: pass

    #--------------------------------------------------------------------------#
    # Observable Interface                                                     #
    #--------------------------------------------------------------------------#
    def Subscribe (self, logger):
        self.loggers.append (logger)
        return Disposable (lambda: self.loggers.remove (logger))

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        for logger in self.loggers:
            try: logger.Dispose ()
            except Exception: pass

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

# vim: nu ft=python columns=120 :
