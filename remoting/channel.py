# -*- coding: utf-8 -*-
import sys

from .async import *
from .message import *
from .util import *

#-----------------------------------------------------------------------------#
# Channel                                                                     #
#-----------------------------------------------------------------------------#
class ChannelError (Exception): pass

class Channel (object):
    def __init__ (self, core):
        self.queue, self.wait, self.worker = {}, None, None
        self.ports = BindPool ()
        self.core  = core

    def BindPort (self, port, handler):
        return self.ports.Bind (port, handler)

    def Start (self):
        if self.worker is not None:
           raise ChannelError ('channel has already been started')
        self.worker = self.worker_run ()
        Fork (self.worker.Continue (self.dispose), 'channel')

    def Stop (self):
        if self.worker is None:
            return
        self.worker.Cancel ()

    # abstract
    def SendMsg (self, message):
        raise NotImplementedError ()

    def RecvMsg (self):
        raise NotImplementedError ()

    def Dispose (self):
        pass

    @Async
    def Request (self, port, **attr):
        """Asynchronous request to remote server"""
        if self.worker is None:
            raise ChannelError ('channel not started or worker is dead')

        # send message
        message = Message (port, **attr)
        yield self.sendmsg (message)

        # register future 
        future = Future (lambda: self.wait_uid (message.uid))
        self.queue [message.uid] = future

        message_getter = yield future
        yield self.core.SleepUntil (0) # guaranteed interrupt

        AsyncReturn (message_getter ())

    @Async
    def worker_run (self):
        """Process incoming messages"""
        try:
            while True:
                self.wait = self.RecvMsg ()
                message_info = yield self.wait
                if message_info is None:
                    break
                port, uid, message_getter = message_info
                if port >= PORT_SYSTEM:
                    # incoming request
                    handler = self.ports.get (port)
                    if handler is None:
                        sys.stderr.write (':: error: unbound port {0}\n'.format (port))
                        continue

                    Fork (self.handle (handler, message_getter), 'handle')
                else:
                    # system message
                    if port == PORT_RESULT:
                        self.queue.pop (uid).ResultSet (message_getter)
                    elif port == PORT_ERROR:
                        self.queue.pop (uid).ErrorSet (*message_getter ().exc_info ())
        except Exception:
            et, eo, tb = sys.exc_info ()
            for future in self.queue.values ():
                future.ErrorSet (et, eo, tb)
            if et is not FutureCanceled:
                raise
        finally:
            self.worker, self.wait = None, None

    @Async
    def handle (self, handler, message_getter):
        yield self.core.SleepUntil (0) # guaranteed interrupt

        message, error = message_getter (), None
        try:
            result = yield handler (message)
        except Exception:
            error = sys.exc_info ()

        yield self.sendmsg (result if error is None else message.Error (*error))

    def wait_uid (self, uid):
        while uid in self.queue:
            self.wait.Wait ()

    def dispose (self, future):
        self.Dispose ()
        return future.Result ()

    @Serialize
    def sendmsg (self, message):
        return self.SendMsg (message)

class PersistenceChannel (Channel):
    def __init__ (self, core):
        self.persistence = BindPool ()
        self.not_persistent = {tuple, list, dict, set, frozenset}

        Channel.__init__ (self, core)

    def BindPersistence (self, slot, save, restore):
        return self.persistence.Bind (slot, (save, restore))

    def Save (self, target):
        if type (target) in self.not_persistent:
            return None
        for slot, pair in self.persistence.items ():
            save, restore = pair
            target_id = save (target)
            if target_id is not None:
                return slot, target_id

    def Restore (self, uid):
        slot, target_id = uid
        return self.persistence [slot][1] (target_id)

'''
import struct, pickle
class SocketChannel (Channel):
    def __init__ (self, sock):
        self.sock = sock
        self.header = struct.Struct ('!I')
        self.OnDispose = Event ()

        Channel.__init__ (self)

    def SendMsg (self, message):
        stream = io.BytesIO ()
        # data
        stream.seek (self.header.size)
        pickle.dump (message, stream, -1)
        # header
        size = stream.tell () - self.header.size
        stream.seek (0)
        stream.write (self.header.pack (size))

        return self.sock.Send (stream.getvalue ())

    @Async
    def RecvMsg (self):
        # recv header
        header = yield self.sock.Recv (self.header.size)
        if len (header) == 0:
            AsyncReturn (None)

        # recv body
        size, data = self.header.unpack (header) [0], io.BytesIO () 
        while data.tell () < size:
            chunk = yield self.sock.Recv (size - data.tell ())
            if len (chunk) == 0:
                raise ChannelError ('connection has been closed unexpectedly')
            data.write (chunk)

        # unpickle message
        data.seek (0)
        AsyncReturn (pickle.load (data))

    def Dispose (self):
        self.sock.close ()
        self.OnDispose ()
'''

#-----------------------------------------------------------------------------#
# File Channel                                                                #
#-----------------------------------------------------------------------------#
import os, errno, struct, pickle

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

class SocketChannel (FileChannel):
    def __init__ (self, sock):
        self.sock = sock

        FileChannel.__init__ (self, sock.core, sock.fileno (), sock.fileno ())

# vim: nu ft=python columns=120 :
