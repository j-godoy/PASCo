fileName = "RoomThermostat.sol"
contractName = "RoomThermostat"
functions = ["StartThermostat();", "SetTargetTemperature(targetTemperature);", "SetMode(mode);"]
statePreconditions = ["State == StateType.Created", "State == StateType.InUse", "State == StateType.InUse"]
functionPreconditions = ["Installer == msg.sender", "User == msg.sender", "User == msg.sender"]
functionVariables = "int targetTemperature, ModeEnum mode"
tool_output = "Found a counterexample"

statesModeState = [[1,0], [0,2]]
statesNamesModeState = ["Created", "InUse"]
statePreconditionsModeState = ["State == StateType.Created", "State == StateType.InUse"]
txBound = 8