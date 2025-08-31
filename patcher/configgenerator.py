import pandas as pd
from packaging.version import parse, Version, InvalidVersion
import re
from rich import print
import pprint
import json
MAJOR = 'MAJOR'
MINOR = 'MINOR'
PATCH = 'PATCH'

RANGE_THRESHOLD = MINOR # read in as env var if args get too long, else as cmdline arg
NORMALIZE_RE = re.compile(r'\.(Final|Release|GA|-SNAPSHOT|-RELEASE|-r)', re.IGNORECASE)
URL_PRECEDED_RE = re.compile(r'(https:\/\/\S+) - ')

# Just super fallback for weird ass mend versions that don't follow a pattern at all (1.5.13;ch.qos.logback...??)
# NOTE that if the inherent format is just not compatible as a Version (e.g. 'A.BBBB.C213') then ur fked
def version_withopts(version):
    retVal = None
    try:
        retVal=Version(version)
    except Exception as e:
        retVal = input(f"'{version}' is not acceptable as a Version(). Enter the corrected version or just press ENTER to discard it: ").strip()
        if len(retVal) == 0: retVal = None 
        # Re-prompt idiot
        else: retVal = version_withopts(retVal)
    return retVal 

# deletes the suffixes from a mvn version that make it noncompliant with Version(). IDK WTF TO DO ABOUT JGIT
def normalize_version(ver):
    ver = URL_PRECEDED_RE.sub('', ver)
    ver = NORMALIZE_RE.sub('', ver)
    return ver
# Iterate through list of universal fixes (str array) and current version (str)
# Return the minimum changing universal fix if there is a match, else return None
def match_universal_fixes(ufixes, cver):
    cver_comp = version_withopts(normalize_version(cver))
    if cver_comp == None: 
        return set()
    viable_fixes = []
    for fv in ufixes:
        fv_comp = version_withopts(normalize_version(fv))
        if fv_comp == None:
            continue
        matching_minvers = fv_comp.minor == cver_comp.minor
        matching_majvers = fv_comp.major == cver_comp.major 
        #print(f'\tcv = {cver}; fv={fv}; mmin={matching_minvers}; mmaj = {matching_majvers}; WTF. {cver_comp.major} vs {fv_comp.major}')
        if RANGE_THRESHOLD == MINOR and matching_majvers and matching_minvers:
            viable_fixes.append(fv)
        elif RANGE_THRESHOLD == MAJOR and matching_majvers:
            viable_fixes.append(fv)
    
    if len(viable_fixes) == 0:
        return None 
    
    return min(viable_fixes, key = parse)

def bigalert(str):
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ WARNING ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    print(f'[bold]{str}[/bold]')
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ WARNING ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")


# string prompt text = go figure. text that prints as the prompt
# validator = lambda/fx used to determine whether input is valid (return t/f)
def prompt_until_valid(prompt_text, validator):
    keep_prompting = True 
    while keep_prompting:
        inpt = input(prompt_text)
        inpt = inpt.strip()
        if validator(inpt):
            return inpt 
        else: 
            print(f"\t[red]'{inpt}' is not a valid input [/red]")

# rows: subset of cve df where all rows are associated with the same package
# returns: map of version range -> fix version associated with pkg, where version range covers all exisitng current versions
def generate_versionmap(rows):
    # Map package name to major, minor, patch versions
    #{'CVE-X': [fixversion1,...], 'CVE-Y': []}
    pkg_name = rows.iloc[0]['Component']
    config = {pkg_name: []}
    cvemap = dict()
    cvers = set() #all current versions of pkg in report
    all_fv = set()
    bigalert(f'Parsing for {pkg_name}')
    for cve in rows['CVE'].unique():
        for idx, row in rows[rows['CVE'] == cve].iterrows():
            cvers.add(row['Current Version'])
            all_fv = all_fv.union(row['Fixed Versions'].split(','))

            # make sure fix versions from the report are compliant with Version() so that max() with key=parse doesn't fail later
            all_fv = {normalize_version(fv) for fv in all_fv}
            all_fv = {str(fv_asver) for fv_asver in {version_withopts(fv) for fv in all_fv} if fv_asver != None}

            if cvemap.get(cve) == None:
                cvemap[cve] = set(row['Fixed Versions'].split(','))
            else:
                cvemap[cve] = cvemap[cve].union(set(row['Fixed Versions'].split(',')))

    # Identify all fix versions that can fix all cves
    print(f'Generating config with range threshold = {RANGE_THRESHOLD}. This means that fix versions will not update {RANGE_THRESHOLD} version or greater.')
        
    universal_fixes = all_fv
    for cve in cvemap.keys():
        universal_fixes = universal_fixes.intersection(cvemap[cve])
    

    #print(f"afv = {all_fv}")
    universal_fixes.add(max(all_fv, key=parse)) # also need to add the max existing fix version
    #print(cvemap)
    #print(f"cvers {cvers}")

    # Map each current version to a fix version
    for currentv in cvers: 
        fv = match_universal_fixes(universal_fixes, currentv)
        #print(f'{currentv} matches with {fv}')
        if not fv: 
            print(f"\nWARNING - [white bold]{pkg_name}:{currentv}[/white bold] has no fix versions within threshold {RANGE_THRESHOLD} that fixes all existing cves.")
            print(f"\t• Universal fixes are: [bold blue]{','.join(universal_fixes)}[/bold blue]")
            for altfv in all_fv:
                cves = cvemap.keys()
                fixedcves = []
                if altfv in universal_fixes:
                    continue 

                for cve in cves:
                    if altfv in cvemap[cve]:
                        fixedcves.append(cve)
                missed_cves = set(cves) - set(fixedcves)
                missed_cves_print = []
                for mcve in missed_cves:
                    severity = rows[rows['CVE'] == mcve].iloc[0]['Severity'] or 'ERROR'
                    missed_cves_print.append(f'{mcve} ({severity})')
                print(f'\t• [bold blue]{altfv}[/bold blue]; fails to fix [red not bold]{', '.join(missed_cves_print)}[/red not bold]')
            
            fv = prompt_until_valid(f"Choose a fix version for from above for {currentv} or ENTER to apply no changes: ", lambda input: input in all_fv or input.strip() =='')
            fv = fv.strip()
        if len(fv)> 0:
            print(f"Setting [white bold] {pkg_name}:{currentv} [/white bold] to have fix version [white bold]{fv}[/white bold]")
            entry = {
                'currentVersion':currentv,
                'fixVersion':fv
            }
            config[pkg_name].append(entry)

        else:
            print(f"No fix version set for {currentv}")

    bigalert(f'parse ended for {pkg_name}')
    return config

def generate_config(fname, configfname='./config.json'):
    df = pd.read_csv(fname)
    #Clean unwanted duplicates and columns
    df.drop(['Detected By', 'Image Name'], axis = 1, inplace = True)
    df.drop(columns=['Summary'], inplace=True, errors='ignore')
    df.drop_duplicates(subset=['Component', 'Current Version', 'CVE'], inplace=True) 

    #For each current version associated with a component, map to a fix version
    df = df[df['Package Type'] == 'maven']
    final_config = {'pom.xml': dict()}

    for pkg in df['Component'].unique():
        pkg_df = df[df['Component'] == pkg]

        x = generate_versionmap(pkg_df)
        final_config['pom.xml'][pkg] = x[pkg]


    pprint.pprint(final_config)
    with open(configfname, 'w') as fp:
        json.dump(final_config, fp)

if __name__ == '__main__':
    generate_config(fname='test.csv', configfname='test.json')