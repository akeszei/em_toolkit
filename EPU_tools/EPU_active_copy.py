#!/usr/bin/env python3

"""
    A simple copy script to loop infinitely while collecting data from an EPU session and 
    transfer files to an attached harddisk.  
"""

## 2024-05-06 A.Keszei: Start script 
## 2024-06-13: Updated for speed (remove full similarity check on large movie files), adjusted flags, moved cmd line parsing to PARAMETERS object & added reorganize behavior

#############################
#region :: GLOBAL FLAGS
#############################
DEBUG = True
#endregion

#############################
#region :: DEFINITION BLOCK
#############################
def usage():
    print("===================================================================================================")
    print(" Usage:")
    print("    $ EPU_active_copy.py  /path/to/EPU  /target/save/dir")
    print(" Will actively mirror the EPU directory in the target directory, e.g.: /target/dir/EPU, every")
    print(" 5 minutes (unless changed). Kill the script with Ctrl + C.")
    print(" Use the reorganize option to copy only the important data, e.g.:")
    print("    $ EPU_active_copy.py  /mnt/dmp/EPU_project  /mount/remote/HDD/  --reorganize")
    print(" -----------------------------------------------------------------------------------------------")
    print(" Options (default in brackets): ")
    # print("           --j (2) : Attempt multiprocessing over given cores (remember speed is limited by HDD!)")
    print("  --movies (*Fractions.mrc) : Change the glob string that identifies movie files uniquely")
    # print("                              if possible, also copy .JPGs for manual curation later")
    print("               --reorganize : Copy EPU project into a simpler directory structure (will also retain")
    print("                              all files placed in a directory named 'Screening' or 'Misc' ")
    print("                  --dry-run : Give an example of what the copy command will do without copying")
    print("                  --n (300) : Delay time in seconds between copy loops; -1 or 0 == dont loop")
    print("===================================================================================================")
    sys.exit()

def copytree(src, dst, symlinks = False, ignore = None, DRY_RUN = False):
    """ Not used, but kept for reference. 
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

def copy_project(source, dest, glob_string = '**', DRY_RUN = False, DEBUG = False):
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

def copy_file(file_path, dest_path, SIZE_ONLY = False, DRY_RUN = False):
    """
    RETURNS 
         1 = file was copied to the destination
         0 = was was skipped since it was a symlink  
        -1 = file was skipped since it was already presenet at the destination directory 
    """
    EXIT_CODE = 0 ## pass 

    initial_time = time.time()

    if os.path.isfile(file_path):
        ## reject symlinks 
        if(os.path.islink(file_path)):
            print(" Symlink skipped (%s)" % file_path)
            return 0

    dest_file = os.path.join(dest_path, os.path.basename(file_path))
    dest_path = os.path.dirname(dest_file)
    if not os.path.exists(dest_file):
        if DRY_RUN:
            print(" copy :: %s -> %s" % (file_path, dest_path))
            EXIT_CODE = 1
        else:
            print(" copy :: %s -> %s" % (file_path, dest_path), end='\r')
            shutil.copy2(file_path, dest_path)
            total_time_taken = time.time() - initial_time
            print(" copy :: %s -> %s (%.2f sec)" % (file_path, dest_path, total_time_taken))
            EXIT_CODE = 1
    else:
        ## the file exists, evaluate if it is different than the source file?
        if SIZE_ONLY:
            ## only use a very shallow check for file size (not contents nor date modified)
            source_size = os.stat(file_path).st_size
            dest_size = os.stat(dest_file).st_size
            if not source_size == dest_size:
                if DRY_RUN:
                    print(" .. file exists but appears different, copy :: %s -> %s" % (file_path, dest_path))
                    EXIT_CODE = 1
                else:
                    print(" .. file exists but appears different, copy :: %s -> %s " % (file_path, dest_path), end='\r')
                    shutil.copy2(file_path, dest_path)
                    total_time_taken = time.time() - initial_time
                    print(" .. file exists but appears different, copy :: %s -> %s (%.2f sec)" % (file_path, dest_path, total_time_taken))
                    EXIT_CODE = 1
            ## if movie exists and is the same size, skip it 
            else:
                if DEBUG: print(" ... file exists already: %s" % dest_file)
                EXIT_CODE = -1
        ## use a more full check for file 
        else:
            if not filecmp.cmp(file_path, dest_file, shallow=True):
                if DRY_RUN:
                    print(" file exists but appears different, copy :: %s -> %s" % (file_path, dest_path))
                    EXIT_CODE = 1
                else:
                    print(" file exists but appears different, copy :: %s -> %s" % (file_path, dest_path), end='\r')
                    shutil.copy2(file_path, dest_path)
                    total_time_taken = time.time() - initial_time
                    print(" file exists but appears different, copy :: %s -> %s (%.2f sec)" % (file_path, dest_path, total_time_taken))

    return EXIT_CODE

def copy_reorganized(source, dest, glob_string, DRY_RUN = False):
    """
        A function to copy an EPU project into a simpler structure while preserving important metadata relationships.
            EPU_project_dir/ (dest)
            ├── Atlas  :: any files relating the grid atlas (i.e.'Atlas*mrc')  
            ├── Movies :: all files matching movie_string (i.e. *Fractions.mrc)
            ├── Xml    :: .xml files for every acquisition containing all relevant microscope metadata for that image
            ├── Jpg    :: .jpg files for every acquisition in case the user wants to quickly check the datset by eye
            └── Other  :: any files found in the root project folder or folders named 'Screening' or 'Misc'    
    """

    #region 1. prepare a list of the files we are interested in copying 
    other_files = []
    for i in os.listdir(source):
        if 'screening' in i:
            if os.path.isdir(os.path.join(source,i)):
                for f in os.listdir(os.path.join(source,i)):
                    other_files.append(os.path.join(os.path.join(source, i),f))
        if 'misc' in i:
            if os.path.isdir(os.path.join(source,i)):
                for f in os.listdir(os.path.join(source,i)):
                    other_files.append(os.path.join(os.path.join(source, i),f))
        ## also take any files in the root folder itself
        if os.path.isfile(os.path.join(source,i)):
            other_files.append(os.path.join(source, i))

    atlas_glob_str = os.path.join(os.path.join(os.path.normpath(source),'**/'), "Atlas*mrc")
    atlas_files = glob.glob(atlas_glob_str, recursive = True)

    movies_glob_str = os.path.join(os.path.join(os.path.normpath(source),'**/'), glob_string)
    movie_files = glob.glob(movies_glob_str, recursive = True)

    xml_glob_str = os.path.join(os.path.join(os.path.normpath(source),'**/'), "*Data*xml")
    xml_files = glob.glob(xml_glob_str, recursive = True)

    ## edit the xml file list to remove xml files referring to the fractionation, keeping only the important exposure xml file 
    for xml in xml_files:
        xml_basename = os.path.splitext(os.path.basename(xml))[0]
        movie_glob_basename = os.path.splitext(os.path.basename(glob_string).replace('*',''))[0]
        
        if xml_basename[-len(movie_glob_basename):] == movie_glob_basename:
            xml_files.remove(xml)

    jpg_glob_str = os.path.join(os.path.join(os.path.normpath(source),'**/'), "*Data*jpg")
    jpg_files = glob.glob(jpg_glob_str, recursive = True)
    #endregion

    #region 2. prepare the output directories if they dont exist
    epu_project_dirname = os.path.basename(os.path.normpath(source))
    atlas_dir = os.path.join(dest, epu_project_dirname, 'Atlas')
    if not os.path.exists(atlas_dir):
        print(" Prep atlas directory: %s" % atlas_dir)
        if not DRY_RUN: os.makedirs(atlas_dir, exist_ok=True)
    movies_dir = os.path.join(dest, epu_project_dirname, 'Movies')
    if not os.path.exists(movies_dir):
        print(" Prep movies directory: %s" % movies_dir)
        if not DRY_RUN: os.makedirs(movies_dir, exist_ok=True)
    jpgs_dir = os.path.join(dest, epu_project_dirname, 'Jpg')
    if not os.path.exists(jpgs_dir):
        print(" Prep jpgs directory: %s" % jpgs_dir)
        if not DRY_RUN: os.makedirs(jpgs_dir, exist_ok=True)
    xml_dir = os.path.join(dest, epu_project_dirname, 'Xml')
    if not os.path.exists(xml_dir):
        print(" Prep xml directory: %s" % xml_dir)
        if not DRY_RUN: os.makedirs(xml_dir, exist_ok=True)
    if len(other_files) > 0:
        other_dir = os.path.join(dest, epu_project_dirname, 'Other')
        if not os.path.exists(other_dir):
            print(" Prep misc directory: %s" % other_dir)
            if not DRY_RUN: os.makedirs(other_dir, exist_ok=True)


    #endregion 

    #region 3. run through the copy operations, list-by-list 
    skipped_files = 0
    copied_files = 0
    movies_skipped = 0
    total_files = len(atlas_files) + len(xml_files) + len(jpg_files) + len(other_files) + len(movie_files)
    for f in atlas_files:
        EXIT_CODE = copy_file(f,atlas_dir, DRY_RUN = DRY_RUN )
        if EXIT_CODE == -1:
            skipped_files += 1
        elif EXIT_CODE == 1:
            copied_files += 1

    for f in xml_files:
        EXIT_CODE = copy_file(f,xml_dir, DRY_RUN = DRY_RUN )
        if EXIT_CODE == -1:
            skipped_files += 1
        elif EXIT_CODE == 1:
            copied_files += 1

    for f in jpg_files:
        EXIT_CODE = copy_file(f,jpgs_dir, DRY_RUN = DRY_RUN )
        if EXIT_CODE == -1:
            skipped_files += 1
        elif EXIT_CODE == 1:
            copied_files += 1

    for f in other_files:
        EXIT_CODE = copy_file(f, other_dir, DRY_RUN = DRY_RUN)
        if EXIT_CODE == -1:
            skipped_files += 1
        elif EXIT_CODE == 1:
            copied_files += 1

    for f in movie_files:
        EXIT_CODE = copy_file(f,movies_dir, DRY_RUN = DRY_RUN, SIZE_ONLY= True)
        if EXIT_CODE == -1:
            skipped_files += 1
            movies_skipped += 1
        elif EXIT_CODE == 1:
            copied_files += 1
    
    #endregion

    print_stats(total_files, glob_string, len(movie_files), skipped_files, movies_skipped, DRY_RUN = DRY_RUN)

    return 

#endregion

class PARAMETERS():
    """
        Use this object to capture all flags and parameter settings from the command line
    """
    def __init__(self, cmdline = None):
        ## set the default parameters 
        self.DRY_RUN = False
        self.seconds_delay = 300
        self.REORGANIZE = False
        self.glob_string = "*Fractions.mrc"
        self.source = None 
        self.dest = None

        ## if a cmdline is supplied, pass it to the parser function
        if cmdline != None:
            self.parse_flags(cmdline)
            self.get_dirs(cmdline[1:]) ## remove the first command, which is the script call that looks 'path-like'
        ## print the parameters 
        self.__str__()
        return 

    def parse_flags(self, cmdline):
        ## sanity check there are even enough commands to run a plausible copy command
        min_cmds = 4
        if len(cmdline) < min_cmds:
            usage()
        
        ## check if the help flag was called in any position
        for cmd in cmdline: 
            if cmd == '-h' or cmd == '--help' or cmd == '--h':
                usage()

        ## parse any flags
        for i in range(len(cmdline)):
            if cmdline[i] in ['--dry-run', '--dry_run', '--dryrun']:
                self.DRY_RUN = True

            if cmdline[i] in ['--reorganize']:
                self.REORGANIZE = True

            if cmdline[i] in ['--n', '-n']:
                try:
                    self.seconds_delay = int(cmdline[i+1])
                except:
                    print(" Could not parse # of seconds delay given (--n flag), using default: %s" % self.seconds_delay)

            if cmdline[i] in ['--movies']:
                try:
                    glob_string = str(cmdline[i+1])
                    if '*' not in glob_string:
                        print(" Unexpected glob pattern given for --movie flag, using default: %s" % self.glob_string)
                    else:
                        self.glob_string = glob_string
                except:
                    print(" No explicit glob pattern given for --movie flag, using default: %s" % self.glob_string)

        return 

    def get_dirs(self, cmdline):
        ## expect directory structures to contain slashes with the source preceding the dest
        source = None 
        dest = None
        for cmd in cmdline:
            if '/' in cmd or '\\' in cmd:
                if source == None:
                    source = cmd 
                elif dest == None:
                    dest = cmd 
                else:
                    print(" WARNING :: More than one path was detected on the command line! (%s)" % cmd)
        
        ## SOURCE
        ## sanity check folder exists 
        if not os.path.isdir(source):
            print(" ERROR :: Could not find source directory: %s" % source)
            usage()

        ## make sure it has a leading slash for consistentcy 
        if not source[-1] in ['/', '\\' ]:
            source = source + '/'

        ## DEST
        ## sanity check folder exists 
        if not os.path.isdir(dest):
            print(" ERROR :: Could not find destination directory: %s" % dest)
            usage()

        ## make sure it has a leading slash for consistentcy 
        if not dest[-1] in ['/', '\\' ]:
            dest = dest + '/'
        
        self.source = source 
        self.dest = dest
        return 

    def __str__(self):
        print("=============================")
        print("  PARAMETERS")
        print("-----------------------------")
        print("  source dir = %s" % self.source)
        print("    dest dir = %s" % self.dest)
        print("  DRY_RUN = %s" % self.DRY_RUN)
        print("  seconds delay = %s" % self.seconds_delay)
        print("  REORGANIZE output dir = %s" % self.REORGANIZE)
        print("  movie glob string = '%s'" % self.glob_string)
        print("=============================")

        return ''


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

    PARAMS = PARAMETERS(sys.argv)

    if PARAMS.seconds_delay <= 0:
        ## no loop
        try:
            start_time = time.time()
            if PARAMS.REORGANIZE:
                copy_reorganized(PARAMS.source, PARAMS.dest, PARAMS.glob_string, DRY_RUN= PARAMS.DRY_RUN)
            else:
                copy_project(PARAMS.source, PARAMS.dest, DRY_RUN= PARAMS.DRY_RUN)
            end_time = time.time()
            total_time_taken = end_time - start_time
            print(" ... copy runtime = %.2f sec" % total_time_taken)

        except KeyboardInterrupt:
            print()
            print(" Terminating ...")

            sys.exit()
    else:
        ## tuck the command into a loop
        while True:
            try:
                start_time = time.time()
                if PARAMS.REORGANIZE:
                    copy_reorganized(PARAMS.source, PARAMS.dest, PARAMS.glob_string, DRY_RUN= PARAMS.DRY_RUN)
                else:
                    copy_project(PARAMS.source, PARAMS.dest, DRY_RUN= PARAMS.DRY_RUN)
                end_time = time.time()
                total_time_taken = end_time - start_time
                print(" ... copy runtime = %.2f sec" % total_time_taken)

                ## Add a live timer to display to the user the sleeping state is actively running 
                for i in range(PARAMS.seconds_delay,0,-1):
                    print(f" ... next copy in: {i} seconds", end="\r", flush=True)
                    time.sleep(1)

            except KeyboardInterrupt:
                print(" Terminating ...")

                sys.exit()

#endregion