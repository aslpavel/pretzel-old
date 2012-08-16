# -*- coding: utf-8 -*-
import unittest

from ..domains.fork import *
from ...async import *

__all__ = ('LinkerTest',)
#------------------------------------------------------------------------------#
# Linker Test                                                                  #
#------------------------------------------------------------------------------#
class LinkerTest (unittest.TestCase):
    def testCall (self):
        @Async
        def run ():
            with ForkDomain (push_main = False) as domain:
                yield domain.Connect ()
                self.assertEqual ((yield domain.Call (RemoteIncrease, 1)), 2)

        with Core.Instance () as core:
            run_future = run ()
            run_future.Continue (lambda future: core.Stop ())
        run_future.Result ()

    def testProxy (self):
        @Async
        def run ():
            with ForkDomain (push_main = False) as domain:
                yield domain.Connect ()

                # create
                proxy = yield domain.Call.Proxy (Remote, 'value')
            
                # method
                self.assertEqual ((yield proxy.Value ()), 'value')

                # property
                self.assertEqual ((yield proxy.value), 'value')
                proxy.value = 'new value'
                self.assertEqual ((yield proxy.value), 'new value')

                # error
                with self.assertRaises (ValueError):
                    yield proxy.Error (ValueError ())

                # lambda proxy
                lambda_proxy = yield proxy.Lambda.Proxy ()
                lambda_proxy ('new new value')
                self.assertEqual ((yield proxy.value), 'new new value')

                # proxy mapping
                obj = yield proxy.ObjectCreate (domain)
                self.assertTrue ((yield proxy.ObjectEqual (obj)))
                self.assertEqual ((yield proxy.obj), obj)

        with Core.Instance () as core:
            run_future = run ()
            run_future.Continue (lambda future: core.Stop ())
        run_future.Result ()

#------------------------------------------------------------------------------#
# Helpers                                                                      #
#------------------------------------------------------------------------------#
def RemoteIncrease (value):
    return value + 1

class Remote (object):
    def __init__ (self, value):
        self.value = value
        self.obj = None

    def Value (self):
        return self.value

    def Same (self, obj):
        return obj

    def Error (self, error):
        raise error

    def Lambda (self):
        return lambda value: setattr (self, 'value', value)

    def ObjectCreate (self, domain, obj = None):
        self.obj = domain.ToProxy (object ()) if obj is None else obj
        return self.obj

    def ObjectEqual (self, obj):
        return self.obj == obj

# vim: nu ft=python columns=120 :
