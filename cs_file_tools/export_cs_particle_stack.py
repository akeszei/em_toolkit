#!/usr/bin/env python3

"""
    Write a convenient script to run in a cryoSPARC job directory to output a particle stack and accompanying
    relion .STAR file to easily import for processing there 
"""

## 2024-02-15: Script started, initially start with only CTF and dataset values without poses... regenerate them in RELION via 3D refinement or initial model jobs 
## To Do: - allow for multiple optics groups?
##        - 

#############################
# region :: FLAGS/GLOBALS
#############################
DEBUG = True
DRY_RUN = False

## Pair each header list from one program to another such that their indexes correspond with the equivalent expected entry 
RELION_OPTICS_HEADERS = [
    "_rlnOpticsGroup",
    "_rlnOpticsGroupName",
    "_rlnAmplitudeContrast",
    "_rlnSphericalAberration",
    "_rlnVoltage",
    "_rlnImageSize",
    "_rlnImageDimensionality",
    "_rlnImagePixelSize"
]

CS_OPTICS_HEADERS = [
    None,
    None,
    "ctf/amp_contrast",
    "ctf/cs_mm",
    "ctf/accel_kv",
    "blob/shape", ## take first value in matrix 
    None,
    "blob/psize_A"
]

RELION_PARTICLE_HEADERS = (
    ## CTF values 
    "_rlnImageName",
    "_rlnDefocusU",
    "_rlnDefocusV",
    "_rlnDefocusAngle",
    "_rlnVoltage",
    "_rlnSphericalAberration",
    "_rlnAmplitudeContrast",
    "_rlnPhaseShift",
    "_rlnOpticsGroup",
    "_rlnOriginXAngst",
    "_rlnOriginYAngst"
    # ## Pose values
    # "_rlnAngleRot",
    # "_rlnAngleTilt",
    # "_rlnAnglePsi",
    # "_rlnOriginX",
    # "_rlnOriginY",
)

# CS_PARTICLE_HEADERS = [
#     ## CTF values 
#     "blob/path",
#     "ctf/df1_A",
#     "ctf/df2_A",
#     "ctf/df_angle_rad",
#     "ctf/accel_kv",
#     "ctf/cs_mm",
#     "ctf/amp_contrast",
#     "ctf/phase_shift_rad",
#     None, # _rlnOpticsGroup
#     None, # _rlnOriginXAngst
#     None # _rlnOriginYAngst
#     # ## Pose values
#     # "_rlnAngleRot",
#     # "_rlnAngleTilt",
#     # "_rlnAnglePsi",
#     # "_rlnOriginX",
#     # "_rlnOriginY",
# ]


## prepare an enum-like structure for how we anticipate to store data for each particle
PARTICLE_DATA_STRUCTURE = (
    'cs_mrc_path', # path of the original CS .MRC stack 
    'cs_mrc_index', # the position of the particle image in the .MRC stack 
    'dZ_U',
    'dZ_V',
    'dZ_angle',
    'kV',
    'Cs',
    'amplitude_contrast',
    'phase_shift',
    'origin_shift_x',
    'origin_shift_y',
)

MRC_MODES = {   0  : 'int8', ## see: https://mrcfile.readthedocs.io/en/stable/usage_guide.html#data-types
                1  : 'int16',
                2  : 'float32', 
                4  : 'complex64', 
                6  : 'uint16', 
                12 : 'float16' }

#endregion


#############################
# region :: DEFINITION BLOCK
#############################

def usage():
    print("===================================================================================================")
    print(" Use CS particles file to extract a particle stack with an accompanying .STAR file for import")
    print(" into RELION:")
    print(" Usage:")
    print("    $ export_cs_particles_stack.py  J##_###_particles.cs  /path/to/root/CS-directory/")
    print(" ")
    print(" -----------------------------------------------------------------------------------------------")
    print(" Options (default in brackets): ")
    print("      --o (mrcs_stacks) : Set target directory name to save particle stacks into")
    print("                --j (4) : Allow multiprocessing using indicated number of cores")
    print("              --dry-run : Read the .cs file and give a report on what the script will do")
    print("===================================================================================================")
    sys.exit()

def sanity_check_inputs(cs_dataset, cs_project_dir):
    ## check if the project directory exists
    if not os.path.isdir(cs_project_dir):
        print(" ERROR :: Could not find input CS-project directory: %s" % cs_project_dir)
        usage()

    ## make sure it has a leading slash for consistentcy 
    if not cs_project_dir[-1] in ['/', '\\' ]:
        cs_project_dir = cs_project_dir + '/'

    #### check if we can locate the .MRC file for the first particle 
    ## first open the dataset & get the path 
    cs_headers = get_cs_headers(cs_dataset) 
    for i in range(1):
        particle_cs_data = cs_dataset[i]
        try:
            particle_path = particle_cs_data[cs_headers['blob/path']].decode('utf-8').strip()
            ## CS likes to add a chevron to indicate the start of the project in some files, remove it incase it is present!
            if particle_path[0] == '>':
                particle_path = particle_path[1:]
            mrc_path = cs_project_dir + particle_path

        except:
            print(" ERROR :: Input .CS file lacks a 'blob/path' field pointing to the extracted particle stack! Try using an exported stack of particles via the output tab in cryoSPARC")
            sys.exit()
        
    ## use the path to check file exists 
    if not os.path.isfile(mrc_path):
        print(" ERROR :: Unable to locate .MRC file described by input CS file: %s" % (mrc_path))
        print("   Double-check you have provided the correct path from the working dir the CS project")
        usage()
    
    return cs_project_dir

def get_cs_headers(dataset):
    """
        Unpack the rec array headers keeping into account the header strings and their corresponding indexes 
    """
    ## Unpack the header data into a dictionary we can refer to later ( 'header_name' : index/column )  
    headers = dataset.dtype.names ## 'headers' for each index position can be retrieved from the main array
    header_dict = {} 
    for i in range(len(headers)):
        header_dict[headers[i]] = i
    return header_dict

def parse_cs_dataset(cs_particles):
    ## 1. Unpack the header data into a dictionary we can refer to later   
    cs_headers = get_cs_headers(cs_particles) ## dict ( 'header_name' : index/column, ... )
    # print(" CS recarray headers = ", cs_headers)

    ## 2. Iterate over each particle in the cs dataset and cast it into an easy format to manipulate later  
    ## We will use a dictionary structure to match all particles from a common micrograph with their metadata, we can then use that structure to write out many small .MRCS files with the correct metadata in the .STAR file 
    particle_data = {}  
    particle_count = 0
    for i in range(len(cs_particles)):
        ## pull out the specific particle info
        particle_cs_data = cs_particles[i]
        particle_count += 1
        
        ## find the corresponding .MRC file for that particle 
        mrc_path = particle_cs_data[cs_headers['blob/path']].decode('utf-8').strip()
        ## CS likes to add a chevron to indicate the start of the project in some files, remove it incase it is present!
        if mrc_path[0] == '>':
            mrc_path = mrc_path[1:]

        ## since multiple extract jobs can exist, use the base name of the .mrc file as the dictionary, removing the UID
        # mrc_fname = os.path.splitext(os.path.basename(mrc_path))[0].split('_', 1)[1] + '.mrcs'
        mrc_fname = os.path.basename(mrc_path).split('_', 1)[1]
        mrc_fname = os.path.splitext(mrc_fname)[0] + '.mrcs'

        ## Use the first particle to set the optics table data 
        if i == 0:
            print(" ... preparing optics table info from first particle entry")
            optics_data = populate_relion_optics_table(particle_cs_data, cs_headers)
            particle_data.setdefault(mrc_fname,[]).append(get_particle_data(particle_cs_data, cs_headers, DEBUG = DEBUG))
        else:
            ## For every particle, retrieve the necessary data and cast it into a familiar format for downstream use 
            particle_data.setdefault(mrc_fname,[]).append(get_particle_data(particle_cs_data, cs_headers))
    
    print(" ... read %s micrographs from file (%s particles)" % (len(particle_data), particle_count))
    
    ## make the particle lists in the dictionary immutable
    for m in particle_data:
        particle_data[m] = tuple(particle_data[m])
    
    if DEBUG:
        print("==================================")
        print(" Example particle data extracted:")
        print("----------------------------------")
        random_micrograph = choice(list(particle_data.keys())) 
        print("  >> %s (%s particles)" % (random_micrograph, len(particle_data[random_micrograph])))
        random_particles = []
        if len(particle_data[random_micrograph]) < 3:
            for _ in range(len(particle_data[random_micrograph]) - 1):
                random_particles.append(_)
                print("    ... particle #%s data: " % _, particle_data[random_micrograph][random_particles[-1]])
        else:
            for _ in range(3):
                random_particle_number = randint(0, len(particle_data[random_micrograph]) - 1)
                while random_particle_number in random_particles:
                    random_particle_number = randint(0, len(particle_data[random_micrograph]) - 1)
                random_particles.append(random_particle_number)
                print("    ... particle #%s data: " % random_particle_number, particle_data[random_micrograph][random_particles[-1]])
        print("    ...")
        print("==================================")

    return optics_data, particle_data

def get_particle_data(particle_cs, header_list, DEBUG = False):
    ## prepare all expected values and their defaults 
    cs_mrc_path = None # path of the original CS .MRC stack 
    cs_mrc_index = None # the position of the particle image in the .MRC stack 
    dZ_U = None 
    dZ_V = None
    dZ_angle = None
    kV = None
    Cs = None
    amplitude_contrast = None
    phase_shift = None
    originX_trans = None
    originY_trans = None

    ## assign each variable from the cs input data point 
    cs_mrc_path = particle_cs[header_list['blob/path']].decode('utf-8').strip()
    cs_mrc_index = particle_cs[header_list['blob/idx']] 
    dZ_U = particle_cs[header_list['ctf/df1_A']] 
    dZ_V = particle_cs[header_list['ctf/df2_A']]
    dZ_angle = particle_cs[header_list['ctf/df_angle_rad']]
    kV = particle_cs[header_list['ctf/accel_kv']]
    Cs = particle_cs[header_list['ctf/cs_mm']]
    amplitude_contrast = particle_cs[header_list['ctf/amp_contrast']]
    phase_shift = particle_cs[header_list['ctf/phase_shift_rad']]
    ## cs origin shifts are given in fractional pixels, need to convert them to angstroms by multiplying by angpix
    ## however, in case there is no 3D alignment data (i.e. cs file is from an export job, we need to provide a shift of 0)
    try:
        originX_trans = particle_cs[header_list['alignments3D/shift']][0] * particle_cs[header_list['alignments3D/psize_A']]
        originY_trans = particle_cs[header_list['alignments3D/shift']][1] * particle_cs[header_list['alignments3D/psize_A']]
    except:
        originX_trans = 0
        originY_trans = 0

    ## package the data into a tuple using the global enum
    particle_data = list(None for _ in range(len(PARTICLE_DATA_STRUCTURE))) # begin by making a mutable list
    # populate the list by index 
    particle_data[PARTICLE_DATA_STRUCTURE.index('cs_mrc_path')] = cs_mrc_path
    particle_data[PARTICLE_DATA_STRUCTURE.index('cs_mrc_index')] = cs_mrc_index
    particle_data[PARTICLE_DATA_STRUCTURE.index('dZ_U')] = dZ_U
    particle_data[PARTICLE_DATA_STRUCTURE.index('dZ_V')] = dZ_V
    particle_data[PARTICLE_DATA_STRUCTURE.index('dZ_angle')] = dZ_angle
    particle_data[PARTICLE_DATA_STRUCTURE.index('kV')] = kV
    particle_data[PARTICLE_DATA_STRUCTURE.index('Cs')] = Cs
    particle_data[PARTICLE_DATA_STRUCTURE.index('amplitude_contrast')] = amplitude_contrast
    particle_data[PARTICLE_DATA_STRUCTURE.index('phase_shift')] = phase_shift
    particle_data[PARTICLE_DATA_STRUCTURE.index('origin_shift_x')] = originX_trans
    particle_data[PARTICLE_DATA_STRUCTURE.index('origin_shift_y')] = originY_trans
    # re-cast data as a fixed tuple 
    particle_data = tuple(particle_data)
    return particle_data

def populate_relion_optics_table(particle_cs, header_list):
    """
        Read a single particle entry and extract the necessary info we can to create an opitcs table for RELION,
        handling all exceptions when converting the input data.  
    """
    OPTICS_DATA = {}
    ## use the data from the particle to retrieve what we can to generate the optics table 
    for i in range(len(RELION_OPTICS_HEADERS)):
        ## handle optics headers that are typically missing from cs particle dataset 
        if CS_OPTICS_HEADERS[i] == None:
            if RELION_OPTICS_HEADERS[i] == "_rlnOpticsGroup": 
                OPTICS_DATA[RELION_OPTICS_HEADERS[i]] = 1
                # if DEBUG: print(" Set default value: %s --> %s" % (RELION_OPTICS_HEADERS[i], OPTICS_DATA['_rlnOpticsGroup']))
            elif RELION_OPTICS_HEADERS[i] == "_rlnOpticsGroupName": 
                OPTICS_DATA[RELION_OPTICS_HEADERS[i]] = "optics_1"
                # if DEBUG: print(" Set default value: %s --> %s" % (RELION_OPTICS_HEADERS[i], OPTICS_DATA["_rlnOpticsGroupName"]))
            elif RELION_OPTICS_HEADERS[i] == "_rlnImageDimensionality": 
                OPTICS_DATA[RELION_OPTICS_HEADERS[i]] = 2
                # if DEBUG: print(" Set default value: %s --> %s" % (RELION_OPTICS_HEADERS[i], OPTICS_DATA["_rlnImageDimensionality"]))
            else:
                print(" WARNING : No default set for optics header '%s' " % (RELION_OPTICS_HEADERS[i]))
        else:
            rec_column = header_list[CS_OPTICS_HEADERS[i]]
            ## handle matrixes 
            if RELION_OPTICS_HEADERS[i] == "_rlnImageSize":
                OPTICS_DATA[RELION_OPTICS_HEADERS[i]] = particle_cs[rec_column][0]
            else:
                OPTICS_DATA[RELION_OPTICS_HEADERS[i]] = particle_cs[rec_column]
            
    if DEBUG: 
        print("==================================")
        print(" Optics table extracted:")
        print("----------------------------------")
        for k in OPTICS_DATA:
            print("  %s :: %s" % (k, OPTICS_DATA[k])) 
        print("==================================")

    return OPTICS_DATA

def write_optics_table(optics_data, output_star_fname):
    ## use overwrite option to generate a clean file initially 
    with open('%s' % (output_star_fname), 'w' ) as f :
        f.write("\n")
        f.write("# version 30001")
        f.write("\n\n")
        ## prepare optics table headers 
        f.write("data_optics\n")
        f.write("\n")
        f.write("loop_\n")
        for i in range(len(RELION_OPTICS_HEADERS)):
            f.write("%s #%s\n" % (RELION_OPTICS_HEADERS[i], i+1))
        ## prepare the optics data string 
        s = " "
        for header in RELION_OPTICS_HEADERS:
            s = s + "    %s" % optics_data[header]
        f.write("%s\n" % s)

    return 

def write_particle_table_headers(output_star_fname):
    ## use append option to add to end of file 
    with open('%s' % (output_star_fname), 'a' ) as f :
        f.write("\n")
        f.write("\n")
        f.write("# version 30001")
        f.write("\n\n")
        f.write("data_particles\n")
        f.write("\n")
        f.write("loop_\n")
        for j in range(len(RELION_PARTICLE_HEADERS)):
            f.write("%s #%s\n" % (RELION_PARTICLE_HEADERS[j], j+1))

    return 

def write_particle_to_star(f, particle_data, particle_star_path):
    s = ""
    ## use the globally defined particle data structure to correctly place each element in sequence with the relion headers 
    for i in range(len(RELION_PARTICLE_HEADERS)):
        if RELION_PARTICLE_HEADERS[i] == "_rlnImageName": s = s + particle_star_path + "\t"
        if RELION_PARTICLE_HEADERS[i] == "_rlnDefocusU": s = s + str(particle_data[PARTICLE_DATA_STRUCTURE.index('dZ_U')]) + "\t"
        if RELION_PARTICLE_HEADERS[i] == "_rlnDefocusV": s = s + str(particle_data[PARTICLE_DATA_STRUCTURE.index('dZ_V')]) + "\t"
        if RELION_PARTICLE_HEADERS[i] == "_rlnDefocusAngle": s = s + str(particle_data[PARTICLE_DATA_STRUCTURE.index('dZ_angle')]) + "\t"
        if RELION_PARTICLE_HEADERS[i] == "_rlnVoltage": s = s + str(particle_data[PARTICLE_DATA_STRUCTURE.index('kV')]) + "\t"
        if RELION_PARTICLE_HEADERS[i] == "_rlnSphericalAberration": s = s + str(particle_data[PARTICLE_DATA_STRUCTURE.index('Cs')]) + "\t"
        if RELION_PARTICLE_HEADERS[i] == "_rlnAmplitudeContrast": s = s + str(particle_data[PARTICLE_DATA_STRUCTURE.index('amplitude_contrast')]) + "\t"
        if RELION_PARTICLE_HEADERS[i] == "_rlnPhaseShift": s = s + str(particle_data[PARTICLE_DATA_STRUCTURE.index('phase_shift')]) + "\t"
        if RELION_PARTICLE_HEADERS[i] == "_rlnOpticsGroup": s = s + str(1) + "\t"
        if RELION_PARTICLE_HEADERS[i] == "_rlnOriginXAngst": s = s + str(particle_data[PARTICLE_DATA_STRUCTURE.index('origin_shift_x')]) + "\t" + "\t"
        if RELION_PARTICLE_HEADERS[i] == "_rlnOriginYAngst": s = s + str(particle_data[PARTICLE_DATA_STRUCTURE.index('origin_shift_y')]) + "\t" + "\t"

    ## add the particle metadata line to the star file 
    f.write("%s\n" % s)
    return 

def make_empty_mrcs(stack_size, mrc_dimensions, mrc_mode, fname, apix, DEBUG = False):
    """ Prepare an empty .MRCS in memory of the correct dimensionality
    PARAMETERS 
        stack_size = int(), how many images will be stacked into this .MRCS 
        mrc_dimensions = list( int(), int() ), size of individual .MRC files to be stacked in the form: [ x, y ]
        mrc_mode = int(), mode of the mrc (necessary to set proper data type)
        fname = str(), full absolution or relative path of the output .MRCS file 
        apix = float(), the voxel size to set the mrcs file to 
    """
    import mrcfile
    import numpy as np
    if mrc_mode in [0, 1, 2, 4, 6, 12]:
        ## we have a compatible mode detected
        if DEBUG:
            print(" ... using MRC mode #%s -> dtype = %s " % (mrc_mode, MRC_MODES[int(mrc_mode)])) 
    else:
        ## we do not have a compatible mode! 
        print("!! ERROR :: Unknown mode read from input file, %s -> mode %s" % (fname, mrc_mode))
        exit()

    with mrcfile.new(fname, overwrite=True) as mrc:
        mrc.set_data(np.zeros(( stack_size, ## stack size
                                mrc_dimensions[1], ## pixel height, 'Y'
                                mrc_dimensions[0]  ## pixel length, 'X'
                            ), dtype=np.dtype(MRC_MODES[int(mrc_mode)])))
                            # ), dtype=np.float32))

        ## set pixel size data 
        mrc.voxel_size = apix
        mrc.update_header_from_data()
        mrc.update_header_stats()
        ## set the mrcfile with the correct header values to indicate it is an image stack
        mrc.set_image_stack()
        if DEBUG:
            print(" ... writing new .MRCS stack (%s, mode %s) with dimensions (x, y, z) = (%s, %s, %s)" % (fname, mrc_mode, mrc.data.shape[2], mrc.data.shape[1], mrc.data.shape[0]))
    return

def write_particle_to_mrcs(input_mrcs, output_mrcs, input_mrcs_path, input_mrcs_index, output_mrcs_path, output_mrcs_index, DEBUG = False):
    if DEBUG:
        print(" Get image from: %s @ %s" % (input_mrcs_index, input_mrcs_path))
        print(" Save image to mrcs: %s @ %s" % (output_mrcs_index, output_mrcs_path))
        print(" ... grabbing frame %s" % (input_mrcs_index + 1))

    ## sanity check there is a frame expected
    if input_mrcs_index in range(0, input_mrcs.data.shape[0]):
        particle_img = input_mrcs.data[input_mrcs_index]
        if DEBUG:
            print(" >> Data read from file = (min, max) -> (%s, %s), dtype = %s" % (np.min(particle_img), np.max(particle_img), particle_img.dtype))

        ## check if the output mrcs is a single frame, in which case we need to deal with appending the frame as a special case 
        if len(output_mrcs.data.shape) == 2:
            output_mrcs.data[0:] = particle_img
        else:
            output_mrcs.data[output_mrcs_index] = particle_img
    else:
        print(" Input frame value requested (%s) not in expected range of .MRCS input file: (%s; [%s, %s])" % (input_mrcs_index, input_mrcs_path, 1, input_mrcs.data.shape[0]))

    return 

def write_star_file(optics_data, particle_data, output_dir, output_star_fname, mrcs_output_dir):
    if DRY_RUN:
        return 
    
    write_optics_table(optics_data, output_star_fname)

    write_particle_table_headers(output_star_fname)

    with open('%s' % (output_dir + output_star_fname), 'a' ) as f :
        for mic in particle_data:
            # output_mrcs_fname = os.path.splitext(os.path.basename(mic))[0].split('_', 1)[1] + '.mrcs'
            output_mrcs_fname = mic
            output_mrcs_path = output_dir + mrcs_output_dir + output_mrcs_fname

            for i in range(len(particle_data[mic])):
                particle_info = particle_data[mic][i]
                particle_star_path = "%s@%s" % (i, output_mrcs_path)

                write_particle_to_star(f, particle_info, particle_star_path)
    return 

def write_mrcs_files(optics_data, particle_data, cs_project_dir, output_dir, mrcs_output_dir):
    import os
    import mrcfile
    
    mics_w_one_particle = []
    mics_w_less_than_five = []
    mics_w_less_than_ten = []

    for output_mrcs_fname in particle_data:

        if DRY_RUN:
            output_mrcs_path = output_dir + mrcs_output_dir + output_mrcs_fname
            box_size = optics_data['_rlnImageSize']
            num_particles = len(particle_data[output_mrcs_fname])
            # print(" ... empty .MRCS file will be created :: (%s, %s, %s) @ %s" % (box_size, box_size, num_particles, output_mrcs_path))
            # print(" WIP write out first three particles, their metadata, their source mrc and output mrc!!")
            
            if num_particles < 10:
                mics_w_less_than_ten.append(output_mrcs_fname)
            if num_particles < 5:
                mics_w_less_than_five.append(output_mrcs_fname)
            if num_particles == 1:
                mics_w_one_particle.append(output_mrcs_fname)
            continue  

        # ## crude solution, but hardcode the name change, later make this an input (i.e. fix the input dictionary during parsing?)
        # output_mrcs_fname = os.path.splitext(output_mrcs_fname)[0] + '.mrcs'

        ## prepare an empty .mrcs file to hold all the frames we want to eventually write
        output_mrcs_path = output_dir + mrcs_output_dir + output_mrcs_fname
        box_size = optics_data['_rlnImageSize']
        try:
            make_empty_mrcs(len(particle_data[output_mrcs_fname]), [box_size, box_size], 2, output_mrcs_path, optics_data['_rlnImagePixelSize'])
            print(" .. processing %s (%s) particles" % (output_mrcs_fname, len(particle_data[output_mrcs_fname])))
        except:
            s = " ERROR! Could not make an empty mrcs for %s (%s) particles" % (output_mrcs_fname, len(particle_data[output_mrcs_fname]))
            log_error(s)
        
        ## open the empty .mrcs file we intend to populate 
        output_mrcs = mrcfile.open(output_mrcs_path, mode='r+')

        input_mrcs = None 

        for i in range(len(particle_data[output_mrcs_fname])):
            ## get the particle data 
            particle_info = particle_data[output_mrcs_fname][i]
            ## retrieve the path to the current particle's mrc file in the CS project and its index in the .mrc stack 
            ## some cs files include a chevron to indicate the root of the CS project, we need to remove it
            cs_project_path_to_mrc = particle_info[PARTICLE_DATA_STRUCTURE.index('cs_mrc_path')]
            if cs_project_path_to_mrc[0] == '>':
                cs_project_path_to_mrc = cs_project_path_to_mrc[1:]
            
            cs_mrc_path = cs_project_dir + cs_project_path_to_mrc
            
            cs_mrc_particle_index = particle_info[PARTICLE_DATA_STRUCTURE.index('cs_mrc_index')]

            ## open the input_mrc file if none is yet open 
            if input_mrcs == None:
                input_mrcs = mrcfile.open(cs_mrc_path, mode='r')

            ## otherwise, check if the open file is different than one we want 
            elif input_mrcs._iostream.name != cs_mrc_path:
                ## since the open mrc file is not the one we want, first we close it
                input_mrcs.close()
                ## then we open the new one we want  
                input_mrcs = mrcfile.open(cs_mrc_path, mode='r')

            ## otherwise, we already have the appropriate open input mrc file 
            else:
                # print(" Input MRC file already open! ")
                pass 

            try:
                write_particle_to_mrcs(input_mrcs, output_mrcs, cs_mrc_path, cs_mrc_particle_index, output_mrcs_path, i)
            except:
                s = " ERROR! Could not properly extract particles:\n %s (%s particles) --> %s" % (cs_mrc_path, len(particle_data[output_mrcs_fname]), output_mrcs_path)
                log_error(s)
                print(" ERROR :: Skipping particles from micrograph: %s" % output_mrcs_fname)
                input_mrcs.close()

        if input_mrcs != None: 
            input_mrcs.close()

        
        ## update & close the now-filled .mrcs file we created 
        output_mrcs.voxel_size = optics_data['_rlnImagePixelSize']
        output_mrcs.update_header_from_data()
        output_mrcs.update_header_stats()
        output_mrcs.close()

    if DRY_RUN:
        print(" # micrographs with:")
        print("      1 particle = %s" % len(mics_w_one_particle))
        print("   < 5 particles = %s" % len(mics_w_less_than_five))
        print("  < 10 particles = %s" % len(mics_w_less_than_ten))

    return 

def log_error(err, out_fname = 'err.log', reset = False):
    if err == '':
        return 

    if reset:
        ## use overwrite option to generate a clean file initially 
        with open('%s' % (out_fname), 'w' ) as f :
            f.write("%s \n" % err)
    else:
        ## use append option to add to error log 
        with open('%s' % (out_fname), 'a' ) as f :
            f.write("%s \n" % err)

    return

def prep_working_dir(mrcs_output_dir_name):
    ## prepare the root directory for all .mrcs files and clean it up if anything already exists in it 
    if os.path.isdir(mrcs_output_dir_name):
        # print(" ERROR :: An existing folder already is present at the target output location for particle .MRCS stacks: %s" % mrcs_output_dir)
        # print("  ... doublecheck & delete this folder before proceeding")
        # exit()

        ## check the directory for .mrcs files and delete them 
        dir_contents = os.listdir(mrcs_output_dir_name)
        for f in dir_contents:
            f_path = mrcs_output_dir_name + f
            if os.path.isfile(f_path):
                if os.path.splitext(f_path)[1] in ['.mrcs', '.MRCS']:
                    os.remove(f_path)
    else:
        os.mkdir(mrcs_output_dir_name)

    return

def split_dict(d, n):
    """ prepare a method to break the dataset into smaller chunks based on number of threads 
    """
    keys = list(d.keys())
    for i in range(0, len(keys), n):
        yield {k: d[k] for k in keys[i: i + n]}

#endregion

#############################
# region RUN BLOCK
#############################

if __name__ == "__main__":
    import sys, os
    import numpy as np
    from random import randint, choice
    try:
        import mrcfile
    except:
        print(" Could not import mrcfile module. Install via:")
        print(" > pip install mrcfile")
        sys.exit()
    from multiprocessing import Pool 
    import time

    start_time = time.time()

    cmd_line = sys.argv
    PARALLEL_PROCESSING = False

    ## read all entries and check if the help flag is called at any point
    for cmd in cmd_line:
        if cmd == '-h' or cmd == '--help' or cmd == '--h':
            usage()
        if len(cmd_line) < 3:
            usage()

    ## parse any flags
    ## set defaults 
    mrcs_output_dir_name = 'mrcs_stacks/'
    for i in range(len(cmd_line)):
        if cmd_line[i] == '--j':
            threads = 4
            PARALLEL_PROCESSING = True
            ## try parsing the number of threads 
            try:
                threads = int(cmd_line[i+1])
                print(" Using %s threads" % threads)
            except:
                print(" Could not parse # of threads, or none given, using default: %s" % threads)
        if cmd_line[i] in ['--dry-run', '--dry_run']:
            DRY_RUN = True
            print(" Running in dry-run mode... no files will be written")
        if cmd_line[i] in ['--o']:
            ## try parsing the desired output folder name  
            try:
                mrcs_output_dir_name = str(cmd_line[i+1])
                ## add leading slash if not provided
                if mrcs_output_dir_name[-1] not in ['/', '\\']:
                    mrcs_output_dir_name = mrcs_output_dir_name + '/'
                print(" Setting output particle stack into folder: %s" % mrcs_output_dir_name)
            except:
                print(" Could not parse desired output folder (--o flag), check command line" )
                usage()

    ## parse cmd line for the .CS file 
    cs_file = None
    for i in range(len(cmd_line)):
        if cs_file == None:
            if os.path.splitext(cmd_line[i])[1] in ['.cs', '.CS']:
                cs_file = cmd_line[i]
        elif os.path.splitext(cmd_line[i])[1] in ['.cs', '.CS']:
            print(" WARNING :: More than one .cs file was detected as input, only the first entry (%s) will be parsed " % cs_file)
            
    if cs_file == None:
        print(" ERROR :: No .cs file was detected as input!")
        usage()

    ## parse the project directory 
    cs_project_dir = None
    for i in range(len(cmd_line)):
        if cs_project_dir == None:
            ## use the final character '/' as indicating the directory path 
            if cmd_line[i][-1] in ['/', '\\']:
                cs_project_dir = cmd_line[i]
        elif cmd_line[i][-1] in ['/', '\\']: 
            print(" WARNING :: More than one entry detected as a path (ends with forward slash)! Using first entry as the CS project directory (%s)" % cs_project_dir)

    if cs_project_dir == None:
        print(" ERROR :: No CS project directory was detected, e.g.: /path/to/CS-project/, be sure to add a forward slash at the end (e.g. ../)")
        usage()


    output_star_fname = 'particles.star'
    output_dir = ''

    print("==================================================================")
    print("  Load cs file: %s" % cs_file)
    print("------------------------------------------------------------------")

    ## cs data is stored as a numpy structured array (recarrays), it can be opened with numpy 
    cs_dataset = np.load(cs_file)

    cs_project_dir = sanity_check_inputs(cs_dataset, cs_project_dir)

    ## clear error logfile 
    log_error("", reset = True)

    ## run through the CS dataset to prepare the necessary data for creating .MRCS and .STAR files
    optics_data, particle_data = parse_cs_dataset(cs_dataset)

    if not DRY_RUN:
        prep_working_dir(output_dir + mrcs_output_dir_name)

    write_star_file(optics_data, particle_data, output_dir, output_star_fname, mrcs_output_dir_name)

    if PARALLEL_PROCESSING:
        ## multithreading set up
        tasks = []
        for subset in split_dict(particle_data, int(len(particle_data) / threads)):
            tasks.append(subset)

        ## generate the working input functions
        try:
            dataset = []
            for task in tasks:
                dataset.append((optics_data, task, cs_project_dir, output_dir, mrcs_output_dir_name))
            ## prepare pool of workers
            pool = Pool(threads)
            ## assign workload to pool
            results = pool.starmap(write_mrcs_files, dataset)
            ## close the pool from recieving any other tasks
            pool.close()
            ## merge with the main thread, stopping any further processing until workers are complete
            pool.join()

        except KeyboardInterrupt:
            print("Multiprocessing run killed")
            pool.terminate()


    else:
        write_mrcs_files(optics_data, particle_data, cs_project_dir, output_dir, mrcs_output_dir_name)

    if DRY_RUN:
        print(" --------------------------------------------------------------------------------------------------")
        print(" ... DRY-RUN COMPLETE")
    else:
        print(" --------------------------------------------------------------------------------------------------")
        print(" ... COMPLETE")
        print("   Written: %s" % output_dir + output_star_fname)
        print("   MRCS files written in: %s" % output_dir + mrcs_output_dir_name)
        print(" --------------------------------------------------------------------------------------------------")
        print(" NOTE: Will likely need to normalize the particles for processing in RELION (this is done on extraction job)")
        print(" To do this, save a back up of the particle stack and run normalization, e.g.:")
        print("     $ mv mrcs_stacks mrcs_backup; mkdir mrcs_stacks")
        print("     $ for m in mrcs_backup/*.mrcs; do \\") 
        print("     > relion_preprocess --operate_on $m --operate_out mrcs_stacks/${m#*/} --norm --float16 --bg_radius %s; done # e.g. <0.37 * box>" % (int(0.37 * optics_data['_rlnImageSize'])))
        print(" --------------------------------------------------------------------------------------------------")
        print(" Once normalized, import the particle stack in RELION and use the corresponding cryoSPARC volume")
        print(" to generate initial Euler angles for each particle to run subsequent jobs")
        print("===================================================================================================")

    end_time = time.time()
    total_time_taken = end_time - start_time
    print("... runtime = %.2f sec" % total_time_taken)
    ## non-parallelized; 10k particles = 48.98, 50.82, 58.76 sec
    ## parallized, pool mode, 4 threads; 10k particles = 24.92, 26.18, 27.68 sec


#endregion