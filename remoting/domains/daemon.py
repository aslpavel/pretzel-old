# -*- coding: utf-8 -*-
import os
from .pair import *
from ..channels.daemon import *
from ..channels.file import *

__all__ = ('DaemonDomain', )
#-----------------------------------------------------------------------------#
# Local Daemon Domain                                                         #
#-----------------------------------------------------------------------------#
class DaemonDomain (LocalDomain):
    def __init__ (self, core, path, run = None):
        LocalDomain.__init__ (self, DaemonChannel (core, path), run = run)

# vim: nu ft=python columns=120 :
