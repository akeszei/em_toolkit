#!/usr/bin/env bash

## A small script to link files from multiple directories with suffix matching into the current working directory 

## Set a trap to terminate running loops (SIGINT) and processes (SIGTERM) with control+C
trap "echo -e; echo -e '${red}Script terminated by user.${default}'; exit;" SIGINT SIGTERM

COUNTER=0
DIRS=( "../../../J2/motioncorrected/" "../../../J6/motioncorrected/" "../../../J11/motioncorrected/")

for dir in ${DIRS[@]}; do
    for mic in $(ls $dir); do
        ## only consider images with a specific string suffix
        SUFFIX="doseweighted.mrc"
        if [[ ${mic##*_} == $SUFFIX ]]; then
            ((COUNTER++))
            fullpath="${dir}${mic}"
            # echo "MATCH = $fullpath"
            ln -s $fullpath
        fi
    done
done

echo " $COUNTER micrographs linked"
