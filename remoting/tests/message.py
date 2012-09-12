# -*- coding: utf-8 -*-
import io
import os
import sys
import unittest

from ..message import Message
from ...async import Async, AsyncFile, ScopeFuture, Core

__all__ = ('MessageTest',)
#------------------------------------------------------------------------------#
# Message Test                                                                 #
#------------------------------------------------------------------------------#
class MessageTest (unittest.TestCase):
    def testSerialize (self):
        msg = Message.FromValue (b'value', b'dst')

        stream = io.BytesIO ()
        msg.Save (stream)
        stream.seek (0)
        msg_load = Message.FromStream (stream)

        self.assertEqual (msg.src, msg_load.src)
        self.assertEqual (msg.dst, msg_load.dst)
        self.assertEqual (msg.Value (), msg_load.Value ())

    def testSerializeAsync (self):
        msg = Message.FromValue (b'value', b'dst')

        with Core.Instance () as core:
            ra, wa = (AsyncFile (fd) for fd in os.pipe ())

            @Async
            def test ():
                yield core.Idle ()
                with ScopeFuture () as cancel:
                    msg_load_future = Message.FromAsyncStream (ra, core.Sleep (1, cancel))
                    self.assertFalse (msg_load_future.IsCompleted ())

                    msg.SaveAsync (wa)
                    yield wa.Flush ()

                    msg_load = yield msg_load_future

                self.assertEqual (msg.src, msg_load.src)
                self.assertEqual (msg.dst, msg_load.dst)
                self.assertEqual (msg.Value (), msg_load.Value ())
            test_future = test ()

            core.Execute ()

        ra.Dispose ()
        wa.Dispose ()

        test_future.Result ()

    def testError (self):
        msg = Message (b'dst', b'src')
        try: raise ValueError ('test error')
        except Exception:
            msg.ErrorSet (sys.exc_info ())

        with self.assertRaises (ValueError):
            msg.Value ()

        # serialize
        stream = io.BytesIO ()
        msg.Save (stream)
        stream.seek (0)
        msg_load = Message.FromStream (stream)

        self.assertEqual (msg_load.src, msg.src)
        self.assertEqual (msg_load.dst, msg.dst)
        with self.assertRaises (ValueError):
            msg_load.Value ()

    def testResponse (self):
        msg = Message (b'dst', b'src')

        self.assertEqual (msg.dst, b'dst')
        self.assertEqual (msg.src, b'src')

        msg_resp = msg.Response ()

        self.assertEqual (msg_resp.dst, msg.src)
        self.assertEqual (msg_resp.src, msg.dst)

# vim: nu ft=python columns=120 :
