# -*- coding: utf-8 -*-
import codecs

from .csi import *
from ..disposable import Disposable

__all__ = ('Text', 'Color', 'TEXT_ENCODING',
           'COLOR_NONE', 'COLOR_BLACK', 'COLOR_RED', 'COLOR_GREEN', 'COLOR_YELLOW',
           'COLOR_BLUE', 'COLOR_MAGENTA', 'COLOR_CYAN','COLOR_WHITE', 'COLOR_DEFAULT',
           'ATTR_NONE', 'ATTR_NORMAL', 'ATTR_BOLD', 'ATTR_ITALIC', 'ATTR_UNDERLINE',
           'ATTR_BLINK', 'ATTR_NEGATIVE', 'ATTR_FORCE')

TEXT_ENCODING = 'utf-8'
#------------------------------------------------------------------------------#
# Text                                                                         #
#------------------------------------------------------------------------------#
class Text (object):
    __slots__ = ('length', 'chunks', 'stack',)
    encoder   = codecs.getencoder (TEXT_ENCODING)

    def __init__ (self, *values):
        self.length = 0
        self.chunks = []
        self.stack  = ColorStack ()

        if values is not None:
            for value in values:
                self.Write (*value)

    #--------------------------------------------------------------------------#
    # Write                                                                    #
    #--------------------------------------------------------------------------#
    def Write (self, value, color = None):
        if color:
            self.chunks.append (self.stack.Push (color))

        string, length = self.encoder (value if hasattr (value, 'encode') else str (value))
        self.length += length
        self.chunks.append (string)

        if color:
            self.chunks.append (self.stack.Pop ())

    def WriteBytes (self, value):
        self.chunks.append (value)

    #--------------------------------------------------------------------------#
    # Color                                                                    #
    #--------------------------------------------------------------------------#
    def Color (self, color):
        self.chunks.append (self.stack.Push (color))
        return Disposable (lambda: self.chunks.append (self.stack.Pop ()))

    #--------------------------------------------------------------------------#
    # Length                                                                   #
    #--------------------------------------------------------------------------#
    def __len__ (self): return self.Length ()
    def Length  (self):
        return self.length

    #--------------------------------------------------------------------------#
    # Encode                                                                   #
    #--------------------------------------------------------------------------#
    def Encode (self):
        self.Dispose ()
        return b''.join (chunk for chunk in self.chunks if not chunk.startswith (CSI_ESCAPE))

    def EncodeCSI (self):
        self.Dispose ()
        return b''.join (self.chunks)

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        while self.stack:
            self.chunks.append (self.stack.Pop ())

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

# vim: nu ft=python columns=120 :
