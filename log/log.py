# -*- coding: utf-8 -*-
import time
from ..observer import *
from ..disposable import *

__all__ = ('Log', 'EVENT_MESSAGE', 'EVENT_PROGRESS', 'EVENT_DEBUG', 'EVENT_INFO',
    'EVENT_WARN', 'EVENT_ERROR', 'EVENT_BAR', 'EVENT_PENDING',)

#------------------------------------------------------------------------------#
# Log                                                                          #
#------------------------------------------------------------------------------#
class Log (Observable):
    def __init__ (self, domain = None):
        self.domain = domain
        self.observables = set ()

    @property
    def Domain (self):
        return self.domain

    #--------------------------------------------------------------------------#
    # Message                                                                  #
    #--------------------------------------------------------------------------#
    def Debug (self, message):
        self.send (MessageEvent (self, message, EVENT_DEBUG | EVENT_MESSAGE))

    def Info (self, message):
        self.send (MessageEvent (self, message, EVENT_INFO | EVENT_MESSAGE))

    def Warning (self, message):
        self.send (MessageEvent (self, message, EVENT_WARN | EVENT_MESSAGE))

    def Error (self, message):
        self.send (MessageEvent (self, message, EVENT_ERROR | EVENT_MESSAGE))

    #--------------------------------------------------------------------------#
    # Progress                                                                 #
    #--------------------------------------------------------------------------#
    def Progress (self, label):
        progress = ProgressEvent (self, label)
        self.send (progress)
        return progress

    def ProgressBar (self, label):
        progress = ProgressBarEvent (self, label)
        self.send (progress)
        return progress

    #--------------------------------------------------------------------------#
    # Pending                                                                  #
    #--------------------------------------------------------------------------#
    def Pending (self, label):
        pending = PendingEvent (self, label)
        self.send (pending)
        return pending

    #--------------------------------------------------------------------------#
    # Observable Interface                                                     #
    #--------------------------------------------------------------------------#
    def Subscribe (self, observer):
        observer = observer.ToSafe ()
        self.observables.add (observer)
        return Disposable (lambda: self.observables.discard (observer))

    def send (self, event):
        for observer in list (self.observables):
            observer.OnNext (event)

#------------------------------------------------------------------------------#
# Message Types                                                                #
#------------------------------------------------------------------------------#
EVENT_MESSAGE  = 1
EVENT_PROGRESS = 2
# message
EVENT_DEBUG    = 4
EVENT_INFO     = 8
EVENT_WARN     = 16
EVENT_ERROR    = 32
# progress
EVENT_BAR      = 64
EVENT_PENDING  = 128

#------------------------------------------------------------------------------#
# Message Event                                                                #
#------------------------------------------------------------------------------#
class MessageEvent (Observable):
    __slots__ = ('log', 'message', 'type')

    def __init__ (self, log, message, type):
        self.log     = log
        self.message = message
        self.type    = type

    @property
    def Message (self):
        return self.message

    @property
    def Log (self):
        return self.log

#------------------------------------------------------------------------------#
# Progress Event                                                               #
#------------------------------------------------------------------------------#
class ProgressEvent (MessageEvent, Observable):
    __slots__ = ('log', 'message', 'type',  'observables', 'value', 'error', 'begin_time', 'end_time')

    def __init__ (self, log, message, type = 0):
        MessageEvent.__init__ (self, log, message, EVENT_PROGRESS | type)

        self.begin_time, self.end_time = None, None
        self.error, self.value = None, None
        self.observables = set ()

    #--------------------------------------------------------------------------#
    # Observable Interface                                                     #
    #--------------------------------------------------------------------------#
    def Subscribe (self, observer):
        observer = observer.ToSafe ()
        if self.observables is None:
            if self.error is None:
                observer.OnCompleted ()
            else:
                observer.OnError (self.error)
            return Disposable ()

        self.observables.add (observer)
        return Disposable (lambda: self.observables.discard (observer) if self.observables else None)

    #--------------------------------------------------------------------------#
    # Progress Interface                                                       #
    #--------------------------------------------------------------------------#
    def __call__ (self, value):
        if self.observables is None:
            raise RuntimeError ('Progress event has already been completed')

        self.value = value
        for observer in list (self.observables):
            observer.OnNext (value)

    @property
    def Value (self):
        if self.error is None:
            return self.value
        reraise (*self.error)

    @Value.setter
    def Value (self, value):
        self (value)

    #--------------------------------------------------------------------------#
    # Elapsed                                                                  #
    #--------------------------------------------------------------------------#
    @property
    def Elapsed (self):
        if self.begin_time is None or self.end_time is None:
            return None
        return self.end_time - self.begin_time

    @property
    def ElapsedString (self):
        seconds = self.Elapsed
        if seconds is None:
            return None

        hours,   seconds = divmod (seconds, 3600)
        minutes, seconds = divmod (seconds, 60)
        return  '{:0>2.0f}:{:0>2.0f}:{:0>4.1f}'.format (hours, minutes, seconds)

    #--------------------------------------------------------------------------#
    # Context                                                                  #
    #--------------------------------------------------------------------------#
    def __enter__ (self):
        self.begin_time = time.time ()
        return self

    def __exit__ (self, et, eo, tb):
        self.end_time = time.time ()
        if self.observables is not None:
            observables, self.observables = self.observables, None
            if isinstance (eo, Exception):
                self.error = (et, eo, tb)
                while observables:
                    observables.pop ().OnError (self.error)
            else:
                while observables:
                    observables.pop ().OnCompleted ()
        return False

#------------------------------------------------------------------------------#
# Progress Bar Event                                                           #
#------------------------------------------------------------------------------#
class ProgressBarEvent (ProgressEvent):
    __slots__ = ProgressEvent.__slots__

    def __init__ (self, log, message):
        ProgressEvent.__init__ (self, log, message, EVENT_BAR)

    #--------------------------------------------------------------------------#
    # Progress Interface                                                       #
    #--------------------------------------------------------------------------#
    def __call__ (self, value):
        if value > 1 or value < 0:
            raise ValueError ('Value expected to lie in [0, 1]')

        ProgressEvent.__call__ (self, value)

#------------------------------------------------------------------------------#
# Pending Event                                                                #
#------------------------------------------------------------------------------#
class PendingEvent (ProgressEvent):
    __slots__ = ProgressEvent.__slots__

    def __init__ (self, log, message):
        ProgressEvent.__init__ (self, log, message, EVENT_PENDING)
        self.value = False

    #--------------------------------------------------------------------------#
    # Pending Interface                                                        #
    #--------------------------------------------------------------------------#
    def __call__ (self, error = None):
        if self.observables is None:
            raise RuntimeError ('Pending event has already been completed')

        self.end_time = time.time ()
        observables, self.observables = self.observables, None

        if error is None:
            self.value = True
            for observable in observables:
                observable.OnCompleted ()
        else:
            self.error = error
            for observable in observables:
                observable.OnError (error)

    #--------------------------------------------------------------------------#
    # Context                                                                  #
    #--------------------------------------------------------------------------#
    def __exit__ (self, et, eo, tb):
        if et is None and self.error is None:
            self.value = True

        return ProgressEvent.__exit__ (self, et, eo, tb)

#------------------------------------------------------------------------------#
# Compatibility                                                                #
#------------------------------------------------------------------------------#
import sys
if sys.version_info [0] > 2:
    import builtins
    exec_ = getattr (builtins, "exec")
    del builtins

    def reraise (tp, value, tb = None):
        if value.__traceback__ is not tb:
            raise value.with_traceback (tb)
        raise value
else:
    def exec_ (code, globs = None, locs = None):
        """Execute code in a namespace."""
        if globs is None:
            frame = sys._getframe (1)
            globs = frame.f_globals
            if locs is None:
                locs = frame.f_locals
            del frame
        elif locs is None:
            locs = globs
        exec ("""exec code in globs, locs""")

    exec_ ("""def reraise (tp, value, tb=None):
        raise tp, value, tb""")

# vim: nu ft=python columns=120 :
