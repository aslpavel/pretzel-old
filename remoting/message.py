# -*- coding: utf-8 -*-
import os
import io
import sys
import pickle

import struct
import traceback
import itertools

from ..async import *

__all__ = ('Message',)
#------------------------------------------------------------------------------#
# Message                                                                      #
#------------------------------------------------------------------------------#
MESSAGE_RESULT = 0
MESSAGE_ERROR  = 1

class Message (object):
    __slots__     = ('src', 'dst', 'data',)
    header_struct = struct.Struct ('!BHHI')
    uid_struct    = struct.Struct ('!I')
    uid_iter      = itertools.count ()
    type          = MESSAGE_RESULT

    def __init__ (self, dst, data, src = None):
        self.src = b'uid::' + self.uid_struct.pack (next (self.uid_iter)) if src is None else src
        self.dst = dst
        self.data = data

    #--------------------------------------------------------------------------#
    # Public                                                                   #
    #--------------------------------------------------------------------------#
    @property
    def Data (self):
        return self.data

    def Response (self, data):
        return Message (self.src, data, self.dst)

    def ErrorResponse (self, error):
        return ErrorMessage.FromError (self.src, error, self.dst)

    #--------------------------------------------------------------------------#
    # Save | Load                                                              #
    #--------------------------------------------------------------------------#
    @DummyAsync
    def SaveAsync (self, stream):
        src_end = len (self.src)
        dst_end = src_end + len (self.dst)
        size    = dst_end + len (self.data)

        stream.Write (self.header_struct.pack (self.type, src_end, dst_end, size) +
            self.src + self.dst + self.data)

    @classmethod
    @Async
    def LoadAsync (cls, stream):
        type, src_end, dst_end, size = cls.header_struct.unpack (
            (yield stream.ReadExactly (cls.header_struct.size)))
        body = yield stream.ReadExactly (size)

        if type == MESSAGE_RESULT:
            AsyncReturn (Message (body [src_end:dst_end], body [dst_end:], body [:src_end]))

        elif type == MESSAGE_ERROR:
            AsyncReturn (ErrorMessage (body [src_end:dst_end], body [dst_end:], body [:src_end]))

        assert False, 'Unknown message type: {}'.format (type)

    def Save (self, stream):
        src_end = len (self.src)
        dst_end = src_end + len (self.dst)
        size    = dst_end + len (self.data)

        stream.write (self.header_struct.pack (self.type, src_end, dst_end, size) +
            self.src + self.dst + self.data)

    @classmethod
    def Load (cls, stream):
        type, src_end, dst_end, size = cls.header_struct.unpack (stream.read (cls.header_struct.size))
        body = stream.read (size)

        if type == MESSAGE_RESULT:
            return Message (body [src_end:dst_end], body [dst_end:], body [:src_end])

        elif type == MESSAGE_ERROR:
            return ErrorMessage (body [src_end:dst_end], body [dst_end:], body [:src_end])

        assert False, 'Unknown message type: {}'.format (type)

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    def __str__ (self):
        return '<Message [{}]: \x1b[38;01m{} -> {}\x1b[m: {}>'\
            .format (os.getpid (), self.src, self.dst, self.data)

    def __repr__ (self):
        return slef.__str__ ()

#------------------------------------------------------------------------------#
# Error Message                                                                #
#------------------------------------------------------------------------------#
error_pattern = """
`-------------------------------------------------------------------------------
Path:  {src} -> {dst}
Error: {name}: {message}

{traceback}"""
class ErrorMessage (Message):
    __slots__ = Message.__slots__
    type      = MESSAGE_ERROR

    #--------------------------------------------------------------------------#
    # Public                                                                   #
    #--------------------------------------------------------------------------#
    @property
    def Data (self):
        info = pickle.loads (self.data)
        error_type = info ['type']
        error      = info ['error']
        traceback  = info ['traceback']

        raise error_type (error_pattern.format (
            src       = self.src,
            dst       = self.dst,
            name      = error_type.__name__,
            message   = str (error).split ('\n') [-1],
            traceback = traceback))

    @classmethod
    def FromError (cls, dst, error, src):
        traceback_stream = io.StringIO ()
        class TracebackStream (object):
            def write (self, data):
                traceback_stream.write (data.decode ('utf-8') if hasattr (data, 'decode') else data)
        traceback.print_exc (file = TracebackStream ())

        return cls (dst, pickle.dumps ({
            'type':      error [0],
            'error':     error [1],
            'message':   str (error [1]).split ('\n') [-1],
            'traceback': traceback_stream.getvalue ().strip ('\n')}), src)

# vim: nu ft=python columns=120 :
