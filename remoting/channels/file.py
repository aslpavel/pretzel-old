# -*- coding: utf-8 -*-
import os
import io
import sys
import struct
import pickle
import errno

from ..async import *
from ..util import *
from .channel import *

__all__ = ('FileChannel',)

#-----------------------------------------------------------------------------#
# File Channel                                                                #
#-----------------------------------------------------------------------------#
class FileChannel (PersistenceChannel):
    def __init__ (self, core, in_fd, out_fd):
        PersistenceChannel.__init__ (self, core)

        # non blocking
        self.in_fd, self.out_fd = in_fd, out_fd
        BlockingSet (in_fd, False)
        if in_fd != out_fd:
            BlockingSet (out_fd, False)

        self.header = struct.Struct ('!III')
        self.in_stream = io.open (self.in_fd, 'rb', buffering = 1 << 16, closefd = False)

        # Pickler
        class pickler_type (pickle.Pickler):
            def persistent_id (this, target):
                return self.Save (target)
        self.pickler_type = pickler_type

        # Unpickler
        class unpickler_type (pickle.Unpickler):
            def persistent_load (this, pid):
                return self.Restore (pid)
        self.unpickler_type = unpickler_type

    @Async
    def RecvMsg (self):
        if not self.IsRunning:
            raise ChannelError ('connection is closed')

        # receive header
        header = yield self.read (self.header.size)
        if not len (header):
            AsyncReturn (None)

        # receive body
        size, port, uid = self.header.unpack (header)
        data = io.BytesIO ()
        while data.tell () < size:
            chunk = yield self.read (size - data.tell ())
            if not len (chunk):
                raise ChannelError ('connection has been closed unexpectedly')
            data.write (chunk)

        data.seek (0)
        AsyncReturn ((port, uid, lambda: self.unpickler_type (data).load ()))

    def SendMsg (self, message):
        if not self.IsRunning:
            try:
                raise ChannelError ('connection is closed')
            except Exception: return FailedFuture (sys.exc_info ())

        stream = io.BytesIO ()

        # data
        stream.seek (self.header.size)
        self.pickler_type (stream, -1).dump (message)

        # header
        size = stream.tell () - self.header.size
        stream.seek (0)
        stream.write (self.header.pack (size, message.port, message.uid))

        return self.write (stream.getvalue ())

    @Async
    def write (self, data):
        try:
            data = data [os.write (self.out_fd, data):]
        except OSError as err:
            if err.errno != errno.EAGAIN:
                raise

        while len (data):
            yield self.core.Poll (self.out_fd, self.core.WRITABLE)
            data = data [os.write (self.out_fd, data):]

    @Async
    def read (self, size):
        data = self.in_stream.read (size)
        if data is not None:
            AsyncReturn (data)

        try:
            yield self.core.Poll (self.in_fd, self.core.READABLE)
            AsyncReturn (self.in_stream.read (size))
        except CoreHUPError:
            AsyncReturn (b'')

# vim: nu ft=python columns=120 :
