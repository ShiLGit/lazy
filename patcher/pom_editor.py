import xml.etree.ElementTree as ET
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
    dependency_found = False
    for dep in dependencies:
        dep_artId = dep.find('m:artifactId', ns).text
        if dep_artId == artId:
            ver_el = dep.find('m:version', ns).text

            # is version is set as a property? process accordingly
            version_match = PLACEHOLDER_RE.search(ver_el.text)
            if version_match:
                property_name = version_match.group(1)
                prop_el = root.find(f'm:properties/m:{property_name}', ns)
                prop_el.text = fixVersion
                dependency_found = True
            else: 
                ver_el.text = fixVersion
                dependency_found = True

        return dependency_found
            


# map depmgmt artId -> etree element
def add_override(root, grpId, artId, version):
    depmgmt = root.find('m:dependencyManagement/m:dependencies/m:dependency', ns)
    parent = None
    if depmgmt != None:
        parent = depmgmt
    else: 
        parent = root.find('m:dependencies/m:dependency', ns)

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

    return deps_updated and depmgmt_updated

def get_all_dependencies(root):
    depmgmt= root.findall('m:dependencyManagement/m:dependencies/m:dependency', ns)  or []
    dependencies = root.findall('m:dependencies/m:dependency', ns) or []
    dependencies.extend(depmgmt)
    
    all_deps = set([])
    for dep in dependencies:
            all_deps.add(dep.find('m:artifactId', ns).text)

    return all_deps


# for testing this script only 
if __name__ == '__main__':
    tree = ET.parse('./runtime/pom.xml')
    root = tree.getroot()
    update_artifact(root, 'spring-web', '2')
    add_override(root, 'fakegrp', 'fakeart', '30000')
    ET.register_namespace('','http://maven.apache.org/POM/4.0.0')
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