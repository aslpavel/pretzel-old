# -*- coding: utf-8 -*-
import sys
import time

from .log import Log
from ..console import Text, TEXT_ENCODING

__all__ = ('TextLogger',)
#------------------------------------------------------------------------------#
# TextLogger                                                                   #
#------------------------------------------------------------------------------#
class TextLogger (object):
    def __init__ (self, stream = None):
        self.stream = stream or sys.stderr
        self.start_time = time.time ()

    #--------------------------------------------------------------------------#
    # Message                                                                  #
    #--------------------------------------------------------------------------#
    def Info (self, *args, **keys):
        self.write_prefix ('info', keys)
        self.write (*args)

        self.stream.write ('\n')
        self.stream.flush ()

    def Warning (self, *args, **keys):
        self.write_prefix ('warn', keys)
        self.write (*args)

        self.stream.write ('\n')
        self.stream.flush ()

    def Error (self, *args, **keys):
        self.write_prefix ('erro', keys)
        self.write (*args)

        self.stream.write ('\n')
        self.stream.flush ()

    #--------------------------------------------------------------------------#
    # Observe                                                                  #
    #--------------------------------------------------------------------------#
    def Observe (self, future, *args, **keys):
        self.write_prefix ('busy', keys)
        self.write (*args)

        self.stream.write ('\n')
        self.stream.flush ()

        def continuation (future):
            error = future.Error ()
            if error is None:
                self.write_prefix ('done', keys)
                self.write (*args)

                result = future.Result ()
                if result is not None:
                    self.stream.write (': ')
                    self.stream.write (str (result))

            else:
                self.write_prefix ('fail', keys)
                self.write (*args)

                self.stream.write (': ')
                self.stream.write (str (error [1]))

            self.stream.write ('\n')
            self.stream.flush ()

        future.Continue (continuation)
        return future

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    def write (self, *texts):
        for text in texts:
            if isinstance (text, Text):
                self.stream.write (text.Encode ().decode (TEXT_ENCODING))
            else:
                self.stream.write (str (text))

    def write_prefix (self, tag, keys):
        seconds = time.time () - self.start_time
        hours,   seconds = divmod (seconds, 3600)
        minutes, seconds = divmod (seconds, 60)
        elapsed_string = '{:0>2.0f}:{:0>2.0f}:{:0>4.1f}'.format (hours, minutes, seconds)

        source = keys.get ('source')
        if source is None:
            self.stream.write ('[{}] [{}] '.format (tag, elapsed_string))
        else:
            self.stream.write ('[{}] [{}] [{}] '.format (tag, elapsed_string, source))

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        pass

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

# register
Log.LoggerRegister ('text', TextLogger)

# vim: nu ft=python columns=120 :
