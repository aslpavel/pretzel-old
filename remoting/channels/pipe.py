# -*- coding: utf-8 -*-
import os

from ...async import BufferedFile

__all__ = ('Pipe',)
#------------------------------------------------------------------------------#
# Pipe                                                                         #
#------------------------------------------------------------------------------#
class Pipe (object):
    def __init__ (self, buffer_size, core):
        self.buffer_size = buffer_size
        self.core = core

        self.fds = os.pipe ()

    #--------------------------------------------------------------------------#
    # Properties                                                               #
    #--------------------------------------------------------------------------#
    @property
    def Read (self):
        if self.fds is None:
            return
        return self.fds [0]

    @property
    def Write (self):
        if self.fds is None:
            return
        return self.fds [1]

    #--------------------------------------------------------------------------#
    # Detach                                                                   #
    #--------------------------------------------------------------------------#
    def DetachRead (self, fd = None):
        return self.detach (True, fd)

    def DetachReadAsync (self):
        return self.detach_async (True)

    def DetachWrite (self, fd = None):
        return self.detach (False, fd)

    def DetachWriteAsync (self):
        return self.detach_async (False)

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    def detach (self, read, fd = None):
        if self.fds is None:
            raise ValueError ('Pipe has already been detached')

        fds, self.fds = self.fds, None
        to_return, to_close = fds if read else reversed (fds)

        os.close (to_close)
        if fd is None or fd == to_return:
            return to_return
        else:
            os.dup2  (to_return, fd)
            os.close (to_return)
            return fd

    def detach_async (self, read):
        async = BufferedFile (self.detach (read), buffer_size = self.buffer_size, core = self.core)
        async.CloseOnExec (True)
        return async

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        if self.fds is None:
            return

        fds, self.fds = self.fds, None
        for fd in fds:
            os.close (fd)

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

# vim: nu ft=python columns=120 :
