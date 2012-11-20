# -*- coding: utf-8 -*-
import os
import threading
from collections import deque
from ..async import Async, AsyncReturn, Core, CoreStopped, BlockingFD

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
        BlockingFD (self.get_pipe, False)

    #--------------------------------------------------------------------------#
    # Enqueue | Dequeue                                                        #
    #--------------------------------------------------------------------------#
    def Enqueue (self, item):
        """Enqueue item, thread safely, in queue
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
    def Dequeue (self):
        """Asynchronously dequeue item from queue
        """
        while not self.disposed:
            with self.queue_lock:
                if self.queue:
                    AsyncReturn (self.queue.popleft ())
                self.queue_wait = True

            try:
                yield self.core.WhenFile (self.get_pipe, self.core.READ)
                while len (os.read (self.get_pipe, 65536)) == 65536: pass

            except OSError: break
            except CoreStopped: break

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

        self.core.WhenFile (self.get_pipe, None)
        os.close (self.get_pipe)
        os.close (self.put_pipe)

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

# vim: nu ft=python columns=120 :
