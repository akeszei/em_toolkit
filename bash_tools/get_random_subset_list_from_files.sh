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


## Set a trap to terminate running loops (SIGINT) and processes (SIGTERM) with control+C
trap "echo; echo '${red}Script terminated by user.${default}'; exit;" SIGINT SIGTERM
## Automatically terminate script if any variables are undefined
set -eu

############ Designate SOURCE and DEST paths
read -ep "${magenta}Full path with glob string for files to consider (e.g. /path/to/*_doseweighted.mrc): ${default}" -i "$HOME/Downloads/test_dir/*.test" GLOB_CMD
read -ep "${magenta}Size of subset needed (e.g. 100): ${default}" -i "100" NUM_FILES_NEEDED
read -ep "${magenta}Output file name: ${default}" -i "subset.txt" OUTPUT_FNAME
echo

############ Logical tests to make sure user has defined all necessary variables
if [ -z "$GLOB_CMD" ]; then
      echo "${red}Glob string not correct. Exit${default}" ; exit
fi

if [ -z "$NUM_FILES_NEEDED" ]; then
      echo "${red}Subset size not given. Exit.${default}" ; exit
fi

## Get the list of files using the glob matching 
file_list=($GLOB_CMD)
echo " ... ${#file_list[@]} files found with glob cmd = ${GLOB_CMD}"

## Set the range based on the number of files that match 
RANDOM_NUMBER_RANGE=${#file_list[@]}
## Sanity check that number is not greater than the subset value given
if (( $RANDOM_NUMBER_RANGE <= $NUM_FILES_NEEDED )); then
    echo "${red}The number of files in glob string found is less than or equal to the subset size given (i.e. ${RANDOM_NUMBER_RANGE} <= ${NUM_FILES_NEEDED})! Exit.${default}"
    exit 
fi

## initialize the array to hold the random number list 
SELECTED_NUMBERS=()

for ((i=0; i<${NUM_FILES_NEEDED}; i++))
do
    #echo "Getting random number at index $i"
    number=$((RANDOM%RANDOM_NUMBER_RANGE))
    #echo " --> $number"
    SELECTED_NUMBERS+=("$number")
done

echo " ... ${#SELECTED_NUMBERS[@]} random numbers generated: (${SELECTED_NUMBERS[0]}, ${SELECTED_NUMBERS[1]}, ..., ${SELECTED_NUMBERS[-1]})"

counter=0

for (( counter=1; counter<=${#SELECTED_NUMBERS[@]}; counter++ ))
do 
    selected_file=${file_list[((counter - 1))]}
    #echo "$counter --> $selected_file"
    if (($counter == 1)); then
        # echo "First entry"
        echo $selected_file > $OUTPUT_FNAME
    else
        # echo "append"
        echo $selected_file >> $OUTPUT_FNAME
    fi
done

echo
echo "Done. Written $((counter-1)) files to: $OUTPUT_FNAME"
exit 0