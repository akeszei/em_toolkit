#!/usr/bin/env python3

def usage():
    print("=================================================================================================================")
    print(" Plot star file FSC curves into a more readable format.")
    print(" If no input file is given, it will automatically look for 'postprocess.star'")
    print(" Usage: ")
    print("   $ plot_fsc.py  input.star")
    print("=================================================================================================================")
    print(" Optional flags:")
    print("     --h : ignore all other flags, print usage and quit")
    print("=================================================================================================================")
    sys.exit()

def parse_star_file(file):
    """ For a given postprocess.star file, parse the FSC data into a list of tuples:
                [
                    ( inverse_resolution,  Ang_resolution,  FSC_corr,  FSC_unmasked,  FSC_masked, FSC_randomized, randomize_from),
                    ...
                ]
    """
    print(" ... parse star file: ", file)

    with open(file, 'r') as f :
        line_num = 0
        table_start = 0
        table_end = 0
        inv_res_col = -1
        ang_res_col = -1
        fsc_corr_col = -1
        fsc_unmask_col = -1
        fsc_mask_col = -1
        fsc_random_col = -1
        parsed_entries = []
        phase_randomize_from = -1

        for line in f :
            line_num += 1
            first_character = ""
            line = line.strip() # remove empty spaces around line
            line_to_list = line.split() # break words into indexed list format
            # ignore empty lines
            if len(line) == 0 :
                continue

            ## grab the value from the phase randomized entry in the star file  when it appears
            if '_rlnRandomiseFrom' in line:
                phase_randomize_from = line_to_list[1]
                print(" Phase radomize from >> %s Ang" % phase_randomize_from)


            ## find the start of the data table we are interested in
            if 'data_fsc' in line:
                # print(" >> Table found at line num: ", line_num)
                table_start = line_num

            ## if we are in the data section of the table, look for the column number for each entry we desire to parse
            if (line_num > table_start):
                if '_rlnResolution' in line:
                    inv_res_col = get_star_column_number(line)
                    # print('class column = ', line, class_name_col)
                if '_rlnAngstromResolution' in line:
                    ang_res_col = get_star_column_number(line)
                    # print('class column = ', line, class_name_col)
                if '_rlnFourierShellCorrelationCorrected' in line:
                    fsc_corr_col = get_star_column_number(line)
                    # print('class column = ', line, class_name_col)
                if '_rlnFourierShellCorrelationUnmaskedMaps' in line:
                    fsc_unmask_col = get_star_column_number(line)
                    # print('class column = ', line, class_name_col)
                if '_rlnFourierShellCorrelationMaskedMaps' in line:
                    fsc_mask_col = get_star_column_number(line)
                    # print('class column = ', line, class_name_col)
                if '_rlnCorrectedFourierShellCorrelationPhaseRandomizedMaskedMaps' in line:
                    fsc_random_col = get_star_column_number(line)
                    # print('class column = ', line, class_name_col)


            ## catch the end of the table to end this function early
            if (line_num > table_start) and (table_end < table_start):
                if 'data_' in line:
                    # print(" >> subsequent table found at line num: " , line_num)
                    table_end = line_num
                    # if VERBOSE:
                    #     print(parsed_entries)
                    return parsed_entries

            ## if we made it this far into the function, we might be on a data entry, run a check first if we have assigned all columns we expect
            if (inv_res_col > 0) and (ang_res_col > 0) and (fsc_corr_col > 0) and (fsc_unmask_col > 0) and (fsc_mask_col > 0) and (fsc_random_col > 0):
                ## filter out any lines that are not data entries based on if they contain '_' or '#' as their first character
                first_character = ""
                first_character = list(line_to_list[0])[0]
                if first_character == '_' or first_character == '#':
                    continue
                ## parse each entry
                parsed_entries.append(
                    (   float(get_star_column_info(line, inv_res_col)),
                        float(get_star_column_info(line, ang_res_col)),
                        float(get_star_column_info(line, fsc_corr_col)),
                        float(get_star_column_info(line, fsc_unmask_col)),
                        float(get_star_column_info(line, fsc_mask_col)),
                        float(get_star_column_info(line, fsc_random_col)),
                        float(phase_randomize_from)
                    )
                )

    print("ERROR :: Did not correctly parse file!")
    return

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

def plot_data(data):
    print("Loading matplotlib...")
    from matplotlib import pyplot as plt
    from matplotlib import rcParams # update figure formatting params

    rcParams.update({'font.family': "Arial"})

    fig, ax = plt.subplots(constrained_layout=True, figsize=(5,3)) # 1 row, 1 column
    ax.set_xlabel('Resolution (Å)', fontsize=14)
    ax.set_ylabel('Correlation', fontsize=14)
    ax.set_title('Fourier Shell Correlation', fontsize=14)
    ax.grid(visible=True, which='major', color='gray', linestyle='-', alpha=0.5)
    ax.grid(visible=True, which='minor', color='gray', linestyle='--', alpha=0.2)

    ##
    plt.yticks(fontsize=12)
    plt.xticks(fontsize=12)
    ## adjust tick thickness to match the spine thickness
    ax.xaxis.set_tick_params(width=1.15)
    ax.yaxis.set_tick_params(width=1.15)

    #
    for axis in ['top','bottom','left','right']:
        ax.spines[axis].set_linewidth(1.15)

    x_values = []
    fsc_corr_y_values = []
    fsc_unmask_y_values = []
    fsc_mask_y_values = []
    fsc_random_y_values = []
    EST_RES = False
    for i in range(len(data)):
        ## expect data in form: tuple(inverse_resolution,  Ang_resolution,  FSC_corr,  FSC_unmasked,  FSC_masked)
        inverse_resolution,  Ang_resolution,  FSC_corr,  FSC_unmasked,  FSC_masked, FSC_randomized, phase_radomize_from = data[i]
        x_values.append(inverse_resolution)
        fsc_corr_y_values.append(FSC_corr)
        if FSC_corr < 0.143 and EST_RES == False:
            print(" 0.143 threshold @ %s" % data[i-1][1])
            EST_RES = data[i-1][1]
            EST_RES_coord = (data[i-1][0], data[i-1][2])
        fsc_unmask_y_values.append(FSC_unmasked)
        fsc_mask_y_values.append(FSC_masked)
        fsc_random_y_values.append(FSC_randomized)

    plt.plot(x_values, fsc_random_y_values, label='Randomized', color = 'tab:purple', linewidth = 3)
    plt.plot(x_values, fsc_corr_y_values, label='Corrected', color = 'black', linewidth = 3)
    plt.plot(x_values, fsc_unmask_y_values, label='No Mask', color = 'tab:blue', linewidth = 3)
    plt.plot(x_values, fsc_mask_y_values, label='Masked', color = 'tab:red', linewidth = 3)

    # fig.canvas.draw()
    ax.set_xlim(xmin=0)
    locs,labels = plt.xticks()
    # ylocs,ylabels = plt.yticks()
    # ax.set_ylim(ymin=ylocs[0])

    ## draw a vertical line where phases were randomized from
    if phase_radomize_from > 0:
        plt.axvline(x = 1 / phase_radomize_from, color = 'tab:purple', label = None, alpha = 0.75, linewidth = 1.5, linestyle = '--')
    ## on phase radomization from Steven Ludtke in google groups discussion:
        # Step forward in time a bit, and you'll see that Richard Henderson published an additional paper suggesting a method for proving that your refinements really are independent, and adjusting your resolution (if it turns out that they were not). The idea is straightforward, take your raw data, do a normal (in EMAN2.1 this would be gold-standard) refinement, then phase-randomize the particle data beyond some target resolution. This resolution should be worse than the resolution your normal refinement claimed to have achieved. Since the particle data no longer has any actual data/signal past some cutoff resolution, if you re-refine it exactly the same way, you should find that the FSC falls rapidly at the exact resolution where you started randomizing the phases. If this does not happen, it implies that your refinement procedure has some hidden correlation between the even/odd maps, and your resolution was over-estimated.



    ## draw fsc 0.143 cutoff lines
    plt.axhline(y = 0.143, color = 'black', label = None, alpha = 0.5, linewidth = 1.5, linestyle = '--')
    # OFFSET = 0.02 ## percent to offset the label from the point
    # point1 = [0, EST_RES_coord[1]]
    # point2 = [ EST_RES_coord[0], EST_RES_coord[1]]
    # point3 = [ EST_RES_coord[0], ylocs[0]]
    # plt.plot([point1[0], point2[0]], [point1[1], point2[1]], '-', color = 'black', alpha = 0.5)
    # plt.plot([point2[0], point3[0]], [point2[1], point3[1]], '-', color = 'black', alpha = 0.5)
    # plt.plot([point2[0]], [point2[1]], 'o', color = 'black', alpha = 0.5)
    # plt.annotate("%.2f Å" % EST_RES, (point2[0] + point2[0] * OFFSET, point2[1] + point2[1] * OFFSET))


    transformed_labels = []
    for i in range(len(locs)):
        if i == 0:
            transformed_labels.append(" ")
        else:
            x_coord = locs[i]
            res = 1/ x_coord
            # print(i, ", ", x_coord, " ->", res)
            transformed_labels.append("{:.2f}".format(res))
    ax.set_xticklabels(transformed_labels)


    ax.legend(fontsize=10)
    plt.minorticks_on()
    plt.show()



#############################
###     RUN BLOCK
#############################
if __name__ == "__main__":

    import os
    import sys

    cmd_line = sys.argv

    ## read all entries and check if the help flag is called at any point
    for cmd in cmd_line:
        if cmd == '-h' or cmd == '--help' or cmd == '--h':
            usage()

    ## parse input for .star file, otherwise default to postprocess.star
    file = 'postprocess.star'
    for cmd in cmd_line:
        if len(cmd) > 5:
            # print(cmd[-5:])
            if cmd[-5:] == ".star":
                file = cmd

    ## TO DO: Sanity check the file exists

    data = parse_star_file(file)

    plot_data(data)
