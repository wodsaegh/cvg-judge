import angr
import archinfo
import networkx as nx
import matplotlib.pyplot as plt
import json


#make a dict of hexadecimal and decimal adresses
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


#make a list of all adresses
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
    sorted_instr_list =  sorted(instr_dict.items(), key=lambda x:x[0])
    return sorted_instr_list
#get the raw text from the node
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

#function that decides wether the arrow is full or dashed
def decide_jump(src,dest,instr_list):
    src_ins = src.block.capstone.insns[-1]
    dest_ins = dest.block.capstone.insns[0]
    index_src = [el[0] for el in instr_list].index(src_ins.address)
    index_dest = [el[0] for el in instr_list].index(dest_ins.address)
    if index_dest-index_src == 1:
        return True
    return False

def get_insns(node,instr_list):
    nodeinsns = ""
    for insn in node.block.capstone.insns:
        nodeinsns+= str([el[0] for el in instr_list].index(insn.address)) +","

    return nodeinsns[:-1]

#create the nodes that will be in the nodes json
def create_nodes(cfg,instr_list):
    nodelist = []
    for node in cfg.nodes():
        nodeinsns = get_insns(node,instr_list)
        nodelist.append(nodeinsns)
    return nodelist


#create the edges that will be in the edges json
def create_edges(cfg,instr_list):
    edgedict = {"Ijk_Ret" : False , "Ijk_Call": False, "Ijk_FakeRet" : True, 'Ijk_Boring' : "decide"}
    edges = []
    for src, dst, data in cfg.graph.edges(data=True):
        edge = {}
        edge_kind = data["jumpkind"]
        edge["dashes"]= edgedict[edge_kind] 
        if(edge["dashes"] == "decide"):
            edge["dashes"]= decide_jump(src,dst,instr_list)
        edge["from"]= get_insns(src,instr_list)
        edge["to"]= get_insns(dst,instr_list)
        json_edge = json.dumps(edge,indent = 3)
        edges.append(edge)
    return edges


if __name__ == "__main__":
    p = angr.Project("test", auto_load_libs=False)
    # Perform full program analysis
    cfg = p.analyses.CFGFast()
    # func_hexwb, func_decwb = gen_dicts(cfg) 
    # addr_list = gen_addr_list(cfg)
    instr_list = gen_instr_list(cfg)
    nodelist = create_nodes(cfg,instr_list)

    edgeslist = create_edges(cfg,instr_list)
    graph_dict = {
    'nodes': nodelist,
    'edges': edgeslist
    }
    graph_json = json.dumps(graph_dict,indent = 2)
    with open("graph.json", "w") as outfile:
        outfile.write(graph_json)

