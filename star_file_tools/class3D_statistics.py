#!/usr/bin/env python3

def usage():
    """ This script requires several input arguments to work correctly. Check they exist, otherwise print usage and exit.
    """
    print("=================================================================================================================")
    print(" A program to determine the status of a Class3D run (i.e. if it has converged")
    print("=================================================================================================================")
    print(" Optional flags:")
    print("     --h : ignore all other flags, print usage and quit")
    print("=================================================================================================================")
    print(" To use, run this script in a Class3D/run directory.")
    print("=================================================================================================================")

def find_and_sort_all_model_files():
    """ Take in a file name and return a sorted list of files according to their iteration number and an empty dictionary for each file
            e.g.:   run_ct020_it023_model.star >> [(23,'run_ct020_it023_model.star'), ...]
                                               >> { 'run_cit020_it023_model.star' : , }
    """
    ## initialize the main data variables we will populate
    sorted_file_list = []
    star_file_dictionary = dict()

    file_list = glob.glob("*model.star") # use globbing to find all matching files in the current working dir
    if len(file_list) == 0:
        print("No *model.star files found in current working directory!")
        sys.exit()

    for file in file_list:
        star_file_dictionary[file] = "" ## add entry to dictionary
        file_name_split = file.split("_")
        ## by RELION 3.1 convention, the interation value is always just before the model.star in the name
        itr_value = int(file_name_split[-2][2:])
        sorted_file_list.append((itr_value, file))

    ## python automatically sorts a list of tuples based on the first entry in the tuple
    sorted_file_list.sort()

    # if VERBOSE:
    #     for file in sorted_file_list:
    #         print(file)
        # print(star_file_dictionary)

    return (sorted_file_list, star_file_dictionary)

def parse_star_file(file):
    """ For a given *_model.star file, parse the data for each class corresponding to its distribution and resolution.
        Returns a list of tuples:
                [ (str(class001.mrc), float(distribution), float(resolution), int(iteration_value) ), ... ]
    """
    print(" ... parse star file: ", file)

    file_name_split = file.split("_")
    ## by RELION 3.1 convention, the interation value is always just before the model.star in the name
    itr_value = int(file_name_split[-2][2:])

    with open(file, 'r') as f :
        line_num = 0
        table_start = 0
        table_end = 0
        class_name_col = -1
        class_distribution_col = -1
        class_resolution_col = -1
        parsed_entries = []

        for line in f :
            line_num += 1
            first_character = ""
            line = line.strip() # remove empty spaces around line
            line_to_list = line.split() # break words into indexed list format
            # ignore empty lines
            if len(line) == 0 :
                continue

            ## find the start of the data table we are interested in
            if 'data_model_classes' in line:
                # print(" >> Table found at line num: ", line_num)
                table_start = line_num

            ## if we are in the data section of the table, look for the column number for each entry we desire to parse
            if (line_num > table_start):
                if '_rlnReferenceImage' in line:
                    class_name_col = get_star_column_number(line)
                    # print('class column = ', line, class_name_col)
                if '_rlnClassDistribution' in line:
                    class_distribution_col = get_star_column_number(line)
                    # print('distribution column = ', line, class_distribution_col)
                if '_rlnEstimatedResolution' in line:
                    class_resolution_col = get_star_column_number(line)
                    # print('resolution column = ', line, class_resolution_col)

            ## catch the end of the table to end this function early
            if (line_num > table_start) and (table_end < table_start):
                if 'data_' in line:
                    # print(" >> subsequent table found at line num: " , line_num)
                    table_end = line_num
                    # if VERBOSE:
                    #     print(parsed_entries)
                    return parsed_entries

            ## if we made it this far into the function, we might be on a data entry, run a check and if it passes parse the data for each entry
            if (class_name_col > 0) and (class_distribution_col > 0) and (class_resolution_col > 0):
                ## filter out any lines that are not data entries based on if they contain '_' or '#' as their first character
                first_character = ""
                first_character = list(line_to_list[0])[0]
                if first_character == '_' or first_character == '#':
                    continue
                parsed_entries.append( ( get_star_column_info(line, class_name_col).split('/')[-1].split('_')[-1], float(get_star_column_info(line, class_distribution_col)), float(get_star_column_info(line, class_resolution_col)), int(itr_value) ) )

def get_star_column_number(line):
    """ For a line in a star file describing a column entry (e.g., '_rlnEstimatedResolution #5'), retrieve the value of that column (e.g. 5)
    """
    column_num = int(line.split()[1].replace("#",""))
    return column_num

def get_star_column_info(line, column):
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

def initialize_dataset(input_data):
    """ Input dictionary should be of the form created by parse_star_file function. Returns a new dictionary of the form:
            { 'class001.mrc' : [ (%_it1, %_it2, ...), (res_it1, res_it2, ...), (iteration value1, ...) ] }
    """
    new_dictionary = {}
    for entry in input_data:
        proportion = entry[1]
        resolution = entry[2]
        iteration_value = entry[3]
        new_dictionary[entry[0]] = ( [proportion], [resolution], [iteration_value] )

    return new_dictionary

def update_dataset(input_dict, input_data):
    """ Add values to an existing dataset created by initialize_dataset function
    """
    for entry in input_data:
       name = entry[0]
       proportion = entry[1]
       resolution = entry[2]
       iteration_value = entry[3]

       input_dict[name][0].append(proportion)
       input_dict[name][1].append(resolution)
       input_dict[name][2].append(iteration_value)

def plot_data(input_dict):
    print("Loading matplotlib...")
    from matplotlib import pyplot as plt
    from matplotlib import rcParams # update figure formatting params

    rcParams.update({'font.family': "Arial"})

    fig, axs = plt.subplots(2, 1, constrained_layout=True, figsize=(12,8)) # 2 rows, 1 column

    # axs[0].set_xlabel('itr #')
    axs[0].set_ylabel('Proportion', fontsize=14)
    axs[0].set_title('Proportion per iteration per class', fontsize=14)
    axs[1].set_xlabel('itr #', fontsize=14)
    axs[1].set_ylabel('Resolution', fontsize=14)
    axs[1].set_title('Resolution per iteration per class', fontsize=14)
    axs[0].grid(visible=True, which='major', color='gray', linestyle='-', alpha=0.5)
    axs[0].grid(visible=True, which='minor', color='gray', linestyle='--', alpha=0.2)
    axs[1].grid(visible=True, which='major', color='gray', linestyle='-', alpha=0.5)
    axs[1].grid(visible=True, which='minor', color='gray', linestyle='--', alpha=0.2)

    plt.yticks(fontsize=10)
    plt.xticks(fontsize=10)
    # adjust tick thickness to match the spine thickness
    axs[0].xaxis.set_tick_params(width=1.15)
    axs[0].yaxis.set_tick_params(width=1.15)
    axs[1].xaxis.set_tick_params(width=1.15)
    axs[1].yaxis.set_tick_params(width=1.15)


    for axis in ['top','bottom','left','right']:
        axs[0].spines[axis].set_linewidth(1.15)
        axs[1].spines[axis].set_linewidth(1.15)

    for each_class in input_dict:
        x_values = []
        y_proportion_values = []
        y_resolution_values = []

        for n in range(len(input_dict[each_class][0])):
            itr_number = input_dict[each_class][2][n]
            proportion_value = input_dict[each_class][0][n]
            resolution_value = input_dict[each_class][1][n]
            x_values.append(itr_number)
            y_proportion_values.append(proportion_value)
            y_resolution_values.append(resolution_value)

        axs[0].plot(x_values, y_proportion_values, label=each_class)

        axs[1].plot(x_values, y_resolution_values, label=each_class)

    axs[0].legend(fontsize=12)
    axs[1].legend(fontsize=12)
    plt.minorticks_on()
    plt.show()


#############################
###     RUN BLOCK
#############################
if __name__ == "__main__":

    import glob
    import os
    import sys


    ##################################################
    ### SET UP GLOBAL VARIABLES & EXPORT THOSE REQUIERD FOR IMPORTED MODULES
    ##################################################
    VERBOSE = True
    PLOT_DATA = True
    ## define VERBOSE as an environment variable so it can be found by my custom imported modules
    os.environ['VERBOSE'] = str(VERBOSE)

    ##################################################


    ###################################
    ### CHECK FOR USAGE CONDITIONS
    ###################################
    ## read all entries and check if the help flag is called at any point
    for n in range(len(sys.argv[1:])+1):
        if sys.argv[n] == '-h' or sys.argv[n] == '--help' or sys.argv[n] == '--h':
            usage()
            sys.exit()
    ###################################

    ###################################
    ### READ USER INPUT
    ###################################
    # # read all commandline arguments and adjust variables accordingly
    # for n in range(len(sys.argv[1:])+1):
    #     if sys.argv[n] == '--remove_duplicates' or sys.argv[n] == '--remove_duplicate':
    #         REMOVE_DUPLICATE = True
    #         remove_distance_angstroms = float(sys.argv[n+1])
    ###################################

    print("Running script...")
    print("")

    ###################################
    ### FIND ALL *_model.star FILES IN DIR AND INITIALIZE DATA SETS
    ###################################
    ordered_file_list, star_file_data = find_and_sort_all_model_files()
    ## ordered_file_list = [ int(interation value), str(file name), ... ], sorted by iteration value
    ## star_file_data = { str(file name) : '', ... }, empty dictinary with keys as file names
    ###################################

    ###################################
    ### PARSE ALL .STAR FILES AND POPULATE DATA STRUCTURES
    ###################################
    for file in ordered_file_list:
        file_data = parse_star_file(file[1])
        # for entry in file_data:
        #     print(entry)
        star_file_data[file[1]] = file_data
    ###################################

    ###################################
    ### REFORMAT DATA INTO A PER-CLASS FORMAT
    ###################################
    ## make a new dictionary of the form:
    ##      { 'class001.mrc' : ( [proportion it001, ... ], [resolution it001, ... ], [iteration value, ...]  ) }
    counter = 0
    for file in ordered_file_list:
        counter += 1
        ## use the first file to determine the number of classes and their titles
        if counter == 1:
            per_class_data_dictionary = initialize_dataset(star_file_data.get(file[1]))
        else:
            update_dataset(per_class_data_dictionary, star_file_data.get(file[1]))
    ###################################

    ###################################
    ### OUTPUT DATA FOR EASY READING
    ###################################
    for each_class in per_class_data_dictionary:
        print(each_class)

        for n in range(len(per_class_data_dictionary[each_class][0])):
            print("itr = %s, proportion = %s \t res = %s" % (per_class_data_dictionary[each_class][2][n], per_class_data_dictionary[each_class][0][n], per_class_data_dictionary[each_class][1][n]))

    if PLOT_DATA:
        plot_data(per_class_data_dictionary)
    ###################################
