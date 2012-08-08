# -*- coding: utf-8 -*-

__all__ = ('Queryable',)
#------------------------------------------------------------------------------#
# Queryable                                                                    #
#------------------------------------------------------------------------------#
class Queryable (object):
    __slots__ = ('provider', 'query')

    def __init__ (self, provider, query = None):
        self.provider = provider
        self.query    = query if query else tuple ()

    def __get__  (self, instance, owner):
        if instance is None:
            return self

        return Queryable (lambda args, keys, query:
            self.provider (instance, args, keys, query), self.query)

    def __getattr__ (self, name):
        return Queryable (self.provider, self.query + (name,))

    def __call__ (self, *args, **keys):
        return self.provider (args, keys, self.query)


# vim: nu ft=python columns=120 :
