fileName = "CounterExampleFiltering.sol"
contractName = "CounterExampleFiltering"
txBound = 8
time_out = 600

functionVariables = ""
functions = ["f();",]
functionPreconditions = ["x > 10 && x < 13",]
statePreconditions = ["true",]

epaExtraConditions = "true"
statesNamesModeState = ["STATE_A","STATE_B","STATE_P",]
statePreconditionsModeState = ["state == STATE_A","state == STATE_B","state == STATE_P",]
statesModeState = [[1],[2],[3],]
statesExtraConditions = ["true","true","true",]

# N: cantidad de contraejemplos analizados
mustN = 10

# Al agregar esto, evalua contraejemlplos.
# counterexampleVariables = [
#     {
#         "state_var": "x",
#         "trace_param": "x",
#         "solidity_type": "int",
#     },
#     {
#         "state_var": "state",
#         "trace_param": "s",
#         "solidity_type": "uint8",
#     },
#     # {
#     #     "state_var": "owner",
#     #     "trace_param": "owner",
#     #     "solidity_type": "address",
#     # },
# ]