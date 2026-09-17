"""
Construcción e inyección de la función check_state en el .sol temporal, y
extracción de contraejemplos concretos a partir del trace de VeriSol.
"""
import re

from helpers.solidity_parser import _split_trace_arguments


def _normalize_counterexample_specs(specs):
    """
    Normaliza counterexampleVariables del config al formato interno:
        [{"state_var": str, "trace_param": str, "solidity_type": str, "value_map": dict, "enum_members": list?}, ...]

    Formatos aceptados en el config:
        - dict con claves state_var/stateVar/name, trace_param/traceParam/param,
          solidity_type/solidityType, value_map/valueMap, y opcionalmente
          enum_members/enumMembers (lista de nombres de miembros en orden,
          p.ej. ["Active", "Refunding", "Closed"] para un `enum State`) --
          necesario si `state_var` es de tipo enum, para poder reconstruir
          la expresión Solidity concreta (`State.Active`) de un valor de trace.
        - list/tuple: (state_var, trace_param, solidity_type, value_map?)
    """
    normalized = []
    for spec in specs or []:
        enum_members = None
        if isinstance(spec, dict):
            state_var    = spec.get("state_var") or spec.get("stateVar") or spec.get("name")
            trace_param  = spec.get("trace_param") or spec.get("traceParam") or spec.get("param") or state_var
            solidity_type = spec.get("solidity_type") or spec.get("solidityType") or "uint256"
            value_map    = spec.get("value_map") or spec.get("valueMap") or {}
            enum_members = spec.get("enum_members") or spec.get("enumMembers")
        elif isinstance(spec, (list, tuple)):
            state_var    = spec[0] if len(spec) > 0 else None
            trace_param  = spec[1] if len(spec) > 1 else state_var
            solidity_type = spec[2] if len(spec) > 2 and isinstance(spec[2], str) else "uint256"
            value_map    = spec[3] if len(spec) > 3 and isinstance(spec[3], dict) else {}
        else:
            state_var    = str(spec)
            trace_param  = state_var
            solidity_type = "uint256"
            value_map    = {}
        if state_var and trace_param:
            normalized_spec = {
                "state_var":    str(state_var),
                "trace_param":  str(trace_param),
                "solidity_type": str(solidity_type),
                "value_map":    value_map,
            }
            if enum_members:
                normalized_spec["enum_members"] = [str(m) for m in enum_members]
            normalized.append(normalized_spec)
    return normalized

def _extract_check_state_args(line):
    """
    Extracts the argument text from a check_state call in a trace line.
    This avoids regex-only parsing because trace values may contain nested
    parentheses, e.g. address(1).
    """
    start_name = line.find("check_state")
    if start_name < 0:
        return None

    start = line.find("(", start_name)
    if start < 0:
        return None

    depth = 0
    for i in range(start, len(line)):
        ch = line[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return line[start + 1:i]
    return None

def _parse_trace_params(line):
    args_text = _extract_check_state_args(line)
    if not args_text:
        return {}, []

    params = {}
    ordered_values = []
    for item in _split_trace_arguments(args_text):
        if ":=" in item:
            name, value = item.split(":=", 1)
        elif "=" in item:
            name, value = item.split("=", 1)
        else:
            continue
        name = name.strip()
        value = value.strip()
        if ":" in name:
            name = name.split(":", 1)[0].strip()
        params[name] = value
        if name != "this" and not name.startswith("msg."):
            ordered_values.append(value)
    return params, ordered_values

def _raw_value_to_solidity(raw_value, solidity_type, value_map, enum_members=None):
    """
    Convierte un valor crudo del trace de VeriSol a una expresión Solidity
    adecuada según el tipo declarado en el config.

    Tipos soportados: int*, uint*, bool, address, bytes*, string, y enums
    declarados en el contrato (usando `enum_members`, la lista de nombres
    de sus miembros en orden de declaración).
    """
    value = str(raw_value).strip()

    # Mapeo explícito definido en el config (tiene prioridad sobre todo)
    if value in value_map:
        return str(value_map[value])

    # --- enum ---
    # Solidity representa los enums como enteros por debajo (0-indexados
    # en orden de declaración), y VeriSol/Corral suelen mostrarlos en el
    # trace como ese entero crudo (a veces con el patrón "<Tipo>!N", igual
    # que hace con address). No admiten comparación con literales enteros
    # sueltos (`_state == 0` no compila), así que hay que reconstruir la
    # expresión con el nombre del miembro (`State.Active`).
    if enum_members:
        enum_type_name = solidity_type.strip()
        members = list(enum_members)
        idx = None

        if re.fullmatch(r"-?\d+", value):
            idx = int(value)
        else:
            m = re.fullmatch(r"0x[0-9a-fA-F]+", value)
            if m:
                idx = int(value, 16)
            else:
                # patrones tipo "State!0" (análogo a "address!N") o "State.0"
                m = re.fullmatch(re.escape(enum_type_name) + r"[!.](\d+)", value)
                if m:
                    idx = int(m.group(1))
                else:
                    # el propio nombre del miembro, con o sin el prefijo del tipo
                    bare = value.split(".")[-1]
                    if bare in members:
                        return f"{enum_type_name}.{bare}"

        if idx is not None and 0 <= idx < len(members):
            return f"{enum_type_name}.{members[idx]}"
        return None

    stype = solidity_type.strip().lower()

    # --- bool ---
    if stype == "bool":
        if value in {"true", "false"}:
            return value
        if value == "0":
            return "false"
        if value == "1":
            return "true"
        return None

    # --- address ---
    if stype == "address":
        if re.fullmatch(r"0x[0-9a-fA-F]+", value):
            return f"address({value})"
        if re.fullmatch(r"address\([^)]+\)", value):
            return value
        # VeriSol a veces emite "address!N" o "addressN"
        m = re.fullmatch(r"address!(\d+)", value)
        if m:
            return f"address({m.group(1)})"
        if re.fullmatch(r"\d+", value):
            return f"address({value})"
        return None

    # --- enteros (int / uint y variantes de tamaño) ---
    if re.match(r"u?int", stype):
        if re.fullmatch(r"-?\d+", value):
            return value
        if re.fullmatch(r"0x[0-9a-fA-F]+", value):
            return str(int(value, 16))
        return None

    # --- bytes fijos (bytes1 … bytes32) ---
    if re.match(r"bytes\d+", stype):
        if re.fullmatch(r"0x[0-9a-fA-F]+", value):
            return value
        if re.fullmatch(r"\d+", value):
            return hex(int(value))
        return None

    # --- string / bytes dinámico ---
    # VeriSol/Corral no exponen el contenido real de un string o bytes
    # dinámico en el trace, así que ya no pedimos el valor crudo: check_state
    # ahora expone keccak256(bytes(state_var)) como parámetro bytes32
    # (ver _build_check_state_function/_build_check_state_call), y lo que
    # llega acá es ese hash concreto, no el string. Lo tratamos igual que
    # un bytes32 fijo.
    if stype in ("string", "bytes"):
        if re.fullmatch(r"0x[0-9a-fA-F]+", value):
            n = int(value, 16)
            return "0x" + format(n, "064x")
        if re.fullmatch(r"-?\d+", value):
            n = int(value)
            if n < 0:
                n &= (1 << 256) - 1
            return "0x" + format(n, "064x")
        return None

    # Fallback genérico: si es un literal reconocible lo dejamos pasar
    if re.fullmatch(r"-?\d+", value) or value in {"true", "false"}:
        return value
    if re.fullmatch(r"0x[0-9a-fA-F]+", value):
        return value
    if re.fullmatch(r"address\([^)]+\)", value):
        return value

    return None


# ---------------------------------------------------------------------------
# Generación de check_state e inyección en el .sol temporal
# ---------------------------------------------------------------------------

def _build_check_state_function(counterexample_specs, contractName):
    """
    Genera la función check_state que VeriSol usará para exponer el estado
    concreto en el trace del contraejemplo.

    Firma generada (ejemplo con x:int256, state:uint8, owner:address):
        function check_state_<ContractName>(int256 _x, uint8 _state, address _owner) public returns (bool) {
            require(_x == x && _state == state && _owner == owner);
            mostrarEstado = true;
            return true;
        }

    El require con la conjunción de igualdades fuerza a Corral a mostrar en el
    trace los valores concretos de cada variable de estado.
    """
    if not counterexample_specs:
        return ""

    params = []
    equalities = []
    for spec in counterexample_specs:
        stype      = spec["solidity_type"]
        trace_p    = spec["trace_param"]   # nombre del parámetro en check_state
        state_var  = spec["state_var"]     # nombre de la variable de estado en el contrato

        stype_norm = stype.strip().lower()

        # Solidity no admite `==` directo entre strings/bytes dinámicos, y
        # además Corral/VeriSol no exponen en el trace el contenido real de
        # un parámetro `string`/`bytes` (aparece como un identificador
        # interno opaco). Por eso, en vez de pedir el string/bytes crudo,
        # check_state pide directamente su hash como `bytes32`: eso sí se
        # imprime como un literal legible en el trace, y sirve exactamente
        # igual para forzar/exponer el valor concreto de state_var.
        if stype_norm == "string":
            params.append(f"bytes32 _{trace_p}")
            equalities.append(f"_{trace_p} == keccak256(bytes({state_var}))")
        elif stype_norm == "bytes":
            params.append(f"bytes32 _{trace_p}")
            equalities.append(f"_{trace_p} == keccak256({state_var})")
        else:
            params.append(f"{stype} _{trace_p}")
            equalities.append(f"_{trace_p} == {state_var}")

    params_str     = ", ".join(params)
    equalities_str = " && ".join(equalities)

    return (
        f"function check_state_{contractName}({params_str}) public returns (bool) {{\n"
        f"    require({equalities_str});\n"
        f"    mostrarEstado = true;\n"
        f"    return true;\n"
        f"}}\n"
    )

def _build_check_state_call(counterexample_specs, contractName, query_type="QUERY_MUST"):
    """
    Emits a call that forces the concrete source state to appear in the
    counterexample trace.
    """
    if not counterexample_specs:
        return ""

    def _call_arg(spec):
        stype_norm = spec["solidity_type"].strip().lower()
        state_var = spec["state_var"]
        if stype_norm == "string":
            return f"keccak256(bytes({state_var}))"
        if stype_norm == "bytes":
            return f"keccak256({state_var})"
        return state_var

    args = ", ".join(_call_arg(spec) for spec in counterexample_specs)
    return (
        f"require(mostrarEstado);//{query_type}: expose concrete state flag\n"
        # f"require(check_state_{contractName}({args}));//{query_type}: expose concrete state\n"
    )


def _has_function_definition(source, func_name):
    return re.search(rf"\bfunction\s+{re.escape(func_name)}\s*\(", source) is not None


def _has_mostrar_estado_definition(source):
    return re.search(r"\bbool\s+(?:public\s+|private\s+|internal\s+|external\s+)?mostrarEstado\b", source) is not None


def _build_mostrar_estado_definition(source):
    if _has_mostrar_estado_definition(source):
        return ""
    return "bool mostrarEstado = false;\n"


def _insert_body_into_contract(fileNameTemp, contractName, body):
    with open(fileNameTemp, "r") as f:
        inputfile = f.readlines()

    with open(fileNameTemp, "w") as write_f:
        for line in inputfile:
            write_f.write(line)
            if f"contract {contractName}" in line:
                write_f.write(body)


def _inject_check_state(fileNameTemp, contractName, counterexample_specs):
    """
    Inserta check_state_<ContractName> en el archivo .sol temporal,
    justo después de la línea `contract <ContractName>`.
    Solo inyecta si hay specs y si la función no existe ya.
    """
    if not counterexample_specs:
        return

    func_name = f"check_state_{contractName}"

    with open(fileNameTemp, "r") as f:
        source = f.read()

    if _has_function_definition(source, func_name):
        return  # ya inyectada (p. ej. está en el contrato base)

    func_body = _build_mostrar_estado_definition(source) + _build_check_state_function(counterexample_specs, contractName)

    lines = source.splitlines(keepends=True)
    out = []
    injected = False
    for line in lines:
        out.append(line)
        if not injected and f"contract {contractName}" in line and "{" in line:
            out.append(func_body + "\n")
            injected = True

    if not injected:
        # Fallback: buscar solo "contract <Name>" sin llave en la misma línea
        out = []
        pending_contract = False
        for i, line in enumerate(lines):
            out.append(line)
            if pending_contract and "{" in line:
                out.append(func_body + "\n")
                injected = True
                pending_contract = False
                continue
            if not injected and f"contract {contractName}" in line:
                # la llave puede estar en la siguiente línea
                if i + 1 < len(lines) and "{" in lines[i + 1]:
                    pending_contract = True
                else:
                    out.append(func_body + "\n")
                    injected = True

    with open(fileNameTemp, "w") as f:
        f.writelines(out)


# ---------------------------------------------------------------------------
# Extracción de contraejemplo concreto desde el output de VeriSol
# ---------------------------------------------------------------------------

def extract_concrete_counterexample(output_verisol, counterexample_specs):
    """
    Parsea el output de VeriSol buscando una línea que contenga check_state.
    De esa línea extrae los valores concretos de cada variable y construye
    una expresión Solidity inline para excluirla en la siguiente query MUST:

        require(!(x == 12 && state == 0 && owner == address(4)));

    Retorna la expresión interior del require!(…) —sin el require ni los
    paréntesis externos— para que el caller la envuelva como necesite.
    Retorna None si no se puede extraer.
    """
    if not counterexample_specs:
        return None

    for line in output_verisol.splitlines():
        if "check_state" not in line:
            continue
        params, ordered_values = _parse_trace_params(line)
        if not params and not ordered_values:
            continue

        clauses = []
        for index, spec in enumerate(counterexample_specs):
            trace_param  = spec["trace_param"]
            state_var    = spec["state_var"]
            solidity_type = spec["solidity_type"]
            value_map    = spec["value_map"]

            # -----------------------------------------------------------------
            # LIMITACIÓN TEMPORAL (bug de Corral con contraejemplos `address`)
            # -----------------------------------------------------------------
            # Corral está devolviendo valores de `address` inconsistentes/
            # incorrectos en el trace de las queries MUST (función `vcMUST`
            # generada más abajo), lo que produce exclusiones
            # (require(!(... && owner == address(N) && ...))) con una
            # dirección que no es la que realmente causó el contraejemplo, y
            # eso rompe la convergencia Must/May.
            #
            # Como workaround MOMENTÁNEO, mientras no se resuelva el bug en
            # Corral, se ignoran acá las variables de tipo `address` /
            # `address payable`: no se incluye su cláusula en el
            # contraejemplo concreto que se excluye. 
            # TODO: Modificar i ete bug se resuelve o se encuentra la causa de su origen.
            if solidity_type.strip().lower() in ("address", "address payable"):
                continue

            candidate_keys = [
                f"_{trace_param}",
                trace_param,
                f"_{state_var}",
                state_var,
            ]
            raw_value = None
            for key in candidate_keys:
                if key in params:
                    raw_value = params[key]
                    break

            # Fallback por posición: útil cuando el parámetro del trace no se
            # llama igual que la variable del contrato, por ejemplo state/_s.
            if raw_value is None and index < len(ordered_values):
                raw_value = ordered_values[index]

            if raw_value is None:
                continue

            value_expr = _raw_value_to_solidity(raw_value, solidity_type, value_map, spec.get("enum_members"))
            if value_expr is None:
                continue

            stype_norm = solidity_type.strip().lower()
            if stype_norm == "string":
                clauses.append(f"keccak256(bytes({state_var})) == {value_expr}")
            elif stype_norm == "bytes":
                clauses.append(f"keccak256({state_var}) == {value_expr}")
            else:
                clauses.append(f"{state_var} == {value_expr}")

        if clauses:
            return " && ".join(clauses)

    return None

