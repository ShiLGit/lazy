from treereader import get_tree, print_tree, parse_values
import configparser
from configgenerator import prompt_until_valid, generate_config
from packaging.version import parse, Version, InvalidVersion
from rich import print
import sys
import os 
import subprocess
import lxml.etree as ET
import pom_editor as PE
import json
import pprint
import re 
from pom_validator import validate_epom, create_epom
from rich import print
DIR = "."
tfname = './runtime/debugtree.dot'
rfname = './runtime/report.csv'
cfname = './runtime/config.json'

def print_banner(str, color='purple', width=120):
    chr = '~'
    chr = chr * int((width-len(str))/2 - 1 )
    print(f'[bold][{color}]{chr} {str} {chr}')


# map artifactId to a fixVersion for validation
validate_config = {}

print_banner('BUILDING DEPENDENCY TREE')
# build tree '
run = subprocess.run(['mvn', 'dependency:tree', '-DoutputType=dot', f'-DoutputFile={tfname}'], shell=True)
if run.returncode != 0:
    print("ERROR - MVN DEPENDENCY TREE FAILED. EXITING")
    exit()
else:
    print(f"Dependency tree file {tfname} generated successfully.")

tree, nodemap = get_tree(tfname)

print_banner('BUILDING CHANGE CONFIG (OPT)')
#build a config 
generate_new = prompt_until_valid('Generate a new config? (y/n): ', lambda inpt : inpt in ['Y', 'y', 'N','n'])
if generate_new.upper() == 'Y':
    generate_config(rfname, cfname)
config = None
with open(cfname, 'r') as file:
    config = json.load(file)
pomconfig = config['pom.xml']


# map artifactId to a fixVersion; cache for fixversions of ancestor artifacts so that ancestor of several cve packages doens't get version-prompted each time 
change_cache = {}

# build the pom tree TODO: multimodular -> need to check all the poms FCK
tree = ET.parse('./runtime/pom.xml')
root = tree.getroot()
all_declared_deps = PE.get_declared_dependencies(root)
print_banner('APPLYING INITIAL REPLACEMENT OF DECLARATIONS')
# for all artifacts in config...
for vuln_art in pomconfig.keys():
    # 1: update ancestors or direct declarations
    declared_ancestor = None 
    nodes = nodemap.get(vuln_art)
    if not nodes: 
        print("ERROR: FAILED TO FIND NODE THAT SHOULD BE IN THE TREE --------------------------------------------------")
        print(f'\tSearching for artifact = {vuln_art}; nodemap keys = {nodemap.keys()}')
        break

    for node in nodes:
        # search itself and up to all ancestors for presence in pom.xml        
        while node:
            node_vals = parse_values(node['value'])
    
            # if present in pom.xml
            matching_declared_dep = next((d for d in all_declared_deps if d['artId'] == node_vals['artId']), None)
            versionmatched_config = next((c for c in pomconfig.get(node_vals['artId']) or [] if c['currentVersion'] == node_vals['version']), None)
            fix_version = None
            if versionmatched_config:   
                fix_version = versionmatched_config['fixVersion']
                validate_config[vuln_art] = fix_version

            elif matching_declared_dep:
                # TODO: mvncentral fetcher this instead of making user save. Also ask if this should be cached in the config for future use
                cached_fix = change_cache.get(node_vals['artId'])
                if cached_fix:
                    fix_version=cached_fix 
                else:
                    fix_version = prompt_until_valid(f"An ancestor '{node_vals['artId']}:{node_vals['version']}' of vulnerable pkg '{vuln_art}' was detected in the pom but no configurations exist for it. Set the version for  version yourself: ", lambda input: len(input) > 0)
                    change_cache[node_vals['artId']] = fix_version

            if fix_version:
                updated = PE.update_artifact(root, node_vals['artId'], fix_version)
                if updated: print(f'{'Successfully' if updated else 'Failed to'} updated {node_vals['artId']} to {fix_version}' )
            node = node.get('parent')

# cache the resulting pom in a tmp.xml
tmp_pname = './runtime/validation/temp_pom.xml'
if os.path.exists(tmp_pname):
    os.remove(tmp_pname)
# Save to a file
tree.write(tmp_pname, encoding="utf-8", xml_declaration=True)

print_banner('VALIDATING RESULTING POM (FIRST PASS)')
# # 2: validate the resulting pom against your config. Are vuln pkgs actually at a fixed version?
# add direct overrides for non fixed pkgs
create_epom('./runtime/validation/temp_pom.xml', './runtime/validation/check.xml')
failed_updates = validate_epom('./runtime/validation/check.xml', validate_config)
for (grpId, artId, targver) in failed_updates:
    print(f'failed {grpId}:{artId}:{targver}')
    #overwrite otttttt
    PE.add_override(root, grpId, artId, targver)
    print(f'Override added for {grpId}:{artId} ')

# validate override-added pom
if len(failed_updates) > 0:
    print_banner('VALIDATING POM WITH OVERRIDES ADDED FOR FAILED UPDATES')
    tree.write('./runtime/validation/pom2.xml', encoding="utf-8", xml_declaration=True)
    create_epom('./runtime/validation/pom2.xml', './runtime/validation/check2.xml')

    validate_epom('./runtime/validation/check2.xml', validate_config)
#subprocess.run('del /Q .\\runtime\\validation\\*', shell=True) #windows bs
# Final analysis, changelog, comparison against original report?