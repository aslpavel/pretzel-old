# -*- coding: utf-8 -*-
import io
import os
import signal

from .async import *
from .disposable import *

__all__ = ('Process', 'ProcessCall', 'ProcessError')
#------------------------------------------------------------------------------#
# Process                                                                      #
#------------------------------------------------------------------------------#
class ProcessError (Exception): pass
class Process (object):
    def __init__ (self, core, command, check = None, buffer_size = None):
        self.core    = core
        self.command = command
        self.buffer_size = default_buffer_size if buffer_size is None else buffer_size
        self.check   = True if check is None else check
        self.dispose = CompositeDisposable ()

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

            self.stdin  = self.core.AsyncFileCreate (li); self.dispose += self.stdin
            self.stdout = self.core.AsyncFileCreate (lo); self.dispose += self.stdout
            self.result = self.result_worker (lalive);    self.dispose += self.result
        else:
            # child
            try:
                os.close (lalive)
                os.close (li); os.dup2 (ri, 0) # standard input
                os.close (lo); os.dup2 (ro, 1) # standard output
                os.execvp (self.command [0], self.command)
            finally:
                os.kill (os.getpid (), signal.SIGKILL)

    #--------------------------------------------------------------------------#
    # Properites                                                               #
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
            yield self.core.Poll (fd, self.core.READABLE)
        except CoreHUPError: pass
        except Exception:
            os.kill (self.pid, signal.SIGKILL)
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
@Async
def ProcessCall (core, command, input = None, check = None, buffer_size = None):
    buffer_size = default_buffer_size if buffer_size is None else buffer_size

    with Process (core, command, check) as proc:
        # input
        if input is not None:
            proc.Stdin.Write (input).Continue (lambda future: proc.Stdin.Close ())
        else:
            proc.Stdin.Close ()

        # output
        try:
            output = io.BytesIO ()
            while True:
                output.write ((yield proc.Stdout.Read (buffer_size)))
        except CoreHUPError: pass

        # return
        yield proc.Result
        AsyncReturn (output.getvalue ())

#------------------------------------------------------------------------------#
# Defaults                                                                     #
#------------------------------------------------------------------------------#
default_buffer_size = 1 << 16
# vim: nu ft=python columns=120 :
