# -*- coding: utf-8 -*-
import pickle
import weakref
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
    DISPOSE = b'linker::dispose'

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
                (self.PROPSET,  self.set_handler),
                (self.DISPOSE,  self.dispose_handler)),
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
        lock = None
        prov  = self.desc2prov.get (desc)
        if prov is None:
            prov  = RemoteProxyProvider (self, desc)
            lock = prov.Lock ()
            self.desc2prov [desc], self.prov2desc [prov] = prov, desc

        return Proxy (prov, lock)

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    @DummyAsync
    def call_handler (self, message):
        with self.domain.Response (message) as response:
            func, args, keys = response.Args
            response (func (*args, **keys))

    @DummyAsync
    def create_handler (self, message):
        with self.domain.Response (message) as response:
            type, args, keys = response.Args
            response (self.ToProxy (type (*args, **keys)))

    @Async
    def method_handler (self, message):
        with self.domain.Response (message) as response:
            desc, name, args, keys = response.Args
            prov = self.desc2prov.get (desc)
            if prov is None:
                raise ValueError ('Unknown proxy provider: \'desc:{}\''.format (desc))

            response ((yield prov.Call (name, *args, **keys)))

    @Async
    def get_handler (self, message):
        with self.domain.Response (message) as response:
            desc, name = response.Args
            prov = self.desc2prov.get (desc)
            if prov is None:
                raise ValueError ('Unknown proxy provider: \'desc:{}\''.format (desc))

            response ((yield prov.PropertyGet (name)))

    @Async
    def set_handler (self, message):
        with self.domain.Response (message) as response:
            desc, name, value = response.Args
            prov = self.desc2prov.get (desc)
            if prov is None:
                raise ValueError ('Unknown proxy provider: \'desc:{}\''.format (desc))

            response ((yield prov.PropertySet (name, value)))

    @Async
    def dispose_handler (self, message):
        desc = pickle.loads (message.Data)
        prov = self.desc2prov.pop (desc, None)
        if prov is not None:
            self.prov2desc.pop (prov, None)

#------------------------------------------------------------------------------#
# Remote Proxy Provider                                                        #
#------------------------------------------------------------------------------#
class RemoteProxyProviderLock (object): pass
class RemoteProxyProvider (ProxyProvider):
    __slots__ = ProxyProvider.__slots__ + ('linker', 'desc', 'lock')

    def __init__ (self, linker, desc = None):
        self.linker = linker
        self.desc   = desc ^ 0x1
        self.lock   = lambda: None

    #--------------------------------------------------------------------------#
    # Proxy Provider Interface                                                 #
    #--------------------------------------------------------------------------#
    def Call (self, name, *args, **keys):
        return self.linker.domain.Request (LinkerService.METHOD, self.desc, name, args, keys)

    def PropertyGet (self, name):
        return self.linker.domain.Request (LinkerService.PROPGET, self.desc, name)

    def PropertySet (self, name, value):
        return self.linker.domain.Request (LinkerService.PROPSET, self.desc, name, value)

    #--------------------------------------------------------------------------#
    # Methods                                                                  #
    #--------------------------------------------------------------------------#
    def Lock (self):
        lock = self.lock ()
        if lock is None:
            lock = RemoteProxyProviderLock ()
            self.lock = weakref.ref (lock, lambda ref: self.Dispose ())
        return lock

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    @Async
    def Dispose (self):
        yield self.linker.domain.channel.core.Idle ()

        self.linker.desc2prov.pop (self.desc ^ 0x1, None)
        self.linker.prov2desc.pop (self, None)
        self.linker.domain.channel.Send (Message (LinkerService.DISPOSE, pickle.dumps (self.desc)))

    def __enter__ (self):
        return self
    
    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

# vim: nu ft=python columns=120 :
