# PASCo
Predicate Abstraction for Smart Contracts tool

This tool generates a predicate abstraction in dot format from Solidity source code.

## Table of Contents
- [Installation](#installation)
- [Usage](#usage)
- [Arguments](#arguments)
- [Examples](#examples)
- [Features](#features)

---

## Installation

### Clone the Repository
Clone this repository to your local machine:

```bash
git clone https://github.com/yourusername/PASCo.git
cd PASCo
```


### Prerequisites
- Python 3.8 or later
- VeriSol: You can download this from: https://github.com/microsoft/verisol/blob/master/INSTALL.md
- Add VeriSol to path (home/user/.dot/...)
- pip install graphviz
- pip install numpy
- pip install psutil
- pip install tabulate
- pip install pydot
- run PASCo.py with some basic example. If it works fine, then:
    - remove VeriSol (option 1): dotnet remove verisol
	- option 2 (if option 1 does not work): dotnet tool uninstall -g verisol
    - install a fork version of Verisol running:
        - git clone https://github.com/j-godoy/verisol.git
        - cd verisol/
        - dotnet build Sources\VeriSol.sln
        - dotnet tool install VeriSol --version 0.1.5-alpha --global --add-source path/to/repo/verisol/nupkg/

Command example to run Verisol for a Solidity file:
- Verisol HelloBlockchain.sol HelloBlockchain /txBound:8 /noPrf


### Usage
Run the tool using the following command:

```bash
python pasco.py --file <ConfigFile> --mode <Mode> [options]
```

Here:
<ConfigFile> specifies the configuration file for the smart contract.
<Mode> defines the mode(s) of execution.

It requires that the corresponding Solidity contract is in the /Contract folder and its config file in the /Config folder.

## Example of Configuration File

Each `.sol` file (located in the `Contracts` folder) must be accompanied by a corresponding `[contractNameFile]Config.py` file. This configuration file specifies various parameters for setting up the abstraction process:

- **fileName**: The name of the Solidity file.
- **contractName**: The name of the smart contract.
- **functions**: A list of public functions defined in the contract.
- **statePreconditions**: A list of preconditions related to state variables for public functions. Each index corresponds to the matching function in the `functions` list (e.g., the first element in this list applies to the first function in `functions`).
- **functionPreconditions**: A list of preconditions related to parameters for public functions. Each index corresponds to the matching function in the `functions` list.
- **functionVariables**: Variables used within the functions.
- **tool_output**: A string pattern to identify the relevant output from VeriSol (or another underlying tool, if updated).
- **statesModeState**: Useful for executing PASCo in `states` mode.
- **statesNamesModeState**: A list of state names used in `states` mode. This provides meaningful names for abstract states.
- **statePreconditionsModeState**: A list of preconditions for states in `states` mode. Each index corresponds to the matching state in `statesNamesModeState`.
- **txBound**: The transaction bound (default is 8).
- **time_out**: The timeout duration in seconds (default is 600 seconds).
- **epaExtraConditions**: Additional conditions for the EPA mode.

This configuration ensures the abstraction process is tailored to the specific requirements of each contract.

### Example Configuration for `HelloBlockchainFixedConfig.py`

Below is an example of a configuration file for the `HelloBlockchain_fixed.sol` contract:

```python
fileName = "HelloBlockchain_fixed.sol"
contractName = "HelloBlockchain"
functions = [
    "SendRequest(requestMessage);",
    "SendResponse(responseMessage);"
]

statePreconditions = [
    "State == StateType.Respond", 
    "State == StateType.Request"
]
functionPreconditions = [
    "msg.sender == Requestor",
    "true"
]

functionVariables = "uint requestMessage, uint responseMessage"
tool_output = "Found a counterexample"

statesModeState = [[1, 0], [0, 2]]
statesNamesModeState = [
    "Request",
    "Respond"
]
statePreconditionsModeState = [
    "State == StateType.Request", 
    "State == StateType.Respond"
]
txBound = 8
```

### Output structure

- **k_n**: Indicates the `k_bound` parameter used to set up PASCo.
- **t_n**: Indicates the timeout used in seconds.

Each generated abstraction contains the following files:
- `.epa` or `.states` files: The abstraction in EPA mode or states (for enum).
- `.csv` file: The query times for that abstraction.
- `.txt` file: Extra information.

### Arguments

- `--file` (Required):  
  Configuration file for the tool. Example: `HelloBlockchainConfig`.

- `--mode` (Required):  
  Execution mode(s). Options: `"epa"` and/or `"states"`.

- `--txBound` (Optional, Default: 8):  
  Bound for the number of transactions.

- `--time_out` (Optional, Default: 600 seconds):  
  Execution timeout in seconds. Set to `0` for no timeout.

- `--folder_store_results` (Optional, Default: `graph`):  
  Path to store results. Default is `current_dir/graph`.

- `--verbose` (Optional, Default: `False`):  
  Print additional information during abstraction generation.

- `--reduceStates` (Optional, Default: `True`):  
  Optimize by discarding unreachable states at the first stage.

- `--reduceTrue` (Optional, Default: `True`):  
  Optimize by reducing states with `True` as preconditions.

- `--reduceEqual` (Optional, Default: `True`):  
  Optimize by reducing states with identical preconditions.

- `--trackAllVars` (Optional, Default: `True`):  
  Track all variables using `corral`.

- `--max_cores` (Optional, Default: Number of system CPU cores):  
  Number of CPU cores to use. Default is all available cores.


### Examples
Basic Usage
Run the tool with a configuration file and a mode:

```bash
python pasco.py --file HelloBlockchainConfig --mode epa
```

Advanced Usage
Customize execution with additional parameters:

```bash
python pasco.py --file HelloBlockchainConfig --mode epa --mode states --txBound 12 --time_out 1200 --folder_store_results results --verbose True --reduceStates False
```

## Features

- **Flexible Execution Modes:**  
  Supports `epa`, `states`, or both for customizable analysis.

- **Optimizations:**  
  Reduces unreachable states, simplifies preconditions, and removes redundant states.

- **Customizable Parameters:**  
  Configure transaction bounds, execution timeout, verbosity, and CPU core usage.

- **Result Management:**  
    Saves results in dot format and pdf. dot format can be viewed [here](https://dreampuf.github.io/GraphvizOnline/). A .csv file is saved to measure query times.

- **Scalability:**  
  Leverages multiple CPU cores for enhanced performance.

---


### Common Issues

1. **Error: Missing Required Argument**  
   - Make sure to include the required `--file` (that must to be in Config folder) and `--mode` arguments.

2. **Slow Execution**  
   - Limit the number of CPU cores used with `--max_cores <value>` (default value is the number of system CPU cores).
