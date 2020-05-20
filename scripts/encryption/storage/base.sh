#!/bin/bash
source "$(dirname "$(readlink -f "${0}")")/../../base.sh" || (echo "Loading base.sh failed." && exit 1)

set_device_mount_and_mapper_paths(){
  set_device_path &&
  mapper_name="encrypteddrive-$device" &&
  mapper_path="/dev/mapper/$mapper_name" &&
  mount_path="/media/$mapper_name" &&
  info "mapper name set to : $mapper_name" &&
  info "mapper path set to : $mapper_path" ||
  info "mount path set to : $mount_path" ||
  error
}
