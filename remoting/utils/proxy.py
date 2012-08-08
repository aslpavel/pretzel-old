# -*- coding: utf-8 -*-
from .queryable import *
from ...async import *

__all__ = ('Proxy', 'ProxyAttribute', 'ProxyProvider', 'LocalProxyProvider',)
#------------------------------------------------------------------------------#
# Proxy                                                                        #
#------------------------------------------------------------------------------#
class Proxy (object):
    __slots__ = ('_provider', '_lock')

    def __init__ (self, provider, lock = None):
        object.__setattr__ (self, '_provider', provider)
        object.__setattr__ (self, '_lock',     lock)

    #--------------------------------------------------------------------------#
    # Call                                                                     #
    #--------------------------------------------------------------------------#
    @Queryable
    def __call__ (self, args, keys, query):
        return self._provider.Call ('__call__', args, keys, query)

    #--------------------------------------------------------------------------#
    # Attributes                                                               #
    #--------------------------------------------------------------------------#
    @Queryable
    def __getattr__ (self, args, keys, query):
        return ProxyAttribute (self._provider, args [0], query)

    def __setattr__ (self, name, value):
        self._provider.PropertySet (name, value)

    #--------------------------------------------------------------------------#
    # Compare                                                                  #
    #--------------------------------------------------------------------------#
    def __eq__ (self, other):
        return True if type (other) == Proxy and self._provider == other._provider else False

    def __hash__ (self):
        return hash (self._provider)

#------------------------------------------------------------------------------#
# Proxy Attribute                                                              #
#------------------------------------------------------------------------------#
class ProxyAttribute (LazyFuture):
    __slots__ = LazyFuture.__slots__ + ('provider', 'name', 'query',)

    def __init__ (self, provider, name, query):
        LazyFuture.__init__ (self, self.propertyGet)

        self.provider = provider
        self.name     = name
        self.query    = query

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    def __call__ (self, *args, **keys):
        return self.provider.Call (self.name, args, keys, self.query)

    def propertyGet (self):
        return self.provider.PropertyGet (self.name, self.query)

#------------------------------------------------------------------------------#
# Proxy Provider                                                               #
#------------------------------------------------------------------------------#
class ProxyProvider (object):
    __slots__ = tuple ()

    def Call (self, name, args, keys, query):
        return FailedFuture (NotImplementedError ())

    def PropertyGet (self, name):
        return FailedFuture (NotImplementedError ())

    def PropertySet (self, name, value):
        return FailedFuture (NotImplementedError ())

#------------------------------------------------------------------------------#
# Local Proxy Provider                                                         #
#------------------------------------------------------------------------------#
class LocalProxyProvider (ProxyProvider):
    __slots__ = ('instance',)

    def __init__ (self, instance):
        self.instance = instance

    @property
    def Instance (self):
        return self.instance
        
    #--------------------------------------------------------------------------#
    # Proxy Provider Interface                                                 #
    #--------------------------------------------------------------------------#
    def Call (self, name, args, keys, query):
        return Query (getattr (self.instance, name) (*args, **keys), query)

    def PropertyGet (self, name, query):
        return Query (getattr (self.instance, name), query)

    @DummyAsync
    def PropertySet (self, name, value):
        return setattr (self.instance, name, value)

# vim: nu ft=python columns=120 :
