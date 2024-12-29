fileName = "SimpleMarketplace_fixed.sol"
contractName = "SimpleMarketplace"
functions = ["MakeOffer(offerPrice);", "AcceptOffer();", "Reject();"]
statePreconditions = ["State == StateType.ItemAvailable", "State == StateType.OfferPlaced", "State == StateType.OfferPlaced"]
functionPreconditions = ["offerPrice != 0 && msg.sender != InstanceOwner", "msg.sender == InstanceOwner", "msg.sender == InstanceOwner"]
functionVariables = "int offerPrice"
tool_output = "Found a counterexample"

statesModeState = [[1,0,0], [0,2,0],[0,0,3]]
statesNamesModeState = ["ItemAvailable", "OfferPlaced", "Accepted"]
statePreconditionsModeState = ["State == StateType.ItemAvailable", "State == StateType.OfferPlaced", "State == StateType.Accepted"]
txBound = 8