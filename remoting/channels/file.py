# -*- coding: utf-8 -*-
from .channel import *
from ..message import *

__all__ = ('FileChannel',)
#------------------------------------------------------------------------------#
# FileChannel                                                                  #
#------------------------------------------------------------------------------#
class FileChannel (Channel):
    def __init__ (self, core = None):
        Channel.__init__ (self, core = core)

        self.ifile = None
        self.ofile = None

    #--------------------------------------------------------------------------#
    # Methods                                                                  #
    #--------------------------------------------------------------------------#
    def Send (self, message):
        return message.SaveAsync (self.ofile)

    def Recv (self):
        return Message.LoadAsync (self.ifile)
    
    def FilesSet (self, ifile, ofile):
        self.ifile = ifile
        self.ofile = ofile

        self.ifile.CloseOnExec (True)
        self.ofile.CloseOnExec (True)

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    def disconnect (self):
        if self.ifile is not None:
            self.ifile.Dispose ()
        if self.ofile is not None:
            self.ofile.Dispose ()

        Channel.disconnect (self)

# vim: nu ft=python columns=120 :
