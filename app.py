# -*- coding: utf-8 -*-
import sys
import io
import traceback
if sys.version_info [0] > 2:
    string_type = io.StringIO
else:
    string_type = io.BytesIO

from .async import Future, Core
from .console import Text, Color, COLOR_YELLOW, ATTR_BOLD
from .log import Log

__all__ = ('Application', 'ApplicationError',)
#------------------------------------------------------------------------------#
# Application                                                                  #
#------------------------------------------------------------------------------#
class ApplicationError (Exception): pass
class Application (object):
    def __init__ (self, main, name = None, execute = None, core = None):
        self.main = main
        self.name = name

        # core
        self.core = Core.Instance (lambda: core or Core ())
        if core and core != self.core:
            raise ApplicationError ('Core has already been initialized')

        # log
        if not Log.Loggers:
            Log.LoggerCreate ('console')

        # execute
        if execute is None or execute:
            self.Execute ()

    #--------------------------------------------------------------------------#
    # Properties                                                               #
    #--------------------------------------------------------------------------#
    Core = property (lambda self: self.core)
    Name = property (lambda self: self.name)

    #--------------------------------------------------------------------------#
    # Execute                                                                  #
    #--------------------------------------------------------------------------#
    def __call__ (self): self.Execute ()
    def Execute  (self):
        try:
            result = self.main (self)
            if isinstance (result, Future):
                result.Continue (lambda future: self.core.Dispose ())
                self.core ()
                return result.Result ()
            else:
                return result

        except Exception as error:
            stream = string_type ()
            traceback.print_exc (file = stream)
            traceback_saved = getattr (error, '_saved_traceback', None)
            if traceback_saved is not None:
                stream.write (traceback_saved)

            stream.seek (0)
            Log.Error (Text (('[Main]', Color (COLOR_YELLOW, None, ATTR_BOLD))), ' has terminated with error:')
            for line in stream:
                Log.Error (line.rstrip ())

        finally:
            self.Dispose ()

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        self.core.Dispose ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

# vim: nu ft=python columns=120 :
