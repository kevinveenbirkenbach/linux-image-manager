#!/bin/bash
# shellcheck disable=SC2010  # ls  | grep allowed
# shellcheck source=/dev/null # Deactivate SC1090
# shellcheck disable=SC2015  # Deactivate bools hints
# shellcheck disable=SC2154  # Deactivate not referenced link
source "$(dirname "$(readlink -f "${0}")")/base.sh" || (echo "Loading base.sh failed." && exit 1)

info "Setupscript for images started..."

info "Define functions..."
destructor(){
  info "Cleaning up..."
  umount -v "$chroot_dev_pts_mount_path" || warning "Umounting $chroot_dev_pts_mount_path failed!"
  umount -v "$chroot_dev_mount_path" || warning "Umounting $chroot_dev_mount_path failed!"
  umount -v "$chroot_proc_mount_path" || warning "Umounting $chroot_proc_mount_path failed!"
  umount -v "$chroot_sys_mount_path" || warning "Umounting $chroot_sys_mount_path failed!"
  umount -v "$root_mount_path""boot/" || warning "Umounting $root_mount_path""boot/ failed!"
  umount -v "$root_mount_path" || warning "Umounting $root_mount_path failed!"
  umount -v "$boot_mount_path" || warning "Umounting $boot_mount_path failed!"
  rmdir -v "$root_mount_path" || warning "Removing $root_mount_path failed!"
  rmdir -v "$boot_mount_path" || warning "Removing $boot_mount_path failed!"
  rmdir -v "$working_folder_path" || warning "Removing $working_folder_path failed!"
}

info "Checking if root..."
if [ "$(id -u)" != "0" ];then
    error "This script must be executed as root!"
fi

make_working_folder

info "Configure user..." &&
question "Please type in a valid working username:" && read -r origin_username &&
getent passwd "$origin_username" > /dev/null 2 || error "User $origin_username doesn't exist."
origin_user_home="/home/$origin_username/"

info "Image routine starts..."
image_folder="$origin_user_home""Images/";
info "The images will be stored in \"$image_folder\"."
if [ ! -d "$image_folder" ]; then
  info "Folder \"$image_folder\" doesn't exist. It will be created now." &&
  mkdir -v "$image_folder" ||
  error
fi

set_device_path

if mount | grep -q "$device_path"
  then
    error "Device $device_path is allready mounted. Umount with \"umount $device_path*\"."
fi

info "Select which architecture type should be used..." &&
echo "1) arm " &&
echo "2) 64_bit" &&
question "Please type in the architecture type:" &&
read -r architecture ||
error


info "Select which operating system should be used..."
info "Available systems:"
if [ "$architecture" = "arm" ]
  then
    echo "1) arch"
    echo "2) moode"
    echo "3) retropie"
fi
if [ "$architecture" = "64_bit" ]
  then
    echo "1) manjaro"
fi
question "Please type in the os:" && read -r os

info "Select which version should be used..."
case "$architecture" in
  "arm")
    echo "Version for Raspberry Pi modell:"
    echo "1) 1"
    echo "2) 2"
    echo "3) 3"
    echo "4) 4"
  ;;
  "64_bit")
    case "$os" in
      "manjaro")
        echo "1) architect"
        echo "1) gnome"
      ;;
      *)
        error "The os system \"$os\" is not supported yet for 64bit!"
      ;;
    esac
  ;;
  *)
    error "The architecture \"$architecture\" is not supported yet!"
  ;;
esac
question "Please type in the version:" && read -r version

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
      "2")
        imagename="ArchLinuxARM-rpi-2-latest.tar.gz"
        ;;
      "3")
        imagename="ArchLinuxARM-rpi-3-latest.tar.gz"
        ;;
      "4")
        imagename="ArchLinuxARM-rpi-4-latest.tar.gz"
        ;;
      *)
        os_does_not_support_raspberry_version_error
        ;;
    esac
    ;;
  "manjaro")
    case "$version" in
      "architect")
        image_checksum="6b1c2fce12f244c1e32212767a9d3af2cf8263b2"
        base_download_url="https://osdn.net/frs/redir.php?m=dotsrc&f=%2Fstorage%2Fg%2Fm%2Fma%2Fmanjaro%2Farchitect%2F20.0%2F";
        imagename="manjaro-architect-20.0-200426-linux56.iso"
        ;;
      "gnome")
        image_checksum="d16118207c546c18201703d80b6356b1522b47d0"
        base_download_url="https://osdn.net/frs/redir.php?m=dotsrc&f=/storage/g/m/ma/manjaro/gnome/20.0.1/";
        imagename="manjaro-gnome-20.0.1-200511-linux56.iso"
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

question "Should the image download be forced?(y/N)" && read -r force_image_download
if [ "$force_image_download" = "y" ]
  then
    if [ -f "$image_path" ]
      then
        info "Removing image $image_path." &&
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
		wget "$download_url" -O "$image_path" || error "Download from \"$download_url\" failed."
fi

info "Verifying image..."
if [[ -v image_checksum ]]
  then
    info "Checking md5 checksum..." && echo "$image_checksum $image_path"| md5sum -c -||
    info "Checking sha1 checksum..." && echo "$image_checksum $image_path"| sha1sum -c -||
    error "Verification failed. HINT: Force the download of the image."
  else
    warning "Verification is not possible. No checksum is defined."
fi

make_mount_folders

set_partition_paths

question "Should the image be transfered to $device_path?(y/n)" && read -r transfer_image
if [ "$transfer_image" = "y" ]
  then

    overwritte_device_with_zeros

    info "Starting image transfer..."
    if [ "$os" = "arch" ]
      then
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
        )| fdisk "$device_path" || error "Creating partitions failed. Try to execute this script with the overwritting parameter."

        info "Format boot partition..." &&
        mkfs.vfat "$boot_partition_path" || error "Format boot is not possible."

        info "Format root partition..." &&
        mkfs.ext4 "$root_partition_path" || error "Format root is not possible."

        mount_partitions;

        info "Root files will be transfered to device..." &&
        bsdtar -xpf "$image_path" -C "$root_mount_path" &&
        sync ||
        error

        info "Boot files will be transfered to device..." &&
        mv -v "$root_mount_path/boot/"* "$boot_mount_path" ||
        error
      elif [ "${image_path: -4}" = ".zip" ]
        then
          info "Transfering .zip file..." &&
          unzip -p "$image_path" | sudo dd of="$device_path" bs="$OPTIMAL_BLOCKSIZE" conv=fsync status=progress || error "DD $image_path to $device_path failed." &&
          sync ||
          error
      elif [ "${image_path: -3}" = ".gz" ]
        then
          info "Transfering .gz file..." &&
          gunzip -c "$image_path" | sudo dd of="$device_path" bs="$OPTIMAL_BLOCKSIZE" conv=fsync status=progress &&
          sync ||
          error
      elif [ "${image_path: -4}" = ".iso" ]
        then
          info "Transfering .iso file..." &&
          sudo dd if="$image_path" of="$device_path" bs="$OPTIMAL_BLOCKSIZE" conv=fsync status=progress &&
          sync ||
          error
      else
        error "Image transfer for operation system \"$os\" is not supported yet!";
      fi
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

question "Should the ssh-key be copied to the image?(y/N)" && read -r copy_ssh_key
if [ "$copy_ssh_key" == "y" ]
  then
    info "Copy ssh key to target..."
    target_user_ssh_folder_path="$target_user_home_folder_path"".ssh/"
    target_authorized_keys="$target_user_ssh_folder_path""authorized_keys"
    origin_user_rsa_pub="$origin_user_home"".ssh/id_rsa.pub";
    if [ -f "$origin_user_rsa_pub" ]
      then
        mkdir -v "$target_user_ssh_folder_path" &&
        cat "$origin_user_rsa_pub" > "$target_authorized_keys" &&
        target_authorized_keys_content=$(cat "$target_authorized_keys") &&
        info "$target_authorized_keys contains the following: $target_authorized_keys_content" &&
        chown -vR 1000 "$target_user_ssh_folder_path" &&
        chmod -v 700 "$target_user_ssh_folder_path" &&
        chmod -v 600 "$target_authorized_keys" ||
        error
      else
        warning "The ssh key \"$origin_user_rsa_pub\" can't be copied to \"$target_authorized_keys\" because it doesn't exist."
    fi
  else
    info "Skipped SSH-key copying.."
fi

info "Start chroot procedures..."

mount_chroot_binds

copy_qemu

copy_resolve_conf

question "Should the image password of the standart user \"$target_username\" be changed?(y/N)" && read -r change_password
if [ "$change_password" == "y" ]
  then
    info "Changing passwords on target system..."
    question "Type in new password: " && read -r password_1
    question "Repeat new password\"$target_username\"" && read -r password_2
    if [ "$password_1" = "$password_2" ]
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
  else
    info "Skipped password change..."
fi

question "Should the hostname be changed?(y/N)" && read -r change_hostname
if [ "$change_hostname" == "y" ]
  then
    question "Type in the hostname:" && read -r hostname;
    echo "$hostname" > "$root_mount_path""etc/hostname" || error "Changing hostname failed."
  else
    info "Skipped hostname change..."
fi

question "Should the image system be updated?(y/N)" && read -r update_system
if [ "$update_system" == "y" ]
  then
    (
    echo "yes | pacman-key --init"
    echo "yes | pacman-key --populate archlinuxarm"
    echo "yes | pacman -Syyu"
    ) | chroot "$root_mount_path" /bin/bash || error "Password change failed."
fi
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
