#!/usr/bin/env python3

## Author : A. Keszei 

"""
    Generate an authoritative beamshift list for all images in the EPU project directory useable by relion scripts mapping optics groups to .STAR files 
"""

## 2024-05-28: Adapted from compare_eer_xml.py 


#############################
#region     FLAGS
#############################
DEBUG = True

#endregion

#############################
#region     DEFINITION BLOCK
#############################


def remove_namespace(input_string = ''):
    """ By default convension, the names of XML headers for EPU files contains a lot of unnecessary
        information, this function aims to remove all that unnecessary text and return the header name
        alone. e.g.:
            {namespace}headerTitle {} -> headerTitle
    """
    if '{' in input_string:
        # print( "input str = ", input_string)
        output_sting = input_string.split('{')[1].split('}')[1]
        return output_sting
    else: 
        return input_string
    
    
def get_xml_tag(xml_tree, header):
    """
    PARAMETERS 
        xml_tree = xml.etree.ElementTree.Element object 
        header = str(); case insensitive string of the header we want to capture (e.g. 'beamtilt')
    RETURNS
        str(); the element tag we can use to search directly for the children values of that header 
    """
    for elem in xml_tree.iter():
        raw_elem = remove_namespace(elem.tag)
        if header.lower() == raw_elem.lower():
            # print(" >> ", elem.tag)
            return elem.tag
    print(" !! ERROR :: Could not find the header (%s) in the XML file, doublecheck it exists in the file (note: case insensitive)" % header)
    exit()

def get_beam_shift(xml_tree):
    search_header = 'beamshift'
    ## get the namespaced version of the expected tag (case insensitive)
    search_string = get_xml_tag(xml_tree, search_header)
    ## enable recursion with './/' leader attached to the search string 
    matches = xml_tree.findall('.//' + search_string)
    if len(matches) == 0:
        print(" !! ERROR :: Could not find the given header in the XML file: %s (note: search is case insensitive)" % search_header)
        return 
    x = None 
    y = None
    ## take first (and likely only) match retrieved by findall 
    for attrib in matches[0]:
        if 'x' in remove_namespace(attrib.tag).lower():
            x = float(attrib.text)
        if 'y' in remove_namespace(attrib.tag).lower():
            y = float(attrib.text)
    if x == None or y == None:
        print(" !! ERROR :: Could not find the x, y attributes for the given header: %s, confirm there is an x and y attribute for this header in the file!" % search_header)
        return 
    return x, y


def plot_points(points, clustering):
    """
    PARAMETERS
        points = list() of (x,y) tuples 
    """
    import matplotlib.pyplot as plt
    import matplotlib.cm as cm
    from matplotlib.colors import Normalize

    x, y, mic = zip(*points)
    # area = 4  # 0 to 15 point radii
    # plt.scatter(x, y)

    # cmap = cm.autumn
    # cmap = cm.hsv
    # cmap = cm.Dark2
    # cmap = cm.viridis
    # norm = Normalize(vmin=np.min(clustering), vmax=np.max(clustering))
    # label_colors = [cmap(norm(l)) for l in clustering]

    ## Set the color into 4 discrete steps to better see how clustering treats different tilts within a hole  
    cmap = cm.tab10
    norm = Normalize(vmin=0, vmax=4)
    label_colors = [cmap(norm(l%4)) for l in clustering]

    plt.scatter(x, y, c=label_colors, alpha=1)
    plt.show()
    return 

def parse_xml(fname):
    ## open the XML file into memory for all functions to use 
    xml_string = open(fname).read()
    xml_tree = ET.fromstring(xml_string)
    return xml_tree

def map_tilt_groups(dataset, grouping):
    mapped = []

    for i in range(len(dataset)):
        x, y, mic = dataset[i]
        group_id = grouping[i]
        # print(" tilt_%s, %s (%.3f, %.3f) "% (group_id, mic, x, y))
        mapped.append((mic, group_id))

    return mapped 

def write_tilt_groups(mapped_dataset, save_fname = 'shiftgroups.txt'):
    with open(save_fname, 'w') as f :
        ## unpack the dataset and write it to the file 
        for mic, group_id in mapped_dataset:
            f.write("%s  shift_%s\n" % (mic, str(group_id).zfill(3)))
    return 

#endregion





#############################
#region     RUN BLOCK
#############################

if __name__ == "__main__":

    import os
    import sys
    import glob 

    ## import element tree for XML parsing
    import xml.etree.ElementTree as ET 
    from datetime import datetime
    import numpy as np

    shifts = []
    for xml_file in glob.glob("*.xml"):
        # xml_fname = sys.argv[1]

        # print("")
        # print("=========================================================")
        # print(" Reading '%s' as XML file" % xml_file)
        # print("---------------------------------------------------------")
        
        xml_tree = parse_xml(xml_file)
        x, y = get_beam_shift(xml_tree)
        mic = os.path.splitext(xml_file)[0]
        # print(" %s :: beam shift = (%s, %s)" % (xml_file, x, y))
        shifts.append( [x, y, mic] )

    # print(shifts)

    ## Check the distance between a few points (use that to calculate the desired threshold? but can we figure out which 3 holes to compare?)
    # a = np.array([1.502, 3.33]).astype(np.float32)/100
    # b = np.array([-3.248, -0.89]).astype(np.float32)/100
    # c = np.array([1.38, -2.86]).astype(np.float32)/100
    # print(np.linalg.norm(a-b))
    # print(np.linalg.norm(a-c))
    # print(np.linalg.norm(b-c))

    from scipy.cluster.hierarchy import ward, fcluster
    from scipy.spatial.distance import pdist

    dist_matrix = pdist([[x, y] for x,y,z in shifts]) ## drop the third element of the input list dynamically to prepare input into pdist function which requires only a list of [ [x,y], ... ]
    linkage_matrix = ward(dist_matrix)
    cluster_matrix = fcluster(linkage_matrix, t = 0.04, criterion='distance') ## still need to figure out best threshold value, based on initial check most tilts are separated by ~ 0.05 or more units 

    # plot_points(shifts, cluster_matrix)

    mapped_dataset = map_tilt_groups(shifts, cluster_matrix) # returns [ ('img_name', tilt_group_#), ... ]

    write_tilt_groups(mapped_dataset)




#endregion