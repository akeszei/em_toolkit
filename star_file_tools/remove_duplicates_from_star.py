#!/usr/bin/env python3


"""
    Parse a particles .STAR file and drop duplicates based on the extracted particle image data 
"""

#############################
# region :: FLAGS/GLOBALS
#############################
DEBUG = False

#endregion 

#############################
# region :: DEFINITION BLOCK
#############################

def usage():
    print("===================================================================================================")
    print(" A simple script to edit a 'particles.star' file to remove multiple references to a single")
    print(" extracted particle (duplicate entries) based on the 'rlnImageName' column value.")
    print(" Usage:")
    print("    $ remove_duplicates_from_star.py  <particles>.star  ")
    # print(" -----------------------------------------------------------------------------------------------")
    print(" Options (default in brackets): ")
    # print("                   --lt (n) : Find micrographs with particle counts less than the value n")
    # print("                   --gt (n) : Find micrographs with particle counts greater than the value n")
    print("     --o (new_particles.star) : Change the output file name from default")
    print("===================================================================================================")
    sys.exit()

def parse_cmdline(cmd_line):
    ## read all entries and check if the help flag is called at any point
    for cmd in cmd_line:
        if cmd == '-h' or cmd == '--help' or cmd == '--h':
            usage()

    ## parse any flags and set defaults 
    out_fname = 'new_particles.star' # set default 
    for i in range(len(cmd_line)):

        if cmd_line[i] == '--o':
            try:
                out_fname = cmd_line[i+1]
                print(" Save output .STAR file as: %s " % out_fname)
            except:
                print(" Could not parse --o entry or none given, using default: %s" % out_fname)

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

    return star_file, out_fname

def parse_star_file(input_file, output_file, data_start, data_end, column_num, DEBUG = DEBUG):
    """ ### Parameters 
        ```
        input_file = str() # name of .star file to read from 
        output_file = str() # name of the .star file to save lines into 
        data_start = int() # line number from which we expect data entries to evaluate 
        data_end = int() # line number from which we expect to stop evaluating data lines 
        column_num = int() # the column number for each data entry we wish to retrieve the rlnImageName value 
        ``` 
    """
    ## open fresh output file (overwrite existing file if it is there)
    with open(output_file, 'w') as o :
        ## open the input file to read/copy the data from 
        with open(input_file, 'r') as f :
            discovered_rlnImageNames = []
            skipped = 0
            line_num = 0
            for line in f :
                line_num += 1
                if data_start <= line_num <= data_end:
                    print("  ... processing particle #%s" % (line_num - (data_start - 1)), end='\r')
                    rlnImageName = star_handler.get_star_data(line, column_num, DEBUG = DEBUG)
                    ## evaluate if the rlnImageName is a duplicate 
                    if not rlnImageName in discovered_rlnImageNames:
                        ## add the discovered value into the list to keep track
                        discovered_rlnImageNames.append(rlnImageName)
                        ## write the line to the file
                        o.write(line)
                    else:
                        ## if the rlnImageName already exists in the discovered list, then skip the line 
                        skipped += 1
                else:
                    o.write(line)
    print("")
    print(" %s data points were identified as duplicates and dropped from output file: %s" % (skipped, output_file))

    return 

#endregion

#############################
#region :: RUN BLOCK
#############################

if __name__ == "__main__":
    import os
    import sys
    import numpy as np
    from matplotlib import pyplot as plt
    from matplotlib import rcParams # update the condition for autolayout to ensure proper figure formatting

    ## Get the execution path of this script so we can find local modules
    script_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    try:
        sys.path.append(script_path)
        import star_handler 
    except :
        print(" ERROR :: Check if star_handler.py script is in same folder as this script and runs without error (i.e. can be compiled)!")


    starfile, out_fname = parse_cmdline(sys.argv)

    print("... running")
    print(" .STAR file = %s" % starfile)

    TABLE_START, HEADER_START, DATA_START, DATA_END = star_handler.get_table_position(starfile, 'data_particles', DEBUG = DEBUG)
    rlnImageName_COLUMN = star_handler.find_star_column(starfile, "_rlnImageName", HEADER_START, DATA_START - 1, DEBUG = DEBUG)

    parse_star_file(starfile, out_fname, DATA_START, DATA_END, rlnImageName_COLUMN)

    print("... job completed.")

#endregion