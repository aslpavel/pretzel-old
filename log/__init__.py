# -*- coding: utf-8 -*-
from .log    import Log
from .logger import TextLogger, ConsoleLogger, LoggerCreate, CompositeLogger
from .string import String

__all__ = ('Log', 'ConsoleLogger', 'TextLogger', 'LoggerCreate', 'CompositeLogger', 'String')
#------------------------------------------------------------------------------#
# Load Test Protocol                                                           #
#------------------------------------------------------------------------------#
def load_tests (loader, tests, pattern):
    from unittest import TestSuite
    from . import tests

    suite = TestSuite ()
    for test in (tests,):
        suite.addTests (loader.loadTestsFromModule (test))

    return suite

# vim: nu ft=python columns=120 :