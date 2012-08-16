# -*- coding: utf-8 -*-
from .default import *

from ..channels.ssh import *
from ..channels.file import *
from ...async.core import *

__all__ = ('SSHDomain', )
#-----------------------------------------------------------------------------#
# Loaca SSH Domain                                                            #
#-----------------------------------------------------------------------------#
class SSHDomain (LocalDomain):
    def __init__ (self, host, port = None, identity_file = None,
        ssh_exec = None, py_exec = None,  push_main = None, core = None,):
        LocalDomain.__init__ (self, SSHChannel (host, port = port, identity_file = identity_file,
            ssh_exec = ssh_exec, py_exec = py_exec, core = core), push_main = push_main)

#-----------------------------------------------------------------------------#
# Remote SSH Domain                                                           #
#-----------------------------------------------------------------------------#
class SSHRemoteDomain (RemoteDomain):
    def __init__ (self, core = None):
        channel = FileChannel (core or Core.Instance ())
        channel.FilesSet (AsyncFile (0, core = channel.core), AsyncFile (1, core = channel.core))

        RemoteDomain.__init__ (self, channel)

# vim: nu ft=python columns=120 :
