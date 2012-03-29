# -*- coding: utf-8 -*-
from .console import *

from ..log import *
from ..utils import *
from ..string import *

from ...observer import *

__all__ = ('ConsoleLogger',)
#------------------------------------------------------------------------------#
# Console Logger                                                               #
#------------------------------------------------------------------------------#
class ConsoleLogger (Observer):
    def __init__ (self, stream = None):
        self.console = Console (stream)
        self.console.NoEcho ()

    #--------------------------------------------------------------------------#
    # Observer Interface                                                       #
    #--------------------------------------------------------------------------#
    def OnNext (self, event):
        # messages
        if event.type & EVENT_MESSAGE:
            if event.type & EVENT_DEBUG:
                prefix = String (('[debug] ', '14'))
            elif event.type & EVENT_INFO:
                prefix = String (('[info] ', '12'))
            elif event.type & EVENT_WARN:
                prefix = String (('[warn] ', '13'))
            elif event.type & EVENT_ERROR:
                prefix = String (('[error] ', '11'))
            else:
                raise ValueError ('Unknown event type')
            with self.console.Put ():
                self.prefix_draw (event)
                self.console.Write (prefix)
                self.console.Write (event.Message)

        # progress
        elif event.type & EVENT_PROGRESS:
            if event.type & EVENT_BAR:
                engine, erase = self.ProgressBarEngine (event), False
            elif event.type & EVENT_PENDING:
                engine, erase = self.PendingEngine (event), False
            else:
                engine, erase = self.ProgressEngine (event), True
            event.Subscribe (ProgressObserver (self.console, engine, erase))

    #--------------------------------------------------------------------------#
    # Progress                                                                 #
    #--------------------------------------------------------------------------#
    def ProgressEngine (self, event):
        try:
            # first
            self.prefix_draw (event)
            value = yield event.Message

            # update
            while True:
                self.prefix_draw (event)
                current = yield String (event.Message, ' ', value)
                if current is None:
                    break
                value = current

            # last
            self.prefix_draw (event)
            yield String (('[{}] '.format (event.ElapsedString), '5'), event.Message, ' ', value)

        except Exception as error:
            # error
            self.prefix_draw (event)
            yield String (('[{}] '.format (event.ElapsedString), '5'),
                event.Message, (' {}:{}'.format (error.__class__.__name__, error), '11'))

    #--------------------------------------------------------------------------#
    # Progress Bar                                                             #
    #--------------------------------------------------------------------------#
    def ProgressBarEngine (self, event):
        value = 0
        try:
            # first
            self.bar_draw (0)
            self.prefix_draw (event)

            # update
            value = yield event.Message
            while value is not None:
                self.bar_draw (value)
                self.prefix_draw (event)
                value = yield event.Message

            # last
            self.bar_draw (1)
            self.prefix_draw (event)
            yield String (('[{}] '.format (event.ElapsedString), '5'), event.Message)

        except Exception as error:
            # error
            self.bar_draw (value)
            self.prefix_draw (event)
            yield String (('[{}] '.format (event.ElapsedString), '5'),
                event.Message, (' {}:{}'.format (error.__class__.__name__, error), '11'))

    bar_pattern = String (('[', '5'), ('{0}{1}', '15'), (']', '5'), ('{2:>3}%', '17'))
    bar_size   = 23

    @Cached
    def bar_string (self, value):
        filled = int (value / 100.0 * self.bar_size)
        return self.bar_pattern.Format ('#' * filled, '-' * (self.bar_size - filled), value)

    def bar_draw (self, value):
        columns, rows = self.console.Size ()
        bar = self.bar_string (int (value * 100))
        self.console.MoveColumn (columns - len (bar) + 1)
        self.console.Write (bar)
        self.console.MoveColumn (0)

    #--------------------------------------------------------------------------#
    # Pending                                                                  #
    #--------------------------------------------------------------------------#
    def PendingEngine (self, event):
        try:
            # busy
            self.pending_draw ()
            self.prefix_draw (event)
            yield event.Message

            # done
            self.pending_draw (True)
            self.prefix_draw (event)
            yield String (('[{}] '.format (event.ElapsedString), '5'), event.Message)

        except Exception as error:
            # failed
            self.pending_draw (False)
            self.prefix_draw (event)
            yield String (('[{}] '.format (event.ElapsedString), '5'),
                event.Message, (' {}:{}'.format (error.__class__.__name__, error), '11'))

    pending_busy = String (('[', '5'), ('BUSY', '15'), (']', '5'))
    pending_fail = String (('[', '5'), ('FAIL', '11'), (']', '5'))
    pending_done = String (('[', '5'), ('DONE', '12'), (']', '5'))

    def pending_draw (self, result = None):
        status = self.pending_busy if result is None else \
            self.pending_done if result else self.pending_fail
        columns, rows = self.console.Size ()
        self.console.MoveColumn (columns - len (status) + 1)
        self.console.Write (status)
        self.console.MoveColumn (0)

    #--------------------------------------------------------------------------#
    # Common                                                                   #
    #--------------------------------------------------------------------------#
    def prefix_draw (self, event):
        self.console.Write (String (('[{}] '.format (event.Log.Domain), '15')))

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        self.console.Dispose ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

#------------------------------------------------------------------------------#
# Progress Observer
#------------------------------------------------------------------------------#
class ProgressObserver (Observer):
    def __init__ (self, console, engine, erase = True):
        self.console   = console
        self.engine = engine
        self.erase = erase

        self.label = console.Label ()
        self.OnNext (None)

    def OnNext (self, value):
        with self.label.Update (self.erase):
            string = self.engine.send (value)
            if string:
                self.console.Write (string)

    def OnError (self, error):
        self.label.Dispose ()
        with self.console.Put ():
            string = self.engine.throw (*error)
            if string:
                self.console.Write (string)
        self.engine.close ()

    def OnCompleted (self):
        self.label.Dispose ()
        with self.console.Put ():
            string = self.engine.send (None)
            if string:
                self.console.Write (string)
        self.engine.close ()

# vim: nu ft=python columns=120 :
