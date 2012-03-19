# -*- coding: utf-8 -*-
from ..utils.fork import *
from ...disposable import *

__all__ = ('Domain',)
#------------------------------------------------------------------------------#
# Domain                                                                       #
#------------------------------------------------------------------------------#
class Domain (object):
    def __init__ (self, channel, services, run = True):
        self.channel = channel
        self.services = services
        self.disposable  = CompositeDisposable (channel)
        try:
            for service in self.services:
                self.disposable += service.Attach (channel)
            if run:
                Fork (self.channel.Run (), 'channel')
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
    # Run                                                                      #
    #--------------------------------------------------------------------------#
    def Run (self):
        return self.channel.Run ()

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
