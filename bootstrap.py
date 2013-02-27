# -*- coding: utf-8 -*-
import os
import sys
import re
import io
import imp
import zlib
import json
import binascii
import textwrap
import inspect
import pkgutil
import importlib
import pickle

__all__ = ('Tomb', 'BootstrapSource', 'BootstrapBootstrap',)
#------------------------------------------------------------------------------#
# Tomb                                                                         #
#------------------------------------------------------------------------------#
class Tomb (object):
    """Tomb importer

    Serializable importer. Capable to import all previously added modules.
    """
    TOMB_UUID = '1f43bbd9-36e0-4084-84e5-b7fb14fdb1bd'

    def __init__ (self, containments = None):
        self.containments = {} if containments is None else containments

    #--------------------------------------------------------------------------#
    # Factory                                                                  #
    #--------------------------------------------------------------------------#
    @classmethod
    def FromModules (cls, modules = None):
        """Create tomb from modules

        If modules install add topmost package containing this module.
        """

        tomb = cls ()
        if modules:
            for module in modules:
                tomb.Add (module)
        else:
            tomb.Add (__package__ or __name__.partition ('.') [0])
        return tomb

    #--------------------------------------------------------------------------#
    # Add                                                                      #
    #--------------------------------------------------------------------------#
    def __iadd__ (self, module):
        """Add module or package
        """
        self.Add (module)
        return self


    def Add (self, module):
        """Add module or package

        Only capable to add modules witch reside on disk as plain python files
        or in tomb.
        """
        if isinstance (module, str):
            # convert module name to module
            module = sys.modules.get (module, None) or importlib.import_module (module)

        # name of the top level package
        modname = (getattr (module, '__package__', '') or module.__name__).partition ('.') [0]
        if modname != module.__name__:
            module = importlib.import_module (modname)

        # skip already imported packages
        if modname in self.containments:
            return

        # check if loader is tomb
        loader  = pkgutil.get_loader (modname)
        if getattr (loader, 'TOMB_UUID', None) == self.TOMB_UUID:
            self.containments.update ((key, value) for key, value in loader.containments.items ()
                if key.startswith (modname))
            return

        # find package file
        filename = inspect.getsourcefile (module)
        if not filename:
            raise ValueError ('Module doesn\'t have sources: \'{}\''.format (modname))

        # Use file name to determine if it is a package instead of loader.is_package
        # because is_package incorrectly handles __main__ module.
        if os.path.basename (filename).lower () == '__init__.py':
            root = os.path.dirname (filename)
            for path, dirs, files in os.walk (root):
                for file in files:
                    if not file.lower ().endswith ('.py'):
                        continue

                    filename = os.path.join (path, file)
                    source   = self.read_source (filename)
                    name     = modname if os.path.samefile (path, root) else \
                        '.'.join ((modname, os.path.relpath (path, root).replace ('/', '.')))
                    if file.lower () == '__init__.py':
                        self.containments [name] = source, filename, True
                    else:
                        self.containments ['.'.join ((name, file [:-3]))] = source, filename, False
        else:
            self.containments [modname] = self.read_source (filename), filename, False

    def AddSource (self, name, source, filename):
        """Add single file module by its source
        """
        self.containments [name] = source, filename, False

    #--------------------------------------------------------------------------#
    # Install                                                                  #
    #--------------------------------------------------------------------------#
    def Install (self):
        """Install tomb to meta_path
        """
        if self in sys.meta_path:
            return
        sys.meta_path.insert (0, self)

    #--------------------------------------------------------------------------#
    # Bootstrap                                                                #
    #--------------------------------------------------------------------------#
    def Bootstrap (self, init = None, *args, **keys):
        """Create bootstrap source for this tomb

        Initialization function (init) and its arguments (args, keys) must be
        pickle-able objects and required modules must added to tomb.
        """
        if init and inspect.getmodule (init).__name__ not in self.containments:
            raise ValueError ('Initialization function must reside in added modules')

        wrap = lambda source: '\\\n'.join (textwrap.wrap (source, 78))
        return ''.join ((
            # tomb
            self.tomb_payload.format (
                bootstrap = BootstrapBootstrap ('_bootstrap'),
                dump = wrap (binascii.b2a_base64 (self.ToBytes ()).strip ().decode ('utf-8'))),
            # init
            '' if init is None else self.init_payload.format (
                wrap (binascii.b2a_base64 (pickle.dumps ((init, args, keys))).strip ().decode ('utf-8')))))

    tomb_payload = """{bootstrap}
# install
_bootstrap.Tomb.FromBytes (binascii.a2b_base64 (b"{dump}")).Install ()
"""
    init_payload = """
import pickle
init, args, keys = pickle.loads (binascii.a2b_base64 (b"{0}"))
if init is not None:
    init (*args, **keys)
    """

    #--------------------------------------------------------------------------#
    # Lookup                                                                   #
    #--------------------------------------------------------------------------#
    def __iter__ (self):
        """Iterate over available module names
        """
        return iter (self.containments.keys ())

    def __continas__ (self, name):
        """Check if tomb is containing module with specified name
        """
        return name in self.containments

    def __getitem__ (self, name):
        """Get module by its name
        """
        try:
            return self.load_module (name)
        except ImportError: pass
        raise KeyError (name)

    #--------------------------------------------------------------------------#
    # Importer Protocol                                                        #
    #--------------------------------------------------------------------------#
    def find_module (self, name, path = None):
        """Find module by its name and path
        """
        return self if name in self.containments else None

    def load_module (self, name):
        """Load module by its name
        """
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
            module.__path__    = [os.path.dirname (filename)]
            module.__package__ = name
        else:
            module.__package__ = name.rpartition ('.') [0]

        module.__initializing__ = True
        sys.modules [name] = module
        try:
            Exec (compile (source, module.__file__, 'exec'), module.__dict__)
            return module
        except Exception:
            sys.modules.pop (name, None)
            raise
        finally:
            module.__initializing__ = False

    def is_package (self, name):
        """Is module identified by name a package
        """
        containment = self.containments.get (name)
        if containment is None:
            raise ImportError ('No such module: \'{}\''.format (name))
        return containment [2]

    def get_code (self, name):
        """Get code for module identified by name
        """
        containment = self.containments.get (name)
        if containment is None:
            raise ImportError ('No such module: \'{}\''.format (name))
        return compile (containment [0], containment [1], 'exec')

    def get_source (self, name):
        """Get source for module identified by name
        """
        containment = self.containments.get (name)
        if containment is None:
            raise ImportError ('No such module: \'{}\''.format (name))
        return containment [0]

    #--------------------------------------------------------------------------#
    # Serialization                                                            #
    #--------------------------------------------------------------------------#
    def ToBytes (self):
        """Save tomb as bytes
        """
        return zlib.compress (json.dumps (self.containments, 2).encode ('utf-8'), 9)

    @classmethod
    def FromBytes (cls, data):
        """Load tomb from bytes
        """
        return cls (json.loads (zlib.decompress (data).decode ('utf-8')))

    def __getstate__ (self):
        return self.ToBytes ()

    def __setstate__ (self, state):
        self.containments = dict (Tomb.FromBytes (state).containments)

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    @staticmethod
    def read_source (filename):
        """Read source from file name
        """
        source   = io.BytesIO ()
        encoding = 'utf-8'
        encoding_pattern = re.compile (b'coding[:=]\s*([-\w.]+)') # PEP: 0263

        with open (filename, 'rb') as stream:
            for line in stream:
                if line.startswith (b'#'):
                    match = encoding_pattern.search (line)
                    if match:
                        encoding = match.group (1).decode ()
                        source.write (b'\n')
                        continue
                source.write (line)

        if PY2:
            # unicode misbehave when creating traceback
            return source.getvalue ()
        else:
            return source.getvalue ().decode (encoding)

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        """Dispose tomb
        """
        if self in sys.meta_path:
            self.meta_path.remove (self)

    def __enter__ (self):
        return self

    def __exit__ (self):
        self.Dispose ()
        return False

#------------------------------------------------------------------------------#
# Bootstrap                                                                    #
#------------------------------------------------------------------------------#
def BootstrapSource (name, source, filename):
    """Bootstrap python source

    Returns python source, witch when executed allows to import specified
    "source" as module with specified "name".
    """
    source = binascii.b2a_base64 (zlib.compress (source.encode ('utf-8'))).strip ().decode ('utf-8')
    return source_payload.format (name = name, filename = filename, source = '\\\n'.join (textwrap.wrap (source, 78)))

source_payload = """import sys, imp, zlib, binascii

def load ():
    \"\"\"Load bootstrap module
    \"\"\"
    module = imp.new_module ("{name}")
    module.__file__    = "{filename}"
    module.__package__ = "{name}"

    sys.modules ["{name}"] = module
    try:
        code = compile (zlib.decompress (binascii.a2b_base64 (b"{source}")), module.__file__, "exec")
        if sys.version_info [0] > 2:
            exec (code, module.__dict__)
        else:
            exec ("exec code in module.__dict__")
        return module

    except Exception:
        sys.modules.pop ("{name}")
        raise

try: {name} = load ()
finally:
    del load
"""

def BootstrapBootstrap (name):
    """Bootstrap this module

    Returns python source, witch when executed allows to import this module
    by specified "name".
    """
    module  = sys.modules [__name__]
    return BootstrapSource (name, inspect.getsource (module), inspect.getsourcefile (module))

#------------------------------------------------------------------------------#
# Exec and Raise                                                               #
#------------------------------------------------------------------------------#
if sys.version_info [0] > 2:
    import builtins
    Exec = getattr (builtins, "exec")
    del builtins

    def Raise (tp, value, tb=None):
        """Raise exception
        """
        if value.__traceback__ is not tb:
            raise value.with_traceback (tb)
        raise value

    PY2 = False

else:
    def Exec (code, globs=None, locs=None):
        """Execute code
        """
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

    PY2 = True

#------------------------------------------------------------------------------#
# Main                                                                         #
#------------------------------------------------------------------------------#
def Usage ():
    """Print usage message
    """
    usage_pattern = '''Usage: {name} [options] [<modules>]
    -h|?      : print this help message
    -m <file> : use file as main
    '''
    sys.stderr.write (usage_pattern.format (name = os.path.basename (sys.argv [0])))

def Main ():
    """Main for this module
    """
    import getopt

    #--------------------------------------------------------------------------#
    # Parse Options                                                            #
    #--------------------------------------------------------------------------#
    try:
        opts, args = getopt.getopt (sys.argv [1:], '?hm:')
    except getopt.GetoptError as error:
        sys.stderr.write (':: error: {}\n'.format (error))
        Usage ()
        sys.exit (1)

    main_path = None
    for o, a in opts:
        if o in ('-h', '-?'):
            Usage ()
            sys.exit (0)
        elif o == '-m':
            main_path = a
        else:
            assert False, 'Unhandled option: {}'.format (o)

    #--------------------------------------------------------------------------#
    # Output                                                                   #
    #--------------------------------------------------------------------------#
    sys.stdout.write ('# -*- coding: utf-8 -*-\n' if main_path is None else '#! /usr/bin/env python\n')
    sys.stdout.write (Tomb.FromModules (args or None).Bootstrap ())
    sys.stdout.write ('\n')

    if main_path:
        sys.stdout.write (Tomb.read_source (main_path))

if __name__ == '__main__':
    Main ()

# vim: nu ft=python columns=120 :
