# -*- coding: utf-8 -*-
import os
import threading
from collections import deque
from ..async import Async, AsyncReturn, Core, CoreDisconnectedError, CoreStopped
from ..async.core.fd import FileBlocking

__all__ = ('CoreQueue', 'CoreQueueError',)
#------------------------------------------------------------------------------#
# Core Queue                                                                   #
#------------------------------------------------------------------------------#
class CoreQueueError (Exception): pass
class CoreQueue (object):
    """Core queue

    You can put item from any thread inside queue and asynchronously get this
    item in core thread.
    """
    def __init__ (self, core = None):
        self.core  = core or Core.Instance ()

        # queue
        self.queue = deque ()
        self.queue_wait = False
        self.queue_lock = threading.RLock ()

        # pipe
        self.get_pipe, self.put_pipe = os.pipe ()
        self.disposed = False
        FileBlocking (self.get_pipe, False)

    #--------------------------------------------------------------------------#
    # Put | Get                                                                #
    #--------------------------------------------------------------------------#
    def Put (self, item):
        """Put item thread safely in queue
        """
        if self.disposed:
            raise CoreQueueError ('Queue has been disposed')

        with self.queue_lock:
            self.queue.append (item)
            if not self.queue_wait:
                return
            self.queue_wait = False
        os.write (self.put_pipe, b' ')

    @Async
    def Get (self):
        """Asynchronously get item from queue
        """
        while not self.disposed:
            with self.queue_lock:
                if self.queue:
                    AsyncReturn (self.queue.popleft ())
                self.queue_wait = True

            try:
                yield self.core.Poll (self.get_pipe, self.core.READ)
                while len (os.read (self.get_pipe, 65536)) == 65536: pass

            except CoreStopped:           break
            except CoreDisconnectedError: break
            except OSError:               break

        raise CoreQueueError ('Queue has been disposed')

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        """Dispose queue
        """
        with self.queue_lock:
            if self.disposed:
                return
            self.disposed = True

        self.core.Poll (self.get_pipe, None)
        os.close (self.get_pipe)
        os.close (self.put_pipe)

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

# vim: nu ft=python columns=120 :
