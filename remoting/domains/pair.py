# -*- coding: utf-8 -*-
import os
import sys
import types
from importlib import import_module

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
    def __init__ (self, channel, push_main = True, run = None):
        self.persist  = PersistService ()
        self.linker   = LinkerService ()
        self.importer = ImportService ()

        # persist
        for target in (self, channel, channel.core):
            self.persist += target

        # push main
        if push_main:
            channel.OnStart += self.PushMain

        Domain.__init__ (self, channel, [self.linker, self.importer, self.persist], run = run)

    #--------------------------------------------------------------------------#
    # Push Main                                                                #
    #--------------------------------------------------------------------------#
    def PushMain (self):
        """Push Main

        Push current __main__ module to remote domain if it has not been yet,
        and create persistent mapping between local and remote __main__ modules
        """
        if not self.channel.IsRunning:
            raise DomainError ('channel is not running')

        main = sys.modules ['__main__']
        if getattr (main, '__file__', None) is None:
            raise DomainError ('__main__ file cannot be determined')

        # push main
        package_name = getattr (main, '__package__', None)
        if package_name is None or len (package_name) == 0:
            with open (main.__file__, 'rb') as stream:
                self.importer.PushModule ('_remote_main', stream.read (), main.__file__)
        else:
            # __main__ is a part of a package
            package = sys.modules [package_name]
            cage = CageBuilder ()
            cage.AddPath (os.path.dirname (package.__file__))
            self.linker.Call (cage_push, package_name, cage.ToBytes ())

        # persistence
        module_persist (self.persist, '__main__')
        self.linker.Call (module_persist, self.persist, '_remote_main')

#------------------------------------------------------------------------------#
# Remote Domain                                                                #
#------------------------------------------------------------------------------#
class RemoteDomain (Domain):
    def __init__ (self, channel, run = None):
        self.persist = PersistService ()
        for target in (self, channel, channel.core):
            self.persist += target
        self.linker = LinkerService ()
        self.importer = ImportService (insert_path = True)

        Domain.__init__ (self, channel, [self.linker, self.importer, self.persist], run = run)

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

def cage_push (package_name, data):
    if sys.modules.get ('_remote_main') is not None:
        return
    sys.meta_path.insert (0, Cage (data))
    sys.modules ['_remote_main'] = import_module ('{}.__main__'.format (package_name))
# vim: nu ft=python columns=120 :