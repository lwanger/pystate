"""
This is an example of the pystate class where the states want to retain some state data. To do so it creates
callable classes. The state machine itself is very simple, it has two states, A and B. It has the following
events:

'FLIP_FOO' - toggle the value of foo between True and False
'GOTO_B' - go from state A to state B
'INCR_BAR' - increment the value of bar by 1
'GOTO_A' - fp tp state B from state A
'END' - end the state machine

There are two ways to handle a state that needs to keep persistant data. You can create a callable clas (i.e. define
the __call__ dunder method to call as the state handler.) This allows you to use the state_handler decorator around
 the __call__ method. Alternatively, you can set the state data above the while loop if you define the co-routine by
 hand, however, this precludes using the decorator.

Len Wanger
7/7/2016
"""

import pystate


# Define the states
STATE_A = pystate.State('STATE_A')
STATE_B = pystate.State('STATE_B')

# Define state handler (define as callable classes so can retain state data)
class StateA(object):
    def __init__(self):
        self.foo = False

    # define using the decorator
    @pystate.state_handler
    def __call__(self, fsm, event):
        if event == 'GOTO_B':
            fsm.transition_to(STATE_B)
        elif event == 'FLIP_FOO':
            self.foo = False if self.foo else True
            print('foo=%s' % self.foo)
        elif event == 'END':
            raise pystate.FsmExit
        else:
            print('Unrecognized event (%s)' % event)


# define without using the decorator. If not using the decorator, you can define some state above the while loop.
#  doing it this way you can define the handler as a function instead of a callable function.
def state_b_handler(fsm):
    bar = 0

    while True:
        event = yield

        if event == 'GOTO_A':
            fsm.transition_to(STATE_A)
        elif event == 'INCR_BAR':
            bar += 1
            print('bar=%s' % bar)
        else:
            print('Unrecognized event (%s)' % event)


# The code
event_list = ( 'FLIP_FOO', 'GOTO_B', 'INCR_BAR', 'GOTO_A', 'FLIP_FOO', 'FLIP_FOO', 'GOTO_B', 'INCR_BAR', 'GOTO_A', 'END')
fsm = pystate.FiniteStateMachine()
state_a = StateA()
fsm.add_state(STATE_A, (STATE_B), state_a, initial=True)
fsm.add_state(STATE_B, (STATE_A), state_b_handler)
fsm.start()

try:
    for event in event_list:
        fsm.dispatch_event(event)
except pystate.FsmExit as e:
    print("state machine stopped in an orderly fashion")