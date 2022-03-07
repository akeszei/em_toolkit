
# UCSF Chimera quick reference

Commonly used (and oft forgotten!) commands & controls for easy driving in **UCSF Chimera** (https://www.cgl.ucsf.edu/chimera/). For full details of all commands, refer to [the index guide](https://www.cgl.ucsf.edu/chimera/current/docs/UsersGuide/framecommand.html).

## Accelerators 
Chimera allows the use of *keyboard accelerators*, which can allow the user to quickly open tools/windows using sequential keystrokes (see: [link](https://www.cgl.ucsf.edu/chimera/docs/ContributedSoftware/accelerators/alist.html)). To enable it for all future sessions you need to toggle it on:

> **Tools... > General Controls... > Keyboard Shortcuts >**  toggle **Enable keyboard shortcuts**

When enabled, you can quickly launch commonly used panels and activate the command line (you may need to re-focus Chimera to run sequential commands):

    mp
    sv
    cl

Note that `ac hc` will close the command line if it is active, so you can run other accelerators before turning it back on.

## Opening & viewing models
Pull a structure from rcsb.org and focus the camera on a specific residue of interest, with automatic clipping:

    open <PDB_ID>
    sel <Residue>
    focus sel; show sel
    color red sel; color byhetero sel
    represent bs sel 

Nomenclature for specifying a residue follow the form: 

> <model_ID> **:** <residue_range> **.** <chain_ID>

The selection can be a single residue (as demonstrated below) or a range (*i.e.* `#0:130-180.A` would select all resides on chain A from 130 to 180).

As an example, lets open a model, select a specific residue, then focus on it:

    open 1UBQ
    sel #0:48
    focus sel 

To make the side chain visible, we can show it and then change its appearance & color:

    show sel 
    represent bs sel 
    color red sel 
    color byhetero sel 

## Opening & viewing maps

Open your density map from local disc and adjust sampling rate & thresholding with preferred scene setup:

    volume <model_ID> step <n> level <y>
    background solid white; set silhouette; lighting reflectivity 0
    cofr models

The target volume can be chosen specifically, or if many volumes are loaded (say, after a 3D classification) and should be treated identically you can use the `all` keyword. For example a common command I always run is:

    volume all step 1 level 0.01 

I then re-run the command (use the arrow-up key to call back the previously submitted command) with different level values (thresholds) until I am happy. 

If many maps are open and should be compared side-by-side, we can array them simply by running:

    tile 

The maps can be returned to their initial origins by simply running:

    reset 

When working with models docked in maps, it is important to ensure the pivot point for each loaded model is at its corresponding origin via:

    cofr models

## Scene management

When honed in on a specific view, you can cache the position by name via:

    savepos <name>

This will allow you to return to that view via:

    reset <name> 

The name of all cached positions can be found via:

    savepos list 
This functionality can be useful to quickly jump between multiple active sites/other regions when trying to assess different maps. 

## Advanced functionalities

Some examples of more advanced uses of chimera for specific cases:

### Color density by docked model
After docking a model/ligand, you may want to have the density around the model colored in a way that shows the density that the model occupies. This is easily achieved by first coloring the model a solid color, then applying the color to a volume using a specific range cutoff, and finally recoloring the model back to the desired heteroatom color:

    sel <model/range/chain/ligand>
    color <magenta/blue/red/other> sel 
    scolor <density_model_ID> zone sel range <n, Angstroms>
    color byhetero sel 
    transparency 30 <density_model_ID>

### Show density around selection only
For viewing/interpretability, it can be necessary to only show density around a selected region (i.e. a small ligand). This is easily achieved by making your selection and then using the *Volume Viewer* panel to only show density around the selection by a given distance by the zone menu:

> **Volume Viewer > Features >** toggle  **Zone**

Once open, you can then choose a radius size and click `Zone`. 

### Docking symmetry-related molecules 
In cases where you have a density where you have docked a model and wish to copy that model to all other symmetry-related densities it is most accurate to use symmetry commands in chimera to duplicate the model.

First, we need to prepare a feature at the center of the box that we can use as a landmark for symmetry operations:

    measure center #<density_id> mark true
This will create a new model entry we can use in the symmetry operation. 

    sym #<model> group <point_group> center #<center> coordinateSystem #<center> 

 In some cases, we may need to explicitly specify which axis to use for an operator by adding the `axis <x,y, or z>` flag as well. 

For example, a protein with D3 symmetry where the 2-fold lies on the alternate y-axis (recall, 3-fold is along z-axis by convention, and 2-fold is assumed to be along x-axis) would need to run the symmetry commands in two steps, first use the defaults along the 3-fold and then save the models and used the in a second command using the `axis y` flag to set the correct 2-fold orientation:

    sym #<model> group c3 center #<center> coordinateSystem #<center>
    sym #<model> group c2 center #<center> coordinateSystem #<center> axis y

### Preparing volumes from models 
`Chimera` is incredibly useful for quickly generating `.mrc` volumes from atomic models (eg, `.pdb` files) that can be used as initial maps or to generate masks for use in processing software. A volume is easily created from a model or user-defined selection by using the `molmap`function:

    molmap <model, or selection> <resolution>

The output density can then be saved using the `Volume Viewer` widget, making sure your volume-of-interest is selected (highlighted white):

> **Volume Viewer > File > Save map as...**

For example, here is a command for generating an 8 Ang density around a selected region:

    molmap sel 8

If you have a density from your processing software already open, you can immediately dock the created density into that box at the same sampling resolution (useful for generating masks around specific regions):

    vop resample #<molmap_density> onGrid #<processing_density>

The output density can then be saved as above and used directly to make a mask (apply soft edges) or as a map. 
