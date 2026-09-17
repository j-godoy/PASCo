fileName = "SimpleAuctionEnded.sol"
contractName = "SimpleAuction"
functions = [
"bid();",
"withdraw();",
"auctionEnd();",
"dummy_isEnded();",
"dummy_is_HB_A();",
"t();"
]
statePreconditions = [
"time <= (auctionStart + biddingTime)",
"pendingReturnsCount > 0",
"!ended && time >= (auctionStart + biddingTime)",
"ended",
"highestBidder == highestBidderA",
"true",
]
functionPreconditions = [
"msg.value > highestBid",
"true",
"true",
"true",
"true",
"true",
]
functionVariables = "address refundee"
tool_output = "Found a counterexample"

statesModeState = [[1,0,0,0,0,0], [0,2,0,0,0,0], [0,0,3,0,0,0], [0,0,0,4,0,0], [0,0,0,0,5,0], [0,0,0,0,0,6]]
statesNamesModeState = ["No bids && !ended", "No bids && ended", "HighestBidder = A && !ended", "HighestBidder = A && ended", "HighestBidder != A && !ended", "HighestBidder != A && ended"]
statePreconditionsModeState = [
"!ended && highestBidder == address(0x0) && pendingReturnsCount == 0", 
"ended && highestBidder == address(0x0) && pendingReturnsCount == 0", 
"!ended && highestBidder != address(0x0) && highestBidder == highestBidderA", 
"ended && highestBidder != address(0x0) && highestBidder == highestBidderA",
"!ended && highestBidder != address(0x0) && highestBidder != highestBidderA",
"ended && highestBidder != address(0x0) && highestBidder != highestBidderA",
]

txBound = 8