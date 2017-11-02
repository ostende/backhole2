###############################################################################
#         FULL BACKUP UYILITY FOR ORIGINAL IMAGE FOR ALL VU+ MODELS           #
#        VU+ UNO, VU+ SOLO, VU+ SOLO2, VU+ DUO, VU+ ULTIMO, VU+ DUO2          #
#                   MAKES A FULLBACK-UP READY FOR FLASHING.                   #
#                                                                             #
#                   Pedro_Newbie (backupsuite@outlook.com)                    #
###############################################################################
#
#!/bin/sh


###################### DEFINE CLEAN-UP ROUTINE ################################
clean_up()
{
umount /tmp/bi/root > /dev/null 2>&1
rmdir /tmp/bi/root > /dev/null 2>&1
rmdir /tmp/bi > /dev/null 2>&1
rm -rf "$WORKDIR" > /dev/null 2>&1
}

###################### BIG OOPS!, HOLY SH... (SHELL SCRIPT :-))################
big_fail()
{
	clean_up
	$SHOW "message15" 		# Image creation FAILED!
	exit 0
}
##### I QUIT #####


########################## DECLARATION OF VARIABLES ###########################
VERSION="Version 12.5 for VU+ Original Image 2.1 - 06-08-2013"
START=$(date +%s)
MEDIA="$1"
DATE=`date +%Y%m%d_%H%M`
IMAGEVERSION=`date +%Y%m%d`
MKFS=/usr/sbin/mkfs.ubifs
NANDDUMP=/usr/sbin/nanddump
UBINIZE=/usr/sbin/ubinize
WORKDIR="$MEDIA/bi"
TARGET="XX"
UBINIZE_ARGS="-m 2048 -p 128KiB"


################### START THE LOGFILE /tmp/BackupSuite.log ####################
echo "Plugin version     = $VERSION" > /tmp/BackupSuite.log
echo "Back-up media      = $MEDIA" >> /tmp/BackupSuite.log
df -h "$MEDIA"  >> /tmp/BackupSuite.log
echo "Back-up date_time  = $DATE" >> /tmp/BackupSuite.log
echo "Working directory  = $WORKDIR" >> /tmp/BackupSuite.log

######################### TESTING FOR UBIFS OR JFFS2 ##########################
if grep rootfs /proc/mounts | grep ubifs > /dev/null; then	
	ROOTFSTYPE=ubifs
else
	$SHOW "message01"			#NO UBIFS, THEN JFFS2 BUT NOT SUPPORTED ANYMORE
	big_fail
fi

####### TESTING IF ALL THE TOOLS FOR THE BUILDING PROCESS ARE PRESENT #########
if [ ! -f $NANDDUMP ] ; then
	echo -n "$NANDDUMP " ; $SHOW "message05"  	# nanddump not found.
	echo "NO NANDDUMP FOUND, ABORTING" >> /tmp/BackupSuite.log
	big_fail
fi
if [ ! -f $MKFS ] ; then
	echo -n "$MKFS " ; $SHOW "message05"  		# mkfs.ubifs not found.
	echo "NO MKFS.UBIFS FOUND, ABORTING" >> /tmp/BackupSuite.log
	big_fail
fi
if [ ! -f $UBINIZE ] ; then
	echo -n "$UBINIZE " ; $SHOW "message05"  	# ubinize not found.
	echo "NO UBINIZE FOUND, ABORTING" >> /tmp/BackupSuite.log
	big_fail
fi

########## TESTING WHICH BRAND AND MODEL SATELLITE RECEIVER IS USED ###########
if [ -f /proc/stb/info/vumodel ] ; then
	MODEL=$( cat /proc/stb/info/vumodel )
	MKUBIFS_ARGS="-m 2048 -e 126976 -c 4096 -F"
	SHOWNAME="Vu+ $MODEL"
	MAINDEST="$MEDIA/fullbackup_OI_2.1_$MODEL/$DATE/vuplus/$MODEL"
	EXTRA="$MEDIA/vuplus"
	echo "Destination        = $MAINDEST" >> /tmp/BackupSuite.log
######################### NO SUPPORTED RECEIVER FOUND #########################
else
	$SHOW "message01"  		# No supported receiver found!
	big_fail
fi

############# START TO SHOW SOME INFORMATION ABOUT BRAND & MODEL ##############
echo
echo -n "$SHOWNAME " | tr  a-z A-Z	# Shows the receiver brand and model
$SHOW "message02"  					# BACK-UP TOOL FOR MAKING A COMPLETE BACK-UP 
echo
echo "$VERSION"
echo "Pedro_Newbie (e-mail: backupsuite@outlook.com)"
echo
$SHOW "message03" 	# Please be patient, ... will take about 5-7 minutes 
echo " "

#exit 0  #USE FOR DEBUGGING/TESTING


##################### PREPARING THE BUILDING ENVIRONMENT ######################
rm -rf "$WORKDIR"		# GETTING RID OF THE OLD REMAINS IF ANY
echo "Remove directory   = $WORKDIR" >> /tmp/BackupSuite.log
mkdir -p "$WORKDIR"		# MAKING THE WORKING FOLDER WHERE EVERYTHING HAPPENS
echo "Recreate directory = $WORKDIR" >> /tmp/BackupSuite.log
mkdir -p /tmp/bi/root
echo "Create directory   = /tmp/bi/root" >> /tmp/BackupSuite.log
sync
mount --bind / /tmp/bi/root


####################### START THE REAL BACK-UP PROCESS ########################
#------------------------------------------------------------------------------
############################# MAKING UBINIZE.CFG ##############################
echo \[ubifs\] > "$WORKDIR/ubinize.cfg"
echo mode=ubi >> "$WORKDIR/ubinize.cfg"
echo image="$WORKDIR/root.ubi" >> "$WORKDIR/ubinize.cfg"
echo vol_id=0 >> "$WORKDIR/ubinize.cfg"
echo vol_type=dynamic >> "$WORKDIR/ubinize.cfg"
echo vol_name=rootfs >> "$WORKDIR/ubinize.cfg"
echo vol_flags=autoresize >> "$WORKDIR/ubinize.cfg"
echo " " >> /tmp/BackupSuite.log
echo "UBINIZE.CFG CREATED WITH THE CONTENT:"  >> /tmp/BackupSuite.log
cat "$WORKDIR/ubinize.cfg"  >> /tmp/BackupSuite.log
touch "$WORKDIR/root.ubi"
chmod 644 "$WORKDIR/root.ubi"
echo "--------------------------" >> /tmp/BackupSuite.log

#############################  MAKING ROOT.UBI(FS) ############################
$SHOW "message06a"  						#Create: root.ubifs
echo "Start creating root.ubi"  >> /tmp/BackupSuite.log
$MKFS -r /tmp/bi/root -o "$WORKDIR/root.ubi" $MKUBIFS_ARGS
if [ -f "$WORKDIR/root.ubi" ] ; then
	echo "ROOT.UBI MADE:" >> /tmp/BackupSuite.log
	ls -e1 "$WORKDIR/root.ubi" >> /tmp/BackupSuite.log
else 
	echo "$WORKDIR/root.ubi NOT FOUND"  >> /tmp/BackupSuite.log
	big_fail
fi

echo "Start UBINIZING" >> /tmp/BackupSuite.log
$UBINIZE -o "$WORKDIR/root.ubifs" $UBINIZE_ARGS "$WORKDIR/ubinize.cfg" >/dev/null
chmod 644 "$WORKDIR/root.ubifs"
if [ -f "$WORKDIR/root.ubifs" ] ; then
	echo "ROOT.UBIFS MADE:" >> /tmp/BackupSuite.log
	ls -e1 "$WORKDIR/root.ubifs" >> /tmp/BackupSuite.log
else 
	echo "$WORKDIR/root.ubifs NOT FOUND"  >> /tmp/BackupSuite.log
	big_fail
fi

############################## MAKING KERNELDUMP ##############################
echo "Start creating kerneldump" >> /tmp/BackupSuite.log
$SHOW "message07"  							# Create: kerneldump
if [ $MODEL = "solo2" ] || [ $MODEL = "duo2" ]; then
	$NANDDUMP /dev/mtd2 -q > "$WORKDIR/vmlinux.gz"
else 
	$NANDDUMP /dev/mtd1 -q > "$WORKDIR/vmlinux.gz"
fi
if [ -f "$WORKDIR/vmlinux.gz" ] ; then
	echo "VMLINUX.GZ MADE:" >> /tmp/BackupSuite.log
	ls -e1 "$WORKDIR/vmlinux.gz" >> /tmp/BackupSuite.log
else 
	echo "$WORKDIR/vmlinux.gz NOT FOUND"  >> /tmp/BackupSuite.log
	big_fail
fi
echo "--------------------------" >> /tmp/BackupSuite.log

############ MOVING THE BACKUP TO THE RIGHT PLACE(S) ##########################
mkdir -p "$MAINDEST"
echo "Created directory  = $MAINDEST"  >> /tmp/BackupSuite.log
if [ $MODEL = "solo2" ] || [ $MODEL = "duo2" ]; then
	mv "$WORKDIR/root.ubifs" "$MAINDEST/root_cfe_auto.bin"
else
	mv "$WORKDIR/root.ubifs" "$MAINDEST/root_cfe_auto.jffs2"
fi
mv "$WORKDIR/vmlinux.gz" "$MAINDEST/kernel_cfe_auto.bin"
if [ $MODEL != "solo" -a $MODEL != "duo" ]; then
	touch "$MAINDEST/reboot.update"  
fi
if [ -f "$MAINDEST/root_cfe_auto"* -a -f "$MAINDEST/kernel_cfe_auto.bin" ] ; then
	echo " "  >> /tmp/BackupSuite.log
	echo "BACK-UP MADE SUCCESSFULLY IN: $MAINDEST"  >> /tmp/BackupSuite.log
	echo " "
	$SHOW "message10" ; echo "$MAINDEST" 	# USB Image created in: 
	$SHOW "message23" 		# "The content of the folder is:"
	ls "$MAINDEST" -e1h | awk {'print $3 "\t" $7'}
	ls -e1 "$MAINDEST" >> /tmp/BackupSuite.log
	echo " "
else
	big_fail
fi

#HERE NEW PART ABOUT NO FOLDER VUPLUS/MODEL WHEN MADE ON HARDDISK OR REPLACEMENT
if  [ $HARDDISK != 1 ]; then
	mkdir -p "$EXTRA/$MODEL"
	echo "Created directory  = $EXTRA/$MODEL" >> /tmp/BackupSuite.log
	cp -r "$MAINDEST" "$EXTRA" 						#copy the made back-up to images
	$SHOW "message11" ; echo "$EXTRA/$MODEL"		# and there is made an extra copy in:
fi

echo " "
$SHOW "message12" 		# directions for restoring the image for a vu+

#################### CHECKING FOR AN EXTRA BACKUP STORAGE #####################
if  [ $HARDDISK = 1 ]; then						# looking for a valid usb-stick
	for candidate in /media/sd* /media/mmc* /media/usb* /media/*
	do
		if [ -f "${candidate}/"*[Bb][Aa][Cc][Kk][Uu][Pp][Ss][Tt][Ii][Cc][Kk]* ]
		then
		TARGET="${candidate}"
		fi    
	done
	if [ "$TARGET" != "XX" ] ; then
		echo " "
		$SHOW "message17"  	# Valid USB-flashdrive detected, making an extra copy
		echo " "
		TOTALSIZE="$(df -h "$TARGET" | tail -n 1 | awk {'print $2'})"
		FREESIZE="$(df -h "$TARGET" | tail -n 1 | awk {'print $4'})"
		$SHOW "message09" ; echo -n "$TARGET ($TOTALSIZE, " ; $SHOW "message16" ; echo "$FREESIZE)"
		rm -rf "$TARGET/vuplus/$MODEL"
		mkdir -p "$TARGET/vuplus/$MODEL"
		cp -r "$MAINDEST" "$TARGET/vuplus/"
		echo " " >> /tmp/BackupSuite.log
		echo "MADE AN EXTRA COPY IN: $TARGET" >> /tmp/BackupSuite.log
		df -h "$TARGET"  >> /tmp/BackupSuite.log
		sync
		$SHOW "message19" 	# Backup finished and copied to your USB-flashdrive
	fi
fi
######################### END OF EXTRA BACKUP STORAGE #########################


################## CLEANING UP AND REPORTING SOME STATISTICS ##################
clean_up
END=$(date +%s)
DIFF=$(( $END - $START ))
MINUTES=$(( $DIFF/60 ))
SECONDS=$(( $DIFF-(( 60*$MINUTES ))))
if [ $SECONDS -le  9 ] ; then 
	SECONDS="0$SECONDS"
fi
$SHOW "message24"  ; echo -n "$MINUTES.$SECONDS " ; $SHOW "message25"
echo "BACKUP FINISHED IN $MINUTES.$SECONDS MINUTES" >> /tmp/BackupSuite.log
exit 
#-----------------------------------------------------------------------------