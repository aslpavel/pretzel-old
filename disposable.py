# -*- coding: utf-8 -*-

__all__ = ('Disposable', 'MutableDisposable', 'CompositeDisposable')
#------------------------------------------------------------------------------#
# Base Disposable                                                              #
#------------------------------------------------------------------------------#
class BaseDisposable (object):
    __slots__ = tuple ()
    #--------------------------------------------------------------------------#
    # Call                                                                     #
    #--------------------------------------------------------------------------#
    def __call__ (self):
        self.Dispose ()

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        raise NotImplementedError ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

    #--------------------------------------------------------------------------#
    # Status                                                                   #
    #--------------------------------------------------------------------------#
    def IsDisposed (self):
        raise NotImplementedError ()

    def __bool__ (self):
        return self.IsDisposed ()

    def __nonzero__(self):
        return self.IsDisposed ()

#------------------------------------------------------------------------------#
# Disposable                                                                   #
#------------------------------------------------------------------------------#
class Disposable (BaseDisposable):
    __slots__ = ('dispose',)
    def __init__ (self, dispose = None):
        self.dispose = dispose

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        if self.dispose is not None:
            self.dispose, dispose = None, self.dispose
            dispose ()

    #--------------------------------------------------------------------------#
    # Status                                                                   #
    #--------------------------------------------------------------------------#
    def IsDisposed (self):
        return self.dispose is None

#------------------------------------------------------------------------------#
# Mutable Disposable                                                           #
#------------------------------------------------------------------------------#
class MutableDisposable (BaseDisposable):
    __slots__ = ('disposable', 'disposed')

    def __init__ (self, disposable = None):
        self.disposable, self.disposed = disposable, False

        if disposable is not None:
            disposable.__enter__ ()

    #--------------------------------------------------------------------------#
    # Replace                                                                  #
    #--------------------------------------------------------------------------#
    def Replace (self, disposable = None):
        if disposable is not None:
            disposable.__enter__ ()

        if not self.disposed:
            self.disposable, disposable = disposable, self.disposable

        if disposable is not None:
            disposable.__exit__ (None, None, None)

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        if self.disposed:
            return
        self.disposed = True

        if self.disposable is not None:
            self.disposable.__exit__ (None, None, None)

    #--------------------------------------------------------------------------#
    # Status                                                                   #
    #--------------------------------------------------------------------------#
    def IsDisposed (self):
        return self.disposed

#------------------------------------------------------------------------------#
# Composite Disposable                                                         #
#------------------------------------------------------------------------------#
class CompositeDisposable (BaseDisposable):
    __slots__ = ('disposed', 'disposables')

    def __init__ (self, *disposables):
        self.disposed = False
        self.disposables = []
        try:
            for disposable in disposables:
                disposable.__enter__ ()
                self.disposables.append (disposable)
        except Exception:
            self.Dispose ()
            raise

    #--------------------------------------------------------------------------#
    # Add|Remove                                                               #
    #--------------------------------------------------------------------------#
    def Add (self, disposable):
        disposable.__enter__ ()
        if self.disposed:
            disposable.__exit__ (None, None, None)
        else:
            self.disposables.append (disposable)

    def __iadd__  (self, disposable):
        self.Add (disposable)
        return self

    def Remove (self, disposable):
        self.disposables.remove (disposable)
        disposable.__exit__ (None, None, None)

    def __isub__ (self, disposable):
        self.Remove (disposable)
        return self

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        if not self.disposed:
            self.disposed = True
            for disposable in reversed (self.disposables):
                disposable.__exit__ (None, None, None)
            del self.disposables [:]

    #--------------------------------------------------------------------------#
    # Status                                                                   #
    #--------------------------------------------------------------------------#
    def IsDisposed (self):
        return self.disposed

    def __len__ (self):
        return len (self.disposables)
# vim: nu ft=python columns=120 :
