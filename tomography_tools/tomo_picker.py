#!/usr/bin/env python3

## Author: Alexander Keszei
## 2022-05-09: Version 1 adapted from mrc_viewer.py to take in large raw tomo stack files 
## 2026-10-24: Version 2 updated to image full tomogram stacks and pick 3d coordinates for sub-tomogram averaging 
"""
To Do:
    - Clean up unused functions
    - Make Ctrl + S save the picked coordinates to load again later (allow for more than one feature per img?)
    - Center-of-mass snapping on pick?? Might be interesting to have a function try to center the pick? Can add a toggle to enable/disable
    - Add option to go to specific slice
    - Add an on-load option to continue where I left off? 
    - Add an options menu during saving to set the tomostar string?
    - Autopicker window, make Gaussian disk ahve option for disk diameter (A) and window size (A) instead of reading the particle pick value for the display window
    - 'Template loaded:' -> add some update text [x, y] px, [a, b] Ang size so the user knows the dimensions when they are updated! 
""" 



import tkinter as tk
from tkinter.filedialog import askopenfilename
from tkinter.filedialog import asksaveasfilename
from tkinter.messagebox import showerror
from tkinter import ttk
import numpy as np
import os, sys, copy
from multiprocessing import Process, Pool
import time
try:
    from PIL import Image as PIL_Image
    from PIL import ImageTk
except:
    print("Problem importing PIL, try installing Pillow via:")
    print("   $ pip install --upgrade Pillow")

import mrcfile
import starfile
import pandas as pd
try:
    import cv2 ## for resizing images with a scaling factor
except:
    print("Could not import cv2, try installing OpenCV via:")
    print("   $ pip install opencv-python")


#region Utils
def parse_cmdline(cmds):
    ## check for help flag 
    for cmd in cmds:
        if cmd in ['-h', '--h', '--help', '-help']:
            print(" Help flag called: %s" % cmd)
            usage()
            sys.exit()

    ## set up return variable defaults  
    scale = 0.2 
    lowpass = -1
    sigma = 3
    input_file = None
    threads = 6
    coord_file = None

    ## parse through the commandline entries for specific flags 
    for i in range(len(cmds)):
        cmd = cmds[i]

        ## check for input .MRCS or .MRC file 
        if cmd[-5:].lower() == '.mrcs' or cmd[-4:].lower() == '.mrc':
            print(" Input file detected: %s" % cmd)
            input_file = cmd

        if cmd == '--scale':
            scale = cast_flag_input_to_type(cmds, i, float())

        if cmd == '--lowpass':
            lowpass = cast_flag_input_to_type(cmds, i, int())

        if cmd == '--sigma':
            sigma = cast_flag_input_to_type(cmds, i, float())

        if cmd == '--threads' or cmd == '--j':
            threads = cast_flag_input_to_type(cmds, i, int())

        if cmd == '--star':
            coord_file = cast_flag_input_to_type(cmds, i, str())


    ## sanity check necessary inputs are populated 
    if input_file == None:
        print(" No input .MRC/.MRCS file was given!")
        usage()
        sys.exit()

    return scale, lowpass, sigma, input_file, threads, coord_file

def cast_flag_input_to_type(cmdline, flag_index, dtype):
    """
    PARAMETERS 
        cmdline = the list of commands given by sys.argv
        flag_index = the index of the flag in question 
        dtype = an example of the type we wish to cast to (e.g. float(), 0.25, bool, ...)
    RETURNS 
        user_input_as_type = the input casted to the given dtype
        ... otherwise will crash with useful output to the user 
    """
    ## set up the return variable 
    user_input_as_type = None 
    ## ensure there is an input given for the flag at the subsequent index 
    if len(cmdline) > flag_index + 1:
        ## if there is room for an input, try casting it to the correct type by checking the dtype given 

        ## Float type
        if isinstance(dtype, float):
            try:
                user_input_as_type = float(cmdline[flag_index + 1])
                print(" %s flag detected: %s" % (cmdline[flag_index], cmdline[flag_index + 1]))
            except:
                print(" %s flag was given an unexpected input: %s" % (cmdline[flag_index], cmdline[flag_index + 1]))
                sys.exit()

        ## Int type
        if isinstance(dtype, int):
            try:
                user_input_as_type = int(cmdline[flag_index + 1])
                print(" %s flag detected: %s" % (cmdline[flag_index], cmdline[flag_index + 1]))
            except:
                print(" %s flag was given an unexpected input: %s" % (cmdline[flag_index], cmdline[flag_index + 1]))
                sys.exit()

        ## String type
        if isinstance(dtype, str):
            try:
                user_input_as_type = str(cmdline[flag_index + 1])
                print(" %s flag detected: %s" % (cmdline[flag_index], cmdline[flag_index + 1]))
            except:
                print(" %s flag was given an unexpected input: %s" % (cmdline[flag_index], cmdline[flag_index + 1]))
                sys.exit()

        ## Bool type
        if isinstance(dtype, bool):
            try:
                user_input_as_type = bool(cmdline[flag_index + 1])
                print(" %s flag detected: %s" % (cmdline[flag_index], cmdline[flag_index + 1]))
            except:
                print(" %s flag was given an unexpected input: %s" % (cmdline[flag_index], cmdline[flag_index + 1]))
                sys.exit()
    else:
        print(" %s flag was given with no input!" % cmdline[flag_index])
        sys.exit()

    return user_input_as_type

def process_single_image(input_array, scale_factor, pixel_size, lowpass_threshold, sigma):
    """
    PARAMETERS
        im_array = raw data of image as an nparray 
    RETURNS
        im_obj = PhotoImage object useable for display on Tk 
    """
    ## it is much faster if we scale down the image prior to doing filtering
    img_scaled = resize_image(input_array, scale_factor)
    grayscale_img_array = mrc2grayscale(img_scaled, pixel_size / scale_factor, lowpass_threshold)
    img_contrasted = sigma_contrast(grayscale_img_array, sigma)  
    # im_obj = get_PhotoImage_obj(img_contrasted)

    return img_contrasted

def convert_to_linux_newlines(file_path: str) -> None:
    """
    Generated by Gemini.
    Opens a text file, reads it into memory, and overwrites it 
    ensuring it uses strict Linux (LF) line endings.
    """
    # 1. Read the file into memory 
    # (Python's universal newline mode converts \r\n to \n automatically)
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 2. Write the data back out with strict Linux line endings
    with open(file_path, 'w', newline='\n', encoding='utf-8') as f:
        f.write(content)

    return 

def usage():
    print("================================================================================================")
    # print(" Open a stack of MRC/MRCS images and load their processed images into buffer. Use left/right ")
    # print(" up/down arrows to navigate through the stack. You can click on particles of interest and ")
    # print(" use Ctrl + e to extract them into a new .MRCS file useable by downstream programs:")
    print("    $ tomo_picker.py  <input>.mrcs")
    print("------------------------------------------------------------------------------------------------")
    print(" Can set options on loadup to bypass defaults: ")
    print("           --scale (0.2) : rescale displayed frame images by a value in range (0,inf)")
    print("          --lowpass (-1) : apply a lowpass filter; -1 turns off filtering (faster)")
    print("             --sigma (3) : set sigma filter contrast ")
    print("      --threads, --j (8) : set number of cores to use (1 = no parallelization) ")
    print("               --star () : give an input .star file with coordinates to load on startup")
    print("------------------------------------------------------------------------------------------------")
    print(" Keyboard shortcuts: ")
    print("   Arrow keys | z,x : Move through z stack")
    print("           Ctrl + x : Open autopick panel")
    print("           Ctrl + z : Open settings panel")
    print("           Ctrl + s : Prompt save coordinates file")
    # print("    Ctrl + e : Save out a '..._extracted.mrcs' file with picked coordinates across the stack")
    print("           Ctrl + q : Quit program")
    print("================================================================================================")
    return 

def sigma_contrast(im_array, sigma, DEBUG = False):
    """ Rescale the image intensity levels to a range defined by a sigma value (the # of
        standard deviations to keep). Can perform better than auto_contrast when there is
        a lot of dark pixels throwing off the level balancing.
    """
    import numpy as np
    stdev = np.std(im_array)
    mean = np.mean(im_array)
    minval = mean - (stdev * sigma)
    maxval = mean + (stdev * sigma)

    if minval < 0: 
        minval = 0
    if maxval > 255:
        maxval = 255

    if DEBUG:
        print("  >> Apply sigma_contrast: %s" % sigma)

    ## remove pixels above/below the defined limits
    im_array = np.clip(im_array, minval, maxval)
    ## rescale the image into the range 0 - 255
    im_array = ((im_array - minval) / (maxval - minval)) * 255

    return im_array.astype('uint8')

def lowpass(img, threshold, pixel_size, DEBUG = False):
    """ An example of a fast implementation of a lowpass filter (not used here)
        ref: https://wsthub.medium.com/python-computer-vision-tutorials-image-fourier-transform-part-3-e65d10be4492
    """

    ## create circle mask at a resolution given by the threshold and pixel size
    radius = int(img.shape[0] * pixel_size / threshold)
    if DEBUG: print("  >> Lowpass image: %s Ang " % (threshold))
    mask = np.zeros_like(img)
    cy = mask.shape[0] // 2
    cx = mask.shape[1] // 2
    cv2.circle(mask, (cx,cy), radius, (255,255), -1)[0]
    ## blur the mask
    lowpass_mask = cv2.GaussianBlur(mask, (19,19), 0)

    f = cv2.dft(img.astype(np.float32), flags=cv2.DFT_COMPLEX_OUTPUT)
    f_shifted = np.fft.fftshift(f)
    f_complex = f_shifted[:,:,0]*1j + f_shifted[:,:,1]
    f_filtered = lowpass_mask * f_complex
    f_filtered_shifted = np.fft.fftshift(f_filtered)
    inv_img = np.fft.ifft2(f_filtered_shifted) # inverse F.T.
    filtered_img = np.abs(inv_img)
    filtered_img -= filtered_img.min()
    filtered_img = filtered_img*255 / filtered_img.max()
    filtered_img = filtered_img.astype(np.uint8)

    ## to view the fft we need to play with the results
    f_abs = np.abs(f_complex)
    f_bounded = 20 * np.log(f_abs) # we take the logarithm of the absolute value of f_complex, because f_abs has tremendously wide range.
    f_img = 255 * f_bounded / np.max(f_bounded) ## convert data to grayscale based on the new range
    f_img = f_img.astype(np.uint8)
    return filtered_img, f_img

def get_mrc_files_in_dir(path):
    files_in_dir = os.listdir(path)
    images = []
    for file in files_in_dir:
        extension = file[-4:]
        if extension.lower() in [".mrc"]:
            images.append(os.path.join(path, file))
    return sorted(images)

def get_fixed_array_index(current_object_number, maximum_number_of_columns):
    """ For a given fixed array width (column max) and object number, return its corresponding array index
    """
    row = int(current_object_number / maximum_number_of_columns)
    col = current_object_number % maximum_number_of_columns
    # print(" get_fixed_array_index -> (%s, %s)" % (row, col))
    return row, col

def get_PhotoImage_obj(img_nparray):
    """ Convert an input numpy array grayscale image and return an ImageTk.PhotoImage object
    """
    PIL_img = PIL_Image.fromarray(img_nparray.astype(np.uint8))  #.convert('L')

    img_obj = ImageTk.PhotoImage(PIL_img)
    return img_obj

def get_mrc_raw_data(file, DEBUG = True):
    """ file = .mrc file
        returns np.ndarray of the mrc data using mrcfile module
    """
    ## NOTE atm works for mrc mode 2 but not mode 6
    with mrcfile.open(file) as mrc:
        image_data = mrc.data.astype(np.float32) ## need to cast it as a float32, since some mrc formats are uint16! (i.e. mode 6)

        # pixel_size = np.around(mrc.voxel_size.item(0)[0], decimals = 2)
        pixel_size = np.around(mrc.voxel_size['x'], decimals = 2)

        ## deal with single frame mrcs files as special case
        if len(mrc.data.shape) == 2:
            y_dim, x_dim = mrc.data.shape[0], mrc.data.shape[1]
            z_dim = 1
        else:
            ## X axis is always the last in shape (see: https://mrcfile.readthedocs.io/en/latest/usage_guide.html)
            y_dim, x_dim, z_dim = mrc.data.shape[1], mrc.data.shape[2], mrc.data.shape[0]

        # ## Read the dtype of the image array 
        # dtype = mrc.data.dtype

    ## set defaults 
    if pixel_size == 0:
        print(" ... pixel size of 0 read from header, setting manually 1")        
        pixel_size = 1.0

    if DEBUG:
        print("   >> image dimensions (x, y, z) = (%s, %s, %s)" % (x_dim, y_dim, z_dim))
        print("   >> pixel size = %s Ang/px" % pixel_size)

    return image_data, pixel_size, x_dim, y_dim, z_dim

def mrc2grayscale(mrc_raw_data, pixel_size, lowpass_threshold):
    """ Convert raw mrc data into a grayscale numpy array suitable for display
    """
    # print(" min, max = %s, %s" % (np.min(mrc_raw_data), np.max(mrc_raw_data)))
    ## remap the mrc data to grayscale range
    remapped = (255*(mrc_raw_data - np.min(mrc_raw_data))/np.ptp(mrc_raw_data)).astype(np.uint8) ## remap data from 0 -- 255 as integers

    if lowpass_threshold > 0:
        lowpassed, ctf = lowpass(remapped, lowpass_threshold, pixel_size) # ~0.7 sec
        return lowpassed

    return remapped  #, ctf

def coord2freq(x, y, fft_width, fft_height, angpix, DEBUG = False):
    """ For a given coordinate in an FFT image, return the frequency spacing corresponding to that position (i.e. resolution ring)
    PARAMETERS
        x = int(), x-axis pixel position in centered FFT
        y = int(), y-axis pixel position in centered FFT
        fft_width = int(), magnitude (in pixels) of x-axis
        fft_height = int(), magnitude (in pixels) of y-axis
        angpix = float(), resolution corresponding to real space image
    RETURNS
        frequency = float(), resolution (in Angstroms) corresponding to that pixel position
        difference_vector_magnitude = float(), the length of the ring corresponding to that frequency spacing (mainly needed for drawing)
    """
    ## calculate the angular distance of the picked coordinate from the center of the image
    FFT_image_center_coordinate = ( int(fft_width / 2), int(fft_height / 2))
    difference_vector = tuple(b - a for a, b in zip( (x, y), FFT_image_center_coordinate))
    difference_vector_magnitude = np.linalg.norm(difference_vector)
    ## convert the magnitude value into frequency value in units angstroms
    frequency = ( 1 / ( difference_vector_magnitude / fft_width ) ) * angpix

    if DEBUG:
        print(" ==============================================================================")
        print(" coord2freq :: inputs:")
        print("   pixel position = (%s, %s)" % (x, y))
        print("   im dimensions = (%s, %s)" % (fft_width, fft_height))
        print("   im angpix = %.2f" % angpix)
        print("  >> FFT image center coordinate = (%s, %s)" % FFT_image_center_coordinate)
        print(" >> Vector magnitude in pixels = ", difference_vector_magnitude)
        print(" >> Frequency of radial pixel position = " + "{:.2f}".format(frequency) + " Ang")
        print(" ==============================================================================")
    return frequency, difference_vector_magnitude

def resize_image(img_nparray, scaling_factor, DEBUG = False):
    """ Uses OpenCV to resize an input grayscale image (0-255, 2d array) based on a given scaling factor
            scaling_factor = float()
    """
    # original_width = img_nparray.shape[1]
    # original_height = img_nparray.shape[0]
    scaled_width = int(img_nparray.shape[1] * scaling_factor)
    scaled_height = int(img_nparray.shape[0] * scaling_factor)
    if DEBUG: print("  >> Resize image: (%s, %s) -> (%s, %s)" % (img_nparray.shape[0], img_nparray.shape[1], scaled_width, scaled_height))
    resized_im = cv2.resize(img_nparray, (scaled_width, scaled_height), interpolation=cv2.INTER_AREA) 
    # resized_im = cv2.resize(img_nparray, (scaled_width, scaled_height)) ## note: default interpolation is INTER_LINEAR, and does not work well for noisy EM micrographs 

    return resized_im

def extract_boxes(im_array, box_size, coords, DEBUG = True):
    """
    PARAMETERS
        im_array = np array (int value range 0 - 255)
        box_size = int(); pixel size of the box to extract
        coords = list( tuple(x, y), ... ); centered coordinates in pixels (top left == 0,0 by convention)
    RETURNS
        extracted_imgs = list( np arrays of dimension box_size , ... )
    """
    if DEBUG:
        print("==============================")
        print(" Extract boxes:")
        print("------------------------------")
        print("   im_array dim = ", im_array.shape)
        print("   box_size = %s px" % box_size)
        print("   input_coords = %s particles" % len(coords))


    extracted_imgs = []
    too_close_to_edge = 0
    ## sanity check that not too many coordinates are being asked to be extracted
    if len(coords) > 500:
        print(" WARNING :: extracted_boxes is capped at 500 coordinates to avoid memory issues. Will arbitrarily take first 500.")
        del coords[500:]
        

    box_size_halfwidth = int( box_size / 2)

    for coordinate in coords:
        x0 = coordinate[0] - box_size_halfwidth
        y0 = coordinate[1] - box_size_halfwidth
        x1 = coordinate[0] + box_size_halfwidth
        y1 = coordinate[1] + box_size_halfwidth
        # print(" input coord (x, y) -> (%s, %s)" % (coordinate[0], coordinate[1]))
        # print(" box_size_halfwidth = %s" % box_size_halfwidth)
        # print(" x0, x1 // y0, y1 :: %s, %s // %s %s" % (x0, x1, y0, y1))

        ## sanity check we are still in the image after adding/subtracting from the point 
        if x0 < 0 or y0 < 0:
            too_close_to_edge += 1
            continue 
        elif x1 > im_array.shape[1] or y1 > im_array.shape[0]:
            too_close_to_edge += 1
            continue 
        else:
            extracted_img = im_array[y0:y1,x0:x1]
            extracted_imgs.append(extracted_img)

    if DEBUG:
        print("------------------------------")
        print(" Extracted %s boxes from image" % len(extracted_imgs))
        print("  %s particles were too close to edge "  % too_close_to_edge)
        print("==============================")

    return extracted_imgs

def template_match(im_array, template_array, input_threshold):
    """
        REF: https://docs.opencv.org/4.x/d4/dc6/tutorial_py_template_matching.html
    """

    img_w, img_h = im_array.shape[::-1]
    template_w, template_h = template_array.shape[::-1]
    print(" im array shape = ", im_array.shape)
    print(" template array shape = ", template_array.shape)

    print("===========================")
    print("   Image_handler :: template_match")
    print("---------------------------")
    print("  input_img :: (x, y) [grayscale range] -> (%s, %s) [%s, %s]" % (img_w, img_h, np.min(im_array), np.max(im_array)))
    print("  input_template :: (x, y) [grayscale range] -> (%s, %s) [%s, %s]" % (template_w, template_h, np.min(template_array), np.max(template_array)))
    print("  picking threshold :: %s" % input_threshold)
    print("===========================")

    res = cv2.matchTemplate(np.uint8(im_array), np.uint8(template_array), cv2.TM_CCOEFF_NORMED)
    threshold = input_threshold

    """ REF: https://stackoverflow.com/questions/50579050/template-matching-with-multiple-objects-in-opencv-python/58514954#58514954
    """
    # fake out max_val for first run through loop
    max_val = 1
    loc = []
    prev_min_val, prev_max_val, prev_min_loc, prev_max_loc = None, None, None, None
    template_step_factor = 5 ## WIP adjust this value to determine how fine the template peak algorithm should look for matches.. this is crucial for templates that are larger than the density of picks we want, such as picking all nodes on a lattice
    while max_val > threshold:
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        
        # Prevent infinite loop. If those 4 values are the same as previous ones, break the loop.
        if prev_min_val == min_val and prev_max_val == max_val and prev_min_loc == min_loc and prev_max_loc == max_loc:
            break
        else:
            prev_min_val, prev_max_val, prev_min_loc, prev_max_loc = min_val, max_val, min_loc, max_loc
        
        if max_val > threshold:
            # Prevent start_row, end_row, start_col, end_col be out of range of image
            start_row = max(0, max_loc[1] - template_h // template_step_factor)
            start_col = max(0, max_loc[0] - template_w // template_step_factor)
            end_row = min(res.shape[0], max_loc[1] + template_h // template_step_factor + 1)
            end_col = min(res.shape[1], max_loc[0] + template_w // template_step_factor + 1)

            res[start_row: end_row, start_col: end_col] = 0
            match = (int(max_loc[0] + template_w/2), int(max_loc[1] + template_h/2), max_val)
            # print(" point found @ (%s, %s) score = %s" % (match[0], match[1], max_val))
            loc.append(match)

    print(" %s template matches found " % len(loc))

    return res, loc

def gaussian_disk(diameter, box_size, sigma = 0.2, background_color = 255, disk_color = 0, INVERT = True):
    """ 
    Creates a soft gaussian grayscale image of given pixel size with values in range 0 -- 255

    ### PARAMETERS 
    ```
        diameter = int() # pixels diameter of the gaussian disk to create 
        box_size = int() # total pixel size of the box to insert the guassian disk into 
        hardness = float() # 1 is smoothest while higher values lead to harder edges 
        sigma = float() # adjust the shape of the guassian by its sigma value, necessary to play with if a specific hardness and diameter are desired (raise this value as the hardness increases)
        background_color = int(0-255) # grayscale value of the background 
        INVERT = False is black signal on white background, True is white signal on black background
    ```

    ### RETURNS  
    ```
        np.array of centered gaussian disk with shape equal to box size in range 0-255
    ```

    ### EXAMPLE
    ```
        from PIL import Image as PIL_Image
        g = gaussian_disk(150, 300, background_color = 100, disk_color = 70)
        img = PIL_Image.fromarray(g).convert('L')
        img.show()
    ```
    """

    if box_size < diameter:
        print(" !! ERROR :: Cannot create a gaussian disk (%s px) larger than the given box size (%s px)" % (diameter, box_size))
        return np.zeros((box_size, box_size))

    ## generate the gaussian disk in a box the size of the taget diameter 
    size = int(diameter)
    x, y = np.meshgrid(np.linspace(-1,1, size), np.linspace(-1,1, size))
    d = np.sqrt(x*x+y*y)
    sigma, mu = sigma, 0.0
    g = np.exp(-( (d-mu)**2 / ( 2.0 * sigma**2 ) ) )
    ## raise the gaussian up along the x-axis to get a larger disk with a sharper edge that is closer to the target diameter size 
    g = g * 10000
    ## clip the gaussian to match a proportional range for rescaling
    g = np.clip(g, 0, 1) 
    ## normalize the gaussian to the range of a grayscale image 
    g = g * 256
    g = g.astype(int)

    ## prepare the larger box to place the gaussian disk into 
    window = np.ones((box_size, box_size))
    window = window * (255 - background_color)
    ## calculate the offset needed to center the gaussian 
    offset = int((window.shape[0] - g.shape[0])/2)
    ## stamp the gaussian values into the window with the offset  
    window[offset : offset + g.shape[0], offset : offset + g.shape[1]] = g

    # ## clip the values to the expected signal & background 
    min_val = 255 - background_color
    max_val = 255 - disk_color
    # if min_val < g.min():
    #     min_val = g.min()
    window = np.clip(window, min_val, max_val) 
    ## invert the colors as we expect to pick with black signal 
    window = 255 - window
    # print(" window min max = ", window.min(), window.max())
    window = gaussian_blur(window, 3)
    if INVERT:
        window = 255 - window
    return window

def gaussian_blur(im_array, sigma, DEBUG = True):
    import scipy.ndimage as ndimage
    if DEBUG:
        print("=======================================")
        print(" image_handler :: gaussian_blur")
        print("---------------------------------------")
        print("  input img dim = ", im_array.shape)
        print("  sigma = ", sigma)
        print("=======================================")

    blurred_img = ndimage.gaussian_filter(im_array, sigma)
    return blurred_img


def check_if_two_ranges_intersect(x0, x1, y0, y1, DEBUG = False):
    """ For two well-ordered ranges (x0 < x1; y0 < y1), check if there is any intersection between them.
        See: https://stackoverflow.com/questions/3269434/whats-the-most-efficient-way-to-test-two-integer-ranges-for-overlap/25369187
        An efficient way to quickly calculate if the erase brush hits a marked coordinate in the image.
    """
    ## sanity check input
    if (x0 > x1):
        print("ERROR: Incorrect range provided, x0 -> x1 == %s -> %s" % (x0, x1))

    if y0 > y1:
        print("ERROR: Incorrect range provided, y0 -> y1 == %s -> %s" % (y0, y1))

    if x0 <= y1 and y0 <= x1:
        if DEBUG:  
            print(" compare intersection of ranges: [a, b] & [c, d] == [%s, %s] & [%s, %s] :: TRUE" % (x0, x1, y0, y1))
        return True
    else:
        if DEBUG:  
            print(" compare intersection of ranges: [a, b] & [c, d] == [%s, %s] & [%s, %s] :: FALSE" % (x0, x1, y0, y1))
        return False
#endregion

#region Class MrcData
class MrcData():
    """
    A class object for loading an .MRC/.MRCS image and handling its accompanying data (e.g. processed images, associated coordinates, ...). Initialize this object with the file and desired default parameters:
        mrcdata = MrcData(image_name, scale_factor, lowpass_threshold, sigma_contrast)
    """

    def __init__(self, fname, input_scale = 0.25, input_lowpass = 10, input_sigma = 3, threads = 8):
        print("=========================================")
        print("      MrcData class initialized")
        print("-----------------------------------------")
        print(" Unpacking MRC data from: %s" % fname)

        self.threads = threads
        if self.threads > 1:
            self.PARALLEL_PROCESSING = True
        else: 
            self.PARALLEL_PROCESSING = False
        self.scale_factor = input_scale
        self.lowpass_threshold = input_lowpass
        self.sigma_contrast = input_sigma
        self.raw_data, self.pixel_size, self.x, self.y, self.z = get_mrc_raw_data(fname)
        self.fname = fname
        self.coordinates_raw = {} ## expected structure: { str(slice_index) : [ (x1, y1), ... (x, y) ], ... }, coordinates are in original pixel dimensions 
        self.process_raw_data()

        return

    def add_coordinate(self, slice_index, x, y, box_width, SCALE_FACTOR = -1):
        """
        PARAMETERS 
            slice_index = which z stack these coordinates belong to
            x, y = pixel position of the coordinate in the scaled image 
            box_width = size of the box (in Angstroms) for a particle to check for clashes
            SCALE_FACTOR = default is negative, which reads scale factor from self.scale_factor, add in specific value to use a custom scaling factor when running this function
        """
        if SCALE_FACTOR < 0:
            ## interpolate the picked coordinates back to the raw image coordinates 
            x = int(x / self.scale_factor) 
            y = int(y / self.scale_factor)
        else:
            x = int(x / SCALE_FACTOR)
            y = int(y / SCALE_FACTOR)
        box_width_px = int(box_width / self.pixel_size)

        ## check if there already exists a list of coordinates for this given slice 
        if str(slice_index) in self.coordinates_raw:

            ## negative box values mean to avoid checking clashes
            if box_width > 0:

                ## check if the pick is a clash with any coordinates
                if self.is_clashing(x, y, box_width_px, self.coordinates_raw[str(slice_index)], slice_index):
                    print(" New coordinate clashes with existing coordinate")
                    pass
                else:
                    self.coordinates_raw[str(slice_index)].append((x, y))
                    print(" Adding coordinate to slice: %s -> (%s, %s)" % (slice_index, x, y))
            else:
                self.coordinates_raw[str(slice_index)].append((x, y))    

        else:
            self.coordinates_raw[str(slice_index)] = [(x, y)]
            print(" Adding coordinate to slice: %s -> (%s, %s)" % (slice_index, x, y))
        return 

    def is_clashing(self, input_x, input_y, box_width, coordinates, slice_index, DEBUG = False):
        """
        PARAMETERS
            input_x, input_y = coordinates of the new coordinate in raw pixel values 
            box_width = pixel width of the box being used for extraction 
            coordinates = list of existing coordinate for this given slice 
            slice_index = the index of the current slice we are editing/checking
        """
        ## Calculate the boundaries to use for the clash check
        box_halfwidth = int(box_width / 2)
        # print(" box width in pixels = %s" % box_width)

        for (x, y) in coordinates:
            if DEBUG:
                print(" CLASH TEST :: mouse_position = ", input_x, input_y, " ; existing coord = " , x, y)
            ## check x-position is in range for potential clash
            if x - box_halfwidth <= input_x <= x + box_halfwidth:
                ## check y-position is in range for potential clash
                if y - box_halfwidth <= input_y <= y + box_halfwidth:
                    ## if both x and y-positions are in range, we have a clash
                    self.coordinates_raw[str(slice_index)].remove((x, y)) # remove the coordinate that clashed
                    return True # for speed, do not check further coordinates (may have to click multiple times for severe overlaps)
        return False

    def remove_coordinate(self, slice_index, x, y, DEBUG = False):
        if DEBUG: print(" Remove coordinate: (%s, %s, %s)" % (x, y, slice_index))
        self.coordinates_raw[str(slice_index)].remove((x, y))
        return 
    
    def clear_coordinates_from_slice(self, slice_index):
        print(" Clear coordinates from slice: %s" % slice_index)
        if str(slice_index) in self.coordinates_raw:
            del self.coordinates_raw[str(slice_index)]
        else:
            print(" Warning :: no coordinates were detected for this slice to clear! Ignoring request.")
        return 

    def remove_clashes_above_below(self, z, clash_distance_Ang, DEBUG = True):
        if DEBUG: print(" REMOVE clashes from planes above/below slice %s (clash distance = %s Ang)" % (z, clash_distance_Ang))
        ## determine the number of slices above & below we need to collate particle coordinates from 
        clash_half_distance_px = int((clash_distance_Ang / self.pixel_size)/2)
        ## collate the coordinate data for each slice above & below by this half distance
        coordinates_above_below = []
        for i in range(clash_half_distance_px + 1):
            if i == 0:
                continue 
            positive_slice = z + i
            if str(positive_slice) in self.coordinates_raw:
                for coordinate in self.coordinates_raw[str(positive_slice)]:
                    coordinates_above_below.append(coordinate)
            negative_slice = z + (i*-1)
            if str(negative_slice) in self.coordinates_raw:
                for coordinate in self.coordinates_raw[str(negative_slice)]:
                    coordinates_above_below.append(coordinate)
        if DEBUG: print(" ... %s coordinates were found within the clash distance above " % len(coordinates_above_below))

        ## iterate over the current coordinate list and remove clashes from the identified coordinates in the above/below planes 
        erase_coordinates = [] # avoid changing dictionary until after iteration complete
        ## find all coordinates that clash
        if str(z) in self.coordinates_raw:
            if len(self.coordinates_raw[str(z)]) > 0:
                for coord in self.coordinates_raw[str(z)]:
                    ## set up a flag to capture when this coordinate is found to be clashing early 
                    CLASH_DETECTED = False
                    ## get each coordinate on the current slice we are evaluating  
                    current_x = coord[0]
                    current_y = coord[1]
                    ## for each coordinate on the current slice, check if it clashes with any points in the planes above/below
                    for coord_above_below in coordinates_above_below:
                        ## on the first clash we find, avoid further calculation by setting this flag to True and existing this nested for loop 
                        if CLASH_DETECTED: break 
                        ## for the point above/below, establish its clash limits 
                        x_max = int(coord_above_below[0] + clash_half_distance_px)
                        x_min = int(coord_above_below[0] - clash_half_distance_px)
                        y_max = int(coord_above_below[1] + clash_half_distance_px)
                        y_min = int(coord_above_below[1] - clash_half_distance_px)

                        if check_if_two_ranges_intersect(current_x - clash_half_distance_px, current_x + clash_half_distance_px, x_min, x_max, DEBUG = False): # x0, x1, y0, y1
                            if check_if_two_ranges_intersect(current_y - clash_half_distance_px, current_y + clash_half_distance_px, y_min, y_max, DEBUG = False): # x0, x1, y0, y1
                                erase_coordinates.append(coord)
                                CLASH_DETECTED = True
                                ## if the coordinate is added, we can move to the next coordinate immediately 
                    ## if we reach here we can continue early to the next coordinate  
                    if CLASH_DETECTED: continue 

        for (x, y) in erase_coordinates:
            self.remove_coordinate(z, x, y)

        return 

    def process_raw_data(self):
        ## reset the processed data variable 
        self.processed_data = list()
        start_time = time.time() ## for images >500px, there is a speed up when using 8 threads on my laptop (~4.7s versus ~10.1s), for smaller images it may actually be faster to avoid the overhead needed to set up parallel processing!

        if self.PARALLEL_PROCESSING:

            ## multithreading set up
            tasks = []
            for z_slice in range(self.z):
                ## find the raw mrc data for the corresponding slice 
                slice_array = self.raw_data[z_slice,:,:]
                ## load each slice to be processed into the working batch 
                tasks.append(slice_array) 

            ### use Pool to split the working batch across threads with a target function  
            try:
                ## define total workset inputs
                dataset = []
                for task in tasks:
                    dataset.append((task, self.scale_factor, self.pixel_size, self.lowpass_threshold, self.sigma_contrast))
                
                ## prepare pool of workers
                pool = Pool(self.threads)
                ## assign workload to pool
                results = pool.starmap(process_single_image, dataset)
                ## close the pool from recieving any other tasks
                pool.close()
                ## merge with the main thread, stopping any further processing until workers are complete
                pool.join()

            except KeyboardInterrupt:
                print("Multiprocessing run killed")
                pool.terminate()

            for result in results:
                ## cast each processed image as a PhotoImage obj
                im_obj = get_PhotoImage_obj(result)

                self.processed_data.append(im_obj)
                print(" # z-slices processed = ", len(self.processed_data), end="\r", flush=True)

        else:
            for z_slice in range(self.z):
                print(" # z-slices processed = ", z_slice + 1, end="\r", flush=True)

                ## find the raw mrc data for the corresponding slice 
                slice_array = self.raw_data[z_slice,:,:]

                im_obj = self.process_single_image_singleThread(slice_array)
                ## pack the processed image object into the mrcdata holder variable 
                self.processed_data.append(im_obj)

        print()
        end_time = time.time()
        total_time_taken = end_time - start_time
        print("... runtime = %.2f sec" % total_time_taken)

        return  
    
    def process_single_image_singleThread(self, input_array):
        """
        PARAMETERS
            im_array = raw data of image as an nparray 
        RETURNS
            im_obj = PhotoImage object useable for display on Tk 
        """
        ## it is much faster if we scale down the image prior to doing filtering
        img_scaled = resize_image(input_array, self.scale_factor)
        grayscale_img_array = mrc2grayscale(img_scaled, self.pixel_size / self.scale_factor, self.lowpass_threshold)
        img_contrasted = sigma_contrast(grayscale_img_array, self.sigma_contrast)  
        im_obj = get_PhotoImage_obj(img_contrasted)

        return im_obj  

    def get_processed_slice_unscaled_as_array(self, z_slice, DEBUG = True):
        """
        For template generation and picking, use an uncompressed image for all work 
        """
        ## find the raw mrc data for the corresponding slice 
        slice_array = self.raw_data[z_slice,:,:]
        ## it is much faster if we scale down the image prior to doing filtering
        grayscale_img_array = mrc2grayscale(slice_array, self.pixel_size, self.lowpass_threshold)
        img_contrasted = sigma_contrast(grayscale_img_array, self.sigma_contrast)  
        # im_obj = get_PhotoImage_obj(img_contrasted)
        if DEBUG: print("  get_processed_slice_unscaled_as_array -> ", type(img_contrasted), img_contrasted.shape)
        return img_contrasted 

    def resize_images(self, new_scale_factor):
        print(" Rescale processed images: %s" % new_scale_factor)
        if new_scale_factor == self.scale_factor:
            print(" ... new scale factor is same as current factor. Make no changes")
        else:
            self.scale_factor = new_scale_factor
            self.process_raw_data()
        return 
    
    def set_lowpass_threshold(self, new_lowpass_threshold):
        if new_lowpass_threshold == self.lowpass_threshold:
            print(" ... new lowpass threshold is same as current threshold. Make no changes")
        else:
            self.lowpass_threshold = new_lowpass_threshold
            self.process_raw_data()
        return 
    
    def set_sigma_contrast(self, new_sigma_contrast):
        if new_sigma_contrast == self.sigma_contrast:
            print(" ... new sigma contrast is same a current sigma contrast. Make no changes")
        else:
            self.sigma_contrast = new_sigma_contrast
            self.process_raw_data()
        return 

    def extract_particles(self, box_width):
        """
        PARAMETERS 
            box_width = size of the box to extract, in Angstroms 
        """
        extracted_imgs = []
        ## Calculate the box dimensions in pixels 
        box_halfwidth_px = int((box_width / self.pixel_size)/2)
        ## Determine the dtype of the original dat 
        dtype = self.raw_data.dtype

        print(" Extract particles (%s Ang / %s px box size): " % (box_width, 2 * box_halfwidth_px))
        for z in self.coordinates_raw:
            print(" ... slice %s" % z)
            im_array = self.raw_data[int(z),:,:]
            for coord in self.coordinates_raw[z]:
                print("         (%s, %s)" % coord)
                x0 = coord[0] - box_halfwidth_px
                y0 = coord[1] - box_halfwidth_px
                x1 = coord[0] + box_halfwidth_px
                y1 = coord[1] + box_halfwidth_px

                extracted_img = im_array[y0:y1,x0:x1]
                extracted_imgs.append(extracted_img)

        ## prepare a reasonable output name adjusting for both expected extensions
        if self.fname[-5:].lower() == '.mrcs':
            output_mrcs_name =  self.fname[:-5] + "_extracted.mrcs"
        elif self.fname[-4:].lower() == '.mrc':
            output_mrcs_name = self.fname[:-4] + "_extracted.mrcs"

        if len(extracted_imgs) > 0:
            self.make_empty_mrcs(len(extracted_imgs), (x1 - x0, y1 - y0), dtype, output_mrcs_name)
            self.write_frames_to_empty_mrcs(output_mrcs_name, extracted_imgs)

            print("======================================")
            print(" Written %s frames to: %s" % (len(extracted_imgs), output_mrcs_name))
            print("--------------------------------------")
        else:
            print("======================================")
            print(" No frames were selected! No subset.mrcs file will be created...")
            print("--------------------------------------")

        return
    
    def make_empty_mrcs(self, stack_size, mrc_dimensions, dtype, fname, DEBUG = True):
        """ Prepare an empty .MRCS in memory of the correct dimensionality
        """
        with mrcfile.new(fname, overwrite=True) as mrcs:
            mrcs.set_data(np.zeros(( stack_size, ## stack size
                                    mrc_dimensions[1], ## pixel height, 'Y'
                                    mrc_dimensions[0]  ## pixel length, 'X'
                                    ), dtype=np.dtype(getattr(np, str(dtype)))
                                ))

            ## set the mrcfile with the correct header values to indicate it is an image stack
            mrcs.set_image_stack()
            if DEBUG:
                print("======================================")
                print(" make_empty_mrcs ")
                print("--------------------------------------")
                print("  name = %s" % fname)
                print("  dimensions = (%s, %s, %s)" % (mrc_dimensions[0], mrc_dimensions[1], stack_size))
                print("  data type = %s" % dtype)
        return
    
    def write_frames_to_empty_mrcs(self, input_mrcs_fname, input_data):
        """ input_mrcs_fname = str(); file name in working dir of the parent .MRCS to take a subset from
            input_data = list[ nparray, ..., nparray ]; list of raw frame data to write 
        """
        ## open the input mrcs into buffer
        input_mrcs = mrcfile.open(input_mrcs_fname, mode='r+')

        # print(" frames to save = ", chosen_frames)
        for i in range(len(input_data)):
            ## grab the frame data 
            frame_data = input_data[i]
            print(" Writing frame %s to file " % i, frame_data.shape)

            ## sanity check there is a frame expected
            if i in range(0, input_mrcs.data.shape[0]):
                # if DEBUG:
                    # print("Data read from file = (min, max) -> (%s, %s), dtype = %s" % (np.min(frame_data), np.max(frame_data), frame_data.dtype))

                ## need to deal with single frame as a special case since array shape changes format
                if len(input_data) == 1:
                    input_mrcs.data[0:] = frame_data
                else:
                    ## pass the frame data into the next available frame of the output mrcs
                    input_mrcs.data[i] = frame_data
                    # if DEBUG:
                    #     print("Data written to file = (min, max) -> (%s, %s), dtype = %s" % (np.min(output_mrcs.data[i]), np.max(output_mrcs.data[i]), output_mrcs.data[i].dtype))
            else:
                print(" Input frame value requested (%s) not in expected range of .MRCS input file: (%s; [%s, %s])" % (i, input_mrcs_fname, 1, input_mrcs.data.shape[0]))

        input_mrcs.voxel_size = input_mrcs.voxel_size
        input_mrcs.update_header_from_data()
        input_mrcs.update_header_stats()

        input_mrcs.close()
        return

    def write_star_coordinates(self, save_path, save_fname, tomo_name = "", DEBUG = False):
        
        if len(tomo_name) == 0:
            tomostar = os.path.splitext(os.path.basename(self.fname))[0] + ".tomostar"
            tomo_name = os.path.splitext(os.path.basename(self.fname))[0]
        else:
            tomostar = tomo_name + ".tomostar"

        columns = ["rlnCoordinateX", "rlnCoordinateY", "rlnCoordinateZ", "rlnMicrographName", "rlnTomoName" ]
        df = pd.DataFrame(columns=columns)
        ## prepare the coordinates as a dataframe, where columns are the datavalues 
        counter = 0
        for slice in self.coordinates_raw:
            for coord in self.coordinates_raw[slice]:
                counter += 1
                if DEBUG: print(" write_star_coordinates :: slice = %s, coord = %s" % (slice, coord))
                x, y = coord
                z = int(slice)
                df.loc[len(df)] = {
                    "rlnCoordinateX" : x, 
                    "rlnCoordinateY" : y, 
                    "rlnCoordinateZ" : z, 
                    "rlnMicrographName" : tomostar,
                    "rlnTomoName" : tomo_name
                }

        # print(df)
        
        ## write the dataframe using starfile package 
        starfile.write(df, os.path.join(save_path, save_fname))


        print(" Write star file: ")
        print("        star file = ", os.path.join(save_path, save_fname))
        print("    # coordinates = ", counter)
        print("     tomostar str = ", tomostar)

        ## not super efficient, but we can re-write the file to ensure LF line endings if running on Windows
        if os.name == 'nt':
            print("     ... Windows OS detected :: converting star file to LF line endings")
            convert_to_linux_newlines(os.path.join(save_path, save_fname))

        return

    def parse_starfile_df(self, df, DEBUG = True):
        ## clear existing star coordinate data 
        self.coordinates_raw = {}

        if DEBUG: print(" Parse input star dataframe:\n", df )
        ## get the max number of z slices in the data structure 
        max_z = self.z        

        ## check we have the expected rlnColumnNames present 
        expected_columns = {"rlnCoordinateX", "rlnCoordinateY", "rlnCoordinateZ", "rlnMicrographName", "rlnTomoName" }
        if not expected_columns.issubset(df.columns):
            print(" ERROR :: Input star file data lacks expected columns")
            print( expected_columns)

        ## iterate through the dictionary to set the coordinates 
        particle_count = 0
        for index, row in df.iterrows():
            x = int(row['rlnCoordinateX'] )
            y = int(row['rlnCoordinateY'] )
            z = int(row['rlnCoordinateZ'] )
            particle_count += 1
            try:
                tomostar_str = row['rlnMicrographName']
            except:
                print(" WARNING :: Missing rlnMicrographName column was missing, skipping")
                tomostar_str = ""

            try:
                tomo_name_str = row['rlnTomoName']
            except:
                print(" WARNING :: Missing rlnTomoName column was missing, skipping")
                tomo_name_str = ""

            ## check if there already exists a list of coordinates for this given slice 
            if str(z) in self.coordinates_raw:
                self.coordinates_raw[str(z)].append((x, y))    
            ## otherwise initialize the dictionary with the slice 
            else:
                self.coordinates_raw[str(z)] = [(x, y)]

        if DEBUG:
            print(" Imported %s coordinates:" % particle_count)
            counter = 0
            for z in self.coordinates_raw:
                if len(self.coordinates_raw[z]) > 1:
                    counter += 1
                    print("    ", self.coordinates_raw[z][0])
                    if counter == 2:
                        print("    ", self.coordinates_raw[z][0])
                        print("     ...")
                        break 


        ## update the tomostar string
        print( " WIP add parsing of tomostar and tomoName data into mainUI widgets ")         
        return tomostar_str

    def shift_coordinates_by_axis(self, axis, dist):
        # print(" shift coords %s px along %s" % (dist, axis))

        ## shift by z
        if axis == 'z':
            ## since the data structure has string as its keys, we need to build a new dictionary entirely to shift the coordinates up or down
            updated_d = {}

            if dist == 'flip':
                z_max = self.z
                for z_str in self.coordinates_raw:
                    z_int = int(z_str)
                    new_z = z_max - z_int
                    print(" %s -> %s" % (z_int, new_z))
                    updated_d[str(new_z)] = self.coordinates_raw[z_str]

            else:
                for z_str in self.coordinates_raw:
                    z_int = int(z_str)
                    new_z = z_int + dist
                    if 0 > new_z > len(self.coordinates_raw):
                        continue 
                    else:
                        updated_d[str(new_z)] = self.coordinates_raw[z_str]

            self.coordinates_raw = updated_d
        elif axis == 'x':
            ## shift x
            ## x and y data are lists of tuples, so we need to make a fresh list and replace the existing one for each slice 
            for z in self.coordinates_raw:
                new_points = []
                for x,y in self.coordinates_raw[z]:
                    new_coord = (x + dist, y)
                    new_points.append(new_coord)
                self.coordinates_raw[z] = new_points
        elif axis == 'y':
            ## shift y
            for z in self.coordinates_raw:
                new_points = []
                for x,y in self.coordinates_raw[z]:
                    new_coord = (x, y + dist)
                    new_points.append(new_coord)
                self.coordinates_raw[z] = new_points

        return 

#endregion

#region Class TK
class MainUI:
    def __init__(self, instance, input_scale, input_lowpass, input_sigma, input_file, input_threads, coord_file):
        self.instance = instance
        instance.title("Tomography picker")
        # instance.geometry("520x500") ## geometry now set by a function 

        ## CLASS VARIABLES
        self.RIGHT_MOUSE_PRESSED = False 
        self.brush_size = 50
        self.displayed_widgets = list() ## container for all widgets packed into the main display UI, use this list to update each
        self.display_data = list() ## container for the image objects for each displayed widgets (they must be in the scope to be drawn)
                                   ## in this program, display_data[0] will contain the scaled .jpg-style image; while display_data[1] will contain the display-ready CTF for that image
        self.display_im_arrays = list() ## contains the nparray versions of the image/ctf currently in the display window (for saving jpgs) 
        self.mrc_dimensions = ('x', 'y')
        self.pixel_size = float()
        self.image_name = input_file
        self.scale_factor = input_scale
        self.lowpass_threshold = input_lowpass
        self.sigma_contrast = input_sigma
        self.SHOW_PICKS = tk.BooleanVar(instance, True)
        self.picks_diameter = 100 ## Angstroms, `picks' are clicked particles by the user
        self.picks_color = 'red'
        self.picks_alt_color = 'blue'
        # self.coordinates = dict() ## list of picked points
        self.SHOW_SCALEBAR = tk.BooleanVar(instance, False)
        self.scalebar_length = 200 ## Angstroms
        self.scalebar_stroke = 5 ## pixels
        self.scalebar_color = 'white'
        self.SHOW_CTF = tk.BooleanVar(instance, False)
        self.slice_index = 180 ## index of the list of known mrc files int he directory to view
        self.working_dir = "."
        self.SPEED_OVER_ACCURACY = tk.BooleanVar(instance, True)
        self.autopickPanel_instance = None
        self.settingsPanel_instance = None
        self.threads = input_threads
        self.picks_display_depth = 5 ## number of frames to show picks above & below the current display z position 
        self.save_star_fname = "" ## file name to save, including path if needed 

        ## MENU BAR LAYOUT
        self.initialize_menubar(instance)

        ## MAIN WINDOW WITH SCROLLBARS
        self.viewport_frame = viewport_frame =  ttk.Frame(instance)

        right_side_panel_fontsize = 10

        ## MRC INFO
        self.iminfo_header = tk.Label(instance, font=("Helvetica, 16"), text="MRC info")
        self.iminfo_header.grid(row = 1, column = 1, columnspan = 2) #, sticky = (tk.N, tk.W))

        self.MRC_dimensions_LABEL = tk.Label(instance, font=("Helvetica", right_side_panel_fontsize), text="(%s, %s, %s)" % ('x', 'y', 'z'))
        self.MRC_dimensions_LABEL.grid(row = 2, column = 1, columnspan = 2)

        self.MRC_angpix_LABEL = tk.Label(instance, font=("Helvetica", right_side_panel_fontsize), text="%s Å/px" % '1')
        self.MRC_angpix_LABEL.grid(row = 3, column = 1, columnspan = 2)

        self.MRC_displayed_angpix_LABEL = tk.Label(instance, font=("Helvetica", right_side_panel_fontsize), text="Display @ %s Å/px" % '2')
        self.MRC_displayed_angpix_LABEL.grid(row = 4, column = 1, columnspan = 2)


        ## DISPLAY SETTINGS
        self.separator = ttk.Separator(instance, orient='horizontal')
        self.separator.grid(row=5, column =1, columnspan = 2, sticky=tk.EW)
        self.settings_header = tk.Label(instance, font=("Helvetica, 16"), text="Display")
        self.settings_header.grid(row = 6, column = 1, columnspan = 2) #, sticky = (tk.N, tk.W))

        self.scale_LABEL = tk.Label(instance, font=("Helvetica", right_side_panel_fontsize), text="Scale factor: ")
        self.scale_ENTRY = tk.Entry(instance, width=4, font=("Helvetica", right_side_panel_fontsize))
        self.scale_LABEL.grid(row = 7, column = 1, sticky = (tk.N, tk.E))
        self.scale_ENTRY.grid(row = 7, column = 2, sticky = (tk.N, tk.W))

        self.lowpass_threshold_LABEL = tk.Label(instance, font=("Helvetica", right_side_panel_fontsize), text="Lowpass: ")
        self.lowpass_threshold_ENTRY = tk.Entry(instance, width=4, font=("Helvetica", right_side_panel_fontsize))
        self.lowpass_threshold_LABEL.grid(row = 8, column = 1, sticky = (tk.N, tk.E))
        self.lowpass_threshold_ENTRY.grid(row = 8, column = 2, sticky = (tk.N, tk.W))

        self.sigma_contrast_LABEL = tk.Label(instance, font=("Helvetica", right_side_panel_fontsize), text="Sigma: ")
        self.sigma_contrast_ENTRY = tk.Entry(instance, width=4, font=("Helvetica", right_side_panel_fontsize))
        self.sigma_contrast_LABEL.grid(row = 9, column = 1, sticky = (tk.N, tk.E))
        self.sigma_contrast_ENTRY.grid(row = 9, column = 2, sticky = (tk.N, tk.W))

        ## OPTIONAL SETTINGS
        self.separator2 = ttk.Separator(instance, orient='horizontal')
        self.separator2.grid(row=12, column =1, columnspan = 2, sticky=tk.EW)
        self.optional_header = tk.Label(instance, font=("Helvetica, 16"), text="Particles")
        self.optional_header.grid(row = 13, column = 1, columnspan = 2) #, sticky = (tk.N, tk.W))

        self.show_picks_TOGGLE = tk.Checkbutton(instance, text='Show particle picks', variable=self.SHOW_PICKS, onvalue=True, offvalue=False, command=self.toggle_SHOW_PICKS)
        self.show_picks_TOGGLE.grid(row = 14, column = 1, columnspan = 2, sticky = (tk.N, tk.W))

        self.picks_diameter_LABEL = tk.Label(instance, font=("Helvetica", right_side_panel_fontsize), text="Diameter (Å): ")
        self.picks_diameter_ENTRY = tk.Entry(instance, width=4, font=("Helvetica", right_side_panel_fontsize))
        self.picks_diameter_LABEL.grid(row = 15, column = 1, sticky = (tk.N, tk.E))
        self.picks_diameter_ENTRY.grid(row = 15, column = 2, sticky = (tk.N, tk.W))

        # self.extract_LABEL = tk.Label(instance, font=("Helvetica", right_side_panel_fontsize), text="%s px" % 'wip')
        # self.extract_LABEL.grid(row = 16, column = 1, columnspan = 2)
        # self.extract_button = tk.Button(instance, text="Extract", font=("Helvetica", right_side_panel_fontsize), command = lambda: self.extract_particles(), width=10)
        # self.extract_button.grid(row = 20, column = 1, columnspan = 2)

        viewport_frame.grid(row = 1, column = 0, rowspan = 100)

        scrollable_frame, viewport_canvas = self.initialize_scrollable_window(self.viewport_frame)

        ## LOAD AN INITIAL MRC FILE

        ## Pack the image data into the MrcData object
        self.mrcdata = MrcData(self.image_name, self.scale_factor, self.lowpass_threshold, self.sigma_contrast, self.threads)
        # self.next_img('none')
        self.load_img()

        ## SET THE SIZE OF THE PROGRAM WINDOW BASED ON THE SIZE OF THE DATA FRAME AND THE SCREEN RESOLUTION
        self.resize_program_to_fit_screen_or_data()

        ## EVENT BINDING
        instance.bind("<Configure>", self.resize) ## Bind manual screen size adjustment to updating the scrollable area

        ## KEYBINDINGS
        self.instance.bind("<F1>", lambda event: self.debugging())
        self.instance.bind('<Left>', lambda event: self.next_img('left'))
        self.instance.bind('<Right>', lambda event: self.next_img('right'))
        self.instance.bind('<Up>', lambda event: self.next_img('left'))
        self.instance.bind('<Down>', lambda event: self.next_img('right'))
        self.instance.bind('<z>', lambda event: self.next_img('left'))
        self.instance.bind('<x>', lambda event: self.next_img('right'))
        # self.instance.bind('<Control-KeyRelease-e>', lambda event: self.extract_particles())
        self.instance.bind('<Control-KeyRelease-q>', lambda event: self.quit())
        self.instance.bind('<Control-KeyRelease-s>', lambda event: self.write_coordinates())
        self.instance.bind('<Control-x>', lambda event: self.open_panel("AutopickPanel"))
        self.instance.bind('<Control-z>', lambda event: self.open_panel("SettingsPanel"))
        self.instance.bind('<Control-o>', lambda event: self.load_star_coordinates())


        self.scale_ENTRY.bind('<Control-KeyRelease-a>', lambda event: self.select_all(self.scale_ENTRY))
        self.scale_ENTRY.bind('<Return>', lambda event: self.scale_updated())
        self.scale_ENTRY.bind('<KP_Enter>', lambda event: self.scale_updated())
        self.lowpass_threshold_ENTRY.bind('<Control-KeyRelease-a>', lambda event: self.select_all(self.lowpass_threshold_ENTRY))
        self.lowpass_threshold_ENTRY.bind('<Return>', lambda event: self.lowpass_threshold_updated())
        self.lowpass_threshold_ENTRY.bind('<KP_Enter>', lambda event: self.lowpass_threshold_updated())
        self.sigma_contrast_ENTRY.bind('<Control-KeyRelease-a>', lambda event: self.select_all(self.sigma_contrast_ENTRY))
        self.sigma_contrast_ENTRY.bind('<Return>', lambda event: self.sigma_updated())
        self.sigma_contrast_ENTRY.bind('<KP_Enter>', lambda event: self.sigma_updated())
        self.picks_diameter_ENTRY.bind('<Control-KeyRelease-a>', lambda event: self.select_all(self.picks_diameter_ENTRY))
        self.picks_diameter_ENTRY.bind('<Return>', lambda event: self.pick_diameter_updated())
        self.picks_diameter_ENTRY.bind('<KP_Enter>', lambda event: self.pick_diameter_updated())

        self.instance.bind("<ButtonPress-3>", self.on_right_mouse_press)
        self.instance.bind("<ButtonRelease-3>", self.on_right_mouse_release)
        self.instance.bind("<Motion>", self.refresh_brush_cursor)
        self.instance.bind("<MouseWheel>", self.MouseWheelHandler) # Windows, Mac: Binding to <MouseWheel> is being used
        self.instance.bind("<Button-4>", self.MouseWheelHandler) # Linux: Binding to <Button-4> and <Button-5> is being used
        self.instance.bind("<Button-5>", self.MouseWheelHandler)
        self.instance.bind("<ButtonPress-2>", self.on_middle_mouse_press)
        self.instance.bind("<ButtonRelease-2>", self.on_middle_mouse_release)

        if not coord_file is None:
            self.load_star_coordinates(coord_file)

        return

    def open_panel(self, panelType = 'None'):

        ## use a switch-case statement logic to open the correct panel
        if panelType == "None":
            return
        elif panelType == "AutopickPanel":
            if self.autopickPanel_instance is None:
                self.autopickPanel_instance = AutopickPanel(self)
            else:
                print(" AutopickPanel is already open: ", self.autopickPanel_instance)
        elif panelType == "SettingsPanel":
            if self.settingsPanel_instance is None:
                self.settingsPanel_instance = SettingsPanel(self)
            else:
                print(" SettingsPanel is already open: ", self.settingsPanel_instance)
                
        else:
            return
        return

    def write_coordinates(self):

        ## make a suggested basename for ease of user saving quickly 
        suggested_name = os.path.splitext(os.path.split(self.image_name)[1])[0] + "_CURATED.star"

        if len(self.save_star_fname) < 6:
            ## launch a save window
            filetypes = [("STAR","*.star"),("All Files","*.*")]
            save_path = asksaveasfilename(parent = self.instance, initialfile = "%s" % suggested_name, defaultextension=".star", filetypes=filetypes)
            self.save_star_fname = save_path
        else:
            ## use the string in the fname
            save_path = self.save_star_fname 


        save_root, save_basename = os.path.split(save_path)
        # print(" Write coordinates file: ", os.path.join(save_root, save_basename))
        if not self.settingsPanel_instance is None:
            self.mrcdata.write_star_coordinates(save_root, save_basename, tomo_name = self.settingsPanel_instance.tomo_name_ENTRY.get())
        else:
            self.mrcdata.write_star_coordinates(save_root, save_basename)
        return 

    def create_gif_animation(self, FORMAT = 'unidirectional'):
        print(" Creating GIF:")

        ## prepare a reasonable output name adjusting for both expected extensions
        if self.mrcdata.fname[-5:].lower() == '.mrcs':
            output_fname =  self.mrcdata.fname[:-5] + ".gif"
        elif self.mrcdata.fname[-4:].lower() == '.mrc':
            output_fname = self.mrcdata.fname[:-4] + ".gif"

        ## reprocess the ImageTk object back to PIL Image format
        frames = []
        for tk_img in self.mrcdata.processed_data:
            pil_img = ImageTk.getimage(tk_img)
            frames.append(pil_img)

        if FORMAT == 'unidirectional':

            frame_one = frames[0]
            frame_one.save(output_fname, format="GIF", append_images=frames, save_all=True, duration=100, loop=0)

        elif FORMAT == 'bidirectional':
            ## deep copy the forward frames, then reverse them
            reversed_frames = copy.deepcopy(frames)
            reversed_frames.reverse()
            ## append reverse direction onto the forward loop 
            for f in reversed_frames:
                frames.append(f)

            frame_one = frames[0]
            frame_one.save(output_fname, format="GIF", append_images=frames, save_all=True, duration=100, loop=0)

        print(" ... complete. Saved as: %s" % output_fname)
        return 

    # def extract_particles(self):
    #     self.mrcdata.extract_particles(self.picks_diameter)
    #     return 
 
    def save_jpg(self):
        ## WIP 
        suggested_jpg_fname = os.path.splitext(self.image_name)[0] + ".jpg"

        file_w_path = asksaveasfilename(  parent = self.instance, initialfile = suggested_jpg_fname,
                            defaultextension=".jpg",filetypes=[("All Files","*.*"),("JPEG","*.jpg")])

        save_dir, save_name = os.path.split(str(file_w_path))
        # print("File selected: ", file_name)
        # print("Working directory: ", file_dir)

        if self.SHOW_CTF.get() == True:
            img_to_save = self.display_im_arrays[1]
        else:
            img_to_save = self.display_im_arrays[0]
    
        cv2.imwrite(file_w_path, img_to_save, [cv2.IMWRITE_JPEG_QUALITY, 100])

        ## open the image to draw coordinate picks if activated 
        if self.SHOW_PICKS.get() == True:
            img_to_write = cv2.imread(file_w_path)
            ## box_size is a value given in Angstroms, we need to convert it to pixels
            display_angpix = self.pixel_size / self.scale_factor
            box_width = self.picks_diameter / display_angpix
            box_halfwidth = int(box_width / 2)

            for coordinate in self.coordinates:
                # print("writing coordinate @ =", coordinate)
                cv2.circle(img_to_write, coordinate, box_halfwidth, (0,0,255), 2)
            
            cv2.imwrite(file_w_path, img_to_write, [cv2.IMWRITE_JPEG_QUALITY, 100])

        ## open the image to draw a scalebar if activated 
        if self.SHOW_SCALEBAR.get() == True:
            img_to_write = cv2.imread(file_w_path)
            scalebar_px = int(self.scalebar_length / (self.pixel_size / self.scale_factor))
            scalebar_stroke = self.scalebar_stroke
            indent_x = int(self.display_im_arrays[0].shape[0] * 0.025)
            indent_y = self.display_im_arrays[0].shape[1] - int(self.display_im_arrays[0].shape[1] * 0.025)
            
            cv2.line(img_to_write, (indent_x, indent_y), (indent_x + scalebar_px, indent_y), (255, 255, 255), scalebar_stroke)

            cv2.imwrite(file_w_path, img_to_write, [cv2.IMWRITE_JPEG_QUALITY, 100])

        print(" Saved display to >> %s" % file_w_path)

        return

    def draw_image_coordinates(self, DEBUG = False):
        """ Read a dictionary of pixel coordinates and draw boxes centered at each point
        """
        canvas = self.displayed_widgets[0]

        ## delete any pre-existing coordinates if already drawn
        canvas.delete('particle_positions')

        ## check if we are allowed to draw coordinates before proceeding
        if self.SHOW_PICKS.get() == False:
            return

        ## box_size is a value given in Angstroms, we need to convert it to pixels
        display_angpix = self.mrcdata.pixel_size / self.mrcdata.scale_factor
        box_width = self.picks_diameter / display_angpix
        box_halfwidth = int(box_width / 2)

        if str(self.slice_index) in self.mrcdata.coordinates_raw:
            for coordinate in self.mrcdata.coordinates_raw[str(self.slice_index)]:
                ## each coordinate is the center of a box, thus we need to offset by half the gif_box_width pixel length to get the bottom left and top right of the rectangle
                x0 = int(coordinate[0] * self.mrcdata.scale_factor) - box_halfwidth
                y0 = int(coordinate[1] * self.mrcdata.scale_factor) - box_halfwidth
                x1 = int(coordinate[0] * self.mrcdata.scale_factor) + box_halfwidth
                y1 = int(coordinate[1] * self.mrcdata.scale_factor) + box_halfwidth 

                canvas.create_oval(x0, y0, x1, y1, outline=self.picks_color, width=2, tags='particle_positions')
        if DEBUG: print(" %s image coordinates drawn onto canvas" % len(self.coordinates))

        ## also draw nearby picks above & below the current plane 
        ## first, readjust the display depth to be equivalent to the diameter of the particle size widget
        self.picks_display_depth = int((self.picks_diameter / 2) / self.pixel_size )
        for i in range(self.picks_display_depth + 1):
            if i == 0:
                continue 
            adjusted_box_size = int(box_halfwidth * (1-i/self.picks_display_depth))
            positive_slice = i + self.slice_index
            if str(positive_slice) in self.mrcdata.coordinates_raw:
                for coordinate in self.mrcdata.coordinates_raw[str(positive_slice)]:
                    x0 = int(coordinate[0] * self.mrcdata.scale_factor) - adjusted_box_size
                    y0 = int(coordinate[1] * self.mrcdata.scale_factor) - adjusted_box_size
                    x1 = int(coordinate[0] * self.mrcdata.scale_factor) + adjusted_box_size
                    y1 = int(coordinate[1] * self.mrcdata.scale_factor) + adjusted_box_size 
                    canvas.create_oval(x0, y0, x1, y1, outline=self.picks_alt_color, width=2, tags='particle_positions')
            negative_slice = (i*-1) + self.slice_index
            if str(negative_slice) in self.mrcdata.coordinates_raw:
                for coordinate in self.mrcdata.coordinates_raw[str(negative_slice)]:
                    x0 = int(coordinate[0] * self.mrcdata.scale_factor) - adjusted_box_size
                    y0 = int(coordinate[1] * self.mrcdata.scale_factor) - adjusted_box_size
                    x1 = int(coordinate[0] * self.mrcdata.scale_factor) + adjusted_box_size
                    y1 = int(coordinate[1] * self.mrcdata.scale_factor) + adjusted_box_size 
                    canvas.create_oval(x0, y0, x1, y1, outline=self.picks_alt_color, width=2, tags='particle_positions')
        return

    def draw_resolution_ring(self, pixel_coordinate):
        """ Let the user click on an FFT image and draw the corresponding resolution ring
        PARAMETERS
            self = instance of MainUI
            pixel_coordinate = tuple(int(), int()); coordinate of pixel position on the image in question (x, y)
        """
        canvas = self.displayed_widgets[0]
        ## delete any pre-existing resolution ring information
        canvas.delete('ctf_markup')

        ## get the frequency data from the pixel position
        x, y = pixel_coordinate
        displayed_angpix = self.pixel_size / self.scale_factor
        fft_width = canvas.winfo_width()
        fft_height = canvas.winfo_height()
        freq, diff_vector_magnitude = coord2freq(x, y, fft_width, fft_height, displayed_angpix)
        FFT_image_center_coordinate = (int(fft_width / 2), int(fft_height / 2))

        ## use simple logic to place the resolution text on the display in a visible location
        estimated_text_box_size = (60, 20) ## (x, y)
        if pixel_coordinate[0] + estimated_text_box_size[0] > fft_width - 8:
            text_box_x = pixel_coordinate[0] - estimated_text_box_size[0] - 5
        else:
            text_box_x = x
        if pixel_coordinate[1] - estimated_text_box_size[1] < 8 :
            text_box_y = pixel_coordinate[1] + estimated_text_box_size[1] + 8
        else:
            text_box_y = y

        if self.SHOW_CTF.get():
            canvas.create_text(text_box_x + 5, text_box_y - 4, font=("Helvetica", 14), text = "{:.2f}".format(freq) + " Å", fill='red', anchor = tk.SW,  tags='ctf_markup')

            ## draw a guiding line that shows the vector being measured from center of image to the mouse position
            canvas.create_line( FFT_image_center_coordinate, pixel_coordinate, fill='yellow', width=1, tags='ctf_markup') # line goes through the series of points (x0, y0), (x1, y1), … (xn, yn)

            ## draw a guiding circle to indicate the resolution ring being measured
            canvas.create_oval(FFT_image_center_coordinate[0] - int(diff_vector_magnitude), FFT_image_center_coordinate[1] - int(diff_vector_magnitude), FFT_image_center_coordinate[0] + int(diff_vector_magnitude), FFT_image_center_coordinate[1] + int(diff_vector_magnitude), dash = (7,4,2,4 ), width = 2, outline = 'red', tags='ctf_markup') # Creates a circle or an ellipse at the given coordinates. It takes two pairs of coordinates; the top left and bottom right corners of the bounding rectangle for the oval.

        return

    def on_left_mouse_down(self, x, y, DEBUG = False):
        """ Add coordinates to the dictionary at the position of the cursor, then call a redraw.
        """
        mouse_position = x, y

        if DEBUG: print(" Add coordinate: x, y =", mouse_position[0], mouse_position[1])

        self.mrcdata.add_coordinate(self.slice_index, x, y, self.picks_diameter)
        self.draw_image_coordinates()

        return

    def load_file(self):
        """ Permits the system browser to be launched to select an image
            form a directory. Loads the directory and file into their
            respective variables and returns them
        """
        # See: https://stackoverflow.com/questions/9239514/filedialog-tkinter-and-opening-files
        file_w_path = askopenfilename(parent=self.instance, initialdir=".", title='Select file', filetypes=(
                                            # ("All files", "*.*"),
                                            ("MRC/MRCS", "*.mrc *.mrcs"),
                                            (".MRC", "*.mrc"),
                                            (".MRCS", "*.mrcs"),
                                            ))
        if file_w_path:
            try:
                # extract file information from selection
                file_dir, file_name = os.path.split(str(file_w_path))
                print("File selected: ", file_name)
                print("Working directory: ", file_dir)
                self.image_name = file_w_path
                self.working_dir = file_dir
                self.save_star_fname = os.path.join(file_dir, os.path.splitext(file_name)[0] + "_CURATED.star") # suggest a full save path

                ## Pack the image data into the MrcData object
                self.slice_index = 0
                self.mrcdata = MrcData(self.image_name, self.scale_factor, self.lowpass_threshold, self.sigma_contrast)
                self.load_img()

                ## check if settings panel is open, we may want to update the text box 
                if not self.settingsPanel_instance is None:
                    self.settingsPanel_instance.tomo_name_ENTRY.delete(0, tk.END)
                    self.settingsPanel_instance.tomo_name_ENTRY.insert(0, "%s" % os.path.splitext(os.path.split(self.image_name)[1])[0])

                ## SET THE SIZE OF THE PROGRAM WINDOW BASED ON THE SIZE OF THE DATA FRAME AND THE SCREEN RESOLUTION
                self.resize_program_to_fit_screen_or_data()

            except:
                showerror("Open Source File", "Failed to read file\n'%s'" % file_w_path)
            return

    def load_star_coordinates(self, input_file = None):
        """ Permits the system browser to be launched to select an image
            form a directory. Loads the directory and file into their
            respective variables and returns them
        """
        if input_file is None:
            # See: https://stackoverflow.com/questions/9239514/filedialog-tkinter-and-opening-files
            file_w_path = askopenfilename(parent=self.instance, initialdir=".", title='Select file', filetypes=(
                                                # ("All files", "*.*"),
                                                ("STAR", "*.star, *.STAR"),
                                                ))
        else:
            file_w_path = input_file

        if file_w_path:
            try:
                # extract file information from selection
                file_dir, file_name = os.path.split(str(file_w_path))
                print("File selected: ", file_name)
                print("Working directory: ", file_dir)
                self.working_dir = file_dir

                ## Pack the image data into the MrcData object
            except:
                showerror("Open Source File", "Failed to read file\n'%s'" % file_w_path)

            ## parse the data into a dataFrame
            try:
                df = starfile.read(file_w_path)
            except Exception as e:
                print("-----------------------------------------------------------------------------")
                print(" ERROR :: Could not open the star file (%s), is it corrupted?" % file_w_path)
                print("-----------------------------------------------------------------------------")
                print("""e""")

            tomostar_str = self.mrcdata.parse_starfile_df(df)
            self.load_img()
            return

    def next_img(self, direction, DEBUG = False):
        """ Increments the current image index based on the direction given to the function.
        """
        ## Check if an entry widget has focus, in which case do not run this function
        # print(" %s has focus" % self.instance.focus_get())
        active_widget = self.instance.focus_get()
        if isinstance(active_widget, tk.Entry):
            if DEBUG: print(" Entry widget has focus, do not run next_img function")
            return

        ## adjust the index based on the input type
        if direction == 'right':
            self.slice_index += 1
            # reset index to the first image when going past the last image in the list
            if self.slice_index > self.mrcdata.z-1 :
                self.slice_index = 0
        if direction == 'left':
            self.slice_index -= 1
            # reset index to the last image in the list when going past 0
            if self.slice_index < 0:
                self.slice_index = self.mrcdata.z-1

        if DEBUG: print(" Load next image: %s/%s" % (self.slice_index + 1, self.mrcdata.z))
        self.load_img()

        # ## clear global variables for redraw
        # self.reset_globals()

        # ## load image with index 'n'
        # self.load_img()
        return

    def toggle_SHOW_PICKS(self, DEBUG = False):
        """
        """
        if self.SHOW_PICKS.get() == True:
            if DEBUG: print(" Display picked coordinates")
            ## WIP update the display window
        else:
            if DEBUG: print(" Hide picked coordinates")
            ## WIP reload the regular image
        ## draw image coordinates if necessary
        self.draw_image_coordinates()

        return

    def pick_diameter_updated(self, DEBUG = True):
        user_input = self.picks_diameter_ENTRY.get().strip()
        ## cast the input to an integer value
        try:
            user_input = int(user_input)
        except:
            self.picks_diameter_ENTRY.delete(0, tk.END)
            self.picks_diameter_ENTRY.insert(0,self.picks_diameter)
            print(" Input requires integer values > 0")
        ## check if input is in range
        if user_input >= 0:
            if DEBUG: print("particle pick diameter updated: %s" % user_input )
            self.picks_diameter = user_input
            ## pass focus back to the main instance
            self.instance.focus()

            self.next_img('none') ## WIP: redraw whole canvas probably not necessary... instead redraw only the markup?
        else:
            self.picks_diameter_ENTRY.delete(0, tk.END)
            self.picks_diameter_ENTRY.insert(0,self.picks_diameter)
            print(" Input requires positive integer values")
        return

    def toggle_SHOW_SCALEBAR(self):
        """
        """
        ## reload the image since the toggle has been changed
        self.next_img("none")
        return

    def scale_updated(self, DEBUG = True):
        user_input = self.scale_ENTRY.get().strip()
        ## cast the input to a float value
        try:
            user_input = float(user_input)
        except:
            self.scale_ENTRY.delete(0, tk.END)
            self.scale_ENTRY.insert(0,self.scale_factor)
            print(" Input requires float values [10,0]")
        ## check if input is in range (prevent making it too large!)
        if 11 > user_input > 0:
            if DEBUG: print(" set scale factor to %s" % user_input )

            self.clear_display_img()

            ## update the scale factor on the instance
            self.scale_factor = user_input
            ## pass the updated scale factor to the mrcdata object to reprocess the series 
            self.mrcdata.resize_images(self.scale_factor)
            ## pass focus back to the main instance
            self.instance.focus()
            self.next_img('none')
            ## reset the size of the main program
            self.resize_program_to_fit_screen_or_data()

        else:
            self.scale_ENTRY.delete(0, tk.END)
            self.scale_ENTRY.insert(0,self.scale_factor)
            print(" Input requires float values [10,0]")
        return

    def lowpass_threshold_updated(self, DEBUG = True):
        user_input = self.lowpass_threshold_ENTRY.get().strip()
        ## cast the input to an integer value
        try:
            user_input = int(user_input)
        except:
            self.lowpass_threshold_ENTRY.delete(0, tk.END)
            self.lowpass_threshold_ENTRY.insert(0,self.lowpass_threshold)
            print(" Input requires integer values >= 0")
        ## check if input is in range
        if user_input >= 0:
            if DEBUG: print(" Lowpass threshold updated: %s Ang" % user_input )

            self.clear_display_img()
            self.lowpass_threshold = user_input
            ## update the threshold on the mrcdata object 
            self.mrcdata.set_lowpass_threshold(user_input)

            ## pass focus back to the main instance
            self.instance.focus()
            self.next_img('none')
        else:
            self.lowpass_threshold_ENTRY.delete(0, tk.END)
            self.lowpass_threshold_ENTRY.insert(0,self.lowpass_threshold)
            print(" Input requires positive integer values")
        return

    def clear_display_img(self):
        """
        Force the display image to immediately be replaced with a grayscale image, useful as a cue for users while they wait for a long step to finish (i.e. updating the low pass filtering or scale values)
        """
        canvas = self.displayed_widgets[0]
        empty_im_obj = get_PhotoImage_obj(np.ones((canvas.winfo_width(), canvas.winfo_height()), dtype=int) * 100)
        ## update the display data on the class
        self.display_data = [ empty_im_obj ]
        self.load_img_on_canvas(self.displayed_widgets[0], self.display_data[0])
        self.instance.update_idletasks()
        return 

    def sigma_updated(self, DEBUG = True):
        user_input = self.sigma_contrast_ENTRY.get().strip()
        ## cast the input to a float value
        try:
            user_input = float(user_input)
        except:
            self.sigma_contrast_ENTRY.delete(0, tk.END)
            self.sigma_contrast_ENTRY.insert(0,self.sigma_contrast)
            print(" Input requires float values >= 0")
        ## check if input is in range
        if user_input > 0:
            if DEBUG: print(" Sigma contrast updated: %s" % user_input )
            self.sigma_contrast = user_input
            self.mrcdata.set_sigma_contrast(user_input)
            ## pass focus back to the main instance
            self.instance.focus()
            self.next_img('none')
        else:
            self.sigma_contrast_ENTRY.delete(0, tk.END)
            self.sigma_contrast_ENTRY.insert(0,self.sigma_contrast)
            print(" Input requires positive float values")

        return

    def load_img(self, DEBUG = False):
        
        self.pixel_size = self.mrcdata.pixel_size
        # mrc_im_array = self.mrcdata.processed_data[self.slice_index]

        self.mrc_dimensions = (self.mrcdata.x, self.mrcdata.y)

        ## get the image object from the MrcData object
        im_obj = self.mrcdata.processed_data[self.slice_index]
        ## update the display data on the class
        self.display_data = [ im_obj ]
        ## update the raw np array for saving jpgs 
        # self.display_im_arrays = img_contrasted

        ## initialize a canvas if it doesnt exist yet
        if len(self.displayed_widgets) == 0:
            self.add_canvas(self.scrollable_frame, img_obj = im_obj, row = 0, col = 0, canvas_reference = self.displayed_widgets, img_reference = self.display_data)
        else:
            ## otherwise, just update the display data instead of creating a fresh canvas object
            if DEBUG: print(" redraw existing canvas")
            self.load_img_on_canvas(self.displayed_widgets[0], self.display_data[0])

        ## update label/entry widgets
        self.update_display_widgets()

        ## draw image coordinates if necessary
        self.draw_image_coordinates()

        return

    def debugging(self):
        total_coordinates = 0 
        for z in self.mrcdata.coordinates_raw:
            total_coordinates += len(self.mrcdata.coordinates_raw[z])
        print(" %s coordinates picked: " % total_coordinates)
        for z in self.mrcdata.coordinates_raw:
            print("   >> slice %s coords: %s " % (z, self.mrcdata.coordinates_raw[z]))
        # self.rescale_picked_coordinates(0.25, 0.2)
        # coord2freq(450, 450, self.display_data[0].width(), self.display_data[0].height(), self.pixel_size / self.scale_factor)
        return

    def select_all(self, widget):
        """ This function is useful for binding Ctrl+A with
            selecting all text in an Entry widget
        """
        return widget.select_range(0, tk.END)

    def update_display_widgets(self):
        """ Updates the input widgets on the main GUI to take on the values of the global dictionary.
            Mainly used after loading a new settings file.
        """
        self.instance.title("Tomography picker :: " + self.mrcdata.fname)

        self.scale_ENTRY.delete(0, tk.END)
        self.scale_ENTRY.insert(0,self.scale_factor)

        self.lowpass_threshold_ENTRY.delete(0, tk.END)
        self.lowpass_threshold_ENTRY.insert(0,self.lowpass_threshold)

        self.sigma_contrast_ENTRY.delete(0, tk.END)
        self.sigma_contrast_ENTRY.insert(0,self.sigma_contrast)

        self.picks_diameter_ENTRY.delete(0, tk.END)
        self.picks_diameter_ENTRY.insert(0,self.picks_diameter)

        self.MRC_dimensions_LABEL['text'] = "(%s, %s, %s)" % (self.mrcdata.x, self.mrcdata.y, self.slice_index)
        self.MRC_angpix_LABEL['text'] = "%s Å/px" % (self.pixel_size)
        self.MRC_displayed_angpix_LABEL['text'] = "Display @ %0.2f Å/px" % (self.pixel_size / self.scale_factor)

        # self.extract_LABEL['text'] = "%s px" % (int(self.picks_diameter / self.pixel_size) - 1)

        return

    def initialize_scrollable_window(self, viewport_frame):
        self.viewport_canvas = viewport_canvas = tk.Canvas(viewport_frame)
        self.viewport_scrollbar_y = viewport_scrollbar_y = ttk.Scrollbar(viewport_frame, orient="vertical", command=viewport_canvas.yview)
        self.viewport_scrollbar_x = viewport_scrollbar_x = ttk.Scrollbar(viewport_frame, orient="horizontal", command=viewport_canvas.xview)
        self.scrollable_frame = scrollable_frame = ttk.Frame(viewport_canvas)
        self.scrollable_frame.bind("<Configure>", lambda e: viewport_canvas.configure(scrollregion=viewport_canvas.bbox("all")))

        viewport_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.viewport_canvas.configure(yscrollcommand=viewport_scrollbar_y.set, xscrollcommand=viewport_scrollbar_x.set)

        # viewport_frame.grid(row = 1, column = 0)
        # viewport_frame.pack()
        viewport_scrollbar_y.pack(side="right", fill="y")
        viewport_scrollbar_x.pack(side="bottom", fill="x")
        viewport_canvas.pack()#fill="both", expand= True)#(side="left", fill="both", expand=True)


        return scrollable_frame, viewport_canvas

    def initialize_menubar(self, parent):
        """ Create the top menu bar dropdown menus
        """
        ## initialize the top menu bar
        menubar = tk.Menu(parent)
        parent.config(menu=menubar)
        ## dropdown menu --> File
        dropdown_file = tk.Menu(menubar)
        menubar.add_cascade(label="File", menu = dropdown_file)
        dropdown_file.add_command(label="Open .mrc", command=self.load_file)
        dropdown_file.add_command(label="Load .star coordinates", command=self.load_star_coordinates)
        # dropdown_file.add_command(label="Save .gif animation (unidirectional)", command=lambda: self.create_gif_animation(FORMAT = 'unidirectional'))
        # dropdown_file.add_command(label="Save .gif animation (bidirectional)", command=lambda: self.create_gif_animation(FORMAT = 'bidirectional'))
        # dropdown_file.add_command(label="Save .jpg", command=self.save_jpg)
        dropdown_file.add_command(label="Exit", command=self.quit)
        ## dropdown menu --> Options
        dropdown_options = tk.Menu(menubar)
        menubar.add_cascade(label="Options", menu = dropdown_options)
        dropdown_options.add_command(label="Autopick (Ctrl+x)", command= lambda: self.open_panel("AutopickPanel"))
        dropdown_options.add_command(label="Options (Ctrl+z)", command= lambda: self.open_panel("SettingsPanel"))
        return

    def resize(self, event):
        """ Sort through event callbacks and detect if the main UI window has been adjusted manually.
            If so, resize the viewport canvas to fit comfortably within the new dimensions.
        """
        ## find the identity of the widget passing in the event data
        widget = event.widget

        ## if the wiget is the main instance, then use its pixel dimensions to adjust the main canvas viewport window
        if widget == self.instance:

            # if DEBUG:
            #     print(" MainUI dimensions adjusted (%s, %s), resize viewport UI" % (event.height, event.width))

            ## determine offsets to comfortably fit the scrollbar on the right side of the main window
            # h = event.height - 5
            h = event.height - 50#- 18
            w = event.width - 30
            self.viewport_canvas.config(width=w - 140, height=h) ## add width to pad in the right-side panel
        return

    def determine_program_dimensions(self, data_frame, DEBUG = False):
        """ Use the screen size and data frame sizes to determine the best dimensions for the main UI.
        PARAMETERS
            data_frame = ttk.Frame object that holds the main display objects in the primary UI window
        """
        ## get the pixel size of the main data window under control of the scrollbars
        data_x, data_y = data_frame.winfo_width(), data_frame.winfo_height()
        ## get the resolution of the monitor
        screen_x = self.instance.winfo_screenwidth()
        screen_y = self.instance.winfo_screenheight()

        if DEBUG:
            print(" Data window dimensions = (%s, %s); Screen resolution = (%s, %s)" % (data_x, data_y, screen_x, screen_y))

        if data_x > screen_x:
            w = screen_x - 150
        else:
            w = data_x + 150
        
        if data_y > screen_y:
            h = screen_y - 250
        else:
            h = data_y + 30


        ## make a minimim dimension size  
        if w < 430:
            w = 430
        if h < 480:
            h = 480

        return w, h

    def canvas_callback(self, event, DEBUG = False):
        """ Tie events for specific canvases by adding this callback
        """
        if DEBUG: print (" Clicked ", event.widget, "at", event.x, event.y)

        for canvas_obj in self.displayed_widgets:
            if event.widget == canvas_obj:
                # print("MATCH = ", canvas_obj)
                # self.toggle_canvas(canvas_obj)
                self.on_left_mouse_down(event.x, event.y)
        return

    def add_canvas(self, parent, img_obj = None, row = 0, col = 0, canvas_reference = [], img_reference = []):
        """ Dynamically add canvases to the main display UI
        """
        ## prepare the tk.Canvas object
        c = tk.Canvas(parent, width = 150, height = 150, background="gray")

        if img_obj != None:
            ## add the object to the scope of the class by making it a reference to a variable
            img_reference.append(img_obj)
            self.load_img_on_canvas(c, img_obj)
        ## add a on-click callback
        c.bind("<ButtonPress-1>", self.canvas_callback)
        ## pack the widget into the data parent frame
        c.grid(row = row, column = col)

        ## add the canvas to the reference variable for the main UI
        canvas_reference.append(c)
        return

    def destroy_active_canvases(self):
        ## clear the canvas objects in memory
        for canvas_obj in self.displayed_widgets:
            # print(canvas_obj, img_obj)
            # canvas_obj.grid_remove()
            canvas_obj.destroy()

        ## clear the placeholder variable for these objects on the root object
        self.displayed_widgets = []
        return

    def resize_program_to_fit_screen_or_data(self):
        """ Update the widget displaying the data and check the best default screen size for the main UI, then adjust to that size
        """
        self.scrollable_frame.update() ## update the frame holding the data
        w, h = self.determine_program_dimensions(self.scrollable_frame) ## use the frame data & screen resolution to find a reasonable program size
        self.instance.geometry("%sx%s" % (w + 24, h + 24)) ## set the main program size using the updated values
        return

    def quit(self, DEBUG = False):
        if DEBUG:
            print(" CLOSING PROGRAM")
        sys.exit()

    def load_img_on_canvas(self, canvas, img_obj):
        """ PARAMETERS
                self = instance of class
                canvas = tk.Canvas object belonging to self
                img_obj = ImageTk.PhotoImage object belonging to self
        """
        ## place the image object onto the canvas
        # canvas.create_image(0, 0, anchor=tk.NW, image = img_obj)
        x,y = img_obj.width(), img_obj.height()

        canvas.delete('all')
        canvas.create_image(int(x/2) + 1, int(y/2) + 1, image = img_obj)
        ## resize canvas to match new image
        canvas.config(width=x - 1, height=y - 1)
        return

    def make_template_from_picks(self, size_angstroms, DEBUG = True):
        """
            Experimental function to see if I can generate a crude template to help speed up manual picking 
        """
        ## Extract the display image and convert it to a np.array 
        # current_display_img = np.asarray(self.display_data[0])
        # pil_img = ImageTk.getimage(self.display_data[0])
        # pil_img = self.mrcdata.get_processed_slice_unscaled(self.slice_index)
        # 2. Convert the PIL Image to a NumPy array
        # img_array = np.array(pil_img)
        img_array = self.mrcdata.get_processed_slice_unscaled_as_array(self.slice_index)
        

        ## box_size is a value given in Angstroms, we need to convert it to pixels
        # display_angpix = get_scale_factor(self.mrc_dimensions, self.jpg_dimensions) * self.pixel_size / self.scale_factor
        # display_angpix = self.pixel_size / self.scale_factor
        rescaled_box_size = int(size_angstroms / self.pixel_size) # add some padding around the particle 

        ## return None if no coordinates on image 

        if str(self.slice_index) in self.mrcdata.coordinates_raw:
            if len(self.mrcdata.coordinates_raw[str(self.slice_index)]) == 0:
                return None
        else:
            return None # there is not entry for this slice in the raw coordinates dictionary 
        
        # rescaled_coordinates = []
        # for Xcoord, Ycoord in self.mrcdata.coordinates_raw[str(self.slice_index)]:
        #     rescaled_coordinates.append((int(Xcoord * self.scale_factor), int(Ycoord * self.scale_factor)))
        coordinates = self.mrcdata.coordinates_raw[str(self.slice_index)]
        particle_imgs = extract_boxes(img_array, rescaled_box_size, coordinates, DEBUG = DEBUG)

        # print(" input to np sum == ", particle_imgs)
        # merged = np.sum(particle_imgs)
        merged = np.sum(np.stack(particle_imgs), axis =0)

        # Normalised [0,255] as integer: don't forget the parenthesis before astype(int)
        normalized_template = (255*(merged - np.min(merged))/np.ptp(merged)).astype(int)
        # import matplotlib.pyplot as plt
        # plt.figure()
        # plt.imshow(normalized_template, cmap='gray', vmin=0, vmax=255) 
        # plt.show()
        # print(" norm_template shape = ", normalized_template.shape)  
        return normalized_template

    def template_picker(self, template, picking_threshold = 0.3):
        """
            Use an input template to pick on the unscaled original processed image 
            PARAMETERS
                template = np.array (uint8, 0 - 255)
        """
        
        # ## get all the picks so far and add them together before re-normalizing
        # pil_img = ImageTk.getimage(self.display_data[0]).convert("L")
        # # 2. Convert the PIL Image to a NumPy array
        # current_display_img = np.array(pil_img)
        # print(" Extract image details: ", type(current_display_img), np.shape(current_display_img))
        current_img_unscaled = self.mrcdata.get_processed_slice_unscaled_as_array(self.slice_index)

        res, loc = template_match(current_img_unscaled, template, picking_threshold) 
        print(" residual img dimensions :: (x, y) color_range [a, b] -> (%s, %s)  [%s, %s]" % (res.shape[0], res.shape[1], np.min(res), np.max(res)))

        # import matplotlib.pyplot as plt
        # fig,ax=plt.subplots()
        # im=ax.imshow(current_display_img, aspect='equal',interpolation=None)
        # for pt in loc:
        #     ax.add_patch(plt.Circle([pt[0],pt[1]], radius=0.5, edgecolor='r',lw=3, fill=False))
        # cbar=plt.colorbar(im)
        # plt.show()

        
        # ## For performance probably want to run the check with fewer calculations per cycle, so pre-calculate the halfbox size, then for each point run a range intersection check for X, if it passes then Y, then if it does not intersect with both add the coordinate a a separate list we later call to add points (to avoid growth of the search set during loop, input coordinates are expected NOT to intersect!)
        # display_angpix = self.pixel_size / self.scale_factor 
        # particle_width = self.picks_diameter / display_angpix
        # particle_halfwidth = int(particle_width / 2)
        # picks_to_keep = []
        # for i in range(len(loc)):
        #     ADD_POINT = True
        #     x, y, score = loc[i]


        #     if str(self.slice_index) in self.mrcdata.coordinates_raw:
        #         if not len(self.mrcdata.coordinates_raw[str(self.slice_index)]) == 0:
        #             for px, py in self.mrcdata.coordinates_raw[str(self.slice_index)]:
        #                 ## coordinates need to be rescaled to the viewing image scale 
        #                 rescaled_x = int(px * self.scale_factor)
        #                 rescaled_y = int(py * self.scale_factor)

        #                 ## run the fast intersection algorithm for X, then Y
        #                 if check_if_two_ranges_intersect(x - particle_halfwidth, x + particle_halfwidth, rescaled_x - particle_halfwidth, rescaled_x + particle_halfwidth):
        #                     if check_if_two_ranges_intersect(y - particle_halfwidth, y + particle_halfwidth, rescaled_y - particle_halfwidth, rescaled_y + particle_halfwidth):
        #                         ## if we pass both checks, we have a clash situation - abandon adding this point to the final roster without further checks 
        #                         ADD_POINT = False
        #     ## use the flag to decide whether we add the point 
        #     if ADD_POINT:
        #         picks_to_keep.append(i)

        # ## add each point we wanted to keep to the final set of coordinates after fishing the looping functions 
        # for p in picks_to_keep:
        #     x, y, score = loc[p]
        #     # self.add_coordinate(x, y, score)
        #     self.mrcdata.add_coordinate(self.slice_index,x,y, box_width=-1)

        for i in range(len(loc)):
            x, y, score = loc[i]
            self.mrcdata.add_coordinate(self.slice_index,x,y, box_width=-1, SCALE_FACTOR=1)

        ## determine the minimum threshold score and set the slider there so we see all points added after running this command 
        # lowest_score = min(loc, key=lambda p:p[2])[2]
        # self.picks_threshold = lowest_score
        # self.threshold_LABEL['text'] = "Threshold: %0.2f" % lowest_score

        self.draw_image_coordinates()
        return

    def MouseWheelHandler(self, event):
        """ See: https://stackoverflow.com/questions/17355902/python-tkinter-binding-mousewheel-to-scrollbar
            Tie the mousewheel to the brush size, draw a green square to show the user the final setting
        """

        canvas = self.displayed_widgets[0]

        def delta(event):
            if event.num == 5 or event.delta < 0:
                return -2
            return 2

        self.brush_size += delta(event)

        ## avoid negative brush_size values
        if self.brush_size <= 0:
            self.brush_size = 0

        ## draw new brush size
        x, y = event.x, event.y
        x_max = int(x + self.brush_size/2)
        x_min = int(x - self.brush_size/2)
        y_max = int(y + self.brush_size/2)
        y_min = int(y - self.brush_size/2)

        ## delete any pre-existing brushes if already drawn
        canvas.delete('brush')

        brush = canvas.create_rectangle(x_max, y_max, x_min, y_min, outline="green2", width=2, tags='brush')

        self.instance.after(250, lambda: canvas.delete('brush'))
        
        return 

    def on_middle_mouse_press(self, event):
        """ When the user clicks the middle mouse, hide all coordinates
        """
        print(" Middle mouse pressed")
        canvas = self.displayed_widgets[0]
        canvas.delete('brush')
        # canvas.delete('marker')
        canvas.delete('particle_positions')
        return

    def on_middle_mouse_release(self, event):
        """ When the middle mouse is released, redraw all coordinates
        """
        print(" Middle mouse released")
        self.draw_image_coordinates()
        return

    def on_right_mouse_press(self, event, DEBUG = False):
        if DEBUG:
            print()
            print("===========================")
            print(" On right mouse press")
            print("---------------------------")
        image_name = os.path.splitext(self.image_name)[0]
        if image_name == None or image_name == '':
            return 

        canvas = self.displayed_widgets[0]
        self.RIGHT_MOUSE_PRESSED = True
    
        x, y = event.x, event.y
        box_halfwidth = int(self.brush_size / 2)
        x_max = int(x + box_halfwidth)
        x_min = int(x - box_halfwidth)
        y_max = int(y + box_halfwidth)
        y_min = int(y - box_halfwidth)
        brush = canvas.create_rectangle(x_max, y_max, x_min, y_min, outline="green2", tags='brush')

        # print("mouse position = ", x, y)
        # print("(x min, x max ; y min, y max) = ", x_min, x_max, y_min, y_max)

        ## particle diameter is a value given in Angstroms, we need to convert it to pixels
        # display_angpix = get_scale_factor(self.mrc_dimensions, self.jpg_dimensions) * self.pixel_size / self.scale_factor
        display_angpix = self.pixel_size / self.scale_factor
        particle_width = self.picks_diameter / display_angpix
        particle_halfwidth = int(particle_width / 2)

        # ## get the loaded coordinates for the image 
        # try:
        #     image_coordinates = self.coordinates[image_name]
        # except:
        #     print(" Could not load coordinates for img (%s), perhaps no particle file was loaded yet" % image_name)
        #     return
        
        # image_coordinates = self.coordinates
        # print(" image coords = ", image_coordinates)

        ## in case the user does not move the mouse after right-clicking, we want to find all clashes in range on this event as well
        erase_coordinates = [] # avoid changing dictionary until after iteration complete
        ## find all coordinates that clash with the brush
        if str(self.slice_index) in self.mrcdata.coordinates_raw:
            if len(self.mrcdata.coordinates_raw[str(self.slice_index)]) > 0:
                for coord in self.mrcdata.coordinates_raw[str(self.slice_index)]:
                    ## rescale the stored coordinates to match the viewing scale 
                    rescaled_x = int(coord[0] * self.scale_factor)
                    rescaled_y = int(coord[1] * self.scale_factor)

                    if check_if_two_ranges_intersect(rescaled_x - particle_halfwidth, rescaled_x + particle_halfwidth, x_min, x_max, DEBUG = False): # x0, x1, y0, y1
                        if check_if_two_ranges_intersect(rescaled_y - particle_halfwidth, rescaled_y + particle_halfwidth, y_min, y_max, DEBUG = False): # x0, x1, y0, y1
                            if DEBUG:
                                print(" Erase coordinate:")
                                print("   brush center (%s, %s), brush limits x = (%s -> %s) & y = (%s -> %s)" % (x, y, x_min, x_max, y_min, y_max))
                                print("   coordinate center (%s, %s)" % (rescaled_x, rescaled_y))
                            erase_coordinates.append(coord)

        # if len(self.coordinates) > 0:
        #     for coord in self.coordinates:
        #         ## rescale the stored coordinates to match the viewing scale 
        #         rescaled_x = int(coord[0] * self.scale_factor)
        #         rescaled_y = int(coord[1] * self.scale_factor)

        #         if check_if_two_ranges_intersect(rescaled_x - particle_halfwidth, rescaled_x + particle_halfwidth, x_min, x_max, DEBUG = False): # x0, x1, y0, y1
        #             if check_if_two_ranges_intersect(rescaled_y - particle_halfwidth, rescaled_y + particle_halfwidth, y_min, y_max, DEBUG = False): # x0, x1, y0, y1
        #                 print(" Erase coordinate:")
        #                 print("   brush center (%s, %s), brush limits x = (%s -> %s) & y = (%s -> %s)" % (x, y, x_min, x_max, y_min, y_max))
        #                 print("   coordinate center (%s, %s)" % (rescaled_x, rescaled_y))
        #                 erase_coordinates.append(coord)

        for (x, y) in erase_coordinates:
            self.mrcdata.remove_coordinate(self.slice_index, x, y)

        # ## erase all coordinates caught by the brush
        # for coord in erase_coordinates:
        #     del self.coordinates[coord] #1 remove the coordinate that clashed
        # print(" # coordinates to erase:", len(erase_coordinates))

        self.draw_image_coordinates()
        return

    def on_right_mouse_release(self, event, DEBUG = False):
        """ Delete the green brush after the user stops erasing and reset the global flag
        """
        if DEBUG: print("Right mouse released")
        canvas = self.displayed_widgets[0]
        self.RIGHT_MOUSE_PRESSED = False
        canvas.delete('brush') # remove any lingering brush marker
        return
    
    def refresh_brush_cursor(self, event, DEBUG = False):
        """ This function is tied to the <Motion> event.
            It constantly checks if the condition RIGHT_MOUSE_PRESSED is True, in which case it runs the erase-coordinates algorithm
        """        
        if self.RIGHT_MOUSE_PRESSED:
            image_name = os.path.splitext(self.image_name)[0]
            if image_name == None or image_name == '':
                return 

            canvas = self.displayed_widgets[0]

            # ## get the loaded coordinates for the image 
            # try:
            #     image_coordinates = self.coordinates[image_name]
            # except:
            #     print(" Could not load coordinates for img (%s), perhaps no particle file was loaded yet" % image_name)
            #     return 
            # image_coordinates = self.coordinates

            x, y = event.x, event.y

            canvas.delete('brush')

            ## box_size is a value given in Angstroms, we need to convert it to pixels
            box_halfwidth = int(self.brush_size / 2)

            x_max = int(x + box_halfwidth)
            x_min = int(x - box_halfwidth)
            y_max = int(y + box_halfwidth)
            y_min = int(y - box_halfwidth)

            brush = canvas.create_rectangle(x_max, y_max, x_min, y_min, outline="green2", tags='brush')

            ## particle diameter is a value given in Angstroms, we need to convert it to pixels
            # display_angpix = get_scale_factor(self.mrc_dimensions, self.jpg_dimensions) * self.pixel_size / self.scale_factor
            display_angpix = self.pixel_size / self.scale_factor
            particle_width = self.picks_diameter / display_angpix
            particle_halfwidth = int(particle_width / 2)

            ## in case the user does not move the mouse after right-clicking, we want to find all clashes in range on this event as well
            erase_coordinates = [] # avoid changing dictionary until after iteration complete
            ## find all coordinates that clash with the brush
            if str(self.slice_index) in self.mrcdata.coordinates_raw:
                if len(self.mrcdata.coordinates_raw[str(self.slice_index)]) > 0:
                    for coord in self.mrcdata.coordinates_raw[str(self.slice_index)]:
                        ## rescale the stored coordinates to match the viewing scale 
                        rescaled_x = int(coord[0] * self.scale_factor)
                        rescaled_y = int(coord[1] * self.scale_factor)

                        if check_if_two_ranges_intersect(rescaled_x - particle_halfwidth, rescaled_x + particle_halfwidth, x_min, x_max, DEBUG = False): # x0, x1, y0, y1
                            if check_if_two_ranges_intersect(rescaled_y - particle_halfwidth, rescaled_y + particle_halfwidth, y_min, y_max, DEBUG = False): # x0, x1, y0, y1
                                if DEBUG:
                                    print(" Erase coordinate:")
                                    print("   brush center (%s, %s), brush limits x = (%s -> %s) & y = (%s -> %s)" % (x, y, x_min, x_max, y_min, y_max))
                                    print("   coordinate center (%s, %s)" % (rescaled_x, rescaled_y))
                                erase_coordinates.append(coord)

            for (x, y) in erase_coordinates:
                self.mrcdata.remove_coordinate(self.slice_index, x, y)

            # erase_coordinates = [] # avoid changing dictionary until after iteration complete
            # ## find all coordinates that clash with the brush
            # if len(self.coordinates) > 0:
            #     for coord in self.coordinates:
            #         ## rescale the coordinates back to the viewing scale 
            #         rescaled_x = int(coord[0] * self.scale_factor)
            #         rescaled_y = int(coord[1] * self.scale_factor)

            #         if check_if_two_ranges_intersect(rescaled_x - particle_halfwidth, rescaled_x + particle_halfwidth, x_min, x_max): # x0, x1, y0, y1
            #             if check_if_two_ranges_intersect(rescaled_y - particle_halfwidth, rescaled_y + particle_halfwidth, y_min, y_max): # x0, x1, y0, y1
            #                 erase_coordinates.append(coord)
            # ## erase all coordinates caught by the brush
            # for coord in erase_coordinates:
            #     del self.coordinates[coord] # remove the coordinate that clashed

            self.draw_image_coordinates()
        else:
            return


#endregion

#region Panel Autopicking Menu
class AutopickPanel(MainUI):
    """ Panel GUI for user options for autopicking
    """
    def __init__(self, mainUI): # Pass in the main window as a parameter so we can access its methods & attributes
        self.mainUI = mainUI # Make the main window an attribute of this Class object
        self.panel = tk.Toplevel() # Make this object an accessible attribute
        self.panel.title('Autopicking')
        # self.panel.geometry('500x310')
        # self.viewport_frame = viewport_frame =  ttk.Frame(self.panel)
        
        ## shift the window to pop up just right and a little down of the main window by default 
        mainUI_x_limit = mainUI.instance.winfo_rootx() + mainUI.instance.winfo_width()
        mainUI_y = mainUI.instance.winfo_rooty() + 200
        self.panel.geometry(f"+{mainUI_x_limit}+{mainUI_y}") #= "+%d+%d" % (x,y+height)

        ## Parameters 
        self.loaded_template_im_array = None
        self.loaded_template_displayObj = None
        self.canvas_size = 150 # px
        self.picking_threshold = 0.1
        self.gaussian_disk_diameter = int(self.mainUI.picks_diameter * 0.8)
        self.template_size = int(self.mainUI.picks_diameter * 1.2) # angstroms

        ## Define widgets

        ## 1. buttons area 
        self.generate_template_from_picks_button = tk.Button(self.panel, text="Template from picks", font = ('Helvetica', '9'), command = lambda: self.generate_template_from_picks(), width=18)
        self.load_template_button = tk.Button(self.panel, text="Load template", font = ('Helvetica', '10'), command = lambda: self.load_template_from_file(), width=10)
        self.save_template_button = tk.Button(self.panel, text="Save template", font = ('Helvetica', '10'), command = lambda: self.save_template(), width=10)
        self.autopick_button = tk.Button(self.panel, text="Autopick", font = ('Helvetica', '12'), command = lambda: self.submit_autopicker_job(), width=10)
        self.clear_coordinates_button = tk.Button(self.panel, text="Clear picks", font = ('Helvetica', '9'), command = lambda: self.clear_picked_coordinates(), width=10)
        self.gaussian_disk_BUTTON = tk.Button(self.panel, text="Gaussian (Å)", font = ('Helvetica', '9'), command = lambda: self.create_gaussian_disk(), width=16)
        self.gaussian_disk_diameter_ENTRY = tk.Entry(self.panel, width=6, font=("Helvetica", '9'), justify='right')
        self.gaussian_disk_diameter_ENTRY.insert(tk.END, "%s" % self.gaussian_disk_diameter)
        self.template_size_ENTRY = tk.Entry(self.panel, width=6, font=("Helvetica", '9'), justify='right')
        self.template_size_ENTRY.insert(tk.END, "%s" % self.template_size)
        self.template_size_LABEL = tk.Label(self.panel, text = 'Template size (Å):', anchor = tk.S, font = ('Helvetica', '9'))
        self.clear_z_clashes_BUTTON = tk.Button(self.panel, text="Remove Z clashes", font = ('Helvetica', '9'), command = lambda: self.clear_z_clashes(), width=16)


        ## 2. threshold slider
        self.threshold_label = tk.Label(self.panel, text = 'Threshold:', anchor = tk.S, font = ('Helvetica', '9'))
        self.threshold_slider = tk.Scale(self.panel, from_=0, to=0.5, resolution=0.01, orient= tk.HORIZONTAL, length = 250, sliderlength = 20, command=self.on_threshold_change)
        self.threshold_slider.set(self.picking_threshold)

        
        ## 3. canvas for template
        self.canvas_label = tk.Label(self.panel, text = 'Template loaded:', anchor = tk.S, font = ('Helvetica', '10'))
        self.canvas = tk.Canvas(self.panel, width = self.canvas_size, height = self.canvas_size, background="gray")

        ## 4. separator widgets for aesthetics 
        self.separator1 = ttk.Separator(self.panel, orient='horizontal')
        self.separator2 = ttk.Separator(self.panel, orient='horizontal')
        self.separator3 = ttk.Separator(self.panel, orient='horizontal')


        ## Pack widgets, dynamic rows to ease adjusting later 
        # row 0
        current_row = 0
        self.gaussian_disk_BUTTON.grid(column = 0, columnspan=2, row = current_row, pady=2, padx=3, sticky=tk.E)
        self.gaussian_disk_diameter_ENTRY.grid(column = 2, columnspan=1,row = current_row, sticky=tk.W)
        # row 
        current_row += 1
        ttk.Separator(self.panel, orient='horizontal').grid(column = 0, row = current_row, columnspan = 6, pady=2, sticky=tk.EW)
        # row
        current_row += 1
        self.generate_template_from_picks_button.grid(column = 0, columnspan=2, row = current_row, pady = 7, padx=5)
        self.load_template_button.grid(column = 2, columnspan=2, row = current_row, pady = 7, padx=5)
        self.save_template_button.grid(column = 4, columnspan=2, row = current_row, pady = 7, padx=5)
        # row
        current_row += 1
        self.template_size_LABEL.grid(column = 0, columnspan=2, row = current_row, sticky=tk.E)
        self.template_size_ENTRY.grid(column = 2, row = current_row, sticky=tk.W)
        # row 
        current_row += 1
        self.separator2.grid(column = 0, row = current_row, columnspan = 6, sticky=tk.EW)
        # row 
        current_row += 1
        self.canvas_label.grid(column = 0, row = current_row, columnspan = 6, sticky=tk.W, pady=5, padx=10)
        # row 
        current_row += 1
        self.canvas.grid(column = 0, row = current_row, columnspan = 6, pady=5)
        # # row 
        # current_row += 1
        # self.separator1.grid(column = 0, row = current_row, columnspan = 3, sticky=tk.EW)
        # row
        current_row +=1 
        self.threshold_label.grid(column = 0, row = current_row, columnspan = 1, sticky=tk.SE)
        self.threshold_slider.grid(column=1, row=current_row, columnspan = 5, padx=5, sticky=tk.W)
        # row
        current_row +=1 
        self.autopick_button.grid(column=0, columnspan=6, row= current_row, pady=10)
        # row  
        current_row += 1
        ttk.Separator(self.panel, orient='horizontal').grid(column = 0, row = current_row, columnspan = 6, pady=2, sticky=tk.EW)
        # row  
        current_row += 1
        self.clear_z_clashes_BUTTON.grid(column=0, columnspan=2,row=current_row, padx = 10, pady=2)
        self.clear_coordinates_button.grid(column=2, columnspan=2, row=current_row, padx = 10, pady=2)

        ## Add some hotkeys for ease of use
        # self.threshold_slider.bind('<Left>', lambda event: self.cutoff_slider.set(self.cutoff_slider.get() - 0.1))
        # self.threshold_slider.bind('<Right>', lambda event: self.cutoff_slider.set(self.cutoff_slider.get() + 0.1))
        # self.panel.bind('<Return>', lambda event: self.submit_autopicker_job())
        # self.panel.bind('<KP_Enter>', lambda event: self.submit_autopicker_job()) # numpad 'Return' key
        self.template_size_ENTRY.bind('<Control-KeyRelease-a>', lambda event: self.mainUI.select_all(self.template_size_ENTRY))
        self.template_size_ENTRY.bind('<Return>', lambda event: self.template_size_updated())
        self.template_size_ENTRY.bind('<KP_Enter>', lambda event: self.template_size_updated())
        self.gaussian_disk_diameter_ENTRY.bind('<Return>', lambda event: self.create_gaussian_disk())
        self.gaussian_disk_diameter_ENTRY.bind('<KP_Enter>', lambda event: self.create_gaussian_disk())


        ## Set focus to the panel
        self.panel.focus()

        ## add an exit function to the closing of this top level window
        self.panel.protocol("WM_DELETE_WINDOW", self.close)

        return

    def create_gaussian_disk(self):
        ## read the entry widget and update the value on the instance 
        try:
            diameter_ang = int(self.gaussian_disk_diameter_ENTRY.get())
            self.gaussian_disk_diameter = diameter_ang
        except:
            self.gaussian_disk_diameter_ENTRY.delete(0, tk.END)
            self.gaussian_disk_diameter_ENTRY.insert(0, "int")
            return 
        ## get the signal range based on the display image values at the first and last quarter of the loaded image
        current_img_slice = self.mainUI.mrcdata.get_processed_slice_unscaled_as_array(self.mainUI.slice_index)  
        background_grayscale = np.percentile(current_img_slice, 75) 
        particle_grayscale = np.percentile(current_img_slice, 25)

        print(" Generate a gaussian disk of %s Ang diameter (background grayscale = %s)" % (diameter_ang, background_grayscale))
        display_angpix = self.mainUI.pixel_size # get_scale_factor(self.mainUI.mrc_dimensions, self.mainUI.jpg_dimensions) * self.mainUI.pixel_size / self.mainUI.scale_factor
        # rescaled_box_size = int(self.mainUI.picks_diameter * 1.2  / display_angpix) # add some padding around the particle 

        gauss_diameter_px = int(self.gaussian_disk_diameter / display_angpix)
        disk = gaussian_disk(gauss_diameter_px, int(gauss_diameter_px * 1.25), background_color = background_grayscale)
        self.loaded_template_im_array = disk 
        self.display_template()
        return 

    def close(self):
        ## unset the panel instance before destroying this instance
        self.mainUI.autopickPanel_instance = None
        ## destroy this instance
        self.panel.destroy()
        return

    def display_template(self, DEBUG = True):
        """ Load the template from memory onto the canvas 
        """
        ## get the proper references 
        im_array = self.loaded_template_im_array
        canvas = self.canvas
        canvas_size = self.canvas_size

        ## determine the scaling factor for the template so it nicely fits the canvas dimensions 
        im_size = im_array.shape[0] ## expect a square dimension so only look at x 
        canvas_size = 150 # px 
        scaling_factor = canvas_size / im_size

        if DEBUG:
            print(" Display template in widget:")
            print("    template size = %s" % im_size)
            print("    canvas size = %s" % canvas_size)
            print("    scaling factor to fit image onto canvas = %s" % scaling_factor)

        ## scale the image appropriately 
        scaled_im_array = resize_image(im_array.astype(np.float32), scaling_factor)

        ## load the image into a PhotoImage object for display and update the reference to it  
        im_obj = get_PhotoImage_obj(scaled_im_array)
        self.loaded_template_displayObj = im_obj

        ## clean up the canvas and display the new object 
        self.canvas.delete('all')
        
        self.canvas.create_image(int(canvas_size/2) + 1, int(canvas_size/2) + 1, image = self.loaded_template_displayObj)
        ## resize canvas to match new image
        self.canvas.config(width=canvas_size - 1, height=canvas_size - 1)
        return

    def submit_autopicker_job(self):
        """ Pass the input parameters back to the mainUI to run the autopicker algorithm
        """
        if not isinstance(self.loaded_template_im_array, np.ndarray):
            print(" No template loaded for autopicking!")
            return
        # template = self.mainUI.make_template_from_picks()
        else:
            print(" Submitting autopick job with template: ", self.loaded_template_im_array.shape)
            self.clear_picked_coordinates()
            self.mainUI.template_picker(self.loaded_template_im_array, float(self.threshold_slider.get()))
            self.mainUI.focus_get()
        return
    
    def generate_template_from_picks(self):
        template = self.mainUI.make_template_from_picks(self.template_size)
        if isinstance(template, bool):
            return 
        self.loaded_template_im_array = template 
        self.display_template()
        return 

    def save_template(self, outfname = 'template.png'):
        """ Write out the loaded template as a .PNG 
        """
        ## later add a gui to save the file explicitly 
        # print(" TEST :: ", self.loaded_template_im_array.shape, type(self.loaded_template_im_array))

        if not isinstance(self.loaded_template_im_array, np.ndarray):
            print(" No template loaded to save out!")
            return

        filetypes = [("PNG","*.png"),("All Files","*.*")]
        save_path = asksaveasfilename(parent = self.panel, initialfile = "%s" % outfname, defaultextension=".png", filetypes=filetypes)

        cv2.imwrite(save_path, self.loaded_template_im_array)
        print(" Written currently loaded template out: ")
        print("   >> %s" % os.path.abspath(outfname))
        return 
    
    def load_template(self, fpath):
        ## later add a gui to select the file explicitly 
        filename = fpath #'template.png'

        ## use cv2 to load the image data then cast it as an integer np.ndarray
        cv_im = cv2.imread(filename, cv2.IMREAD_GRAYSCALE)
        im_array = np.array(cv_im).astype(np.uint8)

        ## assign the array to the template container
        self.loaded_template_im_array = im_array 
        self.display_template()

        print(" Loading template image: ")
        print("   >> %s" % os.path.abspath(filename))

        return 

    def load_template_from_file(self):
        """ Permits the system browser to be launched to select an image
            form a directory. Loads the directory and file into their
            respective variables and returns them
        """
        file_w_path = askopenfilename(parent=self.panel, initialdir=".", title='Select file', filetypes=( ("PNG", "*.png *.PNG"), ("All files", "*.*")) 
                                      )
        if file_w_path:
            try:
                self.load_template(file_w_path)

            except:
                showerror("Open Source File", "Failed to read file\n'%s'" % file_w_path)
            return

    def template_size_updated(self):
        user_input = self.template_size_ENTRY.get().strip()
        ## cast the input to an int value
        try:
            user_input = int(user_input)
        except:
            self.template_size_ENTRY.delete(0, tk.END)
            self.template_size_ENTRY.insert(0,self.template_size)
            print(" Input requires int values")

        self.template_size = user_input
        self.generate_template_from_picks()
        return 

    def on_threshold_change(self, slider_value):

        ## set the threshold value to the instance 
        self.picks_threshold = slider_value
        print(" Template picking threshold = %s" % slider_value )

        return 

    def clear_picked_coordinates(self):
        self.mainUI.mrcdata.clear_coordinates_from_slice(self.mainUI.slice_index)
        self.mainUI.load_img()
        return 

    def clear_z_clashes(self):
        self.mainUI.mrcdata.remove_clashes_above_below(self.mainUI.slice_index, self.mainUI.picks_diameter)
        self.mainUI.load_img()
        return 

#endregion 

#region Panel Settings Menu
class SettingsPanel(MainUI):
    def __init__(self, mainUI): # Pass in the main window as a parameter so we can access its methods & attributes
        self.mainUI = mainUI # Make the main window an attribute of this Class object
        self.panel = tk.Toplevel() # Make this object an accessible attribute
        self.panel.title('Settings')
        # self.panel.geometry('500x310')
        # self.viewport_frame = viewport_frame =  ttk.Frame(self.panel)
        
        ## shift the window to pop up just right of the main window by default 
        mainUI_x_limit = mainUI.instance.winfo_rootx() + mainUI.instance.winfo_width()
        mainUI_y = mainUI.instance.winfo_rooty() -50 
        self.panel.geometry(f"+{mainUI_x_limit}+{mainUI_y}") #= "+%d+%d" % (x,y+height)

        ## Parameters 

        ## Define widgets
        self.write_point_txt_file_BUTTON = tk.Button(self.panel, text="Write points txt", font = ('Helvetica', '9'), command = lambda: self.write_point_txt_file(), width=18)
        self.tomo_name_LABEL = tk.Label(self.panel, text = 'Tomo name:', anchor = tk.S, font = ('Helvetica', '9'))
        self.tomo_name_ENTRY = tk.Entry(self.panel, width=40, font=("Helvetica", '9'), justify='left')
        self.tomo_name_ENTRY.insert(tk.END, "%s" % os.path.splitext(os.path.split(self.mainUI.image_name)[1])[0])

        self.shift_coords_LABEL = tk.Label(self.panel, text = 'Shift coordinates:', anchor = tk.SW, font = ('Helvetica', '9'))
        coord_shift_button_size = 6
        self.shift_z_up_BUTTON = tk.Button(self.panel, text="Z-", font = ('Helvetica', '9'), command = lambda: self.shift_coordinates('z', -1), width=coord_shift_button_size)
        self.shift_z_down_BUTTON = tk.Button(self.panel, text="Z+", font = ('Helvetica', '9'), command = lambda: self.shift_coordinates('z', 1), width=coord_shift_button_size)
        self.flip_z_BUTTON = tk.Button(self.panel, text="flipZ", font = ('Helvetica', '9'), command = lambda: self.shift_coordinates('z', 'flip'), width=coord_shift_button_size)
        self.shift_x_left_BUTTON = tk.Button(self.panel, text="X-", font = ('Helvetica', '9'), command = lambda: self.shift_coordinates('x', -1), width=coord_shift_button_size)
        self.shift_x_right_BUTTON = tk.Button(self.panel, text="X+", font = ('Helvetica', '9'), command = lambda: self.shift_coordinates('x', 1), width=coord_shift_button_size)
        self.shift_y_up_BUTTON = tk.Button(self.panel, text="Y-", font = ('Helvetica', '9'), command = lambda: self.shift_coordinates('y', -1), width=coord_shift_button_size)
        self.shift_y_down_BUTTON = tk.Button(self.panel, text="Y+", font = ('Helvetica', '9'), command = lambda: self.shift_coordinates('y', 1), width=coord_shift_button_size)

        ## Pack widgets, dynamic rows to ease adjusting later 
        # row 0
        current_row = 0
        self.tomo_name_LABEL.grid(column = 0, columnspan=3, row = current_row, pady=1, padx=3, sticky=tk.W)
        # row 
        current_row += 1
        self.tomo_name_ENTRY.grid(column = 0, columnspan=4, row = current_row, pady=1, padx=3)
        # row 
        current_row += 1
        ttk.Separator(self.panel, orient='horizontal').grid(column = 0, row = current_row, columnspan = 6, pady=2, sticky=tk.EW)
        # row 
        current_row +=1 
        self.write_point_txt_file_BUTTON.grid(column = 0, columnspan=3, row = current_row, pady=2, padx=3, sticky=tk.W)
        # row 
        current_row += 1
        ttk.Separator(self.panel, orient='horizontal').grid(column = 0, row = current_row, columnspan = 6, pady=2, sticky=tk.EW)
        # row 
        current_row += 1
        self.shift_coords_LABEL.grid(column = 0, row = current_row)
        # row 
        current_row += 1
        self.shift_z_up_BUTTON.grid(column = 3, row = current_row)
        self.shift_y_up_BUTTON.grid(column = 1, row = current_row)
        # row 
        current_row += 1
        self.shift_x_left_BUTTON.grid(column = 0, row = current_row, sticky=tk.E)
        self.shift_x_right_BUTTON.grid(column = 2, row = current_row, sticky=tk.W)
        self.flip_z_BUTTON.grid(column=3, row = current_row)
        # row 
        current_row += 1
        self.shift_z_down_BUTTON.grid(column = 3, row = current_row)
        self.shift_y_down_BUTTON.grid(column = 1, row = current_row)


        ## Add some hotkeys for ease of use
        # self.panel.bind('<Left>', lambda event: self.cutoff_slider.set(self.cutoff_slider.get() - 1))
        # self.panel.bind('<Right>', lambda event: self.cutoff_slider.set(self.cutoff_slider.get() + 1))
        # self.panel.bind('<Return>', lambda event: self.submit_autopicker_job())
        # self.panel.bind('<KP_Enter>', lambda event: self.submit_autopicker_job()) # numpad 'Return' key

        ## Set focus to the panel
        self.panel.focus()

        ## add an exit function to the closing of this top level window
        self.panel.protocol("WM_DELETE_WINDOW", self.close)

        return

    def close(self):
        ## unset the panel instance before destroying this instance
        self.mainUI.settingsPanel_instance = None
        ## destroy this instance
        self.panel.destroy()
        return

    def write_point_txt_file(self):
        print(" WIP : Write points to txt file for use with IMOD point2model > 3dmod rendering")

        ## initialize the file 
        suggested_fname = self.mainUI.image_name + ".txt"
        print(" write txt file: ", suggested_fname)

        with open(suggested_fname, 'w', newline='\n', encoding='utf-8') as f:
            counter = 0
            for slice in self.mainUI.mrcdata.coordinates_raw:
                for coord in self.mainUI.mrcdata.coordinates_raw[slice]:
                    counter += 1
                    x, y = coord
                    z = int(slice)
                    f.write(" %s   %s   %s \n" % (x, y, z))

        print(" Use the points .txt file to view in 3dmod via:")
        print("     $ point2model %s %s.mod" % (suggested_fname, suggested_fname))
        print("")

        return 

    def shift_coordinates(self, axis, dist):
        print(" shift %s by %s" % (axis, dist))
        self.mainUI.mrcdata.shift_coordinates_by_axis(axis, dist)
        self.mainUI.draw_image_coordinates()
        self.mainUI.instance.focus()
        return 


##########################
### RUN BLOCK
##########################
if __name__ == '__main__':

    input_scale, input_lowpass, input_sigma, input_file, input_threads, coord_file = parse_cmdline(sys.argv)

    usage()

    root = tk.Tk()
    app = MainUI(root, input_scale, input_lowpass, input_sigma, input_file, input_threads, coord_file)
    root.mainloop()
