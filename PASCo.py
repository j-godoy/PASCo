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
import concurrent.futures
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import Manager, Process
import traceback



def getCombinations(funcionesNumeros):
    global statePreconditions
    indices_con_truePreconditions = []
    results = []
    statesTemp = []
    cantidad_funciones = len(funcionesNumeros)
    for index, statePrecondition in enumerate(statePreconditions):
        if statePrecondition == "true":
            indices_con_truePreconditions.append(index + 1)#se suma 1 porque funcionesNumeros empieza en 1

    # Combinations
    for L in range(len(funcionesNumeros) + 1):
        for subset in itertools.combinations(funcionesNumeros, L):
            if reducedTrue:
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
    
    if not(reducedEqual):
        for combination in statesTemp:
            isCorrect = True
            for iNumber, number in enumerate(combination):
                for idx, x in enumerate(statePreconditions):
                    if iNumber != idx:
                        if number == 0:
                            if statePreconditions[iNumber] == x and combination[idx] != 0:
                                isCorrect = False
                        elif statePreconditions[iNumber] == x and not((idx+1) in combination):
                            isCorrect = False
            
            if isCorrect:
                statesTemp2.append(combination)
    else:
        statesTemp2 = statesTemp       
    return statesTemp2

def getPreconditions(funcionesNumeros):
    global states, statePreconditions
    preconditions = []
    for result in states:
        precondition = ""
        for number in funcionesNumeros:
            if precondition != "":
                precondition += " && "
            if number in result:
                precondition += statePreconditions[number-1]
            else:
                precondition += "!(" + statePreconditions[number-1] + ")"
        preconditions.append(precondition)
    return preconditions

def combinationToString(combination):
    output = ""
    for i in combination:
        output += str(i) + "-"
    return output

def functionOutput(number, functionVariables):
    return "function vc" + number + "(" + functionVariables + ") payable public {"

def getToolCommand(includeNumber, toolCommand, combinations, txBound, trackAllVars, contractName):
    command = toolCommand + " " 
    command = command + "/txBound:" + str(txBound) + " "
    command = command + "/noPrf "
    if trackAllVars:
        command = command + "/trackAllVars"+ " "
    for indexCombination, combi in enumerate(combinations):
        if combi != includeNumber: 
            command += "/ignoreMethod:vc"+ combi +"@" + contractName + " "
    # print(command)
    return command

def get_extra_condition_output(condition):
    extraConditionOutput = ""
    if condition != "" and condition != None:
        extraConditionOutput = "require("+condition+");\n"
    return extraConditionOutput 

def output_transitions_function(preconditionRequire, function, preconditionAssert, functionIndex, extraConditionPre, extraConditionPost, mode, functionPreconditions):
    if mode == Mode.epa:
        precondictionFunction = functionPreconditions[functionIndex]
    else:
        precondictionFunction = "true"
    extraConditionOutputPre = get_extra_condition_output(extraConditionPre)
    extraConditionOutputPost = get_extra_condition_output(extraConditionPost)
    verisolFucntionOutput = "require("+preconditionRequire+");//requiere para estado inicial\nrequire("+precondictionFunction+");//require para precondición de parámetros\n" + extraConditionOutputPre + function + "\n"  + "assert(!(" + preconditionAssert + "&& " + extraConditionPost + "));//Llego a estado final\n"
    return verisolFucntionOutput

def output_init_function(preconditionAssert, extraCondition):
    extraConditionOutput = get_extra_condition_output(extraCondition)
    verisolFucntionOutput =  extraConditionOutput + "assert(!(" + preconditionAssert + "));\n"
    return verisolFucntionOutput

def output_valid_state(preconditionRequire, extraCondition):
    extraConditionOutput = get_extra_condition_output(extraCondition)
    return "require("+preconditionRequire+");\n" + extraConditionOutput + "assert(false);\n"

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

def print_combination(indexCombination, tempCombinations, mode, functions, statesNames):
    output = output_combination(indexCombination, tempCombinations, mode, functions, statesNames)
    if basic_mode == False:
        if verbose:
            print(output + "---------")

def print_output(indexPreconditionRequire, indexFunction, indexPreconditionAssert, combinations, fullCombination, succes_by_to, mode, functions, statesNames, basic_mode):
    output ="Desde este estado:\n"+ output_combination(indexPreconditionRequire, combinations, mode, functions, statesNames) + "\nHaciendo " + str(functions[indexFunction]+succes_by_to) + "\n\nLlegas al estado:\n" + output_combination(indexPreconditionAssert, fullCombination, mode, functions, statesNames) + "\n---------"
    if verbose or succes_by_to != "":
        print(output)

def create_directory(index):
    current_directory = os.getcwd()
    final_directory = os.path.join(current_directory, r'output'+str(index))
    if not os.path.exists(final_directory):
        os.makedirs(final_directory)
    return final_directory

def create_directory_base(name):
    current_directory = os.getcwd()
    final_directory = os.path.join(current_directory, name)
    if not os.path.exists(final_directory):
        os.makedirs(final_directory)
    return final_directory

def delete_directory(final_directory):
    try:
        shutil.rmtree(final_directory)
    except Exception as e:
        print("Excepción al querer borrar carpeta: " + str(e))

def create_file(index, final_directory, fileName):
    fileNameTemp = "OutputTemp"+str(index)+".sol"
    fileNameTemp = os.path.join(final_directory, fileNameTemp)
    if os.path.isfile(fileNameTemp):
        os.remove(fileNameTemp)
    shutil.copyfile(fileName, fileNameTemp)
    return fileNameTemp

def create_file_base(final_directory, name):
    global contractName, fileName
    fileNameTemp = os.path.join(final_directory, name)
    if os.path.isfile(fileNameTemp):
        os.remove(fileNameTemp)
    shutil.copyfile(fileName, fileNameTemp)
    return fileNameTemp

def write_file(fileNameTemp, body, contractName):
    inputfile = open(fileNameTemp, 'r').readlines()
    write_file = open(fileNameTemp,'w')
    for line in inputfile:
        write_file.write(line)
        if 'contract ' + contractName in line:
                write_file.write(body)
    write_file.close()

def get_valid_preconditions_output(preconditions, extraConditions, functionVariables):
    temp_output = ""
    tempFunctionNames = []
    for indexPreconditionRequire, preconditionRequire in enumerate(preconditions):
        functionName = get_temp_function_name(indexPreconditionRequire, "0", "0")
        tempFunctionNames.append(functionName)
        temp_function = functionOutput(functionName, functionVariables) + "\n"
        temp_function += output_valid_state(preconditionRequire, extraConditions[indexPreconditionRequire])
        temp_output += temp_function + "}\n"
    return temp_output, tempFunctionNames

def get_valid_transitions_output(arg, preconditionsThread, preconditions, extraConditionsTemp, extraConditions, functions, statesThread, contractName, mode, statesNames, functionVariables, functionPreconditions, fileName, basic_mode, txBound, time_out, verbose, query_list, QUERY_TYPE, states, dot, tool_output, trackAllVars):
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
                for indexFunction, function in enumerate(functions):
                    extraConditionPre = extraConditionsTemp[indexPreconditionRequire]
                    extraConditionPost = extraConditions[indexPreconditionAssert]
                    if ((indexFunction + 1) in statesThread[indexPreconditionRequire] and mode == Mode.epa) or (mode == Mode.states):
                        functionName = get_temp_function_name(indexPreconditionRequireReal, indexPreconditionAssert, indexFunction)
                        tempFunctionNames.append(functionName)
                        temp_function = functionOutput(functionName, functionVariables) + "\n"
                        temp_function += output_transitions_function(preconditionRequire, function, preconditionAssert, indexFunction, extraConditionPre, extraConditionPost, mode, functionPreconditions)
                        temp_function += "}\n"
                        # TODO ejecutar aca Verisol para cada fn?
                        dirname = str(arg)+"_"+functionName
                        final_directory = create_directory(dirname)
                        fileNameTemp = create_file(dirname, final_directory, fileName)
                        write_file(fileNameTemp, temp_function, contractName)
                        tool = "VeriSol " + fileNameTemp + " " + contractName
                        tempToolCommands.append(tool)
                        tempDirectories.append(final_directory)
    except Exception as e:
        print(f"Error en get_valid_transitions_output {arg}: {e}")
        traceback.print_exc()
    return tempToolCommands, tempFunctionNames, tempDirectories

def get_init_output(indexPreconditionAssert, preconditionAssert, extraConditions, functionVariables): 
    temp_output = ""
    functionName = get_temp_function_name(indexPreconditionAssert, "0" , "0")
    temp_function = functionOutput(functionName, functionVariables) + "\n"
    temp_function += output_init_function(preconditionAssert, extraConditions[indexPreconditionAssert])
    temp_output += temp_function + "}\n"
    return functionName, temp_output


def try_init(states, mode, functions, statesNames, extraConditions, contractName, preconditions, functionVariables, functionPreconditions, fileName, basic_mode, txBound, time_out, verbose, query_list, QUERY_TYPE, dot, tool_output, trackAllVars, TRACK_VARS, thread_workers):
    try:
        tempFunctionNames = []
        tool_commands = []
        final_directories = []
        txBound_constructor = 1
        indexPreconditionAssertMap = {}
        for indexPreconditionAssert, preconditionAssert in enumerate(preconditions):
            functionName, body = get_init_output(indexPreconditionAssert, preconditionAssert, extraConditions, functionVariables)
            indexPreconditionAssertMap[functionName] = indexPreconditionAssert
            dirname = f"_init_{indexPreconditionAssert}_{functionName}"
            final_directory = create_directory(dirname)
            fileNameTemp = create_file(dirname, final_directory, fileName)
            write_file(fileNameTemp, body, contractName)
            tool = f"VeriSol {fileNameTemp} {contractName}"
            
            tempFunctionNames.append(functionName)
            tool_commands.append(tool)
            final_directories.append(final_directory)

        # Ejecutar en paralelo
        results = execute_try_command_in_parallel(tool_commands, tempFunctionNames, final_directories, [], txBound_constructor,
                                              time_out, trackAllVars, mode, functions, statesNames,
                                              states, verbose, query_list, QUERY_TYPE, contractName,
                                              tool_output, TRACK_VARS, thread_workers)

        if len(results) != len(tempFunctionNames):
            print("long de results: ", len(results))
            print(results)
            print("long de tempFunctionNames: ", len(tempFunctionNames))
            print("Error: La longitud de resultados no coincide con los nombres de funciones.")
            traceback.print_exc()
            exit(1)


        for functionName, success, to_or_fail in results:
            if success:
                dot['nodes'].append(("init", "init"))
                dot['nodes'].append((combinationToString(states[indexPreconditionAssertMap[functionName]]), output_combination(indexPreconditionAssertMap[functionName], states, mode, functions, statesNames)))
                dot['edges'].append(("init", combinationToString(states[indexPreconditionAssertMap[functionName]]), f"constructor{to_or_fail}"))
        
        if not verbose:
            for final_directory in final_directories:
                delete_directory(final_directory)
    except Exception as e:
        print(f"Error en try_init: {e}")
        traceback.print_exc()


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
       print(command)
    
    result = ""
    FAIL_TO = False
    init = time.time()
    try:
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
        print(output_verisol)
    
    #Corral can "fail"
    output_error = "Corral may have aborted abnormally"
    if output_error in output_verisol:
        if not trackAllVars:
            return False,TRACK_VARS, (QUERY_TYPE, FAIL_TO, "fail_corral_no_trackAllVars", total_query_time)
        else:
            return ADD_TX_IF_FAIL,"fail?", (QUERY_TYPE, FAIL_TO, "fail_corral_with_trackAllVars", total_query_time) # if corral fails with trackvars, we don't know if it's a real counterexample or not
        
    feasible = tool_output in output_verisol
    return feasible, "", (QUERY_TYPE, FAIL_TO, feasible, total_query_time)

def execute_try_command_in_parallel_reduce(args, toolCommands, tempFunctionNames, final_directories, statesTemp, txBound,
                                    time_out, trackAllVars, mode, functions, statesNames,
                                    states, verbose, query_list, QUERY_TYPE, contractName,
                                    tool_output, TRACK_VARS, thread_workers):
    global number_to, number_corral_fail, number_corral_fail_with_tackvars
    
    results = []
    errors = []
    print(f"Executing {len(args)} tasks in parallel - execute_try_command_in_parallel_reduce")
    
    with ProcessPoolExecutor(max_workers=thread_workers) as executor:
        future_to_function = {executor.submit(try_command_task, fn, [], tool, final_directory, stateTemp,
                      txBound, time_out, trackAllVars, mode, functions,
                      statesNames, states, verbose, QUERY_TYPE, contractName,
                      tool_output, TRACK_VARS): (fn,arg) for arg, tool, fn, final_directory, stateTemp in zip(args, toolCommands, tempFunctionNames, final_directories, statesTemp)}

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
                    query_list.append(query_values)
            except Exception as e:
                traceback.print_exc()
                errors.append((function_name, e))
                print(f"Error en la tarea: {e}")

    if errors:
        print(f"Errores encontrados en {len(errors)} tareas: {errors}")
        exit(1)

    return results

def execute_try_command_in_parallel(toolCommands, tempFunctionNames, final_directories, statesTemp, txBound,
                                    time_out, trackAllVars, mode, functions, statesNames,
                                    states, verbose, query_list, QUERY_TYPE, contractName,
                                    tool_output, TRACK_VARS, thread_workers):
    global number_to, number_corral_fail, number_corral_fail_with_tackvars
    """
    Ejecuta try_command en paralelo y actualiza las variables compartidas.

    Args:
        function_names (list): Lista de nombres de función a procesar.
        tool (str): Comando base de la herramienta.
        Otros parámetros: Configuración necesaria para ejecutar `try_command`.

    Returns:
        list: Resultados de las ejecuciones paralelas.
    """

    results = []
    errors = []
    print("Iniciando ejecución execute_try_command_in_parallel con las siguientes funciones:", len(tempFunctionNames))
    with ProcessPoolExecutor(max_workers=thread_workers) as executor:
        future_to_function = {executor.submit(try_command_task, fn, [fn], tool, final_directory, statesTemp,
                                              txBound, time_out, trackAllVars, mode, functions,
                                              statesNames, states, verbose, QUERY_TYPE, contractName,
                                              tool_output, TRACK_VARS): fn for tool, fn, final_directory in zip(toolCommands, tempFunctionNames, final_directories)}
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
                    query_list.append(query_values)
            except Exception as e:
                traceback.print_exc()
                errors.append((function_name, e))
                print(f"Error en la tarea: {e}")

    if errors:
        print(f"Errores encontrados en {len(errors)} tareas: {errors}")
        exit(1)

    return results

def get_temp_function_name(indexPrecondtion, indexAssert, indexFunction):
    return str(indexPrecondtion) + "x" + str(indexAssert) + "x" + str(indexFunction)

def get_params_from_function_name(temp_function_name):
    array = temp_function_name.split('x')
    return int(array[0]), int(array[1]), int(array[2])

def add_node_to_graph(indexPreconditionRequire, indexPreconditionAssert, indexFunction, statesTemp, states, succes_by_to, mode, functions, statesNames, dot):
    dot['nodes'].append((combinationToString(statesTemp[indexPreconditionRequire]), output_combination(indexPreconditionRequire, statesTemp, mode, functions, statesNames)))
    dot['nodes'].append((combinationToString(states[indexPreconditionAssert]), output_combination(indexPreconditionAssert, states, mode, functions, statesNames)))
    # transiciones dummy no las agrego
    if not functions[indexFunction].startswith("dummy_"):
        dot['edges'].append((combinationToString(statesTemp[indexPreconditionRequire]),combinationToString(states[indexPreconditionAssert]) , functions[indexFunction]+succes_by_to))


def reduceCombinations(cant_preconditions, preconditionsThreads, statesThreads, extraConditionsThreads, fileName, functionVariables, contractName, basic_mode, txBound, time_out, mode, functions, statesNames, states, verbose, query_list, QUERY_TYPE, tool_output, TRACK_VARS, trackAllVars, thread_workers):
    print(f"Starting task reduceCombinations para estados = {cant_preconditions}")  # Agregar un print para ver qué se está ejecutando
    try:
        args = []
        toolCommands = []
        tempFunctionNames = []
        final_directories = []
        
        preconditionsTempList = []
        statesTempList = []
        extraConditionsTempList = []
        
        for arg in range(cant_preconditions):
            args.append(arg)
            preconditionsTemp = preconditionsThreads[arg]
            statesTemp = statesThreads[arg]
            extraConditionsTemp = extraConditionsThreads[arg]
            final_directory = create_directory(arg)
            fileNameTemp = create_file(arg, final_directory, fileName)
            body,fuctionCombinations = get_valid_preconditions_output(preconditionsTemp, extraConditionsTemp, functionVariables)
            write_file(fileNameTemp, body, contractName)
            tool = "VeriSol " + fileNameTemp + " " + contractName
            toolCommands.append(tool)
            tempFunctionNames.append(fuctionCombinations[0])
            final_directories.append(final_directory)
            preconditionsTempList.append(preconditionsTemp)
            statesTempList.append(statesTemp)
            extraConditionsTempList.append(extraConditionsTemp)
            
            
        # Ejecutar en paralelo
        results = execute_try_command_in_parallel_reduce(args,toolCommands, tempFunctionNames, final_directories, statesTempList, txBound,
                                                time_out, trackAllVars, mode, functions, statesNames,
                                                states, verbose, query_list, QUERY_TYPE, contractName,
                                                tool_output, TRACK_VARS, thread_workers)

        
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
                    i_state = output_combination(indexPreconditionRequire, statesTempList[i])
                    print(i_state)
        
            preconditionsThreads[i] = preconditionsTemp2
            statesThreads[i] = statesTemp2
            extraConditionsThreads[i] = extraConditionsTemp2
            
        if not verbose:
            for final_directory in final_directories:
                delete_directory(final_directory)
        
    except Exception as e:
        traceback.print_exc()
        print(f"Error en reduceCombinations: {e}")
        exit(1)

def validCombinations(cant_valid_states, preconditionsThreads, statesThreads, extraConditionsThreads, mode, functions, statesNames, extraConditions, contractName, preconditions, functionVariables, functionPreconditions, fileName, basic_mode, txBound, time_out, verbose, query_list, QUERY_TYPE, states, dot, tool_output, trackAllVars, TRACK_VARS, thread_workers):
    print(f"Starting task validCombinations para estados={cant_valid_states}")  # Agregar un print para ver qué se está ejecutando
    try:
        tempFunctionNames = []
        tempToolCommands = []
        tempDirectories = []
        statesTempList = []
        args = []
        cont = 0
        for arg in range(cant_valid_states):
            preconditionsTemp = preconditionsThreads[arg]
            statesTemp = statesThreads[arg]
            extraConditionsTemp = extraConditionsThreads[arg]
            #TODO refactorizar esto, simplificar ahora que se guarda un archivo por query
            toolCommands, functionNames, directories = get_valid_transitions_output(arg, preconditionsTemp, preconditions, extraConditionsTemp, extraConditions, functions, statesTemp, contractName, mode, statesNames, functionVariables, functionPreconditions, fileName, basic_mode, txBound, time_out, verbose, query_list, QUERY_TYPE, states, dot, tool_output, trackAllVars)
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
            
            
        
        if verbose:
            print(f"Procesando transacciones: {tempFunctionNames}")

        results = execute_try_command_in_parallel_reduce(args, tempToolCommands, tempFunctionNames, tempDirectories, statesTempList, txBound,
                                              time_out, trackAllVars, mode, functions, statesNames,
                                              states, verbose, query_list, QUERY_TYPE, contractName,
                                              tool_output, TRACK_VARS, thread_workers)

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
                add_node_to_graph(indexPreconditionRequire, indexPreconditionAssert, indexFunction, statesTempList[i], states, to_or_fail, mode, functions, statesNames, dot)
                if verbose:
                    print_output(indexPreconditionRequire, indexFunction, indexPreconditionAssert, statesTempList[i], states, to_or_fail, mode, functions, statesNames, dot)
        if not verbose:
            for final_directory in tempDirectories:
                delete_directory(final_directory)
    except Exception as e:
        traceback.print_exc()
        print(f"Error en validCombinations: {e}")
        exit(1)


class Mode(Enum):
    epa = "epa"
    states = "states"

def make_global_variables(config):
    global fileName, preconditions, dot, statesNames, functions, statePreconditions, contractName, functionVariables
    global functionPreconditions, txBound, time_out, statePreconditionsModeState, statesModeState, SAVE_GRAPH_PATH, NO_UNKNOWN_TX
    fileName = os.path.join("Contracts", config.fileName)
    print("Running file:",config.fileName)
    functions = config.functions
    statePreconditions = config.statePreconditions
    statesNames = config.statesNamesModeState
    contractName = config.contractName
    functionVariables = config.functionVariables
    functionPreconditions = config.functionPreconditions
    if txBound == None:
        txBound = config.txBound
    else:
        print("txBound en config ignorado. Usando parámetro txBound="+ str(txBound))
    if time_out == None:
        try:
            time_out = float(config.time_out)
        except Exception:
            time_out = 600.0
    else:
        print("time_out en config ignorado. Usando parámetro time_out="+ str(time_out))
    statePreconditionsModeState = config.statePreconditionsModeState
    statesModeState = config.statesModeState
    SAVE_GRAPH_PATH = "graph/k_"+str(txBound)+"/to_"+str(int(time_out))+"/"
    NO_UNKNOWN_TX = "_no_unknown_tx"

def main():
    global query_list, fileName, config, dot, preconditionsThreads, statesThreads, states, preconditions, extraConditionsThreads, extraConditions, SAVE_GRAPH_PATH, QUERY_TYPE
    make_global_variables(config)

    count = len(functions)
    #lista de numeros de 1 a N, donde N es la cantidad de funciones
    funcionesNumeros = list(range(1, count + 1))
    
    
    dot = graphviz.Digraph(comment=config.fileName)

    extraConditions = []
    countPreInitial = 0
    countPreFinal = 0

    if mode == Mode.epa :
        #states tiene todos los posibles estados de acuerdo a las funciones habilitadas/no habilitadas
        states = getCombinations(funcionesNumeros)
        #preconditions tiene las precondiciones de cada estado, donde el indice i de preconditions es el estado i de states
        preconditions = getPreconditions(funcionesNumeros)
        try:
            extraConditions = [config.epaExtraConditions for i in range(len(states))]
        except:
            extraConditions = ["true" for i in range(len(states))]
    else :
        preconditions = statePreconditionsModeState
        states = statesModeState
        try:
            extraConditions = config.statesExtraConditions
        except:
           extraConditions = ["true" for i in range(len(states))]
        
    tempDir = create_directory_base("temp")

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

    if basic_mode == False:
        print("Length")
        print(len(preconditions))
        

    tool_output = "Found a counterexample"
    
    # Pasar a parámetros
    TRACK_VARS = "trackAllVars"
    trackAllVars = True
    thread_workers = os.cpu_count()
    
    
    if mode == Mode.epa and not(reduced):
        print("Reducing combinations...")
        # Otra alternativa
        QUERY_TYPE = "QUERY_REDUCE_COMBINATION"
        reduceCombinations(cant_preconditions, preconditionsThreads, statesThreads, 
                            extraConditionsThreads, fileName, functionVariables, contractName, 
                            basic_mode, txBound, time_out, mode, functions, statesNames, 
                            states, verbose, query_list, QUERY_TYPE, tool_output, TRACK_VARS, trackAllVars, thread_workers)
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
    realThreadCount = len(preconditionsThreads)

    countPreFinal = len(preconditions)
    temp_dir = os.path.join(tempDir, configFile + "-" + str(mode) + ".txt")
    f = open(temp_dir, "w")
    f.write(str(countPreInitial) + "\n" + str(countPreFinal) + "\n" + str(len(functions)))
    f.close()

    if basic_mode == False:
        print("Length")
        print(len(preconditionsThreads))
    cant_valid_states = len(preconditionsThreads)
    preconditionsThreads = np.array_split(preconditionsThreads, cant_valid_states)
    statesThreads = np.array_split(statesThreads, cant_valid_states)
    extraConditionsThreads = np.array_split(extraConditionsThreads, cant_valid_states)

    QUERY_TYPE =  "QUERY_NORMAL"

    dict_nodes_edges = {}
    dict_nodes_edges['nodes'] = []
    dict_nodes_edges['edges'] = []
    
    
    validCombinations(cant_valid_states, preconditionsThreads, statesThreads, extraConditionsThreads, mode, functions, statesNames, extraConditions, contractName, preconditions, functionVariables, functionPreconditions, fileName, basic_mode, txBound, time_out, verbose, query_list, QUERY_TYPE, states, dict_nodes_edges, tool_output, trackAllVars, TRACK_VARS, thread_workers)
    print("FIN ValidCombinations")

    
    QUERY_TYPE = "QUERY_NORMAL_CONSTRUCTOR"
    
    try_init(states, mode, functions, statesNames, extraConditions, contractName, preconditions, functionVariables, functionPreconditions, fileName, basic_mode, txBound, time_out, verbose, query_list, QUERY_TYPE, dict_nodes_edges, tool_output, trackAllVars, TRACK_VARS, thread_workers)

    
    for n in dict_nodes_edges['nodes']:
        dot.node(n[0], n[1])
    for e in dict_nodes_edges['edges']:
        dot.edge(e[0], e[1], label=str(e[2]))
                
                
    print("ENDED")    
    
    tempFileName = configFile.replace('Config','')
    tempFileName = tempFileName + "_" + str(mode)
    output_dot = SAVE_GRAPH_PATH + tempFileName
    dot.render(output_dot)
    # output_with_no_unknown_tx = SAVE_GRAPH_PATH + tempFileName + NO_UNKNOWN_TX
    # ret,removed_tx = remove_unknown_tx.remove_transitions(os.path.join(os.getcwd(), output_dot))
    # ret = "// Total removed tx for timeouts : " + str(removed_tx) + "\n" + ret
    # write_file = open(output_with_no_unknown_tx,'w')
    # write_file.write(ret)
    # write_file.close()
    

states = []
preconditions = []
number_to = 0
number_corral_fail = 0
number_corral_fail_with_tackvars = 0

       
sys.path.append(os.path.join(os.getcwd(), "Configs"))

if __name__ == "__main__":
    global mode, config, verbose, time_mode, txBound, QUERY_TYPE, query_list
    txBound = None
    time_out = None
    init = time.time()
    epaMode = False
    statesMode = False
    
    configFile = sys.argv[1]
    verbose = False
    basic_mode = False
    
    query_list =[] # (Type,TO?,feasible,time(sec)) para cada query a verisol
    
    
    #TODO: ser consistente
    reduced = False
    reducedTrue = True
    reducedEqual = False
    for i in range(1, len(sys.argv)):
        if sys.argv[i] == "-v":
            verbose = True
        if sys.argv[i] == "-b":
            basic_mode = True
        if sys.argv[i] == "-e":
            epaMode = True
        if sys.argv[i] == "-s":
            statesMode = True
        if sys.argv[i] == "-a":
            statesMode = True
            epaMode = True
        if sys.argv[i] == "-default":
            reduced = False
            reducedTrue = True
            reducedEqual = False
        if sys.argv[i] == "-rs":
            reduced = True
        if sys.argv[i] == "-rt":
            reducedTrue = False
        if sys.argv[i] == "-re":
            reducedEqual = True
        if sys.argv[i] == "-rte":
            reducedEqual = True 
            reducedTrue = False       
        if sys.argv[i] == "-ra":
            reducedTrue = False
            reducedEqual = True
            reduced = True
        if "txbound=" in sys.argv[i]:
            txBound = int(sys.argv[i].replace("txbound=","").strip())
        if "time_out=" in sys.argv[i]:
            to = sys.argv[i].replace("time_out=","").strip()
            if to == "0":
                time_out = None
            else:
                time_out = float(to)
            
    
    if epaMode:
        mode = Mode.epa
        config = __import__(configFile)
        main()

    if statesMode:
        config = __import__(configFile, level=0)
        mode = Mode.states
        main()
    
    end = time.time()
    total_time = "Total time: {}".format(str(end-init))
    total_to = "# Time Out: {}".format(str(number_to))
    total_cfail1 = "# Corral Fail without trackvars: {}".format(str(number_corral_fail))
    total_cfail2 = "# Corral Fail with trackvars: {}".format(str(number_corral_fail_with_tackvars))
    
    print(total_time)
    print(total_to)
    print(total_cfail1)
    print(total_cfail2)
    tempFileName = configFile.replace('Config','')+"-"+str(mode)+".txt"
    with open(os.path.join(SAVE_GRAPH_PATH,tempFileName), 'w') as file:
        file.write("Subject: " + tempFileName.replace(".txt", "")+"\n")
        file.write(total_time+"\n")
        file.write(total_to+"\n")
        file.write(total_cfail1+"\n")
        file.write(total_cfail2+"\n")
        
    tempFileName = configFile.replace('Config','')+"-"+str(mode)+"_query_time.csv"
    with open(os.path.join(SAVE_GRAPH_PATH,tempFileName), 'w') as file:
        file.write("Type,TO?,feasible,time(sec)\n")
        for type, timeout, feasible, time_secs in query_list:
            file.write(f"{str(type)},{str(timeout)},{str(feasible)},{str(time_secs)}\n")