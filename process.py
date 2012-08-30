# -*- coding: utf-8 -*-
import io
import os
import sys
import signal
import traceback

from .async      import Async, AsyncReturn, AsyncFile, Future, ScopeFuture, Core, CoreDisconnectedError
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
        stdin       = self.fd_get (stdin, STDIN)
        stdin_pipe  = Pipe (None if stdin is None else (stdin, None), self)

        stdout      = self.fd_get (stdout, STDOUT)
        stdout_pipe = Pipe (None if stdout is None else (None, stdout), self)

        stderr      = self.fd_get (stderr, STDERR)
        stderr_pipe = Pipe (None if stderr is None else (None, stderr), self)

        alive_pipe  = Pipe (None, self)

        #----------------------------------------------------------------------#
        # Fork                                                                 #
        #----------------------------------------------------------------------#
        self.pid = os.fork ()
        if self.pid:
            # pipes
            self.stdin  = stdin_pipe.WriteAsync ()
            self.stdout = stdout_pipe.ReadAsync ()
            self.stderr = stderr_pipe.ReadAsync ()

            # result
            self.result = self.result_worker (alive_pipe.ReadAsync ())

        else:
            try:
                # pipes
                stdin_pipe.Read (0)
                stdout_pipe.Write (1)
                stderr_pipe.Write (2)
                alive_pipe.Write ()

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
        return self.stdin

    @property
    def Stdout (self):
        return self.stdout

    @property
    def Stderr (self):
        return self.stderr

    @property
    def Result (self):
        return self.result

    @property
    def Pid (self):
        return self.pid

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def result_worker (self, alive_stream):
        try:
            with ScopeFuture () as cancel:
                self.dispose += cancel

                yield alive_stream.Read (1, cancel)

        except CoreDisconnectedError: pass
        except Exception:
            os.kill (self.pid, signal.SIGTERM)
            os.waitpid (self.pid, 0)
            raise

        # result
        result = os.waitpid (self.pid, 0) [1]
        if self.check and result:
            raise ProcessError ('Command \'{}\' returned non-zero exit status {}'.format (self.command, result))

        AsyncReturn (result)

    def fd_get (self, file, default):
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
    def __init__ (self, fds, process):
        self.process = process
        if fds:
            self.piped = False
            self.read_fd, self.write_fd = fds
        else:
            self.piped = True
            self.read_fd, self.write_fd = os.pipe ()

        # dispose
        process.dispose += self

    #--------------------------------------------------------------------------#
    # Read Side                                                                #
    #--------------------------------------------------------------------------#
    def Read (self, fd = None):
        read_fd, write_fd = self.fds ()
        self.close (write_fd)
        return self.dup (read_fd, fd)

    def ReadAsync (self):
        return self.async (self.Read ())

    #--------------------------------------------------------------------------#
    # Write Side                                                               #
    #--------------------------------------------------------------------------#
    def Write (self, fd = None):
        read_fd, write_fd = self.fds ()
        self.close (read_fd)
        return self.dup (write_fd, fd)

    def WriteAsync (self):
        return self.async (self.Write ())

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    def fds (self):
        if self.read_fd is None and self.write_fd is None:
            raise ProcessError ('Pipe has already been consumed')

        read_fd, self.read_fd = self.read_fd, None
        write_fd, self.write_fd = self.write_fd, None

        return read_fd, write_fd

    def async (self, fd):
        if fd is None:
            return

        file  = AsyncFile (fd, buffer_size = self.process.buffer_size, closefd = self.piped, core = self.process.core)
        self.process.dispose += file
        if self.piped:
            file.CloseOnExec (True)

        return file

    def dup (self, src, dst):
        if dst is None or src == dst:
            return src
        else:
            os.dup2 (src, dst)
            os.close (src)
            return dst

    def close (self, fd):
        if self.piped and fd is not None:
            os.close (fd)

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        self.close (self.read_fd)
        self.close (self.write_fd)

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

    # vars
    if input is not None and stdin is not None:
        raise ProcessError ('Input cannot be consumed when stdin is set')

    stdin  = PIPE if stdin is None else stdin
    stdout = PIPE if stdout is None else stdout
    stderr = PIPE if stderr is None else stderr

    # read helper
    @Async
    def read (stream):
        if stream is None:
            AsyncReturn (None)

        try:
            data = io.BytesIO ()
            while True:
                data.write ((yield stream.Read (buffer_size, cancel)))
        except CoreDisconnectedError: pass
        AsyncReturn (data.getvalue ())

    # process helper
    @Async
    def process ():
        with Process (command, stdin, stdout, stderr, shell, environ, check, buffer_size, core) as proc:
            # input
            if input is not None:
                proc.Stdin.Write (input).Continue (lambda future: proc.Stdin.Dispose ())
            else:
                proc.Stdin.Dispose ()

            # out
            out = read (proc.Stdout)
            err = read (proc.Stderr)
            yield Future.WhenAll ((out, err))

            # return
            yield proc.Result

            AsyncReturn ((out.Result (), err.Result ()))

    return process ()

#------------------------------------------------------------------------------#
# Defaults                                                                     #
#------------------------------------------------------------------------------#
default_buffer_size = 1 << 16

# vim: nu ft=python columns=120 :
