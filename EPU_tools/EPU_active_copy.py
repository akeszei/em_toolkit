#!/usr/bin/env python3

"""
    A simple copy script to loop infinitely while collecting data from an EPU session and 
    transfer files to an attached harddisk.  
"""

## 2024-05-06 A.Keszei: Start script 
## To do
## - Add details to output of both dry run and final run? 

#############################
#region :: FLAGS
#############################
DEBUG = True
#endregion

#############################
#region :: DEFINITION BLOCK
#############################
def usage():
    print("===================================================================================================")
    print(" Usage:")
    print("    $ EPU_active_copy.py  /path/to/EPU  /target/dir")
    print(" Will actively mirror the EPU directory in the target directory, e.g.: /target/dir/EPU, every")
    print(" 5 minutes (unless changed). Kill the script with Ctrl + C")
    print(" -----------------------------------------------------------------------------------------------")
    print(" Options (default in brackets): ")
    # print("           --j (2) : Attempt multiprocessing over given cores (remember speed is limited by HDD!)")
    # print("  --movies (*Fractions.mrc) : Copy only movies (using the glob pattern) into a single dir,")
    # print("                              if possible, also copy .JPGs for manual curation later")
    print("                  --dry-run : Give an example of what the copy command will do without copying")
    print("                    --n (300): Delay time in seconds between copy loops; -1 or 0 == dont loop")
    print("===================================================================================================")
    sys.exit()

def get_dirs(cmdline):
    ## expect source directory to be at $1
    source = cmdline[1] 
    ## sanity check folder exists 
    if not os.path.isdir(source):
        print(" ERROR :: Could not find source directory: %s" % source)
        usage()

    ## make sure it has a leading slash for consistentcy 
    if not source[-1] in ['/', '\\' ]:
        source = source + '/'

    ## expect dest directory to be at $2
    dest = cmdline[2]
    ## sanity check folder exists 
    if not os.path.isdir(dest):
        print(" ERROR :: Could not find destination directory: %s" % dest)
        usage()

    ## make sure it has a leading slash for consistentcy 
    if not dest[-1] in ['/', '\\' ]:
        dest = dest + '/'
    
    if DEBUG:
        print(" Copy directories:")
        print("   source = ", source)
        print("     dest =", dest)
    return source, dest

def copytree(src, dst, symlinks = False, ignore = None, DRY_RUN = False):
    """ Not used. 
        A reference function from: https://stackoverflow.com/questions/1868714/how-do-i-copy-an-entire-directory-of-files-into-an-existing-directory-using-pyth
    """
    # print(" copy tree :: %s -> %s" % (src,dst))
    if not os.path.exists(dst):
        os.makedirs(dst)
        shutil.copystat(src, dst)
    lst = os.listdir(src)
    if ignore:
        excl = ignore(src, lst)
        lst = [x for x in lst if x not in excl]
    for item in lst:
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if symlinks and os.path.islink(s):
            if os.path.lexists(d):
                os.remove(d)
                os.symlink(os.readlink(s), d)
            try:
                st = os.lstat(s)
                mode = stat.S_IMODE(st.st_mode)
                os.lchmod(d, mode)
            except:
                pass # lchmod not available
        elif os.path.isdir(s):
            if DRY_RUN:
                print(" create dir :: %s -> %s" % (s, d))
            else:
                copytree(s, d, symlinks, ignore)
        else:
            if DRY_RUN:
                print(" copy :: %s -> %s" % (s, d))
            else:
                shutil.copy2(s, d)

def copy_project(source, dest, glob_string = '**', DEBUG = False):
    ## get the name of the root folder we want to copy 
    root_dir_name = os.path.basename(os.path.normpath(source))
    total_files = 0
    skipped_files = 0
    movies_skipped = 0
    total_movies = 0 
    movie_string = "Fractions.mrc"

    for source_file in glob.glob(os.path.join(source, glob_string), recursive = True):
        if DEBUG: print(" 1. Discovered file at source :: ", source_file)
        IS_MOVIE = False
        initial_time = time.time()
        source_file_basename = source_file[len(source):]
        dest_file = os.path.join(dest, os.path.join(root_dir_name, source_file_basename))

        ## treat files and directories differently 
        if os.path.isdir(source_file):
            if not os.path.exists(dest_file):
                if DRY_RUN:
                    print(" create dir :: %s" % (dest_file))
                else:
                    print(" create dir :: %s" % (dest_file))
                    os.makedirs(dest_file, exist_ok=True)
            else:
                continue 

        if os.path.isfile(source_file):
            ## reject symlinks 
            if(os.path.islink(source_file)):
                print(" Symlink skipped (%s)" % source_file)
                continue 

            total_files += 1

            ## treat movies separately from regular files to avoid sluggish filecmp.cmp check for large file 
            if len(source_file_basename) > len(movie_string):
                if source_file_basename[-len(movie_string):] == movie_string:
                    IS_MOVIE = True
                    total_movies += 1

            if not os.path.exists(dest_file):
                dest_path = os.path.dirname(dest_file)
                if DRY_RUN:
                    print(" copy :: %s -> %s" % (source_file, dest_path))
                else:
                    print(" copy :: %s -> %s" % (source_file, dest_path), end='\r')
                    shutil.copy2(source_file, dest_path)
                    total_time_taken = time.time() - initial_time
                    print(" copy :: %s -> %s (%.2f sec)" % (source_file, dest_path, total_time_taken))
            
            else:
                ## treat movies separately from regular files to avoid sluggish filecmp.cmp check for large file 
                if IS_MOVIE:
                    ## only compare file size for movies, not time/changes 
                    source_size = os.stat(source_file).st_size
                    dest_size = os.stat(dest_file).st_size
                    if not source_size == dest_size:
                        dest_path = os.path.dirname(dest_file)
                        if DRY_RUN:
                            print(" .. file exists but appears different, copy :: %s -> %s" % (source_file, dest_path))
                        else:
                            print(" .. file exists but appears different, copy :: %s -> %s " % (source_file, dest_path), end='\r')
                            shutil.copy2(source_file, dest_path)
                            total_time_taken = time.time() - initial_time
                            print(" .. file exists but appears different, copy :: %s -> %s (%.2f sec)" % (source_file, dest_path, total_time_taken))
                    ## if movie exists and is the same size, skip it 
                    else:
                        skipped_files += 1
                        movies_skipped += 1
                        if DEBUG: print(" ... file exists already: %s" % dest_file)
                        continue 


                ## for all non-movies, do a regular (slower) shallow check 
                elif not filecmp.cmp(source_file, dest_file, shallow=True):
                    if DEBUG: print(" 2. Comparison of file from source and dest complete ::")
                    dest_path = os.path.dirname(dest_file)
                    if DRY_RUN:
                        print(" .. file exists but appears different, copy :: %s -> %s" % (source_file, dest_path))
                    else:
                        print(" .. file exists but appears different, copy :: %s -> %s " % (source_file, dest_path), end='\r')
                        shutil.copy2(source_file, dest_path)
                        total_time_taken = time.time() - initial_time
                        print(" .. file exists but appears different, copy :: %s -> %s (%.2f sec)" % (source_file, dest_path, total_time_taken))
                else:
                    skipped_files += 1
                    if DEBUG: print(" ... file exists already: %s" % dest_file)
                    continue 

    print_stats(total_files, movie_string, total_movies, skipped_files, movies_skipped, DRY_RUN)
    return 

def print_stats(num_files, movie_string, num_movies, num_skipped, num_movies_skipped, DRY_RUN = False):
    print(" ==============================================")
    print("       COPY LOOP COMPLETE:")
    if DRY_RUN: print("            (DRY RUN)")
    print(" ----------------------------------------------")
    print("  ...  %s files found" % num_files)
    print("  ...  %s movies found (...%s)" % (num_movies, movie_string))
    print("  ...  %s files (%s movies) skipped this loop (already present at dest)" % (num_skipped, num_movies_skipped))
    print(" ==============================================")

    return 

def copy_movies(source, dest, glob_string):
    ## get the name of the root folder we want to copy 
    root_dir_name = os.path.basename(os.path.normpath(source))

    ## add the leading **/ to the glob string to match expected behavior to bash globbing 
    glob_string = os.path.join(os.path.join(os.path.normpath(source),'**/'), glob_string)

    ## prepare the output directories if they dont exist
    movies_dir = os.path.join(dest, 'movies')
    if not os.path.exists(movies_dir):
        print(" Prep movies directory: %s" % movies_dir)
        os.makedirs(movies_dir, exist_ok=True)
    

    ## prepare the output directories if they dont exist
    movies_dir = os.path.join(dest, 'movies')
    if not os.path.exists(movies_dir):
        print(" Prep movies directory: %s" % movies_dir)
        os.makedirs(movies_dir, exist_ok=True)
    jpgs_dir = os.path.join(dest, 'jpgs')
    if not os.path.exists(jpgs_dir):
        print(" Prep jpgs directory: %s" % jpgs_dir)
        os.makedirs(jpgs_dir, exist_ok=True)

    ## WIP 
    exit()
    for source_file in glob.glob(glob_string, recursive = True):
        print(" source file found =", source_file)
        initial_time = time.time()
        
        dest_file = os.path.join(dest, os.path.join(root_dir_name, source_file[len(source):]))

        ## treat files and directories differently 
        if os.path.isdir(source_file):
            if not os.path.exists(dest_file):
                if DRY_RUN:
                    print(" create dir :: %s" % (dest_file))
                else:
                    print(" create dir :: %s" % (dest_file))
                    os.makedirs(dest_file, exist_ok=True)
            else:
                continue 

        if os.path.isfile(source_file):
            ## reject symlinks 
            if(os.path.islink(source_file)):
                print(" Symlink skipped (%s)" % source_file)
                continue 

            if not os.path.exists(dest_file):
                dest_path = os.path.dirname(dest_file)
                if DRY_RUN:
                    print(" copy :: %s -> %s" % (source_file, dest_path))
                else:
                    print(" copy :: %s -> %s" % (source_file, dest_path), end='\r')
                    shutil.copy2(source_file, dest_path)
                    total_time_taken = time.time() - initial_time
                    print(" copy :: %s -> %s (%.2f sec)" % (source_file, dest_path, total_time_taken))
            elif not filecmp.cmp(source_file, dest_file, shallow=True):
                dest_path = os.path.dirname(dest_file)
                if DRY_RUN:
                    print(" file exists but appears different, copy :: %s -> %s" % (source_file, dest_path))
                else:
                    print(" file exists but appears different, copy :: %s -> %s (%.2f sec)" % (source_file, dest_path, total_time_taken))
                    shutil.copy2(source_file, dest_path)
            else:
                # print(" ... file exists already: %s" % dest_file)
                continue 

    return 

#endregion

#############################
#region :: RUN BLOCK
#############################

if __name__ == '__main__':
    import glob
    import os
    import shutil
    import sys 
    import time
    import filecmp

    seconds_delay = 300

    cmd_line = sys.argv
    # PARALLEL_PROCESSING = False
    DRY_RUN = False
    MOVIES_COPY = False

    ## read all entries and check if the help flag is called at any point
    for cmd in cmd_line:
        if cmd == '-h' or cmd == '--help' or cmd == '--h':
            usage()
        if len(cmd_line) < 3:
            usage()

    ## parse any flags
    for i in range(len(cmd_line)):
        # if cmd_line[i] == '--j':
        #     threads = 2
        #     PARALLEL_PROCESSING = True
        #     ## try parsing the number of threads 
        #     try:
        #         threads = int(cmd_line[i+1])
        #         print(" Using %s threads" % threads)
        #     except:
        #         print(" Could not parse # of threads, or none given, using default: %s" % threads)
        if cmd_line[i] in ['--dry-run', '--dry_run', '--dryrun']:
            DRY_RUN = True
            print(" Running in dry-run mode... no files will be written")
        if cmd_line[i] in ['--n']:
            try:
                seconds_delay = int(cmd_line[i+1])
            except:
                print(" Could not parse # of seconds delay given (--n flag), using default: %s" % seconds_delay)
        if cmd_line[i] in ['--movies']:
            MOVIES_COPY = True
            try:
                glob_string = str(cmd_line[i+1])
                if '*' not in glob_string:
                    glob_string = '*Fractions.mrc'
                    print(" Unexpected glob pattern given for --movie flag (%s), reverting to default: %s" % (cmd_line[i+1], glob_string))
            except:
                glob_string = '*Fractions.mrc'
                print(" No explicit glob pattern given for --movie flag, using default: %s" % glob_string)

    source, dest = get_dirs(cmd_line)

    if seconds_delay <= 0:
        ## no loop
        try:
            start_time = time.time()
            if MOVIES_COPY:
                copy_movies(source, dest, glob_string)
            else:
                copy_project(source, dest)
            end_time = time.time()
            total_time_taken = end_time - start_time
            print(" ... copy runtime = %.2f sec" % total_time_taken)

        except KeyboardInterrupt:
            print(" Terminating ...")

            sys.exit()
    else:
        ## tuck the command into a loop
        while True:
            try:
                start_time = time.time()
                if MOVIES_COPY:
                    copy_movies(source, dest, glob_string)
                else:
                    copy_project(source, dest)
                end_time = time.time()
                total_time_taken = end_time - start_time
                print(" ... copy runtime = %.2f sec" % total_time_taken)

                for i in range(seconds_delay,0,-1):
                    print(f" ... next copy in: {i} seconds", end="\r", flush=True)
                    time.sleep(1)

                # time.sleep(seconds_delay)

            except KeyboardInterrupt:
                print(" Terminating ...")

                sys.exit()

        
    


#endregion