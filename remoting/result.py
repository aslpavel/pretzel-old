# -*- coding: utf-8 -*-
import os
import io
import sys
import socket
import struct

from traceback import format_exception
if sys.version_info [0] > 2:
    import pickle
    string_type = io.StringIO
    PY2 = False
else:
    import cPickle as pickle
    string_type = io.BytesIO
    PY2 = True

from ..async import Async, AsyncReturn

__all__ = ('Result',)
#------------------------------------------------------------------------------#
# Result                                                                       #
#------------------------------------------------------------------------------#
class ResultReturn (BaseException): pass
class Result (object):
    __slots__ = ('value', 'error', 'traceback',)
    hostname      = socket.gethostname ()
    pid           = os.getpid ()
    result_struct = struct.Struct ('!BI')

    def __init__ (self):
        self.value     = None
        self.error     = None
        self.traceback = None

    #--------------------------------------------------------------------------#
    # Factories                                                                #
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

    @classmethod
    def FromBytes (cls, data):
        stream   = io.BytesIO (data)
        instance = cls ()
        instance.Load (stream)
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
            elif issubclass (et, Exception):
                self.ErrorSet ((et, eo, tb))
            else:
                return False
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
    def SaveBuffer (self, stream):
        if self.error is None:
            if self.value is None:
                stream.WriteBuffer (self.result_struct.pack (1, 0))
            else:
                stream.WriteBuffer (self.result_struct.pack (1, len (self.value)))
                stream.WriteBuffer (self.value)
        else:
            try:
                error_value = pickle.dumps ((self.error, self.traceback))
            except Exception:
                error_value = pickle.dumps ((type (self.error) ('Failed to pack arguments'), self.traceback))

            stream.WriteBuffer (self.result_struct.pack (0, len (error_value)))
            stream.WriteBuffer (error_value)

    @Async
    def LoadAsync (self, stream, cancel = None):
        is_value, size = self.result_struct.unpack ((yield stream.ReadUntilSize (self.result_struct.size, cancel)))
        data = (yield stream.ReadUntilSize (size, cancel)) if size else None

        if is_value:
            self.value = data
        else:
            error, traceback = pickle.loads (data)
            error._saved_traceback = traceback

            self.error     = error
            self.traceback = traceback

        AsyncReturn (self)

    def Save (self, stream):
        if self.error is None:
            if self.value is None:
                stream.write (self.result_struct.pack (1, 0))
            else:
                stream.write (self.result_struct.pack (1, len (self.value)))
                stream.write (self.value)
        else:
            try:
                error_value = pickle.dumps ((self.error, self.traceback))
            except Exception:
                error_value = pickle.dumps ((type (self.error) ('Failed to pack arguments'), self.traceback))

            stream.write (self.result_struct.pack (0, len (error_value)))
            stream.write (error_value)

    def Load (self, stream):
        is_value, size = self.result_struct.unpack (stream.read (self.result_struct.size))
        data = stream.read (size) if size else None

        if is_value:
            self.value = data
        else:
            error, traceback = pickle.loads (data)
            error._saved_traceback = traceback

            self.error     = error
            self.traceback = traceback

        return self

    def ToBytes (self):
        stream = io.BytesIO ()
        self.Save (stream)
        return stream.getvalue ()

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
