fileName = "AuctionEnded.sol"
contractName = "Auction"
functions = [
"Bid();",
"Withdraw();",
"AuctionEnd();",
"dummy_isEnded();",
]
statePreconditions = [
"(!ended && (auctionStart + biddingTime) >= blockNumber)",
"pendingReturnsCount > 0",
"(ended && blockNumber > (auctionStart + biddingTime))",
"ended",
]
functionPreconditions = [
"msg.value > highestBid",
"pendingReturns[msg.sender] != 0",
"true",
"true",
]

functionVariables = ""
tool_output = "Found a counterexample"

# statesModeState = [[1,0,0,0,0,0], [0,2,0,0,0,0], [0,0,3,0,0,0], [0,0,0,4,0,0], [0,0,0,0,5,0], [0,0,0,0,0,6]]
statesModeState = [[1,0,0,0,0,0,0,0], [0,2,0,0,0,0,0,0], [0,0,3,0,0,0,0,0], [0,0,0,4,0,0,0,0], [0,0,0,0,5,0,0,0], [0,0,0,0,0,6,0,0], [0,0,0,0,0,0,7,0], [0,0,0,0,0,0,0,8]]
statesNamesModeState = ["Bid && !Withdraw && !AuctionEnd && !ended","Bid && Withdraw && !AuctionEnd && !ended", "!Bid && Withdraw && !AuctionEnd && !ended", "!Bid && !Withdraw && !AuctionEnd && !ended", "!Bid && Withdraw && !AuctionEnd && ended", "!Bid && Withdraw && AuctionEnd && ended", "!Bid && !Withdraw && AuctionEnd && ended", "!Bid && !Withdraw && !AuctionEnd && ended"]
statePreconditionsModeState = [
"(!ended && (auctionStart + biddingTime) >= blockNumber) && !(pendingReturnsCount > 0) && !(ended && blockNumber > (auctionStart + biddingTime)) && !ended", 
"(!ended && (auctionStart + biddingTime) >= blockNumber) && (pendingReturnsCount > 0) && !(ended && blockNumber > (auctionStart + biddingTime)) && !ended", 
"!(!ended && (auctionStart + biddingTime) >= blockNumber) && (pendingReturnsCount > 0) && !(ended && blockNumber > (auctionStart + biddingTime)) && !ended", 
"!(!ended && (auctionStart + biddingTime) >= blockNumber) && !(pendingReturnsCount > 0) && !(ended && blockNumber > (auctionStart + biddingTime)) && !ended", 
"!(!ended && (auctionStart + biddingTime) >= blockNumber) && (pendingReturnsCount > 0) && !(ended && blockNumber > (auctionStart + biddingTime)) && ended",
"!(!ended && (auctionStart + biddingTime) >= blockNumber) && !(pendingReturnsCount > 0) && (ended && blockNumber > (auctionStart + biddingTime)) && ended",
"!(!ended && (auctionStart + biddingTime) >= blockNumber) && !(pendingReturnsCount > 0) && (ended && blockNumber > (auctionStart + biddingTime)) && ended",
"!(!ended && (auctionStart + biddingTime) >= blockNumber) && !(pendingReturnsCount > 0) && !(ended && blockNumber > (auctionStart + biddingTime)) && ended",
]

# epaExtraConditions = "pendingReturnsArray[0] != address(0x0)"
txBound = 8
