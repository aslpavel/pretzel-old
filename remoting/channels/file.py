# -*- coding: utf-8 -*-
import io
import struct
import pickle

from .channel import *
from ...async import *

__all__ = ('FileChannel',)
#-----------------------------------------------------------------------------#
# File Channel                                                                #
#-----------------------------------------------------------------------------#
class FileChannel (PersistenceChannel):
    def __init__ (self, core):
        PersistenceChannel.__init__ (self, core)
        self.header = struct.Struct ('!III')

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
    # Run                                                                      #
    #--------------------------------------------------------------------------#
    @Async
    def Run (self):
        if self.in_file is None or self.out_file is None:
            raise ValueError ('Either in or out file is not set')

        # close files on stop
        def close_files ():
            self.in_file.Dispose ()
            self.out_file.Dispose ()
        self.OnStop += close_files

        yield PersistenceChannel.Run (self)

    #--------------------------------------------------------------------------#
    # Channel Interface                                                        #
    #--------------------------------------------------------------------------#
    @Async
    def RecvMsg (self):
        # receive header
        header = yield self.in_file.ReadExactly (self.header.size)

        # receive body
        size, port, uid = self.header.unpack (header)
        stream = io.BytesIO ()
        yield self.in_file.ReadExactlyInto (size, stream)
        stream.seek (0)
        AsyncReturn ((port, uid, lambda: self.unpickler_type (stream).load ()))

    def SendMsg (self, message):
        if not self.recv_worker:
            return RaisedFuture (ChannelError ('Connection is closed'))

        stream = io.BytesIO ()

        # data
        stream.seek (self.header.size)
        self.pickler_type (stream, -1).dump (message)

        # header
        size = stream.tell () - self.header.size
        stream.seek (0)
        stream.write (self.header.pack (size, message.port, message.uid))

        self.out_file.WriteNoWait (stream.getvalue ())

# vim: nu ft=python columns=120 :
