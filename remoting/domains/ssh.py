# -*- coding: utf-8 -*-
from .domain import *

# channels
from ..channels.ssh import *
from ..channels.file import *

# services
from ..services.linker import *
from ..services.importer import *

__all__ = ('SSHDomain', )
#-----------------------------------------------------------------------------#
# Local SSH Domain                                                            #
#-----------------------------------------------------------------------------#
class SSHDomain (Domain):
    def __init__ (self, core, *args, **keys):
        Domain.__init__ (self, SSHChannel (core, *args, **keys), [
            LinkerService (),
        ])

#-----------------------------------------------------------------------------#
# Remote SSH Domain                                                           #
#-----------------------------------------------------------------------------#
class SSHRemoteDomain (Domain):
    def __init__ (self, core):
        Domain.__init__ (self, FileChannel (core, 0, 1), [
            LinkerService (),
        ])

# vim: nu ft=python columns=120 :
