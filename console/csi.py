# -*- coding: utf-8 -*-

__all__ = ('Color', 'ColorStack', 'MoveUp', 'MoveDown', 'MoveColumn', 'Delete', 'Insert',
           'Erase', 'Save', 'Restore', 'ScrollUp', 'ScrollDown', 'CursorVisible', 'CSI_ESCAPE',
           'COLOR_NONE', 'COLOR_BLACK', 'COLOR_RED', 'COLOR_GREEN', 'COLOR_YELLOW',
           'COLOR_BLUE', 'COLOR_MAGENTA', 'COLOR_CYAN','COLOR_WHITE', 'COLOR_DEFAULT',
           'ATTR_NONE', 'ATTR_NORMAL', 'ATTR_BOLD', 'ATTR_ITALIC', 'ATTR_UNDERLINE',
           'ATTR_BLINK', 'ATTR_NEGATIVE', 'ATTR_FORCE',)

#------------------------------------------------------------------------------#
# Constants                                                                    #
#------------------------------------------------------------------------------#
CSI_ESCAPE = b'\x1b['

COLOR_NONE    = 0
COLOR_BLACK   = 1
COLOR_RED     = 2
COLOR_GREEN   = 3
COLOR_YELLOW  = 4
COLOR_BLUE    = 5
COLOR_MAGENTA = 6
COLOR_CYAN    = 7
COLOR_WHITE   = 8
COLOR_DEFAULT = 10

ATTR_NONE      = 0
ATTR_NORMAL    = 1 << 0
ATTR_BOLD      = 1 << 1
ATTR_ITALIC    = 1 << 3
ATTR_UNDERLINE = 1 << 4
ATTR_BLINK     = 1 << 5
ATTR_NEGATIVE  = 1 << 7
ATTR_FORCE     = 1 << 10 # non CSI attribute

#------------------------------------------------------------------------------#
# Color                                                                        #
#------------------------------------------------------------------------------#
class Color (tuple):
    def __new__ (cls, fg = None, bg = None, attr = None):
        return tuple.__new__ (cls, (fg or COLOR_NONE, bg or COLOR_NONE, attr or ATTR_NONE))

    #--------------------------------------------------------------------------#
    # Property                                                                 #
    #--------------------------------------------------------------------------#
    @property
    def fg (self):
        return self [0]

    @property
    def bg (self):
        return self [1]

    @property
    def attr (self):
        return self [2]

    #--------------------------------------------------------------------------#
    # Composition                                                              #
    #--------------------------------------------------------------------------#
    def __ior__ (self, other): return self | other
    def __or__  (self, other):
        return Color (self.fg or other.fg, self.bg or other.bg, self.attr | other.attr)

    #--------------------------------------------------------------------------#
    # Change Sequence                                                          #
    #--------------------------------------------------------------------------#
    def __lshift__ (self, other): other >> self
    def __rshift__ (self, other):
        flags = []

        # atributes
        attr_changed = self.attr ^ other.attr
        attr_on, attr_off = other.attr & attr_changed, self.attr & attr_changed
        if attr_off:
            flags.extend (b'2' + str (attr).encode ()
                for attr in range (attr_off.bit_length ()) if attr_off & (1 << attr))
        if attr_on:
            flags.extend (b'0' + str (attr).encode ()
                for attr in range (attr_on.bit_length ()) if attr_on & (1 << attr))

        # foreground
        if other.fg and other.fg != self.fg:
            flags.append (b'3' + str (other.fg - 1).encode ())

        # background
        if other.bg and other.bg != self.bg:
            flags.append (b'4' + str (other.bg - 1).encode ())

        return CSI_ESCAPE + b';'.join (flags) + b'm' if flags else b''

    #--------------------------------------------------------------------------#
    # Reper                                                                    #
    #--------------------------------------------------------------------------#
    color_names = {
        COLOR_NONE    : 'none',
        COLOR_BLACK   : 'black',
        COLOR_RED     : 'red',
        COLOR_GREEN   : 'green',
        COLOR_YELLOW  : 'yellow',
        COLOR_BLUE    : 'blue',
        COLOR_MAGENTA : 'magenta',
        COLOR_CYAN    : 'cyan',
        COLOR_WHITE   : 'white',
        COLOR_DEFAULT : 'default',
    }

    attr_names =  {
        ATTR_NORMAL    : 'normal',
        ATTR_BOLD      : 'bold',
        ATTR_ITALIC    : 'italic',
        ATTR_UNDERLINE : 'underlined',
        ATTR_BLINK     : 'blink',
        ATTR_NEGATIVE  : 'negative',
        ATTR_FORCE     : 'force',
    }

    def __repr__ (self): return self.__str__ ()
    def __str__  (self):
        return '<{} fg:{} bg:{} attrs:{}>'.format (
            type (self).__name__,
            self.color_names [self.fg],
            self.color_names [self.bg],
            ','.join (self.attr_names [1 << attr]
                for attr in range (self.attr.bit_length ()) if self.attr & (1 << attr)))

class ColorStack (object):
    __slots__   = ('stack',)
    reset_color = Color (COLOR_DEFAULT, COLOR_DEFAULT, ATTR_NONE)
    push_cache  = {}
    pop_cache   = {}

    def __init__ (self):
        self.stack = [Color (COLOR_DEFAULT, COLOR_DEFAULT, ATTR_NORMAL)]

    #--------------------------------------------------------------------------#
    # Push | Pop                                                               #
    #--------------------------------------------------------------------------#
    def Push (self, color):
        color_cur = self.stack [-1]

        cached = self.push_cache.get ((color_cur, color))
        if cached is None:
            if color.attr & ATTR_FORCE:
                color_cur = self.reset_color
                color = Color (color.fg, color.bg, ATTR_NORMAL | (color.attr & ~ATTR_FORCE))
            else:
                color_cur = self.stack [-1]
                color |= color_cur

            csi = color_cur >> color
            self.push_cache [(color_cur, color)] = csi, color
        else:
            csi, color = cached

        self.stack.append (color)
        return csi

    def Pop (self):
        color_cur, color_new = self.stack.pop () if len (self.stack) > 1 else self.stack [-1], self.stack [-1]

        csi = self.pop_cache.get ((color_cur, color_new))
        if csi is None:
            csi = color_cur >> color_new
            self.pop_cache [(color_cur, color_new)] = csi

        return csi

    #--------------------------------------------------------------------------#
    # Boolean                                                                  #
    #--------------------------------------------------------------------------#
    def __nonzero__ (self): return self.__bool__ ()
    def __bool__    (self):
        return len (self.stack) > 1

#------------------------------------------------------------------------------#
# Control Sequence Initiator Decorator                                         #
#------------------------------------------------------------------------------#
def CSI (factory):
    cache  = {}

    def method (args = None):
        csi = cache.get (args)
        if csi is None:
            value = factory (args)
            if value is None:
                csi = b''
            else:
                csi = CSI_ESCAPE + value
            cache [args] = csi
        return csi

    method.__name__ = factory.__name__ + 'CSI'
    method.__doc__  = factory.__doc__
    return method

#------------------------------------------------------------------------------#
# Move                                                                         #
#------------------------------------------------------------------------------#
@CSI
def MoveUp (count):
    if count == 0:
        return None
    elif count > 0:
        return str (count).encode () + b'A'
    else:
        return str (-count).encode () + b'B'

def MoveDown (count):
    return MoveUp (-count)

@CSI
def MoveColumn (index):
    if index == 0:
        return b'G'
    elif index > 0:
        return str (index).encode () + b'G'
    raise ValueError ('index must be >= 0')

#------------------------------------------------------------------------------#
# Delete | Insert                                                              #
#------------------------------------------------------------------------------#
@CSI
def Delete (count):
    if count == 0:
        return None
    elif count > 0:
        return str (count).encode () + b'M'
    raise ValueError ('count must be >= 0')

@CSI
def Insert (count):
    if count == 0:
        return None
    elif count > 0:
        return str (count).encode () + b'L'
    raise ValueError ('count must be >= 0')

@CSI
def Erase (args):
    return b'2K' # erase line (2 is "Clear All")

#------------------------------------------------------------------------------#
# Save | Restore                                                               #
#------------------------------------------------------------------------------#
@CSI
def Save (args):
    return b's'

@CSI
def Restore (args):
    return b'u'

#------------------------------------------------------------------------------#
# Scroll                                                                       #
#------------------------------------------------------------------------------#
@CSI
def ScrollUp (count):
    if count == 0:
        return None
    elif count > 0:
        return str (count).encode () + b'S'
    else:
        return str (-count).encode () + b'T'

def ScrollDown (count):
    return ScrollUp (-count)

#------------------------------------------------------------------------------#
# Crusor                                                                       #
#------------------------------------------------------------------------------#
@CSI
def CursorVisible (visible):
    if visible:
        return b'?25h'
    else:
        return b'?25l'

# vim: nu ft=python columns=120 :
