# -*- coding: utf-8 -*-
import itertools

from ..async import Async, Future
from ..benchmark import Benchmark
from .conn import ForkConnection

#------------------------------------------------------------------------------#
# Function Benchmark                                                           #
#------------------------------------------------------------------------------#
fn_count = itertools.count (1)
def fn ():
    """Function used for benchmark
    """
    return next (fn_count)

class FuncBench (Benchmark):
    """Benchmark function call
    """
    def __init__ (self):
        Benchmark.__init__ (self, 'remoting.func', 1)
        self.conn = None

    @Async
    def Init (self):
        self.conn = yield ForkConnection ()
        self.func = self.conn (fn) ()
        if ((yield self.func), (yield self.func)) != (1, 2):
            raise ValueError ('Initialization test failed')

    def Body (self):
        return self.func

    def Dispose (self):
        conn, self.conn = self.conn, None
        if conn:
            conn.Dispose ()

class FuncAsyncBench (FuncBench):
    """Benchmark asynchronous function call
    """
    def __init__ (self):
        Benchmark.__init__ (self, 'remoting.func_async', 2048)
        self.conn = None

    def Body (self):
        return Future.All ([self.func.Await () for _ in range (self.factor)])

#------------------------------------------------------------------------------#
# Proxy Method Benchmark                                                       #
#------------------------------------------------------------------------------#
class Remote (object):
    def __init__ (self, value):
        self.value = value

    def Method (self):
        return self.value

class MethodBench (Benchmark):
    """Benchmark proxy method call
    """
    def __init__ (self):
        Benchmark.__init__ (self, 'remoting.method', 1)
        self.conn = None

    @Async
    def Init (self):
        self.conn  = yield ForkConnection ()
        self.proxy = yield +self.conn (Remote) (-1)
        self.method = self.proxy.Method ()
        if (yield self.method) != -1:
            raise ValueError ('Initialization test failed')

    def Body (self):
        return self.method

    def Disopse (self):
        proxy, self.proxy = self.proxy, None
        if proxy:
            proxy.Dispose ()
        conn, self.conn = self.conn, None
        if conn:
            conn.Dispose ()

class MethodAsyncBench (MethodBench):
    """Benchmark asynchronous proxy method call
    """
    def __init__ (self):
        Benchmark.__init__ (self, 'remoting.method_async', 1024)
        self.conn = None

    def Body (self):
        return Future.All ([self.method.Await () for _ in range (self.factor)])

#------------------------------------------------------------------------------#
# Load Benchmark Protocol                                                      #
#------------------------------------------------------------------------------#
def load_bench (runner):
    """Load benchmarks
    """
    for bench in ((
        FuncBench (),
        FuncAsyncBench (),
        MethodBench (),
        MethodAsyncBench (),
    )):
        runner.Add (bench)

# vim: nu ft=python columns=120 :
