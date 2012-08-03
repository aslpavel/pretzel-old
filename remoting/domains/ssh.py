# -*- coding: utf-8 -*-
from .default import *

from ..channels.ssh import *
from ..channels.file import *

__all__ = ('SSHDomain', )
#-----------------------------------------------------------------------------#
# Loaca SSH Domain                                                            #
#-----------------------------------------------------------------------------#
class SSHDomain (LocalDomain):
    def __init__ (self, core, host, port = None, identity_file = None,
        ssh_exec = None, py_exec = None,  push_main = None,):
        LocalDomain.__init__ (self, SSHChannel (core, host, port = port, identity_file = identity_file,
            ssh_exec = ssh_exec, py_exec = py_exec), push_main = push_main)

#-----------------------------------------------------------------------------#
# Remote SSH Domain                                                           #
#-----------------------------------------------------------------------------#
class SSHRemoteDomain (RemoteDomain):
    def __init__ (self, core):
        channel = FileChannel (core)
        channel.FilesSet (
            core.AsyncFileCreate (0),
            core.AsyncFileCreate (1))

        RemoteDomain.__init__ (self, channel)

# vim: nu ft=python columns=120 :
