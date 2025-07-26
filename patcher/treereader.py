import re 
import pprint
# map all RAW DOTGRAPH STRINGS to a node. probably some intermediate structure for building tree idk
nodemap = dict()

#  map artId to list of all nodes with artId value
art_nodemap = dict()

#note: sometimes the scope is missing form the parent entry... need multiple re patterns and multiple handlings ig
LINE_RE= re.compile(r'\s*"([^"]+)" -> "([^"]+)"')
SCOPES = re.compile(r'compile|test|runtime|provided|system')

# encapsulated logic for adding node to artnodemap. handle adding node to non preexisting artId, handle duplicate additions
def addnode_art_nodemap(artId, node):
    existing_nodes = art_nodemap.get(artId)
    if existing_nodes == None:
        art_nodemap[artId] = [node]
    else:
        # Don't add if node is a duplicate already
        for enode in existing_nodes:
            enode['value'] == node['value']
            return 
        
        art_nodemap[artId].append(node)        
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

    if nodemap.get(parent_str) == None:
        node = dict()
        node['value'] = parent_str
        node['children'] = [child_node] 
        nodemap[parent_str] = node
        art_nodemap[pArtId] = [node]
    else:
        node = nodemap[parent_str]
        node['children'].append(child_node)
        addnode_art_nodemap(pArtId, node)
    

    child_node['value'] = child_str 
    child_node['parent'] = node
    child_node['children'] = []

    nodemap[child_str] = child_node
    cArtId = parse_values(child_str)['artId']
    addnode_art_nodemap(cArtId, child_node)


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
            process_line(l)

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

if __name__ == '__main__':
    tree, nm = get_tree('./runtime/debugtree.dot')
    pprint.pprint([x['value'] for x in nm['jackson-databind']])
