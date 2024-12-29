fileName = "FrequentFlyerRewardsCalculator.sol"
contractName = "FrequentFlyerRewardsCalculator"
functions = ["AddMiles(miles);"]

statePreconditions = ["true"]
functionPreconditions = ["msg.sender == Flyer"]

functionVariables = "int[] memory miles"
tool_output = "Found a counterexample"

statesModeState = [[1,0], [0,2]]
statesNamesModeState = ["SetFlyerAndReward", "MilesAdded"]
statePreconditionsModeState = ["State == StateType.SetFlyerAndReward", "State == StateType.MilesAdded"]
txBound = 8