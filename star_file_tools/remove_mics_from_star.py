#!/usr/bin/env python3

# 2019-04-24: Wrote script
# 2021-09-08: Update script to work with new star_handler module

"""
    The goal of this script is to take an input micrographs.star file and a list of micrographs
    (basenames only) and return a new .STAR file where micrographs have been removed. Typically,
    this script should be run on a ManualPick job 'micrographs_selected.star' file to unselect
    bad micrographs from the dataset after manual curation.
"""

#############################
###     FLAGS
#############################
DEBUG = True


#############################
###     DEFINITION BLOCK
#############################

def usage():
    print("=================================================================================================================")
    print(" WIP ")
    print("    $ remove_mics_from_star.py  marked_imgs.txt  micrographs.star ")
    print(" -----------------------------------------------------------------------------------------------")
    print(" Options (default in brackets): ")
    print("     --table (data_micrographs) : name of the table in .STAR file to edit (default is 'data_micrographs')")
    print("                          --out : output name of edited .STAR file (e.g. 'edited_file.star')")
    print("=================================================================================================================")
    sys.exit()

def remove_mics_from_star(PARAMS):
    ## unpack parameter variables for readability
    input_star = PARAMS['input_star']
    mic_list_file = PARAMS['mic_list_file']
    CUSTOM_OUTPUT_NAME = PARAMS['CUSTOM_OUTPUT_NAME']
    output_star = PARAMS['output_star']
    table_title = PARAMS['star_table_name']

    ## if no output file name given, create a default one
    if not CUSTOM_OUTPUT_NAME:
        output_star = os.path.splitext(input_star)[0] + '_micsRemoved.star'

    ## get the basenames from the mirograph list file provided
    mics_to_remove = parse_mic_list_file(mic_list_file)

    ## use star_handler module to parse the input file correctly
    HEADER_START, DATA_START, DATA_END = star_handler.get_table_position(input_star, table_title, DEBUG)
    column_name = '_rlnMicrographName'
    column_num = star_handler.find_star_column(input_star, column_name, HEADER_START, (DATA_START - 1), DEBUG)
    data_range = (DATA_START, DATA_END)

    ## open the input star file and use the parsed information to write out a new one with the requested changes
    read_write_star(input_star, mics_to_remove, data_range, column_num, output_star)
    return

def parse_mic_list_file(file):
    mic_list = []
    with open(file,'r') as f :
        for line in f :
            line = line.strip()
            # remove empty lines
            if len(line) == 0 :
                pass
            # comment handling
            elif line[0] == "#":
                pass
            # ignore empty lines
            elif len(line) > 0 :
                if line not in mic_list:
                    mic_list.append(line)
    if DEBUG:
        print(" ... %s micrograph(s) found in '%s'" % (len(mic_list), file) )
    return mic_list

def read_write_star(file, mics_to_remove, line_range, star_column_num, output_fname) :
    """ Open a .star file and read it line-by-line. Evaluate each line with conditional functions.
        ============================================
        PARAMETERS:
        ============================================
            file = str(); name of .STAR file to read from
            mics_to_remove = list(); list of str() representing micrograph base names
            line_range = tuple(a,b); where a, b are int() representing start and end line # for data to be worked on
            star_column_num = int(); from table header, which column corresponds to 'rlnMicrographName'
            output_fname = str(); name of the file that will be saved on disk
        ===========================================
        OUTPUT:
        ============================================
            No output. Creates a new .STAR file.
    """
    ## create an empty file with the target name (erase previous file if present)
    f = open(output_fname, 'w+')
    f.close()

    ## parse through input file and run algorithm on target lines
    with open(file, 'r') as f :
        line_num = 0 # keep track of line number
        mics_removed = 0 # keep track of mics identified for removal
        for line in f :
            # keep track of what line number is being read
            line_num += 1

            # copy any lines that are out of range without any edit/change
            if line_num < line_range[0] or line_num > line_range[1]:
                write_line(output_fname, line)
                continue
            # deal with empty lines (usually found at the end of the .STAR file)
            if len(line.strip()) == 0 :
                write_line(output_fname, line)
                continue

            ## if reached this part of loop, we are in the data lines of the .STAR file

            # extract micrograph basename from the relevant column
            current_name = star_handler.remove_path(star_handler.get_star_data(line, star_column_num))
            current_basename = os.path.splitext(current_name)[0]

            if current_basename in mics_to_remove:
                mics_removed += 1
                # if DEBUG:
                #     print(" >> Remove micrograph from .STAR file: %s" % current_name)
            else:
                write_line(output_fname, line)
    if DEBUG:
        print("-------------------------------------------------------------------------")
        print("  >> %s micrograph lines removed from %s file." % (mics_removed, file))
        print("=========================================================================")
    return None


def write_line(file, l) :
    """ Open the file and write the line into it as a new line string
    """
    with open(file, 'a') as f :  # mode 'a' opens the file for editing, without truncating the file first
        f.write(l)
    return



#############################
###     RUN BLOCK
#############################

if __name__ == "__main__":
    import string
    import os
    import sys
    import cmdline_parser
    import star_handler


    ##################################
    ## ASSIGN DEFAULT VARIABLES
    ##################################
    PARAMS = {
        'input_star'         : str(),
        'mic_list_file'      : str(), ## file with list of micrograph basenames to remove
        'CUSTOM_OUTPUT_NAME' : False,
        'output_star'        : str(),
        'star_table_name'    : 'data_micrographs'
        }
    ##################################

    ##################################
    ## SET UP EXPECTED DATA FOR PARSER
    ##################################
    FLAGS = {
    '--out' : (
        'output_star', ## PARAMS key
        str(), ## data type
        (), ## legal entries/range
        False, ## toggle information for any entries following flag
        (True, 'CUSTOM_OUTPUT_NAME', True), ## if flag itself has toggle information
        False ## if flag has a default setting
    ),
    '--table' : (
        'star_table_name', ## PARAMS key
        str(), ## data type
        (), ## legal entries/range
        False, ## toggle information for any entries following flag
        False, ## if flag itself has toggle information
        True ## if flag has a default setting
    ),
    }

    FILES = { ## cmd line index    allowed extensions   ## can launch batch mode
        'mic_list_file': (1,       ['.txt'],            False),
        'input_star' : (2,         ['.star'],           False),
        }
    ##################################


    PARAMS, EXIT_CODE = cmdline_parser.parse(sys.argv, 1, PARAMS, FLAGS, FILES)
    if EXIT_CODE < 0:
        # print("Could not correctly parse cmd line")
        usage()
        sys.exit()
    cmdline_parser.print_parameters(PARAMS, sys.argv)

    remove_mics_from_star(PARAMS)

    # print("... running")
    # print("========================")
    #
    # header_size = header_length(star_file)
    # rln_column_index = find_star_column(star_file, 'rlnMicrographName', header_size)
    #
    # bad_mic_list = parse_bad_mics(bad_mics)
    #
    # # name the output file name based on the prefix of the original file with a modified suffix
    # output_fname = star_file.replace('.star','')+'_modified.star'
    #
    # read_write_star(star_file, bad_mic_list, header_size, rln_column_index, output_fname)
    #
    # print("========================")
    # print("... job completed.")
