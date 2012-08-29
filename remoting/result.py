# -*- coding: utf-8 -*-
import os
import io
import sys
import socket

from traceback import format_exception
if sys.version_info [0] > 2:
    import pickle
    string_type = io.StringIO
    PY2 = False
else:
    import cPickle as pickle
    string_type = io.BytesIO
    PY2 = True

__all__ = ('Result',)
#------------------------------------------------------------------------------#
# Result                                                                       #
#------------------------------------------------------------------------------#
class ResultReturn (BaseException): pass
class Result (object):
    __slots__ = ('value', 'error', 'traceback',)
    hostname  = socket.gethostname ()
    pid       = os.getpid ()
    value_tag = b'0' [0]

    def __init__ (self):
        self.value     = None
        self.error     = None
        self.traceback = None

    #--------------------------------------------------------------------------#
    # Factories                                                               #
    #--------------------------------------------------------------------------#
    @classmethod
    def FromError (cls, error):
        instance = cls ()
        instance.ErrorSet (error)
        return instance

    @classmethod
    def FromValue (cls, value):
        instance = cls ()
        instance.ValueSet (value)
        return instance

    #--------------------------------------------------------------------------#
    # Return                                                                   #
    #--------------------------------------------------------------------------#
    def __call__ (self, result = None): return self.Return (result)
    def Return   (self, result = None):
        raise ResultReturn (result)

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        if et is not None:
            if et is ResultReturn:
                self.ValueSet (eo.args [0])
            else:
                self.ErrorSet ((et, eo, tb))
        return True

    #--------------------------------------------------------------------------#
    # Resolve                                                                  #
    #--------------------------------------------------------------------------#
    def Value (self):
        if self.error is None:
            return self.value
        else:
            raise self.error

    def ValueSet (self, value):
        self.value = value

    def Error (self):
        return self.error

    def ErrorSet (self, error):
        # traceback
        traceback = traceback_template.format (
                hostname  = self.hostname,
                pid       = self.pid,
                name      = error [0].__name__,
                message   = str (error [1]),
                traceback = ''.join (format_exception (*error)))

        # saved traceback
        traceback_saved = getattr (error [1], '_saved_traceback', None)
        if traceback_saved is not None:
            traceback += traceback_saved

        # error
        error = error [1]
        error._saved_traceback = traceback

        self.error     = error
        self.traceback = traceback

    def Traceback (self):
        return self.traceback

    #--------------------------------------------------------------------------#
    # Print Exception                                                          #
    #--------------------------------------------------------------------------#
    @staticmethod
    def PrintException (et, eo, tb, file = None):
        stream = file or string_type ()

        # traceback
        traceback = ''.join (format_exception (et, eo, tb))
        stream.write (traceback.encode ('utf-8') if PY2 else traceback)

        # saved traceback
        traceback_saved = getattr (eo, '_saved_traceback', None)
        if traceback_saved is not None:
            stream.write (traceback_saved)

        # flush
        stream.flush ()

        # output
        if file is None:
            sys.stderr.write (stream.getvalue ())
            sys.stderr.flush ()

    #--------------------------------------------------------------------------#
    # Save | Load                                                              #
    #--------------------------------------------------------------------------#
    def Save (self):
        if self.error is None:
            return b'0' + (b'' if self.value is None else self.value)
        else:
            try:
                return b'1' + pickle.dumps ((self.error, self.traceback))
            except Exception:
                return b'1' + pickle.dumps ((type (self.error) ('Failed to pack arguments'), self.traceback))

    @classmethod
    def Load (cls, data):
        result = cls ()

        if data [0] == cls.value_tag:
            result.value = data [1:] if len (data) > 1 else None
        else:
            error, traceback = pickle.loads (data [1:])
            error._saved_traceback = traceback

            result.error     = error
            result.traceback = traceback

        return result

#------------------------------------------------------------------------------#
# Saved Traceback Template                                                     #
#------------------------------------------------------------------------------#
traceback_template = """
`-------------------------------------------------------------------------------
Location : {hostname}/{pid}
Error    : {name}: {message}

{traceback}"""

#------------------------------------------------------------------------------#
# Exception Hook                                                               #
#------------------------------------------------------------------------------#
sys.excepthook = Result.PrintException

# vim: nu ft=python columns=120 :
