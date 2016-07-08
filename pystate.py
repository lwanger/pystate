"""
FiniteStateMachine - A finite state machine class using coroutines

    FiniteStateMachine is a class representing a finite state machine. Each state is represented by an instance of the
    State class. Each state also has a state handler function defined for it. The handler function is a co-routine that
    excepts an event and performs an action based on it.

    To define the state machine:

    1) define the states (e.g. STATE_A = State('STATE_A'))
    2) define the state handler functions. See below for the structure of a state handling function.
    3) create an instance of the state machine (e.g. fsm = Fsm())
    4) add states to the state machine, including exactly one state marked as the initial state. Each state also takes
        a sequence of states that it can be transitioned from (from_states).
    5) call the start function on the FSM (e.g. fsm.start())

    For each event you will need to call the dispatch_event function (e.g. fsm.dispatch_event()) to route the event
    to the co-routine. An event can be anything you want (e.g. a tuple with event_id and arguments). The main loops
    generally looks like:

    try:
        while True:
            event = get_next_event()
            fsm.dispatch_event(event)
    except ExpectedExit as e:
        pass

    The basic structure of a state handler is:

    def state_handler_<state name>(fsm):
        # Enter the main loop for the co-routine
        while True:
            event = yield

            if event == 'EVENT_1':
                # Transition to another state
                fsm.transition_to(STATE_X)
            elif event == 'EVENT_2':
                # Do some processing but stay in this state
                print('Got EVENT_2')
            elif event == 'TERMINATING_EVENT':
                raise FsmExit
            else:
                print('Unrecognized event (%s)' % event)

    A simple example of this is shown in the turnstile_test.py test case.

    For convenience this can be wrapped with a @state_handler decorator. The decorator takes care of the co-routine
    boiler plate and hands the handler function an fsm and event. This would look like:

    @pystate.state_handler
    def state_locked_handler(event, fsm):
        if event == 'EVENT_1':
            # Transition to another state
            fsm.transition_to(STATE_X)
        elif event == 'EVENT_2':
            # Do some processing but stay in this state
            print('Got EVENT_2')
        elif event == 'TERMINATING_EVENT':
            raise FsmExit
        else:
            print('Unrecognized event (%s)' % event)

    There are two ways to handle a state that needs to keep persistant data. You can create a callable clas (i.e. define
    the __call__ dunder method to call as the state handler.) This allows you to use the state_handler decorator around
    the __call__ method. Alternatively, you can set the state data above the while loop if you define the co-routine by
    hand, however, this precludes using the decorator. See the callable_test.py test case for an example.

Author: Len Wanger
Last Updated: 7/7/2016

The MIT License (MIT)
Copyright (c) 2016 Len Wanger

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Note: Substantial code was adapted from Christian Maugg's pystatemachine code
Copyright (c) 2015 Christian Maugg
(https://raw.githubusercontent.com/cmaugg/pystatemachine/master/pystatemachine.py)
"""

from functools import wraps

# Define custom exceptions for the pystate class.
class InvalidStateTransition(Exception): pass   # Passed when trying to transition to a state that is not allowed
class FsmExit(Exception): pass  # Raised when the state machine exits gracefully.


class State(object):
    """
    Base class for pystate states. Each state has a name, handler function, and list of states it can be entered from.
    """
    def __init__(self, name):
        self.name = name
        self.handler_func = self.handler_generator = None
        self.from_states = set([])

    def __repr__(self):
        return '<State: %s, handler_func=%s>' % (self.name, self.handler_func.func_name)


class FiniteStateMachine(object):
    """ Finite State Machine Base Class. The FSM has a list of states, an initial state, and a
     current state. States can be added to the list of states using the add_state method. The current
     state is changed using the transition_to method. Events are handled using the dispatch_event method.
     This will pass the event to the handler function on the current state.
    """
    def __init__(self):
        self.initial_state = self.current_state = None
        self.states = {}

    def __repr__(self):
        return '<Fsm: id=0x{2:X}, initial_state=%s, current_state=%s>'.format(self.initial_state.name, self.current_state.name, id(self))

    def add_state(self, state, from_states, handler_func=None, initial=False):
        """ Add a state to the finite state machine
        :param from_states - a sequence containing the states this state can be entered (transitioned) from.
        :param initial - True if this is the initial state for the state machine. Note: exactly one state is initial.
        """
        from_states_tuple = (from_states, ) if isinstance(from_states, State) else tuple(from_states or [])

        if not initial and not len(from_states_tuple) >= 1: # can only have 0 from_states if it's the initial state
            raise ValueError()
        if not all(isinstance(state, State) for state in from_states_tuple):
            raise TypeError()
        if state.name in self.states:
            raise KeyError("State already exists in FSM.")
        if initial and self.initial_state: # An initial state was already declared
            raise RuntimeError("State machine cannot have multiple initial states (%s, %s)" %
                               (self.initial_state.name, state.name))

        self.states[state.name] = state
        state.from_states = from_states_tuple
        state.handler_func = handler_func

        if initial:
            self.initial_state = self.current_state = state

    def transition_to(self, to_state):
        """ Transition to the to_state (i.e. set current_state to to_state). """
        if not isinstance(to_state, State):
            raise TypeError()
        if self.current_state not in to_state.from_states:
            raise InvalidStateTransition("Cannot transition from state %s to state %s" % (self.current_state.name, to_state.name))

        self.current_state = to_state


    def start(self):
        """ The the state machine running - creates and starts generators for the state handler co-routines. """
        if self.initial_state == None: # Check that an initial state was declared
            raise RuntimeError("No initial state set on the state machine.")

        self.current_state = self.initial_state

        for state in self.states.values():
            state.generator = state.handler_func(self)
            next(state.generator) # start up the co-routine

    def dispatch_event(self, event):
        """ call the state handler for the current state. Each state has a co-routine as a hander function. Dispatch
         calls the handler function on the current state, and passes it an event. The event can be anything you want,
         and it is up to the hander function to decode it.
        """
        self.states[self.current_state.name].generator.send(event)


# Define the state handler decorator (creates theco-routine boilerplate to handle a state.)
def state_handler(f):
    @wraps(f)
    def func_wrapper(*args, **kwargs):
        while True:
            event = yield
            f(*args, event=event, **kwargs)
    return func_wrapper


if __name__ == '__main__':
    # define a simple three state state machine. A goes to B goes to C goes to A.
    STATE_A = State('STATE_A')
    STATE_B = State('STATE_B')
    STATE_C = State('STATE_C')

    @state_handler
    def state_a_handler(fsm, event):
        if event == 'GOTO_B':
            print('Transitioning to state B.')
            fsm.transition_to(STATE_B)
        else:
            raise ValueError('State %s - Unrecognized event (%s)' % (fsm.current_state.name, event))


    @state_handler
    def state_b_handler(fsm, event):
        if event == 'GOTO_C':
            print('Transitioning to state C.')
            fsm.transition_to(STATE_C)
        elif event == 'GOTO_A':
            print('Transitioning to state A (should raise an InvalidStateTransition.)')
            fsm.transition_to(STATE_A)
        else:
            raise ValueError('State %s - Unrecognized event (%s)' % (fsm.current_state.name, event))


    @state_handler
    def state_c_handler(fsm, event):
        if event == 'GOTO_A':
            print('Transitioning to state A.')
            fsm.transition_to(STATE_A)
        elif event == 'END':
            raise FsmExit
        else:
            raise ValueError('State %s - Unrecognized event (%s)'  % (fsm.current_state.name, event))

    def run_event_list(fsm, event_list):
        fsm.start()

        try:
            for event in event_list:
                fsm.dispatch_event(event)
        except ValueError as e:
            print("ValueError exception - %s" % str(e))
        except InvalidStateTransition as e:
            print("InvalidStateTransition exception - %s" % str(e))
        except FsmExit as e:
            print("state machine stopped in an orderly fashion")

    event_list_1 = ('event_list_1 (no errors)', ('GOTO_B', 'GOTO_C', 'GOTO_A', 'GOTO_B', 'GOTO_C', 'END'))
    event_list_2 = ('event_list_2 (raise InvalidStateTransition exception)', ('GOTO_B', 'GOTO_C', 'GOTO_A', 'GOTO_B', 'GOTO_A', 'GOTO_C', 'END'))
    event_list_3 = ('event_list_3 (raise ValueError exception)', ('GOTO_B', 'GOTO_C', 'GOTO_A', 'END', 'GOTO_C', 'END'))

    fsm = FiniteStateMachine()
    fsm.add_state(STATE_A, from_states=(STATE_C), handler_func=state_a_handler, initial=True)
    fsm.add_state(STATE_B, from_states=(STATE_A), handler_func=state_b_handler)
    fsm.add_state(STATE_C, from_states=(STATE_B), handler_func=state_c_handler)

    for event_list in (event_list_1, event_list_2, event_list_3):
        print('\nTesting event_list %s' % event_list[0])
        run_event_list(fsm, event_list[1])
