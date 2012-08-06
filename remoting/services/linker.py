# -*- coding: utf-8 -*-
import itertools

from .service import *
from ..utils.proxy import *
from ..message import *
from ...async import *
from ...disposable import *

__all__ = ('LinkerService',)
#------------------------------------------------------------------------------#
# Linker Service                                                               #
#------------------------------------------------------------------------------#
class LinkerService (Service):
    NAME    = b'linker::'
    CALL    = b'linker::call'
    CREATE  = b'linker::create'
    METHOD  = b'linker::method'
    PROPSET = b'linker::propset'
    PROPGET = b'linker::propget'

    def __init__ (self):
        Service.__init__ (self,
            exports = (
                ('ToProxy',     self.ToProxy),
                ('ProxyCreate', self.ProxyCreate),
                ('Call',        self.Call)),
            handlers = (
                (self.CALL,     self.call_handler),
                (self.CREATE,   self.create_handler),
                (self.METHOD,   self.method_handler),
                (self.PROPGET,  self.get_handler),
                (self.PROPSET,  self.set_handler)),
            persistence = (
                (Proxy, self.proxyPack, self.proxyUnpack),))

        # marshal mappings
        self.desc      = itertools.count ()
        self.desc2prov = {}
        self.prov2desc = {}
        next (self.desc)

    @Async
    def Connect (self, domain):
        yield Service.Connect (self, domain)

        def dispose ():
            self.desc2prov.clear ()
            self.prov2desc.clear ()
        self.dispose += Disposable (dispose)

    #--------------------------------------------------------------------------#
    # Methods                                                                  #
    #--------------------------------------------------------------------------#
    def ToProxy (self, instance):
        return Proxy (LocalProxyProvider (instance))

    def ProxyCreate (self, type, *args, **keys):
        return self.domain.Request (self.CREATE, type, args, keys)
        
    def Call (self, func, *args, **keys):
        return self.domain.Request (self.CALL, func, args, keys)
        
    #--------------------------------------------------------------------------#
    # Marshal                                                                  #
    #--------------------------------------------------------------------------#
    def proxyPack (self, proxy):
        prov = proxy._provider
        desc = self.prov2desc.get (prov)
        if desc is None:
            desc = next (self.desc) << 1
            self.desc2prov [desc], self.prov2desc [prov] = prov, desc

        return desc

    def proxyUnpack (self, desc):
        desc ^= 0x1
        prov = self.desc2prov.get (desc)
        if prov is None:
            prov = RemoteProxyProvider (self, desc)
            self.desc2prov [desc], self.prov2desc [prov] = prov, desc

        return Proxy (prov)

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    @DummyAsync
    def call_handler (self, message):
        with self.domain.Response (message) as response:
            func, args, keys = self.domain.Unpack (message.Data)
            response (func (*args, **keys))

    @DummyAsync
    def create_handler (self, message):
        with self.domain.Response (message) as response:
            type, args, keys = self.domain.Unpack (message.Data)
            response (self.ToProxy (type (*args, **keys)))

    @Async
    def method_handler (self, message):
        with self.domain.Response (message) as response:
            desc, name, args, keys = self.domain.Unpack (message.Data)
            prov = self.desc2prov.get (desc)
            if prov is None:
                raise ValueError ('Unknown proxy provider: \'desc:{}\''.format (desc))

            response ((yield prov.Call (name, *args, **keys)))

    @Async
    def get_handler (self, message):
        with self.domain.Response (message) as response:
            desc, name = self.domain.Unpack (message.Data)
            prov = self.desc2prov.get (desc)
            if prov is None:
                raise ValueError ('Unknown proxy provider: \'desc:{}\''.format (desc))

            response ((yield prov.PropertyGet (name)))

    @Async
    def set_handler (self, message):
        with self.domain.Response (message) as response:
            desc, name, value = self.domain.Unpack (message.Data)
            prov = self.desc2prov.get (desc)
            if prov is None:
                raise ValueError ('Unknown proxy provider: \'desc:{}\''.format (desc))

            response ((yield prov.PropertySet (name, value)))

#------------------------------------------------------------------------------#
# Remote Proxy Provider                                                        #
#------------------------------------------------------------------------------#
class RemoteProxyProvider (ProxyProvider):
    __slots__ = ProxyProvider.__slots__ + ('linker', 'desc',)

    def __init__ (self, linker, desc = None):
        self.linker = linker
        self.desc   = desc ^ 0x1

    #--------------------------------------------------------------------------#
    # Proxy Provider Interface                                                 #
    #--------------------------------------------------------------------------#
    def Call (self, name, *args, **keys):
        return self.linker.domain.Request (LinkerService.METHOD, self.desc, name, args, keys)

    def PropertyGet (self, name):
        return self.linker.domain.Request (LinkerService.PROPGET, self.desc, name)

    def PropertySet (self, name, value):
        return self.linker.domain.Request (LinkerService.PROPSET, self.desc, name, value)
    
# vim: nu ft=python columns=120 :