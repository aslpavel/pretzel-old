# -*- coding: utf-8 -*-
import sys
import os
import traceback

from .file        import FileChannel
from .pipe        import Pipe
from ...async     import Async
from ...bootstrap import Tomb
from ..           import __name__ as remoting_name

__all__ = ('ForkChannel',)
#------------------------------------------------------------------------------#
# ForkChannel                                                                  #
#------------------------------------------------------------------------------#
class ForkChannel (FileChannel):
    def __init__ (self, command = None, buffer_size = None, core = None):
        FileChannel.__init__ (self, core)

        self.buffer_size = buffer_size
        self.command = [sys.executable, '-'] if command is None else command

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def connect (self):
        in_pipe   = Pipe (self.buffer_size, self.core)
        out_pipe  = Pipe (self.buffer_size, self.core)
        load_pipe = Pipe (self.buffer_size, self.core)

        # create child
        self.pid = os.fork ()
        if not self.pid:
            try:
                in_pipe.DetachRead ()    # <- incoming
                out_pipe.DetachWrite ()  # -> outgoing
                load_pipe.DetachRead (0) # <- stdin

                os.execvp (self.command [0], self.command)

            except Exception: traceback.print_exc ()
            finally:
                sys.exit (1)

        # set files
        in_fd, out_fd = in_pipe.Read, out_pipe.Write
        self.FilesSet (out_pipe.DetachReadAsync (), in_pipe.DetachWriteAsync ())

        # send payload
        with load_pipe.DetachWriteAsync () as load_stream:
            load_stream.WriteBuffer (payload.format (
                bootstrap     = Tomb.FromModules ().Bootstrap (),
                remoting_name = remoting_name,
                in_fd         = in_fd,
                out_fd        = out_fd,
                buffer_size   = self.buffer_size).encode ())
            yield load_stream.Flush ()

        yield FileChannel.connect (self)

    @Async
    def disconnect (self):
        yield FileChannel.disconnect (self)

        pid, self.pid = self.pid, None
        if pid is not None:
            os.waitpid (pid, 0)

#-----------------------------------------------------------------------------#
# Payload                                                                     #
#-----------------------------------------------------------------------------#
payload = r"""# -*- coding: utf-8 -*-
{bootstrap}
from importlib import import_module

#------------------------------------------------------------------------------#
# Main                                                                         #
#------------------------------------------------------------------------------#
def Main ():
    import_module ("{remoting_name}")
    async   = import_module ("..async", "{remoting_name}")
    domains = import_module (".domains.fork", "{remoting_name}")

    with async.Core.Instance () as core:
        domain = domains.ForkRemoteDomain ({in_fd}, {out_fd}, {buffer_size}, core)
        domain.channel.OnDisconnect += core.Dispose
        domain.Connect ().Traceback ("remote::connect")
        core ()

if __name__ == "__main__":
    Main ()
"""

# vim: nu ft=python columns=120 :
