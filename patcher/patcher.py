from treereader import get_tree, print_tree, parse_values
import configparser
import configgenerator
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
# generate_new = configgenerator.prompt_until_valid('Generate a new config? (y/n): ', ['Y', 'y', 'N','n'])
# if generate_new.upper() == 'Y':
#     configgenerator.generate_config(rfname, cfname)
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
    # 1) Is it directly declared as a dependency?
    matching_declared_dep = next((d for d in all_declared_deps if d['artId'] == vuln_art), None)
    if matching_declared_dep:
        declared_ver = matching_declared_dep['version']
        pprint.pprint(matching_declared_dep)

# tree.write('out.xml', encoding='utf-8', xml_declaration=True)
    # print(vuln_art)
    # print(nodemap.get(vuln_art))
