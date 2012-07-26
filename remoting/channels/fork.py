# -*- coding: utf-8 -*-
import sys
import os
import traceback

from .file import *
from .channel import *
from .. import __name__ as remoting_name
from ...async import *
from ...bootstrap import *

__all__ = ('ForkChannel',)
#-----------------------------------------------------------------------------#
# Fork Channel                                                                #
#-----------------------------------------------------------------------------#
class ForkChannel (FileChannel):
    def __init__ (self, core, command = None):
        self.command = [sys.executable, '-'] if command is None else command
        FileChannel.__init__ (self, core)

    #--------------------------------------------------------------------------#
    # Run Implementation                                                       #
    #--------------------------------------------------------------------------#
    @Async
    def run (self):
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
            except Exception:
                traceback.print_exc ()
            finally:
                sys.exit (1)

        # set files
        self.in_file = self.core.AsyncFileCreate (lr, closefd = True)
        self.in_file.CloseOnExec (True)

        self.out_file = self.core.AsyncFileCreate (lw, closefd = True)
        self.out_file.CloseOnExec (True)

        # send payload
        try:
            os.write (payload_out, payload.format (bootstrap = BootstrapModule (),
                remoting_name = remoting_name, rr = rr, rw =rw).encode ())
        finally:
            os.close (payload_out)

        yield FileChannel.run (self)

        # wait for child
        self.OnStop += lambda: os.waitpid (self.pid, 0)

#-----------------------------------------------------------------------------#
# Payload Pattern                                                             #
#-----------------------------------------------------------------------------#
payload = r"""# -*- coding: utf-8 -*-
{bootstrap}

import io, os, sys
from importlib import import_module

def main ():
    remoting_name = "{remoting_name}"
    remoting = import_module (remoting_name)
    async = import_module ("..async", remoting_name)
    domains = import_module (".domains.fork", remoting_name)

    with async.Core () as core:
        domain = domains.ForkRemoteDomain (core, {rr}, {rw})
        domain.Channel.OnStop += core.Stop

if __name__ == "__main__":
    main ()
"""
    
# vim: nu ft=python columns=120 :
