fileName = "CrowdfundingTReentrancy.sol"
contractName = "CrowdfundingR"
functions = [
"Donate();",
"GetFunds();",
"Claim_Init();",
"Claim_End();",
"dummy_balanceGTZero();",
# "dummy_balanceIsZero();",
"t();"
]
statePreconditions = [
"(max_block > blockNumber)",
"(max_block < blockNumber && goal <= balance)",
"(blockNumber > max_block && !funded && goal > balance && countBackers > 0)",
"donadores_reentrada.length > 0",
"balance > 0",
# "balance == 0",
"donadores_reentrada.length == 0"
]
functionPreconditions = [
"backers[msg.sender] == 0",
"msg.sender == owner",
"backers[msg.sender] > 0",
"true",
"true",
# "true",
"true"
]
functionVariables = ""
# functionVariables = "uint n"
tool_output = "Found a counterexample"

statesModeState = []
statesNamesModeState = []
statePreconditionsModeState = []

# epaExtraConditions = "address(this).balance == 0"
txBound = 12