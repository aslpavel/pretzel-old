#! /usr/bin/python
# -*- coding: utf-8 -*-
import sys
import os
import io
import time
import getopt
import itertools

from .message import Message
from .domains.fork import ForkDomain
from .domains.ssh  import SSHDomain

from ..app import ApplicationType
from ..async import Async, Future
from ..log import Log

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
    sys.stderr.write ('''Usage: {name} [options] [ssh|fork]
options:
    -p   : run inside profiler
    -h|? : show this help message
'''.format (name = __package__))

class Main (object):
    def __init__ (self, domain_type, domain_args):
        self.domain_type = domain_type
        self.domain_args = domain_args

    @Async
    def __call__ (self, app):
        if self.domain_type == 'fork':
            domain = ForkDomain ()
        elif domain_type == 'ssh':
            domain = SSHDomain  (self.domain_args [0] if self.domain_args else 'localhost')
        else:
            Log.Error ('Unknown domain type: \'{}\''.format (domain_type))
            Usage ()
            sys.exit (1)

        with domain:
            yield domain.Connect ()
            #----------------------------------------------------------------------#
            # Method                                                               #
            #----------------------------------------------------------------------#
            proxy = yield domain.Call.Proxy (Remote)
            with Log ('Method'):
                with Timer () as method_timer:
                    futures = [proxy.Method () for i in range (CallCount)]
                    yield Future.WhenAll (futures)

            if sorted (list (future.Result () for future in futures)) != list (range (CallCount)):
                raise ValueError ('Method benchmark failed')

            #----------------------------------------------------------------------#
            # Function                                                             #
            #----------------------------------------------------------------------#
            with Log ('Function'):
                with Timer () as func_timer:
                    futures = [domain.Call (RemoteFunction) for i in range (CallCount)]
                    yield Future.WhenAll (futures)

            for future in futures:
                if future.Result () != 1:
                    raise ValueError ('Function benchmark failed')

            #----------------------------------------------------------------------#
            # Message                                                              #
            #----------------------------------------------------------------------#
            with Log ('Message'):
                stream = io.BytesIO ()
                with Timer () as msg_timer:
                    for i in range (MsgCount):
                        Message.FromValue (b'DATA', b'dummy::').Save (stream)
                        stream.seek (0)
                        Message.FromStream (stream)
                        stream.seek (0)
                        stream.truncate ()

        #--------------------------------------------------------------------------#
        # Output                                                                   #
        #--------------------------------------------------------------------------#
        Log.Info ('Elapsed:{:.1f}s'.format (method_timer.Elapsed + func_timer.Elapsed + msg_timer.Elapsed))
        sys.stdout.write (OutputTemplate.format (
            method_timer.Elapsed, method_timer.Elapsed / CallCount, int (CallCount / method_timer.Elapsed),
            func_timer.Elapsed,   func_timer.Elapsed / CallCount,   int (CallCount / func_timer.Elapsed),
            msg_timer.Elapsed,    msg_timer.Elapsed / MsgCount,     int (MsgCount  / msg_timer.Elapsed)))

#------------------------------------------------------------------------------#
# Entry Point                                                                  #
#------------------------------------------------------------------------------#
if __name__ == '__main__':
    #--------------------------------------------------------------------------#
    # Arguments                                                                #
    #--------------------------------------------------------------------------#
    try:
        opts, args = getopt.getopt(sys.argv[1:], '?hp')
    except getopt.GetoptError as error:
        sys.stderr.write (':: error: {}\n'.format (error))
        Usage ()
        sys.exit (1)

    # defaults
    profile     = False
    domain_type = args [0] if args else 'fork'

    for o, a in opts:
        if o == '-h':
            Usage ()
            sys.exit (0)
        elif o == '-p':
            profile = True
        else:
            assert False, 'Unhandled option: {}'.format (o)

    main = Main (domain_type, args [1:])

    #--------------------------------------------------------------------------#
    # Application                                                              #
    #--------------------------------------------------------------------------#
    if '-p' in sys.argv:
        from cProfile import runctx
        runctx ('ApplicationType (main, \'benchmark\')', globals (), locals (), sort = 'time')
    else:
        ApplicationType (main, 'benchmark')
# vim: nu ft=python columns=120 :
