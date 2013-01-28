# -*- coding: utf-8 -*-
import unittest
import pickle

from ..result import Result

__all__ = ('ResultTest',)
#------------------------------------------------------------------------------#
# Result Test                                                                  #
#------------------------------------------------------------------------------#
class ResultTest (unittest.TestCase):
    """Result unit tests
    """

    def test (self):
        # default result
        r = Result ()
        with self.assertRaises (ValueError): r ()
        with r: pass
        self.assertEqual (r (), None)
        self.assertEqual (pickle.loads (pickle.dumps (r)) (), None)
        with self.assertRaises (ValueError): r.SetResult ('done')

        # result
        r = Result ()
        with r as ret: ret ('done')
        self.assertEqual (r (), 'done')
        self.assertEqual (pickle.loads (pickle.dumps (r)) (), 'done')

        # error
        r = Result ()
        with r as ret: raise ResultTestError ('test error')
        with self.assertRaises (ValueError): r.SetResult ('done')
        with self.assertRaises (ResultTestError): r ()
        with self.assertRaises (ResultTestError): pickle.loads (pickle.dumps (r)) ()

        # saved traceback
        try:
            pickle.loads (pickle.dumps (r)) ()
        except Exception as e:
            self.assertTrue (hasattr (e, '_saved_traceback'))

class ResultTestError (Exception):
    """Help exception
    """
# vim: nu ft=python columns=120 :
