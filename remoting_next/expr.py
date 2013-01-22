# -*- coding: utf-8 -*-
import io
import sys
import itertools
if sys.version_info [0] > 2:
    string_type = io.StringIO
else:
    string_type = io.BytesIO

from ..async import Async, AsyncReturn

__all__ = ('Expr', 'LoadArgExpr', 'LoadConstExpr', 'CallExpr',
           'GetAttrExpr', 'SetAttrExpr', 'GetItemExpr', 'SetItemExpr',
           'ReturnExpr', 'RaiseExpr', 'AwaitExpr', 'Code',)

#------------------------------------------------------------------------------#
# Expression                                                                   #
#------------------------------------------------------------------------------#
class Expr (object):
    """Expression object
    """
    __slots__ = tuple ()

    def Compile (self, code):
        """Compile expression
        """

    def String (self):
        """String representation
        """
        return 'Nop'

    def __str__  (self): return self.String ()
    def __repr__ (self): return self.String ()

class LoadArgExpr (Expr):
    """Load argument on stack
    """
    __slots__ = ('index',)

    def __init__ (self, index):
        self.index = index

    def Compile (self, code):
        code.Emit (OP_LDARG, self.index)

    def String (self):
        return 'arg [{}]'.format (self.index)

class LoadConstExpr (Expr):
    """Load constant on stack
    """
    __slots__ = ('const',)

    def __init__ (self, const):
        self.const = const

    def Compile (self, code):
        code.Emit (OP_LDCONST, self.const)

    def String (self):
        return repr (self.const)

class CallExpr (Expr):
    """Call expression (arguments are expressions)
    """
    __slots__ = ('fn', 'args', 'keys',)

    def __init__ (self, fn, *args, **keys):
        self.fn   = fn
        self.args = args
        self.keys = keys

    def Compile (self, code):
        compile (self.fn, code)
        if self.args:
            for arg in self.args:
                compile (arg, code)

        if self.keys:
            for key, value in self.keys.items ():
                code.Emit (OP_LDCONST, key)
                compile (value, code)

        code.Emit (OP_CALL, (len (self.args), len (self.keys)))

    def String (self):
        return '{} ({}{}{})'.format (self.fn,
               ', '.join (repr (arg) for arg in self.args),
               ', ' if self.args and self.keys else '',
               ', '.join ('{} = {}'.format (key, value) for key, value in self.keys.items ()))

class GetAttrExpr (Expr):
    """Get attribute expression
    """
    __slots__ = ('target', 'name',)

    def __init__ (self, target, name):
        self.target = target
        self.name = name

    def Compile (self, code):
        compile (self.target, code)
        code.Emit (OP_GETATTR, self.name)

    def String (self):
        return '{}.{}'.format (self.target, self.name)

class SetAttrExpr (Expr):
    """Set attribute expression
    """
    __slots__ = ('target', 'name', 'value',)

    def __init__ (self, target, name, value):
        self.target = target
        self.name = name
        self.value = value

    def Compile (self, code):
        compile (self.value, code)
        compile (self.target, code)
        code.Emit (OP_SETATTR, self.name)

    def String (self):
        return '{}.{} = {}'.format (self.target, self.name, self.value)

class GetItemExpr (Expr):
    """Get item expression
    """
    __slots__ = ('target', 'item',)

    def __init__ (self, target, item):
        self.target = target
        self.item = item

    def Compile (self, code):
        compile (self.target, code)
        compile (self.item, code)
        code.Emit (OP_GETITEM)

    def String (self):
        return '{} [{}]'.format (self.target, self.item)

class SetItemExpr (Expr):
    """Set item expression
    """
    __slots__ = ('target', 'item', 'value',)

    def __init__ (self, target, item, value):
        self.target = target
        self.item = item
        self.value = value

    def Compile (self, code):
        compile (self.value, code)
        compile (self.target, code)
        compile (self.item, code)
        code.Emit (OP_SETITEM)

    def String (self):
        return '{} [{}] = {}'.format (self.target, self.item, self.value)

class ReturnExpr (Expr):
    """Return expression
    """
    __slots__ = ('result',)

    def __init__ (self, result):
        self.result = result

    def Compile (self, code):
        compile (self.result, code)
        code.Emit (OP_RETURN)

    def String (self):
        return 'return {}'.format (self.result)

class RaiseExpr (Expr):
    """Raise epxression
    """
    __slots__ = ('error',)

    def __init__ (self, error):
        self.error = error

    def Compile (self, code):
        compile (self.error, code)
        code.Emit (OP_RAISE)

    def String (self):
        return 'raise {}'.format (self.error)

class AwaitExpr (Expr):
    """Await expression
    """
    __slots__ = ('target',)

    def __init__ (self, target):
        self.target = target

    def Compile (self, code):
        compile (self.target, code)
        code.Emit (OP_AWAIT)

    def String (self):
        return 'await {}'.format (self.target)

def compile (target, code):
    """Compile target

    Compiles target if its expression otherwise emits constant
    opcode with target as its value.
    """
    if isinstance (target, Expr):
        target.Compile (code)
    else:
        code.Emit (OP_LDCONST, target)

#------------------------------------------------------------------------------#
# Operation Codes                                                              #
#------------------------------------------------------------------------------#
OP = itertools.count (1)
OP_LDARG     = next (OP)
OP_LDCONST   = next (OP)
OP_CALL      = next (OP)
OP_GETATTR   = next (OP)
OP_SETATTR   = next (OP)
OP_GETITEM   = next (OP)
OP_SETITEM   = next (OP)
OP_RETURN    = next (OP)
OP_RAISE     = next (OP)
OP_AWAIT     = next (OP)
del OP

opToName = {
    OP_LDARG   : 'LOAD_ARG',
    OP_LDCONST : 'LOAD_CONST',
    OP_CALL    : 'CALL',
    OP_GETATTR : 'ATTR_GET',
    OP_SETATTR : 'ATTR_SET',
    OP_GETITEM : 'ITEM_GET',
    OP_SETITEM : 'ITEM_SET',
    OP_RETURN  : 'RETURN',
    OP_RAISE   : 'RAISE',
    OP_AWAIT   : 'AWAIT',
}

#------------------------------------------------------------------------------#
# Code                                                                         #
#------------------------------------------------------------------------------#
class Code (list):
    """Code object
    """

    #--------------------------------------------------------------------------#
    # Emit                                                                     #
    #--------------------------------------------------------------------------#
    def Emit (self, op, arg = None):
        """Emit opcode
        """
        self.append ((op, arg))

    #--------------------------------------------------------------------------#
    # Execute                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def __call__ (self, *args):
        """Execute code
        """
        pos   = 0
        stack = []

        code_size = len (self)
        while pos < code_size:
            op, arg = self [pos]
            pos += 1
            if op == OP_LDARG:
                stack.append (args [arg])

            elif op == OP_LDCONST:
                stack.append (arg)

            elif op == OP_CALL:
                a_count, kw_count = arg
                if kw_count:
                   kw = {}
                   for _ in range (kw_count):
                       v, k = stack.pop (), stack.pop ()
                       kw [k] = v
                if a_count:
                    a = reversed ([stack.pop () for _ in range (a_count)])
                fn = stack.pop ()
                stack.append (
                    fn (*a, **kw) if a_count and kw_count else
                    fn (*a)       if a_count else
                    fn ())

            elif op == OP_RETURN:
                break

            elif op == OP_RAISE:
                raise arg

            elif op == OP_AWAIT:
                stack.append ((yield stack.pop ()))

            elif op == OP_GETATTR:
                stack.append (getattr (stack.pop (), arg))

            elif op == OP_SETATTR:
                setattr (stack.pop (), arg, stack.pop ())

            elif op == OP_GETITEM:
                item   = stack.pop ()
                target = stack.pop ()

                stack.append (target [item])

            elif op == OP_SETITEM:
                item   = stack.pop ()
                target = stack.pop ()
                value  = stack.pop ()

                target [item] = value

            else:
                raise ValueError ('Unknown opcode: {}'.format (op))

        AsyncReturn (stack.pop () if stack else None)

    #--------------------------------------------------------------------------#
    # To String                                                                #
    #--------------------------------------------------------------------------#
    def __str__ (self):
        """String representation
        """
        stream = string_type ()
        stream.write ('<Code:')
        for op, arg in self:
            stream.write ('\n  {:<11}{}'.format (opToName.get (op, 'UNKNOWN'), repr (arg)))
        stream.write ('>')
        return stream.getvalue ()

    def __repr__ (self):
        """String representation
        """
        return str (self)

# vim: nu ft=python columns=120 :
