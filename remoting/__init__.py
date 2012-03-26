# -*- coding: utf-8 -*-
from .domains.ssh import SSHDomain
from .domains.fork import ForkDomain
from .domains.daemon import DaemonDomain
from .utils.fork import *

__all__ = ('SSHDomain', 'ForkDomain', 'DaemonDomain', 'Fork')
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
