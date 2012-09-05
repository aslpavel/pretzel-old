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

    #--------------------------------------------------------------------------#
    # Message                                                                  #
    #--------------------------------------------------------------------------#
    def Info (self, *args, **keys): self.message ('[info] ', args, keys)
    def Warning (self, *args, **keys): self.message ('[warn] ', args, keys)
    def Error (self, *args, **keys): self.message ('[error] ', args, keys)

    #--------------------------------------------------------------------------#
    # Observe                                                                  #
    #--------------------------------------------------------------------------#
    def Observe (self, future, *args, **keys):
        source = keys.get ('source')
        if source is None:
            self.write ('[busy] ', *args)
        else:
            self.write ('[busy] [{}] '.format (source), *args)

        begin = time.time ()

        def continuation (future):
            # elapsed
            seconds = time.time () - begin
            hours,   seconds = divmod (seconds, 3600)
            minutes, seconds = divmod (seconds, 60)
            elapsed = '[{:0>2.0f}:{:0>2.0f}:{:0>4.1f}] '.format (hours, minutes, seconds)

            # output
            texts = [] if source is None else ['[{}] '.format (source)]
            error = future.Error ()
            if error is None:
                texts.insert (0, '[done] ')
                texts.extend (args)

                # result
                result = future.Result ()
                if result is not None:
                    texts.extend ((': ', result))
            else:
                texts.insert (0, '[fail] ')
                texts.extend (args)
                texts.extend ((': ', str (error [1])))

            self.write (*texts)

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

        self.stream.write ('\n')
        self.stream.flush ()

    def message (self, tag, args, keys):
        self.stream.write (tag)

        source = keys.get ('source')
        if source is not None:
            self.stream.write ('[{}] '.format (source))

        self.write (*args)

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
