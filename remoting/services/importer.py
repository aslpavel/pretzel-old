# -*- coding: utf-8 -*-
import sys
import imp
import zlib

from .service import *
from ..util import *
from ...async import *
from ...disposable import *

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
    """
    def __init__ (self, insert_path = False):
        Service.__init__ (self, [
            (PORT_IMPORT_LOAD, self.port_LOAD),
            (PORT_IMPORT_PUSH, self.port_PUSH)
        ])

        self.modules = {}

        def on_attach (channel):
            if insert_path:
                sys.meta_path.insert (0, self)
        self.OnAttach += on_attach

        def on_detach (channel):
            self.modules.clear ()
            if insert_path:
                sys.meta_path.remove (self)
        self.OnDetach += on_detach

    # Finder Interface
    def find_module (self, name, path = None):
        if name not in self.modules:
            response = self.channel.Request (PORT_IMPORT_LOAD, name = name, path = path)
            response.Wait ()
            try:
                self.modules [name] = response.Result ()
            except ImportError:
                return None

        return self

    # Loader Interface
    def load_module (self, name):
        module = sys.modules.get (name)
        if module is not None:
            return module

        info = self.modules [name]
        return self.load (name, zlib.decompress (info.source), info.file, info.path)

    def is_package (self, name):
        return self.modules [name].path is not None

    def get_code (self, name):
        info = self.modules [name]
        return compile (zlib.decompress (info.source), 'remote:{0}'.format (info.file), 'exec')

    def get_source (self, name):
        source = zlib.decompress (self.modules [name].source)
        return source if isinstance (source, str) else source.decode ('utf-8')

    @Delegate
    def PushModule (self, name, source, file, package = None):
        return self.channel.Request (PORT_IMPORT_PUSH, name = name, source = source,
            file = file, package = package)

    # PORTS
    @DummyAsync
    def port_LOAD (self, request):
        module_name = request.name.split ('.') [-1]
        path = None
        with CompositeDisposable () as disposable:
            stream, file, desc = imp.find_module (module_name, request.path)
            if stream is not None:
                disposable += stream

            # package
            if desc [2] == imp.PKG_DIRECTORY:
                path = file
                stream, file, desc = imp.find_module ('__init__', [path])
                if stream is not None:
                    disposable += stream

            # module
            if desc [2] != imp.PY_SOURCE:
                raise ImportError ('{0}: only source python files are subject to remote import'
                    .format (request.name))

            return request.Result (source = zlib.compress (stream.read ().encode ('utf-8')),
                file = file, path = path)

    @DummyAsync
    def port_PUSH (self, request):
        if request.name not in sys.modules:
            module = self.load (request.name, request.source, request.file)
            if request.package is not None:
                __import__ (request.package)
                sys.modules [request.package].__dict__ [request.name] = module
                module.__package__ = request.package

            return request.Result ()

    def load (self, name, source, file, path = None):
        """Load module by it's source and name"""
        module = imp.new_module (name)
        module.__file__ = 'remote:{}'.format (file)
        module.__loader__ = self
        if path is not None:
            module.__path__ = [path]

        sys.modules [name] = module
        try:
            code = compile (source, module.__file__, 'exec')
            exec_ (code, module.__dict__)

            return module
        except Exception:
            del sys.modules [name]
            raise
# vim: nu ft=python columns=120 :
