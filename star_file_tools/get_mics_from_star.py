#!/usr/bin/env python3

## A.Keszei 2024-05-03 :: Started script, adapted from .CS version 

#############################
#region :: GLOBAL FLAGS
#############################
DEBUG = True
#endregion

#############################
#region :: DEFINITION BLOCK
#############################

def usage():
    print("===================================================================================================")
    print(" Read a RELION .STAR file with micrograph metadata and export their names into a file.")
    print(" Can use options to grab a random subset across the defocus range for manual picking.")
    print(" Usage:")
    print("    $ get_mics_from_star.py  micrographs_ctf.star  ")
    print("    $ get_mics_from_star.py  micrographs_ctf.star  --subset 20")
    print(" ")
    print(" -----------------------------------------------------------------------------------------------")
    print(" Options (default in brackets): ")
    print("                --subset (15) : Get a list of micrographs across the dZ range of the given size")
    print("      --out (subset_mics.txt) : Use a desired output name for the subset file ")
    print("                    --skip () : Read in a subset list to avoid picking mics present in that list ")
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

    star_file = None 
    subset_size = None 
    out_fname = 'mics.txt'
    omit_list = []

    ## check if help flag was called or we have a minimum number of arguments to evaluate
    cmdline = sys.argv
    min_args = 1
    if len(cmdline) - 1 < min_args or check_for_help_flag(cmdline):
        print(" Not enough arguments, or help flag called")
        usage()
        sys.exit()
        
    ## before running dynamically do a first pass through the command list to update potential default values so they can be overwritten correctly later 
    for i in range(len(cmdline)):
        param = cmdline[i]
        if param == '--subset':
            out_fname = 'subset_mics.txt'

    ## check for each relevant optional flag 
    for i in range(len(cmdline)):
        param = cmdline[i]

        ## check for expected input file 
        if ".star" in param.lower():
            if star_file != None:
                print(" Warning: Two .STAR files were found when parsing commandline!")
                print("   ... using: %s" % star_file)
            star_file = sys.argv[i]

        if param == '--subset':
            try:
                subset_size = int(cmdline[i + 1])
                if DEBUG: 
                    print(" .. setting subset size to: %s" % subset_size)
            except:
                ## use defaults
                subset_size = 15
                print(" .. no explicit subset size given, using defaults: %s " % subset_size)
        if param == '--out':
            try:
                out_fname = str(cmdline[i + 1])
            except:
                print(" ... could not parse input to '--out' flag, using default: %s" % out_fname)
        if param == '--skip':
            try: 
                omit_fname = cmdline[i + 1]
                ## try loading the data into memory 
                try:
                    with open(omit_fname, 'r') as f:
                        for line in f:
                            omit_list.append(line.strip())
                except:
                    print(" ... could not read or parse skip file: %s" % omit_fname)
                    exit()
                    
            except:
                print(" ... could not parse input to '--skip' flag")
                exit()

    ## check for existence of input file 
    if star_file == None:
        print(" No input file given!")
        usage()
    if not os.path.exists(star_file):
        print(" Input file (%s) not found! Is path correct?" % star_file)
        sys.exit()

    return star_file, subset_size, out_fname, omit_list

def load_data_from_star_file(fname):
    print(" Loading star file: %s" % fname)
    ## read the header metadata 
    HEADER_START, DATA_START, DATA_END = get_table_position(fname, 'data_micrographs', DEBUG=DEBUG)
    COLUMN_MIC_NAME = find_star_column(fname, '_rlnMicrographName', HEADER_START, DATA_START, DEBUG=DEBUG)
    COLUMN_dZ_U = find_star_column(fname, '_rlnDefocusU', HEADER_START, DATA_START, DEBUG=DEBUG)
    COLUMN_dZ_V = find_star_column(fname, '_rlnDefocusV', HEADER_START, DATA_START, DEBUG=DEBUG)

    ## iterate over each data point and extract the information, then parse it into a desired data structure:
    ##    [ ('img_name', dZ_avg), ('img_name', dZ_avg), ... ]
    with open(fname, 'r') as f :
        parsed = []
        line_num = 0
        for line in f :
            line_num += 1
            ## ignore empty lines
            if len(line.strip()) == 0 :
                continue
            ## start working only after the header length
            if DATA_END >= line_num > DATA_START - 1:
                # mic_name = get_star_data(line, COLUMN_MIC_NAME)
                mic_name = os.path.splitext(remove_path(get_star_data(line, COLUMN_MIC_NAME)))[0]
                dZ_U = float(get_star_data(line, COLUMN_dZ_U))
                dZ_V = float(get_star_data(line, COLUMN_dZ_V))

                dZ_avg = ((dZ_U + dZ_V) / 2)/10000

                parsed.append((mic_name, dZ_avg))

    print(" ... %s entries found" % len(parsed))
    return parsed

def plot_hist(dataset):
    import matplotlib.pyplot as plt
    import numpy as np
    print(" TEST")
    plt.hist(dataset)
    plt.show() 
    return 

def analyse_dZ_range(mic_data, DISPLAY_DATA = False):
    ## find the full range of dZ values 
    dZ_full_list = []
    for mic, dZ in mic_data:
        dZ_full_list.append(dZ)
    dZ_min = min(dZ_full_list)
    dZ_max = max(dZ_full_list)

    print(" The dZ range of the dataset is = %s -> %s" % (dZ_min, dZ_max))

    if DISPLAY_DATA:
        plot_hist(dZ_full_list)

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

    print(" ... written subset of %s micrographs into file: %s" % (len(mic_data), out_fname))
    return 

def get_subset_by_dZ(mic_data, dZ_thresholds, subset_size, omit_list = []):
    subset = []
    if len(omit_list) > 0:
        print(" List of mics to skip provided (%s mics): " % len(omit_list))
        for n in range(3):
            print("   %s" % omit_list[n])
        print("   ...")

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
        n = random.randint(0, len(mic_data) - 1)
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
                    elif current_mic_data in omit_list:
                        print(" !! Match exists in the omit list, find another... ")
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
        if i > 8 or i == len(subset): 
            break 
        print("   %s [dZ %s]" % (subset[i][0], subset[i][1]))
    print("   ...")

    return subset


##### STAR file handler functions 
def get_table_position(file, table_title, DEBUG = True):
    """ Find the line numbers for key elements in a relion .STAR table.
		---------------------------------------------------------------
		PARAMETERS
		---------------------------------------------------------------
			file = str(); name of .STAR file with tables (e.g. "run_it025_model.star")
			table_title = str(); name of the .STAR table we are interested in (e.g. "data_model_classes")
			DEBUG = bool(); optional parameter to display or not return values
		---------------------------------------------------------------
		RETURNS
		---------------------------------------------------------------
			HEADER_START = int(); line number for the first entry after `loop_' in the table
			DATA_START = int(); line number for the first data entry after header
			DATA_END = int(); line number for the last data entry in the table
    """
    TABLE_START = -1
    HEADER_START = -1 ## line number for the first _COLUMN_NAME #value entry in the header
    DATA_START = -1 ## line number for the first data entry corresponding to the table
    DATA_END = -1 ## line number for the last data entry corresponding to the table

    with open(file, 'r') as f :
        line_num = 0
        for line in f :
            line_num += 1
            line = line.strip() # remove empty spaces around line
            line_to_list = line.split() # break words into indexed list format
            ## check if we can exit the loop since we have all data we want
            if DATA_END > 0:
                break
            ## handle empty lines
            if len(line) == 0 :
                ## check if we are in the data section, in which case the first empty line corresponds to the end of the data
                if DATA_START > 0:
                    DATA_END = line_num - 1
                    continue
                else:
                    continue
            ## catch the table title
            if line_to_list[0] == table_title and TABLE_START < 0:
                TABLE_START = line_num
                continue
            ## catch the header start position
            if line_to_list[0] == "loop_" and TABLE_START > 0:
                HEADER_START = line_num + 1
                continue
            ## if we in the header, check if we have entered the data section by checking when the first character is no longer a `_'
            if HEADER_START > 0 and DATA_START < 0:
                first_character = list(line_to_list[0])[0]
                if first_character != '_':
                    DATA_START = line_num
                    continue
    ## in cases where there is no empty line at the end of the file we need to manually update the DATA_END to match this line value
    if DATA_END == -1:
        DATA_END = line_num
        
    if DEBUG:
        print(" Find line numbers for table '%s' in %s" % (table_title, file))
        print("   >> Table starts at line:  %s" % TABLE_START)
        print("   >> Data range (start, end) = (%s, %s)" % (DATA_START, DATA_END))
        print("-------------------------------------------------------------")
    return HEADER_START, DATA_START, DATA_END

def find_star_column(file, column_name, header_start, header_end, DEBUG = True) :
    """ For an input .STAR file and line number range corresponding to the header, find the assigned column of a desired column by name (e.g. 'rlnMicrographName')
	---------------------------------------------------------------
	PARAMETERS
	---------------------------------------------------------------
		file = str(); name of the star file to parse
		column_name = str(); name of the header column to look for (e.g. '_rlnEstimatedResolution')
		header_start = int(); line number correspondnig to the first entry of the header
		header_end = int(); line number corresponding to the last entry of the header (typically line before start of data)
		DEBUG = bool(); optionally print out steps during run
	---------------------------------------------------------------
	RETURNS
	---------------------------------------------------------------
		column_num = int(); number assigned to the given column (e.g. _rlnCoordinateX #3 -> 3)
    """
    column_num = None # initialize variable for error handling
    with open(file, 'r') as f :
        line_num = 0
        for line in f :
            line_num += 1
            ## check if we are in range of the header
            if line_num < header_start or line_num > header_end:
                continue
            ## extract column number for micrograph name
            if column_name in line :
                column_num = int(line.split()[1].replace("#",""))
                ## handle error case where input .STAR file is missing a necessary rlnColumn type
                if column_num is None :
                    print(" ERROR: Input .STAR file: %s, is missing a column for: %s" % (file, column_name) )
                    sys.exit()
                else:
                    if DEBUG:
                        print("  ... %s column value: #%s" % (column_name, column_num))
                        # print("-------------------------------------------------------------")
                    return column_num

def get_star_data(line, column, DEBUG = False):
    """ For a given .STAR file line entry, extract the data at the given column index.
        If the column does not exist (e.g. for a header line read in), return 'False'
		---------------------------------------------------------------
		PARAMETERS
		---------------------------------------------------------------
			line = str(); line from file containing data columns
			column = int(); index of column from which to find data
			DEBUG = bool(); print on cmd line function process
		---------------------------------------------------------------
		RETURNS
		---------------------------------------------------------------
			column_value = str() or bool(); returns the value in star column index as a string, or False if no column exists
    """
    # break an input line into a list data type for column-by-column indexing
    line_to_list = line.split()
    try:
        column_entry = line_to_list[column-1]
        if DEBUG:
            print("Data in column #%s = %s" % (column, column_entry))
        return column_entry
    except:
        return False

def remove_path(file_w_path):
    """ Parse an input string containing a path and return the file name without the path. Useful for getting micrograph name from 'rlnMicrographName' column.
	---------------------------------------------------------------
	PARAMETERS
	---------------------------------------------------------------
		file_w_path = str()
	---------------------------------------------------------------
	RETURNS
	---------------------------------------------------------------
		file_wo_path = str() (e.g. /path/to/file -> 'file')
    """
    globals()['os'] = __import__('os')
    file_wo_path = os.path.basename(file_w_path)
    return file_wo_path
#####

#endregion

#############################
#region :: RUN BLOCK
#############################

if __name__ == '__main__':
    import os, sys
    import random 


    star_fname, subset_size, out_fname, omit_list = parse_flags(sys.argv)

    star_data = load_data_from_star_file(star_fname)

    if subset_size != None:
        dZ_thresholds = analyse_dZ_range(star_data)
        ## overwrite the micrograph list data to grab only the subset we want
        mics = get_subset_by_dZ(star_data, dZ_thresholds, subset_size, omit_list)
        write_all_mics_to_file(mics, out_fname = out_fname)
    else:
        write_all_mics_to_file(star_data, out_fname = out_fname)

#endregion