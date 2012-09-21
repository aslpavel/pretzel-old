# -*- coding: utf-8 -*-
import sys
import io
import inspect
import traceback
if sys.version_info [0] > 2:
    string_type = io.StringIO
else:
    string_type = io.BytesIO

from .async import Async, Future, Core
from .threading import ThreadPool
from .console import Text, Color, COLOR_YELLOW, ATTR_BOLD
from .log import Log

__all__ = ('Application', 'ApplicationType', 'ApplicationError',)
#------------------------------------------------------------------------------#
# Application Type                                                             #
#------------------------------------------------------------------------------#
class ApplicationError (Exception): pass
class ApplicationType  (object):
    def __init__ (self, main, name = None, core = None, pool = None, execute = None):
        self.main = main
        self.name = name

        self.core = Core.InstanceSet (core) if core else Core.Instance ()
        self.pool = ThreadPool.Instance (pool) if pool else ThreadPool.Instance ()

        # execute
        if execute is None or execute:
            self.Execute ()

    #--------------------------------------------------------------------------#
    # Properties                                                               #
    #--------------------------------------------------------------------------#
    Name = property (lambda self: self.name)
    Core = property (lambda self: self.core)
    Pool = property (lambda self: self.pool)

    #--------------------------------------------------------------------------#
    # Execute                                                                  #
    #--------------------------------------------------------------------------#
    def __call__ (self): self.Execute ()
    def Execute  (self):
        try:
            result = self.main (self)
            if isinstance (result, Future):
                result.Continue (lambda _: self.core.Dispose ())
                if not result.IsCompleted ():
                    self.core.Execute ()
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

#------------------------------------------------------------------------------#
# Application                                                                  #
#------------------------------------------------------------------------------#
def Application (name = None, core = None, pool = None):
    def application (main):
        if inspect.isgeneratorfunction (main):
            main = Async (main)
        return ApplicationType (main, name or main.__name__, core, pool, False)
    return application
# vim: nu ft=python columns=120 :
