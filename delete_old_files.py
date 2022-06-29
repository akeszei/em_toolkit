
def usage():
    print("====================================================================================================")
    print(" Run in the working directory to delete files older than a given number of days.")
    print(" Default behaviour is to delete files older than ~6 months (182 days).")
    print("    $ delete_old_files.py ")
    print("------------------------------------------------------------------------------------------------")
    print(" Options: ")
    print("      --days (182) : delete files older than the given value in days")
    print("====================================================================================================")
    sys.exit()

def parse_flags(PARAMS):
    cmdline = sys.argv
    min_args = 0
    ## check if help flag was called or we have a minimum number of arguments to evaluate
    if len(cmdline) - 1 < min_args or check_for_flag(cmdline, ['-h', '-help', '--h', '--help']):
        print(" Not enough arguments, or help flag called")
        usage()

    if check_for_flag(cmdline, ['--days']):
        ## parse the --days flag
        index = get_flag_index(cmdline, '--days')
        if len(cmdline) - 1 >= index + 1:
            try:
                PARAMS['days_threshold'] = int(cmdline[index + 1])
            except:
                print(" ERROR :: Input for '--days' flag not parsable (%s)." % cmdline[index + 1])
        else:
            print(" ERROR :: No value provided for '--days' flag, using default value.")

        print(" Look for files older than %s days" % PARAMS['days_threshold'])
    return PARAMS

def check_for_flag(cmdline, flag_list):
    for entry in cmdline:
        if entry in flag_list:
            return True
    return False

def get_flag_index(cmdline, flag):
    for i in range(len(cmdline)):
        if cmdline[i] == flag:
            return i

def file_age_in_seconds(filepath):
    file_stat = os.stat(filepath)

    try:
        creation_time = datetime.fromtimestamp(file_stat.st_birthtime)
    except AttributeError:
        creation_time = datetime.fromtimestamp(file_stat.st_mtime)

    curret_time = datetime.now()
    delta = curret_time - creation_time
    age = int(delta.days)
    size = file_stat.st_size
    return age, size

def get_all_files_older_than(path, age_cutoff):
    total_size_mb = 0
    old_files = []
    for root, sub_dirs, files in os.walk(path):
        for f in files:
            f_w_path = os.path.join(root, f)
            age, size = file_age_in_seconds(f_w_path)
            if age >= age_cutoff:
                # print(f_w_path, age, True)
                total_size_mb += size / 1000**2
                old_files.append(f_w_path)
            else:
                # print(f_w_path, age, False)
                pass

    return old_files, total_size_mb

def print_report(file_list, disk_size_mb):
    print("--------------------------------------")
    print(" Total # of files to delete = %s" % len(file_list))
    if disk_size_mb > 1000:
        disk_size_gb = disk_size_mb / 1000
        print(" Total size to delete = %.2f Gb" % disk_size_gb)
    else:
        print(" Total size to delete = %.2f Mb" % disk_size_mb)

    print("--------------------------------------")
    print(" Example files to delete:")
    print("--------------------------------------")
    for i in range(6):
        if i < 3:
            print("  " + file_list[i])
        if i == 3:
            print(" ...")
        if i >= 3:
            n = i - 2
            print("  " + file_list[-n])
    print("--------------------------------------")
    return

def delete_files(file_list):
    print("--------------------------------------")
    counter = 0
    for f in file_list:
        counter += 1
        print("  >> (%s/%s) deleting file: %s" % (counter, len(file_list), f), end='\r')
        try:
            os.remove(f)
        except OSError as e:  ## if failed, report it back to the user ##
            print ("Error: %s - %s." % (e.filename, e.strerror))
    print()
    return

if __name__ == "__main__":
    import os, sys
    from datetime import datetime

    ## parse input from user
    PARAMS = {}
    PARAMS['days_threshold'] = 182
    PARAMS = parse_flags(PARAMS)

    ## remap parameters to global variables
    MAX_AGE = PARAMS['days_threshold']

    old_files, total_size_mb = get_all_files_older_than("./", MAX_AGE)

    if len(old_files) == 0:
        print(" No files match the search parameters (%s days old)" % MAX_AGE)
        sys.exit()

    print_report(old_files, total_size_mb)

    ## prompt the user to continue after displaying the proposed action of the script
    user_input = input(" Proceed with deleting files? (y/n): ")
    if user_input in ['y', 'Y', 'yes', 'YES']:
        delete_files(old_files)

    print("--------------------------------------")
    print(" COMPLETE")
