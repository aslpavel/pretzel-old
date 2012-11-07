# -*- coding: utf-8 -*-
import unittest

from ..async import FutureSource, FutureCanceled
from ..event import Event
#------------------------------------------------------------------------------#
# Event                                                                        #
#------------------------------------------------------------------------------#
class EventTests (unittest.TestCase):
    """Event unit tests
    """
    def testAddRemove (self):
        """Test add and remove
        """
        values = []
        def handler (value):
            values.append (value)
            return True

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
        """Test await
        """
        event = Event ()

        # resolve
        future = event.Await ()
        self.assertEqual (len (event.handlers), 1)
        self.assertFalse (future.IsCompleted ())

        event (1)
        self.assertEqual (future.Result (), (1,))
        self.assertEqual (len (event.handlers), 0)

        # cancel
        cancel = FutureSource ()
        future = event.Await (cancel.Future)
        self.assertEqual (len (event.handlers), 1)
        self.assertFalse (future.IsCompleted ())

        cancel.ResultSet (None)
        self.assertEqual (len (event.handlers), 0)
        self.assertTrue (future.IsCompleted ())
        with self.assertRaises (FutureCanceled):
            future.Result ()

# vim: nu ft=python columns=120 :
