# -*- coding: utf-8 -*-
import os
import sys
import struct
import ctypes
import ctypes.util

from ..async import *
from ..event import *

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
        self.libc = libc

    def init (self):
        fd = self.libc.inotify_init ()
        if fd == -1:
            errno = ctypes.get_errno ()
            raise OSError (errno, os.strerror (errno))
        return fd

    def add_watch (self, fd, path, mask):
        assert isinstance (path, str)
        assert (isinstance (fd, int) and fd >= 0)
        assert (isinstance (mask, int) and mask > 0)

        watch_desc = self.libc.inotify_add_watch (fd, path.encode (sys.getfilesystemencoding ()), mask)
        if watch_desc == -1:
            errno = ctypes.get_errno ()
            raise OSError (errno, os.strerror (errno))

        return watch_desc

    def rm_watch (self, fd, wd):
        assert (isinstance (fd, int) and fd >= 0)
        assert (isinstance (wd, int) and wd >= 0)

        if self.libc.inotify_rm_watch (fd, wd) != 0:
            errno = ctypes.get_errno ()
            raise OSError (errno, os.strerror (errno))

#------------------------------------------------------------------------------#
# Flags                                                                        #
#------------------------------------------------------------------------------#
flags = {
    'IN_ACCESS'       : (0x00000001, 'file was accessed'),
    'IN_MODIFY'       : (0x00000002, 'file was modified'),
    'IN_ATTRIB'       : (0x00000004, 'metadata changed'),
    'IN_CLOSE_WRITE'  : (0x00000008, 'writable file was closed'),
    'IN_CLOSE_NOWRITE': (0x00000010, 'unwritable file closed'),
    'IN_OPEN'         : (0x00000020, 'file was opened'),
    'IN_MOVED_FROM'   : (0x00000040, 'file was moved from X'),
    'IN_MOVED_TO'     : (0x00000080, 'file was moved to Y'),
    'IN_CREATE'       : (0x00000100, 'subfile was created'),
    'IN_DELETE'       : (0x00000200, 'subfile was deleted'),
    'IN_DELETE_SELF'  : (0x00000400, 'self was deleted'),
    'IN_MOVE_SELF'    : (0x00000800, 'self was moved'),

    'IN_ONLYDIR'      : (0x01000000, 'only watch the path if it is a directory'),
    'IN_DONT_FOLLOW'  : (0x02000000, 'don\'t follow a sym link'),
    'IN_EXCL_UNLINK'  : (0x04000000, 'exclude events on unlinked objects'),
    'IN_MASK_ADD'     : (0x20000000, 'add to the mask of an already existing watch'),
    'IN_ONESHOT'      : (0x80000000, 'only send event once'),

    # out only flags
    'IN_UNMOUNT'      : (0x00002000, 'backing fs was unmounted'),
    'IN_Q_OVERFLOW'   : (0x00004000, 'event queued overflowed'),
    'IN_IGNORED'      : (0x00008000, 'file was ignored'),
    'IN_ISDIR'        : (0x40000000, 'event occurred against dir'),
}

# combined flags
flags ['IN_MOVE'] = (flags ['IN_MOVED_FROM'][0] | flags ['IN_MOVED_TO'][0], 'file was moved')
flags ['IN_CLOSE'] = (flags ['IN_CLOSE_WRITE'][0] | flags ['IN_CLOSE_NOWRITE'][0], 'file was closed')

for name, desc in flags.items ():
    globals () [name] = desc [0]
__all__.extend (flags)

#------------------------------------------------------------------------------#
# File Monitor                                                                 #
#------------------------------------------------------------------------------#
class FileMonitorError (Exception): pass
class FileMonitor (object):
    inotify_impl = InotifyImpl ()

    def __init__ (self, core):
        self.core = core
        self.watches = {}

        self.event_struct = struct.Struct ('iIII')
        self.fd = self.inotify_impl.init ()
        self.file = core.AsyncFileCreate (self.fd)
        self.worker = self.worker_main ()

    @property
    def Type (self):
        return 'inotify'

    #--------------------------------------------------------------------------#
    # Methods                                                                  #
    #--------------------------------------------------------------------------#
    def Watch (self, path, mask = None):
        if self.worker is None or self.worker.IsCompleted ():
            raise FileMonitorError ('worker is dead')

        desc = self.inotify_impl.add_watch (self.fd, path, mask)
        watch = self.watches.get (desc)
        if watch is not None:
            return watch
        watch = FileMonitorWatch (self, desc, path)
        self.watches [desc] = watch
        return watch
    
    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        self.file.Dispose ()
        if self.worker is not None:
            try: self.worker.Dispose ()
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
        try:
            event_size = self.event_struct.size
            while True:
                # receive
                event_data = yield self.file.ReadExactly (event_size)
                watch_desc, mask, cookie, name_length = self.event_struct.unpack (event_data)
                if name_length > 0:
                    name = (yield self.file.ReadExactly (name_length)).rstrip (b'\x00').decode ()
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
        self.desc = desc
        self.path = path
        self.disposed = False

        self.OnChanged = Event ()
        self.OnDeleted = Event ()

    #--------------------------------------------------------------------------#
    # Methods                                                                  #
    #--------------------------------------------------------------------------#
    def Update (self, mask):
        if slef.disposed is True:
            raise FileMonitorError ('Watch is deleted')

    @Async
    def Changed (self):
        changed, deleted = self.OnChanged.Await (), self.OnDeleted.Await ()
        future = yield AnyFuture (changed, deleted)
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
            finally:
                self.OnDeleted (self)
    
    def __enter__ (self):
        return self
    
    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

# vim: nu ft=python columns=120 :
