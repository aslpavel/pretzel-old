# -*- coding: utf-8 -*-
import sys

from ...disposable import Disposable
from ...async import (Async, DummyAsync, Core, BrokenPipeError, FailedFuture,
                      FutureSource, FutureCanceled, Event)

__all__ = ('Channel', 'ChannelError',)
#------------------------------------------------------------------------------#
# Channel                                                                      #
#------------------------------------------------------------------------------#
class ChannelError (Exception): pass
class Channel (object):
    def __init__ (self, core = None):
        self.core = core or Core.Instance ()

        self.recv_handlers = {}
        self.recv_queue    = {}
        self.recv_worker   = None
        self.recv_cancel   = FutureSource ()

        self.OnDisconnect  = Event ()
        self.OnMessage = Event ()

    #--------------------------------------------------------------------------#
    # Connect                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def Connect (self):
        if not self.IsConnected:
            try:
                self.recv_cancel = FutureSource ()
                yield self.connect ()
            except Exception:
                self.Dispose ()
                raise

    @property
    def IsConnected (self):
        return False if self.recv_worker is None else not self.recv_worker.IsCompleted ()

    #--------------------------------------------------------------------------#
    # Methods                                                                  #
    #--------------------------------------------------------------------------#
    def Send (self, message):
        """Send message
        """
        return FailedFuture (NotImplementedError ())

    def Recv (self, cancel = None):
        """Receive message
        """
        return FailedFuture (NotImplementedError ())

    def RecvTo (self, destination, cancel = None):
        """Receive message with specified destination
        """
        source = self.recv_queue.get (destination)
        if source is None:
            source = FutureSource ()

            # cancel
            if cancel:
                def cancel_continuation (result, error):
                    self.recv_queue.pop (destination, None)
                    source.ErrorRaise (FutureCanceled ())
                cancel.Continue (cancel_continuation)

            # enqueue
            self.recv_queue [destination] = source

        return source.Future

    def RecvToHandler (self, destination, handler):
        """Receive to handler

        Receive all messages with destination to the specified handler.
        """
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

    @DummyAsync
    def disconnect (self):
        self.OnDisconnect ()

    @Async
    def recv_main (self):
        """Receive coroutine
        """
        cancel = self.recv_cancel.Future
        try:
            while True:
                self.recv_dispatch ((yield self.Recv (cancel)))

        except FutureCanceled: pass
        except BrokenPipeError: pass
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
        """Dispatch received message
        """
        yield self.core.IdleAwait ()

        self.OnMessage (message)

        source = self.recv_queue.pop (message.dst, None)
        if source is not None:
            source.ResultSet (message)

        handler = self.recv_handlers.get (message.dst, None)
        if handler is not None:
            handler (message)

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        self.recv_cancel.ResultSet (None)

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

# vim: nu ft=python columns=120 :
