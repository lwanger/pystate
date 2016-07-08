"""
This is a simple example of the pystate class. It implements a turnstile. Initially gates are locked,
depositing a coin unlocks the gate, after a customer passes through the arms are locked again. There
are two states defined: STATE_LOCKED and STATE_UNLOCKED. The events are a string. Legal event values
are: 'COIN' and 'CUST_PASSED'.

Len Wanger
7/7/2016
"""

import pystate

# Define the states
STATE_LOCKED = pystate.State('STATE_LOCKED')
STATE_UNLOCKED = pystate.State('STATE_UNLOCKED')


# Define the state handler functions - the first time using the decorato
@pystate.state_handler
def state_locked_handler(fsm, event):
    if event == 'COIN':
        print('Coin deposited, unlocking the gate.')
        fsm.transition_to(STATE_UNLOCKED)
    elif event == 'CUST_PASSED':
        print('Customer trying to pass through a locked gate... rejected!')
    else:
        print('Unrecognized event (%s)' % event)


# define the unlock state handler by hand (i.e. not using the decorator)
def state_unlocked_handler(fsm):
    while True:
        event = yield

        if event == 'CUST_PASSED':
            print('Customer passed through the gate... relocking the gate.')
            fsm.transition_to(STATE_LOCKED)
        elif event == 'COIN':
            print('Another coin deposited... ignoring... gate already unlocked')
        else:
            print('Unrecognized event (%s)' % event)


event_list = ( 'COIN', 'CUST_PASSED', 'COIN', 'COIN', 'CUST_PASSED', 'CUST_PASSED' )
fsm = pystate.FiniteStateMachine()
fsm.add_state(STATE_LOCKED, from_states=(STATE_UNLOCKED), handler_func=state_locked_handler, initial=True)
fsm.add_state(STATE_UNLOCKED, from_states=(STATE_LOCKED), handler_func=state_unlocked_handler)
fsm.start()

try:
    for event in event_list:
        fsm.dispatch_event(event)
except pystate.FsmExit as e:
    print("state machine stopped in an orderly fashion")