import re 
import pprint
# map all RAW STRINGS to a node. probably some intermediate structure for building tree idk
nodemap = dict()

#  map artId to list of all nodes with artId value
art_nodemap = dict()

#note: sometimes the scope is missing form the parent entry... need multiple re patterns and multiple handlings ig
LINE_RE= re.compile(r'\s*"([^"]+)" -> "([^"]+)"')
SCOPES = re.compile(r'compile|test|runtime|provided|system')

# parse raw dotgraph string into map of actual values
def parse_values(str):
    retVal = dict()
    substrs = str.split(':')
    substrlen = len(substrs)

    if substrlen == 4:  
        retVal['grpId'], retVal['artId'], retVal['packaging'], retVal['version'] = substrs
    elif substrlen == 5:
        retVal['grpId'], retVal['artId'], retVal['packaging'], retVal['version'], last_ele = substrs
        if SCOPES.match(last_ele):
            retVal['scope'] = last_ele
        else: 
            retVal['classifier'] = last_ele
    elif substrlen == 6: 
        retVal['grpId'], retVal['artId'], retVal['packaging'], retVal['version'], retVal['classifier'], retVal['scope'] = substrs
    else:
        print(f"ERRRROR NO PARSING POSSIBLE FOR '{str}'")
    return retVal

# go figure. print tree where node = root
def print_tree(node, depth=0):
    indent = '  ' * depth 
    print(f'{indent}{node['value']}')
    for c in node['children']:
        print_tree(c, depth + 1)

# creates nodes, populates nodemap according to line
def process_line(line):
    capgrps = LINE_RE.search(line).groups()
    node = None
    child_node = dict()
    parent_str = capgrps[0]
    child_str = capgrps[1]
    pArtId = parse_values(parent_str)['artId']

    #simplified dogshit 
    if nodemap.get(parent_str) == None:
        node = dict()
        node['value'] = parent_str
        node['children'] = [child_node] 
        nodemap[parent_str] = node
        art_nodemap[pArtId] = [node]
    else:
        node = nodemap[parent_str]
        node['children'].append(child_node)
        art_nodemap[pArtId].append(parent_str)
    

    child_node['value'] = child_str 
    child_node['parent'] = node
    child_node['children'] = []

    nodemap[child_str] = child_node
    cArtId = parse_values(child_str)['artId']
    if art_nodemap.get(cArtId) == None:
        art_nodemap[cArtId] = [child_node]
    else: 
        art_nodemap[cArtId].append(child_node)

    #print(cArtId)
    #art_nodemap[cArtId] = [child_node]
    # print(capgrps)
    # cGrpId, cArtId, cDepType, cVer, cScope = child_str.split(":")
    # child_node['groupId'] = cGrpId
    # child_node['artId'] = cArtId
    # child_node['version'] = cVer

    # node['groupId'], node['artId'], pDepType, node['version'] = parent_str.split(":")

    # print(f"{parent_str} -> {node}")

# Given dotgraph filename, parse into tree and return root + map of artifactId -> node
def get_tree(fname = 'treed.dot'):
    lines = []
    with open(fname) as fp:
        lines = fp.readlines()

    # parse tree 
    root_key = re.search(r'\s*digraph\s*"(.+)"\s*{', lines[0]).groups()[0]
    print(root_key)
    for l in lines: 
        if LINE_RE.search(l.strip()) != None:    
            node = process_line(l)
        else:
            print(f"No matches made for line '{l}'")

    root = nodemap.get(root_key)
    #print_tree(root)
    #pprint.pprint(art_nodemap.keys())

    return (root, art_nodemap)

# TEST IF ALL ARTIFACTS OCCUR IN ARTNODEMAP. DELETE THIS LATER JUST LOCAL TESTING 
def test_artnodemap():
    allmatches = re.finditer(r'"[^:"]+:([^:"]+):[^->]+" -> "[^:"]+:([^:"]+):.+"', "\n".join(lines))
    for match in allmatches:
        for art in match.groups():
            if art_nodemap.get(art) == None:
                print(f"MISSING FORM NODAMEP {art}")