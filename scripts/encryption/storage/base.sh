#!/bin/bash
# shellcheck disable=SC2015  # Deactivating bool hint
# shellcheck disable=SC2034  # Unused variables
# shellcheck disable=SC2154  # Referenced but not assigned
# shellcheck disable=SC1090  # Can't follow non-constant source. Use a directive to specify location.
# shellcheck disable=SC2001  # See if you can use ${variable//search/replace} instead
source "$(dirname "$(readlink -f "${0}")")/../../../base.sh" || (echo "Loading base.sh failed." && exit 1)

set_device_mount_partition_and_mapper_paths(){
  set_device_path &&
  mapper_name="encrypteddrive-$device" &&
  mapper_path="/dev/mapper/$mapper_name" &&
  mount_path="/media/$mapper_name" &&
  partition_path="$device_path""1" &&
  info "mapper name set to : $mapper_name" &&
  info "mapper path set to : $mapper_path" &&
  info "mount path set to : $mount_path" ||
  error
}

# @var $1 mapper_path
# @var $2 partition_path
create_luks_key_and_update_cryptab(){
  LUKS_KEY_DIRECTORY="/etc/luks-keys/"  &&
  info "Creating luks-key-directory..." &&
  sudo mkdir $LUKS_KEY_DIRECTORY || warning "Directory exists: $LUKS_KEY_DIRECTORY" || error
  luks_key_name="$1.keyfile" &&
  secret_key_path="$LUKS_KEY_DIRECTORY$luks_key_name" &&
  info "Generate secret key under: $secret_key_path" || error
  if [ -f "$secret_key_path" ]
    then
      warning "File allready exist. Overwritting!"
  fi
  sudo dd if=/dev/urandom of="$secret_key_path" bs=512 count=8 &&
  sudo cryptsetup -v luksAddKey "$2" "$secret_key_path" &&
  info "Opening and closing device to verify that that everything works fine..." || error
  sudo cryptsetup -v luksClose "$1" || info "No need to luksClose $1."
  sudo cryptsetup -v luksOpen "$2" "$1" --key-file="$secret_key_path" &&
  sudo cryptsetup -v luksClose "$1" &&
  info "Reading UUID..." &&
  uuid_line=$(sudo cryptsetup luksDump "$2" | grep "UUID") &&
  uuid=$(echo "${uuid_line/UUID:/""}"|sed -e "s/[[:space:]]\+//g") &&
  crypttab_path="/etc/crypttab" &&
  crypttab_entry="$1 UUID=$uuid $secret_key_path luks" &&
  info "Adding crypttab entry..." || error
  if sudo grep -q "$crypttab_entry" "$crypttab_path";
    then
      warning "File $crypttab_path contains allready the following entry:" &&
      echo "$crypttab_entry" &&
      info "Skipped." ||
      error
    else
      sudo sh -c "echo '$crypttab_entry' >> $crypttab_path" ||
      error
  fi

  info "The file $crypttab_path contains now the following:" &&
  sudo cat $crypttab_path ||
  error
}

# @var $1 mapper_name
# @var $2 mount_path
#
# If mount doesn't work adapt it manually to
# @see https://gist.github.com/MaxXor/ba1665f47d56c24018a943bb114640d7
update_fstab(){
  fstab_path="/etc/fstab"
  fstab_entry="$1 $2 btrfs   defaults   0       2"
  info "Adding fstab entry..."
  if sudo grep -q "$fstab_entry" "$fstab_path"; then
    warning "File $fstab_path contains allready a the following entry:" &&
    echo "$fstab_entry" &&
    info "Skipped." ||
    error
  else
    sudo sh -c "echo '$fstab_entry' >> $fstab_path" ||
    error
  fi

  info "The file $fstab_path contains now the following:" &&
  sudo cat $fstab_path ||
  error
}
