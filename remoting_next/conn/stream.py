# -*- coding: utf-8 -*-
from .conn import Connection
from ...async import Async, DummyAsync, FutureCanceled, BrokenPipeError

__all__ = ('StreamConnection',)
#------------------------------------------------------------------------------#
# Stream Connection                                                            #
#------------------------------------------------------------------------------#
class StreamConnection (Connection):
    """Asynchronous stream based connected
    """
    def __init__ (self, hub = None, core = None):
        Connection.__init__ (self, hub, core)

        self.in_stream = None
        self.out_stream = None

    #--------------------------------------------------------------------------#
    # Implementation                                                           #
    #--------------------------------------------------------------------------#
    @DummyAsync
    def connect (self, target):
        """Connect implementation

        Target is tuple of input and output streams.
        """
        self.in_stream, self.out_stream = target

        @Async
        def dispatch_coroutine ():
            try:
                if self.in_stream.Disposed:
                    return

                # Begin read next message before dispatching current one, as
                # connection may be closed during dispatching and input stream
                # became disposed.
                msg_next = self.in_stream.BytesRead ()
                while True:
                    msg, msg_next = (yield msg_next), self.in_stream.BytesRead ()

                    # Use separate function to dispatch message, to copy message
                    # instead of capturing local variable inside dispatch loop.
                    dispatch_message (msg)

            except (FutureCanceled, BrokenPipeError): pass
            finally:
                self.Dispose ()

        def dispatch_message (msg):
            # Detachment from  current coroutine is vital here because if handler
            # tries to create nested core loop to resolve future synchronously
            # (i.g. importer proxy) it can stop dispatching coroutine
            self.core.Idle ().Then (lambda r, e: self.dispatch (msg))

        # start receive coroutine
        dispatch_coroutine ().Traceback ('StreamConnection::dispatch_coroutine')

    def disconnect (self):
        """Disconnect implementation
        """
        if self.in_stream is not None:
            self.in_stream.Dispose ()
        if self.out_stream is not None:
            self.out_stream.Dispose ()

    def handle (self, msg, src, dst):
        """Send message implementation
        """
        self.out_stream.BytesWriteBuffer (Connection.handle (self, msg, src, dst))
        self.out_stream.Flush ()
        return True

# vim: nu ft=python columns=120 :
