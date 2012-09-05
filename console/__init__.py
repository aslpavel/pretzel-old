# -*- coding: utf-8 -*-
from . import text, console
from .console import *
from .text    import *

__all__ = console.__all__ + text.__all__
# vim: nu ft=python columns=120 :
