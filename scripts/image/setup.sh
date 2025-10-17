#!/bin/bash
# shellcheck disable=SC2010  # ls  | grep allowed
# shellcheck source=/dev/null # Deactivate SC1090
# shellcheck disable=SC2015  # Deactivate bools hints
# shellcheck disable=SC2154  # Deactivate not referenced link
# @see https://wiki.polaire.nl/doku.php?id=archlinux-raspberry-encrypted
source "$(dirname "$(readlink -f "${0}")")/base.sh" || (echo "Loading base.sh failed." && exit 1)

install(){
  info "Installing $1..."
  case "$distribution" in
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

replace_in_file() {
  # Assign the first function argument to the local variable search_string
  local search_string=$1
  # Assign the second function argument to the local variable replace_string
  local replace_string=$2
  # Assign the third function argument to the local variable file_path
  local file_path=$3

  # Create a temporary file and store its path in temp_file
  temp_file=$(mktemp)

  # Use sed to replace the search_string with replace_string in the file at file_path
  # Write the output to the temporary file
  sed "s/$search_string/$replace_string/g" "$file_path" > "$temp_file"

  # Compare the original file with the temporary file
  if cmp -s "$file_path" "$temp_file"; then
    # If files are identical, remove the temporary file and signal an error
    rm -f "$temp_file"
    error "Error: Search string '$search_string' not found in $file_path."
  else
    # If files are different, move the temporary file to overwrite the original file
    mv "$temp_file" "$file_path"
  fi
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
image_folder="$origin_user_home""Software/Images/";
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

question "Which operation system would you like to use [linux,windows,...]?" && read -r operation_system || error

case "$operation_system" in
  "linux")
    question "Which distribution should be used [arch,moode,retropie,manjaro,torbox...]?" && read -r distribution || error

    case "$distribution" in
      "android-x86")
        base_download_url="https://www.fosshub.com/Android-x86.html?dwl=android-x86_64-9.0-r2.iso";
        image_name="android-x86_64-9.0-r2.iso"
        image_checksum="f7eb8fc56f29ad5432335dc054183acf086c539f3990f0b6e9ff58bd6df4604e"
        boot_size="+500M"
        ;;
      "torbox")
        base_download_url="https://www.torbox.ch/data/";
        image_name="torbox-20220102-v050.gz"
        image_checksum="0E1BA7FFD14AAAE5F0462C8293D95B62C3BF1D9E726E26977BD04772C55680D3"
        boot_size="+200M"
        ;;
      "arch")
        question "Which Raspberry Pi will be used (e.g.: 1, 2, 3b, 3b+, 4...):" && read -r raspberry_pi_version
        boot_size="+500M"
        base_download_url="http://os.archlinuxarm.org/os/";
        case "$raspberry_pi_version" in
          "1")
            image_name="ArchLinuxARM-rpi-armv7-latest.tar.gz"
            luks_memory_cost="64000"
            ;;
          "2")
            image_name="ArchLinuxARM-rpi-armv7-latest.tar.gz"
            luks_memory_cost="128000"
            ;;
           "3b" | "3b+")
            image_name="ArchLinuxARM-rpi-aarch64-latest.tar.gz"
            luks_memory_cost="128000"
            ;;
            "4" )
            image_name="ArchLinuxARM-rpi-aarch64-latest.tar.gz"
            luks_memory_cost="256000"
            ;;
          *)
            error "Version $raspberry_pi_version isn't supported."
            ;;
        esac
        ;;
      "manjaro")
        question "Which version(e.g.:architect,gnome) should be used:" && read -r gnome_version
        boot_size="+500M"
        case "$gnome_version" in
          "architect")
            image_checksum="6b1c2fce12f244c1e32212767a9d3af2cf8263b2"
            base_download_url="https://osdn.net/frs/redir.php?m=dotsrc&f=%2Fstorage%2Fg%2Fm%2Fma%2Fmanjaro%2Farchitect%2F20.0%2F";
            image_name="manjaro-architect-20.0-200426-linux56.iso"
            ;;
          "gnome")
            question "Which release(e.g.:20,21,raspberrypi) should be used:" && read -r release
            case "$release" in
            "20")
              image_checksum="2df3697908483550d4a473815b08c1377e6b6892"
              base_download_url="https://osdn.net/projects/manjaro-archive/storage/gnome/20.0/"
              image_name="manjaro-gnome-20.0-200426-linux56.iso"
              ;;
            "21")
              base_download_url="https://download.manjaro.org/gnome/21.3.7/"
              image_name="manjaro-gnome-21.3.7-220816-linux515.iso"
              ;;
            "22")
              base_download_url="https://download.manjaro.org/gnome/22.1.3/"
              image_name="manjaro-gnome-22.1.3-230529-linux61.iso"
              ;;
            "24")
              base_download_url="https://download.manjaro.org/gnome/24.2.1/"
              image_name="manjaro-gnome-24.2.1-241216-linux612.iso"
              ;;
            "25")
              base_download_url="https://download.manjaro.org/gnome/25.0.10/"
              image_name="manjaro-gnome-25.0.10-251013-linux612.iso"
              ;;
            "raspberrypi")
              # at the moment just optimized for raspberry pi 4
              base_download_url="https://github.com/manjaro-arm/rpi4-images/releases/download/23.02/"
              image_name="Manjaro-ARM-gnome-rpi4-23.02.img.xz"
              luks_memory_cost="256000"
              raspberry_pi_version="4"
              ;;
            *)
              error "Gnome Version $gnome_version isn't supported."
              ;;
            esac
            ;;
        esac
        ;;
      "moode")
        boot_size="+200M"
        image_checksum="185cbc9a4994534bb7a4bc2744c78197"
        base_download_url="https://github.com/moode-player/moode/releases/download/r651prod/"
        image_name="moode-r651-iso.zip";
        ;;
      "retropie")
        boot_size="+500M"
        question "Which version(e.g.:1,2,3,4) should be used:" && read -r raspberry_pi_version
        base_download_url="https://github.com/RetroPie/RetroPie-Setup/releases/download/4.8/";
        case "$raspberry_pi_version" in
          "1")
            image_checksum="95a6f84453df36318830de7e8507170e"
            image_name="retropie-buster-4.8-rpi1_zero.img.gz"
            ;;
          "2" | "3")
            image_checksum="224e64d8820fc64046ba3850f481c87e"
            image_name="retropie-buster-4.8-rpi2_3_zero2w.img.gz"
            ;;

          "4")
            image_checksum="b5daa6e7660a99c246966f3f09b4014b"
            image_name="retropie-buster-4.8-rpi4_400.img.gz"
            ;;
        esac
        ;;
    esac

    question "Should the system be encrypted?(y/N)" && read -r encrypt_system

    info "Generating os-image..."
    download_url="$base_download_url$image_name"
    image_path="$image_folder$image_name"

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
        info "Image \"$image_name\" doesn't exist under local path \"$image_path\"." &&
        info "Image \"$image_name\" gets downloaded from \"$download_url\"..." &&
        wget "$download_url" -O "$image_path" || error "Download from \"$download_url\" failed."
    fi
    ;;
  *)
    info "Available images:"
    ls -l "$image_folder"
    question "Which image would you like to use?" && read -r image_name || error
    image_path="$image_folder$image_name"
  ;;
esac

info "Verifying image..."
info "Verifying checksum..."
if [ -z "$image_checksum" ]; then
    for ext in sha1 sha512 md5; do
        sha_download_url="$download_url.$ext"
        info "Image Checksum is not defined. Try to download image signature from $sha_download_url."
        if wget -q --method=HEAD "$sha_download_url"; then
            image_checksum="$(wget $sha_download_url -q -O - | cut -d ' ' -f1)"
            info "Defined image_checksum as $image_checksum"
            break
        else
            warning "No checksum found under $sha_download_url."
        fi
    done
fi

if [[ -v image_checksum ]]; then
  info "A checksum is defined for the image."
  info "Checksums verify file integrity to ensure that the file was not corrupted during download."
  info "The script will try verifying the integrity using MD5, then SHA1, and finally SHA256 if needed."
  
  info "Trying MD5 checksum verification..."
  (info "Checking md5 checksum..." && echo "$image_checksum $image_path" | md5sum -c -) ||
  (warning "MD5 verification failed. This may indicate data corruption." &&
   info "Trying SHA1 checksum verification for a secondary integrity check..." &&
   info "Checking sha1 checksum..." && echo "$image_checksum $image_path" | sha1sum -c -) ||
  (warning "SHA1 verification failed. Attempting SHA256 verification for thoroughness." &&
   info "SHA256 provides a more robust check and is used as a final integrity measure." &&
   info "Checking sha256 checksum..." && echo "$image_checksum $image_path" | sha256sum -c -) ||
  error "Verification failed. HINT: Force the download of the image."
else
  warning "No checksum is defined. Skipping checksum verification."
fi

info "Note: Checksums verify integrity but do not confirm authenticity."
info "Proceeding to signature verification, which ensures the file comes from a trusted source."
signature_download_url="$download_url.sig"
info "Attempting to download the image signature from: $signature_download_url"
info "Try to download image signature from $signature_download_url."

if wget -q --method=HEAD "$signature_download_url"; then
    signature_name="${image_name}.sig"
    signature_path="${image_folder}${signature_name}"

    info "Download the signature file"
    if wget -q -O "$signature_path" "$signature_download_url"; then
        info "Extract the key ID from the signature file"
        key_id=$(gpg --status-fd 1 --verify "$signature_path" "$image_path" 2>&1 | grep 'NO_PUBKEY' | awk '{print $NF}')
        
        if [ -n "$key_id" ]; then
            info "Check if the key is already in the keyring"
            if gpg --list-keys "$key_id" > /dev/null 2>&1; then
                info "Key $key_id already in keyring."
            else
                info "Import the public key"
                gpg --keyserver keyserver.ubuntu.com --recv-keys "$key_id"
            fi

            info "Verify the signature again after importing the key"
            if gpg --verify "$signature_path" "$image_path"; then
                info "Signature verification succeeded."
            else
                warning "Signature verification failed."
            fi
        else
            warning "No public key found in the signature file."
        fi
    else
        warning "Failed to download the signature file."
    fi
else
    warning "No signature found under $signature_download_url."
fi


make_mount_folders

set_partition_paths

question "Which filesystem should be used? E.g.:btrfs,ext4... (none):" && read -r root_filesystem

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

    overwrite_device

    info "Starting image transfer..."
    if [ "$distribution" = "arch" ]
      then
        # Set default size of the boot partition
        boot_size=${boot_size:-"+500M"}

        # Use the provided size or the default size
        info "The boot partition will be set to $boot_size."

        # Partitioning with the specified size
        info "Creating partitions..." &&
        (
          echo "o"       # Type o. This will clear out any partitions on the drive.
          echo "p"       # Type p to list partitions. There should be no partitions left
          echo "n"       # Type n,
          echo "p"       # then p for primary,
          echo "1"       # 1 for the first partition on the drive,
          echo ""        # Default start sector
          echo "$boot_size"  # Size of the boot partition
          echo "t"       # Type t,
          echo "c"       # then c to set the first partition to type W95 FAT32 (LBA).
          echo "n"       # Type n,
          echo "p"       # then p for primary,
          echo "2"       # 2 for the second partition on the drive,
          echo ""        # Default start sector
          echo ""        # Default end sector
          echo "w"       # Write the partition table and exit by typing w.
        ) | fdisk "$device_path" || error

        info "Format boot partition..." &&
        mkfs.vfat "$boot_partition_path" || error

        if [ "$encrypt_system" == "y" ]
          then
              # Check if luks_memory_cost is defined and set the luksAddKey command accordingly
              # @see https://chatgpt.com/share/008ea5f1-670c-467c-8320-1ca67f25ac9a
              if [ -n "$luks_memory_cost" ]; then
                info "Formating $root_partition_path with LUKS with --pbkdf-memory set to $luks_memory_cost" &&
                sudo cryptsetup -v luksFormat -c aes-xts-plain64 -s 512 -h sha512 --use-random -i 1000 --pbkdf-memory "$luks_memory_cost" "$root_partition_path" || error
              else
                info "Formating $root_partition_path with LUKS" &&
                sudo cryptsetup -v luksFormat -c aes-xts-plain64 -s 512 -h sha512 --use-random -i 1000 "$root_partition_path" || error
              fi
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
          pv "$image_path" | sudo dd of="$device_path" bs="$OPTIMAL_BLOCKSIZE" conv=fsync &&
          sync ||
          error
      elif [ "${image_path: -3}" = ".xz" ]
        then
          info "Transferring .xz file..." &&
          unxz -c "$image_path" | sudo dd of="$device_path" bs="$OPTIMAL_BLOCKSIZE" conv=fsync status=progress &&
          sync ||
          error
      else
        error "Image transfer for operation system \"$distribution\" is not supported yet!";
      fi
  else
    info "Skipping image transfer..."
fi

# Execute Raspberry Pi specific procedures
if [ -n "$raspberry_pi_version" ]
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
  administrator_username="administrator"
  target_home_path="$root_mount_path""home/" &&
  default_username=$(ls "$target_home_path") &&

  question "Should the $default_username be renamed to $administrator_username? (y/N):" && read -r rename_decision
  if [ "$rename_decision" == "y" ]; 
    then
      variable_old_username="$default_username" &&
      target_username="$administrator_username" &&
      info "Rename home directory from $target_home_path$variable_old_username to $target_home_path$target_username..." &&
      mv -v "$target_home_path$variable_old_username" "$target_home_path$target_username" || error "Failed to rename home directory" 
    else
      target_username="$default_username"
  fi

  target_user_home_folder_path="$target_home_path$target_username/" &&
  target_user_ssh_folder_path="$target_user_home_folder_path"".ssh/" &&
  target_authorized_keys="$target_user_ssh_folder_path""authorized_keys" &&

  # Activate later. Here was a bug
  question "Should the $target_username have sudo rights? (y/N):" && read -r sudo_decision
  if [ "$sudo_decision" == "y" ]; then
    sudo_config_dir="$root_mount_path""etc/sudoers.d/"
    sudo_config_file="$sudo_config_dir$target_username"
    mkdir -vp $sudo_config_dir
    echo "$target_username ALL=(ALL:ALL) ALL" > "$sudo_config_file" || error "Failed to create sudoers file for $target_username"
    chmod 440 "$sudo_config_file" || error "Failed to set permissions on sudoers file for $target_username"
  fi

  question "Enter the path to the SSH key to be added to the image (default: none):" && read -r origin_user_rsa_pub || error
  if [ -z "$origin_user_rsa_pub" ]
    then
      info "Skipped SSH-key copying.."
    else  
        if [ -f "$origin_user_rsa_pub" ]
          then
            info "Copy ssh key to target..."
            mkdir -v "$target_user_ssh_folder_path" || warning "Folder \"$target_user_ssh_folder_path\" exists. Can't be created."
            cat "$origin_user_rsa_pub" > "$target_authorized_keys" &&
            target_authorized_keys_content=$(cat "$target_authorized_keys") &&
            info "$target_authorized_keys contains the following: $target_authorized_keys_content" &&
            info "Set permissions with chmod..." &&
            chmod -v 700 "$target_user_ssh_folder_path" &&
            chmod -v 600 "$target_authorized_keys" || error "Failed to set ownership and permissions on ssh folder"
          else
            error "The ssh key \"$origin_user_rsa_pub\" can't be copied to \"$target_authorized_keys\" because it doesn't exist."
        fi  
  fi

  info "Start chroot procedures..."

  mount_chroot_binds

  copy_qemu

  copy_resolve_conf

  chroot_user_home_path="/home/$target_username/"
  chroot_user_ssh_folder_path="$chroot_user_home_path.ssh"
  if [ "$rename_decision" == "y" ]; then
    info "Delete old user and create new user" &&
    (
    echo "userdel -r $variable_old_username"
    echo "useradd -m -d $chroot_user_home_path -s /bin/bash $target_username"
    echo "chown -R $target_username:$target_username $chroot_user_home_path"
    ) | chroot "$root_mount_path" /bin/bash || error "Failed to delete old user and create new user"
  fi

  if [ -n "$origin_user_rsa_pub" ]
    then
      info "Chroot to set ownership..." &&
      ( echo "chown -vR $target_username:$target_username $chroot_user_ssh_folder_path" ) | chroot "$root_mount_path" /bin/bash || error
  fi  
  question "Type in new password for user root  and $target_username (leave empty to skip): " && read -r password_1

  if [ -n "$password_1" ]; then
    question "Repeat new password for \"$target_username\": " && read -r password_2
    if [ "$password_1" = "$password_2" ]; then
      info "Changing passwords on target system..."
      (
        echo "(
              echo '$password_1'
              echo '$password_1'
              ) | passwd $target_username"
        echo "(
              echo '$password_1'
              echo '$password_1'
        ) | passwd"
      ) | chroot "$root_mount_path" /bin/bash || error "Failed to change password."
    else
      error "Passwords didn't match."
    fi
  else
    info "No password change requested, skipped password change..."
  fi


  hostname_path="$root_mount_path/etc/hostname"

  question "Type in the hostname (leave empty to skip): " && read -r target_hostname

  if [ -n "$target_hostname" ]; then
    echo "$target_hostname" > "$hostname_path" || error "Failed to set hostname."
  else
    target_hostname=$(cat "$hostname_path")
    info "No hostname change requested, skipped hostname change..."
  fi

  info "Used hostname is: $target_hostname"

  case "$distribution" in
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
      case "$distribution" in
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
          warning "System update for operation system \"$distribution\" is not supported yet. Skipped."
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
      # Adapted this instruction for setting up encrypted systems 
      # @see https://gist.github.com/gea0/4fc2be0cb7a74d0e7cc4322aed710d38
      # @see https://gist.github.com/EnigmaCurry/2f9bed46073da8e38057fe78a61e7994
      info "Setup encryption..." &&

      info "Installing neccessary software..." &&
      install "$(get_packages "server/luks")" &&

      dropbear_root_key_path="$root_mount_path""etc/dropbear/root_key" &&
      info "Adding $target_authorized_keys to dropbear..." &&
      cp -v "$target_authorized_keys" "$dropbear_root_key_path" &&

      # Concerning mkinitcpio warning 
      # @see https://gist.github.com/imrvelj/c65cd5ca7f5505a65e59204f5a3f7a6d
      mkinitcpio_path="$root_mount_path""etc/mkinitcpio.conf" &&
      info "Configuring $mkinitcpio_path..." &&
      mkinitcpio_search_modules="MODULES=()" || error

      # Concerning which moduls to load 
      # @see https://raspberrypi.stackexchange.com/questions/67051/raspberry-pi-3-with-archarm-and-encrypted-disk-will-not-boot-how-can-be-identif

      case "$raspberry_pi_version" in
        "1" | "2")
          mkinitcpio_additional_modules=""
          ;;
          "3b")
          mkinitcpio_additional_modules="smsc95xx"
          ;;
          "3b+" | "4")
          mkinitcpio_additional_modules="lan78xx"
          ;;
        *)
          warning "Version $raspberry_pi_version isn't supported."
          ;;
      esac

      mkinitcpio_replace_modules="MODULES=(g_cdc usb_f_acm usb_f_ecm $mkinitcpio_additional_modules g_ether)" || error

      
      mkinitcpio_search_binaries="BINARIES=()" &&
      mkinitcpio_replace_binaries=$(echo "BINARIES=(/usr/lib/libgcc_s.so.1)"| sed -e 's/[\/&]/\\&/g') &&
      mkinitcpio_encrypt_hooks="sleep netconf dropbear encryptssh" &&
      mkinitcpio_hooks_prefix="base udev autodetect microcode modconf kms keyboard keymap consolefont block"
      mkinitcpio_hooks_suffix="filesystems fsck"
      mkinitcpio_search_hooks="HOOKS=($mkinitcpio_hooks_prefix $mkinitcpio_hooks_suffix)" &&
      mkinitcpio_replace_hooks="HOOKS=($mkinitcpio_hooks_prefix $mkinitcpio_encrypt_hooks $mkinitcpio_hooks_suffix)" &&
      replace_in_file "$mkinitcpio_search_modules" "$mkinitcpio_replace_modules" "$mkinitcpio_path" &&
      replace_in_file "$mkinitcpio_search_binaries" "$mkinitcpio_replace_binaries" "$mkinitcpio_path" &&
      replace_in_file "$mkinitcpio_search_hooks" "$mkinitcpio_replace_hooks" "$mkinitcpio_path" &&
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
          # Concerning issues with network adapter names;
          # @see https://forum.iobroker.net/topic/40542/raspberry-pi4-kein-eth0-mehr/16
          boot_txt_setenv_replace=$(echo "setenv bootargs console=ttyS1,115200 console=tty0 ip=::::$target_hostname:eth0:dhcp $cryptdevice_configuration rw rootwait smsc95xx.macaddr=\"\${usbethaddr}\" net.ifnames=0 biosdevname=0"| sed -e 's/[\/&]/\\&/g') &&
          replace_in_file "$boot_txt_delete_line" "" "$boot_txt_path" &&
          replace_in_file "$boot_txt_setenv_origin" "$boot_txt_setenv_replace" "$boot_txt_path" &&
          info "Content of $boot_txt_path:$(cat "$boot_txt_path")" &&
          info "Generating..." &&
          echo "cd /boot/ && ./mkscr || exit 1" | chroot "$root_mount_path" /bin/bash || error
        else
          cmdline_txt_path="$boot_mount_path""cmdline.txt" &&
          info "Configuring $cmdline_txt_path..." &&
          cmdline_search_string=$(echo "root=/dev/mmcblk0p2" | sed -e 's/[\/&]/\\&/g') &&
          cmdline_replace_string=$(echo "$cryptdevice_configuration rootfstype=$root_filesystem"| sed -e 's/[\/&]/\\&/g') &&
          replace_in_file "$cmdline_search_string" "$cmdline_replace_string" "$cmdline_txt_path" &&
          info "Content of $cmdline_txt_path:$(cat "$cmdline_txt_path")" || error
        fi
  fi

  info "Running system specific procedures..."
  if [ "$distribution" = "retropie" ]
    then
      if [ -n "$origin_user_rsa_pub" ]
        then
          ssh_file="$boot_mount_path""ssh" &&
          echo "" > "$ssh_file"
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
