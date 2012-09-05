# -*- coding: utf-8 -*-
import os
import socket

from .service import Service
from ..message import Message
from ...log import Log
from ...console import Text
from ...async import DummyAsync

__all__ = ('LoggerService',)
#------------------------------------------------------------------------------#
# Logger Service                                                               #
#------------------------------------------------------------------------------#
class LoggerService (Service):
    NAME    = b'logger::'
    MESSAGE = b'logger::message'
    OBSERVE = b'logger::observe'

    MESSAGE_INFO = 0
    MESSAGE_WARN = 1
    MESSAGE_ERRO = 2

    def __init__ (self, attach = None):
        Service.__init__ (self,
            handlers = (
                (self.MESSAGE, self.message_handler),
                (self.OBSERVE, self.observe_handler)))

        if attach:
            self.Attach ()

    #--------------------------------------------------------------------------#
    # Public                                                                   #
    #--------------------------------------------------------------------------#
    def Attach (self):
        return Log.LoggerAttach (self)

    #--------------------------------------------------------------------------#
    # Logger Interface                                                         #
    #--------------------------------------------------------------------------#
    def Info (self, *args, **keys):    self.message_send (self.MESSAGE_INFO, args, keys)
    def Warning (self, *args, **keys): self.message_send (self.MESSAGE_WARN, args, keys)
    def Error (self, *args,  **keys):  self.message_send (self.MESSAGE_ERRO, args, keys)

    def Observe (self, future, *args, **keys):
        source = keys.get ('source')
        if source is None:
            keys ['source'] = '{}/{}'.format (socket.gethostname (), os.getpid ())

        self.domain.channel.Send (Message.FromValue (self.domain.Pack ((future, args, keys)), self.OBSERVE))
        return future

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    def message_send (self, type, args, keys):
        args = [(arg if isinstance (arg, Text) else str (arg)) for arg in args]
        source = keys.get ('source')
        if source is None:
            keys ['source'] = '{}/{}'.format (socket.gethostname (), os.getpid ())

        self.domain.channel.Send (Message.FromValue (self.domain.Pack ((type, args, keys)), self.MESSAGE))

    @DummyAsync
    def message_handler (self, message):
        type, args, keys = self.domain.Unpack (message.Value ())
        if type == self.MESSAGE_INFO:
            Log.Info (*args, **keys)
        elif type == self.MESSAGE_WARN:
            Log.Warn (*args, **keys)
        elif type == self.MESSAGE_ERRO:
            Log.Error (*args, **keys)

    @DummyAsync
    def observe_handler (self, message):
        future, args, keys = self.domain.Unpack (message.Value ())
        Log.Observe (future, *args, **keys)

# vim: nu ft=python columns=120 :
