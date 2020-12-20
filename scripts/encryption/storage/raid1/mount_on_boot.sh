#!/bin/bash
source "$(dirname "$(readlink -f "${0}")")/base.sh" || (echo "Loading base.sh failed." && exit 1)
info "Automount raid1 encrypted storages..."
create_luks_key_and_update_cryptab $mapper_name_1 $partition_path_1
create_luks_key_and_update_cryptab $mapper_name_2 $partition_path_2
update_fstab $mapper_path_1 $mount_path_1
success "Installation finished. Please restart :)"
