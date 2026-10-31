#!/usr/bin/env python3

#region Imports & globals
from dataclasses import dataclass, field
import starfile
import os, sys, shutil
import pandas as pd
#endregion 


#region General functions 
def recenter_coordinates(input_starfile, output_starfile, AS_PICKS, DEBUG = True):
    star_data = starfile.read(input_starfile)
    """
    starfile read will pack the data into the following structure:
        {
            'table_name'   : df , 
            ...
            'table_name_n' : df
        }
    """
    
    ## unpack the optics group & associated pixel size data first into an easy to retrieve data structure 
    optics_df = star_data['optics']
    optics_pixel_ref = {} # { 'optics_number' : angpix, ... }
    for i, row in optics_df.iterrows():
        opticsGroup = row['rlnOpticsGroup']
        pixelSize = row['rlnImagePixelSize']
        optics_pixel_ref[str(opticsGroup)] = pixelSize

    if DEBUG: print(" Optics particle pixel size table: \n \t", optics_pixel_ref)

    ## iterate over the particle list and generate an updated list of pd.Series data  
    particles_df = star_data['particles']
    new_particles_series_list = []
    for i, row in particles_df.iterrows():
        shifted_particle = shift_particle(row, optics_pixel_ref)
        ## when appending, convert it to a single column DataFrame and transpose it to a single row 
        new_particles_series_list.append(shifted_particle.to_frame().T)

    ## initialize empty DataFrame with expected columns from the reference DataFrame
    new_particles_df = pd.DataFrame(columns=particles_df.columns)
    ## populate it with list of rows created in the above loop
    new_particles_df = pd.concat(new_particles_series_list, axis=0)


    print(new_particles_df.iloc[0])

    return 

def shift_particle(p, pixel_reference_table, DEBUG = False):
    """
    p = pd.Series of particle data extracted from a data star file
    """
    ## ref pixel size 
    current_particle_angpix = pixel_reference_table[str(p['rlnOpticsGroup'])]

    ## x 
    current_particle_x = p['rlnCoordinateX']
    current_particle_x_shift = p['rlnOriginXAngst'] / current_particle_angpix
    recentered_x = current_particle_x - current_particle_x_shift

    ## y 
    current_particle_y = p['rlnCoordinateY']
    current_particle_y_shift = p['rlnOriginYAngst'] / current_particle_angpix
    recentered_y = current_particle_y - current_particle_y_shift

    ## z 
    current_particle_z = p['rlnCoordinateZ']
    current_particle_z_shift = p['rlnOriginZAngst'] / current_particle_angpix
    recentered_z = current_particle_z - current_particle_z_shift

    if DEBUG:
        print(" Recentering X coordinate :: \n \t   x coordinate = %s \n \t shift / angpix = %s / %s = %s  \n \t   recentered x = %s" % (current_particle_x, p['rlnOriginXAngst'], current_particle_angpix, current_particle_x_shift , recentered_x))
        print(" Recentering Y coordinate :: \n \t   y coordinate = %s \n \t shift / angpix = %s / %s = %s  \n \t   recentered y = %s" % (current_particle_y, p['rlnOriginYAngst'], current_particle_angpix, current_particle_y_shift , recentered_y))
        print(" Recentering Z coordinate :: \n \t   z coordinate = %s \n \t shift / angpix = %s / %s = %s  \n \t   recentered z = %s" % (current_particle_z, p['rlnOriginZAngst'], current_particle_angpix, current_particle_z_shift , recentered_z))

    ## update the Series with the shifted data 
    p['rlnCoordinateX'] = recentered_x
    p['rlnOriginXAngst'] = 0
    p['rlnCoordinateY'] = recentered_y
    p['rlnOriginYAngst'] = 0
    p['rlnCoordinateZ'] = recentered_z
    p['rlnOriginZAngst'] = 0

    return p 
#endregion 

#region Parameters class
"""
Parameters class reads the command line and is the object reference for all options
"""
@dataclass
class Parameters:
    input_starfile_path: str = ""
    output_starfile_name: str = ""
    AS_PARTICLES_STAR_FILE: bool = False


    def usage(self):
        print("================================================================================================================")
        print(" Read in a refined .STAR file from RELION 5 Refine3D or other job and recenter the particle coordinates")
        print(" based on the refined offsets. Can optionally choose to write out individual *_particles.star files")
        print(" for each tomogram to inspect the refined positions & orientations in a viewing software.")
        print(" Usage:")
        print("    $ recenter_subtomo_star.py  /path/to/run_data.star ")
        print(" Options:")
        # print("         --angpix (2) :: pixel size   ")
        print("          --o (*_recentered.star) :: choose a specific output file name")
        print("               --picks :: decompose output by individual tomogram as *_particles.star files suitable")
        print("                          for input into ChimeraX/AritaX or relion Picks annotation directory")
        print("================================================================================================================")
        sys.exit()
        return 

    def parse_cmdline(self, cmdline):

        ## cmd line minimally needs 3 inputs
        if len(cmdline) < 2:
            self.usage()

        ## first check for the help flag before proceeding 
        for i in range(len(cmdline)):
            if cmdline[i] in ['-h', '--h', '-H', '--H']:
                self.usage()
        
        ## iterate over every entry, looking for flags & files  
        for i in range(len(cmdline)):
            cmd = cmdline[i]

            ## look for a .star file 
            if len(cmd) > len('.star'):
                if cmd[-len('.star'):].lower() == '.star':
                    self.assign_input_starfile(cmd)

            ## parse the input angpix  
            if cmd == '--o':
                try:
                    self.output_starfile_name = cmdline[i + 1]
                except:
                    print(" ERROR :: Could not assign output star file ")

            ## parse the input angpix  
            if cmd == '--picks':
                self.AS_PARTICLES_STAR_FILE = True


        return 

    def __str__(self):
        if self.AS_PARTICLES_STAR_FILE:
            output_file = "<tomo>_particles.star"
        else:
            output_file = self.output_starfile_name
        return f"""
    Parameters:
    ------------------------------
           input star file = {self.input_starfile_path}
          output star file = {output_file}
    AS_PARTICLES_STAR_FILE = {self.AS_PARTICLES_STAR_FILE}
    ------------------------------
"""

    def check_inputs(self):
        if len(self.input_starfile_path) == 0:
            print(" ERROR :: No input .STAR file was provided")
            self.usage()

        return

    def assign_input_starfile(self, f, VERBOSE=False):
        ## sanity check we did not already have a star file assigned 
        if self.input_starfile_path != '':
            print(" !! ERROR :: More than one star file was detected as input! (e.g. %s, %s)" % (self.input_starfile_path, f))
            exit()
        else:
            ## check the star file input exists 
            if os.path.exists(f):
                self.input_starfile_path = f
                if VERBOSE: print(" Assigned input star file path: ", self.input_starfile_path)
                self.set_default_output_starfile()

            else:
                print(" !! ERROR :: Input star file (%s) does not exist! Check path carefully " % f)
                exit()
        return 

    def set_default_output_starfile(self): 
        if len(self.output_starfile_name) == 0:
            root, fname = os.path.split(self.input_starfile_path)
            basefname = os.path.splitext(fname)[0]
            new_fname = basefname + "_recentered.star"
            new_full_path = os.path.join(root, new_fname)
            self.output_starfile_name = new_full_path
        return 

   
#endregion




if __name__ == "__main__":
    params = Parameters()
    params.parse_cmdline(sys.argv)
    print(params)
    params.check_inputs()

    recenter_coordinates(params.input_starfile_path, params.output_starfile_name, params.AS_PARTICLES_STAR_FILE)



    # ## if the above passes, then we are certain we can replace the values in the original star file 
    # ## copy the original star file as a back up
    # root, fname = os.path.split(params.input_starfile_path)
    # backup_fname = fname + ".bak"
    # shutil.copy(params.input_starfile_path, os.path.join(root, backup_fname))
    # ## overwrite the original star file 
    # relion_star = starfile.read(params.input_starfile_path)
    # relion_star["rlnTomoXShiftAngst"] = ts_warp.x_shift
    # relion_star["rlnTomoYShiftAngst"] = ts_warp.y_shift
    # relion_star["rlnTomoZRot"] = ts_warp.z_rot
    # starfile.write(relion_star, params.input_starfile_path)

