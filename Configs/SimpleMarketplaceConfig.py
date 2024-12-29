fileName = "SimpleMarketplace.sol"
contractName = "SimpleMarketplace"
functions = ["MakeOffer(offerPrice);", "AcceptOffer();", "Reject();"]
statePreconditions = ["StateEnum == StateType.ItemAvailable", "true", "StateEnum == StateType.OfferPlaced"]
functionPreconditions = ["offerPrice != 0 && msg.sender != InstanceOwner", "msg.sender == InstanceOwner", "msg.sender == InstanceOwner"]
functionVariables = "int offerPrice"
tool_output = "Found a counterexample"

statesModeState = [[1,0,0], [0,2,0],[0,0,3]]
statesNamesModeState = ["ItemAvailable", "OfferPlaced", "Accepted"]
statePreconditionsModeState = ["StateEnum == StateType.ItemAvailable", "StateEnum == StateType.OfferPlaced", "StateEnum == StateType.Accepted"]
txBound = 8