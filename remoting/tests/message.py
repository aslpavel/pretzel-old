# -*- coding: utf-8 -*-
import io
import sys
import unittest

from ..message import Message
from ...async import Pipe, Core
from ...async.tests import AsyncTest

__all__ = ('MessageTest',)
#------------------------------------------------------------------------------#
# Message Test                                                                 #
#------------------------------------------------------------------------------#
class MessageTest (unittest.TestCase):
    """Message unit tests
    """

    def testSerialize (self):
        """Test serialization
        """
        msg = Message.FromValue (b'value', b'dst')

        stream = io.BytesIO ()
        msg.Save (stream)
        stream.seek (0)
        msg_load = Message.FromStream (stream)

        self.assertEqual (msg.src, msg_load.src)
        self.assertEqual (msg.dst, msg_load.dst)
        self.assertEqual (msg.Value (), msg_load.Value ())

    @AsyncTest
    def testSerializeAsync (self):
        """Test asynchronous serialization
        """
        msg = Message.FromValue (b'value', b'dst')

        with Pipe () as pipe:
            msg_load_future = Message.FromAsyncStream (pipe.Read, Core.Instance ().WhenTimeDelay (1))
            if msg_load_future.IsCompleted ():
                msg_load_future.Result ()

            msg.SaveAsync (pipe.Write)
            yield pipe.Write.Flush ()

            msg_load = yield msg_load_future

            self.assertEqual (msg.src, msg_load.src)
            self.assertEqual (msg.dst, msg_load.dst)
            self.assertEqual (msg.Value (), msg_load.Value ())

    def testError (self):
        """Test error value
        """
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
        """Test response
        """
        msg = Message (b'dst', b'src')

        self.assertEqual (msg.dst, b'dst')
        self.assertEqual (msg.src, b'src')

        msg_resp = msg.Response ()

        self.assertEqual (msg_resp.dst, msg.src)
        self.assertEqual (msg_resp.src, msg.dst)

# vim: nu ft=python columns=120 :
