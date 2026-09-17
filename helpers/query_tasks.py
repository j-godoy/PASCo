"""
Construcción de queries individuales (require/assert) y tareas de análisis
de edges (Must/May/HyperMust). `analyze_single_edge_task` y
`check_hypermust_for_group` se pasan directo a
`ProcessPoolExecutor.submit(...)` desde PASCo.py, así que deben seguir
siendo funciones de nivel de módulo.
"""
import os
import shutil
import uuid
import re
import itertools
import traceback

from helpers.exceptions import Mode, RepeatedCounterexampleError, CouldNotExtractCounterexampleError
from helpers.tool_runner import try_command_task
from helpers.counterexamples import (
    extract_concrete_counterexample,
    _inject_check_state,
    _has_function_definition,
    _insert_body_into_contract,
    _build_check_state_call,
)


# ---------------------------------------------------------------------------
# Helpers compartidos por analyze_single_edge_task y check_hypermust_for_group
# ---------------------------------------------------------------------------

def _require_line(condition, trailing_comment=""):
    """
    Construye una línea `require(condition);` (con un comentario opcional
    al final, p.ej. "//QUERY_MUST: ..."), para insertar en el .sol
    temporal armado para cada query.

    Si `condition` es exactamente "true" (no hay ninguna precondición real
    que imponer ahí), en vez de emitir `require(true);` se emite la misma
    línea pero COMENTADA (`//require(true);...`). Un `require(true);`
    trivial puede hacer que VeriSol/Corral aborte de forma anómala en
    algunos casos, así que se comenta para evitar el problema sin perder
    rastro de qué precondición hubiera ido ahí.
    """
    line = f"require({condition});"
    if str(condition).strip() == "true":
        line = "//" + line
    return line + trailing_comment + "\n"

def _get_extra_condition_output(condition):
    if condition and condition.strip():
        return _require_line(condition.strip())
    return ""

def _functionOutput(func_name, functionVariables):
    return f"function vc{func_name}({functionVariables}) payable public {{"

def _safe_query_label(label, max_len=100):
    safe = re.sub(r"[^0-9A-Za-z_]", "_", str(label))
    safe = re.sub(r"_+", "_", safe).strip("_")
    if not safe:
        safe = "query"
    if safe[0].isdigit():
        safe = "q_" + safe
    if len(safe) > max_len:
        safe = safe[:max_len].rstrip("_") + "_" + uuid.uuid4().hex[:8]
    return safe

def _run_query_local(query_body, query_label, QUERY_TYPE,
                     fileName, contractName, functionVariables,
                     functions, statesNames, txBound, time_out,
                     trackAllVars, verbose, tool_output, TRACK_VARS,
                     counterexample_specs=None, save_graph_path=None):
    """
    Escribe un archivo .sol temporal con query_body, lo ejecuta con VeriSol
    y retorna (feasible, to_or_fail, query_list_local, output_verisol).

    Si se proveen counterexample_specs, inyecta check_state en el .sol
    para que VeriSol exponga el estado concreto en el trace.
    """
    base_directory = save_graph_path if save_graph_path else os.getcwd()
    unique_suffix = uuid.uuid4().hex[:8]
    safe_label = _safe_query_label(query_label)
    dirname = f"_must_{safe_label}_{unique_suffix}"
    final_directory = os.path.join(base_directory, f"output{dirname}")
    os.makedirs(final_directory, exist_ok=True)
    query_list_local = []
    try:
        fileNameTemp = os.path.join(final_directory, f"OutputTemp{dirname}.sol")
        if os.path.isfile(fileNameTemp):
            os.remove(fileNameTemp)
        shutil.copyfile(fileName, fileNameTemp)

        func_name = safe_label
        body = _functionOutput(func_name, functionVariables) + "\n" + query_body + "}\n"
        _insert_body_into_contract(fileNameTemp, contractName, body)

        # Inyectar check_state sobre el archivo final que se va a pasar a VeriSol.
        if counterexample_specs:
            _inject_check_state(fileNameTemp, contractName, counterexample_specs)
            with open(fileNameTemp, "r") as f:
                final_source = f.read()
            expected_func = f"check_state_{contractName}"
            if not _has_function_definition(final_source, expected_func):
                raise RuntimeError(f"{expected_func} was not injected into {fileNameTemp}")

        tool = f"VeriSol {os.path.basename(fileNameTemp)} {contractName}"
        feasible, to_or_fail, query_values, output_verisol = try_command_task(
            func_name, [func_name], tool, final_directory, [],
            txBound, time_out, trackAllVars, Mode.epa,
            functions, statesNames, [], verbose,
            QUERY_TYPE, contractName, tool_output, TRACK_VARS,
            return_output=True,
        )
        if query_values:
            query_list_local.append(query_values)
        return feasible, to_or_fail, query_list_local, output_verisol
    except Exception as e:
        traceback.print_exc()
        print(f"Error in _run_query_local ({query_label}): {e}")
        return False, "error", query_list_local, ""
    finally:
        if not verbose:
            try:
                shutil.rmtree(final_directory)
            except Exception:
                pass

def analyze_single_edge_task(edge, preconditions, extraConditions, functions, functionPreconditions,
                            functionVariables, contractName, fileName, txBound, time_out,
                            trackAllVars, verbose, tool_output, TRACK_VARS, statesNames,
                            counterexampleSpecs=None, N=4, save_graph_path=None):
    """
    Analiza un único edge para determinar si es Must o May.

    Cambio respecto a la versión anterior: los contraejemplos ya no son
    negaciones de la precondición fuente (require(!(precond_src))), sino
    negaciones de estados CONCRETOS extraídos del trace de VeriSol:

        require(!(x == 12 && state == 0 && owner == address(4)));

    Esto hace que la exclusión sea mucho más precisa y que el loop converja
    correctamente hacia Must o May.
    """
    def output_enabledness_function_local(preconditionRequire, functionIndex, extraConditionPre):
        pre_f = functionPreconditions[functionIndex]
        extra = _get_extra_condition_output(extraConditionPre)
        return (
            _require_line(preconditionRequire, "//QUERY_ENABLEDNESS: require initial state")
            + extra
            + f"assert({pre_f});//QUERY_ENABLEDNESS: function must be enabled\n"
        )

    def output_must_function_local(preconditionRequire, function, preconditionAssert,
                                   functionIndex, extraConditionPre, extraConditionPost,
                                   concrete_cexamples):
        """
        Construye el cuerpo de la query MUST.

        concrete_cexamples: lista de expresiones concretas del tipo
            "x == 12 && state == 0 && owner == address(4)"
        Cada una se excluye con require(!(expr)).
        """
        pre_f = functionPreconditions[functionIndex]
        extra_pre = _get_extra_condition_output(extraConditionPre)
        check_state_call = _build_check_state_call(counterexampleSpecs, contractName, "QUERY_MUST")
        cex_requires = "".join(
            f"require(!({c})); //QUERY_MUST: exclude concrete counterexample\n"
            for c in concrete_cexamples
        )
        cex_asserts = "".join(
            f"assert(!({c})); //momentaneo\n"
            for c in concrete_cexamples
        )
        return (
            _require_line(preconditionRequire, "//QUERY_MUST: require initial state")
            + _require_line(pre_f, "//QUERY_MUST: require function precondition")
            + cex_requires
            + extra_pre
            + check_state_call
            + function + "\n"
            + cex_asserts
            + f"assert({preconditionAssert} && {extraConditionPost.strip() or 'true'});//QUERY_MUST: must reach dest\n"
        )

    def output_may_function_local(preconditionRequire, function, preconditionAssert,
                                   functionIndex, extraConditionPre, extraConditionPost,
                                   concrete_cexample):
        """
        Construye el cuerpo de la query MAY.

        concrete_cexample: expresión concreta del tipo
            "x == 12 && state == 0 && owner == address(4)"
        Se usa como require(expr) para fijar ese estado concreto.
        """
        pre_f = functionPreconditions[functionIndex]
        extra_pre = _get_extra_condition_output(extraConditionPre)
        check_state_call = _build_check_state_call(counterexampleSpecs, contractName, "QUERY_MAY")
        return (
            _require_line(preconditionRequire, "//QUERY_MAY: require initial state")
            + _require_line(pre_f, "//QUERY_MAY: require function precondition")
            + _require_line(concrete_cexample, "//QUERY_MAY: fix concrete counterexample state")
            + extra_pre
            + check_state_call
            + function + "\n"
            + f"assert(!({preconditionAssert}));//QUERY_MAY: must NOT reach dest from counterexample\n"
        )

    def run_query(query_body, query_label, QUERY_TYPE, inject_check_state=False):
        specs = counterexampleSpecs if inject_check_state else None
        return _run_query_local(
            query_body, query_label, QUERY_TYPE,
            fileName, contractName, functionVariables,
            functions, statesNames, txBound, time_out,
            trackAllVars, verbose, tool_output, TRACK_VARS,
            counterexample_specs=specs,
            save_graph_path=save_graph_path,
        )

    # --- Lógica principal del edge ---
    if len(edge) == 3:
        return edge, None, []

    src_str, dst_str, func_label, _isMust, idx_src, idx_dst, idx_func = edge
    query_list_local = []

    precondition_src = preconditions[idx_src]
    precondition_dst = preconditions[idx_dst]
    extra_src        = extraConditions[idx_src] if len(extraConditions) > idx_src else ""
    extra_dst        = extraConditions[idx_dst] if len(extraConditions) > idx_dst else ""
    function_call    = functions[idx_func]
    func_name_clean  = function_call.replace("(", "").replace(")", "").replace(";", "").strip()

    print(f"\n  [parallel] Analyzing edge: {func_name_clean}  {src_str} -> {dst_str}")

    # Paso 0: QUERY_ENABLEDNESS
    label_en = f"EN_{func_name_clean}_{src_str}"
    cex_found, to_fail, qv, _output_verisol = run_query(
        output_enabledness_function_local(precondition_src, idx_func, extra_src),
        label_en, "QUERY_ENABLEDNESS"
    )
    query_list_local.extend(qv)
    is_enabled = not cex_found

    if not is_enabled:
        print(f"    [parallel] ENABLEDNESS failed -> May  ({func_name_clean} {src_str}->{dst_str})")
        return edge, False, query_list_local

    # Loop principal MUST / MAY
    # concrete_cexamples acumula expresiones del tipo "x == 12 && state == 0 && ..."
    concrete_cexamples = []
    result_must = False
    loop_exhausted = True

    for k in range(N):
        print("k: ", k)
        print()
        # --- QUERY_MUST: ¿siempre llegamos al destino (excluyendo los cex concretos)? ---
        label_must = f"MUST_{func_name_clean}_{src_str}_to_{dst_str}_k{k}"
        cex_found_must, to_fail_must, qv, output_verisol_must = run_query(
            output_must_function_local(precondition_src, function_call, precondition_dst,
                                       idx_func, extra_src, extra_dst, concrete_cexamples),
            label_must, "QUERY_MUST",
            inject_check_state=bool(counterexampleSpecs),  # inyectar check_state solo si hay specs
        )
        query_list_local.extend(qv)

        if not cex_found_must:
            # Sin contraejemplo -> Must confirmado
            print(f"    [parallel] QUERY_MUST passed (k={k}) -> Must  ({func_name_clean} {src_str}->{dst_str})")
            result_must = True
            loop_exhausted = False
            break

        # VeriSol encontró un contraejemplo: intentar extraer el estado concreto
        new_cex_expr = extract_concrete_counterexample(output_verisol_must, counterexampleSpecs)

        if new_cex_expr is None:
            # No se pudo extraer un estado concreto. Como el algoritmo parte de
            # May, si no podemos refinar con otro contraejemplo, queda May.
            print(
                f"    [parallel] Could not extract concrete counterexample; "
                f"keeping edge as May."
            )
            result_must = False
            loop_exhausted = False
            raise CouldNotExtractCounterexampleError("No se pudo extraer el contraejemplo")
            # break
        elif new_cex_expr in concrete_cexamples:
            if k < N - 1:
                raise RepeatedCounterexampleError(
                    f"Contraejemplo repetido en k={k} (de N={N}) para el edge "
                    f"{func_name_clean} {src_str}->{dst_str}: {new_cex_expr!r} "
                    f"ya estaba en concrete_cexamples. Repetido antes de agotar "
                    f"las iteraciones permitidas -> posible falla de exclusión "
                    f"o de granularidad de counterexampleSpecs."
                )
            print(f"    [parallel] Repeated concrete counterexample; keeping edge as May.")
            result_must = False
            loop_exhausted = False
            break
        else:
            print(f"    [parallel] Concrete counterexample (k={k}): {new_cex_expr}")

        # --- QUERY_MAY: ¿desde ese estado concreto se puede NO llegar al destino? ---
        label_may = f"MAY_{func_name_clean}_{src_str}_to_{dst_str}_k{k}"
        cex_found_may, to_fail_may, qv, _output_verisol_may = run_query(
            output_may_function_local(precondition_src, function_call, precondition_dst,
                                      idx_func, extra_src, extra_dst, new_cex_expr),
            label_may, "QUERY_MAY",
            inject_check_state=bool(counterexampleSpecs),
        )
        query_list_local.extend(qv)

        if not cex_found_may:
            # No hay contraejemplo en MAY para este estado; no se pudo refinar.
            print(f"    [parallel] QUERY_MAY found no counterexample (k={k}) -> May  ({func_name_clean} {src_str}->{dst_str})")
            result_must = False
            loop_exhausted = False
            break

        print(f"    [parallel] QUERY_MAY found counterexample (k={k}); excluding state and continuing.")

        # Acumular el contraejemplo concreto para la siguiente iteración MUST
        concrete_cexamples.append(new_cex_expr)
        # print(concrete_cexamples)
        print()

    if loop_exhausted:
        print(f"    [parallel] Loop exhausted (N={N}) -> Must-Unknown  ({func_name_clean} {src_str}->{dst_str})")
        result_must = True # TODO: Must-Unknown (otro color)

    return edge, result_must, query_list_local

def check_hypermust_for_group(group_edges, preconditions, extraConditions, functions,
                               functionPreconditions, functionVariables, contractName,
                               fileName, txBound, time_out, trackAllVars, verbose,
                               tool_output, TRACK_VARS, statesNames, save_graph_path=None):
    """
    Dado un grupo de edges may que comparten (src_str, func_label, idx_src, idx_func),
    busca si alguna combinación de sus destinos forma una hypermust.
    """

    def output_hypermust_function(precondition_src, function_call, dest_preconditions,
                                   functionIndex, extra_src):
        pre_f = functionPreconditions[functionIndex]
        extra_pre = _get_extra_condition_output(extra_src)
        disjunction = " || ".join(f"({p})" for p in dest_preconditions)
        return (
            _require_line(precondition_src, "//QUERY_HYPERMUST: require initial state")
            + _require_line(pre_f, "//QUERY_HYPERMUST: require function precondition")
            + extra_pre
            + function_call + "\n"
            + f"assert({disjunction});//QUERY_HYPERMUST: must reach one of the dest states\n"
        )

    def run_query(query_body, query_label):
        return _run_query_local(
            query_body, query_label, "QUERY_HYPERMUST",
            fileName, contractName, functionVariables,
            functions, statesNames, txBound, time_out,
            trackAllVars, verbose, tool_output, TRACK_VARS,
            save_graph_path=save_graph_path,
        )

    if len(group_edges) < 2:
        return False, None, []

    src_str, _, func_label, _, idx_src, _, idx_func = group_edges[0]
    precondition_src = preconditions[idx_src]
    extra_src        = extraConditions[idx_src] if len(extraConditions) > idx_src else ""
    function_call    = functions[idx_func]
    func_name_clean  = function_call.replace("(", "").replace(")", "").replace(";", "").strip()

    destinations = []
    for e in group_edges:
        _, dst_str, _, _, _, idx_dst, _ = e
        destinations.append((dst_str, preconditions[idx_dst]))

    query_list_all = []
    n_dests = len(destinations)

    print(f"\n  [hypermust] Checking hypermust for: {func_name_clean}  {src_str} -> "
          f"{[d[0] for d in destinations]}")

    for combo_size in range(2, n_dests + 1):
        for combo_indices in itertools.combinations(range(n_dests), combo_size):
            dest_preconditions = [destinations[i][1] for i in combo_indices]
            dest_names         = [destinations[i][0] for i in combo_indices]
            combo_label        = "_".join(dest_names)

            label = f"HM_{func_name_clean}_{src_str}_to_{combo_label}"
            if len(label) > 120:
                label = label[:120] + "_" + uuid.uuid4().hex[:4]

            query_body = output_hypermust_function(
                precondition_src, function_call, dest_preconditions,
                idx_func, extra_src
            )

            cex_found, to_or_fail, qv, _output_verisol = run_query(query_body, label)
            query_list_all.extend(qv)

            if not cex_found:
                print(f"    [hypermust] CONFIRMED HyperMust: {func_name_clean}  "
                      f"{src_str} -> {{{', '.join(dest_names)}}}")
                return True, list(combo_indices), query_list_all
            else:
                print(f"    [hypermust] combo {dest_names} -> NOT hypermust (counterexample found)")

    print(f"    [hypermust] No hypermust found for {func_name_clean} {src_str}")
    return False, None, query_list_all



