#!/bin/bash
#
# Offers base functions for the image management
#
# shellcheck disable=SC2034 #Deactivate checking of unused variables
# shellcheck source=/dev/null # Deactivate SC1090
source "$(dirname "$(readlink -f "${0}")")/../base.sh" || (echo "Loading base.sh failed." && exit 1)

# Writes the full partition name
# @parameter $1 is device path
# @parameter $2 is the partition number
echo_partition_name(){
  if [ "${device_path:5:1}" != "s" ]
    then
      echo "$device_path""p""$2"
    else
      echo "$device_path$2"
  fi
}

set_partition_paths(){
  info "Setting partition paths..."
  root_partition_path=$(echo_partition_name "2")
  boot_partition_path=$(echo_partition_name "1")
}

# Routine to echo the full sd-card-path
set_device_path(){
  info "Available devices:"
  ls -lasi /dev/ | grep -E "sd|mm"
  question "Please type in the name of the device: /dev/" && read -r device
  device_path="/dev/$device"
  if [ ! -b "$device_path" ]
    then
      error "$device_path is not valid device."
  fi
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

mount_binds(){
  info "Mount chroot environments..." &&
  chroot_sys_mount_path="$root_mount_path""sys/" &&
  chroot_proc_mount_path="$root_mount_path""proc/" &&
  chroot_dev_mount_path="$root_mount_path""dev/" &&
  chroot_dev_pts_mount_path="$root_mount_path""dev/pts" &&
  mount --bind "$boot_mount_path" "$root_mount_path""/boot" &&
  mount --bind /dev "$chroot_dev_mount_path" &&
  mount --bind /sys "$chroot_sys_mount_path" &&
  mount --bind /proc "$chroot_proc_mount_path" &&
  mount --bind /dev/pts "$chroot_dev_pts_mount_path" ||
  error
}
