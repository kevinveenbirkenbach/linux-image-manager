#!/bin/bash
echo "Backupscript fuer SD's"
echo "@author KevinFrantz"
echo "@since 2017-03-17"
echo 
echo "Liste der aktuell gemounteten Geraete:"
echo 
ls -lasi /dev/ | grep "sd"
echo "(Die Liste zeigt nur Geraete an welche auf den Filter /dev/sd* passen)"
echo
while [ \! -b "$ifi" ]
	do
		echo "Bitte waehlen Sie die korrekte SD-Karte aus:"
		echo "/dev/:"
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
echo "Inputfile: $ifi"
echo "Outputfile: $ofi"
echo "Bestaetigen Sie mit der Enter-Taste. Zum Abbruch Ctrl + Alt + C druecken"
read bestaetigung
dd if=$ifi of=$ofi bs=1M status=progress
