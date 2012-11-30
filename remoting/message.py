# -*- coding: utf-8 -*-
import os
import struct
import itertools

from .result import Result
from ..async import Async, AsyncReturn

__all__ = ('Message',)
#------------------------------------------------------------------------------#
# Message                                                                      #
#------------------------------------------------------------------------------#
class Message (Result):
    __slots__      = Result.__slots__ + ('src', 'dst',)
    message_struct = struct.Struct ('!HH')
    uid_struct     = struct.Struct ('!I')
    uid_iter       = itertools.count ()

    def __init__ (self, dst, src = None):
        Result.__init__ (self)

        self.src = src or b'uid::' + self.uid_struct.pack (next (self.uid_iter))
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

    @classmethod
    def FromAsyncStream (cls, stream, cancel = None):
        instance = cls (b'::none', b'::none')
        return instance.LoadAsync (stream, cancel)

    @classmethod
    def FromStream (cls, stream):
        instance = cls (b'::none', b'::none')
        return instance.Load (stream)

    #--------------------------------------------------------------------------#
    # Response                                                                 #
    #--------------------------------------------------------------------------#
    def Response (self):
        return Message (self.src, self.dst)

    #--------------------------------------------------------------------------#
    # Save | Load                                                              #
    #--------------------------------------------------------------------------#
    def SaveBuffer (self, stream):
        src_end = len (self.src)
        size    = src_end + len (self.dst)
        stream.WriteBuffer (self.message_struct.pack (size, src_end) + self.src + self.dst)
        Result.SaveBuffer (self, stream)

    @Async
    def LoadAsync (self, stream, cancel = None):
        size, src_end = self.message_struct.unpack ((yield stream.ReadUntilSize (self.message_struct.size, cancel)))
        data = yield stream.ReadUntilSize (size, cancel)
        self.src, self.dst = data [:src_end], data [src_end:]

        yield Result.LoadAsync (self, stream, cancel)

        AsyncReturn (self)

    def Save (self, stream):
        src_end = len (self.src)
        size    = src_end + len (self.dst)
        stream.write (self.message_struct.pack (size, src_end) + self.src + self.dst)

        Result.Save (self, stream)

    def Load (self, stream):
        size, src_end = self.message_struct.unpack (stream.read (self.message_struct.size))
        data = stream.read (size)
        self.src, self.dst = data [:src_end], data [src_end:]

        Result.Load (self, stream)

        return self

    #--------------------------------------------------------------------------#
    # Repr                                                                     #
    #--------------------------------------------------------------------------#
    def __repr__ (self): return self.__str__ ()
    def __str__  (self):
        error  = self.Error ()
        result ='{}:{}'.format (type (error).__name__, error) if error else self.Value ()

        return '<Message [{}]: \x1b[38;01m{} -> {}\x1b[m: {}>'.format (os.getpid (), self.src, self.dst, result)

# vim: nu ft=python columns=120 :
