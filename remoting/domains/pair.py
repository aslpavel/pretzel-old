# -*- coding: utf-8 -*-
import sys
import types

# local
from .domain import *

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
            if main is not None and getattr (main, '__file__', None) is not None:
                with open (main.__file__, 'rb') as stream:
                    source = stream.read ()
                def push_main (channel):
                    importer.PushModule ('_remote_main', source, main.__file__)
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

# vim: nu ft=python columns=120 :