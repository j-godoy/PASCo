fileName = "Crowdfunding_Base_models.sol"
contractName = "CrowdfundingBase"
functions = [
"Donate(n);",
"GetFunds(n);",
"Claim(n);"
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
functionVariables = "uint n"
tool_output = "Found a counterexample"

statesModeState = [[1,0,0,0,0], [0,2,0,0,0], [0,0,3,0,0], [0,0,0,4,0], [0,0,0,0,5]]
statesNamesModeState = ["Vacio sin balance", "Vacio con balance", "Donate", "Funds", "Claim"]
statePreconditionsModeState = [
"(!(max_block > blockNumber) && !(max_block < blockNumber && goal <= balance) && !(blockNumber > max_block && !funded && goal > balance && countBackers > 0) && balance == 0)", 
"(!(max_block > blockNumber) && !(max_block < blockNumber && goal <= balance) && !(blockNumber > max_block && !funded && goal > balance && countBackers > 0) && balance > 0)", 
"(max_block > blockNumber) && !(max_block < blockNumber && goal <= balance) && !(blockNumber > max_block && !funded && goal > balance && countBackers > 0)", 
"!(max_block > blockNumber) && (max_block < blockNumber && goal <= balance) && !(blockNumber > max_block && !funded && goal > balance && countBackers > 0)",
"!(max_block > blockNumber) && !(max_block < blockNumber && goal <= balance) && (blockNumber > max_block && !funded && goal > balance && countBackers > 0)",
]

# epaExtraConditions = "address(this).balance == 0"
txBound = 8
time_out = 7