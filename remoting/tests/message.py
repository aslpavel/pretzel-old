# -*- coding: utf-8 -*-
import io
import os
import sys
import unittest

from ..message import *
from ...async import *

__all__ = ('MessageTest',)
#------------------------------------------------------------------------------#
# Message Test                                                                 #
#------------------------------------------------------------------------------#
class MessageTest (unittest.TestCase):
    def testSerialize (self):
        msg = Message (b'dst', b'data')

        stream = io.BytesIO ()
        msg.Save (stream)
        stream.seek (0)
        msg_load = Message.Load (stream)

        self.assertEqual (msg.src, msg_load.src)
        self.assertEqual (msg.dst, msg_load.dst)
        self.assertEqual (msg.data, msg_load.data)

    def testSerializeAsync (self):
        msg = Message (b'dst', b'data')

        with Core () as core:
            r, w = os.pipe ()
            ra, wa = core.AsyncFileCreate (r), core.AsyncFileCreate (w)
            
            @Async
            def test ():
                yield core.Idle ()
                msg_load_future = Message.LoadAsync (ra)
                self.assertFalse (msg_load_future.IsCompleted ())

                yield msg.SaveAsync (wa)
                msg_load = yield msg_load_future

                self.assertEqual (msg.src, msg_load.src)
                self.assertEqual (msg.dst, msg_load.dst)
                self.assertEqual (msg.data, msg_load.data)
                
            test_future = test ()

        ra.Dispose ()
        wa.Dispose ()

        test_future.Result ()

    def testError (self):
        msg = Message (b'dst', b'data')
        try: raise ValueError ('test error')
        except Exception:
            msg_error = msg.ErrorResponse (sys.exc_info ())

        self.assertEqual (msg_error.src, msg.dst)
        self.assertEqual (msg_error.dst, msg.src)

        stream = io.BytesIO ()
        msg_error.Save (stream)
        stream.seek (0)
        msg_load = Message.Load (stream)

        self.assertEqual (msg_load.src, msg_error.src)
        self.assertEqual (msg_load.dst, msg_error.dst)
        self.assertEqual (type (msg_load), type (msg_error))

    def testResponse (self):
        msg = Message (b'dst', b'data', b'src')

        self.assertEqual (msg.dst, b'dst')
        self.assertEqual (msg.src, b'src')
        self.assertEqual (msg.data, b'data')

        msg_resp = msg.Response (b'new_data')

        self.assertEqual (msg_resp.dst, msg.src)
        self.assertEqual (msg_resp.src, msg.dst)
        self.assertEqual (msg_resp.data, b'new_data')

# vim: nu ft=python columns=120 :
