"""
	A module for parsing command line entries in a generalizable way.
	Import these functions directly via:
		import cmdline_handler
    Then, use functions by dot extension:
		cmdline_handler.parse(sys.argv, usage, min_args, VAR_LIB, EXP_FLAGS, EXP_FILES)

    Be sure to set up the input dictionaries and list in the following format within scripts that call this handler:

    1. Library containing all the variables needed by functions in the script:
            VAR_LIB = {
                'file'     : str(),
                'file2'    : str(),
                'TOGGLE'   : False,     # e.g., default value is False
                'variable' : 4,         # e.g., default value is 4
                'choice'   : 'one'      # e.g., default value of 'one'
            }
    2. Library of each expected flag and details of their type, range, toggle and presence of default settings:
             EXP_FLAGS = {
              ##  flag_name   :  VAR_LIB_key   DATA_TYPE    RANGE/LEGAL ENTRIES,     IS_TOGGLE,   HAS_DEFAULTS
                 '--flag'     : ('TOGGLE',     bool(),      (),                      True,        True ),
                 '--flag2'    : ('variable',   int(),       (1,999),                 False,       True ),
                 '--flag3'    : ('choice',     str(),       ('one', 'two', 'three'),  False,       True ),
             }

     3. List containing all anticipated files and their expected argument position (e.g. $1 = index 1; $2 = index 2,...)
             EXP_FILES = [
              ## cmd_line_index,   expected_extension,          VAR_LIB_key
                (1,                '.ser',                      'file' ),
                (2,                ['.jpg', '.png', '.gif'],    'file2')
             ]
"""

##################################
## DEPENDENCIES
##################################
import os
import sys
import glob


def parse(cmdline, min_args, VAR_LIB, EXP_FLAGS, EXP_FILES):
    """
    Generalizable parser for commandline inputs and options. See parent doc string for formatting example
	---------------------------------------------------------------
	PARAMETERS
	---------------------------------------------------------------
        cmdline = list(); arguments on the command line
        min_args = int(); minimum number of aguments needed to run program (e.g. if need $1 and $2, min_args = 2)
        VAR_LIB = dict(); variable library, see above
        EXP_FLAGS = dict(); expected flags from cmd line, see above
        EXP_FILES = list(); expected files to be read by the program from the cmd line, see above
	---------------------------------------------------------------
	RETURNS
	---------------------------------------------------------------
        VAR_LIB = an updated dict() after reading command line inputs
        EXIT_CODE = return code for main program to determine if it should call the usage() function and terminate:
            1 = successfully parsed cmd line
            -1 = error encountered during parsing
    """
    EXIT_CODE = -1
    ## check there is a minimum number of arguments input by the user
    if len(cmdline) - 1 < min_args:
        return VAR_LIB, EXIT_CODE
    ## check for the help flag with elevated priority
    for entry in cmdline:
        if entry in ['-h', '-help', '--h', '--help']:
            print(' ... help flag called (%s).' % entry)
            return VAR_LIB, EXIT_CODE

    ## load all expected files based on their explicit index and check for proper extension in name, while doing this check if batch mode is being activated
    BATCH_MODE_FILE1 = False
    for index, expected_extension, key in EXP_FILES:
        parsed_extension = os.path.splitext(cmdline[index])[1].lower()
        if len(parsed_extension) == 0:
            print(" ERROR :: Incompatible %s file provided (%s)" % (expected_extension, cmdline[index]))
            return VAR_LIB, EXIT_CODE
        elif os.path.splitext(cmdline[index])[1].lower() in expected_extension:
            VAR_LIB[key] = cmdline[index]
            print(" ... %s set: %s" % (key, VAR_LIB[key]))
        else:
            print(" ERROR :: Incompatible %s file provided (%s)" % (expected_extension, cmdline[index]))
            return VAR_LIB, EXIT_CODE
        ## check if user is attempting to set up batch mode, which requires file #1 to start with * and file #2 to start with @ symbol:
        if index == 1:
            if os.path.splitext(os.path.basename(VAR_LIB[key]))[0] == "*":
                BATCH_MODE_FILE1 = True
        elif index == 2:
            if BATCH_MODE_FILE1:
                if os.path.splitext(os.path.basename(VAR_LIB[key]))[0] == "@":
                    VAR_LIB['BATCH_MODE'] = True
                    print(" ... batch mode = ON")
                else:
                    print(" ERROR :: Batch mode detected (%s), but incompatible second entry (%s), try: @%s" % ('*' + EXP_FILES[0][1], cmdline[index], os.path.splitext(cmdline[index])[1]))
                    return VAR_LIB, EXIT_CODE
            elif os.path.splitext(os.path.basename(VAR_LIB[key]))[0] == "@":
                print(" ERROR :: Batch mode detected (%s), but incompatible first entry (%s), try: *%s" % (cmdline[2], cmdline[1], os.path.splitext(cmdline[index - 1])[1]))
                return VAR_LIB, EXIT_CODE

    ## after checking for help flags, try to read in all flags into global dictionary
    for entry in cmdline:
        if entry in EXP_FLAGS:
            # print("Entry found: %s (index %s)" % (entry, cmd_line.index(entry)))
            VAR_LIB, read_flag_EXIT_CODE = read_flag(cmdline, entry, cmdline.index(entry), VAR_LIB, EXP_FLAGS[entry][0], EXP_FLAGS[entry][1], EXP_FLAGS[entry][2], EXP_FLAGS[entry][3], EXP_FLAGS[entry][4], EXP_FLAGS)
            if read_flag_EXIT_CODE < 0:
                return VAR_LIB, EXIT_CODE
        elif "--" in entry:
            print(" WARNING :: unexpected flag not parsed: (%s)" % entry)

    EXIT_CODE = 1
    return VAR_LIB, EXIT_CODE

def read_flag(cmdline, flag, cmdline_flag_index, VAR_LIB, VAR_LIB_key, data_type, legal_entries, is_toggle, has_defaults, EXP_FLAGS):
    ## if the flag serves as a toggle, switch it on and exit
    if is_toggle:
        VAR_LIB[VAR_LIB_key] = True
        print(" ... set: %s = %s" % (VAR_LIB_key, True))
        return VAR_LIB, 1

    ## if the flag has a default setting, quickly sanity check if we are using it
    if has_defaults:
        ## if there are no more entries on the command line after the flag, we necessarily are using the defaults
        if len(cmdline[1:]) <= cmdline_flag_index:
            print(" ... use default: %s = %s" % (VAR_LIB_key, VAR_LIB[VAR_LIB_key]))
            return VAR_LIB, 1
        else:
            ## check if subsequent entry on cmd line is a flag itself, in which case we are using defaults
            if cmdline[cmdline_flag_index + 1] in EXP_FLAGS:
                print(" ... use default: %s = %s" % (VAR_LIB_key, VAR_LIB[VAR_LIB_key]))
                return VAR_LIB, 1

    ## sanity check there exists an entry next to the flag before attempting to parse it
    if len(cmdline[1:]) <= cmdline_flag_index:
        print(" ERROR :: No value provided for flag (%s)" % flag)
        return VAR_LIB, -1
    ## parse the entry next to the flag depending on its expected type and range
    ## 1) INTEGERS
    if isinstance(data_type, int):
        try:
            user_input = int(cmdline[cmdline_flag_index + 1])
        except:
            print(" ERROR :: %s flag requires an integer as input (%s given)" % (flag, cmdline[cmdline_flag_index + 1]))
            return VAR_LIB, -1
        ## check if the assigned value is in the expected range
        if legal_entries[0] <= user_input <= legal_entries[1]:
            VAR_LIB[VAR_LIB_key] = user_input
            print(" ... set: %s = %s" % (VAR_LIB_key, VAR_LIB[VAR_LIB_key]))
            return VAR_LIB, 1
        else:
            print(" ERROR :: %s flag input (%s) out of expected range: [%s, %s]" % (flag, user_input, legal_entries[0], legal_entries[1]))
            return VAR_LIB, -1
    ## 2) FLOATS
    if isinstance(data_type, float):
        try:
            user_input = float(cmd_line[cmd_line_flag_index + 1])
        except:
            print(" ERROR :: %s flag requires a float as input (%s given)" % (flag, cmdline[cmdline_flag_index + 1]))
            return VAR_LIB, -1
        ## check if the assigned value is in the expected range
        if legal_entries[0] <= user_input <= legal_entries[1]:
            VAR_LIB[VAR_LIB_key] = user_input
            print(" ... set: %s = %s" % (VAR_LIB_key, VAR_LIB[VAR_LIB_key]))
            return VAR_LIB, 1
        else:
            print(" ERROR :: %s flag input (%s) out of expected range: [%s, %s]" % (flag, user_input, legal_entries[0], legal_entries[1]))
            return VAR_LIB, -1
    ## 3) STRINGS
    if isinstance(data_type, str):
        try:
            user_input = cmdline[cmdline_flag_index + 1]
        except:
            print(" ERROR :: %s flag requires a string as input (%s given)" % (flag, cmdline[cmdline_flag_index + 1]))
            return VAR_LIB, -1
        ## check if there are legal keywords (i.e. any entry is acceptable)
        if len(legal_entries) == 0:
            VAR_LIB[VAR_LIB_key] = user_input
            print(" ... set: %s = %s" % (VAR_LIB_key, VAR_LIB[VAR_LIB_key]))
            return VAR_LIB, 1
        ## otherwise, check if the assigned value is a legal keyword
        elif user_input in legal_entries:
            VAR_LIB[VAR_LIB_key] = user_input
            print(" ... set: %s = %s" % (VAR_LIB_key, VAR_LIB[VAR_LIB_key]))
            return VAR_LIB, 1
        else:
            print(" ERROR :: %s flag input (%s) is not a legal entry, try one of: " % (flag, user_input))
            print(legal_entries)
            return VAR_LIB, -1

if __name__ == "__main__":

    VAR_LIB = {
         'file'     : str(),
         'file2'    : str(),
         'TOGGLE'   : False,     # e.g., default value is False
         'variable' : 4,         # e.g., default value is 4
         'choice'   : 'one',      # e.g., default value of 'one'
         'name'     : 'alex',     # e.g., default entry of 'alex'
		 'threads'  : None,
    }

    EXP_FLAGS = {
       ##  flag_name   :  VAR_LIB_key   DATA_TYPE    RANGE/LEGAL ENTRIES,     IS_TOGGLE,   HAS_DEFAULTS
          '--flag'     : ('TOGGLE',     bool(),      (),                      True,        True ),
          '--flag2'    : ('variable',   int(),       (1,999),                 False,       True ),
          '--flag3'    : ('choice',     str(),       ('one', 'two', 'three'), False,       True ),
          '--flag4'    : ('name',       str(),       (),                      False,       True),
		  '--j'        : ('threads',    int(),       (1,999),                 False,       False)
    }

    EXP_FILES = [
       ## cmd_line_index,   expected_extension,          VAR_LIB_key
         (1,                '.ser',                      'file' ),
         (2,                ['.jpg', '.png', '.gif'],    'file2')
    ]

    ## test this script with all options:
    test_cmd = ['cmdline_handler.py', 'test.ser']
    VAR_LIB, EXIT_CODE = parse(test_cmd, 2, VAR_LIB, EXP_FLAGS, EXP_FILES)
    print("EXIT CODE = ", EXIT_CODE)

    test_cmd = ['cmdline_handler.py', 'test.ser', 'test.jpg', '-h']
    VAR_LIB, EXIT_CODE = parse(test_cmd, 2, VAR_LIB, EXP_FLAGS, EXP_FILES)
    print("EXIT CODE = ", EXIT_CODE)

    test_cmd = ['cmdline_handler.py', 'test.ser', 'test.jpg']
    VAR_LIB, EXIT_CODE = parse(test_cmd, 2, VAR_LIB, EXP_FLAGS, EXP_FILES)
    print("EXIT CODE = ", EXIT_CODE)

    test_cmd = ['cmdline_handler.py', 'test.ser', 'test.jpg', '--flag', '--flag2', '22', '--flag3', 'two']
    VAR_LIB, EXIT_CODE = parse(test_cmd, 2, VAR_LIB, EXP_FLAGS, EXP_FILES)
    print("EXIT CODE = ", EXIT_CODE)

    test_cmd = ['cmdline_handler.py', 'test.ser', 'test.jpg', '--flag', '--flag2', 'abc', '--flag3', 'two']
    VAR_LIB, EXIT_CODE = parse(test_cmd, 2, VAR_LIB, EXP_FLAGS, EXP_FILES)
    print("EXIT CODE = ", EXIT_CODE)

    test_cmd = ['cmdline_handler.py', 'test.ser', 'test.jpg', '--flag', '--flag2', '22', '--flag3', 'two']
    VAR_LIB, EXIT_CODE = parse(test_cmd, 2, VAR_LIB, EXP_FLAGS, EXP_FILES)
    print("EXIT CODE = ", EXIT_CODE)

    test_cmd = ['cmdline_handler.py', 'test.jpg', 'test.ser', '--flag', '--flag2', '22', '--flag3', 'two']
    VAR_LIB, EXIT_CODE = parse(test_cmd, 2, VAR_LIB, EXP_FLAGS, EXP_FILES)
    print("EXIT CODE = ", EXIT_CODE)

    test_cmd = ['cmdline_handler.py', 'test.ser', 'test.jpg', '--flag', '--flag2', '22', '--flag3', 'twenty']
    VAR_LIB, EXIT_CODE = parse(test_cmd, 2, VAR_LIB, EXP_FLAGS, EXP_FILES)
    print("EXIT CODE = ", EXIT_CODE)

    test_cmd = ['cmdline_handler.py', 'test.ser', 'test.jpg', '--flag', '--flag2', '22', '--flag3', 'two', '--flag4']
    VAR_LIB, EXIT_CODE = parse(test_cmd, 2, VAR_LIB, EXP_FLAGS, EXP_FILES)
    print("EXIT CODE = ", EXIT_CODE)

    test_cmd = ['cmdline_handler.py', '*.ser', 'test.jpg', '--flag', '--flag2', '22', '--flag3', 'two']
    VAR_LIB, EXIT_CODE = parse(test_cmd, 2, VAR_LIB, EXP_FLAGS, EXP_FILES)
    print("EXIT CODE = ", EXIT_CODE)

    test_cmd = ['cmdline_handler.py', 'test.ser', '@.jpg', '--flag', '--flag2', '22', '--flag3', 'two']
    VAR_LIB, EXIT_CODE = parse(test_cmd, 2, VAR_LIB, EXP_FLAGS, EXP_FILES)
    print("EXIT CODE = ", EXIT_CODE)

    test_cmd = ['cmdline_handler.py', '@.jpg', '--flag', '--flag2', '22', '--flag3', 'two']
    VAR_LIB, EXIT_CODE = parse(test_cmd, 2, VAR_LIB, EXP_FLAGS, EXP_FILES)
    print("EXIT CODE = ", EXIT_CODE)

    test_cmd = ['cmdline_handler.py', '@.jpg', '--flag', '--flag2', '22', '--flag3', 'two', '--flag4', 'peter']
    VAR_LIB, EXIT_CODE = parse(test_cmd, 2, VAR_LIB, EXP_FLAGS, EXP_FILES)
    print("EXIT CODE = ", EXIT_CODE)

    test_cmd = ['cmdline_handler.py', '@.jpg', '--flag', '--flag2', '22', '--flag3', 'two', '--flag4', 'peter', '--j', '4']
    VAR_LIB, EXIT_CODE = parse(test_cmd, 2, VAR_LIB, EXP_FLAGS, EXP_FILES)
    print("EXIT CODE = ", EXIT_CODE)

    test_cmd = ['cmdline_handler.py', '@.jpg', '--flag', '--flag2', '22', '--flag3', 'two', '--flag4', 'peter', '--j']
    VAR_LIB, EXIT_CODE = parse(test_cmd, 2, VAR_LIB, EXP_FLAGS, EXP_FILES)
    print("EXIT CODE = ", EXIT_CODE)
