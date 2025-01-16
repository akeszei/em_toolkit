#!/usr/bin/env python3

## Author : A. Keszei 

## 2024-07-25: Initial script started
## 2024-10-11: The logfile needs to be re-written every time the program restarts... it should find the micrographs, then check for the corresponding text file in the ctf directory and corresponding jpg and fix all mismatches. Then it should re-build the logfile.   
## 2025-01-15: Focus on correct parsing of working directory to allow easy user determination of what squares micrograhs are coming from after-the-fact 

#############################
#region     GLOBAL FLAGS
#############################
DEBUG = False
DRY_RUN = False
h_bar = "==============================================="
h_sub_bar = "------------------------------------"

#endregion
#############################


#############################
#region     CUSTOM OBJECTS
#############################
class PARAMETERS():
    """
    Create an object to contain all parsing and active parameters for the session that we can easily refer to and debug in one location 
    """
    def __init__(self, cmdline):
        ## initialize the object with a commandline input that we can parse 
        ## default parameters on the object 
        self.angpix = False 
        self.movie_glob = "*Fractions.mrc"
        self.jpg_dir = "jpg"
        self.mrc_dir = "micrographs"
        self.ctf_dir = "ctf"
        self.save_movies = False
        self.movie_dir = "movies"
        self.seconds_delay = 5
        self.kV = False
        self.frame_dose = False 
        self.logfile = "ctf.star"
        self.atlas_dir = False    
        self.epu_dir = False


        self.parse_cmdline(cmdline)

        return

    def parse_cmdline(self, cmdline):

        ## read all entries and check if the help flag is called at any point
        for cmd in cmdline:
            if cmd == '-h' or cmd == '--help' or cmd == '--h':
                usage()

        ## parse any flags 
        for i in range(len(cmdline)):
            if cmdline[i] == '--save_movies' or cmdline[i] == '--save_movie':
                self.save_movies = True
            if cmdline[i] == '--angpix':
                try:
                    self.angpix = float(cmdline[i+1])
                except:
                    print(" Could not parse --angpix entry or none given, will read directly from movie")
            if cmdline[i] == '--kV' or cmdline[i] == '--kv':
                try:
                    self.kV = float(cmdline[i+1])
                except:
                    print(" Could not parse --kV entry or none given")
            if cmdline[i] == '--frame_dose':
                try:
                    self.frame_dose = float(cmdline[i+1])
                except:
                    print(" Could not parse --frame_dose entry or none given")

            if "*" in cmdline[i]:
                self.movie_glob = cmdline[i]

        ## check for corresponding directories for EPU session and potential atlas directory 

        for i in range(len(cmdline)):
            ## ignore the first entry on the cmdline (the calling of the script itself)
            if i == 0:
                continue 

            if '/' in cmdline[i] or '\\' in cmdline[i]:
                if self.epu_dir == False:
                    if self.check_if_EPU_directory(cmdline[i]):
                        self.epu_dir = cmdline[i]
                        continue 
                
                if self.atlas_dir == False:
                    if self.check_if_atlas_directory(cmdline[i]):
                        self.atlas_dir = cmdline[i]
                        continue 
                
                print(" WARNING :: Could not parse input directory:", cmdline[i])
                
        if self.epu_dir == False:
            print(" ERROR :: No EPU directory was detected as input (i.e. lacking EpuSession.dm file and/or Images-Disc1 directory!")
            usage()

        
        print(h_bar)
        print(" PARAMETERS :: ")  #%s" % cmdline)
        print(h_sub_bar)
        print("   EPU directory = %s" % self.epu_dir)
        print("   Movie glob string = %s" % self.movie_glob)
        if self.atlas_dir != False:
            print("   Atlas directory = %s" % self.atlas_dir)
        else:
            print("   No atlas directory provided")

        print("   Pixel size = %s" % self.angpix)
        if self.kV != False:
            print("   kV = %s" % self.kV)
        if self.frame_dose != False:
            print("   frame dose = %s e/A**2/frame" % self.frame_dose)
        if self.save_movies != False:
            print("   Save movies = %s " % self.save_movies)
        print(h_bar)

        return 

    def check_if_EPU_directory(self, dir = "./"):

        if not os.path.isdir(dir):
            return False 
        
        SESSION_FILE = False
        IMAGES_DIR = False 

        for f in os.listdir(dir):
            if f.lower() == "EpuSession.dm".lower():
                SESSION_FILE = True 
                
            if f.lower() == "Images-Disc1".lower():
                IMAGES_DIR = True 
        
        if SESSION_FILE and IMAGES_DIR:
            return True

        return False 
    
    def check_if_atlas_directory(self, dir = "./"):
        if not os.path.isdir(dir):
            return False 
        
        ATLAS_FILE = False

        for f in os.listdir(dir):
            if f.lower()[:5] == "Atlas".lower():
                
                if f.lower()[-4:] == ".mrc".lower():
                    ATLAS_FILE = True 
        
        if ATLAS_FILE:
            return True

        return False 

    def prepare_directories(self):

        ## prepare the directory list
        dirs = [self.jpg_dir, self.mrc_dir, self.ctf_dir]
        if self.save_movies:
            dirs = dirs + [self.movie_dir]

        ## make any directories that do not already exist 
        for dir in dirs:
            if not os.path.exists(dir):
                print(" create dir :: %s" % (dir))
                os.makedirs(dir, exist_ok=True)
            else:
                continue 

        return


    # def __str__(self):
    #     print("=============================")
    #     print("  PARAMETERS")
    #     print("-----------------------------")
    #     print("   optics input file = %s" % self.optics_remap_file)
    #     print("   input star file = %s" % self.star_file)
    #     print("   output star file name = %s " % self.output_star_file)
    #     print("=============================")
    #     return ''

    def movie_save_string(self, input_movie_path):
        """"
        For a given input path to a movie in the EPU directory, unpack the path details to formulate how we want to save the movie path as 
        """
        movie_fname = os.path.split(input_movie_path)[-1]
        ## get the GridSquare_##### identity for the movie
        dirs = splitall(input_movie_path) 
        grid_square_str = dirs[-3] # by convention the GridSquare directory is 2 folders behind 
        ## update the basename of the movie to include the gridsquare identity 
        new_movie_fname = grid_square_str + "_" + movie_fname
        ## append the save path for movies to get the full save string for this movie 
        movie_save_string = os.path.join(self.movie_dir, new_movie_fname)

        return movie_save_string

    def mrc_save_string(self, input_movie_path):
        """"
        For a given input path to a movie in the EPU directory, unpack the path details to formulate how we want to save the motion corrected micrograph as  
        """
        movie_fname = os.path.split(input_movie_path)[-1] ## i.e. mic_001.mrc
        movie_basename = os.path.splitext(movie_fname)[0] ## i.e. mic_001
        ## get the GridSquare_##### identity for the movie
        dirs = splitall(input_movie_path) 
        grid_square_str = dirs[-3] # by convention the GridSquare directory is 2 folders behind 
        ## update the basename of the movie to include the gridsquare identity 
        new_movie_basename = grid_square_str + "_" + movie_basename
        ## add the .mrc extension 
        output_mrc_fname = new_movie_basename + ".mrc"
        ## append the save path for mrc files to get the full save string for the motion corrected movie 
        mrc_save_string = os.path.join(self.mrc_dir, output_mrc_fname)

        return mrc_save_string

    def jpg_save_string(self, input_movie_path):
        """"
        For a given input path to a movie in the EPU directory, unpack the path details to formulate how we want to save the motion corrected jpg as  
        """
        ## first generate the mrc name we expect, then use that to develop the string for the expected jpg file 
        mrc_fname = os.path.split(self.mrc_save_string(input_movie_path))[-1]
        mrc_basename = os.path.splitext(mrc_fname)[0] ## i.e. mic_001

        ## add the .jpg extension 
        output_jpg_fname = mrc_basename + ".jpg"
        ## append the save path for mrc files to get the full save string for the motion corrected movie 
        jpg_save_string = os.path.join(self.jpg_dir, output_jpg_fname)

        return jpg_save_string


class DATASET(): 
    """
    For ease of tracking, use a single object to hold all active log file data
    """
    def __init__(self):
        ## initialize the object with an empty dictionary that will contain all micrograph log data 
        self.data = dict()
        return 

    def __str__(self):
        print("=============================")
        print("  DATASET")
        print("-----------------------------")
        print("   # entries = %s" % len(self.data))
        if len(self.data) > 0:
            print("  e.g.:       ")

            i = 1
            for k in self.data:
                dZ = self.data[k][0]
                ctf_fit = self.data[k][1]
                if i < 4:                
                    print("     %s. %s -> dZ = %s, ctf_fit = %s" % (i, k, dZ, ctf_fit))
                    i = i+1
            if len(self.data) > 3:
                print("     ...") 

        print("=============================")
        return ''
    
    def add_entry(self, mic_name, dZ, ctf_fit):
        ## check the micrograph does not already exist in the dictionary, if it does spit out a warning to the user 
        if mic_name in self.data:
            print(" !! WARNING :: Overwriting micrograph CTF data (%s)" % mic_name)
        self.data[mic_name] = [dZ, ctf_fit]
        return 

    def entry_exists(self, mic_name):
        if mic_name in self.data:
            return True
        else:
            return False

    def get_dZ(self, mic_name):
        dZ = self.data[mic_name][0]
        return dZ

    def get_ctf_fit(self, mic_name):
        ctf_fit = self.data[mic_name][1]
        return ctf_fit


    def parse_logfile(self, fname):
        ## first check if a log file even exists yet 
        if not os.path.isfile(fname):
            return 
        
        HEADER_START, DATA_START, DATA_END = get_table_position(fname, 'data_micrographs', DEBUG=DEBUG)
        COLUMN_MIC_NAME = find_star_column(fname, '_MicrographName', HEADER_START, DATA_START, DEBUG=DEBUG)
        COLUMN_dZ = find_star_column(fname, '_dZ', HEADER_START, DATA_START, DEBUG=DEBUG)
        COLUMN_CTFFIT = find_star_column(fname, '_CtfFit', HEADER_START, DATA_START, DEBUG=DEBUG)

        ## iterate over each data point and extract the information, then parse it into a desired data structure:
        with open(fname, 'r') as f :
            line_num = 0
            parsed = 0
            for line in f :
                line_num += 1
                ## ignore empty lines
                if len(line.strip()) == 0 :
                    continue
                ## start working only after the header length
                if DATA_END >= line_num > DATA_START - 1:

                    mic_name = get_star_data(line, COLUMN_MIC_NAME)
                    dZ = float(get_star_data(line, COLUMN_dZ))
                    ctf_fit = float(get_star_data(line, COLUMN_CTFFIT))

                    self.add_entry(mic_name, dZ, ctf_fit)
                    parsed += 1

        print(" ... %s entries parsed from logfile (%s)" % (parsed, fname))
        return 


#endregion
#############################



#############################
#region     DEFINITION BLOCK
#############################

def usage():
    print("===================================================================================================")
    print(" Prepare a working directory on your local disk and point to your EPU directory on the server ")
    print(" (and, optionally, your atlas directory) to begin an on-the-fly motion correction and CTF ")
    print(" estimation pipeline. ")
    print(" Usage:")
    print("    $ EPU_on-the-fly.py  <movie_glob_string>  /path/to/EPU/dir  /path/to/atlas  <options> ")
    print(" i.e.:")
    print("    $ EPU_on-the-fly.py  /mnt/dmp/EPU_session  *Fractions.mrc  /mnt/dmp/Atlases/Sample2/Atlas  --angpix 1.566  --kV 200 --frame_dose 1.5 ")
    print(" -----------------------------------------------------------------------------------------------")
    print(" Options (default in brackets): ")
    print("       --save_movies : also save the movies")
    print("       --angpix (-1) : Angstroms per pixel in movie")
    print("       --kV (-1) : energy of the electron beam  ")
    print("       --frame_dose (-1) : e/squared angstroms for each frame (total dose / total frames)" )
    print("===================================================================================================")
    sys.exit()

def get_all_movies(EPU_dir, movie_glob):
    """
    PARAMETERS 
        EPU_dir = path-like str() pointing to the main EPU Session directory
        movie_glob = glob-like str(), i.e. containing *, that uniquely identifies a movie in the EPU session 
    RETURNS 
        movies = list() object containing all the movies found in the EPU session 
    """
    movies = list()

    ## prepare the EPU dir with infinite recursion string appended (i.e. **)
    search_dir = os.path.join(EPU_dir, "**/Data/**")
    search_glob = os.path.join(search_dir, movie_glob)
    # print(" Glob string to find movies: %s" % search_dir)
    for match in glob.glob(search_glob, recursive = True):
        movies.append(match)

    print(" %s movies found in EPU directory, e.g.: " % (len(movies)))
    print(h_sub_bar)
    if len(movies) > 0:
        for i in range(len(movies)):
            print("    %s" % movies[i])
            if i == 2: 
                print("    ...")
                break 
        
        

    return movies

def splitall(path):
    """
    Split a path into all its parts into a convenient list form, i.e.:
        /path/to/file -> ['/', 'path', 'to', 'file']
    REF: https://www.oreilly.com/library/view/python-cookbook/0596001673/ch04s16.html
    """
    allparts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path: # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    return allparts

# def get_all_micrographs_corrected(mrc_dir, movie_glob):
#     micrographs = []

#     for match in glob.glob(os.path.join(mrc_dir, movie_glob)):
#         micrographs.append(match)

#     print(" %s micrographs found in save directory (%s/)" % (len(micrographs), mrc_dir))
#     return micrographs

# def get_all_movies_not_yet_corrected(movies, micrographs): 
#     ## recast the movies and micrographs to a common basename for direct comparison using sets        
#     movies_basenames = []
#     for movie in movies:
#         movies_basenames.append(os.path.splitext(os.path.split(movie)[1])[0])

#     micrographs_basenames = []
#     for micrograph in micrographs:
#         micrographs_basenames.append(os.path.splitext(os.path.split(micrograph)[1])[0])

#     unique = list(set(movies_basenames).difference(micrographs_basenames))

#     if len(unique) > 0:
#         print(" %s movies remain to be corrected" % len(unique))
#     else:
#         print(" All movies in the EPU directory have been corrected")

#     ## use the output unique set to return a truncated list of the movies we need to correct that still contains their path information 
#     movies_to_correct = []
#     for movie in movies:
#         movie_basename = os.path.splitext(os.path.split(movie)[1])[0]
#         if movie_basename in unique:
#             movies_to_correct.append(movie)
#         else:
#             continue 

#     return movies_to_correct

# def micrographs_not_yet_CTF_estimated(ctf_dir, micrographs):
#     micrographs_to_do = []

#     if len(micrographs) == 0:
#         print(" No micrographs are available for CTF correction yet.")
#         return micrographs_to_do

#     for micrograph in micrographs:
#         micrograph_ctf_name = os.path.splitext(os.path.split(micrograph)[1])[0] + "_PS.mrc"
#         micrograph_ctf_path = os.path.join(ctf_dir, micrograph_ctf_name)
#         if os.path.exists(micrograph_ctf_path):
#             continue
#         else:
#             micrographs_to_do.append(micrograph)

#     if len(micrographs_to_do) > 0:
#         print(" %s micrographs remain to be CTF estimated" % len(micrographs_to_do))
#     else:
#         print(" All micrographs have been CTF estimated")

#     return micrographs_to_do

def get_all_movies_to_save(save_dir, all_movies):
    """
    PARAMETERS
        save_dir = path-like string of the directoy we intend to save movies into 
        all_movies = list() object containing the paths to all the movies we intend to save 
    """
    movies_to_save = []
    for movie in all_movies:
        ## cast the movie sting as the path we intend to save it as so we can diectly check for a file that exists 
        movie_fname = os.path.split(movie)[1]
        save_path = os.path.join(save_dir, movie_fname)
        ## check if the file exists 
        if os.path.exists(save_path):
            continue 
        else:
            movies_to_save.append(movie)

    if len(movies_to_save) > 0:
        print(" %s movies remain to be saved" % len(movies_to_save))
    else:
        print(" All movies have been saved in directoy (%s/)" % save_dir)

    return movies_to_save 

def save_movie(file, save_path, DRY_RUN = False):
    """
    PARAMETERS 
        file : path-like string of the file to save 
        save_path : path-like string of the target directory to save the file into with its full name (i.e. /path/to/mrc_001.mrc)
        DRY_RUN : only write out the terminal the steps to be executed without any copying  
    """
    save_dir = os.path.split(save_path)[0]

    ## check the target file exists 
    if not os.path.isfile(file):
        print(" Input movie to save was not found! (%s)" % file)
        return 

    ## check the save directory exists 
    if not os.path.isdir(save_dir):
        print(" Input save directory for movie not found! (%s)" % save_dir)
        return 
        
    ## check the movie is not already saved 
    if os.path.isfile(save_path):
    ## file appears to exist, check if it is the right size
        source_size = os.stat(file).st_size
        dest_size = os.stat(save_path).st_size
        if source_size == dest_size:
        ## the file appears to already exist and is the correct size, we can skip it 
            # print(" Movie is already saved") 
            return 
    ## if we have not returned, then there is a percieved difference in size, so we should re-copy the file 

    if DRY_RUN:
        print()
        print(" shutil.copy2(%s, %s)" % (file, save_dir))
        print(" shutil.move(%s, %s)" % (os.path.join(save_dir, os.path.split(file)[-1]), save_path ))
    else:
        ## wrap in try statement to allow graceful exiting of program in case it is mid-copying 
        try:
            ## write the target file to the save directory 
            shutil.copy2(file, save_dir)
            ## rename the output file to the desired final name 
            shutil.move(os.path.join(save_dir, os.path.split(file)[-1]), save_path )

        except KeyboardInterrupt:
            ## clean up partial copied file 
            potential_partial_file = os.path.join(save_dir, os.path.split(file)[-1])
            if os.path.isfile(potential_partial_file):
                os.remove(potential_partial_file)

            sys.exit()

    return 

def run_motioncor2(movie, out_micrograph, pixel_size = False, frame_dose = False, kV = False, gain = False, DRY_RUN = False):
    ## sanity check the motion correct micrograph does not already exist 
    if os.path.isfile(out_micrograph):
        mrc_size_bytes = os.stat(out_micrograph).st_size
        mrc_size_mb = mrc_size_bytes / (1024*1024)
        
        ## make sure is at least greater than 30 Mb large
        if mrc_size_mb > 30:
            # print(" Motion corrected micrograph already exists (%.1f Mbs)" % (mrc_size_mb))    
            return 

    out_micrograph_DW = False

    ## Prepare the command line executable 
    command = "motioncor2 -InMrc %s -OutMrc %s "  % (movie, out_micrograph)
    if gain != False:
        command += "-Gain %s" % gain
    command += "-Patch 10 10 "
    ## add option to include dose weighting 
    if pixel_size != False and frame_dose != False and kV != False:
        command += "-PixSize %s -FmDose %s -kV %s " % (pixel_size, frame_dose, kV)
        out_micrograph_DW = os.path.splitext(out_micrograph)[0] + "_DW.mrc"
    ## Turn off the output of a restricted dose range sum that falls between an accumulated dose range of (x, y), where `-SumRange x y' is the value, i.e. can try limiting sum between 3 and 35 electron per square angstroms ... 
    x = 0
    y = 0
    command += "-SumRange %s %s " % (x, y)

    ## Set default GPU behavior 
    command += "-Gpu %s " % ('1')

    if DRY_RUN:
        print(" Motion correction commmand: ")
        print("     $", command)
        return 

    try:

        process = Popen(command, shell=True, stdout=PIPE)
        process.wait()
        # print(process.returncode) ## 0 == finished correctly, 1 == error

        ## Clean up the output directory to remove the non-doseweighted image 
        if out_micrograph_DW != False:
            ## to save space, delete the non-doseweighted file 
            if os.path.exists(out_micrograph_DW):
                if os.path.exists(out_micrograph):
                    os.remove(out_micrograph)
                    ## after deleting the old non-doseweighted image, rename the doseweighted one over the original
                    os.rename(out_micrograph_DW, out_micrograph)

        ## update the pixel size in the header of the output file 
        with mrcfile.open(out_micrograph, mode = 'r+') as mrc:
            mrc.voxel_size = pixel_size
            mrc.update_header_from_data()
            mrc.update_header_stats()

    except KeyboardInterrupt:
        ## clean up potential partial file:
        potential_partial_file = out_micrograph
        if os.path.isfile(potential_partial_file):
            os.remove(potential_partial_file)

        sys.exit()
    return

def write_jpg(input_mrc, output_jpg, bin = 4, DRY_RUN = False):
    ## sanity check the jpg does not already exist 
    if os.path.isfile(output_jpg):
        size_bytes = os.stat(output_jpg).st_size
        size_kb = size_bytes / (1024)
        
        ## make sure is at least greater than 30 Mb large
        if size_kb > 50:
            # print(" .JPG already exists (%.1f kbs)" % (size_kb))    
            return 

    command = "mrc2img.py %s %s " % (input_mrc, output_jpg)
    command += "--bin %s" % bin

    if DRY_RUN:
        print(" ", command)
    else:

        try:
            process = Popen(command, shell=True, stdout=PIPE)
            process.wait()
        except KeyboardInterrupt:
            ## clean up partial files 
            if os.path.isfile(output_jpg):
                os.remove(output_jpg)

    return 

def write_gridsquare_jpg(input_movie_path, jpg_dir):
    ## get the GridSquare_##### identity for the movie
    dirs = splitall(input_movie_path) 
    grid_square_str = dirs[-3] # by convention the GridSquare directory is 2 folders behind 
    
    ## rebuild the path to the gridsquare directory 
    grid_square_dir = ''
    for step in dirs:
        if 'GridSquare' in step:
            grid_square_dir = os.path.join(grid_square_dir, step)
            break
        else:
            grid_square_dir = os.path.join(grid_square_dir, step)
    
    ## find all GridSquare*mrc files 
    search_glob = os.path.join(grid_square_dir, 'GridSquare*mrc')
    ## take the first match 
    gridsquare_file = glob.glob(search_glob)[0]
    gridsquare_jpg_path = os.path.join(jpg_dir, grid_square_str + '.jpg')
    
    write_jpg(gridsquare_file, gridsquare_jpg_path)

    return 

def write_atlas_jpg(atlas_dir, jpg_dir):
    ## get all Atlas files in the directory 
    search_glob = os.path.join(atlas_dir, 'Atlas*mrc')
    ## take the match with the highest alpha numeric match 
    atlas_mrc_path = sorted(glob.glob(search_glob))[-1]

    ## determine the output jpg name 
    atlas_jpg_path = os.path.join(jpg_dir, os.path.splitext(os.path.split(atlas_mrc_path)[-1])[0] + ".jpg")
    # print(" atlas found = %s, jpg = %s" % (atlas_mrc_path, atlas_jpg_path)) 

    write_jpg(atlas_mrc_path, atlas_jpg_path, bin = 2)

    return 

def markup_gridsquare_on_atlas_jpg(input_movie_path, atlas_dir, jpg_dir, DRY_RUN = False):
    ## 1. generate the expected gridsquare markedup output and check if it already exists 
    dirs = splitall(input_movie_path) 
    grid_square_str = dirs[-3] # by convention the GridSquare directory is 2 folders behind 
    gridsquare_markup_jpg_path = os.path.join(jpg_dir, grid_square_str + '_Atlas.jpg')

    if os.path.isfile(gridsquare_markup_jpg_path):
        ## gridsquare markup already exists, we can skip remaking it 
        # print(" Gridsquare atlas position is already made ")
        return 

    ## rebuild the path to the gridsquare directory 
    grid_square_dir = ''
    for step in dirs:
        if 'GridSquare' in step:
            grid_square_dir = os.path.join(grid_square_dir, step)
            break
        else:
            grid_square_dir = os.path.join(grid_square_dir, step)
    
    ## 2. find the corresponding .xml file for the gridsquare 
    ## find all GridSquare*xml files 
    search_glob = os.path.join(grid_square_dir, 'GridSquare*xml')
    ## take the first match 
    gridsquare_xml_file = glob.glob(search_glob)[0]

    ## 3. figure out the expected location of the atlas.jpg file that should already exist 
    search_glob = os.path.join(atlas_dir, 'Atlas*mrc')
    atlas_mrc_path = sorted(glob.glob(search_glob))[-1]
    atlas_jpg_path = os.path.join(jpg_dir, os.path.splitext(os.path.split(atlas_mrc_path)[-1])[0] + ".jpg")
    if not os.path.isfile(atlas_jpg_path):
        print(" !! WARNING :: Could not generate a GridSquare location file since no Atlas_<x>.jpg was found")
        return 

    ## run the mark up script with the relevant input information 
    command = "./show_atlas_position.py %s %s %s %s " % (atlas_dir, atlas_jpg_path, gridsquare_xml_file, gridsquare_markup_jpg_path)

    if DRY_RUN:
        print(" ", command)
    else:
        process = Popen(command, shell=True, stdout=PIPE)
        process.wait()

    return 

def run_ctffind(micrograph_path, out_dir, pixel_size, kV, logfile, ctf_dataset):
    if not kV:
        print(" No --kV value supplied, cannot run CTFFIND4...")
        return -1, -1, None

    micrograph_name = os.path.split(micrograph_path)[1]
    ## check there is no entry already for this micrograph in the logfile
    if ctf_dataset.entry_exists(micrograph_name):
        return -1, -1, None

    micrograph_ctf_name = os.path.splitext(micrograph_name)[0] + "_PS.mrc"
    micrograph_ctf_path = os.path.join(out_dir, micrograph_ctf_name)

    input_mrc = str(micrograph_path)
    diagnostic_output_mrc = str(micrograph_ctf_path)
    pixel_size = str(pixel_size)
    kV = str(kV)
    Cs = "2.7"
    amp_contrast = "0.09"
    amplitude_spectrum_size = "700"
    resolution_min = "50"
    resolution_max = "5"
    dZ_min = "5000"
    dZ_max = "50000"
    dZ_search_step = "50"
    astig_known_Q = "no"
    slower_more_exhaustive_Q = "no"
    astig_restraint_Q = "no"
    additional_phase_shift_Q = "no"
    set_expert_options_Q = "yes"
    ## if expert options yes
    resample_Q = "no"
    dZ_known_Q = "no"
    threads = "20"
    #################################

    cmds = [input_mrc, diagnostic_output_mrc, pixel_size, kV, Cs, amp_contrast, amplitude_spectrum_size, resolution_min, resolution_max, dZ_min, dZ_max, dZ_search_step, astig_known_Q, slower_more_exhaustive_Q, astig_restraint_Q, additional_phase_shift_Q, set_expert_options_Q, resample_Q, dZ_known_Q, threads]

    # print(" CTFFIND4 command: ")
    # print( "    ", cmds)

    try:
        ## REF: https://stackoverflow.com/questions/8475290/how-do-i-write-to-a-python-subprocess-stdin
        p = Popen('ctffind', stdin=PIPE, stdout=DEVNULL)
        for x in cmds:
            p.stdin.write(x.encode() + b'\n')

        p.communicate()
        p.wait()

        ## clean up undesired outputs 
        avrot_file_name = os.path.splitext(micrograph_name)[0] + "_PS_avrot.txt"
        avrot_file_path = os.path.join(out_dir, avrot_file_name)
        if os.path.exists(avrot_file_path):
            os.remove(avrot_file_path)

        ## parse the output text tile for dZ_1, dZ_2, ctf_fit
        data_file_name = os.path.splitext(micrograph_name)[0] + "_PS.txt"
        data_file_path = os.path.join(out_dir, data_file_name)
        dZ, ctf_fit = parse_ctffind_datafile(data_file_path)
        # print(" CTFFIND results: ")
        # print("    dZ =", dZ)
        # print("   fit =", ctf_fit)
        ## add this entry to the dataset 
        ctf_dataset.add_entry(micrograph_name, dZ, ctf_fit)
        write_logfile(logfile, ctf_dataset)
        return dZ, ctf_fit, micrograph_name
    
    except KeyboardInterrupt:
        ## clean up any partial files 
        print(" !!! WIP")
        sys.exit()

def parse_ctffind_datafile(fname):
    """
    A crude parser to read the output .txt file from CTFFIND4 output 
    """
    with open(fname, 'r') as f:
        ## load all lines into buffer
        lines = f.readlines()
        ## get the last line
        data = lines[-1].split()

    dZ_1 = float(data[1]) / 10000
    dZ_2 = float(data[2]) / 10000
    dZ_avg = np.round(np.average([dZ_1, dZ_2]), decimals=2)
    ctf_fit = np.round(float(data[-1]), decimals=2)

    return dZ_avg, ctf_fit

def write_logfile(logfile, ctf_dataset):
    ## overwrite any existing logfile by making a fresh file with headers 
    # with open(logfile, 'w') as f:
    #     f.write("mic_name  dZ  ctf_fit \n")
    
    # ## write the new entry to the logfile 
    # with open(logfile, 'a') as f:
    #     if len(ctf_dataset.data) > 0:
    #         for mic in ctf_dataset.data:
    #             dZ = ctf_dataset.get_dZ(mic)
    #             ctf_fit = ctf_dataset.get_ctf_fit(mic)
    #             f.write("%s  %s  %s  \n" % (mic, dZ, ctf_fit))

    ## create an empty file with the target name (erase previous file if present)
    f = open(logfile, 'w+')
    f.write("\n")
    f.write("data_micrographs\n")
    f.write("\n")
    f.write("loop_\n")
    f.write("_MicrographName #1\n")
    f.write("_dZ #2\n")
    f.write("_CtfFit #3\n")
    f.close()

    ## write the entries to the logfile 
    with open(logfile, 'a') as f:
        if len(ctf_dataset.data) > 0:
            for mic in ctf_dataset.data:
                dZ = ctf_dataset.get_dZ(mic)
                ctf_fit = ctf_dataset.get_ctf_fit(mic)
                f.write("%s\t%s\t%s\n" % (mic, dZ, ctf_fit))


    # print(" Written logfile: %s" % logfile )
    return 

def processing_pipeline(movie, i, PARAMS):
    step_string = "  Processing movie #%s :: " % (i + 1)
    print(step_string, end = "")
    print("\r", end="")

    ## 1. Check if we want to save the full movie
    print(" " * len(step_string), end = "")
    print("\r", end="")
    step_string = "  Processing movie #%s :: saving movie" % (i + 1)
    print(step_string, end = "")
    print("\r", end="")
    save_movie(movie, PARAMS.movie_save_string(movie), DRY_RUN = DRY_RUN)

    ## 2. Motion correct the movie to a single .MRC
    print(" " * len(step_string), end = "")
    print("\r", end="")
    step_string = "  Processing movie #%s :: running motion correction" % (i + 1)
    print(step_string, end = "")
    print("\r", end="")
    run_motioncor2(movie, PARAMS.mrc_save_string(movie), pixel_size = PARAMS.angpix, kV = PARAMS.kV, frame_dose = PARAMS.frame_dose, DRY_RUN = DRY_RUN)

    ## 3. Write out a compressed .JPG file for analysis later 
    print(" " * len(step_string), end = "")
    print("\r", end="")
    step_string = "  Processing movie #%s :: writing jpgs" % (i + 1)
    print(step_string, end = "")
    print("\r", end="")
    write_jpg(PARAMS.mrc_save_string(movie), PARAMS.jpg_save_string(movie), DRY_RUN = DRY_RUN)

    ## 4. If not yet, write out a GridSquare image for the corresponding micrograph
    write_gridsquare_jpg(movie, PARAMS.jpg_dir)

    ## 5. If atlas directory was provided, write out the main atlas of the grid
    if PARAMS.atlas_dir != False:
        write_atlas_jpg(PARAMS.atlas_dir, PARAMS.jpg_dir)

    ## 6. If atlas directory was provided, write out the marked location of the GridSquare on the atlas 
    if PARAMS.atlas_dir != False:
        markup_gridsquare_on_atlas_jpg(movie, PARAMS.atlas_dir, PARAMS.jpg_dir, DRY_RUN = DRY_RUN)

    ## 7. Calculate CTF estimate of micrograph
    print(" " * len(step_string), end = "")
    print("\r", end="")
    step_string = "  Processing movie #%s :: running CTFFIND4" % (i + 1)
    print(step_string, end = "")
    print("\r", end="")
    dZ, ctf_fit, micrograph_name = run_ctffind(PARAMS.mrc_save_string(movie), PARAMS.ctf_dir, PARAMS.angpix, PARAMS.kV, PARAMS.logfile, CTF_DATA)

    print(" " * len(step_string), end = "")
    print("\r", end="")
    if micrograph_name == None:
        step_string = ""
    else:
        step_string = "  Processing movie #%s :: running CTFFIND4 (dZ = %s, ctf_fit = %s)" % ((i + 1), dZ, ctf_fit)
    print(step_string, end = "")
    print("\r", end="")

    print()


#region STAR handler functions
def get_table_position(file, table_title, DEBUG = True):
    """ Find the line numbers for key elements in a relion .STAR table.
		---------------------------------------------------------------
		PARAMETERS
		---------------------------------------------------------------
			file = str(); name of .STAR file with tables (e.g. "run_it025_model.star")
			table_title = str(); name of the .STAR table we are interested in (e.g. "data_model_classes")
			DEBUG = bool(); optional parameter to display or not return values
		---------------------------------------------------------------
		RETURNS
		---------------------------------------------------------------
			HEADER_START = int(); line number for the first entry after `loop_' in the table
			DATA_START = int(); line number for the first data entry after header
			DATA_END = int(); line number for the last data entry in the table
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
            if line_to_list[0] == "loop_" and TABLE_START > 0:
                HEADER_START = line_num + 1
                continue
            ## if we in the header, check if we have entered the data section by checking when the first character is no longer a `_'
            if HEADER_START > 0 and DATA_START < 0:
                first_character = list(line_to_list[0])[0]
                if first_character != '_':
                    DATA_START = line_num
                    continue
    ## in cases where there is no empty line at the end of the file we need to manually update the DATA_END to match this line value
    if DATA_END == -1:
        DATA_END = line_num
        
    if DEBUG:
        print(" Find line numbers for table '%s' in %s" % (table_title, file))
        print("   >> Table starts at line:  %s" % TABLE_START)
        print("   >> Data range (start, end) = (%s, %s)" % (DATA_START, DATA_END))
        print("-------------------------------------------------------------")
    return HEADER_START, DATA_START, DATA_END

def find_star_column(file, column_name, header_start, header_end, DEBUG = True) :
    """ For an input .STAR file and line number range corresponding to the header, find the assigned column of a desired column by name (e.g. 'rlnMicrographName')
	---------------------------------------------------------------
	PARAMETERS
	---------------------------------------------------------------
		file = str(); name of the star file to parse
		column_name = str(); name of the header column to look for (e.g. '_rlnEstimatedResolution')
		header_start = int(); line number correspondnig to the first entry of the header
		header_end = int(); line number corresponding to the last entry of the header (typically line before start of data)
		DEBUG = bool(); optionally print out steps during run
	---------------------------------------------------------------
	RETURNS
	---------------------------------------------------------------
		column_num = int(); number assigned to the given column (e.g. _rlnCoordinateX #3 -> 3)
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
                    print(" ERROR: Input .STAR file: %s, is missing a column for: %s" % (file, column_name) )
                    sys.exit()
                else:
                    if DEBUG:
                        print("  ... %s column value: #%s" % (column_name, column_num))
                        # print("-------------------------------------------------------------")
                    return column_num

def get_star_data(line, column, DEBUG = False):
    """ For a given .STAR file line entry, extract the data at the given column index.
        If the column does not exist (e.g. for a header line read in), return 'False'
		---------------------------------------------------------------
		PARAMETERS
		---------------------------------------------------------------
			line = str(); line from file containing data columns
			column = int(); index of column from which to find data
			DEBUG = bool(); print on cmd line function process
		---------------------------------------------------------------
		RETURNS
		---------------------------------------------------------------
			column_value = str() or bool(); returns the value in star column index as a string, or False if no column exists
    """
    # break an input line into a list data type for column-by-column indexing
    line_to_list = line.split()
    try:
        column_entry = line_to_list[column-1]
        if DEBUG:
            print("Data in column #%s = %s" % (column, column_entry))
        return column_entry
    except:
        return False

def remove_path(file_w_path):
    """ Parse an input string containing a path and return the file name without the path. Useful for getting micrograph name from 'rlnMicrographName' column.
	---------------------------------------------------------------
	PARAMETERS
	---------------------------------------------------------------
		file_w_path = str()
	---------------------------------------------------------------
	RETURNS
	---------------------------------------------------------------
		file_wo_path = str() (e.g. /path/to/file -> 'file')
    """
    globals()['os'] = __import__('os')
    file_wo_path = os.path.basename(file_w_path)
    return file_wo_path
#endregion


#endregion
#############################

#############################
#region     RUN BLOCK
#############################

if __name__ == "__main__":
    import os, sys, time, glob, shutil
    from subprocess import Popen, PIPE, DEVNULL
    import numpy as np
    import mrcfile 

    print(h_bar)
    print("    EPU ON-THE-FLY PROCESSING")


    PARAMS = PARAMETERS(sys.argv)
    PARAMS.prepare_directories()
    CTF_DATA = DATASET()

    ## discover all movies in the EPU session 
    movies_discovered = get_all_movies(PARAMS.epu_dir, PARAMS.movie_glob)

    ## parse any existing log file in the working directory 
    CTF_DATA.parse_logfile(PARAMS.logfile)

    ## for each movie, determine the desired outputs 
    print(h_bar)
    print("  Processing :: ", end = "")
    print("\r", end="")
    # print(h_sub_bar)
    for i in range(len(movies_discovered)):
        movie = movies_discovered[i]
        processing_pipeline(movie, i, PARAMS)
        # step_string = "  Processing movie #%s :: " % (i + 1)
        # print(step_string, end = "")
        # print("\r", end="")

        # ## 1. Check if we want to save the full movie
        # print(" " * len(step_string), end = "")
        # print("\r", end="")
        # step_string = "  Processing movie #%s :: saving movie" % (i + 1)
        # print(step_string, end = "")
        # print("\r", end="")
        # save_movie(movie, PARAMS.movie_save_string(movie), DRY_RUN = DRY_RUN)

        # ## 2. Motion correct the movie to a single .MRC
        # print(" " * len(step_string), end = "")
        # print("\r", end="")
        # step_string = "  Processing movie #%s :: running motion correction" % (i + 1)
        # print(step_string, end = "")
        # print("\r", end="")
        # run_motioncor2(movie, PARAMS.mrc_save_string(movie), pixel_size = PARAMS.angpix, kV = PARAMS.kV, frame_dose = PARAMS.frame_dose, DRY_RUN = DRY_RUN)

        # ## 3. Write out a compressed .JPG file for analysis later 
        # print(" " * len(step_string), end = "")
        # print("\r", end="")
        # step_string = "  Processing movie #%s :: writing jpgs" % (i + 1)
        # print(step_string, end = "")
        # print("\r", end="")
        # write_jpg(PARAMS.mrc_save_string(movie), PARAMS.jpg_save_string(movie), DRY_RUN = DRY_RUN)

        # ## 4. If not yet, write out a GridSquare image for the corresponding micrograph
        # write_gridsquare_jpg(movie, PARAMS.jpg_dir)

        # ## 5. If atlas directory was provided, write out the main atlas of the grid
        # if PARAMS.atlas_dir != False:
        #     write_atlas_jpg(PARAMS.atlas_dir, PARAMS.jpg_dir)

        # ## 6. If atlas directory was provided, write out the marked location of the GridSquare on the atlas 
        # if PARAMS.atlas_dir != False:
        #     markup_gridsquare_on_atlas_jpg(movie, PARAMS.atlas_dir, PARAMS.jpg_dir, DRY_RUN = DRY_RUN)

        # ## 7. Calculate CTF estimate of micrograph
        # print(" " * len(step_string), end = "")
        # print("\r", end="")
        # step_string = "  Processing movie #%s :: running CTFFIND4" % (i + 1)
        # print(step_string, end = "")
        # print("\r", end="")
        # dZ, ctf_fit, micrograph_name = run_ctffind(PARAMS.mrc_save_string(movie), PARAMS.ctf_dir, PARAMS.angpix, PARAMS.kV, PARAMS.logfile, CTF_DATA)

        # print(" " * len(step_string), end = "")
        # print("\r", end="")
        # step_string = "  Processing movie #%s :: running CTFFIND4 (dZ = %s, ctf_fit = %s)" % ((i + 1), dZ, ctf_fit)
        # print(step_string, end = "")
        # print("\r", end="")

        # print()

    print(h_bar)


    # angpix, movie_glob, epu_dir, atlas_dir, jpg_dir, mrc_dir, ctf_dir, save_movies, movie_dir, seconds_delay, kV, frame_dose, logfile = parse_cmdline(sys.argv)

    # ## if saving movies, start by saving them to the target directory  
    # if save_movies:
    #     ## find the movies that do not have a corresponding file in the save directory 
    #     movies_to_save = get_all_movies_to_save(movie_dir, movies_discovered)
    #     ## save the movies not present in the save directory 
    #     for i in range(len(movies_to_save)):
    #         print(" ... saving movie #%s: %s -> %s/" % (i + 1, movies_to_save[i], movie_dir), end='\r')

    #         save_movie(movies_to_save[i], movie_dir)

    #     ## report the number of movies saved on completion 
    #     print(" ")
    #     print(" %s movies were saved in %s/" % (len(movies_to_save), movie_dir))

    # ## get all motion corrected micrographs
    # micrographs_corrected = get_all_micrographs_corrected(mrc_dir, movie_glob)

    # ## find which movies have not been corrected yet 
    # movies_not_yet_corrected = get_all_movies_not_yet_corrected(movies_discovered, micrographs_corrected)

    # ## iterate across all movies to be corrected 
    # for i in range(len(movies_not_yet_corrected)):
    #     print(" ")
    #     print(" ... motion correcting movie #%s: %s -> %s/" % (i + 1, movies_not_yet_corrected[i], mrc_dir), end='\r')
    #     corrected_micrograph = run_motioncor2(movies_not_yet_corrected[i], mrc_dir, pixel_size = angpix, kV = kV, frame_dose = frame_dose)
    #     write_jpg(corrected_micrograph, jpg_dir)

    #     ## while motion correcting, run the CTF estimation step immediately after so we can some quick feedback on quality during the run 
    #     print(" ... CTF estimating micrograph #%s: %s -> %s/" % (i + 1, corrected_micrograph, ctf_dir), end='\r')
    #     dZ, ctf_fit, mic_name = run_ctffind(corrected_micrograph, ctf_dir, angpix, kV)
    #     write_logfile(logfile, i, dZ, ctf_fit, mic_name)


    # ## find which micrographs (prior to the initial correction step) have not had CTF estimates calculated 
    # micrographs_ctf = micrographs_not_yet_CTF_estimated(ctf_dir, micrographs_corrected)

    # ## iterate across all micrographs to be CTF estimated
    # for i in range(len(micrographs_ctf)): 
    #     # print(" ... CTF estimating micrograph #%s: %s -> %s/" % (i + 1, micrographs_ctf[i], ctf_dir), end='\r')
    #     dZ, ctf_fit, mic_name = run_ctffind(micrographs_ctf[i], ctf_dir, angpix, kV)
    #     write_logfile(logfile, dZ, ctf_fit, mic_name)

    print(" ")

    ## run infinite loop after initial pass 
    while True:
        try:
            # start_time = time.time()
            # end_time = time.time()
            # total_time_taken = end_time - start_time
            # print(" ... copy runtime = %.2f sec" % total_time_taken)

            ## discover all movies in the EPU session 
            movies_discovered = get_all_movies(PARAMS.epu_dir, PARAMS.movie_glob)

            for i in range(len(movies_discovered)):
                movie = movies_discovered[i]
                processing_pipeline(movie, i, PARAMS)


            ## Add a live timer to display to the user the sleeping state is actively running 
            for i in range(PARAMS.seconds_delay,0,-1):
                print(f" ... next check in: {i} seconds", end="\r", flush=True)
                time.sleep(1)

        except KeyboardInterrupt:
            print(" Terminating ...")

            sys.exit()

#endregion
#############################
