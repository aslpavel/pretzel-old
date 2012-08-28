# -*- coding: utf-8 -*-
import os
import struct
import itertools

from .result import Result
from ..async import Async, AsyncReturn, DummyAsync

__all__ = ('Message',)
#------------------------------------------------------------------------------#
# Message                                                                      #
#------------------------------------------------------------------------------#
class Message (Result):
    __slots__     = Result.__slots__ + ('src', 'dst',)
    header_struct = struct.Struct ('!IHH')
    uid_struct    = struct.Struct ('!I')
    uid_iter      = itertools.count ()

    def __init__ (self, dst, src = None):
        Result.__init__ (self)

        self.src = b'uid::' + self.uid_struct.pack (next (self.uid_iter)) if src is None else src
        self.dst = dst

    #--------------------------------------------------------------------------#
    # Factories                                                                #
    #--------------------------------------------------------------------------#
    @classmethod
    def FromValue (cls, value, dst, src = None):
        instance = cls (dst, src)
        instance.ValueSet (value)
        return instance

    @classmethod
    def FromError (cls, error, dst, src = None):
        instance = cls (dst, src)
        instance.ErrorSet (error)
        return instance

    #--------------------------------------------------------------------------#
    # Response                                                                 #
    #--------------------------------------------------------------------------#
    def Response (self):
        return Message (self.src, self.dst)

    #--------------------------------------------------------------------------#
    # Save | Load                                                              #
    #--------------------------------------------------------------------------#
    @DummyAsync
    def SaveAsync (self, stream):
        result  = Result.Save (self)

        src_end = len (self.src)
        dst_end = src_end + len (self.dst)
        size    = dst_end + len (result)

        stream.Write (self.header_struct.pack (size, src_end, dst_end) + self.src + self.dst + result)

    @classmethod
    @Async
    def LoadAsync (cls, stream, cancel = None):
        # header
        header = yield stream.ReadExactly (cls.header_struct.size, cancel)
        size, src_end, dst_end = cls.header_struct.unpack (header)

        # body
        body = yield stream.ReadExactly (size, cancel)
        src    = body [:src_end]
        dst    = body [src_end:dst_end]
        result = Result.Load (body [dst_end:])

        # instance
        instance = cls (dst, src)
        instance.error     = result.error
        instance.value     = result.value
        instance.traceback = result.traceback

        AsyncReturn (instance)

    def Save (self, stream):
        result  = Result.Save (self)

        src_end = len (self.src)
        dst_end = src_end + len (self.dst)
        size    = dst_end + len (result)

        stream.write (self.header_struct.pack (size, src_end, dst_end) + self.src + self.dst + result)

    @classmethod
    def Load (cls, stream):
        # header
        size, src_end, dst_end = cls.header_struct.unpack (stream.read (cls.header_struct.size))

        # body
        body = stream.read (size)
        src    = body [:src_end]
        dst    = body [src_end:dst_end]
        result = Result.Load (body [dst_end:])

        # instance
        instance = cls (dst, src)
        instance.error     = result.error
        instance.value     = result.value
        instance.traceback = result.traceback

        return instance

    #--------------------------------------------------------------------------#
    # Repr                                                                     #
    #--------------------------------------------------------------------------#
    def __repr__ (self): return self.__str__ ()
    def __str__  (self):
        error  = self.Error ()
        result ='{}:{}'.format (type (error).__name__, error) if error else self.Value ()

        return '<Message [{}]: \x1b[38;01m{} -> {}\x1b[m: {}>'.format (os.getpid (), self.src, self.dst, result)

# vim: nu ft=python columns=120 :
