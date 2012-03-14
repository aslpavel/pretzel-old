# -*- coding: utf-8 -*-
# local
from .pair import *

# channels
from ..channels.ssh import *
from ..channels.file import *

__all__ = ('SSHDomain', )
#-----------------------------------------------------------------------------#
# Local SSH Domain                                                            #
#-----------------------------------------------------------------------------#
class SSHDomain (LocalDomain):
    def __init__ (self, core, host, port = None, identity_file = None, ssh_exec = None, py_exec = None,
        push_main = True):
        LocalDomain.__init__ (self, SSHChannel (core, host, port = port, identity_file= identity_file,
                ssh_exec = ssh_exec, py_exec = py_exec), push_main = push_main)

#-----------------------------------------------------------------------------#
# Remote SSH Domain                                                           #
#-----------------------------------------------------------------------------#
class SSHRemoteDomain (RemoteDomain):
    def __init__ (self, core):
        RemoteDomain.__init__ (self, FileChannel (core, 0, 1, closefd = True))

# vim: nu ft=python columns=120 :
