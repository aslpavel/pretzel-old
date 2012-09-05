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
    def Info (self, *texts): self.write ('[info] ', *texts)
    def Warning (self, *texts): self.write ('[warn] ', *texts)
    def Error (self, *texts): self.write ('[error] ', *texts)

    #--------------------------------------------------------------------------#
    # Observe                                                                  #
    #--------------------------------------------------------------------------#
    def Observe (self, future, *args, **keys):
        self.write ('[busy] ', *args)
        start = time.time ()
        
        def continuation (future):
            # elapsed
            seconds = time.time () - start
            hours,   seconds = divmod (seconds, 3600)
            minutes, seconds = divmod (seconds, 60)

            # output
            texts  = ['[{:0>2.0f}:{:0>2.0f}:{:0>4.1f}] '.format (hours, minutes, seconds)]
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
