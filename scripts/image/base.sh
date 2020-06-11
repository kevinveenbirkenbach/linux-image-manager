#!/bin/bash
#
# Offers base functions for the image management
#
# shellcheck disable=SC2034 #Deactivate checking of unused variables
# shellcheck disable=SC2010  # ls  | grep allowed
# shellcheck source=/dev/null # Deactivate SC1090
# shellcheck disable=SC2015  # Deactivate bools hints
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
  info "Setting partition paths..."
  root_partition_path=$(echo_partition_name "2")
  boot_partition_path=$(echo_partition_name "1")
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
  working_folder_path="/tmp/raspberry-pi-tools-$(date +%s)/" &&
  info "Create temporary working folder in $working_folder_path" &&
  mkdir -v "$working_folder_path" ||
  error
}

mount_partitions(){
  info "Mount boot and root partition..." &&
  mount "$boot_partition_path" "$boot_mount_path" &&
  mount "$root_partition_path" "$root_mount_path" &&
  info "The following mounts refering this setup exist:" && mount | grep "$working_folder_path" ||
  error
}

umount_everything(){
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
