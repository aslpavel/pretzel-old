# -*- coding: utf-8 -*-
import unittest

from ..domains.fork import *
from ...async import *

__all__ = ('FutureTest',)
#------------------------------------------------------------------------------#
# Future Test                                                                  #
#------------------------------------------------------------------------------#
class FutureTest (unittest.TestCase):
    def testFuture (self):
        @Async
        def run ():
            with ForkDomain (core, push_main = False) as domain:
                yield domain.Connect ()
                proxy = yield domain.ProxyCreate (RemoteFuture)

                # done future
                yield proxy.Create ()
                future = yield proxy.Future
                self.assertFalse (future.IsCompleted ())
                self.assertEqual (future, (yield proxy.Future))
                self.assertTrue  ((yield proxy.Equal (future)))

                yield proxy.Done ('result')
                self.assertEqual (future.Result (), 'result')
                self.assertEqual (type ((yield proxy.Future)), SucceededFuture)

                # error future
                yield proxy.Create ()
                future = yield proxy.Future

                yield proxy.Error (ValueError ('test'))
                self.assertEqual (future.Error () [0], ValueError)
                self.assertEqual (future.Error () [1].args, ('test',))
                self.assertEqual (type ((yield proxy.Future)), RaisedFuture)

                # succeeded future
                future = yield proxy.Succeeded ()
                self.assertEqual (future.Result (), 'success')
                self.assertEqual (type (future), SucceededFuture)

                # failed future
                future = yield proxy.Failed ()
                self.assertEqual (future.Error () [0], ValueError)
                self.assertEqual (future.Error () [1].args, ('failed',))
                self.assertEqual (type (future), RaisedFuture)

        with Core () as core:
            run_future = run ()
        run_future.Result ()

#------------------------------------------------------------------------------#
# Helpers                                                                      #
#------------------------------------------------------------------------------#
class RemoteFuture (object):
    def __init__ (self):
        self.future = None

    # future
    @property
    def Future (self):
        return self.future

    def Create (self):
        self.future = Future ()

    # resolve
    def Done (self, result):
        self.future.ResultSet (result)

    def Error (self, error):
        self.future.ErrorRaise (error)

    # completed
    def Succeeded (self):
        return SucceededFuture ('success')

    def Failed (self):
        return RaisedFuture (ValueError ('failed'))

    # compare
    def Equal (self, future):
        return self.future == future

# vim: nu ft=python columns=120 :
