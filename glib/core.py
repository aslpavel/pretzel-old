# -*- coding: utf-8 -*-
import time
import errno
from gi.repository import GLib

from ..async import (FutureSourcePair, FutureCanceled, SucceededFuture,
                     BrokenPipeError, ConnectionError)

__all__ = ('GCore',)
#------------------------------------------------------------------------------#
# GLib Core                                                                    #
#------------------------------------------------------------------------------#
class GCore (object):
    def __init__ (self, context = None):
        self.sources = set ()

    #--------------------------------------------------------------------------#
    # Time                                                                     #
    #--------------------------------------------------------------------------#
    def Time (self, resume, cancel = None):
        return self.TimeDelay (resume - time.time (), cancel)

    def TimeDelay (self, delay, cancel = None):
        resume = time.time () + delay
        if delay < 0:
            return SucceededFuture (resume)

        return self.source_create (lambda source: source.TrySetResult (resume),
            cancel, GLib.timeout_add, (int (delay * 1000),))

    #--------------------------------------------------------------------------#
    # Idle                                                                     #
    #--------------------------------------------------------------------------#
    def Idle (self, cancel = None):
        return self.source_create (lambda source: source.TrySetResult (None), cancel, GLib.idle_add)

    #--------------------------------------------------------------------------#
    # Poll                                                                     #
    #--------------------------------------------------------------------------#
    READ       = GLib.IO_IN
    WRITE      = GLib.IO_OUT
    URGENT     = GLib.IO_PRI
    DISCONNECT = GLib.IO_HUP
    ERROR      = GLib.IO_ERR | GLib.IO_NVAL | GLib.IO_HUP

    def Poll (self, fd, mask, cancel = None):
        if mask is None:
            return # no clean up for closed file descriptors

        def resolve (source, fd, cond):
            if cond & ~self.ERROR:
                source.TrySetResult (cond)
            else:
                source.TrySetException (BrokenPipeError (errno.EPIPE, 'Broken pipe')
                    if cond & self.DISCONNECT else ConnectionError ())

        return self.source_create (resolve, cancel, GLib.io_add_watch, (fd, mask | self.ERROR))

    #--------------------------------------------------------------------------#
    # Execute                                                                  #
    #--------------------------------------------------------------------------#
    def __call__ (self): return self.Execute ()
    def Execute  (self):
        try:
            for none in self.Iterator ():
                if not self.sources:
                    return
        finally:
            self.Dispose ()

    #--------------------------------------------------------------------------#
    # Iterator                                                                 #
    #--------------------------------------------------------------------------#
    def __iter__ (self): return self.Iterator ()
    def Iterator (self, block = True):
        context = GLib.main_context_default ()
        while True:
            context.iteration (block)
            yield

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    def source_create (self, resolve, cancel, enqueue, args = None):
        """Create and enqueue future

        enqueue (*args, resolve)        -> source_id
        resolve (source, *resolve_args) -> None
        """
        future, source = FutureSourcePair ()

        def resolve_internal (*resolve_args):
            self.sources.discard (source)
            resolve (source, *resolve_args)
            return False # remove from event loop

        if cancel:
            def cancel_cont (result, error):
                GLib.source_remove (source_id)
                self.sources.discard (source)
                source.TrySetCanceled ()
            cancel.Await ().OnCompleted (cancel_cont)

        source_id = enqueue (*(args + (resolve_internal,))) if args else enqueue (resolve_internal)
        self.sources.add (source)

        return future

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self, error = None):
        error = error or FutureCanceled ('Core has been stopped')

        # resolve futures
        sources, self.sources = self.sources, set ()
        for source in list (sources):
            source.TrySetException (error)

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose (eo)
        return False

# vim: nu ft=python columns=120 :
