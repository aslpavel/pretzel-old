# -*- coding: utf-8 -*-
import sys

from ..message import *
from ..util import *
from ...event import *
from ...async import *

__all__ = ('Channel', 'PersistenceChannel', 'ChannelError')
#------------------------------------------------------------------------------#
# Channel                                                                      #
#------------------------------------------------------------------------------#
class ChannelError (Exception): pass
class Channel (object):
    def __init__ (self, core):
        self.queue, self.wait, self.worker = {}, None, None
        self.ports = BindPool ()
        self.core  = core

        self.OnStart, self.OnStop = Event (), Event ()
        self.IsRunning = False

    #--------------------------------------------------------------------------#
    # Start | Stop                                                             #
    #--------------------------------------------------------------------------#
    def Start (self):
        if self.IsRunning:
           raise ChannelError ('worker is running')

        self.worker = self.worker_run ()
        if self.worker.IsCompleted ():
            return self.worker.Result ()
        self.OnStart (self)
        Fork (self.worker, 'channel')

    def Stop (self):
        if not self.IsRunning:
            return
        self.worker.Cancel ()

    #--------------------------------------------------------------------------#
    # Request                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def Request (self, port, **attr):
        """Asynchronous request to remote server"""
        if not self.IsRunning:
            raise ChannelError ('worker is dead')

        # send message
        message = Message (port, **attr)
        yield self.sendmsg (message)

        # register future
        future = Future (lambda: self.wait_uid (message.uid))
        self.queue [message.uid] = future

        message_getter = yield future
        yield self.core.SleepUntil (0) # guaranteed interrupt

        AsyncReturn (message_getter ())

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
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def worker_run (self):
        """Process incoming messages"""
        try:
            self.IsRunning = True
            while True:
                self.wait = self.RecvMsg ()
                message_info = yield self.wait
                if message_info is None:
                    break
                port, uid, message_getter = message_info
                if port >= PORT_SYSTEM:
                    # incoming request
                    handler = self.ports.get (port)
                    if handler is None:
                        sys.stderr.write (':: error: unbound port {0}\n'.format (port))
                        continue

                    Fork (self.handle (handler, message_getter), 'handle')
                else:
                    # system message
                    if port == PORT_RESULT:
                        self.queue.pop (uid).ResultSet (message_getter)
                    elif port == PORT_ERROR:
                        self.queue.pop (uid).ErrorSet (message_getter ().exc_info ())
        except FutureCanceled:
            pass
        finally:
            # resolve queued futures
            error = sys.exc_info ()
            self.queue, queue = {}, self.queue
            for future in queue.values ():
                if error [0] is None:
                    future.ErrorRaise (ChannelError ('connection has been closed unexpectedly'))
                else:
                    future.ErrorSet (error)

            # fire stop event
            self.IsRunning = False
            self.OnStop ()

    @Async
    def handle (self, handler, message_getter):
        yield self.core.SleepUntil (0) # guaranteed interrupt

        message, error = message_getter (), None
        try:
            result = yield handler (message)
        except Exception:
            error = sys.exc_info ()

        yield self.sendmsg (result if error is None else message.Error (*error))

    def wait_uid (self, uid):
        while uid in self.queue:
            self.wait.Wait ()

    @Serialize
    def sendmsg (self, message):
        return self.SendMsg (message)

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
