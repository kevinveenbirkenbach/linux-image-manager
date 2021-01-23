#!/bin/bash
# shellcheck disable=SC1090  # Can't follow non-constant source. Use a directive to specify location.
# shellcheck disable=SC2015  # Deactivating bool hint
# shellcheck disable=SC2034  # Unused variables
# shellcheck disable=SC2154  # Referenced but not assigned
source "$(dirname "$(readlink -f "${0}")")/../base.sh" || (echo "Loading base.sh failed." && exit 1)
set_raid1_devices_mount_partition_and_mapper_paths(){
  info "RAID1 partition 1..." &&
  set_device_mount_partition_and_mapper_paths &&
  partition_path_1=$partition_path &&
  mapper_name_1=$mapper_name &&
  mapper_path_1=$mapper_path &&
  mount_path_1=$mount_path &&
  device_path_1=$device_path &&
  info "RAID1 partition 2..." &&
  set_device_mount_partition_and_mapper_paths &&
  partition_path_2=$partition_path &&
  mapper_name_2=$mapper_name &&
  mapper_path_2=$mapper_path &&
  mount_path_2=$mount_path &&
  device_path_2=$device_path || error
}
