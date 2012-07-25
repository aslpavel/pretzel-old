# -*- coding: utf-8 -*-
import unittest

from .domains.fork import *
from ..async import *

#-----------------------------------------------------------------------------#
# Fork Domain                                                                 #
#-----------------------------------------------------------------------------#
class ForkDomainTests (unittest.TestCase):
    def setUp (self):
        self.domain = ForkDomain (Core (), run = True, push_main = False)
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

    def testContext (self):
        value = self.remote.value
        with self.remote as remote:
            self.assertEqual (value + 1, remote.value)

    def testError (self):
        with self.assertRaises (SomeError):
            self.remote.Error ()

    def testReferenctToLambda (self):
        ctx = [0]
        def inc ():
            ctx [0] += 1
        self.remote.Call (self.domain.ToReference (inc))
        self.assertEqual (ctx [0], 1)

    def testInvertReferenceToLambda (self):
        increment = self.remote.ValueIncrement (self.domain)
        self.assertEqual (self.remote.value, 10)
        increment ()
        self.assertEqual (self.remote.value, 11)

    def testCallFunction (self):
        import os
        remote_pid, local_pid = self.domain.Call (os.getpid), os.getpid ()
        self.assertTrue (isinstance (remote_pid, int))
        self.assertNotEqual (remote_pid, local_pid)

    def testDomainPersistence (self):
        self.assertNotEqual (self.domain.Call (GetId, self.domain),
            id (self.domain))

    def testNestedDomain (self):
        import os
        local_pid  = os.getpid ()
        remote_pid = self.domain.Call (os.getpid)
        nested_pid = self.remote.NestedCall (self.domain.channel.core, os.getpid)

        self.assertNotEqual (local_pid, remote_pid)
        self.assertNotEqual (local_pid, nested_pid)
        self.assertNotEqual (remote_pid, nested_pid)

#-----------------------------------------------------------------------------#
# Helpers                                                                     #
#-----------------------------------------------------------------------------#
class Remote (object):
    def __init__ (self, value):
        self.value = value
        self.non_marshable = lambda: None # non marshable type

    def ValueGet (self):
        return self.value

    def ValueIncrement (self, domain):
        def increment ():
            self.value += 1
        return domain.ToReference (increment)

    def __len__ (self):
        return self.value

    def Call (self, target, *args, **keys):
        return target (*args, **keys)

    def Error (self):
        raise SomeError ()

    def NestedCall (self, core, func, *args, **keys):
        with ForkDomain (core, run = True, push_main = False) as domain:
            return domain.Call (func, *args, **keys)

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        pass

    def __enter__ (self):
        self.value += 1
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

class SomeError (Exception):
    pass

def GetId (value):
    return id (value)

# vim: nu ft=python columns=120 :
