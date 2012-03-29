# -*- coding: utf-8 -*-
import sys

from .text_logger import *
from .composite_logger import *
try:
    from .console_logger import *
except ImportError:
    ConsoleLogger = TextLogger

__all__ = ('ConsoleLogger', 'TextLogger', 'LoggerCreate', 'CompositeLogger')
#------------------------------------------------------------------------------#
# Logger Create                                                                #
#------------------------------------------------------------------------------#
def LoggerCreate (stream = None):
    stream = sys.stderr if stream is None else stream
    if stream.isatty ():
        return ConsoleLogger (stream)
    return TextLogger (stream)
# vim: nu ft=python columns=120 :
