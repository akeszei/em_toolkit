#!/usr/bin/env bash

## run this script in the parent folder of an EPU session, e.g.
##      session_2021-08-18/<run here>
##          /A3g1
##          /A3g2
##          ..
## The script will automatically make new folders arranged in a manner I like, e.g.
##          /reorganized/A3g1/Raw_data/*.mrc
##                           /Jpgs/*.jpg
##

############ Simplify text output modifiers (e.g. echo -e -e -e "${red}color text here,${default} normal text color here");
## NOTE: tput function can slow down the launch of colorized scripts significantly on some setups and completely fail on installs lacking tput.
## Escape sequences are much faster and more widely implemented, with the minor drawback of less color control. To implement you require the 'echo -e -e -e' environment. Cannot be used within the 'read' environment unfortunately - requires rebuilding prompt elements
default='\033[0m' #$(tput sgr0)
red='\033[0;31m' #$(tput setaf 1)
green='\033[0;32m' #$(tput setaf 2)
yellow='\033[0;33m' #$(tput setaf 3)
blue='\033[0;34m' #$(tput setaf 4)
magenta='\033[0;35m' #$(tput setaf 5)
cyan='\033[0;36m' #$(tput setaf 6)
white='\033[0;37m' #$(tput setaf 7)


# echo -e "Color palette: ${red} red ${green} green ${yellow} yellow ${blue} blue ${magenta} magenta ${cyan} cyan ${white} white ${default} default"

## Set a trap to terminate running loops (SIGINT) and processes (SIGTERM) with control+C
trap "echo -e; echo -e '${red}Script terminated by user.${default}'; exit;" SIGINT SIGTERM

## prepare new parent directory
if [ ! -d "reorganized" ]; then
   echo "Files will be passed into new directory: reoganized"
   mkdir reorganized
fi


## prepare the directory structure for each grid, then run the processing steps
for grid in $(ls -d */); do
    ## ignore the directory named 'reorganized'
    if [[ $grid == "reorganized/" ]]; then
        continue
    fi

    echo "EPU directory found: " $grid ## returns folder with a trailing slash (e.g. 'A3g1/')

    ## confirm the directory is potentially a grid by checking if it has *mrc files within it
    mrc_file_num=$(find $grid -name "*.mrc" | wc -l)
    if [ $mrc_file_num -eq 0 ]; then
        echo "Directory found: " ${grid} "but, no mrc files within, skipping..."
        continue
    fi

    ## prepare new parent directory
    if [ ! -d "reorganized/"${grid} ]; then
       echo "Pepare sub-directory: reoganized/"${grid}
       mkdir "reorganized/"${grid}
    fi

    ## prepare sub-directory for exposure images
    if [ ! -d "reorganized/"${grid}Raw_data ]; then
       mkdir "reorganized/"${grid}Raw_data
    fi

    ## prepare sub-directory for search images
    if [ ! -d "reorganized/"${grid}Jpgs ]; then
       mkdir "reorganized/"${grid}Jpgs
    fi

    ## Check if there is a folder called 'Screening' in the grid directory, if so then copy the relevant files over to the reorganized directory
    if [ -d ${grid}Screening ]; then
        echo "  ... Screening directory present at: ${grid}Screening, copying relevant files over (.ser,.jpg,.png,.bmp,.txt)"
        mkdir "reorganized/"${grid}Screening
        ## check if there are .ser files and copy them over with convertion to .mrc & preparing a binned .jpg
        if [ $(ls ${grid}Screening/*.ser | head -n 1 | wc -l) -gt 0 ]; then
            for n in ${grid}Screening/*.ser; do n2=${n/.ser/}.mrc; ser2mrc.py $n reorganized/${grid}Screening/${n2##*/} --jpg >> /dev/null; done
        else
            echo "No .SER files in Screening directory";
        fi
        ## also copy any existing images or text files
        cp ${grid}Screening/*.jpg reorganized/${grid}Screening/
        cp ${grid}Screening/*.png reorganized/${grid}Screening/
        cp ${grid}Screening/*.bmp reorganized/${grid}Screening/
        cp ${grid}Screening/*.txt reorganized/${grid}Screening/
    fi


    save_parent_path="reorganized/"${grid} ## parent folder where Raw_data and Jpgs folders will be
    retrieve_square_path=${grid}"Images-Disc1/" ## path to the folder containing the grid square images
    atlas_directory=${grid}Atlas/

    ## check there is an atlas file and convert it to a .jpg if so
    if [ $(find ${grid}Atlas -name "Atlas*.mrc" | wc -l) -gt 0 ]; then
        atlas_path=$(find ${grid}Atlas -name "Atlas*.mrc")
        atlas_basename=${grid%/}"_atlas"
        atlas_jpg_path=${save_parent_path}"Jpgs/"${atlas_basename}.jpg
        echo "  ... preparing atlas at: reorganized/"${grid}"Jpgs/"${atlas_basename}.jpg
        mrc2img.py $atlas_path ${save_parent_path}"Jpgs/"${atlas_basename}.jpg --bin 1 >> /dev/null
        mogrify -normalize ${save_parent_path}"Jpgs/"${atlas_basename}.jpg
    else
        echo "No atlas found in " $grid
    fi

    ## iterate over all grid squares
    square_counter=0
    for sq_dir in $(ls -d ${retrieve_square_path}*); do
        ## advance the counter
        ((square_counter++))

        ## check the max number of micrographs in this directory and determine the padding factor (leading zeroes) to add
        total_mics_in_dir=$(ls -f ${sq_dir}/Data/*.mrc | wc -l)
        padding_factor=$(echo -n $total_mics_in_dir | wc -m)

        ## add a sanity check to find any *.mrc files, otherwise skip the directory ...
        if [ $total_mics_in_dir -eq 0 ]; then
            echo "No mrcs in ${sq_dir}, skipping..."
            continue
        fi

        echo "  ... processing grid square #" ${square_counter}
        ## copy the square .mrc to a .jpg with a new name
        sq_basename=${grid///}"_sq_"${square_counter}
        current_sq_mrc=$(ls ${sq_dir}/*.mrc | tail -1) ## get the only/last .mrc file in the directory
        current_sq_xml=$(ls ${sq_dir}/*.xml | head -1) ## get the only/last .xml file in the directory (can try: tail -1 to get the first one for the .xml if its more accurate tbh!)
            ## for the XML file take the first one, which corresponds to the more accruate position on the Atlas
            ## for the MRC file take the last one, which is usually the recentered image of the square but whose XML coordinates are offset from the stitched Atlas
        mrc2img.py $current_sq_mrc ${save_parent_path}"Jpgs/"${sq_basename}_lm.jpg --bin 2 >> /dev/null
        echo "      ... grid square low mag img saved"

        ## check if we have an atlas reference, in which case try to map the position of this square to the atlas; othwerise, skip this procedure
        if [ -f $atlas_jpg_path ]; then
            echo "      ... grid square atlas location drawn"
            output_atlas_location_fname=${save_parent_path}"Jpgs/"${sq_basename}_atlas.jpg
            show_atlas_position.py $atlas_directory $atlas_jpg_path $current_sq_xml $output_atlas_location_fname
        fi

        ## while in a grid square directory, iterate over files in its data subdirectory
        exposure_counter=0
        for mic in $(ls -f ${sq_dir}/Data/*.mrc); do
            ## advance the iterator
            ((exposure_counter++))
            ## check there is at least one entry or exit the loop
            if [ $(ls -f ${sq_dir}/Data/*.mrc | wc -l) -eq 0 ]; then
                echo "      ... no data images for square, skipping "
                break
            fi
            ## update the exposure counter to use leading zeros, using only as many are necessary for how large the pool of images will be (i.e. if 99 or less use 01, 02, ...; if 100 or more use 001, 002, etc)
            ## store a formatted string of the number to append to the micrograph with padded zeroes
            printf -v padded_number "%0${padding_factor}d" ${exposure_counter}
            mic_basename=${sq_basename}"_mic_"${padded_number}
            echo -en "\r\033[K          ... processing mic #${exposure_counter}  (${mic##*/})"
            ## save a .jpg image
            mrc2img.py $mic ${save_parent_path}"Jpgs/"${mic_basename}.jpg --bin 4 >> /dev/null
            ## copy .mrc to Raw_data directory with new name
            cp $mic ${save_parent_path}"Raw_data/"${mic_basename}.mrc
        done
        echo -en "\r\033[K          ... processed #${exposure_counter} micrographs"
        echo ""

    done

done
