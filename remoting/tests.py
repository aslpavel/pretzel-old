# -*- coding: utf-8 -*-
import unittest

from .util import *
from .async import *
from .domains.fork import *

#-----------------------------------------------------------------------------#
# Fork Domain                                                                 #
#-----------------------------------------------------------------------------#
class ForkDomainTests (unittest.TestCase):
    def setUp (self):
        self.domain = ForkDomain (Core (), push_main = False)
        self.remote = self.domain.InstanceCreate (Remote, 10)

    def tearDown (self):
        self.domain.Dispose ()

    def testCallMethod (self):
        self.assertEqual (self.remote.ValueGet (), 10)

    def testCallSpecialMethod (self):
        self.assertEqual (len (self.remote), 10)

    def testPropertyGet (self):
        self.assertEqual (self.remote.value, 10)

    def testPropertySet (self):
        self.remote.value = 11
        self.assertEqual (self.remote.ValueGet (), 11)

    def testError (self):
        with self.assertRaises (SomeError):
            self.remote.Error ()

    def testReferenctToLambda (self):
        ctx = [0]
        def inc ():
            ctx [0] += 1
        self.remote.Call (self.domain.ToReference (inc))
        self.assertEqual (ctx [0], 1)

    def testInvertReferenceToLamba (self):
        incrementer = self.remote.ValueIncrementer (self.domain)
        self.assertEqual (self.remote.value, 10)
        incrementer ()
        self.assertEqual (self.remote.value, 11)

    def testCallFunction (self):
        import os
        remote_pid, local_pid = self.domain.Call (os.getpid), os.getpid ()
        self.assertTrue (isinstance (remote_pid, int))
        self.assertNotEqual (remote_pid, local_pid)

    def testDomainPersistence (self):
        self.assertNotEqual (self.domain.Call (GetId, self.domain),
            id (self.domain))

#-----------------------------------------------------------------------------#
# Disposables                                                                 #
#-----------------------------------------------------------------------------#
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

#-----------------------------------------------------------------------------#
# Helpers                                                                     #
#-----------------------------------------------------------------------------#
class Remote (object):
    def __init__ (self, value):
        self.value = value

    def ValueGet (self):
        return self.value

    def ValueIncrementer (self, domain):
        def incrementer ():
            self.value += 1
        return domain.ToReference (incrementer)

    def __len__ (self):
        return self.value

    def Call (self, target, *args, **keys):
        return target (*args, **keys)

    def Error (self):
        raise SomeError ()

class SomeError (Exception):
    pass

def GetId (value):
    return id (value)

# vim: nu ft=python columns=120 :
