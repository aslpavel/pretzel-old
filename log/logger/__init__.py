# -*- coding: utf-8 -*-
import sys

from .console_logger import *
from .text_logger import *

__all__ = ('ConsoleLogger', 'TextLogger', 'LoggerCreate')
#------------------------------------------------------------------------------#
# Logger Create                                                                #
#------------------------------------------------------------------------------#
def LoggerCreate (stream = None):
    stream = sys.stderr if stream is None else stream
    if stream.isatty ():
        return ConsoleLogger (stream)
    return TextLogger (stream)
# vim: nu ft=python columns=120 :
