# Chimera command line cheat-sheet

Commonly used (and oft forgotten!) commands to easy driving in **UCSF Chimera** (https://www.cgl.ucsf.edu/chimera/). For full details of all commands, refer to: <https://www.cgl.ucsf.edu/chimera/current/docs/UsersGuide/framecommand.html>.

## Opening & viewing models
Pull a structure from rcsb.org and focus the camera on a specific residue of interest, with automatic clipping:

    open <PDB_ID>
    sel <Residue>
    focus sel; show sel
    color red sel; color byhetero sel
    represent bs sel 

Nomenclature for specifying a residue follow the form: 

> <model_ID>**:**<residue_range>**.**<chain_ID>

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

I then re-run the command (use the arrow-up key to call back the previously submitted command) with different level (thresholding) values until I am happy. 

If many maps are open and should be compared side-by-side, we can array them simply by running:

    tile 

The maps can be returned to their initial origins by simply running:

    reset 

When working with models docked in maps, it is important to ensure the pivot point for each loaded model is at its corresponding origin via:

    cofr models
