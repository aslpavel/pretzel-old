# -*- coding: utf-8 -*-
import unittest

from ..process import Process, ProcessCall, ProcessWaiter, PIPE
from ..async import Idle, Future, Core
from ..async.tests import AsyncTest

#------------------------------------------------------------------------------#
# Process Call Tests                                                           #
#------------------------------------------------------------------------------#
class ProcessTest (unittest.TestCase):
    """Process unit tests
    """

    @AsyncTest
    def testCall (self):
        """Process call
        """

        command = ['python', '-c', """
import sys
for value in range (int (input ())):
    if value % 2 == 1:
        sys.stderr.write (str (value))
    else:
        sys.stdout.write (str (value))
sys.stderr.flush ()
sys.stdout.flush ()
sys.exit (117)
"""]

        out, err, code = yield ProcessCall (command, input = b'10', check = False)

        self.assertEqual (code, 117)
        self.assertEqual (out, b'02468')
        self.assertEqual (err, b'13579')

    @AsyncTest
    def testCleanup (self):
        """Process cleanup
        """
        with Process (['cat'], stdin = PIPE, stdout = PIPE, stderr = PIPE) as proc:
            self.assertTrue (proc.Stdin.CloseOnExec ())
            self.assertTrue (proc.Stdout.CloseOnExec ())
            self.assertTrue (proc.Stderr.CloseOnExec ())

        yield proc

        self.assertEqual (proc.Stdin, None)
        self.assertEqual (proc.Stdout, None)
        self.assertEqual (proc.Stderr, None)

    @AsyncTest
    def testBad (self):
        """Test bad executable
        """
        with self.assertRaises (OSError):
            yield ProcessCall (['does_not_exists'])

        # wait for full process termination (SIGCHLD)
        process_waiter = ProcessWaiter.Instance ()
        for _ in Core.Instance ():
            if not process_waiter.conts:
                break

    @AsyncTest
    def testStress (self):
        procs = [ProcessCall (['uname']) for _ in range (20)]

        yield Future.All (procs)
        for proc in procs:
            proc.Result ()

        yield Idle ()
        self.assertFalse (ProcessWaiter.Instance ().conts)

# vim: nu ft=python columns=120 :
