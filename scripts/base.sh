#!/bin/bash
#
# This script contains the global program variables and functions
# @author Kevin Veen-Birkenbach [aka. Frantz]
#
# shellcheck disable=SC2034 #Deactivate checking of unused variables
REPOSITORY_PATH=$(readlink -f "$(dirname "$(readlink -f "${0}")")/../")
ENCRYPTED_PATH="$REPOSITORY_PATH/.encrypted";
DECRYPTED_PATH="$REPOSITORY_PATH/decrypted";
SCRIPT_PATH="$REPOSITORY_PATH/scripts";
DATA_PATH="$DECRYPTED_PATH/data";
BACKUP_PATH="$DECRYPTED_PATH/backup";
TEMPLATE_PATH="$REPOSITORY_PATH/templates";
LOCAL_REPOSITORIES_PATH="$HOME/Documents/repositories";
declare -a BACKUP_LIST=("$HOME/.ssh/" \
  "$HOME/.gitconfig" \
  "$HOME/.atom/config.cson" \
  "$HOME/Documents/certificates/" \
  "$HOME/Documents/recovery_codes/" \
  "$HOME/Documents/identity/" \
  "$HOME/Documents/passwords/" \
  "$HOME/.local/share/rhythmbox/rhythmdb.xml" \
  "$HOME/.config/keepassxc/keepassxc.ini");
