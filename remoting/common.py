# -*- coding: utf-8 -*-
import sys, os
import fcntl
import traceback

#-----------------------------------------------------------------------------#
# Disposable                                                                  #
#-----------------------------------------------------------------------------#
class Disposable (object):
    __slots__ = ('dispose')
    def __init__ (self, dispose = None):
        self.dispose = dispose

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        if self.dispose is not None:
            self.dispose ()
            self.dispose = None
        return False

    def __bool__ (self):
        return self.dispose is not None

    def Dispse (self):
        if self.dispose is not None:
            self.dispose ()
            self.dispose = None

#-----------------------------------------------------------------------------#
# Event                                                                       #
#-----------------------------------------------------------------------------#
class Event (object):
    """Simple Event implementation"""
    def __init__ (self):
        self.__handlers = set ()

    def __call__ (self, *args, **keys):
        for handler in self.__handlers:
            handler (*args, **keys)

    def __iadd__ (self, handler):
        self.__handlers.add (handler)
        return self

    def __isub__ (self, handler):
        self.__handlers.discard (handler)
        return self

#-----------------------------------------------------------------------------#
# Bind Pool                                                                   #
#-----------------------------------------------------------------------------#
class BindPool (dict):
    """Bind key to value and return unbinder (Disposable)"""

    def Bind (self, key, value):
        if self.get (key) is not None:
            raise ValueError ('\'{0}\' has already been bound'.format (key))
        self [key] = value
        return Disposable (lambda : self.pop (key))

#-----------------------------------------------------------------------------#
# Blocking                                                                    #
#-----------------------------------------------------------------------------#
def BlockingSet (fd, enabled = True):
    """Change blocking flag for descriptor"""

    flags = fcntl.fcntl (fd, fcntl.F_GETFL)
    if enabled:
        flags &= ~os.O_NONBLOCK
    else:
        flags |= os.O_NONBLOCK
    fcntl.fcntl (fd, fcntl.F_SETFL, flags)
    return flags

#-----------------------------------------------------------------------------#
# Fork                                                                        #
#-----------------------------------------------------------------------------#
def Fork (future, tag = None):
    """Treat future as coroutine"""
    def finished (future):
        try: return future.Result ()
        except Exception:
            if tag is not None:
                sys.stderr.write (' {0} '.format (tag).center (80, '-') + '\n')
            traceback.print_exc (file = sys.stderr)
            sys.stderr.flush ()
            raise
    return future.Continue (finished)

# vim: nu ft=python columns=120 :
