# -*- coding: utf-8 -*-
import unittest

from ..process import ProcessCall, PIPE
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

        command = ['python', '-c', '''
import sys
for value in range (int (input ())):
    if value % 2 == 1:
        sys.stderr.write (str (value))
    else:
        sys.stdout.write (str (value))''']

        out, err, code = yield ProcessCall (command, input = b'10', check = False, stdout = PIPE, stderr = PIPE)

        self.assertEqual (code, 0)
        self.assertEqual (out, b'02468')
        self.assertEqual (err, b'13579')

# vim: nu ft=python columns=120 :
