# -*- coding: utf-8 -*-
import time

from ..async import *
from ..async.core.file import *
from ..async.core.sock import *
from ..async.wait import *
from ..async.cancel import *

from gi.repository import GLib

__all__ = ('GtkCore',)
#------------------------------------------------------------------------------#
# Gtk Core                                                                     #
#------------------------------------------------------------------------------#
class GtkCore (object):
    def __init__ (self, context = None):
        self.uids, self.futures = set (), set ()

    #--------------------------------------------------------------------------#
    # Sleep                                                                    #
    #--------------------------------------------------------------------------#
    def SleepUntil (self, resume):
        return self.Sleep (resume - time.time ())

    def Sleep (self, delay):
        resume = time.time () + delay
        if delay < 0:
            return SucceededFuture (resume)

        # create future
        def resolve (future):
            future.ResultSet (resume)
        return self.future_create (GLib.timeout_add, resolve, int (delay * 1000))

    def Schedule (self, delay, action):
        return self.Sleep (delay).ContinueWithFunction (lambda now: action ())

    #--------------------------------------------------------------------------#
    # Poll                                                                     #
    #--------------------------------------------------------------------------#
    READABLE     = GLib.IO_IN
    WRITABLE     = GLib.IO_OUT
    URGENT       = GLib.IO_PRI
    DISCONNECTED = GLib.IO_HUP
    INVALID      = GLib.IO_NVAL
    ERROR        = GLib.IO_ERR
    ALL          = URGENT | WRITABLE | READABLE
    ALL_ERRORS   = ERROR | DISCONNECTED | INVALID

    def Poll (self, fd, mask):
        # create future
        def resolve (future, fd, cond):
            if cond & self.ALL_ERRORS:
                future.ErrorRaise (CoreDisconnectedError () if cond & self.DISCONNECTED
                    else CoreInvalidError () if cond & self.INVALID
                    else CoreIOError ())
            else:
                future.ResultSet (cond)
        return self.future_create (GLib.io_add_watch, resolve, fd, mask | self.ALL_ERRORS)

    #--------------------------------------------------------------------------#
    # Idle                                                                     #
    #--------------------------------------------------------------------------#
    def Idle (self):
        def resolve (future):
            future.ResultSet (None)
        return self.future_create (GLib.idle_add, resolve)

    #--------------------------------------------------------------------------#
    # Factories                                                                #
    #--------------------------------------------------------------------------#
    def AsyncSocketCreate (self, sock):
        return AsyncSocket (self, sock)

    def AsyncFileCreate (self, fd, buffer_size = None, closefd = None):
        return AsyncFile (self, fd, buffer_size, closefd)

    #--------------------------------------------------------------------------#
    # Run | Stop                                                               #
    #--------------------------------------------------------------------------#
    def Run (self):
        try:
            context = GLib.main_context_default ()
            while self.uids:
                context.iteration (True)
        finally:
            self.resolve_with_error (CoreError ('Core has terminated without resolving this future'))

    def Stop (self):
        self.resolve_with_error (CoreStopped ())
            
    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    def wait (self, uids):
        context = GLib.main_context_default ()
        uids = set (uids)
        while not (uids - self.uids):
            context.iteration (True)

    def future_create (self, enqueue, resolve, *args):
        """Create and enqueue future

        enqueue (*args, resolve)        -> source_id
        resolve (future, *resolve_args) -> None
        """
        # create future
        def cancel ():
            GLib.source_remove (source_id)
            self.uids.discard (source_id)
            self.futures.discard (future)
            future.ErrorRaise (FutureCanceled ())

        def resolve_internal (*resolve_args):
            self.uids.discard (source_id)
            self.futures.discard (future)
            resolve (future, *resolve_args)
            # remove from event loop
            return False

        future  = Future (cancel = Cancel (cancel))

        # enqueue
        args = list (args)
        args.append (resolve_internal)
        source_id = enqueue (*args)
        future.wait = Wait (source_id, self.wait)

        # update sets
        self.uids.add (source_id)
        self.futures.add (future)

        return future

    def resolve_with_error (self, error):
        # resolve futures
        futures, self.futres = self.futures, set ()
        for future in list (futures):
            future.ErrorRaise (error)

        # clear queues
        self.uids.clear ()
        self.futures.clear ()

    #--------------------------------------------------------------------------#
    # Context                                                                  #
    #--------------------------------------------------------------------------#
    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        if et is None:
            self.Run ()
        else:
            self.resolve_with_error (CoreError ('Core\'s context raised an error: {}'.format (eo), eo))
        return False

# vim: nu ft=python columns=120 :
