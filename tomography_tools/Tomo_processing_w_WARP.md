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
