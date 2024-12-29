fileName = "RefrigeratedTransportation.sol"
contractName = "RefrigeratedTransportation"
functions = ["IngestTelemetry(humidity, temperature, timestamp);", "TransferResponsibility(newCounterparty);", "Complete();"]
statePreconditions = ["(State != StateType.Completed && State != StateType.OutOfCompliance) ", "(State != StateType.Completed && State != StateType.OutOfCompliance)", "(State != StateType.Completed && State != StateType.OutOfCompliance)"]
functionPreconditions = ["Device == msg.sender", "InitiatingCounterparty == msg.sender && Counterparty == msg.sender && newCounterparty != Device", "Owner == msg.sender && SupplyChainOwner == msg.sender"]
functionVariables = "int humidity, int temperature, int timestamp, address newCounterparty"
tool_output = "Found a counterexample"

statesModeState = [[1,0,0,0], [0,2,0,0], [0,0,3,0], [0,0,0,4]]
statesNamesModeState = [ "Created", "InTransit", "Completed", "OutOfCompliance"]
statePreconditionsModeState = ["State == StateType.Created", "State == StateType.InTransit", "State == StateType.Completed", "State == StateType.OutOfCompliance"]
txBound = 8