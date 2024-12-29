fileName = "Auction_imdea_bepa.sol"
contractName = "Auction"
functions = [
"Bid();",
"Withdraw();",
"AuctionEnd();",
"t();",
]
statePreconditions = [
"(!ended && ((auctionStart + biddingTime) >= blockNumber) || blockNumber <= lastBidBlock)",
"pendingReturnsCount > 0 && (auctionStart + biddingTime < blockNumber) && blockNumber > lastBidBlock",
"(!ended && blockNumber > (auctionStart + biddingTime) && blockNumber > lastBidBlock)",
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
