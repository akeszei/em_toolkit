#!/usr/bin/env python3

## Author: Alexander Keszei
## 2022-05-11: Version 1 finished
## 2023-03-27: Updated to improve filtering on fast implementation (switching interpolation mode on resize function was crucial)
## 2024-05-08: Adapted for topaz analysis 

"""
To Do:
    - Somehow lock the left/right keys from firing while loading an image. Basic attempts to do this by adding a flag on the start/end of the load_img function fails since the keystrokes are queued and fire after the function completes 
    - Load the csv file more generically, in case header locations are added or moved around
    - Add a template picker UI so the user can set the threshold limit and see the current template 
    - Add an eraser function
    - Speed up clash test 
    - Save out the template? 
""" 

DEBUG = True

#region :: Utilities 

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

def suggest_target_angpix(particle_diameter, CNN_architecture = 'resnet8'):
    """
    PARAMETERS 
        particle_diameter = particle size in Angstroms 
        CNN_architecture = str(); what CNN achitecture is used in topaz
    """
    receptive_field_size = {'resnet8' : 71, 'conv127' : 127, 'conv63' : 63, 'conv31' : 31}
    target_relative_size = 0.75 # aim for the particle to comfortably fit the receptive field 

    target_angpix = particle_diameter / (receptive_field_size[CNN_architecture] * target_relative_size)
    
    return target_angpix

def load_topaz_csv(fname, DEBUG = True):
    """
        Parse a csv particles file into a fixed data structure:
            {
                'img_name' : [ (x, y, score), (x2, y2, score), ... ]
            }
    """

    ## initialize an empty dictionary 
    particle_data = {}
    ## extract file information from selection
    file_path = str(fname)

    ## load particle data as a pandas DataFrame object for easy manipulation
    csv_data = pd.read_csv(file_path, sep="\t", header=0)

    ## reorganize the DataFrame by the image name
    csv_data = csv_data.groupby('image_name')

    total_micrographs = 0
    total_particles = 0
    for img, particles in csv_data:
        total_micrographs += 1
        ## add a new entry to the dictionary 
        particle_data[img] = []

        ## add particles to the new entry list 
        for row_index, row in particles.iterrows():
            total_particles += 1
            x = row['x_coord']
            y = row['y_coord']
            s = row['score']
            particle_data[img].append((x, y, s))

    if DEBUG:
        print("=======================================")
        print(" Loaded dataset from: ")
        print("    %s" % fname)
        print("---------------------------------------")
        print("   %s micrographs " % total_micrographs)
        print("   %s particles " % total_particles)
        print("---------------------------------------")
        print("  Example entries:")
        if total_particles > 3:
            ## get the first key in the dictionary 
            for k in particle_data:
                break 
            ## use the first key of the dictionary to print out a few coordinates 
            i = 0
            for p in particle_data[k]:                    
                print("     (x, y, score) :: ", particle_data[k][i])
                i += 1
                if i == 2:
                    print("     ...")
                    print("     (x, y, score) :: ", particle_data[k][-1])
                    break
        print("=======================================")
    return particle_data

def get_resized_dimensions(percent, input_dimensions):
    """
    PARAMETERS:
        percent = % size to change from original (i.e. 50 would shrink by half)
        input_dimensions = tuple(x, y); pixel size of original image
    RETURNS:
        new_dimensions = tuple(x, y); the dimensions of the image after applying the percent scaling
    """
    new_dimension_x = int(input_dimensions[0] * (percent / 100))
    new_dimension_y = int(input_dimensions[1] * (percent / 100))
    new_dimensions = (new_dimension_x, new_dimension_y)
    return new_dimensions

def images_in_dir(path, USE_MRC = False, DEBUG = True) :
    """ Create a list object populated with the names of image files present
    PARAMETERS
        path = str(), path to the directory with images to view
    """
    image_list = []
    for file in sorted(os.listdir(path)):
        if is_image(file, USE_MRC = USE_MRC):
            image_list.append(file)

    if DEBUG:
        print("=======================================")
        print(" %s images found in working dir: " % len(image_list))
        # print("   USE_MRC = %s" % USE_MRC)
        print("---------------------------------------")
        print("  Example entries:")
        if len(image_list) > 0:
            i = 0
            for n in range(len(image_list)):                    
                print("     %s " % image_list[n])
                i += 1
                if i > 3:
                    print("     ...")
                    print("     %s " % image_list[-1])
                    break
        print("=======================================")

    return image_list

def is_image(file, USE_MRC = False):
    """ For a given file name, check if it has an appropriate suffix.
        Returns True if it is a file with proper suffix (e.g. .gif)
    PARAMETERS
        file = str(); name of the file (e.g. 'test.jpg')
    """
    detected_extension = os.path.splitext(file)[1].lower()
    if USE_MRC:
        image_formats = [".mrc"]
    else:
        image_formats = [".gif", ".jpg", ".jpeg"]
    for suffix in image_formats:
        if suffix == detected_extension:
            return True
    return False

def resize_image(img_nparray, scaling_factor):
    """ Uses OpenCV to resize an input grayscale image (0-255, 2d array) based on a given scaling factor
            scaling_factor = float()
    """
    ## check if the input np.array is type float32 which is necessary for cv2.resize function 
    if not img_nparray.dtype == 'float32':
        print(" ERROR :: Input np.array is not dtype np.float32, recast it before running this function")
        return 

    original_width = img_nparray.shape[1]
    original_height = img_nparray.shape[0]
    scaled_width = int(img_nparray.shape[1] * scaling_factor)
    scaled_height = int(img_nparray.shape[0] * scaling_factor)
    if DEBUG: print("resize_img function, original img_dimensions = ", img_nparray.shape, img_nparray.dtype,", new dims = ", scaled_width, scaled_height)
    resized_im = cv2.resize(img_nparray, (scaled_width, scaled_height), interpolation=cv2.INTER_AREA) 
    # resized_im = cv2.resize(img_nparray, (scaled_width, scaled_height)) ## note: default interpolation is INTER_LINEAR, and does not work well for noisy EM micrographs 
    return resized_im

def get_PhotoImage_obj(img_nparray):
    """ Convert an input numpy array grayscale image and return an ImageTk.PhotoImage object
    """
    PIL_img = PIL_Image.fromarray(img_nparray.astype(np.uint8))  #.convert('L')

    img_obj = ImageTk.PhotoImage(PIL_img)
    return img_obj

def get_mrc_raw_data(file):
    """ file = .mrc file
        returns np.ndarray of the mrc data using mrcfile module
    """
    ## NOTE atm works for mrc mode 2 but not mode 6
    try:
        with mrcfile.open(file) as mrc:
            image_data = mrc.data.astype(np.float32) ## need to cast it as a float32, since some mrc formats are uint16! (i.e. mode 6)
            # print("mrc dtype = ", type(image_data.dtype))
            pixel_size = np.around(mrc.voxel_size.item(0)[0], decimals = 2)
    except:
        print(" There was a problem opening .MRC file (%s), try permissive mode. Consider fixing this file later!" % file)
        with mrcfile.open(file, permissive = True) as mrc:
            image_data = mrc.data.astype(np.float32) ## need to cast it as a float32, since some mrc formats are uint16! (i.e. mode 6)
            # print("mrc dtype = ", type(image_data.dtype))
            pixel_size = np.around(mrc.voxel_size.item(0)[0], decimals = 2)

    if DEBUG:
        print(" Opening %s" % file)
        print("   >> image dimensions (x, y) = (%s, %s)" % (image_data.shape[1], image_data.shape[0]))
        print("   >> pixel size = %s Ang/px" % pixel_size)

    ## set defaults 
    if pixel_size == 0:
        pixel_size = 1.0

    return image_data, pixel_size

def mrc2grayscale(mrc_raw_data, pixel_size):
    """ Convert raw mrc data into a grayscale numpy array suitable for display
    """
    # print(" min, max = %s, %s" % (np.min(mrc_raw_data), np.max(mrc_raw_data)))
    ## remap the mrc data to grayscale range
    remapped = (255*(mrc_raw_data - np.min(mrc_raw_data))/np.ptp(mrc_raw_data)).astype(np.uint8) ## remap data from 0 -- 255 as integers

    return remapped

def sigma_contrast(im_array, sigma):
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
        print(" sigma_contrast (s = %s)" % sigma)

    ## remove pixels above/below the defined limits
    im_array = np.clip(im_array, minval, maxval)
    ## rescale the image into the range 0 - 255
    im_array = ((im_array - minval) / (maxval - minval)) * 255

    return im_array.astype('uint8')

#endregion 

#region :: GUIs
class MainUI:
    def __init__(self, instance, start_index, particle_data = dict()):
        self.instance = instance
        instance.title("Tk-based Topaz viewer")
        # instance.geometry("520x500")
        # instance.resizable(False, False)

        #region :: CLASS PARAMETERS
        self.RIGHT_MOUSE_PRESSED = False 
        self.brush_size = 50
        self.displayed_widgets = list() ## container for all widgets packed into the main display UI, use this list to update each
        self.display_data = list() ## container for the image objects for each displayed widgets (they must be in the scope to be drawn)
                                   ## in this program, display_data[0] will contain the scaled .jpg-style image; while display_data[1] will contain the display-ready CTF for that image
        self.display_im_arrays = list() ## contains the nparray versions of the image/ctf currently in the display window (for saving jpgs) 
        self.mrc_dimensions = ('x', 'y')
        self.pixel_size = float()
        self.image_name = str()
        self.scale_factor = 0.5 ## scaling factor for displayed image
        self.sigma_contrast = 3
        self.SHOW_PICKS = tk.BooleanVar(instance, True)
        self.picks_diameter = 50 ## Angstroms, `picks' are clicked particles by the user
        self.picks_color = 'red'
        self.picks_threshold = 0
        self.threshold_min = -1
        self.threshold_max = 1
        self.coordinates = particle_data # dict() ## list of picked points
        self.index = start_index ## 0 ## index of the list of known mrc files int he directory to view
        self.working_dir = "."
        self.USE_MRC = tk.BooleanVar(instance, True) # option to switch between .jpg and .mrc
        self.particles_file_save_name = 'particles.txt'
        #endregion

        ## MENU BAR LAYOUT
        self.initialize_menubar(instance)

        ## MAIN WINDOW WITH SCROLLBARS
        self.image_name_label = image_name_label = tk.Entry(instance, font=("Helvetica", 16), highlightcolor="blue", borderwidth=None, relief=tk.FLAT, foreground="black", background="light gray")
        # image_name_label.pack(fill='both', padx= 20)
        image_name_label.grid(row = 0 , column =  0, sticky = (tk.EW), padx = 5)
        self.viewport_frame = viewport_frame =  ttk.Frame(instance)

        #region :: RIGHT SIDE PANELS
        right_side_panel_fontsize = 9

        ## MRC INFO
        self.iminfo_header = tk.Label(instance, font=("Helvetica, 16"), text="MRC info")
        self.iminfo_header.grid(row = 1, column = 1, columnspan = 2) #, sticky = (tk.N, tk.W))

        self.MRC_dimensions_LABEL = tk.Label(instance, font=("Helvetica", right_side_panel_fontsize), text="(%s, %s)" % ('x', 'y'))
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

        self.sigma_contrast_LABEL = tk.Label(instance, font=("Helvetica", right_side_panel_fontsize), text="Sigma: ")
        self.sigma_contrast_ENTRY = tk.Entry(instance, width=4, font=("Helvetica", right_side_panel_fontsize))
        self.sigma_contrast_LABEL.grid(row = 9, column = 1, sticky = (tk.N, tk.E))
        self.sigma_contrast_ENTRY.grid(row = 9, column = 2, sticky = (tk.N, tk.W))

        ## TOPAZ PANEL
        self.separator2 = ttk.Separator(instance, orient='horizontal')
        self.separator2.grid(row=12, column =1, columnspan = 2, sticky=tk.EW)
        self.optional_header = tk.Label(instance, font=("Helvetica, 16"), text="Topaz")
        self.optional_header.grid(row = 13, column = 1, columnspan = 2) #, sticky = (tk.N, tk.W))

        self.threshold_LABEL = tk.Label(instance, font=("Helvetica", right_side_panel_fontsize), text="Threshold: %s" % self.picks_threshold)
        self.threshold_SLIDER = tk.Scale(instance, font=("Helvetica", right_side_panel_fontsize), from_=0, to=100, resolution=0.1, showvalue =0, tickinterval=0, orient=tk.HORIZONTAL, sliderlength = 20, length = 105, width = 10, command=self.on_slider_change)
        self.threshold_LABEL.grid(row = 14, column = 1, sticky = (tk.S)) #, tk.CENTER))
        self.threshold_SLIDER.grid(row = 15, column = 1,  columnspan = 2) #, sticky = (tk.N, tk.E))


        self.show_picks_TOGGLE = tk.Checkbutton(instance, text='Show particle picks', variable=self.SHOW_PICKS, onvalue=True, offvalue=False, command=self.toggle_SHOW_PICKS)
        self.show_picks_TOGGLE.grid(row = 16, column = 1, columnspan = 2, sticky = (tk.N, tk.W))

        self.picks_diameter_LABEL = tk.Label(instance, font=("Helvetica", right_side_panel_fontsize), text="Diameter (Å): ")
        self.picks_diameter_ENTRY = tk.Entry(instance, width=4, font=("Helvetica", right_side_panel_fontsize))
        self.picks_diameter_LABEL.grid(row = 17, column = 1, sticky = (tk.N, tk.E))
        self.picks_diameter_ENTRY.grid(row = 17, column = 2, sticky = (tk.N, tk.W))

        self.particle_diameter_pixels_LABEL = tk.Label(instance, font=("Helvetica", right_side_panel_fontsize), text="%s px" % '?')
        self.particle_diameter_pixels_LABEL.grid(row = 18, column = 1, columnspan = 2, sticky = (tk.N))

        self.suggested_angpix_LABEL = tk.Label(instance, font=("Helvetica", right_side_panel_fontsize), text="Crop to: %s Å/px" % '?')
        self.suggested_angpix_LABEL.grid(row = 19, column = 1, columnspan = 2, sticky = (tk.N))

        #endregion

        viewport_frame.grid(row = 1, column = 0, rowspan = 100)

        scrollable_frame, viewport_canvas = self.initialize_scrollable_window(self.viewport_frame)
        ## capture the close window command so we can force it to launch the quit function ahead of closure 
        self.instance.protocol("WM_DELETE_WINDOW", self.quit)

        self.load_settings()

        ## LOAD AN INITIAL MRC FILE
        self.next_img('none')

        ## SET THE SIZE OF THE PROGRAM WINDOW BASED ON THE SIZE OF THE DATA FRAME AND THE SCREEN RESOLUTION
        self.resize_program_to_fit_screen_or_data()

        ## EVENT BINDING
        instance.bind("<Configure>", self.resize) ## Bind manual screen size adjustment to updating the scrollable area

        #region :: KEYBINDINGS
        self.instance.bind("<F1>", lambda event: self.debugging())
        self.instance.bind('<Control-s>', lambda event: self.write_particles_file()) # Ctrl + S
        self.instance.bind('<Control-S>', lambda event: self.write_particles_file(QUERY = False)) # Ctrl + Shift + S
        self.instance.bind('<F5>', lambda event: self.write_particles_file(QUERY = False)) 
        self.instance.bind('<Control-c>', lambda event: self.local_contrast_and_blur())
        self.instance.bind('<Control-x>', lambda event: self.open_panel("AutopickPanel"))
        canvas = self.displayed_widgets[0]
        canvas.bind("<MouseWheel>", self.MouseWheelHandler) # Windows, Mac: Binding to <MouseWheel> is being used
        canvas.bind("<Button-4>", self.MouseWheelHandler) # Linux: Binding to <Button-4> and <Button-5> is being used
        canvas.bind("<Button-5>", self.MouseWheelHandler)
        canvas.bind("<ButtonPress-2>", self.on_middle_mouse_press)
        canvas.bind("<ButtonRelease-2>", self.on_middle_mouse_release)
        canvas.bind("<ButtonPress-3>", self.on_right_mouse_press)
        canvas.bind("<ButtonRelease-3>", self.on_right_mouse_release)
        canvas.bind("<Motion>", self.refresh_brush_cursor)

        self.instance.bind('<Left>', lambda event: self.next_img('left'))
        self.instance.bind('<Right>', lambda event: self.next_img('right'))
        self.instance.bind('<z>', lambda event: self.next_img('left'))
        self.instance.bind('<x>', lambda event: self.next_img('right'))
        # self.instance.bind('<c>', lambda event: self.toggle_SHOW_CTF()) ## will need to set the toggle

        self.image_name_label.bind('<Control-KeyRelease-a>', lambda event: self.select_all(self.image_name_label))
        # self.image_name_label.bind('<Return>', lambda event: self.image_name_updated())
        # self.image_name_label.bind('<KP_Enter>', lambda event: self.image_name_updated())
        self.scale_ENTRY.bind('<Control-KeyRelease-a>', lambda event: self.select_all(self.scale_ENTRY))
        self.scale_ENTRY.bind('<Return>', lambda event: self.scale_updated())
        self.scale_ENTRY.bind('<KP_Enter>', lambda event: self.scale_updated())
        # self.lowpass_threshold_ENTRY.bind('<Control-KeyRelease-a>', lambda event: self.select_all(self.lowpass_threshold_ENTRY))
        # self.lowpass_threshold_ENTRY.bind('<Return>', lambda event: self.lowpass_threshold_updated())
        # self.lowpass_threshold_ENTRY.bind('<KP_Enter>', lambda event: self.lowpass_threshold_updated())
        self.sigma_contrast_ENTRY.bind('<Control-KeyRelease-a>', lambda event: self.select_all(self.sigma_contrast_ENTRY))
        self.sigma_contrast_ENTRY.bind('<Return>', lambda event: self.sigma_updated())
        self.sigma_contrast_ENTRY.bind('<KP_Enter>', lambda event: self.sigma_updated())
        self.picks_diameter_ENTRY.bind('<Control-KeyRelease-a>', lambda event: self.select_all(self.picks_diameter_ENTRY))
        self.picks_diameter_ENTRY.bind('<Return>', lambda event: self.pick_diameter_updated())
        self.picks_diameter_ENTRY.bind('<KP_Enter>', lambda event: self.pick_diameter_updated())
        # self.scalebar_length_ENTRY.bind('<Control-KeyRelease-a>', lambda event: self.select_all(self.scalebar_length_ENTRY))
        # self.scalebar_length_ENTRY.bind('<Return>', lambda event: self.scalebar_updated())
        # self.scalebar_length_ENTRY.bind('<KP_Enter>', lambda event: self.scalebar_updated())
        self.instance.bind('<F2>', lambda event: self.make_template())
        #endregion

        ####################################
        #region :: Panel Instances
        ####################################
        self.autopickPanel_instance = None
        #endregion
        ####################################

        self.usage()
        return

    def clear_coordinates(self):
        if len(self.coordinates) > 0:
            image_name = os.path.splitext(self.image_name)[0]
            if image_name == None or image_name == '':
                ## we cannot have coordinates if we have no name!
                return 
            else:
                ## reset the list for the particle data under this image name
                self.coordinates[image_name] = [] 
                self.draw_image_coordinates()
   
        return 

    def open_panel(self, panelType = 'None'):

        ## use a switch-case statement logic to open the correct panel
        if panelType == "None":
            return
        elif panelType == "AutopickPanel":
            if self.autopickPanel_instance is None:
                self.autopickPanel = AutopickPanel(self)
            else:
                print(" AutopickPanel is already open: ", self.autopickPanel_instance)
        else:
            return
        return

    def make_template_from_picks(self):
        """
            Experimental function to see if I can generate a crude template to help speed up manual picking 
        """
        ## get all the picks so far and add them together before re-normalizing
        current_display_img = self.display_im_arrays[0]

        ## box_size is a value given in Angstroms, we need to convert it to pixels
        display_angpix = self.pixel_size / self.scale_factor
        rescaled_box_size = int(self.picks_diameter * 1.4  / display_angpix) # add some padding around the particle 
        ## img coordinates are given in raw file pixel positions
        image_name = os.path.splitext(self.image_name)[0]
        if image_name == None or image_name == '':
            return None
        image_coordinates = self.coordinates[image_name] 
        ## return None if no coordinates on image 
        if len(image_coordinates) == 0:
            return None
        
        rescaled_coordinates = []
        for Xcoord, Ycoord, score in image_coordinates:
            rescaled_coordinates.append((int(Xcoord * self.scale_factor), int(Ycoord * self.scale_factor)))
        particle_imgs = image_handler.extract_boxes(current_display_img, rescaled_box_size, rescaled_coordinates, DEBUG = DEBUG)

        merged = np.sum(particle_imgs, axis =0)

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
            Use an input template to pick on the displayed image 
            PARAMETERS
                template = np.array (uint8, 0 - 255)
        """
        image_name = os.path.splitext(self.image_name)[0]
        if image_name == None or image_name == '':
            print(" Abandoned template_picker function as no image is loaded!")
            return 
        
        ## get all the picks so far and add them together before re-normalizing
        current_display_img = self.display_im_arrays[0]

        res, loc = image_handler.template_match(current_display_img, template, picking_threshold) 
        print(" residual img dimensions :: (x, y) color_range [a, b] -> (%s, %s)  [%s, %s]" % (res.shape[0], res.shape[1], np.min(res), np.max(res)))

        # fig,ax=plt.subplots()
        # im=ax.imshow(current_display_img, aspect='equal',interpolation=None)
        # for pt in loc:
        #     ax.add_patch(plt.Circle([pt[0],pt[1]], radius=0.5, edgecolor='r',lw=3, fill=False))
        # cbar=plt.colorbar(im)
        # plt.show()


        # ## add the picks to the current coordinate list, avoiding any that are clashing with current picks 
        # for Xcoord, Ycoord, score in loc:
        #     if self.is_clashing((Xcoord, Ycoord), REMOVE = False): 
        #         pass
        #     else:
        #         self.add_coordinate(Xcoord, Ycoord, score)
        
        ## For performance probably want to run the check with fewer calculations per cycle, so pre-calculate the halfbox size, then for each point run a range intersection check for X, if it passes then Y, then if it does not intersect with both add the coordinate a a separate list we later call to add points (to avoid growth of the search set during loop, input coordinates are expected NOT to intersect!)
        display_angpix = self.pixel_size / self.scale_factor
        particle_width = self.picks_diameter / display_angpix
        particle_halfwidth = int(particle_width / 2)
        picks_to_keep = []
        for i in range(len(loc)):
            ADD_POINT = True
            x, y, score = loc[i]
            ## check first if we have points to even compare against (i.e. is this an empty micrograph?)
            ## check if the image_name is in self.coordinates dictionary, make an empty entry if not  
            if not image_name in self.coordinates:
                ## if there is no entry, create it 
                self.coordinates[image_name] = []

            if not len(self.coordinates[image_name]) == 0:                
                for px, py, pscore in self.coordinates[image_name]:
                    ## coordinates need to be rescaled to the viewing image scale 
                    rescaled_x = int(px * self.scale_factor)
                    rescaled_y = int(py * self.scale_factor)

                    ## run the fast interection algorithm for X, then Y
                    if check_if_two_ranges_intersect(x - particle_halfwidth, x + particle_halfwidth, rescaled_x - particle_halfwidth, rescaled_x + particle_halfwidth):
                        if check_if_two_ranges_intersect(y - particle_halfwidth, y + particle_halfwidth, rescaled_y - particle_halfwidth, rescaled_y + particle_halfwidth):
                            ## if we pass both checks, we have a clash situation - abandon adding this point to the final roster without further checks 
                            ADD_POINT = False
            ## use the flag to decide whether we add the point 
            if ADD_POINT:
                picks_to_keep.append(i)

        ## add each point we wanted to keep to the final set of coordinates after fishing the looping functions 
        for p in picks_to_keep:
            x, y, score = loc[p]
            self.add_coordinate(x, y, score)

        ## determine the minimum threshold score and set the slider there so we see all points added after running this command 
        lowest_score = min(loc, key=lambda p:p[2])[2]
        self.picks_threshold = lowest_score
        self.threshold_LABEL['text'] = "Threshold: %0.2f" % lowest_score

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
        return 

    def on_right_mouse_press(self, event):
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
        display_angpix = self.pixel_size / self.scale_factor
        particle_width = self.picks_diameter / display_angpix
        particle_halfwidth = int(particle_width / 2)

        ## get the loaded coordinates for the image 
        try:
            image_coordinates = self.coordinates[image_name]
        except:
            print(" Could not load coordinates for img (%s), perhaps no particle file was loaded yet" % image_name)
            return 

        ## in case the user does not move the mouse after right-clicking, we want to find all clashes in range on this event as well
        erase_coordinates = [] # avoid changing dictionary until after iteration complete
        ## find all coordinates that clash with the brush
        if len(image_coordinates) > 0:
            for coord in image_coordinates:
                ## rescale the stored coordinates to match the viewing scale 
                rescaled_x = int(coord[0] * self.scale_factor)
                rescaled_y = int(coord[1] * self.scale_factor)

                if check_if_two_ranges_intersect(rescaled_x - particle_halfwidth, rescaled_x + particle_halfwidth, x_min, x_max, DEBUG = False): # x0, x1, y0, y1
                    if check_if_two_ranges_intersect(rescaled_y - particle_halfwidth, rescaled_y + particle_halfwidth, y_min, y_max, DEBUG = False): # x0, x1, y0, y1
                        print(" Erase coordinate:")
                        print("   brush center (%s, %s), brush limits x = (%s -> %s) & y = (%s -> %s)" % (x, y, x_min, x_max, y_min, y_max))
                        print("   coordinate center (%s, %s)" % (rescaled_x, rescaled_y))
                        erase_coordinates.append(coord)

        ## erase all coordinates caught by the brush
        for coord in erase_coordinates:
            i = image_coordinates.index(coord)
            del self.coordinates[image_name][i] # remove the coordinate that clashed

        self.draw_image_coordinates()
        return

    def on_right_mouse_release(self, event):
        """ Delete the green brush after the user stops erasing and reset the global flag
        """
        print("Right mouse released")
        canvas = self.displayed_widgets[0]
        self.RIGHT_MOUSE_PRESSED = False
        canvas.delete('brush') # remove any lingering brush marker
        return

    def refresh_brush_cursor(self, event):
        """ This function is tied to the <Motion> event.
            It constantly checks if the condition RIGHT_MOUSE_PRESSED is True, in which case it runs the erase-coordinates algorithm
        """        
        if self.RIGHT_MOUSE_PRESSED:
            image_name = os.path.splitext(self.image_name)[0]
            if image_name == None or image_name == '':
                return 

            canvas = self.displayed_widgets[0]

            ## get the loaded coordinates for the image 
            try:
                image_coordinates = self.coordinates[image_name]
            except:
                print(" Could not load coordinates for img (%s), perhaps no particle file was loaded yet" % image_name)
                return 

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
            display_angpix = self.pixel_size / self.scale_factor
            particle_width = self.picks_diameter / display_angpix
            particle_halfwidth = int(particle_width / 2)

            erase_coordinates = [] # avoid changing dictionary until after iteration complete
            ## find all coordinates that clash with the brush
            if len(image_coordinates) > 0:
                for coord in image_coordinates:
                    ## rescale the coordinates back to the viewing scale 
                    rescaled_x = int(coord[0] * self.scale_factor)
                    rescaled_y = int(coord[1] * self.scale_factor)

                    if check_if_two_ranges_intersect(rescaled_x - particle_halfwidth, rescaled_x + particle_halfwidth, x_min, x_max): # x0, x1, y0, y1
                        if check_if_two_ranges_intersect(rescaled_y - particle_halfwidth, rescaled_y + particle_halfwidth, y_min, y_max): # x0, x1, y0, y1
                            erase_coordinates.append(coord)
            ## erase all coordinates caught by the brush
            for coord in erase_coordinates:
                i = image_coordinates.index(coord)
                del self.coordinates[image_name][i] # remove the coordinate that clashed

            self.draw_image_coordinates()
        else:
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

    def usage(self):
        print("===================================================================================================")
        print(" Load this viewer in a directory with test micrographs to help pick initial binning, or to ")
        print(" inspect the predicted picks from a trained model to choose a good threshold.")
        print(" Usage:")
        print("    $ cd /path/to/test/mics")
        print("    $ topaz_viewer.py  ")
        print(" Alternatively, can directly point to the particle picks file on loadup:")
        print("    $ topaz_viewer.py  predicted.txt")
        # print(" -----------------------------------------------------------------------------------------------")
        # print(" Options (default in brackets): ")
        print("===================================================================================================")
        return

    def set_threshold(self):
        current_set_threshold = self.picks_threshold
        current_min = self.threshold_min
        current_max = self.threshold_max

        ## determine the absolute range for the current min/max
        current_range = current_max - current_min 

        ## in case we have too few particles we need to avoid setting the threshold 
        if current_range <= 0:
            return 

        ## find the relative location of the current threshold set value  
        current_set_threshold_absolute = current_set_threshold - current_min
        current_set_threshold_relative = current_set_threshold_absolute / current_range 

        ## map the relative location back to the slider range
        slider_range = 100  
        current_set_threshold_relative_to_slider_range = current_set_threshold_relative * slider_range

        print(" threshold value set to = ", current_set_threshold)
        print(" threshold value relative to scale (%s, %s) = %s" % (current_min, current_max, current_set_threshold_relative))
        print(" set threshold slider to = ", current_set_threshold_relative_to_slider_range)

        self.threshold_SLIDER.set(current_set_threshold_relative_to_slider_range)
        return 

    def on_slider_change(self, slider_value):
        ## find the absolute range of the current threshold values 
        current_min = self.threshold_min
        current_max = self.threshold_max
        current_range = current_max - current_min 

        ## get the relative position of the slider 
        slider_value_relative = float(slider_value) / 100

        ## remap the relative position to the initial range  
        new_set_threshold = current_min + (current_range * slider_value_relative)

        ## set the threshold value to the instance 
        self.picks_threshold = new_set_threshold
        print(" new threshold value picked = (%s -> %s)" % (slider_value, new_set_threshold) )

        self.threshold_LABEL['text'] = "Threshold: %0.2f" % new_set_threshold

        self.draw_image_coordinates()
        return 

    def draw_image_coordinates(self):
        """ Read a dictionary of pixel coordinates and draw boxes centered at each point
        """
        canvas = self.displayed_widgets[0]

        ## delete any pre-existing coordinates if already drawn
        canvas.delete('particle_positions')

        ## check if we are allowed to draw coordinates before proceeding
        if self.SHOW_PICKS.get() == False:
            return

        image_name = os.path.splitext(self.image_name)[0]
        if image_name == None or image_name == '':
            return 

        try:
            image_coordinates = self.coordinates[image_name]
            self.threshold_max = max(image_coordinates, key=itemgetter(2))[2]
            self.threshold_min = min(image_coordinates, key=itemgetter(2))[2]
            print(" Coordinates found for image:")
            print("    %s particles, score range = [%s -> %s]" % (len(image_coordinates), self.threshold_min, self.threshold_max))
            self.set_threshold()

        except:
            print(" Could not load coordinates for img (%s), perhaps no particle file was loaded yet" % image_name)
            return 

        ## box_size is a value given in Angstroms, we need to convert it to pixels
        display_angpix = self.pixel_size / self.scale_factor
        box_width = self.picks_diameter / display_angpix
        box_halfwidth = int(box_width / 2)

        counter = 0
        skipped = 0 
        for coordinate in image_coordinates:
            score = coordinate[2]
            threshold = self.picks_threshold # WIP
            if score >= threshold:
                counter += 1
                ## each coordinate is the center of a box, thus we need to offset by half the img_box_width pixel length to get the bottom left and top right of the rectangle
                x0 = int(coordinate[0] * self.scale_factor) - box_halfwidth
                y0 = int(coordinate[1] * self.scale_factor) - box_halfwidth
                x1 = int(coordinate[0] * self.scale_factor) + box_halfwidth
                y1 = int(coordinate[1] * self.scale_factor) + box_halfwidth #y0 - img_box_size # invert direction of box to take into account x0,y0 are at bottom left, not top left
                # self.canvas.create_rectangle(x0, y0, x1, y1, outline='red', width=1, tags='particle_positions')
                canvas.create_oval(x0, y0, x1, y1, outline=self.picks_color, width=2, tags='particle_positions')
            else:
                skipped += 1
        
        print(" %s particles drawn (%s skipped)" % (counter, skipped))
        return

    def on_left_mouse_down(self, x, y):
        """ Add coordinates to the dictionary at the position of the cursor, then call a redraw.
        """
        mouse_position = x, y
        if DEBUG: print("Clicked on pixel coordinate: x, y =", mouse_position[0], mouse_position[1])

        ## when clicking, check the mouse position against loaded coordinates to figure out if the user is removing a point or adding a point
        if self.is_clashing(mouse_position): # this function will also remove the point if True
            pass
        else:
            if DEBUG: print("Add coordinate: x, y with a max score value of 1 =", mouse_position[0], mouse_position[1])
            x_coord = mouse_position[0]
            y_coord = mouse_position[1]
            score = 1
            self.add_coordinate(x_coord, y_coord, score)
            # self.coordinates[(x_coord, y_coord)] = 'new_point'

        self.draw_image_coordinates()

        return

    def add_coordinate(self, x, y, score):
        ## rescale the x,y coordinates based on the scale of the displayed image 
        rescaled_x = int(x / self.scale_factor)
        rescaled_y = int(y / self.scale_factor)

        ## get the root image name from the instance 
        image_name = os.path.splitext(self.image_name)[0]
        ## check if the image_name is in self.coordinates dictionary 
        if not image_name in self.coordinates:
            ## if there is no entry, create it 
            self.coordinates[image_name] = [(rescaled_x, rescaled_y, score)]
        else:
            ## append the new entry to the existing dataset 
            self.coordinates[image_name].append((rescaled_x, rescaled_y, score))
        return 

    def is_clashing(self, mouse_position, REMOVE = True):
        """
        PARAMETERS
            mouse_position = tuple(x, y); pixel position of the mouse when the function is called
            REMOVE = bool(); optional flag to determine if the clashing point should be removed from the parent list as well
        """
        image_name = os.path.splitext(self.image_name)[0]
        ## check if the image_name is in self.coordinates dictionary 
        if not image_name in self.coordinates:
            ## there can be no clash if there is no entry for the micrograph!
            return False
        else:
            image_coordinates = self.coordinates[image_name]

        ## Calculate the boundaries to use for the clash check
        display_angpix = self.pixel_size / self.scale_factor
        box_width = self.picks_diameter / display_angpix
        box_halfwidth = int(box_width / 2)
        print(" box width in pixels = %s" % box_width)

        i = 0
        for (x_coord, y_coord, score) in image_coordinates:
            ## rescale the search coordinates to the viewing scale 
            rescaled_x = int(x_coord * self.scale_factor)
            rescaled_y = int(y_coord * self.scale_factor)
            if DEBUG:
                print(" CLASH TEST :: mouse_position = ", mouse_position, " ; existing coord = " , rescaled_x, rescaled_y)
            ## check x-position is in range for potential clash
            if rescaled_x - box_halfwidth <= mouse_position[0] <= rescaled_x + box_halfwidth:
                ## check y-position is in range for potential clash
                if rescaled_y - box_halfwidth <= mouse_position[1] <= rescaled_y + box_halfwidth:
                    ## if both x and y-positions are in range, we have a clash
                    if REMOVE:
                        del self.coordinates[image_name][i] # remove the coordinate that clashed based on its index position 
                    return True # for speed, do not check further coordinates (may have to click multiple times for severe overlaps)
            i += 1
        return False

    def load_file(self):
        """ Permits the system browser to be launched to select an image
            form a directory. Loads the directory and file into their
            respective variables and returns them
        """
        # See: https://stackoverflow.com/questions/9239514/filedialog-tkinter-and-opening-files
        file_w_path = askopenfilename(parent=self.instance, initialdir=".", title='Select file', filetypes=(
                                            # ("All files", "*.*"),
                                            ("Medical Research Council format", "*.mrc"),
                                            ))
        if file_w_path:
            try:
                # extract file information from selection
                file_dir, file_name = os.path.split(str(file_w_path))
                # print("File selected: ", file_name)
                # print("Working directory: ", file_dir)
                self.working_dir = file_dir
                self.load_img(file_w_path)

            except:
                showerror("Open Source File", "Failed to read file\n'%s'" % file_w_path)
            return

    def load_particle_picks(self):
        ## arrange the filetypes to match the expected one
        expected_extension = os.path.splitext(self.particles_file_save_name)[1]
        if expected_extension.lower() == ".coord":
            filetypes = [("Coordinate","*.coord"),("Text","*.txt"),("All Files","*.*")]
        elif expected_extension.lower() == ".txt":
            filetypes = [("Text","*.txt"),("Coordinate","*.coord"),("All Files","*.*")]
        else: 
            filetypes = [("Text","*.txt"),("Coordinate","*.coord"),("All Files","*.*")]


        ## load selected file into variable fname
        fname = askopenfilename(parent=self.instance, initialdir="./", title='Select file', filetypes=filetypes)
        if fname:
            try:
                ## extract file information from selection
                file_path = str(fname)
                particle_data = load_topaz_csv(file_path)
                ## save the image coordinate data into our instance container 
                self.coordinates = particle_data

            except:
                showerror("Open Source File", "Failed to read file\n'%s'" % fname)

            self.next_img('none')
        
        return

    def next_img(self, direction):
        """ Increments the current image index based on the direction given to the function.
        """
        ## Check if an entry widget has focus, in which case do not run this function
        # print(" %s has focus" % self.instance.focus_get())
        active_widget = self.instance.focus_get()
        if isinstance(active_widget, tk.Entry):
            if DEBUG: print(" Entry widget has focus, do not run next_img function")
            return

        ## find the files in the working directory
        image_list = images_in_dir(self.working_dir, self.USE_MRC.get(), DEBUG = DEBUG)
        if len(image_list) == 0:
            print(" No images found in working directory! ")
            exit()

        ## adjust the index based on the input type
        if direction == 'right':
            self.index += 1
            # reset index to the first image when going past the last image in the list
            if self.index > len(image_list)-1 :
                self.index = 0
        if direction == 'left':
            self.index -= 1
            # reset index to the last image in the list when going past 0
            if self.index < 0:
                self.index = len(image_list)-1

        if DEBUG: print(" Load next image: %s" % image_list[self.index])
        self.load_img(image_list[self.index])

        return

    def toggle_SHOW_PICKS(self):
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

    def pick_diameter_updated(self):
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
            ## update the display widget that converts this number into pixels 
            pixel_length = int(self.picks_diameter / self.pixel_size)
            self.particle_diameter_pixels_LABEL['text'] = "%s px" % pixel_length
            self.suggested_angpix_LABEL['text'] = "Crop to: ~%.1f Å/px" % suggest_target_angpix(self.picks_diameter)
            ## pass focus back to the main instance
            self.instance.focus()
            self.draw_image_coordinates()
        else:
            self.picks_diameter_ENTRY.delete(0, tk.END)
            self.picks_diameter_ENTRY.insert(0,self.picks_diameter)
            print(" Input requires positive integer values")
        return

    def sigma_updated(self):
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
            if DEBUG: print("sigma contrast updated to %s" % user_input )
            self.sigma_contrast = user_input
            ## pass focus back to the main instance
            self.instance.focus()
            self.next_img('none')
        else:
            self.sigma_contrast_ENTRY.delete(0, tk.END)
            self.sigma_contrast_ENTRY.insert(0,self.sigma_contrast)
            print(" Input requires positive float values")

        return

    def scale_updated(self):
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
            # ## rescale any existing particle picks to approximately the same position
            ## update the scale factor on the instance
            self.scale_factor = user_input
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

    def load_img(self, fname, input_im_array = None):
        """ Load the image with the given file name, or if an image object is given load that instead 
        """
        ## check if there was an input im array 
        if isinstance(input_im_array, np.ndarray):
            ## use the input img array to form the image instead of looking for it by name and assign it to the saved img datums
            img_contrasted = input_im_array
            im_obj = get_PhotoImage_obj(img_contrasted)
        else:
            if self.USE_MRC:
                ## it is much faster if we scale down the image prior to doing filtering
                mrc_im_array, self.pixel_size = get_mrc_raw_data(fname)
                img_scaled = resize_image(mrc_im_array, self.scale_factor)
                img_array = mrc2grayscale(img_scaled, self.pixel_size / self.scale_factor)
                img_contrasted = sigma_contrast(img_array, self.sigma_contrast)  
                im_obj = get_PhotoImage_obj(img_contrasted)

                self.mrc_dimensions = (mrc_im_array.shape[1], mrc_im_array.shape[0])

            else:
                with PIL_Image.open(fname) as im:
                    
                    new_dimensions = get_resized_dimensions(100 * self.scale_factor, im.size)
                    im = im.resize(new_dimensions)
                    im = im.convert('L') ## make grayscale
                    # im = im.convert('RGB') ## make RGB ;; note that local contrast function does not work on RGB images atm   
                    img_array = np.asarray(im)
                    img_contrasted = sigma_contrast(img_array, self.sigma_contrast)
                    im_obj = get_PhotoImage_obj(img_contrasted)

                    # im_obj = ImageTk.PhotoImage(im)

        ## update the display data on the class
        self.display_data = [ im_obj ]
        self.display_im_arrays = [ img_contrasted ]
        self.image_name = os.path.basename(fname)

        # a, b = get_fixed_array_index(1, 1)
        ## initialize a canvas if it doesnt exist yet
        if len(self.displayed_widgets) == 0:
            self.add_canvas(self.scrollable_frame, img_obj = im_obj, row = 0, col = 0, canvas_reference = self.displayed_widgets, img_reference = self.display_data)
        else:
            ## otherwise, just update the display data instead of creating a fresh canvas object
            if DEBUG: print(" redraw existing canvas")
            self.load_img_on_canvas(self.displayed_widgets[0], self.display_data[0])

        ## update label/entry widgets
        self.update_input_widgets()

        ## draw image coordinates if necessary
        self.draw_image_coordinates()

        return

    def debugging(self):
        image_name = os.path.splitext(self.image_name)[0]
        ## check if the image_name is in self.coordinates dictionary 

        print("===================================")
        print(" Debugging log: ")
        print("    Loaded img = %s" % image_name)
        print("    Display threshold score = %s" % self.picks_threshold)
        if not image_name in self.coordinates:
            print("   # coordinates this img = 0")
        else:
            print("    # coordinates this img = %s" % len(self.coordinates[image_name]))
            print("      e.g.: ")
            print("          ", self.coordinates[image_name])

        print("===================================")
        return

    def select_all(self, widget):
        """ This function is useful for binding Ctrl+A with
            selecting all text in an Entry widget
        """
        return widget.select_range(0, tk.END)

    def update_input_widgets(self):
        """ Updates the input widgets on the main GUI to take on the values of the global dictionary.
            Mainly used after loading a new settings file.
        """
        self.image_name_label.delete(0, tk.END)
        self.image_name_label.insert(0,self.image_name)

        self.scale_ENTRY.delete(0, tk.END)
        self.scale_ENTRY.insert(0,self.scale_factor)

        self.sigma_contrast_ENTRY.delete(0, tk.END)
        self.sigma_contrast_ENTRY.insert(0,self.sigma_contrast)

        self.picks_diameter_ENTRY.delete(0, tk.END)
        self.picks_diameter_ENTRY.insert(0,self.picks_diameter)

        pixel_length = int(self.picks_diameter / self.pixel_size)
        self.particle_diameter_pixels_LABEL['text'] = "%s px" % pixel_length

        self.suggested_angpix_LABEL['text'] = "Crop to: ~%.1f Å/px" % suggest_target_angpix(self.picks_diameter)

        self.MRC_dimensions_LABEL['text'] = "(%s, %s)" % (self.mrc_dimensions)
        self.MRC_angpix_LABEL['text'] = "%s Å/px" % (self.pixel_size)
        self.MRC_displayed_angpix_LABEL['text'] = "Display @ %0.2f Å/px" % (self.pixel_size / self.scale_factor)

        # self.draw_image_coordinates()

        return

    def initialize_scrollable_window(self, viewport_frame):
        self.viewport_canvas = viewport_canvas = tk.Canvas(viewport_frame)
        self.viewport_scrollbar_y = viewport_scrollbar_y = ttk.Scrollbar(viewport_frame, orient="vertical", command=viewport_canvas.yview)
        self.viewport_scrollbar_x = viewport_scrollbar_x = ttk.Scrollbar(viewport_frame, orient="horizontal", command=viewport_canvas.xview)
        self.scrollable_frame = scrollable_frame = ttk.Frame(viewport_canvas)
        self.scrollable_frame.bind("<Configure>", lambda e: viewport_canvas.configure(scrollregion=viewport_canvas.bbox("all")))

        viewport_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.viewport_canvas.configure(yscrollcommand=viewport_scrollbar_y.set, xscrollcommand=viewport_scrollbar_x.set)

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
        dropdown_file.add_command(label="Open particle file", command=self.load_particle_picks)
        dropdown_file.add_command(label="Save particles (Ctrl + S)", command=self.write_particles_file)
        dropdown_file.add_command(label="Quick save particles (Ctrl + Shift + S, or F5)", command=self.write_particles_file)
        dropdown_file.add_command(label="Exit", command=self.quit)

        ## dropdown menu --> Image processing functions 
        dropdown_functions = tk.Menu(menubar)
        menubar.add_cascade(label="Functions", menu=dropdown_functions)
        dropdown_functions.add_command(label="Autopicking (Ctrl + X)", command = lambda: self.open_panel("AutopickPanel"))
        dropdown_functions.add_command(label="Clear picks on image", command = lambda: self.clear_coordinates())
        dropdown_functions.add_command(label="Local contrast", command=self.local_contrast)
        dropdown_functions.add_command(label="Blur", command=self.gaussian_blur)
        dropdown_functions.add_command(label="Local contrast & Blur (Ctrl + C)", command=self.local_contrast_and_blur)
        dropdown_functions.add_command(label="Auto-contrast", command=self.auto_contrast)
        # dropdown_functions.add_command(label="Contrast from selection", command=self.contrast_by_selected_particles)
        dropdown_functions.add_command(label="Reset img", command=lambda: self.load_img(self.image_name))

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

    def determine_program_dimensions(self, data_frame):
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

    def canvas_callback(self, event):
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

    def quit(self):
        self.save_settings()
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

    def write_particles_file(self, QUERY = True):
        if QUERY:
            ## arrange the filetypes to match the expected one
            expected_extension = os.path.splitext(self.particles_file_save_name)[1]
            if expected_extension.lower() == ".coord":
                filetypes = [("Coordinate","*.coord"),("Text","*.txt"),("All Files","*.*")]
            elif expected_extension.lower() == ".txt":
                filetypes = [("Text","*.txt"),("Coordinate","*.coord"),("All Files","*.*")]
            else: 
                filetypes = [("Text","*.txt"),("Coordinate","*.coord"),("All Files","*.*")]

            save_path = asksaveasfilename(parent = self.instance, initialfile = "%s" % self.particles_file_save_name, 
                                            defaultextension="%s" % expected_extension,
                                            filetypes=filetypes)
        else:
            ## save the file with current loaded defaults
            save_path = os.path.join(self.working_dir, self.particles_file_save_name)
            print(" Quick saving file: %s" % save_path)

        if len(save_path) <= 0:
            return 
        
        ## update the instance to take in the new save name into its meta data
        save_dir, save_name = os.path.split(str(save_path))
        self.particles_file_save_name = save_name

        ## add a prompt window if file already exists
        # if os.path.isfile(save_path):
        #     answer = askyesno('Warning', 'Overwrite existing particle coordinates file?')
        #     if answer == False:
        #         return 

        ## initialize the file with the header before appending particles 
        with open(save_path, 'w') as f : # NOTE: 'w' == overwrite existing file; 'a' appends to file
            f.write("%s\t%s\t%s\t%s\n" % ('image_name', 'x_coord', 'y_coord', 'score'))

        counter = 0
        with open(save_path, 'a') as f : 
            for img in self.coordinates:
                for Xcoord, Ycoord, score in self.coordinates[img]:
                    f.write("%s\t%s\t%s\t%s\n" % (img, Xcoord, Ycoord, score))
                    counter += 1
        print(" Wrote %s particles to: %s" % (counter, save_path))
        return 

    def save_settings(self):
        """ Write out a settings file for ease of use on re-launching the program in the same directory
        """
        save_fname = '.topaz_viewer.config'
        save_path = os.path.join(self.working_dir, save_fname)

        ## sanity check a file is loaded into buffer, otherwise no reason to save settings
        if len(self.image_name) <= 0:
            print("Abort save settings :: No image is loaded")
            return

        with open(save_path, 'w') as f :
            f.write("## Last used settings for topaz_viewer.py\n")
            f.write("img_loaded %s\n" % self.image_name)
            f.write("picks_diameter %s\n" % self.picks_diameter)
            f.write("scale_factor %s\n" % self.scale_factor)
            f.write("sigma_contrast %s\n" % self.sigma_contrast)
            f.write("picks_threshold %s\n" % self.picks_threshold)
            f.write("particles_file_save_name %s\n" % self.particles_file_save_name)
        print(" >> Saved current settings to '%s'" % save_path)

        return 
    
    def load_settings(self):
        """ On loadup, search the directory for input files and load them into memory automatically
        """
        settingsfile = '.topaz_viewer.config'

        if os.path.exists(settingsfile):
            ## update marked file list with file in directory
            with open(settingsfile, 'r') as f :
                for line in f:
                    line2list = line.split()
                    if not '#' in line2list[0]: ## ignore comment lines
                        if line2list[0] == 'img_loaded':
                            image_to_load = line2list[1]
                        if line2list[0] == 'picks_diameter':
                            self.picks_diameter = int(line2list[1])
                        if line2list[0] == 'scale_factor':
                            self.scale_factor = float(line2list[1])
                        if line2list[0] == 'sigma_contrast':
                            self.sigma_contrast = float(line2list[1])
                        if line2list[0] == 'picks_threshold':
                            self.picks_threshold = float(line2list[1])
                        if line2list[0] == 'particles_file_save_name':
                            self.particles_file_save_name = line2list[1]

        ## update the index to match the image we wanted to load, with a fallback to the first image on a failure
        try:
            image_list = images_in_dir(self.working_dir, self.USE_MRC.get(), DEBUG = DEBUG) 
            self.index = image_list.index(image_to_load)
        except:
            print(" ERROR: Settings file points to image that does not exist in working directory! Resetting index to 0")

        return

    #region :: IMAGE PROCESSING FUNCTIONS 
    def local_contrast_and_blur(self):
        self.local_contrast()
        self.gaussian_blur()
        return 

    def local_contrast(self):
        ## get the image array from buffer 
        display_im_array = self.display_im_arrays[0]
        ## send the array to the image_handler function 
        im = image_handler.local_contrast(display_im_array, self.picks_diameter, DEBUG = DEBUG)
        ## get the updated array and pass it to the load_img function 
        self.load_img(self.image_name, input_im_array=im)
        return

    def gaussian_blur(self):
        ## get the image array from buffer 
        display_im_array = self.display_im_arrays[0]
        ## send the array to the image_handler function 
        im = image_handler.gaussian_blur(display_im_array, 1.5)
        ## get the updated array and pass it to the load_img function 
        self.load_img(self.image_name, input_im_array=im)
        return

    def auto_contrast(self):
        """ Use the auto_contrast function on the loaded image
        """
        ## get the image array from buffer 
        display_im_array = self.display_im_arrays[0]
        ## send the array to the image_handler function 
        im = image_handler.auto_contrast(display_im_array)
        ## get the updated array and pass it to the load_img function 
        self.load_img(self.image_name, input_im_array=im)
        return

    #endregion 

class AutopickPanel(MainUI):
    """ Panel GUI for user options for autopicking
    """
    def __init__(self, mainUI): # Pass in the main window as a parameter so we can access its methods & attributes
        self.mainUI = mainUI # Make the main window an attribute of this Class object
        self.panel = tk.Toplevel() # Make this object an accessible attribute
        self.panel.title('Autopicking')
        # self.panel.geometry('500x310')
        # self.viewport_frame = viewport_frame =  ttk.Frame(self.panel)
        
        ## Parameters 
        self.loaded_template_im_array = None
        self.loaded_template_displayObj = None
        self.canvas_size = 150 # px
        self.picking_threshold = 0.3


        ## Define widgets

        ## 1. buttons
        self.generate_template_from_picks_button = tk.Button(self.panel, text="Template from picks", font = ('Helvetica', '9'), command = lambda: self.generate_template_from_picks(), width=18)
        self.load_template_button = tk.Button(self.panel, text="Load template", font = ('Helvetica', '10'), command = lambda: self.load_template(), width=10)
        self.save_template_button = tk.Button(self.panel, text="Save template", font = ('Helvetica', '10'), command = lambda: self.save_template(), width=10)
        self.autopick_button = tk.Button(self.panel, text="Autopick", font = ('Helvetica', '12'), command = lambda: self.submit_autopicker_job(), width=10)
        self.clear_coordinates_button = tk.Button(self.panel, text="Clear picks", font = ('Helvetica', '9'), command = lambda: self.clear_picked_coordinates(), width=10)

        ## 2. threshold slider
        self.threshold_label = tk.Label(self.panel, text = 'Picking threshold:', anchor = tk.S, font = ('Helvetica', '9'))
        self.threshold_slider = tk.Scale(self.panel, from_=0, to=1, resolution=0.01, orient= tk.HORIZONTAL, length = 250, sliderlength = 20, command=self.on_threshold_change)
        self.threshold_slider.set(self.picking_threshold)

        
        ## 3. canvas for template
        self.canvas_label = tk.Label(self.panel, text = 'Template loaded:', anchor = tk.S, font = ('Helvetica', '10'))
        self.canvas = tk.Canvas(self.panel, width = self.canvas_size, height = self.canvas_size, background="gray")

        ## 4. separator widgets for aesthetics 
        self.separator1 = ttk.Separator(self.panel, orient='horizontal')
        self.separator2 = ttk.Separator(self.panel, orient='horizontal')
        self.separator3 = ttk.Separator(self.panel, orient='horizontal')


        ## Pack widgets
        self.generate_template_from_picks_button.grid(column = 0, row = 0, pady = 7, padx=5)
        self.load_template_button.grid(column = 1, row = 0, pady = 7, padx=5)
        self.save_template_button.grid(column = 2, row = 0, pady = 7, padx=5)
        self.separator1.grid(column = 0, row = 1, columnspan = 3, sticky=tk.EW)
        self.threshold_label.grid(column = 0, row = 2, columnspan = 1, sticky=tk.SE)
        self.threshold_slider.grid(column=1, row=2, columnspan = 2, padx=5, sticky=tk.W)
        self.separator2.grid(column = 0, row = 3, columnspan = 3, sticky=tk.EW)
        self.canvas_label.grid(column = 0, row = 4, columnspan = 3, sticky=tk.W, pady=5, padx=10)
        self.canvas.grid(column = 0, row = 5, columnspan = 3, pady=5)
        self.separator1.grid(column = 0, row = 6, columnspan = 3, sticky=tk.EW)
        self.autopick_button.grid(column=1, row= 7, pady=10)
        self.clear_coordinates_button.grid(column=2, row=7, padx = 10, sticky=tk.W)


        ## Add some hotkeys for ease of use
        # self.panel.bind('<Left>', lambda event: self.cutoff_slider.set(self.cutoff_slider.get() - 1))
        # self.panel.bind('<Right>', lambda event: self.cutoff_slider.set(self.cutoff_slider.get() + 1))
        self.panel.bind('<Return>', lambda event: self.submit_autopicker_job())
        self.panel.bind('<KP_Enter>', lambda event: self.submit_autopicker_job()) # numpad 'Return' key

        ## Set focus to the panel
        self.panel.focus()

        ## add an exit function to the closing of this top level window
        self.panel.protocol("WM_DELETE_WINDOW", self.close)

        return

    def close(self):
        ## unset the panel instance before destroying this instance
        self.mainUI.autopickPanel_instance = None
        ## destroy this instance
        self.panel.destroy()
        return

    def display_template(self):
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
            self.mainUI.template_picker(self.loaded_template_im_array, float(self.threshold_slider.get()))
        return
    
    def generate_template_from_picks(self):
        template = self.mainUI.make_template_from_picks()
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

        cv2.imwrite(outfname, self.loaded_template_im_array)
        print(" Written currently loaded template out: ")
        print("   >> %s" % os.path.abspath(outfname))
        return 
    
    def load_template(self):
        ## later add a gui to select the file explicitly 
        filename = 'template.png'

        ## use cv2 to load the image data then cast it as an integer np.ndarray
        cv_im = cv2.imread(filename, cv2.IMREAD_GRAYSCALE)
        im_array = np.array(cv_im).astype(np.uint8)

        ## assign the array to the template container
        self.loaded_template_im_array = im_array 
        self.display_template()

        print(" Loading template image: ")
        print("   >> %s" % os.path.abspath(filename))

        return 

    def on_threshold_change(self, slider_value):

        ## set the threshold value to the instance 
        self.picks_threshold = slider_value
        print(" Template picking threshold = %s" % slider_value )

        return 

    def clear_picked_coordinates(self):
        self.mainUI.clear_coordinates()
        return 


#endregion

##########################
#region :: RUN BLOCK
##########################
if __name__ == '__main__':
    from operator import itemgetter
    import sys
    import tkinter as tk
    from tkinter.filedialog import askopenfilename, asksaveasfilename
    from tkinter.messagebox import showerror, askyesno
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

    import scipy.ndimage as ndimage
    import pandas as pd 

    ## Get the execution path of this script so we can find local modules
    script_path = os.path.dirname(os.path.abspath(sys.argv[0]))

    try:
        sys.path.append(script_path)
        import image_handler #as image_handler
    except :
        print(" ERROR :: Check if image_handler.py script is in same folder as this script and runs without error (i.e. can be compiled)!")


    ## parse the commandline in case the user added specific file to open, it will open the last one if more than one is given 
    start_index =  0

    try:
        particle_data = load_topaz_csv(sys.argv[1], DEBUG = DEBUG )
    except:
        particle_data = dict() 

    root = tk.Tk()
    app = MainUI(root, start_index, particle_data)
    root.mainloop()

#endregion 