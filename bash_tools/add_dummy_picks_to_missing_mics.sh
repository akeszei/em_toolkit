#!/usr/bin/env bash

## A small script to add a dummy star file for every micrograph that had 0 picks during cryolo writeout (necessary for cryosparc import particle stack job... we think)

## Set a trap to terminate running loops (SIGINT) and processes (SIGTERM) with control+C
trap "echo -e; echo -e '${red}Script terminated by user.${default}'; exit;" SIGINT SIGTERM

MIC_COUNTER=0
STAR_COUNTER=0
NO_PICK_COUNTER=0

## 'dummy' star file we can use to copy from when needed 
DUMMY_FILE="dummy_pick.star"
## sanity check the dummy file exists 
if ! [ -f "${DUMMY_FILE}" ]; then 
    echo " ERROR !! Could not find dummy file: $DUMMY_FILE"
    exit
fi

## relative path to the folder containing all micrographs in the datasets 
MIC_DIR="Doseweighted_motion_corrected_full_dataset"
## relative path to the folder containing all star files with picks (i.e. the folder that has some missing star files for micrographs with 0 picks)
STAR_DIR="particle_picks/STAR/"

## check how many star file we had in the directory at the start of runtime 
for star in $(ls $STAR_DIR); do
    ((STAR_COUNTER++))
    #echo $mic
done

## iterate over all micrographs we expect to have a corresponding star file for 
for mic in $(ls $MIC_DIR); do
    ## advance the counter 
    ((MIC_COUNTER++))
    ## extract the basename of the file (i.e. filename.mrc -> filename)
    F_BASENAME=${mic%%.*}
    ## prepare a seach string of the expected .star file we intend to find (i.e. filename -> filename.star)
    EXP_STARFILE=${F_BASENAME}.star
    ## do a logic check if the expected star file exists in the target directory
    if [ -f "${STAR_DIR}${EXP_STARFILE}" ]; then
        continue 
    else 
        echo "$EXP_STARFILE does not exist... creating dummy star file."
        ((NO_PICK_COUNTER++))
        ## copy the dummy file to the target directory with the expected star file name 
        cp $DUMMY_FILE ${STAR_DIR}${EXP_STARFILE}
    fi
done


echo "============================================================================="
echo "  $MIC_COUNTER micrographs detected in $MIC_DIR"
echo "  $STAR_COUNTER star files detected in $STAR_DIR"
echo "  >> $NO_PICK_COUNTER 'dummy' star files were created"
