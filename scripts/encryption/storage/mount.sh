source "$(dirname "$(readlink -f "${0}")")/base.sh" || (echo "Loading base.sh failed." && exit 1)
echo "Mounting encrypted storage..."

set_device_mount_and_mapper_paths

info "Unlock partition..." &&
sudo cryptsetup luksOpen $device_path $mapper_name ||
error

info "Mount partition..." &&
sudo mount $mapper_path $mount_path ||
error

success "Mounting successfull :)"
