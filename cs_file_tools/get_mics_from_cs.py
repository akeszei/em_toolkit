#!/usr/bin/env python3

## To do:
##   - Internally keep track of micrographs selected already to prevent double picking! 
##   - Maybe add an option to check against other directories? Useul for grabbing random micrographs outside of a training set 

#############################
###     GLOBAL FLAGS
#############################
DEBUG = False

#############################
###     DEFINITION BLOCK
#############################

def usage():
    print("===================================================================================================")
    print(" Read a cryoSPARC .CS file with micrograph data and extract them into a text file.")
    print(" Can use options to grab a random subset across the defocus range for manual picking.")
    print(" Usage:")
    print("    $ get_mics_from_cs.py  input.cs  ")
    print("    $ get_mics_from_cs.py  passthrough_exposures_accepted.cs  --subset 20")
    print(" ")
    print(" -----------------------------------------------------------------------------------------------")
    print(" Options (default in brackets): ")
    print("       --subset (15) : Get a list of micrographs across the dZ range of the given size")
    print("===================================================================================================")
    sys.exit()
    return

def check_for_help_flag(cmdline):
    for entry in cmdline:
        if entry in ['-h', '-help', '--h', '--help']:
            if DEBUG:
                print(' ... help flag called (%s).' % entry)
            return True
    return False

def parse_flags(cmdline):

    cs_file = None 
    subset_size = None 

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

        if param == '--subset':
            try:
                subset_size = int(cmdline[i + 1])
                if DEBUG: 
                    print(" .. setting subset size to: %s" % subset_size)
            except:
                ## use defaults
                subset_size = 15
                print(" .. no explicit subset size given, using defaults: %s " % subset_size)

    ## check for existence of input file 
    if not os.path.splitext(cs_file)[-1] in [".cs", ".CS"]:
        print(" Input file does not have the proper extension (.cs)")
        sys.exit()

    return cs_file, subset_size 

def load_data_from_cs_file(fname):
    print(" Loading cs file: %s" % cs_fname)
    cs_data = np.load(cs_fname)
    print(" ... %s entries found" % len(cs_data))
    return cs_data

def get_mics_from_cs_data(cs_data):
    """
    Unpack the data in a cs numpy recarray into an easier form to iterate over internally:
       [ ('img_name', dZ_avg), ('img_name', dZ_avg), ... ]

    """
    mics = []

    ## assign the headers we need to read from for each entry in the recarray 
    mic_path_header = 'micrograph_blob/path'
    mic_path_header_alt = 'micrograph_blob_non_dw/path'
    dZ_1_header = 'ctf/df1_A'
    dZ_2_header = 'ctf/df2_A'
    ## load the headers from the recarray 
    headers = cs_data.dtype.names
    NO_CTF = False
    if dZ_1_header not in headers:
        NO_CTF = True

    ## iterate over each entry in the recarray and extract the relevant data 
    for entry in cs_data:
        ## there are inconsistencies in the headers used to indicate paths, so use fallback headers to try and shore up gaps 
        try: 
            mic_path = str(entry[headers.index(mic_path_header)], 'UTF-8')
        except:
            mic_path = str(entry[headers.index(mic_path_header_alt)], 'UTF-8')

        if not NO_CTF:
            dZ_1 = entry[headers.index(dZ_1_header)]
            dZ_2 = entry[headers.index(dZ_2_header)]
            dZ_avg = ((dZ_1 + dZ_2) / 2)/10000
        else:
            dZ_avg = -1

        mics.append((mic_path, dZ_avg))

    if DEBUG:
        print(" Extracted .CS data:")
        for i in range(2):
            print("  >> %s [dZ = %s]" % (mics[i]))
        print('     ...')

    return mics

def analyse_dZ_range(mic_data):
    ## find the full range of dZ values 
    dZ_full_list = []
    for mic, dZ in mic_data:
        dZ_full_list.append(dZ)
    dZ_min = min(dZ_full_list)
    dZ_max = max(dZ_full_list)

    print(" The dZ range of the dataset is = %s -> %s" % (dZ_min, dZ_max))

    ## split the range over 5 ranges
    step_size = (dZ_max - dZ_min) / 5
    range_thresholds = []
    for i in range(5):
        range_thresholds.append(dZ_min + step_size * (i + 1))

    print(" Split dataset across 5 dZ upper thresholds: ", range_thresholds)
    return range_thresholds

def write_all_mics_to_file(mic_data, out_fname = "mics.txt"):
    with open(out_fname, 'w') as f:
        for item in mic_data:
            f.write("%s\n" % item[0]) 
    return 

def get_subset_by_dZ(mic_data, dZ_thresholds, subset_size):
    subset = []
    for i in range(subset_size):
        chosen_micrograph = None 

        ## for each step in the subset, find the desired defocus threshold we are seeking to fit within
        threshold_upper = dZ_thresholds[i%len(dZ_thresholds)]
        if i%len(dZ_thresholds) == 0:
            threshold_lower = 0
        else:
            threshold_lower = dZ_thresholds[i%len(dZ_thresholds) - 1]

        if DEBUG: print(" Find micrograph within dZ range %s -> %s" % (threshold_lower, threshold_upper))

        ## start at a random initial point in the dataset and iterate forward until we find a match 
        n = random.randint(0, len(mic_data))
        full_traversal = 0 ## keep track how many times we run through the full dataset, we may have to skip some bins if there are no suitable micrographs!
        while chosen_micrograph == None:
            # print(" Start search for micrograph at #%s" % n)
            current_mic_data = mic_data[n]
            # print(" ... checking micrograph #%s (dZ = %s)" % (n, current_mic_data[1]))
            # print(" %s vs. threshold %s" %  (current_mic_data[1], threshold_upper))
            if float(current_mic_data[1]) < threshold_upper:
                if float(current_mic_data[1]) > threshold_lower:
                    if DEBUG: print(" ... found match (%s, mic #%s)" % (current_mic_data[1], n))
                    ## check if the match already exists in the subset
                    if current_mic_data in subset:
                        print(" !! Match already exists in the subset, find another... ")
                        n = random.randint(0, len(mic_data) - 1)
                    else:
                        chosen_micrograph = current_mic_data

            ## we have not found a match, so iterate forward 
            if n >= len(mic_data) - 1:
                if DEBUG: print(" ... hit end of dataset (n = %s), return to beginning" % n)

                n = 0
                full_traversal += 1
            else:
                n = n+1

            ## avoid infinite loop in case there are no suitable matches in the dataset for a given bin 
            if full_traversal >= 2:
                ## no match was found for this bin, try the next
                threshold_upper = dZ_thresholds[(i+1)%len(dZ_thresholds)]
                if i%len(dZ_thresholds) == 0:
                    threshold_lower = 0
                else:
                    threshold_lower = dZ_thresholds[(i+1)%len(dZ_thresholds) - 1]
                if DEBUG: print(" No match for this bin. Move to the next dZ range: %s -> %s" % (threshold_lower, threshold_upper))
                full_traversal = 0 


        ## Add the discovered micrograph to the subset list 
        if chosen_micrograph != None:
            subset.append(chosen_micrograph)
        else:
            continue
        
    print(" >> Randomly selected %s micrographs across the dZ range" % (len(subset)))
    for i in range(len(subset)):
        if i > 8: 
            break 
        print("   %s [dZ %s]" % (subset[i][0], subset[i][1]))
    print("   ...")

    return subset


######################
## useful functions to read cs datasets and find the correct headers of interest...
def read_cs_data(dataset, headers_of_interest = []):
    """ 
    PARAMETERS
        dataset = numpy recarray, of the style created when opening a .cs file 
        headers_of_interest = list of headers we want to print, if empty will print all headers 

    RETURNS 
        header_dict = dictionary of form { 'header_name' : index }, useful for looking up specific columns for a data point for this given dataset later 
    """

    print(" cs recarray shape = ", dataset.shape)

    ## 1. Unpack the header data into a dictionary we can refer to later ( 'header_name' : index/column )  
    headers = get_cs_headers(dataset) ## dict ( 'header_name' : index/column, ... )
    
    print(" headers = ")
    for key in headers:
        print("   %s. %s" % (headers[key], key))

    ## if no explicit headers of interest were given, use all 
    if len(headers_of_interest) == 0:
        for header in headers:
            headers_of_interest.append(header) 

    ## 2. Show a few entries and their header values
    ## each entry in the main array represents one entry/micrograph/particle
    for i in range(len(dataset)):
        if i < 3:
            print(" ------------------------------")
            print(" Entry #%s" % i)
            for key in headers:
                header_name = key
                header_index = headers[key]
                if header_name in headers_of_interest:
                    print("    %s = %s" % (header_name, dataset[i][header_index]))

    print(" ------------------------------")
    print(" ...")
    return 

def get_cs_headers(dataset):
    ## Unpack the header data into a dictionary we can refer to later ( 'header_name' : index/column )  
    headers = dataset.dtype.names ## 'headers' for each index position can be retrieved from the main array
    header_dict = {} 
    for i in range(len(headers)):
        header_dict[headers[i]] = i
    return header_dict
######################


#############################
###     RUN BLOCK
#############################

if __name__ == '__main__':
    import numpy as np
    import os, sys
    import random 


    cs_fname, subset_size = parse_flags(sys.argv)

    cs_data = load_data_from_cs_file(cs_fname)

    ## temp to read the full dataset and retrieve the relevant header names 
    # read_cs_data(cs_data)

    mics = get_mics_from_cs_data(cs_data)

    if subset_size != None:
        dZ_thresholds = analyse_dZ_range(mics)
        ## overwrite the micrograph list data to grab only the subset we want
        mics = get_subset_by_dZ(mics, dZ_thresholds, subset_size)
        write_all_mics_to_file(mics, out_fname = 'subset_mics.txt')
    else:
        write_all_mics_to_file(mics)
