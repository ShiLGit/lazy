from lxml import etree, objectify
import os
import re
from pprint import pprint


DEBUG = True
ENUM_PARENT = "ENUM_PARENT"
fp = open("./tree.txt", "r", encoding="utf-16", errors="ignore")
lines = fp.readlines()
fp.close()

def create_child_node(parent, dep):
    child = {"children": [],"parent": parent,"dep": dep}
    parent['children'].append(child)
    dprint(f'\t[p = {parent['dep']}] New node added {child['dep']}; child of {child['parent']['dep']}')
    return child

#maps 'groupId:artifactId' to a tree node
node_map = dict()
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

def dprint(arg):
    if DEBUG:
        print("DEBUG: ", arg)

#proj_root should not be hardcoded but taken as cmdline arg ofc
def get_submodule_matchers(proj_root = './maven-modular'):
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

def get_node_key(string):
    #dprint(f"\tSTTRING = {string}")
    string = string.replace(" ", "").replace("$", "").replace("#", "").replace("@", "")
    substrs = string.split(":")
    #dprint("\tKEY = " + ':'.join([substrs[0], substrs[1]]))
    return ':'.join(substrs[0:2])

# builds tree from descendant deps of parent arg if any
def scan_module_subtree(lines, start_idx, h_offset, parent, dep_watchlist, depth = 0):
    dprint(f'****************************CALL FOR SUBTREE OF [p = {parent['dep']}] ***************************************')
    #First line after parent line begins with # - direct child. Sometimes \- will be on same level as parent line so need to cover with first clause 
    if lines[start_idx][0] == '#' or lines[start_idx][h_offset:][0] == '#':
        dep = get_node_key(lines[start_idx])
        child = create_child_node(parent, dep)
        scan_module_subtree(lines, start_idx + 1, h_offset, child, dep_watchlist, depth = 0)

    for i in range(start_idx, len(lines)):
        line = lines[i][h_offset:]
        dprint(f'[p = {parent['dep']}] line:"{lines[i]}";"{line}"')

        if line[0] == '@': # new 
            dep = get_node_key(line)
            #TODO: What about duplicate packages?
            child = create_child_node(parent, dep)
            node_map[get_node_key(line)] = child
            #build subtree of the new child
            dprint(f'\t[p = {parent['dep']}] building subtree of {child['dep']}')
            scan_module_subtree(lines, i + 1, h_offset + 1, child, dep_watchlist, depth + 1)
        elif line[0] == '$':
            #it's deeper than immediate children. leave up to recursive scanmodsubntree call to eventually process it 
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

#[INFO] io.jitpack:module2:jar:2.0-SNAPSHOT
if __name__ == "__main__":
    # print(f"FUCK {bool(re.search("\[INFO\]\s*io.jitpack:module2:.+", "[INFO] io.jitpack:module2:jar:2.0-SNAPSHOT"))}")
    # exit()
    submodule_matchers = get_submodule_matchers()
    dprint(submodule_matchers)
    dep_watchlist = [] #supposed to be parsed from config..
    scan = False

    for i in range(0, len(lines)):
        line = lines[i].strip()
        treelines = []
        horizontal_scan_max = 0

        #latter clause is spaghetti for "at least one of submodules present in line. Looking for start of actual dependency tree"
        if "[INFO]" in line and sum([1 if bool(re.search(s, line)) else 0 for s in submodule_matchers]) > 0: 
            print("BUILDING TREE FOR " + line)
            line = line.strip().replace("[INFO] ", "")
            parent_key = get_node_key(line)

            print("ROOT KEY  = |" + parent_key+ "|")
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

            print("TREELINES START")
            for l in treelines: print(l)
            print("TREELINES END ")
            #DO THE TREE SCANNING SHIT
            
            root = {"children": [],"parent": None,"dep": parent_key}
            node_map[parent_key] = root
            scan_module_subtree(treelines, 1, 0, root, dep_watchlist)
            print_tree(0, root)
        else:
            #print("fk")
            continue
            #dprint("REJECT " + line)

    print(treelines)
