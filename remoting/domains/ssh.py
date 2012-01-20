# -*- coding: utf-8 -*-
import sys
import types

# local
from .domain import *

# channels
from ..channels.ssh import *
from ..channels.file import *

# services
from ..services.linker import *
from ..services.importer import *
from ..services.persist import *

__all__ = ('SSHDomain', )
#-----------------------------------------------------------------------------#
# Local SSH Domain                                                            #
#-----------------------------------------------------------------------------#
class SSHDomain (Domain):
    def __init__ (self, core, host, port = None, identity_file = None, ssh_exec = None, py_exec = None,
        import_main = True):
        channel = SSHChannel (core, host, port = port, identity_file= identity_file,
                ssh_exec = ssh_exec, py_exec = py_exec)

        persist = PersistService ()
        for target in (self, core):
            persist += target

        linker = LinkerService ()

        importer = ImportService ()
        if import_main:
            main = sys.modules ['__main__']
            if main is not None and getattr (main, '__file__', None) is not None:
                with open (main.__file__, 'rb') as stream:
                    source = stream.read ()
                def push_main (channel):
                    importer.PushModule ('_remote_main', source, main.__file__)
                    module_persist (persist, '__main__')
                    linker.Call (module_persist, persist, '_remote_main')
                channel.OnStart += push_main

        Domain.__init__ (self, channel, [linker, importer, persist])

#-----------------------------------------------------------------------------#
# Remote SSH Domain                                                           #
#-----------------------------------------------------------------------------#
class SSHRemoteDomain (Domain):
    def __init__ (self, core):
        persist = PersistService ()
        for target in (self, core):
            persist += target

        Domain.__init__ (self, FileChannel (core, 0, 1), [
            LinkerService (),
            ImportService (insert_path = True),
            persist
        ])

#-----------------------------------------------------------------------------#
# Helpers                                                                     #
#-----------------------------------------------------------------------------#
def module_persist (persist, module_name):
    module = sys.modules.get (module_name)
    if module is None:
        raise ValueError ('module {} not found'.format (module_name))
    mapping = module.__dict__
    for name in sorted (mapping.keys ()):
        value = mapping [name]
        if isinstance (value, (type, types.FunctionType)):
            persist += value

# vim: nu ft=python columns=120 :
