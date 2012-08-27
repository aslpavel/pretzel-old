# -*- coding: utf-8 -*-
from ...async      import DummyAsync
from ...disposable import CompositeDisposable

__all__ = ('Service', 'ServiceError',)
#------------------------------------------------------------------------------#
# Service                                                                      #
#------------------------------------------------------------------------------#
class ServiceError (Exception): pass
class Service (object):
    NAME = b'service::'

    def __init__ (self, exports = None, handlers = None, persistence = None):
        self.exports     = tuple () if exports is None     else exports
        self.handlers    = tuple () if handlers is None    else handlers
        self.persistence = tuple () if persistence is None else persistence

        self.domain   = None
        self.dispose  = CompositeDisposable ()

    #--------------------------------------------------------------------------#
    # Public                                                                   #
    #--------------------------------------------------------------------------#
    @DummyAsync
    def Connect (self, domain):
        if self.domain is not None:
            raise ServiceError ('Service has alread been connected')
        self.domain = domain

        # exports
        for name, handler in self.exports:
            self.dispose += domain.Export (name, handler)

        # handlers
        for destination, handler in self.handlers:
            self.dispose += domain.channel.RecvToHandler (destination, handler)

        # persistence
        for type, pack, unpack in self.persistence:
            self.dispose += domain.RegisterType (type, pack, unpack)
        self.dispose += domain.RegisterObject (self, self.NAME)

    @property
    def IsConnected (self):
        return self.domain is not None

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        self.domain = None
        self.dispose.Dispose ()
        self.dispose = CompositeDisposable ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

# vim: nu ft=python columns=120 :
