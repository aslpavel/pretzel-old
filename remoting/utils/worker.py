# -*- coding: utf-8 -*-
from ...async import *
from ...event import *

__all__ = ('Worker', 'WorkerError')
#------------------------------------------------------------------------------#
# Worker                                                                       #
#------------------------------------------------------------------------------#
class WorkerError (Exception): pass
class Worker (object):
    STOPPED    = 1
    RUNNING    = 2
    TERMINATED = 4

    def __init__ (self, task_main):
        self.task_main = task_main
        self.task_copier = None
        self.state = self.STOPPED

        self.OnStart = Event ()
        self.OnStop  = Event ()

    #--------------------------------------------------------------------------#
    # Run                                                                      #
    #--------------------------------------------------------------------------#
    @DummyAsync
    def Run (self):
        if not (self.state & self.STOPPED):
            raise WorkerError ('Worker is {}'.format ('running' if self.state & self.RUNNING else 'terminated'))
        self.task ()

    #--------------------------------------------------------------------------#
    # Future                                                                   #
    #--------------------------------------------------------------------------#
    @property
    def Task (self):
        if self.state & self.STOPPED:
            return RaisedFuture (WorkerError ('Worker is stopped'))
        return self.task_copier.Copy ()

    @Async
    def task (self):
        try:
            self.state = self.RUNNING
            self.task_copier = FutureCopier (self.task_main ())
            self.OnStart ()
            yield self.task_copier.Copy ()
        finally:
            self.state = self.TERMINATED
            self.OnStop ()

    #--------------------------------------------------------------------------#
    # State                                                                    #
    #--------------------------------------------------------------------------#
    def Running (self):
        if self.state & self.RUNNING:
            raise WorkerError ('Worker is {}'.format ('stopped' if self.state & self.STOPPED else 'terminated'))

    @property
    def IsRunning (self):
        return self.state & self.RUNNING

    @property
    def IsTerminated (self):
        return self.state & self.STOPPED

    def __bool__ (self):
        return bool (self.state & self.RUNNING)

    def __nonzero__ (self):
        return bool (self.state & self.RUNNING)

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        if self.IsRunning:
            self.task_copier.Future.Cancel ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

#------------------------------------------------------------------------------#
# Future Copier                                                                #
#------------------------------------------------------------------------------#
class FutureCopier (object):
    def __init__ (self, future):
        self.future = future
        self.copies = []

        future.Continue (self.future_cont)

    #--------------------------------------------------------------------------#
    # Copy                                                                     #
    #--------------------------------------------------------------------------#
    def Copy (self):
        copy = Future (self.future.Wait, self.future.Cancel)
        if self.copies is None:
            error = self.future.Error ()
            if error is None:
                copy.ErrorSet (error)
            else:
                copy.ResultSet (self.future.Result ())
        else:
            self.copies.append (copy)
        return copy

    #--------------------------------------------------------------------------#
    # Future                                                                   #
    #--------------------------------------------------------------------------#
    @property
    def Future (self):
        return self.future

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    def future_cont (self, future):
        copies, self.copies = self.copies, None
        error = self.future.Error ()
        if error is None:
            result = future.Result ()
            for copy in copies:
                copy.ResultSet (result)
        else:
            for copy in copies:
                copy.ErrorSet (error)

# vim: nu ft=python columns=120 :
