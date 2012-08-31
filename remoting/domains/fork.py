# -*- coding: utf-8 -*-
from .default import LocalDomain, RemoteDomain

from ..channels.fork import ForkChannel
from ..channels.file import FileChannel
from ...async.core   import AsyncFile

__all__ = ('ForkDomain', )
#-----------------------------------------------------------------------------#
# Local Fork Domain                                                           #
#-----------------------------------------------------------------------------#
class ForkDomain (LocalDomain):
    def __init__ (self, command = None, push_main = None, buffer_size = None, core = None):
        LocalDomain.__init__ (self, ForkChannel (command, buffer_size, core), push_main)

#-----------------------------------------------------------------------------#
# Remote Fork Domain                                                          #
#-----------------------------------------------------------------------------#
class ForkRemoteDomain (RemoteDomain):
    def __init__ (self, rr, rw, buffer_size, core):
        channel = FileChannel (core)
        channel.FilesSet (
            AsyncFile (rr, buffer_size = buffer_size, core = channel.core),
            AsyncFile (rw, buffer_size = buffer_size, core = channel.core))

        RemoteDomain.__init__ (self, channel)

# vim: nu ft=python columns=120 :
