# -*- coding: utf-8 -*-
import unittest
import operator
import itertools

from ..disposable import Disposable, CompositeDisposable
#------------------------------------------------------------------------------#
# Disposables                                                                  #
#------------------------------------------------------------------------------#
class DisposablesTests (unittest.TestCase):
    """Disposable unite tests
    """
    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def testDisposable (self):
        """Test disposable
        """
        ctx = [0]
        def dispose ():
            ctx [0] += 1

        with Disposable (dispose) as d0:
            self.assertEqual (ctx [0], 0)
        self.assertEqual (ctx [0], 1)
        d0.Dispose ()
        self.assertEqual (ctx [0], 1)

        d1 = Disposable (dispose)
        self.assertEqual (ctx [0], 1)
        d1.Dispose ()
        self.assertEqual (ctx [0], 2)

    #--------------------------------------------------------------------------#
    # Composite Disposable                                                     #
    #--------------------------------------------------------------------------#
    def testCompositeDisposable (self):
        """Test composite disposable
        """
        ctx = [0, 0, 0, 0]
        d0, d1, d2, d3 = map (Disposable, (
            lambda: operator.setitem (ctx, 0, 1),
            lambda: operator.setitem (ctx, 1, 1),
            lambda: operator.setitem (ctx, 2, 1),
            lambda: operator.setitem (ctx, 3, 1)))

        d = CompositeDisposable ((d0,))
        self.assertEqual (ctx, [0, 0, 0, 0])

        d += d1
        with d:
            self.assertEqual (ctx, [0, 0, 0, 0])
        self.assertEqual (ctx, [1, 1, 0, 0])

        d += Disposable (lambda: d.Add (d3))

        d.Dispose ()
        self.assertEqual (ctx, [1, 1, 0, 1])

    def testCompsiteDisposableOrder (self):
        """Test dispose order
        """
        ctx, count = [0, 0, 0, 0], itertools.count ()
        next (count)
        d0, d1, d2, d3 = map (Disposable, (
            lambda: operator.setitem (ctx, 0, next (count)),
            lambda: operator.setitem (ctx, 1, next (count)),
            lambda: operator.setitem (ctx, 2, next (count)),
            lambda: operator.setitem (ctx, 3, next (count))))

        with CompositeDisposable () as d:
            d.Add (d0)
            d.Add (d2)
            d.Add (d1)
            d.Add (d3)
            self.assertEqual (ctx, [0, 0, 0, 0])

        self.assertEqual (ctx, [4, 2, 3, 1])

# vim: nu ft=python columns=120 :
