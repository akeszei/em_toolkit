

# UCSF ChimeraX quick reference  
Common commands used for structural analysis are shown here for easy reference.

### Prepare an initial volume from an atomic model
Load a model and prepare a density, shifting it to a zero origin:
```
open <pdb_id>
molmap <model_id> <res>
volume <molmap_id> origin 0,0,0
```
Prepare an empty box with the correct dimensions and pixel size:
```
vop new size <box_size> gridSpacing <apix> origin 0,0,0

// example for a box size of 200 px, 1.03 Ang/px:
vop new size 200 gridSpacing 1.03 origin 0,0,0

// note you may need to adjust the threshold to see the box
```
Finally, resample the molmap into the box as usual:
```
vop resample <molmap_id> onGrid <empty_box_id>
```
The resulting resampled volume can be saved to disk via:
```
save /path/to/disk models <resampled_id> 

// example on Windows PC:
save C:\Users\Alexander\Desktop\test.mrc models #2
```

### Segment a volume around a selected model
`volume zone <map> near <selection> range <ang dist>`
For example:
`volume zone #1 near #2/D range 3`
Revert to full volume with
`volume unzone <map>`

### Auto focus camera to selection
`view <selection> `

### Create volume from atomic model
Command works as usual from regular Chimera:
```
molmap  <model_id>  <res> 

// example making a density from an atomic model
molmap #1 10 
```


### Dock volume into box
`vop resample <volume> onGrid <box>` works as usual from Chimera

### Color density by nearby model
WIP

### Scene management
When honed in on a specific view, you can cache the position by name via:

    view name <name>

This will allow you to return to that view via its unique name:

    view <name>

The name of all cached positions can be found via:

    view list
This functionality can be useful to quickly jump between multiple active sites/other regions when trying to assess different maps.

### Figure styles
#### Cartoon models with clear edges
Ambient occlusion with thick coil diameter and heavy stroke/outline can highlight cartoon regions especially when surrounded by other subunits.

`preset 1; lighting soft `

`show cartoon; hide atoms`

`graphics silhouettes width 5; cartoon style coil thickness 1`

#### Cartoon slab with specific side chains
When viewing side chains we want to color by heteroatom type and can improve visibility by making the side chains a bit thicker than default.

`preset 1; lighting soft `

`show cartoon; hide atoms`

`graphics silhouettes width 2; color byHetero; style stick; size stickRadius 0.25`

`view sel`  (adjust camera and slab thickness manually)
