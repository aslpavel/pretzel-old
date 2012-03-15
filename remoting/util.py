# -*- coding: utf-8 -*-
import sys, os
import fcntl
import traceback
from ..disposable import *

__all__ = ('BindPool', 'Fork', 'exec_', 'reraise')

#------------------------------------------------------------------------------#
# Bind Pool                                                                    #
#------------------------------------------------------------------------------#
class BindPool (dict):
    """Bind key to value and return unbinder (Disposable)"""

    def Bind (self, key, value):
        if self.get (key) is not None:
            raise ValueError ('\'{0}\' has already been bound'.format (key))
        self [key] = value
        return Disposable (lambda : self.pop (key))

#------------------------------------------------------------------------------#
# Fork                                                                         #
#------------------------------------------------------------------------------#
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

#------------------------------------------------------------------------------#
# exec_ and reraise                                                            #
#------------------------------------------------------------------------------#
if sys.version_info [0] > 2:
    import builtins
    exec_ = getattr (builtins, "exec")
    del builtins

    def reraise (tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback (tb)
        raise value
else:
    def exec_ (code, globs=None, locs=None):
        """Execute code in a namespace."""
        if globs is None:
            frame = sys._getframe (1)
            globs = frame.f_globals
            if locs is None:
                locs = frame.f_locals
            del frame
        elif locs is None:
            locs = globs
        exec ("""exec code in globs, locs""")

    exec_ ("""def reraise (tp, value, tb=None):
        raise tp, value, tb""")

# vim: nu ft=python columns=120 :
