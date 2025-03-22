#!/bin/bash
#
# This script contains the global program variables and functions
#
# shellcheck disable=SC2034 #Deactivate checking of unused variables
# shellcheck disable=SC2003 #Deactivate "expr is antiquated"
# shellcheck disable=SC2015 #Deactivate bool hint
# shellcheck disable=SC2005 #Remove useless echo hint
# shellcheck disable=SC2010 #Deactivate ls | grep hint
REPOSITORY_PATH="$(readlink -f "${0}" | sed -e 's/\/scripts\/.*//g')"
CONFIGURATION_PATH="$REPOSITORY_PATH""/configuration/"
PACKAGE_PATH="$CONFIGURATION_PATH""packages/"
TEMPLATE_PATH="$CONFIGURATION_PATH""templates/";
HOME_TEMPLATE_PATH="$TEMPLATE_PATH""home/";
ENCRYPTED_PATH="$REPOSITORY_PATH/.encrypted";
DECRYPTED_PATH="$REPOSITORY_PATH/decrypted";
SCRIPT_PATH="$REPOSITORY_PATH/scripts/";
DATA_PATH="$DECRYPTED_PATH/data";
BACKUP_PATH="$DECRYPTED_PATH/backup";

COLOR_RED=$(tput setaf 1)
COLOR_GREEN=$(tput setaf 2)
COLOR_YELLOW=$(tput setaf 3)
COLOR_BLUE=$(tput setaf 4)
COLOR_MAGENTA=$(tput setaf 5)
COLOR_CYAN=$(tput setaf 6)
COLOR_WHITE=$(tput setaf 7)
COLOR_RESET=$(tput sgr0)

# FUNCTIONS

message(){
  echo "$1[$2]:${COLOR_RESET} $3 ";
}

question(){
  message "${COLOR_MAGENTA}" "QUESTION" "$1";
}

info(){
  message "${COLOR_BLUE}" "INFO" "$1";
}

warning(){
  message "${COLOR_YELLOW}" "WARNING" "$1";
}

success(){
  message "${COLOR_GREEN}" "SUCCESS" "$1";
}

error(){
  if [ -z "$1" ]
    then
      message="Failed."
    else
      message="$1"
  fi
  message "${COLOR_RED}" "ERROR" "$message -> Leaving program."
  if declare -f "destructor" > /dev/null
    then
      info "Calling destructor..."
      destructor
    else
      warning "No destructor defined."
      info "Can be that this script left some waste."
  fi
  exit 1;
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
  info "Device path set to: $device_path"
  # @see https://www.heise.de/ct/hotline/Optimale-Blockgroesse-fuer-dd-2056768.html
  PHYSICAL_BLOCK_SIZE_PATH="/sys/block/$device/queue/physical_block_size"
  if [ -f "$PHYSICAL_BLOCK_SIZE_PATH" ]; then
      PHYSICAL_BLOCK_SIZE=$(sudo cat $PHYSICAL_BLOCK_SIZE_PATH)
      if [ $? -eq 0 ]; then
          OPTIMAL_BLOCKSIZE=$((64 * PHYSICAL_BLOCK_SIZE)) || error
      else
          echo "Unable to read $PHYSICAL_BLOCK_SIZE_PATH"
          OPTIMAL_BLOCKSIZE="4K"
      fi
  else
      OPTIMAL_BLOCKSIZE="4K"
  fi
  info "Optimal blocksize set to: $OPTIMAL_BLOCKSIZE" || error
}

print_partition_table_info() {
  echo "##########################################################################################"
  echo "Note on Partition Table Deletion:"
  echo "---------------------------------------------"
  echo "• MBR (Master Boot Record):"
  echo "  - Typically occupies the first sector (512 bytes), i.e., 1 block."
  echo ""
  echo "• GPT (GUID Partition Table):"
  echo "  - Uses a protective MBR (1 block), a GPT header (1 block),"
  echo "    and usually a partition entry array that takes up about 32 blocks."
  echo "  - Total: approximately 34 blocks (assuming a 512-byte block size)."
  echo ""
  echo "Recommendation: For deleting a GPT partition table, use a block size of 512 bytes"
  echo "                and overwrite at least 34 blocks to ensure the entire table is cleared."
  echo "##########################################################################################"
}

overwrite_device() {
  # Call the function to display the information.
  print_partition_table_info

  question "Should $device_path be overwritten with zeros before copying? (y/N/block count)" && read -r copy_zeros_to_device
  case "$copy_zeros_to_device" in
    y)
      info "Overwriting entire device..." &&
      dd if=/dev/zero of="$device_path" bs="$OPTIMAL_BLOCKSIZE" status=progress && sync || error "Overwriting $device_path failed."
      ;;
    N|'')
      info "Skipping Overwriting..."
      ;;
    ''|*[!0-9]*)
      error "Invalid input."
      ;;
    *)
      if [[ "$copy_zeros_to_device" =~ ^[0-9]+$ ]]; then
        info "Overwriting $copy_zeros_to_device blocks..." &&
        dd if=/dev/zero of="$device_path" bs="$OPTIMAL_BLOCKSIZE" count="$copy_zeros_to_device" status=progress && sync || error "Overwriting $device_path failed."
      else
        error "Invalid input. Block count must be a number."
      fi
      ;;
  esac
}

get_packages(){
  for package_collection in "$@"
  do
    package_collection_path="$PACKAGE_PATH""$package_collection.txt" &&
    echo "$(sed -e "/^#/d" -e "s/#.*//" "$package_collection_path" | tr '\n' ' ')" ||
    error
  done
}

HEADER(){
  echo
  echo "${COLOR_YELLOW}The"
  echo "LINUX IMAGE MANAGER"
  echo "is an administration tool designed from and for Kevin Veen-Birkenbach."
  echo
  echo "Licensed under GNU GENERAL PUBLIC LICENSE Version 3"
  echo "${COLOR_RESET}"
}

HEADER
