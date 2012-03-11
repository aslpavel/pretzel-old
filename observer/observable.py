# -*- coding: utf-8 -*-
import sys
import operator

from .disposable import *

__all__ = ('Observable', 'Observer')
#------------------------------------------------------------------------------#
# Observable Interface                                                         #
#------------------------------------------------------------------------------#
class Observable (object):
    def Subscribe (self, observer):
        raise NotImplementedError ()

    #--------------------------------------------------------------------------#
    # Creation                                                                 #
    #--------------------------------------------------------------------------#
    @classmethod
    def FromEvent (cls, event, add = None, remove = None):
        if add is None:
            add = lambda handler: operator.iadd (event, handler)
        if remove is None:
            remove = lambda handler: operator.isub (event, handler)

        def Subscribe (self, observer):
            add (observer.OnNext)
            return Disposable (remove)

        return AnonymousObservable (Subscribe)

    #--------------------------------------------------------------------------#
    # Select                                                                   #
    #--------------------------------------------------------------------------#
    def Select (self, selector):
        def Subscribe (observer):
            disposable = MutableDisposable ()

            def onError (error):
                disposable.Replace ()
                observer.OnError (error)

            def onCompleted ():
                disposable.Replace ()
                observer.OnCompleted ()

            def onNext (value):
                try:
                    selected_value = selector (value)
                except Exception:
                    onError (sys.exc_info ())
                    return
                observer.OnNext (selected_value)

            disposable.Replace (self.Subscribe (AnonymousObserver (onNext, onError, onCompleted)))
            return disposable

        return AnonymousObservable (Subscribe)

    #--------------------------------------------------------------------------#
    # Merge                                                                    #
    #--------------------------------------------------------------------------#
    @staticmethod
    def Merge (*observables):
        def Subscribe (observer):
            disposables = CompositeDisposable ()

            def onNext (value):
                observer.OnNext (value)

            def onError (error):
                disposables.Dispose ()
                observer.OnError (error)

            def onCompletedFactory ():
                context = Context (disposable = None)
                def onCompleted ():
                    if context.disposable is not None:
                        disposables.Remove (context.disposable)
                    if not len (disposables):
                        observable.OnCompoleted ()
                return context, onCompleted

            try:
                for observable in observables:
                    context, onCompleted = onCompletedFactory ()
                    context.disposable = observable.Subscribe (AnonymousObserver (onNext, onError, onCompleted))
                    disposables += context.disposable

                return disposables
            except Exception:
                disposables.Dispose ()
                raise

        return AnonymousObservable (Subscribe)

#------------------------------------------------------------------------------#
# Observer Interface                                                           #
#------------------------------------------------------------------------------#
class Observer (object):
    def OnNext (self, value):
        raise NotImplementedError ()

    def OnError (self, error):
        raise NotImplementedError ()

    def OnCompleted (self):
        raise NotImplementedError ()

from .utils import *
# vim: nu ft=python columns=120 :
