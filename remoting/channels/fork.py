# -*- coding: utf-8 -*-
import sys
import os
import traceback

from .file import *
from .. import __name__ as remoting_name
from ...async import *
from ...bootstrap import *

__all__ = ('ForkChannel',)
#------------------------------------------------------------------------------#
# ForkChannel                                                                  #
#------------------------------------------------------------------------------#
class ForkChannel (FileChannel):
    def __init__ (self, command = None, core = None):
        FileChannel.__init__ (self, core = core)
        self.command = [sys.executable, '-'] if command is None else command

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def connect (self):
        # create pipes
        lr, rw = os.pipe ()
        rr, lw = os.pipe ()
        payload_in, payload_out = os.pipe ()

        # create child
        self.pid = os.fork ()
        if self.pid:
            # parent
            os.close (rr)
            os.close (rw)
            os.close (payload_in)

        else:
            # child
            try:
                os.close (lr)
                os.close (lw)
                os.close (payload_out)

                os.dup2 (payload_in, 0)
                os.close (payload_in)

                os.execvp (self.command [0], self.command)

            except Exception: traceback.print_exc ()
            finally:
                sys.exit (1)

        # set files
        self.FilesSet (AsyncFile (lr, core = self.core), AsyncFile (lw, core = self.core))

        # send payload
        try:
            os.write (payload_out, payload.format (bootstrap = BootstrapModules (),
                remoting_name = remoting_name, rr = rr, rw = rw).encode ())
        finally:
            os.close (payload_out)

        yield FileChannel.connect (self)

    def disconnect (self):
        FileChannel.disconnect (self)

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
        domain = domains.ForkRemoteDomain ({rr}, {rw}, core = core)
        domain.channel.OnDisconnect += core.Stop
        domain.Connect ().Traceback ("remote::connect")

if __name__ == "__main__":
    Main ()
"""

# vim: nu ft=python columns=120 :
