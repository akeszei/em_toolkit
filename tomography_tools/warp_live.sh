#!/usr/bin/env bash

## Usage:
##     cd /path/to/tomo5_session
##     warp_live.sh

#region GLOBAL VARS
MIN_TILTS=10 # consider any mdoc with fewer than this many tilts to not be a viable tomographic dataset
DELAY=1 # seconds delay between loops
PROCESSING_FOLDER_NAME="warp_live"
FRAMES_FOLDER_NAME="frames"
MDOC_FOLDER_NAME="mdoc"
WARP_TILTSERIES_FOLDER_NAME="warp_tiltseries"
WARP_TILTSERIES_SETTINGS_NAME="warp_tiltseries.settings"
WARP_TOMOSTAR_FOLDER_NAME="tomostar"
WARP_FRAMESERIES_FOLDER_NAME="warp_frameseries"
WARP_FRAMESERIES_SETTINGS_NAME="warp_frameseries.settings"
EER_NGROUP=3
MOVIE_EXTENSION="*.eer"
TOMO_THICKNESS_ANG=3000 # 300nm
#endregion

set -uo pipefail #note cannot use -e option as it will terminate whole script when a function return is not 0
shopt -s nullglob extglob

#region ORGANIZE FUNCTIONS

## Usage:
##    print_array "${arr[@]}"
print_array(){
    local arr=("$@")
    
    size=${#arr[@]}
    echo "Print array: (size $size})"
    for i in "${!arr[@]}"; do 
        echo "$i = ${arr[$i]}"
    done
    
}

## Check for Session.dm file in working directory to ensure user is running this script in the right location
## Usage:
##     is_tomo5_dir
is_tomo5_dir(){
	## look for Session.dm
    session_file=(*.dm)
    if (( ${#session_file[@]} < 1 )); then
        echo " WARNING: No Session.dm file found. Be sure you are running this script in a raw tomo5 folder."
        read -p ">> Proceed? (y/N) " user_input 
        if [ "$user_input" != "y" ] && [ "$user_input" != "yes" ] && [ "$user_input" != "Y" ] && [ "$user_input" != "Yes" ]; then 
            echo "User stopped script."
            exit 0;
        fi
        return 0
    fi
    
    ## check the .dm file for TomographySession keyword
    if grep -q "TomographySession" "${session_file[0]}"; then
        echo " Found Session.dm..."
        return 0
    else
        echo " WARNING: Session.dm file found but does not appear to be from Tomo5. "
        read -p ">> Proceed? (y/N) " user_input 
        if [ "$user_input" != "y" ] && [ "$user_input" != "yes" ] && [ "$user_input" != "Y" ] && [ "$user_input" != "Yes" ]; then 
            echo "User stopped script."
            exit 0;
        fi
    fi
	return 0
}


## Find .gain file in working directory
## Usage:
##    file=$(find_gain)
find_gain(){
    gain=(*.gain)
    if (( ${#gain[@]} > 1 )); then
        echo " WARNING: More than 1 .gain file was found, using first match"
        echo "${gain[0]}"
    fi

    if (( ${#gain[@]} == 1 )); then
        echo "${gain[0]}"
    fi


    if (( ${#gain[@]} == 0 )); then
        echo " ERROR :: No .gain file was found!"
        exit 1
    fi

}


## Create directory with built in sanity checking
## Usage:
##    create_dir /path/to/new/dir
create_dir(){
   if [ -d $1 ]; then
      echo "   .. output directory ($1) already exists. Skipping mkdir function."
      return 1
   else 
      echo "   .. creating directory: $1"
      mkdir -p $1 
      return 0
   fi
}

## Set up processing folder & data structure from within a Tomo5 raw directory 
## Tomo5_dir/
##    Session.dm
##    file.gain
##    tomo1...eer
##    tomo1...mdoc
##       └── warp_live/ 
##                  └── tomo1.../  
##                          └── frames/ ## eer & gain symlinks here 
##                          └── mdoc/ ## mdoc file symlink here 
##
## Usage: 
##    create_warp_workspace <fname>.mdoc 
create_warp_workspace(){
    mdoc=$1
    tomo_name=${mdoc%.*}
    workspace_dir_name=$PROCESSING_FOLDER_NAME
    frames_dir_name=$FRAMES_FOLDER_NAME
    mdoc_dir_name=$MDOC_FOLDER_NAME
    gain_file=$(find_gain)

    
    ## read the mdoc for SubFramePath contents to get the dmp paths of the movies for each tilt 
    local movie_arr
    mapfile -t movie_arr < <(awk '/SubFramePath/ {print $3}' $mdoc)
 
    if (( ${#movie_arr[@]} < $MIN_TILTS )); then
        echo " >> $mdoc points to too few tilt movies (${#movie_arr[@]}), skipping..."
        return 1
    else
        echo " >> $mdoc points to ${#movie_arr[@]} tilt movies"
        
    fi
        
    ## edit the path data in the movie array to get only the movie name, not full path
    for i in "${!movie_arr[@]}"; do 
        v=${movie_arr[i]}
        v_basename=${v##*\\}
        v_basename_remove_return=${v_basename//$'\r'/}
        
        movie_arr[i]="${v_basename_remove_return}" 
    done

    #print_array "${movie_arr[@]}"


    ## create the directory structure
    create_dir $workspace_dir_name/$tomo_name/$frames_dir_name
    create_dir $workspace_dir_name/$tomo_name/$mdoc_dir_name
    create_dir $workspace_dir_name/$tomo_name/$WARP_TILTSERIES_FOLDER_NAME
    create_dir $workspace_dir_name/$tomo_name/$WARP_FRAMESERIES_FOLDER_NAME
    create_dir $workspace_dir_name/$tomo_name/$WARP_TOMOSTAR_FOLDER_NAME


    ## create relative symlinks to the mdoc, gain, and movies
    ln -sfn ../../../$mdoc $workspace_dir_name/$tomo_name/$mdoc_dir_name
    ln -sfn ../../../$gain_file $workspace_dir_name/$tomo_name/$frames_dir_name
    for m in "${movie_arr[@]}"; do
        ln -sfn ../../../$m $workspace_dir_name/$tomo_name/$frames_dir_name
    done
}
#endregion


#region WARP FUNCTIONS

## Usage:
##    warp_settings  tomo_name  angpix  tilt_dose  gain_file_name  tomo_dims
warp_settings(){
    # for questions related to inputs try: WarpTools create_settings --help
    tomo_name=$1
    angpix=$2
    tilt_dose=$3 # dose per Ang**2 for each tilt
    gain_file=$4
    tomo_dim=$5
    dose_per_virtual_frame=$(awk "BEGIN {print $tilt_dose / $EER_NGROUP}")  

    echo "   .. motion correction will integrate $dose_per_virtual_frame e/A**2 per step. Adjust EER_NGROUP global to change this value."  

    echo "   .. running WarpTools create_settings"


    WarpTools create_settings \
    --output $PROCESSING_FOLDER_NAME/$tomo_name/$WARP_FRAMESERIES_SETTINGS_NAME \
    --folder_data $FRAMES_FOLDER_NAME \
    --folder_processing $WARP_FRAMESERIES_FOLDER_NAME \
    --extension "$MOVIE_EXTENSION" \
    --eer_ngroups $EER_NGROUP  \
    --angpix $angpix \
    --gain_path $FRAMES_FOLDER_NAME/$gain_file \
    --exposure $tilt_dose > /dev/null

    WarpTools create_settings \
    --output $PROCESSING_FOLDER_NAME/$tomo_name/$WARP_TILTSERIES_SETTINGS_NAME \
    --folder_processing $WARP_TILTSERIES_FOLDER_NAME \
    --folder_data $WARP_TOMOSTAR_FOLDER_NAME \
    --extension "*.tomostar" \
    --angpix $angpix \
    --exposure $tilt_dose \
    --tomo_dimensions $tomo_dim > /dev/null

}

## Usage:
##    warp_motion_and_ctf  voltage  <vars>
warp_motion_and_ctf(){
    echo "   .. running WarpTools fs_motion_and_ctf"

    voltage=$1
    if [ "$voltage" -eq 200 ]; then
        amplitude_contrast=0.09
    else
        amplitude_contrast=0.07 
    fi

    m_grid="2x2x3" # motion correction patch & depth size 
    c_grid="4x4x1" # ctf estimation patch & depth size
    max_ctf=7 # max Ang fit to consider for estimation
    max_dZ=8
    thumbnail_size=512
    threads_per_gpu=2 # divide GPU ram by 16, use that integer 
    spherical_aberration=2.7 # mm


    WarpTools fs_motion_and_ctf \
        --settings warp_frameseries.settings \
        --m_grid $m_grid \
        --c_grid $c_grid \
        --c_voltage $voltage \
        --c_amplitude $amplitude_contrast \
        --c_cs $spherical_aberration \
        --c_range_max $max_ctf \
        --c_use_sum \
        --c_defocus_max $max_dZ \
        --out_average_halves \
        --out_thumbnails $thumbnail_size \
        --perdevice $threads_per_gpu \
        --out_averages  

}


#endregion

#region RUN BLOCK

## 1. sanity check the working folder has a .dm file 
is_tomo5_dir

## 2. begin loop 
while sleep $DELAY; do 

	## 3. update available .mdoc files, ignoring override mdocs  
	mdocs=(!(*_override).mdoc)

	## 4. iterate over the list of mdocs 
	for i in "${!mdocs[@]}"; do
		counter=$((i+1))
    	mdoc=${mdocs[$i]}
		tomo_name=${mdoc%.*}
        gain_file=$(find_gain)

        echo 
		echo "... reading $counter of ${#mdocs[@]} mdoc files"

		## 5. check if a reconstruction exists for this mdoc, skip rest of pipeline if so
		reconstruction_files=(${PROCESSING_FOLDER_NAME}/${tomo_name}/${WARP_TILTSERIES_FOLDER_NAME}/reconstruction/${tomo_name}*.mrc)
		if (( ${#reconstruction_files[@]} )); then
			echo " ... reconstruction exists for ${tomo_name}, skipping."
			continue 
		fi

		## 6. if no reconstruction, re-run setup in all cases 
		create_warp_workspace $mdoc
        exit_code=$?
        ## skip subsequent steps if the above function returns a failure code 
        if [ $exit_code -ne 0 ]; then
            # echo "   .. error creating warp workspace, skipping $mdoc" 
            continue 
        fi

		## 7. run warp processing pipeline steps
		setting_files=(${PROCESSING_FOLDER_NAME}/${tomo_name}/*.settings)
		if [ ${#setting_files[@]} -ne 2 ]; then
            angpix=$(awk '/PixelSpacing/ {print $3; exit}' $mdoc)
            tilt_dose=$(awk '/ExposureDose/ {print $3; exit}' $mdoc)
            movie_x=$(awk '/ImageSize/ {print $3; exit}' $mdoc)
            movie_y=$(awk '/ImageSize/ {print $4; exit}' $mdoc)
            tomo_thickness_px=$(awk -v t="$TOMO_THICKNESS_ANG" -v p="$angpix" 'BEGIN{printf "%d", t/p}')
            tomo_dims="${movie_x}x${movie_y}x${tomo_thickness_px}"
            warp_settings  $tomo_name $angpix  $tilt_dose $gain_file $tomo_dims
		fi


        voltage_float=$(awk '/Voltage/ {print $3; exit}' $mdoc)
        voltage_int=$(awk -v num="$voltage_float" 'BEGIN {printf "%.0f\n", num}')
        warp_motion_and_ctf $voltage_int

        exit 0


	done

done

exit 0

#endregion 
