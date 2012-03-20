# -*- coding: utf-8 -*-
from ..utils.fork import *
from ...disposable import *
from ...async import *

__all__ = ('Domain',)
#------------------------------------------------------------------------------#
# Domain                                                                       #
#------------------------------------------------------------------------------#
class Domain (object):
    def __init__ (self, channel, services, run = None):
        self.channel = channel
        self.services = services
        self.disposable  = Disposable ()

        if True if run is None else run:
            Fork (self.Run (), 'domain')

    #--------------------------------------------------------------------------#
    # Run                                                                      #
    #--------------------------------------------------------------------------#
    @Async
    def Run (self):
        self.disposable.Dispose ()
        self.disposable  = CompositeDisposable (self.channel)
        try:
            for service in self.services:
                self.disposable += service.Attach (self.channel)

            yield self.channel.Run ()
        except Exception:
            self.disposable.Dispose ()
            raise

    #--------------------------------------------------------------------------#
    # Attribute                                                                #
    #--------------------------------------------------------------------------#
    def __getattr__ (self, attr):
        if attr [0].isupper ():
            for service in self.services:
                try:
                    return getattr (service, attr)
                except  AttributeError:
                    pass
        raise AttributeError (attr)

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        self.disposable.Dispose ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

# vim: nu ft=python columns=120 :
