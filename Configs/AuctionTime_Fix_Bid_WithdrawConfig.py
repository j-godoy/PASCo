fileName = "AuctionTime_Fix_Bid_Withdraw.sol"
contractName = "Auction"
functions = [
"BidA();",
"BidNotA();",
"WithdrawA();",
"WithdrawNotA();",
"AuctionEnd();",
"t();",
]
statePreconditions = [
"(!ended && (auctionStart + biddingTime) >= blockNumber)",
"(!ended && (auctionStart + biddingTime) >= blockNumber)",
"!ended && pendingReturnsCount > 0 && hasA && blockNumber > (auctionStart + biddingTime)",
"!ended && pendingReturnsCount > 0 && (!hasA || pendingReturnsCount > 1) && blockNumber > (auctionStart + biddingTime)",
"(!ended && blockNumber > (auctionStart + biddingTime))",
"true",
]
functionPreconditions = [
"true",
"true",
"true",
"true",
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