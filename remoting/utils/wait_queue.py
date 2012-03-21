# -*- coding: utf-8 -*-
from ...async import *

__all__ = ('WaitQueue',)
#------------------------------------------------------------------------------#
# Wait Queue                                                                   #
#------------------------------------------------------------------------------#
class WaitQueue (object):
    def __init__ (self, wait):
        self.wait = wait
        self.wait_future = SucceededFuture ()
        self.waiting = False
        self.queue = []

    def Enqueue (self, action, *args):
        self.queue.append ((action, args))
        if not self.waiting:
            self.wait_task ()

    @property
    def Future (self):
        return self.wait_future

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def wait_task (self):
        self.waiting = True
        try:
            self.wait_future = self.wait ()
            yield self.wait_future
        finally:
            self.waiting = False

        queue, self.queue = self.queue, []
        for action, args in queue:
            action (*args)

# vim: nu ft=python columns=120 :
