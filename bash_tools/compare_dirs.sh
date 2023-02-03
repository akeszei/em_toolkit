#!/usr/bin/env bash

############ Simplify text output modifiers (e.g. echo "${red}color text here,${default} normal text color here");
default=$(tput sgr0)
red=$(tput setaf 1)
green=$(tput setaf 2)
yellow=$(tput setaf 3)
blue=$(tput setaf 4)
magenta=$(tput setaf 5)
cyan=$(tput setaf 6)
white=$(tput setaf 7)

## Explain script on startup 
echo "${cyan}"
echo "====================================================================="
echo "  A script to compare to directories to find the missing/different"
echo "  files between them. Can compare files with different extensions "
echo "  by specifying different suffixes to consider in each directory."
echo "=====================================================================${default}"

## Set a trap to terminate running loops (SIGINT) and processes (SIGTERM) with control+C
trap "echo; echo '${red}Script terminated by user.${default}'; exit;" SIGINT SIGTERM
## Automatically terminate script if any variables are undefined
set -eu

############ Designate SOURCE and DEST paths by user prompt 
read -ep "${magenta}First directory to consider (e.g. /path/to/dir1): ${default}" DIR_1
## allow the user to choose the extension to consider in this folder 
read -ep "${magenta} ... suffix to truncate in directory #1 (e.g. '_EER.eer'): ${default}" -i "_EER.eer" DIR_1_SUFFIX
read -ep "${magenta}Second directory to compare with (e.g. /path/to/dir2): ${default}" DIR_2
read -ep "${magenta} ... suffix to truncate in directory #2 (e.g. '.mrc'): ${default}" -i ".mrc" DIR_2_SUFFIX

echo

############ Logical tests to make sure user has defined all necessary variables
if [ -z "$DIR_1" ]; then
      echo "${red}No input directory #1 given. ${default}" ; exit
fi

if [ ! -d "$DIR_1" ]; then
      echo "${red}Input directory #1 (${DIR_1}) is not a directory, check your input path. ${default}" ; exit
fi

if [ -z "$DIR_2" ]; then
      echo "${red}No input directory #2 given. ${default}" ; exit
fi

if [ ! -d "$DIR_2" ]; then
      echo "${red}Input directory #2 (${DIR_2}) is not a directory, check your input path. ${default}" ; exit
fi

## initialize a container to hold mismatches for each directory 
dir_1_unique=()
dir_2_unique=()

## compare DIR_1 to DIR_2 and find all files unique to DIR_1 
for f in $(ls $DIR_1); do
    ## extract the basename of the file (i.e. file with suffix removed)
    PREFIX_LENGTH=$((${#f} - ${#DIR_1_SUFFIX}))
    F_BASENAME=${f:0:$PREFIX_LENGTH}
    ## calculate the expected name of the file in the second directory by appending its suffix 
    EXPECTED_FNAME=${F_BASENAME}${DIR_2_SUFFIX}
    ## do a logic check if there exists a file in the target directory
    if [ -f "${DIR_2}/${EXPECTED_FNAME}" ]; then
        continue 
    else 
        dir_1_unique+=("$f")
    fi
done

## compare DIR_2 to DIR_1 and find all files unique to DIR_2 
for f in $(ls $DIR_2); do
    ## extract the basename of the file (i.e. file with suffix removed)
    PREFIX_LENGTH=$((${#f} - ${#DIR_2_SUFFIX}))
    F_BASENAME=${f:0:$PREFIX_LENGTH}
    ## calculate the expected name of the file in the second directory by appending its suffix 
    EXPECTED_FNAME=${F_BASENAME}${DIR_1_SUFFIX}
    ## do a logic check if there exists a file in the target directory
    if [ -f "${DIR_1}/${EXPECTED_FNAME}" ]; then
        continue 
    else 
        dir_2_unique+=("$f")
    fi
done

## need to handle empty arrays in case there is no difference 
if [ ${#dir_1_unique[*]} == 0 ]; then
    echo "====================================================================="
    echo "  DIR #1 HAS NO UNIQUE FILES"
    echo "  path = ${DIR_1}"
    echo "====================================================================="
    echo 
else
    echo "====================================================================="
    echo "  ${#dir_1_unique[*]} FILES UNIQUE TO DIR #1"
    echo "  path = ${DIR_1}"
    echo "---------------------------------------------------------------------"
    for f in "${dir_1_unique[@]}"; do
        echo "  $f"
    done
    echo "====================================================================="
    echo 
fi

if [ ${#dir_2_unique[*]} == 0 ]; then
    echo "====================================================================="
    echo "  DIR #2 HAS NO UNIQUE FILES"
    echo "  path = ${DIR_2}"
    echo "====================================================================="
    echo 
else
    echo "====================================================================="
    echo "  ${#dir_2_unique[*]} FILES UNIQUE TO DIR #2"
    echo "  path = ${DIR_2}"
    echo "---------------------------------------------------------------------"
    for f in "${dir_2_unique[@]}"; do
        echo "  $f"
    done
    echo "====================================================================="
    echo 
fi

