#!/usr/bin/env python3

#############################
###     GLOBAL FLAGS
#############################
DEBUG = False
WRITE_LIST = False

#############################
###     DEFINITION BLOCK
#############################

def usage():
    print("===================================================================================================")
    print(" Export a .CSV file of processed metadata from a cryoSPARC Live session (via Browse tab) and use")
    print(" this script to write a list of rejected movies you can use to free up space on a disk, e.g.:")
    print("    $ for mic in $(cat rejected_movies.txt); do mic_path=$(find -name $mic); rm $mic_path; done")
    print(" Usage:")
    print("    $ curate_by_csv.py  input.csv  --use_defaults --write")
    print(" ")
    print(" -----------------------------------------------------------------------------------------------")
    print(" Options (default in brackets): ")
    print("                  --dZ (0.8-2.5) : Keep movies within this target range")
    print("                   --ctf_fit (5) : Keep movies with CTF fits equal or better (Ang)")
    print("          --ice_thickness (1.06) : Keep movies less than this value")
    print("         --in-frame_motion (25) : Keep moves less than this value")
    print("                  --use_defaults : Use all above flags at their default values")
    print("     --write (rejected_mics.txt) : Write out a list of movies that are rejected")
    print("===================================================================================================")
    sys.exit()
    return

def parse_flags(cmdline):
    global out_fname, csv_file, dZ_min, dZ_max, ctf_fit_max, ice_thickness_max, in_frame_motion_max, WRITE_LIST

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
        if ".csv" in param.lower():
            if csv_file != None:
                print(" Warning: Two .CSV files were found when parsing commandline!")
                print("   ... using: %s" % csv_file)
            csv_file = sys.argv[i]

        ## Parse specific flags
        if param == '--use_defaults':
                ## use defaults
                dZ_min = 0.8 # default
                dZ_max = 2.5 # set default
                ctf_fit_max = 5.0 # set default 
                ice_thickness_max = 1.06
                in_frame_motion_max = 25

        if param == '--dZ':
            try:
                dZ_min = float(cmdline[i + 1].split('-')[0])
                dZ_max = float(cmdline[i + 1].split('-')[1])
            except:
                ## use defaults
                dZ_min = 0.8 # default
                dZ_max = 2.5 # set default
                print(" Warning: Cannot correctly parse dZ range given: %s " % cmdline[i+1])
                print("  ... using default values")

        if param == '--ctf_fit':
            try:
                ctf_fit_max = float(cmdline[i+1])
            except:
                ctf_fit_max = 5.0 # set default 
                print(" Warning: Could not parse --ctf_fit value: %s " % cmdline[i+1])
                print("  ... using default value")

        if param == '--ice_thickness':
            try: 
                ice_thickness_max = float(cmdline[i + 1])
            except: 
                ice_thickness_max = 1.06
                print(" Warning: Could not parse --ice_thickness value: %s" % cmdline[i+1])
                print("  ... using defaults")

        if param == '--in-frame_motion':
            try:
                in_frame_motion_max = float(cmdline[i+1])
            except:
                in_frame_motion_max = 2.5
                print(" Warning: Could not parse --in-frame_motion value: %s" % cmdline[i + 1] )
                print("  ... using defaults")

        if param == '--write':
            WRITE_LIST = True
            if len(cmdline) >= i+2:
                if ".txt" in cmdline[i+1].lower():
                    out_fname = cmdline[i+1]
                else:
                    print(" --write flag detected but could not parse input. Using default: %s" % out_fname)

    # check for existence of input file 
    if not os.path.splitext(csv_file)[-1] in [".csv", ".CSV"]:
        print(" Input file does not have the proper extension (.csv)")
        sys.exit()

    return 

def get_csv_data(fname):
    """ Convert CSV file into a pandas DataFrame object for easy manipulation 
    """
    csv_data = pd.read_csv(fname)
    return csv_data 

def check_csv_columns(csv_data):
    """ Before running on data, check the correct CSV headers are found in the file!
    """
    ## Initialize with defaults from a CSV file generated by cryosparc instance on our workstation 
    CSV_columns = {
        'REJECT' : 'Threshold Reject',
        'CTF_FIT' : 'CTF Fit',
        'dZ_FIT' : 'DF Avg',
        'ICE_THICKNESS' : 'Rel Ice Thick.',
        'MAX_INFRAME_MOTION' : 'Motion dist.',
        'ID' : 'Index',
        'MIC_PATH' : 'File'
    }


    ## check the first DataFrame for the expected entries and switch to the correct one (if possible)
    for row in csv_data.iterrows():
        index, row_obj = row 

        # print(row_obj)

        ## Iterate over the relevant headers proceeding with the first match 
        if CSV_columns['CTF_FIT'] not in row_obj:
            try:
                ## Swap the text for a known alternate header from a cryosparc live session CSV file 
                CSV_columns["CTF_FIT"] = 'CTF Fit (A)'
                ## Check if it can retrieve a result 
                row_obj[CSV_columns['CTF_FIT']]
            except:
                print(" ERROR :: Could not find a correct CSV header for CTF_FIT parameter")
        
        if CSV_columns['dZ_FIT'] not in row_obj:
            try:
                ## Swap the text for a known alternate header from a cryosparc live session CSV file 
                CSV_columns["dZ_FIT"] = 'Defocus Avg. (μm)'
                ## Check if it can retrieve a result 
                row_obj[CSV_columns['dZ_FIT']]
            except:
                print(" ERROR :: Could not find a correct CSV header for dZ_FIT parameter")

        if CSV_columns['ICE_THICKNESS'] not in row_obj:
            try:
                ## Swap the text for a known alternate header from a cryosparc live session CSV file 
                CSV_columns["ICE_THICKNESS"] = 'Relative Ice Thickness'
                ## Check if it can retrieve a result 
                row_obj[CSV_columns['ICE_THICKNESS']]
            except:
                print(" ERROR :: Could not find a correct CSV header for ICE_THICKNESS parameter")

        if CSV_columns['MAX_INFRAME_MOTION'] not in row_obj:
            try:
                ## Swap the text for a known alternate header from a cryosparc live session CSV file 
                CSV_columns["MAX_INFRAME_MOTION"] = 'Max In-frame Motion'
                ## Check if it can retrieve a result 
                row_obj[CSV_columns['MAX_INFRAME_MOTION']]
            except:
                print(" ERROR :: Could not find a correct CSV header for MAX_INFRAME_MOTION parameter")

        if CSV_columns['ID'] not in row_obj:
            try:
                ## Swap the text for a known alternate header from a cryosparc live session CSV file 
                CSV_columns["ID"] = 'ID'
                ## Check if it can retrieve a result 
                row_obj[CSV_columns['ID']]
            except:
                print(" ERROR :: Could not find a correct CSV header for ID parameter")


        if CSV_columns['MIC_PATH'] not in row_obj:
            try:
                ## Swap the text for a known alternate header from a cryosparc live session CSV file 
                CSV_columns["MIC_PATH"] = 'File Path'
                ## Check if it can retrieve a result 
                row_obj[CSV_columns['MIC_PATH']]
            except:
                print(" ERROR :: Could not find a correct CSV header for MIC_PATH parameter")


    return CSV_columns

def get_rejected_mics(csv_data):
    """ Run through the DataFrame object and check for the cryoSPARC 'Theshold Reject' flag 
        and extract the corresponding micrograph name when True. Return the list of micrographs
        that result.
    """
    ## add a new column for the color mapping on the plotting function 
    blue = 'tab:blue'
    red = 'tab:red'
    csv_data['color'] = blue

    rejection_list = []
    ## another approach is to look at each file name and then use its unique name to look up its threshold flag in the DataFrame
    for row in csv_data.iterrows():
        index, row_obj = row 
        # print(row_obj)
        if CSV_columns['REJECT'] in row_obj:
            REJECT = row_obj[CSV_columns['REJECT']]
        else:
            REJECT = False
        # CTF_FIT = row_obj['CTF Fit (A)']
        CTF_FIT = row_obj[CSV_columns['CTF_FIT']]
        # dZ_FIT = row_obj['Defocus Avg. (μm)']
        dZ_FIT = row_obj[CSV_columns['dZ_FIT']]
        # ICE_THICKNESS = row_obj['Relative Ice Thickness']
        ICE_THICKNESS = row_obj[CSV_columns['ICE_THICKNESS']]
        # MAX_INFRAME_MOTION = row_obj['Max In-frame Motion']
        MAX_INFRAME_MOTION = row_obj[CSV_columns['MAX_INFRAME_MOTION']]
        mic_basename = os.path.splitext(os.path.basename(row_obj[CSV_columns["MIC_PATH"]]))[0]


        if REJECT:
            ## Modify the associated color for this point in the data frame 
            csv_data.at[index, 'color'] = red
            mic_basename = os.path.splitext(os.path.basename(row_obj[CSV_columns["MIC_PATH"]]))[0]
            rejection_list.append(mic_basename)
            if DEBUG:
                print("===================================================================")
                print(" Rejected: %s" % mic_basename)
                print("-------------------------------------------------------------------")
                print("   ... ID = %s" % row_obj[CSV_columns["ID"]])
                print("   ... CTF Fit (A) = %.2f" % row_obj[CSV_columns["CTF_FIT"]])
        
        if ctf_fit_max != None and CTF_FIT > ctf_fit_max:
            csv_data.at[index, 'color'] = red
            # mic_basename = os.path.splitext(os.path.basename(row_obj['File Path']))[0]
            rejection_list.append(mic_basename)
            continue 

        if dZ_min != None:
            if dZ_FIT > (dZ_max * 10000) or dZ_FIT < (dZ_min * 10000):
                csv_data.at[index, 'color'] = red
                # mic_basename = os.path.splitext(os.path.basename(row_obj['File Path']))[0]
                rejection_list.append(mic_basename)
                continue
        
        if ice_thickness_max != None and ICE_THICKNESS > ice_thickness_max:
            csv_data.at[index, 'color'] = red
            # mic_basename = os.path.splitext(os.path.basename(row_obj['File Path']))[0]
            rejection_list.append(mic_basename)
            continue

        if in_frame_motion_max != None and MAX_INFRAME_MOTION > in_frame_motion_max:
            csv_data.at[index, 'color'] = red
            # mic_basename = os.path.splitext(os.path.basename(row_obj['File Path']))[0]
            rejection_list.append(mic_basename)
            continue

    return rejection_list, csv_data

def write_list_to_file(list_obj, out_fname):
    with open(out_fname, "w") as f:
        for obj in list_obj:
            f.write("%s \n" % obj)
    return 
    
def check_for_help_flag(cmdline):
    for entry in cmdline:
        if entry in ['-h', '-help', '--h', '--help']:
            if DEBUG:
                print(' ... help flag called (%s).' % entry)
            return True
    return False

def hline_text(x, y, text, color="red", fontsize=10, linestyle="-", ax=None):
    """ Not used here but may be useful 
        draw hline at y interrupted by text at x 
        REF: https://stackoverflow.com/questions/41924767/matplotlib-can-i-interrupt-an-axhline-with-text 
    """
    if ax is None:
        ax = plt.gca()
    text = f" {text} "  # pad with single space
    label = ax.text(x, y, text, color=color, fontsize=fontsize,
                    va="center", ha="center")
    # draw text to get its bounding box
    ax.get_figure().canvas.draw()
    bbox = label.get_window_extent().transformed(ax.transData.inverted())
    # add hlines next to bounding box
    left, right = ax.get_xlim()
    ax.hlines([y]*2, [left, bbox.x1], [bbox.x0, right], color=color, linestyle=linestyle)

def plot_cutoffs(csv_data):
    fig, axes = plt.subplots(4, 1, figsize=(11,7))
    marker_size = 5

    csv_data.plot(x=CSV_columns['ID'], y=CSV_columns['dZ_FIT'], s = marker_size, kind='scatter', ax=axes[0], c=csv_data['color'])
    axes[0].set(xlabel="", ylabel="Ang", title="Avg. dZ")

    if dZ_max != None:
        axes[0].axhline(y=(dZ_max*10000), c="red",linewidth=1,zorder=0)
        text = axes[0].text(1.01, (dZ_max*10000), "%s" % (dZ_max), verticalalignment='center', horizontalalignment='left', transform=axes[0].get_yaxis_transform(), color='red', fontsize=10)

    if dZ_min != None:
        axes[0].axhline(y=(dZ_min*10000), c="red",linewidth=1,zorder=0)
        text = axes[0].text(1.01, (dZ_min*10000), "%s" % (dZ_min), verticalalignment='center', horizontalalignment='left', transform=axes[0].get_yaxis_transform(), color='red', fontsize=10)
    

    csv_data.plot(x=CSV_columns['ID'], y=CSV_columns['CTF_FIT'], s = marker_size, kind='scatter', ax=axes[1], c=csv_data['color'])
    axes[1].set(xlabel="", ylabel="Ang", title="CTF fit")

    if ctf_fit_max != None:
        axes[1].axhline(y=ctf_fit_max, c="red",linewidth=1,zorder=1)
        text = axes[1].text(1.01, ctf_fit_max, "%s" % ctf_fit_max, verticalalignment='center', horizontalalignment='left', transform=axes[1].get_yaxis_transform(), color='red', fontsize=10)
    
    csv_data.plot(x=CSV_columns['ID'], y=CSV_columns['MAX_INFRAME_MOTION'], s = marker_size, kind='scatter', ax=axes[2], c=csv_data['color'])
    axes[2].set(xlabel="", ylabel="px", title="Max. in-frame motion")

    if in_frame_motion_max != None:
        axes[2].axhline(y=in_frame_motion_max, c="red",linewidth=1,zorder=1)
        text = axes[2].text(1.01, in_frame_motion_max, "%s" % in_frame_motion_max, verticalalignment='center', horizontalalignment='left', transform=axes[2].get_yaxis_transform(), color='red', fontsize=10)

    csv_data.plot(x=CSV_columns['ID'], y=CSV_columns["ICE_THICKNESS"], s = marker_size, kind='scatter', ax=axes[3], c=csv_data['color'])
    axes[3].set(xlabel="", ylabel="signal", title="Relative ice thickness")
    if ice_thickness_max != None:
        axes[3].axhline(y=ice_thickness_max, c="red",linewidth=1,zorder=1)
        text = axes[3].text(1.01, ice_thickness_max, "%s" % ice_thickness_max, verticalalignment='center', horizontalalignment='left', transform=axes[3].get_yaxis_transform(), color='red', fontsize=10)

    fig.tight_layout()
    plt.show()

def print_summary(csv_file, rejection_list, out_fname):
    print("===================================================================")
    print(" %s micrographs were flagged as rejected from: %s" % (len(rejection_list), csv_file))
    if WRITE_LIST:
        print(" ... micrograph names are listed in: %s" % out_fname)
        print("-------------------------------------------------------------------")
        print(" Use the output file to manually delete movies from Images-Disc1 folder, e.g.:")
        print("    $ for mic in $(cat %s); do mic_path=$(find -name $mic); rm $mic_path; done" % out_fname)

    else:
        print(" ... to generate a file with micrograph names, add the --write flag and re-run")


#############################
###     RUN BLOCK
#############################


if __name__ == "__main__":

    import os
    import sys
    import pandas as pd
    import matplotlib.pyplot as plt

    ## prepare the output file name 
    out_fname = 'rejected_mics.txt'
    csv_file = None

    ## Unset all optional flags, set them only if the flag is called without input values  
    dZ_min = None 
    dZ_max = None 
    ctf_fit_max = None  
    ice_thickness_max = None
    in_frame_motion_max = None

    parse_flags(sys.argv)



    print(" RUNNING  " )
    print("-------------------------------------------------------------------")
    if dZ_min != None and dZ_max != None:
        print(" >>            dZ range : %s -> %s" % (dZ_min, dZ_max) )
    else: print(" >> No dZ range specified")
    if ctf_fit_max != None:
        print(" >>        Min. CTF fit : %s " % ctf_fit_max )
    else: print(" >> No CTF fit cutoff specified")
    if in_frame_motion_max != None:
        print(" >> Max in-frame motion : %s " % in_frame_motion_max )
    else: print(" >> No max. in-frame motion cut off specified")
    if ice_thickness_max != None:
        print(" >>   Max ice thickness : %s " % ice_thickness_max )
    else: print(" >> No ice thickness cutoff specified")


    csv_data = get_csv_data(csv_file)

    CSV_columns = check_csv_columns(csv_data)

    rejection_list, csv_data = get_rejected_mics(csv_data)

    print_summary(csv_file, rejection_list, out_fname)

    plot_cutoffs(csv_data)


    if WRITE_LIST:
        write_list_to_file(rejection_list, out_fname)

    print("===================================================================")
    print("  COMPLETE.")

