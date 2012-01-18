# -*- coding: utf-8 -*-
import os
import io
import errno
import struct
import pickle

from ..async import *
from ..util import *
from .channel import *

__all__ = ('FileChannel',)

#-----------------------------------------------------------------------------#
# File Channel                                                                #
#-----------------------------------------------------------------------------#
class FileChannel (PersistenceChannel):
    def __init__ (self, core, in_fd, out_fd):
        self.disposed = False

        # non blocking
        self.in_fd, self.out_fd = in_fd, out_fd
        BlockingSet (in_fd, False)
        if in_fd != out_fd:
            BlockingSet (out_fd, False)

        self.header = struct.Struct ('!III')
        self.OnDispose = Event ()

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

        PersistenceChannel.__init__ (self, core)

    @Async
    def RecvMsg (self):
        if self.disposed:
            raise ChanneldError ('connection is closed')

        # recv header
        header = yield self.read (self.header.size)
        if len (header) == 0:
            AsyncReturn (None)

        # recv body
        size, port, uid = self.header.unpack (header)
        data = io.BytesIO ()
        while data.tell () < size:
            chunk = yield self.read (size - data.tell ())
            if len (chunk) == 0:
                raise ChannelError ('connection has been closed unexpectedly')
            data.write (chunk)

        data.seek (0)
        AsyncReturn ((port, uid, lambda: self.unpickler_type (data).load ()))

    def SendMsg (self, message):
        if self.disposed:
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

    def Dispose (self):
        self.disposed = True
        self.OnDispose ()

    @Async
    def write (self, data):
        '''
        try:
            AsyncReturn (os.write (self.out_fd, data))
        except OSError as err:
            if err.errno != errno.EAGAIN:
                raise
        '''

        yield self.core.Poll (self.out_fd, self.core.WRITABLE)
        AsyncReturn (os.write (self.out_fd, data))

    @Async
    def read (self, size):
        '''
        try:
            AsyncReturn (os.read (self.in_fd, size))
        except OSError as err:
            if err.errno != errno.EAGAIN:
                raise
        '''

        try:
            yield self.core.Poll (self.in_fd, self.core.READABLE)
            AsyncReturn (os.read (self.in_fd, size))
        except CoreHUPError:
            AsyncReturn (b'')

# vim: nu ft=python columns=120 :
