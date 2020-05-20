#!/bin/bash
source "$(dirname "$(readlink -f "${0}")")/base.sh" || (echo "Loading base.sh failed." && exit 1)
echo "Automount encrypted storages"
echo
set_device_mount_and_mapper_paths

secret_key_path="/etc/luks-keys/$mapper""_name_secret_key" &&
info "Generate secret key under: $secret_key_path" &&
dd if=/dev/urandom of=$secret_key_path bs=512 count=8 &&
sudo cryptsetup -v luksAddKey $device_path $secret_key_path ||
error

info "Opening and closing device to verify that that everything works fine..." &&
sudo cryptsetup -v luksOpen $device_path $mapper_name --key-file=$secret_key_path &&
sudo cryptsetup -v luksClose $mapper_name ||
error

uuid_line=$(sudo cryptsetup luksDump $device_path | grep "UUID")
uuid=$(uuid_line "${test/UUID:/""}"|sed -e "s/[[:space:]]\+//g")
crypttab_path="/etc/crypttab"
if grep -q "$uuid" "$crypttab_path"; then
  error "File $crypttab_path contains allready a string with the UUID:$uuid"
fi
"$mapper_name UUID=$uuid $secret_key_path luks" >> $crypttab_path

info "The file $crypttab_path contains the following:" &&
sudo cat $crypttab_path ||
error

info "Verifying crypttab configuration..." &&
sudo cryptdisks_start $mapper_name ||
error

fstab_path="/etc/fstab"
if grep -q "$uuid" "f$stab_path"; then
  error "File $fstab_path contains allready a string with the UUID:$uuid"
fi
"$mapper_path $mount_path btrfs   defaults   0       2" >> $fstab_path ||
error

info "The file $crypttab_path contains the following:" &&
sudo cat $crypttab_path ||
error

success "Installation finished. Please restart :)"
