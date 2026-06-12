import os
import networkx as nx
import pydot
import Benchmark_info
import time
from os.path import expanduser

### Borrador: comparar los dots generados en Alloy con los generados en PASCO

def load_dot_file(file_path, considerTimeouts=False, considerConstructor=True, considerColor=False):
    graph = pydot.graph_from_dot_file(file_path)[0]

    # Remove all attributes from the graph object for all edges, except attribute "label" and "color"
    for edge in graph.get_edge_list():
        label = edge.get('label')
        color = edge.get('color')
        if color is None:
            color = '\"black\"'
        edge.obj_dict['attributes'].clear()
        edge.set_label(label)
        edge.set_color(color)
    

    dot_representation = graph.to_string()
    # Divide el formato DOT en líneas
    dot_lines = dot_representation.split('];\n')
    #saco /n
    dot_lines = [line.replace("digraph G {","").replace("\n","") for line in dot_lines]
    outgoing_edges = {}
    total_edges = 0
    for line in dot_lines:
        if '->' in line:
            parts = line.strip().split('->')
            from_node = parts[0].strip()
            to_node = parts[1].split('[')[0].strip()
            full_edge_name = "constructor" if "[label=constructor" in parts[1] else parts[1].split('label="')[1].split('"')[0]
            if "?" in full_edge_name and not considerTimeouts:
                continue
            full_edge_name = full_edge_name.replace("?","") # remove ? para no contar de más
            for edge_name in full_edge_name.split(");"):
                if not edge_name:
                    continue
                if not considerConstructor and "constructor" in edge_name:
                    continue
                total_edges += 1
                edge_name = edge_name.split("(")[0].strip().lower()
                key = str(from_node)+str(to_node)
                if considerColor:
                    color = parts[1].split('color="')[1].split('"')[0] if 'color=' in parts[1] else "black"
                    edge_name_and_color = edge_name + "_" + color
                else:
                    edge_name_and_color = edge_name
                if key in outgoing_edges:
                    outgoing_edges[key].append(edge_name_and_color)
                else:
                    outgoing_edges[key] = [edge_name_and_color]

    edge_sets = ["".join(sorted(outgoing_edges[node])) for node in outgoing_edges]


    nx_graph = nx.DiGraph()
    for edge in graph.get_edge_list():
        if considerTimeouts:
            edge_name = edge.get('label')
            if "?" in edge_name:
                continue
        source = edge.get_source()
        target = edge.get_destination()
        nx_graph.add_edge(u_of_edge=source, v_of_edge=target)

    return nx_graph, edge_sets, total_edges, nx_graph.number_of_nodes()



def are_dot_files_equivalent(file1, file2, considerTimeout):
    try:
        g1, es1, t1, _ = load_dot_file(file1, considerTimeout)
        g2, es2, t2, _ = load_dot_file(file2, considerTimeout)
    except Exception as e:
        print(e)
        exit(1)
        # return False
    # print(sorted(es1))
    # print()
    # print(sorted(es2))
    # print(sorted(es1) == sorted(es2))
    # print("size: "+str(t1)+" "+str(t2))
    return sorted(es1) == sorted(es2) and nx.is_isomorphic(g1,g2)

def discover_new_transitions(file1, file2, considerTimeout):
    try:
        g1, es1, t1 = load_dot_file(file1, considerTimeout)
        g2, es2, t2 = load_dot_file(file2, considerTimeout)
    except Exception as e:
        print(e)
        exit(1)
        # return False
    return t2 > t1


def diff(file1Name, file2Name, considerTimeouts=False):
    if not are_dot_files_equivalent(file1Name, file2Name, considerTimeouts):
        print(file1Name + " is different from " + file2Name)
        return True
        # differences(file1Name, file2Name)
    return False


def get_alloy_subjects(subjects, benchmark):
    solidityabstractor_subjects_b1 = ["AssetTransferFixed_Mode.states", "AssetTransfer_Mode.states", "BasicProvenanceFixed_Mode.states", "BasicProvenance_Mode.states", "DefectiveComponentCounterFixed_Mode.states", "DefectiveComponentCounter_Mode.states", "DigitalLockerFixed_Mode.states", "DigitalLocker_Mode.states", "FrequentFlyerRewardsCalculator_Mode.states", "HelloBlockchainFixed_Mode.states", "HelloBlockchain_Mode.states", "RefrigeratedTransportationFixed_Mode.states", "RefrigeratedTransportation_Mode.states", "RoomThermostat_Mode.states", "SimpleMarketplaceFixed_Mode.states", "SimpleMarketplace_Mode.states"]
    alloy_subjects_b1 = ["AssetTransfer_fixed", "AssetTransfer_original", "BasicProvenance_fixed", "BasicProvenance_original", "DefectiveComponentCounter_fixed", "DefectiveComponentCounter_original", "DigitalLocker_fixed", "DigitalLocker_original", "FrequentFlyerRewardsCalculator_original", "HelloBlockchain_fixed", "HelloBlockchain_original", "RefrigeratedTransportation_fixed", "RefrigeratedTransportation_original", "RoomThermostat_original", "SimpleMarketplace_fixed", "SimpleMarketplace_original"]
    
    solidityabstractor_subjects_b2 = ["RefundEscrow_Mode.states", "RefundEscrow_Mode.epa", "RefundEscrowWithdraw_Mode.epa", "EscrowVault_Mode.states", "EscrowVault_Mode.epa", "EPXCrowdsale_Mode.states", "EPXCrowdsale_Mode.epa", "EPXCrowdsaleIsCrowdsaleClosed_Mode.epa", "CrowdfundingTime_Base_Mode.epa", "CrowdfundingTime_BaseBalance_Mode.epa", "CrowdfundingTime_BaseBalanceFix_Mode.epa", "ValidatorAuction_Mode.states", "ValidatorAuction_Mode.epa", "ValidatorAuction_withdraw_Mode.epa", "SimpleAuction_Mode.epa", "SimpleAuctionTime_Mode.epa", "SimpleAuctionEnded_Mode.epa",       "SimpleAuctionHB_Mode.states", "Auction_Mode.epa",      "AuctionEnded_Mode.epa", "AuctionWithdraw_Mode.epa",        "RockPaperScissors_Mode.states", "RockPaperScissors_Mode.epa"]
    alloy_subjects_b2 =              [            "RefundEscrow",      "RefundEscrow_EPA",        "RefundEscrow_withdrawA",             "EscrowVault",      "EscrowVault_EPA",             "EPXCrowdsale",      "EPXCrowdsale_EPA",     "EPXCrowdsale_EPA_isCrowdSaleClosed",          "CrowdfundingTime_Base",          "CrowdfundingTime_BaseBalance",          "CrowdfundingTime_BaseBalanceFix",             "ValidatorAuction",      "ValidatorAuction_EPA",    "ValidatorAuction_WithdrawA+NotA",      "SimpleAuction_EPA",    "SimpleAuction_EPA_time",          "SimpleAuction+Ended", "SimpleAuction+Ended+highestBidder",      "Auction_EPA", "Auction_EPA+predicateEnded",    "Auction_EPA_withdrawA", "RockPaperScissors+predicateOneWinner",      "RockPaperScissors_EPA"]
    
    to_find_verisol = []
    to_find_alloy = []
    if benchmark == "B1":
        to_find_verisol = solidityabstractor_subjects_b1
        to_find_alloy = alloy_subjects_b1
    elif benchmark == "B2":
        to_find_verisol = solidityabstractor_subjects_b2
        to_find_alloy = alloy_subjects_b2
    else:
        print("solo benchmark B1 o B2!")
        exit(1)
    ret = []
    for i in range(len(subjects)):
        for j in range(len(to_find_verisol)):
            if subjects[i] == to_find_verisol[j]:
                ret.append(to_find_alloy[j])
    return ret


home = expanduser("~")
repo_path = os.path.join(home, "Repos","SolidityAbstractor")
# D:\Documentos\Git\SolidityAbstractor
# repo_path = "D:\\Documentos\\Git\\SolidityAbstractor"
repo_alloy = os.path.join(home, "Repos","sosym23")

def get_diff_prev(solidityabstractor_subjects, k_prev, k_curr, timeout):
    path_solidityabstractor_prev = f"{repo_path}\\graph\\k_{k_prev}\\to_{timeout}"
    path_solidityabstractor_curr = f"{repo_path}\\graph\\k_{k_curr}\\to_{timeout}"
    
    cant_dif = 0
    subjects_diff = []

    for i in range(len(solidityabstractor_subjects)):
        solidityabstractor_subject = solidityabstractor_subjects[i]
        if len(solidityabstractor_subject) == 2: # es una lista de configs [subject,mode]
            mode = "_Mode.epa" if solidityabstractor_subject[1][0] == 'e' else "_Mode.states"
            solidityabstractor_subject = solidityabstractor_subject[0].replace("Config",mode)
        solidityabstractor_dot_prev = os.path.join(path_solidityabstractor_prev, solidityabstractor_subject)
        solidityabstractor_dot_curr = os.path.join(path_solidityabstractor_curr, solidityabstractor_subject)
        if not os.path.exists(solidityabstractor_dot_prev):
            print(f"NO EXISTE ARCHIVO VERISOL {solidityabstractor_dot_prev}")
            continue
        if not os.path.exists(solidityabstractor_dot_curr):
            print(f"NO EXISTE ARCHIVO VERISOL {solidityabstractor_dot_curr}")
            continue
        ret = discover_new_transitions(solidityabstractor_dot_prev, solidityabstractor_dot_curr, False)
        if ret:
            subjects_diff.append(solidityabstractor_subjects[i])
            cant_dif += 1
    print("total diff: "+ str(cant_dif))
    print("diffs: ")
    print(subjects_diff)
    return subjects_diff

def get_diff(solidityabstractor_subjects, benchmark, k, timeout):
    path_solidityabstractor = f"{repo_path}\\graph\\k_{k}\\to_{timeout}"
    path_alloy = f"{repo_alloy}\\models_alloy\\{benchmark}\\"
    cant_dif = 0
    subjects_diff = set()
    subjects_eq = set()

    alloy_subjects = get_alloy_subjects(solidityabstractor_subjects, benchmark)
    if len(alloy_subjects) != len(solidityabstractor_subjects):
        print("Diferente cantidad de subjects alloy y solidityabstractor")
        exit(1)
    for i in range(len(alloy_subjects)):
        if solidityabstractor_subjects[i].endswith("_Mode.states") or solidityabstractor_subjects[i].endswith("_Mode.epa"):
            solidityabstractor_dot = os.path.join(path_solidityabstractor, solidityabstractor_subjects[i])
        else:
            print(f"agregar modo states o epa al subject '{solidityabstractor_subjects[i]}'")
        alloy_dot = os.path.join(path_alloy,alloy_subjects[i],alloy_subjects[i]+"_original_reachable.dot")
        if not os.path.exists(alloy_dot) or not os.path.exists(solidityabstractor_dot):
            if not os.path.exists(alloy_dot):
                print(f"NO EXISTE ARCHIVO ALLOY {alloy_dot}")
            if not os.path.exists(solidityabstractor_dot):
                print(f"NO EXISTE ARCHIVO VERISOL {solidityabstractor_dot}")
                # subjects_diff.add(solidityabstractor_subjects[i])
        else:
            ret = diff(solidityabstractor_dot, alloy_dot, False)
            if ret:
                subjects_diff.add(solidityabstractor_subjects[i])
                cant_dif += 1
            else:
                subjects_eq.add(solidityabstractor_subjects[i])
    print("total diff: "+ str(cant_dif))
    print("diffs: ")
    print(subjects_diff)
    return subjects_diff, subjects_eq



def main():
    benchmarks_to_run = ["B1", "B2", "B3"]
    # benchmarks_to_run = ["B3"]
    for Benchmark in benchmarks_to_run:
        if Benchmark == "B1":
            subjects_original = ["AssetTransferFixed_Mode.states", "AssetTransfer_Mode.states", "BasicProvenanceFixed_Mode.states", "BasicProvenance_Mode.states", "DefectiveComponentCounterFixed_Mode.states", "DefectiveComponentCounter_Mode.states", "DigitalLockerFixed_Mode.states", "DigitalLocker_Mode.states", "FrequentFlyerRewardsCalculator_Mode.states", "HelloBlockchainFixed_Mode.states", "HelloBlockchain_Mode.states", "RefrigeratedTransportationFixed_Mode.states", "RefrigeratedTransportation_Mode.states", "RoomThermostat_Mode.states", "SimpleMarketplaceFixed_Mode.states", "SimpleMarketplace_Mode.states"]
            # subjects_original = ["DigitalLockerFixed_Mode.states"]
        elif Benchmark == "B2":
            subjects_original = ["RefundEscrow_Mode.states", "RefundEscrow_Mode.epa", "RefundEscrowWithdraw_Mode.epa", "EscrowVault_Mode.states", "EscrowVault_Mode.epa", "EPXCrowdsale_Mode.states", "EPXCrowdsale_Mode.epa", "EPXCrowdsaleIsCrowdsaleClosed_Mode.epa", "CrowdfundingTime_Base_Mode.epa", "CrowdfundingTime_BaseBalance_Mode.epa", "CrowdfundingTime_BaseBalanceFix_Mode.epa", "ValidatorAuction_Mode.states", "ValidatorAuction_Mode.epa", "ValidatorAuction_withdraw_Mode.epa", "SimpleAuction_Mode.epa", "SimpleAuctionTime_Mode.epa", "SimpleAuctionEnded_Mode.epa", "SimpleAuctionHB_Mode.states", "Auction_Mode.epa", "AuctionEnded_Mode.epa", "AuctionWithdraw_Mode.epa", "RockPaperScissors_Mode.states", "RockPaperScissors_Mode.epa"]
            # subjects_original = ["EPXCrowdsale_Mode.states"]
        elif Benchmark == "B3":
            subjects_original = Benchmark_info.config_B3_1().extend(Benchmark_info.config_B3_2())
    
        subjects = subjects_original
        total_diff_antes = len(subjects)
        total_diff_despues = len(subjects)
        k_parameter = 4
        k_prev = k_parameter
        time_out = 600
        first = True
        tempFileName = "diff_result_"+Benchmark+".txt"
        init = time.time()
        while (len(subjects)>0) or first:
            if not first:
                k_parameter *= 2
            print(f"Con k={k_parameter}...")
            total_diff_antes = total_diff_despues
            total_subjects = len(subjects)
            Benchmark_info.main(subjects, 1, k_parameter, k_parameter, time_out)
            if not first:
                subjects = get_diff_prev(subjects, k_prev, k_parameter, time_out)
            total_diff_despues = len(subjects)
            with open(os.path.join(tempFileName), 'a+') as file:
                if first:
                    file.write(f"Benchmark: {Benchmark}\n")
                    file.write(f"time out: {time_out}\n")
                else:
                    file.write(f"k: {k_parameter}\n")
                    file.write(f"total diff: {total_diff_despues} de un total de {total_subjects}\n")
                    file.write("subjects diferentes:\n")
                    file.write(str(subjects)+"\n\n")
                file.close()
            first = False
            k_prev = k_parameter
        end = time.time()
        total_time = end-init
        print(f"Tiempo total: {total_time}")
        with open(os.path.join(tempFileName), 'a+') as file:
            file.write(f"Tiempo total: {total_time}\n\n")
            file.close()

        subjects = subjects_original
        alldiff = set()
        alleq = set()
        while k_parameter >= 4 and len(subjects)>0:
            subjects_diff, subjects_eq = get_diff(subjects, Benchmark, k_parameter, time_out)
            alldiff.update(subjects_diff)
            alleq.update(subjects_eq)
            subjects = set(subjects) - subjects_diff - subjects_eq
            subjects = list(subjects)
            tempFileName = "diff_result_"+Benchmark+".txt"
            with open(os.path.join(tempFileName), 'a+') as file:
                file.write(f"Con k=: {k_parameter}\n")
                file.write(f"Iguales ({len(subjects_eq)}): ")
                file.write(str(subjects_eq)+"\n")
                file.write(f"subjects diferentes ({len(subjects_diff)}):\n")
                file.write(str(subjects_diff)+"\n")
                file.write("Faltan revisar: ")
                file.write(str(subjects)+"\n\n")
                file.close()
            k_parameter = int(k_parameter/2)

        with open(os.path.join(tempFileName), 'a+') as file:
            file.write(f"Iguales({len(alleq)}): ")
            file.write(str(alleq)+"\n")
            file.write(f"subjects diferentes({len(alldiff)}):\n")
            file.write(str(alldiff)+"\n\n")
        
# para comparar dos abstracciones
# file_name = "EtherstoreReentrancy_Mode.epa"
# repo_path = os.path.join(home, "Repos","SolidityAbstractor")
# file1 = os.path.join(repo_path, "graph", "k_8", "to_600", file_name)
# file2 = os.path.join(repo_path, "graph", "k_16", "to_600", file_name)
# print(are_dot_files_equivalent(file1, file2, False))

def compare_diff_runs():
    # For two different paths, recursively compare files that end in .states or .epa
    # and generate a report of differences
    # path1 = r"C:\Users\j_god\Repos\SolidityAbstractor\graph"
    # path2 = r"C:\Users\j_god\Repos\SolidityAbstractor\graph_one_thread"
    path1 = r"C:\Users\j_god\Repos\Predicate_Queries_Alloy\examples\Benchmarks\B2"
    path2 = r"D:\Documentos\Git\imdea\subjects\Benchmark2\generated"
    # file_ends_with = [".states", ".epa"]
    file_ends_with = ["_parsed.dot"]
    diff_subjects = []
    eq_subjects = []
    for root, _, files in os.walk(path1):
        for file in files:
            if file.endswith(tuple(file_ends_with)):
                file_path1 = os.path.join(root, file)
                file_path2 = file_path1.replace(path1, path2)
                if not os.path.exists(file_path2):
                    print(f"El archivo {file_path2} no existe.")
                    continue
                # print(f"Comparando {file_path1} con {file_path2}")
                if diff(file_path1, file_path2):
                    diff_subjects.append((file_path1, file_path2))
                    print()
                else:
                    eq_subjects.append((file_path1, file_path2))

    print(f"Total de archivos con diferencias: {len(diff_subjects)}")
    for diff_subject in diff_subjects:
        print(diff_subject)
    print(f"Total de archivos iguales: {len(eq_subjects)}")
    # for eq_subject in eq_subjects:
    #     print(eq_subject)
    
compare_diff_runs()


# Para ejecutar Differ para todos los subjects de B1 y B2
# main()
