# star_file_processing
A series of scripts to manipulate data from star files for various purposes:

<b>relion_to_cistem_coords.py</b> = For an input RELION coordinate file and initialized cistem sqlite .DB file, return a coordinate file suitable for import into cistem. The main steps of this script are to read the .DB file and associate each RELION particle coordinate with the correct micrograph .DB ID number. Run script with three input variables:
> relion_to_cistem_coords.py  INPUT_particles.star  INPUT_project.db  ang_pix
-------
<b>select_into_boxfiles.py</b> = A small script to read in a .STAR file with a list of particles, their coordinates, and their associated micrographs to print out \*.box files. The written purpose of this script was to take refined coordinates of particles after an initial 2D classification and return those coordinates into a particle picking program, such as crYOLO, to improve the quality of the learned model. Run script with one input variable:
> select_into_boxfiles.py  particles.star

<b>select_into_manpick_file.py</b> = A script to take a .STAR file with particles and return their coordinates in a file format suitable for direct use in a RELION ManualPick job. This allows the user to select classes of good particles and return to each image to see what those particles looked like in the raw micrograph. Run with one input variable:
> select_into_manpick_file.py particles.star
