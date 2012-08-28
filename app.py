# -*- coding: utf-8 -*-
import io
import sys
import traceback

from . import async
from .async import *

from .log import Log, String, LoggerCreate, CompositeLogger, TextLogger
from .event import Event
from .disposable import CompositeDisposable
from .remoting.result import *

if sys.version_info [0] > 2:
    string_type = io.StringIO
else:
    string_type = io.BytesIO

__all__ = async.__all__ + ('Application',)
#------------------------------------------------------------------------------#
# Application                                                                  #
#------------------------------------------------------------------------------#
class ApplicationError (Exception): pass
class Application (object):
    def __init__ (self, main, name = None, excecute = True, log_file = None, console = None, core = None):
        """Application Object

        Options:
            name:     application name
            run:      run application immediately
            log_file: use log file
            console:  try to use console logger first
        """
        self.main      = main
        self.name      = name or main.__name__
        self.excecuted = False

        # logging
        self.log      = Log (name)
        self.logger   = None
        self.log_file = log_file
        self.console  = True if console is None else console

        # core
        self.core = Core.Instance (lambda: core or Core ())
        if core and core != self.core:
            raise ApplicationError ('Core has already been initialized')

        # quit
        self.OnQuit  = Event ()
        if excecute:
            self.Execute ()

    #--------------------------------------------------------------------------#
    # Run                                                                      #
    #--------------------------------------------------------------------------#
    def __call__ (self): self.Execute ()
    def Execute (self):
        if self.excecuted:
            raise RuntimeError ('Application has already been run')
        self.executed = True

        # create log and logger
        self.logger = CompositeLogger (LoggerCreate () if self.console else TextLogger ())
        try:
            with CompositeDisposable ((self.logger,)) as disposable:
                #--------------------------------------------------------------#
                # Logging                                                      #
                #--------------------------------------------------------------#
                disposable.Add (self.log.Subscribe (self.logger))
                if self.log_file:
                    try:
                        log_stream = open (self.log_file, 'a+')
                        disposable.Add (log_stream)
                        disposable.Add (self.Logger.Subscribe (TextLogger (log_stream)))
                    except IOError as error:
                        self.log.Error ('Failed to open log file \'{}\': {}'.format (self.log_file, error.strerror))

                #--------------------------------------------------------------#
                # Main                                                         #
                #--------------------------------------------------------------#
                try:
                    main_result = self.main (self)
                    if isinstance (main_result, Future):
                        with self.core:
                            self.Watch (main_result, name = self.name, critical = True)
                            self.core.Execute ()
                finally:
                    self.OnQuit (self)
        finally:
            self.logger, self.log = None, None

    #--------------------------------------------------------------------------#
    # Watch                                                                    #
    #--------------------------------------------------------------------------#
    def Watch (self, future, name = None, critical = False):
        """Watch over future"""
        def watch_continuation (future):
            try:
                return future.Result ()

            except Exception:
                # header
                self.log.Error (String (('UNNAMED' if name is None else name, '17'), ' has terminated with error:'))

                # error
                stream = string_type ()
                Result.PrintException (*sys.exc_info (), file = stream)

                # output
                stream.seek (0)
                for line in stream:
                    self.log.Error (line.rstrip ('\n'))

                raise

            finally:
                if critical:
                    self.core.Dispose ()

        return future.Continue (watch_continuation)

    #--------------------------------------------------------------------------#
    # Properties                                                               #
    #--------------------------------------------------------------------------#
    Name   = property (lambda self: self.name)
    Core   = property (lambda self: self.core)
    Log    = property (lambda self: self.log)
    Logger = property (lambda self: self.logger)

# vim: nu ft=python columns=120 :
