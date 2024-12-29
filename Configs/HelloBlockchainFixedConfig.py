fileName = "HelloBlockchain_fixed.sol"
contractName = "HelloBlockchain"
functions = ["SendRequest(requestMessage);", "SendResponse(responseMessage);"]

statePreconditions = ["State == StateType.Respond", 
"State == StateType.Request"]
functionPreconditions = ["msg.sender == Requestor",
"true"]

functionVariables = "uint requestMessage, uint responseMessage"
tool_output = "Found a counterexample"

statesModeState = [[1,0], [0,2]]
statesNamesModeState = ["Request", "Respond"]
statePreconditionsModeState = ["State == StateType.Request", "State == StateType.Respond"]
txBound = 8

epaExtraConditions = "true"
statesExtraConditions = ["true", "true"]