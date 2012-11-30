# -*- coding: utf-8 -*-
import io
import os
import sys
import errno
import pickle
import signal
import threading

from .disposable import Disposable, CompositeDisposable
from .async import (Async, AsyncReturn, Future, FutureSource, FutureCanceled,
                    SucceededFuture, Pipe, BrokenPipeError, Core)

__all__ = ('Process', 'ProcessCall', 'ProcessWaiter', 'ProcessError',
           'PIPE', 'DEVNULL', 'STDIN', 'STDOUT', 'STDERR',)
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
    default_kill_delay = 10

    def __init__ (self, command, stdin = None, stdout = None, stderr = None,
        preexec = None, shell = None, environ = None, check = None,
        buffer_size = None, kill_delay = None, core = None):

        self.core = core or Core.Instance ()
        self.process_waiter = ProcessWaiter.Instance ()

        # vars
        self.command = ['/bin/sh', '-c', command] if shell else command
        self.environ = environ
        self.kill_delay = kill_delay or self.default_kill_delay
        self.check = check is None or check

        # dispose
        self.dispose = CompositeDisposable ()

        # status
        self.pid = None
        self.status_source = FutureSource ()

        #----------------------------------------------------------------------#
        # Pipes                                                                #
        #----------------------------------------------------------------------#
        def to_fd (file, default):
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

        # status
        status_pipe  = self.dispose.Add (Pipe (core = core))

        # standard output
        stdout_fd = to_fd (stdout, STDOUT)
        self.stdout_pipe = self.dispose.Add (
            Pipe (None if stdout_fd is None else (None, stdout_fd), buffer_size, core))

        # standard error
        stderr_fd = to_fd (stderr, STDERR)
        self.stderr_pipe = self.dispose.Add (
            Pipe (None if stderr_fd is None else (None, stderr_fd), buffer_size ,core))

        # standard input
        stdin_fd = to_fd (stdin, STDIN)
        self.stdin_pipe = self.dispose.Add (
            Pipe (None if stdin_fd is None else (stdin_fd, None), buffer_size, core))

        #----------------------------------------------------------------------#
        # Fork                                                                 #
        #----------------------------------------------------------------------#
        self.pid = os.fork ()
        if self.pid:
            # dispose remote streams
            self.stdin_pipe.Reader.Dispose ()
            self.stdout_pipe.Writer.Dispose ()
            self.stderr_pipe.Writer.Dispose ()
            status_pipe.Writer.Dispose ()

            # close on exec
            for stream in (self.stdin_pipe.Writer, self.stdout_pipe.Reader,
                self.stderr_pipe.Reader, status_pipe.Reader):
                    if stream is not None:
                        stream.CloseOnExec (True)

            # start status coroutine
            self.status_main (status_pipe.Reader).Traceback ('process status main')

        else:
            try:
                # status descriptor (must not block)
                status_fd = status_pipe.DetachWriter ().Result ()

                self.stdin_pipe.DetachReader   (0)
                self.stdout_pipe.DetachWriter (1)
                self.stderr_pipe.DetachWriter (2)

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
        return self.stdin_pipe.Writer

    @property
    def Stdout (self):
        """Standard output asynchronous stream
        """
        return self.stdout_pipe.Reader

    @property
    def Stderr (self):
        """Standard error asynchronous stream
        """
        return self.stderr_pipe.Reader

    @property
    def Status (self):
        """Future object for return code of the process
        """
        return self.status_source.Future

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
        status_future = self.process_waiter (self.pid, self.core)

        # restore error from error stream if any
        try:
            error_dump = yield error_stream.ReadUntilEof ()
            if error_dump:
                self.status_source.ErrorRaise (pickle.loads (error_dump))
                return
        except BrokenPipeError: pass

        # wait for process to terminate
        self.status_source.ResultSet ((yield status_future))

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        """Terminate process and dispose associated resources
        """
        self.dispose.Dispose ()

        @Async
        def kill ():
            """Kill process (with SIGTREM)

            Kill process unless its terminated in ``kill_delay`` seconds.
            """
            if self.Status.IsCompleted ():
                return

            try:
                if self.kill_delay > 0:
                    yield self.core.TimeDelayAwait (self.kill_delay, cancel = self.Status)
            except FutureCanceled: pass
            finally:
                if not self.Status.IsCompleted ():
                    os.kill (self.pid, signal.SIGTERM)
        kill ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

    #--------------------------------------------------------------------------#
    # Representation                                                           #
    #--------------------------------------------------------------------------#
    def __str__ (self):
        """String representation of the process
        """
        if self.Status.IsCompleted ():
            error = self.Status.Error ()
            if error:
                status = repr (error)
            else:
                status = self.Status.Result ()
        else:
            status = 'running'
        return '<Process [pid:{} status:{}] at {}'.format (self.pid, status, id (self))
    __repr__ = __str__

#------------------------------------------------------------------------------#
# Call Process                                                                 #
#------------------------------------------------------------------------------#
def ProcessCall (command, input = None, stdin = None, stdout = None, stderr = None,
    preexec = None, shell = None, environ = None, check = None, buffer_size = None,
    kill_delay = None, core = None, cancel = None):
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
        with Process (command = command, stdin = stdin, stdout = stdout, stderr = stderr,
            preexec = preexec, shell = shell, environ = environ, check = check,
            buffer_size = buffer_size, kill_delay = kill_delay, core = core) as proc:

            # input
            if input:
                proc.Stdin.WriteBuffer (input)
                proc.Stdin.Flush ().Continue (lambda *_: proc.Stdin.Dispose ())

            # output
            out = proc.Stdout.ReadUntilEof (cancel) if proc.Stdout else SucceededFuture (None)
            err = proc.Stderr.ReadUntilEof (cancel) if proc.Stderr else SucceededFuture (None)
            yield Future.All ((out, err))

            AsyncReturn ((out.Result (), err.Result (), (yield proc.Status)))

    return process ()

#------------------------------------------------------------------------------#
# Process Waiter                                                               #
#------------------------------------------------------------------------------#
class ProcessWaiter (object):
    """Process waiter

    Waits for child process to terminate and returns its exit code. This object
    MUST BE CREATED INSIDE MAIN THREAD as signal.signal would fail otherwise.
    """
    instance_lock = threading.RLock ()
    instance      = None

    def __init__ (self):
        self.queue = []
        self.handle_signal_prev = signal.signal (signal.SIGCHLD, self.handle_signal)

    #--------------------------------------------------------------------------#
    # Instance                                                                 #
    #--------------------------------------------------------------------------#
    @classmethod
    def Instance (cls, instance = None):
        """Global process waiter instance

        If ``instance`` is provided sets current global instance to ``instance``,
        otherwise returns current global instance, creates it if needed.
        """
        try:
            with cls.instance_lock:
                if instance is None:
                    if cls.instance is None:
                        cls.instance = ProcessWaiter ()
                else:
                    if instance is cls.instance:
                        return instance
                    instance, cls.instance = cls.instance, instance
                return cls.instance
        finally:
            if instance:
                instance.Dispose ()

    #--------------------------------------------------------------------------#
    # Wait                                                                     #
    #--------------------------------------------------------------------------#
    def __call__ (self, pid, core = None):
        """Wait for process exit status

        Returned future will be resolved inside core's context.
        """
        # check if process has already been terminated
        pid, status = os.waitpid (pid, os.WNOHANG)
        if pid != 0:
            return SucceededFuture (os.WEXITSTATUS (status))

        # enqueue source
        with self.instance_lock:
            source = FutureSource ()
            self.queue.append ((pid, source, core or Core.Instance (),))
        return source.Future

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    def handle_signal (self, sig, frame):
        """Handle SIGCHLD
        """
        with self.instance_lock:
            resolved_queue, unresolved_queue = [], []
            for pid, source, core in self.queue:
                try:
                    pid, status = os.waitpid (pid, os.WNOHANG)
                    if pid == 0:
                        unresolved_queue.append ((pid, source, core,))
                        continue
                except OSError as error:
                    if error.errno != errno.ECHILD:
                        raise
                    status = -1
                resolved_queue.append ((pid, source, core, status))
            self.queue = unresolved_queue

        for pid, source, core, status in resolved_queue:
            try:
                # Resolve source inside calling core's thread
                core.ContextAwait (os.WEXITSTATUS (status)).Continue (
                    lambda result, error: source.ResultSet (result))
            except FutureCanceled: pass

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        """Dispose process waiter
        """
        signal.signal (signal.SIGCHLD, self.handle_signal_prev)

        pid_source, self.pid_source = self.pid_source, {}
        for pid, source in pid_source.items ():
            source.ErrorRaise (FutureCanceled ('Process waiter has been disposed'))

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

# vim: nu ft=python columns=120 :
