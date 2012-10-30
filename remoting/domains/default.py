# -*- coding: utf-8 -*-
import sys
import types
import inspect
from importlib import import_module

from .domain import Domain, DomainError

from ..message import Message
from ..services.persistence import PersistenceService
from ..services.linker import LinkerService
from ..services.importer import ImporterService
from ..services.future import FutureService
from ..services.channel import ChannelService
from ..services.logger import LoggerService

from ...async import Async, AsyncReturn
from ...bootstrap import Tomb

__all__ = ('LocalDomain', 'RemoteDomain',)
#------------------------------------------------------------------------------#
# Default Domain                                                               #
#------------------------------------------------------------------------------#
class DefaultDomain (Domain):
    CORE_NAME    = b'core::object'
    DOMAIN_NAME  = b'domain::object'
    CHANNEL_NAME = b'channel::object'

    def __init__ (self, channel, insert_importer, attach_logger):
        Domain.__init__ (self, channel, [
            PersistenceService (),
            ImporterService (insert = insert_importer),
            LinkerService (),
            FutureService (),
            ChannelService (),
            LoggerService (attach = attach_logger)])

    #--------------------------------------------------------------------------#
    # Request | Response                                                       #
    #--------------------------------------------------------------------------#
    @Async
    def Request (self, destination, *args):
        request  = Message.FromValue (self.Pack (args), destination)
        response = self.channel.RecvTo (request.src)

        self.channel.Send (request)
        AsyncReturn (self.Unpack ((yield response).Value ()))

    def Response (self, message):
        return Response (self, message)

    #--------------------------------------------------------------------------#
    # Connect                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def Connect (self):
        yield Domain.Connect (self)

        # register (core|channel|domain) as persistent
        for obj, name in (
            (self, self.DOMAIN_NAME),
            (self.channel, self.CHANNEL_NAME),
            (self.channel.core, self.CORE_NAME)):
                self.dispose += self.RegisterObject (obj, name)

#------------------------------------------------------------------------------#
# Response                                                                     #
#------------------------------------------------------------------------------#
class ResponseReturn (BaseException): pass
class Response (object):
    __slots__ = ('domain', 'message',)

    def __init__ (self, domain, message):
        self.domain  = domain
        self.message = message

    #--------------------------------------------------------------------------#
    # Properties                                                               #
    #--------------------------------------------------------------------------#
    @property
    def Args (self):
        return self.domain.Unpack (self.message.Value ())

    #--------------------------------------------------------------------------#
    # Return                                                                   #
    #--------------------------------------------------------------------------#
    def __call__ (self, result = None):
        raise ResponseReturn (result)

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        response = self.message.Response ()

        if et is None:
            response.ValueSet (self.domain.Pack (None))
        elif et == ResponseReturn:
            try:
                response.ValueSet (self.domain.Pack (eo.args [0]))
            except Exception:
                response.ErrorSet (sys.exc_info ())
        elif issubclass (et, Exception):
            response.ErrorSet ((et, eo, tb))
        else:
            return False

        self.domain.channel.Send (response)
        return True

#------------------------------------------------------------------------------#
# Local Domain                                                                 #
#------------------------------------------------------------------------------#
class LocalDomain (DefaultDomain):
    def __init__ (self, channel, push_main):
        DefaultDomain.__init__ (self, channel, insert_importer = False, attach_logger = False)

        self.push_main = push_main is None or push_main

    @Async
    def Connect (self):
        yield DefaultDomain.Connect (self)

        if self.push_main:
            yield self.do_push_main ()

    #--------------------------------------------------------------------------#
    # Push Main                                                                #
    #--------------------------------------------------------------------------#
    @Async
    def do_push_main (self):
        if not self.IsConnected:
            raise DomainError ('Channel isn\'t connected')

        mainname = '_remote_main' if '_remote_main' in sys.modules else '__main__'
        main     = sys.modules [mainname]
        pkgname  = getattr (main, '__package__', None)
        if pkgname:
            tomb    = None
            topname = pkgname.split ('.') [0]
            if topname != __name__.split ('.') [0]:
                # __main__ is not a part of this (pretzel) package
                tomb = Tomb ()
                tomb.Add (sys.modules [topname])
            yield self.Call (main_import, tomb, pkgname)

        else:
            yield self.ModulePush ('_remote_main', inspect.getsource (main), inspect.getsourcefile (main))

        # persistence
        persistence_service = self.ServiceByName (PersistenceService.NAME)
        main_register (persistence_service, mainname)
        yield self.Call (main_register, persistence_service, '_remote_main')

#------------------------------------------------------------------------------#
# Remote Domain                                                                #
#------------------------------------------------------------------------------#
class RemoteDomain (DefaultDomain):
    def __init__ (self, channel):
        DefaultDomain.__init__ (self, channel, insert_importer = True, attach_logger = True)

#-----------------------------------------------------------------------------#
# Helpers                                                                     #
#-----------------------------------------------------------------------------#
def main_register (persistence, mainname):
    module = sys.modules.get (mainname)
    if module is None:
        raise ValueError ('No such module: \'{}\''.format (mainname))

    # register unpackable top level objects
    for name, value in module.__dict__.items ():
        if isinstance (value, type) or \
           isinstance (value, types.FunctionType):
            persistence.RegisterObject (value, 'main::{}'.format (name))

def main_import (tomb, pkgname):
    if '_remote_main' in sys.modules:
        return

    if tomb:
        sys.meta_path.insert (0, tomb)
    sys.modules ['_remote_main'] = import_module ('{}.__main__'.format (pkgname))

# vim: nu ft=python columns=120 :
