# -*- coding: utf-8 -*-
import os
import unittest

from ..domains.fork import ForkDomain
from ...async import Async, AsyncReturn
from ...async.tests import AsyncTest

__all__ = ('NestedDomainTest',)
#------------------------------------------------------------------------------#
# Nested Domain Test                                                           #
#------------------------------------------------------------------------------#
class NestedDomainTest (unittest.TestCase):
    """Test nested domain creation unit test
    """

    @AsyncTest
    def test (self):
        """Tests nested domain creation
        """
        with ForkDomain (push_main = False) as domain:
            yield domain.Connect ()

            this_pid   = os.getpid ()
            remote_pid = yield domain.Call (os.getpid)
            nested_pid = yield Unwrap (domain.Call (Nested, os.getpid))

            self.assertNotEqual (this_pid, remote_pid)
            self.assertNotEqual (this_pid, nested_pid)
            self.assertNotEqual (remote_pid, nested_pid)

#------------------------------------------------------------------------------#
# Helpers                                                                      #
#------------------------------------------------------------------------------#
def Nested (func, *args, **keys):
    """Create domain and run function inside it
    """
    def nested ():
        with ForkDomain (push_main = False) as domain:
            yield domain.Connect ()
            AsyncReturn ((yield domain.Call (func, *args, **keys)))
    return Async (nested) ()

@Async
def Unwrap (future):
    """Unwrap future
    """
    AsyncReturn ((yield ((yield future))))

# vim: nu ft=python columns=120 :
