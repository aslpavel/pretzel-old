# -*- coding: utf-8 -*-
from ...console.text import *

__all__ = ('PendingDrawer', 'PENDING_BUSY', 'PENDING_DONE', 'PENDING_FAIL',
            'BarDrawer', 'TimeDrawer', 'TagDrawer',)
#------------------------------------------------------------------------------#
# Colors                                                                       #
#------------------------------------------------------------------------------#
COLOR_OK       = Color (COLOR_GREEN)
COLOR_OK_BOLD  = Color (COLOR_GREEN, None, ATTR_BOLD)
COLOR_ERR      = Color (COLOR_RED)
COLOR_ERR_BOLD = Color (COLOR_RED, None, ATTR_BOLD)
COLOR_WRN      = Color (COLOR_YELLOW)
COLOR_WRN_BOLD = Color (COLOR_YELLOW, None, ATTR_BOLD)
COLOR_PRI = Color (COLOR_MAGENTA, None, ATTR_BOLD)
COLOR_SEC = Color (COLOR_MAGENTA)

#------------------------------------------------------------------------------#
# Pending Label                                                                #
#------------------------------------------------------------------------------#
PENDING_BUSY = 0
PENDING_DONE = 1
PENDING_FAIL = 2

class PendingDrawer (object):
    __slots__    = ('console',)
    pending_busy = Text (('[', COLOR_SEC), ('busy', COLOR_PRI), (']', COLOR_SEC)).EncodeCSI ()
    pending_done = Text (('[', COLOR_OK), ('done', COLOR_OK_BOLD), (']', COLOR_OK)).EncodeCSI ()
    pending_fail = Text (('[', COLOR_ERR), ('fail', COLOR_ERR_BOLD), (']', COLOR_ERR)).EncodeCSI ()

    def __init__ (self, console):
        self.console = console

    def __call__ (self, status):
        self.console.WriteBytes (
            self.pending_busy if status == PENDING_BUSY else
            self.pending_done if status == PENDING_DONE else
            self.pending_fail)

        return 6 # width

#------------------------------------------------------------------------------#
# Bar Drawer                                                                   #
#------------------------------------------------------------------------------#
class BarDrawer (object):
    __slots__     = ('console', 'width',)
    default_width = 20
    bar_begin     = '[', COLOR_SEC
    bar_end       = ']', COLOR_SEC
    bar_cache     = {}

    def __init__ (self, console, width = None):
        self.console = console
        self.width   = width  or self.default_width

    def __call__ (self, value):
        if value > 1:
            raise ValueError ('Bad bar value: {}'.format (value))

        filled = round (value * (self.width - 2))
        bar = self.bar_cache.get ((self.width, filled))
        if bar is None:
            text = Text ()
            text.Write (*self.bar_begin)
            with text.Color (COLOR_PRI):
                text.Write ('#' * filled)
                text.Write ('-' * (self.width - filled - 2))
            text.Write (*self.bar_end)

            bar = text.EncodeCSI ()
            self.bar_cache [(self.width, filled)] = bar

        self.console.WriteBytes (bar)
        return self.width

#------------------------------------------------------------------------------#
# Time Drawer                                                                  #
#------------------------------------------------------------------------------#
class TimeDrawer (object):
    __slots__ = ('console',)

    def __init__ (self, console):
        self.console = console

    def __call__ (self, seconds):
        hours,   seconds = divmod (seconds, 3600)
        minutes, seconds = divmod (seconds, 60)
        time_string = '[{:0>2.0f}:{:0>2.0f}:{:0>4.1f}]'.format (hours, minutes, seconds)

        text = Text ()
        with text.Color (COLOR_SEC):
            text.Write (time_string)

        self.console.Write (text)
        return len (time_string)

#------------------------------------------------------------------------------#
# Tag Drawer                                                                   #
#------------------------------------------------------------------------------#
class TagDrawer (object):
    __slots__ = ('console', 'fg', 'bg', 'cache',)

    def __init__ (self, console, color):
        self.console = console
        self.fg    = Color (color, attr = ATTR_BOLD)
        self.bg    = Color (color, attr = ATTR_FORCE)
        self.cache = {}

    def __call__ (self, label):
        tag = self.cache.get (label)
        if tag is None:
            text = Text ()
            with text.Color (self.bg):
                text.Write ('[')
                with text.Color (self.fg):
                    text.Write (label)
                text.Write (']')

            tag = text.EncodeCSI ()
            self.cache [label] = tag

        self.console.WriteBytes (tag)
        return len (label) + 2

# vim: nu ft=python columns=120 :
