#!/bin/bash
# shellcheck source=/dev/null # Deactivate SC1090
# shellcheck disable=SC2015  # Deactivating bool hint
source "$(dirname "$(readlink -f "${0}")")/base.sh" || (echo "Loading base.sh failed." && exit 1)

info "Starting chroot..."

set_device_path

info "Making mount dir..." &&
mkdir -p /mnt/raspbian ||
error


root_mount_path="/mnt/raspbian"
boot_mount_path="/mnt/raspbian/boot"
root_partition_path=$(echo_partition_name "2")
boot_partition_path=$(echo_partition_name "1")

info "Mount partitions..."
mount -o rw "$boot_partition_path" "$boot_mount_path" ||
mount -o rw "$root_partition_path" "$root_mount_path"  &&
error

info "Mount binds..." &&
mount --bind /dev "$root_mount_path/dev/" &&
mount --bind /sys "$root_mount_path/sys/" &&
mount --bind /proc "$root_mount_path/proc/" &&
mount --bind /dev/pts "$root_mount_path/dev/pts" ||
error

info "ld.so.preload fix" &&
sed -i 's/^/#CHROOT /g' "$root_mount_path/etc/ld.so.preload" ||
error

info "copy qemu binary" &&
cp -v /usr/bin/qemu-arm-static "$root_mount_path/usr/bin/" ||
error

info "You will be transferred to the bash shell now." &&
info "Issue 'exit' when you are done." &&
info "Issue 'su pi' if you need to work as the user pi." &&
info "chroot to raspbian" &&
chroot "$root_mount_path" /bin/bash ||
error

info "Clean up" &&
info "revert ld.so.preload fix" &&
sed -i 's/^#CHROOT //g' "$root_mount_path/etc/ld.so.preload" ||
error

info "unmount everything" &&
umount "$root_mount_path"/{dev/pts,dev,sys,proc,boot,} ||
error
