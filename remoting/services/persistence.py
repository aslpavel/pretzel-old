# -*- coding: utf-8 -*-
import io
import pickle

from .service      import Service
from ...async      import Future
from ...disposable import Disposable

__all__ = ('PersistenceService',)
#------------------------------------------------------------------------------#
# Persistence Service                                                          #
#------------------------------------------------------------------------------#
class PersistenceService (Service):
    NAME   = b'persistence::'
    OBJECT = b'persistence::object'

    def __init__ (self):
        Service.__init__ (self,
            exports = (
                ('Pack',           self.Pack),
                ('Unpack',         self.Unpack),
                ('RegisterObject', self.RegisterObject),
                ('RegisterType',   self.RegisterType)))

        # Pickler | Unpickler
        class pickler_type (pickle.Pickler):
            def persistent_id (this, target):
                return self.pack (target)
        class unpickler_type (pickle.Unpickler):
            def persistent_load (this, pid):
                return self.unpack (pid)
        self.pickler_type = pickler_type
        self.unpickler_type = unpickler_type

        # types
        self.type_pack   = {}
        self.tag_unpack  = {self.OBJECT: lambda desc: self.desc_object [desc]}

        # objects
        self.id_desc     = {}
        self.desc_object = {}

    #--------------------------------------------------------------------------#
    # Methods                                                                  #
    #--------------------------------------------------------------------------#
    def Pack (self, target):
        stream = io.BytesIO ()
        self.pickler_type (stream, -1).dump (target)
        return stream.getvalue ()

    def Unpack (self, data):
        return self.unpickler_type (io.BytesIO (data)).load ()

    def RegisterObject (self, object, desc):
        if desc in self.desc_object:
            raise ValueError ('Descriptor has already been registered: {}'.format (desc))

        self.id_desc [id (object)], self.desc_object [desc] = desc, object
        return Disposable (lambda: (self.id_desc.pop (id (object), None), self.desc_object.pop (desc, None)))

    def RegisterType (self, type, pack, unpack):
        if type in self.type_pack:
            raise ValueError ('Type has already been registered: {}'.format (type))

        self.type_pack [type], self.tag_unpack [type] = pack, unpack
        return Disposable (lambda: (self.type_pack.pop (type, None), self.tag_unpack.pop (type, None)))

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    def pack (self, target):
        # type package
        for type, pack in self.type_pack.items ():
            if isinstance (target, type):
                return (type, pack (target))

        # object packer
        desc = self.id_desc.get (id (target))
        if desc is not None:
            return (self.OBJECT, desc)

    def unpack (self, state):
        return self.tag_unpack [state [0]] (state [1])

# vim: nu ft=python columns=120 :