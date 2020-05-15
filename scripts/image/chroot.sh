#!/bin/bash
# shellcheck source=/dev/null # Deactivate SC1090
# shellcheck disable=SC2015  # Deactivating bool hint
source "$(dirname "$(readlink -f "${0}")")/base.sh" || (echo "Loading base.sh failed." && exit 1)

info "Starting chroot..."

set_device_path

make_working_folder

make_mount_folders

set_partition_paths

mount_partitions

mount_binds

info "ld.so.preload fix" &&
sed -i 's/^/#CHROOT /g' "$root_mount_path""etc/ld.so.preload" ||
warning "Failed."

info "Copy qemu binary..." &&
cp -v /usr/bin/qemu-arm-static "$root_mount_path""usr/bin/" ||
error

info "Copy resolve.conf..."
cp -v /etc/resolv.conf "$root_mount_path""etc/" &&
warning "Failed. Propably there is no internet connection available."

info "You will be transferred to the bash shell now." &&
info "Issue 'exit' when you are done." &&
info "Issue 'su pi' if you need to work as the user pi." &&
info "chroot to raspbian" &&
chroot "$root_mount_path" /bin/bash ||
error

info "Clean up" &&
info "revert ld.so.preload fix" &&
sed -i 's/^#CHROOT //g' "$root_mount_path""etc/ld.so.preload" ||
warning "Failed."

info "unmount everything" &&
umount "$root_mount_path"/{dev/pts,dev,sys,proc,boot,} ||
error
