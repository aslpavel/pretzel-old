# -*- coding: utf-8 -*-
import sys
import os

from ..bootstrap import *
from .file import *
from .. import __name__ as remoting_name
from ...async import *

__all__ = ('SSHChannel',)
#------------------------------------------------------------------------------#
# SSH Channel                                                                  #
#------------------------------------------------------------------------------#
class SSHChannel (FileChannel):
    def __init__ (self, core, host, port = None, identity_file = None, ssh_exec = None, py_exec = None):
        self.host = host
        self.identity_file = identity_file

        # executable
        if py_exec is None:
            py_exec = sys.executable
        if ssh_exec is None:
            ssh_exec = 'ssh'

        # ssh command
        self.command = [ssh_exec, host, py_exec]
        if identity_file is not None:
            self.command.extend (('-i', identity_file))
        if port is not None:
            self.command.extend (('-p', port))
        self.command.extend (('-c', '\'{0}\''.format (payload.format (
            bootstrap = FullBootstrap (), remoting_name = remoting_name))))

        FileChannel.__init__ (self, core)

    #--------------------------------------------------------------------------#
    # Run                                                                      #
    #--------------------------------------------------------------------------#
    @Async
    def Run (self):
        # create ssh connection
        lr, rw = os.pipe ()
        rr, lw = os.pipe ()

        # create child
        self.pid = os.fork ()
        if self.pid:
            os.close (rr), os.close (rw)
        else:
            # child
            os.close (lr), os.close (lw)
            sys.stdin.close ()
            os.dup2 (rr, 0)
            sys.stdout.close ()
            os.dup2 (rw, 1)
            os.execvp (self.command [0], self.command)

        # set descriptors
        self.in_fd, self.out_fd = lr, lw
        self.closefd = True

        yield FileChannel.Run (self)

        # wait for child
        self.OnStop += lambda: os.waitpid (self.pid, 0)

#------------------------------------------------------------------------------#
# Payload Pattern                                                              #
#------------------------------------------------------------------------------#
payload = r"""# -*- coding: utf-8 -*-
{bootstrap}

import io, os, sys
from importlib import import_module

def main ():
    remoting_name = "{remoting_name}"
    remoting = import_module (remoting_name)
    async = import_module ("..async", remoting_name)
    domains = import_module (".domains.ssh", remoting_name)

    with async.Core () as core:
        domains.SSHRemoteDomain (core)

if __name__ == "__main__":
    sys.stdout = sys.stderr
    main ()
"""
    
# vim: nu ft=python columns=120 :
