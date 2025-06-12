fileName = "EtherstoreReentrancyFixed_lock.sol"
contractName = "EtherStore"
functions = [
"depositFunds();",
"withdrawFunds_Init(_weiToWithdraw);",
"withdrawFunds_End();",
"t(_time);",
"dummy_balanceGTZero();",
# "dummy_balanceIsZero();",
"dummy_balanceAGTZero();"
# "dummy_balanceAIsZero();"
]

statePreconditions = [
"true",
"senders_in_mapping > 0",
"senders_reentrant.length > 0",
"senders_reentrant.length == 0",
"balance > 0",
# "balance == 0",
"balances[A] > 0"
# "balances[A] == 0"
]
functionPreconditions = [
"true",
"true",
"true",
"_time > 0",
"true",
# "true",
# "true",
"true"
]
functionVariables = "uint _weiToWithdraw, address A, uint _time"
# functionVariables = "uint n"
tool_output = "Found a counterexample"

statesModeState = []
statesNamesModeState = []
statePreconditionsModeState = []

# epaExtraConditions = "address(this).balance == 0"
txBound = 8