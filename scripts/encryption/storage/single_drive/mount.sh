#!/bin/bash
# shellcheck disable=SC1090  # Can't follow non-constant source. Use a directive to specify location.
# shellcheck disable=SC2015  # Deactivating bool hint
# shellcheck disable=SC2154  # Referenced but not assigned
source "$(dirname "$(readlink -f "${0}")")/base.sh" || (echo "Loading base.sh failed." && exit 1)
echo "Mounts encrypted storages"

set_device_mount_partition_and_mapper_paths

info "Unlock partition..." &&
sudo cryptsetup luksOpen "$partition_path" "$mapper_name" ||
error

info "Mount partition..." &&
sudo mount "$mapper_path" "$mount_path" ||
error

success "Mounting successfull :)"
