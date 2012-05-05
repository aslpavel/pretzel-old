# -*- coding: utf-8 -*-
import unittest

from .async import *
from .event import *
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
