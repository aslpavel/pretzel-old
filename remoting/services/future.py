# -*- coding: utf-8 -*-
import itertools

from .service import *
from ..message import *
from ...disposable import *
from ...async import *
from ...async.cancel import *

__all__ = ('FutureService',)
#------------------------------------------------------------------------------#
# Future Service                                                               #
#------------------------------------------------------------------------------#
class FutureServiceError (Exception): pass
class FutureService (Service):
    NAME    = b'future::'
    RESOLVE = b'future::resolve'

    FUTURE_SUCCESS = 0
    FUTURE_ERROR   = 1
    FUTURE_WAIT    = 2

    def __init__ (self):
        Service.__init__ (self,
            handlers = ((self.RESOLVE, self.resolve_handler),),
            persistence = ((BaseFuture, self.futurePack, self.futureUnpack),))

        self.desc        = itertools.count ()
        self.desc2future = {}
        self.future2desc = {}
        next (self.desc)

    @Async
    def Connect (self, domain):
        yield Service.Connect (self, domain)

        def dispose ():
            desc2future, self.desc2future = self.desc2future, {}
            future2desc, self.future2desc = self.future2desc, {}
            for desc, future in list (desc2future.items ()):
                if desc & 0x1:
                    future.ErrorRaise (FutureServiceError ('Has disconnected before being resolved'))
        self.dispose += Disposable (dispose)

    #--------------------------------------------------------------------------#
    # Marshal                                                                  #
    #--------------------------------------------------------------------------#
    def futurePack (self, future):
        if future.IsCompleted ():
            error = future.Error ()
            if error is None:
                return self.FUTURE_SUCCESS, future.Result ()
            return self.FUTURE_ERROR, error [1]

        desc = self.future2desc.get (future)
        if desc is None:
            desc = next (self.desc) << 1
            self.desc2future [desc], self.future2desc [future] = future, desc

            def resolve (future):
                self.desc2future.pop (desc, None)
                self.future2desc.pop (future, None)

                error = future.Error ()
                if error is None:
                    data = desc ^ 0x1, self.FUTURE_SUCCESS, future.Result () 
                else:
                    data = desc ^ 0x1, self.FUTURE_ERROR, error [1]
                self.domain.channel.Send (Message (self.RESOLVE, self.domain.Pack (data)))
                    
            future.Continue (resolve).Traceback ()

        return self.FUTURE_WAIT, desc

    def futureUnpack (self, state):
        type, value = state
        if type == self.FUTURE_SUCCESS:
            return SucceededFuture (value)

        elif type == self.FUTURE_ERROR:
            return RaisedFuture (value)

        elif type == self.FUTURE_WAIT:
            desc   = value ^ 0x1
            future = self.desc2future.get (desc)
            if future is None:
                def resolve (future):
                    self.desc2future.pop (desc, None)
                    self.future2desc.pop (future, None)

                def cancel ():
                    resolve ()
                    future.ErrorRaise (FutureCanceled ())

                future = Future (cancel = Cancel (cancel))
                future.Continue (resolve)

                self.desc2future [desc], self.future2desc [future] = future, desc

            return future

        assert False, 'Unknown future type: {}'.format (type)
            
    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    @DummyAsync
    def resolve_handler (self, message):
        desc, type, value = self.domain.Unpack (message.Data)
        future = self.desc2future.get (desc)
        if future is not None:
            if type == self.FUTURE_SUCCESS:
                future.ResultSet (value)
            elif type == self.FUTURE_ERROR:
                future.ErrorRaise (value)
            else:
                assert False, 'Invalid future type: {}'.format (type)

# vim: nu ft=python columns=120 :
