# -*- coding: utf-8 -*-
from .file import *

__all__ = ('SocketChannel',)

#-----------------------------------------------------------------------------#
# Socket Channel                                                              #
#-----------------------------------------------------------------------------#
class SocketChannel (FileChannel):
    def __init__ (self, sock):
        self.sock = sock

        FileChannel.__init__ (self, sock.core, sock.fileno (), sock.fileno ())
# vim: nu ft=python columns=120 :
