"""
	A module for commonly-needed functions when handling .STAR files from relion v.3.1
	Import these functions directly via:
		from star_handler import *
	Or only specific functions via:
		from star_handler import get_table_position, find_star_column, get_star_data , ...
	Or import the module and call functions by extension, e.g.:
		import star_handler
		star_handler.get_table_position('filename.star', 'data_model_classes')
"""

def get_table_position(file, table_title, DEBUG = True):
    """ Find the line numbers for key elements in a relion .STAR table.
		---------------------------------------------------------------
		PARAMETERS
		---------------------------------------------------------------
			file = str(); name of .STAR file with tables (e.g. "run_it025_model.star") \n
			table_title = str(); name of the .STAR table we are interested in (e.g. "data_model_classes") \n
			DEBUG = bool(); optional parameter to display or not return values \n
		---------------------------------------------------------------
		RETURNS
		---------------------------------------------------------------
			TABLE_START = int(); line number from which the table begins \n
            HEADER_START = int(); line number for the first entry after `loop_' in the table \n
			DATA_START = int(); line number for the first data entry after header \n
			DATA_END = int(); line number for the last data entry in the table \n
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
    return TABLE_START, HEADER_START, DATA_START, DATA_END

def get_star_columns_from_table(file, table_title, VERBOSE = False):
    """
    Example: 
    ------
    ```
    ## Get the execution path of this script so we can find local modules
    script_path = os.path.dirname(os.path.abspath(sys.argv[0]))

    ## Try to import the module 
    try:
        sys.path.append(script_path)
        import star_handler 
    except :
        print(" ERROR :: Check if star_handler.py script is in same folder as this script and runs without error (i.e. can be compiled)!")

    star_handler.get_star_columns_from_table('example.star', 'data_')
    ```
    """
    TABLE_START, HEADER_START, DATA_START, DATA_END = get_table_position(file, table_title, DEBUG = True)
    cols = []
    with open(file, 'r') as f :
        line_num = 0
        for line in f :
            line_num += 1
            ## check if we are in range of the header
            if line_num < HEADER_START or line_num >= DATA_START:
                continue

            line = line.strip() # remove empty spaces around line
            ## get all non-empty entries 
            if len(line) <= 0:
                continue

            ## extract the first word as the column name present in the header 
            column_name = line.split()[0]
            if len(column_name) > 0:
                cols.append(column_name)
    if VERBOSE:
        print(" get_star_columns_from_table :: ")
        print(" --------------------------------")
        for col in cols:
            print("  ", col)
        print(" --------------------------------")

    return cols

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
            if column_name == line.split()[0] :
                column_num = int(line.split()[1].replace("#",""))
                ## handle error case where input .STAR file is missing a necessary rlnColumn type
                if column_num is None :
                    print(" ERROR: Input .STAR file: %s, is missing a column for: %s" % (file, column_name) )
                    exit()
                else:
                    if DEBUG:
                        print("  ... %s column value: #%s" % (column_name, column_num))
                        # print("-------------------------------------------------------------")
                    return column_num

def get_star_data(line, column_index, DEBUG = False):
    """ For a given .STAR file line entry, extract the data at the given column index.
        If the column does not exist (e.g. for a header line read in), return 'False'
		---------------------------------------------------------------
		PARAMETERS
		---------------------------------------------------------------
			line = str(); line from file containing data columns
			column_index = int(); index of column from which to find data
			DEBUG = bool(); print on cmd line function process
		---------------------------------------------------------------
		RETURNS
		---------------------------------------------------------------
			column_value = str() or bool(); returns the value in star column index as a string, or False if no column exists
    """
    # break an input line into a list data type for column-by-column indexing
    line_to_list = line.split()
    try:
        column_entry = line_to_list[column_index-1]
        if DEBUG:
            print("Data in column #%s = %s" % (column_index, column_entry))
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

def find_star_column_index_from_table(file, table_title, column_name, VERBOSE = False):
    """
    Example: 
    ------
    ```
    ## Get the execution path of this script so we can find local modules
    script_path = os.path.dirname(os.path.abspath(sys.argv[0]))

    ## Try to import the module 
    try:
        sys.path.append(script_path)
        import star_handler 
    except :
        print(" ERROR :: Check if star_handler.py script is in same folder as this script and runs without error (i.e. can be compiled)!")

    star_handler.find_star_column_index_from_table('example.star', 'data_', '_rlnMicrographName')
    ```
    """
    TABLE_START, HEADER_START, DATA_START, DATA_END = get_table_position(file, table_title, DEBUG = True)
    column_index = -1
    with open(file, 'r') as f :
        line_num = 0
        for line in f :
            line_num += 1
            ## check if we are in range of the header
            if line_num < HEADER_START or line_num >= DATA_START:
                continue

            line = line.strip() # remove empty spaces around line
            ## avoid empty lines 
            if len(line) <= 0:
                continue

            ## extract column number for micrograph name
            if column_name == line.split()[0] :
                column_index = int(line.split()[1].replace("#",""))

    ## handle error case where input .STAR file is missing a necessary rlnColumn type
    if column_index < 0 :
        print(" ERROR: Input .STAR file: %s, is missing a column for: %s" % (file, column_name) )
        exit()
    else:
        if VERBOSE:
            print(" find_star_column_index_from_table :: ")
            print(" --------------------------------")
            print("  %s > #%s" % (column_name, column_index))
            print(" --------------------------------")

    return column_index

def get_column_values_from_table(file, table_title, column_name, VERBOSE = False):
    """
    WIP
    """
    TABLE_START, HEADER_START, DATA_START, DATA_END = get_table_position(file, table_title, DEBUG = VERBOSE)
    column_index = find_star_column_index_from_table(file, table_title, column_name, VERBOSE = VERBOSE)
    column_values = []
    with open(file, 'r') as f :
        line_num = 0
        for line in f :
            line_num += 1
            ## check if we are in range of the header
            if line_num < DATA_START or line_num > DATA_END:
                continue

            line = line.strip() # remove empty spaces around line
            ## avoid empty lines 
            if len(line) <= 0:
                continue

            ## extract value at the target column index 
            current_val = get_star_data(line, column_index, DEBUG = VERBOSE)
            if current_val != False:
                column_values.append(current_val)


    ## handle error case where input .STAR file is missing a necessary rlnColumn type
    # if column_index < 0 :
    #     print(" ERROR: Input .STAR file: %s, is missing a column for: %s" % (file, column_name) )
    #     exit()
    # else:
    if VERBOSE:
        print(" get_column_values_from_table :: ")
        print(" --------------------------------")
        print(" Column name = ", column_name)
        for v in column_values:
            print("      %s" % v)
        print(" --------------------------------")


    return column_values

# ## example script to read a star file for specific entries 
#     with open(fname, 'r') as f :
#         parsed = []
#         line_num = 0
#         for line in f :
#             line_num += 1
#             ## ignore empty lines
#             if len(line.strip()) == 0 :
#                 continue
#             ## start working only after the header length
#             if DATA_END >= line_num > DATA_START - 1:
#                 print(" line == ", line_num, line)
#                 # mic_name = get_star_data(line, COLUMN_MIC_NAME)
#                 mic_name = os.path.splitext(remove_path(get_star_data(line, COLUMN_MIC_NAME)))[0]
#                 dZ_U = float(get_star_data(line, COLUMN_dZ_U))
#                 dZ_V = float(get_star_data(line, COLUMN_dZ_V))

#                 dZ_avg = ((dZ_U + dZ_V) / 2)/10000

#                 parsed.append((mic_name, dZ_avg))

if __name__ == "__main__":
    import sys 

    print(" Testing star_handler functions:")

    cmd_line = sys.argv
    star_file = ''
    for cmd in cmd_line:
        if '.star' in cmd:
            star_file = cmd

    if len(star_file) <= 5:
        print(" No star file supplied, please point to one on the command line for testing")
        print(" e.g.   $ star_handler test.star")
        exit()

    print(" --------------------------------")
    print(" Test file: ", star_file)
    print(" --------------------------------")

    # get_star_columns_from_table(star_file, 'data_', VERBOSE = True)
    # find_star_column_index_from_table(star_file, 'data_', '_filamentDiameterAngstroms', VERBOSE=True)
    get_column_values_from_table(star_file,'data_','_filamentDiameterAngstroms', VERBOSE = True)

