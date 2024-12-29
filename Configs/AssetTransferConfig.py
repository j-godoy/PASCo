fileName = "AssetTransfer.sol"
contractName = "AssetTransfer"
functions = [
"Terminate();",
"Modify(price);",
"MakeOffer(inspector, appraiser, offerPrice);",
"AcceptOffer();",
"Reject();",
"Accept();",
"ModifyOffer(offerPrice);",
"RescindOffer();",
"MarkAppraised();",
"MarkInspected();"
]
statePreconditions = [
"true",
"State == StateType.Active",
"State == StateType.Active",
"State == StateType.OfferPlaced",
"(State == StateType.OfferPlaced || State == StateType.PendingInspection || State == StateType.Inspected || State == StateType.Appraised || State == StateType.NotionalAcceptance || State == StateType.BuyerAccepted)",
"(State == StateType.NotionalAcceptance || State == StateType.BuyerAccepted || State == StateType.SellerAccepted)",
"State == StateType.OfferPlaced",
"(State == StateType.OfferPlaced || State == StateType.PendingInspection || State == StateType.Inspected || State == StateType.Appraised || State == StateType.NotionalAcceptance || State == StateType.SellerAccepted)",
"(State == StateType.PendingInspection || State == StateType.Inspected)",
"(State == StateType.PendingInspection || State == StateType.Appraised)"
]
functionPreconditions = [
"InstanceOwner == msg.sender",
"InstanceOwner == msg.sender",
"InstanceOwner != msg.sender && inspector != address(0x0) && appraiser != address(0x0) && offerPrice != 0",
"InstanceOwner == msg.sender",
"InstanceOwner == msg.sender",
"(msg.sender == InstanceBuyer || msg.sender == InstanceOwner) && (msg.sender != InstanceOwner || State == StateType.NotionalAcceptance || State == StateType.BuyerAccepted) && (msg.sender != InstanceBuyer || State == StateType.NotionalAcceptance || State == StateType.SellerAccepted)",
"InstanceBuyer == msg.sender && offerPrice != 0",
"InstanceBuyer == msg.sender",
"InstanceAppraiser == msg.sender",
"InstanceInspector == msg.sender"
]
functionVariables = "uint256 offerPrice, address inspector, address appraiser, string memory description, uint256 price"
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