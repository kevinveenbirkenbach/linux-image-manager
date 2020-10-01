#!/bin/bash
# shellcheck source=/dev/null # Deactivate SC1090
# shellcheck disable=SC2015  # Deactivating bool hint
# shellcheck disable=SC2154  # Deactivate not referenced link
source "$(dirname "$(readlink -f "${0}")")/base.sh" || (echo "Loading base.sh failed." && exit 1)

info "Starting chroot..."

set_device_path

make_working_folder

make_mount_folders

set_partition_paths

decrypt_root

mount_partitions

mount_chroot_binds

copy_qemu

copy_resolve_conf

info "Bash shell starts..." &&
chroot "$root_mount_path" /bin/bash ||
error

destructor
