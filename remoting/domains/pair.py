# -*- coding: utf-8 -*-
import os
import sys
import types

# local
from .domain import *
from ..bootstrap.cage import *

# services
from ..services.linker import *
from ..services.importer import *
from ..services.persist import *

__all__ = ('LocalDomain', 'RemoteDomain')
#------------------------------------------------------------------------------#
# Local Domain                                                                 #
#------------------------------------------------------------------------------#
class LocalDomain (Domain):
    def __init__ (self, channel, push_main = True):
        persist = PersistService ()
        for target in (self, channel, channel.core):
            persist += target

        linker = LinkerService ()

        importer = ImportService ()
        if push_main:
            main = sys.modules ['__main__']
            if getattr (main, '__file__', None) is not None:
                def push_main ():
                    # push module
                    package = getattr (main, '__package__', None)
                    if package is None or len (package) == 0:
                        # main is a separate file
                        with open (main.__file__, 'rb') as stream:
                            importer.PushModule ('_remote_main', stream.read (), main.__file__)
                    else:
                        # main is a part of a package
                        cage = CageBuilder ()
                        cage.AddPath (os.path.dirname (main.__file__))
                        linker.Call (cage_push, package, cage.ToBytes ())
                    # create persistence map
                    module_persist (persist, '__main__')
                    linker.Call (module_persist, persist, '_remote_main')
                channel.OnStart += push_main

        Domain.__init__ (self, channel, [linker, importer, persist])

#------------------------------------------------------------------------------#
# Remote Domain                                                                #
#------------------------------------------------------------------------------#
class RemoteDomain (Domain):
    def __init__ (self, channel):
        persist = PersistService ()
        for target in (self, channel, channel.core):
            persist += target

        Domain.__init__ (self, channel, [
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

def cage_push (package, data):
    sys.meta_path.insert (0, Cage (data))
    sys.modules ["_remote_main"] = __import__ ('{0}.__main__'.format (package)).__main__
# vim: nu ft=python columns=120 :