# -*- coding: utf-8 -*-
import os
import unittest

from .common import Remote, RemoteError
from ..conn import ForkConnection
from ..proxy import Proxy
from ...async import Async
from ...async.tests import AsyncTest

__all__ = ('ConnectionTest',)
#------------------------------------------------------------------------------#
# Connection Test                                                              #
#------------------------------------------------------------------------------#
class ConnectionTest (unittest.TestCase):
    """Connection unit tests
    """
    @AsyncTest
    def testFork (self):
        """Fork connection tests
        """
        with (yield ForkConnection ()) as conn:
            self.assertNotEqual (os.getpid (), (yield conn (os.getpid) ()))
            self.assertEqual (conn.Process.pid, (yield conn (os.getpid) ()))

            with (yield +conn (Remote) (0)) as proxy:
                # call
                self.assertEqual ((yield proxy ('test')), 'test')

                #  attributes
                self.assertEqual ((yield proxy.value), 0)
                proxy.value = 1
                self.assertEqual ((yield proxy.value), 1)

                # items
                self.assertEqual ((yield proxy.items), {})
                proxy ['item'] = 'item_value'
                self.assertEqual ((yield proxy ['item']), 'item_value')
                with self.assertRaises (KeyError):
                    yield proxy ['bad item']

                # method
                self.assertEqual ((yield proxy.Value ()), (yield proxy.value))
                with self.assertRaises (RemoteError):
                    yield proxy.Error (RemoteError ())

                # await
                await_future = (~proxy.ValueAsync ()).Await ()
                self.assertFalse (await_future.IsCompleted (), False)
                yield proxy ()
                self.assertEqual ((yield await_future), (yield proxy.value))

                # proxy
                with (yield +proxy.Value) as value_proxy:
                    self.assertTrue (isinstance (value_proxy, Proxy))

        with self.assertRaises (ValueError):
            conn ('test')

        # process exit status
        self.assertEqual ((yield conn.Process), 0)
        self.assertFalse (conn.hub.handlers)

    @AsyncTest
    def testNested (self):
        """Nested connection test
        """
        with (yield ForkConnection ()) as c0:
            c0_pid = yield c0 (os.getpid) ()
            with (yield ~c0 (ForkConnection) ()) as c1:
                c1_pid = yield c1 (os.getpid) ()

        self.assertNotEqual (c0_pid, c1_pid)
        self.assertNotEqual (os.getpid (), c0_pid)
        self.assertNotEqual (os.getpid (), c1_pid)

# vim: nu ft=python columns=120 :
