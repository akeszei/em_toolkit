#!/usr/bin/env python3

# 2019-02-05: Started project
# 2019-02-06: Script is ready to be used. Might benefit from more output outside of VERBOSE flag

"""
    For an input RELION coordinate file and initialized cistem sqlite .DB file, return a coordinate file suitable
    for import into cistem.
    The main steps of this script are to read the .DB file and associate each RELION particle coordinate with the
    correct micrograph .DB ID number.
"""

#############################
###     FLAGS
#############################
VERBOSE = False

#############################
###     DEFINITION BLOCK
#############################

def usage():
    """ This script requires several input arguments to work correctly. Check they exist, otherwise print usage and exit.
    """
    if not len(sys.argv) == 4:
        print("=================================================================================================================")
        print(" The coordinates must be for the same micrograph scales (e.g. binned equivalently) to work correctly.")
        print("    $ relion_to_cistem_coords.py  INPUT_particles.star  INPUT_project.db  ang_pix")
        print("=================================================================================================================")
        sys.exit()
    else:
        return

def parse_db_file(file, table_name, table_data_entries):
    """ Parse an sqlite3 .DB file to extract the data entries for each micrograph and its associated ID # in the database:
         >> INPUT: (i) file as string; (ii) table_name as string (e.g. parent table name); (iii) table_data_entries as list of strings (e.g. columns from the parent table to extract: [ 'column_1', 'column_2', ... ]
         >> RETURN: dictionary matching each micrograph name to its ID number
    """
    d = dict()
    # open a connection to the database
    conn = sq.connect(file)
    # create a cursor object to navigate the data structure using the given table identifiers
    cursor = conn.execute("SELECT %s from %s" % (', '.join(table_data_entries), table_name))
    for row in cursor:
        d[row[1]] = row[0]
        # if VERBOSE:
        #     print(row, "... Image ID = %s, Image name = %s" % (row[0], row[1]))
    if VERBOSE:
        print (d)
    # close connection to database
    conn.close()
    return d

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
                if VERBOSE:
                    print("Line # %d = " % line_num, end="")
                    print(line, " --> ", line_to_list, sep=" ")
        return max(header_lines)

def find_star_column(file, column_type, header_length) :
    """ For an input .STAR file, search through the header and find the column numbers assigned to a given column_type (e.g. 'rlnMicrographName', ...)
    """
    with open(file, 'r') as f :
        line_num = 0
        for line in f :
            line_num += 1
            # extract column number for micrograph name
            if column_type in line :
                for i in line.split()[1]:
                    if i in string.digits :
                        column_num = int(i)
            # search header and no further to find setup values
            if line_num >= header_length :
                if VERBOSE:
                    # print("Read though header (%s lines total)" % header_length)
                    print("Column value for %s is %d" % (column_type, column_num))
                return column_num

def find_star_info(line, column):
    """ For a given .STAR file line entry, extract the data at the given column index.
        If the column does not exist (e.g. for a header line read in), return 'False'
    """
    # break an input line into a list data type for column-by-column indexing
    line_to_list = line.split()
    try:
        column_value = line_to_list[column-1]
        # if VERBOSE:
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

def parse_star_file(file, columnName, columnX, columnY, header_size):
    """ For a given .STAR file, extract the micrograph name, X Y coordinates, and class of all particles present.
            >> Input (i) .STAR file name as str; (ii) column Name,X,Y as int; (iii) header_size as int
            >> Returns a dictionary of tuples: { mic1 : [(x1,y1),(x2,y2),...], mic2 : [(x1,y1),...] ...}
    """
    with open(file, 'r') as f :
        data_parse_list = dict()
        line_num = 0
        for line in f :
            line_num += 1
            # ignore empty lines
            if len(line.strip()) == 0 :
                continue
            # start working only after the header length
            if line_num > header_size:
                X_coordinate = float(find_star_info(line, columnX))
                Y_coordinate = float(find_star_info(line, columnY))
                mic_name = os.path.splitext(extract_mic_name(find_star_info(line, columnName)))[0]
                if mic_name not in data_parse_list:
                    data_parse_list[mic_name] = [(X_coordinate, Y_coordinate)]
                else:
                    data_parse_list[mic_name].append((X_coordinate, Y_coordinate))
                # if VERBOSE:
                #     print("Coordinates found: (%s, %s, %s)" % (mic_name, X_coordinate, Y_coordinate))
        return data_parse_list

def write_star_file(db_dict, star_dict, ang_pix):
    """ For two given dictionaries, return a coordinate file suitable for import into cistem.
        Coordinates are converted from pixel to angstroms via the ang_pix constant
    """
    counter = 0
    for mic in star_dict:
        # deal with cases where the cistem db list lacks micrographs that might be in the particle file (e.g. corrupted during transfer/upload)
        if not mic in db_dict:
            print("Micrograph %s not found in cistem database!" % mic)
        else:
            for X,Y in star_dict[mic]:
                if VERBOSE:
                    print(mic, X,Y, '->', db_dict[mic] , X*ang_pix, Y*ang_pix)
                with open('cistem_input_coordinates.txt', 'a') as f :
                    f.write("%s   %0.2f \t%0.2f \n" % (db_dict[mic], X*ang_pix, Y*ang_pix))
                counter += 1
    print("Written %s coordinates" % counter)
    return


#############################
###     RUN BLOCK
#############################

if __name__ == "__main__":
    import string
    import os
    import sys
    import numpy as np
    import sqlite3 as sq

    usage()

    # read bash arguments $1, $2, and $3 as variables
    star_file = sys.argv[1]
    db_file = sys.argv[2]
    ang_pix = float(sys.argv[3])

    print("... running")

    cistem_db_file = parse_db_file(db_file, 'IMAGE_ASSETS', ['image_asset_id', 'name'])

    header_size = header_length(star_file)
    X_coord_column = find_star_column(star_file, '_rlnCoordinateX', header_size)
    Y_coord_column = find_star_column(star_file, '_rlnCoordinateY', header_size)
    mic_name_column = find_star_column(star_file, '_rlnMicrographName', header_size)
    particle_coordinate_info = parse_star_file(star_file, mic_name_column, X_coord_column, Y_coord_column, header_size)
    write_star_file(cistem_db_file, particle_coordinate_info, ang_pix)

    print("... job completed.")
