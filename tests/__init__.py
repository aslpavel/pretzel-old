# -*- coding: utf-8 -*-

__all__ = []
#------------------------------------------------------------------------------#
# Load Test Protocol                                                           #
#------------------------------------------------------------------------------#
def load_tests (loader, tests, pattern):
    """Load test protocol
    """
    from unittest import TestSuite
    from . import process, disposable, pool

    suite = TestSuite ()
    for test in (process, disposable, pool):
        suite.addTests (loader.loadTestsFromModule (test))
    return suite

# vim: nu ft=python columns=120 :
