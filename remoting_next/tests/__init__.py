# -*- coding: utf-8 -*-

__all__ = tuple ()
#------------------------------------------------------------------------------#
# Load Test Protocol                                                           #
#------------------------------------------------------------------------------#
def load_tests (loader, tests, pattern):
    from unittest import TestSuite
    from . import hub, result, proxy, conn

    suite = TestSuite ()
    for test in (hub, result, proxy, conn,):
        suite.addTests (loader.loadTestsFromModule (test))

    return suite

# vim: nu ft=python columns=120 :
