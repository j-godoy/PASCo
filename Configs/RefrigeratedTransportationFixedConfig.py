fileName = "RefrigeratedTransportation_fixed.sol"
contractName = "RefrigeratedTransportation"
functions = ["IngestTelemetry(humidity, temperature, timestamp);", "TransferResponsibility(newCounterparty);", "Complete();"]
statePreconditions = [
    "(State != StateType.Completed && State != StateType.OutOfCompliance)", 
    "(State != StateType.Completed && State != StateType.OutOfCompliance)", 
    "(State != StateType.Completed && State != StateType.OutOfCompliance && State != StateType.Created)"]
functionPreconditions = ["Device == msg.sender", "InitiatingCounterparty == msg.sender && Counterparty == msg.sender && newCounterparty != Device", "Owner == msg.sender && SupplyChainOwner == msg.sender"]
functionVariables = "int humidity, int temperature, int timestamp, address newCounterparty"
tool_output = "Found a counterexample"

statesModeState = [[1,0,0,0], [0,2,0,0], [0,0,3,0], [0,0,0,4]]
statesNamesModeState = [ "Created", "InTransit", "Completed", "OutOfCompliance"]
statePreconditionsModeState = ["State == StateType.Created", "State == StateType.InTransit", "State == StateType.Completed", "State == StateType.OutOfCompliance"]
txBound = 8

# Nuevas:
# mustN = 1
# counterexampleVariables = [
#     {
#         "state_var": "uint8(State)",
#         "trace_param": "state",
#         "solidity_type": "uint8",
#     },
#     {
#         "state_var": "Owner",
#         "trace_param": "owner",
#         "solidity_type": "address",
#     },
#     {
#         "state_var": "InitiatingCounterparty",
#         "trace_param": "initCounterparty",
#         "solidity_type": "address",
#     },
#     {
#         "state_var": "Counterparty",
#         "trace_param": "counterparty",
#         "solidity_type": "address",
#     },
#     {
#         "state_var": "Device",
#         "trace_param": "device",
#         "solidity_type": "address",
#     },
#     {
#         "state_var": "SupplyChainOwner",
#         "trace_param": "supplyChainOwner",
#         "solidity_type": "address",
#     },
#     {
#         "state_var": "uint8(ComplianceDetail)",
#         "trace_param": "complianceDetail",
#         "solidity_type": "uint8",
#     },
#     {
#         "state_var": "ComplianceStatus",
#         "trace_param": "complianceStatus",
#         "solidity_type": "bool",
#     },
# ]