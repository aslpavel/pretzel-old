# -*- coding: utf-8 -*-
import os
import sys
import errno
import struct
import ctypes
import ctypes.util

from ..async import Future, FutureSource, FutureCanceled, Async, AsyncReturn, AsyncFile, Core
from ..event import Event

__all__ = ['FileMonitor']
#------------------------------------------------------------------------------#
# Inotify Implementation                                                       #
#------------------------------------------------------------------------------#
class InotifyImpl (object):
    def __init__ (self):
        libc = ctypes.CDLL (ctypes.util.find_library ('c'), use_errno = True)
        if not hasattr (libc, 'inotify_init') or \
           not hasattr (libc, 'inotify_add_watch') or \
           not hasattr (libc, 'inotify_rm_watch'):
               raise NotImplementedError ('inotify interface not implemented by libc')

        # functions
        self.inotify_init = libc.inotify_init
        self.inotify_init.argtypes = tuple ()
        self.inotify_init.restype  = ctypes.c_int

        self.inotify_add_watch = libc.inotify_add_watch
        self.inotify_add_watch.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_uint,)
        self.inotify_add_watch.restype  = ctypes.c_int

        self.inotify_rm_watch = libc.inotify_rm_watch
        self.inotify_rm_watch.argtypes  = (ctypes.c_int, ctypes.c_int,)
        self.inotify_rm_watch.restype   = ctypes.c_int

    def init (self):
        fd = self.inotify_init ()
        if fd == -1:
            errno = ctypes.get_errno ()
            raise OSError (errno, os.strerror (errno))
        return fd

    def add_watch (self, fd, path, mask):
        watch_desc = self.inotify_add_watch (fd, path.encode (sys.getfilesystemencoding ()), mask)
        if watch_desc == -1:
            errno = ctypes.get_errno ()
            raise OSError (errno, os.strerror (errno))

        return watch_desc

    def rm_watch (self, fd, wd):
        if self.inotify_rm_watch (fd, wd) != 0:
            errno = ctypes.get_errno ()
            raise OSError (errno, os.strerror (errno))

#------------------------------------------------------------------------------#
# Flags                                                                        #
#------------------------------------------------------------------------------#
inotify_flags = {
    'FM_ACCESS'       : (0x00000001, 'access'),
    'FM_MODIFY'       : (0x00000002, 'modify'),
    'FM_ATTRIB'       : (0x00000004, 'attrib'),
    'FM_CLOSE_WRITE'  : (0x00000008, 'close_write'),
    'FM_CLOSE_NOWRITE': (0x00000010, 'close_nowrite'),
    'FM_OPEN'         : (0x00000020, 'open'),
    'FM_MOVED_FROM'   : (0x00000040, 'moved_from'),
    'FM_MOVED_TO'     : (0x00000080, 'moved_to'),
    'FM_CREATE'       : (0x00000100, 'create'),
    'FM_DELETE'       : (0x00000200, 'delete'),
    'FM_DELETE_SELF'  : (0x00000400, 'delete_self'),
    'FM_MOVE_SELF'    : (0x00000800, 'move_self'),

    'FM_ONLYDIR'      : (0x01000000, 'onlydir'),
    'FM_DONT_FOLLOW'  : (0x02000000, 'dont_follow'),
    'FM_EXCL_UNLINK'  : (0x04000000, 'excl_unlink'),
    'FM_MASK_ADD'     : (0x20000000, 'mask_add'),
    'FM_ONESHOT'      : (0x80000000, 'oneshot'),

    # out only flags
    'FM_UNMOUNT'      : (0x00002000, 'unmount'),
    'FM_Q_OVERFLOW'   : (0x00004000, 'overflow'),
    'FM_IGNORED'      : (0x00008000, 'ignored'),
    'FM_ISDIR'        : (0x40000000, 'isdir'),
}

# combined flags
inotify_flags ['FM_MOVE'] = (inotify_flags ['FM_MOVED_FROM'][0] | inotify_flags ['FM_MOVED_TO'][0], 'moved')
inotify_flags ['FM_CLOSE'] = (inotify_flags ['FM_CLOSE_WRITE'][0] | inotify_flags ['FM_CLOSE_NOWRITE'][0], 'closed')

inotify_flag_to_name = {}
for name, desc in inotify_flags.items ():
    inotify_flag_to_name [desc [0]] = desc [1]
    globals () [name] = desc [0]
__all__.extend (inotify_flags)

#------------------------------------------------------------------------------#
# File Monitor                                                                 #
#------------------------------------------------------------------------------#
class FileMonitorError (Exception): pass
class FileMonitor (object):
    inotify_impl = InotifyImpl ()

    def __init__ (self, core = None):
        self.core = core or Core.Instance ()
        self.watches = {}

        self.event_struct = struct.Struct ('iIII')
        self.fd = self.inotify_impl.init ()
        self.file = AsyncFile (self.fd, core = self.core)

        self.worker_cancel = FutureSource ()
        self.worker = self.worker_main ()

    @property
    def Type (self):
        return 'inotify'

    #--------------------------------------------------------------------------#
    # Methods                                                                  #
    #--------------------------------------------------------------------------#
    def Watch (self, path, mask):
        if self.worker.IsCompleted ():
            raise FileMonitorError ('Worker is dead: {}'.format (self.worker))

        desc = self.inotify_impl.add_watch (self.fd, path, mask)
        watch = self.watches.get (desc)
        if watch is not None:
            return watch
        watch = FileMonitorWatch (self, desc, path)
        self.watches [desc] = watch
        return watch

    @staticmethod
    def FlagsToNames (flags):
        return tuple (inotify_flag_to_name [1 << bit]
            for bit in range (flags.bit_length ()) if flags & (1 << bit))

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        self.file.Dispose ()
        try: self.worker_cancel.ResultSet (None)
        except FutureCanceled:
            pass

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def worker_main (self):
        cancel = self.worker_cancel.Future
        try:
            event_size = self.event_struct.size
            while True:
                # receive
                event_data = yield self.file.ReadExactly (event_size, cancel)
                watch_desc, mask, cookie, name_length = self.event_struct.unpack (event_data)
                if name_length > 0:
                    name = (yield self.file.ReadExactly (name_length, cancel)).rstrip (b'\x00').decode ()
                else:
                    name = ''

                # process
                watch = self.watches.get (watch_desc)
                if watch is None:
                    continue
                watch.OnChanged (watch, mask, cookie, name)

        finally:
            # dispose watches
            watches, self.watches = self.watches, {}
            for watch in watches.values ():
                watch.Dispose ()

#------------------------------------------------------------------------------#
# File Monitor Watch                                                           #
#------------------------------------------------------------------------------#
class FileMonitorWatch (object):
    def __init__ (self, monitor, desc, path):
        self.monitor = monitor
        self.desc    = desc
        self.path    = path

        self.disposed = False
        self.OnChanged = Event ()
        self.OnDeleted = Event ()

    #--------------------------------------------------------------------------#
    # Methods                                                                  #
    #--------------------------------------------------------------------------#
    def Update (self, mask):
        if self.disposed is True:
            raise FileMonitorError ('Watch is deleted')

    @Async
    def Changed (self):
        changed, deleted = self.OnChanged.Await (), self.OnDeleted.Await ()
        future = yield Future.WhenAny ((changed, deleted))
        if future is deleted:
            raise FileMonitorError ('Watch has been deleted')

        AsyncReturn (changed.Result ())

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        if not self.disposed:
            self.disposed = True
            try:
                self.monitor.watches.pop (self.desc, None)
                self.monitor.inotify_impl.rm_watch (self.monitor.fd, self.desc)
            except OSError as error:
                # watch has been removed by ignore event
                if error.errno != errno.EINVAL:
                    raise
            finally:
                self.OnDeleted (self)

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

# vim: nu ft=python columns=120 :
