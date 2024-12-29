# PASCo
Predicate Abstraction for Smart Contracts tool

This tool generates a predicate abstraction in dot format from Solidity source code.

How to run:

```
python3 Pasco.py [contract_name] [mode] [info_level] [optim_params] [timeout] [bound]
```
where
- contract_name: name of the config file in /Config folder. Example: HelloBlockchainConfig
- mode: "-e" for EPA and "-s" for states.
- info_level: "-v" for verbose and "-b" for basic info.
- optim_params: "-default" for default parameters.
- time_out: "time_out=n", n=seconds
- bound: "txbound=n", n=max transaction bound for Verisol

It requires that the corresponding Solidity contract is in the /Contract folder and its config file in the /Config folder.

### Requirements:
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

