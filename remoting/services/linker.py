# -*- coding: utf-8 -*-
import inspect

from .service import *
from ..async import *

__all__ = ('LinkerService',)

#-----------------------------------------------------------------------------#
# Ports                                                                       #
#-----------------------------------------------------------------------------#
PORT_LINKER_CREATE = 10
PORT_LINKER_INFO   = 11
PORT_LINKER_METHOD = 12
PORT_LINKER_GET    = 13
PORT_LINKER_SET    = 14
PORT_LINKER_CALL   = 15

PERSISTENCE_LINKER = 1
#-----------------------------------------------------------------------------#
# Linker                                                                      #
#-----------------------------------------------------------------------------#
class LinkerError (ServiceError): pass

class LinkerService (Service):
    def __init__ (self):
        self.local_d2r, self.remote_d2r = {}, {}
        self.desc = 0

        Service.__init__ (self, [
            (PORT_LINKER_CREATE, self.port_CREATE),
            (PORT_LINKER_INFO, self.port_INFO),
            (PORT_LINKER_METHOD, self.port_METHOD),
            (PORT_LINKER_GET, self.port_GET),
            (PORT_LINKER_SET, self.port_SET),
            (PORT_LINKER_CALL, self.port_CALL),
        ], [
            (PERSISTENCE_LINKER, self.save_Reference, self.restore_Reference)
        ])

        self.method_skip = {
            # creation
            '__init__', '__new__',
            # attributes
            '__getattr__', '__setattr__', '__delattr__', '__getattribute__',
            # pickle
            '__reduce_ex__', '__reduce__', '__getstate__', '__setstate__',
            # repr
            '__repr__', '__str__',
            # type
            '__class__', '__subclasshook__',
            # hash
            '__hash__'
        }

        def detach (channel):
            self.local_d2r.clear ()
            self.remote_d2r.clear ()
        self.OnDetach += detach

    def ToReference (self, target):
        """Create reference to target"""
        if self.channel is None:
            raise LinkerError ('channel hasn\'t been attached')

        if isinstance (target, Reference):
            if target.ref_linker == self:
                return target
            target = target.ref_target

        # methods
        members = {}
        for name, member in inspect.getmembers (target):
            if hasattr (member, '__call__') and name not in self.method_skip:
                members [name] = member

        # fields
        def getter (this, name):
            return getattr (target, name)
        def setter (this, name, value):
            setattr (target, name, value)
        members ['__getattr__'] = getter
        members ['__setattr__'] = setter

        # create reference
        desc, self.desc = self.desc, self.desc + 1
        ref = (type ('{0}_ref'.format (type (target).__name__), (Reference,), members) \
            (REFERENCE_LOCAL, self, desc, target))

        # update mapping
        self.local_d2r [desc] = ref

        return ref

    @Delegate
    def InstanceCreate (self, type, *args, **keys):
        return self.channel.Request (PORT_LINKER_CREATE, type = type,
            args = args, keys = keys).ContinueWithFunction (lambda msg: msg.reference)

    @Delegate
    def Call (self, func, *args, **keys):
        return (self.channel.Request (PORT_LINKER_CALL, func = func, args = args, keys = keys)
            .ContinueWithFunction (lambda msg: msg.result))

    # PERSISTENCE
    def save_Reference (self, ref):
        if isinstance (ref, Reference):
            return ref.ref_type, ref.ref_desc

    def restore_Reference (self, ref_state):
        ref_type, ref_desc = ref_state

        if ref_type == REFERENCE_LOCAL:
            # means local for remote host
            ref = self.remote_d2r.get (ref_desc)
            if ref is None:
                ref_future = self.restore_remote (ref_type, ref_desc)
                ref_future.Wait ()
                return ref_future.Result ()

        elif ref_type == REFERENCE_REMOTE:
            ref = self.local_d2r.get (ref_desc)
            if not ref:
                raise LinkerError ('unregistred reference descriptor')
        else:
            raise LinkerError ('invalid reference type: {0}'.format (ref_type))

        return ref

    @Async
    def restore_remote (self, ref_type, ref_desc):
        info = yield self.channel.Request (PORT_LINKER_INFO, desc = ref_desc)

        # create methods
        members = {}
        def method_factory (method_name):
            @Delegate
            def method (this, *args, **keys):
                return (self.channel.Request (PORT_LINKER_METHOD,
                    desc = ref_desc,
                    name = method_name,
                    args = args,
                    keys = keys)
                        .ContinueWithFunction (lambda msg: msg.result))
            return method

        for method_name in info.methods:
            members [method_name] = method_factory (method_name)

        @Delegate
        def getter (this, name):
            return (self.channel.Request (PORT_LINKER_GET, desc = ref_desc, name = name)
                .ContinueWithFunction (lambda msg: msg.result))
        @Delegate
        def setter (this, name, value):
            return self.channel.Request (PORT_LINKER_SET, desc = ref_desc, name = name, value = value)
        members ['__getattr__'] = getter
        members ['__setattr__'] = setter

        ref = type ('%s_remote_ref' % info.name, (Reference, ), members) \
            (REFERENCE_REMOTE, self, ref_desc, None)

        # update cache
        self.remote_d2r [ref_desc] = ref

        AsyncReturn (ref)

    # PORTS
    @DummyAsync
    def port_CREATE (self, msg):
        return msg.Result (reference = self.ToReference (msg.type (*msg.args, **msg.keys)))

    @DummyAsync
    def port_INFO (self, msg):
        instance = self.instance_get (msg)
        methods = [name for name, method in inspect.getmembers (instance)
            if hasattr (method, '__call__')
            if name not in self.method_skip]
        return msg.Result (methods = methods, name = type (instance).__name__)

    @DummyAsync
    def port_METHOD (self, msg):
        return msg.Result (result = getattr (self.instance_get (msg), msg.name) (*msg.args, **msg.keys))

    @DummyAsync
    def port_GET (self, request):
        return request.Result (result = getattr (self.instance_get (request), request.name))

    @DummyAsync
    def port_SET (self, request):
        setattr (self.instance_get (request), request.name, request.value)
        return request.Result ()

    @DummyAsync
    def port_CALL (self, request):
        return request.Result (result = request.func (*request.args, **request.keys))

    def instance_get (self, request):
        ref = self.local_d2r.get (request.desc)
        if not ref:
            raise ValueError ('bad descriptor {0}'.format (request.desc))
        return ref.ref_target

#-----------------------------------------------------------------------------#
# Reference                                                                   #
#-----------------------------------------------------------------------------#
REFERENCE_LOCAL = 0
REFERENCE_REMOTE = 1

class Reference (object):
    __slots__ = ('ref_type', 'ref_desc', 'ref_linker', 'ref_target')

    def __init__ (self, type, linker, desc, target):
        object.__setattr__ (self, 'ref_type', type)
        object.__setattr__ (self, 'ref_desc', desc)
        object.__setattr__ (self, 'ref_linker', linker)
        object.__setattr__ (self, 'ref_target', target)
# vim: nu ft=python columns=120 :
