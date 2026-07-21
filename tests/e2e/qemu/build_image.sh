#!/bin/bash
# Build a QEMU-bootable, LUKS-encrypted image that reproduces lim's Tor
# unlock stack: the REAL initcpio files from lim/configuration/initcpio/,
# the tor hook wired between netconf and dropbear, offline onion keys, and
# a boot-ok marker service. Boots on a virtio machine (we model the stack,
# not the Raspberry Pi board, whose USB-gadget net QEMU cannot emulate).
#
# Needs root (loop device, cryptsetup, chroot). To keep a host rootless,
# run this inside a throwaway VM — see tests/e2e/qemu/README.md.
#
# Required environment:
#   WORK_DIR      writable scratch directory (outputs land here)
#   REPO_ROOT     linux-image-manager checkout (for the real initcpio files)
#   ARCH          x86_64 (default) or aarch64
#   PASSPHRASE    LUKS passphrase the harness will send over Tor
#   SSH_PUBKEY    path to the public key authorized for dropbear
#
# Writes $WORK_DIR/image.env with LUKS_UUID / MAPPER_NAME / KERNEL / INITRAMFS
# / IMAGE for the Python harness to consume.

set -euo pipefail

: "${WORK_DIR:?set WORK_DIR}"
: "${REPO_ROOT:?set REPO_ROOT}"
: "${PASSPHRASE:?set PASSPHRASE}"
: "${SSH_PUBKEY:?set SSH_PUBKEY}"
ARCH="${ARCH:-x86_64}"
MAPPER_NAME="cryptroot"

ROOTFS="$WORK_DIR/rootfs"
IMAGE="$WORK_DIR/image.raw"
INITCPIO_SRC="$REPO_ROOT/lim/configuration/initcpio"

case "$ARCH" in
  x86_64)  KERNEL_PKG=linux; CONSOLE=ttyS0 ;;
  aarch64) KERNEL_PKG=linux; CONSOLE=ttyAMA0 ;;
  *) echo "Unsupported ARCH: $ARCH" >&2; exit 2 ;;
esac

banner() { printf "\n========== %s ==========\n" "$1"; }

cleanup() {
  set +e
  mountpoint -q "$WORK_DIR/mnt" && umount -R "$WORK_DIR/mnt"
  [ -e "/dev/mapper/$MAPPER_NAME" ] && cryptsetup close "$MAPPER_NAME"
  [ -n "${LOOP:-}" ] && losetup -d "$LOOP"
}
trap cleanup EXIT

banner "bootstrapping rootfs with pacstrap"
mkdir -p "$ROOTFS"
# -c reuses the host package cache (fast). If a cached package is corrupt,
# clear it first: sudo rm -f /var/cache/pacman/pkg/<pkg>-*.pkg.tar.zst*
# A file of blank lines on stdin takes the default answer for every provider
# and confirmation prompt (e.g. the `linux` virtual package), keeping the
# bootstrap non-interactive without the SIGPIPE/pipefail pitfalls of `yes`.
printf '\n%.0s' $(seq 100) > "$WORK_DIR/pacman-answers"
pacstrap -c "$ROOTFS" \
  base "$KERNEL_PKG" mkinitcpio cryptsetup \
  busybox tor openssh \
  mkinitcpio-utils mkinitcpio-netconf mkinitcpio-dropbear \
  < "$WORK_DIR/pacman-answers"

banner "configuring mkinitcpio (virtio modules, tor between netconf/dropbear)"
# No `autodetect`: it narrows the initramfs to the *build host's* modules and
# would strip the virtio drivers the guest VM needs for early networking.
cat > "$ROOTFS/etc/mkinitcpio.conf" <<EOF
MODULES=(virtio_pci virtio_blk virtio_net)
BINARIES=(/usr/lib/libgcc_s.so.1)
FILES=()
HOOKS=(base udev modconf keyboard block ptsmount netconf tor dropbear encryptssh filesystems fsck)
EOF

banner "adding a devpts-mount hook (dropbear needs a PTY for encryptssh)"
# Without a mounted devpts, dropbear cannot allocate /dev/pts/0, so the
# interactive encryptssh passphrase prompt never runs and the SSH session
# just exits ("TIOCSCTTY: Input/output error", "/dev/pts/0: No such file").
cat > "$ROOTFS/etc/initcpio/install/ptsmount" <<'EOF'
#!/bin/bash
build() { add_runscript; }
help() { echo "Mount devpts so dropbear can allocate PTYs for encryptssh."; }
EOF
cat > "$ROOTFS/etc/initcpio/hooks/ptsmount" <<'EOF'
#!/usr/bin/ash
run_hook() {
    mkdir -p /dev/pts
    mount -t devpts devpts /dev/pts -o mode=620,gid=5,ptmxmode=666 2>/dev/null
    [ -e /dev/ptmx ] || ln -s /dev/pts/ptmx /dev/ptmx
}
EOF

banner "installing the real lim initcpio files"
install -D -m0644 "$INITCPIO_SRC/tor_install" "$ROOTFS/etc/initcpio/install/tor"
install -D -m0644 "$INITCPIO_SRC/tor_hook"    "$ROOTFS/etc/initcpio/hooks/tor"
install -D -m0644 "$INITCPIO_SRC/torrc"       "$ROOTFS/etc/tor/initramfs-torrc"

if [ -n "${TOR_TEST_NETWORK_CONF:-}" ]; then
  banner "wiring the image to a private (chutney) Tor network"
  cat "$TOR_TEST_NETWORK_CONF" >> "$ROOTFS/etc/tor/initramfs-torrc"
fi

banner "generating onion keys offline"
install -d -m0700 "$ROOTFS/etc/tor/initramfs-onion"
: > "$WORK_DIR/keygen-torrc"
tor -f "$WORK_DIR/keygen-torrc" --DisableNetwork 1 \
    --DataDirectory "$WORK_DIR/keygen-data" \
    --HiddenServiceDir "$ROOTFS/etc/tor/initramfs-onion" \
    --HiddenServicePort "22 127.0.0.1:22" \
    --SocksPort 0 --RunAsDaemon 0 --Log "notice stderr" &
keygen_pid=$!
for _ in $(seq 1 30); do
  [ -s "$ROOTFS/etc/tor/initramfs-onion/hostname" ] && break
  sleep 1
done
kill "$keygen_pid" 2>/dev/null || true
ONION_ADDRESS="$(cat "$ROOTFS/etc/tor/initramfs-onion/hostname")"

banner "authorizing the ssh key for dropbear"
install -D -m0600 "$SSH_PUBKEY" "$ROOTFS/etc/dropbear/root_key"

banner "baking the boot-ok marker service"
cat > "$ROOTFS/etc/systemd/system/lim-boot-ok.service" <<'EOF'
[Unit]
Description=Signal a successful LUKS-unlock boot to the serial console
After=multi-user.target
[Service]
Type=oneshot
ExecStart=/bin/sh -c 'echo LIM_UNLOCK_BOOT_OK > /dev/console'
[Install]
WantedBy=multi-user.target
EOF
ln -sf /etc/systemd/system/lim-boot-ok.service \
  "$ROOTFS/etc/systemd/system/multi-user.target.wants/lim-boot-ok.service"
ln -sf "/usr/lib/systemd/system/getty@.service" \
  "$ROOTFS/etc/systemd/system/getty.target.wants/getty@$CONSOLE.service"

banner "generating the initramfs"
# arch-chroot binds /proc, /sys, /dev itself; no pre-mount needed.
arch-chroot "$ROOTFS" mkinitcpio -P

banner "creating the LUKS image"
truncate -s 4G "$IMAGE"
LOOP="$(losetup -f --show "$IMAGE")"
# Cap the argon2 memory so the unlock fits in the guest's RAM (see QemuSpec).
printf '%s' "$PASSPHRASE" | cryptsetup luksFormat --type luks2 --batch-mode \
  --pbkdf-memory 262144 "$LOOP" -
LUKS_UUID="$(cryptsetup luksUUID "$LOOP")"
printf '%s' "$PASSPHRASE" | cryptsetup open "$LOOP" "$MAPPER_NAME" -
mkfs.ext4 -q "/dev/mapper/$MAPPER_NAME"

banner "copying the rootfs into the encrypted volume"
mkdir -p "$WORK_DIR/mnt"
mount "/dev/mapper/$MAPPER_NAME" "$WORK_DIR/mnt"
cp -a "$ROOTFS/." "$WORK_DIR/mnt/"
echo "/dev/mapper/$MAPPER_NAME / ext4 defaults,noatime 0 1" > "$WORK_DIR/mnt/etc/fstab"
# Kernel/initramfs filenames differ per distro (Arch: vmlinuz-linux /
# initramfs-linux.img; Manjaro: vmlinuz-6.1-x86_64 / initramfs-6.1-x86_64.img).
# Discover them instead of hard-coding, and skip the larger fallback image.
KERNEL_IMG="$(find "$ROOTFS/boot" -maxdepth 1 -name 'vmlinuz-*' | sort | head -1)"
INITRAMFS_IMG="$(find "$ROOTFS/boot" -maxdepth 1 -name 'initramfs-*.img' \
  ! -name '*fallback*' | sort | head -1)"
[ -n "$KERNEL_IMG" ] || { echo "No kernel image in $ROOTFS/boot" >&2; exit 1; }
[ -n "$INITRAMFS_IMG" ] || { echo "No initramfs in $ROOTFS/boot" >&2; exit 1; }
echo "Using kernel $KERNEL_IMG and initramfs $INITRAMFS_IMG"
cp "$KERNEL_IMG" "$WORK_DIR/kernel"
cp "$INITRAMFS_IMG" "$WORK_DIR/initramfs"
sync
umount -R "$WORK_DIR/mnt"
cryptsetup close "$MAPPER_NAME"
losetup -d "$LOOP"
LOOP=""

banner "writing image.env"
cat > "$WORK_DIR/image.env" <<EOF
LUKS_UUID=$LUKS_UUID
MAPPER_NAME=$MAPPER_NAME
ONION_ADDRESS=$ONION_ADDRESS
IMAGE=$IMAGE
KERNEL=$WORK_DIR/kernel
INITRAMFS=$WORK_DIR/initramfs
EOF
echo "Build complete. Onion address: $ONION_ADDRESS"
