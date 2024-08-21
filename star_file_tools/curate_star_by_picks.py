#!/usr/bin/env python3


"""
    Parse a particles .STAR file and return data on the number of particles per micrograph. Allow the user to 
    submit a flag to output a file of micrographs satisfying a particular input threshold 
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
    print(" ")
    print(" Usage:")
    print("    $ curate_star_by_picks.py  <particles>.star  ")
    print(" Example command to find all micrographs with >50 particles:")
    print("    $ curate_star_by_picks.py  run_data.star  --gt 50  --o mics_to_keep.txt")
    print(" -----------------------------------------------------------------------------------------------")
    print(" Options (default in brackets): ")
    print("                   --lt (n) : Find micrographs with particle counts less than the value n")
    print("                   --gt (n) : Find micrographs with particle counts greater than the value n")
    print("   --o (threshold_mics.txt) : Change the output file name from default")
    print("===================================================================================================")
    sys.exit()

def parse_cmdline(cmd_line):
    ## read all entries and check if the help flag is called at any point
    for cmd in cmd_line:
        if cmd == '-h' or cmd == '--help' or cmd == '--h':
            usage()

    ## parse any flags and set defaults 
    LESS_THAN = None
    GREATER_THAN = None
    out_fname = 'threshold_mics.txt' # set default 
    for i in range(len(cmd_line)):
        if cmd_line[i] == '--lt':
            try:
                LESS_THAN = int(cmd_line[i+1])
                print(" Find micrographs containing less than %s particles" % LESS_THAN)
            except:
                print(" Could not parse --lt entry or none given, provide an integer value")
                usage()

        if cmd_line[i] == '--gt':
            try:
                GREATER_THAN = int(cmd_line[i+1])
                print(" Find micrographs containing more than %s particles" % GREATER_THAN)
            except:
                print(" Could not parse --gt entry or none given, provide an integer value")
                usage()

        if cmd_line[i] == '--o':
            try:
                out_fname = cmd_line[i+1]
                print(" Save micrograph names above/below threshold into text file: %s " % out_fname)
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

    return star_file, LESS_THAN, GREATER_THAN, out_fname

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
                # if DEBUG:
                #     print("Line # %d = " % line_num, end="")
                #     print(line, " --> ", line_to_list, sep=" ")
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
                if DEBUG:
                    # print("Read though header (%s lines total)" % header_length)
                    print(" Column value for %s = %d" % (column_type, column_num))
                return column_num

def find_star_info(line, column):
    """ For a given .STAR file line entry, extract the data at the given column index.
        If the column does not exist (e.g. for a header line read in), return 'False'
    """
    # break an input line into a list data type for column-by-column indexing
    line_to_list = line.split()
    try:
        column_value = line_to_list[column-1]
        # if DEBUG:
        #     print("Data in column #%s = %s" % (column, column_value))
        return column_value
    except:
        return False

def extract_mic_name(input_string):
    """ Parse the entry for 'rlnMicrographName' to extract only the micrograph name without any path names etc...
    """
    mic_name = os.path.basename(input_string)
    # if DEBUG:
    #     print("Extract micrograph name from entry: %s -> %s" % (input_string, mic_name))
    return mic_name

def parse_star_file(file, columnName, header_size):
    """ For a given .STAR file, extract the micrograph name, # of coordinates
        WIP 
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
                # X_coordinate = float(find_star_info(line, columnX))
                # Y_coordinate = float(find_star_info(line, columnY))
                mic_name = os.path.splitext(extract_mic_name(find_star_info(line, columnName)))[0]
                if mic_name not in data_parse_list:
                    data_parse_list[mic_name] = 1
                else:
                    data_parse_list[mic_name] += 1
                # if DEBUG:
                #     print("Coordinates found: (%s, %s, %s)" % (mic_name, X_coordinate, Y_coordinate))
        return data_parse_list

def write_thresholded_mics(list_of_mics, out_fname):
    """
    """

    with open('%s' % out_fname, 'w' ) as f :
        for mic in list_of_mics:
            f.write("%s\n" % mic)
    return 

def plot_hist(particles_per_micrograph, LESS_THAN = None, GREATER_THAN = None, DEBUG = DEBUG):
    """
    PARAMETERS 
        particles_per_micrograph = dictionary of the form, {  mic_name : #_particles, ... }
        LESS_THAN = int(), threshold cutoff for selecting micrographs 
    RETURNS 
        void, display histogram of data 
    """

    min_value = min(particles_per_micrograph.values())
    max_value = max(particles_per_micrograph.values())
    # bin_size = int((max_value - min_value)/40)
    bin_size = 10
    all_values = list(particles_per_micrograph.values())

    bins = make_bins(min_value, max_value, bin_size)
    binned_data = bin_data(all_values, bins, bin_size)
    plot_data(binned_data, lower_threshold=LESS_THAN, upper_threshold=GREATER_THAN)
    plt.show()
    return 

def make_bins(lower_limit, upper_limit, bin_size, DEBUG = DEBUG):
    """ Create a set of empty bins as a dictionary to fit the incoming data. To deal with edge cases on the
        upper limit, an extra bin is made after the upper limit is reached.
    """
    if DEBUG: print(" Data limit range used: [%s, %s]" % (lower_limit, upper_limit), "; Bin size used:", bin_size)
    bins = {}
    x = lower_limit
    while x < upper_limit:
        bins[x] = 0
        #x += bin_size
        x = float("{0:.4f}".format(x+bin_size))
    # add one final bin for edge cases on the upper limit
    x = float("{0:.4f}".format(x+bin_size))
    bins[x] = 0
    if DEBUG:
        bin_list = sorted(bins.keys()) # create a sorted list to print the bins in desired order
        print("Created %s empty bins: {%s, %s, %s, ..., %s} " % (len(bins),bin_list[0], bin_list[1], bin_list[2], bin_list[-1]) )
    return bins

def bin_data(data, bin_dict, bin_size, DEBUG = False):
    """
    PARAMETERS: 
        data = a list of the entries that need to be binned (i.e. a list of the particle number for each micrograph; e.g.: [ n1, n2, ..., n ] )
        bin_dict = dictionary of the bins we will seek to fill as each entry in the data is read, of the form: { bin_1 : n1, bin_2 : n2, ..., bin : n }
        bin_size = the step size for each bin, particles at the edge of a bin will be placed into the upper bin
    RETURNS:
        bin_dict = the dictionary of each bin and its final score after all the data has been passed through 
    """
    # create a sorted list of each bin to facilitate binning data in a step-wise manner
    bins_list = sorted(bin_dict.keys())
    # run through each data and bin it
    for datum in data:
        # for each datum, run through each bin until it is placed
        for i in range(len(bins_list)):
            n = bins_list[i]
            if datum < n:
                bin_dict[bins_list[i-1]] += 1
                break # terminates the nested for loop (e.g. stops the binning loop) when a match is found
    if DEBUG:
        count = 0
        for key in bin_dict:
            count += bin_dict[key]
        print("Binned %s entries into %s bins" % (count,len(bin_dict)) )
        print(" average value = ", np.average(data))
        print(" median value = ", np.median(data))
    return bin_dict

def plot_data(data, lower_threshold = None, upper_threshold = None):
    """
    PARAMETERS:
        data = dict( bin : frequency )
        lower_threshold = int(), the cutoff for choosing micrographs less than this value, add a red line at this point for visual purposes 
        upper_threshold = int(), the cutoff for choosing micrographs more than this value, add a red line at this point for visual purposes 
    """
    bins = []
    freq = []
    for bin in data:
        bins.append(bin)
        freq.append(data[bin])

    ## pre-determine the color for each histogram bin based on the given thresholds:
    colors = []
    for bin in bins:
        # if lower_threshold != None:
        #     print(" is bin < threshold? :: %s < %s ? " % (bin, lower_threshold))
        #     if bin < lower_threshold:
        #         colors.append('tab:red')
        #     else:
        #         colors.append('tab:blue')
        colors.append('tab:blue')


    fig, ax = plt.subplots()

    bin_width = float("{0:.4f}".format(bins[2]-bins[1]))

    # draw the data as a bargraph object, associated with axes 'ax'
    hist = ax.bar(bins[1:], freq[1:], width=-bin_width, align='edge',color=colors, alpha=1.0, linewidth=0.5, edgecolor='black') # negative width with edge alignment puts the x-tick on the right side of each bar (as desired)


    ### set up grid line visuals, comment on and off to add guide lines to the figure
    # plt.minorticks_on()
    ax.set_axisbelow(True)
    # ax.grid(b=True, which='major', color='gray', linestyle='-', alpha=0.5)
    # ax.grid(b=True, which='minor', color='gray', linestyle='--', alpha=0.5)
    ax.yaxis.grid(which="major", color='gray', linestyle='-', alpha=0.5) # use this alone to see only horizontal major grid


    # read x- and y-axis limits used
    figure_left, figure_right = ax.get_xbound()
    figure_bottom, figure_top = ax.get_ybound()
    # define axes labels
    ax.set_xlabel('# particles', fontname='Arial', size='12')
    ax.set_ylabel('# micrographs', fontname='Arial', size='12')
    # define tick labels
    plt.yticks(fontname='Arial',fontsize=10)
    plt.xticks(ticks=[bins[1]-bin_width] + bins[1:], fontname='Arial',fontsize=10)
    # adjust tick thickness to match the spine thickness
    ax.xaxis.set_tick_params(width=1.15)
    ax.yaxis.set_tick_params(width=1.15)

    # Adjust figure border ('spine') thickness; to change each line separately, use: ax.spines['right'].set_linewidth(0.5)
    for axis in ['top','bottom','left','right']:
        ax.spines[axis].set_linewidth(1.15)

    if lower_threshold != None:
        ax.axvline(x=lower_threshold, c="red",linewidth=2,zorder=1)
        # text = ax.text(100, 100, "%s" % (lower_threshold), verticalalignment='center', horizontalalignment='left', transform=ax.get_yaxis_transform(), color='red', fontsize=10, zorder= 1)

    if upper_threshold != None:
        ax.axvline(x=upper_threshold, c="red",linewidth=2,zorder=1)
        # text = ax.text(100, 100, "%s" % (lower_threshold), verticalalignment='center', horizontalalignment='left', transform=ax.get_yaxis_transform(), color='red', fontsize=10, zorder= 1)



    return 

def find_mics_less_than(particles_per_mic, threshold):
    mics_less_than = []
    for mic in particles_per_mic:
        particle_num = particles_per_mic[mic]
        if particle_num < threshold:
            mics_less_than.append(mic)

    print(" %s micrographs were found to have particle counts less than %s" % (len(mics_less_than), threshold))
    return mics_less_than

def find_mics_greater_than(particles_per_mic, threshold):
    mics_greater_than = []
    for mic in particles_per_mic:
        particle_num = particles_per_mic[mic]
        if particle_num > threshold:
            mics_greater_than.append(mic)

    print(" %s micrographs were found to have particle counts greater than %s" % (len(mics_greater_than), threshold))
    return mics_greater_than

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

    star_file, LESS_THAN, GREATER_THAN, out_fname = parse_cmdline(sys.argv)

    print("... running")
    print(" .STAR file = %s" % star_file)

    header_size = header_length(star_file)
    mic_name_column = find_star_column(star_file, '_rlnMicrographName', header_size)
    particle_data = parse_star_file(star_file, mic_name_column, header_size)
    # write_manpick_files(particle_coordinate_info)

    print("==============================================")
    print("  Example micrograph particle counts:")
    print("----------------------------------------------")

    n = 0
    for i in particle_data:
        n += 1
        print(i, particle_data[i])
        if n > 3:
            break
    print("==============================================")


    mics = []
    if isinstance(LESS_THAN, int):
        mics += find_mics_less_than(particle_data, LESS_THAN)

    if isinstance(GREATER_THAN, int):
        mics += find_mics_greater_than(particle_data, GREATER_THAN)

    if len(mics) > 0:
        write_thresholded_mics(mics, out_fname)
        print(" %s micrographs were printed into file: %s" % (len(mics), out_fname))
    
    # if LESS_THAN == None and GREATER_THAN == None:
    #     plot_hist(particle_data)
    plot_hist(particle_data, LESS_THAN, GREATER_THAN)


    print("... job completed.")

#endregion