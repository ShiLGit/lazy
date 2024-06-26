from lxml import etree, objectify
import os
import re
DEBUG = True
fp = open("./input.txt", "r")
lines = fp.readlines()
fp.close()

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
    print(f'{indent}{'' if node['dep'] == None else node['dep']}')
    for c in node['children']:
        print_tree(depth + 1, c)

def dprint(arg):
    if DEBUG:
        print("DEBUG: ", arg)
#proj_root should not be hardcoded but taken as cmdline arg ofc
def get_submodule_matchers(proj_root = './horrible'):
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
    string = string.replace(" ", "").replace("$", "").replace("#", "").replace("$", "")
    substrs = string.split(":")
    dprint("KEY = " + substrs[0] + substrs[1] + substrs[3])
    return substrs[0] + substrs[1] + substrs[3]

# Returns resume index. builds tree from descendant deps of parent arg if any
def scan_module_subtree(lines, start_idx, h_offset, parent, dep_watchlist):
    for i in range(start_idx, len(lines)):
        line = lines[start_idx][h_offset:]
        if line[0] == '@':
            #REGEX IT SO THAT IT'S JUST GRP:ART:VER? SAFER LOOKUP
            child = {"children": [],"parent": parent,"dep": line[1:]}
            parent['children'].append(child)
            node_map[get_node_key(line)] = child
            #build subtree of the new child
            scan_module_subtree(lines, i + 1, h_offset + 1, child, dep_watchlist)
        elif line[0] == '#':
            #go to line[i-1]; extract the lookup grp:art:ver
            #add it to the chilre returnedf by the lookup. continue
            parent_line = lines[start_idx - 1]
            parent = node_map[get_node_key(parent_line)]
            pass 
        elif line[0] != '$':
            #it's deeper than immediate children. leave up to recursive scanmodsubntree call to eventually process it 
            pass
 



def replace_tokens(line):
    index_stop = re.search(rf"[^\s]+\:[^\s]+", line)
    if index_stop == None:
        dprint(f"IN REPLACE_TOKENS(). NOT FOUND {line}")
        return ""
    index_stop = index_stop.start()
    dont_touch = line[index_stop:]
    mutable = line[0:index_stop]

    #Assuming these are special chars that don't shot up as the first char of a dep (y would they??)...
    mutable = mutable.replace("+-", "@") #NEW
    mutable = mutable.replace(r"\-", "#") #DIRECT CHILD OF ABOVE?
    mutable = mutable.replace("|", "$") #SIBLING

    line = mutable + dont_touch
    line = line.replace(" ", "")
    line = line.replace("[INFO]", "" )

    return line


if __name__ == "__main__":
    submodule_matchers = get_submodule_matchers()
    dprint(submodule_matchers)
    dep_watchlist = [] #supposed to be parsed from config..

    scan = False

    for i in range(0, len(lines)):
        line = lines[i]
        treelines = []
        horizontal_scan_max = 0

        #latter clause is spaghetti for "at least one of submodules present in line. Looking for start of actual dependency tree"
        if "[INFO]" in line and sum([1 if bool(re.search(s, line)) else 0 for s in submodule_matchers]) > 0: 
            scan = True
            #dprint("ACCEPT " + line)
            i = i + 1 #increment before entering loop for deranged edge case where i+1 >= len(lines)
            
            #populate treelines with parseable lines of dependency tree
            while scan == True and i < len(lines): 
                line = lines[i]
                #matching end of tree lines; alwways prints grpId:artId:... etc. 
                if not bool(re.search(".+:.+:.+", line)):
                    dprint(f"TERMINATING SCAN AT LINE {line}")
                    scan = False
                    break
                line = replace_tokens(line)
                dprint(line)
                treelines.append(line)
                scan_stop = re.search(r"[^\@\$\%]", line).start()
                if scan_stop > horizontal_scan_max:
                    horizontal_scan_max = scan_stop
                i = i + 1
            
            root = {"children": [],"parent": None,"dep": None}
            #DO THE TREE SCANNING SHIT
            scan_module_subtree(treelines, 1, 0, root, dep_watchlist)
            print("TREEEEEEEEEEE")
            print_tree(-1, root)
        else:
            #print("fk")
            continue
            #dprint("REJECT " + line)


