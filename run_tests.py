#!/usr/bin/env python3
"""
pasco_compare.py
=================

Herramienta única (todo en un archivo) para correr PASCo.py y/o comparar los
grafos .dot que genera, determinando si dos (o más) contratos son
equivalentes según las reglas acordadas para cada modo de PASCo:

  - mode=states (CSM): isomorfismo de nodos ignorando nombres/labels de estado;
    las aristas deben coincidir exactamente por (función normalizada, color).
  - mode=epa: igual que states para las aristas, PERO además el conjunto de
    funciones presentes en el label de cada nodo (normalizado, incluyendo 't')
    debe coincidir entre nodos mapeados. No importa si en el .dot original las
    funciones aparecen agrupadas en una sola línea de label o como aristas
    t() separadas/dashed: lo que se compara es el conjunto resultante.

DOS MODOS DE USO (subcomandos)
-------------------------------

1) Solo comparar archivos .dot ya generados (no corre PASCo):

   python pasco_compare.py compare --mode epa archivo1.dot archivo2.dot [archivo3.dot ...]

2) Correr PASCo.py para uno o más contratos y comparar los .dot resultantes:

   python pasco_compare.py run-and-compare \
       --pasco-script /ruta/a/PASCo.py \
       --mode states \
       --contract ValidatorAuctionConfig --must true \
       --contract OtroContrato --must true

   Para comparar la versión "must" vs "may" del MISMO contrato en una sola
   corrida (alias: contratos "must" y "may"):

   python pasco_compare.py run-and-compare \
       --pasco-script /ruta/a/PASCo.py \
       --mode epa \
       --contract ValidatorAuctionConfig --must true \
       --contract ValidatorAuctionConfig --must false

   Si pasás un solo --must, se aplica a todos los --contract. Si pasás varios,
   tienen que ser tantos como --contract, emparejados en el mismo orden.

Con 3+ grafos/contratos se comparan TODOS los pares posibles y se imprime
además una matriz resumen IGUAL/DIST.

⚠️ Nota importante sobre run-and-compare: el archivo que genera PASCo NO tiene
extensión ".dot" literal -- el patrón confirmado es "{file}_Mode.{mode}", por
ejemplo "EscrowVault_Mode.states" o "EscrowVault_Mode.epa" (la extensión es
el modo; el contenido es texto formato DOT igual). El script ya usa ese
patrón por defecto. Si tu instalación de PASCo usa otro patrón, pasalo con
--dot-name-pattern, por ejemplo: "{file}_Mode.{mode}" (placeholders: {file}
{mode} {must} {must_lower}).
Aún no está confirmado si --must TRUE vs FALSE generan nombres distintos
(sufijo o carpeta separada) o sobreescriben el mismo archivo. Por las dudas,
para protegerse de que dos corridas (ej. must y may del mismo contrato)
generen el mismo nombre de archivo y se sobrescriban entre sí, cada archivo
detectado se copia de inmediato a una carpeta temporal exclusiva de esta
ejecución, ANTES de lanzar la siguiente corrida de PASCo.
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from dataclasses import asdict, dataclass, field

import networkx as nx
from networkx.algorithms.isomorphism import MultiDiGraphMatcher


# =============================================================================
# SECCIÓN 1: Parser de archivos .dot (subset usado por PASCo)
# =============================================================================
#
# No depende de pydot/graphviz. Soporta:
#
#   digraph {
#       "node-id" [label="texto multi-linea"]
#       nodeA -> nodeB [label="..." color=... style=...]
#   }
#
# Notas de robustez:
# - Los nombres de nodo pueden venir citados ("1-0-0-4-") o sin citar (init).
# - Los labels de nodo pueden tener saltos de línea reales dentro de comillas.
# - PASCo repite declaraciones del mismo nodo; nos quedamos con la primera.
# - Los atributos de arista pueden venir en cualquier orden, citados o no.

@dataclass
class RawNode:
    node_id: str
    label: str  # texto crudo del label, tal como aparece en el .dot


@dataclass
class RawEdge:
    source: str
    target: str
    label: str
    color: str
    style: str


@dataclass
class RawGraph:
    nodes: dict[str, RawNode] = field(default_factory=dict)
    edges: list[RawEdge] = field(default_factory=list)
    source_path: str = ""


_NODE_ID_QUOTED = r'"((?:[^"\\]|\\.)*)"'
_NODE_ID_BARE = r"([A-Za-z_][A-Za-z0-9_]*)"
_NODE_ID = rf"(?:{_NODE_ID_QUOTED}|{_NODE_ID_BARE})"

# Declaración de nodo: "id" [label="..."]   o   id [label=...]
_NODE_DECL_RE = re.compile(rf"^\s*{_NODE_ID}\s*\[(.*?)\]\s*;?\s*$", re.DOTALL)

# Arista: "a" -> "b" [label="..." color=... style=...]
_EDGE_RE = re.compile(rf"^\s*{_NODE_ID}\s*->\s*{_NODE_ID}\s*\[(.*?)\]\s*;?\s*$", re.DOTALL)


def _node_id_from_match(m: re.Match, group_offset: int) -> str:
    quoted = m.group(group_offset)
    bare = m.group(group_offset + 1)
    return quoted if quoted is not None else bare


def _parse_attrs(attr_text: str) -> dict[str, str]:
    """
    Parsea atributos tipo:  label="bid();" color=blue style=dashed
    en {label: 'bid();', color: 'blue', style: 'dashed'}.
    Soporta valores citados (con saltos de línea/escapes) y sin citar.
    """
    attrs: dict[str, str] = {}
    i = 0
    n = len(attr_text)
    key_re = re.compile(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*")
    while i < n:
        m = key_re.match(attr_text, i)
        if not m:
            j = i
            while j < n and attr_text[j] in " \t\r\n,":
                j += 1
            if j == i:
                break
            i = j
            continue
        key = m.group(1)
        i = m.end()
        if i < n and attr_text[i] == '"':
            j = i + 1
            buf = []
            while j < n:
                c = attr_text[j]
                if c == "\\" and j + 1 < n:
                    buf.append(attr_text[j + 1])
                    j += 2
                    continue
                if c == '"':
                    j += 1
                    break
                buf.append(c)
                j += 1
            value = "".join(buf)
            i = j
        else:
            j = i
            while j < n and attr_text[j] not in " \t\r\n,]":
                j += 1
            value = attr_text[i:j]
            i = j
        attrs[key.strip().lower()] = value
        while i < n and attr_text[i] in " \t\r\n,":
            i += 1
    return attrs


def _split_statements(body: str) -> list[str]:
    """
    Divide el cuerpo del digraph en statements individuales, balanceando
    corchetes y comillas para no cortar labels multi-línea.
    """
    statements = []
    buf = []
    depth = 0
    in_quotes = False
    i = 0
    n = len(body)
    while i < n:
        c = body[i]
        if in_quotes:
            buf.append(c)
            if c == "\\" and i + 1 < n:
                buf.append(body[i + 1])
                i += 2
                continue
            if c == '"':
                in_quotes = False
            i += 1
            continue
        if c == '"':
            in_quotes = True
            buf.append(c)
            i += 1
            continue
        if c == "[":
            depth += 1
            buf.append(c)
            i += 1
            continue
        if c == "]":
            depth -= 1
            buf.append(c)
            i += 1
            if depth == 0:
                statements.append("".join(buf))
                buf = []
            continue
        buf.append(c)
        i += 1
    return [s.strip().strip(";").strip() for s in statements if s.strip()]


def parse_dot_file(path: str) -> RawGraph:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    return parse_dot_string(text, source_path=path)


def parse_dot_string(text: str, source_path: str = "") -> RawGraph:
    graph = RawGraph(source_path=source_path)

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No se encontró un bloque 'digraph {{ ... }}' válido en {source_path!r}")
    body = text[start + 1:end]

    for stmt in _split_statements(body):
        edge_m = _EDGE_RE.match(stmt)
        if edge_m:
            src = _node_id_from_match(edge_m, 1)
            dst = _node_id_from_match(edge_m, 3)
            attrs = _parse_attrs(edge_m.group(5))
            graph.edges.append(RawEdge(
                source=src, target=dst,
                label=attrs.get("label", ""),
                color=attrs.get("color", ""),
                style=attrs.get("style", ""),
            ))
            continue

        node_m = _NODE_DECL_RE.match(stmt)
        if node_m:
            node_id = _node_id_from_match(node_m, 1)
            attrs = _parse_attrs(node_m.group(3))
            label = attrs.get("label", node_id)
            if node_id not in graph.nodes:
                graph.nodes[node_id] = RawNode(node_id=node_id, label=label)
            continue

        # statement no reconocido (comentarios, atributos globales, etc.) -> se ignora

    for e in graph.edges:
        for nid in (e.source, e.target):
            if nid not in graph.nodes:
                graph.nodes[nid] = RawNode(node_id=nid, label=nid)

    return graph


# =============================================================================
# SECCIÓN 2: Normalización y modelo de grafo comparable
# =============================================================================
#
# Reglas acordadas:
#
# MODO STATES (CSM):
#   - Isomorfismo de nodos ignorando nombres/labels de nodo por completo
#     (incluyendo 'init'). Las aristas deben coincidir exactamente por
#     (función normalizada, color).
#
# MODO EPA:
#   - Igual que arriba para las aristas.
#   - Además, el CONJUNTO de tokens del label del nodo (normalizado a
#     minúsculas, sin contenido entre paréntesis ni ';', SIN omitir 't')
#     debe coincidir exactamente entre nodos mapeados. No importa el orden
#     ni si en el .dot aparecen agrupados en una sola línea de label o como
#     aristas t() separadas/dashed.
#   - El nodo 'init' se normaliza igual que cualquier función (init ≡ Init).
#
# Normalización de nombre de función: minúsculas + se quita el contenido
# entre paréntesis (argumentos) + se quita ';'.
#   "auctionEnd();"                              -> "auctionend"
#   "TransferResponsibility(newCounterparty);"   -> "transferresponsibility"
#   "Bid"                                         -> "bid"
#
# El color de la arista SÍ es parte de la identidad de la transición.
# El 'style' (dashed/solid) y el agrupamiento visual del label NO se comparan.

_PAREN_CONTENT_RE = re.compile(r"\([^()]*\)")
_SEMICOLON_RE = re.compile(r";")


def normalize_function_name(raw_label: str) -> str:
    cleaned = _PAREN_CONTENT_RE.sub("", raw_label)
    cleaned = _SEMICOLON_RE.sub("", cleaned)
    return cleaned.strip().lower()


def normalize_color(raw_color: str) -> str:
    return raw_color.strip().lower()


def _split_node_label_tokens(raw_label: str) -> frozenset:
    """
    Para EPA: parte el label de un nodo (posiblemente multi-línea, ej.
    "bid();\\nwithdraw();\\nt();\\n") en el conjunto de tokens normalizados.
    Para nodos simples (CSM, o el nodo init/Init) da un conjunto de 1 token.
    """
    parts = re.split(r"[\n;]+", raw_label)
    tokens = set()
    for p in parts:
        tok = normalize_function_name(p)
        if tok:
            tokens.add(tok)
    return frozenset(tokens)


def build_comparable_graph(raw: RawGraph, mode: str) -> nx.MultiDiGraph:
    """
    Construye un MultiDiGraph con:
      - atributo de nodo 'tokens' (frozenset; solo se usa en modo epa)
      - atributos de arista 'function' y 'color' (normalizados)
    Los IDs de nodo originales se conservan únicamente para reportar diffs
    legibles; el isomorfismo se calcula vía node_match/edge_match, no por id.
    """
    if mode not in ("states", "epa"):
        raise ValueError(f"mode debe ser 'states' o 'epa', recibido: {mode!r}")

    g = nx.MultiDiGraph()
    for node_id, raw_node in raw.nodes.items():
        tokens = _split_node_label_tokens(raw_node.label) if mode == "epa" else frozenset()
        g.add_node(node_id, tokens=tokens, original_label=raw_node.label)

    for e in raw.edges:
        g.add_edge(
            e.source, e.target,
            function=normalize_function_name(e.label),
            color=normalize_color(e.color),
            original_label=e.label,
        )
    return g


def node_match_factory(mode: str):
    if mode == "epa":
        def node_match(attrs1: dict, attrs2: dict) -> bool:
            return attrs1.get("tokens", frozenset()) == attrs2.get("tokens", frozenset())
        return node_match
    return lambda attrs1, attrs2: True  # modo states: no se compara nada del nodo


def multi_edge_match(edges1: dict, edges2: dict) -> bool:
    """
    edge_match para MultiDiGraphMatcher: recibe TODAS las aristas paralelas
    entre un par de nodos candidatos, como {edge_key: {'function', 'color'}}.
    Dos paquetes de aristas paralelas son equivalentes si tienen el mismo
    multiset de pares (function, color).
    """
    def as_multiset(edges: dict):
        return Counter((attrs.get("function"), attrs.get("color")) for attrs in edges.values())
    return as_multiset(edges1) == as_multiset(edges2)


# =============================================================================
# SECCIÓN 3: Comparación (isomorfismo VF2 + reporte de diffs)
# =============================================================================

@dataclass
class ComparisonResult:
    are_equal: bool
    mode: str
    graph1_path: str
    graph2_path: str
    node_count_1: int
    node_count_2: int
    edge_count_1: int
    edge_count_2: int
    node_mapping: dict | None = None  # solo si are_equal: id_grafo1 -> id_grafo2
    global_edge_profile_diff: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def summary_lines(self) -> list[str]:
        lines = []
        verdict = "IGUALES" if self.are_equal else "DIFERENTES"
        lines.append(f"Resultado ({self.mode}): los grafos son {verdict}")
        lines.append(f"  Grafo 1: {self.graph1_path}  -> nodos={self.node_count_1}, aristas={self.edge_count_1}")
        lines.append(f"  Grafo 2: {self.graph2_path}  -> nodos={self.node_count_2}, aristas={self.edge_count_2}")
        if self.are_equal and self.node_mapping is not None:
            lines.append("  Mapeo de nodos (grafo1 -> grafo2):")
            for n1, n2 in sorted(self.node_mapping.items(), key=lambda kv: str(kv[0])):
                lines.append(f"    {n1!r} -> {n2!r}")
        if not self.are_equal:
            if self.node_count_1 != self.node_count_2:
                lines.append(
                    f"  Diferencia evidente: distinta cantidad de nodos "
                    f"({self.node_count_1} vs {self.node_count_2})"
                )
            if self.edge_count_1 != self.edge_count_2:
                lines.append(
                    f"  Diferencia evidente: distinta cantidad de aristas "
                    f"({self.edge_count_1} vs {self.edge_count_2})"
                )
            if self.global_edge_profile_diff:
                lines.append("  Diferencias en el perfil global de transiciones (función, color):")
                for d in self.global_edge_profile_diff:
                    lines.append(f"    {d}")
            if self.node_count_1 == self.node_count_2 and not self.global_edge_profile_diff:
                lines.append(
                    "  Misma cantidad de nodos/aristas y mismo perfil global de transiciones, "
                    "pero no existe un mapeo de nodos válido (estructura/conectividad distinta)."
                )
        for note in self.notes:
            lines.append(f"  Nota: {note}")
        return lines


def _global_edge_profile(g: nx.MultiDiGraph) -> Counter:
    return Counter((data.get("function"), data.get("color")) for _, _, data in g.edges(data=True))


def _profile_diff(profile1: Counter, profile2: Counter) -> list[str]:
    diffs = []
    keys = set(profile1) | set(profile2)
    for key in sorted(keys, key=lambda k: (k[0] or "", k[1] or "")):
        c1, c2 = profile1.get(key, 0), profile2.get(key, 0)
        if c1 != c2:
            func, color = key
            diffs.append(f"(función={func!r}, color={color!r}): grafo1={c1} ocurrencias, grafo2={c2} ocurrencias")
    return diffs


def compare_raw_graphs(raw1: RawGraph, raw2: RawGraph, mode: str) -> ComparisonResult:
    g1 = build_comparable_graph(raw1, mode)
    g2 = build_comparable_graph(raw2, mode)

    node_match = node_match_factory(mode)
    matcher = MultiDiGraphMatcher(g1, g2, node_match=node_match, edge_match=multi_edge_match)

    are_equal = matcher.is_isomorphic()
    mapping = next(matcher.isomorphisms_iter()) if are_equal else None

    profile1, profile2 = _global_edge_profile(g1), _global_edge_profile(g2)
    profile_diff = [] if are_equal else _profile_diff(profile1, profile2)

    notes = []
    if mode == "epa":
        notes.append(
            "Modo EPA: se comparó también el conjunto de funciones presentes en el "
            "label de cada nodo (incluyendo 't'), normalizado e ignorando agrupación/orden."
        )
    else:
        notes.append("Modo STATES: el label/nombre de cada estado se ignoró por completo.")

    return ComparisonResult(
        are_equal=are_equal,
        mode=mode,
        graph1_path=raw1.source_path,
        graph2_path=raw2.source_path,
        node_count_1=g1.number_of_nodes(),
        node_count_2=g2.number_of_nodes(),
        edge_count_1=g1.number_of_edges(),
        edge_count_2=g2.number_of_edges(),
        node_mapping=mapping,
        global_edge_profile_diff=profile_diff,
        notes=notes,
    )


# =============================================================================
# SECCIÓN 4: Runner de PASCo (subproceso + localización del .dot generado)
# =============================================================================

class PascoRunError(RuntimeError):
    pass


@dataclass
class PascoRunSpec:
    pasco_script: str
    file_name: str           # valor de --file (nombre base del contrato/config)
    mode: str                # 'states' o 'epa'
    must: bool                # True -> --must TRUE ("must"), False -> --must FALSE ("may")
    savepdf: bool = True
    python_executable: str = sys.executable
    extra_args: list[str] | None = None
    working_dir: str | None = None


def _bool_to_pasco_str(value: bool) -> str:
    return "TRUE" if value else "FALSE"


def build_pasco_command(spec: PascoRunSpec) -> list[str]:
    cmd = [
        spec.python_executable, spec.pasco_script,
        "--file", spec.file_name,
        "--mode", spec.mode,
        "--must", _bool_to_pasco_str(spec.must),
        "--savepdf", _bool_to_pasco_str(spec.savepdf),
    ]
    if spec.extra_args:
        cmd.extend(spec.extra_args)
    return cmd


def run_pasco(spec: PascoRunSpec, timeout_seconds: int = 600) -> subprocess.CompletedProcess:
    cmd = build_pasco_command(spec)
    cwd = spec.working_dir or os.path.dirname(os.path.abspath(spec.pasco_script))
    print(f"[pasco_runner] Ejecutando: {' '.join(cmd)}  (cwd={cwd})", file=sys.stderr)
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout_seconds)
    except FileNotFoundError as e:
        raise PascoRunError(f"No se pudo ejecutar PASCo. Revisá --pasco-script y --python. Detalle: {e}") from e
    except subprocess.TimeoutExpired as e:
        raise PascoRunError(f"PASCo no terminó en {timeout_seconds}s. Detalle: {e}") from e

    if result.stdout:
        print(result.stdout, file=sys.stderr)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    if result.returncode != 0:
        raise PascoRunError(
            f"PASCo.py terminó con código de error {result.returncode}.\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def guess_dot_output_path(spec: PascoRunSpec, search_dir: str | None = None, name_pattern: str | None = None) -> str:
    """
    Mejor esfuerzo para encontrar el archivo de grafo generado por PASCo para
    este spec. IMPORTANTE: PASCo no genera un .dot con extensión literal
    ".dot" -- genera "{file}_Mode.{mode}" (ej: "EscrowVault_Mode.states" o
    "EscrowVault_Mode.epa"), donde la EXTENSIÓN del archivo es el modo. El
    contenido es texto formato DOT igual, solo cambia el nombre/extensión.

    Prueba name_pattern (si se dio) o una lista de patrones comunes (el
    confirmado primero); si ninguno existe en disco, cae a "el archivo más
    reciente con extensión .{mode} en el directorio".

    NOTA: a la fecha no tengo confirmado si --must TRUE vs FALSE generan
    nombres distintos (sufijo o carpeta separada) o si sobreescriben el mismo
    archivo. Por eso run_and_compare copia cada archivo detectado a una
    carpeta temporal exclusiva inmediatamente después de cada corrida, antes
    de lanzar la siguiente -- así el resultado es correcto aunque el nombre
    se repita entre corridas must/may.
    """
    cwd = search_dir or spec.working_dir or os.path.dirname(os.path.abspath(spec.pasco_script))
    must_str = _bool_to_pasco_str(spec.must)
    ext = spec.mode  # 'states' o 'epa': la extensión real del archivo generado

    candidate_patterns = [name_pattern] if name_pattern else [
        "{file}_Mode.{mode}",       # patrón confirmado por el usuario
        "{file}_mode.{mode}",       # variante de capitalización, por robustez
        "{file}.{mode}",
        "{file}_{must}_Mode.{mode}",
        "{file}_{must_lower}_Mode.{mode}",
        os.path.join("output", "{file}_Mode.{mode}"),
        os.path.join("results", "{file}_Mode.{mode}"),
    ]

    for pattern in candidate_patterns:
        candidate = pattern.format(file=spec.file_name, mode=spec.mode, must=must_str, must_lower=must_str.lower())
        full_path = candidate if os.path.isabs(candidate) else os.path.join(cwd, candidate)
        if os.path.isfile(full_path):
            return full_path

    # Fallback: el archivo más reciente con extensión .{mode} en el directorio
    # (hasta 2 niveles de profundidad). Se busca por la extensión del modo
    # (.states o .epa), NO por ".dot", ya que PASCo no usa esa extensión.
    newest_path, newest_mtime = None, -1.0
    target_suffix = f".{ext}".lower()
    for root, dirs, files in os.walk(cwd):
        depth = root[len(cwd):].count(os.sep)
        if depth > 2:
            dirs[:] = []
            continue
        for fname in files:
            if fname.lower().endswith(target_suffix):
                fpath = os.path.join(root, fname)
                mtime = os.path.getmtime(fpath)
                if mtime > newest_mtime:
                    newest_mtime, newest_path = mtime, fpath

    if newest_path is None:
        raise PascoRunError(
            f"No se encontró ningún archivo *.{ext} en {cwd!r} tras correr PASCo para "
            f"file={spec.file_name!r} mode={spec.mode!r} must={must_str!r}. "
            f"Probá pasar --dot-name-pattern con el patrón real, o revisá la salida de PASCo."
        )
    print(
        f"[pasco_runner] Aviso: no se encontró un .dot con los patrones probados; "
        f"se usó el modificado más recientemente como mejor suposición: {newest_path}",
        file=sys.stderr,
    )
    return newest_path


def run_pasco_and_get_dot(spec: PascoRunSpec, name_pattern: str | None = None) -> str:
    launch_time = time.time()
    run_pasco(spec)
    dot_path = guess_dot_output_path(spec, name_pattern=name_pattern)
    if os.path.getmtime(dot_path) < launch_time - 1:
        print(
            f"[pasco_runner] Aviso: el .dot encontrado ({dot_path}) parece más viejo que "
            f"esta corrida de PASCo (puede ser de una corrida anterior). Verificá o ajustá "
            f"--dot-name-pattern.",
            file=sys.stderr,
        )
    return dot_path


# =============================================================================
# SECCIÓN 5: CLI
# =============================================================================

def _parse_bool_flag(value: str) -> bool:
    v = value.strip().lower()
    if v in ("true", "1", "yes", "y", "t"):
        return True
    if v in ("false", "0", "no", "n", "f"):
        return False
    raise argparse.ArgumentTypeError(f"Valor booleano inválido: {value!r} (usar true/false)")


@dataclass
class LoadedGraph:
    label: str          # identificador legible para el reporte
    dot_path: str
    raw: RawGraph


def _load_graphs_from_paths(paths: list[str], labels: list[str] | None = None) -> list[LoadedGraph]:
    loaded = []
    for i, path in enumerate(paths):
        try:
            raw = parse_dot_file(path)
        except (OSError, ValueError) as e:
            print(f"Error leyendo/parseando {path!r}: {e}", file=sys.stderr)
            sys.exit(1)
        loaded.append(LoadedGraph(label=labels[i] if labels else path, dot_path=path, raw=raw))
    return loaded


def _compare_all_pairs(graphs: list[LoadedGraph], mode: str) -> list[tuple[LoadedGraph, LoadedGraph, ComparisonResult]]:
    return [(g1, g2, compare_raw_graphs(g1.raw, g2.raw, mode=mode)) for g1, g2 in itertools.combinations(graphs, 2)]


def _print_pairwise_results(results: list[tuple[LoadedGraph, LoadedGraph, ComparisonResult]]) -> None:
    for g1, g2, result in results:
        print("=" * 78)
        print(f"Comparando: {g1.label}  <->  {g2.label}")
        print("-" * 78)
        for line in result.summary_lines():
            print(line)
    print("=" * 78)


def _print_summary_matrix(graphs: list[LoadedGraph], results: list[tuple[LoadedGraph, LoadedGraph, ComparisonResult]]) -> None:
    if len(graphs) <= 2:
        return
    print()
    print("Matriz resumen (IGUAL / DIFERENTE):")
    lookup = {}
    for g1, g2, result in results:
        lookup[(g1.label, g2.label)] = result.are_equal
        lookup[(g2.label, g1.label)] = result.are_equal

    labels = [g.label for g in graphs]
    col_width = max(max(len(l) for l in labels), 9) + 2
    print(" " * col_width + "".join(f"{l[:col_width-1]:<{col_width}}" for l in labels))
    for li in labels:
        row = f"{li[:col_width-1]:<{col_width}}"
        for lj in labels:
            cell = "—" if li == lj else ("IGUAL" if lookup[(li, lj)] else "DIST")
            row += f"{cell:<{col_width}}"
        print(row)
    print()


def _results_to_json(results: list[tuple[LoadedGraph, LoadedGraph, ComparisonResult]]) -> list[dict]:
    out = []
    for g1, g2, result in results:
        d = asdict(result)
        d["graph1_label"] = g1.label
        d["graph2_label"] = g2.label
        out.append(d)
    return out


def cmd_compare(args: argparse.Namespace) -> None:
    if len(args.dot_files) < 2:
        print("Se necesitan al menos 2 archivos .dot para comparar.", file=sys.stderr)
        sys.exit(1)
    graphs = _load_graphs_from_paths(args.dot_files)
    results = _compare_all_pairs(graphs, mode=args.mode)

    if not args.json_only:
        _print_pairwise_results(results)
        _print_summary_matrix(graphs, results)
    if args.json or args.json_only:
        print(json.dumps(_results_to_json(results), indent=2, ensure_ascii=False))


@dataclass
class ContractSpec:
    file_name: str
    must: bool


def _parse_contract_specs(args: argparse.Namespace) -> list[ContractSpec]:
    contracts = args.contract
    musts = args.must
    if not contracts:
        print("Hay que pasar al menos un --contract.", file=sys.stderr)
        sys.exit(1)

    if len(musts) == 1:
        musts = musts * len(contracts)
    elif len(musts) != len(contracts):
        print(
            f"Cantidad de --must ({len(musts)}) no coincide con cantidad de --contract "
            f"({len(contracts)}). Pasá un único --must global, o uno por --contract en el mismo orden.",
            file=sys.stderr,
        )
        sys.exit(1)

    return [ContractSpec(file_name=c, must=m) for c, m in zip(contracts, musts)]


def cmd_run_and_compare(args: argparse.Namespace) -> None:
    contract_specs = _parse_contract_specs(args)

    # Carpeta temporal exclusiva de esta invocación: evita que una corrida de
    # PASCo pise el .dot de otra cuando dos contratos (p.ej. must vs may del
    # mismo --file) generan el archivo con el mismo nombre predecible.
    run_tmp_dir = tempfile.mkdtemp(prefix="pasco_compare_run_")

    loaded: list[LoadedGraph] = []
    try:
        for idx, spec in enumerate(contract_specs):
            run_spec = PascoRunSpec(
                pasco_script=args.pasco_script,
                file_name=spec.file_name,
                mode=args.mode,
                must=spec.must,
                savepdf=args.savepdf,
                python_executable=args.python,
                extra_args=args.pasco_arg,
                working_dir=args.pasco_workdir,
            )
            try:
                dot_path = run_pasco_and_get_dot(run_spec, name_pattern=args.dot_name_pattern)
            except PascoRunError as e:
                print(f"Error corriendo PASCo para {spec.file_name!r} (must={spec.must}): {e}", file=sys.stderr)
                sys.exit(1)

            # Copia inmediata a un destino único de esta corrida, ANTES de
            # lanzar la próxima ejecución de PASCo (que podría sobrescribir
            # el mismo nombre de archivo si el patrón de salida no distingue
            # must/may).
            must_tag = "must" if spec.must else "may"
            safe_copy_path = os.path.join(run_tmp_dir, f"{idx:02d}_{spec.file_name}_{args.mode}_{must_tag}.dot")
            shutil.copy2(dot_path, safe_copy_path)

            try:
                raw = parse_dot_file(safe_copy_path)
            except (OSError, ValueError) as e:
                print(f"Error leyendo/parseando el .dot generado ({dot_path!r}): {e}", file=sys.stderr)
                sys.exit(1)

            raw.source_path = dot_path  # trazabilidad: ruta original generada por PASCo
            loaded.append(LoadedGraph(label=f"{spec.file_name} [{args.mode}/{must_tag}]", dot_path=dot_path, raw=raw))

        results = _compare_all_pairs(loaded, mode=args.mode)

        if not args.json_only:
            _print_pairwise_results(results)
            _print_summary_matrix(loaded, results)
        if args.json or args.json_only:
            print(json.dumps(_results_to_json(results), indent=2, ensure_ascii=False))
    finally:
        shutil.rmtree(run_tmp_dir, ignore_errors=True)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pasco_compare.py",
        description="Compara grafos .dot generados por PASCo (modo states o epa).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- subcomando: compare (solo comparar .dot ya generados) ---
    p_compare = subparsers.add_parser("compare", help="Compara archivos .dot ya generados (no corre PASCo).")
    p_compare.add_argument("--mode", choices=["states", "epa"], required=True, help="Modelo de comparación a aplicar.")
    p_compare.add_argument("dot_files", nargs="+", help="Rutas a 2 o más archivos .dot a comparar entre sí (todos los pares).")
    p_compare.add_argument("--json", action="store_true", help="Además del texto, imprimir reporte JSON.")
    p_compare.add_argument("--json-only", action="store_true", help="Imprimir solo el reporte JSON (sin texto).")
    p_compare.set_defaults(func=cmd_compare)

    # --- subcomando: run-and-compare (correr PASCo + comparar) ---
    p_run = subparsers.add_parser("run-and-compare", help="Corre PASCo.py para uno o más contratos y compara los .dot resultantes.")
    p_run.add_argument("--pasco-script", required=True, help="Ruta a PASCo.py")
    p_run.add_argument("--python", default=sys.executable, help="Ejecutable de Python para correr PASCo.py (default: el mismo que corre este script).")
    p_run.add_argument("--mode", choices=["states", "epa"], required=True, help="Se pasa tal cual a PASCo (--mode) y define el modelo de comparación.")
    p_run.add_argument("--contract", action="append", required=True, help="Nombre base del contrato/config (--file de PASCo). Repetir para comparar varios.")
    p_run.add_argument(
        "--must", action="append", type=_parse_bool_flag, default=None,
        help=(
            "true (contrato 'must') o false (contrato 'may'), se pasa como --must a PASCo. "
            "Pasalo una sola vez para aplicar a todos los --contract, o repetilo en el mismo "
            "orden que --contract para usar un valor distinto por contrato (ej: comparar la "
            "misma config en must vs may)."
        ),
    )
    p_run.add_argument("--savepdf", type=_parse_bool_flag, default=True, help="Se pasa tal cual a PASCo (--savepdf). Default: true.")
    p_run.add_argument("--pasco-arg", action="append", default=None, help="Argumento adicional para PASCo.py tal cual (repetible).")
    p_run.add_argument("--pasco-workdir", default=None, help="Directorio de trabajo para correr PASCo.py (default: carpeta de PASCo.py).")
    p_run.add_argument(
        "--dot-name-pattern", default=None,
        help=(
            "Plantilla del nombre del archivo de grafo generado por PASCo, con "
            "placeholders {file} {mode} {must} {must_lower}. Default confirmado: "
            "'{file}_Mode.{mode}' (ej: EscrowVault_Mode.states / EscrowVault_Mode.epa; "
            "la extensión ES el modo, no '.dot'). Si tu PASCo usa otro patrón, pasalo acá."
        ),
    )
    p_run.add_argument("--json", action="store_true", help="Además del texto, imprimir reporte JSON.")
    p_run.add_argument("--json-only", action="store_true", help="Imprimir solo el reporte JSON (sin texto).")
    p_run.set_defaults(func=cmd_run_and_compare, must=None)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.command == "run-and-compare" and args.must is None:
        print("Falta --must (true para contratos 'must', false para contratos 'may'). Pasalo al menos una vez.", file=sys.stderr)
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()