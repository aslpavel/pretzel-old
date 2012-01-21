# -*- coding: utf-8 -*-
from . import async
from .async import *
__all__ = async.__all__

from .domains.ssh import *
from .domains.fork import *
__all__ += ('SSHDomain', 'ForkDomain')

# information
__author__ = 'Pavel Aslanov'
__version__ = '1.0'

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
