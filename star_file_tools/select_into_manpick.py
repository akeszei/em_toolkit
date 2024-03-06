#!/usr/bin/env python3


"""
    A small script to read in a .STAR file with a list of particles, their coordinates, and their associated
    micrographs to print out *_manualpick.star files suitable for use directly in a ManualPick job for a
    subsequent extract and further processing.
"""

#############################
###     FLAGS
#############################
VERBOSE = True

#############################
###     DEFINITION BLOCK
#############################

def usage():
    """ This script requires several input arguments to work correctly. Check they exist, otherwise print usage and exit.
    """
    if not len(sys.argv) == 2:
        print("=================================================================================================================")
        print(" A script to take a .STAR file with particles and return their coordinates in a file format suitable")
        print(" for direct use in a RELION ManualPick job: ")
        print("    $ select_into_manpick.py  INPUT_particles.star")
        print("")
        print(" To use, copy particle .STAR file into a directory and transfer *_manualpick.star output files into the")
        print(" corresponding ManualPick/job###/Micrographs/ directory for inspection & extraction for further processing.")
        print("=================================================================================================================")
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
                column_num = int(line.split()[1].replace("#",""))
                ## handle error case where input .STAR file is missing a necessary rlnColumn type
                if column_num is None :
                    print(" ERROR: Input .STAR file: %s, is missing a column for: %s" % (file, column_name) )
                    sys.exit()
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


# def write_star_file(coordinates, output_file):
#     """ For input coordinate list (as generated by parse_coordinates() function), print a new .STAR file suitable for
#         use by a ManualPick job in RELION.
#             >> Input: (i) coordinates in form a tupled list [ (x,y), ...]; (ii) file name for new file (typically of the convention: Micrograph_name_####_manualpick.star)
#     """
#     particle_num = len(coordinates)
#     print(">> %d coordinates written to %s" % (particle_num, output_file) )
#     ############
#     ## HEADER
#     ############
#     with open(output_file, 'a') as f :  # mode 'a' opens the file for editing, without truncating the file first
#         f.write("\n")
#         f.write("data_\n")
#         f.write("\n")
#         f.write("loop_\n")
#         f.write("_rlnCoordinateX #1\n")
#         f.write("_rlnCoordinateY #2\n")
#         f.write("_rlnClassNumber #3\n")
#         f.write("_rlnAnglePsi #4\n")
#         f.write("_rlnAutopickFigureOfMerit #5\n")
#
#     ############
#     ## BODY
#     ############
#     with open(output_file, 'a') as f :  # mode 'a' opens the file for editing, without truncating the file first
#         for (X_coord, Y_coord) in coordinates:
#             f.write("%s\t%s\t-999\t-999.0\t-999.0\n" % (X_coord, Y_coord))


def write_manpick_files(data_dict):
    """
    note
    """

    for mic in data_dict:
        with open('%s' % (mic+'_manualpick.star'), 'a' ) as f :
            f.write("\n")
            f.write("data_\n")
            f.write("\n")
            f.write("loop_\n")
            f.write("_rlnCoordinateX #1\n")
            f.write("_rlnCoordinateY #2\n")
            f.write("_rlnClassNumber #3\n")
            f.write("_rlnAnglePsi #4\n")
            f.write("_rlnAutopickFigureOfMerit #5\n")
            f.write("_rlnParticleSelectionType #6\n")

    for mic in data_dict:
        with open('%s' % (mic+'_manualpick.star'), 'a' ) as f :
            for (X_coord, Y_coord) in data_dict[mic] :
                f.write("%s\t%s\t-999\t-999.0\t-999.0\t2\n" % (X_coord, Y_coord))


#############################
###     RUN BLOCK
#############################

if __name__ == "__main__":
    import string
    import os
    import sys

    usage()

    # read bash argument $1 as variable
    star_file = sys.argv[1]

    print("... running")

    header_size = header_length(star_file)
    X_coord_column = find_star_column(star_file, '_rlnCoordinateX', header_size)
    Y_coord_column = find_star_column(star_file, '_rlnCoordinateY', header_size)
    mic_name_column = find_star_column(star_file, '_rlnMicrographName', header_size)
    particle_coordinate_info = parse_star_file(star_file, mic_name_column, X_coord_column, Y_coord_column, header_size)
    write_manpick_files(particle_coordinate_info)

    print("... job completed.")
