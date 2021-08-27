#!/usr/bin/env python3

"""
    A script to easily change the optics group number for all particles that come from micrographs
    matching a glob-based search criteria.

    For large files, use vim to manually update the optics table header

    NOTE: The output .star file needs to be in Linux-style line endings to be properly read by RELION
"""

## 2021-02-25: Wrote script & tested on mTRC dataset

#############################
###     FLAGS
#############################
DEBUG = True

#############################
###     DEFINITION BLOCK
#############################

def usage():
    """ This script requires several input arguments to work correctly. Check they exist, otherwise print usage and exit.
    """
    if not len(sys.argv) == 4:
        print("===============================================================================================================================")
        print(" Remap the optics group assigment of particles based on a micrograph name match criteria:")
        print("    $ remap_optics_groups.py  particles.star  mic_name_match_critera  optics_group_value  ")
        print(" Example command: ")
        print("    $ remap_optics_groups.py  particles.star  Name*012.mrc  12  ")
        print("===============================================================================================================================")
        sys.exit()
    else:
        return


def header_length(file):
    """ For an input .STAR file, define the length of the header and
        return the last line in the header. Header length is determined by
        finding the highest line number starting with '_' character
    """
    with open(file, 'r') as f :
        line_num = 0
        header_lines = []
        for line in f :
            line_num += 1
            first_character = ""
            line = line.strip() # remove empty spaces around line
            line_to_list = line.split() # break words into indexed list format
            # ignore empty lines
            if len(line) == 0 :
                continue
            first_character = list(line_to_list[0])[0]
            if first_character == '_':
                header_lines.append(line_num)
                if DEBUG:
                    print("Line # %d = " % line_num, end="")
                    print(line, " --> ", line_to_list, sep=" ")
        return max(header_lines)

def find_star_column(file, column_type, header_length) :
    """ For an input .STAR file, search through the header and find the column numbers assigned to a given column_type (e.g. 'rlnMicrographName', ...)
    """
    column_num = None # initialize variable for error handling
    with open(file, 'r') as f :
        line_num = 0
        for line in f :
            line_num += 1
            ## extract column number for micrograph name
            if column_type in line :
                column_num = int(line.split()[1].replace("#",""))
            ## search header and no further to find setup values
            if line_num >= header_length :
                ## handle error case where input .STAR file is missing a necessary rlnColumn type
                if column_num is None :
                    print("Input .STAR file: %s, is missing a column for: %s" % (file, column_type) )
                    sys.exit()
                else:
                    if DEBUG:
                        # print("Read though header (%s lines total)" % header_length)
                        print("Column value for %s is %s" % (column_type, column_num))
                    return column_num


def find_star_info(line, column):
    """ For a given .STAR file line entry, extract the data at the given column index.
        If the column does not exist (e.g. for a header line read in), return 'False'
    """
    # break an input line into a list data type for column-by-column indexing
    line_to_list = line.split()
    try:
        column_value = line_to_list[column-1]
        # if DEBUG:
        #     print("Data in column #%s = %s" % (column, column_value))
        return column_value
    except:
        return False

def extract_mic_name(input_string):
    """ Parse the entry for 'rlnMicrographName' to extract only the micrograph name without any path names etc...
    """
    mic_name = os.path.basename(input_string)
    # if VERBOSE:
    #     print("Extract micrograph name from entry: %s -> %s" % (input_string, mic_name))
    return mic_name

def remap_optics_group(file, column_micName, column_opticsGroup, header_size, optics_value):
    """
    """
    global search_criteria
    with open(file, 'r') as f :
        lines = f.readlines()

    with open(file, 'w') as f :
        counter = 0 ## to get statistics on number of particles changed
        ## for overwriting a file see solution : https://stackoverflow.com/questions/41667617/how-to-overwrite-a-file-correctly
        for i in range(len(lines)):
            line_num = i + 1
            line = lines[i]
            ## copy the header into the new file
            if line_num <= header_size:
                f.write(line)
            ## ignore empty lines
            if len(line.strip()) == 0 :
                continue
            ## start working only after the header length
            if line_num > header_size:
                ## get the micrograph name
                mic_name = extract_mic_name(find_star_info(line, column_micName))
                ## check if the micrograph name matches the search criteria using a glob-style matchmaking
                if Path(mic_name).match(search_criteria):
                    counter += 1
                    if DEBUG and counter < 9: print(" >> search_criteria = %s ; match found = %s ; ... change optics group to: %s" % (search_criteria, mic_name, optics_value) )
                    ## on a match change the optics value in the correct column
                    new_line = line.split()
                    new_line[column_opticsGroup - 1] = optics_value ## change the column
                    f.write(' ' + '\t'.join(new_line) + '\n')
                else:
                    f.write(line)
    if DEBUG:
        print("...")
        print( "{:,}".format(counter) + " particle optical groups were updated")


#############################
###     RUN BLOCK
#############################

if __name__ == "__main__":
    from pathlib import Path # requires python 3.4+
    import string
    import os
    import sys
    import re

    usage()

    # read bash arguments $1, $2, ... as variables
    star_file = sys.argv[1]
    search_criteria = sys.argv[2]
    new_optics_value = sys.argv[3]

    print("... running")

    header_size = header_length(star_file)
    mic_name_column = find_star_column(star_file, '_rlnMicrographName', header_size)
    optics_column = find_star_column(star_file, '_rlnOpticsGroup', header_size)

    remap_optics_group(star_file, mic_name_column, optics_column, header_size, new_optics_value)

    print("... job completed.")
