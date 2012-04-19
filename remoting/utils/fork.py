# -*- coding: utf-8 -*-
import sys, io, os, traceback

__all__ = ('Fork',)
#------------------------------------------------------------------------------#
# Fork                                                                         #
#------------------------------------------------------------------------------#
buffer_type = io.StringIO if sys.version_info [0] > 2 else io.BytesIO
def Fork (future, tag = None):
    """Treat future as coroutine"""
    def finished (future):
        try: return future.Result ()
        except Exception:
            error = buffer_type ()
            if tag is not None:
                error.write (' {0}:{1} '.format (tag, os.getpid ()).center (80, '-') + '\n')
            traceback.print_exc (file = error)
            os.write (sys.stderr.fileno (), error.getvalue ().encode ('utf-8'))
            raise
    return future.Continue (finished)

# vim: nu ft=python columns=120 :