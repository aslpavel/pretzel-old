# -*- coding: utf-8 -*-
import sys
import io
import itertools
import traceback

__all__ = ('Message', 'PORT_RESULT', 'PORT_ERROR', 'PORT_SYSTEM')
#-----------------------------------------------------------------------------#
# Ports                                                                       #
#-----------------------------------------------------------------------------#
PORT_RESULT = 0
PORT_ERROR  = 1
PORT_SYSTEM = 10

#-----------------------------------------------------------------------------#
# Message                                                                     #
#-----------------------------------------------------------------------------#
class Message (object):
    __slots__ = ('uid', 'port', 'attr')
    _uid = itertools.count ()
    def __init__ (self, port, **attr):
        object.__setattr__ (self, 'uid', next (self._uid))
        object.__setattr__ (self, 'port', port)
        object.__setattr__ (self, 'attr', attr)

    #--------------------------------------------------------------------------#
    # Attributes                                                               #
    #--------------------------------------------------------------------------#
    def __getattr__ (self, attr):
        try: return self.attr [attr]
        except KeyError:
            pass
        raise AttributeError (attr)

    def __setattr__ (self, attr, value):
        raise AttributeError ('Message attributes are read only')

    #--------------------------------------------------------------------------#
    # Save | Restore                                                           #
    #--------------------------------------------------------------------------#
    def __setstate__ (self, state):
        port, uid, attr =  state
        object.__setattr__ (self, 'uid', uid)
        object.__setattr__ (self, 'port', port)
        object.__setattr__ (self, 'attr', attr)

    def __getstate__  (self):
        return self.port, self.uid, self.attr

    #--------------------------------------------------------------------------#
    # Create Response                                                          #
    #--------------------------------------------------------------------------#
    def Result (self, **attr):
        return ResponseMessage (self, **attr)

    def Error (self, error):
        return ErrorMessage (self, *error)

    def Raise (self, error):
        try: raise error
        except Exception:
            return self.Error (*sys.exc_info ())

#-----------------------------------------------------------------------------#
# Response Message                                                            #
#-----------------------------------------------------------------------------#
class ResponseMessage (Message):
    __slots__ = Message.__slots__
    def __init__ (self, _source, **attr):
        object.__setattr__ (self, 'port', PORT_RESULT)
        object.__setattr__ (self, 'uid', _source.uid)
        object.__setattr__ (self, 'attr', attr)

#-----------------------------------------------------------------------------#
# Error Message                                                               #
#-----------------------------------------------------------------------------#
class ErrorMessage (Message):
    __slots__ = Message.__slots__
    def __init__ (self, _source, et, eo, tb):
        object.__setattr__ (self, 'port', PORT_ERROR)
        object.__setattr__ (self, 'uid', _source.uid)
        object.__setattr__ (self, 'attr', {
            'error_type' : et,
            'error'      : eo,
            'traceback'  : traceback.format_exception (et, eo, tb)
        })

    def exc_info (self):
        tb_stream = io.StringIO () if sys.version_info [0] > 2 else io.BytesIO ()
        tb_stream.write ('\n`{0:-^79}\n'.format (' remote traceback '))
        tb_stream.write (''.join (self.traceback).rstrip ('\n'))
        return self.error_type, self.error_type (tb_stream.getvalue ()), None

# vim: nu ft=python columns=120 :
