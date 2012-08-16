# -*- coding: utf-8 -*-
from .default import *

from ..channels.fork import *
from ..channels.file import *
from ...async.core import *

__all__ = ('ForkDomain', )
#-----------------------------------------------------------------------------#
# Local Fork Domain                                                           #
#-----------------------------------------------------------------------------#
class ForkDomain (LocalDomain):
    def __init__ (self, command = None, push_main = None, core = None):
        LocalDomain.__init__ (self, ForkChannel (command, core), push_main = push_main)

#-----------------------------------------------------------------------------#
# Remote Fork Domain                                                          #
#-----------------------------------------------------------------------------#
class ForkRemoteDomain (RemoteDomain):
    def __init__ (self, rr, rw, core = None):
        channel = FileChannel (core or Core.Instance ())
        channel.FilesSet (AsyncFile (rr, core = channel.core), AsyncFile (rw, core = channel.core))

        RemoteDomain.__init__ (self, channel)

# vim: nu ft=python columns=120 :
