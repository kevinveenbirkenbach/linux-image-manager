#!/bin/bash
# @see https://stackoverflow.com/questions/32408820/how-to-list-files-and-match-first-line-in-bash-script
# @see https://unix.stackexchange.com/questions/298590/using-find-non-recursively
# @see https://security.stackexchange.com/questions/129724/how-to-check-if-an-ssh-private-key-has-passphrase-or-not
find "$HOME/.ssh" -maxdepth 1 -type f -print0 | while IFS= read -r -d $'\0' file; do
  if [[ $(head -n1 "$file") == "-----BEGIN OPENSSH PRIVATE KEY-----" ]]; then
      echo "Test file: $file"
      ssh-keygen -y -P "" -f "$file"
  fi
done
