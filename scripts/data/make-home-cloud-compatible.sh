#!/bin/bash
#
# This script syncronizes home folders with the cloud
# @param $1 clouddomain.tld
#
directories=("Documents" "Pictures" "Music" "Books" "Videos");
for folder in "${directories[@]}"; do
  home_directory="$HOME/$folder";
  cloud_directory="$HOME/Clouds/$1/$folder";
  if [ -L "$home_directory" ]
    then
      if [ "$(readlink -f "$home_directory")" == "$(realpath "$cloud_directory")" ]
        then
          "Folder $home_directory is allready symlinked with $cloud_directory. Skipped.";
        else
          "ERROR: Folder $home_directory links to a wrong target. Solve manually!" && exit 1;
      fi
    else
      if [ -d "$cloud_directory" ]
        then
          mv --backup -v "$home_directory/"* "$cloud_directory/" &&
          rmdir -v "$home_directory" &&
          ln -vs "$cloud_directory" "$home_directory" &&
          echo "Folder $home_directory is now syncronized with cloud." || exit 1
        else
          echo "Directory $home_directory skipped, because it doesn't exist here $cloud_directory." &&
          echo "Please create $cloud_directory or syncronize the cloud folder!" && exit 1;
      fi
  fi
done
