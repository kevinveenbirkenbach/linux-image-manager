#!/bin/bash
# shellcheck disable=SC2010
# shellcheck disable=SC2015  # Deactivating bool hint
# shellcheck source=/dev/null # Deactivate SC1090
source "$(dirname "$(readlink -f "${0}")")/base.sh" || (echo "Loading base.sh failed." && exit 1)
info "Backupscript for memory devices started..."
echo
set_device_path
while [ "$path" == "" ]
	do
		echo "Bitte Backupimagepfad+Namen zu $PWD eingeben:"
		read -r path
		if [ "${path:0:1}" == "/" ]
			then
				ofi="$path.img"
			else
				ofi="$PWD/$path.img"
		fi
done
info "Input file: $device_path"
info "Output file: $ofi"
question "Please confirm by pushing \"Enter\". To cancel use \"Ctrl + Alt + C\""
read -r bestaetigung && echo "$bestaetigung";

info "Imagetransfer starts. This can take a while..." &&
dd if="$device_path" of="$ofi" bs=1M status=progress || error "\"dd\" failed.";

success "Imagetransfer successfull." && exit 0;
