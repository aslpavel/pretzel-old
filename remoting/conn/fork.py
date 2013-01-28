# -*- coding: utf-8 -*-
import sys

from .stream import StreamConnection
from ..importer import ImporterInstall
from ...bootstrap import Tomb
from ...async import Async, Core, Pipe, BufferedFile
from ...process import Process, PIPE

__all__ = ('ForkConnection',)
#------------------------------------------------------------------------------#
# Fork Connection                                                              #
#------------------------------------------------------------------------------#
class ForkConnection (StreamConnection):
    """Fork connection

    Connection with forked and exec-ed process. Target function must be pickle-able.
    """
    def __init__ (self, command = None, buffer_size = None, hub = None, core = None):
        StreamConnection.__init__ (self, hub, core)

        self.buffer_size = buffer_size
        self.command = [sys.executable, '-'] if command is None else command
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
        # pipes
        in_pipe = self.dispose.Add (Pipe (buffer_size = self.buffer_size, core = self.core))
        out_pipe = self.dispose.Add (Pipe (buffer_size = self.buffer_size, core = self.core))

        # process
        def preexec ():
            in_pipe.DetachReader ()
            out_pipe.DetachWriter ()

        self.process = self.dispose.Add (Process (self.command, stdin = PIPE,
            preexec = preexec, shell = False, buffer_size = self.buffer_size, core = self.core))

        # close remote side of pipes
        in_fd  = in_pipe.Reader.Fd
        yield in_pipe.Reader.Dispose ()
        out_fd = out_pipe.Writer.Fd
        yield out_pipe.Writer.Dispose ()

        # send payload
        yield self.process.Stdin.Write (Tomb.FromModules ()
            .Bootstrap (ForkConnectionInit, in_fd, out_fd, self.buffer_size).encode ())
        yield self.process.Stdin.Dispose ()

        out_pipe.Reader.CloseOnExec (True)
        in_pipe.Writer.CloseOnExec (True)
        yield StreamConnection.connect (self, (out_pipe.Reader, in_pipe.Writer))

        # install importer
        self.dispose.Add ((yield ImporterInstall (self)))

    def disconnect (self):
        """Fork disconnect implementation
        """
        self.dispose.Dispose ()

#------------------------------------------------------------------------------#
# Connection Initializer                                                       #
#------------------------------------------------------------------------------#
def ForkConnectionInit (in_fd, out_fd, buffer_size):
    """Fork connection initialization function
    """
    with Core.Instance () as core:
        # initialize connection
        conn = StreamConnection (core = core)
        conn.dispose.Add (core)

        # connect
        in_stream  = BufferedFile (in_fd, buffer_size = buffer_size, core = core)
        in_stream.CloseOnExec (True)
        out_stream = BufferedFile (out_fd, buffer_size = buffer_size, core = core)
        out_stream.CloseOnExec (True)
        conn.Connect ((in_stream, out_stream)).Traceback ('remote connect')

        # execute core
        if not core.Disposed:
            core ()

# vim: nu ft=python columns=120 :
