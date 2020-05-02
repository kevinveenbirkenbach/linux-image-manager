#!/bin/bash
# shellcheck disable=SC2010  # ls  | grep allowed

echo "Setupscript for Raspberry Pi devices"
echo
echo "@author Kevin Veen-Birkenbach [kevin@veen.world]"
echo "@since 2017-03-12"
echo

# Define colors
red_color=$(tput setaf 1)
green_color=$(tput setaf 2)
yellow_color=$(tput setaf 3)
blue_color=$(tput setaf 4)
magenta_color=$(tput setaf 5)
reset_color=$(tput sgr0)

message(){
  echo "$1[$2]:${reset_color} $3 ";
}

question(){
  message "${magenta_color}" "QUESTION" "$1";
}

info(){
  message "${blue_color}" "INFO" "$1";
}

warning(){
  message "${yellow_color}" "WARNING" "$1";
}

success(){
  message "${green_color}" "SUCCESS" "$1";
}

destructor(){
  info "Cleaning up..."
  sed -i 's/^#CHROOT //g' "$root_mount_path""etc/ld.so.preload"
  umount -v "$chroot_dev_pts_mount_path" || warning "Umounting $chroot_dev_pts_mount_path failed!"
  umount -v "$chroot_dev_mount_path" || warning "Umounting $chroot_dev_mount_path failed!"
  umount -v "$chroot_proc_mount_path" || warning "Umounting $chroot_proc_mount_path failed!"
  umount -v "$chroot_sys_mount_path" || warning "Umounting $chroot_sys_mount_path failed!"
  umount -v "$root_mount_path""/boot/" || warning "Umounting $root_mount_path/boot/ failed!"
  umount -v "$root_mount_path" || warning "Umounting $root_mount_path failed!"
  umount -v "$boot_mount_path" || warning "Umounting $boot_mount_path failed!"
  rmdir -v "$root_mount_path" || warning "Removing $root_mount_path failed!"
  rmdir -v "$boot_mount_path" || warning "Removing $boot_mount_path failed!"
  rmdir -v "$working_folder" || warning "Removing $working_folder failed!"
}

error(){
  message "${red_color}" "ERROR" "$1 -> Leaving program."
  if [ "$2" != "no_destructor" ]
    then
      destructor
  fi
  exit 1;
}

info "Starting setup..."

info "Define variables..."
working_folder="/tmp/raspberry-pi-tools-$(date +%s)/";

info "Define functions..."

info "Create temporary working folder in $working_folder";
mkdir -v "$working_folder"

info "Checking if root..."
if [ "$(id -u)" != "0" ];then
    error "This script must be executed as root!"
fi

info "Configure user..."
question "Please type in a valid username from which the SSH-Key should be copied:" && read -r origin_username;
getent passwd "$origin_username" > /dev/null 2 || error "User $origin_username doesn't exist.";
origin_user_home="/home/$origin_username/";

info "Image routine starts..."
image_folder="$origin_user_home""Images/";
info "The images will be stored in \"$image_folder\"."
if [ ! -d "$image_folder" ]; then
  info "Folder \"$image_folder\" doesn't exist. It will be created now."
  mkdir -v "$image_folder"
fi

info "Selecting sd-card..."
info "Show available devices..."
ls -lasi /dev/ | grep -E "sd|mm"
question "Please type in the name of the correct device: /dev/" && read -r device
sd_card_path="/dev/$device"

if [ ! -b "$sd_card_path" ]
  then
    error "$sd_card_path is not valid device."
fi

if mount | grep -q "$sd_card_path"
  then
    error "Device $sd_card_path is allready mounted. Umount with \"umount $sd_card_path*\"."
fi

question "Select which Raspberry Pi version should be used:" && read -r version

info "Selecting operating system should be used..."
info "Available systems:"
echo
echo "1) arch"
echo "2) moode"
echo "3) retropie"
echo
question "Please type in the os:" && read -r os

os_does_not_support_raspberry_version_error () {
  error "$os for Raspberry Pi Version $version is not supported!";
}

case "$os" in
  "arch")
    base_download_url="http://os.archlinuxarm.org/os/";
    case "$version" in
      "1")
        imagename="ArchLinuxARM-rpi-latest.tar.gz"
        ;;
      "2" | "3")
        imagename="ArchLinuxARM-rpi-2-latest.tar.gz"
        ;;
      "4")
        imagename="ArchLinuxARM-rpi-4-latest.tar.gz"
        ;;
      *)
        os_does_not_support_raspberry_version_error
        ;;
    esac
    ;;
  "moode")
    image_checksum="185cbc9a4994534bb7a4bc2744c78197"
    base_download_url="https://github.com/moode-player/moode/releases/download/r651prod/"
    imagename="moode-r651-iso.zip";
    ;;
  "retropie")
    base_download_url="https://github.com/RetroPie/RetroPie-Setup/releases/download/4.6/";
    case "$version" in
      "1")
        image_checksum="98b4205ad0248d378c6776e20c54e487"
        imagename="retropie-buster-4.6-rpi1_zero.img.gz"
        ;;

      "2" | "3")
        image_checksum="2e082ef5fc2d7cf7d910494cf0f7185b"
        imagename="retropie-buster-4.6-rpi2_rpi3.img.gz"
        ;;

      "4")
        image_checksum="9154d998cba5219ddf23de46d8845f6c"
        imagename="retropie-buster-4.6-rpi4.img.gz"
        ;;
      *)
        os_does_not_support_raspberry_version_error
        ;;
    esac
    ;;
  *)
    error "The operation system \"$os\" is not supported yet!"
  ;;
esac

info "Generating os-image..."
download_url="$base_download_url$imagename"
image_path="$image_folder$imagename"

question "Should the image download be forced?(y/n)" && read -r force_image_download
if [ "$force_image_download" = "y" ]
  then
    if [ -f "$image_path" ]
      then
        info "Removing image $image_path."
        rm "$image_path" || error "Removing image \"$image_path\" failed."
      else
        info "Forcing download wasn't neccessary. File $image_path doesn't exist."
    fi
fi

info "Start Download procedure..."
if [ -f "$image_path" ]
	then
    info "Image exist local. Download skipped."
  else
		info "Image \"$imagename\" doesn't exist under local path \"$image_path\"."
    info "Image \"$imagename\" gets downloaded from \"$download_url\"..."
		wget "$download_url" -P "$image_folder" || error "Download from \"$download_url\" failed."
fi

info "Verifying image..."
if [[ -v image_checksum ]]
  then
    echo "$image_checksum $image_path"| md5sum -c -|| error "Verification failed. HINT: Force the download of the image."
  else
    warning "Verification is not possible. No checksum is defined."
fi

info "Preparing mount paths..."
boot_mount_path="$working_folder""boot/"
root_mount_path="$working_folder""root/"
mkdir -v "$boot_mount_path"
mkdir -v "$root_mount_path"

info "Defining partition paths..."
if [ "${sd_card_path:5:1}" != "s" ]
  then
    partion="p"
  else
    partion=""
fi
boot_partition_path=$sd_card_path$partion"1"
root_partition_path=$sd_card_path$partion"2"

mount_partitions(){
  info "Mount boot and root partition..."
  mount "$boot_partition_path" "$boot_mount_path" || error "Mount from $boot_partition_path to $boot_mount_path failed..."
  mount "$root_partition_path" "$root_mount_path" || error "Mount from $root_partition_path to $root_mount_path failed..."
  info "The following mounts refering this setup exist:" && mount | grep "$working_folder"
}

question "Should the image be transfered to $sd_card_path?(y/n)" && read -r transfer_image
if [ "$transfer_image" = "y" ]
  then

    question "Should $sd_card_path be overwritten with zeros before copying?(y/n)" && read -r copy_zeros_to_device
    if [ "$copy_zeros_to_device" = "y" ]
      then
        info "Overwritting..."
        dd if=/dev/zero of="$sd_card_path" bs=1M || error "Overwritting $sd_card_path failed."
      else
        info "Skipping Overwritting..."
    fi

    info "Starting image transfer..."
    case "$os" in
      "arch")
        info "Execute fdisk..."
        (	echo "o"	#Type o. This will clear out any partitions on the drive.
        	echo "p"	#Type p to list partitions. There should be no partitions left
        	echo "n"	#Type n,
        	echo "p"	#then p for primary,
        	echo "1"	#1 for the first partition on the drive,
        	echo ""		#press ENTER to accept the default first sector,
        	echo "+100M"	#then type +100M for the last sector.
        	echo "t"	#Type t,
        	echo "c"	#then c to set the first partition to type W95 FAT32 (LBA).
        	echo "n"	#Type n,
        	echo "p"	#then p for primary,
        	echo "2"	#2 for the second partition on the drive,
        	echo ""		#and then press ENTER twice to accept the default first and last sector.
        	echo ""
        	echo "w"	#Write the partition table and exit by typing w.
        )| fdisk "$sd_card_path" || error "Creating partitions failed. Try to execute this script with the overwritting parameter."

        info "Format boot partition..."
        mkfs.vfat "$boot_partition_path" || error "Format boot is not possible."

        info "Format root partition..."
        mkfs.ext4 "$root_partition_path" || error "Format root is not possible."

        mount_partitions;

        info "Root files will be transfered to device..."
        bsdtar -xpf "$image_path" -C "$root_mount_path"
        sync

        info "Boot files will be transfered to device..."
        mv -v "$root_mount_path/boot/"* "$boot_mount_path"

        ;;
      "moode")
        unzip -p "$image_path" | sudo dd of="$sd_card_path" bs=1M conv=fsync || error "DD $image_path to $sd_card_path failed."
        sync
        ;;
      "retropie")
        gunzip -c "$image_path" | sudo dd of="$sd_card_path" bs=1M conv=fsync
        sync
        ;;
      *)
        error "Image transfer for operation system \"$os\" is not supported yet!";
        ;;
    esac
  else
    info "Skipping image transfer..."
fi

info "Start regular mounting procedure..."
if mount | grep -q "$boot_mount_path" && mount | grep -q "$root_mount_path"
  then
    info "Everything allready mounted. Skipping..."
  else
    mount_partitions
fi

info "Define target paths..."
target_home_path="$root_mount_path""home/";
target_username=$(ls "$target_home_path");
target_user_home_folder_path="$target_home_path$target_username/";

info "Copy ssh key to target..."
target_user_ssh_folder_path="$target_user_home_folder_path"".ssh/"
target_authorized_keys="$target_user_ssh_folder_path""authorized_keys"
origin_user_rsa_pub="$origin_user_home"".ssh/id_rsa.pub";
if [ -f "$origin_user_rsa_pub" ]
  then
    mkdir -v "$target_user_ssh_folder_path"
    cat "$origin_user_rsa_pub" > "$target_authorized_keys"
    target_authorized_keys_content=$(cat "$target_authorized_keys")
    info "$target_authorized_keys contains the following: $target_authorized_keys_content"
    chown -vR 1000 "$target_user_ssh_folder_path"
    chmod -v 700 "$target_user_ssh_folder_path"
    chmod -v 600 "$target_authorized_keys"
  else
    warning "The ssh key \"$origin_user_rsa_pub\" can't be copied to \"$target_authorized_keys\" because it doesn't exist."
fi

info "Start chroot procedures..."
info "Mount chroot environments..."
chroot_sys_mount_path="$root_mount_path""sys/"
chroot_proc_mount_path="$root_mount_path""proc/"
chroot_dev_mount_path="$root_mount_path""dev/"
chroot_dev_pts_mount_path="$root_mount_path""dev/pts"
mount --bind "$boot_mount_path" "$root_mount_path""/boot" || error "Mounting $chroot_dev_mount_path failed."
mount --bind /dev "$chroot_dev_mount_path" || error "Mounting $chroot_dev_mount_path failed."
mount --bind /sys "$chroot_sys_mount_path" || error "Mounting $chroot_sys_mount_path failed."
mount --bind /proc "$chroot_proc_mount_path" || error "Mounting $chroot_proc_mount_path failed."
mount --bind /dev/pts "$chroot_dev_pts_mount_path" || error "Mounting $chroot_dev_pts_mount_path failed."

sed -i 's/^/#CHROOT /g' "$root_mount_path""etc/ld.so.preload"
cp -v /usr/bin/qemu-arm-static "$root_mount_path""/usr/bin/" || error "Copy qemu-arm-static failed. The following packages are neccessary: qemu qemu-user-static binfmt-support."

info "Changing passwords on target system..."
question "Type in new password: " && read -r password_1
question "Repeat new password\"$target_username\"" && read -r password_2
if [ "$password_1" == "$password_2" ]
  then
    (
    echo "(
          echo '$password_1'
          echo '$password_1'
          ) | passwd $target_username"
    echo "(
          echo '$password_1'
          echo '$password_1'
          ) | passwd"
    ) | chroot "$root_mount_path" /bin/bash || error "Password change failed."
  else
    error "Passwords didn't match."
fi

question "Type in the hostname:" && read -r hostname;
echo "$hostname" > "$root_mount_path""etc/hostname" || error "Changing hostname failed."

# question "Do you want to copy all Wifi passwords to the device?(y/n)" && read -r copy_wifi
# if [ "$copy_wifi" = "y" ]
#   then
#     origin_wifi_config_path="/etc/NetworkManager/system-connections/"
#     target_wifi_config_path="$root_mount_path$origin_wifi_config_path"
#     rsync -av "$origin_wifi_config_path" "$target_wifi_config_path"
# fi

info "The first level folder structure on $root_mount_path is:" && tree -laL 1 "$root_mount_path"
info "The first level folder structure on $boot_mount_path is:" && tree -laL 1 "$boot_mount_path"

destructor
success "Setup successfull :)" && exit 0
