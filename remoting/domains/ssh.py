# -*- coding: utf-8 -*-
from .pair import *
from ..channels.ssh import *
from ..channels.file import *

__all__ = ('SSHDomain', )
#-----------------------------------------------------------------------------#
# Local SSH Domain                                                            #
#-----------------------------------------------------------------------------#
class SSHDomain (LocalDomain):
    def __init__ (self, core, host, port = None, identity_file = None, ssh_exec = None, py_exec = None,
        push_main = True, run = None):
        LocalDomain.__init__ (self, SSHChannel (core, host, port = port, identity_file= identity_file,
                ssh_exec = ssh_exec, py_exec = py_exec), push_main = push_main, run = run)

#-----------------------------------------------------------------------------#
# Remote SSH Domain                                                           #
#-----------------------------------------------------------------------------#
class SSHRemoteDomain (RemoteDomain):
    def __init__ (self, core):
        # create channel
        channel = FileChannel (core)
        channel.in_file = core.AsyncFileCreate (0, closefd = True)
        channel.out_file = core.AsyncFileCreate (1, closefd = True)

        RemoteDomain.__init__ (self, channel, run = True)

# vim: nu ft=python columns=120 :
