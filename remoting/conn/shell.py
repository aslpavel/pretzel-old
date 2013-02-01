# -*- coding: utf-8 -*-
import sys
import struct

from .stream import StreamConnection
from ..importer import ImporterInstall
from ...bootstrap import Tomb
from ...async import Async, Core, BufferedFile
from ...process import Process, PIPE

__all__ = ('ShellConnection',)
#------------------------------------------------------------------------------#
# Shell Connection                                                             #
#------------------------------------------------------------------------------#
class ShellConnection (StreamConnection):
    """Process connection

    Connection with process over standard output and input, error stream
    is untouched.
    """
    def __init__ (self, command = None, escape = None, py_exec = None,
        buffer_size = None, hub = None, core = None):

        StreamConnection.__init__ (self, hub, core)

        self.buffer_size = buffer_size
        self.py_exec = py_exec or sys.executable
        self.command = command or []
        self.command.extend ((self.py_exec, '-c',
            '\'{}\''.format (ShellConnectionTrampoline) if escape else ShellConnectionTrampoline))

        self.process = None

    #--------------------------------------------------------------------------#
    # Process                                                                  #
    #--------------------------------------------------------------------------#
    @property
    def Process (self):
        return self.process

    #--------------------------------------------------------------------------#
    # Protected                                                                #
    #--------------------------------------------------------------------------#
    @Async
    def connect (self, target):
        """Fork connect implementation

        Target is pickle-able and call-able which will be called upon successful
        connection with connection this as its only argument.
        """
        self.process = self.dispose.Add (Process (self.command, stdin = PIPE, stdout = PIPE,
            buffer_size = self.buffer_size, core = self.core))

        # send payload
        payload = Tomb.FromModules ().Bootstrap (
            ShellConnectionInit, self.buffer_size).encode ('utf-8')
        yield self.process.Stdin.Write (struct.pack ('>I', len (payload)))
        yield self.process.Stdin.Write (payload)
        yield self.process.Stdin.Flush ()

        yield StreamConnection.connect (self, (self.process.Stdout, self.process.Stdin))

        # install importer
        self.dispose.Add ((yield ImporterInstall (self)))

#------------------------------------------------------------------------------#
# Connection Initializer                                                       #
#------------------------------------------------------------------------------#
def ShellConnectionInit (buffer_size):
    """Shell connection initialization function
    """
    with Core.Instance () as core:
        # initialize connection
        conn = StreamConnection (core = core)
        conn.dispose.Add (core)

        # connect
        in_stream  = BufferedFile (0, buffer_size = buffer_size, core = core)
        in_stream.CloseOnExec (True)
        out_stream = BufferedFile (1, buffer_size = buffer_size, core = core)
        out_stream.CloseOnExec (True)
        conn.Connect ((in_stream, out_stream)).Traceback ('remote connect')

        # execute core
        if not core.Disposed:
            core ()

#------------------------------------------------------------------------------#
# Trampoline                                                                   #
#------------------------------------------------------------------------------#
ShellConnectionTrampoline = """
# load and execute payload
import io, struct
with io.open (0, "rb", buffering = 0, closefd = False) as stream:
    size = struct.unpack (">I", stream.read (struct.calcsize (">I"))) [0]
    data = io.BytesIO ()
    while size > data.tell ():
        chunk = stream.read (size - data.tell ())
        if not chunk:
            raise ValueError ("Payload is incomplete")
        data.write (chunk)
exec (data.getvalue ().decode ("utf-8"))
"""
# vim: nu ft=python columns=120 :
