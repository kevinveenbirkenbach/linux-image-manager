#!/bin/bash
# shellcheck disable=SC1090  # Can't follow non-constant source. Use a directive to specify location.
# shellcheck disable=SC2154  # Referenced but not assigned
source "$(dirname "$(readlink -f "${0}")")/base.sh" || (echo "Loading base.sh failed." && exit 1)
info "Automount raid1 encrypted storages..." &&
set_raid1_devices_mount_partition_and_mapper_paths &&
create_luks_key_and_update_cryptab "$mapper_name_1" "$device_path_1" &&
create_luks_key_and_update_cryptab "$mapper_name_2" "$device_path_2" &&
update_fstab "$mapper_path_1" "$mount_path_1" &&
success "Installation finished. Please restart :)" ||
error
