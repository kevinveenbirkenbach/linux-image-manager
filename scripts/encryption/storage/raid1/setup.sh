#!/bin/bash
# @author Kevin Veen-Birkenbach [kevin@veen.world]
# @see https://balaskas.gr/btrfs/raid1.html
# @see https://mutschler.eu/linux/install-guides/ubuntu-btrfs-raid1/
# shellcheck disable=SC1090  # Can't follow non-constant source. Use a directive to specify location.
# shellcheck disable=SC2015  # Deactivating bool hint
# shellcheck disable=SC2154  # Referenced but not assigned
source "$(dirname "$(readlink -f "${0}")")/base.sh" || (echo "Loading base.sh failed." && exit 1)

set_raid1_devices_mount_partition_and_mapper_paths

info "Encrypting $partition_path_1..." &&
cryptsetup luksFormat "$partition_path_1" &&
info "Encrypting $partition_path_2..." &&
cryptsetup luksFormat "$partition_path_2" &&
blkid | tail -2 &&
cryptsetup luksOpen "$partition_path_1" "$mapper_name_1" &&
cryptsetup luksOpen "$partition_path_2" "$mapper_name_2" &&
cryptsetup status "$mapper_path_1" &&
cryptsetup status "$mapper_path_2" &&
mkfs.btrfs -m raid1 -d raid1 "$mapper_path_1" "$mapper_path_2" &&
success "Encryption successfull :)" ||
error
