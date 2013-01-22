# -*- coding: utf-8 -*-
import unittest

from .common import Remote, RemoteError
from ..hub import Hub
from ..proxy import Proxy, Proxify
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
        remote = Remote (0)
        with Proxify (remote) as proxy:
            # this
            self.assertEqual ((yield proxy), remote)

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
            self.assertEqual ((yield await_future), (remote.value))

            # proxy
            with (yield +proxy.Value) as value_proxy:
                self.assertTrue (isinstance (value_proxy, Proxy))

        self.assertFalse (Hub.Instance ().handlers)

# vim: nu ft=python columns=120 :
