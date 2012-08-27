# -*- coding: utf-8 -*-
import itertools

from .service      import Service, ServiceError
from ..message     import Message
from ...disposable import Disposable
from ...async      import Async, DummyAsync, Future, FutureSource, SucceededFuture, RaisedFuture

__all__ = ('FutureService',)
#------------------------------------------------------------------------------#
# Future Service                                                               #
#------------------------------------------------------------------------------#
class FutureServiceError (ServiceError): pass
class FutureService (Service):
    NAME    = b'future::'
    RESOLVE = b'future::resolve'

    FUTURE_SUCCESS = 0
    FUTURE_ERROR   = 1
    FUTURE_WAIT    = 2

    def __init__ (self):
        Service.__init__ (self,
            handlers = ((self.RESOLVE, self.resolve_handler),),
            persistence = ((Future, self.futurePack, self.futureUnpack),))

        self.desc        = itertools.count ()
        self.desc_info   = {} # desc   => info
        self.future_info = {} # future => info
        next (self.desc)

    @Async
    def Connect (self, domain):
        yield Service.Connect (self, domain)

        def dispose ():
            desc_info,   self.desc_info   = self.desc_info,   {}
            future_info, self.future_info = self.future_info, {}

            for desc, info in list (desc_info.items ()):
                if desc & 0x1:
                    info.Source.ErrorRaise (FutureServiceError ('Has disconnected before being resolved'))

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

        info = self.future_info.get (future)
        if info is None:
            desc = next (self.desc) << 1
            info = FutureInfo (desc, future)
            self.desc_info [desc], self.future_info [future] = info, info

            def resolve (future):
                if self.desc_info.pop (desc, None) is not None:
                    self.future_info.pop (future, None)

                    # data
                    error = future.Error ()
                    if error is None:
                        data = desc ^ 0x1, self.FUTURE_SUCCESS, future.Result ()
                    else:
                        data = desc ^ 0x1, self.FUTURE_ERROR, error [1]

                    # send
                    self.domain.channel.Send (Message (self.RESOLVE, self.domain.Pack (data)))

            future.Continue (resolve)

        return self.FUTURE_WAIT, info.Desc

    def futureUnpack (self, state):
        type, value = state
        if type == self.FUTURE_SUCCESS:
            return SucceededFuture (value)

        elif type == self.FUTURE_ERROR:
            return RaisedFuture (value)

        elif type == self.FUTURE_WAIT:
            desc = value ^ 0x1

            info = self.desc_info.get (desc)
            if info is None:
                source = FutureSource ()
                future = source.Future
                info   = FutureInfo (desc, future, source)
                self.desc_info [desc], self.future_info [future] = info, info

                def resolve (this):
                    self.desc_info.pop   (desc, None)
                    self.future_info.pop (future, None)

                future.Continue (resolve)

            return info.Future

        assert False, 'Unknown future type: {}'.format (type)

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    @DummyAsync
    def resolve_handler (self, message):
        desc, type, value = self.domain.Unpack (message.Data)

        info = self.desc_info.get (desc)
        if info is not None:
            if type == self.FUTURE_SUCCESS:
                info.Source.ResultSet (value)
            elif type == self.FUTURE_ERROR:
                info.Source.ErrorRaise (value)
            else:
                assert False, 'Invalid future type: {}'.format (type)

#------------------------------------------------------------------------------#
# Future Info                                                                  #
#------------------------------------------------------------------------------#
class FutureInfo (object):
    __slots__ = ('Desc', 'Future', 'Source',)

    def __init__ (self, desc, future, source = None):
        self.Desc   = desc
        self.Future = future
        self.Source = source

# vim: nu ft=python columns=120 :
