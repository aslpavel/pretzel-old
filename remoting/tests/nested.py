# -*- coding: utf-8 -*-
import os
import unittest

from ..domains.fork import ForkDomain
from ...async import Async, AsyncReturn, Core

__all__ = ('NestedDomainTest',)
#------------------------------------------------------------------------------#
# Nested Domain Test                                                           #
#------------------------------------------------------------------------------#
class NestedDomainTest (unittest.TestCase):
    def test (self):
        @Async
        def run ():
            with ForkDomain (push_main = False) as domain:
                yield domain.Connect ()

                this_pid   = os.getpid ()
                remote_pid = yield domain.Call (os.getpid)
                nested_pid = yield Unwrap (domain.Call (Nested, os.getpid))

                self.assertNotEqual (this_pid, remote_pid)
                self.assertNotEqual (this_pid, nested_pid)
                self.assertNotEqual (remote_pid, nested_pid)

        with Core.Instance () as core:
            run_future = run ()
            run_future.Continue (lambda _: core.Dispose ())
            core ()

        run_future.Result ()

#------------------------------------------------------------------------------#
# Helpers                                                                      #
#------------------------------------------------------------------------------#
def Nested (func, *args, **keys):
    def nested ():
        with ForkDomain (push_main = False) as domain:
            yield domain.Connect ()
            AsyncReturn ((yield domain.Call (func, *args, **keys)))
    return Async (nested) ()

@Async
def Unwrap (future):
    AsyncReturn ((yield ((yield future))))

# vim: nu ft=python columns=120 :
