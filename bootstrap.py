# -*- coding: utf-8 -*-
import os
import sys
import re
import io
import imp
import zlib
import pickle
import binascii
import inspect

__all__ = ('Tomb', 'BootstrapModules', 'BootstrapSource', 'BootstrapBootstrap',)
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
                    source   = self.read_source (filename)
                    name     = modname if os.path.samefile (path, root) else \
                        '.'.join ((modname, os.path.relpath (path, root).replace ('/', '.')))
                    if file.lower () == '__init__.py':
                        self.containments [name] = source, filename, True
                    else:
                        self.containments ['.'.join ((name, file [:-3]))] = source, filename, False
        else:
            self.containments [modname] = self.read_source (filename), filename, False

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
        return containment [0]

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

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    @staticmethod
    def read_source (filename):
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

#------------------------------------------------------------------------------#
# Bootstrap                                                                    #
#------------------------------------------------------------------------------#
def BootstrapModules (modules = None):
    # bootstrap payload
    bootstrap = BootstrapBootstrap ('_bootstrap')

    # modules payload
    tomb    = Tomb ()
    modules = modules if modules else (sys.modules [(__package__ if __package__ else __name__).split ('.') [0]],)
    for module in modules:
        tomb.Add (module)
    modules_data = binascii.b2a_base64 (tomb.Save ()).strip ().decode ('utf-8')

    return module_payload.format (**locals ())

module_payload = """{bootstrap}\
sys.meta_path.append (_bootstrap.Tomb.Load (binascii.a2b_base64 (b"{modules_data}")))
"""

def BootstrapSource (name, source, filename):
    data = binascii.b2a_base64 (zlib.compress (source.encode ('utf-8'))).strip ().decode ('utf-8')
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
        if value.__traceback__ is not tb:
            raise value.with_traceback (tb)
        raise value

    PY2 = False

else:
    def Exec (code, globs=None, locs=None):
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
    usage_pattern = '''Usage: {name} [options] [<modules>]
    -h|?      : print this help message
    -m <file> : use file as main
'''
    sys.stderr.write (usage_pattern.format (name = os.path.basename (sys.argv [0])))

def Main ():
    import getopt
    import importlib

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
            assert False, 'Uhnadled option: {}'.format (o)

    #--------------------------------------------------------------------------#
    # Output                                                                   #
    #--------------------------------------------------------------------------#
    sys.stdout.write ('# -*- coding: utf-8 -*-\n' if main_path is None else '#! /usr/bin/env python\n')
    if args:
        sys.stdout.write (BootstrapModules (importlib.import_module (name) for name in args))
    else:
        sys.stdout.write (BootstrapModules ())
    sys.stdout.write ('\n')

    if main_path:
        sys.stdout.write (Tomb.read_source (main_path))

if __name__ == '__main__':
    Main ()

# vim: nu ft=python columns=120 :
