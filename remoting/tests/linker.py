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
            with ForkDomain (core, push_main = False) as domain:
                yield domain.Connect ()
                self.assertEqual ((yield domain.Call (RemoteIncrease, 1)), 2)

        with Core () as core:
            run_future = run ()
        run_future.Result ()

    def testProxy (self):
        @Async
        def run ():
            with ForkDomain (core, push_main = False) as domain:
                yield domain.Connect ()

                # create
                proxy = yield domain.ProxyCreate (Remote, 'value')
            
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
                lambda_proxy = yield proxy.Lambda (domain)
                lambda_proxy ('new new value')
                self.assertEqual ((yield proxy.value), 'new new value')

        with Core () as core:
            run_future = run ()
        run_future.Result ()

#------------------------------------------------------------------------------#
# Helpers                                                                      #
#------------------------------------------------------------------------------#
def RemoteIncrease (value):
    return value + 1

class Remote (object):
    def __init__ (self, value):
        self.value = value

    def Value (self):
        return self.value

    def Same (self, obj):
        return obj

    def Error (self, error):
        raise error

    def Lambda (self, domain):
        return domain.ToProxy (lambda value: setattr (self, 'value', value))

# vim: nu ft=python columns=120 :
