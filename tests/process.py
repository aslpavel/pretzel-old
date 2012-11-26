# -*- coding: utf-8 -*-
import unittest

from ..process import Process, ProcessCall, PIPE
from ..async import Core
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
        yield Core.Instance ().WhenIdle ()

        with Process (['cat'], stdin = PIPE, stdout = PIPE, stderr = PIPE) as proc:
            self.assertTrue (proc.Stdin.CloseOnExec ())
            self.assertTrue (proc.Stdout.CloseOnExec ())
            self.assertTrue (proc.Stderr.CloseOnExec ())

        self.assertEqual (proc.Stdin, None)
        self.assertEqual (proc.Stdout, None)
        self.assertEqual (proc.Stderr, None)

# vim: nu ft=python columns=120 :
