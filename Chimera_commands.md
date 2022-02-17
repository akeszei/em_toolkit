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
