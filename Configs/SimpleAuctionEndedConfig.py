fileName = "SimpleAuctionEnded.sol"
contractName = "SimpleAuction"
functions = [
"bid();",
"withdraw();",
"auctionEnd();",
"dummy_isEnded();",
"t();"
]
statePreconditions = [
"time <= (auctionStart + biddingTime)",
"pendingReturnsCount > 0",
"!ended && time >= (auctionStart + biddingTime)",
"ended",
"true",
]
functionPreconditions = [
"msg.value > highestBid",
"true",
"true",
"true",
"true",
]
functionVariables = "address refundee"
tool_output = "Found a counterexample"

statesModeState = []
statesNamesModeState = []
statePreconditionsModeState = []
txBound = 8