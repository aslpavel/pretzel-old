# -*- coding: utf-8 -*-
import sys, os
import imp, pickle, zlib

#-----------------------------------------------------------------------------#
# Cage                                                                        #
#-----------------------------------------------------------------------------#
class Cage (object):
    def __init__ (self, data):
        self.sources = pickle.loads (data)

    def find_module (self, name, path = None):
        name = name.replace ('.', '/')
        source = self.sources.get (name + '.py')
        if source is not None:
            return self.CageLoader (source, name + '.py', None)
        source = self.sources.get (name + '/__init__.py')
        if source is not None:
            return self.CageLoader (source, name + '/__init__.py', name)
        return None

    class CageLoader (object):
        __slots__ = ('source', 'file', 'path')
        def __init__ (self, source, file, path):
            self.source = source
            self.file = file
            self.path = path

        def load_module (self, name):
            module = imp.new_module (name)
            module.__file__ = 'cage:{0}'.format (self.file)
            module.__loader__ = self
            if self.path is not None:
                module.__path__ = [self.path]

            sys.modules [name] = module
            try:
                code = compile (zlib.decompress (self.source), self.file, 'exec')
                exec_ (code, module.__dict__)

                return module
            except Exception:
                del sys.modules [name]
                raise

        def is_package (self, name):
            return self.path is not None

        def get_code (self, name):
            return compile (zlib.decompress (self.source), self.file, 'exec')

        def get_source (self, name):
            return self.source

#-----------------------------------------------------------------------------#
# Cage Builder                                                                #
#-----------------------------------------------------------------------------#
class CageBuilder (object):
    def __init__ (self):
        self.files = {}

    def Add (self, path, data):
        self.files [path] = data

    def AddPath (self, path):
        path = path.rstrip ('/')
        name = os.path.split (path) [-1]
        for root, dirs, files in os.walk (path):
            prefix = root [len (path) - len (name):].lstrip ('/')
            for file in files:
                if not file.endswith ('.py'):
                    continue
                with open (os.path.join (root, file), 'rb') as stream:
                    fullpath = '{0}/{1}'.format (prefix, file) if len (prefix) > 0 else file
                    self.files [fullpath] = zlib.compress (stream.read (), 9)

    def ToBytes (self):
        return pickle.dumps (self.files)

#-----------------------------------------------------------------------------#
# Compatibility                                                               #
#-----------------------------------------------------------------------------#
if sys.version_info [0] > 2:
    import builtins
    exec_ = getattr (builtins, "exec")
    del builtins

    def reraise (tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback (tb)
        raise value
else:
    def exec_ (code, globs=None, locs=None):
        """Execute code in a namespace."""
        if globs is None:
            frame = sys._getframe (1)
            globs = frame.f_globals
            if locs is None:
                locs = frame.f_locals
            del frame
        elif locs is None:
            locs = globs
        exec ("""exec code in globs, locs""")

    exec_ ("""def reraise (tp, value, tb=None):
        raise tp, value, tb""")

# vim: nu ft=python columns=120 :
