#!/usr/bin/env python3

###############################
##  FLAGS
###############################
VERBOSE = False
###############################


###############################
##  FUNCTIONS
###############################
def usage():
    print("===================================================================================================")
    print(" For a given EPU Atlas directory with .JPG images, array the images into a full atlas for ")
    print(" visual inspection at higher resolution.")
    print(" Usage:")
    print("    $ array_EPU_atlas_jpgs.py  /path/to/atlas/")
    print("===================================================================================================")
    sys.exit()

def get_tile_files(directory):
    ## permit the user to use the simple '.' string to point to the current directory
    if directory == ".":
        directory = "./"

    file_list = []
    for file in glob.glob(directory + "*.jpg"):
        if 'Tile' in file:
            file_list.append(file)
    ## organize file list by alpha numeric
    file_list = sorted(file_list)

    print(" %s tile files found in directory (%s)" % (len(file_list), directory))
    return file_list

def prepare_canvas(tile_num, example_tile_file):
    """ For a given number of tiles, work out the dimensions of the canvas we need to prepare
    """
    ## read a single tile to get the image dimensions
    with PIL_Image.open(example_tile_file) as im:
        x = im.width
        y = im.height

    ## determine the canvas rows/columns
    cols = np.sqrt(tile_num)
    if cols == int(cols):
        cols = int(cols)
    elif cols < int(cols) + 0.5:
        cols = int(cols) + 1
    else:
        cols = int(cols) + 1

    rows = np.sqrt(tile_num)
    if rows == int(rows):
        rows = int(rows)
    elif rows > int(rows) + 0.5:
        rows = int(rows) + 1
    else:
        rows = int(rows)

    canvas = PIL_Image.new('L', (x * cols, y * rows))


    print(" Tile dimensions :: (x, y) -> (%s, %s) px" % (x, y))
    print(" Atlas dimensions :: %s x %s tiles -> (%s, %s) px" % (cols, rows, canvas.width, canvas.height))
    return canvas, cols, rows

def paste_tile_onto_canvas(tile_path, displacement_index, array_index, canvas_obj, OVERLAP):
    with PIL_Image.open(tile_path) as im:

        ## convert the array index to a pixel position
        x = array_index[0] * im.width
        y = array_index[1] * im.height

        # scale the pixel position by the expected overlap in the correct directions
        x = int(x - displacement_index[0] * im.width * OVERLAP)
        y = int(y - displacement_index[1] * im.height * OVERLAP)

        canvas_obj.paste(im, (x, y))
    return

def get_array_index_from_linear_index(cols, rows, index):
    """ Convert a linear index (e.g. 0, 1, 2, ..., n) to an array index in a serpentine fashion (e.g. tile index in EPU).
        EPU's first image is in the center, then it continues by going down and counter clockwise
    """
    ox = int(cols / 2) - 1
    oy = int(rows / 2) - 1
    origin = np.array([ox, oy])

    displacement = get_serpentine_displacement_index(index)
    array_index = origin + displacement

    if VERBOSE:
        print(" Placing tile # %s at index (col, row) -> (%s, %s)" % (index, array_index[0], array_index[1]))

    return displacement, array_index[0], array_index[1]

def get_serpentine_displacement_index(steps):
    """ For a given number of steps starting at the origin. Return the displacement index ([x, y] as np.array) of the final step.
            i.e. 1 step =  [ 0, -1] ... we start the serpentine shape going down in EPU
                 2 steps = [ 1, -1]
                 3 steps = [ 2, -1]
                 ...
    """
    displacement = np.array([0,0])

    L = np.array([-1, 0])
    R = np.array([1, 0])
    U = np.array([0, -1])
    D = np.array([0, 1])

    m = 0
    for i in range(steps + 1):
        if i == 0:
            # print( " add  NONE")
            m += 1
        else:
            n = 0
            axis = True
            while n < i * 2:
                # print( "n = ", n)
                if i % 2 == 0: ## even
                    if axis == True:
                        # print(" add ", U)
                        displacement = displacement + U
                    else:
                        # print(" add ", L)
                        displacement = displacement + L
                else: ## odd
                    if axis == True:
                        # print(" add ", D)
                        displacement = displacement + D
                    else:
                        # print(" add ", R)
                        displacement = displacement + R
                n += 1
                m += 1
                if m == steps + 1:
                    break

                ## switch the axis at the half way mark only
                if n == i:
                    axis = not axis

        if m == steps + 1:
            break
    # if VERBOSE:
    #     print(" Displacement index for step %s = %s" % (steps, displacement))
    return displacement


###############################


###############################
##  RUN BLOCK
###############################
if __name__ == '__main__':
    from PIL import Image as PIL_Image
    import numpy as np
    import glob
    import sys

    ## parse inputs
    cmdline = sys.argv
    if not len(cmdline) == 2:
        print(" ERROR :: Program takes one positional argument")
        usage()
    else:
        ## check for help flag with top priority
        for cmd in cmdline:
            if cmd in ['--h', '--help']:
                usage()
        ## grab $1 argument as the tentative path to the tile files
        path_to_jpgs = cmdline[1]

    OVERLAP = 0.06 # percent by which images are expected to overlap along the edges (0.06 = 6%)

    jpgs = get_tile_files(path_to_jpgs)
    canvas, cols, rows = prepare_canvas(len(jpgs), jpgs[0])

    for n in range(len(jpgs)):
        displacement_index, i, j = get_array_index_from_linear_index(cols, rows, n)
        paste_tile_onto_canvas(jpgs[n], displacement_index, (i,j), canvas, OVERLAP)

    canvas.show()
