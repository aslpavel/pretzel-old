# -*- coding: utf-8 -*-
import sys

from ..log import *
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
            self.stream.write ('\n')
            self.stream.flush ()

        # progress
        elif event.type & EVENT_PROGRESS:
            if event.type & EVENT_BAR:
                engine = self.ProgressEngine (event)
            elif event.type & EVENT_PENDING:
                engine = self.PendingEngine (event)
            else:
                engine = self.ProgressEngine (event)
            event.Subscribe (ProgressObserver (self.stream, engine))

    #--------------------------------------------------------------------------#
    # Progress                                                                 #
    #--------------------------------------------------------------------------#
    def ProgressEngine (self, event):
        try:
            # first
            self.prefix_draw (event)
            self.write (event.Message)
            self.stream.write (' ... [BEGIN]\n')
            yield

            # update
            while (yield):
                pass

            # last
            self.prefix_draw (event)
            self.write (event.Message)
            self.stream.write (' ... [END]\n')
            yield

        except Exception as error:
            # error
            self.prefix_draw (event)
            self.write (event.Message)
            self.stream.write (' {}:{} [FAILED]\n'.format (error.__class__.__name__, error))

    #--------------------------------------------------------------------------#
    # Pending                                                                  #
    #--------------------------------------------------------------------------#
    def PendingEngine (self, event):
        try:
            # busy
            self.prefix_draw (event)
            self.write (event.Message)
            self.stream.write (' ... [BUSY]\n')
            yield

            # done
            self.prefix_draw (event)
            self.write (event.Message)
            self.stream.write (' ... [DONE]\n')
            yield

        except Exception as error:
            # failed
            self.prefix_draw (event)
            self.write (event.Message)
            self.stream.write (' {}:{} [FAILED]\n'.format (error.__class__.__name__, error))
            yield

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
        self.stream.flush ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

#------------------------------------------------------------------------------#
# Progress Observer
#------------------------------------------------------------------------------#
class ProgressObserver (Observer):
    def __init__ (self, stream, engine):
        self.stream = stream
        self.engine = engine

        self.OnNext (None)

    def OnNext (self, value):
        self.engine.send (value)
        self.stream.flush ()

    def OnError (self, error):
        self.engine.throw (*error)
        self.engine.close ()
        self.stream.flush ()

    def OnCompleted (self):
        self.OnNext (None)
        self.engine.close ()
        self.stream.flush ()
# vim: nu ft=python columns=120 :
