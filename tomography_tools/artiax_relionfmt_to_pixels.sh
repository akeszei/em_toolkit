#!/usr/bin/env bash 

## Pick particles in ArtiaX (usually these are 10A sub-sampled tomos), and save the particle list in RELION format (not version 5 format). 
## Then run the output .star file through this script to rescale the picks to pixels and add the necessary _rlnTomoName entry
## Use your RELION project to find the correct input for that (e.g. refer to: Import/tilt_series.star)

read -p "ArtiaX particles star file with rlnCoordinateX,Y,Z to use: " -i "" -e star_file

read -p "rlnTomoName to use: " -i "$star_file" -e rln_tomo_name

read -p "Tomogram dimensions (X,Y,Z,angpix): " -i "643,643,299,10" -e tomo_dim_xyza


IFS=',' read -r tomo_dim_x tomo_dim_y tomo_dim_z tomo_angpix <<< $tomo_dim_xyza

# echo "   X, Y, Z = $tomo_dim_x, $tomo_dim_y, $tomo_dim_z"

##  ArtiaX particle coordinates saved in regular RELION format (not v.5) will have headers for
##  rlnCoordinateX,Y, and Z, each of which are reported in Angstroms (i.e. pixel position * angpix).
##  To import into a relion tomo annotation folder, we need to rescale back to pixels
scaling_factor=$(awk "BEGIN {print 1 / $tomo_angpix}")

relion_star_handler --i DVO14g3_2026-09-25_tomo10_2_manualPicked2.star --o rescaled.star --operate rlnCoordinateX --operate2 rlnCoordinateY --operate3 rlnCoordinateZ --multiply_by $scaling_factor 

## ArtiaX particle file lacks the necessary rlnTomoName header, add it here 
relion_star_handler --i rescaled.star --o rescaled.star --add_column rlnTomoName --add_column_value $rln_tomo_name

echo " Finished!"
echo "    Next: save this particle file as <rlnTomoName>_particles.star in the Picks/jobX/annotations/ folder"
echo "          and re-run the Picks job with Napari to confirm correct import. Then save in Napari and close"
echo "          This will generate the necessary particles.star file and optimization_set.star outputs"