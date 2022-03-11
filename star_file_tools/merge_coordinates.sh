#!/usr/bin/env bash

#### USAGE:
####   Run this script in a directory of .star files with particle coordinates (i.e. output
####   from crYOLO or select_into_manpick.py) to collate them all into one large file for
####   input into cryoSPARC as a single merged_coordinates.star file for the Import Particle
####   Stack job. Adjust this script as necessary to fit your custom situation.

### Prepare file and header
OUT_FNAME="merged_coordinates.star"
echo ' ' > $OUT_FNAME
echo 'data_' >> $OUT_FNAME
echo ' ' >> $OUT_FNAME
echo 'loop_' >> $OUT_FNAME
echo '_rlnMicrographName #1' >> $OUT_FNAME
echo '_rlnCoordinateX #2' >> $OUT_FNAME
echo '_rlnCoordinateY #3' >> $OUT_FNAME

### Read data from each star file and extract the X and Y coordinates
for STAR_FILE in *.star ; do
    # echo " Reading star file: $STAR_FILE"
    while IFS= read -r line; do
        # echo "Text read from file: $line"
        ### Use awk to grab column data, only if the line contains at least 4 columns (i.e. avoid header and empty lines)
        X=$(awk -F ' ' '{if (NF>3) {print $1}}' <<< $line)
        Y=$(awk -F ' ' '{if (NF>3) {print $2}}' <<< $line)

        ### if neither X nor Y is assigned, skip any further annotation
        if [ -z "${X}" ]; then
            # echo "No assigned x-coordinate"
            continue
        fi
        if [ -z "${Y}" ]; then
            # echo "No assigned y-coordinate"
            continue
        fi

        # echo "    ... coordinate found = $X, $Y"
        MIC_BASE_NAME=${STAR_FILE/.star/}
        printf "$MIC_BASE_NAME \t $X \t $Y \n" >> $OUT_FNAME
    done < $STAR_FILE
done
