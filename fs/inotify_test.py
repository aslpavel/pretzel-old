# -*- coding: utf-8 -*-
import unittest

from .inotify import FileMonitor, FM_CLOSE_NOWRITE
from ..tests import AsyncTest
from ..async import Future, ScopeFuture, Core
from ..disposable import CompositeDisposable

__all__ = ('FileMonitorInotifyTest',)
#------------------------------------------------------------------------------#
# File Monitor Inotify                                                         #
#------------------------------------------------------------------------------#
class FileMonitorInotifyTest (unittest.TestCase):
    @AsyncTest
    def test (self):
        core = Core.Instance ()
        with CompositeDisposable () as dispose:
            # stream
            stream = open (__file__)
            dispose += stream
            core.Idle ().Continue (lambda *_: stream.close ())

            # monitor
            file_monitor = FileMonitor ()
            dispose += file_monitor

            # watch
            file_watch = file_monitor.Watch (stream.name, FM_CLOSE_NOWRITE)
            dispose += file_watch

            # init
            with ScopeFuture () as cancel:
                changed = file_watch.Changed ()
                result  = yield Future.WhenAny ((changed, core.Sleep (1, cancel)))

                # check
                self.assertTrue  (stream.closed, 'File was not closed')
                self.assertEqual (result, changed, 'Test timeouted')
                self.assertTrue  (result, result.Result () [1] & FM_CLOSE_NOWRITE)

# vim: nu ft=python columns=120 :
