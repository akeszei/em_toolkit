#!/usr/bin/env python3


"""
    A quick script to add necessary empty metadata elements to the output .STAR files from
    crYOLO so they can be opened and edited in RELION ManualPick job window.  
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
    if not len(sys.argv) == 2:
        print("=================================================================================================================")
        print(" A script to take a crYOLO output .STAR file with coordinates and return a .STAR file suitable ")
        print(" for direct use in a RELION ManualPick job: ")
        print("    $ cryolo2manpick.py  MIC_NAME.star")
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

def parse_star_file(file, columnX, columnY, header_size):
    """ For a given .STAR file with micrograph name, extract the X Y coordinates of all particles present.
    PARAMETERS 
        file = str(); name of the file (i.e. micrograph.star)
        columnX = int(); star column for the X coordinate 
        colummnY = int(); star column for the Y coordinate 
        header_size = int(); number of lines which make up the header 
    RETURNS
        data_parse_list = dictionary of tuples: { mic1 : [(x1,y1),(x2,y2),...], mic2 : [(x1,y1),...] ...}
    """
    ## get the base name of the image (i.e. micrograph_001.star -> micrograph_001)
    mic_name = os.path.splitext(os.path.basename(cryolo_star_file))[0]

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
                if mic_name not in data_parse_list:
                    data_parse_list[mic_name] = [(X_coordinate, Y_coordinate)]
                else:
                    data_parse_list[mic_name].append((X_coordinate, Y_coordinate))
                # if VERBOSE:
                #     print("Coordinates found: (%s :: %s, %s)" % (mic_name, X_coordinate, Y_coordinate))
        return data_parse_list

def write_manpick_files(data_dict):
    """
    Write out _manualpick.star files for each micrograph containing coordinates 
    """
    for mic in data_dict:
        out_fname = mic+'_manualpick.star'
        with open('%s' % (out_fname), 'a' ) as f :
            f.write("\n")
            f.write("data_\n")
            f.write("\n")
            f.write("loop_\n")
            f.write("_rlnCoordinateX #1\n")
            f.write("_rlnCoordinateY #2\n")
            f.write("_rlnParticleSelectionType #3\n")
            f.write("_rlnAnglePsi #4\n")
            f.write("_rlnAutopickFigureOfMerit #5\n")

    for mic in data_dict:
        with open('%s' % (out_fname), 'a' ) as f :
            for (X_coord, Y_coord) in data_dict[mic] :
                f.write("%s\t%s\t2\t-999.0\t-999.0\n" % (X_coord, Y_coord))
    return out_fname

#############################
###     RUN BLOCK
#############################

if __name__ == "__main__":
    import os
    import sys

    usage()

    # read bash argument $1 as variable
    cryolo_star_file = sys.argv[1]

    ## get only the base file name without the .STAR extension given by crYOLO
    header_size = header_length(cryolo_star_file)
    X_coord_column = find_star_column(cryolo_star_file, '_rlnCoordinateX', header_size)
    Y_coord_column = find_star_column(cryolo_star_file, '_rlnCoordinateY', header_size)
    particle_coordinate_info = parse_star_file(cryolo_star_file, X_coord_column, Y_coord_column, header_size)
    out_fname = write_manpick_files(particle_coordinate_info)

    print(" ... written: %s" % out_fname)