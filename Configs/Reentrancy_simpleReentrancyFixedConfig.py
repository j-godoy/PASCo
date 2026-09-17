fileName = "Reentrancy_simpleReentrancyFixed.sol"
contractName = "Reentrance"
functions = [
"addToBalance();",
"withdrawBalance_Init();",
"withdrawBalance_End();",
"dummy_balanceGTZero();",
# "dummy_balanceIsZero();",
"dummy_balanceAGTZero();"
# "dummy_balanceAIsZero();"
]
statePreconditions = [
"true",
"senders_in_mapping > 0",
"senders_reentrant.length > 0",
"balance > 0",
# "balance == 0",
"userBalance[A] > 0"
# "userBalance[A] == 0"
]
functionPreconditions = [
"true",
"true",
"senders_reentrant[senders_reentrant.length-1] == msg.sender",
"true",
# "true",
# "true",
"true"
# "true",
# "true"
]
functionVariables = "address A"
# functionVariables = "uint n"
tool_output = "Found a counterexample"

statesModeState = []
statesNamesModeState = []
statePreconditionsModeState = []

# epaExtraConditions = "address(this).balance == 0"
txBound = 8