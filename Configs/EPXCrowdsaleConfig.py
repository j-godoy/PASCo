fileName = "EPXCrowdsale.sol"
contractName = "EPXCrowdsale"
functions = [
"SetupCrowdsale(_fundingStartBlock, _fundingEndBlock);",
"buy();",
# "beneficiaryMultiSigWithdraw(_amount);",
"checkGoalReached();",
"refund();",
"t();"
]
statePreconditions = [
"(!isCrowdSaleSetup && !(beneficiaryWallet != address(0x0)))",
"(tokensRemaining > 0 && (blockNumber <= fundingEndBlock) && (blockNumber >= fundingStartBlock))",
# "(areFundsReleasedToBeneficiary && (amountRaisedInWei >= fundingMinCapInWei))",
"isCrowdSaleSetup",
"((amountRaisedInWei < fundingMinCapInWei) && (isCrowdSaleClosed) && (blockNumber > fundingEndBlock) && (usersEPXfundValueCount != 0))",
"true"
]
functionPreconditions = [
"msg.sender == admin && msg.sender == owner",
"(!(msg.value == 0))",
# "true",
"msg.sender == owner",
"(usersEPXfundValue[msg.sender] > 0)",
"true"
]
functionVariables = "uint256 _amount, uint256 _fundingStartBlock,  uint256 _fundingEndBlock"
tool_output = "Found a counterexample"

# statesModeState = [[1,0,0,0,0,0], [0,2,0,0,0,0], [0,0,3,0,0,0], [0,0,0,4,0,0], [0,0,0,0,5,0], [0,0,0,0,0,6]]
statesModeState = [[1,0,0,0,0,0,0], [0,2,0,0,0,0,0], [0,0,3,0,0,0,0], [0,0,0,4,0,0,0], [0,0,0,0,5,0,0], [0,0,0,0,0,6,0], [0,0,0,0,0,0,7]]
statesNamesModeState = ["Crowdsale is setup", "In progress (Eth < Softcap)", "Successful (EPX >= Hardcap)!", "Unsuccessful (Eth < Softcap)", "Crowdsale deployed to chain", "Successful (Eth >= Softcap)!", "In progress (Eth >= Softcap)!"]
statePreconditionsModeState = [
    "keccak256(abi.encodePacked(CurrentStatus)) == keccak256(abi.encodePacked('Crowdsale is setup'))",
    "keccak256(abi.encodePacked(CurrentStatus)) == keccak256(abi.encodePacked('In progress (Eth < Softcap)'))",
    "keccak256(abi.encodePacked(CurrentStatus)) == keccak256(abi.encodePacked('Successful (EPX >= Hardcap)!'))",
    "keccak256(abi.encodePacked(CurrentStatus)) == keccak256(abi.encodePacked('Unsuccessful (Eth < Softcap)'))",
    "keccak256(abi.encodePacked(CurrentStatus)) == keccak256(abi.encodePacked('Crowdsale deployed to chain'))",
    "keccak256(abi.encodePacked(CurrentStatus)) == keccak256(abi.encodePacked('Successful (Eth >= Softcap)!'))",
    "keccak256(abi.encodePacked(CurrentStatus)) == keccak256(abi.encodePacked('In progress (Eth >= Softcap)!'))",

]
txBound = 8