#!/usr/bin/env python3

"""
    Sort EPU data into tilt groups using code groups in the filename, e.g.:
        FoilHole_<x>_Data_<y>_<tiltgroup>_<d>_<t>_EER.eer
    The data will be printed out into a file of the form:
        tilt_1  FoilHole_<x>_Data_<y>_<tiltgroup>_<d>_<t>_EER.eer
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
        if os.path.splitext(file)[1].lower() == ".mrc":
            counter += 1
            mrcFiles.append(file)

    print(" %s .mrc files found in directory" % counter)
    return mrcFiles


def get_all_eer_files():
    counter = 0
    allFiles = os.listdir()
    eerFiles = []
    for file in allFiles:
        if os.path.splitext(file)[1].lower() == ".eer":
            counter += 1
            eerFiles.append(file)

    print(" %s .eer files found in directory" % counter)
    return eerFiles


def find_all_tiltgroups(fileList):
    """ Find all unique ID codes for each tilt group in the dataset and return them as a list for use:
            [ "tilt_id_1", "tilt_id_2", ... "tilt_id_n"]
    """
    tilt_ids = []
    for file in fileList:
        filename_to_list = file.split("_") ## REF: https://forum.scilifelab.se/t/creating-optics-groups-from-epu-afis-data-and-more/122/7
                                           ## FoilHole_<x>_Data_<y>_<tiltgroup>_<d>_<t>_EER.eer
                                           ## Look for the second entry after 'Data'
        idx_position_of_data = filename_to_list.index('Data')
        relative_idx_position_from_data_to_tiltgrp = 2
        tilt_id = filename_to_list[idx_position_of_data + relative_idx_position_from_data_to_tiltgrp]
        if not tilt_id in tilt_ids:
            tilt_ids.append(tilt_id)
    print(" %s tilt groups found in dataset" % len(tilt_ids))
    return tilt_ids


def classify_images_into_tiltgroups(tiltgroupList, fileList):
    """ Create a dictionary for each tilt group, e.g.
            {   "tilt_1" : [ "img1", ... ] ,
                "tilt_2" : [ "img2", ... ] ,
                ...
                "tilt_n" : [ "img3", ... ] ,
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

    ## try getting eer files first, if that fails try getting mrc next 
    imgFiles = get_all_eer_files()
    if len(imgFiles) == 0:
        imgFiles = get_all_mrc_files() ## ["name_1.mrc", "name_2.mrc", ... "name_n.mrc"]

    tiltgroups = find_all_tiltgroups(imgFiles)

    tilt_data = classify_images_into_tiltgroups(tiltgroups, imgFiles)

    write_tilt_data(tilt_data)
