#!/bin/bash
# shellcheck disable=SC1090  # Can't follow non-constant source. Use a directive to specify location.
# shellcheck disable=SC2154  # Referenced but not assigned
# shellcheck disable=SC2015 #Deactivate bool hint
source "$(dirname "$(readlink -f "${0}")")/base.sh" || (echo "Loading base.sh failed." && exit 1)
info "Activate Automount raid1 encrypted storages..." &&
echo ""
for dev in $(lsblk -dno NAME); do
    if sudo cryptsetup isLuks /dev/$dev 2>/dev/null; then
        info "/dev/$dev is a LUKS encrypted storage device."
    fi
done
set_raid1_devices_mount_partition_and_mapper_paths &&
create_luks_key_and_update_cryptab "$mapper_name_1" "$device_path_1" &&
info "Creating mount folder unter \"$mount_path_1\"..." &&
sudo mkdir -vp "$mount_path_1" &&
create_luks_key_and_update_cryptab "$mapper_name_2" "$device_path_2" &&
update_fstab "$mapper_path_1" "$mount_path_1" &&
success "Installation finished. Please restart :)" ||
error
