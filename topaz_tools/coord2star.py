#!/usr/bin/env python3


"""
    Read in a coordinates file and output a .STAR file suitable for use directly in a ManPick job with optional unbinning  
"""

#############################
#region     FLAGS
#############################
DEBUG = False

#endregion

#############################
#region    DEFINITION BLOCK
#############################

def usage():
    """ This script requires several input arguments to work correctly. Check they exist, otherwise print usage and exit.
    """
    if not len(sys.argv) >= 2:
        print("===============================================================================================")
        print(" A script to take a csv output .COORD file with coordinates and return a .STAR ")
        print(" file suitable for direct use in a RELION ManualPick job: ")
        print("    $ coord2star.py  <file>.coord/txt")
        print(" Use in a bash loop to change many files in a directory with one command, e.g.:")
        print("    $ for c in *.coord; do coord2star.py $c; done")
        print(" -----------------------------------------------------------------------------------------------")
        print(" Options (default in brackets): ")
        print("        --unbin (n) : Rescale picked coordinates by n (e.g. binned_angpix / raw_angpix)")
        print("===============================================================================================")
        sys.exit()
    else:
        return

def get_coord_file(fname, DEBUT = True):
    if fname == None:
        print(" !! ERROR :: No .COORD/TXT file was parsed from the command line!")
        exit()
        
    ## check file exists 
    if not os.path.isfile(fname):
        print(" !! ERROR :: Input file not found (%s)" % fname)

    ## check headers are as expected
    HEADER_CHECK = False
    with open(fname, 'r') as f :
        for line in f :
            ## ignore empty lines
            if len(line.strip()) == 0 :
                continue
            ## ignore comments indicated by # symbol
            if line.strip()[0] == '#':
                continue 
            ## take the first line that has non-comment text and check it for headers 
            file_headers = line.strip().split()
            if 'image_name' in file_headers:
                if 'x_coord' in file_headers:
                    if 'y_coord' in file_headers:
                        if 'score' in file_headers:
                            HEADER_CHECK = True

    if HEADER_CHECK:
        return fname
    else:
        print(" !! ERROR :: Input coordinate file (%s) is missing expected headers:" % fname)
        print("      image_name    x_coord  y_coord  score")
        exit()

def load_topaz_csv(fname, DEBUG = True):
    """
        Parse a csv particles file into a fixed data structure:
            {
                'img_name' : [ (x, y, score), (x2, y2, score), ... ]
            }
    """

    ## initialize an empty dictionary 
    particle_data = {}
    ## extract file information from selection
    file_path = str(fname)

    ## load particle data as a pandas DataFrame object for easy manipulation
    csv_data = pd.read_csv(file_path, sep="\t", header=0)

    ## reorganize the DataFrame by the image name
    csv_data = csv_data.groupby('image_name')

    total_micrographs = 0
    total_particles = 0
    for img, particles in csv_data:
        total_micrographs += 1
        ## add a new entry to the dictionary 
        particle_data[img] = []

        ## add particles to the new entry list 
        for row_index, row in particles.iterrows():
            total_particles += 1
            x = row['x_coord']
            y = row['y_coord']
            s = row['score']
            particle_data[img].append((x, y, s))

    if DEBUG:
        print("=======================================")
        print(" Loaded dataset from: ")
        print("    %s" % fname)
        print("---------------------------------------")
        print("   %s micrographs " % total_micrographs)
        print("   %s particles " % total_particles)
        print("---------------------------------------")
        print("  Example entries:")
        if total_particles > 3:
            ## get the first key in the dictionary 
            for k in particle_data:
                break 
            ## use the first key of the dictionary to print out a few coordinates 
            i = 0
            for p in particle_data[k]:                    
                print("     (x, y, score) :: ", particle_data[k][i])
                i += 1
                if i == 2:
                    print("     ...")
                    print("     (x, y, score) :: ", particle_data[k][-1])
                    break
        print("=======================================")
    return particle_data

def write_manpick_files(data_dict, unbinning_factor):
    """
        Write out _manualpick.star files for each micrograph containing coordinates
    PARAMETERS 
        data_dict = dict(); of the form { 'img_name' : [ (x, y, score), (x2, y2, score), ... ] , ... }
        unbinning_factor = float(); how much to scale the pixel coordinates by in the output file  
    """
    
    for mic in data_dict:
        
        mic_basename = os.path.splitext(mic)[0]
        out_fname = mic_basename + '_manualpick.star'
        ## initialize the file with its header 
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

    ## write into the file with the particle data
    for mic in data_dict:
        with open('%s' % (out_fname), 'a' ) as f :
            for (X_coord, Y_coord, score) in data_dict[mic] :
                rescaled_X = int(X_coord * unbinning_factor)
                rescaled_Y = int(Y_coord * unbinning_factor)
                f.write("%s\t%s\t2\t-999.0\t%s\n" % (rescaled_X, rescaled_Y, score))
    return out_fname
#endregion

#############################
#region     RUN BLOCK
#############################

if __name__ == "__main__":
    import os
    import sys
    import pandas as pd 

    usage()
    cmd_line = sys.argv
    coord_file = None

    unbinning_factor = 1 ## no unbinning 
    ## parse any flags
    for i in range(len(cmd_line)):
        ## check for expected input file 
        if ".coord" in cmd_line[i].lower() or ".txt" in cmd_line[i].lower():
            if coord_file != None:
                print(" Warning: Two .COORD files were found when parsing commandline!")
                print("   ... using: %s" % coord_file)
            coord_file = sys.argv[i]

        if cmd_line[i] in ['--unbin']:
            try:
                unbinning_factor = float(cmd_line[i+1])
            except:
                print(" !! ERROR :: Could not parse unbinning factor given (--unbin flag), add a value")
                usage()

    ## read bash argument $1 as variable and sanity-check it
    coord_file = get_coord_file(sys.argv[1])

    ## pass the file to the topaz csv parser 
    coordinates = load_topaz_csv(coord_file) ## output structure = { 'img_name' : [ (x, y, score), (x2, y2, score), ... ] , ... }

    ## check only 1 micrograph exists?
    if len(coordinates) != 1:
        print(" !! ERROR :: Data for more than 1 micrograph was parsed from file (%s)! Skipping file!" % coord_file)
        
    ## write out manpick file 
    out_fname = write_manpick_files(coordinates, unbinning_factor)

    print(" ... written: %s" % out_fname)

#endregion