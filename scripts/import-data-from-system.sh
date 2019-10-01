#!/bin/bash
# Imports data from the system
# @author Kevin Veen-Birkenbach [aka. Frantz]
# @param $1 If the first parameter is "reverse" the data will be exported to the system
source "$(dirname "$(readlink -f "${0}")")/base.sh"
DATA_FOLDER=$ENCRYPTED
if [ -z "$(mount | grep $DATA_FOLDER)" ]
  then
    echo "The data folder $DATA_FOLDER is locked. You need to unlock it!"
    bash "$(dirname "$(readlink -f "${0}")")/unlock.sh" || exit 1;
fi
declare -a BACKUP_LIST=("$HOME/.ssh/" "$HOME/.gitconfig" "$HOME/.mozilla/firefox/" "$HOME/.atom/config.cson");
for system_item_path in "${BACKUP_LIST[@]}";
do
    data_item_path="$DATA_FOLDER$system_item_path"
    if [ "$1" = "reverse" ]
      then
        destination="$system_item_path"
        source="$data_item_path"
        echo "Export data from $source to $destination..."
      else
        source="$system_item_path"
        destination="$data_item_path"
        echo "Import data from $source to $destination..."
    fi
    if [ -f "$destination" ]
      then
        echo "The destination file allready exists!";
        echo "Difference:"
        diff "$destination" "$source"
    fi
    destination_dir=$(dirname "$destination")
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
