#!/bin/bash

## This script takes the postprocessing/boundaryProbes
## data and organizes it in simpler files for handling.
##
## ./pointFiles.sh <pathToFolder> <pathToDestination>
##
## Example
## ./pointFiles.sh CASE/postProcessing/boundaryProbes
##
## Added to the espuma project
##

INPUT_DIR=$1
OUTPUT_DIR=$2

# Reset output directory
rm -rf $OUTPUT_DIR
mkdir -p $OUTPUT_DIR


# Create a time file
TIME_FILE=$OUTPUT_DIR/time.txt
rm -f $TIME_FILE

TIMES=$(ls -v $INPUT_DIR)
LEN_TIMES=${#TIMES[@]}

echo $TIMES > $TIME_FILE
sed -i "s/ /\n/g" $TIME_FILE

# Create a coordinates file
COORD_FILE=$OUTPUT_DIR/xyz.txt
rm -f $COORD_FILE

## Pick some random time to get the coordinates
RAND_FOLDER=$INPUT_DIR/$(ls -v $INPUT_DIR | shuf -n 1)

## This should return one of the .xy files
RAND_FILE=$RAND_FOLDER/$(ls -v $RAND_FOLDER | shuf -n 1)
sed -e "s/\s\s*/ /g" $RAND_FILE | cut -d " " -f 1,2,3 > $COORD_FILE

## Save the list of point_$FIELDS.xy
FIELDS=$(ls -v $RAND_FOLDER)
# echo $FIELDS

# Read each time and generate a pressure array
# with each timestep as rows and coords points as cols

for FIELD in $FIELDS
  do

  OUT_FIELD_FILE=$OUTPUT_DIR/$FIELD
  rm -f $OUT_FIELD_FILE
  
  for T in $TIMES
  do
    P_FILE=$INPUT_DIR/$T/$FIELD
    sed -e "s/\s\s*/ /g" $P_FILE | cut --complement -d " " -f 1,2,3 | tr '\n' ' ' >> $OUT_FIELD_FILE
    echo "" >> $OUT_FIELD_FILE
  done

  sed -i "s/ $//g" $OUT_FIELD_FILE
  
#   echo "Processed $FIELD !"

done
