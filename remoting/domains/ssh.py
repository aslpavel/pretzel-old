# -*- coding: utf-8 -*-
from .default import LocalDomain, RemoteDomain

from ..channels.ssh  import SSHChannel
from ..channels.file import FileChannel
from ...async.core   import AsyncFile

__all__ = ('SSHDomain', )
#-----------------------------------------------------------------------------#
# Local SSH Domain                                                            #
#-----------------------------------------------------------------------------#
class SSHDomain (LocalDomain):
    def __init__ (self, host, port = None, identity_file = None, ssh_exec = None, py_exec = None,
            push_main = None, buffer_size = None, core = None,):

        channel = SSHChannel (host, port, identity_file, ssh_exec, py_exec, buffer_size, core)
        LocalDomain.__init__ (self, channel, push_main)

#-----------------------------------------------------------------------------#
# Remote SSH Domain                                                           #
#-----------------------------------------------------------------------------#
class SSHRemoteDomain (RemoteDomain):
    def __init__ (self, buffer_size, core):
        channel = FileChannel (core)
        channel.FilesSet (
            AsyncFile (0, buffer_size = buffer_size, core = channel.core),
            AsyncFile (1, buffer_size = buffer_size, core = channel.core))

        RemoteDomain.__init__ (self, channel)

# vim: nu ft=python columns=120 :
