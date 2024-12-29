fileName = "EscrowVault.sol"
contractName = "EscrowVault"
functions = [
"deposit(investor);",
"setGoalReached();",
"withdraw(_amount);",
"withdrawAll();",
"close();",
"enableRefunds();",
"refund(investor);",
"transferOwnership(newOwner);"
]
statePreconditions = [
"(state == State.Active || state == State.GoalReached)",
"state == State.Active",
"state == State.GoalReached",
"state == State.GoalReached",
"state == State.GoalReached",
"state == State.Active",
"state == State.Refunding",
"true"
]
functionPreconditions = [
"true",
"true",
"msg.sender == superOwner && _amount <= address(this).balance &&  _amount > 0",
"true",
"true",
"true",
"true",
"newOwner != address(0)"
]
functionVariables = "uint256 _amount, address payable investor, address newOwner"
tool_output = "Found a counterexample"

statesModeState = [[1,0,0,0], [0,2,0,0], [0,0,3,0], [0,0,0,4]]
statesNamesModeState = ["Active", "Refunding", "Goal Reached", "Closed"]
statePreconditionsModeState = ["state == State.Active", 
"state == State.Refunding", 
"state == State.GoalReached", 
"state == State.Closed",
]
txBound = 8