fileName = "Reentrancy_daoReentrancyFixed_lock.sol"
contractName = "ReentrancyDAO"
functions = [
"deposit();",
"withdrawAll_Init();",
"withdrawAll_End();",
# "t(_time);",
"dummy_balanceGTZero();",
# "dummy_balanceIsZero();",
"dummy_balanceAGTZero();"
# "dummy_balanceAIsZero();"
]

statePreconditions = [
"true",
"senders_in_mapping > 0",
"senders_reentrant.length > 0",
# "true",
"balance > 0",
# "balance == 0",
"credit[A] > 0"
# "credit[A] == 0"
]
functionPreconditions = [
"true",
"true",
"senders_reentrant[senders_reentrant.length-1] == msg.sender",
# "_time > 0",
"true",
# "true",
# "true",
"true"
# "true",
# "true"
]
functionVariables = ""#"address A, uint _amount, address _to"
# functionVariables = "uint n"
tool_output = "Found a counterexample"

statesModeState = []
statesNamesModeState = []
statePreconditionsModeState = []

# epaExtraConditions = "address(this).balance == 0"
txBound = 8