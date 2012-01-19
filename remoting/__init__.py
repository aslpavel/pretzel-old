# -*- coding: utf-8 -*-
from .domains.ssh import SSHDomain

__all__ = ('SSHDomain',)

# load test protocol
def load_tests (loader, tests, pattern):
    from unittest import TestSuite
    from . import tests
    from . import async

    suite = TestSuite ()
    for test in (tests, async):
        suite.addTests (loader.loadTestsFromModule (test))

    return suite
# vim: nu ft=python columns=120 :
