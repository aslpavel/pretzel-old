# -*- coding: utf-8 -*-
import collections

from ...async import Async
from ...disposable import Disposable, CompositeDisposable

__all__ = ('Domain', 'DomainError',)
#------------------------------------------------------------------------------#
# Domain                                                                       #
#------------------------------------------------------------------------------#
class DomainError (Exception): pass
class Domain (object):
    def __init__ (self, channel, services):
        self.channel  = channel
        self.services = collections.OrderedDict ((service.NAME, service) for service in services)

        self.exports   = {}
        self.dispose   = CompositeDisposable ()

    #--------------------------------------------------------------------------#
    # Methods                                                                  #
    #--------------------------------------------------------------------------#
    def ServiceByName (self, name):
        service = self.services.get (name)
        if service is None:
            raise DomainError ('No such service: \'{}\''.format (name))
        return service

    #--------------------------------------------------------------------------#
    # Connect                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def Connect (self):
        if self.IsConnected:
            return

        # methods
        for service in self.services.values ():
            yield service.Connect (self)
            self.dispose += service

        # channel
        yield self.channel.Connect ()
        self.dispose += self.channel

    @property
    def IsConnected (self):
        return self.channel.IsConnected

    #--------------------------------------------------------------------------#
    # Exports                                                                  #
    #--------------------------------------------------------------------------#
    def Export (self, name, handler):
        if hasattr (self, name):
            raise ValueError ('Name has already been bound: \'{}\''.format (name))
        self.exports [name] = handler
        return Disposable (lambda: self.exports.pop (name))

    def __getattr__ (self, name):
        handler = self.exports.get (name)
        if handler is None:
            raise AttributeError ('No such attribute: \'{}\''.format (name))
        return handler

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        self.dispose.Dispose ()
        self.dispose = CompositeDisposable ()
        self.exports.clear ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

# vim: nu ft=python columns=120 :
