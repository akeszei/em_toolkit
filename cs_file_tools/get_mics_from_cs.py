#!/usr/bin/env python


def load_data_from_cs_file(fname):
    print(" Loading cs file: %s" % cs_fname)
    cs_data = np.load(cs_fname)
    print(" ... %s entries found" % len(cs_data))
    return cs_data

def get_mics_from_cs_data(cs_data):
    mics = []

    for entry in cs_data:
        for item in entry:
            ## convert to a string type for matching  
            item = str(item)
            if "patch_aligned.mrc" in item:
                mic = item.split("/")[-1]
                mics.append(mic)
                ## the micrograph name can appear multiple times in an entry, so break out of the loop early as soon as the first match is found 
                break

    print(" >> %s mics extracted from cs file" % len(mics))
    return mics

def write_list_to_file(list_obj, out_fname = "mics.txt"):
    with open(out_fname, 'a') as f:
        for item in list_obj:
            f.write("%s\n" % item) 
    return 

if __name__ == '__main__':
    import numpy as np
    import sys

    cs_fname = sys.argv[1]

    cs_data = load_data_from_cs_file(cs_fname)
    mics = get_mics_from_cs_data(cs_data)

    write_list_to_file(mics)

