#!/bin/bash
# Imports data from the system
# @author Kevin Veen-Birkenbach [aka. Frantz]
# @param $1 If the first parameter is "reverse" the data will be exported to the system
DATA_FOLDER="./data";
BACKUP_LIST=("$HOME/.gitconfig");
for system_item_path in "${BACKUP_LIST[@]}";
do
    data_item_path="$DATA_FOLDER$BACKUP_LIST"
    if [ "$1" = "reverse" ]
      then
        destination="$system_item_path"
        source="$data_item_path"
      else
        source="$system_item_path"
        destination="$data_item_path"
    fi
    echo "Data will be copied from $source to $destination..."
    if [ -f "$destination" ]
      then
        echo "The destination file allready exists!";
        echo "Difference:"
        diff $destination $source
    fi
    destination_dir=$(dirname $destination)
    mkdir -p "$destination_dir"
    cp -vi "$source" "$destination"
done
