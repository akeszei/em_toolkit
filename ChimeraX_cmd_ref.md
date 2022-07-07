

# UCSF ChimeraX quick reference  
Common commands used for structural analysis are shown here for easy reference.

### Segment a volume around a selected model
`volume zone <map> near <selection> range <ang dist>`
For example:
`volume zone #1 near #2/D range 3`
Revert to full volume with
`volume unzone <map>`

### Auto focus camera to selection
`view <selection> `

### Create volume from atomic model
`molmap` command works as usual from regular Chimera.

### Dock volume into box
`vop resample <volume> onGrid <box>` works as usual from Chimerma

### Color density by nearby model
WIP

### Scene management
WIP

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
