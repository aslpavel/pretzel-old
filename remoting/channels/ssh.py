# -*- coding: utf-8 -*-
import os
import sys
import struct
import traceback

from .file        import FileChannel
from .pipe        import Pipe
from ...async     import Async
from ...bootstrap import Tomb, BootstrapBootstrap
from ..           import __name__ as remoting_name

__all__ = ('SSHChannel',)
#------------------------------------------------------------------------------#
# SSH Channel                                                                  #
#------------------------------------------------------------------------------#
class SSHChannel (FileChannel):
    def __init__ (self, host, port = None, identity_file = None, ssh_exec = None, py_exec = None,
            buffer_size = None, core = None):

        self.host          = host
        self.port          = port
        self.identity_file = identity_file
        self.ssh_exec      = 'ssh' if ssh_exec is None else ssh_exec
        self.py_exec       = sys.executable if py_exec is None else py_exec
        self.buffer_size   = buffer_size

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
            bootstrap     = BootstrapBootstrap ('_bootstrap'),
            remoting_name = remoting_name,
            buffer_size   = buffer_size)))

        self.pid = None

        # base .ctor
        FileChannel.__init__ (self, core = core)

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def connect (self):
        in_pipe  = Pipe (self.buffer_size, self.core)
        out_pipe = Pipe (self.buffer_size, self.core)

        # create child
        self.pid = os.fork ()
        if not self.pid:
            try:
                sys.stdin.close ()
                in_pipe.DetachRead (0)   # -> incoming

                sys.stdout.close ()
                out_pipe.DetachWrite (1) # <- outgoing

                os.execvp (self.command [0], self.command)

            except Exception: traceback.print_exc ()
            finally:
                sys.exit (1)

        # set files
        in_stream = in_pipe.DetachWriteAsync ()
        self.FilesSet (out_pipe.DetachReadAsync (), in_stream)

        # send payload
        payload = Tomb.FromModules ().ToBytes ()
        in_stream.WriteBuffer (struct.pack ('!L', len (payload)))
        in_stream.WriteBuffer (payload)
        yield in_stream.Flush ()

        # parent connect
        yield FileChannel.connect (self)

    @Async
    def disconnect (self):
        yield FileChannel.disconnect (self)

        pid, self.pid = self.pid, None
        if pid is not None:
            os.waitpid (pid, 0)

#------------------------------------------------------------------------------#
# Payload Pattern                                                              #
#------------------------------------------------------------------------------#
payload_template = r"""'# -*- coding: utf-8 -*-
{bootstrap}

import io, struct
#------------------------------------------------------------------------------#
# Pretzel                                                                      #
#------------------------------------------------------------------------------#
with io.open (0, "rb", buffering = 0, closefd = False) as stream:
    size = struct.unpack ("!L", stream.read (struct.calcsize ("!L"))) [0]
    data = io.BytesIO ()
    while size > data.tell ():
        chunk = stream.read (size - data.tell ())
        if not chunk:
            raise ValueError ("Payload is incomplete")
        data.write (chunk)
    _bootstrap.Tomb.FromBytes (data.getvalue ()).Install ()

#------------------------------------------------------------------------------#
# Main                                                                         #
#------------------------------------------------------------------------------#
import sys
from importlib import import_module
def Main ():
    import_module ("{remoting_name}")
    async    = import_module ("..async", "{remoting_name}")
    domains  = import_module (".domains.ssh", "{remoting_name}")

    with async.Core.Instance () as core:
        domain = domains.SSHRemoteDomain ({buffer_size}, core)
        domain.channel.OnDisconnect += core.Dispose
        domain.Connect ().Traceback ("remote::connect")
        core ()

if __name__ == "__main__":
    sys.stdout = sys.stderr
    Main ()
'"""

# vim: nu ft=python columns=120 :
