import angr
import matplotlib.pyplot as plt
import json
import subprocess
import sys

# make a dict of hexadecimal and decimal adresses
# def gen_dicts(cfg):
#     func_hexwb = {}
#     func_decwb = {}
#     for func_addr in cfg.kb.functions.keys():
#         func_name = cfg.kb.functions[func_addr].demangled_name
#         #print(func_addr)
#         func_hexwb["0x%x" %(func_addr)] = func_name
#         func_decwb[func_addr] = func_name
#         #print("Function address: 0x%x, Name: %s" % (func_addr, func_name))
#     #print(func_decwb)
#     return func_hexwb, func_decwb


# make a list of all adresses
# def gen_addr_list(cfg):
#     addr_list = []
#     for node in cfg.nodes():
#         for insn in node.block.capstone.insns:
#             addr_list.append("0x%x" %(insn.address))
#     return addr_list

def gen_instr_list(cfg):
    instr_dict = {}
    for node in cfg.nodes():
        block = node.block
        # Iterate over all instructions in the block
        for insn in block.capstone.insns:
            instr_dict[insn.address] = f"{insn.mnemonic} {insn.op_str}"
    sorted_instr_list = sorted(instr_dict.items(), key=lambda x: x[0])
    return sorted_instr_list
# get the raw text from the node
# def get_node_text(node,func_hexwb,func_decwb,addr_list):
#     nodestr = ""
#     for insn in node.block.capstone.insns:
#         if (insn.address in func_decwb.keys()):             #if it is the start of a function
#             nodestr+= (f"{func_decwb[insn.address]}: ")
#         if insn.op_str in func_hexwb.keys():                #if there is a call to a function
#             nodestr += (f"{insn.mnemonic} {func_hexwb[insn.op_str]} ")
#         elif insn.op_str in addr_list:                      #if there is a jump, currently issues with jump
#             nodestr += (f"{insn.mnemonic} ")
#         else:
#             nodestr += (f"{insn.mnemonic} {insn.op_str} ")     #string of mnemonic and operands
#     return nodestr

# function that decides wether the arrow is full or dashed


def decide_jump(src, dest, instr_list):
    src_ins = src.block.capstone.insns[-1]
    dest_ins = dest.block.capstone.insns[0]
    index_src = [el[0] for el in instr_list].index(src_ins.address)
    index_dest = [el[0] for el in instr_list].index(dest_ins.address)
    if index_dest-index_src == 1:
        return True
    return False


def get_insns(node, instr_list):
    nodeinsns = ""
    for insn in node.block.capstone.insns:
        nodeinsns += str([el[0]
                         for el in instr_list].index(insn.address)) + ","

    return nodeinsns[:-1]

# create the nodes that will be in the nodes json


def create_nodes(cfg, instr_list):
    nodelist = []
    extra_edges = []
    changed_nodes = {}
    for node in cfg.nodes():
        nodeinsns = get_insns(node, instr_list)
        inslist = nodeinsns.split(",")
        nodelist.append(nodeinsns)
    for j in range(len(nodelist)):  # needed for nodes that do not end in return
        copynodes = nodelist.copy()
        copynodes.remove(nodelist[j])
        for i in range(len(nodelist[j])):
            if (nodelist[j][i:] in copynodes):
                nodeinsns = nodelist[j][i:]
                extra_edges.append(
                    {"dashes": True, "from": nodelist[j][:i-1], "to": nodelist[j][i:]})
                changed_nodes[nodelist[j]] = nodelist[j][:i-1]
                nodelist.append(nodelist[j][:i-1])
                nodelist.remove(nodelist[j])

    return nodelist, extra_edges, changed_nodes


# create the edges that will be in the edges json
def create_edges(cfg, instr_list, changed_nodes):
    edgedict = {"Ijk_Ret": False, "Ijk_Call": False,
                "Ijk_FakeRet": True, 'Ijk_Boring': "decide"}
    edges = []
    fromlist = []
    tolist = []
    for src, dst, data in cfg.graph.edges(data=True):
        edge = {}
        edge_kind = data["jumpkind"]
        edge["dashes"] = edgedict[edge_kind]
        if (edge["dashes"] == "decide"):
            edge["dashes"] = decide_jump(src, dst, instr_list)
        edge["from"] = get_insns(src, instr_list)
        edge["to"] = get_insns(dst, instr_list)
        if (edge["to"] in changed_nodes.keys()):
            edge["to"] = changed_nodes[edge["to"]]
        json_edge = json.dumps(edge, indent=3)
        if (edge["from"] not in changed_nodes.keys()):
            edges.append(edge)

    return edges


if __name__ == "__main__":
    file = sys.argv[1]
    with open(file, "r") as file:
        solution_content = file.read()
    writefile = "writefile.s"
    try:
        if sys.argv[2].lower() == "intel":
            with open(writefile, "w") as file2:
                file2.write(".intel_syntax noprefix\n" +
                            solution_content + "\n")
            proc = subprocess.run(f"as {writefile} -o runcode", shell=True)
        elif sys.argv[2].lower() == "att":
            with open(writefile, "w") as file2:
                file2.write(solution_content)
            proc = subprocess.run(f"as {writefile} -o runcode", shell=True)
        elif sys.argv[2].lower() == "arm":
            with open(writefile, "w") as file2:
                file2.write(solution_content)
            proc = subprocess.run(
                f"arm-linux-gnueabihf-as {writefile} -o runcode", shell=True)

        else:
            print(
                "ERROR:Wrong architecture\nCorrect architectures: intel, ATT (=AT&T), ARM")

    except:
        print("ERROR:No architecture given.\nCorrect usage: python3 generateCVG.py <inputfile> <architecture> ")

    p = angr.Project("runcode", auto_load_libs=False)
    # Perform full program analysis
    cfg = p.analyses.CFGFast()
    # func_hexwb, func_decwb = gen_dicts(cfg)
    # addr_list = gen_addr_list(cfg)
    instr_list = gen_instr_list(cfg)
    nodelist, extra_edges, changed_nodes = create_nodes(cfg, instr_list)
    edgeslist = create_edges(cfg, instr_list, changed_nodes)
    for edge in extra_edges:
        edgeslist.append(edge)
    graph_dict = {
        'nodes': nodelist,
        'edges': edgeslist
    }
    graph_json = json.dumps(graph_dict, indent=2)
    with open("solution.json", "w") as outfile:
        outfile.write(graph_json)
