fileName = "ValidatorAuction.sol"
contractName = "ValidatorAuction"
functions = [
"bid();",
"startAuction();",
"depositBids();",
"closeAuction();",
"addToWhitelist(addressesToWhitelist);",
"withdraw();",
]
statePreconditions = [
"(countWhitelist > 0 && depositLocker.initialized() && !depositLocker.deposited() && (biddersTotal < maximalNumberOfParticipants) && ((time - startTime) < (100 * 365) && time > startTime && time <= (startTime + auctionDurationInDays * 1)) && auctionState == AuctionState.Started)",
"depositLocker.initialized() && auctionState == AuctionState.Deployed",
"auctionState == AuctionState.DepositPending",
"((biddersTotal < maximalNumberOfParticipants) && (time > (startTime + auctionDurationInDays * 1)) && auctionState == AuctionState.Started)",
"auctionState == AuctionState.Deployed",
"countBidders > 0 && (auctionState == AuctionState.Ended || auctionState == AuctionState.Failed)",
]
functionPreconditions = [
"true",
"true",
"true",
"true",
"true",
"true",
]
functionVariables = "address[] memory addressesToWhitelist"
tool_output = "Found a counterexample"

statesModeState = [[1,0,0,0,0], [0,2,0,0,0], [0,0,3,0,0], [0,0,0,4,0], [0,0,0,0,5]]
statesNamesModeState = ["Deployed", "Started", "DepositPending", "Ended", "Failed"]
statePreconditionsModeState = ["auctionState == AuctionState.Deployed", 
"auctionState == AuctionState.Started", 
"auctionState == AuctionState.DepositPending", 
"auctionState == AuctionState.Ended",
"auctionState == AuctionState.Failed",
]
txBound = 8