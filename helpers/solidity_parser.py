"""
Utilidades de parsing de código fuente Solidity: detección de tipos
elementales, remoción de comentarios, ubicación del cuerpo de un contrato,
parsing de declaraciones de variables de estado, enums, y separación de
argumentos de una llamada (usado tanto para preconditions como para
check_state).
"""
import re


_SOLIDITY_DECL_SKIP_KEYWORDS = (
    "function", "constructor", "modifier", "event", "using", "import",
    "pragma", "fallback", "receive", "error",
)

_SOLIDITY_VISIBILITY_KEYWORDS = {
    "public", "private", "internal", "external", "constant", "immutable", "payable",
}

_SOLIDITY_ELEMENTARY_TYPES = {
    "bool", "address", "address payable", "string", "bytes",
}


def _is_elementary_solidity_type(stype):
    s = stype.strip()
    if s in _SOLIDITY_ELEMENTARY_TYPES:
        return True
    # int8..int256 / uint8..uint256 (incluye "int"/"uint" sin tamaño explícito)
    if re.fullmatch(r"u?int\d*", s):
        return True
    # bytes1..bytes32
    if re.fullmatch(r"bytes\d+", s):
        return True
    return False


def _strip_solidity_comments(source, preserve_length=False):
    """
    Elimina comentarios `// ...` y `/* ... */` de código Solidity, respetando
    los literales de string ("..." y '...') para no romper comentarios que
    aparezcan dentro de un string.

    Si `preserve_length` es False (default): descarta el contenido del
    comentario, conservando los saltos de línea para no pegar tokens entre
    sí (uso para trocear statements, donde los índices no importan).

    Si `preserve_length` es True: reemplaza cada carácter del comentario por
    un espacio (dejando intactos los saltos de línea), de forma que el
    resultado tiene EXACTAMENTE el mismo largo que `source` y cada índice
    sigue apuntando al mismo lugar. Necesario para funciones como
    `_find_contract_body`, que devuelven offsets sobre el source original.
    """
    out = []
    i = 0
    n = len(source)
    in_string = None  # None, '"' o "'"
    while i < n:
        ch = source[i]

        if in_string:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                # conservar el carácter escapado tal cual
                out.append(source[i + 1])
                i += 2
                continue
            if ch == in_string:
                in_string = None
            i += 1
            continue

        if ch in ("\"", "'"):
            in_string = ch
            out.append(ch)
            i += 1
            continue

        if ch == "/" and i + 1 < n and source[i + 1] == "/":
            # comentario de línea: enmascarar hasta '\n' (sin incluirlo)
            j = i + 2
            if preserve_length:
                out.append("  ")
            while j < n and source[j] != "\n":
                if preserve_length:
                    out.append(" ")
                j += 1
            i = j
            continue

        if ch == "/" and i + 1 < n and source[i + 1] == "*":
            # comentario de bloque: enmascarar hasta '*/', preservando '\n'
            j = i + 2
            if preserve_length:
                out.append("  ")
            while j + 1 < n and not (source[j] == "*" and source[j + 1] == "/"):
                if source[j] == "\n":
                    out.append("\n")
                elif preserve_length:
                    out.append(" ")
                j += 1
            if preserve_length:
                out.append("  ")
            i = j + 2
            continue

        out.append(ch)
        i += 1

    return "".join(out)


def _get_parent_contract_names(source, contractName):
    """
    Devuelve la lista de nombres de contratos padre de la declaración
        contract <contractName> is A, B(args), C { ... }
    Soporta argumentos de constructor en la lista de herencia
    (p.ej. `is B(x, y)`), que se ignoran ya que solo interesa el nombre.

    Usa una versión del source con comentarios enmascarados (mismo largo,
    mismos índices) para evitar falsos positivos por `{`/`}` sueltas dentro
    de comentarios.
    """
    masked = _strip_solidity_comments(source, preserve_length=True)
    match = re.search(r"\bcontract\s+" + re.escape(contractName) + r"\b([^{]*)\{", masked)
    if not match:
        return []
    header = match.group(1)
    is_match = re.search(r"\bis\b(.*)", header, re.DOTALL)
    if not is_match:
        return []
    parents = []
    for part in _split_trace_arguments(is_match.group(1)):
        name_match = re.match(r"\s*([A-Za-z_]\w*)", part)
        if name_match:
            parents.append(name_match.group(1))
    return parents


def _find_contract_body(source, contractName):
    """
    Devuelve (start, end) -- los índices del cuerpo del contrato
    (contenido entre las llaves que abren y cierran `contract <contractName> { ... }`),
    o None si no se encuentra.
    Soporta herencia: `contract Foo is Bar, Baz {`.

    Busca y cuenta llaves sobre una versión del source con los comentarios
    enmascarados (mismo largo, mismos índices), para que una `{` o `}`
    suelta dentro de un comentario (código viejo comentado, típico en
    contratos reales) no descuadre el conteo de profundidad.
    """
    masked = _strip_solidity_comments(source, preserve_length=True)

    match = re.search(r"\bcontract\s+" + re.escape(contractName) + r"\b[^{]*\{", masked)
    if not match:
        return None

    start = match.end()
    depth = 1
    i = start
    while i < len(masked) and depth > 0:
        ch = masked[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        i += 1
    if depth != 0:
        return None
    end = i - 1  # índice de la '}' que cierra el contrato
    return start, end


def _split_top_level_statements(body):
    """
    Recorre el cuerpo de un contrato y devuelve la lista de statements de
    "primer nivel" (declaraciones de variables, terminadas en ';'),
    descartando por completo el contenido de cualquier bloque con llaves
    (funciones, constructor, modifiers, structs, etc.), ya que esos
    bloques no pueden contener declaraciones de variables de estado.

    Además devuelve los nombres de los structs declarados, y un dict con
    los enums declarados en el contrato mapeados a la lista de sus
    miembros en el orden en que fueron declarados (p.ej.
    {"State": ["Active", "Refunding", "Closed"]}), para poder clasificar
    correctamente los tipos custom y, en el caso de los enums, poder
    reconstruir la expresión Solidity (`State.Active`) correspondiente a
    un valor concreto extraído de un trace.
    """
    body = _strip_solidity_comments(body)

    statements = []
    struct_names = set()
    enum_members = {}

    buffer = []
    i = 0
    n = len(body)
    while i < n:
        ch = body[i]
        if ch == "{":
            header = "".join(buffer).strip()
            m = re.match(r"^struct\s+(\w+)", header)
            if m:
                struct_names.add(m.group(1))
            enum_match = re.match(r"^enum\s+(\w+)", header)

            depth = 1
            j = i + 1
            block_start = j
            while j < n and depth > 0:
                if body[j] == "{":
                    depth += 1
                elif body[j] == "}":
                    depth -= 1
                j += 1
            block_end = j - 1  # índice de la '}' que cierra el bloque

            if enum_match:
                inner = body[block_start:block_end]
                members = [m.strip() for m in inner.split(",") if m.strip()]
                if members:
                    enum_members[enum_match.group(1)] = members

            i = j
            buffer = []
            continue
        elif ch == ";":
            statements.append("".join(buffer).strip())
            buffer = []
            i += 1
            continue
        else:
            buffer.append(ch)
            i += 1

    tail = "".join(buffer).strip()
    if tail:
        statements.append(tail)

    return statements, struct_names, enum_members



def _parse_state_variable_declaration(statement, struct_names):
    """
    Intenta interpretar `statement` como una declaración de variable de
    estado y devuelve (solidity_type, name, is_private) o None si no
    corresponde (es una declaración de otra cosa, un mapping, un array,
    un struct, etc).

    is_private indica si la variable tiene el modifier `private`, lo cual
    es relevante para variables heredadas: una variable `private` del
    contrato padre NO es visible/referenciable desde el contrato hijo.
    """
    stmt = statement.strip()
    if not stmt:
        return None

    first_word = re.match(r"^(\w+)", stmt)
    if first_word and first_word.group(1) in _SOLIDITY_DECL_SKIP_KEYWORDS:
        return None

    # Las declaraciones de variable de estado no llevan paréntesis en su
    # parte de tipo+nombre (eso descarta llamadas a `using X for Y;`,
    # errores custom, etc.). El VALOR de inicialización sí puede legítimamente
    # tener paréntesis (`address(0x0)`, casts, llamadas a constructores como
    # `StandardToken(...)`), así que el chequeo se hace solo sobre la parte
    # antes del primer `=`.
    decl_part = stmt.split("=", 1)[0].strip()

    if "(" in decl_part or ")" in decl_part:
        # mapping(...) sí tiene paréntesis, lo tratamos aparte:
        if not decl_part.startswith("mapping"):
            return None

    if stmt.startswith("mapping"):
        return None  # no se puede comparar un mapping con ==

    tokens = decl_part.split()
    if len(tokens) < 2:
        return None

    name = tokens[-1]
    if not re.fullmatch(r"[A-Za-z_]\w*", name):
        return None

    type_and_mods = tokens[:-1]
    mods = [t for t in type_and_mods if t in _SOLIDITY_VISIBILITY_KEYWORDS]
    type_tokens = [t for t in type_and_mods if t not in _SOLIDITY_VISIBILITY_KEYWORDS]
    if not type_tokens:
        return None

    solidity_type = " ".join(type_tokens)
    is_private = "private" in mods

    # Constantes en tiempo de compilación: no son "estado" en el sentido de
    # esta herramienta (su valor nunca cambia ni distingue contraejemplos).
    if "constant" in mods:
        return None

    # Arrays (fixed o dynamic): "uint[]", "uint[3]", "uint256 [ ]"...
    if "[" in solidity_type:
        return None

    # Structs: no soportan comparación directa con ==
    if solidity_type in struct_names:
        return None

    return solidity_type, name, is_private


def _collect_enum_members(source, contractName, _visited=None):
    """
    Recorre recursivamente `contractName` y sus contratos padre (siguiendo
    `contract X is A, B { ... }`) para reunir todos los enums declarados
    en la jerarquía, mapeados a la lista de sus miembros en el orden en
    que fueron declarados, p.ej. {"State": ["Active", "Refunding", "Closed"]}.

    Se usa para poder reconstruir, más adelante, la expresión Solidity
    concreta (`State.Active`) correspondiente a un valor extraído de un
    trace de VeriSol para una variable de tipo enum.
    """
    if _visited is None:
        _visited = set()
    if contractName in _visited:
        return {}
    _visited.add(contractName)

    bounds = _find_contract_body(source, contractName)
    if bounds is None:
        return {}
    start, end = bounds
    body = source[start:end]
    _statements, _struct_names, enum_members = _split_top_level_statements(body)

    combined = dict(enum_members)
    for parent in _get_parent_contract_names(source, contractName):
        parent_members = _collect_enum_members(source, parent, _visited)
        for k, v in parent_members.items():
            combined.setdefault(k, v)
    return combined


def _extract_state_variables_from_solidity(source, contractName, _visited=None, _is_root=True,
                                            _enum_members=None):
    """
    Parsea el código fuente Solidity y extrae las variables de estado del
    contrato `contractName`, incluyendo las heredadas de sus contratos
    padre (recursivamente, siguiendo `contract X is A, B { ... }`).
    Devuelve specs en el mismo formato que
    `_normalize_counterexample_specs`:
        [{"state_var": str, "trace_param": str, "solidity_type": str, "value_map": {}}, ...]

    Las variables cuyo tipo coincide con un `enum` declarado en la
    jerarquía del contrato (p.ej. `State private _state;` con
    `enum State { Active, Refunding, Closed }`) incluyen además una clave
    "enum_members" con la lista de miembros en orden, para poder
    reconstruir la expresión Solidity concreta (`State.Active`) de un
    valor extraído de un trace de VeriSol.

    Se excluyen automáticamente:
        - constantes (`constant`)
        - variables `private` DE LOS CONTRATOS PADRE (no serían visibles ni
          referenciables desde `contractName`). Las variables `private`
          del propio `contractName` (el contrato "raíz" bajo análisis) SÍ
          se incluyen, ya que ahí no hay problema de visibilidad.
        - arrays, fixed o dynamic (no comparables con == en Solidity)
        - variables de tipo struct (no comparables con ==)
        - mappings (no comparables con == de forma directa)
        - declaraciones que no sean variables de estado (funciones, eventos,
          modifiers, structs, enums, etc.)

    Las variables `string`/`bytes` (dynamic) SÍ se incluyen: la comparación
    se resuelve más adelante en `_build_check_state_function` usando
    `keccak256`, ya que Solidity no admite `==` directo entre ellas.

    _visited: usado internamente para evitar recursión infinita en
    jerarquías de herencia con ciclos (o diamante) mal formadas.
    _is_root: True solo en la llamada inicial (el contrato bajo análisis);
    False en las llamadas recursivas sobre contratos padre. Determina si
    las variables `private` de ese nivel se incluyen o se descartan.
    _enum_members: mapa combinado {enumName: [miembros...]} de toda la
    jerarquía; se calcula una sola vez en la llamada raíz y se propaga
    hacia las llamadas recursivas.
    """
    if _visited is None:
        _visited = set()
    if contractName in _visited:
        return []
    if _enum_members is None:
        _enum_members = _collect_enum_members(source, contractName)
    _visited.add(contractName)

    bounds = _find_contract_body(source, contractName)
    if bounds is None:
        return []

    start, end = bounds
    body = source[start:end]

    statements, struct_names, _own_enum_members = _split_top_level_statements(body)

    specs = []
    seen_names = set()

    # 1. Variables heredadas de los contratos padre primero (nunca incluyen
    #    sus `private`, ya que no serían referenciables desde `contractName`).
    for parent in _get_parent_contract_names(source, contractName):
        parent_specs = _extract_state_variables_from_solidity(
            source, parent, _visited, _is_root=False, _enum_members=_enum_members
        )
        for spec in parent_specs:
            if spec["state_var"] in seen_names:
                continue
            seen_names.add(spec["state_var"])
            specs.append(spec)

    # 2. Variables de estado propias de este nivel del contrato.
    for stmt in statements:
        parsed = _parse_state_variable_declaration(stmt, struct_names)
        if parsed is None:
            continue
        solidity_type, name, is_private = parsed
        if name in seen_names:
            continue
        if is_private and not _is_root:
            # private en un contrato padre: no visible desde contractName
            continue
        seen_names.add(name)
        spec = {
            "state_var":    name,
            "trace_param":  name,
            "solidity_type": solidity_type,
            "value_map":    {},
        }
        if solidity_type in _enum_members:
            spec["enum_members"] = _enum_members[solidity_type]
        specs.append(spec)

    return specs


def _split_trace_arguments(args_text):
    args = []
    current = []
    paren_depth = 0
    bracket_depth = 0
    for ch in args_text:
        if ch == "(":
            paren_depth += 1
        elif ch == ")":
            paren_depth = max(0, paren_depth - 1)
        elif ch == "[":
            bracket_depth += 1
        elif ch == "]":
            bracket_depth = max(0, bracket_depth - 1)
        if ch == "," and paren_depth == 0 and bracket_depth == 0:
            args.append("".join(current).strip())
            current = []
            continue
        current.append(ch)
    tail = "".join(current).strip()
    if tail:
        args.append(tail)
    return args

