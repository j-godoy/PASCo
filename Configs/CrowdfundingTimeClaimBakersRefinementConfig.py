fileName = "CrowdfundingTClaimBakersRefinement.sol"
contractName = "CrowdfundingR"
functions = [
"Donate();",
"GetFunds();",
"Claim_A();",
"Claim_B();",
"t();",
"dummy_balanceAGTZeroAndNotB();",
"dummy_balanceAGTZeroAndBGTZero();",
"dummy_balanceBGTZeroAndNotA();",
"dummy_balanceAAndBZero();"
]
statePreconditions = [
"(max_block > blockNumber)",
"(max_block < blockNumber && goal <= balance)",
"(blockNumber > max_block && !funded && goal > balance && countBackers > 0 && backers[_A] > 0)",
"(blockNumber > max_block && !funded && goal > balance && countBackers > 0 && backers[_B] > 0)",
"true",
"(backers[_A] > 0 && backers[_B] == 0)",
"(backers[_A] > 0 && backers[_B] > 0)",
"(backers[_B] > 0 && backers[_A] == 0)",
"(backers[_A] == 0 && backers[_B] == 0)"
]
functionPreconditions = [
"backers[msg.sender] == 0",
"msg.sender == owner",
"msg.sender == _A && msg.sender != _B",
"msg.sender == _B && msg.sender != _A",
"true",
"true",
"true",
"true",
"true",
]
functionVariables = "address _A, address _B"
# functionVariables = "uint n"
tool_output = "Found a counterexample"

statesModeState = []
statesNamesModeState = []
statePreconditionsModeState = []

# epaExtraConditions = ""
txBound = 8