# -*- coding: utf-8 -*-
import sys

from ..async      import Async, FutureSourcePair, FutureError, SucceededFuture
from ..disposable import Disposable, CompositeDisposable, MutableDisposable

__all__ = ('Observable', 'Observer', 'Subject',)
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
    def FromEvent (cls, event):
        def Subscribe (observer):
            handler_id = event.Add (lambda *args: (observer.OnNext (args),))
            return Disposable (lambda: event.Remove (handler_id))

        return AnonymousObservable (Subscribe)

    #--------------------------------------------------------------------------#
    # Await                                                                    #
    #--------------------------------------------------------------------------#
    def Await (self, cancel = None):
        future, source = FutureSourcePair ()

        if cancel:
            def cancel_cont (result, error):
                disposable.Dispose ()
                source.TrySetCanceled ()
            cancel.Await ().OnCompleted (cancel_cont)

        # create observer
        def onNext (value):
            disposable.Dispose ()
            source.TrySetResult (value)

        def onError (error):
            disposable.Dispose ()
            source.TrySetError (error)

        def onCompleted ():
            disposable.Dispose ()
            source.TrySetException (FutureError ('Observable has been completed'))

        disposable = self.Subscribe (AnonymousObserver (onNext, onError, onCompleted))

        return future

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
    # Throttle                                                                 #
    #--------------------------------------------------------------------------#
    def Throttle (self, core, delay):
        def Subscribe (observer):
            context = Context (value = None, hasValue = False, worker = SucceededFuture (None))
            @Async
            def worker ():
                yield core.TimeDelay (delay)
                observer.OnNext (context.value)
                context.value, context.hasValue = None, False

            def onNext (value):
                context.worker.Cancel ()
                context.value, context.hasValue = value, True
                context.worker = worker ()

            def onError (error):
                context.worker.Cancel ()
                observer.OnError (error)

            def onCompleted ():
                context.worker.Cancel ()
                if context.hasValue:
                    observer.OnNext (context.value)
                observer.OnCompleted ()

            return CompositeDisposable ((context.worker,
                self.Subscribe (AnonymousObserver (onNext, onError, onCompleted))))

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
    def Smother (self, core, delay):
        def Subscribe (observer):
            context = Context (value = None, hasValue = False, worker = SucceededFuture (None))
            @Async
            def worker ():
                yield core.TimeDelay (delay)
                observer.OnNext (context.value)
                context.value, context.hasValue = None, False

            def onNext (value):
                context.value, context.hasValue = value, True
                if context.worker.IsCompleted ():
                    worker ()

            def onError (error):
                context.worker.Cancel ()
                observer.OnError ()

            def onCompleted ():
                context.worker.Cancel ()
                if context.hasValue:
                    observer.OnNext (context.value)
                observer.OnCompleted ()

            return CompositeDisposable ((context.worker,
                self.Subscribe (AnonymousObserver (onNext, onError, onCompleted))))

        return AnonymousObservable (Subscribe)

#------------------------------------------------------------------------------#
# Observer Interface                                                           #
#------------------------------------------------------------------------------#
class Observer (object):
    #--------------------------------------------------------------------------#
    # Observer                                                                 #
    #--------------------------------------------------------------------------#
    def OnNext (self, value):
        raise NotImplementedError ()

    def OnError (self, error):
        raise NotImplementedError ()

    def OnCompleted (self):
        raise NotImplementedError ()

    #--------------------------------------------------------------------------#
    # Safe Observer                                                            #
    #--------------------------------------------------------------------------#
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

#------------------------------------------------------------------------------#
# Subject                                                                      #
#------------------------------------------------------------------------------#
class Subject (Observable, Observer):
    __slots__ = ('observers',)

    def __init__ (self):
        self.observers = []

    #--------------------------------------------------------------------------#
    # Observable Interface                                                     #
    #--------------------------------------------------------------------------#
    def Subscribe (self, observer):
        self.observers.append (observer)
        def dispose ():
            try:
                self.observers.remove (observer)
            except ValueError: pass
        return Disposable (dispose)

    #--------------------------------------------------------------------------#
    # Observer Interface                                                       #
    #--------------------------------------------------------------------------#
    def OnNext (self, value):
        for observer in tuple (self.observers):
            observer.OnNext (value)

    def OnError (self, error):
        for observer in tuple (self.observers):
            observer.OnError (error)
        del self.observers [:]

    def OnCompleted (self):
        for observer in tuple (self.observers):
            observer.OnCompleted ()
        del self.observers [:]

from .utils import *
# vim: nu ft=python columns=120 :
