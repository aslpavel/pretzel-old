# -*- coding: utf-8 -*-
import os
import sys
import inspect
import binascii
import zlib

from . import cage

__all__ = ('ModuleBootstrap', 'FullBootstrap')

#------------------------------------------------------------------------------#
# Full Bootstrap                                                               #
#------------------------------------------------------------------------------#
def FullBootstrap ():
    cage_payload = ModuleBootstrap (cage_file, "cage")
    cage_builder = cage.CageBuilder ()
    cage_builder.AddPath (root_path)
    data = binascii.b2a_base64 (cage_builder.ToBytes ()).strip ().decode ('utf-8')
    bootstrap = __name__
    return full_payload.format (**locals ())

cage_file = os.path.realpath (inspect.getsourcefile (cage))
root_path = os.path.realpath (os.path.dirname (sys.modules [__name__.split ('.') [0]].__file__))

full_payload = r"""
# pypy bug fix
try: import exceptions
except ImportError: pass

# cage bootstrap
{cage_payload}

# full bootstrap
def full_loader ():
    full_cage = cage.Cage (binascii.a2b_base64 (b"{data}"))
    sys.meta_path.insert (0, full_cage)

try:
    full_loader ()
finally:
    del cage
    del full_loader

bootstrap = "{bootstrap}"
"""

#------------------------------------------------------------------------------#
# Module Bootstrap                                                             #
#------------------------------------------------------------------------------#
def ModuleBootstrap (source_file, name):
    """Create source string with embeded compressed source file"""
    with open (source_file, 'rb') as stream:
        source = binascii.b2a_base64 (zlib.compress (stream.read ())).strip ().decode ('utf-8')
    if sys.version_info [0] > 2:
        execute = "exec (code, module.__dict__)"
    else:
        execute = "exec code in module.__dict__"

    return module_payload.format (**locals ())

module_payload = r"""
import sys, imp, zlib, binascii
def loader ():
    source = zlib.decompress (binascii.a2b_base64 (b"{source}"))

    module = imp.new_module ("{name}")
    module.__file__ = "remote:{source_file}"
    sys.modules ["{name}"] = module

    try:
        code = compile (source, module.__file__, "exec")
        {execute}
        return module
    except Exception:
        del sys.modules ["{name}"]
        raise

try:
    {name} = loader ()
finally:
    del loader
"""

# vim: nu ft=python columns=120 :
