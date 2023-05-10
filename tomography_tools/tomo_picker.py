#!/usr/bin/env python3

## Author: Alexander Keszei
## 2022-05-09: Version 1 adapted from mrc_viewer.py to take in large raw tomo stack files 
"""
To Do:
    - Clean up unused functions
    - Re-implement save_jpg function and Ctrl + s hotkey
    - Are top functions best packed into MrcData object?
""" 

def usage():
    print("================================================================================================")
    print(" Open a stack of MRC/MRCS images and load their processed images into buffer. Use left/right ")
    print(" up/down arrows to navigate through the stack. You can click on particles of interest and ")
    print(" use Ctrl + e to extract them into a new .MRCS file useable by downstream programs:")
    print("    $ tomo_picker.py  <input>.mrcs")
    print("------------------------------------------------------------------------------------------------")
    print(" Can set options on loadup to bypass defaults: ")
    print("           --scale (0.2) : rescale displayed frame images by a value in range (0,inf)")
    print("          --lowpass (10) : set lowpass filter")
    print("             --sigma (3) : set sigma filter contrast ")
    print("------------------------------------------------------------------------------------------------")
    print(" Keyboard shortcuts: ")
    print("    Ctrl + e : Save out a '..._extracted.mrcs' file with picked coordinates across the stack")
    print("    Ctrl + q : Quit program")
    print("================================================================================================")
    return 

def sigma_contrast(im_array, sigma, DEBUG = True):
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

def lowpass(img, threshold, pixel_size, DEBUG = True):
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

    # lowpassed, ctf = lowpass(remapped, lowpass_threshold, pixel_size) # ~0.8 sec
    lowpassed, ctf = lowpass(remapped, lowpass_threshold, pixel_size) # ~0.7 sec

    return lowpassed, ctf

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

def resize_image(img_nparray, scaling_factor, DEBUG = True):
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

class MrcData():
    """
    A class object for loading an .MRC/.MRCS image and handling its accompanying data (e.g. processed images, associated coordinates, ...). Initialize this object with the file and desired default parameters:
        mrcdata = MrcData(image_name, scale_factor, lowpass_threshold, sigma_contrast)
    """

    def __init__(self, fname, input_scale = 0.25, input_lowpass = 10, input_sigma = 3):
        print("=========================================")
        print("      MrcData class initialized")
        print("-----------------------------------------")
        print(" Unpacking MRC data from: %s" % fname)

        self.scale_factor = input_scale
        self.lowpass_threshold = input_lowpass
        self.sigma_contrast = input_sigma
        self.raw_data, self.pixel_size, self.x, self.y, self.z = get_mrc_raw_data(fname)
        self.fname = fname
        self.coordinates_raw = {} ## expected structure: { str(slice_index) : [ (x1, y1), ... (x, y) ], ... }, coordinates are in original pixel dimensions 
        self.process_raw_data()

        return

    def add_coordinate(self, slice_index, x, y, box_width):
        """
        PARAMETERS 
            slice_index = which z stack these coordinates belong to
            x, y = pixel position of the coordinate in the scaled image 
            box_width = size of the box (in Angstroms) for a particle to check for clashes
        """
        ## interpolate the picked coordinates back to the raw image coordinates 
        x = int(x / self.scale_factor) 
        y = int(y / self.scale_factor) 
        box_width_px = int(box_width / self.pixel_size)

        ## check if there already exists a list of coordinates for this given slice 
        if str(slice_index) in self.coordinates_raw:
            ## check if the pick is a clash with any coordinates
            if self.is_clashing(x, y, box_width_px, self.coordinates_raw[str(slice_index)], slice_index):
                print(" New coordinate clashes with existing coordinate")
                pass
            else:
                self.coordinates_raw[str(slice_index)].append((x, y))
                print(" Adding coordinate to slice: %s -> (%s, %s)" % (slice_index, x, y))

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

    def process_raw_data(self):
        ## reset the processed data variable 
        self.processed_data = list()

        for z_slice in range(self.z):
            print("----------------------------------------------")
            print(" Processing slice :: %s " % z_slice)
            ## find the raw mrc data for the corresponding slice 
            slice_array = self.raw_data[z_slice,:,:]

            im_obj = self.process_single_image(slice_array)
            ## pack the processed image object into the mrcdata holder variable 
            self.processed_data.append(im_obj)

        return  
    
    def process_single_image(self, input_array):
        """
        PARAMETERS
            im_array = raw data of image as an nparray 
        RETURNS
            im_obj = PhotoImage object useable for display on Tk 
        """
        ## it is much faster if we scale down the image prior to doing filtering
        img_scaled = resize_image(input_array, self.scale_factor)
        grayscale_img_array, grayscale_fft_array = mrc2grayscale(img_scaled, self.pixel_size / self.scale_factor, self.lowpass_threshold)
        img_contrasted = sigma_contrast(grayscale_img_array, self.sigma_contrast)  
        im_obj = get_PhotoImage_obj(img_contrasted)

        return im_obj  
    
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
            output_mrcs_name =  self.fname[-5:] + "_extracted.mrcs"
        elif self.fname[-4:].lower() == '.mrc':
            output_mrcs_name = self.fname[-4:] + "_extracted.mrcs"

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


class MainUI:
    def __init__(self, instance, input_scale, input_lowpass, input_sigma, input_file):
        self.instance = instance
        instance.title("Tomography picker")
        # instance.geometry("520x500") ## geometry now set by a function 

        ## CLASS VARIABLES
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
        self.picks_diameter = 1000 ## Angstroms, `picks' are clicked particles by the user
        self.picks_color = 'red'
        # self.coordinates = dict() ## list of picked points
        self.SHOW_SCALEBAR = tk.BooleanVar(instance, False)
        self.scalebar_length = 200 ## Angstroms
        self.scalebar_stroke = 5 ## pixels
        self.scalebar_color = 'white'
        self.SHOW_CTF = tk.BooleanVar(instance, False)
        self.slice_index = 0 ## index of the list of known mrc files int he directory to view
        self.working_dir = "."
        self.SPEED_OVER_ACCURACY = tk.BooleanVar(instance, True)

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

        self.extract_LABEL = tk.Label(instance, font=("Helvetica", right_side_panel_fontsize), text="%s px" % 'wip')
        self.extract_LABEL.grid(row = 16, column = 1, columnspan = 2)


        self.extract_button = tk.Button(instance, text="Extract", font=("Helvetica", right_side_panel_fontsize), command = lambda: self.extract_particles(), width=10)
        self.extract_button.grid(row = 20, column = 1, columnspan = 2)

        viewport_frame.grid(row = 1, column = 0, rowspan = 100)

        scrollable_frame, viewport_canvas = self.initialize_scrollable_window(self.viewport_frame)

        ## LOAD AN INITIAL MRC FILE

        ## Pack the image data into the MrcData object
        self.mrcdata = MrcData(self.image_name, self.scale_factor, self.lowpass_threshold, self.sigma_contrast)
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
        self.instance.bind('<Control-KeyRelease-e>', lambda event: self.extract_particles())
        self.instance.bind('<Control-KeyRelease-q>', lambda event: self.quit())

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


        ## PANEL INSTANCES
        # self.optionPanel_instance = None
        return

    def extract_particles(self):
        self.mrcdata.extract_particles(self.picks_diameter)
        return 

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

        # for coordinate in self.coordinates:
        if str(self.slice_index) in self.mrcdata.coordinates_raw:
            for coordinate in self.mrcdata.coordinates_raw[str(self.slice_index)]:
                ## each coordinate is the center of a box, thus we need to offset by half the gif_box_width pixel length to get the bottom left and top right of the rectangle
                x0 = int(coordinate[0] * self.mrcdata.scale_factor) - box_halfwidth
                y0 = int(coordinate[1] * self.mrcdata.scale_factor) - box_halfwidth
                x1 = int(coordinate[0] * self.mrcdata.scale_factor) + box_halfwidth
                y1 = int(coordinate[1] * self.mrcdata.scale_factor) + box_halfwidth #y0 - img_box_size # invert direction of box to take into account x0,y0 are at bottom left, not top left
                # canvas.create_rectangle(x0, y0, x1, y1, outline='red', width=1, tags='particle_positions')
                canvas.create_oval(x0, y0, x1, y1, outline=self.picks_color, width=2, tags='particle_positions')
        if DEBUG: print(" %s image coordinates drawn onto canvas" % len(self.coordinates))
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
                self.working_dir = file_dir

                ## Pack the image data into the MrcData object
                self.slice_index = 0
                self.mrcdata = MrcData(self.image_name, self.scale_factor, self.lowpass_threshold, self.sigma_contrast)
                self.load_img()

                ## SET THE SIZE OF THE PROGRAM WINDOW BASED ON THE SIZE OF THE DATA FRAME AND THE SCREEN RESOLUTION
                self.resize_program_to_fit_screen_or_data()

            except:
                showerror("Open Source File", "Failed to read file\n'%s'" % file_w_path)
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
        mrc_im_array = self.mrcdata.processed_data[self.slice_index]

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

        self.extract_LABEL['text'] = "%s px" % (int(self.picks_diameter / self.pixel_size) - 1)

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
        # dropdown_file.add_command(label="Save .jpg", command=self.save_jpg)
        dropdown_file.add_command(label="Exit", command=self.quit)
        # ## dropdown menu --> Options
        # dropdown_options = tk.Menu(menubar)
        # menubar.add_cascade(label="Options", menu = dropdown_options)
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


def parse_cmdline(cmds):
    ## check for help flag 
    for cmd in cmds:
        if cmd in ['-h', '--h', '--help', '-help']:
            print(" Help flag called: %s" % cmd)
            usage()
            sys.exit()

    ## set up return variable defaults  
    scale = 0.2 
    lowpass = 10 
    sigma = 3
    input_file = None

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

    ## sanity check necessary inputs are populated 
    if input_file == None:
        print(" No input .MRC/.MRCS file was given!")
        usage()
        sys.exit()

    return scale, lowpass, sigma, input_file

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

##########################
### RUN BLOCK
##########################
if __name__ == '__main__':
    import tkinter as tk
    from tkinter.filedialog import askopenfilename
    from tkinter.filedialog import asksaveasfilename
    from tkinter.messagebox import showerror
    from tkinter import ttk
    import numpy as np
    import os, sys
    import time
    try:
        from PIL import Image as PIL_Image
        from PIL import ImageTk
    except:
        print("Problem importing PIL, try installing Pillow via:")
        print("   $ pip install --upgrade Pillow")

    import mrcfile
    try:
        import cv2 ## for resizing images with a scaling factor
    except:
        print("Could not import cv2, try installing OpenCV via:")
        print("   $ pip install opencv-python")

    input_scale, input_lowpass, input_sigma, input_file = parse_cmdline(sys.argv)

    usage()

    root = tk.Tk()
    app = MainUI(root, input_scale, input_lowpass, input_sigma, input_file)
    root.mainloop()
