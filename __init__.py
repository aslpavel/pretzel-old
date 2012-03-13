# -*- coding: utf-8 -*-

#------------------------------------------------------------------------------#
# Load Test Protocol                                                           #
#------------------------------------------------------------------------------#
def load_tests (loader, tests, pattern):
    from unittest import TestSuite

    from . import async
    from . import udb
    from . import log
    from . import remoting

    suite = TestSuite ()
    for test in (async, log, udb, remoting):
        suite.addTests (loader.loadTestsFromModule (test))

    return suite
# vim: nu ft=python columns=120 :
