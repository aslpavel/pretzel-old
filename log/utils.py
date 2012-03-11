# -*- coding: utf-8 -*-

__all__ = ('Cached', )
#------------------------------------------------------------------------------#
# Cached Decorator                                                             #
#------------------------------------------------------------------------------#
def Cached (function):
    cache, token = {}, object ()
    def function_cached (*args):
        result = cache.get (args, token)
        if result is token:
            result = function (*args)
            cache [args] = result
        return result
    return function_cached
# vim: nu ft=python columns=120 :
