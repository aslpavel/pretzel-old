# -*- coding: utf-8 -*-
import sys
import os

from ..message import *
from ...async import *

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
        self.ports = BindPool ()
        self.yield_queue = WaitQueue (lambda: core.SleepUntil (0))

        # receive
        self.recv_queue = {}
        self.recv_future = None
        self.recv_worker = Worker (self.recv_main)

        # events
        self.OnStop = self.recv_worker.OnStop
        self.OnStart = self.recv_worker.OnStart

    #--------------------------------------------------------------------------#
    # Run                                                                      #
    #--------------------------------------------------------------------------#
    def Run (self):
        return self.recv_worker.Run ()

    #--------------------------------------------------------------------------#
    # Request                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def Request (self, port, **attr):
        if not self.recv_worker:
            raise ChannelError ('Receive worker is not running')

        # message
        message = Message (port, **attr)
        self.SendMsg (message)

        # future
        future = Future (lambda: self.recv_wait (message.uid))
        self.recv_queue [message.uid] = future

        getter = yield future
        AsyncReturn (getter ())

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
                self.recv_future = self.RecvMsg ()
                port, uid, getter = yield self.recv_future
                if port >= PORT_SYSTEM:
                    handler = self.ports.get (port)
                    if handler is None:
                        sys.stderr.write (':: error: unbound port {0}\n'.format (port), file = sys.stderr)
                        continue

                    self.yield_queue.Enqueue (self.handle_request, handler, getter)
                else:
                    future = self.recv_queue.pop (uid)
                    if port == PORT_RESULT:
                        self.yield_queue.Enqueue (future.ResultSet, getter)
                    elif port == PORT_ERROR:
                        self.yield_queue.Enqueue (lambda: future.ErrorSet (getter ().exc_info ()))

        except CoreHUPError: pass
        except FutureCanceled: pass
        finally:
            # resolve queued futures
            error = sys.exc_info ()
            self.recv_queue, recv_queue = None, self.recv_queue
            for future in recv_queue.values ():
                if error [0] is None:
                    future.ErrorRaise (ChannelError ('connection has been closed unexpectedly'))
                else:
                    future.ErrorSet (error)

    @Async
    def handle_request (self, handler, getter):
        message = getter ()
        try:
            self.SendMsg ((yield handler (message)))
        except Exception:
            error = sys.exc_info ()
            self.SendMsg (message.Error (error))
            raise

    #--------------------------------------------------------------------------#
    # Wait Uid                                                                 #
    #--------------------------------------------------------------------------#
    def recv_wait (self, uid):
        while uid in self.recv_queue:
            self.recv_future.Wait ()
        self.yield_queue.Future.Wait ()

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
