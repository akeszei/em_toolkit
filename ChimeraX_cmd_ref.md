
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

