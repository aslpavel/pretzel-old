# -*- coding: utf-8 -*-
import pickle
import weakref
import itertools

from .service          import Service
from ..utils.proxy     import Proxy, ProxyQuery, ProxyProvider, LocalProxyProvider
from ..utils.queryable import Queryable
from ..message         import Message
from ...async          import Async, DummyAsync
from ...disposable     import Disposable

__all__ = ('LinkerService',)
#------------------------------------------------------------------------------#
# Linker Service                                                               #
#------------------------------------------------------------------------------#
class LinkerService (Service):
    NAME    = b'linker::'
    CALL    = b'linker::call'
    METHOD  = b'linker::method'
    PROPSET = b'linker::propset'
    PROPGET = b'linker::propget'
    DISPOSE = b'linker::dispose'

    def __init__ (self):
        Service.__init__ (self,
            exports = (
                ('ToProxy',    self.ToProxy),
                ('Call',       self.Call)),
            handlers = (
                (self.CALL,    self.call_handler),
                (self.METHOD,  self.method_handler),
                (self.PROPGET, self.get_handler),
                (self.PROPSET, self.set_handler),
                (self.DISPOSE, self.dispose_handler)),
            persistence = (
                (Proxy, self.proxyPack, self.proxyUnpack),))

        # marshal mappings
        self.desc      = itertools.count ()
        self.desc_prov = {}
        self.prov_desc = {}
        next (self.desc)

    @Async
    def Connect (self, domain):
        yield Service.Connect (self, domain)

        def dispose ():
            self.desc_prov.clear ()
            self.prov_desc.clear ()
        self.dispose += Disposable (dispose)

    #--------------------------------------------------------------------------#
    # Methods                                                                  #
    #--------------------------------------------------------------------------#
    def ToProxy (self, instance):
        return Proxy (LocalProxyProvider (instance))

    @Queryable
    def Call (self, args, keys, query):
        return self.domain.Request (self.CALL, args [0], args [1:], keys, query)

    #--------------------------------------------------------------------------#
    # Marshal                                                                  #
    #--------------------------------------------------------------------------#
    def proxyPack (self, proxy):
        prov = proxy._provider
        desc = self.prov_desc.get (prov)
        if desc is None:
            desc = next (self.desc) << 1
            self.desc_prov [desc], self.prov_desc [prov] = prov, desc

        return desc

    def proxyUnpack (self, desc):
        desc ^= 0x1
        lock = None
        prov  = self.desc_prov.get (desc)
        if prov is None:
            prov  = RemoteProxyProvider (self, desc)
            lock = prov.Lock ()
            self.desc_prov [desc], self.prov_desc [prov] = prov, desc

        return Proxy (prov, lock)

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def call_handler (self, message):
        with self.domain.Response (message) as response:
            func, args, keys, query = response.Args
            response ((yield ProxyQuery (func (*args, **keys), query)))

    @Async
    def method_handler (self, message):
        with self.domain.Response (message) as response:
            desc, name, args, keys, query = response.Args
            prov = self.desc_prov.get (desc)
            response ((yield prov.Call (name, args, keys, query)))

    @Async
    def get_handler (self, message):
        with self.domain.Response (message) as response:
            desc, name, query = response.Args
            prov = self.desc_prov.get (desc)
            if prov is None:
                raise ValueError ('Unknown proxy provider: \'desc:{}\''.format (desc))

            response ((yield prov.PropertyGet (name, query)))

    @Async
    def set_handler (self, message):
        with self.domain.Response (message) as response:
            desc, name, value = response.Args
            prov = self.desc_prov.get (desc)
            if prov is None:
                raise ValueError ('Unknown proxy provider: \'desc:{}\''.format (desc))

            response ((yield prov.PropertySet (name, value)))

    @DummyAsync
    def dispose_handler (self, message):
        desc = pickle.loads (message.Value ())
        prov = self.desc_prov.pop (desc, None)
        if prov is not None:
            self.prov_desc.pop (prov, None)

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
    def Call (self, name, args, keys, query):
        return self.linker.domain.Request (LinkerService.METHOD, self.desc, name, args, keys, query)

    def PropertyGet (self, name, query):
        return self.linker.domain.Request (LinkerService.PROPGET, self.desc, name, query)

    def PropertySet (self, name, value):
        return self.linker.domain.Request (LinkerService.PROPSET, self.desc, name, value)

    #--------------------------------------------------------------------------#
    # Methods                                                                  #
    #--------------------------------------------------------------------------#
    def Lock (self):
        lock = self.lock ()
        if lock is None:
            lock = RemoteProxyProviderLock ()
            self.lock = weakref.ref (lock, lambda _: self.Dispose ())
        return lock

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    @Async
    def Dispose (self):
        yield self.linker.domain.channel.core.Idle ()

        self.linker.desc_prov.pop (self.desc ^ 0x1, None)
        self.linker.prov_desc.pop (self, None)
        self.linker.domain.channel.Send (Message.FromValue (pickle.dumps (self.desc), LinkerService.DISPOSE))

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

# vim: nu ft=python columns=120 :
