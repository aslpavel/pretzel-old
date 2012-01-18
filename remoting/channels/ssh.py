# -*- coding: utf-8 -*-
import sys
import os

from ..bootstrap import *
from .file import *
from .. import __name__ as remoting_name

__all__ = ('SSHChannel',)

#-----------------------------------------------------------------------------#
# SSH Channel                                                                 #
#-----------------------------------------------------------------------------#
class SSHChannel (FileChannel):
    def __init__ (self, core, host, port = None, identity_file = None,
            ssh_exec = None, py_exec = None):
        self.host = host
        self.identity_file = identity_file

        if py_exec is None:
            py_exec = sys.executable
        if ssh_exec is None:
            ssh_exec = 'ssh'

        # create ssh command
        command = [ssh_exec, host, py_exec]
        if identity_file is not None:
            command.extend (('-i', identity_file))
        if port is not None:
            command.extend (('-p', port))
        command.extend (('-c', '\'{0}\''.format (payload.format (
            bootstrap = FullBootstrap (), remoting_name = remoting_name))))

        # create ssh connection
        lr, rw = os.pipe ()
        rr, lw = os.pipe ()
        if os.fork ():
            # parrent process
            os.close (rr), os.close (rw)
        else:
            # child
            os.close (lr), os.close (lw)
            sys.stdin.close ()
            os.dup2 (rr, 0)
            sys.stdout.close ()
            os.dup2 (rw, 1)
            os.execvp (ssh_exec, command)
            
        FileChannel.__init__ (self, core, lr, lw) 

        # close descriptors if connection has been disposed
        def on_dispose ():
            try:
                os.close (lr)
                os.close (lw)
            except OSError:
                pass
        self.OnDispose += on_dispose

#-----------------------------------------------------------------------------#
# Payload Pattern                                                             #
#-----------------------------------------------------------------------------#
payload = r"""# -*- coding: utf-8 -*-
{bootstrap}

import io, os
from importlib import import_module

def main ():
    remoting_name = "{remoting_name}"

    remoting = import_module (remoting_name)
    channels = import_module (".channels", remoting_name)
    async = import_module (".async", remoting_name)

    in_fd, out_fd = 0, 1
    with async.Core () as core:
        channel = channels.FileChannel (core, in_fd, out_fd)

        # TODO: Create domain
        import time
        @async.DummyAsync
        def now (msg):
            return msg.Result (time = time.time ())
        channel.BindPort (100, now) 

        channel.Start ()

if __name__ == "__main__":
    sys.stdout = sys.stderr
    main ()
"""
    
# vim: nu ft=python columns=120 :
