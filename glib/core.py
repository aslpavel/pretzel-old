# -*- coding: utf-8 -*-
import time
from gi.repository import GLib

from ..async import (FutureSource, FutureCanceled, SucceededFuture,
                     CoreError, CoreStopped, CoreDisconnectedError, CoreIOError)

__all__ = ('GCore',)
#------------------------------------------------------------------------------#
# GLib Core                                                                    #
#------------------------------------------------------------------------------#
class GCore (object):
    def __init__ (self, context = None):
        self.sources = set ()

    #--------------------------------------------------------------------------#
    # Sleep                                                                    #
    #--------------------------------------------------------------------------#
    def Sleep (self, delay, cancel = None):
        resume = time.time () + delay
        if delay < 0:
            return SucceededFuture (resume)

        return self.source_create (lambda source: source.ResultSet (resume),
            cancel, GLib.timeout_add, (int (delay * 1000),))

    def SleepUntil (self, resume, cancel = None):
        return self.Sleep (resume - time.time (), cancel)

    #--------------------------------------------------------------------------#
    # Idle                                                                     #
    #--------------------------------------------------------------------------#
    def Idle (self, cancel = None):
        return self.source_create (lambda source: source.ResultSet (None), cancel, GLib.idle_add)

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
            return # no cleanup for closed file descriptors

        def resolve (source, fd, cond):
            if cond & self.ERROR:
                source.ErrorRaise (CoreDisconnectedError () if cond & self.DISCONNECT else CoreIOError ())
            else:
                source.ResultSet (cond)

        return self.source_create (resolve, cancel, GLib.io_add_watch, (fd, mask | self.ERROR))

    #--------------------------------------------------------------------------#
    # Execute                                                                  #
    #--------------------------------------------------------------------------#
    @property
    def IsExecuting (self):
        return bool (self.sources)

    def __call__ (self): return self.Execute ()
    def Execute  (self):
        try:
            for none in self.Iterator ():
                if not self.sources:
                    return
        finally:
            self.Dispose (CoreError ('Core has terminated without resolving this future'))

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
        source = FutureSource ()

        def resolve_internal (*resolve_args):
            self.sources.discard (source)
            resolve (source, *resolve_args)
            return False # remove from event loop

        if cancel:
            def cancel_continuation (future):
                GLib.source_remove (source_id)
                self.sources.discard (source)
                source.ErrorRaise (FutureCanceled ())

            cancel.Continue (cancel_continuation)

        source_id = enqueue (*(args + (resolve_internal,))) if args else enqueue (resolve_internal)
        self.sources.add (source)

        return source.Future

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self, error = None):
        error = error or CoreStopped ()

        # resolve futures
        sources, self.sources = self.sources, set ()
        for source in list (sources):
            source.ErrorRaise (error)

        # clear queue
        self.sources.clear ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose (eo)
        return False

# vim: nu ft=python columns=120 :
