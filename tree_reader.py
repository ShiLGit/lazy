from lxml import etree, objectify
import os
import re
from pprint import pprint
import subprocess
import json
from utils import version_comp, LT, GT, EQ
DEBUG = False
ENUM_PARENT = "ENUM_PARENT"


def create_child_node(parent, dep, ver, node_map):
    child = {"children": [],"parent": parent,"dep": dep, "version": ver}
    parent['children'].append(child)
    node_map[dep] = child
    #TODO: need to cover possibility of multiple <grpId>:<artId> occurrences in the tree.
    #Possible approach: child = shortest path to a root node? (since we're using nodemap to eventually determine distance and whether dep needs an override or parent update) 
    # assuming this doesn't interfere with tree generation
    dprint(f'\t[p = {parent['dep']}] New node added {child['dep']}; child of {child['parent']['dep']}')
    return child

def clean_xml_namespaces(root):
    for element in root.getiterator():
        if isinstance(element, etree._Comment):
            continue
        element.tag = etree.QName(element).localname
    etree.cleanup_namespaces(root)

def print_tree(depth, node):
    indent = '\t' * depth
    print(f'{indent}[{depth}] {node['dep']}')
    for c in node['children']:
        print_tree(depth + 1, c)

def dprint(arg, parent = None):
    if DEBUG:
        print(f"DEBUG: {f'[p = {parent['dep']}]' if parent else ''}", arg)

#proj_root should not be hardcoded but taken as cmdline arg ofc
def get_submodule_matchers(proj_root):
    matchers = []
    for root, dirs, files in os.walk(proj_root):
        if "target" in root: 
            continue
        if 'pom.xml' in files:
        #xml_root = etree.parse(root + "/pom.xml").getroot()
            xml_root = etree.parse(root + "/pom.xml").getroot()
            clean_xml_namespaces(xml_root)
            try: 
                # Possible NPE if these tags somehow (illegally?) aren't present 
                grpId = xml_root.find("groupId").text 
                artId = xml_root.find("artifactId").text
                #
                matchers.append(rf"\[INFO\]\s*{grpId}:{artId}:.+")
            except Exception as e:
                print(f"Exception - tag not found in {root}/pom.xml: \n", e )
    return matchers

# Given a string from tree outputted by mvn dependency:tree (post token replacement), return (artifactId:grpId, packageVersion)
def get_node_key(string):
    #dprint(f"\tSTTRING = {string}")
    string = string.replace(" ", "").replace("$", "").replace("#", "").replace("@", "")
    substrs = string.split(":")
    #dprint("\tKEY = " + ':'.join([substrs[0], substrs[1]]))
    return (':'.join(substrs[0:2]), substrs[3])

# builds tree from descendant deps of parent arg if any
def scan_module_subtree(lines, start_idx, h_offset, parent, dep_watchlist, node_map, depth = 0):
    dprint(f'****************************CALL FOR SUBTREE OF [p = {parent['dep']}] ***************************************')
    #First line after parent line begins with # - direct child. Sometimes \- will be on same level as parent line so need to cover with first clause 
    if start_idx >= len(lines):
        dprint("Line index > len(lines); terminating", parent)
        return

    dprint(f"OFFSET LINE '{lines[start_idx][h_offset:]}'")

    if lines[start_idx][h_offset-1] == '#'or lines[start_idx][h_offset:][0] == '#':
        h_offset_incr = 0 if lines[start_idx][h_offset-1] == '#' else 1
        dprint(f"HOFFSET= {h_offset_incr}", parent )
        dep, ver = get_node_key(lines[start_idx])
        child = create_child_node(parent, dep, ver, node_map)
        dprint(f"edge case reached; calling subtree search for child {child['dep']}; hoffs={h_offset} ;hoffseti={h_offset_incr}", parent)
        scan_module_subtree(lines, start_idx + 1, h_offset + h_offset_incr, child, dep_watchlist, node_map, depth = 0)

    for i in range(start_idx, len(lines)):
        line = lines[i][h_offset:]
        dprint(f'[p = {parent['dep']}] line:"{lines[i]}";"{line}"')

        if line[0] == '@': # new 
            dep, ver = get_node_key(line)
            #TODO: What about duplicate packages?
            child = create_child_node(parent, dep, ver, node_map)
            node_map[dep] = child
            #build subtree of the new child
            dprint(f'\t[p = {parent['dep']}] building subtree of {child['dep']}')
            scan_module_subtree(lines, i + 1, h_offset + 1, child, dep_watchlist, node_map, depth + 1)
        elif line[0] == '$':
            #it's deeper than immediate children. leave up to recursive scanmodsubntree call to eventually process it 
            dprint(f"skipping processing for {line} to wait for rescursive calls", parent)
            continue
        else:
            dprint(f'\t[p = {parent['dep']}] Base case reached on line "{line}" (no token @/$/#). Terminating')
            dprint(f'****************************END OF CALL FOR SUBTREE OF [p = {parent['dep']}] ***************************************')

            return
 
def replace_tokens(line):
    index_stop = re.search(rf"[^\s]+\:[^\s]+", line)
    if index_stop == None:
        dprint(f"IN REPLACE_TOKENS(). NOT FOUND {line}")
        return ""
    index_stop = index_stop.start()
    dont_touch = line[index_stop:]
    mutable = line[0:index_stop]

    #Assuming these are special chars that don't shot up as the first char of a dep (y would they??)...
    mutable = mutable.replace("+- ", "@") #NEW
    mutable = mutable.replace(r"\- ", "#") #DIRECT CHILD OF ABOVE?
    mutable = mutable.replace("|  ", "$") # (WAS SIBLING). indicate that this line needs to be processed in a deeper recursive call

    line = mutable + dont_touch
    line = line.replace("[INFO] ", "")
    line = line.replace("   ", "$")
    return line.strip()

# THIS IS NOT COMPLETE U IDIOT. JUST PORTED LINES FROM MAIN(). WHO KNOWS
# NEEDS RETURN VALUE AND NEEDS TO ACCEPT NON HARDCODED ARGS TO FIND WHICH TREE TO CHECK
def parse_trees(lines, submodule_matchers):
    #maps 'groupId:artifactId' to a tree node
    node_map = dict()
    dep_watchlist = [] #supposed to be parsed from config..
    scan = False
    module_trees = []
    for i in range(0, len(lines)):
        line = lines[i].strip()
        treelines = []
        horizontal_scan_max = 0

        #latter clause is spaghetti for "at least one of submodules present in line. Looking for start of actual dependency tree"
        if "[INFO]" in line and sum([1 if bool(re.search(s, line)) else 0 for s in submodule_matchers]) > 0: 
            dprint("BUILDING TREE FOR " + line)
            line = line.strip().replace("[INFO] ", "")
            parent_key, parent_ver = get_node_key(line)

            dprint("ROOT KEY  = |" + parent_key+ "|")
            scan = True
            #populate treelines with parseable lines of dependency tree
            while scan == True and i < len(lines): 
                line = lines[i]
                #matching end of tree lines; alwways prints grpId:artId:... etc. 
                if not bool(re.search(".+:.+:.+", line)):
                    dprint(f"TERMINATING SCAN AT LINE {line}")
                    scan = False
                    break
                line = replace_tokens(line)
                treelines.append(line)
                scan_stop = re.search(r"[^\@\$\%]", line).start()
                if scan_stop > horizontal_scan_max:
                    horizontal_scan_max = scan_stop
                i = i + 1

            dprint("TREELINES START")
            for l in treelines: dprint(l)
            dprint("TREELINES END ")
            
            root = {"children": [],"parent": None,"dep": parent_key, "version": parent_ver}
            node_map[parent_key] = root
            scan_module_subtree(treelines, 1, 0, root, dep_watchlist, node_map)
            print_tree(0, root)
            module_trees.append(root)
        else:
            continue

    return (module_trees, node_map)

# Generate tree given the path to the root of the maven project
def generate_tree_from_scratch(proj_root ='./maven-modular'):

    #Get lines to parse
    #print(f'[STATUS] ~~~~~~~~~~~~~~~~~~~~~~~~ RUNNING MVN DEPENDENCY:TREE ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
    fp = open("./tree.txt", "r", encoding="utf-16", errors="ignore")
    #cmd = subprocess.run(['mvn', 'dependency:tree'], shell = True, stdout = fp)
    #print(f'{'[ERROR] MVN DEPENDENCY:TREE FAILED!!! ' if cmd.returncode != 0 else '[STATUS] MVN DEPENDENCY:TREE COMPLETED SUCCESSFULLY'}')
    lines = fp.readlines()
    fp.close()

    #get submodule names 
    submodule_matchers = get_submodule_matchers(proj_root)
    return parse_trees(lines, submodule_matchers)

# Given config + tree, return list of non-covered cves' profiles
def get_cve_nodes(node_map, config_path):
    config = None
    cve_nodes = []
    with open(config_path) as fp:
        config = json.loads(fp.read())["pom.xml"]
    
    problem_pkgs = config.keys()
    for pkg in problem_pkgs:
        pkg_node = node_map.get(pkg)
        # grpId:artId matches something in config; check if version is a target one and add to list if yes
        if  pkg_node != None: 
            for fix in config[pkg]:
                lower_bound, upper_bound = fix['range']
                lb_comparison = version_comp(pkg_node['version'], lower_bound)
                ub_comparison = version_comp(pkg_node['version'], upper_bound)
                # "if current version <= upper bound && current version >= lower bound..."
                if (lb_comparison == GT or lb_comparison == EQ) and (ub_comparison == LT or ub_comparison == EQ):
                    cve_nodes.append(pkg_node)

    return cve_nodes
            
#[INFO] io.jitpack:module2:jar:2.0-SNAPSHOT
if __name__ == "__main__":
    # print(f"FUCK {bool(re.search("\[INFO\]\s*io.jitpack:module2:.+", "[INFO] io.jitpack:module2:jar:2.0-SNAPSHOT"))}")
    # exit()
    (trees, node_map) = generate_tree_from_scratch('./maven-modular')
    #..when will you ever use tree
    print('fuckkk')
    print(get_cve_nodes(node_map, './config.json'))
   # get_tree()