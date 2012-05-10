# -*- coding: utf-8 -*-
import sys
import operator

from ..disposable import *
from ..async import *
from ..async.cancel import *

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
    def FromEvent (cls, event):
        def Subscribe (observer):
            handler_id = event.Add (lambda *args: observer.OnNext (args))
            return Disposable (lambda: event.Remove (handler_id))

        return AnonymousObservable (Subscribe)

    #--------------------------------------------------------------------------#
    # Await                                                                    #
    #--------------------------------------------------------------------------#
    def Await (self):
        # create future
        def cancel ():
            disposable.Dispose ()
            future.ErrorRaise (FutureCanceled ())

        future = Future (cancel = Cancel (cancel))

        # create observer
        def onNext (value):
            disposable.Dispose ()
            future.ResultSet (value)

        def onError (error):
            disposable.Dispose ()
            future.ErrorSet (error)

        def onCompleted ():
            disposable.Dispose ()
            future.ErrorRaise (FutureError ('Observable has been completed'))

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
                yield core.Sleep (delay)
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

            return CompositeDisposable (context.worker,
                self.Subscribe (AnonymousObserver (onNext, onError, onCompleted)))

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
                yield core.Sleep (delay)
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

            return CompositeDisposable (context.worker,
                self.Subsctibe (AnonymousObserver (onNext, onError, onCompleted)))

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

from .utils import *
# vim: nu ft=python columns=120 :
