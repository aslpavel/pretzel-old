# -*- coding: utf-8 -*-
import io
import os
import sys
import pickle
import signal

from .disposable import Disposable, CompositeDisposable
from .async import Async, AsyncReturn, Future, SucceededFuture, Pipe, BrokenPipeError

__all__ = ('Process', 'ProcessCall', 'ProcessError', 'PIPE', 'DEVNULL', 'STDIN', 'STDOUT', 'STDERR',)
#------------------------------------------------------------------------------#
# Constants                                                                    #
#------------------------------------------------------------------------------#
PIPE    = -1
DEVNULL = -2
STDIN   = sys.stdin.fileno ()
STDOUT  = sys.stdout.fileno ()
STDERR  = sys.stderr.fileno ()

#------------------------------------------------------------------------------#
# Process                                                                      #
#------------------------------------------------------------------------------#
class ProcessError (Exception): pass
class Process (object):
    """Create child process
    """
    def __init__ (self, command, stdin = None, stdout = None, stderr = None, preexec = None,
            shell = None, environ = None, check = None, buffer_size = None, core = None):

        # vars
        self.command     = ['/bin/sh', '-c', command] if shell else command
        self.environ     = environ
        self.check       = check is None or check

        # dispose
        self.dispose = CompositeDisposable ()

        # state
        self.pid    = None
        self.status = None

        #----------------------------------------------------------------------#
        # Pipes                                                                #
        #----------------------------------------------------------------------#
        stdin_fd = self.to_fd (stdin, STDIN)
        self.stdin_pipe = self.dispose.Add (
            Pipe (None if stdin_fd is None else (stdin_fd, None), buffer_size, core))

        stdout_fd = self.to_fd (stdout, STDOUT)
        self.stdout_pipe = self.dispose.Add (
            Pipe (None if stdout_fd is None else (None, stdout_fd), buffer_size, core))

        stderr_fd = self.to_fd (stderr, STDERR)
        self.stderr_pipe = self.dispose.Add (
            Pipe (None if stderr_fd is None else (None, stderr_fd), buffer_size ,core))

        status_pipe  = self.dispose.Add (Pipe (core = core))

        #----------------------------------------------------------------------#
        # Fork                                                                 #
        #----------------------------------------------------------------------#
        self.pid = os.fork ()
        if self.pid:
            # dispose remote streams
            self.stdin_pipe.Read.Dispose ()
            self.stdout_pipe.Write.Dispose ()
            self.stderr_pipe.Write.Dispose ()
            status_pipe.Write.Dispose ()

            # close on exec
            for stream in (self.stdin_pipe.Write, self.stdout_pipe.Read,
                self.stderr_pipe.Read, status_pipe.Read):
                    if stream is not None:
                        stream.CloseOnExec (True)

            # status
            self.status = self.status_main (status_pipe.Read)

        else:
            try:
                # status
                status_pipe.Write.Blocking (True)
                status_fd = status_pipe.Write.Detach ().Result ()
                status_pipe.Dispose ()

                # standard input
                self.stdin_pipe.Read.Blocking (True)
                if self.stdin_pipe.Read.Fd != 0:
                    os.dup2 (self.stdin_pipe.Read.Fd, 0)
                    self.stdin_pipe.Dispose ()

                # standard output
                self.stdout_pipe.Write.Blocking (True)
                if self.stdout_pipe.Write.Fd != 1:
                    os.dup2 (self.stdout_pipe.Write.Fd, 1)
                    self.stdin_pipe.Dispose ()

                # standard error
                self.stderr_pipe.Write.Blocking (True)
                if self.stderr_pipe.Write.Fd != 2:
                    os.dup2 (self.stderr_pipe.Write.Fd, 2)
                    self.stderr_pipe.Dispose ()

                # pre-exec hook
                if preexec is not None:
                    preexec ()

                # exec
                os.execvpe (self.command [0], self.command, self.environ or os.environ)

            except Exception as error:
                with io.open (status_fd, 'wb') as error_stream:
                    pickle.dump (error, error_stream)

            finally:
                getattr (os, '_exit', lambda _: os.kill (os.getpid (), signal.SIGKILL)) (255)

    #--------------------------------------------------------------------------#
    # Properties                                                               #
    #--------------------------------------------------------------------------#
    @property
    def Stdin (self):
        """Standard input asynchronous stream
        """
        return self.stdin_pipe.Write

    @property
    def Stdout (self):
        """Standard output asynchronous stream
        """
        return self.stdout_pipe.Read

    @property
    def Stderr (self):
        """Standard error asynchronous stream
        """
        return self.stderr_pipe.Read

    @property
    def Status (self):
        """Future object for return code of the process
        """
        return self.status

    @property
    def Pid (self):
        """Pid of the process
        """
        return self.pid

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def status_main (self, error_stream):
        """Status coroutine main
        """
        error_dump = b''
        try:
            error_dump = yield error_stream.ReadUntilEof ()

        except BrokenPipeError: pass
        finally:
            error_stream.Dispose ()

            pid, status = os.waitpid (self.pid, os.WNOHANG)
            if pid != self.pid:
                os.kill (self.pid, signal.SIGTERM)
                pid, status = os.waitpid (self.pid, 0)

            if error_dump:
                raise pickle.loads (error_dump)
            elif self.check and status:
                raise ProcessError ('Command \'{}\' returned non-zero exit status {}'
                    .format (self.command, status))

        AsyncReturn (status)

    def to_fd (self, file, default):
        """Convert file object to file descriptor
        """
        if file is None:
            return default

        elif file == PIPE:
            return

        elif file == DEVNULL:
            if not hasattr (self, 'null_fd'):
                self.null_fd  = os.open (os.devnull, os.O_RDWR)
                self.dispose += Disposable (lambda: os.close (self.null_fd))
            return self.null_fd

        return file if isinstance (file, int) else file.fileno ()

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        """Terminate process and dispose associated resources
        """
        self.dispose.Dispose ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

#------------------------------------------------------------------------------#
# Call Process                                                                 #
#------------------------------------------------------------------------------#
def ProcessCall (command, input = None, stdin = None, stdout = None, stderr = None,
        shell = None, environ = None, check = None, buffer_size = None, core = None, cancel = None):
    """Asynchronously run command

    Asynchronously returns standard output, standard error and return code tuple.
    """

    # vars
    if input is not None and stdin is not None:
        raise ProcessError ('Input cannot be consumed when stdin is set')

    stdin  = PIPE if input else stdin
    stdout = PIPE if stdout is None else stdout
    stderr = PIPE if stderr is None else stderr

    # process helper
    @Async
    def process ():
        with Process (command, stdin, stdout, stderr, shell, environ, check, buffer_size, core) as proc:
            # input
            if input:
                proc.Stdin.Write (input)
                proc.Stdin.Flush ().Continue (lambda *_: proc.Stdin.Dispose ())

            # output
            out = proc.Stdout.ReadUntilEof () if proc.Stdout else SucceededFuture (None)
            err = proc.Stderr.ReadUntilEof () if proc.Stderr else SucceededFuture (None)
            yield Future.WhenAll ((out, err))

            AsyncReturn ((out.Result (), err.Result (), (yield proc.Status)))

    return process ()

# vim: nu ft=python columns=120 :
