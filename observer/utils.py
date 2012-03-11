# -*- coding: utf-8 -*-
from .observable import *
from .disposable import *

__all__ = ('Context', 'AnonymousObserver', 'AnonymousObservable',)
#------------------------------------------------------------------------------#
# Context                                                                      #
#------------------------------------------------------------------------------#
class Context (object):
    def __init__ (self, **keys):
        for attr, value in keys:
            object.__setattr__ (self, attr, value)

    def __setattr__ (self, attr, value):
        if not hasattr (self, attr):
            raise AttributeError ('New attribute can not be created')
        object.__setattr__ (self, attr, value)

#------------------------------------------------------------------------------#
# Anonymous Observer                                                           #
#------------------------------------------------------------------------------#
class AnonymousObserver (Observer):
    __slots__ = ('onNext', 'onError', 'onCompleted')

    def __init__ (self, onNext = None, onError = None, onCompleted = None):
        self.onNext = onNext
        self.onError = onError
        self.onCompleted = onCompleted

    def OnNext (self, value):
        if self.onNext is not None:
            self.onNext (value)

    def OnError (self, error):
        if self.onError is not None:
            self.onError (error)

    def OnCompleted (self):
        if self.onCompleted is not None:
            self.onCompleted ()

#------------------------------------------------------------------------------#
# Anonymous Observable                                                         #
#------------------------------------------------------------------------------#
class AnonymousObservable (Observable):
    __slots__ = ('subscribe',)

    def __init__ (self, subscribe = None):
        self.subscribe = subscribe

    def Subscribe (self, observer):
        if self.subscribe is None:
            return Disposable ()
        return self.subscribe (observer)

# vim: nu ft=python columns=120 :
