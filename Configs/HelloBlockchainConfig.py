fileName = "HelloBlockchain.sol"
contractName = "HelloBlockchain"
functions = ["SendRequest(requestMessage);", "SendResponse(responseMessage);"]

statePreconditions = ["true", 
"true"]
functionPreconditions = ["msg.sender == Requestor",
"true"]

functionVariables = "string memory requestMessage, string memory responseMessage"
tool_output = "Found a counterexample"

statesModeState = [[1,0], [0,2]]
statesNamesModeState = ["Request", "Respond"]
statePreconditionsModeState = ["State == StateType.Request", "State == StateType.Respond"]
txBound = 8

epaExtraConditions = "true"
statesExtraConditions = ["true", "true"]