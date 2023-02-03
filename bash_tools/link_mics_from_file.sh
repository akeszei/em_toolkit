### A small script to link files matching a list of names (with extension) in a text file to a target directory.
### The explicit path of each file is discovered using the find function

ROOT_DIR=/data3/import/cryosparc_dir/
LINK_DIR=Micrographs/
COUNTER=0

echo "... running: link_mics_from_file.sh"

for mic in $(cat mics.txt); do

    F_PATH=$(find $ROOT_DIR -name $mic)
    ln -s $F_PATH $LINK_DIR
    ((COUNTER++))
done

echo " ... COMPLETE"
echo " >> linked $COUNTER files"
