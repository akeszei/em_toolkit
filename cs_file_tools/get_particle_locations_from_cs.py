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
    print(" Read a cryoSPARC .CS file with particle locations data (e.g. file created with Export button)")
    print(" and print out individual files for each micrograph with coordinates suitable for import into ")
    print(" a RELION manualpick job or crYOLO annotations (via .star file import). Run in a separate folder")
    print(" to hold all the micrograph files in one easy-to-access location!")
    print(" Usage:")
    print("    $ get_particle_locations_from_cs.py  exported.cs  ")
    # print(" ")
    # print(" -----------------------------------------------------------------------------------------------")
    # print(" Options (default in brackets): ")
    # print("       --option (default) : description")
    print("===================================================================================================")
    sys.exit()

def check_for_help_flag(cmdline):
    for entry in cmdline:
        if entry in ['-h', '-help', '--h', '--help']:
            if DEBUG:
                print(' ... help flag called (%s).' % entry)
            return True
    return False

def parse_flags(cmdline):

    cs_file = None 

    ## check if help flag was called or we have a minimum number of arguments to evaluate
    cmdline = sys.argv
    min_args = 1
    if len(cmdline) - 1 < min_args or check_for_help_flag(cmdline):
        print(" Not enough arguments, or help flag called")
        usage()
        sys.exit()


    ## check for each relevant optional flag 
    for i in range(len(cmdline)):
        param = cmdline[i]

        ## check for expected input file 
        if ".cs" in param.lower():
            if cs_file != None:
                print(" Warning: Two .CS files were found when parsing commandline!")
                print("   ... using: %s" % cs_file)
            cs_file = sys.argv[i]

    ## check for existence of input file 
    if not os.path.splitext(cs_file)[-1] in [".cs", ".CS"]:
        print(" Input file does not have the proper extension (.cs)")
        sys.exit()

    return cs_file

def load_data_from_cs_file(fname):
    print(" Loading cs file: %s" % cs_fname)
    cs_data = np.load(cs_fname)
    print(" ... %s entries found" % len(cs_data))
    return cs_data

def parse_particles_from_cs_data(cs_data):
    """
    Combine particles coordinates with their respective micrographs 
    REF: https://tools.cryosparc.com/examples/recenter-particles.html
    """
    mic_particle_data = dict()

    ## assign the headers we need to read from for each entry in the recarray 
    header_mic_path = 'location/micrograph_path'
    header_mic_shape = 'location/micrograph_shape'
    header_mic_angpix = 'blob/psize_A'

    header_x_location_frac = 'location/center_x_frac'
    header_y_location_frac = 'location/center_y_frac'
    header_class2D_angpix = 'alignments2D/psize_A'
    header_class2D_shift = 'alignments2D/shift'

    ## load the headers from the recarray 
    headers = cs_data.dtype.names

    ## check if there is 2D alignment data present to determine shifts 
    RECENTER = False
    if header_class2D_shift in headers:
        RECENTER = True

    ## iterate over each entry in the recarray and extract the relevant data
    i = 0 
    for entry in cs_data:
        i += 1
        mic_path = str(entry[headers.index(header_mic_path)], 'UTF-8')
        mic_name = extract_mic_name(mic_path)
        micrograph_ny  = entry[headers.index(header_mic_shape)][0]
        micrograph_nx  = entry[headers.index(header_mic_shape)][1]

        ## calulate the current locations of the particles in pixels
        initial_x = entry[headers.index(header_x_location_frac)] * micrograph_nx
        initial_y = entry[headers.index(header_y_location_frac)] * micrograph_ny

        if RECENTER:
            micrograph_pixel_size = entry[headers.index(header_mic_angpix)]

            ## transform the pixel shifts from the 2D classification scale to the micrograph scale 
            class2D_pixel_size = entry[headers.index(header_class2D_angpix)]
            shift_x = entry[headers.index(header_class2D_shift)][0] * class2D_pixel_size / micrograph_pixel_size
            shift_y = entry[headers.index(header_class2D_shift)][1] * class2D_pixel_size / micrograph_pixel_size

            recentered_x = initial_x - shift_x 
            recentered_y = initial_y - shift_y 

            x = int(recentered_x)
            y = int(recentered_y)
        else:
            x = int(initial_x)
            y = int(initial_y)

        
        if mic_name not in mic_particle_data:
            mic_particle_data[mic_name] = [(x, y)]
        else:
            mic_particle_data[mic_name].append((x, y))

        if i < 5: 
            # print(" -------------------------------------------------------")
            print(" Processing particle #%s" % i)
            print("   mic = %s" % mic_name)
            print("   mic_shape = (%s, %s) : (x, y)" % (micrograph_nx, micrograph_ny))
            if RECENTER:
                print("   shifts (px) = (x, y) -> (%s, %s)" % (shift_x, shift_y))
                print("   initial pixel coordinate = (x, y) -> (%s, %s)" % (initial_x, initial_y))

            # print("   recenter with shifts = (%.2f, %.2f) -> (%.2f, %.2f)" % (location_x, location_y, location_xs, location_ys))
                print("   recentered pixel coordinate = (x, y) -> (%s, %s)" % (x, y))
            else:
                print("   pixel coordinate = (x, y) -> (%s, %s)" % (initial_x, initial_y))
            print(" -------------------------------------------------------")

        else:
            print(f"\r Processing particle #%s" % i, end="")

    print("")

    if DEBUG:
        print(" Extracted .CS particle data:")
        for mic in mic_particle_data:
            print(" Mic = %s (%s particles)" % (mic, len(mic_particle_data[mic])))
            # for particle in mic_particle_data[mic]:
            #     print("  >> ", particle)
    return mic_particle_data

def extract_mic_name(input_string):
    """ Parse the entry for 'rlnMicrographName' to extract only the micrograph name without any path names etc...
    """
    mic_name = os.path.basename(input_string)
    # if VERBOSE:
    #     print("Extract micrograph name from entry: %s -> %s" % (input_string, mic_name))
    return mic_name

def write_manpick_files(data_dict):
    """
    note
    """
    for mic in data_dict:
        mic_basename = os.path.splitext(mic)[0]
        with open('%s' % (mic_basename + ".star"), 'w' ) as f :
            f.write("\n")
            f.write("data_\n")
            f.write("\n")
            f.write("loop_\n")
            f.write("_rlnCoordinateX #1\n")
            f.write("_rlnCoordinateY #2\n")
            f.write("_rlnParticleSelectionType #3")
            f.write("\n")

            for (X_coord, Y_coord) in data_dict[mic] :
                f.write("%s\t%s\t2\n" % (X_coord, Y_coord))


#############################
###     RUN BLOCK
#############################

if __name__ == "__main__":
    import os, sys
    import numpy as np

    cs_fname = parse_flags(sys.argv)

    cs_data = load_data_from_cs_file(cs_fname)

    particle_data = parse_particles_from_cs_data(cs_data)

    write_manpick_files(particle_data)