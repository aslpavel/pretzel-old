# -*- coding: utf-8 -*-
from .channel import Channel
from ..message import Message

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

    def Recv (self, cancel = None):
        return Message.LoadAsync (self.ifile, cancel)

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
