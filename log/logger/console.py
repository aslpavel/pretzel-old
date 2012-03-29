# -*- coding: utf-8 -*-
import sys
import struct
import fcntl
import termios
from contextlib import contextmanager

from ..string import *
from ...disposable import *

__all__ = ('Console', 'ConsoleError')
#------------------------------------------------------------------------------#
# Console                                                                      #
#------------------------------------------------------------------------------#
class Console (object):
    def __init__ (self, stream = None):
        self.stream = stream if stream is not None else sys.stderr

        self.labels = []
        self.flags  = []
        self.colors = []

        self.locked = False

    #--------------------------------------------------------------------------#
    # Output                                                                   #
    #--------------------------------------------------------------------------#
    @contextmanager
    def Put (self):
        position = len (self.labels) + 1
        self.acquire ()
        self.stream.write ('\n')
        self.MoveUp (position)
        self.stream.write (CSI_INSERT)

        try: yield
        finally:
            self.MoveDown (position)
            self.stream.flush ()
            self.release ()

    def Write (self, string):
        if isinstance (string, String):
            for string, color in string:
                newline = string.find ('\n')
                self.ColorSave (color)
                if newline < 0:
                    self.stream.write (string)
                    self.ColorRestore ()
                else:
                    self.stream.write (string [:newline])
                    self.stream.write ('...')
                    self.ColorRestore ()
                    break
        else:
            self.stream.write (string)
        return len (string)

    def Label (self):
        return Label (self)

    #--------------------------------------------------------------------------#
    # Colors                                                                   #
    #--------------------------------------------------------------------------#
    @contextmanager
    def Color (self, color = None):
        try:
            self.ColorSave (color)
            yield
        finally:
            self.ColorRestore ()

    def ColorSave (self, color = None):
        """Save color and set new one

        Color is attribute tuple. With following format
        Format:
            (foreground,)                   : set foreground color
            (attr, foreground)              : set foreground color and attributes
            (attr, foreground, background)  : set background, foreground colors and attributes
        """
        if color is None:
            code = CSI_COLOR_RESET
        else:
            color, format = tuple (color), len (color)
            if format == 1:
                code = CSI_COLOR.format ('3%s' % color)
            elif format == 2:
                code = CSI_COLOR.format ('0%s;3%s' % color)
            elif format == 3:
                code = CSI_COLOR.format ('0%s;3%s;4%s' % color)
            else:
                raise ValueError ('Bad color specifier {0}'.format (color))

        self.colors.append (code)
        self.stream.write (code)

    def ColorRestore (self):
        if not self.colors:
            return

        self.colors.pop ()
        if len (self.colors) > 1:
            self.stream.write (self.colors [-1])
        else:
            self.stream.write (CSI_COLOR_RESET)

    #--------------------------------------------------------------------------#
    # Size                                                                     #
    #--------------------------------------------------------------------------#
    def Size (self):
        """Get terminal size in characters

        returns: columns, rows
        """
        if not self.stream.isatty ():
            return

        rows, columns, xpixel, ypixel = struct.unpack ('4H',
            fcntl.ioctl (self.stream.fileno (), termios.TIOCGWINSZ, struct.pack ('4H', 0, 0, 0, 0)))
        return columns, rows

    #--------------------------------------------------------------------------#
    # Flags                                                                    #
    #--------------------------------------------------------------------------#
    TERMINAL_IFLAG = 0
    TERMINAL_OFLAG = 1
    TERMINAL_CFLAG = 2
    TERMINAL_LFLAG = 3
    TERMINAL_ISPEED = 4
    TERMINAL_OSPEED = 5
    TERMINAL_CC = 6

    def FlagsSave (self, on = None, off = None, index = TERMINAL_LFLAG):
        if not self.stream.isatty ():
            return

        # save
        flags = termios.tcgetattr (self.stream.fileno ())
        self.flags.append (list (flags))

        # update
        if on is not None:
            flags [index] |= on
        if off is not None:
            flags [index] &= ~off

        # set
        termios.tcsetattr (self.stream.fileno (), termios.TCSADRAIN, flags)

    def FlagsRestore (self):
        if not self.stream.isatty () or len (self.flags) == 0:
            return False
        termios.tcsetattr (self.stream.fileno (), termios.TCSADRAIN, self.flags.pop ())
        return True

    def NoEcho (self):
        self.FlagsSave (off = termios.ECHO)
        return Disposable (lambda: self.FlagsRestore ())

    #--------------------------------------------------------------------------#
    # Move                                                                     #
    #--------------------------------------------------------------------------#
    def MoveUp (self, count):
        if count > 0:
            self.stream.write (CSI_MOVE_UP.format (count))
        else:
            assert count == 0
            self.stream.write (CSI_MOVE_BEGIN)

    def MoveDown (self, count):
        if count > 0:
            self.stream.write (CSI_MOVE_DOWN.format (count))
        else:
            assert count == 0
            self.stream.write (CSI_MOVE_BEGIN)

    def MoveColumn (self, column):
        self.stream.write (CSI_MOVE_COLUMN.format (column))

    #--------------------------------------------------------------------------#
    # Lock                                                                     #
    #--------------------------------------------------------------------------#
    def acquire (self):
        if self.locked:
            raise ConsoleError ('Console is locked, leave previous update context first')
        self.locked = True

    def release (self):
        if not self.locked:
            raise ConsoleError ('Console is not locked')
        self.locked = False

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        while self.FlagsRestore ():
            pass

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

#------------------------------------------------------------------------------#
# Label                                                                        #
#------------------------------------------------------------------------------#
class Label (object):
    def __init__ (self, console):
        self.console  = console
        self.index    = len (console.labels)
        self.disposed = False

        # allocate label
        console.labels.append (self)
        console.stream.write ('\n')

    @contextmanager
    def Update (self, erase = True):
        if self.disposed:
            raise RuntimeError ('Label has already been disposed')

        position = len (self.console.labels) - self.index
        self.console.acquire ()
        self.console.MoveUp (position)
        if erase:
            self.console.stream.write (CSI_ERASE)

        try: yield
        finally:
            # move to the end label set
            self.console.MoveDown (position)
            self.console.stream.flush ()
            self.console.release ()

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        if self.disposed:
            return
        self.disposed = True

        # update label set
        del self.console.labels [self.index]
        for label in self.console.labels [self.index:]:
            label.index -= 1

        # delete label
        position = len (self.console.labels) - self.index + 1
        self.console.MoveUp (position)
        self.console.stream.write (CSI_DELETE)
        self.console.MoveDown (position - 1)
        self.console.stream.flush ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

#------------------------------------------------------------------------------#
# Control Sequence Initiator                                                   #
#------------------------------------------------------------------------------#
# REMARK:
#   Shorter version of CSI_MOVE_DOWN, CSI_MOVE_UP ('\x1b[{0}E', '\x1b[{0}F')
#   not so well supported for example by konsole. Moves with {0} = 0 is also
#   sometimes misinterpreted (xterm, linux, konsole)


CSI_SAVE        = '\x1b[s'          # save position
CSI_RESTORE     = '\x1b[u'          # restore position
CSI_SCROLL_UP   = '\x1b[{0}S'       # scroll {0} lines up
CSI_SCROLL_DOWN = '\x1b[{0}T'       # scroll {0} lines down

CSI_MOVE_DOWN   = '\x1b[{0}B\x1b[G' # move {0} lines down and to the first column
CSI_MOVE_UP     = '\x1b[{0}A\x1b[G' # move {0} lines up and to the first column
CSI_MOVE_BEGIN  = '\x1b[G'          # move to the first column
CSI_MOVE_COLUMN = '\x1b[{0}G'       # move to {0} column
CSI_DELETE      = '\x1b[1M'         # delete 1 line
CSI_INSERT      = '\x1b[1L'         # insert 1 line
CSI_ERASE       = '\x1b[2K'         # erase line (2 is "Clear All")

CSI_CURSOR_HIDE = '\x1b[?25l'       # hide cursor
CSI_CURSOR_SHOW = '\x1b[?25h'       # show cursor

CSI_COLOR       = '\x1b[{0}m'       # set color {0}
CSI_COLOR_RESET = '\x1b[m'          # reset color to default

#------------------------------------------------------------------------------#
# Errors                                                                       #
#------------------------------------------------------------------------------#
class ConsoleError (Exception): pass

# vim: nu ft=python columns=120 :
