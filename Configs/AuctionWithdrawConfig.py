fileName = "AuctionWithdraw.sol"
contractName = "Auction"

functions = [
"Bid();",
"WithdrawA();",
"WithdrawOther();",
"AuctionEnd();",
# "t();",
]
statePreconditions = [
"(!ended && (auctionStart + biddingTime) >= blockNumber)",
"pendingReturnsCount > 0 && hasA",
"pendingReturnsCount > 0 && !hasA",
"(ended && blockNumber > (auctionStart + biddingTime))",
# "true",
]
functionPreconditions = [
"msg.value > highestBid",
"pendingReturns[msg.sender] != 0 && msg.sender == A",
"pendingReturns[msg.sender] != 0 && msg.sender != A",
"true",
# "true",
]
functionVariables = ""
tool_output = "Found a counterexample"

statesModeState = [[1,0,0,0,0,0,0,0,0,0], [0,2,0,0,0,0,0,0,0,0], [0,0,3,0,0,0,0,0,0,0], [0,0,0,4,0,0,0,0,0,0], [0,0,0,0,5,0,0,0,0,0], [0,0,0,0,0,6,0,0,0,0], [0,0,0,0,0,0,7,0,0,0], [0,0,0,0,0,0,0,8,0,0], [0,0,0,0,0,0,0,0,9,0], [0,0,0,0,0,0,0,0,0,10]]
statesNamesModeState = ["Active", "OfferPlaced", "PendingInspection", "Inspected", "Appraised", "NotionalAcceptance", "BuyerAccepted", "SellerAccepted", "Accepted", "Terminated"]
statePreconditionsModeState = ["State == StateType.Active", 
"State == StateType.OfferPlaced", 
"State == StateType.PendingInspection", 
"State == StateType.Inspected",
"State == StateType.Appraised",
"State == StateType.NotionalAcceptance",
"State == StateType.BuyerAccepted",
"State == StateType.SellerAccepted",
"State == StateType.Accepted",
"State == StateType.Terminated"]

# epaExtraConditions = "pendingReturnsArray[0] != address(0x0)"
txBound = 8
