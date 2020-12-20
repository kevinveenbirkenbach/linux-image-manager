#!/bin/bash
# shellcheck disable=SC1090  # Can't follow non-constant source. Use a directive to specify location.
# shellcheck disable=SC2154  # Referenced but not assigned
source "$(dirname "$(readlink -f "${0}")")/base.sh" || (echo "Loading base.sh failed." && exit 1)
echo "Automount encrypted storages"
echo
set_device_mount_partition_and_mapper_paths

create_luks_key_and_update_cryptab "$mapper_name" "$partition_path"

update_fstab "$mapper_path" "$mount_path"

success "Installation finished. Please restart :)"
