# -*- coding: utf-8 -*-
import sys

from ..message import *
from ...async import *
from ...async.wait import *
from ...async.cancel import *

from ..utils.bind_pool import *
from ..utils.worker import *
from ..utils.wait_queue import *

__all__ = ('Channel', 'PersistenceChannel', 'ChannelError')
#------------------------------------------------------------------------------#
# Channel                                                                      #
#------------------------------------------------------------------------------#
class ChannelError (Exception): pass
class Channel (object):
    def __init__ (self, core):
        self.core  = core
        self.runned = False
        self.ports = BindPool ()
        self.yield_queue = WaitQueue (lambda: core.SleepUntil (0))

        # receive
        self.recv_queue = {}
        self.recv_wait = MutableWait ()
        self.recv_worker = Worker (self.recv_main, 'receive worker')

        # events
        self.OnStop = self.recv_worker.OnStop
        self.OnStart = self.recv_worker.OnStart

    #--------------------------------------------------------------------------#
    # Task Interface                                                           #
    #--------------------------------------------------------------------------#
    @Async
    def Run (self):
        if self.runned:
            raise ChannelError ('Channel has already been run')
        self.runned = True
        yield self.run ()

    @property
    def IsRunning (self):
        return bool (self.recv_worker)

    @property
    def Task (self):
        return self.recv_worker.Task

    #--------------------------------------------------------------------------#
    # Request                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def Request (self, port, **attr):
        if not self.recv_worker:
            raise ChannelError ('Receive worker is {}'.format (self.recv_worker.StateString))

        # message
        message = Message (port, **attr)
        yield self.SendMsg (message)

        # cancel
        def cancel ():
            if not future.IsCompleted ():
                self.recv_queue.pop (message.uid, None)
                future.ErrorRaise (FutureCanceled ())

        # future
        future = MutableFuture ()
        future.wait.Replace (self.recv_wait)
        future.cancel.Replace (Cancel (cancel))

        # enqueue
        self.recv_queue [message.uid] = future

        AsyncReturn ((yield future) ())

    #--------------------------------------------------------------------------#
    # Port Interface                                                           #
    #--------------------------------------------------------------------------#
    def BindPort (self, port, handler):
        return self.ports.Bind (port, handler)

    #--------------------------------------------------------------------------#
    # Channel Interface                                                        #
    #--------------------------------------------------------------------------#
    def SendMsg (self, message):
        raise NotImplementedError ()

    def RecvMsg (self):
        raise NotImplementedError ()

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        self.recv_worker.Dispose ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def recv_main (self):
        try:
            while True:
                future = self.RecvMsg ()
                self.recv_wait.Replace (future.Wait)
                port, uid, getter = yield future
                if port >= PORT_SYSTEM:
                    handler = self.ports.get (port)
                    if handler is None:
                        sys.stderr.write (':: error: unbound port {0}\n'.format (port))
                        continue

                    self.yield_queue.Enqueue (self.handle_request, handler, uid, getter)
                else:
                    future = self.recv_queue.pop (uid)
                    future.cancel.Replace ()

                    if port == PORT_RESULT:
                        self.yield_queue.Enqueue (future.ResultSet, getter)
                    elif port == PORT_ERROR:
                        self.yield_queue.Enqueue (self.handle_error, future, getter)

                    future.wait.Replace (self.yield_queue.Future.Wait)

        except CoreHUPError: pass
        except FutureCanceled: pass
        finally:
            # resolve queued futures
            error = sys.exc_info ()
            self.recv_queue, recv_queue = {}, self.recv_queue
            for future in recv_queue.values ():
                if error [0] is None:
                    future.ErrorRaise (ChannelError ('Connection has been closed unexpectedly'))
                else:
                    future.ErrorSet (error)

    #--------------------------------------------------------------------------#
    # Handlers                                                                 #
    #--------------------------------------------------------------------------#
    def handle_error (self, future, getter):
        try: future.ErrorSet (getter ().exc_info ())
        except Exception:
            future.ErrorSet (sys.exc_info ())

    @Async
    def handle_request (self, handler, uid, getter):
        try:
            yield self.SendMsg ((yield handler (getter ())))
            return
        except Exception:
            error = sys.exc_info ()
        yield self.SendMsg (ErrorMessage (uid, *error))

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    def run (self):
        """Run implementation"""
        return self.recv_worker.Run ()

#------------------------------------------------------------------------------#
# Persistence Channel                                                          #
#------------------------------------------------------------------------------#
class PersistenceChannel (Channel):
    def __init__ (self, core):
        self.persistence = BindPool ()
        self.not_persistent = {tuple, list, dict, set, frozenset}

        Channel.__init__ (self, core)

    #--------------------------------------------------------------------------#
    # Persistence Interface                                                    #
    #--------------------------------------------------------------------------#
    def BindPersistence (self, slot, save, restore):
        return self.persistence.Bind (slot, (save, restore))

    def Save (self, target):
        if type (target) in self.not_persistent:
            return None
        for slot, pair in self.persistence.items ():
            save, restore = pair
            target_id = save (target)
            if target_id is not None:
                return slot, target_id

    def Restore (self, uid):
        slot, target_id = uid
        return self.persistence [slot][1] (target_id)

# vim: nu ft=python columns=120 :
