# -*- coding: utf-8 -*-
import sys
import os
import traceback

from .file import *
from .channel import *
from .. import __name__ as remoting_name
from ...async import *
from ...bootstrap import *

__all__ = ('SSHChannel',)
#------------------------------------------------------------------------------#
# SSH Channel                                                                  #
#------------------------------------------------------------------------------#
class SSHChannel (FileChannel):
    def __init__ (self, core, host, port = None, identity_file = None, ssh_exec = None, py_exec = None):
        self.pid           = None
        self.host          = host
        self.port          = port
        self.ssh_exec      = 'ssh' if ssh_exec is None else ssh_exec
        self.py_exec       = sys.executable if py_exec is None else py_exec
        self.identity_file = identity_file

        # ssh command
        self.command = [self.ssh_exec, host, self.py_exec]
        if self.identity_file is not None:
            self.command.extend (('-i', self.identity_file))
        if self.port is not None:
            self.command.extend (('-p', self.port))
        self.command.extend (('-c', '\'{0}\''
            .format (payload.format (bootstrap = BootstrapModules (), remoting_name = remoting_name))))

        FileChannel.__init__ (self, core)

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def connect (self):
        # create ssh connection
        lr, rw = os.pipe ()
        rr, lw = os.pipe ()

        # create child
        self.pid = os.fork ()
        if self.pid:
            # parent
            os.close (rr)
            os.close (rw)

        else:
            # child
            try:
                os.close (lr)
                os.close (lw)

                sys.stdin.close ()
                os.dup2 (rr, 0)
                os.close (rr)

                sys.stdout.close ()
                os.dup2 (rw, 1)
                os.close (rw)

                os.execvp (self.command [0], self.command)

            except Exception: traceback.print_exc ()
            finally:
                sys.exit (1)

        # set files
        self.FilesSet (
            self.core.AsyncFileCreate (lr, closefd = True),
            self.core.AsyncFileCreate (lw, closefd = True))

        yield FileChannel.connect (self)

    def disconnect (self):
        FileChannel.disconnect (self)

        pid, self.pid = self.pid, None
        if pid is not None:
            os.waitpid (pid, 0)

#------------------------------------------------------------------------------#
# Payload Pattern                                                              #
#------------------------------------------------------------------------------#
payload = r"""# -*- coding: utf-8 -*-
{bootstrap}

import sys
from importlib import import_module

def Main ():
    import_module ("{remoting_name}")
    async    = import_module ("..async", "{remoting_name}")
    domains  = import_module (".domains.ssh", "{remoting_name}")

    with async.Core () as core:
        domain = domains.SSHRemoteDomain (core)
        domain.channel.OnDisconnect += core.Stop
        domain.Connect ().Traceback ("remote::connect")

if __name__ == "__main__":
    sys.stdout = sys.stderr
    Main ()
"""
    
# vim: nu ft=python columns=120 :
