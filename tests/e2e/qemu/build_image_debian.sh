#!/bin/bash
# Build a QEMU-bootable, LUKS-encrypted Debian image that reproduces lim's Tor
# unlock stack for the initramfs-tools backend: the REAL hooks from
# lim/configuration/initramfs-tools/, cryptsetup-initramfs + dropbear-initramfs,
# offline onion keys, and a boot-ok marker service. Boots on a virtio machine
# (models the software stack, not the Raspberry Pi board).
#
# Debian amd64 on an x86_64 host — no qemu-user needed. Needs root (debootstrap,
# loop device, cryptsetup, chroot). See tests/e2e/qemu/README.md.
#
# Same env contract and image.env output as build_image.sh.

set -euo pipefail

: "${WORK_DIR:?set WORK_DIR}"
: "${REPO_ROOT:?set REPO_ROOT}"
: "${PASSPHRASE:?set PASSPHRASE}"
: "${SSH_PUBKEY:?set SSH_PUBKEY}"
SUITE="${DEBIAN_SUITE:-bookworm}"
MIRROR="${DEBIAN_MIRROR:-http://deb.debian.org/debian}"
MAPPER_NAME="cryptroot"

ROOTFS="$WORK_DIR/rootfs"
IMAGE="$WORK_DIR/image.raw"
HOOK_SRC="$REPO_ROOT/lim/configuration/initramfs-tools"

banner() { printf "\n========== %s ==========\n" "$1"; }

# Debian keeps tools in /usr/sbin, which an Arch host's PATH (merged /usr/bin)
# omits, so chroot can't find update-initramfs. Force a Debian-style PATH.
in_chroot() {
  chroot "$ROOTFS" /usr/bin/env \
    PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin "$@"
}

cleanup() {
  set +e
  for m in dev/pts dev proc sys; do
    mountpoint -q "$ROOTFS/$m" && umount -l "$ROOTFS/$m"
  done
  mountpoint -q "$WORK_DIR/mnt" && umount -R "$WORK_DIR/mnt"
  [ -e "/dev/mapper/$MAPPER_NAME" ] && cryptsetup close "$MAPPER_NAME"
  [ -n "${LOOP:-}" ] && losetup -d "$LOOP"
}
trap cleanup EXIT

banner "bootstrapping Debian rootfs with debootstrap ($SUITE)"
mkdir -p "$ROOTFS"
debootstrap --arch=amd64 --variant=minbase \
  --include=linux-image-amd64,cryptsetup,cryptsetup-initramfs,dropbear-initramfs,tor,busybox,systemd-sysv,udev,ifupdown,isc-dhcp-client \
  "$SUITE" "$ROOTFS" "$MIRROR"

banner "binding chroot filesystems"
cp /etc/resolv.conf "$ROOTFS/etc/resolv.conf"
for m in proc sys dev dev/pts; do
  mkdir -p "$ROOTFS/$m"
  mount --bind "/$m" "$ROOTFS/$m"
done

banner "creating the LUKS image (UUID must exist before update-initramfs)"
truncate -s 6G "$IMAGE"
LOOP="$(losetup -f --show "$IMAGE")"
printf '%s' "$PASSPHRASE" | cryptsetup luksFormat --type luks2 --batch-mode \
  --pbkdf-memory 262144 "$LOOP" -
LUKS_UUID="$(cryptsetup luksUUID "$LOOP")"

banner "configuring crypttab / fstab / networking"
# `initramfs` bakes the mapping in so cryptsetup-initramfs unlocks before pivot.
echo "$MAPPER_NAME UUID=$LUKS_UUID none luks,initramfs" > "$ROOTFS/etc/crypttab"
echo "/dev/mapper/$MAPPER_NAME / ext4 defaults,noatime 0 1" > "$ROOTFS/etc/fstab"
echo "lim-e2e" > "$ROOTFS/etc/hostname"
# initramfs-tools includes virtio via MODULES=most (default); be explicit.
sed -i 's/^MODULES=.*/MODULES=most/' "$ROOTFS/etc/initramfs-tools/initramfs.conf"

banner "authorizing the ssh key for dropbear-initramfs"
install -D -m0600 "$SSH_PUBKEY" "$ROOTFS/etc/dropbear/initramfs/authorized_keys"

banner "installing the real lim initramfs-tools tor hooks"
install -D -m0755 "$HOOK_SRC/tor_hook"     "$ROOTFS/etc/initramfs-tools/hooks/tor"
install -D -m0755 "$HOOK_SRC/tor_premount" "$ROOTFS/etc/initramfs-tools/scripts/init-premount/tor"
install -D -m0755 "$HOOK_SRC/tor_bottom"   "$ROOTFS/etc/initramfs-tools/scripts/init-bottom/tor"
install -D -m0644 "$HOOK_SRC/torrc"        "$ROOTFS/etc/tor/initramfs-torrc"
if [ -n "${TOR_TEST_NETWORK_CONF:-}" ]; then
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

banner "baking the boot-ok marker service + serial getty"
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
in_chroot systemctl enable lim-boot-ok.service serial-getty@ttyS0.service

banner "generating the initramfs (update-initramfs)"
in_chroot update-initramfs -c -k all || in_chroot update-initramfs -u -k all

banner "exporting kernel + initramfs"
KERNEL_IMG="$(find "$ROOTFS/boot" -maxdepth 1 -name 'vmlinuz-*' | sort | tail -1)"
INITRAMFS_IMG="$(find "$ROOTFS/boot" -maxdepth 1 -name 'initrd.img-*' | sort | tail -1)"
[ -n "$KERNEL_IMG" ] || { echo "No kernel in $ROOTFS/boot" >&2; exit 1; }
[ -n "$INITRAMFS_IMG" ] || { echo "No initramfs in $ROOTFS/boot" >&2; exit 1; }
echo "Using kernel $KERNEL_IMG and initramfs $INITRAMFS_IMG"
cp "$KERNEL_IMG" "$WORK_DIR/kernel"
cp "$INITRAMFS_IMG" "$WORK_DIR/initramfs"

banner "unbinding chroot filesystems"
for m in dev/pts dev proc sys; do umount -l "$ROOTFS/$m"; done

banner "copying the rootfs into the encrypted volume"
printf '%s' "$PASSPHRASE" | cryptsetup open "$LOOP" "$MAPPER_NAME" -
mkfs.ext4 -q "/dev/mapper/$MAPPER_NAME"
mkdir -p "$WORK_DIR/mnt"
mount "/dev/mapper/$MAPPER_NAME" "$WORK_DIR/mnt"
cp -a "$ROOTFS/." "$WORK_DIR/mnt/"
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
