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
