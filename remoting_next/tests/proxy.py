# -*- coding: utf-8 -*-
import unittest

from .common import Remote, RemoteError
from ..hub import Hub
from ..proxy import Proxy, Proxify
from ...async import Async
from ...async.tests import AsyncTest

__all__ = ('ProxyTest',)
#------------------------------------------------------------------------------#
# Proxy Test                                                                   #
#------------------------------------------------------------------------------#
class ProxyTest (unittest.TestCase):
    """Proxy unit tests
    """

    @AsyncTest
    def test (self):
        with Proxify (Remote (0)) as proxy:
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

        self.assertFalse (Hub.Instance ().handlers)

# vim: nu ft=python columns=120 :
