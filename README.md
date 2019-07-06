# star_file_processing
A series of scripts to manipulate data from star files for various purposes

> <b>relion_to_cistem_coords.py</b> = For an input RELION coordinate file and initialized cistem sqlite .DB file, return a coordinate file suitable for import into cistem. The main steps of this script are to read the .DB file and associate each RELION particle coordinate with the correct micrograph .DB ID number. 
