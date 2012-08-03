# -*- coding: utf-8 -*-
from .default import *

from ..channels.fork import *
from ..channels.file import *

__all__ = ('ForkDomain', )
#-----------------------------------------------------------------------------#
# Local Fork Domain                                                           #
#-----------------------------------------------------------------------------#
class ForkDomain (LocalDomain):
    def __init__ (self, core, command = None, push_main = None):
        LocalDomain.__init__ (self, ForkChannel (core, command), push_main = push_main)

#-----------------------------------------------------------------------------#
# Remote Fork Domain                                                          #
#-----------------------------------------------------------------------------#
class ForkRemoteDomain (RemoteDomain):
    def __init__ (self, core, rr, rw):
        channel = FileChannel (core)
        channel.FilesSet (
        	core.AsyncFileCreate (rr, closefd = True),
        	core.AsyncFileCreate (rw, closefd = True))

        RemoteDomain.__init__ (self, channel)

# vim: nu ft=python columns=120 :
