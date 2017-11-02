#!/bin/sh
### Still somewhat experimental but I think it will work! [ Untill proven otherwise :-) ]

export LANG=$1
export SHOW="python /usr/lib/enigma2/python/Plugins/Extensions/BackupSuiteHDD/message.py $LANG"
export HARDDISK=1
$SHOW "message20"   	#echo "Full back-up to the harddisk"
FREESIZE_0=0				
TOTALSIZE_0=0
MEDIA=0
MINIMUN=33				# avoid all sizes below 33GB
UBIFS="$(df -h /hdd | grep ubi0:rootfs | awk {'print $1'})" > /dev/null 2>&1
if [ "$UBIFS" = ubi0:rootfs ] ; then
	HDD_MOUNT="$(ls -l /hdd | grep -o media/hdd)"
		if [ "$?" = "0" ] ; then
			HDD_MOUNT="$(echo "$HDD_MOUNT refers to the flash memory")" > /dev/null 2>&1
		else
			echo ""
		fi
else
	touch /hdd/hdd-check > /dev/null 2>&1
fi
if [ -f /hdd/hdd-check ] ; then  
	CHECKMOUNT1="$(df -h /hdd | tail -n 1 | awk {'print $6'})"
	CHECKMOUNT2="$(df -h /hdd | tail -n 1 | awk {'print $5'})"
	if [ "${CHECKMOUNT1:1:5}" = media ] ; then
		TOTALSIZE="$(df -h /hdd | tail -n 1 | awk {'print $2'})"
		FREESIZE="$(df -h /hdd | tail -n 1 | awk {'print $4'})"	
		MEDIA="$(df -h /hdd | tail -n 1 | awk {'print $6'})"
	elif [ "${CHECKMOUNT2:1:5}" = media ] ; then
		TOTALSIZE="$(df -h /hdd | tail -n 1 | awk {'print $1'})"		
		FREESIZE="$(df -h /hdd | tail -n 1 | awk {'print $3'})"	
		MEDIA="$(df -h /hdd | tail -n 1 | awk {'print $5'})"
	else
		TOTALSIZE="??"
		FREESIZE="??"
		MEDIA="unknown"
	fi
	echo -n " -> /hdd -> $MEDIA ($TOTALSIZE, "; $SHOW "message16" ; echo "$FREESIZE)"
	backupsuite.sh /hdd
	rm -f /hdd/hdd-check
	sync
else
	for candidate in /dev/sda1 /dev/sdb1 /dev/sdc1 /dev/sdd1 /dev/sde1 /dev/sdf1
	do
		if grep ${candidate} /proc/mounts > /dev/null ; then
			DISK="$( grep ${candidate} /proc/mounts | awk {'print $3'})" 
			MEDIA="$( grep -m1 ${candidate} /proc/mounts | awk {'print $2'})" 
			CHECK=${DISK:0:3}
			if [ $CHECK = "ext" ] ; then
				TOTALSIZE="$(df -B 1073741824 ${candidate} | tail -n 1 | awk {'print $2'})" 
				FREESIZE="$(df -B 1073741824 ${candidate} | tail -n 1 | awk {'print $4'})" 
				if [ "$FREESIZE" -gt $FREESIZE_0 -a $TOTALSIZE -gt $MINIMUN ] ; then
					BMEDIA=$MEDIA
					TOTALSIZE_0=$TOTALSIZE
					FREESIZE_0=$FREESIZE
					echo "This is an absolete testfile" > $BMEDIA/HDD-TEST
					if [ -f $BMEDIA/HDD-TEST ] ; then
						rm -f $BMEDIA/HDD-TEST
					else
						#non-writeable disk
						MEDIA=
					fi
				fi
			fi
		fi
	done
	if  [ $MEDIA = "0" ] ; then
		$SHOW "message15"  #echo "No suitable media found"
		exit 0
	else
		TOTALSIZE_0="$(df -h $BMEDIA | tail -n 1 | awk {'print $2'})"		
		FREESIZE_0="$(df -h $BMEDIA | tail -n 1 | awk {'print $4'})"
		echo -n " -> $BMEDIA ($TOTALSIZE_0, "; $SHOW "message16" ; echo -n "$FREESIZE_0)"
		backupsuite.sh $BMEDIA 
		echo "$HDD_MOUNT" > /tmp/BackupSuiteHDD.log
		sync
	fi
fi
