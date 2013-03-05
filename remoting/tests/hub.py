# -*- coding: utf-8 -*-
import unittest
import collections

from ..hub import Hub, HubError, Address, Sender, ReceiverSenderPair

__all__ = ('HubTest',)
#------------------------------------------------------------------------------#
# Hub Test                                                                     #
#------------------------------------------------------------------------------#
class HubTest (unittest.TestCase):
    """Hub unit tests
    """
    def testAddress (self):
        """Address tests
        """
        addr = Hub.Instance ().Address ()
        self.assertEqual (len (addr), 1)

        # route
        addr_111 = addr + (111,)
        self.assertTrue (isinstance (addr_111, Address))
        self.assertEqual (addr_111, Address ((111,)))

        # strip
        self.assertEqual (addr_111 - 1, addr)

        # hub
        self.assertFalse (Hub.Instance ().handlers)

    def testSender (self):
        """Sender tests
        """
        r0, s0 = ReceiverSenderPair ()

        # raise error when nobody is receiving
        with self.assertRaises (HubError):
            s0.Send ('test')

        queue = collections.deque ()
        def handler (msg, src, dst):
            queue.append ((msg, src, dst))
            return True
        # register handler
        r0.On (handler)

        # send
        s0.Send ('message 0')
        msg, src, dst = queue.popleft ()
        self.assertEqual (msg, 'message 0')
        self.assertEqual (src, None)
        self.assertEqual (dst, r0.dst)

        # send with source
        r1, s1 = ReceiverSenderPair ()
        s0.Send ('message 1', s1)
        msg, src, dst = queue.popleft ()
        self.assertEqual (msg, 'message 1')
        self.assertEqual (src, s1)
        self.assertEqual (dst, r0.dst)

        # call
        future = s0 ('message 2')
        msg, src, dst = queue.popleft ()
        self.assertEqual (msg, 'message 2')
        self.assertTrue (isinstance (src, Sender))
        self.assertEqual (dst, r0.dst)

        self.assertFalse (future.IsCompleted ())
        src.Send ('done')
        self.assertTrue  (future.IsCompleted ())
        self.assertEqual (future.GetResult (), ('done', None))

        # unregister handler
        self.assertEqual (len (queue), 0)
        r0.Off (handler)

        # hub
        self.assertFalse (Hub.Instance ().handlers)

    def testReceiver (self):
        """Receiver tests
        """
        r0, s0 = ReceiverSenderPair ()

        queue_single = collections.deque ()
        def handler_single (msg, src, dst):
            queue_single.append ((msg, src, dst))
            return False

        queue_multi = collections.deque ()
        def handler_multi (msg, src, dst):
            queue_multi.append ((msg, src, dst))
            return True

        # subscription
        r0.On (handler_single)
        r0.On (handler_multi)

        s0.Send ('message 0')
        self.assertEqual (queue_single.popleft (), ('message 0', None, s0.dst))
        self.assertEqual (queue_multi.popleft (), ('message 0', None, s0.dst))

        s0.Send ('message 1')
        self.assertEqual (len (queue_single), 0)
        self.assertEqual (queue_multi.popleft (), ('message 1', None, s0.dst))

        # un-subscription
        self.assertFalse (r0.Off (handler_single))
        self.assertTrue (r0.Off (handler_multi))

        # awaitable -> Future<Tuple<Message, Sender?>>
        future = r0.Await ()
        self.assertFalse (future.IsCompleted ())

        s0.Send ('message 2')
        self.assertTrue (future.IsCompleted ())
        self.assertEqual (future.GetResult (), (('message 2', None), None))

        # hub
        self.assertFalse (Hub.Instance ().handlers)

    def testRequestResponse (self):
        """Request|Reponse tests
        """
        r0, s0 = ReceiverSenderPair ()

        # response with result
        def result_handler (msg, src, dst):
            self.assertEqual (msg, 'request')
            with src.Response () as send:
                send ('response')
            return False
        r0.On (result_handler)

        f0 = s0.Request ('request')
        self.assertEqual (f0.Result (), 'response')

        # response with error
        def error_handler (msg, src, dst):
            self.assertEqual (msg, 'error')
            with src.Response ():
                raise ValueError ('error')
            return False
        r0.On (error_handler)

        f1 = s0.Request ('error')
        with self.assertRaises (ValueError):
            f1.Result ()

        # hub
        self.assertFalse (Hub.Instance ().handlers)

    def testFaultyHandler (self):
        r, s = ReceiverSenderPair ()
        results = set ()

        try:
            def prev_handler (msg, src, dst):
                results.add ('prev')
                return False
            r.On (prev_handler)

            def faulty_handler (msg, src, dst):
                results.add ('bad')
                raise ValueError ()
            r.On (faulty_handler)

            def next_handler (msg, src, dst):
                results.add ('next')
                return False
            r.On (next_handler)

            with self.assertRaises (ValueError):
                s.Send ('test')
            self.assertEqual (results, {'prev', 'bad', 'next'})

            results.clear ()
            with self.assertRaises (ValueError):
                s.Send ('test')
            self.assertEqual (results, {'bad'})

        finally:
            r.Off (prev_handler)
            r.Off (faulty_handler)
            r.Off (next_handler)

            self.assertFalse (Hub.Instance ().handlers)

    def testReentrancy (self):
        r, s = ReceiverSenderPair ()
        results = []
        try:
            def handler (msg, src, dst):
                results.append (msg)
                if msg == 'first':
                    # new message received inside handler
                    s.Send ('second')
                return True
            r.On (handler)

            s.Send ('first')
            self.assertEqual (results, ['first', 'second'])

        finally:
            r.Off (handler)

# vim: nu ft=python columns=120 :
