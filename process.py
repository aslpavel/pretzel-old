# -*- coding: utf-8 -*-
import io
import os
import sys
import signal

from .async import (Async, AsyncReturn, AsyncFile, Future, ScopeFuture, Core,
                    BrokenPipeError)
from .disposable import Disposable, CompositeDisposable

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
    def __init__ (self, command, stdin = None, stdout = None, stderr = None,
            shell = None, environ = None, check = None, buffer_size = None, core = None):

        # vars
        self.command     = ['/bin/sh', '-c', command] if shell else command
        self.environ     = environ
        self.check       = check is None or check
        self.buffer_size = buffer_size or default_buffer_size
        self.core        = core or Core.Instance ()

        # dispose
        self.dispose = CompositeDisposable ()

        # state
        self.pid    = None
        self.result = None

        self.stdin  = None
        self.stdout = None
        self.stderr = None

        #----------------------------------------------------------------------#
        # Pipes                                                                #
        #----------------------------------------------------------------------#
        stdin       = self.to_fd (stdin, STDIN)
        stdin_pipe  = Pipe (None if stdin is None else (stdin, None), self)

        stdout      = self.to_fd (stdout, STDOUT)
        stdout_pipe = Pipe (None if stdout is None else (None, stdout), self)

        stderr      = self.to_fd (stderr, STDERR)
        stderr_pipe = Pipe (None if stderr is None else (None, stderr), self)

        alive_pipe  = Pipe (None, self)

        #----------------------------------------------------------------------#
        # Fork                                                                 #
        #----------------------------------------------------------------------#
        self.pid = os.fork ()
        if self.pid:
            # pipes
            self.stdin  = stdin_pipe.DetachWriteAsync ()
            self.stdout = stdout_pipe.DetachReadAsync ()
            self.stderr = stderr_pipe.DetachReadAsync ()

            # result
            self.result = self.result_main (alive_pipe.DetachReadAsync ())

        else:
            try:
                # pipes
                stdin_pipe.DetachRead (0)
                stdout_pipe.DetachWrite (1)
                stderr_pipe.DetachWrite (2)
                alive_pipe.DetachWrite ()

                # exec
                if self.environ is None:
                    os.execvp (self.command [0], self.command)
                else:
                    os.execvpe (self.command [0], self.command, self.environ)

            finally:
                exit = getattr (os, '_exit', None)
                if exit: exit (255)
                else:
                    os.kill (os.getpid (), signal.SIGKILL)

    #--------------------------------------------------------------------------#
    # Properties                                                               #
    #--------------------------------------------------------------------------#
    @property
    def Stdin (self):
        """Standard input asynchronous stream
        """
        return self.stdin

    @property
    def Stdout (self):
        """Standard output asynchronous stream
        """
        return self.stdout

    @property
    def Stderr (self):
        """Standard error asynchronous stream
        """
        return self.stderr

    @property
    def Result (self):
        """Future object for return code of the process
        """
        return self.result

    @property
    def Pid (self):
        """Pid of the process
        """
        return self.pid

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def result_main (self, alive_stream):
        """Result coroutine main
        """
        try:
            with ScopeFuture () as cancel:
                self.dispose += cancel

                yield alive_stream.Read (1, cancel)

        except BrokenPipeError: pass
        except Exception:
            os.kill (self.pid, signal.SIGTERM)
            os.waitpid (self.pid, 0)
            raise

        # result
        result = os.waitpid (self.pid, 0) [1]
        if self.check and result:
            raise ProcessError ('Command \'{}\' returned non-zero exit status {}'.format (self.command, result))

        AsyncReturn (result)

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
# Pipe                                                                         #
#------------------------------------------------------------------------------#
class Pipe (object):
    """Pipe helper type
    """
    def __init__ (self, fds, process):
        self.process = process
        if fds:
            self.piped = False
            self.fds   = fds
        else:
            self.piped = True
            self.fds   = os.pipe ()

        # dispose
        process.dispose += self

    #--------------------------------------------------------------------------#
    # Detach                                                                   #
    #--------------------------------------------------------------------------#
    def DetachRead (self, fd = None):
        """Detach read side
        """
        self.detach (True, fd)

    def DetachReadAsync (self):
        """Detach read side and create asynchronous stream out of it
        """
        return self.detach_async (True)

    def DetachWrite (self, fd = None):
        """Detach write side
        """
        self.detach (False, fd)

    def DetachWriteAsync (self):
        """Detach write side and create asynchronous stream out of it
        """
        return self.detach_async (False)

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    def detach (self, read, fd = None):
        """Detach from the pipe

        Detaches requested side of the pipe, and close the other one. Returns
        detached file descriptor.
        """
        if self.fds is None:
            raise ProcessError ('Pipe has already been detached')

        fds, self.fds = self.fds, None
        to_return, to_close = fds if read else reversed (fds)

        if self.piped and to_close is not None:
            os.close (to_close)

        if fd is None or fd == to_return:
            return to_return
        else:
            os.dup2  (to_return, fd)
            os.close (to_return)
            return fd

    def detach_async (self, read):
        """Detach from the pipe

        Detaches requested side of the pipe, and close the other one. Returns
        asynchronous file stream for detached side.
        """
        fd = self.detach (read)
        if fd is None:
            return

        file  = AsyncFile (fd, buffer_size = self.process.buffer_size,
                           closefd = self.piped, core = self.process.core)
        self.process.dispose += file
        if self.piped:
            file.CloseOnExec (True)

        return file

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        """Dispose pipe
        """
        if self.fds is None:
            return

        fds, self.fds = self.fds, None
        for fd in fds:
            if self.piped and fd is not None:
                os.close (fd)

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
    buffer_size = buffer_size or default_buffer_size

    # read helper
    @Async
    def read (stream):
        if stream is None:
            AsyncReturn (None)

        try:
            data = io.BytesIO ()
            while True:
                data.write ((yield stream.Read (buffer_size, cancel)))
        except BrokenPipeError: pass
        AsyncReturn (data.getvalue ())

    # process helper
    @Async
    def process ():
        with Process (command, stdin, stdout, stderr, shell, environ, check, buffer_size, core) as proc:
            # input
            if input:
                proc.Stdin.Write (input)
                proc.Stdin.Flush ().Continue (lambda *_: proc.Stdin.Dispose ())

            # output
            out = read (proc.Stdout)
            err = read (proc.Stderr)
            yield Future.WhenAll ((out, err))

            AsyncReturn ((out.Result (), err.Result (), (yield proc.Result)))

    return process ()

#------------------------------------------------------------------------------#
# Defaults                                                                     #
#------------------------------------------------------------------------------#
default_buffer_size = 1 << 16

# vim: nu ft=python columns=120 :
