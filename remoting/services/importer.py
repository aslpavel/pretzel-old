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

        self.infos    = {}
        self.locked   = False
        self.override = override
        self.tag      = '{}{}'.format (id (self), time.time ())

        def on_attach (channel):
            if insert_path:
                sys.meta_path.append (self)
        self.OnAttach += on_attach

        def on_detach (channel):
            self.infos.clear ()
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

        if name in self.infos:
            # previously found
            return self

        if not self.IsAttached:
            raise ImportError ('Import service is detached')

        # search locally
        if not self.override and not self.locked:
            self.locked = True
            try:
                loader = pkgutil.get_loader (name)
                if loader is not None:
                    return loader
            finally:
                self.locked = False

        # remote import
        info = ~self.channel.Request (PORT_IMPORT_LOAD, name = name, path = path)
        if info.source is None:
            return

        self.infos [name] = info
        return self

    #--------------------------------------------------------------------------#
    # Loader Interface                                                         #
    #--------------------------------------------------------------------------#
    def load_module (self, name):
        module = sys.modules.get (name)
        if module is not None:
            return module

        info = self.info (name)
        return self.load (name, zlib.decompress (info.source), info.file, info.is_package)

    # data
    def get_data (self, path):
        raise NotImplementedError ()

    # introspect
    def is_package (self, name):
        return self.info (name).is_package

    def get_code (self, name):
        info = self.info (name)
        return compile (zlib.decompress (info.source), info.file, 'exec')

    def get_source (self, name):
        return zlib.decompress (self.info (name).source).decode ('utf-8')

    #--------------------------------------------------------------------------#
    # Service's Methods                                                        #
    #--------------------------------------------------------------------------#
    @Delegate
    def PushModule (self, name, source, file):
        return self.channel.Request (PORT_IMPORT_PUSH, name = name, source = zlib.compress (source),
            file = file, is_package = False)

    #--------------------------------------------------------------------------#
    # Ports Handlers                                                           #
    #--------------------------------------------------------------------------#
    @DummyAsync
    def port_LOAD (self, request):
        # python 2.7 bug in pkgutil.get_loader
        if sys.modules.get (request.name) is None:
            return request.Result (source = None)

        loader = pkgutil.get_loader (request.name)
        if (loader is None or                    # loader is not found
            not hasattr (loader, 'get_source')): # get_source is not available
                return request.Result (source = None)

        source = loader.get_source (request.name)
        if source is None:
            return request.Result (source = None)

        return request.Result (source = zlib.compress (source.encode ('utf-8')),
            is_package = loader.is_package (request.name), file = '<ImportService \'{}\'>'.format (request.name))

    @DummyAsync
    def port_PUSH (self, request):
        if request.name not in sys.modules:
            self.load (request.name, zlib.decompress (request.source), request.file)
            self.infos [request.name] = request

        return request.Result ()

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    def load (self, name, source, file, is_package = False):
        module = imp.new_module (name)
        module.__file__   = file
        module.__loader__ = self
        if is_package:
            module.__path__ = [self.tag]

        sys.modules [name] = module
        try:
            code = compile (source, module.__file__, 'exec')
            Exec (code, module.__dict__)

            return module
        except Exception:
            del sys.modules [name]
            raise

    def info (self, name):
        info = self.infos.get (name)
        if info is None:
            raise ImportError ('Can\'t find module \'{}\''.format (name))
        return info

# vim: nu ft=python columns=120 :
