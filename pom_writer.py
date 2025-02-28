from lxml import etree, objectify
import json 
from io import StringIO
import os
import re
proj_root = "."
#this is a common fx. move to a util file later 
def clean_xml_namespaces(root):
    for element in root.getiterator():
        if isinstance(element, etree._Comment):
            continue
        element.tag = etree.QName(element).localname
    etree.cleanup_namespaces(root)

# Given pom xml tree, return a map (property name -> val) of the <properties> section of pom
def populate_properties_map (xml_root):
    map = dict()
    props = xml_root.find("properties")
    if props is None or len(props) == 0:
        return map
    
    for p in props.iter(): 
        map[p.tag] = p.text

    del map['properties']
    return map


if __name__ == "__main__": 
    fp = open("./config.json")
    rules = json.load(fp)
    fp.close()
    xml = etree.parse(proj_root + "/pom.xml")
    clean_xml_namespaces(xml)
    xml_root = xml.getroot()
    properties_map = populate_properties_map(xml_root)
    # check <dependencies>
    deps = xml_root.find("dependencies") 
    for dep in deps: 
        if dep.tag is etree.Comment:
            continue 

        grpId = dep.find("groupId")
        if grpId is None: 
            print("...? GroupId is none") 
            continue
        grpId = grpId.text

        artId = dep.find("artifactId")
        if artId is None: 
            print("artId is none??")
            continue 
        artId = artId.text 

        matchingRule = rules["pom.xml"].get(f"{grpId}:{artId}")
        if matchingRule is not None: 
            print("THERE IS A MATCH")
            ver = dep.find("version")
            if ver is None: 
                # ver from depMgmt, parent?
                continue

            ver = ver.text
            ver_property = None
            # Using a placeholder from properties or hardcoded?
            if re.match(r"\s*\$\{.+\}", ver):
                ver_property = ver.replace("$", "").replace("{", "").replace("}", "")
                ver = properties_map.get(ver_property)
                
            target_ver = ""
            # find the range that version falls in
            for rule in matchingRule: 
                lb, ub = rule['range'][0], rule['range'][1]
                under_ub = True if ub == "INF" else ver < ub 

                if ver >= lb  and under_ub:
                    target_ver = rule['fixVersion']
                    print(f"GRADUATING {ver} --> {target_ver}")
                    if ver_property:
                        props = xml_root.find("properties")
                        props.find(ver_property).text = target_ver
                    break

    with open("pom_modified.xml", "wb") as fp:
        xml.write(fp)
    #check <dependencyManagement>
