#!/usr/bin/env python3

"""
    Sort EPU data into tilt groups using code groups in the filename, e.g.:
        FoilHole_<x>_Data_<tiltgroup>_<x>_<y>_<z>_Fractions.mrc
    The data will be printed out into a file of the form:
        tilt_1  FoilHole_<x>_Data_<tiltgroup>_<x>_<y>_<z>_Fractions.mrc
        ...
    This file can then be used to remap optics groups in RELION.
"""


#############################
###     DEFINITION BLOCK
#############################

def usage():
    if not len(sys.argv) == 1:
        print("===============================================================================================================================")
        print(" Run this script in the directory with all movies:")
        print("    $ EPU_assign_tiltgroups.py   ")
        print(" Output of this script is a file named: tiltgroups.txt")
        print("===============================================================================================================================")
        sys.exit()
    else:
        return

def check_for_help_flag(cmdline):
    for entry in cmdline:
        if entry in ['-h', '-help', '--h', '--help']:
            return True
    return False

def get_all_mrc_files():
    counter = 0
    allFiles = os.listdir()
    mrcFiles = []
    for file in allFiles:
        if os.path.splitext(file)[1] == ".mrc":
            counter += 1
            mrcFiles.append(file)

    print(" %s .mrc files found in directory" % counter)
    return mrcFiles


def find_all_tiltgroups(fileList):
    """ Find all unique ID codes for each tilt group in the dataset and return them as a list for use:
            [ "tilt_id_1", "tilt_id_2", ... "tilt_id_n"]
    """
    tilt_ids = []
    for file in fileList:
        filename_to_list = file.split("_")
        tilt_id = filename_to_list[3]
        if not tilt_id in tilt_ids:
            tilt_ids.append(tilt_id)
    print(" %s tilt groups found in dataset" % len(tilt_ids))
    return tilt_ids


def classify_images_into_tiltgroups(tiltgroupList, fileList):
    """ Create a dictionary for each tilt group, e.g.
            {   "tilt_1" : [ "img1.mrc", ... ] ,
                "tilt_2" : [ "img2.mrc", ... ] ,
                ...
                "tilt_n" : [ "img3.mrc", ... ] ,
            }
    """
    classified_dictionary = {}
    ## initialize a dictionary structure
    n = 0
    for tilt in tiltgroupList:
        n += 1
        tilt_name = "tilt_%s" % n
        classified_dictionary[tilt_name] = []
    ## fill the dictionary with files based on matching tilt name
    for file in fileList:
        file_tilt_id = file.split("_")[3]
        ## match the file to the index of the tilt group list
        matching_tilt_group = tiltgroupList.index(file_tilt_id) + 1
        matching_tilt_group_name = "tilt_%s" % matching_tilt_group
        classified_dictionary[matching_tilt_group_name].append(file)
    return classified_dictionary


def write_tilt_data(tilt_data):
    file = "tiltgroups.txt"
    ## write new marked images into file, if any present
    counter = 0
    with open(file, 'w') as f :
        for tilt in tilt_data:
            for img in tilt_data[tilt]:
                counter += 1
                f.write("%s  %s\n" % (tilt, img))

    print(" >> %s entries written into '%s'" % (counter, file))



#############################
###     RUN BLOCK
#############################

if __name__ == "__main__":
    # from pathlib import Path # requires python 3.4+
    # import string
    import os
    import sys
    # import re

    cmdline = sys.argv
    if (check_for_help_flag(cmdline)):
        usage()

    mrcFiles = get_all_mrc_files() ## ["name_1.mrc", "name_2.mrc", ... "name_n.mrc"]

    tiltgroups = find_all_tiltgroups(mrcFiles)

    tilt_data = classify_images_into_tiltgroups(tiltgroups, mrcFiles)

    write_tilt_data(tilt_data)
