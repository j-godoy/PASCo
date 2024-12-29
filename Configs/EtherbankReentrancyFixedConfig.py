fileName = "EtherbankReentrancyFixed.sol"
contractName = "EtherBank"
functions = [
"addToBalance();",
"withdrawBalance_Init();",
"withdrawBalance_End();",
"dummy_balanceGTZero();",
"dummy_balanceIsZero();"
]
statePreconditions = [
"true",
"balance > 0",
"senders_reentrant.length > 0",
"balance > 0",
"balance == 0"
]
functionPreconditions = [
"true",
"true",
"true",
"true",
"true"
]
functionVariables = ""
# functionVariables = "uint n"
tool_output = "Found a counterexample"

statesModeState = []
statesNamesModeState = []
statePreconditionsModeState = []

# epaExtraConditions = "address(this).balance == 0"
txBound = 8