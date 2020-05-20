#!/bin/bash
source "$(dirname "$(readlink -f "${0}")")/base.sh" || (echo "Loading base.sh failed." && exit 1)
echo "Automount encrypted storages"
echo
set_device_mount_partition_and_mapper_paths

info "Creating key luks-key-directory..." &&
key_directory="/etc/luks-keys/" &&
sudo mkdir $key_directory || warning "Directory exists: $key_directory"
luks_key_name="$mapper_name""_name_secret_key" &&
secret_key_path="$key_directory$luks_key_name" &&
info "Generate secret key under: $secret_key_path" &&
if [ -f "$secret_key_path" ]
  then
    warning "File allready exist. Overwritting!"
fi
sudo dd if=/dev/urandom of=$secret_key_path bs=512 count=8 &&
sudo cryptsetup -v luksAddKey $partition_path $secret_key_path ||
error

info "Opening and closing device to verify that that everything works fine..." &&
sudo cryptsetup -v luksOpen $partition_path $mapper_name --key-file=$secret_key_path &&
sudo cryptsetup -v luksClose $mapper_name ||
error

info "Reading UUID..."
uuid_line=$(sudo cryptsetup luksDump $partition_path | grep "UUID") &&
uuid=$(echo "${uuid_line/UUID:/""}"|sed -e "s/[[:space:]]\+//g") ||
error

crypttab_path="/etc/crypttab"
crypttab_entry="$mapper_name UUID=$uuid $secret_key_path luks"
info "Adding crypttab entry..."
if sudo grep -q "$crypttab_entry" "$crypttab_path";
  then
    warning "File $crypttab_path contains allready a the following entry:" &&
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

# info "Verifying crypttab configuration..." &&
# sudo cryptdisks_start $mapper_name ||
# error

fstab_path="/etc/fstab"
fstab_entry="$mapper_path $mount_path btrfs   defaults   0       2"
info "Adding fstab entry..."
if sudo grep -q "$fstab_entry" "$fstab_path"; then
  warning "File $crypttab_path contains allready a the following entry:" &&
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

success "Installation finished. Please restart :)"
