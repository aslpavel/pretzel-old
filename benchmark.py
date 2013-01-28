#! /usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
import sys
import time
import functools
import operator

from .async import Async, AsyncReturn, DummyAsync, Core

__all__ = ('Benchmark',)
#------------------------------------------------------------------------------#
# Benchmark                                                                    #
#------------------------------------------------------------------------------#
class Benchmark (object):
    """Benchmark
    """
    default_error = 0.01
    default_time  = time.time

    min_count = 5
    max_time = 15

    def __init__ (self, name = None, factor = None):
        self.name = name or type (self).__name__
        self.factor = factor or 1

    #--------------------------------------------------------------------------#
    # Interface                                                                #
    #--------------------------------------------------------------------------#
    @DummyAsync
    def Init (self):
        """Initialize benchmark
        """

    @DummyAsync
    def Body (self):
        raise NotImplementedError ()

    def Dispose (self):
        """Dispose benchmark
        """

    #--------------------------------------------------------------------------#
    # Execute                                                                  #
    #--------------------------------------------------------------------------#
    def __call__ (self, error = None, time = None):
        """Execute benchmark
        """
        error = error or self.default_error
        time  = time  or self.default_time

        results = []
        def result (result = None):
            """Calculate mean value and standard diviation
            """
            if result is not None:
                results.append (float (result))

            if len (results) < self.min_count:
                return None, None

            result_mean = functools.reduce (operator.add, results, 0) / len (results)
            result_error = (functools.reduce (operator.add,
                    ((result - result_mean)**2 for result in results), 0) / (len (results) - 1))
            return result_mean, result_error

        @Async
        def run ():
            """Run benchmark
            """
            yield self.Init ()

            begin_time = time ()
            while True:
                start_time = time ()
                yield self.Body ()
                stop_time = time ()

                result_mean, result_error = result (stop_time - start_time)
                if result_mean is None:
                    continue

                if result_error / result_mean <= error or (stop_time - begin_time) >= self.max_time:
                    AsyncReturn ((result_mean, result_error))

        # create new execution core
        with Core.Instance () as core:
            run_future = run ().Then (lambda r, e: core.Dispose ())
            if not core.Disposed:
                core ()

        result_mean, result_error = run_future.Result ()
        return self.name, result_mean/self.factor, result_error/result_mean, len (results)*self.factor

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

#------------------------------------------------------------------------------#
# Benchmark Runners                                                            #
#------------------------------------------------------------------------------#
class TextBenchmarkRunner (object):
    def __init__ (self, file = None):
        self.benchs = []
        self.file = sys.stdout

    def Add (self, bench):
        """Add benchmark
        """
        self.benchs.append (bench)

    def AddModule (self, module):
        """Add benchmark from module
        """
        getattr (module, 'load_bench') (self)

    def __call__ (self, error_thresh = None, timer = None):
        # run benchmarks
        lines = [('Name', 'Time', 'Count', 'Count/Time', 'Deviation',)]
        time_total = 0
        for bench in self.benchs:
            name, time, error, count = bench (error_thresh, timer)
            lines.append ((name,                 # name
                '{:.3f}s'.format (time * count), # time
                '{:.0f}'.format (count),         # count
                '{:.0f}'.format (1/time),        # count/time
                '{:.3f}%'.format (error * 100),  # error
            ))
            time_total += time * count
            self.file.write ('.')
            self.file.flush ()
        self.file.write ('\n{}\n'.format ('-' * 70))
        self.file.write ('Ran {} benchmarks in {:.3f}s\n\n'.format (len (lines), time_total))

        # calculate columns width
        widths = [0] * len (lines [0])
        for line in lines:
            for index in range (len (widths)):
                widths [index] = max (widths [index], len (line [index]))

        for index in range (len (widths)):
            widths [index] += 2

        format = '  ' + ''.join ('{{:<{}}}'.format (width) for width in widths) + '\n'
        lines.insert (1, tuple ('-' * (width - 1) for width in widths))
        for line in lines:
            self.file.write (format.format (*line))
        self.file.write ('\n')
        self.file.flush ()

#------------------------------------------------------------------------------#
# Main                                                                         #
#------------------------------------------------------------------------------#
def Main ():
    from importlib import import_module

    bench_runner = TextBenchmarkRunner ()
    bench_runner.AddModule (import_module (__package__))
    bench_runner ()

if __name__ == '__main__':
    Main ()

# vim: nu ft=python columns=120 :
