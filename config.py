# -*- coding: utf-8 -*-
import json
from .udb import sack

__all__ = ('Config', 'FileConfig', 'SackConfig')
#------------------------------------------------------------------------------#
# Config Node                                                                  #
#------------------------------------------------------------------------------#
class ConfigNode (object):
    __slots__ = ('Target', 'Root')
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
        if attr [0].isupper ():
            raise AttributeError ('Config path can not be started with capital')
       
        try:
            return self.Target [attr]
        except KeyError: pass

        raise AttributeError (attr)

    def __setattr__ (self, attr, value):
        if attr [0].isupper ():
            try:
                object.__setattr__ (self, attr, value)
                return
            except AttributeError: pass
            raise AttributeError ('Config path can not be started with capital')

        self.Target [attr] = self.ToNode (value)

    def __delattr__ (self, attr):
        del self.Target [attr]

    def __contains__ (self, attr):
        return attr in self.Target

    def Keys (self):
        return self.Target.keys ()

    def Values (self):
        return self.Target.values ()

    def Items (self):
        return self.Target.items ()

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
# Sack Config                                                                  #
#------------------------------------------------------------------------------#
class SackConfig (Config):
    __slots__ = ('Root', 'Target', 'Location', 'Sack')

    def __init__ (self, sack, cell, factory = None):
        self.Sack = sack

        Config.__init__ (self, cell, factory)

    #--------------------------------------------------------------------------#
    # Storage Interface                                                        #
    #--------------------------------------------------------------------------#
    def LoadState (self):
        return self.Sack.Cell [self.Location]

    def SaveState (self, state):
        self.Sack.Cell [self.Location] = state
        self.Sack.Flush ()

#------------------------------------------------------------------------------#
# File Config                                                                  #
#------------------------------------------------------------------------------#
class FileConfig (Config):
    __slots__ = Config.__slots__

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
