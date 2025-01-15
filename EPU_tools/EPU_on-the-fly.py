#!/usr/bin/env python3

## Author : A. Keszei 

## 2024-07-25: Initial script started
## 2024-10-11: The logfile needs to be re-written every time the program restarts... it should find the micrographs, then check for the corresponding text file in the ctf directory and corresponding jpg and fix all mismatches. Then it should re-build the logfile.   
## 2025-01-15: Focus on correct parsing of working directory to allow easy user determination of what squares micrograhs are coming from after-the-fact 

#############################
#region     GLOBAL FLAGS
#############################
DEBUG = True
DRY_RUN = True

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
        self.logfile = "otf.log"
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

        if DEBUG:
            print("====================================")
            print(" parse_cmdline :: %s" % cmdline)
            print("------------------------------------")
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
            print("====================================")

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

    print(" %s movies found in EPU directory (%s)" % (len(movies), EPU_dir))
    if len(movies) > 1:
        print("    %s" % movies[0])
        print("    ...")

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

def get_all_micrographs_corrected(mrc_dir, movie_glob):
    micrographs = []

    for match in glob.glob(os.path.join(mrc_dir, movie_glob)):
        micrographs.append(match)

    print(" %s micrographs found in save directory (%s/)" % (len(micrographs), mrc_dir))
    return micrographs

def get_all_movies_not_yet_corrected(movies, micrographs): 
    ## recast the movies and micrographs to a common basename for direct comparison using sets        
    movies_basenames = []
    for movie in movies:
        movies_basenames.append(os.path.splitext(os.path.split(movie)[1])[0])

    micrographs_basenames = []
    for micrograph in micrographs:
        micrographs_basenames.append(os.path.splitext(os.path.split(micrograph)[1])[0])

    unique = list(set(movies_basenames).difference(micrographs_basenames))

    if len(unique) > 0:
        print(" %s movies remain to be corrected" % len(unique))
    else:
        print(" All movies in the EPU directory have been corrected")

    ## use the output unique set to return a truncated list of the movies we need to correct that still contains their path information 
    movies_to_correct = []
    for movie in movies:
        movie_basename = os.path.splitext(os.path.split(movie)[1])[0]
        if movie_basename in unique:
            movies_to_correct.append(movie)
        else:
            continue 

    return movies_to_correct

def micrographs_not_yet_CTF_estimated(ctf_dir, micrographs):
    micrographs_to_do = []

    if len(micrographs) == 0:
        print(" No micrographs are available for CTF correction yet.")
        return micrographs_to_do

    for micrograph in micrographs:
        micrograph_ctf_name = os.path.splitext(os.path.split(micrograph)[1])[0] + "_PS.mrc"
        micrograph_ctf_path = os.path.join(ctf_dir, micrograph_ctf_name)
        if os.path.exists(micrograph_ctf_path):
            continue
        else:
            micrographs_to_do.append(micrograph)

    if len(micrographs_to_do) > 0:
        print(" %s micrographs remain to be CTF estimated" % len(micrographs_to_do))
    else:
        print(" All micrographs have been CTF estimated")

    return micrographs_to_do

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

    if DRY_RUN:
        print(" shutil.copy2(%s, %s)" % (file, save_dir))
        print(" shutil.move(%s, %s)" % (os.path.join(save_dir, os.path.split(file)[-1]), save_path ))
    else:
        ## write the target file to the save directory 
        shutil.copy2(file, save_dir)
        ## rename the output file to the desired final name 
        shutil.move(os.path.join(save_dir, os.path.split(file)[-1]), save_path )
    return 



def run_motioncor2(movie, out_dir, pixel_size = False, frame_dose = False, kV = False, gain = False):
    ## generate a suitable output path for the motion correct movie 
    out_micrograph = os.path.join(out_dir, os.path.split(movie)[1])
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



    # print(" MotionCor2 command: ")
    # print( "    ", command)

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

    return out_micrograph

def write_jpg(mrc, dest):
    out_fname = os.path.splitext(os.path.split(mrc)[1])[0] + ".jpg"
    out_fname_w_path = os.path.join(dest, out_fname)
    command = "mrc2img.py %s %s " % (mrc, out_fname_w_path)
    command += "--bin"

    process = Popen(command, shell=True, stdout=PIPE)
    process.wait()
    return 

def run_ctffind(micrograph_path, out_dir, pixel_size, kV):
    if not kV:
        print(" No --kV value supplied, cannot run CTFFIND4...")
        return 

    micrograph_name = os.path.split(micrograph_path)[1]
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
    ## write the resulting data to a logfile 
    
    return dZ, ctf_fit, micrograph_name

def parse_ctffind_datafile(fname):
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

def write_logfile(logfile, index, dZ, ctf_fit, mic):
    ## check if logfile already exists, in which case add to it
    if not os.path.exists(logfile):
        ## create the logfile header (use a csv structure easily parsed by Pandas into a DataFrame object)
        with open(logfile, 'w') as f:
            f.write("index  mic_name  dZ  ctf_fit \n")
    
    ## write the new entry to the logfile 
    with open(logfile, 'a') as f:
        f.write("%s  %s  %s  %s \n" % (index, mic, dZ, ctf_fit))

    return 

#endregion
#############################

#############################
#region     RUN BLOCK
#############################

if __name__ == "__main__":
    import os, sys, time, glob, shutil
    from subprocess import Popen, PIPE, DEVNULL
    import numpy as np

    PARAMS = PARAMETERS(sys.argv)
    PARAMS.prepare_directories()

    ## discover all movies in the EPU session 
    movies_discovered = get_all_movies(PARAMS.epu_dir, PARAMS.movie_glob)

    ## for each movie, determine the desired outputs 
    for movie in movies_discovered:
        print(" ===============================================")
        print("    ", movie)
        print(" -----------------------------------------------")
        ## 1. Check if we want to save the full movie
        save_movie(movie, PARAMS.movie_save_string(movie), DRY_RUN = DRY_RUN)

        exit()
        ## 2. Motion correct the movie to a single .MRC
        print(PARAMS.mrc_save_string(movie))

        ## 3. Write out a compressed .JPG file for analysis later 
        print(PARAMS.jpg_save_string(movie))

        ## 4. If not yet, write out a GridSquare image for the corresponding micrograph


        ## 5. If atlase directory was provided, write out the main atlas of the grid


        ## 6. If atlas directory was provided, write out the marked location of the GridSquare on the atlas 


        print(" ===============================================")

    exit()

    angpix, movie_glob, epu_dir, atlas_dir, jpg_dir, mrc_dir, ctf_dir, save_movies, movie_dir, seconds_delay, kV, frame_dose, logfile = parse_cmdline(sys.argv)

    ## if saving movies, start by saving them to the target directory  
    if save_movies:
        ## find the movies that do not have a corresponding file in the save directory 
        movies_to_save = get_all_movies_to_save(movie_dir, movies_discovered)
        ## save the movies not present in the save directory 
        for i in range(len(movies_to_save)):
            print(" ... saving movie #%s: %s -> %s/" % (i + 1, movies_to_save[i], movie_dir), end='\r')

            save_movie(movies_to_save[i], movie_dir)

        ## report the number of movies saved on completion 
        print(" ")
        print(" %s movies were saved in %s/" % (len(movies_to_save), movie_dir))

    ## get all motion corrected micrographs
    micrographs_corrected = get_all_micrographs_corrected(mrc_dir, movie_glob)

    ## find which movies have not been corrected yet 
    movies_not_yet_corrected = get_all_movies_not_yet_corrected(movies_discovered, micrographs_corrected)

    ## iterate across all movies to be corrected 
    for i in range(len(movies_not_yet_corrected)):
        print(" ")
        print(" ... motion correcting movie #%s: %s -> %s/" % (i + 1, movies_not_yet_corrected[i], mrc_dir), end='\r')
        corrected_micrograph = run_motioncor2(movies_not_yet_corrected[i], mrc_dir, pixel_size = angpix, kV = kV, frame_dose = frame_dose)
        write_jpg(corrected_micrograph, jpg_dir)

        ## while motion correcting, run the CTF estimation step immediately after so we can some quick feedback on quality during the run 
        print(" ... CTF estimating micrograph #%s: %s -> %s/" % (i + 1, corrected_micrograph, ctf_dir), end='\r')
        dZ, ctf_fit, mic_name = run_ctffind(corrected_micrograph, ctf_dir, angpix, kV)
        write_logfile(logfile, i, dZ, ctf_fit, mic_name)


    ## find which micrographs (prior to the initial correction step) have not had CTF estimates calculated 
    micrographs_ctf = micrographs_not_yet_CTF_estimated(ctf_dir, micrographs_corrected)

    ## iterate across all micrographs to be CTF estimated
    for i in range(len(micrographs_ctf)): 
        # print(" ... CTF estimating micrograph #%s: %s -> %s/" % (i + 1, micrographs_ctf[i], ctf_dir), end='\r')
        dZ, ctf_fit, mic_name = run_ctffind(micrographs_ctf[i], ctf_dir, angpix, kV)
        write_logfile(logfile, dZ, ctf_fit, mic_name)

    print(" ")

    ## run infinite loop 
    while True:
        try:
            # start_time = time.time()
            # end_time = time.time()
            # total_time_taken = end_time - start_time
            # print(" ... copy runtime = %.2f sec" % total_time_taken)

            ## Add a live timer to display to the user the sleeping state is actively running 
            for i in range(seconds_delay,0,-1):
                print(f" ... next check in: {i} seconds", end="\r", flush=True)
                time.sleep(1)

        except KeyboardInterrupt:
            print(" Terminating ...")

            sys.exit()

#endregion
#############################
