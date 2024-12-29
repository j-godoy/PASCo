fileName = "EtherstoreOriginalReentrancy.sol"
contractName = "EtherStore"
functions = [
"depositFunds();",
"withdrawFunds(_weiToWithdraw);",
"t(_time);",
"dummy_balanceGTZero();",
# "dummy_balanceIsZero();",
"dummy_balanceAGTZero();"
# "dummy_balanceAIsZero();"
]

statePreconditions = [
"true",
"senders_in_mapping > 0",
"true",
"balance > 0",
# "balance == 0",
"balances[A] > 0"
# "balances[A] == 0"
]
functionPreconditions = [
"true",
"balances[msg.sender] >= _weiToWithdraw && _weiToWithdraw <= withdrawalLimit && time >= lastWithdrawTime[msg.sender] + 1 weeks",
"_time > 0",
"true",
# "true",
"true"
# "true"
# "true",
# "true"
]
functionVariables = "address A, uint256 _weiToWithdraw, uint _time"
# functionVariables = "uint n"
tool_output = "Found a counterexample"

statesModeState = []
statesNamesModeState = []
statePreconditionsModeState = []

# epaExtraConditions = "address(this).balance == 0"
txBound = 8