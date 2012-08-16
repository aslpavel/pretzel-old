# -*- coding: utf-8 -*-
import unittest

from .inotify import *
from ..async import *
from ..disposable import *

__all__ = ('FileMonitorInotifyTest',)
#------------------------------------------------------------------------------#
# File Monitor Inotify                                                         #
#------------------------------------------------------------------------------#
class FileMonitorInotifyTest (unittest.TestCase):
    def test (self):
        @Async
        def main ():
            with CompositeDisposable () as dispose:
                # stream
                stream = open (__file__)
                dispose += stream
                Core.Instance ().Idle ().Continue (lambda future: stream.close ())

                # monitor
                file_monitor = FileMonitor ()
                dispose += file_monitor

                # watch
                file_watch = file_monitor.Watch (stream.name, FM_CLOSE_NOWRITE)
                dispose += file_watch

                # init
                try:
                    changed, timeout = file_watch.Changed (), Core.Instance ().Sleep (1)
                    self.assertFalse  (stream.closed, 'File has been closed too early')
                    result = yield AnyFuture (changed, timeout)
                finally:
                    timeout.Dispose ()
                    changed.Dispose ()

                # check
                self.assertTrue  (stream.closed, 'File was not closed')
                self.assertEqual (result, changed, 'Test timeouted')
                self.assertTrue  (result, result.Result () [1] & FM_CLOSE_NOWRITE)

        with Core.Instance ():
            main_future = main ()
        main_future.Result ()

# vim: nu ft=python columns=120 :
