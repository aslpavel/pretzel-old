# -*- coding: utf-8 -*-
import unittest
import operator

from .log import *
from ..observer import *

#------------------------------------------------------------------------------#
# Log Tests                                                                    #
#------------------------------------------------------------------------------#
class LogTests (unittest.TestCase):
    def setUp (self):
        self.log = Log ('test')

    def testMessage (self):
        o = ListObserver ()

        self.log.Info (0)
        with self.log.Select (operator.attrgetter ('Message')).Subscribe (o):
            self.log.Info (1)
            self.assertEqual (o, [1])

    def testProgress (self):
        o = ListObserver ()
        d = MutableDisposable ()

        # normal
        d.Replace (self.log.Subscribe (o))
        with self.log.Progress ('Progress') as progress:
            self.assertEqual (o [0], progress)
            d.Replace (progress.Subscribe (o))
            progress (0)
            progress (1)
            self.assertEqual (o [1:], [0, 1])
        self.assertEqual (o [1:], [0, 1, None])

        # error
        del o [:]
        try:
            with self.log.Progress ('Progress') as progress:
                d.Replace (progress.Subscribe (o))
                progress (0)
                raise ValueError ()
        except ValueError:
            pass
        self.assertEqual (o [0], 0)
        self.assertEqual (o [1] [0], ValueError)

        with self.assertRaises (ValueError):
            print (progress.Value)

    def testPending (self):
        o = ListObserver ()
        d = MutableDisposable ()

        # normal
        d.Replace (self.log.Subscribe (o))
        with self.log.Pending ('Pending') as pending:
            self.assertEqual (o [0], pending)
            self.assertEqual (pending.Value, False)
            del o [:]
            d.Replace (pending.Subscribe (o))
        self.assertEqual (o, [None])
        self.assertEqual (pending.Value, True)

#------------------------------------------------------------------------------#
# List Observer                                                                #
#------------------------------------------------------------------------------#
class ListObserver (Observer, list):
    def __hash__ (self):
        return id (self)

    def OnNext (self, value):
        self.append (value)

    def OnError (self, error):
        self.append (error)

    def OnCompleted (self):
        self.append (None)
# vim: nu ft=python columns=120 :
