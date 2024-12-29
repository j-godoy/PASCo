fileName = "RefundEscrow.sol"
contractName = "RefundEscrow"
functions = [
"deposit(refundee);",
"close();",
"enableRefunds();",
"beneficiaryWithdraw();",
"withdraw(payee);",
"transferPrimary(recipient);"
]
statePreconditions = [
"_state == State.Active",
"_state == State.Active",
"_state == State.Active",
"_state == State.Closed && address(this).balance > 0",
"depositsCount > 0 && _state == State.Refunding",
"true"
]
functionPreconditions = [
"true",
"true",
"true",
"true",
"true",
"recipient != address(0)"
]
functionVariables = "address refundee, address payable payee, address recipient"
tool_output = "Found a counterexample"

statesModeState = [[1,0,0], [0,2,0], [0,0,3]]
statesNamesModeState = ["Active", "Refunding", "Close"]
statePreconditionsModeState = [
"_state == State.Active", 
"_state == State.Refunding", 
"_state == State.Closed", 
]
txBound = 8