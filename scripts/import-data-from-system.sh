#!/bin/bash
# Imports data from the system
# @author Kevin Veen-Birkenbach [aka. Frantz]
# @param $1 If the first parameter is "reverse" the data will be exported to the system
DATA_FOLDER="$(dirname "$(readlink -f "${0}")")/../data";
BACKUP_LIST=("$HOME/.ssh/") #,"$HOME/.gitconfig");
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
    echo "Trying to copy data from $source to $destination..."
    if [ -f "$destination" ]
      then
        echo "The destination file allready exists!";
        echo "Difference:"
        diff $destination $source
    fi
    destination_dir=$(dirname $destination)
    mkdir -p "$destination_dir"
    if [ -f "$source" ]
      then
        echo "Copy data from $source to $destination..."
        cp -vi "$source" "$destination"
      else
        if [ -d "$source" ]
        then
          echo "Copy data from directory $source to directory $destination_dir..."
          cp -vir "$source" "$destination_dir"
        else
          echo "$source doesn't exist. Copying data is not possible."
      fi
    fi
done
