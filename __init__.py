# -*- coding: utf-8 -*-

__all__ = []
#------------------------------------------------------------------------------#
# Load Test Protocol                                                           #
#------------------------------------------------------------------------------#
def load_tests (loader, tests, pattern):
    from unittest import TestSuite
    from . import tests
    from . import async
    from . import udb
    from . import log
    from . import remoting
    from . import observer

    suite = TestSuite ()
    for test in (tests, async, log, udb, remoting, observer):
        suite.addTests (loader.loadTestsFromModule (test))

    return suite
# vim: nu ft=python columns=120 :
