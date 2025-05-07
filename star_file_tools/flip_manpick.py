#!/usr/bin/env python3

"""
    Quickly edit _manualpick.star files to flip the coordinates around an axis 
"""

#############################
#region     FLAGS
#############################
VERBOSE = False

#endregion
#############################


#############################
#region     DEFINITION BLOCK
#############################

def usage():
    print("===================================================================================================")
    print(" Usage:")
    print("    $ flip_manpick.py  <particles>.star --img_dim <x_length>x<y_length> ")
    print(" Example:")
    print("    $ flip_manpick.py input.star --img_dim 4092x4092 --flipy")
    print(" -----------------------------------------------------------------------------------------------")
    print(" Options (default in brackets): ")
    print("                   --flipy : Find micrographs with particle counts less than the value n")
    print("                   --flipx : Find micrographs with particle counts greater than the value n")
    # print("   --o (threshold_mics.txt) : Change the output file name from default")
    print("===================================================================================================")
    sys.exit()

def parse_cmdline(cmd_line):
    """ 
    RETURNS
        ```
        tuple() of form: ( star_file, img_x, img_y, FLIPX, FLIPY )
        ```
    """
    ## read all entries and check if the help flag is called at any point
    for cmd in cmd_line:
        if cmd == '-h' or cmd == '--help' or cmd == '--h':
            usage()

    ## check for the .STAR file  
    star_file = None
    for i in range(len(cmd_line)):
        if star_file == None:
            if os.path.splitext(cmd_line[i])[1] in ['.star', '.STAR']:
                star_file = cmd_line[i]
        elif os.path.splitext(cmd_line[i])[1] in ['.star', '.STAR']:
            print(" WARNING :: More than one .STAR file was detected as input, only the first entry (%s) will be parsed " % star_file)
            
    if star_file == None:
        print(" ERROR :: No .STAR file was detected as input!")
        usage()

    ## parse any flags and set defaults 
    FLIPX = False
    FLIPY = False
    for i in range(len(cmd_line)):
        if cmd_line[i] in ['--flipy', '--flipY']:
            FLIPY = True
        if cmd_line[i] in ['--flipy', '--flipY']:
            FLIPY = True
        if cmd_line[i] == '--img_dim':
            ## sanity check user input
            img_shape = cmd_line[i + 1]
            if not "x" in img_shape :
                print("ERROR: Incorrect --img_dim provided: ", img_shape, "; instead, try of the form: 4092x4092")
                usage()
            try:
                img_x = int(img_shape.split('x')[0]) # Define number of rows
            except: 
                print(" ERROR :: Could not parse the X value for the input image dimension flag")
            try:
                img_y = int(img_shape.split('x')[1]) # Define number of rows
            except: 
                print(" ERROR :: Could not parse the Y value for the input image dimension flag")

    return star_file, img_x, img_y, FLIPX, FLIPY

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
    mic_name = os.path.splitext(os.path.basename(file))[0]

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
        if VERBOSE:
            print(" %s coordinates found from .STAR file (%s)" % (len(data_parse_list[mic_name]), mic_name))
        return data_parse_list

def write_manpick_files(data_dict, FLIPX, FLIPY, x_len, y_len):
    """
    Write out _manualpick.star files for each micrograph containing coordinates 
    """
    for mic in data_dict:
        ## add _manualpick.star if it is not in the name already 
        if '_manualpick' in mic:
            out_fname = mic + '.star'
        else:
            out_fname = mic+'_manualpick.star'

        ## overwrite a fresh output file with its header 
        with open('%s' % (out_fname), 'w' ) as f :
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
                if FLIPX:
                    X_coord = x_len - X_coord
                    if X_coord < 0:
                        print(" WARNING :: Flipped X coordinate is negative!")
                if FLIPY: 
                    Y_coord = y_len - Y_coord
                    if Y_coord < 0:
                        print(" WARNING :: Flipped Y coordinate is negative!")

                f.write("%s\t%s\t2\t-999.0\t-999.0\n" % (X_coord, Y_coord))

    if VERBOSE:
        print(" Saved modified .STAR file as: %s" % out_fname)
    return out_fname

#endregion
#############################



#############################
#region     RUN BLOCK
#############################

if __name__ == "__main__":
    import os
    import sys

    star_file, img_x, img_y, FLIPX, FLIPY = parse_cmdline(sys.argv)

    print(" Input star file: %s" % star_file)
    print(" Flip X = %s" % FLIPX)
    print(" Flip Y = %s" % FLIPY)
    print(" Image dimensions = (%s, %s)" % (img_x, img_y))


    header_size = header_length(star_file)
    X_coord_column = find_star_column(star_file, '_rlnCoordinateX', header_size)
    Y_coord_column = find_star_column(star_file, '_rlnCoordinateY', header_size)
    particle_coordinate_info = parse_star_file(star_file, X_coord_column, Y_coord_column, header_size)

    out_fname = write_manpick_files(particle_coordinate_info, FLIPX, FLIPY, img_x, img_y)

    # print(" ... written: %s" % out_fname)

#endregion
#############################
