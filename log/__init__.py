# -*- coding: utf-8 -*-
from .string import *
from .log import *
from .logger import *

__all__ = ('Log', 'ConsoleLogger', 'TextLogger', 'LoggerCreate', 'String')
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
