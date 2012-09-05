# -*- coding: utf-8 -*-
import atexit
import operator

from ..async import FutureSource, ProgressFuture
from ..disposable import Disposable

__all__ = ('Log',)
#------------------------------------------------------------------------------#
# Log Type                                                                     #
#------------------------------------------------------------------------------#
class LogType (object):
    logger_types   = {}
    logger_default = 'text'

    def __init__ (self):
        self.loggers = None

        # Observe
        self.observe = self.caller ('Observe')

        # Message
        self.Info    = self.caller ('Info')
        self.Warning = self.caller ('Warning')
        self.Error   = self.caller ('Error')

    #--------------------------------------------------------------------------#
    # Logger                                                                   #
    #--------------------------------------------------------------------------#
    @property
    def Loggers (self):
        return self.loggers

    def LoggerAttach (self, logger):
        # attach
        if self.loggers is None:
            self.loggers = [logger]
        else:
            self.loggers.append (logger)

        # detach
        def detach ():
            try:
                if self.loggers:
                    self.loggers.remove (logger)
            except ValueError: pass

        return Disposable (detach)

    def LoggerCreate (self, name, *args, **keys):
        logger_type = self.logger_types.get (name)
        if logger_type is None:
            raise ValueError ('Uknown logger name: {}'.format (name))

        return self.LoggerAttach (logger_type (*args, **keys))

    @classmethod
    def LoggerRegister (cls, name, logger_type):
        if logger_type != cls.logger_types.setdefault (name, logger_type):
            raise ValueError ('Name has already been registred: {}', name)

    #--------------------------------------------------------------------------#
    # Observe                                                                  #
    #--------------------------------------------------------------------------#
    def Observe (self, future, *args, **keys):
        self.observe (future, *args, **keys)
        return future

    #--------------------------------------------------------------------------#
    # Scope                                                                    #
    #--------------------------------------------------------------------------#
    def __call__ (self, *args, **keys):
        return LogScope (self, args, keys)

    def Scope (self, *args, **keys):
        return LogScope (self, args, keys)

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    def caller (self, name):
        method = operator.attrgetter (name)

        def call (*args, **keys):
            if not self.loggers:
                self.LoggerCreate (self.logger_default)
            for logger in self.loggers:
                method (logger) (*args, **keys)

        call.__name__ = name
        return call

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        if not self.loggers:
            return

        loggers, self.loggers = self.loggers, None
        for logger in loggers:
            logger.Dispose ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

#------------------------------------------------------------------------------#
# Log                                                                          #
#------------------------------------------------------------------------------#
Log = LogType ()
atexit.register (Log.Dispose)

#------------------------------------------------------------------------------#
# Log Scope                                                                    #
#------------------------------------------------------------------------------#
class LogScope (object):
    __slots__  = ('log', 'args', 'keys', 'source',)

    def __init__ (self, log, args, keys):
        self.log  = log
        self.args = args
        self.keys = keys
        self.source = None

    #--------------------------------------------------------------------------#
    # Decorator                                                                #
    #--------------------------------------------------------------------------#
    def __call__ (self, async):
        def log_async (*args, **keys):
            return self.log.Observe (async (*args, **keys), *self.args, **self.keys)

        log_async.__name__ = async.__name__
        return log_async

    #--------------------------------------------------------------------------#
    # Scope                                                                    #
    #--------------------------------------------------------------------------#
    def __enter__ (self):
        self.source = FutureSource ()
        future = ProgressFuture (self.source.Future)
        self.log.Observe (future, *self.args, **self.keys)
        return future.OnReport

    def __exit__ (self, et, eo, tb):
        if et is None:
            self.source.ResultSet (None)
        else:
            self.source.ErrorSet ((et, eo, tb))
        return False

# vim: nu ft=python columns=120 :
