source "$(dirname "$(readlink -f "${0}")")/base.sh" || (echo "Loading base.sh failed." && exit 1)
echo "Setups disk encryption"

set_device_mount_partition_and_mapper_paths

overwritte_device_with_zeros

info "Creating new GPT partition table..."
(	echo "g"	# create a new empty GPT partition table
  echo "w"  # Write partition table
)| sudo fdisk --wipe always "$device_path" ||
error

info "Creating partition table..."
(	echo "n"	# Create new partition
  echo ""   # Accept default
  echo ""   # Accept default
  echo ""   # Accept default
  echo "p"	# Create GPT partition table
  echo "w"  # Write partition table
)| sudo fdisk --wipe always "$device_path" ||
error

info "Encrypt $device_path..." &&
sudo cryptsetup -v -y luksFormat $partition_path ||
error

info "Unlock partition..." &&
sudo cryptsetup luksOpen $partition_path $mapper_name ||
error

info "Create btrfs file system..." &&
sudo mkfs.btrfs $mapper_path || error

info "Creating mount folder unter \"$mount_path\"..." &&
sudo mkdir -p $mount_path || error

info "Mount partition..." &&
sudo mount $mapper_path $mount_path ||
error

info "Own partition by user..." &&
sudo chown -R $USER:$USER $mount_path ||
error

success "Encryption successfull :)"
