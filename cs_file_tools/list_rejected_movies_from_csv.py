#!/usr/bin/env python3

#############################
###     GLOBAL FLAGS
#############################
DEBUG = False

#############################
###     DEFINITION BLOCK
#############################

def usage():
    print("===================================================================================================")
    print(" Read a .CSV file output from cryosparc live session and return a list of ")
    print(" all movies rejected by name. This list can be used to delete images, e.g.:")
    print("    $ for mic in $(cat rejected_movies.txt); do mic_path=$(find -name $mic); rm $mic_path; done")
    print(" Usage:")
    print("    $ list_rejected_movies.py  input.csv ")
    # print(" -----------------------------------------------------------------------------------------------")
    # print(" Options (default in brackets): ")
    # print("===================================================================================================")
    sys.exit()
    return

def get_csv_data(fname):
    """ Convert CSV file into a pandas DataFrame object for easy manipulation 
    """
    csv_data = pd.read_csv(fname)
    return csv_data 

def get_rejected_mics(csv_data):
    """ Run through the DataFrame object and check for the cryoSPARC 'Theshold Reject' flag 
        and extract the corresponding micrograph name when True. Return the list of micrographs
        that result.
    """
    rejection_list = []
    ## another approach is to look at each file name and then use its unique name to look up its threshold flag in the DataFrame
    for row in csv_data.iterrows():
        index, row_obj = row 
        # print(row_obj)
        REJECT = row_obj['Threshold Reject']
        if REJECT:
            mic_basename = os.path.splitext(os.path.basename(row_obj['File Path']))[0]
            rejection_list.append(mic_basename)
            if DEBUG:
                print("===================================================================")
                print(" Rejected: %s" % mic_basename)
                print("-------------------------------------------------------------------")
                print("   ... ID = %s" % row_obj['ID'])
                print("   ... CTF Fit (A) = %.2f" % row_obj['CTF Fit (A)'])

    return rejection_list

def write_list_to_file(list_obj, out_fname):
    with open(out_fname, "w") as f:
        for obj in list_obj:
            f.write("%s \n" % obj)
    return 

def print_summary(csv_file, rejection_list, out_fname):
    print("===================================================================")
    print("  COMPLETE.")
    print("===================================================================")
    print(" %s micrographs were flagged as rejected from: %s" % (len(rejection_list), csv_file))
    print(" ... micrograph names are listed in: %s" % out_fname)
    print("-------------------------------------------------------------------")
    print(" Use the output file to manually delete movies, e.g.:")
    print("    $ for mic in $(cat %s); do mic_path=$(find -name $mic); rm $mic_path; done" % out_fname)
    
def check_for_help_flag(cmdline):
    for entry in cmdline:
        if entry in ['-h', '-help', '--h', '--help']:
            if DEBUG:
                print(' ... help flag called (%s).' % entry)
            return True
    return False

#############################
###     RUN BLOCK
#############################

if __name__ == "__main__":

    import os
    import sys
    import pandas as pd

    ## check if help flag was called or we have a minimum number of arguments to evaluate
    cmdline = sys.argv
    min_args = 1
    if len(cmdline) - 1 < min_args or check_for_help_flag(cmdline):
        print(" Not enough arguments, or help flag called")
        sys.exit()

    out_fname = 'rejected_mics.txt'
    csv_file = sys.argv[1]
    if not os.path.splitext(csv_file)[-1] in [".csv", ".CSV"]:
        print(" Input file does not have the proper extension (.csv)")
        sys.exit()

    print(" RUNNING: list_rejected_movies.py  %s" % csv_file)
    # print("-------------------------------------------------------------------")
    csv_data = get_csv_data(csv_file)

    rejection_list = get_rejected_mics(csv_data)

    write_list_to_file(rejection_list, out_fname)

    print_summary(csv_file, rejection_list, out_fname)
