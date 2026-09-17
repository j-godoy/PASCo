import itertools
import os
import shutil
import numpy as np
import graphviz
import time
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
import traceback
import argparse
import pickle
from collections import defaultdict

from helpers.exceptions import Mode
from helpers.tool_runner import (
    output_combination,
    get_params_from_function_name,
    try_command_task,
)
from helpers.solidity_parser import _extract_state_variables_from_solidity
from helpers.preconditions import sanitize_function_preconditions
from helpers.counterexamples import (
    _normalize_counterexample_specs,
    _build_check_state_call,
    _inject_check_state,
    _has_function_definition,
    _insert_body_into_contract,
)
from helpers.query_tasks import (
    _require_line,
    _safe_query_label,
    analyze_single_edge_task,
    check_hypermust_for_group,
)

# Inicializacion de variables que contabilizan los timeouts y errores.-
number_to = 0
number_corral_fail = 0
number_corral_fail_with_tackvars = 0

class PASCo:
    def __init__(self, configFile, mode, txBound, time_out, folder_store_results, verbose, reduceStates, reduceTrue, reduceEqual, trackAllVars, max_cores, must, savepdf=True, dot=None):
        self.configFile = configFile
        self.modes = mode
        self.txBound = txBound
        self.time_out = time_out
        self.verbose = verbose
        self.reduceStates = reduceStates
        self.reduceTrue = reduceTrue
        self.reduceEqual = reduceEqual
        self.trackAllVars = trackAllVars
        self.max_cores = max_cores
        self.must = must
        self.savepdf = savepdf
        self.dotResumePath = dot
        self.TRACK_VARS = "trackAllVars"
        self.tool_output = "Found a counterexample"
        self.statesNames = []
        
        self.config = __import__(self.configFile)
        self.fileName = os.path.join("Contracts", self.config.fileName)
        self.functions = self.config.functions
        self.contractName = self.config.contractName
        self.functionVariables = self.config.functionVariables
        self.originalFunctionPreconditions = self.config.functionPreconditions
        self.functionPreconditions = sanitize_function_preconditions(self.originalFunctionPreconditions, self.functions)
        manual_specs = _normalize_counterexample_specs(getattr(self.config, "counterexampleVariables", []))
        auto_detect  = getattr(self.config, "counterexampleVariablesAuto", True)
        if manual_specs:
            # El config define explícitamente las variables a usar: respetamos eso.
            self.counterexampleSpecs = manual_specs
        elif auto_detect:
            # No hay lista manual (o está vacía): parseamos el .sol y usamos
            # directamente las variables de estado del contrato (incluyendo
            # las heredadas de sus contratos padre).
            try:
                with open(self.fileName, "r") as f:
                    _sol_source = f.read()
                self.counterexampleSpecs = _extract_state_variables_from_solidity(
                    _sol_source, self.contractName
                )
                if self.counterexampleSpecs:
                    detected_names = ", ".join(s["state_var"] for s in self.counterexampleSpecs)
                    print(f"[counterexampleVariables] Auto-detectadas desde {self.config.fileName}: {detected_names}")
            except Exception as e:
                print(f"[counterexampleVariables] No se pudieron auto-detectar variables de estado: {e}")
                self.counterexampleSpecs = []
        else:
            self.counterexampleSpecs = []
        try:
            self.mustLoopBound = int(
                getattr(self.config, "mustLoopBound", getattr(self.config, "mustN", 5))
            )
        except Exception:
            self.mustLoopBound = 5
        try:
            self.txBound = int(txBound)
            print(f"txBound in config ignored. Using txBound={str(self.txBound)}")
        except Exception:
            try:
                self.txBound = self.config.txBound
            except Exception:
                self.txBound = 8
            
        try:
            self.time_out = float(time_out)
            print(f"time_out in config ignored. Using time_out={str(self.time_out)}")
        except Exception as err:
            print(f"Error reading time_out {time_out}.", err)
            try:
                self.time_out = float(self.config.time_out)
                print(f"Using time_out={str(self.time_out)} from config file.")
            except Exception:
                print(f"Exception getting time_out from config. Using default time_out=600")
                self.time_out = 600.0
        
        run_timestamp = time.strftime("%Y%m%d_%H%M%S")
        run_id = f"{self.contractName}_k{self.txBound}_to{int(self.time_out)}_{run_timestamp}"
        self.SAVE_GRAPH_PATH = os.path.join(folder_store_results, run_id) + os.sep
        os.makedirs(self.SAVE_GRAPH_PATH, exist_ok=True)
        self.NO_UNKNOWN_TX = "_no_unknown_tx"

        print(f"Configuration: {self.configFile}")
        print(f"Modes: {self.modes}")
        print(f"File Name: {self.fileName}")
        print(f"Contract Name: {self.contractName}")
        print(f"txBound: {self.txBound}")
        print(f"time_out: {self.time_out}")
        print(f"Folder to store results: {self.SAVE_GRAPH_PATH}")
        print(f"Verbose: {self.verbose}")
        print(f"Reduce States: {self.reduceStates}")
        print(f"Reduce True: {self.reduceTrue}")
        print(f"Reduce Equal: {self.reduceEqual}")
        print(f"Track All Vars: {self.trackAllVars}")
        print(f"Max Cores: {self.max_cores}")
        print(f"Function Variables: {self.functionVariables}")
        print(f"Functions: {self.functions}")
        print(f"Function Preconditions for queries: {self.functionPreconditions}")
        print(f"Counterexample Variables: {self.counterexampleSpecs}")
        print(f"Must loop bound: {self.mustLoopBound}")
        print(f"May graph resume file (--dot): {self.dotResumePath}")
        

    # -------------------------------------------------------------------------
    # Persistencia del grafo May, para poder reutilizarlo como punto de
    # partida de un análisis must (--dot) sin recalcularlo desde cero.
    # -------------------------------------------------------------------------

    def _maygraph_resume_path(self, mode):
        tempFileName = self.configFile.replace('Config', '') + "_" + str(mode.value if hasattr(mode, "value") else mode)
        return os.path.join(self.SAVE_GRAPH_PATH, tempFileName + "_maygraph.dot")

    def save_maygraph_data(self, mode, preconditions, states, extraConditions):
        """
        Serializa el grafo May ya calculado (nodos, edges con sus índices, y
        las listas de preconditions/states/extraConditions sobre las que se
        construyó) para poder usarlo después como punto de partida de un
        análisis must vía `--dot`, evitando recalcular toda la parte May
        (la más lenta).
        """
        payload = {
            "contractName": self.contractName,
            "fileName": self.fileName,
            "mode": mode.value if hasattr(mode, "value") else str(mode),
            "dict_nodes_edges": self.dict_nodes_edges,
            "preconditions": list(preconditions),
            "states": list(states),
            "extraConditions": list(extraConditions),
            "statesNames": self.statesNames,
        }
        path = self._maygraph_resume_path(mode)
        try:
            with open(path, "wb") as f:
                pickle.dump(payload, f)
            print(f"[may graph] Punto de partida para --dot guardado en: {path}")
        except Exception as e:
            print(f"[may graph] No se pudo guardar el archivo de resume ({path}): {e}")
        return path

    def load_maygraph_data(self, path):
        """
        Carga un grafo May previamente guardado con `save_maygraph_data`.
        Devuelve (preconditions, states, extraConditions, mode_str).
        """
        with open(path, "rb") as f:
            payload = pickle.load(f)

        if payload.get("contractName") != self.contractName:
            print(
                f"[--dot] Advertencia: '{path}' fue generado para el contrato "
                f"'{payload.get('contractName')}', pero la config actual usa "
                f"'{self.contractName}'. Los resultados pueden ser inconsistentes."
            )

        self.dict_nodes_edges = payload["dict_nodes_edges"]
        self.statesNames = payload.get("statesNames", self.statesNames)
        return (
            payload["preconditions"],
            payload["states"],
            payload["extraConditions"],
            payload.get("mode"),
        )

    def _render_or_save(self, dot, output_path):
        if self.savepdf:
            dot.render(output_path)
        else:
            dot.save(output_path + '.gv')

    def run(self):
        for current_mode in self.modes:
            init = time.time()
            if current_mode == Mode.epa.value:
                current_mode = Mode.epa
            if current_mode == Mode.states.value:
                current_mode = Mode.states
            self.run_mode(current_mode)
        
            end = time.time()

            # Constancia de tiempos:
            total_time = "Total time: {}".format(str(end-init))
            total_to = "# Time Out: {}".format(str(number_to))
            total_cfail1 = "# Corral Fail without trackvars: {}".format(str(number_corral_fail))
            total_cfail2 = "# Corral Fail with trackvars: {}".format(str(number_corral_fail_with_tackvars))
            
            print(total_time)
            print(total_to)
            print(total_cfail1)
            print(total_cfail2)
            tempFileName = self.configFile.replace('Config','')+"-"+str(current_mode)+".txt"
            with open(os.path.join(self.SAVE_GRAPH_PATH,tempFileName), 'w') as file:
                file.write("Subject: " + tempFileName.replace(".txt", "")+"\n")
                file.write(total_time+"\n")
                file.write(total_to+"\n")
                file.write(total_cfail1+"\n")
                file.write(total_cfail2+"\n")
                
            tempFileName = self.configFile.replace('Config','')+"-"+str(current_mode)+"_query_time.csv"
            with open(os.path.join(self.SAVE_GRAPH_PATH,tempFileName), 'w') as file:
                file.write("Type,TO?,feasible,time(sec)\n")
                for type, timeout, feasible, time_secs in self.query_list:
                    file.write(f"{str(type)},{str(timeout)},{str(feasible)},{str(time_secs)}\n")

            # ---------------------------------------------------------------
            # Resumen May | Must | Total de esta corrida (config + mode).
            # Se guarda un CSV propio de la corrida (queda junto al resto de
            # los resultados en self.SAVE_GRAPH_PATH) y además se imprime una
            # línea "TIMING_SUMMARY|..." fácil de parsear por un script batch
            # que orqueste múltiples corridas y arme la tabla final.
            # ---------------------------------------------------------------
            total_time_secs = end - init
            tempFileName = self.configFile.replace('Config','')+"-"+str(current_mode)+"_timing.csv"
            with open(os.path.join(self.SAVE_GRAPH_PATH,tempFileName), 'w') as file:
                file.write("Config,Mode,May(s),Must(s),Total(s)\n")
                file.write(f"{self.configFile},{current_mode},{self.time_may:.4f},{self.time_must:.4f},{total_time_secs:.4f}\n")

            print(f"TIMING_SUMMARY|{self.configFile}|{current_mode}|{self.time_may:.4f}|{self.time_must:.4f}|{total_time_secs:.4f}")

    
    def run_mode(self, mode):
        print()
        print(f"STARTING RUN IN MODE: {mode}")
        self.query_list = []
        self.dict_nodes_edges = {}
        self.dict_nodes_edges['nodes'] = []
        self.dict_nodes_edges['edges'] = []

        # Tiempos parciales de esta corrida (se exponen luego via self.time_may /
        # self.time_must para que run() arme el resumen May | Must | Total).
        self.time_may = 0.0
        self.time_must = 0.0

        if mode == Mode.states:
            self.statesNames = self.config.statesNamesModeState
            self.statePreconditionsModeState = self.config.statePreconditionsModeState
            self.statesModeState = self.config.statesModeState
        if mode == Mode.epa:
            self.statePreconditions = self.config.statePreconditions

        must_enabled = str(args.must).lower() == 'true'
        dot_resume_path = self.dotResumePath

        resumed_from_dot = False
        if dot_resume_path:
            if not must_enabled:
                print("[--dot] Se ignora porque --must no está habilitado (--dot solo sirve como punto de partida para must).")
            else:
                try:
                    preconditions, states, extraConditions, saved_mode = self.load_maygraph_data(dot_resume_path)
                    if saved_mode and saved_mode != mode.value:
                        print(
                            f"[--dot] Advertencia: '{dot_resume_path}' fue guardado para el modo "
                            f"'{saved_mode}', pero se está corriendo en modo '{mode.value}'."
                        )
                    resumed_from_dot = True
                    print(f"[--dot] Grafo May cargado desde '{dot_resume_path}'. Se omite el cálculo de May.")
                except Exception as e:
                    print(f"[--dot] No se pudo cargar '{dot_resume_path}': {e}. Se calculará el grafo May normalmente.")
                    traceback.print_exc()
                    resumed_from_dot = False

        t_may_start = time.time()
        if not resumed_from_dot:
            count = len(self.functions)
            funcionesNumeros = list(range(1, count + 1))

            extraConditions = []
            countPreInitial = 0
            countPreFinal = 0

            if mode == Mode.epa :
                states = self.getCombinations(funcionesNumeros)
                preconditions = self.getPreconditions(funcionesNumeros, states)
                try:
                    extraConditions = [self.config.epaExtraConditions for i in range(len(states))]
                except:
                    extraConditions = ["true" for i in range(len(states))]
            else :
                preconditions = self.statePreconditionsModeState
                states = self.statesModeState
                try:
                    extraConditions = self.config.statesExtraConditions
                except:
                    extraConditions = ["true" for i in range(len(states))]

            tempDir = self.create_directory_base("temp")

            countPreInitial = len(preconditions)

            cant_preconditions = len(preconditions)
            preconditionsThreads = preconditions
            preconditionsThreads = np.array_split(preconditionsThreads, cant_preconditions)
            statesThreads = states
            statesThreads = np.array_split(statesThreads, cant_preconditions)
            extraConditionsThreads = extraConditions
            if len(extraConditionsThreads) != 0:
                extraConditionsThreads = np.array_split(extraConditions, cant_preconditions)

            print(f"Number potential states: {len(preconditions)}")        

            if mode == Mode.epa and self.reduceStates:
                print("Reducing combinations...")
                self.reduceCombinations(cant_preconditions, preconditionsThreads, statesThreads, 
                                    extraConditionsThreads, mode, states)
            print("Reducing combinations Ended.")

            preconditionsThreads = [x for x in preconditionsThreads if len(x)]
            statesThreads = [x for x in statesThreads if len(x)]
            extraConditionsThreads = [x for x in extraConditionsThreads if len(x)]

            preconditionsThreads = np.concatenate(preconditionsThreads)
            statesThreads = np.concatenate(statesThreads)
            if len(extraConditionsThreads) != 0:
                extraConditionsThreads = np.concatenate(extraConditionsThreads)
            states = statesThreads
            preconditions = preconditionsThreads
            extraConditions = extraConditionsThreads

            countPreFinal = len(preconditions)
            temp_dir = os.path.join(tempDir, self.configFile + "-" + str(mode) + ".txt")
            f = open(temp_dir, "w")
            f.write(str(countPreInitial) + "\n" + str(countPreFinal) + "\n" + str(len(self.functions)))
            f.close()

            print(f"Number reachable states: {len(preconditionsThreads)}")        

            cant_valid_states = len(preconditionsThreads)
            preconditionsThreads = np.array_split(preconditionsThreads, cant_valid_states)
            statesThreads = np.array_split(statesThreads, cant_valid_states)
            extraConditionsThreads = np.array_split(extraConditionsThreads, cant_valid_states)

            self.validCombinations(cant_valid_states, preconditionsThreads, statesThreads, extraConditionsThreads, mode, extraConditions, preconditions, states)
            print("Ended ValidCombinations\n")

            self.try_init(states, mode, extraConditions, preconditions)
            print("Ended try_init\n")

            # Guardamos el grafo May ya calculado (nodos + edges con sus
            # índices, y las listas de preconditions/states/extraConditions
            # sobre las que se construyó) para poder reutilizarlo más
            # adelante como punto de partida de un análisis must (--dot),
            # sin tener que volver a correr toda esta parte (la más lenta).
            self.save_maygraph_data(mode, preconditions, states, extraConditions)

        # Tiempo de la parte May: exploración de estados/preconditions,
        # reducción de combinaciones y try_init. Si se resumió desde --dot,
        # este bloque no se ejecuta y el tiempo queda ~0 (no se recalculó May).
        self.time_may = time.time() - t_may_start

        tempFileName = self.configFile.replace('Config','')
        tempFileName = tempFileName + "_" + str(mode)
        output_dot = self.SAVE_GRAPH_PATH + tempFileName

        if must_enabled:
            t_must_start = time.time()

            # Conservamos una copia del grafo May "puro" (antes de
            # clasificar must/may/HyperMust) para poder emitir, además del
            # grafo must, el grafo may correspondiente.
            may_nodes_snapshot = list(self.dict_nodes_edges['nodes'])
            may_edges_snapshot = list(self.dict_nodes_edges['edges'])

            self.analyze_must_transitions(preconditions, states, extraConditions, mode)

            dot_may = self.create_graph_from(may_nodes_snapshot, may_edges_snapshot)
            dot_must = self.create_must_graph()

            self._render_or_save(dot_may, output_dot + "_may")
            self._render_or_save(dot_must, output_dot + "_must")

            # Tiempo de la parte Must: análisis de transiciones must +
            # construcción/render de ambos grafos (may snapshot y must).
            self.time_must = time.time() - t_must_start
        else:
            dot_may = self.create_graph()
            self._render_or_save(dot_may, output_dot)

        print("PROCESS ENDED\n")

    def getCombinations(self, funcionesNumeros):
        indices_con_truePreconditions = []
        results = []
        statesTemp = []
        cantidad_funciones = len(funcionesNumeros)
        for index, statePrecondition in enumerate(self.statePreconditions):
            if statePrecondition == "true":
                indices_con_truePreconditions.append(index + 1)

        for L in range(len(funcionesNumeros) + 1):
            for subset in itertools.combinations(funcionesNumeros, L):
                if self.reduceTrue:
                    isTrue = True
                    for truePre in indices_con_truePreconditions:
                        if truePre not in subset:
                            isTrue = False
                    if isTrue == True:
                        results.append(subset)
                else:
                    results.append(subset)

        for partialResult in results:
            paddingResult = []
            paddingResult = [0 for _ in range(cantidad_funciones)] 
            for i in range(cantidad_funciones):
                if len(partialResult) > i and partialResult[i] >=0:
                    indice = partialResult[i]
                    paddingResult[indice-1] = indice
            statesTemp.append(paddingResult)
        statesTemp2 = []
        
        if self.reduceEqual:
            for combination in statesTemp:
                isCorrect = True
                for iNumber, number in enumerate(combination):
                    for idx, x in enumerate(self.statePreconditions):
                        if iNumber != idx:
                            if number == 0:
                                if self.statePreconditions[iNumber] == x and combination[idx] != 0:
                                    isCorrect = False
                            elif self.statePreconditions[iNumber] == x and not((idx+1) in combination):
                                isCorrect = False
                
                if isCorrect:
                    statesTemp2.append(combination)
        else:
            statesTemp2 = statesTemp
        return statesTemp2

    def getPreconditions(self, funcionesNumeros, states):
        preconditions = []
        for result in states:
            precondition = ""
            for number in funcionesNumeros:
                if precondition != "":
                    precondition += " && "
                if number in result:
                    precondition += self.statePreconditions[number-1]
                else:
                    precondition += "!(" + self.statePreconditions[number-1] + ")"
            preconditions.append(precondition)
        return preconditions

    def combinationToString(self, combination):
        output = ""
        for i in combination:
            output += str(i) + "-"
        return output

    def functionOutput(self, number):
        return "function vc" + number + "(" + self.functionVariables + ") payable public {"

    def get_extra_condition_output(self, condition):
        extraConditionOutput = ""
        if condition != "" and condition != None:
            extraConditionOutput = _require_line(condition)
        return extraConditionOutput 

    def output_transitions_function(self, preconditionRequire, function, preconditionAssert, functionIndex, extraConditionPre, extraConditionPost, mode):
        if mode == Mode.epa:
            precondictionFunction = self.functionPreconditions[functionIndex]
        else:
            precondictionFunction = "true"
        extraConditionOutputPre = self.get_extra_condition_output(extraConditionPre)
        extraConditionOutputPost = self.get_extra_condition_output(extraConditionPost)
        verisolFucntionOutput = _require_line(preconditionRequire, "//require for initial state") + _require_line(precondictionFunction, "//require for parameter preconditions") + extraConditionOutputPre + function + "\n"  + "assert(!(" + preconditionAssert + " && " + extraConditionPost + "));//reach final state\n"
        return verisolFucntionOutput

    def output_init_function(self, preconditionAssert, extraCondition):
        extraConditionOutput = self.get_extra_condition_output(extraCondition)
        verisolFucntionOutput =  extraConditionOutput + "assert(!(" + preconditionAssert + "));\n"
        return verisolFucntionOutput

    def output_valid_state(self, preconditionRequire, extraCondition):
        extraConditionOutput = self.get_extra_condition_output(extraCondition)
        return _require_line(preconditionRequire) + extraConditionOutput + "assert(false);\n"

    def print_combination(self, indexCombination, tempCombinations, mode, functions, statesNames):
        output = self, output_combination(indexCombination, tempCombinations, mode, functions, statesNames)
        if self.verbose:
           print(output + "---------")

    def print_output(self, indexPreconditionRequire, indexFunction, indexPreconditionAssert, combinations, fullCombination, succes_by_to, mode):
        if self.verbose or succes_by_to != "":
            source = output_combination(indexPreconditionRequire, combinations, mode, self.functions, self.statesNames) + "\nCalling function" + str(self.functions[indexFunction]+succes_by_to)
            target = output_combination(indexPreconditionAssert, fullCombination, mode, self.functions, self.statesNames)
            output =f"From state:\n {source}\n\n it can reach state:\n {target}\n---------"
            print(output)

    def create_directory(self, index):
        final_directory = os.path.join(self.SAVE_GRAPH_PATH, 'output' + str(index))
        if not os.path.exists(final_directory):
            os.makedirs(final_directory)
        return final_directory

    def create_directory_base(self, name):
        current_directory = os.getcwd()
        final_directory = os.path.join(current_directory, name)
        if not os.path.exists(final_directory):
            os.makedirs(final_directory)
        return final_directory

    def delete_directory(self, final_directory):
        try:
            shutil.rmtree(final_directory)
        except Exception as e:
            print(f"Exception removing folder {final_directory}:\n{str(e)}")

    def create_file(self, index, final_directory):
        fileNameTemp = "OutputTemp"+str(index)+".sol"
        fileNameTemp = os.path.join(final_directory, fileNameTemp)
        if os.path.isfile(fileNameTemp):
            os.remove(fileNameTemp)
        shutil.copyfile(self.fileName, fileNameTemp)
        return fileNameTemp

    def create_file_base(self, final_directory, name):
        global contractName, fileName
        fileNameTemp = os.path.join(final_directory, name)
        if os.path.isfile(fileNameTemp):
            os.remove(fileNameTemp)
        shutil.copyfile(fileName, fileNameTemp)
        return fileNameTemp

    def write_file(self, fileNameTemp, body):
        _insert_body_into_contract(fileNameTemp, self.contractName, body)

    def get_valid_preconditions_output(self, preconditions, extraConditions):
        temp_output = ""
        tempFunctionNames = []
        for indexPreconditionRequire, preconditionRequire in enumerate(preconditions):
            functionName = self.get_temp_function_name(indexPreconditionRequire, "0", "0")
            tempFunctionNames.append(functionName)
            temp_function = self.functionOutput(functionName) + "\n"
            temp_function += self.output_valid_state(preconditionRequire, extraConditions[indexPreconditionRequire])
            temp_output += temp_function + "}\n"
        return temp_output, tempFunctionNames

    def get_valid_transitions_output(self, arg, preconditionsThread, preconditions, extraConditionsTemp, extraConditions, statesThread, states, mode):
        tempFunctionNames = []
        tempToolCommands = []
        tempDirectories = []
        try:
            for indexPreconditionRequire, preconditionRequire in enumerate(preconditionsThread):
                indexPreconditionRequireReal = None
                current_state = list(statesThread[indexPreconditionRequire])
                for indexState, state in enumerate(states):
                    if list(state) == current_state:
                        indexPreconditionRequireReal = indexState
                        break
                if indexPreconditionRequireReal is None:
                    for indexPreconditionAssert, preconditionAssert in enumerate(preconditions):
                        if str(preconditionRequire) == str(preconditionAssert):
                            indexPreconditionRequireReal = indexPreconditionAssert
                            break
                if indexPreconditionRequireReal is None:
                    raise Exception(f"Could not find global index for state {current_state}")
                for indexPreconditionAssert, preconditionAssert in enumerate(preconditions):
                    for indexFunction, function in enumerate(self.functions):
                        extraConditionPre = extraConditionsTemp[indexPreconditionRequire]
                        extraConditionPost = extraConditions[indexPreconditionAssert]
                        if ((indexFunction + 1) in statesThread[indexPreconditionRequire] and mode == Mode.epa) or (mode == Mode.states):
                            functionName = self.get_temp_function_name(indexPreconditionRequireReal, indexPreconditionAssert, indexFunction)
                            tempFunctionNames.append(functionName)
                            temp_function = self.functionOutput(functionName) + "\n"
                            temp_function += self.output_transitions_function(preconditionRequire, function, preconditionAssert, indexFunction, extraConditionPre, extraConditionPost, mode)
                            temp_function += "}\n"
                            dirname = str(arg)+"_"+functionName
                            final_directory = self.create_directory(dirname)
                            fileNameTemp = self.create_file(dirname, final_directory)
                            self.write_file(fileNameTemp, temp_function)
                            tool = f"VeriSol {os.path.basename(fileNameTemp)} {self.contractName}"
                            tempToolCommands.append(tool)
                            tempDirectories.append(final_directory)
        except Exception as e:
            print(f"Exception in method get_valid_transitions_output: {e}")
            traceback.print_exc()
        return tempToolCommands, tempFunctionNames, tempDirectories

    def get_init_output(self, indexPreconditionAssert, preconditionAssert, extraConditions): 
        temp_output = ""
        functionName = self.get_temp_function_name(indexPreconditionAssert, "0" , "0")
        temp_function = self.functionOutput(functionName) + "\n"
        temp_function += self.output_init_function(preconditionAssert, extraConditions[indexPreconditionAssert])
        temp_output += temp_function + "}\n"
        return functionName, temp_output

    def try_init(self, states, mode, extraConditions, preconditions):
        try:
            tempFunctionNames = []
            tool_commands = []
            final_directories = []
            txBound_constructor = 1
            indexPreconditionAssertMap = {}
            QUERY_TYPE = "QUERY_NORMAL_CONSTRUCTOR"

            for indexPreconditionAssert, preconditionAssert in enumerate(preconditions):
                functionName, body = self.get_init_output(indexPreconditionAssert, preconditionAssert, extraConditions)
                indexPreconditionAssertMap[functionName] = indexPreconditionAssert
                dirname = f"_init_{indexPreconditionAssert}_{functionName}"
                final_directory = self.create_directory(dirname)
                fileNameTemp = self.create_file(dirname, final_directory)
                self.write_file(fileNameTemp, body)
                tool = f"VeriSol {os.path.basename(fileNameTemp)} {self.contractName}"
                
                tempFunctionNames.append(functionName)
                tool_commands.append(tool)
                final_directories.append(final_directory)

            results = self.execute_try_command_in_parallel(tool_commands, tempFunctionNames, final_directories, [], states, txBound_constructor, mode, QUERY_TYPE)

            if len(results) != len(tempFunctionNames):
                print("long de results: ", len(results))
                print(results)
                print("long de tempFunctionNames: ", len(tempFunctionNames))
                print("Error: La longitud de resultados no coincide con los nombres de funciones.")
                traceback.print_exc()
                exit(1)

            for functionName, success, to_or_fail in results:
                if success:
                    self.dict_nodes_edges['nodes'].append(("init", "init"))
                    self.dict_nodes_edges['nodes'].append((self.combinationToString(states[indexPreconditionAssertMap[functionName]]), output_combination(indexPreconditionAssertMap[functionName], states, mode, self.functions, self.statesNames)))
                    self.dict_nodes_edges['edges'].append(("init", self.combinationToString(states[indexPreconditionAssertMap[functionName]]), f"constructor{to_or_fail}"))
            
            if not self.verbose:
                for final_directory in final_directories:
                    self.delete_directory(final_directory)
        except Exception as e:
            print(f"Exeption in method try_init: {e}")
            traceback.print_exc()

    def get_temp_function_name(self, indexPrecondtion, indexAssert, indexFunction):
        return str(indexPrecondtion) + "x" + str(indexAssert) + "x" + str(indexFunction)

    # -------------------------------------------------------------------------
    # MUST-transition analysis  (Algorithm del paper)
    # -------------------------------------------------------------------------

    def output_enabledness_function(self, preconditionRequire, functionIndex, extraConditionPre):
        pre_f = self.functionPreconditions[functionIndex]
        extra = self.get_extra_condition_output(extraConditionPre)
        return (
            _require_line(preconditionRequire, "//QUERY_ENABLEDNESS: require initial state")
            + extra
            + f"assert({pre_f});//QUERY_ENABLEDNESS: function must be enabled\n"
        )

    def output_must_function(self, preconditionRequire, function, preconditionAssert,
                             functionIndex, extraConditionPre, extraConditionPost,
                             concrete_cexamples):
        """
        Versión del método de instancia. Recibe concrete_cexamples como lista de
        expresiones concretas ("x == 12 && state == 0 && owner == address(4)").
        """
        pre_f = self.functionPreconditions[functionIndex]
        extra_pre = self.get_extra_condition_output(extraConditionPre)
        check_state_call = _build_check_state_call(self.counterexampleSpecs, self.contractName, "QUERY_MUST")

        cex_requires = "".join(
            f"require(!({c}));//QUERY_MUST: exclude concrete counterexample\n"
            for c in concrete_cexamples
        )

        post_cond = extraConditionPost if extraConditionPost.strip() else "true"
        return (
            _require_line(preconditionRequire, "//QUERY_MUST: require initial state")
            + _require_line(pre_f, "//QUERY_MUST: require function precondition")
            + cex_requires
            + extra_pre
            + check_state_call
            + function + "\n"
            + f"assert({preconditionAssert} && {post_cond});//QUERY_MUST: must reach dest\n"
        )

    def output_may_function(self, preconditionRequire, function, preconditionAssert,
                            functionIndex, extraConditionPre, extraConditionPost,
                            concrete_cexample):
        """
        Versión del método de instancia. Recibe concrete_cexample como expresión
        concreta ("x == 12 && state == 0 && owner == address(4)").
        """
        pre_f = self.functionPreconditions[functionIndex]
        extra_pre = self.get_extra_condition_output(extraConditionPre)
        check_state_call = _build_check_state_call(self.counterexampleSpecs, self.contractName, "QUERY_MAY")

        return (
            _require_line(preconditionRequire, "//QUERY_MAY: require initial state")
            + _require_line(pre_f, "//QUERY_MAY: require function precondition")
            + _require_line(concrete_cexample, "//QUERY_MAY: fix concrete counterexample state")
            + extra_pre
            + check_state_call
            + function + "\n"
            + f"assert(!({preconditionAssert}));//QUERY_MAY: must NOT reach dest from counterexample\n"
        )

    def run_single_query(self, query_body, query_label, QUERY_TYPE, inject_check_state=False):
        safe_label = _safe_query_label(query_label)
        dirname = f"_must_{safe_label}"
        final_directory = self.create_directory(dirname)
        try:
            fileNameTemp = self.create_file(dirname, final_directory)

            func_name = safe_label
            body = self.functionOutput(func_name) + "\n" + query_body + "}\n"
            self.write_file(fileNameTemp, body)

            # Inyectar check_state sobre el archivo final que se va a pasar a VeriSol.
            if inject_check_state and self.counterexampleSpecs:
                _inject_check_state(fileNameTemp, self.contractName, self.counterexampleSpecs)
                with open(fileNameTemp, "r") as f:
                    final_source = f.read()
                expected_func = f"check_state_{self.contractName}"
                if not _has_function_definition(final_source, expected_func):
                    raise RuntimeError(f"{expected_func} was not injected into {fileNameTemp}")

            tool = f"VeriSol {os.path.basename(fileNameTemp)} {self.contractName}"
            feasible, to_or_fail, query_values = try_command_task(
                func_name, [func_name], tool, final_directory, [],
                self.txBound, self.time_out, self.trackAllVars, Mode.epa,
                self.functions, self.statesNames, [], self.verbose,
                QUERY_TYPE, self.contractName, self.tool_output, self.TRACK_VARS,
            )
            if query_values:
                self.query_list.append(query_values)
            return feasible, to_or_fail
        except Exception as e:
            traceback.print_exc()
            print(f"Error in run_single_query ({query_label}): {e}")
            return False, "error"
        finally:
            if not self.verbose:
                self.delete_directory(final_directory)
    
    def analyze_must_transitions(self, preconditions, states, extraConditions, mode):
        print("\nStarting analyze_must_transitions (parallel)...")
        N = self.mustLoopBound

        edges = self.dict_nodes_edges['edges']

        constructor_edges = [e for e in edges if len(e) == 3]
        functional_edges  = [e for e in edges if len(e) != 3]

        def is_time_transition(fn):
            return fn.replace(";", "").strip() == "t()"
    
        t_edges = [e for e in functional_edges if is_time_transition(self.functions[e[6]])]
        non_t_edges = [e for e in functional_edges if not is_time_transition(self.functions[e[6]])]

        t_classified = []
        t_groups = defaultdict(list)
        for e in t_edges:
            t_groups[e[0]].append(e)

        for src_str, group in t_groups.items():
            if len(group) == 1:
                e = group[0]
                src, dst, func_label, _, idx_src, idx_dst, idx_func = e
                t_classified.append((src, dst, func_label, True, idx_src, idx_dst, idx_func))
                print(f"  [t()] Must (single dest): {src} -> {dst}")
            else:
                winning_dsts = frozenset(e[1] for e in group)
                for e in group:
                    src, dst, func_label, _, idx_src, idx_dst, idx_func = e
                    t_classified.append((src, dst, func_label, "HyperMust", idx_src, idx_dst, idx_func, winning_dsts))
                print(f"  [t()] HyperMust: {src_str} -> {list(winning_dsts)}")

        # ------------------------------------------------------------------
        # FASE 1: Must / May  (solo non_t_edges)
        # ------------------------------------------------------------------
        queried_edges = []

        with ProcessPoolExecutor(max_workers=self.max_cores) as executor:
            future_to_edge = {
                executor.submit(
                    analyze_single_edge_task,
                    edge,
                    list(preconditions),
                    list(extraConditions),
                    self.functions,
                    self.functionPreconditions,
                    self.functionVariables,
                    self.contractName,
                    self.fileName,
                    self.txBound,
                    self.time_out,
                    self.trackAllVars,
                    self.verbose,
                    self.tool_output,
                    self.TRACK_VARS,
                    self.statesNames,
                    self.counterexampleSpecs,  # <- specs pasadas al proceso paralelo
                    N,
                    self.SAVE_GRAPH_PATH,
                ): edge
                for edge in non_t_edges
            }

            for future in as_completed(future_to_edge):
                original_edge = future_to_edge[future]
                src, dst, func_label, _, idx_src, idx_dst, idx_func = original_edge
                try:
                    _, result_must, query_list_local = future.result()
                    self.query_list.extend(query_list_local)
                except Exception as e:
                    traceback.print_exc()
                    print(f"Error analyzing edge {original_edge}: {e}")
                    result_must = False
                queried_edges.append((src, dst, func_label, result_must, idx_src, idx_dst, idx_func))

        # ------------------------------------------------------------------
        # FASE 2: HyperMust sobre los May de non_t_edges
        # ------------------------------------------------------------------
        may_edges   = [e for e in queried_edges if e[3] is False]
        resolved_edges = [e for e in queried_edges if e[3] is not False]

        groups: dict[tuple, list] = defaultdict(list)
        for e in may_edges:
            groups[(e[0], e[2])].append(e)

        hypermust_groups  = {k: v for k, v in groups.items() if len(v) >= 2}
        singleton_may     = [e for k, v in groups.items() if len(v) < 2 for e in v]

        print(f"\n  [hypermust] {len(hypermust_groups)} group(s) of May edges to check for HyperMust.")

        hypermust_results: dict[tuple, tuple] = {}

        if hypermust_groups:
            with ProcessPoolExecutor(max_workers=self.max_cores) as executor:
                future_to_key = {
                    executor.submit(
                        check_hypermust_for_group,
                        group_edges,
                        list(preconditions),
                        list(extraConditions),
                        self.functions,
                        self.functionPreconditions,
                        self.functionVariables,
                        self.contractName,
                        self.fileName,
                        self.txBound,
                        self.time_out,
                        self.trackAllVars,
                        self.verbose,
                        self.tool_output,
                        self.TRACK_VARS,
                        self.statesNames,
                        self.SAVE_GRAPH_PATH,
                    ): key
                    for key, group_edges in hypermust_groups.items()
                }

                for future in as_completed(future_to_key):
                    key = future_to_key[future]
                    try:
                        found, combo_indices, qlist = future.result()
                        self.query_list.extend(qlist)
                        hypermust_results[key] = (found, combo_indices)
                    except Exception as e:
                        traceback.print_exc()
                        print(f"Error in hypermust check for group {key}: {e}")
                        hypermust_results[key] = (False, None)

        final_may_edges = []
        for key, group_edges in hypermust_groups.items():
            found, combo_indices = hypermust_results.get(key, (False, None))
            if found and combo_indices is not None:
                winning_dsts = frozenset(group_edges[i][1] for i in combo_indices)
                for e in group_edges:
                    src, dst, func_label, _, idx_src, idx_dst, idx_func = e
                    if dst in winning_dsts:
                        final_may_edges.append((src, dst, func_label, "HyperMust", idx_src, idx_dst, idx_func, winning_dsts))
                    else:
                        final_may_edges.append(e)
            else:
                final_may_edges.extend(group_edges)

        self.dict_nodes_edges['edges'] = (
            constructor_edges
            + t_classified
            + resolved_edges
            + singleton_may
            + final_may_edges
        )
        print("analyze_must_transitions finished (parallel).\n")

    def create_must_graph(self):
        dot = graphviz.Digraph(comment=self.fileName)
        for n in self.dict_nodes_edges['nodes']:
            dot.node(n[0], n[1])

        for e in self.dict_nodes_edges['edges']:
            if len(e) == 3:
                dot.edge(e[0], e[1], label=str(e[2]), color="blue")
            else:
                src_str, dst_str, func_label, is_must = e[0], e[1], e[2], e[3]
                style = "dashed" if str(func_label).replace(";", "").strip().startswith("t(") else "solid"
                if is_must == "HyperMust":
                    dot.edge(src_str, dst_str, label=str(func_label), color="turquoise", style=style)
                elif is_must is True:
                    dot.edge(src_str, dst_str, label=str(func_label), color="blue", style=style)
                else:
                    dot.edge(src_str, dst_str, label=str(func_label), style=style)
        return dot

    def create_graph_from(self, nodes, edges):
        dot = graphviz.Digraph(comment=self.fileName)
        for n in nodes:
            dot.node(n[0], n[1])
        for e in edges:
            dot.edge(e[0], e[1], label=str(e[2]))
        return dot

    def create_graph(self):
        return self.create_graph_from(self.dict_nodes_edges['nodes'], self.dict_nodes_edges['edges'])

    def add_node_to_graph(self, indexPreconditionRequire, indexPreconditionAssert, indexFunction, statesTemp, states, succes_by_to, mode):
        self.dict_nodes_edges['nodes'].append((self.combinationToString(statesTemp[indexPreconditionRequire]), output_combination(indexPreconditionRequire, statesTemp, mode, self.functions, self.statesNames)))
        self.dict_nodes_edges['nodes'].append((self.combinationToString(states[indexPreconditionAssert]), output_combination(indexPreconditionAssert, states, mode, self.functions, self.statesNames)))
        if not self.functions[indexFunction].startswith("dummy_"):
            self.dict_nodes_edges['edges'].append((
                self.combinationToString(statesTemp[indexPreconditionRequire]),
                self.combinationToString(states[indexPreconditionAssert]),
                self.functions[indexFunction] + succes_by_to,
                False,
                indexPreconditionRequire,
                indexPreconditionAssert,
                indexFunction,
            ))

    def reduceCombinations(self, cant_preconditions, preconditionsThreads, statesThreads, extraConditionsThreads, mode, states):
        print(f"Starting task reduceCombinations for '{cant_preconditions}' states")
        try:
            args = []
            toolCommands = []
            tempFunctionNames = []
            final_directories = []
            
            preconditionsTempList = []
            statesTempList = []
            extraConditionsTempList = []

            QUERY_TYPE = "QUERY_REDUCE_COMBINATION"
            
            for arg in range(cant_preconditions):
                args.append(arg)
                preconditionsTemp = preconditionsThreads[arg]
                statesTemp = statesThreads[arg]
                extraConditionsTemp = extraConditionsThreads[arg]
                final_directory = self.create_directory(arg)
                fileNameTemp = self.create_file(arg, final_directory)
                body,fuctionCombinations = self.get_valid_preconditions_output(preconditionsTemp, extraConditionsTemp)
                self.write_file(fileNameTemp, body)
                tool = f"VeriSol {os.path.basename(fileNameTemp)} {self.contractName}"
                toolCommands.append(tool)
                tempFunctionNames.append(fuctionCombinations[0])
                final_directories.append(final_directory)
                preconditionsTempList.append(preconditionsTemp)
                statesTempList.append(statesTemp)
                extraConditionsTempList.append(extraConditionsTemp)
                
            results = self.execute_try_command_in_parallel_reduce(args, toolCommands, tempFunctionNames, final_directories, statesTempList, mode, states, QUERY_TYPE)

            for i, functionName, success, to_or_fail in results:
                indexPreconditionRequire, _, _ = get_params_from_function_name(functionName)
                preconditionsTemp2 = []
                statesTemp2 = []
                extraConditionsTemp2 = []
                
                if success:
                    preconditionsTemp2.append(preconditionsTempList[i][indexPreconditionRequire])
                    statesTemp2.append(statesTempList[i][indexPreconditionRequire])
                    extraConditionsTemp2.append(extraConditionsTempList[i][indexPreconditionRequire])
                    if to_or_fail:
                        print(f"[try_preconditions] Timeout en función: {functionName}")
                        i_state = output_combination(indexPreconditionRequire, statesTempList[i], mode, self.functions, self.statesNames)
                        print(i_state)
            
                preconditionsThreads[i] = preconditionsTemp2
                statesThreads[i] = statesTemp2
                extraConditionsThreads[i] = extraConditionsTemp2
                
            if not self.verbose:
                for final_directory in final_directories:
                    self.delete_directory(final_directory)
            
        except Exception as e:
            traceback.print_exc()
            print(f"Error en reduceCombinations: {e}")
            exit(1)

    def validCombinations(self, cant_valid_states, preconditionsThreads, statesThreads, extraConditionsThreads, mode, extraConditions, preconditions, states):
        print(f"Starting task validCombinations for '{cant_valid_states}' states")
        try:
            tempFunctionNames = []
            tempToolCommands = []
            tempDirectories = []
            statesTempList = []
            args = []
            cont = 0

            QUERY_TYPE =  "QUERY_NORMAL"
            for arg in range(cant_valid_states):
                preconditionsTemp = preconditionsThreads[arg]
                statesTemp = statesThreads[arg]
                extraConditionsTemp = extraConditionsThreads[arg]
                toolCommands, functionNames, directories = self.get_valid_transitions_output(arg, preconditionsTemp, preconditions, extraConditionsTemp, extraConditions, statesTemp, states, mode)
                tempToolCommands.extend(toolCommands)
                tempFunctionNames.extend(functionNames)
                tempDirectories.extend(directories)
                
                statesTempList.extend([states]*len(functionNames))
                for _ in range(0, len(functionNames)):
                    args.append(cont)
                    cont += 1
                
                if len(tempToolCommands) != len(tempFunctionNames) or len(tempFunctionNames) != len(tempDirectories) or len(tempFunctionNames) != len(statesTempList) or len(tempFunctionNames) != len(args):
                    print("Error: Las longitudes de las listas no coinciden.")
                    print("longitud de tempToolCommands: ", len(tempToolCommands))
                    print("longitud de tempFunctionNames: ", len(tempFunctionNames))
                    print("longitud de tempDirectories: ", len(tempDirectories))
                    print("longitud de statesTempList: ", len(statesTempList))
                    print("longitud de args: ", len(args))
                    exit(1)
                
            if self.verbose:
                print(f"Processing transactions: {tempFunctionNames}")

            results = self.execute_try_command_in_parallel_reduce(args, tempToolCommands, tempFunctionNames, tempDirectories, statesTempList, mode, states, QUERY_TYPE)

            if len(results) != len(tempFunctionNames):
                print("long de results: ", len(results))
                print(results)
                print("long de tempFunctionNames: ", len(tempFunctionNames))
                print("Error: La longitud de resultados no coincide con los nombres de funciones.")
                traceback.print_exc()
                exit(1)

            for i, functionName, success, to_or_fail in results:
                indexPreconditionRequire, indexPreconditionAssert, indexFunction = get_params_from_function_name(functionName)
                if success:
                    self.add_node_to_graph(indexPreconditionRequire, indexPreconditionAssert, indexFunction, statesTempList[i], states, to_or_fail, mode)
                    if self.verbose:
                        self.print_output(indexPreconditionRequire, indexFunction, indexPreconditionAssert, statesTempList[i], states, to_or_fail, mode)
            if not self.verbose:
                for final_directory in tempDirectories:
                    self.delete_directory(final_directory)
        except Exception as e:
            traceback.print_exc()
            print(f"Error en validCombinations: {e}")
            exit(1)

    def execute_try_command_in_parallel_reduce(self, args, toolCommands, tempFunctionNames, final_directories, statesTemp, mode, states, QUERY_TYPE):
        global number_to, number_corral_fail, number_corral_fail_with_tackvars
        
        results = []
        errors = []
        print(f"Executing {len(args)} tasks in parallel - execute_try_command_in_parallel_reduce")
        
        with ProcessPoolExecutor(max_workers=self.max_cores) as executor:
            future_to_function = {executor.submit(try_command_task, fn, [], tool, final_directory, stateTemp,
                        self.txBound, self.time_out, self.trackAllVars, mode, self.functions,
                        self.statesNames, states, self.verbose, QUERY_TYPE, self.contractName,
                        self.tool_output, self.TRACK_VARS): (fn,arg) for arg, tool, fn, final_directory, stateTemp in zip(args, toolCommands, tempFunctionNames, final_directories, statesTemp)}

            for future, value in future_to_function.items():
                function_name = value[0]
                arg = value[1]
                try:
                    feasible, to_or_fail, query_values = future.result()
                    results.append((arg, function_name, feasible, to_or_fail))
                    if to_or_fail == "?":
                        number_to += 1
                    elif to_or_fail == "fail?":
                        number_corral_fail_with_tackvars += 1
                    elif to_or_fail != "":
                        number_corral_fail += 1

                    if query_values:
                        self.query_list.append(query_values)
                except Exception as e:
                    traceback.print_exc()
                    errors.append((function_name, e))
                    print(f"Error en la tarea: {e}")

        if errors:
            print(f"Errores encontrados en {len(errors)} tareas: {errors}")
            exit(1)

        return results

    def execute_try_command_in_parallel(self, toolCommands, tempFunctionNames, final_directories, statesTemp, states, txBound, mode, QUERY_TYPE):
        global number_to, number_corral_fail, number_corral_fail_with_tackvars

        results = []
        errors = []
        print(f"Starting execute_try_command_in_parallel for {len(tempFunctionNames)} functions")
        with ProcessPoolExecutor(max_workers=self.max_cores) as executor:
            future_to_function = {executor.submit(try_command_task, fn, [fn], tool, final_directory, statesTemp,
                                                txBound, self.time_out, self.trackAllVars, mode, self.functions,
                                                self.statesNames, states, self.verbose, QUERY_TYPE, self.contractName,
                                                self.tool_output, self.TRACK_VARS): fn for tool, fn, final_directory in zip(toolCommands, tempFunctionNames, final_directories)}
            for future in as_completed(future_to_function):
                function_name = future_to_function[future]
                try:
                    feasible, to_or_fail, query_values = future.result()
                    results.append((function_name, feasible, to_or_fail))
                    if to_or_fail == "?":
                        number_to += 1
                    elif to_or_fail == "fail?":
                        number_corral_fail_with_tackvars += 1
                    elif to_or_fail != "":
                        number_corral_fail += 1

                    if query_values:
                        self.query_list.append(query_values)
                except Exception as e:
                    traceback.print_exc()
                    errors.append((function_name, e))
                    print(f"Error en la tarea: {e}")

        if errors:
            print(f"Errores encontrados en {len(errors)} tareas: {errors}")
            exit(1)

        return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                    prog=sys.argv[0],
                    description='PASCo tool - Predicate Abstraction for Smart Contracts Generator',
                    formatter_class=argparse.RawTextHelpFormatter)
    
    sys.path.append(os.path.join(os.getcwd(), "Configs"))

    parser.add_argument('--file', default='.', required=True,
        help='ConfigFile to run the tool. Example: HelloBlockchainConfig')
    parser.add_argument('--mode', default=[], choices=[Mode.epa.value, Mode.states.value],
        action='append', required=True,
        help='Mode to execute the tool. Options are "epa" and/or "states"')
    parser.add_argument('--txBound', required=False, default='.',
        help='parameter to bound the number of transactions. Default is 8')
    parser.add_argument('--time_out', required=False, default='600',
        help='parameter to bound the time of execution. Default is 600 seconds; 0 means no time out')
    parser.add_argument('--folder_store_results', required=False, default='graph',
        help='path to store the results. Default is stored in current_dir/graph')
    parser.add_argument('--verbose', required=False, default=False,
        help='Option to print extra information during abstraction generation')
    parser.add_argument('--reduceStates', required=False, default=True,
        help='optimization to discard states that are not reachable at a first stage')
    parser.add_argument('--reduceTrue', required=False, default=True,
        help='optimization to reduce states that has True as preconditions')
    parser.add_argument('--reduceEqual', required=False, default=True,
        help='optimization to reduce states that has the same preconditions')
    parser.add_argument('--trackAllVars', required=False, default=True,
        help='parameter to track all variables by corral. Default is True')
    parser.add_argument('--max_cores', required=False, default=os.cpu_count(),
        help='parameter to set the number of cores to use. Default is the number of cores in current computer')
    parser.add_argument('--must', required=False, default=False, action='store_true',
        help='parameter to generate graphs with must transitions. Pass just --must to enable. Default is False')
    parser.add_argument('--savepdf', required=False, default=True,
        help='whether to save the output graph as PDF. Default is True')
    parser.add_argument('--dot', required=False, default=None,
        help="(optional) ruta a un archivo '<config>_<epa|states>_maygraph.dot' generado en una corrida "
             "previa (con o sin --must). Si se pasa junto con --must, se usa como punto de partida del "
             "análisis must, evitando recalcular el grafo May (la parte más lenta). Si no se pasa, el "
             "grafo May se calcula normalmente. Se ignora si --must no está habilitado.")

    args = parser.parse_args()

    if Mode.epa.value not in args.mode and Mode.states.value not in args.mode:
        print("Error: At least one mode must be selected. Options are 'epa' and/or 'states'")
        exit(1)

    pasco = PASCo(
        configFile=args.file,
        mode=args.mode,
        txBound=args.txBound,
        time_out=args.time_out,
        folder_store_results=args.folder_store_results,
        verbose=args.verbose,
        reduceStates=args.reduceStates,
        reduceTrue=args.reduceTrue,
        reduceEqual=args.reduceEqual,
        trackAllVars=args.trackAllVars,
        max_cores=int(args.max_cores),
        must=args.must,
        savepdf=str(args.savepdf).lower() == 'true',
        dot=args.dot,
    )
    
    pasco.run()