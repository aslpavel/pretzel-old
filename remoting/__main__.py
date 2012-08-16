#! /usr/bin/python
# -*- coding: utf-8 -*-
import sys
import os
import io
import time
import itertools

from . import *
from .message import *
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
# Timer                                                                        #
#------------------------------------------------------------------------------#
class Timer (object):
    def __init__ (self):
        self.start, self.stop = None, None

    def __enter__ (self):
        self.start = time.time ()
        return self

    def __exit__ (self, et, oe, tb):
        self.stop = time.time ()
        return False

    @property
    def Elapsed (self):
        return self.stop - self.start if self.start and self.stop else None

    @property
    def ElapsedString (self):
        return 'None' if self.Elapsed is None else '{:.3f}'.format (self.Elapsed ())

#------------------------------------------------------------------------------#
# Main                                                                         #
#------------------------------------------------------------------------------#
OutputTemplate = """
  Type       Total   Per Call   Calls/Sec
  ---------  ------  ---------  --------
  Method   : {:6<.3f}s  {:6<.6f}s  {}
  Function : {:6<.3f}s  {:6<.6f}s  {}
  Message  : {:6<.3f}s  {:6<.6f}s  {}

"""
CallCount = 1 << 13
MsgCount  = 1 << 18

def Usage ():
    sys.stderr.write ('Usage: {} [ssh|fork]\n'.format (__package__))

@Async
def Main (app):
    if '-h' in sys.argv:
        Usage ()
        sys.exit (0)

    domain_type = 'fork' if len (sys.argv) < 2 else sys.argv [1]
    if domain_type == 'fork':
        domain = ForkDomain ()
    elif domain_type == 'ssh':
        domain = SSHDomain  ('localhost' if len (sys.argv) < 3 else sys.argv [2])
    else:
        app.Log.Error ('Unknown domain type: \'{}\''.format (domain_type))
        Usage ()
        sys.exit (1)

    with domain:
        yield domain.Connect ()
        #----------------------------------------------------------------------#
        # Method                                                               #
        #----------------------------------------------------------------------#
        proxy = yield domain.Call.Proxy (Remote)
        with app.Log.Pending ('Method'):
            with Timer () as method_timer:
                futures = [proxy.Method () for i in range (CallCount)]
                yield AllFuture (*futures)

        for index, future in enumerate (futures):
            if index != future.Result ():
                raise ValueError ('Method benchmark failed')
        
        #----------------------------------------------------------------------#
        # Function                                                             #
        #----------------------------------------------------------------------#
        with app.Log.Pending ('Function'):
            with Timer () as func_timer:
                futures = [domain.Call (RemoteFunction) for i in range (CallCount)]
                yield AllFuture (*futures)

        for future in futures:
            if future.Result () != 1:
                raise ValueError ('Function benchmark failed')
            
        #----------------------------------------------------------------------#
        # Message                                                              #
        #----------------------------------------------------------------------#
        with app.Log.Pending ('Message'):
            stream = io.BytesIO ()
            with Timer () as msg_timer:
                for i in range (MsgCount):
                    Message (b'dummy::', b'DATA').Save (stream)
                    stream.seek (0)
                    Message.Load (stream)
                    stream.seek (0)
                    stream.truncate ()
        
    #--------------------------------------------------------------------------#
    # Output                                                                   #
    #--------------------------------------------------------------------------#
    app.Log.Info ('Elapsed:{:.1f}s'.format (method_timer.Elapsed + func_timer.Elapsed + msg_timer.Elapsed))
    sys.stdout.write (OutputTemplate.format (
        method_timer.Elapsed, method_timer.Elapsed / CallCount, int (CallCount / method_timer.Elapsed),
        func_timer.Elapsed,   func_timer.Elapsed / CallCount,   int (CallCount / func_timer.Elapsed),
        msg_timer.Elapsed,    msg_timer.Elapsed / MsgCount,     int (MsgCount  / msg_timer.Elapsed)))

#------------------------------------------------------------------------------#
# Entry Point                                                                  #
#------------------------------------------------------------------------------#
if __name__ == '__main__':
    Application (Main, 'benchmark')
# vim: nu ft=python columns=120 :
