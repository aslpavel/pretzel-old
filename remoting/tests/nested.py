# -*- coding: utf-8 -*-
import os
import unittest

from ..domains.fork import *
from ...async import *

__all__ = ('NestedDomainTest',)
#------------------------------------------------------------------------------#
# Nested Domain Test                                                           #
#------------------------------------------------------------------------------#
class NestedDomainTest (unittest.TestCase):
    def test (self):
        @Async
        def run ():
            with ForkDomain (core, push_main = False) as domain:
                yield domain.Connect ()

                this_pid   = os.getpid ()
                remote_pid = yield domain.Call (os.getpid)
                nested_pid = yield domain.Call (Nested, core, os.getpid).Unwrap ()

                self.assertNotEqual (this_pid, remote_pid)
                self.assertNotEqual (this_pid, nested_pid)
                self.assertNotEqual (remote_pid, nested_pid)

        with Core () as core:
            run_future = run ()
        run_future.Result ()

#------------------------------------------------------------------------------#
# Helpers                                                                      #
#------------------------------------------------------------------------------#
def Nested (core, func, *args, **keys):
    def nested ():
        with ForkDomain (core, push_main = False) as domain:
            yield domain.Connect ()
            AsyncReturn ((yield domain.Call (func, *args, **keys)))
    return Async (nested) ()

# vim: nu ft=python columns=120 :
