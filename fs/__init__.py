# -*- coding: utf-8 -*-
import sys

__all__ = tuple ()
#------------------------------------------------------------------------------#
# File Monitor (Linux)                                                         #
#------------------------------------------------------------------------------#
if sys.platform.startswith ('linux'):
    from . import inotify
    from .inotify import *

    __all__ = inotify.__all__

    #--------------------------------------------------------------------------#
    # Load Test Protocol                                                       #
    #--------------------------------------------------------------------------#
    def load_tests (loader, tests, pattern):
        from unittest import TestSuite
        from . import inotify_test

        suite = TestSuite ()
        for test in (inotify_test,):
            suite.addTests (loader.loadTestsFromModule (test))

        return suite

# vim: nu ft=python columns=120 :
