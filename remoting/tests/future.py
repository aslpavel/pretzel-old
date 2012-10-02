# -*- coding: utf-8 -*-
import unittest

from ..domains.fork import ForkDomain
from ...tests import AsyncTest
from ...async import FutureSource, SucceededFuture, FailedFuture, RaisedFuture

__all__ = ('FutureTest',)
#------------------------------------------------------------------------------#
# Future Test                                                                  #
#------------------------------------------------------------------------------#
class FutureTest (unittest.TestCase):
    """Future service unit tests
    """
    @AsyncTest
    def testFuture (self):
        """Future tests
        """
        with ForkDomain (push_main = False) as domain:
            yield domain.Connect ()
            proxy = yield domain.Call.Proxy (RemoteFuture)

            # done future
            yield proxy.Create ()
            future = yield proxy.Future
            self.assertFalse (future.IsCompleted ())
            self.assertEqual (future, (yield proxy.Future))
            self.assertTrue  ((yield proxy.Equal (future)))

            yield proxy.Done ('result')
            yield future
            self.assertEqual (future.Result (), 'result')
            self.assertEqual (type ((yield proxy.Future)), SucceededFuture)

            # error future
            yield proxy.Create ()
            future = yield proxy.Future

            yield proxy.Error (ValueError ('test'))
            self.assertEqual (type ((yield proxy.Future)), FailedFuture)
            try:
                yield future
            except Exception as error:
                self.assertEqual (type (error), ValueError)
                self.assertEqual (error.args, ('test',))

            # succeeded future
            future = yield proxy.Succeeded ()
            self.assertEqual (future.Result (), 'success')
            self.assertEqual (type (future), SucceededFuture)

            # failed future
            future = yield proxy.Failed ()
            self.assertEqual (future.Error () [0], ValueError)
            self.assertEqual (future.Error () [1].args, ('failed',))
            self.assertEqual (type (future), FailedFuture)

#------------------------------------------------------------------------------#
# Helpers                                                                      #
#------------------------------------------------------------------------------#
class RemoteFuture (object):
    """Remote helper
    """
    def __init__ (self):
        self.source = None

    # future
    @property
    def Future (self):
        return None if self.source is None else self.source.Future

    def Create (self):
        self.source = FutureSource ()

    # resolve
    def Done (self, result):
        self.source.ResultSet (result)

    def Error (self, error):
        self.source.ErrorRaise (error)

    # completed
    def Succeeded (self):
        return SucceededFuture ('success')

    def Failed (self):
        return RaisedFuture (ValueError ('failed'))

    # compare
    def Equal (self, future):
        return False if self.source is None else self.source.Future == future

# vim: nu ft=python columns=120 :
