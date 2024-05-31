#!/usr/bin/env python3

"""
    An alternative preprocessing script for adjusting mrc files for use by topaz 
"""

## 2024-05-27: Adapted from mrc2img.py 

#############################
#region     FLAGS
#############################
DEBUG = False

#endregion 

#############################
#region     DEFINITION BLOCK
#############################

def usage():
    """ This script requires several input arguments to work correctly. Check they exist, otherwise print usage and exit.
    """
    print("===================================================================================================")
    print(" Usage:")
    print("    $ topaz_preproc_mrc.py  input.mrc  --o output.mrc  <options>  # specify output concretely")
    print("    $ topaz_preproc_mrc.py  ../dir/input.mrc  <options>           # writes output to cwd")
    print(" Batch mode with parallelization:")
    print("    $ topaz_preproc_mrc.py  ../dir/@.mrc  <options>  --j <n>")
    print(" Example:")
    print("    $ topaz_preproc_mrc.py  raw/@.mrc --out_dir proc/  --norm  --rescale_angpix <a>  --j <n>")
    print(" -----------------------------------------------------------------------------------------------")
    print(" Options (default in brackets): ")
    print("   --rescale_angpix (3.0) : rescale the pixel size of the image to this value")
    print("                   --norm : Normalize the image to avg of 0 and stdev of 1")
    print("           --out_dir (./) : If using batch mode, can specify where to place the output files rather in the cwd")
    print("                  --j (4) : Allow multiprocessing using indicated number of cores")
    print("===================================================================================================")
    sys.exit()
    return

def parse_cmdline(cmdline):
    ## initialize the PARAMETERS object to hold the values we parse 
    PARAMS = PARAMETERS()

    if len(cmdline) < 2:
        usage()

    ## first check for the help flag before proceeding 
    for i in range(len(cmdline)):
        if cmdline[i] in ['-h', '--h', '-H', '--H']:
            usage()     

    ## iterate over every entry, looking for flags 
    for i in range(len(cmdline)):

        ## check for expected input file 
        if len(cmdline[i]) > 4:
            if cmdline[i][-4:].lower() == '.mrc':
                ## avoid detecting the .mrc file if it is preceded by the --o flag! 
                SKIP = False
                if i > 2:
                    if cmdline[i - 1] in ['--o']:
                        SKIP = True 
                if not SKIP:                    
                    # print(" Detected input file = %s" % cmdline[i])
                    input_path, input_fname = os.path.split(cmdline[i])
                    basename = os.path.splitext(input_fname)[0]

                    ## check if this is a batch job 
                    if '@' in basename:
                        PARAMS.set_batch_mode(True)
                        PARAMS.set_input_file(cmdline[i])

                    ## otherwise we are running in single-file mode 
                    else:
                        ## sanity check file exists
                        if not os.path.exists(cmdline[i]):
                            print( " !! ERROR :: Input file not found (%s) "% cmdline[i])
                            exit()
                        else:
                            PARAMS.set_input_file(cmdline[i])

        if cmdline[i] in ['--rescale_angpix']:
            if len(cmdline) > i+1:
                PARAMS.set_rescale_angpix(cmdline[i+1])

        if cmdline[i] in ['--norm']:
            PARAMS.set_normalize(True)

        if cmdline[i] in ['--j']:
            if len(cmdline) > i+1:
                PARAMS.set_threads(cmdline[i+1])
            
            PARAMS.set_parallelize(True)

        if cmdline[i] in ['--o']:
            if len(cmdline) > i+1:
                PARAMS.set_output_file(cmdline[i+1])
            
        if cmdline[i] in ['--out_dir', '--out-dir']:
            if len(cmdline) > i+1:
                PARAMS.set_output_dir(cmdline[i+1])


    # ## sanity check we have an output file name if we are not running in batch mode 
    # if len(PARAMS.input_file) > 0:
    #     if len(PARAMS.output_file) < 1:
    #         print(" !! WARNING :: No output file given (e.g. --o <filename> missing), will write out file in current working directory")
    #         exit()

    return PARAMS

def get_mrc_data(file):
    """ 
        PARAMETERS 
            file = str(); path-like string to .mrc file
            returns = np.ndarray of the mrc data using mrcfile module
    """
    try:
        with mrcfile.open(file) as mrc:
            ## get the raw image
            image_data = mrc.data.astype(np.float32) ## need to cast it as a float32, since some mrc formats are uint16! (i.e. mode 6)

            ## grab the pixel size from the header 
            pixel_size = np.around(mrc.voxel_size.item(0)[0], decimals = 3)
    except:
        print(" There was a problem opening .MRC file (%s), try permissive mode. Consider fixing this file later!" % file)
        with mrcfile.open(file, permissive = True) as mrc:
            ## get the raw image
            image_data = mrc.data.astype(np.float32) ## need to cast it as a float32, since some mrc formats are uint16! (i.e. mode 6)

            ## grab the pixel size from the header 
            pixel_size = np.around(mrc.voxel_size.item(0)[0], decimals = 3)

    if DEBUG:
        print("=================================")
        print("   get_mrc_data :: %s" % file)
        print("---------------------------------")
        print("     img shape =", image_data.shape)
        print("    pixel_size = %s" % pixel_size )
        print("=================================")

    return image_data, pixel_size

def write_image(input_file, output_file, output_dir, rescale_angpix, normalize):
    check_dependencies()

    ## load the image from the .MRC file
    img_path = input_file 
    im_array, angpix = get_mrc_data(img_path)

    ## check if we are resizing the image 
    if rescale_angpix != None:
        ## determine the scaling factor 
        scaling_factor = get_scale_factor(angpix, rescale_angpix)
        ## apply the scaling factor to resize the image using the cv2 library 
        im_array = resize_image(im_array, scaling_factor)

    ## check if we are normalizing the image 
    if normalize:
        ## normalize using a simple procedure (later can try GMM)
        im_array = normalize_image(im_array)

    ## determine the output filename, eiher from params obj or generate it dynamically
    if len(output_file) == 0:
        ## use the input file base name stripped of any path 
        input_path, input_fname = os.path.split(input_file)
        output_file = input_fname

    if DEBUG:        
        print(" input file = %s" % input_file)
        print(" output_file = %s" % output_file) 

    ## save out the edited im_array as a new mrc file 
    save_mrc_image(im_array, output_file, output_dir, rescale_angpix)

    # ## reset the output file variable 
    # params.reset_output_file()
    return  

def get_scale_factor(current_sampling, target_sampling):
    ## get the scale factor 
    scaling_factor = current_sampling / target_sampling

    ## bound the possibility to a resonable range  
    if scaling_factor > 3:
        ## avoid too large sampling
        print(" !! ERROR :: Requested scaling factor is too high (%s -> %s, upsampling of %s)" %  (current_sampling, target_sampling, scaling_factor))
        print(" Consider adjusting the rescale_angpix value higher")
        exit()
    elif scaling_factor < 0.01:
        ## avoid too small sampling 
        print(" !! ERROR :: Requested scaling factor is too low (%s -> %s, downsampling of %s)" %  (current_sampling, target_sampling, scaling_factor))
        print(" Consider adjusting the rescale_angpix value lower")
        exit()

    if DEBUG:
        print("=================================")
        print("   get_scale_factor ")
        print("---------------------------------")
        print("     %s -> %s" % (current_sampling, target_sampling))
        print("    scale factor = %s" % scaling_factor )
        print("=================================")
    return scaling_factor

def resize_image(img_nparray, scaling_factor, interpolation_method = 'AREA'):
    """ Uses OpenCV to resize an input grayscale image (0-255, 2d array) based on a given scaling factor
            img_nparray = np.array of dtype float32
            scaling_factor = float()
            interpolation_method = str(), flag corresponding to the library defined in this method
    """
    ## possible interpolation methods from cv2 library 
    inter_methods = {
        'NEAREST' : cv2.INTER_NEAREST,
        'LINEAR' : cv2.INTER_LINEAR,
        'CUBIC' : cv2.INTER_CUBIC,
        'AREA' : cv2.INTER_AREA,
        'LANCZOS4' : cv2.INTER_LANCZOS4,
        'LINEAR_EXACT' : cv2.INTER_LINEAR_EXACT,
        'NEAREST_EXACT' : cv2.INTER_NEAREST_EXACT

    }

    ## check if the input np.array is type float32 which is necessary for cv2.resize function 
    if not img_nparray.dtype == 'float32':
        print(" ERROR :: Input np.array is not dtype np.float32, recast it before running this function")
        return 

    # original_width = img_nparray.shape[1]
    # original_height = img_nparray.shape[0]
    scaled_width = int(img_nparray.shape[1] * scaling_factor)
    scaled_height = int(img_nparray.shape[0] * scaling_factor)

    # print("resize_img function, original img_dimensions = ", img_nparray.shape, img_nparray.dtype,", new dims = ", scaled_width, scaled_height)
    resized_im = cv2.resize(img_nparray, (scaled_width, scaled_height), interpolation = inter_methods[interpolation_method]) 
    # resized_im = cv2.resize(img_nparray, (scaled_width, scaled_height)) ## note: default interpolation is INTER_LINEAR, and does not work well for noisy EM micrographs 

    if DEBUG: 
        print("=================================")
        print("   resize_image " )
        print("---------------------------------")
        print("  interpolation method = %s" % interpolation_method)
        print("   input array =", img_nparray.shape) 
        print("       min = %s, max = %s" % (np.min(img_nparray), np.max(img_nparray)))
        print("   output array =", resized_im.shape) 
        print("       min = %s, max = %s" % (np.min(resized_im), np.max(resized_im)))
        print("=================================")

    return resized_im

def normalize_image(im_array):
    mu = np.mean(im_array)
    std = np.std(im_array)

    if DEBUG: 
        print("=================================")
        print("   normalize_image " )
        print("---------------------------------")
        print("   input array =", im_array.shape) 
        print("       min = %s, max = %s, mean = %s, stdev = %s" % (np.min(im_array), np.max(im_array), mu, std))

    im_array = (im_array - mu) / std 
    im_array = im_array.astype(np.float32)

    if DEBUG:
        print("   output array =", im_array.shape) 
        print("       min = %s, max = %s, mean = %s, stdev = %s" % (np.min(im_array), np.max(im_array), np.mean(im_array), np.std(im_array)))
        print("=================================")

    return im_array 

def save_mrc_image(im_data, output_name, output_dir, pixel_size):
    """
        im_data = np.array, dtype = float32
        output_name = str(); name (& optionally, path) of the output file to be saved
        output_dir = str(); relative or absolute path to save the images
        pixel_size = voxel size of the new image 
    """
    output_path = os.path.join(output_dir, output_name)
    with mrcfile.new(output_path, overwrite = True) as mrc:
        mrc.set_data(im_data)
        mrc.voxel_size = pixel_size
        mrc.update_header_from_data()
        mrc.update_header_stats()

    print(" ... written file: %s (angpix %s, mean %s, stdev %s)" % (output_path, pixel_size, np.mean(im_data), np.std(im_data)))

    return

def check_dependencies():
    ## load built-in packages, if they fail to load then python install is completely wrong!
    globals()['sys'] = __import__('sys')
    globals()['os'] = __import__('os')
    globals()['glob'] = __import__('glob')
    globals()['mp'] = __import__('multiprocessing')

    try:
        globals()['np'] = __import__('numpy') ## similar to: import numpy as np
    except:
        print(" ERROR :: Failed to import 'numpy'. Try: pip install numpy")
        sys.exit()

    try:
        from PIL import Image
    except:
        print(" Could not import PIL.Image. Install depenency via:")
        print(" > pip install --upgrade Pillow")
        sys.exit()

    try:
        globals()['mrcfile'] = __import__('mrcfile') 
    except:
        print(" ERROR :: Failed to import 'mrcfile'. Try: pip install mrcfile")
        sys.exit()

    try:
        globals()['cv2'] = __import__('cv2') 
    except:
        print(" ERROR :: Failed to import 'cv2'. Try: pip install opencv-python")
        sys.exit()


#endregion 

class PARAMETERS():
    def __init__(self, rescale_angpix = None, normalize = False, input_file = '', output_file = '', output_dir = '.'):
        self.rescale_angpix = rescale_angpix
        self.batch_mode = False
        self.input_file = input_file
        self.output_file = output_file
        self.output_dir = output_dir
        self.normalize = normalize 
        self.parallelize = False 
        self.threads = 4

        return 
    
    def set_rescale_angpix(self, input_value):
        try:
            value = float(input_value)
            self.rescale_angpix = value 
        except:
            print(" ERROR !! Could not parse value for rescaling angpix (%s)" % input_value)
            exit()
        return 

    def set_normalize(self, input_bool):
        try:
            norm = bool(input_bool)
            self.normalize = norm 
        except:
            print(" ERROR !! Could not parse normalization flag (%s)" % input_bool)
            exit()
        return 

    def set_batch_mode(self, input_bool):
        try:
            batch = bool(input_bool)
            self.batch_mode = batch 
        except:
            print(" ERROR !! Could not parse batch_mode flag (%s)" % input_bool)
            exit()
        return 

    def set_parallelize(self, input_bool):
        try:
            parallel = bool(input_bool)
            self.parallelize = parallel 
        except:
            print(" ERROR !! Could not parse parallization flag (%s)" % input_bool)
            exit()
        return 

    def set_threads(self, input_value):
        try:
            value = int(input_value)
            self.threads = value 
        except:
            print(" ERROR !! Could not parse value for threads (%s), using defaults (%s)" % (input_value, self.threads))
            exit()
        return 

    def set_input_file(self, input_str):
        if len(self.input_file) > 0 and not self.batch_mode:
            print(" !! ERROR :: More than one input file is trying to be specified (%s, %s), did you miss the '--o' flag to define the output file?" % (input_str, self.input_file))
            exit()
        if len(input_str) > 0:
            self.input_file = input_str
        else:
            print(" ERROR !! No input file name given!")
        return

    def set_output_file(self, input_str):
        if len(input_str) > 0:
            self.output_file = input_str
        else:
            print(" ERROR !! No output file name given!")
        return

    def set_output_dir(self, input_str):
        if len(input_str) > 0:
            self.output_dir = input_str
            ## check directory exists 
            if not os.path.isdir(self.output_dir):
                print(" !! ERROR :: Output directory (%s) given does not exist!" % self.output_dir)
                exit()
        else:
            print(" ERROR !! No output file name given!")
        return 

    def reset_output_file(self):
        self.output_file = ''
        return 

    def __str__(self):
        print("=============================")
        print("  PARAMETERS")
        print("-----------------------------")

        if self.batch_mode:
            print("  Batch mode = %s" % self.batch_mode)
            print("     ... fetching all from: %s" % self.input_file)
            print("     ... saving into: %s" % self.output_dir)

        else:
            print("  Input file = %s" % self.input_file)
            print("  Output file = %s" % self.output_file)
        print("  Rescale angpix = %s" % self.rescale_angpix)
    
        print("  Normalization = %s" % self.normalize)
        if self.parallelize:
            print("  Parallelize = %s " % self.parallelize)
            print("  Threads = %s" % self.threads)
        print("=============================")

        return ''


#############################
#region     RUN BLOCK
#############################

if __name__ == "__main__":

    import os
    import sys
    import glob
    import numpy as np
    from multiprocessing import Process, Pool
    import time


    try:
        import mrcfile
    except:
        print(" Could not import mrcfile module. Install via:")
        print(" > pip install mrcfile")
        sys.exit()

    try:
        import cv2 ## for resizing images with a scaling factor
    except:
        print("Could not import cv2, try installing OpenCV via:")
        print("   $ pip install opencv-python")
    ##################################

    start_time = time.time()

    ## Parse commandline 
    cmdline = sys.argv
    PARAMS = parse_cmdline(cmdline)
    if DEBUG:
        print(PARAMS)

    # ## check if batch mode was enabled while also providing an explicit input file
    # if PARAMS.batch_mode and len(PARAMS.input_file) > 0:
    #     print(" ERROR :: Cannot launch batch mode using `@' symbol while also providing an explicit input file!")
    #     print(" Remove the input file and re-run to enable batch mode processing")
    #     sys.exit()



    if not PARAMS.batch_mode:
        ## warn the user if they activated parallel processing for a single image
        if PARAMS.parallelize:
            print(" NOTE: --j flag was set for parallel processing, but without batch mode. Only 1 core can be used for processing a single image.")
            ## single image conversion mode

        write_image(PARAMS.input_file, PARAMS.output_file, PARAMS.output_dir, PARAMS.rescale_angpix, PARAMS.normalize)

    else:
        if PARAMS.parallelize:
            print(" ... multithreading activated (%s threads) " % PARAMS.threads)

            ## multithreading set up
            threads = PARAMS.threads

            tasks = []
            ## extract the path to the input files based on the input string supplied   
            input_path, input_fname = os.path.split(PARAMS.input_file)
            ## get all files and prepare an independent PARAMS object to use for parallization 
            for file in glob.glob(os.path.join(input_path, "*.mrc")):
                # current_params = (PARAMETERS(rescale_angpix = PARAMS.rescale_angpix, normalize = PARAMS.normalize, input_file = file, output_file = '')) ## NOTE: Sadly cannot pass in custom objects into the pool starmap function; refactor the write_image function to take in simple python types
                tasks.append( (file, '', PARAMS.output_dir, PARAMS.rescale_angpix, PARAMS.normalize) )

            try:
                ## prepare pool of workers
                pool = Pool(threads)
                ## assign workload to pool
                results = pool.starmap(write_image, tasks)
                ## close the pool from recieving any other tasks
                pool.close()
                ## merge with the main thread, stopping any further processing until workers are complete
                pool.join()

            except KeyboardInterrupt:
                print("Multiprocessing run killed")
                pool.terminate()

        else:
            ## extract the path of the input files based on the input 
            input_path, input_fname = os.path.split(PARAMS.input_file)
            # print(" %s, %s, %s" % (PARAMS.input_file, input_path, input_fname))
            ## get all files with extension
            for file in glob.glob(os.path.join(input_path, "*.mrc")):
                PARAMS.set_input_file(file)
                write_image(PARAMS.input_file, PARAMS.output_file, PARAMS.output_dir, PARAMS.rescale_angpix, PARAMS.normalize)

    end_time = time.time()
    total_time_taken = end_time - start_time
    print("... runtime = %.2f sec" % total_time_taken)
    ## non-parallelized = 17.08 sec, 16.49 sec, 16.62 sec
    ## parallized, manual mode = 12.43 sec, 12.95 sec, 12.12 sec
    ## parallized, pool mode = 8.42 sec, 8.24 sec, 8.2 sec

#endregion