# -*- coding: utf-8 -*-
import json

__all__ = ('Config', 'FileConfig', 'StoreConfig')
#------------------------------------------------------------------------------#
# Config Node                                                                  #
#------------------------------------------------------------------------------#
class ConfigNode (object):
    __slots__ = ('Root', 'Target')
    special_names = {'Root', 'Target', 'Location', 'Store'}

    def __init__ (self, root, target):
        self.Target = target
        self.Root   = root

    def ToNode (self, value):
        if isinstance (value, dict):
            return ConfigDict (self.Root, value)
        if isinstance (value, (list, tuple)):
            return ConfigList (self.Root, value)
        return value

    #--------------------------------------------------------------------------#
    # Common                                                                   #
    #--------------------------------------------------------------------------#
    def __len__ (self):
        return len (self.Target)

    def __iter__ (self):
        return iter (self.Target)

    #--------------------------------------------------------------------------#
    # Context Interface                                                        #
    #--------------------------------------------------------------------------#
    def Flush (self):
        self.Root.Flush ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Flush ()
        return False

#------------------------------------------------------------------------------#
# Config Dictionary                                                            #
#------------------------------------------------------------------------------#
class ConfigDict (ConfigNode):
    __slots__ = ConfigNode.__slots__

    def __init__ (self, root, target):
        self.Root = root
        ConfigNode.__init__ (self, root, {key : self.ToNode (value) for key, value in target.items ()})

    #--------------------------------------------------------------------------#
    # Dictionary                                                               #
    #--------------------------------------------------------------------------#
    def __getattr__ (self, attr):
        try:
            return self [attr]
        except KeyError: pass
        raise AttributeError (attr)

    def __setattr__ (self, attr, value):
        if attr in self.special_names:
            try:
                object.__setattr__ (self, attr, value)
                return
            except AttributeError: pass
            raise AttributeError ('Config path can not use special names')

        self.Target [attr] = self.ToNode (value)

    def __delattr__ (self, attr):
        del self.Target [attr]

    def __getitem__ (self, item):
        if item in self.special_names:
            raise AttributeError ('Config path can not use special names')
        return self.Target [item]

    __setitem__ = __setattr__
    __delitem__ = __delattr__

    def __contains__ (self, attr):
        return attr in self.Target

    def Keys (self):
        return self.Target.keys ()

    def Values (self):
        return self.Target.values ()

    def Items (self):
        return self.Target.items ()

    def Get (self, item, default):
        try:
            return self [item]
        except KeyError: pass
        return default

    #--------------------------------------------------------------------------#
    # Config Node Interface`                                                   #
    #--------------------------------------------------------------------------#
    def Copy (self):
        return {key: (value.Copy () if isinstance (value, ConfigNode) else value)
            for key, value in self.Target.items ()}

#------------------------------------------------------------------------------#
# Config List                                                                  #
#------------------------------------------------------------------------------#
class ConfigList (ConfigNode):
    __slots__ = ConfigNode.__slots__

    def __init__ (self, root, target):
        self.Root = root
        ConfigNode.__init__ (self, root, [self.ToNode (item) for item in target])

    #--------------------------------------------------------------------------#
    # List                                                                     #
    #--------------------------------------------------------------------------#
    def __getitem__ (self, index):
        return self.Target [index]

    def __setitem__ (self, index, value):
        self.Target [index] = self.ToNode (value)

    def __delitem__ (self, index):
        del self.Target [index]

    def Append (self, value):
        self.Target.append (self.ToNode (value))

    #--------------------------------------------------------------------------#
    # Config Node Interface`                                                   #
    #--------------------------------------------------------------------------#
    def Copy (self):
        return [(item.Copy () if isinstance (item, ConfigNode) else item) for item in self.Target]

#------------------------------------------------------------------------------#
# Config                                                                       #
#------------------------------------------------------------------------------#
class Config (ConfigDict):
    __slots__ = ('Root', 'Target', 'Location',)

    def __init__ (self, location, factory = None):
        self.Location = location

        # retrieve config target
        state = self.LoadState ()
        if state:
            ConfigDict.__init__ (self, self, json.loads (state.decode ('utf-8')))
        else:
            ConfigDict.__init__ (self, self, {} if factory is None else factory ())
            self.Flush ()

    #--------------------------------------------------------------------------#
    # Config Node Interface                                                    #
    #--------------------------------------------------------------------------#
    def Flush (self):
        self.SaveState (json.dumps (self.Copy (), indent = 4).encode ('utf-8'))

    #--------------------------------------------------------------------------#
    # Storage Interface                                                        #
    #--------------------------------------------------------------------------#
    def LoadState (self):
        raise NotImplementedError ()

    def SaveState (self, state):
        raise NotImplementedError ()

#------------------------------------------------------------------------------#
# Store Config                                                                 #
#------------------------------------------------------------------------------#
class StoreConfig (Config):
    __slots__ = ('Root', 'Target', 'Location', 'Store')

    def __init__ (self, store, name, factory = None):
        self.Store = store

        Config.__init__ (self, name, factory)

    #--------------------------------------------------------------------------#
    # Storage Interface                                                        #
    #--------------------------------------------------------------------------#
    def LoadState (self):
        return self.Store.LoadByName (self.Location)

    def SaveState (self, state):
        self.Store.SaveByName (self.Location, state)

#------------------------------------------------------------------------------#
# File Config                                                                  #
#------------------------------------------------------------------------------#
class FileConfig (Config):
    __slots__ = Config.__slots__

    #--------------------------------------------------------------------------#
    # Properties                                                               #
    #--------------------------------------------------------------------------#
    @property
    def File (self):
        return self.Location

    #--------------------------------------------------------------------------#
    # Storage Interface                                                        #
    #--------------------------------------------------------------------------#
    def LoadState (self):
        try:
            with open (self.Location, 'rb') as stream:
                return stream.read ()
        except IOError: pass
        return None

    def SaveState (self, state):
        with open (self.Location, 'w+b') as stream:
            stream.write (state)

# vim: nu ft=python columns=120 :
