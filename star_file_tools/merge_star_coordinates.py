#!/usr/bin/env python3

###############################
##  FLAGS
###############################
DEBUG = True
###############################

def usage():
    print("===================================================================================================")
    print(" Run this in a directory with .star files named after each micrograph and containing X & Y")
    print(" coordinate data (e.g. output from crYOLO STAR/ directory, or manualpick.star files) to ")
    print(" generate a new 'merged_coordinates.star' file containing each coordinate as a 'particle'")
    print(" suitable for import into cryoSPARC. Double check if you need to flip y-axis after import.")
    print(" Usage:")
    print("    $ merge_star_coordinates.py ")
    print("===================================================================================================")
    sys.exit()

def find_all_star_files(ignore_file = "merged_coordinates.star"):
    """ Return list of .star files in cwd
    """
    all_files_in_dir = os.listdir()
    star_files = []
    for file in all_files_in_dir:
        if os.path.splitext(file)[1] == ".star":
            if file == ignore_file:
                continue
            else:
                star_files.append(file)
    return star_files

def get_coords(input_star, VERBOSE = False):
    ## use star_handler module to parse the input file correctly
    table_title = "data_"
    TABLE_START, HEADER_START, DATA_START, DATA_END = star_handler.get_table_position(input_star, table_title, DEBUG = False)
    X_column_name = '_rlnCoordinateX'
    Y_column_name = '_rlnCoordinateY'
    X_column_num = star_handler.find_star_column(input_star, X_column_name, HEADER_START, (DATA_START - 1), DEBUG = False)
    Y_column_num = star_handler.find_star_column(input_star, Y_column_name, HEADER_START, (DATA_START - 1), DEBUG = False)
    data_range = (DATA_START, DATA_END)

    # print(" X column, Y column indexes = (%s, %s); data line range = %s" % (X_column_num, Y_column_num, data_range))
    coords = []
    ## parse through input file and run algorithm on target lines
    with open(input_star, 'r') as f :
        line_num = 0 # keep track of line number
        for line in f :
            # keep track of what line number is being read
            line_num += 1

            # ignore lines out of range
            if line_num < data_range[0] or line_num > data_range[1]:
                continue

            # deal with empty lines (usually found at the end of the .STAR file)
            if len(line.strip()) == 0 :
                continue

            X_coord = star_handler.get_star_data(line, X_column_num)
            Y_coord = star_handler.get_star_data(line, Y_column_num)
            coords.append((X_coord, Y_coord))
    if VERBOSE:
        print(" ... %s coordinates extracted from file: %s" % (len(coords), input_star))
    return coords

def prepare_merged_star_file(fname = 'merged_coordinates.star'):
    ## create an empty file with the target name (erase previous file if present)
    f = open(fname, 'w+')
    f.write("\n")
    f.write("data_\n")
    f.write("\n")
    f.write("loop_\n")
    f.write("_rlnMicrographName #1\n")
    f.write("_rlnCoordinateX #2\n")
    f.write("_rlnCoordinateY #3\n")
    f.close()
    return

def add_coords_to_file(mic_name, coordinates, target_file = 'merged_coordinates.star'):
    with open(target_file, 'a') as f:
        for (X_coord, Y_coord) in coordinates:
            f.write("%s\t%s\t%s\n" % (mic_name, X_coord, Y_coord))
    return

def merge_star_file_coords():
    """ The main function for this script.
    """
    ## 0. Prepare an empty .star file with correct headers to populate with data
    prepare_merged_star_file()
    total_coordinates_parsed = 0

    ## 1. Get all the star files in the directory
    star_files = find_all_star_files()
    if DEBUG:
        print("   >> %s .star files found in directory" % len(star_files))
        print(" -----------------------------------------------")

    ## 2. Iterate over each star file
    n = 0
    for star_file in star_files:
        n += 1
        if n == 4:
            if DEBUG:
                print(" ... ")
        ## 2a. Extract the coordinates in that file
        if n < 4:
            coords_in_file = get_coords(star_file, VERBOSE = DEBUG)
        elif n > len(star_files) - 3:
            coords_in_file = get_coords(star_file, VERBOSE = DEBUG)
        else:
            coords_in_file = get_coords(star_file, VERBOSE = False)
        total_coordinates_parsed += len(coords_in_file)
        ## 2b. Write the coordinates to a target star file
        add_coords_to_file(star_file, coords_in_file, target_file = 'merged_coordinates.star')

    if DEBUG:
        print(" -----------------------------------------------")
        print("    TOTAL COORDINATES PARSED = %s" % "{:,}".format(total_coordinates_parsed))
    return


#############################
###     RUN BLOCK
#############################

if __name__ == "__main__":
    import string
    import os
    import sys
    import star_handler

    cmd_line = sys.argv
    if len(cmd_line) != 1:
        usage()

    if DEBUG:
        print(" ===============================================")
        print("     Running: merge_star_coordinates.py")
        print(" -----------------------------------------------")

    merge_star_file_coords()
