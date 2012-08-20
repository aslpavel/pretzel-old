# -*- coding: utf-8 -*-
import os
import sys
import struct
import traceback

from .file import *
from .. import __name__ as remoting_name
from ...async import *
from ...bootstrap import *

__all__ = ('SSHChannel',)
#------------------------------------------------------------------------------#
# SSH Channel                                                                  #
#------------------------------------------------------------------------------#
class SSHChannel (FileChannel):
    def __init__ (self, host, port = None, identity_file = None, ssh_exec = None, py_exec = None, core = None):
        self.pid           = None
        self.host          = host
        self.port          = port
        self.ssh_exec      = 'ssh' if ssh_exec is None else ssh_exec
        self.py_exec       = sys.executable if py_exec is None else py_exec
        self.identity_file = identity_file

        # ssh command
        self.command = [
            self.ssh_exec,         # command
            '-T',                  # disable pseudo-tty allocation
            '-o', 'BatchMode=yes', # don't ask password
            host,                  # host
            self.py_exec           # python command
        ]
        self.command.extend (('-i', self.identity_file) if self.identity_file else [])
        self.command.extend (('-p', self.port)          if self.port          else [])
        self.command.extend (('-c', payload_template.format (
            bootstrap = BootstrapBootstrap ('_bootstrap'),
            remoting_name = remoting_name)))

        # base .ctor
        FileChannel.__init__ (self, core = core)

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

        # send payload
        tomb    = Tomb ()
        tomb   += sys.modules [(__package__ if __package__ else __name__).split ('.') [0]]
        payload = tomb.Save ()
        os.write (lw, struct.pack ('!L', len (payload)))
        os.write (lw, payload)

        # set files
        self.FilesSet (AsyncFile (lr, core = self.core), AsyncFile (lw, core = self.core))

        yield FileChannel.connect (self)

    def disconnect (self):
        FileChannel.disconnect (self)

        pid, self.pid = self.pid, None
        if pid is not None:
            os.waitpid (pid, 0)

#------------------------------------------------------------------------------#
# Payload Pattern                                                              #
#------------------------------------------------------------------------------#
payload_template = r"""'# -*- coding: utf-8 -*-
{bootstrap}

#------------------------------------------------------------------------------#
# Pretzel                                                                      #
#------------------------------------------------------------------------------#
import io, sys, struct
with io.open (0, "rb", buffering = 0, closefd = False) as stream:
    size = struct.unpack ("!L", stream.read (struct.calcsize ("!L"))) [0]
    data = io.BytesIO ()
    while size > data.tell ():
        chunk = stream.read (size - data.tell ())
        if not chunk:
            raise ValueError ("Payload is incomplete")
        data.write (chunk)
    sys.meta_path.append (_bootstrap.Tomb.Load (data.getvalue ()))

#------------------------------------------------------------------------------#
# Main                                                                         #
#------------------------------------------------------------------------------#
from importlib import import_module
def Main ():
    import_module ("{remoting_name}")
    async    = import_module ("..async", "{remoting_name}")
    domains  = import_module (".domains.ssh", "{remoting_name}")

    with async.Core.Instance () as core:
        domain = domains.SSHRemoteDomain (core)
        domain.channel.OnDisconnect += core.Dispose
        domain.Connect ().Traceback ("remote::connect")

if __name__ == "__main__":
    sys.stdout = sys.stderr
    Main ()
'"""
    
# vim: nu ft=python columns=120 :
