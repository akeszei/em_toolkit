#!/usr/bin/env bash 

star_file=$1

echo "Processing star file:  $star_file"

echo ""

read -p "rlnTomoName to use: " -i "DVO14g3_2026-09-25_tomo10_2" -e rln_tomo_name

read -p "Tomogram dimensions (X,Y,Z,angpix): " -i "643,643,299,10" -e tomo_dim_xyza


IFS=',' read -r tomo_dim_x tomo_dim_y tomo_dim_z tomo_angpix <<< $tomo_dim_xyza

# echo "   X, Y, Z = $tomo_dim_x, $tomo_dim_y, $tomo_dim_z"

##  ArtiaX particle coordinates saved in regular RELION format (not v.5) will have headers for
##  rlnCoordinateX,Y, and Z, each of which are reported in Angstroms (i.e. pixel position * angpix).
##  To import into a relion tomo annotation folder, we need to rescale back to pixels

scaling_factor=$(awk "BEGIN {print 1 / $tomo_angpix}")
relion_star_handler --i DVO14g3_2026-09-25_tomo10_2_manualPicked2.star --o rescaled.star --operate rlnCoordinateX --operate2 rlnCoordinateY --operate3 rlnCoordinateZ --multiply_by $scaling_factor 


relion_star_handler --i rescaled.star --o rescaled.star --add_column rlnTomoName --add_column_value $rln_tomo_name
