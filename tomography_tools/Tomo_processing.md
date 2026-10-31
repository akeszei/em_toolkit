# Tomography processing w/ WARP

## Prepare the dataset
Make a folder for processing and prepare the following structure
```sh
WARP_project/
          └── frames/
                  └── *.eer # raw movies from Tomo5 collection
                  └── ...GainReference.gain # gain file from Tomo5
          └── mdoc/
                  └── *.mdoc # mdoc file from Tomo5 collection
          └── warp_frameseries/ # folder for motion corrected stack
```


## Moving coordinates around

### IMOD 
If picking particles with `3dmod`, you can save the picks as a `.mod` file (you will need to set the picks to be single points via: `3dmod` > `Edit` > `Object` > `Type...` window and selecting `Scattered` as the `Object Type`). These picks can be moved over to `.star` format for use in `warp` or `relion` via `IMOD` helper functions:
```sh
model2point  <imod_picks>.mod  <imod_picks>.txt
imod_picks_to_relion.sh  <imod_picks>.txt  <imod_picks>.star 
## can use this star file for warp extraction 
```


## Picking particles

### Template pickers 
Can try with warp or pytom

### Geometric models with ChimeraX + ArtiaX
The ChimeraX extension [AritaX](https://github.com/FrangakisLab/ArtiaX) is a powerful tool for annotation and orientation-aware particle picking using geometric models as a guide. It is easily installed on all platforms from within ChimeraX via the built-in commandline:
```sh
(chimeraX) toolshed reload all
(chimeraX) toolshed install ArtiaX
```
Once installed it can be launched via the play button in its associated tab. Outlined below are a few steps that help show how you can generate a gemetric model for particle picking along a surface with orientations positioned normal to the plane. 

- Open the tomogram from the AritaX left menu.
- Pick points on planes around the object of interest as you move through the z-stack to define its limits
- Create a geometric model using those points 
- 


- Set the view to `tilted slab` via Map > Slab, or:
```
(chimeraX) volume #1 imageMode "tilted slab" tiltedSlabPlaneCount 15
```
- For this filament we want to view along the xz-plane to pick the membrane, we can set this orientation using the unit vector pointing along Y and tilting the camera around the X axis:
```
(chimeraX) volume tiltedSlabAxis 0,1,0
(chimeraX) turn x 90
```
- Set the right mouse to move planes only and show the side view:
```
(chimeraX) ui mousemode right "move planes"
(chimeraX) ui tool show "Side View" 
```
- Add a particle list
- Set ArtiaX ti Place Particles > Plane
- Right click to build a series of points aroudn the membrane of interest 
- Use ArtiaX Models panel to create a Boundary model, then smoothen it with max alpha
- Use the Geometric Model right menu tab to Generate Points on Surface with a Poisson Disk using more points than anticipated (ie. saturate the surface) and a distance spacing that is useful for your particles 
- Reorient particles when complete 