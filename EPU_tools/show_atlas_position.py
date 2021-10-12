def usage():
    print("===================================================================================================")
    print(" For a given EPU Atlas directory, atlas .JPG file, and .XML file for a position of interest")
    print(" (containing stage position <X> and <Y> coordinates), print an image of the atlas with the ")
    print(" stage position indicated by a red circle. Useful for following up after screening.")
    print(" Usage:")
    print("    $ show_atlas_position.py  /path/to/Atlas  atlas.jpg  position_metadata.xml  output_name.jpg")
    print("===================================================================================================")
    sys.exit()

def header_from_xml(input_string):
    """ By default convension, the names of XML headers for EPU files contains a lot of unnecessary
        information, this function aims to remove all that unnecessary text and return the header name
        alone. e.g.:
            {unnecessary text}headerTitle {} -> headerTitle
    """
    output_sting = input_string.split('{')[1].split('}')[1]
    return output_sting

def image2array(file, DEBUG = True):
    """
        Import an image into a grayscal 2d numpy array with values from (0 - 255), where
            0 == black
            255 == white
    """
    im = PIL_Image.open(file).convert('L') # 'L' == convert to grayscale data
    # convert image to numpy array
    im_data = np.asarray(im)

    if DEBUG:
        print("===================================================")
        print(" IMPORT IMAGE :: %s" % file)
        print("===================================================")
        print("   >> %s px, min = %s, max = %s" % (im_data.shape, np.min(im_data), np.max(im_data)))

    return im_data

def get_tile_files(directory):
    file_list = []
    for file in glob.glob(directory + "*.xml"):
        if 'Tile' in file:
            file_list.append(file)
    ## organize file list by alpha numeric
    file_list = sorted(file_list)
    return file_list

def get_tile_coords(file_list):
    tile_coordinates = []
    for xml_file in file_list:
        tile_coordinates.append(point_from_xml(xml_file))

    print(" >> %s atlas tiles parsed" % len(tile_coordinates))
    return tile_coordinates

def plot_points(coordinates):
    """ For a given set of coordinates, add points to an open 'matplotlib.pyplot as plt' canvas
    PARAMETERS
        coordinates = [(x1, y1), (x2, y2), ... (xn, yn)]
    RETURNS
        void
    """
    ## unzip the data and generate two independent lists for each x and y coordinate
    xs, ys = zip(*coordinates)
    xs = list(xs)
    ys = list(ys)
    ## pass the unzipped values into the scatter function
    plt.scatter(xs, ys, s = 15, color = 'gray', alpha = 0.5)
    return

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
    print(" percent position of point to basis vectors = %s, %s " % (fold_difference_point2basis_x, fold_difference_point2basis_y))

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

def find_scaling_factor(tile_num):
    """ For a given number of tiles composing the EPU atlas, determine the number of basis vector lengths span from the center of the image to an edge.
    PARAMETERS
        tile_num = int(), number of tiles of which the atlas is composed
    RETURNS
        scaling_factor = float()
    """
    if tile_num <= 9:
        return 1.5
    elif tile_num <= 25:
        return 2.5
    elif tile_num <= 49:
        return 3.5
    elif tile_num <= 81:
        return 4.5
    elif tile_num <= 121:
        return 5.5
    elif tile_num <= 169:
        return 6.5
    else:
        return print("ERROR :: Unexpected number of tiles for atlas (%s)!" % tile_num)

if __name__ == '__main__':
    from PIL import Image as PIL_Image
    import numpy as np
    import xml.etree.ElementTree as ET
    import glob
    import sys # for sys.exit() calls while building script
    import matplotlib.pyplot as plt

    cmd_line = sys.argv
    if len(cmd_line) != 5:
        usage()

    # show_atlas_position.py  /path/to/Atlas  atlas.jpg  position_metadata.xml")
    atlas_directory = sys.argv[1]
    atlas_jpg = sys.argv[2]
    input_xml = sys.argv[3]
    output_fname = sys.argv[4]

    print("==================================================")
    print(" show_atlas_position.py ")
    print("--------------------------------------------------")
    print("  atlas_directory = %s " % atlas_directory)
    print("  atlas_jpg = %s " % atlas_jpg)
    print("  input_xml = %s" % input_xml)
    print("  output_fname = %s " % output_fname)
    print("==================================================")

    ## get all .xml files corresponding to Tiles in the atlas
    tile_files = get_tile_files(atlas_directory)

    ## pass each xml file through a parser and get the cached X and Y coordinates
    tile_coordinates = get_tile_coords(tile_files)

    ## for visualization, plot tile coordinates
    # plot_points(tile_coordinates)

    ## get the point of interest in real space (the values found in the EPU .XML file)
    poi_real = np.array(point_from_xml(input_xml))

    ## for visualization, plot the position of the real POI
    # plt.scatter(poi_real[0], poi_real[1], s = 30, color = 'red', alpha = 1)

    ## determine the basis vectors for real space
    real_origin = np.array(tile_coordinates[0])

    ## after trial-and-error, I have determined that EPU atlases can be aligned with real space coordinates by using Tile 3 and 5 as basis vectors representing a fixed step in the positive x and y directions, respectively
    x_basis_real = np.array(tile_coordinates[3]) - real_origin
    y_basis_real = np.array(tile_coordinates[5]) - real_origin
    realspace_basis = (x_basis_real, y_basis_real)

    ## for visualization, plot these basis vectors
    # plt.plot([real_origin[0], x_basis_real[0]], [real_origin[1], x_basis_real[1]], color='blue', alpha = 0.5)
    # plt.plot([real_origin[0], y_basis_real[0]], [real_origin[1], y_basis_real[1]], color='blue', alpha = 0.5)
    # print("Basis vectors = %s, %s)" % (x_basis_real, y_basis_real))

    ## determine for the given point, how much it lies on each axis defined by basis vectors of a fixed (known) length:
    relative_x, relative_y = point_to_relative_basis_lengths(poi_real, realspace_basis)

    ## load the atlas image
    im_atlas = image2array(atlas_jpg, DEBUG = False)
    print(" image dimensions = ", im_atlas.shape)

    ## move the image so the origin (0, 0) is at the center
    ## see: https://stackoverflow.com/questions/34458251/plot-over-an-image-background-in-python
    left = 0 - int(im_atlas.shape[0] / 2)
    right = int(im_atlas.shape[0] / 2)
    bottom = 0 - int(im_atlas.shape[0] / 2)
    top = int(im_atlas.shape[0] / 2)
    plt.imshow(im_atlas, cmap = 'gray', extent=[left, right, bottom, top])

    ## set up basis vectors for image space, their magnitude should be directly related to the manitude of the realspace_basis vectors
    scaling_factor = find_scaling_factor(len(tile_coordinates))
    x_basis_im = np.array([1, 0]) * int(right / scaling_factor)
    y_basis_im = np.array([0, 1]) * int(top / scaling_factor)
    # plt.plot([0, x_basis_im[0]], [0, x_basis_im[1]], color='green', alpha = 0.5)
    # plt.plot([0, y_basis_im[0]], [0, y_basis_im[1]], color='orange', alpha = 0.5)
    print(" img basis vectors = %s, %s" % (x_basis_im, y_basis_im))


    ## multiply the image-space basis vectors by the determined scaling factor to find the target pixel position of the input point
    img_pixel_position = (x_basis_im[0] * relative_x, y_basis_im[1] * relative_y)
    print( " position of remapped pixel coordinate = ", img_pixel_position)

    ## draw a red cicle of arbitrary size centered at the target pixel position
    plt.plot(img_pixel_position[0], img_pixel_position[1], 'o', markersize = 20, markerfacecolor="None", markeredgecolor = 'tab:red', markeredgewidth=2)

    ## save the image
    plt.axis('off')
    plt.savefig(output_fname, format="jpg", bbox_inches='tight', dpi = 350, pad_inches=0)
