#!/bin/bash
#
# Imports data from the system
# @param $1 If the first parameter is "reverse" the data will be exported to the system
#
# shellcheck source=/dev/null # Deactivate SC1090
# shellcheck disable=SC2143  # Comparing with -z allowed
# shellcheck disable=SC2015  # Deactivating bool hint
source "$(dirname "$(readlink -f "${0}")")/../base.sh" || (echo "Loading base.sh failed." && exit 1)

declare -a BACKUP_LIST=("$HOME/.ssh/" \
  "$HOME/.gitconfig" \
  "$HOME/.atom/config.cson" \
  "$HOME/.local/share/rhythmbox/rhythmdb.xml" \
  "$HOME/.config/keepassxc/keepassxc.ini" \
  "$HOME/Documents/certificates/" \
  "$HOME/Documents/recovery_codes/" \
  "$HOME/Documents/identity/" \
  "$HOME/Documents/passwords/" \
  "$HOME/Documents/licenses/");
  
if [ -z "$(mount | grep "$DECRYPTED_PATH")" ]
  then
    info "The decrypted folder $DECRYPTED_PATH is locked. You need to unlock it!" &&
    bash "$SCRIPT_PATH""encryption/unlock.sh" || error "Unlocking failed.";
fi
if [ "$1" = "reverse" ]
  then
    MODE="export"
  else
    MODE="import"
fi
CONCRETE_BACKUP_FOLDER="$BACKUP_PATH/$MODE/$(date '+%Y%m%d%H%M%S')"
mkdir -p "$CONCRETE_BACKUP_FOLDER" || error "Failed to create \"$CONCRETE_BACKUP_FOLDER\"."
for system_item_path in "${BACKUP_LIST[@]}";
do
    data_item_path="$DATA_PATH$system_item_path"
    if [ "$MODE" = "export" ]
      then
        destination="$system_item_path"
        source="$data_item_path"
        info "Export data from $source to $destination..."
      else
        source="$system_item_path"
        destination="$data_item_path"
        info "Import data from $source to $destination..."
    fi
    if [ -f "$destination" ]
      then
        info "The destination file allready exists!" &&
        info "Difference:" &&
        diff "$destination" "$source"
    fi
    destination_dir=$(dirname "$destination")
    mkdir -p "$destination_dir" || error "Failed to create \"$destination_dir\"."
    if [ -f "$source" ]
      then
        backup_dir=$(dirname "$CONCRETE_BACKUP_FOLDER/$system_item_path");
        mkdir -p "$backup_dir" || error "Failed to create \"$backup_dir\"."
        info "Copy data from $source to $destination..."
        rsync -abcEPuvW --backup-dir="$backup_dir" "$source" "$destination" || error
      else
        if [ -d "$source" ]
          then
            mkdir -p "$destination" || error "Failed to create \"$destination\"."
            backup_dir="$CONCRETE_BACKUP_FOLDER/$system_item_path";
            mkdir -p "$backup_dir" || error "Failed to create \"$backup_dir\"."
            info "Copy data from directory $source to directory $destination..."
            rsync -abcEPuvW --delete --backup-dir="$backup_dir" "$source" "$destination" || error
          else
            warning "$source doesn't exist. Copying data is not possible."
        fi
    fi
done
