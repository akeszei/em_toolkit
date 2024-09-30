#!/usr/bin/env python3

## Author : A. Keszei 

"""
    A simple script to make easy-to-use outputs for curating a dataset on-the-fly 
"""

## 2024-07-25: Initial script started  

#############################
#region     FLAGS
#############################
DEBUG = True

#endregion

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


def parse_cmdline(cmdline):

    ## read all entries and check if the help flag is called at any point
    for cmd in cmdline:
        if cmd == '-h' or cmd == '--help' or cmd == '--h':
            usage()

    ## set defaults 
    angpix = False
    movie_glob = "*Fractions.mrc"
    jpg_dir = "jpg"
    mrc_dir = "micrographs"
    ctf_dir = "ctf"
    save_movies = False
    movie_dir = "movies"
    seconds_delay = 5
    kV = False
    frame_dose = False 
    logfile = "otf.log"

    ## parse any flags 
    for i in range(len(cmdline)):
        if cmdline[i] == '--save_movies':
            save_movies = True
        if cmdline[i] == '--angpix':
            try:
                angpix = float(cmdline[i+1])
            except:
                print(" Could not parse --angpix entry or none given, will read directly from movie")
        if cmdline[i] == '--kV' or cmdline[i] == '--kv':
            try:
                kV = float(cmdline[i+1])
            except:
                print(" Could not parse --kV entry or none given")
        if cmdline[i] == '--frame_dose':
            try:
                frame_dose = float(cmdline[i+1])
            except:
                print(" Could not parse --frame_dose entry or none given")

        if "*" in cmdline[i]:
            movie_glob = cmdline[i]

    ## check for corresponding directories for EPU session and potential atlas directory 
    atlas_dir = False    
    epu_dir = False

    for i in range(len(cmdline)):
        ## ignore the first entry on the cmdline (the calling of the script itself)
        if i == 0:
            continue 

        if '/' in cmdline[i] or '\\' in cmdline[i]:
            if epu_dir == False:
                if check_if_EPU_directory(cmdline[i]):
                    epu_dir = cmdline[i]
                    continue 
            
            if atlas_dir == False:
                if check_if_atlas_directory(cmdline[i]):
                    atlas_dir = cmdline[i]
                    continue 
            
            print(" WARNING :: Could not parse input directory:", cmdline[i])
            
    if epu_dir == False:
        print(" ERROR :: No EPU directory was detected as input (i.e. lacking EpuSession.dm file and/or Images-Disc1 directory!")
        usage()

    if DEBUG:
        print("====================================")
        print(" parse_cmdline :: %s" % cmdline)
        print("------------------------------------")
        print("   EPU directory = %s" % epu_dir)
        print("   Movie glob string = %s" % movie_glob)
        if atlas_dir != False:
            print("   Atlas directory = %s" % atlas_dir)

        print("   Pixel size = %s" % angpix)
        if kV != False:
            print("   kV = %s" % kV)
        if frame_dose != False:
            print("   frame dose = %s e/A**2/frame" % frame_dose)
        if save_movies != False:
            print("   Save movies = %s " % save_movies)
        print("====================================")


    return angpix, movie_glob, epu_dir, atlas_dir, jpg_dir, mrc_dir, ctf_dir, save_movies, movie_dir, seconds_delay, kV, frame_dose, logfile

def check_if_atlas_directory(dir = "./"):
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

def check_if_EPU_directory(dir = "./"):

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

def prepare_directories(jpg_dir, mrc_dir, ctf_dir, save_movies, movie_dir):

    ## prepare the directory list
    dirs = [jpg_dir, mrc_dir, ctf_dir]
    if save_movies:
        dirs = dirs + [movie_dir]

    ## make any directories that do not already exist 
    for dir in dirs:
        if not os.path.exists(dir):
            print(" create dir :: %s" % (dir))
            os.makedirs(dir, exist_ok=True)
        else:
            continue 

    return

def get_all_movies(EPU_dir, movie_glob):
    """
    PARAMETERS 
        EPU_dir = path-like str() pointing to the main EPU Session directory
        movie_glob = glob-like str(), i.e. containing *, that uniquely identifies a movie in the EPU session 
    RETURNS 
        movies = list() object containing all the movies found in the EPU session 
    """
    movies = list()

    ## prepare the EPU dir with infinite recursion string appended
    search_dir = os.path.join(EPU_dir, "**/Data/**")
    search_glob = os.path.join(search_dir, movie_glob)
    print(" Glob string to find movies: %s" % search_dir)
    for match in glob.glob(search_glob, recursive = True):
        movies.append(match)

    print(" %s movies found in EPU directory (%s)" % (len(movies), EPU_dir))
    if len(movies) > 1:
        print("    %s" % movies[0])
        print("    ...")

    return movies

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

def save_movie(file, save_dir):
    """
    PARAMETERS 
        file : path-like string of the file to save 
        save_dir : path-like string of the target directory to save the file into 
    """
    ## check the target file exists 
    if not os.path.isfile(file):
        print(" Input movie to save was not found! (%s)" % file)
        return 

    ## check the save directory exists 
    if not os.path.isdir(save_dir):
        print(" Input save director for movie not found! (%s)" % save_dir)
        return 

    ## write the target file to the save directory 
    shutil.copy2(file, save_dir)
    return 

def run_motioncor2(movie, out_dir, pixel_size = False, frame_dose = False, kV = False, gain = False):
    ## generate a suitable output path for the motion correct movie 
    out_micrograph = os.path.join(out_dir, os.path.split(movie)[1])

    ## Prepare the command line executable 
    command = "motioncor2 -InMrc %s -OutMrc %s "  % (movie, out_micrograph)
    if gain != False:
        command += "-Gain %s" % gain
    command += "-Patch 10 10 "
    if pixel_size != False and frame_dose != False and kV != False:
        command += "-PixSize %s -FmDose %s -kV %s " % (pixel_size, frame_dose, kV)
    command += "-Gpu %s " % ('1')



    # print(" MotionCor2 command: ")
    # print( "    ", command)

    process = Popen(command, shell=True, stdout=PIPE)
    process.wait()
    # print(process.returncode) ## 0 == finished correctly, 1 == error

    return out_micrograph

def run_ctffind(micrograph, out_dir, pixel_size, kV):
    if not kV:
        print(" No --kV value supplied, cannot run CTFFIND4...")
        return 

    micrograph_ctf_name = os.path.splitext(os.path.split(micrograph)[1])[0] + "_PS.mrc"
    micrograph_ctf_path = os.path.join(out_dir, micrograph_ctf_name)

    input_mrc = str(micrograph)
    diagnostic_output_mrc = str(micrograph_ctf_path)
    pixel_size = str(pixel_size)
    kV = str(kV)
    Cs = "2.7"
    amp_contrast = "0.1"
    amplitude_spectrum_size = "512"
    resolution_min = "50"
    resolution_max = "5"
    dZ_min = "5000"
    dZ_max = "50000"
    dZ_search_step = "100"
    astig_known_Q = "no"
    slower_more_exhaustive_Q = "no"
    astig_restraint_Q = "no"
    additional_phase_shift_Q = "no"
    set_expert_options_Q = "no"

    cmds = [input_mrc, diagnostic_output_mrc, pixel_size, kV, Cs, amp_contrast, amplitude_spectrum_size, resolution_min, resolution_max, dZ_min, dZ_max, dZ_search_step, astig_known_Q, slower_more_exhaustive_Q, astig_restraint_Q, additional_phase_shift_Q, set_expert_options_Q]

    # print(" CTFFIND4 command: ")
    # print( "    ", cmds)


    ## REF: https://stackoverflow.com/questions/8475290/how-do-i-write-to-a-python-subprocess-stdin
    p = Popen('ctffind', stdin=PIPE, stdout=DEVNULL)
    for x in cmds:
        p.stdin.write(x.encode() + b'\n')

    p.communicate()
    p.wait()

    ## clean up undesired outputs 
    avrot_file_name = os.path.splitext(os.path.split(micrograph)[1])[0] + "_PS_avrot.txt"
    avrot_file_path = os.path.join(out_dir, avrot_file_name)
    if os.path.exists(avrot_file_path):
        os.remove(avrot_file_path)

    ## parse the output text tile for dZ_1, dZ_2, ctf_fit
    data_file_name = os.path.splitext(os.path.split(micrograph)[1])[0] + "_PS.txt"
    data_file_path = os.path.join(out_dir, data_file_name)
    dZ, ctf_fit = parse_ctffind_datafile(data_file_path)
    ## write the resulting data to a logfile 
    
    return dZ, ctf_fit, os.path.split(micrograph)[1]

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

def write_logfile(logfile, dZ, ctf_fit, mic):
    ## check if logfile already exists, in which case add to it
    if not os.path.exists(logfile):
        ## create the logfile 
        with open(logfile, 'w') as f:
            f.write("## mic_name  dZ  ctf_fit \n")
    
    ## write the new entry to the logfile 
    with open(logfile, 'a') as f:
        f.write("%s  %s  %s \n" % (mic, dZ, ctf_fit))

    return 

#############################
#region     RUN BLOCK
#############################

if __name__ == "__main__":
    import os, sys, time, glob, shutil
    from subprocess import Popen, PIPE, DEVNULL
    import numpy as np

    angpix, movie_glob, epu_dir, atlas_dir, jpg_dir, mrc_dir, ctf_dir, save_movies, movie_dir, seconds_delay, kV, frame_dose, logfile = parse_cmdline(sys.argv)

    ## make any directories needed
    prepare_directories(jpg_dir, mrc_dir, ctf_dir, save_movies, movie_dir)

    ## get all movies in the EPU session 
    movies_discovered = get_all_movies(epu_dir, movie_glob)

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

        ## while motion correcting, run the CTF estimation step immediately after so we can some quick feedback on quality during the run 
        print(" ... CTF estimating micrograph #%s: %s -> %s/" % (i + 1, corrected_micrograph, ctf_dir), end='\r')
        dZ, ctf_fit, mic_name = run_ctffind(corrected_micrograph, ctf_dir, angpix, kV)
        write_logfile(logfile, dZ, ctf_fit, mic_name)


    ## find which micrographs (prior to the initial correction step) have not had CTF estimates calculated 
    micrographs_ctf = micrographs_not_yet_CTF_estimated(ctf_dir, micrographs_corrected)

    ## iterate across all micrographs to be CTF estimated
    for i in range(len(micrographs_ctf)): 
        print(" ... CTF estimating micrograph #%s: %s -> %s/" % (i + 1, micrographs_ctf[i], ctf_dir), end='\r')
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