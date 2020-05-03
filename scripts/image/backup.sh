#!/bin/bash
info "Backupscript for memory devices started"
echo
info "Actual mounted devices:"
echo
ls -lasi /dev/ | grep -E "sd|mm"
echo
while [ \! -b "$ifi" ]
	do
		info "Please select the correct device."
		question "/dev/:"
		read device
		ifi="/dev/$device"
done
while [ "$path" == "" ]
	do
		echo "Bitte Backupimagepfad+Namen zu $(pwd) eingeben:"
		read path
		if [ "${path:0:1}" == "/" ]
			then
				ofi=$path.img
			else
				ofi=$(pwd)"/"$path.img
		fi
done
info "Input file: $ifi"
info "Output file: $ofi"
question "Please confirm by pushing \"Enter\". To cancel use \"Ctrl + Alt + C\""
read bestaetigung
dd if=$ifi of=$ofi bs=1M status=progress
