# -*- coding: utf-8 -*-
import io
import sys
import fcntl
import struct
import termios

from .csi  import *
from .text import Text, TEXT_ENCODING
from ..disposable import Disposable

__all__ = ('Console', 'ConsoleError',)
#------------------------------------------------------------------------------#
# Console                                                                      #
#------------------------------------------------------------------------------#
class ConsoleError (Exception): pass
class Console (object):
    default_size = (80, 40)

    def __init__ (self, stream = None):
        self.stream = stream or io.open (sys.stderr.fileno (), 'wb', closefd = False)
        self.labels = []
        self.flags  = []

        self.stream.write (CursorVisible (False))

    #--------------------------------------------------------------------------#
    # Write                                                                    #
    #--------------------------------------------------------------------------#
    def Write (self, *texts):
        write = self.stream.write

        for text in texts:
            if isinstance (text, Text):
                write (text.EncodeCSI ())
            else:
                write (str (text).encode (TEXT_ENCODING))

    def WriteBytes (self, value):
        self.stream.write (value)

    #--------------------------------------------------------------------------#
    # Line                                                                     #
    #--------------------------------------------------------------------------#
    def Line (self):
        position = len (self.labels) + 1
        write    = self.stream.write
        write (b'\n')
        write (MoveUp (position))
        write (Insert (1))

        return Disposable (lambda: (
            write (MoveUp (-position)),
            write (MoveColumn (0)),
            self.stream.flush ()))

    #--------------------------------------------------------------------------#
    # Label                                                                    #
    #--------------------------------------------------------------------------#
    def Label (self):
        return ConsoleLabel (self)

    #--------------------------------------------------------------------------#
    # Size                                                                     #
    #--------------------------------------------------------------------------#
    def Size (self):
        if not self.stream.isatty ():
            return self.default_size

        rows, columns, xpixel, ypixel = struct.unpack ('4H',
            fcntl.ioctl (self.stream.fileno (), termios.TIOCGWINSZ, struct.pack ('4H', 0, 0, 0, 0)))
        return rows, columns

    #--------------------------------------------------------------------------#
    # Flush                                                                    #
    #--------------------------------------------------------------------------#
    def Flush (self):
        return self.stream.flush ()

    #--------------------------------------------------------------------------#
    # Moves                                                                    #
    #--------------------------------------------------------------------------#
    def Move (self, row = None, column = None):
        if row is not None:
            self.stream.write (MoveUp (row))
        if column is not None:
            self.stream.write (MoveColumn (column))

    #--------------------------------------------------------------------------#
    # Flags                                                                    #
    #--------------------------------------------------------------------------#
    TERMINAL_IFLAG  = 0
    TERMINAL_OFLAG  = 1
    TERMINAL_CFLAG  = 2
    TERMINAL_LFLAG  = 3
    TERMINAL_ISPEED = 4
    TERMINAL_OSPEED = 5
    TERMINAL_CC     = 6

    def FlagsPush (self, on = None, off = None, index = TERMINAL_LFLAG):
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

    def FlagsPop (self):
        if not self.stream.isatty () or len (self.flags) == 0:
            return False

        termios.tcsetattr (self.stream.fileno (), termios.TCSADRAIN, self.flags.pop ())
        return True

    def NoEcho (self):
        self.FlagsPush (off = termios.ECHO)
        return Disposable (lambda: self.FlagsPop ())

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        # destroy labels
        for label in tuple (self.labels):
            label.Dispose ()

        # restore flags
        while self.FlagsPop ():
            pass

        self.stream.write (CursorVisible (True))
        self.stream.write (b'\x1b[m')
        self.stream.flush ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

#------------------------------------------------------------------------------#
# Console Label                                                                #
#------------------------------------------------------------------------------#
class ConsoleLabel (object):
    def __init__ (self, console):
        self.console = console
        self.index   = len (console.labels)

        console.labels.append (self)
        console.stream.write (b'\n')

    #--------------------------------------------------------------------------#
    # Update                                                                   #
    #--------------------------------------------------------------------------#
    def Update (self, erase = None):
        if self.index < 0:
            raise ConsoleError ('Label has already been disposed')

        position = len (self.console.labels) - self.index
        write    = self.console.stream.write
        write (MoveUp (position))
        write (MoveColumn (0))

        if erase is None or erase:
            write (Erase ())

        return Disposable (lambda: (
            write (MoveUp (-position)),
            write (MoveColumn (0)),
            self.console.stream.flush ()))

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        if self.index < 0:
            return
        index, self.index = self.index, -1

        del self.console.labels [index]
        for label in self.console.labels [index:]:
            label.index -= 1

        position = len (self.console.labels) - index + 1
        write    = self.console.stream.write
        # cursor -> label
        write (MoveUp (position))
        write (MoveColumn (0))
        write (Delete (1))
        # cursor -> end
        write (MoveUp (-position + 1))
        self.console.stream.flush ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

# vim: nu ft=python columns=120 :
