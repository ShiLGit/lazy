
import re 
import subprocess
from configgenerator import normalize_version
import lxml.etree as ET
from common_consts import NS
from rich import print

# generate an effective pom at path=epom based on the pom at path=pom
def create_epom(pom, epom):
    run = subprocess.run(['mvn', '-f', pom, 'help:effective-pom', '>', './runtime/temp.xml'], shell=True)
    if run.returncode != 0:
        print("ERROR - VALIDATION FAILED. EXITING")
        exit()

    fp = open("./runtime/temp.xml", "r", errors="ignore")
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

    with open(epom, 'w', errors='ignore') as fp:
        fp.writelines(pomlines)

# check the generated effective-pom at path epom_fname against a validation map {artifactId: targetVersion}
# return a list of (groupId, artifactId, fixVersion) whose real version undershoots the fix version
def validate_epom(epom_fname, pomconfig):
    failures = []
    root = ET.parse(epom_fname).getroot()
    dependencies=root.findall('m:dependencies/m:dependency', NS)
    for dep in dependencies:
        artifact = dep.find('m:artifactId', NS)
        group = dep.find('m:groupId', NS)
        print(f'{group.text}:{artifact.text}')
        target_ver = pomconfig.get(artifact.text)
        if target_ver:
            version = dep.find('m:version', NS).text
            version_normalized = normalize_version(version)
            target_ver_normalized = normalize_version(target_ver)
            if version == target_ver or max(set([version_normalized, target_ver_normalized]), key=parse) == version_normalized:
                print(f'\t[green]Validated - {group.text}{artifact.text}:{version} is >= configured version of {target_ver}')
            else: 
                print(f'\t[red]Failure - {group.text}{artifact.text}:{version} is <= configured version of {target_ver}')
                failures.append((group.text, artifact.text, target_ver))
    return failures