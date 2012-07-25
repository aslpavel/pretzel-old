# -*- coding: utf-8 -*-
import sys
import imp
import pkgutil
import zlib
import time

from .service import *
from ..utils.compat import *
from ...async import *

__all__ = ('ImportService',)
#-----------------------------------------------------------------------------#
# Ports                                                                       #
#-----------------------------------------------------------------------------#
PORT_IMPORT_LOAD   = 20
PORT_IMPORT_PUSH   = 21

#-----------------------------------------------------------------------------#
# Import                                                                      #
#-----------------------------------------------------------------------------#
class ImportService (Service):
    """Import module from remote client

    Client implementation that providers PEP302 Finder and Loader
    Arguments:
        insert_path: add this finder to meta_path
        override:    override default import machinery
    """
    def __init__ (self, insert_path = False, override = False):
        Service.__init__ (self, [
            (PORT_IMPORT_LOAD, self.port_LOAD),
            (PORT_IMPORT_PUSH, self.port_PUSH)
        ])

        self.locked   = False
        self.override = override
        self.tag      = '{}{}'.format (id (self), time.time ())
        self.containments = {}

        def on_attach (channel):
            if insert_path:
                sys.meta_path.append (self)
        self.OnAttach += on_attach

        def on_detach (channel):
            self.containments.clear ()
            if insert_path:
                sys.meta_path.remove (self)
        self.OnDetach += on_detach

    #--------------------------------------------------------------------------#
    # Finder Interface                                                         #
    #--------------------------------------------------------------------------#
    def find_module (self, name, path = None):
        if path and self.tag not in path:
            # inside package but it is imported with different loader
            return

        if name in self.containments:
            # previously found
            return self

        if not self.IsAttached:
            raise ImportError ('Import service is detached')

        # search locally
        if not self.override:
            if not self.locked:
                self.locked = True
                try:
                    loader = pkgutil.get_loader (name)
                    if loader is not None:
                        return loader
                finally:
                    self.locked = False
            else:
                return None

        # remote import
        response = ~self.channel.Request (PORT_IMPORT_LOAD, name = name, path = path)
        if response.source is None:
            return None

        self.containments [name] = response.source, response.filename, response.ispkg
        return self

    #--------------------------------------------------------------------------#
    # Loader Interface                                                         #
    #--------------------------------------------------------------------------#
    def load_module (self, name):
        module = sys.modules.get (name)
        if module is not None:
            return module

        source, filename, ispkg = self.containment (name)
        return self.load (name, zlib.decompress (source), filename, ispkg)

    # data
    def get_data (self, path):
        raise NotImplementedError ()

    # introspect
    def is_package (self, name):
        return self.containment (name) [2]

    def get_code (self, name):
        source, filename, ispkg = self.containment (name)
        return compile (zlib.decompress (source), filename, 'exec')

    def get_source (self, name):
        return zlib.decompress (self.containment (name) [0]).decode ('utf-8')

    #--------------------------------------------------------------------------#
    # Service's Methods                                                        #
    #--------------------------------------------------------------------------#
    @Delegate
    def PushModule (self, name, source, filename):
        return self.channel.Request (PORT_IMPORT_PUSH, name = name, source = zlib.compress (source),
            filename = filename, ispkg = False)

    #--------------------------------------------------------------------------#
    # Ports Handlers                                                           #
    #--------------------------------------------------------------------------#
    @DummyAsync
    def port_LOAD (self, request):
        # python 2.7 bug in pkgutil.get_loader
        if sys.modules.get (request.name, False) is None:
            return request.Result (source = None)

        loader = pkgutil.get_loader (request.name)
        if loader is None or not hasattr (loader, 'get_source'):
            return request.Result (source = None)

        source = loader.get_source (request.name)
        if source is None:
            return request.Result (source = None)

        return request.Result (source = zlib.compress (source.encode ('utf-8')),
            ispkg = loader.is_package (request.name), filename = 'file:{}'.format (request.name))

    @DummyAsync
    def port_PUSH (self, request):
        if request.name not in sys.modules:
            self.load (request.name, zlib.decompress (request.source), request.filename)
            self.containments [request.name] = request.source, request.filename, request.ispkg

        return request.Result ()

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    def load (self, name, source, filename, ispkg = False):
        module = imp.new_module (name)
        module.__file__   = filename
        module.__loader__ = self
        if ispkg:
            module.__path__    = [self.tag]
            module.__package__ = name
        else:
            module.__package__ = name.rpartition('.')[0]

        sys.modules [name] = module
        try:
            Exec (compile (source, module.__file__, 'exec'), module.__dict__)
            return module
        except Exception:
            sys.modules.pop (name, None)
            raise

    def containment (self, name):
        containment = self.containments.get (name)
        if containment is None:
            raise ImportError ('Can\'t find module \'{}\''.format (name))
        return containment

# vim: nu ft=python columns=120 :
