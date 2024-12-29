fileName = "Crowdfunding_Base.sol"
contractName = "CrowdfundingBase"
functions = [
"Donate();",
"GetFunds();",
"Claim();"
]
statePreconditions = [
"(max_block > blockNumber)",
"(max_block < blockNumber && goal <= balance)",
"(blockNumber > max_block && !funded && goal > balance && countBackers > 0)"
]
functionPreconditions = [
"backers[msg.sender] == 0",
"msg.sender == owner",
"backers[msg.sender] != 0"
]
functionVariables = ""
tool_output = "Found a counterexample"

statesModeState = []
statesNamesModeState = []
statePreconditionsModeState = []

# epaExtraConditions = "address(this).balance == 0"
txBound = 8