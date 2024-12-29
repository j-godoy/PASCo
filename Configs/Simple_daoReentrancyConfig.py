fileName = "Simple_daoReentrancy.sol"
contractName = "SimpleDAO"
functions = [
"donate(to);",
"withdraw_Init(amount);",
"withdraw_End();",
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
"credit[A] > 0"
# "credit[A] == 0"
]
functionPreconditions = [
"true",
"true",
"true",
"true",
# "true",
"true"
# "true"
# "true",
# "true"
]
functionVariables = "address to, uint amount, address A"
# functionVariables = "uint n"
tool_output = "Found a counterexample"

statesModeState = []
statesNamesModeState = []
statePreconditionsModeState = []

# epaExtraConditions = "address(this).balance == 0"
txBound = 8