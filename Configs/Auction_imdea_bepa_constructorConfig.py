fileName = "Auction_imdea_bepa_constructor.sol"
contractName = "Auction"
functions = [
"constructor_f(_auctionStart,_biddingTime,_beneficiary);",
"Bid();",
"Withdraw();",
"AuctionEnd();",
"t();",
]
statePreconditions = [
"!initialized",
"initialized && (!ended && ((auctionStart + biddingTime) >= blockNumber) || blockNumber <= lastBidBlock)",
"initialized && pendingReturnsCount > 0 && (auctionStart + biddingTime < blockNumber) && blockNumber > lastBidBlock",
"(initialized && !ended && blockNumber > (auctionStart + biddingTime) && blockNumber > lastBidBlock)",
"initialized && true",
]
functionPreconditions = [
"true",
"msg.value > highestBid",
"pendingReturns[msg.sender] != 0",
"true",
"true",
]
functionVariables = "uint _auctionStart, uint _biddingTime, address payable _beneficiary"
tool_output = "Found a counterexample"

statesModeState = []
statesNamesModeState = []
statePreconditionsModeState = []

# epaExtraConditions = "pendingReturnsArray[0] != address(0x0)"
txBound = 8
