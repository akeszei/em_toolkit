#!/usr/bin/env bash

## run this script from within an EPU parent directory (i.e. contains Atlas, Images-Disc1, etc... folders
## This script will find all movies, corrected micrographs, and meta data and make symbolic links to more accesible folders, e.g.
##          movies will be linked at -> movies/
##          corrected micrographs -> micrographs/
##          meta data images (i.e. jpgs) -> jpgs/
## Symbolic links will also have more instructive nomenclature to easily tell which square it came from for ease during manual curation

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

## TO DO: Add step here to sanity check user is in an EPU directory, maybe look for 'EpuSession.dm' within the cwd
project_name=${PWD##*/}
echo " Project name = $project_name"

## prepare new directories
movies_dir="movies"
corrected_mics_dir="micrographs"
jpgs_dir="jpgs"

if [ ! -d $movies_dir ]; then
   echo " ... $movies_dir directory prepared"
   mkdir $movies_dir
fi

if [ ! -d $corrected_mics_dir ]; then
   echo " ... $corrected_mics_dir directory prepared"
   mkdir $corrected_mics_dir
fi

if [ ! -d $jpgs_dir ]; then
   echo " ... $jpgs_dir directory prepared"
   mkdir $jpgs_dir
fi

## check there is an atlas file and convert it to a reasonable size .jpg if so
if [ $(find {Sample*,Atlas} -name "Atlas_1.mrc" | wc -l) -gt 0 ]; then ## handle errors by using an if statement with the check
    atlas_path=$(find {Sample*,Atlas} -name "Atlas_1.mrc") ## on the Krios we have to use find function since it can be in any one of the 'Sample##' folders depending on which cartridge was used
    atlas_dir=${atlas_path%/*}
    atlas_jpg_path=${atlas_dir}/${project_name}_atlas.jpg
    echo " ... preparing 2x binned atlas at: $atlas_jpg_path"
    mrc2img.py $atlas_path $atlas_jpg_path --bin 2 >> /dev/null
    mogrify -normalize $atlas_jpg_path
    mv $atlas_jpg_path $jpgs_dir
    ## update the location of the atlas jpg
    atlas_jpg_path=${jpgs_dir}/${project_name}_atlas.jpg
    # ln -sr $atlas_jpg_path $jpgs_dir
else
    echo "No atlas found for " $project_name
fi

## iterate over all grid squares
square_counter=0
for sq_dir in $(ls -d Images-Disc1/*); do
    ## sanity check if there is a data folder in the square folder
    if [ ! -d ${sq_dir}/Data ]; then
       echo " ... no data folder in ${sq_dir}, skipping..."
       continue
    fi

    ## check the max number of micrographs in this directory and determine the padding factor (leading zeroes) to add
    total_movies_in_dir=$(ls -f ${sq_dir}/Data/*_Fractions.mrc | wc -l)
    padding_factor=$(echo -n $total_movies_in_dir | wc -m)

    ## advance the counter
    ((square_counter++))

    # ## for debugging, only run on the first folder and terminate early
    # if [ "$square_counter" -gt 1 ]; then
    #     exit
    # fi


    echo " >> PROCESSING grid square #" ${square_counter}
    ## copy the square .mrc to a .jpg with a new name
    sq_basename=${project_name}"_sq_"${square_counter}
    current_sq_mrc=$(ls ${sq_dir}/*.mrc | tail -1) ## get the only/last .mrc file in the directory
    current_sq_xml=$(ls ${sq_dir}/*.xml | head -1) ## get the only/last .xml file in the directory (can try: tail -1 to get the first one for the .xml if its more accurate tbh!)
        ## for the XML file take the first one, which corresponds to the more accruate position on the Atlas
        ## for the MRC file take the last one, which is usually the recentered image of the square but whose XML coordinates are offset from the stitched Atlas
    mrc2img.py $current_sq_mrc ${jpgs_dir}"/"${sq_basename}_lm.jpg --bin 2 >> /dev/null
    echo "    ... grid square low mag img saved"

    ## check if we have an atlas reference, in which case try to map the position of this square to the atlas; othwerise, skip this procedure
    if [ -f $atlas_jpg_path ]; then
        echo "    ... grid square position drawn on atlas"
        output_atlas_location_fname=${jpgs_dir}"/"${sq_basename}_atlas.jpg
        show_atlas_position.py ${atlas_dir}/ $atlas_jpg_path $current_sq_xml $output_atlas_location_fname
    fi

    ## while in a grid square directory, iterate over files in its data subdirectory
    movie_counter=0
    for movie in $(ls -f ${sq_dir}/Data/*_Fractions.mrc); do
        ## advance the iterator
        ((movie_counter++))

        # ## for debugging, only run on the first folder and terminate early
        # if [ "$movie_counter" -gt 1 ]; then
        #     exit
        # fi

        ## check there is at least one entry or exit the loop
        if [ $(ls -f ${sq_dir}/Data/*Fractions.mrc | wc -l) -eq 0 ]; then
            echo "      ... no data images for square, skipping "
            break
        fi

        ## update the movie counter to use leading zeros, using only as many are necessary for how large the pool of images will be (i.e. if 99 or less use 01, 02, ...; if 100 or more use 001, 002, etc)
        ## store a formatted string of the number to append to the micrograph with padded zeroes
        printf -v padded_number "%0${padding_factor}d" ${movie_counter}
        movie_basename=${sq_basename}"_mic_"${padded_number}
        echo -en "\r\033[K      ... working on mic #${movie_counter}  (${movie##*/})"

        ## find the associated corrected micrograph associated with this movie
        corrected_mic=${movie/_Fractions.mrc/}.mrc
        corrected_mic_basename=${sq_basename}"_mic_"${padded_number}

        ## save a .jpg image using the corrected image not the movie
        mrc2img.py $corrected_mic ${jpgs_dir}"/"${movie_basename}.jpg --bin 4 >> /dev/null
        ## make a named symbolic link of the movie
        ln -sr $movie ${movies_dir}/${movie_basename}.mrc
        ## make a named symbolic link of the on-the-fly corrected micrograph
        ln -sr $corrected_mic ${corrected_mics_dir}/${corrected_mic_basename}.mrc
    done
    echo -en "\r\033[K      ... #${movie_counter} micrographs total "
    echo ""

echo " Consider curating the jpgs folder, then reading the marked images by their full path to their movie, e.g.:"
echo '     $ for m in $(cat jpgs/marked_imgs.txt); do f=$(readlink -f movies/${m}.mrc); rm -v $f; rm -v movies/${m}.mrc done'

done
