#!/bin/bash
#
# Offers base functions for the image management
#
# shellcheck disable=SC2034 #Deactivate checking of unused variables
# shellcheck disable=SC2010  # ls  | grep allowed
# shellcheck source=/dev/null # Deactivate SC1090
# shellcheck disable=SC2015  # Deactivate bools hints
# shellcheck disable=SC2154  # Deactivate referenced but not assigned hints
source "$(dirname "$(readlink -f "${0}")")/../base.sh" || (echo "Loading base.sh failed." && exit 1)

# Writes the full partition name
# @parameter $1 is device path
# @parameter $2 is the partition number
echo_partition_name(){
  if [ "${device_path:5:1}" != "s" ]
    then
      echo "$device_path""p""$1"
    else
      echo "$device_path$1"
  fi
}

set_partition_paths(){
  info "Setting partition and mapper paths..."
  boot_partition_path=$(echo_partition_name "1")
  root_partition_path=$(echo_partition_name "2")
  root_mapper_path=$root_partition_path
}

make_mount_folders(){
  info "Preparing mount paths..." &&
  boot_mount_path="$working_folder_path""boot/" &&
  root_mount_path="$working_folder_path""root/" &&
  mkdir -v "$boot_mount_path" &&
  mkdir -v "$root_mount_path" ||
  error
}

make_working_folder(){
  working_folder_path="/tmp/linux-image-manager-$(date +%s)/" &&
  info "Create temporary working folder in $working_folder_path" &&
  mkdir -v "$working_folder_path" ||
  error
}

decrypt_root(){
  if [ "$(blkid "$root_partition_path" -s TYPE -o value)" == "crypto_LUKS" ]
    then
      root_partition_uuid=$(blkid "$root_partition_path" -s UUID -o value) &&
      root_mapper_name="linux-image-manager-$root_partition_uuid" &&
      root_mapper_path="/dev/mapper/$root_mapper_name" &&
      info "Decrypting of $root_partition_path is neccessary..." &&
      sudo cryptsetup -v luksOpen "$root_partition_path" "$root_mapper_name" || error
  fi
}

mount_partitions(){
  info "Mount boot and root partition..." &&
  mount -v "$boot_partition_path" "$boot_mount_path" &&
  mount -v "$root_mapper_path" "$root_mount_path" &&
  info "Settind uuid variables..." &&
  root_partition_uuid=$(blkid "$root_partition_path" -s UUID -o value) &&
  boot_partition_uuid=$(blkid "$boot_partition_path" -s UUID -o value) &&
  info "The following mounts refering this setup exist:" && mount | grep "$working_folder_path" ||
  error
}

destructor(){
  info "Cleaning up..."
  info "Unmounting everything..."
  umount -lv "$chroot_dev_pts_mount_path" || warning "Umounting $chroot_dev_pts_mount_path failed!"
  umount -lv "$chroot_dev_mount_path" || warning "Umounting $chroot_dev_mount_path failed!"
  umount -v "$chroot_proc_mount_path" || warning "Umounting $chroot_proc_mount_path failed!"
  umount -v "$chroot_sys_mount_path" || warning "Umounting $chroot_sys_mount_path failed!"
  umount -v "$root_mount_path""boot/" || warning "Umounting $root_mount_path""boot/ failed!"
  umount -v "$root_mount_path" || warning "Umounting $root_mount_path failed!"
  umount -v "$boot_mount_path" || warning "Umounting $boot_mount_path failed!"
  info "Deleting mount folders..."
  rmdir -v "$root_mount_path" || warning "Removing $root_mount_path failed!"
  rmdir -v "$boot_mount_path" || warning "Removing $boot_mount_path failed!"
  rmdir -v "$working_folder_path" || warning "Removing $working_folder_path failed!"
  if [ "$(blkid "$root_partition_path" -s TYPE -o value)" == "crypto_LUKS" ]
    then
      info "Trying to close decrypted $root_mapper_name..." &&
      sudo cryptsetup -v luksClose "$root_mapper_name" || warning "Failed."
  fi
}

mount_chroot_binds(){
  info "Mount chroot environments..." &&
  chroot_sys_mount_path="$root_mount_path""sys/" &&
  chroot_proc_mount_path="$root_mount_path""proc/" &&
  chroot_dev_mount_path="$root_mount_path""dev/" &&
  chroot_dev_pts_mount_path="$root_mount_path""dev/pts" &&
  mount --bind "$boot_mount_path" "$root_mount_path""boot" &&
  mount --bind /dev "$chroot_dev_mount_path" &&
  mount --bind /sys "$chroot_sys_mount_path" &&
  mount --bind /proc "$chroot_proc_mount_path" &&
  mount --bind /dev/pts "$chroot_dev_pts_mount_path" ||
  error
}

copy_qemu(){
  info "Copy qemu binary..." &&
  cp -v /usr/bin/qemu-arm-static "$root_mount_path""usr/bin/" ||
  error
}

copy_resolve_conf(){
  info "Copy resolve.conf..." &&
  cp --remove-destination -v /etc/resolv.conf "$root_mount_path""etc/" ||
  warning "Failed. Propably there is no internet connection available."
}
