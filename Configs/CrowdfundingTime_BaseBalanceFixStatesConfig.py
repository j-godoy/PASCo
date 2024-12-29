fileName = "CrowdfundingT_BaseBalanceFixStates.sol"
contractName = "CrowdfundingBase"
functions = [
"Donate();",
"GetFunds();",
"Claim();",
"dummy_balanceGTZero();",
# "dummy_balanceIsZero();",
"t();",
]
statePreconditions = [
"(max_block >= blockNumber)",
"(max_block < blockNumber && goal <= balance)",
"(max_block < blockNumber && !funded && goal > balance && countBackers > 0)",
"balance > 0",
# "balance == 0",
"true",
]
functionPreconditions = [
"backers[msg.sender] == 0",
"msg.sender == owner",
"backers[msg.sender] != 0",
"true",
# "true",
"true"
]
functionVariables = ""
tool_output = "Found a counterexample"

statesModeState = [[1,0], [0,2]]
statesNamesModeState = ["B>0", "B=0"]
statePreconditionsModeState = ["balance > 0", "balance == 0"]

# epaExtraConditions = "address(this).balance == 0"
txBound = 8