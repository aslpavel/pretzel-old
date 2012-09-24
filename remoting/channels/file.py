# -*- coding: utf-8 -*-
from .channel import Channel
from ..message import Message
from ...async import Async

__all__ = ('FileChannel',)
#------------------------------------------------------------------------------#
# FileChannel                                                                  #
#------------------------------------------------------------------------------#
class FileChannel (Channel):
    def __init__ (self, core = None):
        Channel.__init__ (self, core = core)

        self.in_file  = None
        self.out_file = None

    #--------------------------------------------------------------------------#
    # Methods                                                                  #
    #--------------------------------------------------------------------------#
    def Send (self, message):
        message.SaveAsync (self.out_file)
        return self.out_file.Flush ()

    def Recv (self, cancel = None):
        return Message.FromAsyncStream (self.in_file, cancel)

    def FilesSet (self, in_file, out_file):
        self.in_file  = in_file
        self.out_file = out_file

        self.in_file.CloseOnExec (True)
        self.out_file.CloseOnExec (True)

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def disconnect (self):
        if self.in_file is not None:
            yield self.in_file.Dispose ()
        if self.out_file is not None:
            yield self.out_file.Dispose ()

        yield Channel.disconnect (self)

# vim: nu ft=python columns=120 :
