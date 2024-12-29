fileName = "ValidatorAuction_withdraw.sol"
contractName = "ValidatorAuction_withdraw"
functions = [
"dlocker_init(uint _releaseTimestamp, address _slasher, address _depositorsProxy,uint _time);",
"dlocker_registerDepositor(address _depositor);",
"dlocker_deposit(uint _valuePerDepositor);",

"bid();",
"startAuction();",
"depositBids();",
"closeAuction();",
"addToWhitelist(addressToWhitelist);",

"withdrawA();",
"withdrawOther();",
]
statePreconditions = [
"(!dlocker_initialized && _releaseTimestamp > time)",
"(dlocker_initialized && !dlocker_deposited)",
"(dlocker_initialized && !dlocker_deposited && dlocker_numberOfDepositors > 0)",
    
"(countWhitelist > 0 && dlocker_initialized && !dlocker_deposited && (biddersTotal < maximalNumberOfParticipants) && ((time - startTime) < (100 * 365) && time >= startTime && time <= (startTime + auctionDurationInDays * 1)) && auctionState == AuctionState.Started)",
"dlocker_initialized && auctionState == AuctionState.Deployed",
"auctionState == AuctionState.DepositPending",
"((biddersTotal < maximalNumberOfParticipants) && (time > (startTime + auctionDurationInDays * 1)) && auctionState == AuctionState.Started)",
"auctionState == AuctionState.Deployed",
"((auctionState == AuctionState.Ended || auctionState == AuctionState.Failed) && countBidders > 0 && hasA)",
"((auctionState == AuctionState.Ended || auctionState == AuctionState.Failed) && countBidders > 0 && (!hasA || countBidders > 1))",
]
functionPreconditions = [
"true",
"true",
"true",
    
"true",
"true",
"true",
"true",
"true",
"msg.sender == A && bids[msg.sender] > 0",
"msg.sender != A && bids[msg.sender] > 0", 
]
functionVariables = "address addressToWhitelist, uint _releaseTimestamp, address _slasher, address _depositorsProxy,uint _time, address _depositor, uint _valuePerDepositor"
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
txBound = 8