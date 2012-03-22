# -*- coding: utf-8 -*-
from .pair import *
from ..channels.fork import *
from ..channels.file import *

__all__ = ('ForkDomain', )
#-----------------------------------------------------------------------------#
# Local Fork Domain                                                           #
#-----------------------------------------------------------------------------#
class ForkDomain (LocalDomain):
    def __init__ (self, core, push_main = True, run = None):
        LocalDomain.__init__ (self, ForkChannel (core), push_main = push_main, run = run)

#-----------------------------------------------------------------------------#
# Remote Fork Domain                                                          #
#-----------------------------------------------------------------------------#
class ForkRemoteDomain (RemoteDomain):
    def __init__ (self, core, rr, rw):
        # create channel
        channel = FileChannel (core)
        channel.in_file = core.AsyncFileCreate (rr, closefd = True)
        channel.out_file = core.AsyncFileCreate (rw, closefd = True)

        RemoteDomain.__init__ (self, channel, run = True)

# vim: nu ft=python columns=120 :
