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
