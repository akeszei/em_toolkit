#!/usr/bin/env python3

## Author : A. Keszei 

"""
    A simple script to make easy-to-use outputs for curating a dataset on-the-fly 
"""

## 2024-07-25: Initial script started  

#############################
#region     FLAGS
#############################
DEBUG = True

#endregion

#############################
#region     DEFINITION BLOCK
#############################

def check_if_EPU_directory(dir = "./"):
    SESSION_FILE = False
    IMAGES_DIR = False 

    for f in os.listdir(dir):
        print(" file found: ", f)
        if f.lower() == "EpuSession.dm".lower():
            SESSION_FILE = True 
            
        if f.lower() == "Images-Disc1".lower():
            IMAGES_DIR = True 
    
    if SESSION_FILE and IMAGES_DIR:
        return True

    return False 


def run_ctf():
    cmds = ["test.mrc", "out.mrc", "2.48", "120", "2", "0.15", "512", "50", "5", "5000", "50000", "100", "no", "no", "no", "no", "no"]

    p = Popen('ctffind', stdin=PIPE)
    for x in cmds:
        p.stdin.write(x.encode() + b'\n')

    p.communicate()


#############################
#region     RUN BLOCK
#############################

if __name__ == "__main__":
    import os 
    # REF: https://stackoverflow.com/questions/8475290/how-do-i-write-to-a-python-subprocess-stdin
    from subprocess import Popen, PIPE


    ## check if the working directory shows signs of being an EPU directory 
    if not check_if_EPU_directory():
        print(" Working directory does not appear to be a normal EPU directory")
        exit()

#endregion