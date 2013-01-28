# -*- coding: utf-8 -*-
from . import hub, proxy, conn

from .hub import *
from .proxy import *
from .conn import *

__all__ = hub.__all__ + proxy.__all__ + conn.__all__
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

#------------------------------------------------------------------------------#
# Load Benchmark Protocol                                                      #
#------------------------------------------------------------------------------#
def load_bench (benchs):
    from . import benchmark
    benchmark.load_bench (benchs)

# vim: nu ft=python columns=120 :
