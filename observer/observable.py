# -*- coding: utf-8 -*-
import sys
import operator

from ..disposable import *
from ..async import *

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

    #--------------------------------------------------------------------------#
    # Smother                                                                  #
    #--------------------------------------------------------------------------#
    def Smother (self, delay, core):
        """Smother observable
        
        Producue only last event within each delay time span
        """
        def Subscribe (observer):
            context = Context (value = None, changed = False, running = False)

            @Async
            def timerTask ():
                now = yield core.Sleep (0)
                context.running = True
                try:
                    while True:
                        now = yield core.SleepUntil (now + delay)
                        if context.stopped:
                            return
                        if context.chagned:
                            observer.OnNext (context.value)
                            context.changed = False
                finally:
                    context.running = False

            def onNext (value):
                if not context.running:
                    timerTask ()
                context.value, context.changed = value, True

            def onError (error):
                context.running = False
                observer.OnError (error)

            def onCompleted ():
                context.running = False
                if context.changed:
                    observer.OnNext (context.value)
                observer.OnCompleted ()

            return CompositeDisposable (lambda: setattr (context, 'running', False),
                self.Subscribe (AnonymousObserver (onNext, onError, onCompleted)))

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

    def ToSafe (self):
        def onNext (value):
            try: self.OnNext (value)
            except Exception: pass

        def onError (error):
            try: self.OnError (error)
            except Exception: pass

        def onCompleted ():
            try: self.OnCompleted ()
            except Exception: pass

        return AnonymousObserver (onNext, onError, onCompleted)

from .utils import *
# vim: nu ft=python columns=120 :
