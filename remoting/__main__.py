#! /usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function
import time
import itertools

from . import *
from ..app import *
#------------------------------------------------------------------------------#
# Remote Objects                                                               #
#------------------------------------------------------------------------------#
class Remote (object):
    def __init__ (self):
        self.count = itertools.count ()

    def Method (self):
        return next (self.count)

def RemoteFunction ():
    return 1

#------------------------------------------------------------------------------#
# Benchmark                                                                    #
#------------------------------------------------------------------------------#
Count = 1 << 13
class Benchmark (object):
    def __init__ (self, async):
        self.async = async
        self.results = []

        self.future = None
        self.started, self.stopped = None, None

    #--------------------------------------------------------------------------#
    # Run                                                                      #
    #--------------------------------------------------------------------------#
    def Run (self):
        self.started = time.time ()
        for count in range (Count):
            self.async ().Continue (self.result_append)

        self.future = Future ()
        return self.future

    #--------------------------------------------------------------------------#
    # Properties                                                               #
    #--------------------------------------------------------------------------#
    @property
    def Results (self):
        return self.results

    @property
    def Elapsed (self):
        return self.stopped - self.started

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    def result_append (self, future):
        error = future.Error ()
        if error is None:
            self.results.append (future.Result ())
            if len (self.results) == Count:
                self.stopped = time.time ()
                self.future.ResultSet (self)
        else:
            self.stopped = time.time ()
            self.future.ErrorSet (error)

#------------------------------------------------------------------------------#
# Main                                                                         #
#------------------------------------------------------------------------------#
output_template = """
  Type       Total   Per Call   Calls/Sec
  ---------  ------  ---------  --------
  Method   : {0:6<.3f}s  {1:6<.6f}s  {2}
  Function : {3:6<.3f}s  {4:6<.6f}s  {5}
"""

@Async
def Main (app):
    with ForkDomain (app.Core) as domain:
        started = time.time ()
        with app.Log.Pending ('Domain Start'):
            yield domain.Run ()
        instance = domain.InstanceCreate (Remote)

        with app.Log.Pending ('Method'):
            method_bench = yield Benchmark (lambda: instance.Method.Async ()).Run ()
            if method_bench.Results != list (range (Count)):
                raise ValueError ('Method benchmark failed')

        with app.Log.Pending ('Function'):
            func_bench = yield Benchmark (lambda: domain.Call.Async (RemoteFunction)).Run ()
            if func_bench.Results != [1,] * Count:
                raise ValueError ('Function benchmark failed')
        stopped = time.time ()

    # output result
    app.Log.Info ('Count:{0} Elapsed:{1:.1f}s'.format (Count, stopped - started))
    print (output_template.format (
        method_bench.Elapsed, method_bench.Elapsed / Count, int (Count / method_bench.Elapsed),
        func_bench.Elapsed,   func_bench.Elapsed / Count,   int (Count / func_bench.Elapsed)))

#------------------------------------------------------------------------------#
# Entry Point                                                                  #
#------------------------------------------------------------------------------#
if __name__ == '__main__':
    Application (Main, 'remoting benchmark')
# vim: nu ft=python columns=120 :
