# -*- coding: utf-8 -*-
import os
import sys
import types
import inspect
from importlib import import_module

from .domain import *
from ..services.linker import *
from ..services.importer import *
from ..services.persist import *
from ...async import *
from ...bootstrap import *

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
    @Async
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
        pkgname = getattr (main, '__package__', None)
        if pkgname:
            # __main__ is a part of a package
            tomb = None
            topname = pkgname.split ('.') [0]
            if topname != __name__.split ('.') [0]:
                # __main__ is not a part of this package
                tomb = Tomb ()
                tomb.Add (sys.modules [topname])
            yield self.linker.Call.Async (tomb_push, pkgname, tomb)

        else:
            yield self.importer.PushModule.Async ('_remote_main',
                inspect.getsource (main).encode ('utf-8'),
                inspect.getsourcefile (main))

        # persistence
        module_persist (self.persist, '__main__')
        yield self.linker.Call.Async (module_persist, self.persist, '_remote_main')

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

def tomb_push (name, tomb):
    if '_remote_main' in sys.modules:
        return

    if tomb:
        sys.meta_path.insert (0, tomb)

    sys.modules ['_remote_main'] = import_module ('{}.__main__'.format (name))
# vim: nu ft=python columns=120 :
