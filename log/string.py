# -*- coding: utf-8 -*-

__all__ = ('String',)
#------------------------------------------------------------------------------#
# String                                                                       #
#------------------------------------------------------------------------------#
class String (object):
    __slots__ = ('chunks', 'length')

    def __init__ (self, *items):
        self.chunks = []
        self.length = 0

        for item in items:
            self.Append (item)

    #--------------------------------------------------------------------------#
    # Append                                                                   #
    #--------------------------------------------------------------------------#
    def Append (self, other):
        if isinstance (other, String):
            self.chunks.extend (other.chunks)
            self.length += other.length
        elif isinstance (other, tuple):
            self.chunks.append (other)
            self.length += len (other [0])
        else:
            self.chunks.append ((other, None))
            self.length += len (other)

    def __iadd__ (self, other):
        self.Append (other)
        return self

    #--------------------------------------------------------------------------#
    # Format                                                                   #
    #--------------------------------------------------------------------------#
    def Format (self, *args, **keys):
        def format (chunk):
            string, color = chunk
            return string.format (*args, **keys), color
        return String (*(map (format, self.chunks)))

    #--------------------------------------------------------------------------#
    # Interfaces                                                               #
    #--------------------------------------------------------------------------#
    def __len__ (self):
        return self.length

    def __iter__ (self):
        return iter (self.chunks)

    def __bool__ (self):
        return self.length > 0

    def __nonzero__ (self):
        return self.length > 0

# vim: nu ft=python columns=120 :
