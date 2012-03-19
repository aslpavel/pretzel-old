# -*- coding: utf-8 -*-
import sys

__all__ = ('Exec', 'Raise')
#------------------------------------------------------------------------------#
# Exec and Raise                                                               #
#------------------------------------------------------------------------------#
if sys.version_info [0] > 2:
    import builtins
    Exec = getattr (builtins, "exec")
    del builtins

    def Raise (tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback (tb)
        raise value
else:
    def Exec (code, globs=None, locs=None):
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

    Exec ("""def Raise (tp, value, tb=None):
        raise tp, value, tb""")

# vim: nu ft=python columns=120 :
