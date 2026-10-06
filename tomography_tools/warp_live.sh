#!/usr/bin/env bash

## Author: Alexander Keszei (refactored from scripts initially written by Landon Getz)
## 2026-10-05: Version 1 finished 

## Dependencies:
## 1. run in warp conda environment (need WarpTools)
## 2. imod needs to be installed and on path (e.g. etomo should be visible)
## 3. mrcs_slices.py should be installed and on path (e.g. mrcs_sclies.py -h returns no error)

## Usage:
##     cd /path/to/tomo5_session
##     warp_live.sh
## See usage() function below for details, or execute with -h option for a list on the terminal 

#region GLOBAL VARS
MIN_TILTS=10 # consider any mdoc with fewer than this many tilts to not be a viable tomographic dataset
DELAY=100 # seconds delay between loops
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
MIN_INTENSITY=0.2 # for ts_import step 
ETOMO_PATCH_SIZE_ANG=2000
WARP_WORKERS_PER_GPU=2 # increase to 2 for larger gpus 
DEFOCUS_HAND_CHECK_LOG_NAME="defocus_hand_check.log"
RESOLUTION_RECONSTRUCTION=8 # ang to use for reconstruction & alignments
MRCS_SLICES_OUTPUT_FOLDER="tomo_slices_png"
GPU_LIST="" # requires space delimited list, e.g. 0 1 2 3...
#endregion

set -uo pipefail #note cannot use -e option as it will terminate whole script when a function return is not 0
shopt -s nullglob extglob
## Set a trap to terminate running loops (SIGINT) and processes (SIGTERM) with control+C
trap "echo -e; echo -e 'Script terminated by user.'; exit;" SIGINT SIGTERM


#region GENERAL FUNCTIONS

## Usage:
## get_gpus 
## Description:
## Set the global GPU_LIST to all GPUs by creating a string of their index, e.g. ("0 1 2") based on what is found by nvidia-smi 
get_gpus(){
    local gpu_arr
    gpu_arr=()
    for m in $(nvidia-smi --query-gpu=index --format=csv,noheader); do
        gpu_arr+=($m)
    done
    ## set the global to the result with space delimitation
    GPU_LIST="${gpu_arr[@]}"
}

## Usage:
## countdown <seconds>
countdown(){
    local seconds=$1
    while [ "$seconds" -gt 0 ]; do
        printf "\r  ... waiting: %2d seconds     " "$seconds"
        sleep 1
        : $((seconds--))
    done
    printf "\r\e[K\n"
}

## Usage:
## is_integer <value>
is_integer(){
    # Check if an argument was actually passed
    if [ -z "$1" ]; then
        return 1
    fi

    # Regex breakdown:
    # ^-?    -> Optional negative sign at the start
    # [0-9]+ -> One or more digits
    # $      -> End of the string
    if [[ "$1" =~ ^-?[0-9]+$ ]]; then
        return 0 # True: It is a valid integer
    else
        return 1 # False: It is a string or empty
    fi
}

## Usage:
## is_float <value>
is_float(){
    # Check if an argument was actually passed
    if [ -z "$1" ]; then
        return 1
    fi

    # Regex breakdown:
    # ^-?    -> Optional negative sign at the start
    # [0-9]+ -> One or more digits
    # $      -> End of the string
    if [[ "$1" =~ ^-?[0-9]+(\.[0-9]+)?$ ]]; then
        return 0 # True: It is a valid float
    else
        return 1 # False: It is a string or empty
    fi

}

usage(){
    echo " Usage:"
    echo "     $ cd /path/to/Tomo5/folder"
    echo "     $ warp_live.sh "
    echo "--------------------------------------------------"
    echo "  Options:"
    echo "                      --help, -h : Display this help message and exit "
    echo "     --root_dir, -rd (warp_live) : Change the default root folder to use for all processing" 
    echo "           --min_tilts, -mt (10) : Minimum # of tilts needed to be present to in mdoc to run processing on"
    echo "               --delay, -d (100) : Seconds to pause in between re-running pipeline "
    echo "          --eer_ngroup, -eng (3) : Set eer_ngroup value for WarpTools create_settings "
    echo "        --tomo_z_ang, -tz (3000) : Desired thickness in Angstroms of final tomogram "
    echo "            --min_int, -mi (0.2) : Minimum average intensity relative to the zero tilt for tilted images to be kept for processing "
    echo "       --patch_size, -eps (2000) : Patch size in Angstroms for etomo patch tracking step "
    echo "                    --gpu, -g () : Choose specific GPUs to run on (e.g. 0,1 will use dev 0 & 1 only)"  
    echo "     --workers_per_gpu, -wpg (2) : Number of threads to run on each GPU; recommend to provide 16GB per thread"
    echo "    --reconstruct_res, -rr (8.0) : Max Angstrom resolution to use for patch alignment and tomogram reconstruction "

    exit 0
}
#endregion

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
    #   echo "   .. output directory ($1) already exists. Skipping mkdir function."
      return 1
   else 
    #   echo "   .. creating directory: $1"
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
##                  └── tomo_slices_png/ ## folder for mrcs_slices.py output of all tomograms for quick review   
##                  └── tomo1.../  
##                          └── frames/ ## eer & gain symlinks here 
##                          └── mdoc/ ## mdoc file symlink here 
##                          └── warp_rameseries/ ## motion correction files
##                          └── warp_tiltseries/ ## tilt series files including etomo and reconstruction
##                          └── tomostar/ ## final tilt series data for reconstruction
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
    ## consider a tomogram to contain at least a minimum number of tilts 
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
    create_dir $workspace_dir_name/$MRCS_SLICES_OUTPUT_FOLDER


    ## create relative symlinks to the mdoc, gain, and movies
    ln -sfn ../../../$mdoc $workspace_dir_name/$tomo_name/$mdoc_dir_name
    ln -sfn ../../../$gain_file $workspace_dir_name/$tomo_name/$frames_dir_name
    for m in "${movie_arr[@]}"; do
        ln -sfn ../../../$m $workspace_dir_name/$tomo_name/$frames_dir_name
    done
}

check_for_dependencies(){
    if ! command -v WarpTools >/dev/null 2>&1; then
        echo " !! Could not find WarpTools ... check you are in the warp conda environment"
        exit 1
    fi

    if ! command -v etomo >/dev/null 2>&1; then
        echo " !! Could not find etomo ... check you have sourced imod startup scripts"
        exit 1
    fi

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
    --gain_path $PROCESSING_FOLDER_NAME/$tomo_name/$FRAMES_FOLDER_NAME/$gain_file \
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
##    warp_motion_and_ctf  voltage 
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
    threads_per_gpu=$WARP_WORKERS_PER_GPU # divide GPU ram by 16, use that integer 
    spherical_aberration=2.7 # mm


    WarpTools fs_motion_and_ctf \
        --settings $PROCESSING_FOLDER_NAME/$tomo_name/$WARP_FRAMESERIES_SETTINGS_NAME \
        --m_grid $m_grid \
        --c_grid $c_grid \
        --c_voltage $voltage \
        --c_amplitude $amplitude_contrast \
        --c_cs $spherical_aberration \
        --c_range_max $max_ctf \
        --c_use_sum \
        --c_defocus_max $max_dZ \
        --out_thumbnails $thumbnail_size \
        --perdevice $threads_per_gpu \
        --device_list $GPU_LIST \
        --out_average_halves \
        --out_averages > /dev/null

}

## Usage:
## warp_ts_import  mdoc
warp_ts_import(){
    echo "   .. running WarpTools ts_import"
    mdoc=$1

    tilt_dose=$(awk '/ExposureDose/ {print $3; exit}' $mdoc)
    tilt_axis=$(awk '/RotationAngle/ {print $3; exit}' $mdoc)

    WarpTools ts_import \
        --mdocs $PROCESSING_FOLDER_NAME/$tomo_name/$MDOC_FOLDER_NAME \
        --frameseries $PROCESSING_FOLDER_NAME/$tomo_name/$WARP_FRAMESERIES_FOLDER_NAME \
        --tilt_exposure $tilt_dose \
        --min_intensity $MIN_INTENSITY \
        --override_axis $tilt_axis \
        --dont_invert \
        --output $PROCESSING_FOLDER_NAME/$tomo_name/$WARP_TOMOSTAR_FOLDER_NAME >> /dev/null

    #echo " Manually edit tomostar file to remove bad frames later"
}

## Usage:
## warp_etomo_patches  
warp_etomo_patches(){
    echo "   .. running WarpTools ts_etomo_patches"

    set_angpix=$RESOLUTION_RECONSTRUCTION # downsample to this target angpix, or set to full res
    patch_size_ang=$ETOMO_PATCH_SIZE_ANG # Ang size for each patch, patches are arranged with 80% overlap 
    threads_per_gpu=$WARP_WORKERS_PER_GPU # divide GPU ram by 16, use that integer


    # --initial_axis "$AXIS" not yet sure if this is required... run pipeline again  
    WarpTools ts_etomo_patches \
        --settings $PROCESSING_FOLDER_NAME/$tomo_name/$WARP_TILTSERIES_SETTINGS_NAME \
        --angpix $set_angpix \
        --patch_size $patch_size_ang \
        --device_list $GPU_LIST \
        --perdevice $threads_per_gpu > /dev/null

}

## Usage:
##    warp_check_hand
warp_check_hand(){
    echo "   .. running WarpTools ts_defocus_hand"

    defocus_hand_log_fpath=$PROCESSING_FOLDER_NAME/$tomo_name/$WARP_TILTSERIES_FOLDER_NAME/$DEFOCUS_HAND_CHECK_LOG_NAME
    WarpTools ts_defocus_hand \
    --settings $PROCESSING_FOLDER_NAME/$tomo_name/$WARP_TILTSERIES_SETTINGS_NAME \
    --check > $defocus_hand_log_fpath 
    #> /dev/null

    average_correlation=$(awk '/Average correlation:/ {print $3; exit}' $defocus_hand_log_fpath)

    if is_float $average_correlation; then 

        FLIP_HAND=$(awk -v num="$average_correlation" 'BEGIN { print (num < 0) ? "true" : "false" }')

        echo "   .. handedness correlation = $average_correlation -> FLIP_HAND = $FLIP_HAND"

        if [[ $FLIP_HAND == 'true' ]]; then
            WarpTools ts_defocus_hand --settings $PROCESSING_FOLDER_NAME/$tomo_name/$WARP_TILTSERIES_SETTINGS_NAME --set_flip > /dev/null
        fi

    else    
        echo "   .. could not parse average correlation value"
    fi

}

## Usage:
##    warp_ts_ctf  voltage 
warp_ts_ctf(){
    echo "   .. running WarpTools ts_ctf"

    voltage=$1
    if [ "$voltage" -eq 200 ]; then
        amplitude_contrast=0.09
    else
        amplitude_contrast=0.07 
    fi
    spherical_aberration=2.7 # mm
    max_ctf=6 # max Ang fit to consider for estimation
    max_dZ=8

	WarpTools ts_ctf \
		--settings $PROCESSING_FOLDER_NAME/$tomo_name/$WARP_TILTSERIES_SETTINGS_NAME \
		--range_high $max_ctf \
        --defocus_max $max_dZ \
        --cs $spherical_aberration \
        --voltage $voltage \
        --amplitude $amplitude_contrast \
        --device_list $GPU_LIST \
		--perdevice $WARP_WORKERS_PER_GPU > /dev/null

}

## Usage:
##    warp_ts_reconstruct
warp_ts_reconstruct(){
    echo "   .. running WarpTools ts_reconstruct"

	WarpTools ts_reconstruct \
		--settings $PROCESSING_FOLDER_NAME/$tomo_name/$WARP_TILTSERIES_SETTINGS_NAME \
		--angpix $RESOLUTION_RECONSTRUCTION \
        --device_list $GPU_LIST \
        --perdevice $WARP_WORKERS_PER_GPU > /dev/null
}

#endregion

#region RUN BLOCK

## 0. parse command line options & set defaults 
get_gpus

while [[ $# -gt 0 ]]; do
    case "$1" in
        --root_dir|-rd)
            PROCESSING_FOLDER_NAME="$2"
            shift 2 # Move past the flag and its value
            ;;

        --min_tilts|-mt)
            if is_integer "$2"; then
                MIN_TILTS="$2"
            else
                echo "Error: --min_tilts|-mt requires a valid integer, got '$2'" >&2
                usage
            fi
            shift 2 # Move past the flag and its value
            ;;
        --delay|-d)
            if is_integer "$2"; then
                DELAY="$2"
            else 
                echo "Error: --delay|-d requires a valid integer, got '$2'" >&2
                usage
            fi
            shift 2 
            ;;
        --eer_ngroup|-eng)
            if is_integer "$2"; then
                EER_NGROUP="$2"
            else 
                echo "Error: --eer_ngroup|-eng requires a valid integer, got '$2'" >&2
                usage
            fi
            shift 2 
            ;;
        --tomo_z_ang|-tz)
            if is_integer "$2"; then
                TOMO_THICKNESS_ANG="$2"
            else 
                echo "Error: --tomo_z_ang|-tz requires a valid integer, got '$2'" >&2
                usage
            fi
            shift 2 
            ;;
        --min_int|-mi)
            if is_float "$2"; then
                MIN_INTENSITY="$2"
            else 
                echo "Error: --min_int|-mi requires a valid integer, got '$2'" >&2
                usage
            fi
            shift 2 
            ;;
        --patch_size|-eps)
            if is_integer "$2"; then
                ETOMO_PATCH_SIZE_ANG="$2"
            else 
                echo "Error: --patch_size|-eps requires a valid integer, got '$2'" >&2
                usage
            fi
            shift 2 
            ;;
        --workers_per_gpu|-wpg)
            if is_integer "$2"; then
                WARP_WORKERS_PER_GPU="$2"
            else 
                echo "Error: --workers_per_gpu|-wpg requires a valid integer, got '$2'" >&2
                usage
            fi
            shift 2 
            ;;
        --gpu|-g)
            GPU_COMMA_DELIMITED="$2"
            ## recast list to space delimited
            l=${GPU_COMMA_DELIMITED//,/ }
            ## map list to array
            l_arr=($l)                
            ## iterate over the array to check each entry is an  integer 
            for val in ${l_arr[@]}; do 
                if is_integer $val; then 
                    continue 
                else 
                    echo "Error: --gpu|-g list flag requires a comma-separated set of integers, could not parse: '$2'" >&2
                    usage 
                fi
            done
            ## if no failure, recast space-delimited list to the $GPU global  
            GPU_LIST=$l
            shift 2 
            ;;

        --reconstruct_res|-rr)
            if is_float "$2"; then
                RESOLUTION_RECONSTRUCTION="$2"
            else 
                echo "Error: --reconstruct_res|-rr requires a valid integer, got '$2'" >&2
                usage
            fi
            shift 2 
            ;;
        # -t|--toggle)
        #     toggle=1
              ## example of toggle type flag 
        #     shift 1 # Move past the standalone flag
        #     ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage
            ;;
    esac
    
done

## 1. sanity check the working folder has a .dm file & we have the necessary programs  

is_tomo5_dir

check_for_dependencies

## 2. begin loop 
while true; do 

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

		## 5. check if a reconstruction & png output exists for this mdoc, skip rest of /pipeline if so
        expected_final_output_file=$PROCESSING_FOLDER_NAME/$MRCS_SLICES_OUTPUT_FOLDER/${tomo_name}.png
        reconstruction_files=(${PROCESSING_FOLDER_NAME}/${tomo_name}/${WARP_TILTSERIES_FOLDER_NAME}/reconstruction/${tomo_name}*.mrc)
        if [[ -f "$expected_final_output_file" && ${#reconstruction_files[@]} -ge 1 ]]; then
            echo " >> $mdoc already processed by pipeline, skipping."
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

        ## step 1 :: generate settings files for frame & tilt series
		setting_files=(${PROCESSING_FOLDER_NAME}/${tomo_name}/*.settings)
		if [ ${#setting_files[@]} -ne 2 ]; then
            angpix=$(awk '/PixelSpacing/ {print $3; exit}' $mdoc)
            tilt_dose=$(awk '/ExposureDose/ {print $3; exit}' $mdoc)
            movie_x=$(awk '/ImageSize/ {print $3; exit}' $mdoc)
            movie_y=$(awk '/ImageSize/ {print $4; exit}' $mdoc)
            tomo_thickness_px=$(awk -v t="$TOMO_THICKNESS_ANG" -v p="$angpix" 'BEGIN{printf "%d", t/p}')
            tomo_dims="${movie_x}x${movie_y}x${tomo_thickness_px}"
            warp_settings  $tomo_name $angpix  $tilt_dose $gain_file $tomo_dims
        else
            echo "   .. warp settings already present, skipping step."
		fi

        ## step 2 :: motion correction & ctf estimation 
		corrected_avg_mrc_files=(${PROCESSING_FOLDER_NAME}/${tomo_name}/${WARP_FRAMESERIES_FOLDER_NAME}/average/*.mrc)
        mapfile -t movies_in_mdoc < <(awk '/SubFramePath/ {print $3}' $mdoc)
		if [ ${#corrected_avg_mrc_files[@]} -ne ${#movies_in_mdoc[@]} ]; then
            voltage_float=$(awk '/Voltage/ {print $3; exit}' $mdoc)
            voltage_int=$(awk -v num="$voltage_float" 'BEGIN {printf "%.0f\n", num}')
            warp_motion_and_ctf $voltage_int
        else
            echo "   .. warp motion correction and ctf already finished, skipping step."
        fi

        ## step 3 :: import mdoc and create tomostar
        tomostar_file=${PROCESSING_FOLDER_NAME}/${tomo_name}/${WARP_TOMOSTAR_FOLDER_NAME}/${tomo_name}.tomostar
        if [[ ! -f "$tomostar_file" ]]; then
		# if [ ${#corrected_avg_mrc_files[@]} -lt 1 ]; then
            warp_ts_import $mdoc
        else
            echo "   .. warp tomostar already present, skipping step."
        fi

        ## step 4 :: etomo patch alignment 
        etomo_xf_file=${PROCESSING_FOLDER_NAME}/${tomo_name}/${WARP_TILTSERIES_FOLDER_NAME}/tiltstack/${tomo_name}/${tomo_name}.xf # 2d transforms to center tilts along y-axis aligned tilt axis
        etomo_tlt_file=${PROCESSING_FOLDER_NAME}/${tomo_name}/${WARP_TILTSERIES_FOLDER_NAME}/tiltstack/${tomo_name}/${tomo_name}.tlt # refined tilt angles for each tilt image 
        if [[ ! -f "$etomo_xf_file" && ! -f "$etomo_tlt_file" ]]; then
            warp_etomo_patches 
        else
            echo "   .. etomo alignment files already present, skipping patch motion."
        fi 

        ## step 5 :: check handedness 
        dZ_hand_file=${PROCESSING_FOLDER_NAME}/${tomo_name}/${WARP_TILTSERIES_FOLDER_NAME}/$DEFOCUS_HAND_CHECK_LOG_NAME
        if [[ ! -f "$dZ_hand_file" ]]; then
            warp_check_hand
        else
            echo "   .. defocus hand check already performed, skipping."
        fi

        ## step 6 :: refine tilt series ctf
        ctf_refine_file=(${PROCESSING_FOLDER_NAME}/${tomo_name}/${WARP_TILTSERIES_FOLDER_NAME}/ctf_tiltseries.settings)
        if [[ ! -f "$ctf_refine_file" ]]; then
            voltage_float=$(awk '/Voltage/ {print $3; exit}' $mdoc)
            voltage_int=$(awk -v num="$voltage_float" 'BEGIN {printf "%.0f\n", num}')
            warp_ts_ctf $voltage_int
        else
            echo "   .. ctf refinement already performed, skipping."
        fi

        ## step 7 :: reconstruct tomogram
		reconstruction_files=(${PROCESSING_FOLDER_NAME}/${tomo_name}/${WARP_TILTSERIES_FOLDER_NAME}/reconstruction/${tomo_name}*.mrc)
		if [ ${#reconstruction_files[@]} -lt 1 ]; then
            warp_ts_reconstruct
        else
            echo "   .. reconstruction already exists for this tomogram, skipping."
        fi

        ## step 8 :: write a png for quick review of the tomogram based on integrated slices through the middle parts of the tomogram along the Z axis 
        if [ ${#reconstruction_files[@]} -ge 1 ]; then
            tomogram_mrc=${reconstruction_files[0]}
            mrcs_slices.py  "${reconstruction_files[0]}"  $PROCESSING_FOLDER_NAME/$MRCS_SLICES_OUTPUT_FOLDER/${tomo_name}.png \
            --scale 0.5 \
            --set_slice 20,80,12 >> /dev/null
            echo "   .. written tomo slices png -> $PROCESSING_FOLDER_NAME/$MRCS_SLICES_OUTPUT_FOLDER/${tomo_name}.png"
        fi

	done

    countdown $DELAY
    echo "============================="
    echo " Re-running pipeline"
    echo "-----------------------------"

done

#endregion 
