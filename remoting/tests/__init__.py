# -*- coding: utf-8 -*-

__all__ = tuple ()
#------------------------------------------------------------------------------#
# Load Test Protocol                                                           #
#------------------------------------------------------------------------------#
def load_tests (loader, tests, pattern):
    from unittest import TestSuite
    from . import message
    from . import linker
    from . import future
    from . import nested

    suite = TestSuite ()
    for test in (message, linker, future, nested,):
        suite.addTests (loader.loadTestsFromModule (test))
    return suite

# vim: nu ft=python columns=120 :
