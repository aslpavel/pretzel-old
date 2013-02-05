# -*- coding: utf-8 -*-
import os
import sys
import imp
import inspect
import pkgutil

from .result import ResultSender
from .hub import ReceiverSenderPair
from .expr import Code, SetItemExpr, GetAttrExpr, LoadArgExpr
from ..async import Core, Async, AsyncReturn
from ..async.future.compat import Exec

__all__ = ('Importer', 'ImporterLoader',)
#------------------------------------------------------------------------------#
# Importer Proxy                                                               #
#------------------------------------------------------------------------------#
class ImporterProxy (object):
    """Importer proxy
    """
    def __init__ (self, sender):
        self.sender = sender
        self.loaders = {}

    #--------------------------------------------------------------------------#
    # Install                                                                  #
    #--------------------------------------------------------------------------#
    def __call__ (self, index = None):
        """Install importer
        """
        if self in sys.meta_path:
            return

        if index is None:
            sys.meta_path.append (self)
        else:
            sys.meta_path.insert (index, self)

    #--------------------------------------------------------------------------#
    # Finder                                                                   #
    #--------------------------------------------------------------------------#
    def find_module (self, name, path = None):
        if self.sender is None:
            return None

        loader = self.loaders.get (name, False)
        if loader is False:
            # Function find_module must be synchronous, so we must execute core
            # until request is fulfilled.
            loader = self.sender.Request (name)
            for _ in Core.Instance ():
                if loader.IsCompleted ():
                    loader = loader.Result ()
                    break
            self.loaders [name] = loader

        if loader is None:
            return None

        return loader

    #--------------------------------------------------------------------------#
    # Equality                                                                 #
    #--------------------------------------------------------------------------#
    def __eq__ (self, other):
        if not isinstance (other, type (self)):
            return False
        return self.sender == other.sender

    def __hash__ (self):
        return hash (self.sender)

    #--------------------------------------------------------------------------#
    # Proxy                                                                    #
    #--------------------------------------------------------------------------#
    def Proxy (self):
        """Get proxy
        """
        return self

    #--------------------------------------------------------------------------#
    # Pickle                                                                   #
    #--------------------------------------------------------------------------#
    def __reduce__ (self):
        """Get proxy to this importer
        """
        return ImporterProxy, (self.sender,)

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        """Dispose importer proxy
        """
        if self in sys.meta_path:
            sys.meta_path.remove (self)

        sender, self.sender = self.sender, None
        if sender is not None:
            sender.Send (None)

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

    #--------------------------------------------------------------------------#
    # To String                                                                #
    #--------------------------------------------------------------------------#
    def __str__ (self):
        """String representation
        """
        return '<{} [addr:{}]>'.format (type (self).__name__,
            self.sender.dst if self.sender else None)

    def __repr__ (self):
        """String representation
        """
        return str (self)

#------------------------------------------------------------------------------#
# Importer Loader                                                              #
#------------------------------------------------------------------------------#
class ImporterLoader (object):
    __slots__ = ('name', 'pkg', 'ispkg', 'filename', 'source',)

    def __init__ (self, name, pkg, ispkg, filename, source):
        self.name = name
        self.pkg = pkg
        self.ispkg = ispkg
        self.filename = filename
        self.source = source

    #--------------------------------------------------------------------------#
    # Loader                                                                   #
    #--------------------------------------------------------------------------#
    def __call__ (self):
        """Load module
        """
        return self.load_module (self.name)

    def load_module (self, name):
        """Load module
        """
        module = sys.modules.get (name)
        if module is not None:
            return module

        if name != self.name:
            raise ImportError ('loader cannot handle {}'.format (name))

        module = imp.new_module (self.name)
        module.__package__ = self.pkg
        module.__file__    = self.filename
        module.__loader__  = self
        if self.ispkg:
            module.__path__= [os.path.dirname (self.filename)]

        module.__initializing__ = True
        sys.modules [name] = module
        try:
            Exec (compile (self.source, module.__file__, 'exec'), module.__dict__)
            return module
        except Exception:
            sys.modules.pop (name, None)
            raise
        finally:
            module.__initializing__ = False

    #--------------------------------------------------------------------------#
    # Inspect Loader                                                           #
    #--------------------------------------------------------------------------#
    def is_package (self, name):
        if name != self.name:
            raise ImportError ('loader cannot handle {}'.format (name))
        return self.ispkg

    def get_source (self, name):
        if name != self.name:
            raise ImportError ('loader cannot handle {}'.format (name))
        return self.source

    def get_code (self, name):
        if name != self.name:
            raise ImportError ('loader cannot handle {}'.format (name))
        return compile (self.source, self.filename, 'exec')

    #--------------------------------------------------------------------------#
    # To String                                                                #
    #--------------------------------------------------------------------------#
    def __str__ (self):
        """String representation
        """
        return '<{} [name:{} package:{}] from {}>'.format (
            type (self).__name__, self.name, self.pkg, self.filename)

    def __repr__ (self):
        """String representation
        """
        return str (self)

#------------------------------------------------------------------------------#
# Importer                                                                     #
#------------------------------------------------------------------------------#
def Importer (hub = None):
    """Create importer proxy object
    """
    receiver, sender = ReceiverSenderPair (hub = hub)

    def importer_handler (name, src, dst):
        with ResultSender (src) as send:
            if name is None:
                return False # dispose importer

            module = sys.modules.get (name, False)
            if module is None:
                send (None) # Module is cached as not found (python 2)

            loader = pkgutil.get_loader (name)
            if loader is None or not hasattr (loader, 'get_source'):
                send (None)

            source = loader.get_source (name)
            if source is None:
                send (None)

            ispkg = loader.is_package (name)
            if module and hasattr (module, '__package__'):
                pkg = module.__package__
            else:
                pkg = name if ispkg else name.rpartition ('.') [0]

            try:
                filename = (inspect.getfile (loader.get_code (name)) if not module else
                            inspect.getfile (module))
            except TypeError:
                filename = '<unknown>'

            send (ImporterLoader (name, pkg, ispkg, filename, source))
        return True

    receiver.On (importer_handler)
    return ImporterProxy (sender)

#------------------------------------------------------------------------------#
# Importer Install                                                             #
#------------------------------------------------------------------------------#
@Async
def ImporterInstall (conn, index = None):
    """Create and install importer on specified connection
    """
    importer = Importer (conn.hub)
    try:
        yield conn (importer) (index)

        # determine full name of __main__ module
        module = sys.modules.get ('__main__', None)
        while module is not None:
            try:
                file = inspect.getsourcefile (module)
                if not file:
                    break
            except TypeError:
                # __main__ is a built-in module. Do not need to map anything
                break

            name = os.path.basename (file).partition ('.') [0]

            package = getattr (module, '__package__', None)
            if package:
                name = '{}.{}'.format (package, name)
            else:
                try:
                    source = inspect.getsource (module)
                except Exception:
                    # __main__ source file is <stdin> or something like this
                    break
                loader = ImporterLoader (name, None, False, file, source)
                yield conn (loader) ().__package__

            # remote_conn.module_map ['__main__'] = main
            yield conn.sender.Request (Code.FromExpr (
                SetItemExpr (GetAttrExpr (LoadArgExpr (0), 'module_map'), '__main__', name)))
            conn.module_map [name] = '__main__'
            break

        AsyncReturn (importer)

    except Exception:
        importer.Dispose ()
        raise

# vim: nu ft=python columns=120 :
