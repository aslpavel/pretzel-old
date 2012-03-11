# -*- coding: utf-8 -*-
from .string import *
from .logger import *
from .log import *

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
