fileName = "EtherbankOriginalReentrancy.sol"
contractName = "EtherBank"
functions = [
"addToBalance();",
"withdrawBalance();",
"dummy_balanceGTZero();",
# "dummy_balanceIsZero();",
"dummy_balanceAGTZero();",
# "dummy_balanceAIsZero();"
]
statePreconditions = [
"true",
"true",
"balance > 0",
# "balance == 0",
"userBalances[A] > 0"
# "userBalances[A] == 0"
]
functionPreconditions = [
"true",
"true",
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