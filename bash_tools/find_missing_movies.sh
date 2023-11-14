#!/usr/bin/env bash 

echo "======================================================================================================"
echo " The goal of this script is to quickly figure out which movies were not transferred to disk in the "
echo " rare case where the initial HDD filled up during data collection. Running this script with a list " 
echo " of the movies on the HDD will return a new list of the movies that remain on the camera server in "
echo " the form of a text file: 'missing_movies.txt'. You can then use that list to iteratively transfer "
echo " the movies using a bash one-liner."
echo " Usage:"
echo "    $ find_missing_movies.sh  <txt_file>  /path/to/EPU/dir "
echo "------------------------------------------------------------------------------------------------------"
echo " The reference text file should have only the name of each movie in full (no path data), e.g.:"
echo "     FoilHole_#######_Data_#####_#####_#####_#####_EER.eer"
echo "     ... "
echo " You can generate such a file from a disk containing a partial transfer via:"
echo "    $ cd /path/to/HDD/EPU/dir"
echo '    $ for f in $(find -name *EER.eer); do echo ${f##*/} >> already_transferred.txt; done'
echo "======================================================================================================"

######################################################################
## Check the user supplied expected arguments
if [ -z "$1" ]; then
    echo " ERROR :: No input text file was supplied as the first argument"
    exit 1
fi

if [ -z "$2" ]; then
    echo " ERROR :: No EPU directory was supplied as the second argument"
    exit 1
fi


txt_path=$1
search_path=$2
######################################################################


set +e # prevent exiting the script on error, needed for array matching function

containsElement() {
    local e match="$1"
    shift 
    for e; do [[ "$e" == "$match" ]] && return 0; done 
    return 1
}

######################################################################
## EXTRACT DATA FROM TXT FILE 
######################################################################


movie_suffix='EER.eer'
## Populate a list of files in the text file we were given 
files_from_txt=()
for f in $(cat $txt_path); do 
    min_fname_size=${#movie_suffix}

    ## STEP 1: only take inputs that are sufficiently long to be a match 
    if [ "${#f}" -gt "$min_fname_size" ]; then 
        
        ## STEP 2: only take inputs with the proper suffix match 
        suffix_chars=${f:(-${min_fname_size})}
        if [ "$suffix_chars" = $movie_suffix ]; then
            # echo " >> " ${f}

            ## STEP 3: add file to the array 
            files_from_txt+=("$f")
        fi
    fi

done

## For debugging, can directly read the array:
# for i in ${files_from_txt[@]}; do echo $i; done 

######################################################################


######################################################################
## FIND THE MOVIES THAT ARE MISSING FROM THE TEXT FILE VS. THE SEARCH DIRECTORY
######################################################################

search_dir_size=$(find $search_path -name *${movie_suffix} | wc -l)
echo " Movies found in search dir : $search_dir_size"

echo " Movies found in text file : ${#files_from_txt[@]}"

missing_files=()
## Iterate over each movie found in the search directory 
for j in $(find $search_path -name *${movie_suffix}); do
    ## extract the basename of the file 
    j_basename=${j##*/}
    ## check if the movie exists in the rejection array 
    containsElement "$j_basename" "${files_from_txt[@]}"
    ## check the exit code to determine the match (0 == match, 1 == no match)
    if [ $? = 1 ]; then
        # echo "new file to copy: $j_basename"
        missing_files+=("$j_basename")
    fi
done

echo " Movies to be transferred : ${#missing_files[@]}"

## For debugging, can directly read the array:
# for i in ${missing_files[@]}; do echo $i; done 

######################################################################


######################################################################
## ITERATE OVER THE ARRAY TO WRITE A TEXT FILE 
######################################################################
output_fname="missing_movies.txt"

for k in "${missing_files[@]}"; do 
    echo $k >> $output_fname
done 

echo " ... written missing movies into file: ${output_fname}"

echo 
echo " Use the output file to selectively copy the missing movies to a target drive, for example:"
echo '    $ dest='/path/to/save'; for f in $(cat missing_movies.txt); do path=$(find -name $f); scp -v $path $dest; done'

######################################################################
