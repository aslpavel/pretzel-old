# -*- coding: utf-8 -*-
import os
import sys
import imp
import zlib
import pickle
import binascii
import inspect

__all__ = ('Tomb', 'BootstrapModule', 'BootstrapSource',)
#------------------------------------------------------------------------------#
# Tomb                                                                         #
#------------------------------------------------------------------------------#
class Tomb (object):
    UID = '1f43bbd9-36e0-4084-84e5-b7fb14fdb1bd'

    def __init__ (self, containments = None):
        self.containments = {} if containments is None else containments

    #--------------------------------------------------------------------------#
    # Methods                                                                  #
    #--------------------------------------------------------------------------#
    def Add (self, module):
        modname = module.__name__
        if modname.find ('.') > 0:
            raise ValueError ('Module isn\'t a top level: \'{}\''.format (modname))

        loader = getattr (module, '__loader__', None)
        if getattr (loader, 'UID', None) == self.UID:
            self.containments.update ((key, value) for key, value in loader.containments.items ()
                if key.startswith (modname))
            return

        filename = inspect.getsourcefile (module)
        if not filename:
            raise ValueError ('Module doesn\'t have sources: \'{}\''.format (modname))

        if os.path.basename (filename).lower () == '__init__.py':
            root = os.path.dirname (filename)
            for path, dirs, files in os.walk (root):
                for file in files:
                    if not file.lower ().endswith ('.py'):
                        continue

                    filename = os.path.join (path, file)
                    with open (filename, 'rb') as stream:
                        source = stream.read ()
                    name = modname if os.path.samefile (path, root) else \
                        '.'.join ((modname, os.path.relpath (path, root).replace ('/', '.')))
                    if file.lower () == '__init__.py':
                        self.containments [name] = source, filename, True 
                    else:
                        self.containments ['.'.join ((name, file [:-3]))] = source, filename, False 
        else:
            with open (filename, 'rb') as stream:
                self.containments [modname] = stream.read (), filename, False

    def __iadd__ (self, module):
        self.Add (module)
        return self
    
    def __iter__ (self):
        return iter (self.containments.keys ())

    #--------------------------------------------------------------------------#
    # Importer Protocol                                                        #
    #--------------------------------------------------------------------------#
    def find_module (self, name, path = None):
        return self if name in self.containments else None

    def load_module (self, name):
        module = sys.modules.get (name)
        if module is not None:
            return module

        containment = self.containments.get (name)
        if containment is None:
            raise ImportError ('No such module: \'{}\''.format (name))
        source, filename, ispkg = containment

        module = imp.new_module (name)
        module.__loader__ = self
        module.__file__   = filename
        if ispkg:
            module.__path__    = []
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

    def is_package (self, name):
        containment = self.containments.get (name)
        if containment is None:
            raise ImportError ('No such module: \'{}\''.format (name))
        return containment [2]

    def get_code (self, name):
        containment = self.containments.get (name)
        if containment is None:
            raise ImportError ('No such module: \'{}\''.format (name))
        return compile (containment [0], containment [1], 'exec')

    def get_source (self, name):
        containment = self.containments.get (name)
        if containment is None:
            raise ImportError ('No such module: \'{}\''.format (name))
        return containment [0].decode ('utf-8')

    #--------------------------------------------------------------------------#
    # Save | Load                                                              #
    #--------------------------------------------------------------------------#
    def Save (self):
        return zlib.compress (pickle.dumps (self.containments, 2), 9)

    @classmethod
    def Load (cls, data):
        return cls (pickle.loads (zlib.decompress (data)))

    def __getstate__ (self):
        return self.Save ()

    def __setstate__ (self, state):
        self.containments = dict (Tomb.Load (state).containments)

#------------------------------------------------------------------------------#
# Bootstrap                                                                    #
#------------------------------------------------------------------------------#
def BootstrapModule (module = None):
    this_module = sys.modules [__name__]
    if module is None:
        module  = sys.modules [(__package__ if __package__ else __name__).split ('.') [0]]
    tomb = Tomb ()
    tomb += module

    data = binascii.b2a_base64 (tomb.Save ()).strip ().decode ('utf-8')
    this_payload = BootstrapSource ('_bootstrap', inspect.getsource (this_module),
        inspect.getsourcefile (this_module))
    return module_payload.format (**locals ())

module_payload = r"""{this_payload}
sys.meta_path.insert (0, _bootstrap.Tomb.Load (binascii.a2b_base64 (b"{data}")))
"""

def BootstrapSource (name, source, filename):
    data = binascii.b2a_base64 (zlib.compress (source.encode ('utf-8'))).strip ().decode ('utf-8')
    if sys.version_info [0] > 2:
        execute = "exec (code, module.__dict__)"
    else:
        execute = "exec code in module.__dict__"

    return source_payload.format (**locals ())

source_payload = r"""
import sys, imp, zlib, binascii
def load ():
    module = imp.new_module ("{name}")
    module.__file__    = "{filename}"
    module.__package__ = "{name}"

    sys.modules ["{name}"] = module
    try:
        code = compile (zlib.decompress (binascii.a2b_base64 (b"{data}")), module.__file__, "exec")
        {execute}
        return module
    except Exception:
        sys.modules.pop ("{name}")
        raise

try: {name} = load ()
finally:
    del load
"""

#------------------------------------------------------------------------------#
# Exec and Raise                                                               #
#------------------------------------------------------------------------------#
if sys.version_info [0] > 2:
    import builtins
    Exec = getattr (builtins, "exec")
    del builtins

    def Raise (tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback (tb)
        raise value
else:
    def Exec (code, globs=None, locs=None):
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

    Exec ("""def Raise (tp, value, tb=None):
        raise tp, value, tb""")

#------------------------------------------------------------------------------#
# Main                                                                         #
#------------------------------------------------------------------------------#
def Main ():
    if '-h' in sys.argv:
        sys.stderr.write ('Usage: {} [<module>]\n'.format (os.path.basename (sys.argv [0])))
        sys.exit (1)

    import importlib
    module_name = sys.argv [1] if len (sys.argv) > 1 else None
    payload = BootstrapModule (None if module_name is None else importlib.import_module (module_name))

    sys.stdout.write ('# -*- coding: utf-8 -*-')
    sys.stdout.write (payload)
    sys.stdout.write ('\n')

if __name__ == '__main__':
    Main ()

# vim: nu ft=python columns=120 :
