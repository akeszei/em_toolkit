#!/usr/bin/env python3

#region Imports & globals
from dataclasses import dataclass, field
import starfile
import os, sys, shutil
import xml.etree.ElementTree as ET
import pandas as pd
#endregion 


#region General functions 
def parse_xml(fname):
    ## open the XML file into memory for all functions to use 
    xml_string = open(fname, "r", encoding="utf-8").read()
    xml_tree = ET.fromstring(xml_string)

    return xml_tree

#endregion 

#region Parameters class
"""
Parameters class reads the command line and is the object reference for all options
"""
@dataclass
class Parameters:
    input_starfile_path: str = ""
    input_xmlfile_path: str = ""


    def usage(self):
        print("================================================================================================================")
        print(" Read a warp tiltseries XML file and import the refined values (e.g. after miss-alignment) into an exising ")
        print(" RELION tilt_series star file:")
        print(" Usage:")
        print("    $ update_relion_ts_star_from_warp_xml.py  /path/to/tilt_series/<tomo>.star  /path/to/warp_tiltseries/<tomo>xml")
        # print(" Options:")
        # print("         --angpix (2) :: pixel size   ")
        # print("               --plot :: show a plot of tilt series from warp & relion")
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

            ## look for a .xml file 
            if len(cmd) > len('.xml'):
                if cmd[-len('.xml'):].lower() == '.xml':
                    self.assign_xmlfile(cmd)

        return 

    def __str__(self):
        return f"""
    Parameters:
    ----------------
        star file = {self.input_starfile_path}
         xml file = {self.input_xmlfile_path}
    ----------------
"""

    def assign_xmlfile(self, f, VERBOSE=False):
        ## sanity check we did not already have a star file assigned 
        if self.input_xmlfile_path != '':
            print(" !! ERROR :: More than one xml file was detected as input! (e.g. %s, %s)" % (self.input_xmlfile_path, f))
            exit()
        else:
            ## check the file input exists 
            if os.path.exists(f):
                self.input_xmlfile_path = f
                if VERBOSE: print(" Assigned input xml file path: ", self.input_xmlfile_path)

            else:
                print(" !! ERROR :: Input xml file (%s) does not exist! Check path carefully " % f)
                exit()
        return 

    def assign_starfile(self, f, VERBOSE=False):
        ## sanity check we did not already have a star file assigned 
        if self.input_starfile_path != '':
            print(" !! ERROR :: More than one star file was detected as input! (e.g. %s, %s)" % (self.input_starfile_path, f))
            exit()
        else:
            ## check the star file input exists 
            if os.path.exists(f):
                self.input_starfile_path = f
                if VERBOSE: print(" Assigned input star file path: ", self.input_starfile_path)

            else:
                print(" !! ERROR :: Input star file (%s) does not exist! Check path carefully " % f)
                exit()
        return 

#endregion

@dataclass
class TiltSeriesData:
    nominal_tilt: list[float] = field(default_factory=list) 
    # dZ: list[float] = field(default_factory=list) ## rlnTomoNominalDefocus (maybe not useful to update this? rather U and V?)
    x_shift: list[float] = field(default_factory=list) ## rlnTomoXShiftAngst | AxisOffsetX
    y_shift: list[float] = field(default_factory=list) ## rlnTomoYShiftAngst | AxisOffsetY
    z_rot: list[float] = field(default_factory=list) ## rlnTomoZRot | AxisAngle
    
    VERBOSE: bool = True

    def parse_warp_xml(self, xml_fpath):
        # if self.VERBOSE: print(" parse xml file: ", xml_fpath)
        xml_tree = parse_xml(xml_fpath)

        for elem in xml_tree.iter():
            xml_section = elem.tag
            section_attributes = elem.attrib 
            
            sections_w_text_data = ['AxisAngle', 'AxisOffsetX', 'AxisOffsetY']
            if xml_section == 'AxisAngle':
                self.z_rot = [float(x) for x in elem.text.split()]

            if xml_section == 'AxisOffsetX':
                self.x_shift = [float(x) for x in elem.text.split()]

            if xml_section == 'AxisOffsetY':
                self.y_shift = [float(x) for x in elem.text.split()]

            if xml_section == 'Angles':
                self.nominal_tilt = [float(x) for x in elem.text.split()]


            # if xml_section == 'CTF':
            #     elem.get('')

        return 

    def parse_relion5_star(self, star_fpath):
        # if self.VERBOSE: print(" parse star file:, ", star_fpath)

        df = starfile.read(star_fpath)

        self.x_shift = df['rlnTomoXShiftAngst'].astype(float).tolist()
        self.y_shift = df['rlnTomoYShiftAngst'].astype(float).tolist()
        self.z_rot = df['rlnTomoZRot'].astype(float).tolist()
        self.nominal_tilt = df['rlnTomoNominalStageTiltAngle'].astype(float).tolist()
        return 

    def set_x_shift(self, l):
        ## sanity check the input list is the same size as the existing length of tilts 
        num_tilts = len(self.nominal_tilt)
        num_input_values = len(l)
        if l == num_tilts:
            self.x_shift = l
        else:
            print(" ERROR :: Input values for X shift (%s) are not the same number as expected number of tilts (%s)! " % (num_input_values, num_tilts))
            sys.exit()
        if self.VERBOSE: print(" Updated X shifts")
        return 

    def set_y_shift(self, l):
        ## sanity check the input list is the same size as the existing length of tilts 
        num_tilts = len(self.nominal_tilt)
        num_input_values = len(l)
        if l == num_tilts:
            self.y_shift = l
        else:
            print(" ERROR :: Input values for Y shift (%s) are not the same number as expected number of tilts (%s)! " % (num_input_values, num_tilts))
            sys.exit()
        if self.VERBOSE: print(" Updated Y shifts")
        return 


    def as_df(self):
        """
        Return the tiltseries data as an organized pandas dataframe 
        """
        d = {
            "nominal_tilt" : self.nominal_tilt,
            "x_shift" : self.x_shift, 
            "y_shift" : self.y_shift,
            "zrot" : self.z_rot 
        }

        df = pd.DataFrame(d)
        return df

    def __str__(self):
        return f"""
    TiltSeriesData:
    ----------------
{self.as_df().to_string(index=False, col_space=15)}
"""



if __name__ == "__main__":
    params = Parameters()
    params.parse_cmdline(sys.argv)
    print(params)

    # ## Example: loading star & xml files, then comparing the differences 
    # ts = TiltSeriesData()
    # ts.parse_relion5_star(params.input_starfile_path)

    # ts2 = TiltSeriesData()
    # ts2.parse_warp_xml(params.input_xmlfile_path)

    # print(ts.as_df() - ts2.as_df())
    # ## end


    ## Example: loading star & xml files, then updating the star values from the xml values and writing out a file 
    ts_relion = TiltSeriesData()
    ts_relion.parse_relion5_star(params.input_starfile_path)
    ts_warp = TiltSeriesData()
    ts_warp.parse_warp_xml(params.input_xmlfile_path)

    ts_relion.x_shift = ts_warp.x_shift
    ts_relion.y_shift = ts_warp.y_shift
    ts_relion.z_rot = ts_warp.z_rot

    ## confirm the values are identical by getting a zero table when finding the difference
    difference_df = ts_relion.as_df() - ts_warp.as_df()
    difference_score = difference_df.to_numpy().sum()
    if difference_score > 0:
        print(" ERROR :: There was a problem remapping the warp data into the relion file, here is the difference dataframe:")
        print(difference_df)
        sys.exit()

    ## if the above passes, then we are certain we can replace the values in the original star file 
    ## copy the original star file as a back up
    root, fname = os.path.split(params.input_starfile_path)
    backup_fname = fname + ".bak"
    shutil.copy(params.input_starfile_path, os.path.join(root, backup_fname))
    ## overwrite the original star file 
    relion_star = starfile.read(params.input_starfile_path)
    relion_star["rlnTomoXShiftAngst"] = ts_warp.x_shift
    relion_star["rlnTomoYShiftAngst"] = ts_warp.y_shift
    relion_star["rlnTomoZRot"] = ts_warp.z_rot
    starfile.write(relion_star, params.input_starfile_path)
    print("                 backup file written: ", os.path.join(root, backup_fname))
    print("        updated alignment written to: ", params.input_starfile_path)
