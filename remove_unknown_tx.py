# Remove transitions marked with "?" (not confirmed)
# input: dot file

import pydot

def remove_transitions(dot_file):
    graph = pydot.graph_from_dot_file(dot_file)[0]
    # Remove all attributes from the graph object for all edges, except attribute "label"
    for edge in graph.get_edge_list():
        label = edge.get('label')
        edge.obj_dict['attributes'].clear()
        edge.set_label(label)
    

    dot_representation = graph.to_string()
    # Divide el formato DOT en líneas
    dot_lines = dot_representation.split("\n")
    ret = ""
    removed_txs = 0
    for line in dot_lines:
        if '?' in line:
            removed_txs += 1
        else:
            ret += line + "\n"
            
    #salteo nodos que no tienen transiciones
    ret_filtrado = ""
    nodes_removed = 0
    to_remove = False
    for line in ret.split("\n"):
        #tengo que eliminar todas las lineas hasta cerrar lo que seria el label del nodo que saco
        if to_remove:
            if "]" in line:
                to_remove = False
                continue
            else:                
                continue
        #Si no es nodo (por ejemplo, es una transición) lo agrego
        if not "[label=" in line or "->" in line:
            ret_filtrado += line + "\n"
            continue
        #si es un nodo, sólo lo agrego en caso que sea origen o destino de una transición
        if not "->" in line:
            node = line.split("[label")[0].strip()
            found = False
            for edge in ret.split("\n"):
                if "->" in edge:
                    source = edge.split(" -> ")[0].strip()
                    dest = edge.split(" -> ")[1].strip()
                    if node == source or node in dest:
                        found = True
                        break
            if found:
                ret_filtrado += line + "\n"
            else:
                to_remove = True
                nodes_removed += 1            
    

    # print(ret_filtrado)
    # print(f"Removed {removed_txs} transitions marked with '?'")
    # print(f"Removed {nodes_removed} nodes without transitions")
    return ret_filtrado, removed_txs
    
