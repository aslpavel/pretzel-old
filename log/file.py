# -*- coding: utf-8 -*-
from .log import Log
from .text import TextLogger

__all__ = ('FileLogger',)
#------------------------------------------------------------------------------#
# FileLogger                                                                   #
#------------------------------------------------------------------------------#
class FileLogger (TextLogger):
    def __init__ (self, filename):
        TextLogger.__init__ (self, open (filename, 'a+'))

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        TextLogger.Dispose (self)
        self.stream.close ()
    
# register
Log.LoggerRegister ('file', FileLogger)

# vim: nu ft=python columns=120 :
