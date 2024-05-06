#!/usr/bin/env python3

"""
    A simple copy script to loop infinitely while collecting data from an EPU session and 
    transfer files to an attached harddisk.  
"""

## 2024-05-06 A.Keszei: Start script 

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
    print("    $ EPU_active_copy.py  /source/EPU/dir  /target/dir")
    print(" ")
    print(" -----------------------------------------------------------------------------------------------")
    print(" Options (default in brackets): ")
    # print("           --j (2) : Attempt multiprocessing over given cores (remember speed is limited by HDD!)")
    print("         --dry-run : Give an example of what the copy command will do without copying")
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
        print(" Parsed source and dest directories:")
        print("   source = ", source)
        print("     dest =", dest)
    return source, dest

def copytree(src, dst, symlinks = False, ignore = None, DRY_RUN = False):
    """
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

    start_time = time.time()

    cmd_line = sys.argv
    # PARALLEL_PROCESSING = False
    DRY_RUN = False

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

    source, dest = get_dirs(cmd_line)

    for source_file in glob.glob(os.path.join(source,'**'), recursive = True):
        dest_file = os.path.join(dest, source_file[len(source):])

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
                    print(" copy :: %s -> %s" % (source_file, dest_path))
                    shutil.copy2(source_file, dest_path)
            elif not filecmp.cmp(source_file, dest_file, shallow=True):
                dest_path = os.path.dirname(dest_file)
                if DRY_RUN:
                    print(" file exists but appears different, copy :: %s -> %s" % (source_file, dest_path))
                else:
                    print(" file exists but appears different, copy :: %s -> %s" % (source_file, dest_path))
                    shutil.copy2(source_file, dest_path)
            else:
                # print(" ... file exists already: %s" % dest_file)
                continue 

    end_time = time.time()
    total_time_taken = end_time - start_time
    print("... runtime = %.2f sec" % total_time_taken)

#endregion