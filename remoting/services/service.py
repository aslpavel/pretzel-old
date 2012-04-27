# -*- coding: utf-8 -*-
from ...event import *
from ...disposable import *

__all__ = ('Service', 'ServiceError')
#------------------------------------------------------------------------------#
# Service                                                                      #
#------------------------------------------------------------------------------#
class ServiceError (Exception): pass
class Service (object):
    def __init__ (self, ports = None, persistence = None):
        self.channel = None
        self.ports = [] if ports is None else ports
        self.persistence = [] if persistence is None else persistence

        # events
        self.OnAttach = Event ()
        self.OnDetach = Event ()

    #--------------------------------------------------------------------------#
    # Attach                                                                   #
    #--------------------------------------------------------------------------#
    def Attach (self, channel):
        if self.channel is not None:
            raise ServiceError ('channel already been attached')
        self.channel = channel

        def disconnect ():
            channel, self.channel = self.channel, None
            self.OnDetach (channel)
        disposable = CompositeDisposable (Disposable (disconnect))
        try:
            for port, handler in self.ports:
                disposable += channel.BindPort (port, handler)
            for slot, save, restore  in self.persistence:
                disposable += channel.BindPersistence (slot, save, restore)
            self.OnAttach (channel)

            return disposable
        except Exception:
            disposable.Dispose ()
            raise

    @property
    def IsAttached (self):
        return self.channel is not None
# vim: nu ft=python columns=120 :
