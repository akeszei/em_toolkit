#!/usr/bin/env python3

"""
    An iniial foray into working with .cs files. Commented functions are useful starting points for swapping
    data from one .cs file to another. 
"""

## 2023-03-22: Script started
## 2023-04-05: Stopped working on script since use case for which it was necessary was solved in a simpler way. Keep progress and make this script simply output details regarding an input cs file.

#############################
###     FLAGS/GLOBALS
#############################
DEBUG = True

#############################
###     DEFINITION BLOCK
#############################



def read_cs_data(dataset, headers_of_interest = []):
    """ 
    PARAMETERS
        dataset = numpy recarray, of the style created when opening a .cs file 
        headers_of_interest = list of headers we want to print, if empty will print all headers 

    RETURNS 
        header_dict = dictionary of form { 'header_name' : index }, useful for looking up specific columns for a data point for this given dataset later 
    """

    print(" cs recarray shape = ", dataset.shape)

    ## 1. Unpack the header data into a dictionary we can refer to later ( 'header_name' : index/column )  
    headers = get_cs_headers(dataset) ## dict ( 'header_name' : index/column, ... )
    
    print(" headers = ")
    for key in headers:
        print("   %s. %s" % (headers[key], key))

    ## if no explicit headers of interest were given, use all 
    if len(headers_of_interest) == 0:
        for header in headers:
            headers_of_interest.append(header) 

    ## 2. Show a few entries and their header values
    ## each entry in the main array represents one entry/micrograph/particle
    for i in range(len(dataset)):
        if i < 3:
            print(" ------------------------------")
            print(" Entry #%s" % i)
            for key in headers:
                header_name = key
                header_index = headers[key]
                if header_name in headers_of_interest:
                    print("    %s = %s" % (header_name, dataset[i][header_index]))

    print(" ------------------------------")
    print(" ...")
    return 

def get_data_from_cs_by_headers(dataset, target_headers):
    """
    RETURNS
        extracted_data = dict() of the form: 
            { UID1 : [ ('header name', value), ... ], ... }
    """
    extracted_data = {}

    ## 1. Unpack the header data into a dictionary we can refer to later ( 'header_name' : index/column )  
    headers = dataset.dtype.names ## 'headers' for each index position can be retrieved from the main array
    header_dict = {} 
    for i in range(len(headers)):
        header_dict[headers[i]] = i
    
    ## 2. iterate over the dataset and extract the values of interest 
    for i in range(len(dataset)):
        for key in header_dict:
            header_name = key
            header_index = header_dict[key]

            if header_name == 'uid':
                UID = dataset[i][header_index]
                extracted_data[UID] = []

            if header_name in target_headers:
                data_point = (header_name, dataset[i][header_index])
                extracted_data[UID].append(data_point)

    # print(extracted_data)

    return extracted_data

def get_cs_headers(dataset):
    ## Unpack the header data into a dictionary we can refer to later ( 'header_name' : index/column )  
    headers = dataset.dtype.names ## 'headers' for each index position can be retrieved from the main array
    header_dict = {} 
    for i in range(len(headers)):
        header_dict[headers[i]] = i
    return header_dict

def replace_data(dataset, input_data):
    """
    PARAMETERS 
        dataset = numpy recarray from cs file 
        input_data = dictionary of the form ( 'UID' : [ ('header', value), ... ] )
    """
    headers = get_cs_headers(dataset) ## dict ( 'header_name' : index/column, ... )
    UID_index = headers['uid']
    if DEBUG:
        print("UID index found at col = ", UID_index)
        
    ## iterate over each entry in the main array and use the input_data dictionary to look up new values 
    for i in range(len(dataset)):
        ## get the UID value for each entry first 
        UID = dataset[i][UID_index]
        ## check if UID is in input_data 
        if UID in input_data: 
            new_header_value_list = input_data[UID]
            # print(" UID %s has modified values -> %s" % (UID, new_header_value_list))
        else:
            print(" UID %s has no modified values to adjust")
            
        ## update the correct column for each data point 
        for update_header, update_value in new_header_value_list:
            ## find the index for the corresponding header 
            target_index = headers[update_header]

            if DEBUG: 
                print(" modifying %s :: %s -> %s" % (update_header, dataset[i][target_index], update_value))
                print( " ... are types preserved? %s -> %s" % (type(dataset[i][target_index]), type(update_value)))
            
            ## change the value of the datapoint at that index 
            dataset[i][target_index] = update_value 

    return dataset 


def save_cs(fname, dataset):
    with open(fname, mode='wb') as f:
        np.save(f, dataset)

    return 

#############################
###     RUN BLOCK
#############################

if __name__ == "__main__":
    import sys
    import numpy as np

    cs_file = sys.argv[1]

    ## hardcode the files for now:
    # cs_file = 'J38_exposures_ctf_estimated.cs'
    # cs_file2 = 'J39_exposures_ctf_estimated.cs'


    print("==================================================================")
    print("  Load cs file: %s" % cs_file)
    print("------------------------------------------------------------------")


    ## cs data is stored as a numpy structured array (recarrays), it can be opened with numpy 
    cs_dataset = np.load(cs_file)

    ## choose which headers we are interested in 
    # target_headers = ['uid', 'ctf/path', 'ctf/df1_A', 'ctf/df2_A', 'ctf/df_angle_rad', 'ctf/ctf_fit_to_A']

    ## an example, print out the metadata for a given entry
    # read_cs_data(cs_dataset, headers_of_interest = target_headers)
    read_cs_data(cs_dataset)

    ## we next need to open the other dataset and iterate over it to grab the relevant data we want to swap in... 
    # cs_dataset_2 = np.load(cs_file2)
    # extracted_data = get_data_from_cs_by_headers(cs_dataset_2, target_headers)

    # new_dataset = replace_data(cs_dataset, extracted_data)

    # save_cs('test_output.cs', new_dataset)

    # read_cs_data(np.load('test_output.cs'), headers_of_interest = target_headers)


    # ## ASIDE ON NUMPY STRINGS: 
    # ## a python string can be converted to np.bytes_ type by simply calling it with the .bytes_ method: 
    # a = 'a'
    # a = np.bytes_(a)    
    # print(a, type(a))
    # ## We can decode a np.bytes_ array back to a string by using the ptyhon builtin decode method:
    # a = a.decode('UTF-8')
    # print(a, type(a))
