# -*- coding: utf-8 -*-
import unittest

from .disposable import *
#------------------------------------------------------------------------------#
# Disposables                                                                  #
#------------------------------------------------------------------------------#
class DisposablesTests (unittest.TestCase):
    def testDisposable (self):
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

    def testCompositeDisposable (self):
        ctx = [0, 0, 0]
        def f0 ():
            ctx [0] += 1
        def f1 ():
            ctx [1] += 1
        def f2 ():
            ctx [2] += 1

        d0, d1, d2 = map (Disposable, (f0, f1, f2))
        d = CompositeDisposable (d0)
        self.assertEqual (ctx, [0, 0, 0])
        d += d1
        with d:
            self.assertEqual (ctx, [0, 0, 0])
        self.assertEqual (ctx, [1, 1, 0])
        d.Dispose ()
        self.assertEqual (ctx, [1, 1, 0])

# vim: nu ft=python columns=120 :