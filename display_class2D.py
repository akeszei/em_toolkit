#!/usr/bin/env python3

"""
    A script to quickly create an image of an array of 2D classes, organized by
    paticle # or resolution with an optional size bar. Typically run in a subfolder
    of a Class2D or Select folder
"""

## 2021-08-24: Initial script written. To Do: clean up debugging output, otherwise should work as expected. Also add transparency if using PNG!
## 2021-08-25: Updated to add transparency behaviour when using .PNG format

#############################
###     FLAGS
#############################
DEBUG = True

#############################
###     DEFINITION BLOCK
#############################

def usage():
    """ This script requires several input arguments to work correctly. Check they exist, otherwise print usage and exit.
    """
    print("===================================================================================================")
    print(" Script to quickly generate a figure of the top classes genreated by a RELION Class2D job, ")
    print(" sorted by either class distribution or estimated resolution with, or without, a scalebar. ")
    print(" Usage:")
    print("    $ display_class2D.py  classes.mrcs  model.star")
    print(" -----------------------------------------------------------------------------------------------")
    print(" Options: ")
    print("    --out (2d_classes.jpg) : output name of the image file (can use ..jpg, .png, .gif, .tif). ")
    print("                             If --scalebar flag is provided, its size will be added to name")
    print("             --spacing (2) : spacing between images in the panel ")
    print("       --array_shape (5x3) : dimensions of the panel (columns x rows)")
    print("           --scalebar (-1) : length of scalebar in Angstroms. Note: uses 1.94 Ang/px by default")
    print("           --angpix (1.94) : Angstroms per pixel, necessary for scalebar to be correct size")
    print("          --sort_by (size) : sort classes by class distribution (size) or est. resolution (res)")
    print("              --indent (8) : pixels to inset the scalebar from the bottom left")
    print("               --scale (3) : thickness of the scalebar stroke ")
    print("===================================================================================================")
    sys.exit()

def parse_flags():
    global array_dimensions, sort_by, angpix, scalebar_angstroms, ADD_SCALEBAR, scalebar_stroke, scalebar_indent, mrcs_file, model_file, output_file_name, padding

    ## check there is a minimum number of entries otherwise print usage and exit
    if len(sys.argv) < 3:
        usage()

    ## read all entries and check if the help flag is called at any point
    for n in range(len(sys.argv[1:])+1):
        # if the help flag is called, pring usage and exit
        if sys.argv[n] == '-h' or sys.argv[n] == '--help' or sys.argv[n] == '--h':
            usage()

    ## read all legal commandline arguments
    for n in range(len(sys.argv[1:])+1):
        ## read any entry with '.star' as the model file
        if os.path.splitext(sys.argv[n])[1] == '.star':
            model_file = sys.argv[n]
        ## read any entry with '.mrcs' as the mrcs file
        if os.path.splitext(sys.argv[n])[1] == '.mrcs':
            mrcs_file = sys.argv[n]
        ## check for optional flags
        if sys.argv[n] == '--array_shape':
            ## sanity check user input
            array_shape = sys.argv[n + 1]
            if not "x" in array_shape :
                print("ERROR: Incorrect --array_shape provided: ", array_shape, "; instead, try: 5x3")
                usage()
            nrows = int(array_shape.split('x')[0]) # Define number of rows
            ncols = int(array_shape.split('x')[1]) # Define number of columns
            if nrows > 0 and ncols > 0:
                array_dimensions = array_shape
            else:
                print("ERROR: Incorrect --array_shape provided: ", array_shape, "; instead, try: 5x3")
                usage()
        if sys.argv[n] == '--scalebar':
            try:
                scalebar_angstroms = int(sys.argv[n+1])
                ADD_SCALEBAR = True
            except ValueError:
                print("ERROR: Wrong --scalebar value provided: ", sys.argv[n+1])
                usage()
        if sys.argv[n] == '--sort_by':
            if sys.argv[n+1] == "size":
                sort_by = "class_distribution"
            elif sys.argv[n+1] == "res":
                sort_by = "estimated_resolution"
            else:
                print("ERROR: Incorrect --sort_by flag given: ", sys.argv[n+1])
                usage()
        if sys.argv[n] == '--indent':
            try:
                scalebar_indent = int(sys.argv[n+1])
            except ValueError:
                print("ERROR: Incompatible --indent flag given (must be int): ", sys.argv[n+1])
                usage()
        if sys.argv[n] == '--stroke':
            try:
                scalebar_stroke = int(sys.argv[n+1])
            except ValueError:
                print("ERROR: Incompatible --stroke flag given (must be int): ", sys.argv[n+1])
                usage()
        if sys.argv[n] == '--out':
            output_file_name = sys.argv[n+1]
            if len(output_file_name) <= 0:
                output_file_name = "2d_classes.jpg"
        if sys.argv[n] == '--spacing':
            try:
                padding = int(sys.argv[n+1])
            except ValueError:
                print("ERROR: Incompatible --spacing flag given (must be int): ", sys.argv[n+1])
                usage()
            if padding <= 0:
                print("ERROR: Negative --spacing value supplied, must be >= 0")
                usage()


    ## sanity check we at least have an .mrcs and .star file assigned, rest of variables have default parameters we can use
    if not ".mrcs" in mrcs_file:
        print(" ERROR: missing an assigned .MRCS file")
        usage()
    if not ".star" in model_file:
        print(" ERROR: missing an assigned .STAR file")
        usage()

    ## print warning if no --angpix is given but --scalebar is (i.e. user may want to use a differnet pixel size)
    if ADD_SCALEBAR:
        commands = []
        ## get all commands
        for n in range(len(sys.argv[1:])+1):
            commands.append(sys.argv[n])
        ## check if --angpix was given
        if not '--angpix' in commands:
            print("!! WARNING: --scalebar was given without an explicit --angpix, using default value of 1.94 Ang/px !!")

    return

def get_table_line_numbers(file, table_title = "data_model_classes"):
    """ Find the position of the table by its line numbers for ther functions to use as their working area in the file
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
            if line_to_list[0] == "loop_":
                HEADER_START = line_num + 1
                continue
            ## if we in the header, check if we have entered the data section by checking when the first character is no longer a `_'
            if HEADER_START > 0 and DATA_START < 0:
                first_character = list(line_to_list[0])[0]
                if first_character != '_':
                    DATA_START = line_num
                    continue
    if DEBUG:
        print(" Find line numbers for table '%s' in %s" % (table_title, file))
        print("   >> Table starts at line:  %s" % TABLE_START)
        print("   >> Data range (start, end) = (%s, %s)" % (DATA_START, DATA_END))
        print("-------------------------------------------------------------")
    return HEADER_START, DATA_START, DATA_END

def find_star_column(file, column_name, header_start, header_end) :
    """ For an input .STAR file, search through the header and find the column numbers assigned to a given column_type (e.g. 'rlnMicrographName', ...)
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
                    print("ERROR: Input .STAR file: %s, is missing a column for: %s" % (file, column_name) )
                    sys.exit()
                else:
                    if DEBUG:
                        print("   >> %s column value: #%s" % (column_name, column_num))
                        # print("-------------------------------------------------------------")
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
    # if VERBOSE:
    #     print("Extract micrograph name from entry: %s -> %s" % (input_string, mic_name))
    return mic_name

def sort_data_by_column(file, data_start, data_end, COLUMN_rlnReferenceImage, COLUMN_rlnClassDistribution = -1, COLUMN_rlnEstimatedResolution = -1):
    """ Return a list of ReferenceImages, sorted by the target column type
    """
    parsed_data = []
    with open(file, 'r') as f :
        line_num = 0
        for line in f :
            line_num += 1
            ## skip parser if we are out of range of the data line numbers
            if line_num < data_start or line_num > data_end:
                continue
            ## parse the reference image number and class distribution for each line entry
            current_reference_img = find_star_info(line, COLUMN_rlnReferenceImage)
            if COLUMN_rlnClassDistribution > 0:
                current_data_entry = find_star_info(line, COLUMN_rlnClassDistribution)

            elif COLUMN_rlnEstimatedResolution > 0:
                current_data_entry = find_star_info(line, COLUMN_rlnEstimatedResolution)

            ## format the extracted data into a tuple and pass it into the list we are building
            parsed_data.append((int(current_reference_img.split('@')[0]), float(current_data_entry)))


    if COLUMN_rlnClassDistribution > 0:
        parsed_data.sort(key=lambda x: x[1], reverse = True)
    elif COLUMN_rlnEstimatedResolution > 0:
        parsed_data.sort(key=lambda x: x[1], reverse = False)

    if DEBUG:
        metadata_type = ""
        if COLUMN_rlnClassDistribution > 0:
            metadata_type = "class distribution"
        elif COLUMN_rlnEstimatedResolution > 0:
            metadata_type = "estimated resolution"

        print("-------------------------------------------------------------")
        print(" Sort classes by %s:" % metadata_type)
        print("     Class #%s, %s = %s" % (parsed_data[0][0], metadata_type, parsed_data[0][1]))
        print("     Class #%s, %s = %s" % (parsed_data[1][0], metadata_type, parsed_data[1][1]))
        print("     ...")
        print("     Class #%s, %s = %s" % (parsed_data[-2][0], metadata_type, parsed_data[-2][1]))
        print("     Class #%s, %s = %s" % (parsed_data[-1][0], metadata_type, parsed_data[-1][1]))
        print("-------------------------------------------------------------")

    ## return the sorted list for use by other functions
    return parsed_data

def get_mrcs_images(mrcs_file):
    """ returns a list of images as a normalized nparray
    """
    images_as_array = []

    ## open the mrcs file as an nparray of dimension (n, box_size, box_size), where n is the number of images in the stack
    with mrcfile.open(mrcs_file) as mrcs:
        counter = 0
        ## interate over the mrcs stack by index n
        for n in range(mrcs.data.shape[0]):
            counter +=1
            remapped = (255*(mrcs.data[n] - np.min(mrcs.data[n]))/np.ptp(mrcs.data[n])).astype(int) ## remap data from 0 -- 255
            images_as_array.append(remapped)

    if DEBUG:
        print(" Extract images from %s " % mrcs_file)
        print("   >> %s images extracted" % len(images_as_array))
        print("   >> dimensions (x, y) = (%s, %s) pixels " % (images_as_array[0].shape[0], images_as_array[0].shape[1]))
        print("-------------------------------------------------------------")

    return images_as_array

def create_image_array(array_shape, image_dataset, img_array_list, image_format, padding):
    ## sanity check image format being used
    if not image_format.lower() in [".jpg", ".jpeg", ".png", ".gif", ".tif"]:
        print("ERROR: Noncompatible extension used to save image: ", os.path.splitext(save_name)[1])
        usage()

    PADDING = padding

    nrows = int(array_shape.split('x')[1])
    ncols = int(array_shape.split('x')[0])

    ## get the image size (should be a perfect square so only grab one dimension)
    image_box_size = img_array_list[0].shape[0]

    ## prepare a blank canvas to draw upon, if .PNG format add empty alpha channel
    if image_format.lower() == ".png":
        canvas = np.full((nrows * image_box_size + PADDING * (nrows - 1), ncols * image_box_size + PADDING * (ncols - 1), 2), (0, 0), np.uint8) ## by convention, alpha is last channel
    else:
        canvas = np.full((nrows * image_box_size + PADDING * (nrows - 1), ncols * image_box_size + PADDING * (ncols - 1)), np.inf) ## by convention, top left of the image is coordinate (0, 0)

    ## populate the canvas with each image at a specific location
    counter = 0
    for panel in range(nrows * ncols):
        col = counter % ncols
        row = int(counter / ncols)
        # print("panel position (row, column) = (%s, %s)" % (col, row))

        x_range = (row * image_box_size + (PADDING * row), (row * image_box_size) + image_box_size + (PADDING * row))
        y_range = (col * image_box_size + (PADDING * col), (col * image_box_size) + image_box_size + (PADDING * col))

        # print("x and y ranges = ", x_range, y_range)

        ## check if we have an image at this index
        if len(image_dataset) - 1 >= counter:
            ## get the index of the image based on the sorted image dataset
            img_index = image_dataset[counter][0] - 1
            # print(img_index)
            ## 'stamp' the image onto the target location
            if image_format.lower() == ".png":
                ## add alpha channel data to the incoming image
                alpha = np.full((image_box_size, image_box_size), 255, np.uint8) ## remove full transparency from area where image will be displayed
                image_RGBA = np.dstack((img_array_list[img_index], alpha)) ## apply the new transparency values to the image area in quest
                canvas[ x_range[0]: x_range[1] , y_range[0] : y_range[1]] = image_RGBA
            else:
                canvas[ x_range[0]: x_range[1] , y_range[0] : y_range[1]] = img_array_list[img_index]

        counter += 1

    if DEBUG:
        print(" Print image array onto canvas")
        if image_format.lower() == ".png":
            print("   >> PNG mode active, apply transparency as RGBA")
        print("   >> Array %s images into %s columns by %s rows" % (ncols * nrows, ncols, nrows))
        print("   >> Spacing factor between images = %s px" % PADDING)
        print("-------------------------------------------------------------")
    return canvas

def add_scalebar(im, box_size, angpix, scalebar_size, indent_px = 8, stroke = 4):
    scalebar_px = int(scalebar_size / angpix)

    ## find the pixel range for the scalebar, typically 5 x 5 pixels up from bottom left
    LEFT_INDENT = indent_px # px from left to indent the scalebar
    BOTTOM_INDENT = indent_px # px from bottom to indent the scalebar
    STROKE = stroke # px thickness of scalebar
    x_range = (LEFT_INDENT, LEFT_INDENT + scalebar_px)
    y_range = (box_size - BOTTOM_INDENT - STROKE, box_size - BOTTOM_INDENT)

    ## set the pixels white for the scalebar
    for x in range(x_range[0], x_range[1]):
        for y in range(y_range[0], y_range[1]):
            im[y][x] = np.inf

    if DEBUG:
        print(" Printing scalebar onto first panel:")
        print("   >> %s pixels (%s Angstroms)" % (scalebar_px, scalebar_size))
        print("   >> Indent scalebar %s pixels from bottom left edge of panel" % indent_px)
        print("-------------------------------------------------------------")

    return im

def publish_image(im, save_name):
    global scalebar_angstroms, angpix, sort_by
    ## if scalebar is drawn, add its size and angpix used
    if scalebar_angstroms > 0:
        if sort_by == "class_distribution":
            save_name = os.path.splitext(save_name)[0] + "_sizeSorted_" + str(scalebar_angstroms) + "AngBar_" + str(angpix) + "apix" + os.path.splitext(save_name)[1]
        elif sort_by == "estimated_resolution":
            save_name = os.path.splitext(save_name)[0] + "_resSorted" + str(scalebar_angstroms) + "AngBar_" + str(angpix) + "apix" + os.path.splitext(save_name)[1]
    else:
        if sort_by == "class_distribution":
            save_name = os.path.splitext(save_name)[0] + "_sizeSorted" + os.path.splitext(save_name)[1]
        elif sort_by == "estimated_resolution":
            save_name = os.path.splitext(save_name)[0] + "_resSorted" + os.path.splitext(save_name)[1]

    ## sanity check extension being used
    if not os.path.splitext(save_name)[1].lower() in [".jpg", ".jpeg", ".png", ".gif", ".tif"]:
        print("ERROR: Noncompatible extension used to save image: ", os.path.splitext(save_name)[1])
        usage()

    if os.path.splitext(save_name)[1].lower() == '.png':
        im = Image.fromarray(im_array).convert('RGBA')
    else:
        im = Image.fromarray(im_array).convert('RGB')

    im.save(save_name)
    if DEBUG:
        print(" Saved image with metadata suffixes: ")
        print("   >> %s" % save_name)
        # print("-------------------------------------------------------------")
    im.show()
    return

#############################
###     RUN BLOCK
#############################

if __name__ == "__main__":
    from pathlib import Path # requires python 3.4+
    import string
    import os
    import sys
    import re
    from PIL import Image
    import numpy as np
    import mrcfile

    ##################################
    ## DEFAULT VARIABLES
    ##################################
    array_dimensions = '5x3'
    sort_by = "class_distribution"
    angpix = 1.94
    scalebar_angstroms = -1 # angstroms
    ADD_SCALEBAR = False
    scalebar_stroke = 4 # how thick the scalebar should be
    scalebar_indent = 8 # inset from the bottom left corner to place the scalebar
    mrcs_file = "" #sys.argv[1]
    model_file = "" #sys.argv[2]
    output_file_name = '2d_classes.jpg'
    COLUMN_rlnClassDistribution = -1
    COLUMN_rlnEstimatedResolution = -1
    padding = 2

    ## check if user has passed in approrpiate entries & parse flags into global variables
    parse_flags()

    print("=============================================================")
    print(" ... running: display_class2D.py")
    print("=============================================================")

    ## initially parse through the model file to get the line numbers we need to extract data from our specific table of interest
    HEADER_START, DATA_START, DATA_END = get_table_line_numbers(model_file, "data_model_classes")

    ## subsequently, get the column numbers for the desired data types
    print(" Find column values from header loop:")
    COLUMN_rlnReferenceImage = find_star_column(model_file, "_rlnReferenceImage", HEADER_START, DATA_START - 1)
    if sort_by == "class_distribution":
        COLUMN_rlnClassDistribution = find_star_column(model_file, "_rlnClassDistribution", HEADER_START, DATA_START - 1)
    elif sort_by == "estimated_resolution":
        COLUMN_rlnEstimatedResolution = find_star_column(model_file, "_rlnEstimatedResolution", HEADER_START, DATA_START - 1)
    else:
        print("ERROR: Unsupported sorting method requested.")

    ## once I have column positions, I can parse through the dataset, ordering it by the desired column type
    sorted_dataset = sort_data_by_column(model_file, DATA_START, DATA_END, COLUMN_rlnReferenceImage, COLUMN_rlnClassDistribution, COLUMN_rlnEstimatedResolution)

    ## use the sorted data to publish the image based on user input
    images_as_array = get_mrcs_images(mrcs_file)
    output_extension = os.path.splitext(output_file_name)[1]
    im_array = create_image_array(array_dimensions, sorted_dataset, images_as_array, output_extension, padding)

    if ADD_SCALEBAR:
        box_size = images_as_array[0].shape[0]
        im_array = add_scalebar(im_array, box_size, angpix, scalebar_angstroms, scalebar_indent, scalebar_stroke)

    publish_image(im_array, output_file_name)

    print("=============================================================")
    print(" ... job completed.")
    print("=============================================================")
