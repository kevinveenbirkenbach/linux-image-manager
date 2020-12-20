#!/bin/bash
source "$(dirname "$(readlink -f "${0}")")/../base.sh" || (echo "Loading base.sh failed." && exit 1)
set_raid1_devices_mount_partition_and_mapper_paths(){
  info "RAID1 partition 1..." &&
  set_device_mount_partition_and_mapper_paths &&
  partition_path_1=$partition_path &&
  mapper_name_1=$mapper_name &&
  mapper_path_1=$mapper_path &&
  mount_path_1=$mount_path &&
  info "RAID1 partition 2..." &&
  set_device_mount_partition_and_mapper_paths &&
  partition_path_2=$partition_path &&
  mapper_name_2=$mapper_name &&
  mapper_path_2=$mapper_path &&
  mount_path_2=$mount_path || error
}
