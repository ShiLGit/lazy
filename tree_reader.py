from lxml import etree
import os
import re
fp = open("./input.txt", "r")
lines = fp.readlines()
fp.close()

#proj_root should not be hardcoded but taken as cmdline arg ofc
def get_submodule_matchers(proj_root = './maven-modular'):
    submodule_matchers = []
    xml_root = etree.parse("C:\\Users\\fukof\\Programming\\lazy\\maven-modular\\module1\\pom.xml").getroot()
    shiat = xml_root.find("wasap/target")
    print(shiat.text)
    return
    for root, dirs, files in os.walk(proj_root):
        if "target" in root: 
            continue
        
        grpId = artId = None
        if 'pom.xml' in files:
            #xml_root = etree.parse(root + "/pom.xml").getroot()
            xml_root = etree.parse("C:\\Users\\fukof\\Programming\\lazy\\maven-modular\\module1\\pom.xml").getroot()
            print(xml_root.find("/root/wasap"))
            exit()
            return 
            for el in xml_root.iter():
                tag = el.tag
                context = etree.iterwalk(xml_root, events=("start", "end"), tag=tag)
                    # Assign the first encountered groupIds and artifactIds because those should for the submodule itself
                    # ^No. That's the parent tag. FUCK
                print(f"TAG = {tag}")
                for action, element in context:
                    print(f"AC[{action}]AC = EL[{element.text}]EL")
                    # if "groupId" in str(element.tag):
                    #     if grpId == None:
                    #         grpId = element.text
                    # elif "artifactId" in str(element.tag):
                    #     if artId == None:
                    #         artId = element.text
                    # if grpId != None and artId != None:
                    #     submodule_matchers.append(rf"\[INFO\]\s*{grpId}:{artId}:")
                    #     break
            return
    return submodule_matchers



#READ CNFIG. not supposed to be hardcoded but ur too lazy to do the xmlparsing part? 
submodule_matchers = get_submodule_matchers()
print(submodule_matchers)

exit()

for line in lines:
    scan = False

    #latter clause is spaghetti for "at least one of submodules present in line. Looking for start of actual dependency tree"
    if "[INFO]" in line and sum([1 if bool(re.search(s, line)) else 0 for s in submodule_matchers]) > 0: 
        scan = True
        print(f"YES! SCAN {line}")
    elif scan == False:
        continue 

