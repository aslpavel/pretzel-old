# -*- coding: utf-8 -*-
import sys
import io
import traceback

from . import async
from .log import *
from .async import *
from .disposable import *

__all__ = async.__all__ + ('Application',)
#------------------------------------------------------------------------------#
# Application                                                                  #
#------------------------------------------------------------------------------#
class Application (object):
    def __init__ (self, main, name = None, run = True, log_file = None, console = None, core = None):
        """Application Object

        Options:
            name:     application name
            run:      run application immediately
            log_file: use log file
            console:  try to use console logger first
        """
        self.main   = main
        self.name   = main.__name__ if name is None else name
        self.log_file = log_file
        self.runned = False

        self.log     = Log (name)
        self.logger  = None
        self.core    = Core () if core is None else core
        self.console = True if console is None else console

        if run:
            self.Run ()

    #--------------------------------------------------------------------------#
    # Run                                                                      #
    #--------------------------------------------------------------------------#
    def Run (self):
        if self.runned:
            raise RuntimeError ('Application has already been run')
        self.runned = True

        # create log and logger
        self.logger = CompositeLogger (LoggerCreate () if self.console else TextLogger ())
        try:
            with CompositeDisposable (self.logger) as disposable:
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
                main_result = self.main (self)
                if isinstance (main_result, BaseFuture):
                    with self.core:
                        self.core.Sleep (1 << 27) # ~ 100 Years (keeps core running until main is resolved)
                        self.Watch (main_result, name = self.name, critical = True)
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
                error_stream = stream_type ()
                traceback.print_exc (file = error_stream)
                self.log.Error (String (('UNNAMED' if name is None else name, '17'), ' has terminated with error:'))
                error_stream.seek (0)
                for line in error_stream:
                    self.log.Error (line.rstrip ('\n'))
                raise

            finally:
                if critical:
                    self.core.Stop ()

        return future.Continue (watch_continuation)

    #--------------------------------------------------------------------------#
    # Properties                                                               #
    #--------------------------------------------------------------------------#
    Name   = property (lambda self: self.name)
    Core   = property (lambda self: self.core)
    Log    = property (lambda self: self.log)
    Logger = property (lambda self: self.logger)

stream_type = io.BytesIO if sys.version_info [0] < 3 else io.StringIO
# vim: nu ft=python columns=120 :
