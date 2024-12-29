fileName = "CrowdfundingTDonateRefinement.sol"
contractName = "CrowdfundingR"
functions = [
"Donate_A();",
"Donate_B();",
"GetFunds();",
"Claim();",
"t();"
]
statePreconditions = [
"(max_block > blockNumber) && backers[_A] == 0",
"(max_block > blockNumber) && backers[_B] == 0",
"(max_block < blockNumber && goal <= balance)",
"(blockNumber > max_block && !funded && goal > balance && countBackers > 0)",
"true"
]
functionPreconditions = [
"backers[msg.sender] == 0 && msg.sender == _A",
"backers[msg.sender] == 0 && msg.sender == _B",
"msg.sender == owner",
"backers[msg.sender] > 0",
"true"
]
functionVariables = "address _A, address _B"
# functionVariables = "uint n"
tool_output = "Found a counterexample"

statesModeState = []
statesNamesModeState = []
statePreconditionsModeState = []

# epaExtraConditions = "address(this).balance == 0"
txBound = 8