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

        self.in_file     = None
        self.out_file    = None

    #--------------------------------------------------------------------------#
    # Methods                                                                  #
    #--------------------------------------------------------------------------#
    def Send (self, message):
        return message.SaveAsync (self.out_file)

    def Recv (self, cancel = None):
        return Message.LoadAsync (self.in_file, cancel)

    def FilesSet (self, in_file, out_file):
        self.in_file  = in_file
        self.out_file = out_file

        self.in_file.CloseOnExec (True)
        self.out_file.CloseOnExec (True)

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    def disconnect (self):
        if self.in_file is not None:
            self.in_file.Dispose ()
        if self.out_file is not None:
            self.out_file.Dispose ()

        Channel.disconnect (self)

# vim: nu ft=python columns=120 :
