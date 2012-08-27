# -*- coding: utf-8 -*-
import io
import os
import signal
import traceback

from .async         import Async, AsyncReturn, AsyncFile, Core
from .async.core.fd import FileCloseOnExec
from .disposable    import CompositeDisposable

__all__ = ('Process', 'ProcessCall', 'ProcessError')
#------------------------------------------------------------------------------#
# Process                                                                      #
#------------------------------------------------------------------------------#
class ProcessError (Exception): pass
class Process (object):
    def __init__ (self, command, environ = None, check = None, buffer_size = None, core = None):
        self.core        = core or Core.Instance ()
        self.command     = command
        self.environ     = environ
        self.buffer_size = buffer_size or default_buffer_size
        self.check       = True if check is None else check
        self.dispose     = CompositeDisposable ()

        self.pid     = None
        self.stdin   = None
        self.stdout  = None
        self.result  = None

        # start
        ri, li = os.pipe ()
        lo, ro = os.pipe ()
        lalive, ralive = os.pipe ()

        self.pid = os.fork ()
        if self.pid:
            # parent
            os.close (ri); os.close (ro); os.close (ralive)

            self.stdin = AsyncFile (li, self.buffer_size, core = self.core)
            self.stdin.CloseOnExec (True)
            self.dispose += self.stdin

            self.stdout = AsyncFile (lo, self.buffer_size, core = self.core)
            self.stdout.CloseOnExec (True)
            self.dispose += self.stdout

            self.result = self.result_worker (lalive)
            self.dispose += self.result

        else:
            # child
            try:
                os.close (lalive)
                os.close (li)
                os.close (lo)

                os.dup2 (ri, 0)
                os.close (ri)

                os.dup2 (ro, 1)
                os.close (ro)

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
    def Result (self):
        return self.result

    @property
    def Pid (self):
        return self.pid

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

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def result_worker (self, fd):
        try:
            FileCloseOnExec (fd, True)
            yield self.core.Poll (fd, self.core.READ)
        except CoreDisconnectedError: pass
        except Exception:
            os.kill (self.pid, signal.SIGTERM)
            os.waitpid (self.pid, 0)
            raise
        finally:
            os.close (fd)

        result = os.waitpid (self.pid, 0) [1]
        if self.check and result:
            raise ProcessError ('Command \'{}\' returned non-zero exit status {}'.format (self.command, result))

        AsyncReturn (result)

#------------------------------------------------------------------------------#
# Call Process                                                                 #
#------------------------------------------------------------------------------#
def ProcessCall (command, input = None, environ = None, check = None, buffer_size = None, core = None):
    # helper
    def processCall ():
        with Process (command, environ, check, buffer_size, core) as proc:
            # input
            if input is not None:
                proc.Stdin.Write (input).Continue (lambda future: proc.Stdin.Dispose ())
            else:
                proc.Stdin.Dispose ()

            # output
            try:
                output = io.BytesIO ()
                while True:
                    output.write ((yield proc.Stdout.Read (buffer_size)))
            except CoreDisconnectedError: pass

            # return
            yield proc.Result
            AsyncReturn (output.getvalue ())

    # coroutine future
    return Async (processCall) ()

#------------------------------------------------------------------------------#
# Defaults                                                                     #
#------------------------------------------------------------------------------#
default_buffer_size = 1 << 16
# vim: nu ft=python columns=120 :
