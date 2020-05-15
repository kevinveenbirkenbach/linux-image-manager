#!/bin/bash
# shellcheck source=/dev/null # Deactivate SC1090
# shellcheck disable=SC2015  # Deactivating bool hint
source "$(dirname "$(readlink -f "${0}")")/../base.sh" || (echo "Loading base.sh failed." && exit 1)

info "Making mount dir..." &&
mkdir -p /mnt/raspbian ||
error

info "Mount partitions..."
mount -o rw "$1""2"  /mnt/raspbian &&
mount -o rw "$1""1" /mnt/raspbian/boot ||
error

info "Mount binds..." &&
mount --bind /dev /mnt/raspbian/dev/ &&
mount --bind /sys /mnt/raspbian/sys/ &&
mount --bind /proc /mnt/raspbian/proc/ &&
mount --bind /dev/pts /mnt/raspbian/dev/pts ||
error

info "ld.so.preload fix" &&
sed -i 's/^/#CHROOT /g' /mnt/raspbian/etc/ld.so.preload ||
error

info "copy qemu binary" &&
cp -v /usr/bin/qemu-arm-static /mnt/raspbian/usr/bin/ ||
error

info "You will be transferred to the bash shell now." &&
info "Issue 'exit' when you are done." &&
info "Issue 'su pi' if you need to work as the user pi." &&
info "chroot to raspbian" &&
chroot /mnt/raspbian /bin/bash ||
error

info "Clean up" &&
info "revert ld.so.preload fix" &&
sed -i 's/^#CHROOT //g' /mnt/raspbian/etc/ld.so.preload ||
error

info "unmount everything" &&
umount /mnt/raspbian/{dev/pts,dev,sys,proc,boot,} ||
error
