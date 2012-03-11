# -*- coding: utf-8 -*-
from .async import *
from .observer import *
from .event import *
from .log import *
from .udb import *

#------------------------------------------------------------------------------#
# Load Test Protocol                                                           #
#------------------------------------------------------------------------------#
def load_tests (loader, tests, pattern):
    from unittest import TestSuite

    from . import async
    from . import log
    from . import udb

    suite = TestSuite ()
    for test in (async, log, udb):
        suite.addTests (loader.loadTestsFromModule (test))

    return suite
# vim: nu ft=python columns=120 :
