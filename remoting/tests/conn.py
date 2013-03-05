# -*- coding: utf-8 -*-
import os
import unittest

from .common import Remote, RemoteError
from ..conn import ForkConnection
from ..conn.conn import ConnectionProxy
from ..proxy import Proxy
from ..hub import ReceiverSenderPair
from ...async import Idle
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

        # process exit status
        self.assertEqual ((yield conn.Process), 0)
        self.assertFalse (conn.hub.handlers)

    @AsyncTest
    def testNested (self):
        """Nested connection test
        """
        with (yield ForkConnection ()) as c0:
            c0_pid = yield c0 (os.getpid) ()
            self.assertTrue (isinstance (c0_pid, int))
            with (yield ~c0 (ForkConnection) ()) as c1:
                c1_pid = yield c1 (os.getpid) ()
                self.assertTrue (isinstance (c1_pid, int))
                self.assertTrue (isinstance (c1, ConnectionProxy))

        self.assertNotEqual (c0_pid, c1_pid)
        self.assertNotEqual (os.getpid (), c0_pid)
        self.assertNotEqual (os.getpid (), c1_pid)

        yield Idle () # make sure we are not in handler
        self.assertFalse (c0.hub.handlers)

    @AsyncTest
    def testSenderRoundTrip (self):
        r, s = ReceiverSenderPair ()
        with (yield ForkConnection ()) as conn:
            self.assertEqual ((yield conn (s)), s)

# vim: nu ft=python columns=120 :
