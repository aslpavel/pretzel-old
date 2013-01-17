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
        conn_real = ForkConnection ()
        with (yield conn_real) as conn:
            self.assertNotEqual (os.getpid (), (yield conn (os.getpid)))
            self.assertEqual (conn_real.Process.pid, (yield conn (os.getpid)))

            with (yield conn.Proxy (Remote, 0)) as proxy:
                # get(set) attribute
                self.assertEqual ((yield proxy.value), 0)
                proxy.value = 1
                self.assertEqual ((yield proxy.value), 1)

                # call
                self.assertEqual ((yield proxy ('test')), 'test')

                # method
                self.assertEqual ((yield proxy.Value ()), (yield proxy.value))
                with self.assertRaises (RemoteError):
                    yield proxy.Error (RemoteError ())

                # proxy (mutator)
                value_proxy = yield proxy.Value.Proxy ()
                self.assertTrue (isinstance (value_proxy, Proxy))
                value_proxy.Dispose ()

                # null (mutator)
                self.assertEqual ((yield proxy.Value.Null ()), None)

                # yield (mutator)
                yield_future = proxy.ValueAsync.Yield ()
                self.assertFalse (yield_future.IsCompleted (), False)
                yield proxy ()
                self.assertEqual ((yield yield_future), (yield proxy.value))

                # awaitable
                await_result = []
                @Async
                def await ():
                    await_result.append ((yield proxy))
                await ()
                self.assertFalse (await_result)
                yield proxy ('await done')
                self.assertEqual (await_result, ['await done'])

        with self.assertRaises (ValueError):
            conn ('test')

        # process exit status
        self.assertEqual ((yield conn_real.Process), 0)
        self.assertFalse (conn_real.hub.handlers)

    @AsyncTest
    def testNested (self):
        """Nested connection test
        """
        with (yield ForkConnection ()) as c0:
            c0_pid = yield c0 (os.getpid)
            with (yield c0.Yield (ForkConnection)) as c1:
                c1_pid = yield c1 (os.getpid)

        self.assertNotEqual (c0_pid, c1_pid)
        self.assertNotEqual (os.getpid (), c0_pid)
        self.assertNotEqual (os.getpid (), c1_pid)

# vim: nu ft=python columns=120 :
