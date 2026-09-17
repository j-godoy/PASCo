"""
Saneamiento de preconditions de funciones para uso en QUERY_ENABLEDNESS:
elimina conjuntos que dependan de msg.sender/msg.value o de los parámetros
propios de la función que todavía no fue invocada.
"""
import re

from helpers.solidity_parser import _split_trace_arguments


def _split_top_level_conjunction(expr):
    parts = []
    current = []
    paren_depth = 0
    bracket_depth = 0
    i = 0
    while i < len(expr):
        ch = expr[i]
        if ch == "(":
            paren_depth += 1
        elif ch == ")":
            paren_depth = max(0, paren_depth - 1)
        elif ch == "[":
            bracket_depth += 1
        elif ch == "]":
            bracket_depth = max(0, bracket_depth - 1)

        if (
            ch == "&"
            and i + 1 < len(expr)
            and expr[i + 1] == "&"
            and paren_depth == 0
            and bracket_depth == 0
        ):
            parts.append("".join(current).strip())
            current = []
            i += 2
            continue

        current.append(ch)
        i += 1

    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts

def _uses_msg_sender_or_value(expr):
    return re.search(r"\bmsg\s*\.\s*(sender|value)\b", expr) is not None

def _extract_function_param_names(function_call):
    """
    Extrae los nombres de los parámetros de una llamada de función del tipo
        "TransferResponsibility(newCounterparty)"
    devolviendo ["newCounterparty"].

    Si la función no tiene parámetros (p.ej. "Foo()") devuelve [].
    """
    function_call = str(function_call).strip()
    start = function_call.find("(")
    end = function_call.rfind(")")
    if start < 0 or end < 0 or end <= start:
        return []
    args_text = function_call[start + 1:end]
    params = [p.strip() for p in _split_trace_arguments(args_text) if p.strip()]
    return params

def _uses_any_identifier(expr, identifiers):
    """
    True si `expr` referencia alguno de los identificadores dados como
    identificador completo (no como substring de otro identificador).
    """
    for ident in identifiers:
        ident = str(ident).strip()
        if not ident:
            continue
        if re.search(r"\b" + re.escape(ident) + r"\b", expr) is not None:
            return True
    return False

def _sanitize_function_precondition(precondition, param_names=None):
    """
    Limpia una precondición de función para uso en QUERY_ENABLEDNESS:
      - elimina conjuntos que dependan de msg.sender / msg.value
      - elimina conjuntos que dependan de los parámetros propios de la
        función (param_names), ya que en la query de enabledness la función
        todavía no fue invocada y esos parámetros no deben restringirse.
    """
    precondition = str(precondition).strip()
    if not precondition or precondition == "true":
        return "true"

    param_names = param_names or []

    kept_parts = []
    for part in _split_top_level_conjunction(precondition):
        if _uses_msg_sender_or_value(part):
            continue
        if param_names and _uses_any_identifier(part, param_names):
            continue
        kept_parts.append(part)

    if not kept_parts:
        return "true"
    return " && ".join(kept_parts)

def sanitize_function_preconditions(preconditions, functions=None):
    """
    functions: lista paralela a `preconditions` con las llamadas de función
    (p.ej. "TransferResponsibility(newCounterparty)") usada para detectar y
    excluir, de cada precondición, los conjuntos que dependan de los
    parámetros propios de esa función.
    """
    if functions is None:
        functions = [None] * len(preconditions)
    sanitized = []
    for precondition, function_call in zip(preconditions, functions):
        param_names = _extract_function_param_names(function_call) if function_call is not None else []
        sanitized.append(_sanitize_function_precondition(precondition, param_names))
    return sanitized

