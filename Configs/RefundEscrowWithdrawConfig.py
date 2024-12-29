fileName = "RefundEscrowWithdraw.sol"
contractName = "RefundEscrow"
functions = [
"deposit(refundee);",
"close();",
"enableRefunds();",
"beneficiaryWithdraw();",
"withdrawA(payee);",
"withdrawOther(payee);",
"transferPrimary(recipient);"
]
statePreconditions = [
"_state == State.Active",
"_state == State.Active",
"_state == State.Active",
"_state == State.Closed && address(this).balance > 0",
"(depositsCount > 0 && _state == State.Refunding && hasA)",
"(depositsCount > 0 && _state == State.Refunding && (!hasA || depositsCount > 1))",
"true"
]
functionPreconditions = [
"true",
"msg.sender == _primary",
"msg.sender == _primary",
"true",
"withdrawalAllowed(payee) && A == payee && _deposits[payee] > 0",
"withdrawalAllowed(payee) && A != payee && _deposits[payee] > 0",
"msg.sender == _primary"
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