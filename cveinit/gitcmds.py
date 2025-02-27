import subprocess
import sys
import os 
# USAGE: py gitcmds.py <DIR> <BRANCH OR TAG>
def cmd(cmds, fatal = False, report_success = True):
    output = subprocess.run(cmds, shell = True, capture_output=True)
    cmd_str = ' '.join(cmds)
    if(output.returncode == 0):
        if report_success: 
            print(f"Command '{cmd_str}' completely successfully")
        return output
    else:
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!ERROR!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(f"Command '{cmd_str}' failed!! stderr = \n\t{output.stderr}")
        print("\n\t" + 'Exiting job prematurely.' if fatal else 'Proceeding anyways.')
        if fatal:
            exit()



 

def git_init(folder, branch):
    os.chdir(f"C:/Users/ls185267/{folder}")

    # cmd(['git', 'checkout', 'master'], fatal = True)
    # cmd(['git', 'pull'], fatal = True)
    # cmd(['git', 'checkout', branch], fatal = True)
    # cmd(['git', 'pull'], fatal = True)
    cmd(['mvn'])
    


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Bad input. Command should look like 'py gitcmds.py <FOLDER> <BRANCH/TAG>")
        exit()

    folder = sys.argv[1]
    branch = sys.argv[2]
    git_init(folder, branch)