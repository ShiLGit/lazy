import treereader as treereader
import configparser
import configgenerator
import sys
import os 
import subprocess
import xml.etree.ElementTree as ET
import pom_editor as PE
DIR = "."
tfname = './runtime/debugtree.dot'
rfname = './runtime/report.csv'
# build tree '
run = subprocess.run(['mvn', 'dependency:tree', '-DoutputType=dot', f'-DoutputFile={tfname}'], shell=True)
if run.returncode != 0:
    print("ERROR - MVN DEPENDENCY TREE FAILED. EXITING")
    exit()
else:
    print(f"Dependency tree file {tfname} generated successfully.")

tree, nodemap = treereader.get_tree(tfname)
treereader.print_tree(tree)

# build a config 
generate_new = configgenerator.prompt_until_valid('Generate a new config? (y/n): ', ['Y', 'y', 'N','n'])
if generate_new.upper() == 'Y':
    configgenerator.generate_config(rfname, './runtime/config.json')


# build the pom tree 
tree = ET.parse('./runtime/pom.xml')
root = tree.getroot()
all_arts = PE.get_all_dependencies(root)
print(all_arts)