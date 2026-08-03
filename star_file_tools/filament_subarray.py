#!/usr/bin/env python3

from dataclasses import dataclass
import matplotlib.pyplot as plt
import numpy as np
import starfile
import os, sys


@dataclass
class Parameters:
    mrc_dimension_x: int = 4096
    mrc_dimension_y: int = 4096
    mrc_angpix: float = 2.0 # Angstroms / pixel 
    distance_between_picks: float = 80 # Angstroms 
    input_starfile_path: str = ""
    filament_diameter_px: int = 1132

    def mrc_dimensions(self):
        return [self.mrc_dimension_x, self.mrc_dimension_y]

    def pixel_distance(self):
        return int(self.distance_between_picks / self.mrc_angpix)

    def assign_starfile(self, f):
        ## sanity check we did not already have a star file assigned 
        if self.input_starfile_path != '':
            print(" !! ERROR :: More than one star file was detected as input! (e.g. %s, %s)" % (self.input_starfile_path, f))
            exit()
        else:
            ## check the star file input exists 
            if os.path.exists(f):
                self.input_starfile_path = f
                print(" Assigned input star file path: ", self.input_starfile_path)

            else:
                print(" !! ERROR :: Input star file (%s) does not exist! Check path carefully " % f)
                exit()
        return 

    def usage(self):
        print("================================================================================================================")
        print(" For a given manually picked .star file containing filament start/end coordinates, return a new .star file")
        print(" containing an array of coordinates along the filament axis sampling out to a given diameter at a given")
        print(" spacing distance:")
        print(" Usage:")
        print("    $ filament_subarray.py  manualpick.star")
        print(" Practical example:")
        print("    $ cd new_dir")
        print("    $ for m in ../*manualpick.star; do filament_subarray.py  $m  --angpix 2  --spacing 160 --diameter 2250  ")
        print(" Options:")
        print("    --angpix (2) :: pixel size of the raw micrograph  ")
        print("    --spacing (80) :: spacing (in Angstroms) between coordinates ")
        print("    --diameter (2250) :: diameter of the filament (in Angstroms) that we need to sample ")
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
                    self.assign_starfile(cmd)

            ## parse the input angpix  
            if cmd == '--angpix':
                try:
                    self.mrc_angpix = float(cmdline[i + 1])
                    print(" Assigned angpix value = ", self.mrc_angpix)
                except:
                    print(" ERROR :: Could not assign angpix value given ")


        ## only run the next flags after we have assigned an angpix value   
        for i in range(len(cmdline)):
            cmd = cmdline[i]

            if cmd == '--spacing':

                try:
                    self.distance_between_picks = int( float(cmdline[i + 1]) / self.mrc_angpix)
                    print(" Assigned inter-coordinate spacing of %s Ang (%s pixels)" % (float(cmdline[i + 1]), self.distance_between_picks ))
                except:
                    print(" ERROR :: Could not assign spacing value given ")
                

            if cmd == '--diameter':

                try:
                    self.filament_diameter_px = int( float(cmdline[i + 1]) / self.mrc_angpix)
                    print(" Assigned filament diameter to %s Ang (%s pixels)" % (float(cmdline[i + 1]), self.filament_diameter_px))
                except:
                    print(" ERROR :: Could not assign diameter value given: ", int( float(cmdline[i + 1]) / self.mrc_angpix))

        return 

@dataclass
class Filament:
    start_pixel_x: int
    start_pixel_y: int

    end_pixel_x: int
    end_pixel_y: int

    diameter: int # pixels

    def set_start_coords(self, x, y):
        self.start_pixel_x = x
        self.start_pixel_y = y

    def set_end_coords(self, x, y):
        self.end_pixel_x = x
        self.end_pixel_y = y

    def start(self):
        return [self.start_pixel_x, self.start_pixel_y]

    def end(self):
        return [self.end_pixel_x, self.end_pixel_y]

    def norm(self):
        position_vector = [self.end_pixel_x - self.start_pixel_x, self.end_pixel_y - self.start_pixel_y]
        return np.linalg.norm(position_vector) 

    def unit_vector(self):
        position_vector = [self.end_pixel_x - self.start_pixel_x, self.end_pixel_y - self.start_pixel_y]
        return position_vector / np.linalg.norm(position_vector) 

    def orthogonal_unit_vector(self, v):
        # Swap x and y, and negate one axis
        orth_v = np.array([-v[1], v[0]]) 
        return orth_v

def in_range(v, x, y):
    """
    PARAMETERS
        v = coordinate position 
        x = maximum value in first coordinate 
        y = maximum value in second coordinate 
    """
    ## check the coord is in bounds of the image
    if 0 > v[0] or v[0] > x:
        return False 
    elif 0 > v[1] or v[1] > y:
        return False 
    else:
        return True

def get_filaments(star_file, params):
    filaments = []

    star_df = starfile.read(star_fname)

    ## sanity check we have enough points to complete all filaments
    if len(star_df) % 2 != 0:
        print(" WARNING : There is an odd number of coordinates, meaning we have an incomplete filament in this file:", star_fname)
        print("           Final coordinate will be ignored.")

    for row in star_df.itertuples():
        # print(row.Index, row.rlnCoordinateX)
        # determine if this point is the start of a filament
        if row.Index % 2 == 0:
            print(" filament start = ", row.rlnCoordinateX, row.rlnCoordinateY)
            FILAMENT_START = [row.rlnCoordinateX, row.rlnCoordinateY]
        else:
            print(" filament end = ", row.rlnCoordinateX, row.rlnCoordinateY)
            FILAMENT_END = [row.rlnCoordinateX, row.rlnCoordinateY]
            new_filament = Filament(start_pixel_x=FILAMENT_START[0], start_pixel_y=FILAMENT_START[1], end_pixel_x=FILAMENT_END[0], end_pixel_y=FILAMENT_END[1], diameter=params.filament_diameter_px)
            # new_filament.set_start_coords(FILAMENT_START)
            # new_filament.set_end_coords(FILAMENT_END)
            filaments.append(new_filament)

    return filaments

def get_subfilament_coordinates(f, params):
    """
    For a given Filament object & pixel sampling rate (distance) return an array of points defined by that sampling & the filament diameter values.
    PARAMETERS
        f = Filament() object 
        params = Parameters() object 
    RETURNS
        p = list() of particle coordinates that make up the subfilament array 
    """
    p = list()
    dims = params.mrc_dimensions() # [max_x, max_y]
    max_x = dims[0]
    max_y = dims[1]

    ## first find out how many steps we need to take along the filament based on how finely we want to sample it
    steps = int(f.norm() / params.pixel_distance())
    step_size = params.pixel_distance() 

    ## calcualte the unit vector of the filament
    unit_vec = f.unit_vector()
    ## calculate the orthogonal vector fo he main filament
    ortho_vec = filament.orthogonal_unit_vector(unit_vec)

    count = 0
    for i in range(steps + 1):
        ## walk along the main filament axis and pick particles based on the target pixel spacing 
        filament_shift = unit_vec * step_size * i
        shift_origin = f.start()
        v = filament_shift + shift_origin
        if in_range(v.astype(int), max_x, max_y):
            ## append the the main filament coordinates to the data list
            count += 1 
            # print(f"\r Processing coordinate #%s" % count, end="")
            p.append(v.astype(int))

        ## at each step, also plot along the orthogonal directions until we reach the filament radius 
        orthogonal_steps = int( ( f.diameter / 2) / step_size )
        for j in range(orthogonal_steps + 1): 
            if j == 0:
                continue 
            ## calculate the upper and lower orthogonal points
            v_ortho_plus = v + ortho_vec * step_size * j
            v_ortho_minus = v + ortho_vec * step_size * j * -1 
            if in_range(v_ortho_plus.astype(int), max_x, max_y):
                p.append(v_ortho_plus.astype(int))
                count += 1
            if in_range(v_ortho_minus.astype(int), max_x, max_y):

                p.append(v_ortho_minus.astype(int))
                count += 1

            # print(f"\r Processing coordinate #%s" % count, end="")

    # print("")
    return p

def plot_points(filaments, coords):
    fig, ax = plt.subplots()

    for filament in filaments:
        ## plot the filament and coordinates
        plt.plot(*zip(*[filament.start(), filament.end()]), color=color, linestyle='--', zorder=1)
        for point in coords:
            ax.scatter(point[0], point[1], c='tab:purple', label=color, alpha=0.9, edgecolors='none')

    # ax.legend()
    ax.grid(True)
    plt.axis('equal') ## force equal aspect ratio between x & y axes to better see orthogonality 
    plt.show()

    return 

def write_manpick_file(input_star_path, coordinates):
    """
    Write out new star file, inheriting the name of the input file, with the array of coordinates
    PARAMETERS
        input_star_path = str(), name of the star file input 
        coordinates = list(), list of points to write into the star file  
    """
    ## write the output star file in the current working directory using the same name as the input star file 
    output_fname = os.path.basename(input_star_path)

    with open('%s' % (output_fname), 'w' ) as f :
        f.write("\n")
        f.write("data_\n")
        f.write("\n")
        f.write("loop_\n")
        f.write("_rlnCoordinateX #1\n")
        f.write("_rlnCoordinateY #2\n")
        f.write("_rlnParticleSelectionType #3\n")
        f.write("_rlnAnglePsi #4\n")
        f.write("_rlnAutopickFigureOfMerit #5\n")

    for c in coordinates:
        with open('%s' % (output_fname), 'a' ) as f :
            x = c[0]
            y = c[1]
            f.write("%s\t%s\t2\t-999.0\t-999.0\n" % (x, y))

    print(" Written file: %s, with %s coordinates" % (output_fname, len(coordinates)))
    return 

if __name__ == "__main__":

    params = Parameters()

    params.parse_cmdline(sys.argv)

    star_fname = params.input_starfile_path

    ## find all filament coordinates in the given .star file 
    filaments = get_filaments(star_fname, params)    

    color = 'tab:blue'

    coordinates = list() ## this is the list of all coordinates from all filaments

    ## generate an array of points along the filament based on the spacing value & pixel size set in the Parameters object 
    for filament in filaments:
        subfilament_coordinates = get_subfilament_coordinates(filament, params)
        ## repackage the coordinates from the list above into a master list in case we have more than one filament we need to combine points for in a micrograph
        for c in subfilament_coordinates:
            coordinates.append(c)

    ## Can sanity check results by plotting the filament axis and the array of points around it 
    # plot_points(filaments, coordinates)

    ## print out the new .star file with the array of coordinates 
    write_manpick_file(star_fname, coordinates)
