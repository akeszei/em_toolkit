#!/usr/bin/env bash 

## Pick particles in 3dmod (usually these are 10A sub-sampled tomos)
## Convert the .mod file to a .txt file with model2point <file>.mod <out>.txt
## Then pass the .txt file into this script to create a .star file for warp extraction

read -p "IMOD coordinates txt file: " -i "imod_picks.txt" -e txt_file

read -p "output star file name: " -i "imod_picks.star" -e star_file

read -p "tomostar file to use: " -i " DVO14g3_2026-09-25_tomo10_2.tomostar" -e tomostar_file

read -p "Tomogram dimensions (X,Y,Z,angpix): " -i "643,643,299,10" -e tomo_dim_xyza


IFS=',' read -r tomo_dim_x tomo_dim_y tomo_dim_z tomo_angpix <<< $tomo_dim_xyza

echo "   Tomo X, Y, Z = $tomo_dim_x, $tomo_dim_y, $tomo_dim_z"

## Create a fresh .star file with appropriate headers 
echo "" > $star_file 
echo "data_" >> $star_file
echo "" >> $star_file
echo "loop_" >> $star_file
echo "_rlnCoordinateX #1" >> $star_file
echo "_rlnCoordinateY #2" >> $star_file
echo "_rlnCoordinateZ #3" >> $star_file
echo "_rlnMicrographName #4" >> $star_file


## read points from imod txt file: 
count=0
while IFS= read -r line; do
    read -r x y z <<< "$line"
    ((count++))
    x_norm=$(awk "BEGIN {print $x/$tomo_dim_x}")
    y_norm=$(awk "BEGIN {print $y/$tomo_dim_y}")
    z_norm=$(awk "BEGIN {print $z/$tomo_dim_z}")
    if (( count < 3 )); then
        echo " Input coords: $x | $y | $z --> Normalized coords: $x_norm | $y_norm | $z_norm"
    fi
    if ((count == 3)); then 
        echo " ..."
    fi
    
    echo "$x_norm   $y_norm   $z_norm   $tomostar_file" >> $star_file
    
done < <(sed 's/[\xa0\xc2\r]//g' $txt_file)
    

echo " Finished!"
echo "    Wrote $count particles to $star_file"

