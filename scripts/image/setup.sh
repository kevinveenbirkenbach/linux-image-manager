#!/bin/bash
# shellcheck disable=SC2010  # ls  | grep allowed
# shellcheck source=/dev/null # Deactivate SC1090
# shellcheck disable=SC2015  # Deactivate bools hints
# shellcheck disable=SC2154  # Deactivate not referenced link
# @see https://wiki.polaire.nl/doku.php?id=archlinux-raspberry-encrypted
source "$(dirname "$(readlink -f "${0}")")/base.sh" || (echo "Loading base.sh failed." && exit 1)

install(){
  info "Installing $1..."
  case "$os" in
    "arch"|"manjaro")
      echo "pacman --noconfirm -S --needed $1" | chroot "$root_mount_path" /bin/bash || error
      ;;
    "moode"|"retropie")
      echo "yes | apt install $1" | chroot "$root_mount_path" /bin/bash || error
      ;;
    *)
      error "Package manager not supported."
      ;;
  esac
}

info "Setupscript for images started..."

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

question "Which distribution should be used(e.g.:arch,moode,retropie,manjaro):" && read -r os || error

case "$os" in
  "arch")
    question "Which Raspberry Pi will be used(e.g.:1,2,3,4,aarch64):" && read -r version
    base_download_url="http://os.archlinuxarm.org/os/";
    if [ "$version" == "1" ]
      then
        imagename="ArchLinuxARM-rpi-latest.tar.gz"
      else
        imagename="ArchLinuxARM-rpi-$version-latest.tar.gz"
    fi
    ;;
  "manjaro")
    question "Which version(e.g.:architect,gnome) should be used:" && read -r version
    case "$version" in
      "architect")
        image_checksum="6b1c2fce12f244c1e32212767a9d3af2cf8263b2"
        base_download_url="https://osdn.net/frs/redir.php?m=dotsrc&f=%2Fstorage%2Fg%2Fm%2Fma%2Fmanjaro%2Farchitect%2F20.0%2F";
        imagename="manjaro-architect-20.0-200426-linux56.iso"
        ;;
      "gnome")
        question "Which release(e.g.:20,21) should be used:" && read -r release
        case "$release" in
        "20")
          image_checksum="d16118207c546c18201703d80b6356b1522b47d0"
          base_download_url="https://osdn.net/frs/redir.php?m=dotsrc&f=/storage/g/m/ma/manjaro/gnome/20.0.1/"
          imagename="manjaro-gnome-20.0.1-200511-linux56.iso"
          ;;
        "21")
          image_checksum="3ee5c59d21b1d78ec7fc655acc8f05c47237c6c0"
          base_download_url="https://download.manjaro.org/gnome/21.2rc1/"
          imagename="manjaro-gnome-21.2rc1-211211-linux515.iso"
          ;;
        esac
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
    esac
    ;;
esac

question "Should the system be encrypted?(y/N)" && read -r encrypt_system

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
		info "Image \"$imagename\" doesn't exist under local path \"$image_path\"." &&
    info "Image \"$imagename\" gets downloaded from \"$download_url\"..." &&
		wget "$download_url" -O "$image_path" || error "Download from \"$download_url\" failed."
fi

info "Verifying image..."
if [[ -v image_checksum ]]
  then
    (info "Checking md5 checksum..." && echo "$image_checksum $image_path"| md5sum -c -) ||
    (info "Checking sha1 checksum..." && echo "$image_checksum $image_path"| sha1sum -c -) ||
    error "Verification failed. HINT: Force the download of the image."
  else
    warning "Verification is not possible. No checksum is defined."
fi

make_mount_folders

set_partition_paths

question "Which filesystem should be used(e.g.:btrfs,ext4):" && read -r root_filesystem

question "Should the image be transfered to $device_path?(y/N)" && read -r transfer_image
if [ "$transfer_image" = "y" ]
  then

    question "Should the partition table of $device_path be deleted?(y/N)" && read -r delete_partition_table
    if [ "$delete_partition_table" = "y" ]
      then
        info "Deleting..." &&
        wipefs -a "$device_path" || error
      else
        info "Skipping partition table deletion..."
    fi

    overwritte_device_with_zeros

    info "Starting image transfer..."
    if [ "$os" = "arch" ]
      then
        info "Creating partitions..." &&
        (	echo "o"       #Type o. This will clear out any partitions on the drive.
        	echo "p"       #Type p to list partitions. There should be no partitions left
        	echo "n"       #Type n,
        	echo "p"       #then p for primary,
        	echo "1"       #1 for the first partition on the drive,
        	echo ""        #Default start sector
        	echo "+300M"   #then type +300M for the last sector.
        	echo "t"       #Type t,
        	echo "c"       #then c to set the first partition to type W95 FAT32 (LBA).
        	echo "n"       #Type n,
        	echo "p"       #then p for primary,
        	echo "2"       #2 for the second partition on the drive,
        	echo ""        #Default start sector
        	echo ""        #Default end sector
        	echo "w"       #Write the partition table and exit by typing w.
        )| fdisk "$device_path" || error

        info "Format boot partition..." &&
        mkfs.vfat "$boot_partition_path" || error

        if [ "$encrypt_system" == "y" ]
          then
            info "Formating $root_partition_path with LUKS..." &&
            sudo cryptsetup -v luksFormat -c aes-xts-plain64 -s 512 -h sha512 --use-random -i 1000 "$root_partition_path" &&
            decrypt_root || error
        fi

        info "Format root partition..." &&
        "mkfs.$root_filesystem" -f "$root_mapper_path" || error
        mount_partitions;

        info "Root files will be transfered to device..." &&
        bsdtar -xpf "$image_path" -C "$root_mount_path" &&
        sync ||
        error

        info "Boot files will be transfered to device..." &&
        mv -v "$root_mount_path""boot/"* "$boot_mount_path" ||
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

if [ "$os" != "manjaro" ]
  then
  info "Start regular mounting procedure..."
  if mount | grep -q "$boot_partition_path"
    then
      info "$boot_partition_path is allready mounted..."
    else
      if mount | grep -q "$root_mapper_path"
        then
          info "$root_mapper_path is allready mounted..."
        else
          decrypt_root
          mount_partitions
      fi
  fi

  fstab_path="$root_mount_path""etc/fstab" &&
  fstab_search_string=$(echo "/dev/mmcblk0p1"| sed -e 's/[\/&]/\\&/g') &&
  fstab_replace_string=$(echo "UUID=$boot_partition_uuid"| sed -e 's/[\/&]/\\&/g') &&
  info "Seeding UUID to $fstab_path to avoid path conflicts..." &&
  sed -i "s/$fstab_search_string/$fstab_replace_string/g" "$fstab_path" &&
  info "Content of $fstab_path:$(cat "$fstab_path")" || error

  info "Define target paths..." &&
  target_home_path="$root_mount_path""home/" &&
  target_username=$(ls "$target_home_path") &&
  target_user_home_folder_path="$target_home_path$target_username/" &&
  target_user_ssh_folder_path="$target_user_home_folder_path"".ssh/" &&
  target_authorized_keys="$target_user_ssh_folder_path""authorized_keys" &&
  question "Should the ssh-key be copied to the image?(y/N)" && read -r copy_ssh_key || error
  if [ "$copy_ssh_key" == "y" ]
    then
      info "Copy ssh key to target..." &&
      origin_user_rsa_pub="$origin_user_home"".ssh/id_rsa.pub" || error
      if [ -f "$origin_user_rsa_pub" ]
        then
          mkdir -v "$target_user_ssh_folder_path" || warning "Folder \"$target_user_ssh_folder_path\" exists. Can't be created."
          cat "$origin_user_rsa_pub" > "$target_authorized_keys" &&
          target_authorized_keys_content=$(cat "$target_authorized_keys") &&
          info "$target_authorized_keys contains the following: $target_authorized_keys_content" &&
          chown -vR 1000 "$target_user_ssh_folder_path" &&
          chmod -v 700 "$target_user_ssh_folder_path" &&
          chmod -v 600 "$target_authorized_keys" || error
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

  question "Should the password of the standart user \"$target_username\" be changed?(y/N)" && read -r change_password
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
          ) | chroot "$root_mount_path" /bin/bash || error
        else
          error "Passwords didn't match."
      fi
    else
      info "Skipped password change..."
  fi

  hostname_path="$root_mount_path""etc/hostname"
  question "Should the hostname be changed?(y/N)" && read -r change_hostname
  if [ "$change_hostname" == "y" ]
    then
      question "Type in the hostname:" && read -r target_hostname;
      echo "$target_hostname" > "$hostname_path" || error
    else
      target_hostname=$(cat "$hostname_path")
      info "Skipped hostname change..."
  fi
  info "Used hostname is: $target_hostname"

  case "$os" in
    "arch"|"manjaro")
      info "Populating keys..." &&
      (
      echo "yes | pacman-key --init"
      echo "yes | pacman-key --populate archlinuxarm"
      ) | chroot "$root_mount_path" /bin/bash || error
    ;;
  esac

  question "Should the system be updated?(y/N)" && read -r update_system
  if [ "$update_system" == "y" ]
    then
      info "Updating system..."
      case "$os" in
        "arch"|"manjaro")
          echo "pacman --noconfirm -Syyu" | chroot "$root_mount_path" /bin/bash || error
          ;;
        "moode"|"retropie")
          (
          echo "yes | apt update"
          echo "yes | apt upgrade"
          ) | chroot "$root_mount_path" /bin/bash || error
          ;;
        *)
          warning "System update for operation system \"$os\" is not supported yet. Skipped."
          ;;
      esac
  fi

  info "Installing software for filesystem $root_filesystem..."
  if [ "$root_filesystem" == "btrfs" ]
    then
      install "btrfs-progs"
    else
      info "Skipped."
  fi

  if [ "$encrypt_system" == "y" ]
    then
      # Adapted this instruction for setting up encrypted systems @see https://gist.github.com/gea0/4fc2be0cb7a74d0e7cc4322aed710d38
      info "Setup encryption..." &&

      info "Installing neccessary software..." &&
      install "$(get_packages "server/luks")" &&

      dropbear_root_key_path="$root_mount_path""etc/dropbear/root_key" &&
      info "Adding $target_authorized_keys to dropbear..." &&
      cp -v "$target_authorized_keys" "$dropbear_root_key_path" &&

      #Concerning mkinitcpio warning @see https://gist.github.com/imrvelj/c65cd5ca7f5505a65e59204f5a3f7a6d
      mkinitcpio_path="$root_mount_path""etc/mkinitcpio.conf" &&
      info "Configuring $mkinitcpio_path..." &&
      mkinitcpio_search_modules="MODULES=()" &&
      mkinitcpio_replace_modules="MODULES=(g_cdc usb_f_acm usb_f_ecm smsc95xx g_ether)" &&
      mkinitcpio_search_binaries="BINARIES=()" &&
      mkinitcpio_replace_binaries=$(echo "BINARIES=(/usr/lib/libgcc_s.so.1)"| sed -e 's/[\/&]/\\&/g') &&
      mkinitcpio_encrypt_hooks="sleep netconf dropbear encryptssh" &&
      mkinitcpio_search_hooks="HOOKS=(base udev autodetect modconf block filesystems keyboard fsck)" &&
      mkinitcpio_replace_hooks="HOOKS=(base udev autodetect modconf block $mkinitcpio_encrypt_hooks filesystems keyboard fsck)" &&
      sed -i "s/$mkinitcpio_search_modules/$mkinitcpio_replace_modules/g" "$mkinitcpio_path" &&
      sed -i "s/$mkinitcpio_search_binaries/$mkinitcpio_replace_binaries/g" "$mkinitcpio_path" &&
      sed -i "s/$mkinitcpio_search_hooks/$mkinitcpio_replace_hooks/g" "$mkinitcpio_path" &&
      info "Content of $mkinitcpio_path:$(cat "$mkinitcpio_path")" &&
      info "Generating mkinitcpio..." &&
      echo "mkinitcpio -vP" | chroot "$root_mount_path" /bin/bash &&

      fstab_insert_line="UUID=$root_partition_uuid  / $root_filesystem    defaults,noatime  0  1" &&
      info "Configuring $fstab_path..." || error
      if grep -q "$fstab_insert_line" "$fstab_path"
        then
          warning "$fstab_path contains allready $fstab_insert_line - Skipped."
        else
          echo "$fstab_insert_line" >> "$fstab_path" || error
      fi
      info "Content of $fstab_path:$(cat "$fstab_path")" &&

      crypttab_path="$root_mount_path""etc/crypttab" &&
      crypttab_insert_line="$root_mapper_name UUID=$root_partition_uuid none luks" &&
      info "Configuring $crypttab_path..." || error
      if grep -q "$crypttab_insert_line" "$crypttab_path"
        then
          warning "$crypttab_path contains allready $crypttab_insert_line - Skipped."
        else
          echo "$crypttab_insert_line" >> "$crypttab_path" || error
      fi
      info "Content of $crypttab_path:$(cat "$crypttab_path")" &&

      boot_txt_path="$boot_mount_path""boot.txt" &&
      cryptdevice_configuration="cryptdevice=UUID=$root_partition_uuid:$root_mapper_name root=$root_mapper_path" || error
      if [ -f "$boot_txt_path" ];
        then
          info "Configuring $boot_txt_path..." &&
          boot_txt_delete_line=$(echo "part uuid \${devtype} \${devnum}:2 uuid" | sed -e 's/[]\/$*.^[]/\\&/g') &&
          boot_txt_setenv_origin=$(echo "setenv bootargs console=ttyS1,115200 console=tty0 root=PARTUUID=\${uuid} rw rootwait smsc95xx.macaddr=\"\${usbethaddr}\"" | sed -e 's/[]\/$*.^[]/\\&/g') &&
          boot_txt_setenv_replace=$(echo "setenv bootargs console=ttyS1,115200 console=tty0 ip=::::$target_hostname:eth0:dhcp $cryptdevice_configuration rw rootwait smsc95xx.macaddr=\"\${usbethaddr}\""| sed -e 's/[\/&]/\\&/g') &&
          sed -i "s/$boot_txt_delete_line//g" "$boot_txt_path" &&
          sed -i "s/$boot_txt_setenv_origin/$boot_txt_setenv_replace/g" "$boot_txt_path" &&
          info "Content of $boot_txt_path:$(cat "$boot_txt_path")" &&
          info "Generating..." &&
          echo "cd /boot/ && ./mkscr || exit 1" | chroot "$root_mount_path" /bin/bash || error
        else
          cmdline_txt_path="$boot_mount_path""cmdline.txt" &&
          info "Configuring $cmdline_txt_path..." &&
          cmdline_search_string=$(echo "root=/dev/mmcblk0p2" | sed -e 's/[\/&]/\\&/g') &&
          cmdline_replace_string=$(echo "$cryptdevice_configuration rootfstype=$root_filesystem"| sed -e 's/[\/&]/\\&/g') &&
          sed -i "s/$cmdline_search_string/$cmdline_replace_string/g" "$cmdline_txt_path"  &&
          info "Content of $cmdline_txt_path:$(cat "$cmdline_txt_path")" || error
        fi
  fi

  question "Do you want to setup Wifi on the device?(y/N)" && read -r setup_wifi
  if [ "$setup_wifi" = "y" ]
    then
      question "Please type in the ssid:" && read -r ssid
      question "Please type in the psk:" && read -r psk
      case "$os" in
        "retropie")
          wifi_file="$boot_mount_path""wifikeyfile.txt" &&
          echo "ssid=\"$ssid\"" > "$wifi_file" &&
          echo "psk=\"$psk\"" >> "$wifi_file" || error
          ;;
        *)
          warning "Wifi setting for operation system \"$os\" is not supported yet. Skipped."
          ;;
      esac
  fi

  info "Running system specific procedures..."
  if [ "$os" = "retropie" ]
    then
      question "Should the roms be copied to the system?(y/N)" && read -r copy_roms
      if [ "$copy_roms" == "y" ]
        then
          target_roms_path="$target_user_home_folder_path""/RetroPie/roms/" &&
          source_roms_path="$origin_user_home""Games/roms/" &&
          info "Copy roms from $source_roms_path to $target_roms_path..." &&
          cp -v "$source_roms_path" "$target_roms_path" &&
          chown -vR 1000 "$target_roms_path" || error
      fi
      question "Should the RetroFlag specific procedures be executed?(y/N)" && read -r setup_retroflag
      if [ "$setup_retroflag" == "y" ]
        then
          info "Executing RetroFlag specific procedures..." &&
          (
          echo 'wget -O - "https://raw.githubusercontent.com/RetroFlag/retroflag-picase/master/install_gpi.sh" | bash'
          ) | chroot "$root_mount_path" /bin/bash || error
      fi
  fi
fi
destructor
success "Setup successfull :)" && exit 0
