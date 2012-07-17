# -*- coding: utf-8 -*-
import unittest
import operator
import itertools

from .async import *
from .event import *
from .disposable import *
#------------------------------------------------------------------------------#
# Disposables                                                                  #
#------------------------------------------------------------------------------#
class DisposablesTests (unittest.TestCase):
    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
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

    #--------------------------------------------------------------------------#
    # Composite Disposable                                                     #
    #--------------------------------------------------------------------------#
    def testCompositeDisposable (self):
        ctx = [0, 0, 0, 0]
        d0, d1, d2, d3 = map (Disposable, (
            lambda: operator.setitem (ctx, 0, 1),
            lambda: operator.setitem (ctx, 1, 1),
            lambda: operator.setitem (ctx, 2, 1),
            lambda: operator.setitem (ctx, 3, 1)))

        d = CompositeDisposable (d0)
        self.assertEqual (ctx, [0, 0, 0, 0])

        d += d1
        with d:
            self.assertEqual (ctx, [0, 0, 0, 0])
        self.assertEqual (ctx, [1, 1, 0, 0])

        d += Disposable (lambda: d.Add (d3))

        d.Dispose ()
        self.assertEqual (ctx, [1, 1, 0, 1])

    def testCompsiteDisposableOrder (self):
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

#------------------------------------------------------------------------------#
# Event                                                                        #
#------------------------------------------------------------------------------#
class EventTests (unittest.TestCase):
    def testAddRemove (self):
        values = []
        def handler (value):
            values.append (value)

        # create
        event = Event ()
        event (0)

        # add
        event.Add (handler)
        event (1)
        self.assertEqual (values, [1])

        # remove
        self.assertTrue (event.Remove (handler))
        event (2)
        self.assertEqual (values, [1])

        # double remove
        self.assertFalse (event.Remove (handler))
        event (3)
        self.assertEqual (values, [1])

    def testAwait (self):
        event = Event ()

        # resolve
        future = event.Await ()
        self.assertEqual (len (event.handlers), 1)
        self.assertFalse (future.IsCompleted ())

        event (1)
        self.assertEqual (future.Result (), (1,))
        self.assertEqual (len (event.handlers), 0)

        # cancel
        future = event.Await ()
        self.assertEqual (len (event.handlers), 1)
        self.assertFalse (future.IsCompleted ())

        future.Cancel ()
        self.assertEqual (len (event.handlers), 0)
        self.assertTrue (future.IsCompleted ())
        with self.assertRaises (FutureCanceled):
            future.Result ()

        # wait
        future = event.Await ()
        self.assertEqual (len (event.handlers), 1)
        self.assertFalse (future.IsCompleted ())

        with self.assertRaises (NotImplementedError):
            future.Wait ()
        self.assertEqual (len (event.handlers), 1)
        self.assertFalse (future.IsCompleted ())

# vim: nu ft=python columns=120 :
