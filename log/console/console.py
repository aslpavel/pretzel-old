# -*- coding: utf-8 -*-
import time

from .draw import (BarDrawer, TimeDrawer, TagDrawer,
                   PendingDrawer, PENDING_BUSY, PENDING_DONE, PENDING_FAIL)

from ..log import Log
from ...console import Console
from ...console import COLOR_RED, COLOR_GREEN, COLOR_YELLOW, COLOR_BLUE

__all__ = ('ConsoleLogger',)
#------------------------------------------------------------------------------#
# ConsoleLogger                                                                #
#------------------------------------------------------------------------------#
class ConsoleLogger (object):
    def __init__ (self, stream = None, noecho = None):
        self.console    = Console (stream)
        self.start_time = time.time ()

        if noecho is None or noecho:
            self.console.NoEcho ()

        # message
        self.info_draw = TagDrawer (self.console, COLOR_GREEN)
        self.warn_draw = TagDrawer (self.console, COLOR_YELLOW)
        self.error_draw = TagDrawer (self.console, COLOR_RED)
        self.source_draw = TagDrawer (self.console, COLOR_BLUE)

        # pending
        self.pending_draw = PendingDrawer (self.console)
        self.time_draw = TimeDrawer (self.console)

        # bar
        self.bar_draw = BarDrawer (self.console)

    #--------------------------------------------------------------------------#
    # Message                                                                  #
    #--------------------------------------------------------------------------#
    def Info (self, *args, **keys):
        with self.console.Line ():
            self.info_draw ('info')
            self.elapsed_draw ()
            source = keys.get ('source')
            if source is not None:
                self.source_draw (source)
            self.console.Write (' ', *args)

    def Warning (self, *args, **keys):
        with self.console.Line ():
            self.warn_draw ('warn')
            self.elapsed_draw ()
            source = keys.get ('source')
            if source is not None:
                self.source_draw (source)
            self.console.Write (' ', *args)

    def Error (self, *args, **keys):
        with self.console.Line ():
            self.error_draw ('erro')
            self.elapsed_draw ()
            source = keys.get ('source')
            if source is not None:
                self.source_draw (source)
            self.console.Write (' ', *args)

    #--------------------------------------------------------------------------#
    # Observe                                                                  #
    #--------------------------------------------------------------------------#
    def Observe (self, future, *args, **keys):
        #----------------------------------------------------------------------#
        # Begin                                                                #
        #----------------------------------------------------------------------#
        label = self.console.Label ()
        begin = time.time ()
        with label.Update ():
            self.pending_draw (PENDING_BUSY)
            self.elapsed_draw ()
            source = keys.get ('source')
            if source is not None:
                self.source_draw (source)
            self.console.Write (' ', *args)

        #----------------------------------------------------------------------#
        # Report                                                               #
        #----------------------------------------------------------------------#
        on_report = getattr (future, 'OnReport', None)
        if on_report:
            def report (value):
                with label.Update (False):
                    self.console.Move (None, self.console.Size () [1] - self.bar_draw.width + 1)
                    self.bar_draw (value)
            on_report += report

        #----------------------------------------------------------------------#
        # Continuation                                                         #
        #----------------------------------------------------------------------#
        def continuation (future):
            label.Dispose ()
            with self.console.Line ():
                error = future.Error ()
                if error is None:
                    self.pending_draw (PENDING_DONE)
                    self.elapsed_draw ()
                    if source is not None:
                        self.source_draw (source)
                    self.console.Write (' ', *args)

                    result = future.Result ()
                    if result is not None:
                        self.console.Write (': ', result)
                else:
                    self.pending_draw (PENDING_FAIL)
                    self.elapsed_draw ()
                    if source is not None:
                        self.source_draw (source)
                    self.console.Write (' ', *args)
                    self.console.Write (': ', error [1])

        future.Continue (continuation)
        return future

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    def elapsed_draw (self):
        self.time_draw (time.time () - self.start_time)

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        self.console.Dispose ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

# register
Log.LoggerRegister ('console', ConsoleLogger)

# vim: nu ft=python columns=120 :
