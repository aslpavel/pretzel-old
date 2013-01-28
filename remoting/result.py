# -*- coding: utf-8 -*-
import io
import os
import sys
import socket

from traceback import format_exception
if sys.version_info [0] > 2:
    string_type = io.StringIO
    PY2 = False
else:
    string_type = io.BytesIO
    PY2 = True

__all__ = ('Result', 'ResultSender',)
#------------------------------------------------------------------------------#
# Result                                                                       #
#------------------------------------------------------------------------------#
class ResultReturn (BaseException):
    """Result return exception
    """
    __slots__ = tuple ()

class Result (object):
    """Result

    Serializable object containing result of the execution (value or exception).
    """
    __slots__ = ('state', 'value',)

    pid  = os.getpid ()
    host = socket.gethostname ()

    STATE_NONE  = 0x0
    STATE_DONE  = 0x1
    STATE_FAIL  = 0x2
    STATE_ERROR = STATE_DONE | STATE_FAIL

    def __init__ (self, state = None, value = None):
        self.state = state or self.STATE_NONE
        self.value = value

    #--------------------------------------------------------------------------#
    # Set Result                                                               #
    #--------------------------------------------------------------------------#
    def SetResult (self, result):
        """Set result
        """
        if self.state & self.STATE_DONE:
            raise ValueError ('Result has already been set')

        self.state |= self.STATE_DONE
        self.value  = result
        return self

    def SetError (self, error):
        """Set error
        """
        if self.state & self.STATE_DONE:
            raise ValueError ('Result has already been set')

        # create string traceback
        traceback = traceback_template.format (
            host      = self.host,
            pid       = self.pid,
            name      = error [0].__name__,
            message   = str (error [1]),
            traceback = ''.join (format_exception (*error)))

        # saved traceback
        traceback_saved = getattr (error [1], '_saved_traceback', None)
        if traceback_saved is not None:
            traceback += traceback_saved

        # update error
        error = error [1]
        error._saved_traceback = traceback

        self.state |= self.STATE_ERROR
        self.value  = error
        return self

    def SetCurrentError (self):
        """Set error from current active exception
        """
        return self.SetError (sys.exc_info ())

    #--------------------------------------------------------------------------#
    # Get Result                                                               #
    #--------------------------------------------------------------------------#
    def GetResult (self):
        """Get result
        """
        return self ()

    def __call__ (self):
        """Get result
        """
        if self.state & self.STATE_DONE:
            if self.state & self.STATE_FAIL:
                raise self.value
            else:
                return self.value
        else:
            raise ValueError ('Result has not been resolved')

    #--------------------------------------------------------------------------#
    # Scope                                                                    #
    #--------------------------------------------------------------------------#
    def __enter__ (self):
        """Enter result scope
        """
        def result_return (result):
            """Return from result scope
            """
            raise ResultReturn (result)

        return result_return

    def __exit__ (self, et, eo, tb):
        """Leave result scope
        """
        if et is None:
            self.SetResult (None)
        else:
            if et is ResultReturn:
                self.SetResult (eo.args [0])
            elif issubclass (et, Exception):
                self.SetError ((et, eo, tb))
            else:
                return False
        return True

    #--------------------------------------------------------------------------#
    # Pickle                                                                   #
    #--------------------------------------------------------------------------#
    def __reduce__ (self):
        """Reduce result
        """
        return Result, (self.state, self.value,)

    #--------------------------------------------------------------------------#
    # To String                                                                #
    #--------------------------------------------------------------------------#
    def __str__ (self):
        """String representation
        """
        return '<{} [{}]>'.format (type (self).__name__,
            '?' if not self.state & self.STATE_DONE else
            '~{}'.format (self.value) if self.state & self.STATE_FAIL else
            '={}'.format (self.value))

    def __repr__ (self):
        """String representation
        """
        return str (self)

traceback_template = """
`-------------------------------------------------------------------------------
Location : {host}/{pid}
Error    : {name}: {message}

{traceback}"""

#------------------------------------------------------------------------------#
# Result Sender                                                                #
#------------------------------------------------------------------------------#
class ResultSender (object):
    """Result sender
    """
    __slots__ = ('sender',)

    def __init__ (self, sender):
        self.sender = sender

    #--------------------------------------------------------------------------#
    # Send                                                                     #
    #--------------------------------------------------------------------------#
    def __call__ (self, result = None):
        """Send result
        """
        raise ResultReturn (result)

    #--------------------------------------------------------------------------#
    # Scope                                                                    #
    #--------------------------------------------------------------------------#
    def __enter__ (self):
        """Enter sender scope
        """
        return self

    def __exit__ (self, et, eo, tb):
        """Leave sender scope
        """
        if self.sender is not None:
            try:
                if et is None:
                    self.sender.Send (Result ().SetResult (None))
                else:
                    if et is ResultReturn:
                        self.sender.Send (Result ().SetResult (eo.args [0]))
                    elif issubclass (et, Exception):
                        self.sender.Send (Result ().SetError ((et, eo, tb)))
                    else:
                        return False
            except Exception:
                # Failed to send result (It is probably failed to pickle), try
                # to send error.
                self.sender.Send (Result ().SetCurrentError ())
        return True

#------------------------------------------------------------------------------#
# Result Print Exception                                                       #
#------------------------------------------------------------------------------#
def ResultPrintException (et, eo, tb, file = None):
    stream = file or string_type ()

    traceback = ''.join (format_exception (et, eo, tb))
    stream.write (traceback.encode ('utf-8') if PY2 else traceback)

    # chain traceback
    traceback_saved = getattr (eo, '_saved_traceback', None)
    if traceback_saved is not None:
        stream.write (traceback_saved)

    if file is None:
        sys.stderr.write (stream.getvalue ())
        sys.stderr.flush ()

# install exception hook
sys.excepthook = ResultPrintException

# vim: nu ft=python columns=120 :
