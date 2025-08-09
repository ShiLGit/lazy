import lxml.etree as ET
import re
ns = {'m': 'http://maven.apache.org/POM/4.0.0'}
PLACEHOLDER_RE = re.compile(r'\$\{(.*)\}')
# root.find() except with ns bs handled
def find(root, query):
    return root.find(f'm:{query}', ns)


# HELPER FX: Iterate through all entries in <dependencies> node (passed in as dependencies)
# update relevant properties such that new version of artId occurring in the dependency is set to fixVersion
# return True if a dependency was found and processed, False if no such dependency found
def process_dependencies(dependencies, artId, fixVersion):
    updated = False
    for dep in dependencies:
        dep_artId = dep.find('m:artifactId', ns).text
        print(f'{dep_artId} matching = {dep_artId==artId}')
        if dep_artId == artId:
            ver_el = dep.find('m:version', namespaces=ns) 
            if ver_el is None:
                print('ver el is none bye')
                break
            
            # is version is set as a property? process accordingly
            version_match = PLACEHOLDER_RE.search(ver_el.text)
            if version_match:
                property_name = version_match.group(1)
                prop_el = root.find(f'm:properties/m:{property_name}', ns)
                prop_el.text = fixVersion
                updated = True
            else: 
                ver_el.text = fixVersion
                updated = True

    return updated
            


# map depmgmt artId -> etree element
def add_override(root, grpId, artId, version):
    depmgmt = root.find('m:dependencyManagement/m:dependencies', ns)
    parent = None
    if depmgmt != None:
        parent = depmgmt
    else: 
        parent = root.find('m:dependencies', ns)

    if parent == None:
        print("FROM ADD_OVERIDE: NO DEPENDENCY OR DEPENDENCY MANAGEMENT NODE FOUND. EXITING")
        return 
    dependency = ET.SubElement(parent, 'dependency')

    grpId_el = ET.SubElement(dependency, 'groupId')
    grpId_el.text = grpId
    artId_el = ET.SubElement(dependency, 'artifactId')
    artId_el.text = artId
    version_el = ET.SubElement(dependency, 'version')
    version_el.text = version

# Return T/F based on whether or not a dependency was able to be found and updated
def update_artifact(root, artId, fixVersion):
    # search artifacts in dependencyManagement
    depmgmt= root.findall('m:dependencyManagement/m:dependencies/m:dependency', ns)
    depmgmt_updated = process_dependencies(depmgmt, artId, fixVersion)
    dependencies = root.findall('m:dependencies/m:dependency', ns)
    deps_updated = process_dependencies(dependencies, artId, fixVersion)

    return deps_updated or depmgmt_updated

# returns list of declared artifacts as [{artId: <>, version: <>}] given the pom root
def get_declared_dependencies(root):
    depmgmt= root.findall('m:dependencyManagement/m:dependencies/m:dependency', ns)  or []
    dependencies = root.findall('m:dependencies/m:dependency', ns) or []
    dependencies.extend(depmgmt)

    all_deps = list([])
    for dep in dependencies:
            to_add = dict()
            to_add['artId'] = dep.find('m:artifactId', ns).text
            ver_el = dep.find('m:version', ns)

            # don't add as declared dep because no version specified?
            if ver_el == None:
                continue 

            # is version is set as a property? process accordingly
            version_match = PLACEHOLDER_RE.search(ver_el.text)
            if version_match:
                property_name = version_match.group(1)
                prop_el = root.find(f'm:properties/m:{property_name}', ns)
                to_add['version'] = prop_el.text
            else: 
                to_add = ver_el.text
            
            all_deps.append(to_add)

    return all_deps


# for testing this script only 
if __name__ == '__main__':
    tree = ET.parse('./runtime/pom.xml')
    root = tree.getroot()
    update_artifact(root, 'spring-boot-starter-web', '9999')
    add_override(root, 'fakegrp', 'fakeart', '30000')
    tree.write('out.xml', encoding='utf-8', xml_declaration=True)
    # for child in root:
    #     print(child.tag)


    # # map property -> etree Element
    # properties = find(root, 'properties')
    # properties_map = dict()
    # for child in properties:
    #     properties_map[child.tag] = child

    # # map direct dep name artId -> etree element
    # ddep_map = dict()
    # direct_deps = find(root, 'dependencies')
    # for child in direct_deps:
    #     print(f'wtf -|{child}|-')
    #     artId = find(child, 'artifactId')
    #     print(artId.text)