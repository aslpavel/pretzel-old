# -*- coding: utf-8 -*-

__all__ = ('Disposable', 'MutableDisposable', 'CompositeDisposable')
#------------------------------------------------------------------------------#
# Base Disposable                                                              #
#------------------------------------------------------------------------------#
class BaseDisposable (object):
    """Base disposable object
    """
    __slots__ = tuple ()
    #--------------------------------------------------------------------------#
    # Call                                                                     #
    #--------------------------------------------------------------------------#
    def __call__ (self):
        """Dispose object
        """
        self.Dispose ()

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        """Dispose object
        """
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
        """Is object disposed
        """
        raise NotImplementedError ()

    def __bool__ (self):
        return self.IsDisposed ()

    def __nonzero__(self):
        return self.IsDisposed ()

#------------------------------------------------------------------------------#
# Disposable                                                                   #
#------------------------------------------------------------------------------#
class Disposable (BaseDisposable):
    """Call "dispose" function on Dispose
    """
    __slots__ = ('dispose',)
    def __init__ (self, dispose = None):
        self.dispose = dispose

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        """Dispose
        """
        if self.dispose is not None:
            self.dispose, dispose = None, self.dispose
            return dispose ()

    #--------------------------------------------------------------------------#
    # Status                                                                   #
    #--------------------------------------------------------------------------#
    def IsDisposed (self):
        """Is disposed
        """
        return self.dispose is None

#------------------------------------------------------------------------------#
# Mutable Disposable                                                           #
#------------------------------------------------------------------------------#
class MutableDisposable (BaseDisposable):
    """Mutable disposable
    """
    __slots__ = ('disposable', 'disposed')

    def __init__ (self, disposable = None):
        self.disposable, self.disposed = disposable, False

        if disposable is not None:
            disposable.__enter__ ()

    #--------------------------------------------------------------------------#
    # Replace                                                                  #
    #--------------------------------------------------------------------------#
    def Replace (self, disposable = None):
        """Replace disposable object and dispose old one if any
        """
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
        """Dispose disposable object if any
        """
        if self.disposed:
            return
        self.disposed = True

        if self.disposable is not None:
            self.disposable.__exit__ (None, None, None)

    #--------------------------------------------------------------------------#
    # Status                                                                   #
    #--------------------------------------------------------------------------#
    def IsDisposed (self):
        """Is disposed
        """
        return self.disposed

#------------------------------------------------------------------------------#
# Composite Disposable                                                         #
#------------------------------------------------------------------------------#
class CompositeDisposable (BaseDisposable):
    """Composite disposable

    Treat multiple disposable as one.
    """
    __slots__ = ('disposables',)

    def __init__ (self, disposables = None):
        self.disposables = []
        if disposables:
            try:
                for disposable in disposables:
                    self.Add (disposable)
            except Exception:
                self.Dispose ()
                raise

    #--------------------------------------------------------------------------#
    # Add|Remove                                                               #
    #--------------------------------------------------------------------------#
    def Add (self, disposable):
        """Register disposable
        """
        disposable.__enter__ ()
        if self.disposables is None:
            disposable.__exit__ (None, None, None)
        else:
            self.disposables.append (disposable)

    def __iadd__  (self, disposable):
        """Register disposable
        """
        self.Add (disposable)
        return self

    def Remove (self, disposable):
        """Unregister disposable and dispose it
        """
        if self.disposables is None:
            return

        self.disposables.remove (disposable)
        disposable.__exit__ (None, None, None)

    def __isub__ (self, disposable):
        """Unregister disposable and dispose it
        """
        self.Remove (disposable)
        return self

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        """Dispose all registered disposables
        """
        if self.disposables is None:
            return

        disposables, self.disposables = self.disposables, None
        for disposable in reversed (disposables):
            disposable.__exit__ (None, None, None)

    #--------------------------------------------------------------------------#
    # Status                                                                   #
    #--------------------------------------------------------------------------#
    def IsDisposed (self):
        """Is disposed
        """
        return self.disposables is None

    def __len__ (self):
        """Number of registered disposables
        """
        return len (self.disposables) if self.disposables else 0
# vim: nu ft=python columns=120 :
