#!/usr/bin/env bash

## Usage:
##     cd /path/to/tomo5_session
##     warp_live.sh

TESTING=1

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
    workspace_dir_name="warp_live"
    frames_dir_name="frames"
    mdoc_dir_name="mdoc"
    gain_file=$(find_gain)

    
    ## read the mdoc for SubFramePath contents to get the dmp paths of the movies for each tilt 
    local movie_arr
    mapfile -t movie_arr < <(awk '/SubFramePath/ {print $3}' $mdoc)
 
    if (( ${#movie_arr[@]} < 10 )); then
        echo "$mdoc points to too few tilt movies (${#movie_arr[@]}), skipping..."
        return 1
    else
        echo "$mdoc points to ${#movie_arr[@]} tilt movies"
        
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
    
    ## create relative symlinks to the mdoc, gain, and movies
    ln -sfn ../../../$mdoc $workspace_dir_name/$tomo_name/$mdoc_dir_name
    ln -sfn ../../../$gain_file $workspace_dir_name/$tomo_name/$frames_dir_name
    for m in "${movie_arr[@]}"; do
        ln -sfn ../../../$m $workspace_dir_name/$tomo_name/$frames_dir_name
    done
}
#endregion


#region WARP FUNCTIONS


#endregion

#region RUN BLOCK

################### TESTING
## use a testing global for laptop testing functions remove this flag later 
if (( TESTING )); then
## 4. run warp through all tomograms, skipping those withoutputs 

while sleep 1; do 
	echo " ... running warp across all tomograms "

done

exit 0

fi
################### TESTING OVER 


## 1. sanity check folder has a .dm file 
is_tomo5_dir

## 2. get only the regular .mdoc file for each tomogram 
mdocs=(!(*_override).mdoc)

## 3. iterate over the list of mdocs, preparing the workspace for each 
for i in "${!mdocs[@]}"; do
    counter=$((i+1))
    echo " ... preparing $counter of ${#mdocs[@]} workspaces"  
    create_warp_workspace ${mdocs[$i]}
done


exit 0

#endregion 
