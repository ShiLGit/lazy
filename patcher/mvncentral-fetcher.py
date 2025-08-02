import requests 
import xml.etree.ElementTree as ET
def get_versions(grpId, artId):
    grpPath = grpId.replace('.', '/')
    url = f'https://repo1.maven.org/maven2/{grpPath}/{artId}/maven-metadata.xml'
    res = requests.get(url)
    res.raise_for_status()

    root = ET.fromstring(res.text)
    versions = [v.text for v in root.findall('./versioning/versions/version')]
    return versions


# TODO: RECURSE TO ACNESTOR POMS UNTIL YOU RETRIEVE THE DECLARED VERSIONS FOR ALL DEPENDENCIES
# --> When to give up search though?
def get_dependencies(grpId, artId, ver):
    grpPath = grpId.replace('.', '/')
    url = f'https://repo1.maven.org/maven2/{grpPath}/{artId}/{ver}/{artId}-{ver}.pom'
    res = requests.get(url)
    res.raise_for_status()

    root = ET.fromstring(res.text)
    print(root)
    deps = []
    ns = {'m': 'http://maven.apache.org/POM/4.0.0'}

    for dep in root.findall('.//m:dependencies/m:dependency', ns):
        print(f'tf? {dep}')
        deps.append({
                'grpId': dep.find('m:groupId', ns).text,
                'artId': dep.find('m:artifactId', ns).text,
                'version': dep.find('m:version', ns)
            })
    print(res)
    return deps


# vs = get_dependencies('org.eclipse.jgit', 'org.eclipse.jgit', '2.0.0.201206130900-r') 
# print(vs)