#!/bin/bash
source "$(dirname "$(readlink -f "${0}")")/base.sh" || (echo "Loading base.sh failed." && exit 1)
echo "Mounts encrypted storages"

set_device_mount_partition_and_mapper_paths

info "Unlock partition..." &&
sudo cryptsetup luksOpen $partition_path $mapper_name ||
error

info "Mount partition..." &&
sudo mount $mapper_path $mount_path ||
error

success "Mounting successfull :)"