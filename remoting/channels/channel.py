# -*- coding: utf-8 -*-
import sys

from ...event import *
from ...async import *
from ...async.wait import *
from ...async.cancel import *
from ...disposable import *

__all__ = ('Channel', 'ChannelError',)
#------------------------------------------------------------------------------#
# Channel                                                                      #
#------------------------------------------------------------------------------#
class ChannelError (Exception): pass
class Channel (object):
    def __init__ (self, core):
        self.core = core

        self.recv_handlers = {}
        self.recv_queue    = {}
        self.recv_worker   = None
        self.recv_wait     = MutableWait ()

        self.OnDisconnect  = Event ()

    #--------------------------------------------------------------------------#
    # Connect                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def Connect (self):
        if not self.IsConnected:
            try: yield self.connect ()
            except Exception:
                self.disconnect ()
                
    @property
    def IsConnected (self):
        return False if self.recv_worker is None else not self.recv_worker.IsCompleted ()

    #--------------------------------------------------------------------------#
    # Methods                                                                  #
    #--------------------------------------------------------------------------#
    def Send (self, message):
        return FailedFuture (NotImplementedError ())

    def Recv (self):
        return FailedFuture (NotImplementedError ())

    def RecvTo (self, destination):
        future = self.recv_queue.get (destination)
        if future is None:
            def cancel ():
                self.recv_queue.pop (destination, None)
                future.ErrorRaise (FutureCanceled ())

            future = MutableFuture ()
            future.wait.Replace (self.recv_wait)
            future.cancel.Replace (Cancel (cancel))

            self.recv_queue [destination] = future

        return future

    def RecvToHandler (self, destination, handler):
        if self.recv_handlers.get (destination) is not None:
            raise ChannelError ('Handler has already been assigned')
        self.recv_handlers [destination] = handler
        return Disposable (lambda: self.recv_handlers.pop (destination))
        
    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    @DummyAsync
    def connect (self):
        self.recv_worker = self.recv_main ().Traceback ('recv_main')
        if self.recv_worker.IsCompleted ():
            self.recv_worker.Result ()
            raise ChannelError ('Receive worker has terminated immediately')

    def disconnect (self):
        self.OnDisconnect ()

    @Async
    def recv_main (self):
        try:
            while True:
                message_future = self.Recv ()
                self.recv_wait.Replace (message_future.Wait)
                self.recv_dispatch ((yield message_future))

        except FutureCanceled: pass
        except CoreStopped: pass
        except CoreDisconnectedError: pass
        finally:
            # resolve queued futures
            error = sys.exc_info ()
            self.recv_queue, recv_queue = {}, self.recv_queue
            for future in recv_queue.values ():
                if error [0] is None:
                    future.ErrorRaise (ChannelError ('Connection has been closed unexpectedly'))
                else:
                    future.ErrorSet (error)

            self.disconnect ()

    @Async
    def recv_dispatch (self, message):
        untie_future = self.core.Idle ()

        future = self.recv_queue.pop (message.dst, None)
        if future is not None:
            future.wait.Replace (untie_future.Wait)
            yield untie_future
            future.ResultSet (message)

        handler = self.recv_handlers.get (message.dst, None)
        if handler is not None:
            yield untie_future
            handler (message)

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        if self.recv_worker is not None:
            self.recv_worker.Dispose ()

    def __enter__ (self):
        return self
    
    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False
    
# vim: nu ft=python columns=120 :