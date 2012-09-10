# -*- coding: utf-8 -*-
import os
import sys
import imp
import pkgutil

from .service       import Service
from ..utils.compat import Exec
from ...async       import Async, DummyAsync
from ...disposable  import Disposable

__all__ = ('ImporterService',)
#------------------------------------------------------------------------------#
# Importer Service                                                             #
#------------------------------------------------------------------------------#
class ImporterService (Service):
    NAME = b'importer::'
    FIND = b'importer::find'
    PUSH = b'importer::push'

    def __init__ (self, insert = None):
        Service.__init__ (self,
            exports = (('ModulePush', self.ModulePush),),
            handlers = ((self.FIND, self.find_handler), (self.PUSH, self.push_handler)))

        self.insert = False if insert is None else insert
        self.pid = os.getpid ()
        self.containments = {} # name -> name, source, filename, ispkg

        self.dispose += Disposable (lambda: self.containments.clear ())

    #--------------------------------------------------------------------------#
    # Public                                                                   #
    #--------------------------------------------------------------------------#
    @Async
    def Connect (self, domain):
        yield Service.Connect (self, domain)

        if self.insert:
            sys.meta_path.append (self)
            self.dispose += Disposable (lambda: sys.meta_path.remove (self))

    def ModulePush (self, name, source, filename):
        return self.domain.Request (self.PUSH, name, source, filename)

    #--------------------------------------------------------------------------#
    # Importer Interface                                                       #
    #--------------------------------------------------------------------------#
    def find_module (self, name, path = None):
        if (self.pid != os.getpid () or
            self.containment (name, False) is None):
               return None
        return self

    def load_module (self, name):
        module = sys.modules.get (name)
        if module is not None:
            return module
        return self.load (*self.containment (name))

    def is_package (self, name):
        return self.containment (name) [3]

    def get_source (self, name):
        return self.containment (name) [1]

    def get_code (self, name):
        name, source, filename, ispkg = self.containment (name)
        return compile (source, filename, 'exec')

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    @DummyAsync
    def find_handler (self, message):
        with self.domain.Response (message) as response:
            name = response.Args [0]
            if sys.modules.get (name, False) is None:
                return
            loader = pkgutil.get_loader (name)
            if loader is None or not hasattr (loader, 'get_source'):
                return
            source = loader.get_source (name)
            if source is None:
                return
            code = loader.get_code (name)
            if code is None:
                return

            response ((name, source, code.co_filename, loader.is_package (name)))

    @DummyAsync
    def push_handler (self, message):
        with self.domain.Response (message) as response:
            name, source, filename = response.Args
            self.containments [name] = name, source, filename, False
            self.load (name, source, filename, ispkg = False)

    def load (self, name, source, filename, ispkg):
        module = imp.new_module (name)
        module.__file__   = filename
        module.__loader__ = self
        if ispkg:
            module.__path__    = [os.path.dirname (filename)]
            module.__package__ = name
        else:
            module.__package__ = name.rpartition ('.') [0]

        sys.modules [name] = module
        try:
            Exec (compile (source, module.__file__, 'exec'), module.__dict__)
            return module
        except Exception:
            sys.modules.pop (name, None)
            raise

    def containment (self, name, throw = True):
        containment = self.containments.get (name, False)
        if containment is False:
            parent = sys.modules.get (name.rpartition ('.') [0])
            if parent and getattr (parent, '__loader__', None) != self:
                # parent was loaded with different loader
                containment = None
            else:
                core   = self.domain.channel.core
                future = self.domain.Request (self.FIND, name)

                # wait for future to be resolved
                for none in core:
                    if future.IsCompleted ():
                        break
                containment = future.Result ()

            self.containments [name] = containment

        if containment is None and throw:
            raise ImportError ('Can\'t find module: \'{}\''.format (name))

        return containment

# vim: nu ft=python columns=120 :
