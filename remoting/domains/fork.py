# -*- coding: utf-8 -*-
from .pair import *
from ..channels.fork import *
from ..channels.file import *
from ..utils.fork import *

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
        RemoteDomain.__init__ (self, FileChannel (core, rr, rw, closefd = True), run = True)

# vim: nu ft=python columns=120 :
