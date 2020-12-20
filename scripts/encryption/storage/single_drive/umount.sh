#!/bin/bash
source "$(dirname "$(readlink -f "${0}")")/base.sh" || (echo "Loading base.sh failed." && exit 1)
echo "Unmount encrypted storages"

set_device_mount_partition_and_mapper_paths

info "Unmount $mapper_path..."
sudo umount $mapper_path &&
sudo cryptsetup luksClose $mapper_path ||
error

success "Successfull :)"
