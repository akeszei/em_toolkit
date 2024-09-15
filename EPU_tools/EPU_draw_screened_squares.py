#!/usr/bin/env python3

###############################
##  FLAGS
###############################
VERBOSE = True
###############################


def usage():
    print("===================================================================================================")
    print(" Run inside an EPU project directory (i.e. containing Images-Disc1 folder) while pointing to the ")
    print(" corresponding atlas directory (containing the correct Atlas...mrc and Tile...mrc files) to draw ")
    print(" an image of the atlas with the approximate position of each grid square that has signs of being ")
    print(" screened previously (i.e. contains the Data folder). Useful if transferring grid to another ")
    print(" microscope later to avoid double imaging on screened areas. ")
    print("  Usage:")
    print("     $ EPU_draw_screened_squares.py  /path/to/Atlas/Atlas_<x>.mrc")
    print(" -----------------------------------------------------------------------------------------------")
    print(" Options (default in brackets): ")
    print("       --bin (2) : binning factor for atlas")
    print("       --orientation (1) : what orientation to use for mapping coordinates")
    print("                              1 = default; 2 = flip x; 3 = flip y; 4 = flip x & y")
    print("===================================================================================================")
    sys.exit()

def parse_cmdline(cmdline):
    ## read all entries and check if the help flag is called at any point
    for cmd in cmdline:
        if cmd == '-h' or cmd == '--help' or cmd == '--h':
            usage()

    ## parse any flags 
    out_fname = 'atlas_annotated.jpg' # set default 
    binning = 2 # set default 
    orientation = 1 # set default 
    for i in range(len(cmdline)):
        if cmdline[i] == '--o':
            try:
                out_fname = cmdline[i+1]
                print(" Save output annotated atlas image: %s " % out_fname)
            except:
                print(" Could not parse --o entry or none given, using default: %s" % out_fname)
        if cmdline[i] == '--bin':
            try:
                binning = int(cmdline[i+1])
                print(" Atlas img binning factor: %s " % binning)
            except:
                print(" Could not parse --bin entry or none given, using default: %s" % binning)
        if cmdline[i] == '--orientation':
            try:
                orientation = int(cmdline[i+1])
                print(" Mapping orientation: %s " % orientation)
            except:
                print(" Could not parse --orientation entry or none given, using default: %s" % orientation)


    ## check for the .MRC file  
    atlas_mrc_path = None
    for i in range(len(cmdline)):
        if atlas_mrc_path == None:
            if os.path.splitext(cmdline[i])[1] in ['.mrc', '.MRC']:
                atlas_mrc_path = cmdline[i]
        elif os.path.splitext(cmdline[i])[1] in ['.mrc', '.MRC']:
            print(" WARNING :: More than one .MRC file was detected as input, only the first entry (%s) will be parsed " % atlas_mrc_path)
            
    if atlas_mrc_path == None:
        print(" ERROR :: No atlas .MRC file was detected as input!")
        usage()

    return atlas_mrc_path, out_fname, binning, orientation

def get_mrc_data(file):
    """ 
    PARAMETERS 
        file = path like string to .mrc file
    RETURNS
        np.ndarray of the mrc data using mrcfile module
    """
    try:
        with mrcfile.open(file) as mrc:
            ## get the raw image
            image_data = mrc.data.astype(np.float32) ## need to cast it as a float32, since some mrc formats are uint16! (i.e. mode 6)

            ## grab the pixel size from the header 
            pixel_size = np.around(mrc.voxel_size.item(0)[0], decimals = 2)
    except:
        print(" There was a problem opening .MRC file (%s), try permissive mode. Consider fixing this file later!" % file)
        with mrcfile.open(file, permissive = True) as mrc:
            ## get the raw image
            image_data = mrc.data.astype(np.float32) ## need to cast it as a float32, since some mrc formats are uint16! (i.e. mode 6)

            ## grab the pixel size from the header 
            pixel_size = np.around(mrc.voxel_size.item(0)[0], decimals = 2)

    return image_data, pixel_size

def apply_sigma_contrast(im_data, sigma_value):
    """
        Apply sigma contrast to an image.
    PARAMETERS
        im_data = 2d np.array
        sigma_value = float; typical values are 3 - 4
    RETURNS
        2d np.array, where values from original array are rescaled based on the sigma contrast value
    """
    ## 1. find the standard deviation of the data set
    im_stdev = np.std(im_data)
    ## 2. find the mean of the dataset
    im_mean = np.mean(im_data)
    ## 3. define the upper and lower limit of the image using a chosen sigma contrast value
    min = im_mean - (sigma_value * im_stdev)
    max = im_mean + (sigma_value * im_stdev)
    ## 4. clip the dataset to the min and max values
    im_contrast_adjusted = np.clip(im_data, min, max)

    return im_contrast_adjusted

def header_from_xml(input_string):
    """ By default convension, the names of XML headers for EPU files contains a lot of unnecessary
        information, this function aims to remove all that unnecessary text and return the header name
        alone. e.g.:
            {unnecessary text}headerTitle {} -> headerTitle
    """
    output_sting = input_string.split('{')[1].split('}')[1]
    return output_sting

def mrc2array(file, BINNING = 1, DEBUG = VERBOSE):
    """
        Import an image into a grayscale 2d numpy array with values from (0 - 255), where
            0 == black
            255 == white
    """
    im_raw, pixel_size = get_mrc_data(file) 

    ## apply sigma contrast to the image
    im_contrast_adjusted = apply_sigma_contrast(im_raw, 6)

    ## rescale the image data to grayscale range (0,255)
    im_data = (255*(im_contrast_adjusted - np.min(im_contrast_adjusted))/np.ptp(im_contrast_adjusted)).astype(np.uint8) ## remap data from 0 -- 255

    ## use PIL_Image module resize function to apply binning to the image array 
    if BINNING > 1:
        im_data = np.asarray(PIL_Image.fromarray(im_data).reduce(BINNING))

    if DEBUG:
        print(" mrc2array :: %s" % file)
        print("------------------------------------")
        print("   >> %s px, min = %s, max = %s" % (im_data.shape, np.min(im_data), np.max(im_data)))
        print("   >> pixel size = %s" % pixel_size)
        print("====================================")

    return im_data

def get_tile_files(directory, atlas_id = 1):
    """
    PARAMETERS 
        directory = str() defining the location of the expected Tile...xml files 
        atlas_id = str() defining the atlas to which the tiles are related (denoted by filename: 'Atlas_<atlas_id>.mrc')
    RETURNS 
        file_list = list() of filenames for each Tile...xml file in their defined order taken by EPU 
    """
    tile_glob_str = os.path.join(directory, "Tile*" + str(atlas_id) + ".xml")
    if VERBOSE:
        print(" get_tile_files :: ")
        print("------------------------------------")
        print("  search directory = %s" % directory)
        print("  atlas_id string = %s" % atlas_id)
        print("  tile glob string = %s" % tile_glob_str)


    file_list = []
    for file in glob.glob(tile_glob_str):
        if 'Tile' in file:
            file_list.append(file)
    ## organize file list by alpha numeric
    file_list = sorted(file_list)

    if not len(file_list) > 0:
        print(" ERROR :: Could not find Tile_..._%s.xml files! Check given atlas directory for Tile and proper atlas id: %s" % (atlas_id, directory)) 
        usage()

    if VERBOSE: 
        print("------------------------------------")
        print("  # tile files found: ", len(file_list))
        print("       %s" % file_list[0])
        print("       %s" % file_list[1])
        print("        ...")
        print("       %s" % file_list[-1])
        print("====================================")

    return file_list

def get_tile_coords(file_list):
    tile_coordinates = []
    for xml_file in file_list:
        tile_coordinates.append(point_from_xml(xml_file))

    # if VERBOSE:
    #     print(" >> %s atlas tiles parsed" % len(tile_coordinates))
    return tile_coordinates

def as_unit_vector(input_vector):
    """ For an input vector sitting at the origin, normalize its magnitude to make it a unit vector in the range of 0 through 1.
    PARAMETERS
        input_vector = np.array([x, y])
    RETURNS
        output_vector = np.array([a, b]) whose norm == 1
    """
    output_vector = input_vector / np.linalg.norm(input_vector)
    return output_vector

def point_to_relative_basis_lengths(point, basis_vectors):
    """ For a given point sitting on a plane defined by two basis vectors of fixed length, determine how many basis-lengths along each basis
        direction the point lies. The output fold differences can be used to scale the point along a new set of basis vectors later.
    PARAMETERS
        point = np.array([x, y]), where (x, y) define a point sitting on a plane
        basis_vectors = tuple(np.array([x1, y1]), np.array([x2, y2])), where (x1, y1) and (x2, y2) define two basis vectors sitting at a common origin of (0, 0)
    RETURNS
    """
    ## 1. normalize the basis vectors so they range from 0 to 1 (effectively making them abitrarily larger than any point we might consider, and hence not limiting in a dot product calculation)
    x_unit = as_unit_vector(basis_vectors[0])
    y_unit = as_unit_vector(basis_vectors[1])
    # print(" unit vectors for x, y = %s, %s" % (x_unit_real, y_unit_real))
    ## 2. calculate the inner (i.e. dot) product of the POI along each axis defined by the basis vectors
    inner_product_x = np.inner(point, x_unit)
    inner_product_y = np.inner(point, y_unit)
    # print("inner products along x, y = %s, %s" % (inner_product_x, inner_product_y))
    ## 3. determine the fold difference of the POI inner products against the magnitude of each basis vector along that axis (since the position of each basis vector is known relative to the final image, we can use this fold difference to rescale the image basis vectors correctly)
    fold_difference_point2basis_x = inner_product_x / np.linalg.norm(basis_vectors[0])
    fold_difference_point2basis_y = inner_product_y / np.linalg.norm(basis_vectors[1])
    # if VERBOSE:
    #     print(" percent position of point to basis vectors = %s, %s " % (fold_difference_point2basis_x, fold_difference_point2basis_y))

    return (fold_difference_point2basis_x, fold_difference_point2basis_y)

def point_from_xml(fname):
    """ For an input EPU .XML file, find the X and Y coordinates of the stage embedded within
    PARAMETERS
        fname = str(), name of the file
    RETURNS
        coords = tuple(x, y), where x, y correspond to the entries at <X> and <Y> for the stage position
    """
    ## load the file into xml data structure
    xml_data = ET.fromstring(open(fname).read())

    x, y = (None, None)
    for entry in xml_data:
        # print("PARENT ENTRIES")
        # print(header_from_xml(entry.tag))
        if 'microscopeData' == header_from_xml(entry.tag):
            # print("MICROSCOPE DATA")
            for subentry in entry:
                # print(header_from_xml(subentry.tag))
                if 'stage' == header_from_xml(subentry.tag):
                    # print("STAGE DATA")
                    for subsubentry in subentry:
                        # print(subsubentry.tag, subsubentry.attrib)
                        if 'Position' == header_from_xml(subsubentry.tag):
                            # print("POSITION DATA")
                            for subsubsubentry in subsubentry:
                                # print(subsubsubentry.tag, subsubsubentry.attrib)
                                if 'X' == header_from_xml(subsubsubentry.tag):
                                    x = float(subsubsubentry.text)
                                    # print("X = ", x)
                                if 'Y' in header_from_xml(subsubsubentry.tag):
                                    y = float(subsubsubentry.text)
                                    # print("Y = ", y)
    coords = (x, y)
    return coords

def find_scaling_factor(tile_num, DEBUG = VERBOSE):
    """ For a given number of tiles composing the EPU atlas, determine the number of basis vector lengths span from the center of the image to an edge.
    PARAMETERS
        tile_num = int(), number of tiles of which the atlas is composed
    RETURNS
        scaling_factor = float()
    """

    if DEBUG:
        print(" find_scaling_factor :: ")
        print("------------------------------------")
        print("  # tiles in atlas = %s" % tile_num)

    ## the number of tiles making up an atlas can give you the expected basis lengths using a simple algorithm
    x = np.sqrt(tile_num) / 2

    if x == int(x):
        pass 
    elif x <= int(x) + 0.5:
        x = int(x) + 0.5
    elif x > int(x) + 0.5:
        x = int(x) + 1
    else:
        return print("ERROR :: Unexpected number of tiles for atlas (%s)!" % tile_num)

    if DEBUG: 
        print("  # tile lengths from center of atlas to one edge = %s" % str(x))
        print("====================================")

    return x 

def prepare_matplotlib_canvas(im):
    left = 0 - int(im.shape[0] / 2)
    right = int(im.shape[0] / 2)
    bottom = 0 - int(im.shape[0] / 2)
    top = int(im.shape[0] / 2)
    plt.imshow(im, cmap = 'gray', extent=[left, right, bottom, top])
    # plt.show()
    return left, right, bottom, top 

def get_basis_vector_details(tile_coordinates, left, right, top, bottom, ORIENTATION = 1):
    ## determine the basis vectors for real space by using the first three stage positions (positions 0, 3, 5), which define the corner of a rectangle in the correct orientation:
    ##     4 -- 3 -- 2
    ##     |         |
    ##     5    0 -- 1
    ##     |
    ##     6 -- 7 

    ## choose which tiles define the x and y basis vectors in real space
    ## glacios == 1 
    if ORIENTATION == 1:
        x_tile_basis = 1
        y_tile_basis = 3
    elif ORIENTATION == 2: # flip x 
        x_tile_basis = 5
        y_tile_basis = 3
    elif ORIENTATION == 3: # flip y 
        x_tile_basis = 1
        y_tile_basis = 7
    elif ORIENTATION == 4: # flip x and y
        x_tile_basis = 5
        y_tile_basis = 7 


    x_basis_real = np.array(tile_coordinates[x_tile_basis]) - np.array(tile_coordinates[0])
    y_basis_real = np.array(tile_coordinates[y_tile_basis]) - np.array(tile_coordinates[0])

    realspace_basis = (x_basis_real, y_basis_real)

    ## set up basis vectors for image space, their magnitude should be directly related to the manitude of the realspace_basis vectors
    scaling_factor = find_scaling_factor(len(tile_coordinates))
    x_basis_im = np.array([1, 0]) * int(right / scaling_factor)
    y_basis_im = np.array([0, 1]) * int(top / scaling_factor)

    return realspace_basis, x_basis_im, y_basis_im

def get_gridsquare_xmls(DEBUG = VERBOSE):
    skipped = 0
    ## check for Images-Disc1 folder in working directory and get all GridSquare folders 
    if 'Images-Disc1' in os.listdir():
        ## find all GridSquare_* folders 
        gridsquare_folders = []
        for f in os.listdir('Images-Disc1'):
            if 'GridSquare' in f:
                gridsquare_folders.append(f)

        if len(gridsquare_folders) < 1:
            print(" No GridSquare_* folders found in Images-Disc1/ subfolder")
            return 
        
    ## iterate over all GridSquare folders checking if there is a Data/ folder before grabbing the first instance of the GridSquare*xml file
    gridsquare_xmls = []
    for g in gridsquare_folders:
        gridsquare_path = os.path.join('Images-Disc1', g)
        if 'Data' in os.listdir(gridsquare_path):
            xmls = glob.glob(os.path.join(gridsquare_path, 'GridSquare_*xml'))
            gridsquare_xmls.append(xmls[0])
        else:
            skipped += 1

    if DEBUG: 
        print(" get_gridsquare_xmls :: ")
        print("------------------------------------")
        print("  gridsquares found = %s" % len(gridsquare_folders))
        if skipped > 0:
            print("  ... %s skipped (i.e. missing Data/ sub-folder)" % skipped)
        print("====================================")
   

    return gridsquare_xmls

if __name__ == '__main__':
    from PIL import Image as PIL_Image
    import numpy as np
    import xml.etree.ElementTree as ET
    import glob
    import os, sys 
    import matplotlib.pyplot as plt
    import mrcfile

    ## get commandline inputs 
    atlas_mrc_path, out_fname, binning, orientation = parse_cmdline(sys.argv)
    atlas_directory = os.path.split(atlas_mrc_path)[0]
    atlas_mrc_fname = os.path.split(atlas_mrc_path)[1]
    atlas_id = os.path.splitext(atlas_mrc_fname)[0].split("_")[-1]

    print("------------------------------------")
    print(" parse inputs ::")
    print("------------------------------------")
    print("  atlas_directory = %s" % atlas_directory)
    print("  altas_mrc_fname = %s" % atlas_mrc_fname)
    print("  atlas id = %s" % atlas_id)
    print("====================================")

    ## prepare the image array from the mrc to work from with 2x binning 
    im_atlas = mrc2array(atlas_mrc_path, BINNING = binning)

    ## move the image so the origin (0, 0) is at the center and place it on a matplotlib canvas 
    ## see: https://stackoverflow.com/questions/34458251/plot-over-an-image-background-in-python
    left, right, bottom, top = prepare_matplotlib_canvas(im_atlas)

    ## get all .xml files corresponding to Tiles in the atlas
    tile_files = get_tile_files(atlas_directory, atlas_id = atlas_id)

    ## pass each xml file through a parser and get the cached X and Y coordinates
    tile_coordinates = get_tile_coords(tile_files)

    ## determine the basis vectors from real space stage positions
    realspace_basis, x_basis_im, y_basis_im = get_basis_vector_details(tile_coordinates, left, right, top, bottom, ORIENTATION = orientation)

    ## For debugging, plot all grid squares found in the target directory onto the atlas 
    gridsquare_xmls = get_gridsquare_xmls()

    for xml in gridsquare_xmls:

        poi_real = np.array(point_from_xml(xml))
    
        ## determine for the given point, how much it lies on each axis defined by basis vectors of a fixed (known) length:
        relative_x, relative_y = point_to_relative_basis_lengths(poi_real, realspace_basis)
    
        ## multiply the image-space basis vectors by the determined scaling factor to find the target pixel position of the input point
        img_pixel_position = (x_basis_im[0] * relative_x, y_basis_im[1] * relative_y)
    
        ## draw a red cicle of arbitrary size centered at the target pixel position
        plt.plot(img_pixel_position[0], img_pixel_position[1], 'o', markersize = 10, markerfacecolor="None", markeredgecolor = 'tab:red', markeredgewidth=2)


    # # For debugging, print the coordinate of each tile for the atlas 
    # for coord in tile_coordinates:
    #     poi_real = coord
    
    #     ## determine for the given point, how much it lies on each axis defined by basis vectors of a fixed (known) length:
    #     relative_x, relative_y = point_to_relative_basis_lengths(poi_real, realspace_basis)
    
    #     ## multiply the image-space basis vectors by the determined scaling factor to find the target pixel position of the input point
    #     img_pixel_position = (x_basis_im[0] * relative_x, y_basis_im[1] * relative_y)
    
    #     ## draw a red cicle of arbitrary size centered at the target pixel position
    #     plt.plot(img_pixel_position[0], img_pixel_position[1], 'o', markersize = 10, markerfacecolor="None", markeredgecolor = 'yellow', markeredgewidth=2)

    ## save the image
    plt.axis('off')
    plt.show()
    plt.savefig(out_fname, format="jpg", bbox_inches='tight', dpi = 350, pad_inches=0)
