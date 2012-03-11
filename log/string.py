# -*- coding: utf-8 -*-

__all__ = ('String',)
#------------------------------------------------------------------------------#
# String                                                                       #
#------------------------------------------------------------------------------#
class String (object):
    def __init__ (self, *chunks):
        self.chunks = []
        self.length = 0

        for chunk in chunks:
            if isinstance (chunk, String):
                self.chunks.extend (chunk.chunks)
                self.length += len (chunk)
            elif isinstance (chunk, tuple):
                string, color = chunk
                string = str (string)
                self.chunks.append ((string, color))
                self.length += len (string)
            else:
                self.chunks.append ((chunk, None))
                self.length += len (chunk)

    #--------------------------------------------------------------------------#
    # Modify                                                                   #
    #--------------------------------------------------------------------------#
    def Append (self, string, *args, **keys):
        if isinstance (string, String):
            if args or keys:
                string.Format (*args, **keys)

            self.chunks.extend (string.chunks)
            self.length += len (string)
        else:
            string = str (string)
            if args or keys:
                string = string.format (*args, **keys)

            self.chunks.append ((string, None))
            self.length += len (string)

    def Format (self, *args, **keys):
        def format (pair):
            string, color = pair
            return string.format (*args, **keys), color
        return String (*(map (format, self.chunks)))

    #--------------------------------------------------------------------------#
    # String like behavior                                                     #
    #--------------------------------------------------------------------------#
    def __len__ (self):
        return self.length

    def __iter__ (self):
        return iter (self.chunks)

    def __bool__ (self):
        return bool (self.length)

    def __nonzero__ (self):
        return bool (self.length)
# vim: nu ft=python columns=120 :