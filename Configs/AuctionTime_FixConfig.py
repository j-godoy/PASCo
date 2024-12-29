fileName = "Auction.sol"
contractName = "Auction"
functions = [
"Bid();",
"Withdraw();",
"AuctionEnd();",
"t();",
]
statePreconditions = [
"(!ended && (auctionStart + biddingTime) >= blockNumber)",
"pendingReturnsCount > 0",
"(!ended && blockNumber > (auctionStart + biddingTime))",
"true",
]
functionPreconditions = [
"msg.value > highestBid",
"pendingReturns[msg.sender] != 0",
"true",
"true",
]
functionVariables = ""
tool_output = "Found a counterexample"

statesModeState = []
statesNamesModeState = []
statePreconditionsModeState = []

# epaExtraConditions = "pendingReturnsArray[0] != address(0x0)"
txBound = 8
