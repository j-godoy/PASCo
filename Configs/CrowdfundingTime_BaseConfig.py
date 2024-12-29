fileName = "CrowdfundingT_Base.sol"
contractName = "CrowdfundingT_Base"
functions = [
"Donate();",
"GetFunds();",
"Claim();",
"t();"
]
statePreconditions = [
"(max_block > blockNumber)",
"(max_block < blockNumber && goal <= balance)",
"(blockNumber > max_block && !funded && goal > balance && countBackers > 0)",
"true"
]
functionPreconditions = [
"backers[msg.sender] == 0",
"msg.sender == owner",
"backers[msg.sender] != 0",
"true"
]
functionVariables = ""
tool_output = "Found a counterexample"

statesModeState = []
statesNamesModeState = []
statePreconditionsModeState = []

# epaExtraConditions = "address(this).balance == 0"
txBound = 8