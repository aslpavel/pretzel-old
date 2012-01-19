# -*- coding: utf-8 -*-
from ..util import *

__all__ = ('Domain',)
#------------------------------------------------------------------------------#
# Domain                                                                       #
#------------------------------------------------------------------------------#
class Domain (object):
    def __init__ (self, channel, services):
        self.channel = channel
        self.services = services
        self.disposable  = CompositeDisposable ()
        try:
            for service in self.services:
                self.disposable += service.Attach (channel)
            self.channel.Start ()
        except Exception:
            self.disposable.Dispose ()
            raise

    def __getattr__ (self, attr):
        for service in self.services:
            try:
                return getattr (service, attr)
            except  AttributeError:
                pass
        raise AttributeError (attr)

    def Dispose (self):
        self.disposable.Dispose ()
        self.channel.Stop ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Disopose ()
        return False

# vim: nu ft=python columns=120 :
