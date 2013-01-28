# -*- coding: utf-8 -*-

__all__ = []
#------------------------------------------------------------------------------#
# Load Test Protocol                                                           #
#------------------------------------------------------------------------------#
def load_tests (loader, tests, pattern):
    from unittest import TestSuite
    from . import tests
    from . import async
    from . import store
    from . import log
    from . import remoting
    from . import observer
    from . import fs

    suite = TestSuite ()
    for test in (tests, async, log, store, remoting, observer, fs):
        suite.addTests (loader.loadTestsFromModule (test))

    return suite

#------------------------------------------------------------------------------#
# Load Benchmarks Protocol                                                     #
#------------------------------------------------------------------------------#
def load_bench (runner):
    from . import remoting_next

    for module in (remoting_next,):
        runner.AddModule (remoting_next)

# vim: nu ft=python columns=120 :
