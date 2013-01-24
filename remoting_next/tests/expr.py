# -*- coding: utf-8 -*-
import unittest

from ..expr import *
from ...async import Event

__all__ = ('ExprTest',)
#------------------------------------------------------------------------------#
# Expression Test                                                              #
#------------------------------------------------------------------------------#
class ExprTest (unittest.TestCase):
    """Expression tests
    """

    def testLoadArg (self):
        arg_0 = Compile (LoadArgExpr (0))
        arg_1 = Compile (LoadArgExpr (1))

        self.assertEqual (arg_0 ('one', 'two').Result (), 'one')
        self.assertEqual (arg_1 ('one', 'two').Result (), 'two')

    def testLoadConst (self):
        const = Compile (LoadConstExpr ('constant'))
        self.assertEqual (const ().Result (), 'constant')

    def testCall (self):
        fn = lambda *a, **kw: (a, kw)

        call_a  = Compile (CallExpr (fn, 'arg'))
        call_kw = Compile (CallExpr (fn, k = 'key'))
        call_a_kw = Compile (CallExpr (fn, 'arg', k = 'key'))

        self.assertEqual (call_a ().Result (), (('arg',), {}))
        self.assertEqual (call_kw ().Result (), (tuple (), {'k': 'key'}))
        self.assertEqual (call_a_kw ().Result (), (('arg',), {'k': 'key'}))

    def testAttr (self):
        class A (object): pass
        a = A ()

        get_attr = Compile (GetAttrExpr (LoadConstExpr (a), 'key'))
        set_attr = Compile (SetAttrExpr (LoadConstExpr (a), 'key', LoadArgExpr (0)))

        with self.assertRaises (AttributeError):
            get_attr ().Result ()
        set_attr ('value').Result ()
        self.assertEqual (a.key, 'value')
        self.assertEqual (get_attr ().Result (), 'value')


    def testItem (self):
        d = {}
        get_item = Compile (GetItemExpr (LoadConstExpr (d), LoadArgExpr (0)))
        set_item = Compile (SetItemExpr (LoadConstExpr (d), LoadArgExpr (0), LoadArgExpr (1)))

        with self.assertRaises (KeyError):
            get_item ('key').Result ()
        set_item ('key', 'value').Result ()
        self.assertEqual ({'key': 'value'}, d)
        self.assertEqual (get_item ('key').Result (), 'value')

    def testRaise (self):
        error = Compile (RaiseExpr (LoadArgExpr (0)))

        with self.assertRaises (ValueError):
            error (ValueError ('test')).Result ()

    def testAwait (self):
        event = Event ()
        await = Compile (AwaitExpr (LoadArgExpr (0)))

        future = await (event)
        self.assertEqual (future.IsCompleted (), False)
        event ('result')
        self.assertEqual (future.Result (), ('result',))

#------------------------------------------------------------------------------#
# Compile Helper                                                               #
#------------------------------------------------------------------------------#
def Compile (expr):
    """Compile expression
    """
    code = Code ()
    expr.Compile (code)
    return code

# vim: nu ft=python columns=120 :
