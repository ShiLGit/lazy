from treereader import get_tree, print_tree, parse_values
import configparser
from configgenerator import prompt_until_valid, generate_config, normalize_version
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
DIR = "."
tfname = './runtime/debugtree.dot'
rfname = './runtime/report.csv'
cfname = './runtime/config.json'
ns = {'m': 'http://maven.apache.org/POM/4.0.0'}

# map artifactId to a fixVersion for validation
validate_config = {}

# check the generated effective-pom at path epom_fname against a validation map {artifactId: targetVersion}
# return a list of (groupId, artifactId, fixVersion) whose real version undershoots the fix version
def validate_pom(epom_fname, pomconfig):
    failures = []
    print('~~~~~~~~~~~~~~~~ STEP X - Validating POM... ~~~~~~~~~~~~~~~~~')
    root = ET.parse(epom_fname).getroot()
    dependencies=root.findall('m:dependencies/m:dependency', ns)
    for dep in dependencies:
        artifact = dep.find('m:artifactId', ns)
        group = dep.find('m:groupId', ns)
        target_ver = pomconfig.get(artifact.text)
        if target_ver:
            version = dep.find('m:version', ns).text
            version_normalized = normalize_version(version)
            target_ver_normalized = normalize_version(target_ver)
            if version == target_ver or max(set([version_normalized, target_ver_normalized]), key=parse) == version_normalized:
                print(f'\t[green]Validated - {group.text}{artifact.text}:{version} is >= configured version of {target_ver}')
            else: 
                print(f'\t[red]Failure - {group.text}{artifact.text}:{version} is <= configured version of {target_ver}')
                failures.append((group.text, artifact.text, target_ver))
    return failures
# build tree '
# run = subprocess.run(['mvn', 'dependency:tree', '-DoutputType=dot', f'-DoutputFile={tfname}'], shell=True)
# if run.returncode != 0:
#     print("ERROR - MVN DEPENDENCY TREE FAILED. EXITING")
#     exit()
# else:
#     print(f"Dependency tree file {tfname} generated successfully.")

tree, nodemap = get_tree(tfname)
# print_tree(tree, 0)
# exit()

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
print('[purple]~~~~~~~~~~~~~~~~~~~~~~~~~ STEP X: INITIAL REPLACEMENT OF DECLARATIONS ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~[/purple]')
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
tmp_pname = 'temp_pom.xml'
if os.path.exists(tmp_pname):
    os.remove(tmp_pname)
# Save to a file

tree.write(tmp_pname, encoding="utf-8", xml_declaration=True)
print("temp tree written")

# # 2: validate the resulting pom against your config. Are vuln pkgs actually at a fixed version?
run = subprocess.run(['mvn', '-f', './runtime/temp_pom.xml', 'help:effective-pom', '>', './runtime/check.xml'], shell=True)
if run.returncode != 0:
    print("ERROR - VALIDATION FAILED. EXITING")
    exit()

fp = open("./runtime/check.xml", "r", errors="ignore")
lines = fp.readlines()
fp.close()
include = False
pomlines = []
for line in lines:
    if not include and re.match(r'<project(\s+[^>]*)?>', line):
        include = True

    if include:
        pomlines.append(line)

    if include and re.match(r'</project>', line):
        break

with open('./runtime/check.xml', 'w', errors='ignore') as fp:
    fp.writelines(pomlines)
# 3: Add direct overrides to the unfixed packages  
print('\n\n')

failed_updates = validate_pom('./runtime/check.xml', validate_config)
for (grpId, artId, targver) in failed_updates:
    print(f'failed {grpId}:{artId}:{targver}')
    #overwrite otttttt
    PE.add_override(root, grpId, artId, targver)

tree.write('pom2.xml', encoding="utf-8", xml_declaration=True)
validate_pom('pom2.xml', config)