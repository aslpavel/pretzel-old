# -*- coding: utf-8 -*-
import os, sys, traceback

__all__ = ('Fork',)
#------------------------------------------------------------------------------#
# Fork                                                                         #
#------------------------------------------------------------------------------#
def Fork (future, tag = None):
    """Treat future as coroutine"""
    def finished (future):
        try: return future.Result ()
        except Exception:
            if tag is not None:
                sys.stderr.write (' {0}:{1} '.format (tag, os.getpid ()).center (80, '-') + '\n')
            traceback.print_exc (file = sys.stderr)
            sys.stderr.flush ()
            raise
    return future.Continue (finished)

# vim: nu ft=python columns=120 :
