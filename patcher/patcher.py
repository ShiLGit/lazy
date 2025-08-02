from treereader import get_tree, print_tree, parse_values
import configparser
from configgenerator import prompt_until_valid, generate_config
import sys
import os 
import subprocess
import xml.etree.ElementTree as ET
import pom_editor as PE
import json
import pprint

DIR = "."
tfname = './runtime/debugtree.dot'
rfname = './runtime/report.csv'
cfname = './runtime/config.json'
# build tree '
# run = subprocess.run(['mvn', 'dependency:tree', '-DoutputType=dot', f'-DoutputFile={tfname}'], shell=True)
# if run.returncode != 0:
#     print("ERROR - MVN DEPENDENCY TREE FAILED. EXITING")
#     exit()
# else:
#     print(f"Dependency tree file {tfname} generated successfully.")

tree, nodemap = get_tree(tfname)
#print_tree(tree)

#build a config 
generate_new = prompt_until_valid('Generate a new config? (y/n): ', lambda inpt : inpt in ['Y', 'y', 'N','n'])
if generate_new.upper() == 'Y':
    generate_config(rfname, cfname)
config = None
with open(cfname, 'r') as file:
    config = json.load(file)
pomconfig = config['pom.xml']

# build the pom tree TODO: multimodular -> need to check all the poms FCK
tree = ET.parse('./runtime/pom.xml')
root = tree.getroot()
all_declared_deps = PE.get_declared_dependencies(root)


# for all artifacts in config...
for vuln_art in pomconfig.keys():
    versionmatched_config = None # the config under artifact whose version actually matches with what occurs in dep tree

    # Search node tree and try to update the ancestor
    declared_ancestor = None 
    nodes = nodemap.get(vuln_art)
    if not nodes: 
        print("ERROR: FAILED TO FIND NODE THAT SHOULD BE IN THE TREE --------------------------------------------------")
        print(f'\tSearching for artifact = {vuln_art}; nodemap keys = {nodemap.keys()}')
        break


    for node in nodes:
        # search itself and up to all ancestors for presence in pom.xml        
        while node.get('parent'):
            print(f'FOR ART {vuln_art}: v = {node['value']}')
            node_vals = parse_values(node['value'])
            print(f'vmc = {versionmatched_config}')

            # if present in pom.xml
            matching_declared_dep = next((d for d in all_declared_deps if d['artId'] == node_vals['artId']), None)
            versionmatched_config = next((c for c in pomconfig[vuln_art] if c['currentVersion'] == node_vals['version']), None)
            fixVersion = None
            if versionmatched_config:   
                fixVersion = versionmatched_config['fixVersion']
            else:
                # TODO: mvncentral fetcher this instead of making user save. Also ask if this should be cached in the config for future us
                fixVersion = prompt_until_valid(f"An ancestor '{node_vals['artId']}' of vulnerable pkg '{vuln_art}' was detected in the pom but no configurations exist for it. Enter a fix version yourself: ", lambda input: len(input) > 0)

            if fixVersion:
                print(f'Updating {node_vals['artId']}@{node_vals['version']} -> {fixVersion}')
                PE.update_artifact(root, node_vals['artId'], fixVersion)
            node = node.get('parent')
    
    print('\n\n')

