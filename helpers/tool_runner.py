"""
Construcción y ejecución de los comandos que invocan VeriSol/Corral por
subprocess, y helpers de bajo nivel usados en ese flujo.

`try_command_task` y `try_command` se pasan directo a
`ProcessPoolExecutor.submit(...)` desde PASCo.py, así que deben seguir
siendo funciones de nivel de módulo (no métodos ni closures).
"""
import subprocess
import time
import platform
import psutil

from helpers.exceptions import Mode


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
                        tool_output, TRACK_VARS, return_output=False):
    result = try_command(tool, function_name, tempFunctionNames, final_directory, statesTemp,
                        txBound, time_out, trackAllVars, mode, functions,
                        statesNames, states, verbose, QUERY_TYPE, contractName,
                        tool_output, TRACK_VARS, return_output)
    if return_output:
        feasible, to_or_fail, query_values, output_verisol = result
    else:
        feasible, to_or_fail, query_values = result
        output_verisol = ""
    if to_or_fail == TRACK_VARS:
        result = try_command(tool, function_name, tempFunctionNames, final_directory, statesTemp,
                        txBound, time_out, True, mode, functions,
                        statesNames, states, verbose, QUERY_TYPE, contractName,
                        tool_output, TRACK_VARS, return_output)
        if return_output:
            feasible, to_or_fail, query_values, output_verisol = result
        else:
            feasible, to_or_fail, query_values = result
            output_verisol = ""
    if return_output:
        return feasible, to_or_fail, query_values, output_verisol
    return feasible, to_or_fail, query_values


def try_command(tool, temp_function_name, tempFunctionName, final_directory, statesTemp,
                txBound, time_out, trackAllVars, mode, functions,
                statesNames, states, verbose, QUERY_TYPE, contractName,
                tool_output, TRACK_VARS, return_output=False):
    ADD_TX_IF_TIMEOUT = False
    ADD_TX_IF_FAIL = False
    
    if len(statesTemp) > 0:
        indexPreconditionRequire, indexPreconditionAssert, indexFunction = get_params_from_function_name(temp_function_name)
        i_state = output_combination(indexPreconditionRequire, statesTemp, mode, functions, statesNames)
        f_state = output_combination(indexPreconditionAssert, states, mode, functions, statesNames)
        if functions[indexFunction].startswith("dummy_"):
            if i_state != f_state:
                return (False,"",(), "") if return_output else (False,"",())
            else:
                return (True,"",(), "") if return_output else (True,"",())
    
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
        else:
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
        process.wait(2)
        
    
    total_query_time = end - init

    if FAIL_TO:
        query_values = (QUERY_TYPE, FAIL_TO, False, total_query_time)
        return (ADD_TX_IF_TIMEOUT,"?", query_values, "") if return_output else (ADD_TX_IF_TIMEOUT,"?", query_values)
    
    if isinstance(result, subprocess.CompletedProcess):
        output_verisol = result.stdout.decode("utf-8")
    else:
        output_verisol = result[0].decode("utf-8")

    output_successful = "Formal Verification successful"

    if not tool_output in output_verisol and not output_successful in output_verisol:
        print(f"Fail running VeriSol:\n{output_verisol}")
    
    output_error = "Corral may have aborted abnormally"
    # Si el contraejemplo ya está en el output, el abort de Corral es irrelevante:
    # no hay que pisar un feasible=True real con un "fail" forzado.
    if output_error in output_verisol and tool_output not in output_verisol:
        if not trackAllVars:
            query_values = (QUERY_TYPE, FAIL_TO, "fail_corral_no_trackAllVars", total_query_time)
            return (False, TRACK_VARS, query_values, output_verisol) if return_output else (False, TRACK_VARS, query_values)
        else:
            query_values = (QUERY_TYPE, FAIL_TO, "fail_corral_with_trackAllVars", total_query_time)
            return (ADD_TX_IF_FAIL, "fail?", query_values, output_verisol) if return_output else (ADD_TX_IF_FAIL, "fail?", query_values)

    feasible = tool_output in output_verisol
    query_values = (QUERY_TYPE, FAIL_TO, feasible, total_query_time)
    return (feasible, "", query_values, output_verisol) if return_output else (feasible, "", query_values)

