# -*- coding: utf-8 -*-
import sys
import struct
import itertools

from .service      import Service, ServiceError
from ..message     import Message
from ..result      import Result
from ...disposable import Disposable
from ...async      import Async, DummyAsync, Future, FutureSource, SucceededFuture, FailedFuture

__all__ = ('FutureService',)
#------------------------------------------------------------------------------#
# Future Service                                                               #
#------------------------------------------------------------------------------#
class FutureServiceError (ServiceError): pass
class FutureService (Service):
    # service
    NAME    = b'future::'
    RESOLVE = b'future::resolve'

    # persistence
    FUTURE_DONE = 0
    FUTURE_WAIT = 1

    # resolve helper struct
    desc_struct = struct.Struct ('!Q')

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
            with Result () as result:
                result (self.domain.Pack (future.Result ()))
            return self.FUTURE_DONE, result.ToBytes ()

        info = self.future_info.get (future)
        if info is None:
            desc = next (self.desc) << 1
            info = FutureInfo (desc, future)
            self.desc_info [desc], self.future_info [future] = info, info

            def resolve (result, error):
                if self.desc_info.pop (desc, None) is not None:
                    self.future_info.pop (future, None)

                    # result
                    with Result () as result:
                        result (self.domain.Pack (future.Result ()))

                    # send
                    value = self.desc_struct.pack (desc ^ 0x1) + result.ToBytes ()
                    self.domain.channel.Send (Message.FromValue (value, self.RESOLVE))

            future.Continue (resolve)

        return self.FUTURE_WAIT, info.Desc

    def futureUnpack (self, state):
        type, value = state
        if type == self.FUTURE_DONE:
            try:
                return SucceededFuture (self.domain.Unpack (Result.FromBytes (value).Value ()))
            except Exception:
                return FailedFuture (sys.exc_info ())

        elif type == self.FUTURE_WAIT:
            desc = value ^ 0x1

            info = self.desc_info.get (desc)
            if info is None:
                source = FutureSource ()
                future = source.Future
                info   = FutureInfo (desc, future, source)
                self.desc_info [desc], self.future_info [future] = info, info

                def resolve (result, error):
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
        value  = message.Value ()
        desc   = self.desc_struct.unpack (value [:self.desc_struct.size]) [0]
        result = Result.FromBytes (value [self.desc_struct.size:])

        info = self.desc_info.get (desc)
        if info is not None:
            try:
                info.Source.ResultSet (self.domain.Unpack (result.Value ()))
            except Exception:
                info.Source.ErrorSet (sys.exc_info ())

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
