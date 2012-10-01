# -*- coding: utf-8 -*-
import sys
import threading
from collections import deque

from .queue import CoreQueue, CoreQueueError
from ..async import Async, FutureSource, RaisedFuture

__all__ = ('ThreadPool', 'ThreadPoolError',)
#------------------------------------------------------------------------------#
# Thread Pool                                                                  #
#------------------------------------------------------------------------------#
class ThreadPoolError (Exception): pass
class ThreadPoolExit (BaseException): pass
class ThreadPool (object):
    """Thread pool

    Execute action asynchronously inside thread pool.
    """
    instance_lock = threading.Lock ()
    instance = None

    def __init__ (self, size, core = None):
        self.disposed = False
        self.sources = set ()

        self.threads = set ()
        self.threads_max = size
        self.threads_idle = 0
        self.threads_queue = deque ()
        self.threads_lock = threading.RLock ()
        self.threads_cond = threading.Condition (self.threads_lock)

        self.core_queue = CoreQueue (core)
        self.core_main ().Traceback ('core queue')

    #--------------------------------------------------------------------------#
    # Instance                                                                 #
    #--------------------------------------------------------------------------#
    @classmethod
    def Instance (cls):
        """Get global thread pool instance, creates it if it's None
        """
        with cls.instance_lock:
            if cls.instance is None:
                cls.instance = ThreadPool (4)
            return cls.instance

    @classmethod
    def InstanceSet (cls, instance):
        """Set global thread pool instance
        """
        with cls.instance_lock:
            instance_prev, cls.instance = cls.instance, instance
        if instance_prev is not None and instance_prev != instance:
            instance_prev.Dispose ()
        return instance

    #--------------------------------------------------------------------------#
    # Execute                                                                  #
    #--------------------------------------------------------------------------#
    def __call__ (self, action, *args, **keys):
        """Same as Execute
        """
        return self.Execute (action, *args, **keys)

    def Execute  (self, action, *args, **keys):
        """Execute action asynchronously inside thread pool
        """
        if self.disposed:
            return RaisedFuture (ThreadPoolError ('Thread pool has been disposed'))

        source = FutureSource ()
        self.sources.add (source)

        with self.threads_lock:
            self.threads_queue.append ((source, action, args, keys))
            if not self.threads_idle and len (self.threads) < self.threads_max:
                thread = threading.Thread (target = self.thread_main)
                thread.daemon = True
                thread.start ()
                self.threads.add (thread)
            else:
                self.threads_cond.notify ()

        return source.Future

    #--------------------------------------------------------------------------#
    # Size                                                                     #
    #--------------------------------------------------------------------------#
    def Size (self, size = None):
        """Maximum number of worker threads
        """
        if size is None:
            return self.threads_max
        elif size <= 0:
            raise ValueError ('Size must be > 0')
        else:
            with self.threads_lock:
                self.threads_max = size
                if len (self.threads) > size:
                    self.thread_exit (len (self.threads) - size)
                return size

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def core_main (self):
        """Main core coroutine
        """
        try:
            while True:
                source, result, error = yield self.core_queue.Get ()

                try:
                    self.sources.discard (source)
                    if error is None:
                        source.ResultSet (result)
                    else:
                        source.ErrorSet (error)
                except Exception: pass

        except CoreQueueError: pass
        finally:
            self.Dispose ()

    def thread_exit (self, count = None):
        """Leave only count thread running. Terminate all if count is None.
        """
        def action_exit (): raise ThreadPoolExit ()
        with self.threads_lock:
            count = count or len (self.threads)
            self.threads_queue.extendleft ((None, action_exit, [], {}) for _ in range (count))
            self.threads_cond.notify (count)

    def thread_main (self):
        """Main thread function
        """
        try:
            while True:
                with self.threads_lock:
                    while not self.threads_queue:
                        self.threads_idle += 1
                        self.threads_cond.wait ()
                        self.threads_idle -= 1

                    source, action, args, keys = self.threads_queue.popleft ()

                result, error = None, None
                try:
                    result = action (*args, **keys)
                except Exception:
                    error = sys.exc_info ()
                except ThreadPoolExit:
                    return

                self.core_queue.Put ((source, result, error))

        except CoreQueueError: pass
        finally:
            with self.threads_lock:
                self.threads.discard (threading.current_thread ())

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        """Dispose thread pool
        """
        with self.threads_lock:
            if self.disposed:
                return
            elif threading.current_thread () in self.threads:
                raise ValueError ('Thread pool cannot be disposed from its own thread')
            self.disposed = True

        # terminate threads
        self.thread_exit ()

        # dispose core queueu
        self.core_queue.Dispose ()

        # resolve futures
        for source in self.sources:
            source.ErrorRaise (ThreadPoolError ('Thread pool has been disposed'))

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

# vim: nu ft=python columns=120 :
