# -*- coding: utf-8 -*-
import time
import unittest

from ..thread import ThreadPool
from ..async import Future
from ..async.tests import AsyncTest

__all__ = ('ThreadPoolTest',)
#------------------------------------------------------------------------------#
# Thread pool test                                                             #
#------------------------------------------------------------------------------#
class ThreadPoolTest (unittest.TestCase):
    """Thread pool unit test
    """

    @AsyncTest
    def test (self):
        """Approximate test
        """
        time_span = .3
        try:
            # pool instance
            pool = ThreadPool.Instance ()

            # enqueue jobs
            futures = set (pool (lambda: time.sleep (time_span)) for _ in range (pool.Size () + 1))

            # register jobs completion
            for future in futures:
                future.ContinueSelf (lambda future: futures.discard (future))
            self.assertEqual (len (futures), pool.Size () + 1)

            # wait for jobs
            time_start = time.time ()
            for _ in range (pool.Size ()):
                yield Future.WhenAny (futures)
                self.assertEqual (round ((time.time () - time_start) / time_span), 1)

            self.assertEqual (len (futures), 1)
            yield Future.WhenAny (futures)
            self.assertEqual (round ((time.time () - time_start) / time_span), 2)

        finally:
            pool.Instance (None)

# vim: nu ft=python columns=120 :
