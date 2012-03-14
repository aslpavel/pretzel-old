# -*- coding: utf-8 -*-
# local
from .pair import *

# channels
from ..channels.fork import *
from ..channels.file import *

__all__ = ('ForkDomain', )
#-----------------------------------------------------------------------------#
# Local Fork Domain                                                           #
#-----------------------------------------------------------------------------#
class ForkDomain (LocalDomain):
    def __init__ (self, core, push_main = True):
        LocalDomain.__init__ (self, ForkChannel (core), push_main = push_main)

#-----------------------------------------------------------------------------#
# Remote Fork Domain                                                          #
#-----------------------------------------------------------------------------#
class ForkRemoteDomain (RemoteDomain):
    def __init__ (self, core, rr, rw):
        RemoteDomain.__init__ (self, FileChannel (core, rr, rw, closefd = True))

# vim: nu ft=python columns=120 :
