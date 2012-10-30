# -*- coding: utf-8 -*-

__all__ = ('StateMachine',)
#------------------------------------------------------------------------------#
# State Machine                                                                #
#------------------------------------------------------------------------------#
class StateMachineError (Exception):
    """State machine specific errors
    """

class StateMachine (object):
    """State machine graph
    """
    __slots__ = ('states', 'state', 'trans')

    def __init__ (self, state, states, transitions):
        """Initialize state machine graph

        Requires initial state, all states and available transitions
        """

        self.states = {st: {} for st in states}
        trans = self.states.get (state)
        if trans is None:
            raise StateMachineError ('Invalid initial state: {}'.format (state))

        for from_state, to_state, handler in transitions:
            from_trans = self.states.get (from_state)
            if from_trans is None:
                raise StateMachineError ('Unknown state: {}'.format (from_state))

            to_trans =  self.states.get (to_state)
            if to_trans is None:
                raise StateMachineError ('Unknown state: {}'.format (to_state))

            from_trans [to_state] = (to_trans, handler)

        self.state = state
        self.trans = trans

    def __call__   (self, state, *args): return self.Transition (state, *args)
    def Transition (self, state, *args):
        """Make transition to specified state
        """
        cur_state = self.state
        if cur_state == state:
            return

        trans, handler = self.trans.get (state, (None, None))
        if trans is None:
            raise StateMachineError ('Invalid transition: {} -> {}'.format (cur_state, state))

        self.trans = trans
        self.state = state

        return None if handler is None else handler (cur_state, state, *args)

    @property
    def State (self):
        """Current state
        """
        return self.state

    @property
    def Transitions (self):
        """Available transitions
        """
        return tuple (self.trans.values ())

    def __repr__ (self):
        return '<StateMachine: {}>'.format (self.state)

# vim: nu ft=python columns=120 :