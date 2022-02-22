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

> **Volume Viewer > Features > ** toggle  **Zone**

Once open, you can then choose a radius size and click `Zone`. 
