#!/usr/bin/env bash 

echo "======================================================================================================"
echo " Script to easily find movies not present in a given file: "
echo "    $ find_missing_movies.sh  <txt_file_with_fnames_to_skip>  /path/to/search/dir "
echo " The reference text file should have only the name of the movie in full (no path data)"
echo "======================================================================================================"

txt_path=$1
search_path=$2

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
