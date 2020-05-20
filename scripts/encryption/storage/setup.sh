source "$(dirname "$(readlink -f "${0}")")/base.sh" || (echo "Loading base.sh failed." && exit 1)
echo "Setups disk encryption"

set_device_mount_and_mapper_paths

info "Overwritting device \"$device_path\" with zeros..." &&
sudo dd if=/dev/zero of=$device_path bs=$OPTIMAL_BLOCKSIZE status=progress conv=fdatasync ||
error

info "Creating new GPT partition table..."
(	echo "g"	# create a new empty GPT partition table
  echo "w"  # Write partition table
)| sudo fdisk "$device_path" || error

info "Creating partition table..."
(	echo "n"	# Create GPT partition table
  echo "p"	# Create GPT partition table
  echo "w"  # Write partition table
)| sudo fdisk "$device_path" || error

info "Show memory devices..." &&
sudo fdisk -l || error

info "Encrypt $device_path..." &&
sudo cryptsetup -v -y luksFormat $device_path

info "Unlock partition..." &&
sudo cryptsetup luksOpen $device_path $mapper_name

info "Create btrfs file system..." &&
sudo mkfs.btrfs $mapper_path || error

info "Creating mount folder unter \"$mount_path\"..." &&
mkdir -p $mount_path || error

info "Mount partition..." &&
sudo mount $mapper_path $mount_path || error

info "Own partition by user..." &&
sudo chown -R $USER:$USER $mount_path || error
