# -*- coding: utf-8 -*-
import time

from ..async import *
from ..async.core.file import *
from ..async.wait import *
from ..async.cancel import *

from gi.repository import GLib

__all__ = ('GCore',)
#------------------------------------------------------------------------------#
# GLib Core                                                                    #
#------------------------------------------------------------------------------#
class GCore (object):
    def __init__ (self, context = None):
        self.futures = set ()

    #--------------------------------------------------------------------------#
    # Sleep                                                                    #
    #--------------------------------------------------------------------------#
    def Sleep (self, delay):
        resume = time.time () + delay
        if delay < 0:
            return SucceededFuture (resume)

        # create future
        def resolve (future):
            future.ResultSet (resume)
        return self.future_create (GLib.timeout_add, resolve, int (delay * 1000))

    def SleepUntil (self, resume):
        return self.Sleep (resume - time.time ())

    #--------------------------------------------------------------------------#
    # Poll                                                                     #
    #--------------------------------------------------------------------------#
    READ       = GLib.IO_IN
    WRITE      = GLib.IO_OUT
    URGENT     = GLib.IO_PRI
    DISCONNECT = GLib.IO_HUP
    ERROR      = GLib.IO_ERR | GLib.IO_NVAL | GLib.IO_HUP

    def Poll (self, fd, mask):
        # create future
        def resolve (future, fd, cond):
            if cond & self.ERROR:
                future.ErrorRaise (CoreDisconnectedError () if cond & self.DISCONNECT
                    else CoreInvalidError () if cond & self.INVALID
                    else CoreIOError ())
            else:
                future.ResultSet (cond)
        return self.future_create (GLib.io_add_watch, resolve, fd, mask | self.ERROR)

    #--------------------------------------------------------------------------#
    # Idle                                                                     #
    #--------------------------------------------------------------------------#
    def Idle (self):
        def resolve (future):
            future.ResultSet (None)
        return self.future_create (GLib.idle_add, resolve)

    #--------------------------------------------------------------------------#
    # Run | Stop                                                               #
    #--------------------------------------------------------------------------#
    def Run (self):
        try:
            context = GLib.main_context_default ()
            while self.futures:
                context.iteration (True)
        finally:
            self.Dispose (CoreError ('Core has terminated without resolving this future'))

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    def wait (self, uids):
        context = GLib.main_context_default ()
        running = AnyFuture (uid () for uid in uids)
        while not running.IsCompleted ():
            context.iteration (True)

    def future_create (self, enqueue, resolve, *args):
        """Create and enqueue future

        enqueue (*args, resolve)        -> source_id
        resolve (future, *resolve_args) -> None
        """
        # create future
        def cancel ():
            GLib.source_remove (source_id)
            self.futures.discard (future)
            future.ErrorRaise (FutureCanceled ())

        def resolve_internal (*resolve_args):
            self.futures.discard (future)
            resolve (future, *resolve_args)

            # remove from event loop
            return False

        future = Future (Wait (lambda: future, self.wait), Cancel (cancel))

        # enqueue
        args = list (args)
        args.append (resolve_internal)
        source_id = enqueue (*args)

        # update sets
        self.futures.add (future)

        return future

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self, error = None):
        error = error or CoreStopped ()

        # resolve futures
        futures, self.futres = self.futures, set ()
        for future in list (futures):
            future.ErrorRaise (error)

        # clear queues
        self.futures.clear ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        if et is None:
            self.Run ()
        else:
            self.Dispose (CoreError ('Core\'s context raised an error: {}'.format (eo), eo))
        return False

# vim: nu ft=python columns=120 :
