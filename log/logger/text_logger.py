# -*- coding: utf-8 -*-
import sys

from ..log import *
from ..utils import *
from ..string import *

from ...observer import *

__all__ = ('TextLogger',)
#------------------------------------------------------------------------------#
# Text Logger                                                                  #
#------------------------------------------------------------------------------#
class TextLogger (Observer):
    def __init__ (self, stream = None):
        self.stream = sys.stderr if stream is None else stream

    #--------------------------------------------------------------------------#
    # Observer Interface                                                       #
    #--------------------------------------------------------------------------#
    def OnNext (self, event):
        # messages
        if event.type & EVENT_MESSAGE:
            if event.type & EVENT_DEBUG:
                prefix = '[debug] '
            elif event.type & EVENT_INFO:
                prefix = '[info] '
            elif event.type & EVENT_WARN:
                prefix = '[warn] '
            elif event.type & EVENT_ERROR:
                prefix = '[error] '
            else:
                raise ValueError ('Unknown event type')

            self.prefix_draw (event)
            self.stream.write (prefix)
            self.write (event.Message)

        # progress
        elif event.type & EVENT_PROGRESS:
            if event.type & EVENT_BAR:
                engine = self.ProgressBarEngine (event)
            elif event.type & EVENT_PENDING:
                engine = self.PendingEngine (event)
            else:
                engine = self.ProgressEngine (event)
            event.Subscribe (ProgressObserver (self, engine))

    #--------------------------------------------------------------------------#
    # Progress                                                                 #
    #--------------------------------------------------------------------------#
    def ProgressEngine (self, event):
        try:
            # first
            self.prefix_draw (event)

            # update
            value = yield event.Message
            while value is not None:
                self.prefix_draw (event)
                value = yield String (event.Message, (' ',), value)

            # last
            self.prefix_draw (event)
            yield String (event.Message, (' ',), value)

        except Exception as error:
            # error
            self.prefix_draw (event)
            yield String (event.Message, (' {}:{}'.format (error.__class__.__name__, error), '11'))

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
            yield event.Message

        except Exception as error:
            print ('test')
            # error
            self.bar_draw (value)
            self.prefix_draw (event)
            yield String (event.Message, (' {}:{}'.format (error.__class__.__name__, error), '11'))

    bar_pattern = String (('[', '5'), ('{0}{1}', '15'), (']', '5'), ('{2:>3}%', '17'))
    bar_size   = 23

    @Cached
    def bar_string (self, value):
        filled = int (value / 100 * self.bar_size)
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
            yield event.Message

        except Exception as error:
            # failed
            self.pending_draw (False)
            self.prefix_draw (event)
            yield String (event.Message, (' {}:{}'.format (error.__class__.__name__, error), '11'))

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
        self.stream.write ('[{}] '.format (event.Log.Domain))

    def write (self, string):
        if isinstance (string, String):
            for chunk, color in string:
                self.stream.write (chunk)
        else:
            self.stream.write (string)

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        pass

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

#------------------------------------------------------------------------------#
# Progress Observer
#------------------------------------------------------------------------------#
class ProgressObserver (Observer):
    def __init__ (self, logger, engine):
        self.engine = engine
        self.logger = logger

        self.OnNext (None)

    def OnNext (self, value):
        string = self.engine.send (value)
        if string:
            self.logger.write (string)
        self.logger.stream.write ('\n')

    def OnError (self, error):
        string = self.engine.throw (*error)
        if string:
            self.logger.write (string)
        self.logger.stream.write ('\n')
        self.engine.close ()

    def OnCompleted (self):
        self.OnNext (None)
        self.engine.close ()

# vim: nu ft=python columns=120 :
