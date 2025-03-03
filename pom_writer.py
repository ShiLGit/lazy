from lxml import etree, objectify
import json 
from io import StringIO
import os
import re
#this is a common fx. move to a util file later 
def clean_xml_namespaces(root):
    for element in root.getiterator():
        if isinstance(element, etree._Comment):
            continue
        element.tag = etree.QName(element).localname

# Given pom xml tree, return a map (property name -> val) of the <properties> section of pom
def populate_properties_map (xml_root):
    map = dict()
    props = xml_root.find("properties")
    if props is None or len(props) == 0:
        return map
    
    for p in props.iter(): 
        map[p.tag] = {
            'value': p.text,
            'element': p
        }

    del map['properties']
    return map

def write_pom(xml, proj_root, fname = "pom_modified.xml"):
    xml_declaration = ""
    with open(proj_root + "/pom.xml") as fp:
        xml_declaration = fp.readline()

    with open(proj_root + f'/{fname}', "wb") as fp:
        fp.write(xml_declaration.encode("utf-8"))
        xml.write(fp)
    print(f"[INFO] Changes written to modified file {proj_root}/{fname}")

# Iterate through children of <dependencies> or similar; check if applicable rule applies for each child and make changes to file accordingly
def processDeps(deps, rules, properties_map):
    if len(deps) == 0:
        print("[INFO] null element passed into deps! <dependencies> or <dependencyManagement> section is most likely missing")
        return
    for dep in deps: 
            if dep.tag is etree.Comment:
                continue 

            # find groupId:artifactId of current dependency
            grpId = dep.find("groupId")
            if grpId is None: 
                continue
            grpId = grpId.text

            artId = dep.find("artifactId")
            if artId is None: 
                continue 
            artId = artId.text 

            # does there exist a rule for current dependency? process if yes
            matchingRule = rules.get(f"{grpId}:{artId}")
            if matchingRule is not None: 
                ver_tag = dep.find("version")
                if ver_tag is None: 
                    print(f"[WARNING] - No version listed for {grpId}:{artId} - skipping processing")
                    continue

                ver = ver_tag.text
                ver_property = None
                # Using a placeholder from properties or hardcoded?
                if re.match(r"\s*\$\{.+\}", ver):
                    ver_property = ver.replace("$", "").replace("{", "").replace("}", "")
                    ver = properties_map.get(ver_property).get('value')

                target_ver = ""
                # find the range that version falls in
                for rule in matchingRule: 
                    lb, ub = rule['range'][0], rule['range'][1]
                    under_ub = True if ub == "INF" else ver < ub 
                    overeq_lb = True if lb == "INF" else ver >= lb
                    if overeq_lb and under_ub:
                        target_ver = rule['fixVersion']
                        print(f"[INFO] GRADUATING {grpId}:{artId} FROM {ver} --> {target_ver}")
                        if ver_property:
                            props = properties_map[ver_property]['element']
                            props.text = target_ver
                        else: 
                            print(f"[WARNING] {grpId}:{artId} has a hardcoded version!!! Consider using a property instead")
                            ver_tag.text = target_ver
                        break



def main(proj_root = "."):
    fp = open("./config.json")
    rules = json.load(fp)["pom.xml"]
    fp.close()
    xml = etree.parse(proj_root + "/pom.xml")
    xml_root = xml.getroot()
    clean_xml_namespaces(xml)

    properties_map = populate_properties_map(xml_root)
    # check <dependencies>
    processDeps(xml_root.find("dependencies"), rules, properties_map)
    processDeps(xml_root.find("dependencyManagement"), rules, properties_map)

    write_pom(xml, proj_root)

if __name__ == "__main__": 
    main()
