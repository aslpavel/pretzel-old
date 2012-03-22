# -*- coding: utf-8 -*-
import sys
import os
import socket
import errno
import binascii

from .file import *
from ..domains.pair import *
from ..bootstrap import *
from ..utils.worker import *
from .. import __name__ as remoting_name
from ...async import *
from ...event import *

__all__ = ('DaemonChannel',)
#------------------------------------------------------------------------------#
# Daemon Channel                                                               #
#------------------------------------------------------------------------------#
class DaemonChannel (FileChannel):
    def __init__ (self, core, path):
        FileChannel.__init__ (self, core)

        self.path = path
        self.OnCreate = Event ()

    #--------------------------------------------------------------------------#
    # Run                                                                      #
    #--------------------------------------------------------------------------#
    @Async
    def Run (self):
        try:
            # try to connect
            yield self.connect ()
            return
        except socket.error as error:
            if error.errno != errno.ECONNREFUSED:
                raise

        # create child
        payload_in, payload_out = os.pipe ()
        ready_in, ready_out = os.pipe ()
        if os.fork ():
            os.close (payload_in)
            os.close (ready_out)
        else:
            try:
                # new session
                os.setsid ()

                # redirect payload into standard input
                os.close (payload_out)
                os.dup2 (payload_in, 0)

                # exec
                os.execvp (sys.executable, [sys.executable, '-'])
            finally:
                sys.exit (1)

        # send payload
        try:
            path_base64 = binascii.b2a_base64 (self.path.encode ('utf-8')).strip ().decode ('utf-8')
            os.write (payload_out, payload.format (bootstrap = FullBootstrap (), remoting_name = remoting_name,
                path = path_base64, ready_out = ready_out).encode ())
        finally:
            os.close (payload_out)

        # wait for daemon
        try: os.read (ready_in, 1)
        finally:
            os.close (ready_in)

        # connect
        yield self.connect ()
        self.OnCreate ()

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def connect (self):
        sock = self.core.AsyncSocketCreate (socket.socket (socket.AF_UNIX))
        try:
            yield sock.Connect (self.path)

            self.in_file = self.out_file = sock
            yield FileChannel.Run (self)

        except Exception:
            sock.Dispose ()
            raise

#------------------------------------------------------------------------------#
# Daemon                                                                       #
#------------------------------------------------------------------------------#
class Daemon (Worker):
    def __init__ (self, core, path, ready, backlog = 10):
        Worker.__init__ (self, self.daemon_main, 'daemon worker')

        self.core = core
        self.path = path
        self.ready = ready
        self.backlog = backlog
        self.domains = set ()

    #--------------------------------------------------------------------------#
    # Properties                                                               #
    #--------------------------------------------------------------------------#
    @property
    def Domains (self):
        return self.domains

    #--------------------------------------------------------------------------#
    # Main                                                                     #
    #--------------------------------------------------------------------------#
    @Async
    def daemon_main (self):
        sock = self.core.AsyncSocketCreate (socket.socket (socket.AF_UNIX))
        sock.Bind (self.path)
        sock.Listen (self.backlog)
        os.close (self.ready) # signal client to connect

        def domain_remover (domain):
            """remove domain from domains set"""
            return lambda future: self.domains.remove (domain)

        # accept loop
        while True:
            client, addr = yield sock.Accept ()

            # create new domain
            channel = FileChannel (self.core)
            channel.in_file = channel.out_file = sock
            domain = RemoteDomain (channel, run = True)

            # keep domain set
            self.domains.add (domain)
            domain.Task.Continue (domain_remover (domain))

#------------------------------------------------------------------------------#
# Payload Pattern                                                              #
#------------------------------------------------------------------------------#
payload = r"""# -*- coding: utf-8 -*-
{bootstrap}
import io, os, sys, socket, binascii
from importlib import import_module

import_module ("{remoting_name}")
async = import_module ("..async", "{remoting_name}")
daemon = import_module (".channels.daemon", "{remoting_name}")

if __name__ == "__main__":
    with async.Core () as core:
        daemon.Daemon (core, binascii.a2b_base64 (b"{path}"), {ready_out}).Run ()
"""
    
# vim: nu ft=python columns=120 :
