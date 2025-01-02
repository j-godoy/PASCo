import itertools
import subprocess
import os
import shutil
import numpy  as np
import graphviz
from threading import Thread
import time
from enum import Enum
import sys
import platform
import psutil
import remove_unknown_tx
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import Manager, Process
import traceback
import argparse



class Mode(Enum):
    epa = "epa"
    states = "states"


number_to = 0
number_corral_fail = 0
number_corral_fail_with_tackvars = 0

def getToolCommand(includeNumber, toolCommand, combinations, txBound, trackAllVars, contractName):
        command = toolCommand + " " 
        command = command + "/txBound:" + str(txBound) + " "
        command = command + "/noPrf "
        if trackAllVars:
            command = command + "/trackAllVars"+ " "
        for indexCombination, combi in enumerate(combinations):
            if combi != includeNumber: 
                command += "/ignoreMethod:vc"+ combi +"@" + contractName + " "
        return command

def get_params_from_function_name(temp_function_name):
        array = temp_function_name.split('x')
        return int(array[0]), int(array[1]), int(array[2])

def output_combination(indexCombination, tempCombinations, mode, functions, statesNames):
        combination = tempCombinations[indexCombination]
        output = ""
        for function in combination:
            if function != 0:
                if mode == Mode.epa:
                    output += functions[function-1] +"\n"
                else:
                    output += statesNames[function-1]

        if output == "":
            output = "Vacio\n"
        return output

def try_command_task(function_name, tempFunctionNames, tool, final_directory, statesTemp,
                        txBound, time_out, trackAllVars, mode, functions,
                        statesNames, states, verbose, QUERY_TYPE, contractName,
                        tool_output, TRACK_VARS):
    """
    Ejecuta `try_command` para una tarea específica y actualiza las variables compartidas.
    """
    feasible, to_or_fail, query_values = try_command(tool, function_name, tempFunctionNames, final_directory, statesTemp,
                        txBound, time_out, trackAllVars, mode, functions,
                        statesNames, states, verbose, QUERY_TYPE, contractName,
                        tool_output, TRACK_VARS)
    if to_or_fail == TRACK_VARS: #Lo vuelvo a ejecutar, pero con el parámetro trackAllVars=True
        feasible, to_or_fail, query_values = try_command(tool, function_name, tempFunctionNames, final_directory, statesTemp,
                        txBound, time_out, True, mode, functions,
                        statesNames, states, verbose, QUERY_TYPE, contractName,
                        tool_output, TRACK_VARS)
    return feasible, to_or_fail, query_values


def try_command(tool, temp_function_name, tempFunctionName, final_directory, statesTemp,
                txBound, time_out, trackAllVars, mode, functions,
                statesNames, states, verbose, QUERY_TYPE, contractName,
                tool_output, TRACK_VARS):
    ADD_TX_IF_TIMEOUT = False
    ADD_TX_IF_FAIL = False
    
    #Evito chequear funciones "dummy"
    if len(statesTemp) > 0:
        indexPreconditionRequire, indexPreconditionAssert, indexFunction = get_params_from_function_name(temp_function_name)
        i_state = output_combination(indexPreconditionRequire, statesTemp, mode, functions, statesNames)
        f_state = output_combination(indexPreconditionAssert, states, mode, functions, statesNames)
        if functions[indexFunction].startswith("dummy_"):
            if i_state != f_state:
                return False,"",()
            else:
                return True,"",()
    
    command = getToolCommand(temp_function_name, tool, tempFunctionName, txBound, trackAllVars, contractName)
    if verbose:
        print(f"Running command {command}")
    
    result = ""
    FAIL_TO = False
    try:
        init = time.time()
        if platform.system() == "Windows":
            proc = subprocess.Popen(command.split(" "), stdout=subprocess.PIPE, cwd=final_directory)
            result = proc.communicate(timeout=time_out)
            # result = subprocess.check_output(command.split(" "), shell = False, cwd=final_directory, timeout=10.0)#Javi
        else:
            #TODO: run with timeout in unix
            result = subprocess.run([command, ""], shell = True, cwd=final_directory, stdout=subprocess.PIPE)
        end = time.time()
    except Exception as e:
        end = time.time()
        FAIL_TO = True
        if verbose:
            print(f"---EXCEPTION por time out de {time_out} segs al ejecutar '{command}' desde folder '{final_directory}'")
        indexPreconditionRequire, indexPreconditionAssert, indexFunction = get_params_from_function_name(temp_function_name)
        i_state = output_combination(indexPreconditionRequire, statesTemp, mode, functions, statesNames)
        f_state = output_combination(indexPreconditionAssert, states, mode, functions, statesNames)
        if verbose:
            print(f"TimeOut ([indexPre,indexAssert,indxFn][{indexPreconditionRequire},{indexPreconditionAssert},{indexFunction}]) desde state \n{i_state}\n al state \n{f_state}\n con la función '{functions[indexFunction]}'")
        process = psutil.Process(proc.pid)
        for proc in process.children(recursive=True):
            proc.kill()
        process.kill()
        process.wait(2) # wait for killing subprocess
        
    
    
    total_query_time = end - init

    if FAIL_TO:
        return ADD_TX_IF_TIMEOUT,"?", (QUERY_TYPE, FAIL_TO, False, total_query_time) # Si tiró timeout, retorno False.
    
    output_verisol = str(result[0].decode('utf-8'))
    output_successful = "Formal Verification successful"

    
    # if verbose:
    #   print(output_verisol)

    if not tool_output in output_verisol and not output_successful in output_verisol:
        print(f"Fail running VeriSol:\n{output_verisol}")
    
    #Corral can "fail"
    output_error = "Corral may have aborted abnormally"
    if output_error in output_verisol:
        if not trackAllVars:
            return False,TRACK_VARS, (QUERY_TYPE, FAIL_TO, "fail_corral_no_trackAllVars", total_query_time)
        else:
            return ADD_TX_IF_FAIL,"fail?", (QUERY_TYPE, FAIL_TO, "fail_corral_with_trackAllVars", total_query_time) # if corral fails with trackvars, we don't know if it's a real counterexample or not
        
    feasible = tool_output in output_verisol
    return feasible, "", (QUERY_TYPE, FAIL_TO, feasible, total_query_time)




class PASCo:
    def __init__(self, configFile, mode, txBound, time_out, folder_store_results, verbose, reduceStates, reduceTrue, reduceEqual, trackAllVars, max_cores):
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
        self.TRACK_VARS = "trackAllVars"
        self.tool_output = "Found a counterexample"
        self.statesNames = []
        
        self.config = __import__(self.configFile)
        self.fileName = os.path.join("Contracts", self.config.fileName)
        self.functions = self.config.functions
        self.contractName = self.config.contractName
        self.functionVariables = self.config.functionVariables
        self.functionPreconditions = self.config.functionPreconditions
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
            print(f"time_out in config ignored. Using time_out={str(self.time)}")
        except Exception:
            try:
                self.time_out = float(self.config.time_out)
            except Exception:
                self.time_out = 600.0
        
        self.SAVE_GRAPH_PATH = f"{folder_store_results}/k_"+str(self.txBound)+"/to_"+str(int(self.time_out))+"/"
        self.NO_UNKNOWN_TX = "_no_unknown_tx"

        # print the configuration
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
        

    def run(self):
        for current_mode in self.modes:
            init = time.time()
            if current_mode == Mode.epa.value:
                current_mode = Mode.epa
            if current_mode == Mode.states.value:
                current_mode = Mode.states
            self.run_mode(current_mode)
        
            end = time.time()

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

    
    def run_mode(self, mode):
        print()
        print(f"STARTING RUN IN MODE: {mode}")
        self.query_list = [] # (Type,TO?,feasible,time(sec)) for each query to verisol
        self.dict_nodes_edges = {}
        self.dict_nodes_edges['nodes'] = []
        self.dict_nodes_edges['edges'] = []

        if mode == Mode.states:
            self.statesNames = self.config.statesNamesModeState
            self.statePreconditionsModeState = self.config.statePreconditionsModeState
            self.statesModeState = self.config.statesModeState
        if mode == Mode.epa:
            self.statePreconditions = self.config.statePreconditions


        count = len(self.functions)
        #lista de numeros de 1 a N, donde N es la cantidad de funciones
        funcionesNumeros = list(range(1, count + 1))
        
        
        extraConditions = []
        countPreInitial = 0
        countPreFinal = 0

        if mode == Mode.epa :
            #states tiene todos los posibles estados de acuerdo a las funciones habilitadas/no habilitadas
            states = self.getCombinations(funcionesNumeros)
            #preconditions tiene las precondiciones de cada estado, donde el indice i de preconditions es el estado i de states
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

        # Quiero que haya 1 metodo tipo query por archivo
        # si hay muchas queries en un archivo, por más que se use ignoreMethod, puede llegar a tardar mucho
        # para no cambiar tanto la implementación, vamos a tener un archivo por cada query
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
            # Otra alternativa
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

        dot = graphviz.Digraph(comment=self.fileName)
        for n in self.dict_nodes_edges['nodes']:
            dot.node(n[0], n[1])
        for e in self.dict_nodes_edges['edges']:
            dot.edge(e[0], e[1], label=str(e[2]))
                    
                    
        print("PROCESS ENDED\n")
        
        tempFileName = self.configFile.replace('Config','')
        tempFileName = tempFileName + "_" + str(mode)
        output_dot = self.SAVE_GRAPH_PATH + tempFileName
        dot.render(output_dot)
        # TODO: this is useful if timeout transitions would be considered and would keep a version of the graph clean
        # output_with_no_unknown_tx = SAVE_GRAPH_PATH + tempFileName + NO_UNKNOWN_TX
        # ret,removed_tx = remove_unknown_tx.remove_transitions(os.path.join(os.getcwd(), output_dot))
        # ret = "// Total removed tx for timeouts : " + str(removed_tx) + "\n" + ret
        # write_file = open(output_with_no_unknown_tx,'w')
        # write_file.write(ret)
        # write_file.close()

    def getCombinations(self, funcionesNumeros):
        indices_con_truePreconditions = []
        results = []
        statesTemp = []
        cantidad_funciones = len(funcionesNumeros)
        for index, statePrecondition in enumerate(self.statePreconditions):
            if statePrecondition == "true":
                indices_con_truePreconditions.append(index + 1)#se suma 1 porque funcionesNumeros empieza en 1

        # Combinations
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
            extraConditionOutput = "require("+condition+");\n"
        return extraConditionOutput 

    def output_transitions_function(self, preconditionRequire, function, preconditionAssert, functionIndex, extraConditionPre, extraConditionPost, mode):
        if mode == Mode.epa:
            precondictionFunction = self.functionPreconditions[functionIndex]
        else:
            precondictionFunction = "true"
        extraConditionOutputPre = self.get_extra_condition_output(extraConditionPre)
        extraConditionOutputPost = self.get_extra_condition_output(extraConditionPost)
        verisolFucntionOutput = "require("+preconditionRequire+");//require for initial state\nrequire("+precondictionFunction+");//require for parameter preconditions\n" + extraConditionOutputPre + function + "\n"  + "assert(!(" + preconditionAssert + " && " + extraConditionPost + "));//reach final state\n"
        return verisolFucntionOutput

    def output_init_function(self, preconditionAssert, extraCondition):
        extraConditionOutput = self.get_extra_condition_output(extraCondition)
        verisolFucntionOutput =  extraConditionOutput + "assert(!(" + preconditionAssert + "));\n"
        return verisolFucntionOutput

    def output_valid_state(self, preconditionRequire, extraCondition):
        extraConditionOutput = self.get_extra_condition_output(extraCondition)
        return "require("+preconditionRequire+");\n" + extraConditionOutput + "assert(false);\n"


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
        current_directory = os.getcwd()
        final_directory = os.path.join(current_directory, r'output'+str(index))
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
        inputfile = open(fileNameTemp, 'r').readlines()
        write_file = open(fileNameTemp,'w')
        for line in inputfile:
            write_file.write(line)
            if 'contract ' + self.contractName in line:
                    write_file.write(body)
        write_file.close()

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

    def get_valid_transitions_output(self, arg, preconditionsThread, preconditions, extraConditionsTemp, extraConditions, statesThread, mode):
        tempFunctionNames = []
        tempToolCommands = []
        tempDirectories = []
        try:
            for indexPreconditionRequire, preconditionRequire in enumerate(preconditionsThread):
                #TODO refactorizar esto, no tiene sentido que se pase el indexPreconditionRequire
                #busco el índice real de la precondición, preconditionsThread va a tener solo un elemento, por lo que indexPreconditionRequire siempre es 0
                for indexPreconditionAssert, preconditionAssert in enumerate(preconditions):
                    if str(preconditionRequire) == str(preconditionAssert):
                        indexPreconditionRequireReal = indexPreconditionRequire
                        break
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
                            # TODO ejecutar aca Verisol para cada fn?
                            dirname = str(arg)+"_"+functionName
                            final_directory = self.create_directory(dirname)
                            fileNameTemp = self.create_file(dirname, final_directory)
                            self.write_file(fileNameTemp, temp_function)
                            tool = f"VeriSol {fileNameTemp} {self.contractName}"
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
                tool = f"VeriSol {fileNameTemp} {self.contractName}"
                
                tempFunctionNames.append(functionName)
                tool_commands.append(tool)
                final_directories.append(final_directory)

            # Ejecutar en paralelo
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

    

    def add_node_to_graph(self, indexPreconditionRequire, indexPreconditionAssert, indexFunction, statesTemp, states, succes_by_to, mode):
        self.dict_nodes_edges['nodes'].append((self.combinationToString(statesTemp[indexPreconditionRequire]), output_combination(indexPreconditionRequire, statesTemp, mode, self.functions, self.statesNames)))
        self.dict_nodes_edges['nodes'].append((self.combinationToString(states[indexPreconditionAssert]), output_combination(indexPreconditionAssert, states, mode, self.functions, self.statesNames)))
        # dummy transitions are not added to the graph
        if not self.functions[indexFunction].startswith("dummy_"):
            self.dict_nodes_edges['edges'].append((self.combinationToString(statesTemp[indexPreconditionRequire]),self.combinationToString(states[indexPreconditionAssert]) , self.functions[indexFunction]+succes_by_to))


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
                tool = f"VeriSol {fileNameTemp} {self.contractName}"
                toolCommands.append(tool)
                tempFunctionNames.append(fuctionCombinations[0])
                final_directories.append(final_directory)
                preconditionsTempList.append(preconditionsTemp)
                statesTempList.append(statesTemp)
                extraConditionsTempList.append(extraConditionsTemp)
                
                
            # Ejecutar en paralelo
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
                #TODO refactorizar esto, simplificar ahora que se guarda un archivo por query                
                toolCommands, functionNames, directories = self.get_valid_transitions_output(arg, preconditionsTemp, preconditions, extraConditionsTemp, extraConditions, statesTemp, mode)
                tempToolCommands.extend(toolCommands)
                tempFunctionNames.extend(functionNames)
                tempDirectories.extend(directories)
                
                # se usa el mismo statesTemp para estas functionNames
                statesTempList.extend([statesTemp]*len(functionNames))
                # en args voy guardarndo un identificador para cada query
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

                    # Extiende `query_list` con los valores obtenidos
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
        """
        Ejecuta try_command en paralelo y actualiza las variables compartidas.

        Args:
            function_names (list): Lista de nombres de función a procesar.
            tool (str): Comando base de la herramienta.

        Returns:
            list: Resultados de las ejecuciones paralelas.
        """

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

                    # Extiende `query_list` con los valores obtenidos
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

    parser.add_argument(
        '--file',
        default='.',
        required=True,
        help='ConfigFile to run the tool. Example: HelloBlockchainConfig'
    )

    parser.add_argument(
        '--mode',
        default=[],
        choices=[Mode.epa.value, Mode.states.value],
        action='append',
        required=True,
        help='Mode to execute the tool. Options are "epa" and/or "states"'
    )

    parser.add_argument(
        '--txBound',
        required=False,
        default='.',
        help='parameter to bound the number of transactions. Default is 8'
    )

    parser.add_argument(
        '--time_out',
        required=False,
        default='.',
        help='parameter to bound the time of execution. Default is 600 seconds; 0 means no time out'
    )

    parser.add_argument(
        '--folder_store_results',
        required=False,
        default='graph',
        help='path to store the results. Default is stored in current_dir/graph'
    )

    parser.add_argument(
        '--verbose',
        required=False,
        default=False,
        help='Option to print extra information during abstraction generation'
    )

    parser.add_argument(
        '--reduceStates',
        required=False,
        default=True,
        help='optimization to discard states that are not reachable at a first stage'
    )

    parser.add_argument(
        '--reduceTrue',
        required=False,
        default=True,
        help='optimization to reduce states that has True as preconditions'
    )

    parser.add_argument(
        '--reduceEqual',
        required=False,
        default=True,
        help='optimization to reduce states that has the same preconditions'
    )

    parser.add_argument(
        '--trackAllVars',
        required=False,
        default=True,
        help='parameter to track all variables by corral. Default is True'
    )

    parser.add_argument(
        '--max_cores',
        required=False,
        default=os.cpu_count(),
        help='parameter to set the number of cores to use. Default is the number of cores in current computer'
    )


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
        max_cores=int(args.max_cores)
    )
    
    pasco.run()