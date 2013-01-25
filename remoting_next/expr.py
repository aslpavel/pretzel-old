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
           'ReturnExpr', 'RaiseExpr', 'AwaitExpr', 'CmpExpr', 'IfExpr', 'WhileExpr',
           'Code',)

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
        return 'arg_{}'.format (self.index)

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
    """Raise expression
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

class CmpExpr (Expr):
    """Compare expression
    """
    __slots__ = ('op', 'first', 'second',)

    def __init__ (self, op, first, second):
        self.op = op
        self.first = first
        self.second = second

    def Compile (self, code):
        compile (self.first, code)
        compile (self.second, code)
        code.Emit (OP_COMPARE, self.op)

    def String (self):
        return '{} {} {}'.format (self.first, self.op, self.second)

class IfExpr (Expr):
    """If expression
    """
    __slots__ = ('cond', 'true', 'false',)

    def __init__ (self, cond, true, false = None):
        self.cond = cond
        self.true = true
        self.false = false

    def Compile (self, code):
        # condition
        compile (self.cond, code)
        if_pos = len (code)
        code.Emit (OP_JMP_IF)

        # true
        compile (self.false, code)
        else_pos = len (code)
        code.Emit (OP_JMP)

        # false
        compile (self.true, code)

        # update jumps
        code.Emit (OP_JMP_IF, else_pos + 1, if_pos)
        code.Emit (OP_JMP, len (code), else_pos)

    def String (self):
        return '{} if {} else {}'.format (self.true, self.cond, self.false)

class WhileExpr (Expr):
    """While expression
    """
    __slots__ = ('cond', 'body',)

    def __init__ (self, cond, body):
        self.cond = cond
        self.body = body

    def Compile (self, code):
        # condition
        cond_pos = len (code)
        compile (self.cond, code)
        if_pos = len (code)
        code.Emit (OP_JMP_IF_NOT)

        # body
        compile (self.body, code)
        code.Emit (OP_POP)
        code.Emit (OP_JMP, cond_pos)

        # update jumps
        code.Emit (OP_JMP_IF_NOT, len (code), if_pos)

    def String (self):
        return 'while {}: {}'.format (self.cond, self.body)

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
OP_LDARG      = next (OP)
OP_LDCONST    = next (OP)
OP_CALL       = next (OP)
OP_GETATTR    = next (OP)
OP_SETATTR    = next (OP)
OP_GETITEM    = next (OP)
OP_SETITEM    = next (OP)
OP_RETURN     = next (OP)
OP_RAISE      = next (OP)
OP_AWAIT      = next (OP)
OP_JMP        = next (OP)
OP_JMP_IF     = next (OP)
OP_JMP_IF_NOT = next (OP)
OP_COMPARE    = next (OP)
OP_POP        = next (OP)
del OP

opToName = {
    OP_LDARG      : 'LOAD_ARG',
    OP_LDCONST    : 'LOAD_CONST',
    OP_CALL       : 'CALL',
    OP_GETATTR    : 'ATTR_GET',
    OP_SETATTR    : 'ATTR_SET',
    OP_GETITEM    : 'ITEM_GET',
    OP_SETITEM    : 'ITEM_SET',
    OP_RETURN     : 'RETURN',
    OP_RAISE      : 'RAISE',
    OP_AWAIT      : 'AWAIT',
    OP_JMP        : 'JMP',
    OP_JMP_IF     : 'JMP_IF',
    OP_JMP_IF_NOT : 'JMP_IF_NOT',
    OP_COMPARE    : 'COMPARE',
    OP_POP        : 'POP'
}

#------------------------------------------------------------------------------#
# Code                                                                         #
#------------------------------------------------------------------------------#
class Code (list):
    """Code object
    """
    #--------------------------------------------------------------------------#
    # Factory                                                                  #
    #--------------------------------------------------------------------------#
    @classmethod
    def FromExpr (cls, expr):
        code = cls ()
        expr.Compile (code)
        return code

    #--------------------------------------------------------------------------#
    # Emit                                                                     #
    #--------------------------------------------------------------------------#
    def Emit (self, op, arg = None, pos = None):
        """Emit opcode
        """
        if pos is None:
            self.append ((op, arg))
        else:
            self [pos] = (op, arg)

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
                if a_count:
                    if kw_count: stack.append (fn (*a, **kw))
                    else:        stack.append (fn (*a))
                else:
                    if kw_count: stack.append (fn (**kw))
                    else:        stack.append (fn ())

            elif op == OP_RETURN:
                break

            elif op == OP_RAISE:
                raise stack.pop ()

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

            elif op == OP_JMP:
                pos = arg

            elif op == OP_JMP_IF:
                if stack.pop ():
                    pos = arg

            elif op == OP_JMP_IF_NOT:
                if not stack.pop ():
                    pos = arg

            elif op == OP_COMPARE:
                second, first = stack.pop (), stack.pop ()
                stack.append (first < second      if arg == '<' else
                              first <= second     if arg == '<=' else
                              first == second     if arg == '==' else
                              first != second     if arg == '!=' else
                              first > second      if arg == '>' else
                              first >= second     if arg == '>=' else
                              first in second     if arg == 'in' else
                              first not in second if arg == 'not in' else
                              first is second     if arg == 'is' else
                              first is not second if arg == 'is not' else
                              raiseError (ValueError ('Unknown compare operation: {}'.format (arg))))

            elif op == OP_POP:
                stack.pop ()

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
        for pos, op_arg in enumerate (self):
            op, arg = op_arg
            stream.write ('\n  {:>02} {:<11}{}'.format (pos, opToName.get (op, 'UNKNOWN'), repr (arg)))
        stream.write ('>')
        return stream.getvalue ()

    def __repr__ (self):
        """String representation
        """
        return str (self)

#------------------------------------------------------------------------------#
# Helpers                                                                      #
#------------------------------------------------------------------------------#
def raiseError (error):
    """Raise error
    """
    raise error
# vim: nu ft=python columns=120 :
