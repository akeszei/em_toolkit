## Initial script written: 2023-04-14

if [ $# -ne 3 ]; then
    echo "Usage:"
    echo "  Copy files that are missing from the partial_copy_dir relative to the full_data_dir"
    echo "  into a new target directory. Useful for copying data across multiple HDDs from a "
    echo "  single larger source. "
    echo "    $ copy_missing.sh  full_data_dir  partial_copy_dir  name_of_new_dir"
    echo "Example:"
    echo "    $ copy_missing.sh /Falcon4idata/Session/ /media/cryosparc_user/HDD1/Session /media/cryosparc_user/HDD2/Session_overflow"
    exit 0
fi


## establish directories 
MAIN_DIR=$1 
COPY_DIR_1=$2 
NEW_DIR=$3

## leading slash is vital so rsync only copies the contents of this directory, not the main directory itself
## this allows us to change the name of the parent directory 
if [ "${MAIN_DIR: -1}" != "/" ]; then
    MAIN_DIR="${MAIN_DIR}/"
fi

## Step 1
## Create a list of files that exist in the first copy session into memory 

echo "============================================"
echo " Determine files already present in: "
echo "     $COPY_DIR_1"

## remove any previous existing copy list file 
COPY_LIST_FNAME='already_copied.txt'
if [ -f "$COPY_LIST_FNAME" ]; then
    rm $COPY_LIST_FNAME
fi

## write out a new copy list into file, omitting the parent directory form the find call 
for f in $(find $COPY_DIR_1 -type f); do 
    f_relative=${f/$COPY_DIR_1/} # strip the parent folder so the path is relative to it (follows what rsync expects)
    echo $f_relative >> $COPY_LIST_FNAME
done 

COPY_DIR_1_FILE_NUM=$(cat $COPY_LIST_FNAME | wc -l)
echo "  >> ${COPY_DIR_1_FILE_NUM} files found"
echo "--------------------------------------------"

## Step 2 
## Use the copy list as an exlude option for rsync-ing to the new directory 
echo " Generated rsync command: "
echo "   $ rsync -varhu --exclude-from=$COPY_LIST_FNAME $MAIN_DIR $NEW_DIR"

read -p ">> Proceed? (y/n) " user_input 
if [ "$user_input" != "y" ] && [ "$user_input" != "yes" ] && [ "$user_input" != "Y" ] && [ "$user_input" != "Yes" ]; then 
    echo "User stopped script."
    exit 0;
fi

rsync -varhu --exclude-from=$COPY_LIST_FNAME $MAIN_DIR $NEW_DIR
