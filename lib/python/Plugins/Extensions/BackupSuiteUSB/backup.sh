#!/bin/sh

export LANG=$1
export HARDDISK=0
export SHOW="python /usr/lib/enigma2/python/Plugins/Extensions/BackupSuiteHDD/message.py $LANG"
TARGET="XX"
for candidate in /media/*
do
	if [ -f "${candidate}/"*[Bb][Aa][Cc][Kk][Uu][Pp][Ss][Tt][Ii][Cc][Kk]* ]
	then
	TARGET="${candidate}"
	fi 
done

if [ "$TARGET" = "XX" ] ; then
	$SHOW "message21" #error about no USB-found
else
	$SHOW "message22" 
	SIZE_1="$(df -h "$TARGET" | tail -n 1 | awk {'print $4'})"
	SIZE_2="$(df -h "$TARGET" | tail -n 1 | awk {'print $2'})"
	echo -n " -> $TARGET ($SIZE_2, " ; $SHOW "message16" ; echo "$SIZE_1)"
	backupsuite.sh "$TARGET" 
	sync
fi
