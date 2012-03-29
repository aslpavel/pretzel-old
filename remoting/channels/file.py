# -*- coding: utf-8 -*-
import io
import struct
import pickle
import binascii

from .channel import *
from ...async import *

__all__ = ('FileChannel',)
#-----------------------------------------------------------------------------#
# File Channel                                                                #
#-----------------------------------------------------------------------------#
class FileChannel (PersistenceChannel):
    def __init__ (self, core):
        PersistenceChannel.__init__ (self, core)
        self.header = struct.Struct ('!IIII')

        # files
        self.in_file = None
        self.out_file = None

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

    #--------------------------------------------------------------------------#
    # Run Implementation                                                       #
    #--------------------------------------------------------------------------#
    @Async
    def run (self):
        if self.in_file is None or self.out_file is None:
            raise ValueError ('Either in or out file is not set')

        # close files on stop
        @DummyAsync
        def close_files ():
            self.in_file.Dispose ()
            self.out_file.Dispose ()
        self.OnStop += close_files

        yield PersistenceChannel.run (self)

    #--------------------------------------------------------------------------#
    # Channel Interface                                                        #
    #--------------------------------------------------------------------------#
    @Async
    def RecvMsg (self):
        # receive header
        header = yield self.in_file.ReadExactly (self.header.size)
        size, port, uid, checksum = self.header.unpack (header)

        # receive body
        stream = io.BytesIO ()
        yield self.in_file.ReadExactlyInto (size, stream)
        if (binascii.crc32 (stream.getvalue ()) & 0xffffffff) != checksum:
            raise ChannelError ('Checksum error')
        stream.seek (0)

        AsyncReturn ((port, uid, lambda: self.unpickler_type (stream).load ()))

    @DummyAsync
    def SendMsg (self, message):
        if not self.recv_worker:
            raise ChannelError ('Connection is closed')

        # message dump
        stream = io.BytesIO ()
        self.pickler_type (stream, -1).dump (message)
        data  = stream.getvalue ()
        header = self.header.pack (len (data), message.port, message.uid, binascii.crc32 (data) & 0xffffffff)

        self.out_file.WriteNoWait (header + data)

# vim: nu ft=python columns=120 :
