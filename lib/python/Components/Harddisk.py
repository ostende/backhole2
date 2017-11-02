from os import system, listdir, statvfs, popen, makedirs, stat, major, minor, path, access

from Tools.Directories import SCOPE_HDD, resolveFilename, fileExists

from Tools.CList import CList
from SystemInfo import SystemInfo
import time
from Components.Console import Console

def MajorMinor(path):
	rdev = stat(path).st_rdev
	return (major(rdev),minor(rdev))

def readFile(filename):
	file = open(filename)
	data = file.read().strip()
	file.close()
	return data

def getProcMounts():
	try:
		mounts = open("/proc/mounts", 'r')
	except IOError, ex:
		print "[Harddisk] Failed to open /proc/mounts", ex
		return []
	result = [line.strip().split(' ') for line in mounts]
	for item in result:
		# Spaces are encoded as \040 in mounts
		item[1] = item[1].replace('\\040', ' ')
	return result

DEVTYPE_UDEV = 0
DEVTYPE_DEVFS = 1

class Harddisk:
	def __init__(self, device):
		self.device = device

		if access("/dev/.udev", 0):
			self.type = DEVTYPE_UDEV
		elif access("/dev/.devfsd", 0):
			self.type = DEVTYPE_DEVFS
		else:
			print "Unable to determine structure of /dev"

		self.max_idle_time = 0
		self.idle_running = False
		self.timer = None

		self.dev_path = ''
		self.disk_path = ''
		self.mount_path = None
		self.mount_device = None
		self.phys_path = path.realpath(self.sysfsPath('device'))
		self.mount_path = None
		self.mount_device = None

		if self.type == DEVTYPE_UDEV:
			self.dev_path = '/dev/' + self.device
			self.disk_path = self.dev_path

		elif self.type == DEVTYPE_DEVFS:
			tmp = readFile(self.sysfsPath('dev')).split(':')
			s_major = int(tmp[0])
			s_minor = int(tmp[1])
			for disc in listdir("/dev/discs"):
				dev_path = path.realpath('/dev/discs/' + disc)
				disk_path = dev_path + '/disc'
				try:
					rdev = stat(disk_path).st_rdev
				except OSError:
					continue
				if s_major == major(rdev) and s_minor == minor(rdev):
					self.dev_path = dev_path
					self.disk_path = disk_path
					break

		print "new Harddisk", self.device, '->', self.dev_path, '->', self.disk_path
		self.startIdle()

	def __lt__(self, ob):
		return self.device < ob.device

	def partitionPath(self, n):
		if self.type == DEVTYPE_UDEV:
			return self.dev_path + n
		elif self.type == DEVTYPE_DEVFS:
			return self.dev_path + '/part' + n

	def sysfsPath(self, filename):
		return path.realpath('/sys/block/' + self.device + '/' + filename)

	def stop(self):
		if self.timer:
			self.timer.stop()
			self.timer.callback.remove(self.runIdle)

	def bus(self):
		# CF (7025 specific)
		if self.type == DEVTYPE_UDEV:
			ide_cf = False	# FIXME
		elif self.type == DEVTYPE_DEVFS:
			ide_cf = self.device[:2] == "hd" and "host0" not in self.dev_path

		internal = "pci" in self.phys_path

		if ide_cf:
			ret = "External (CF)"
		elif internal:
			ret = "Internal"
		else:
			ret = "External"
		return ret

	def diskSize(self):
		try:
			line = readFile(self.sysfsPath('size'))
		except:
			harddiskmanager.removeHotplugPartition(self.device)
			print "error remove",self.device
			return -1
		try:
			cap = int(line)
		except:
			return 0;
		return cap / 1000 * 512 / 1000

	def capacity(self):
		cap = self.diskSize()
		if cap == 0:
			return ""
		return "%d.%03d GB" % (cap/1000, cap%1000)

	def model(self):
		try:
			if self.device[:2] == "hd":
				return readFile('/proc/ide/' + self.device + '/model')
			elif self.device[:2] == "sd":
				vendor = readFile(self.sysfsPath('device/vendor'))
				model = readFile(self.sysfsPath('device/model'))
				return vendor + '(' + model + ')'
			else:
				assert False, "no hdX or sdX"
		except:
			harddiskmanager.removeHotplugPartition(self.device)
			print "error remove",self.device
			return -1

	def free(self):
		try:
			mounts = open("/proc/mounts")
		except IOError:
			return -1

		lines = mounts.readlines()
		mounts.close()

		for line in lines:
			parts = line.strip().split(" ")
			real_path = path.realpath(parts[0])
			if not real_path[-1].isdigit():
				continue
			try:
				if MajorMinor(real_path) == MajorMinor(self.partitionPath(real_path[-1])):
					stat = statvfs(parts[1])
					return stat.f_bfree/1000 * stat.f_bsize/1000
			except OSError:
				pass
		return -1

	def numPartitions(self):
		numPart = -1
		if self.type == DEVTYPE_UDEV:
			try:
				devdir = listdir('/dev')
			except OSError:
				return -1
			for filename in devdir:
				if filename.startswith(self.device):
					numPart += 1

		elif self.type == DEVTYPE_DEVFS:
			try:
				idedir = listdir(self.dev_path)
			except OSError:
				return -1
			for filename in idedir:
				if filename.startswith("disc"):
					numPart += 1
				if filename.startswith("part"):
					numPart += 1
		return numPart

	def mountDevice(self):
		for parts in getProcMounts():
			if path.realpath(parts[0]).startswith(self.dev_path):
				self.mount_device = parts[0]
				self.mount_path = parts[1]
				return parts[1]

	def findMount(self):
		if self.mount_path is None:
			return self.mountDevice()
		return self.mount_path

	def unmount(self):
		
		try:
			mounts = open("/proc/mounts")
		except IOError:
			return -1

		lines = mounts.readlines()
		mounts.close()

		cmd = "umount"

                for line in lines:                                                                          
                        parts = line.strip().split(" ")                                                     
                        real_path = path.realpath(parts[0])                                                 
                        if not real_path[-1].isdigit():                                                     
                                continue                                                                    
                        try:                                                                                
                                if MajorMinor(real_path) == MajorMinor(self.partitionPath(real_path[-1])):
					cmd = ' ' . join([cmd, parts[1]])
					break
			except OSError:
				pass

#Bh
		cmd = "umount /media/hdd"

		res = system(cmd)
		return (res >> 8)

        def checkPartionPath(self, mypath):
                import time, os
                for i in range(1,10):
                        if path.exists(mypath):
                                return True
                        time.sleep(1)
                return False

	def createPartition(self):
				
		if self.diskSize() < 300000:
			cmd = 'printf "8,\nwrite\n" | sfdisk -f -uS ' + self.disk_path
			res = system(cmd)
		else:
			cmd = 'parted ' + self.disk_path + ' --script -- mklabel gpt'
			res = system(cmd)
			cmd = 'parted ' + self.disk_path + ' --align optimal --script -- mkpart primary 1 100%'
			res = system(cmd)

		if not self.checkPartionPath(self.partitionPath("1")):
			print "no exist : ", self.partitionPath("1")
			return 1
		return (res >> 8)

	def mkfs(self):
		cmd = "mkfs.ext4 "
		if self.diskSize() > 4 * 1024:
			cmd += "-T largefile "
		cmd += "-m0 -O dir_index " + self.partitionPath("1")
		res = system(cmd)
		return (res >> 8)

	def mount(self):

# Bh
#		try:
#			fstab = open("/etc/fstab")
#		except IOError:
#			return -1

#		lines = fstab.readlines()
#		fstab.close()

#		res = -1
#		for line in lines:
#			parts = line.strip().split(" ")
#			real_path = path.realpath(parts[0])                                                 
#                       if not real_path[-1].isdigit():                                                     
#							continue                                                                    
#                       try:                                                                                
#							if MajorMinor(real_path) == MajorMinor(self.partitionPath(real_path[-1])):
#					cmd = "mount -t ext3 " + parts[0]
#					
#					res = system(cmd)
#					break
#			except OSError:
#				pass
		cmd = "mount " + self.disk_path + "1 /media/hdd" 
		res = system(cmd)
#end

		return (res >> 8)

	def createMovieFolder(self):
		try:
			if not fileExists("/hdd", 0):
				print "not found /hdd"
				system("ln -s /media/hdd /hdd")
	
			makedirs(resolveFilename(SCOPE_HDD))
		except OSError:
			return -1
		return 0

	def fsck(self):
		# We autocorrect any failures
		
		cmd = 'parted ' + self.disk_path + ' --script print > /tmp/ninfo2'
		res = system(cmd)
		cmd = "fsck.ext4 -f -p " + self.partitionPath("1")
		if fileExists("/tmp/ninfo2"):
			f = open("/tmp/ninfo2",'r')
			for line in f.readlines():
				if line.find('ext3') != -1:
					cmd = "fsck.ext3 -f -p " + self.partitionPath("1")
			f.close()
		
		res = system(cmd)
		return (res >> 8)

	def killPartition(self, n):
		part = self.partitionPath(n)

		if access(part, 0):
			cmd = 'dd bs=512 count=3 if=/dev/zero of=' + part
			res = system(cmd)
		else:
			res = 0

		return (res >> 8)

	errorList = [ _("Everything is fine"), _("Creating partition failed"), _("Mkfs failed"), _("Mount failed"), _("Create movie folder failed"), _("Fsck failed"), _("Please Reboot"), _("Filesystem contains uncorrectable errors"), _("Unmount failed")]

	def initialize(self):
		self.unmount()

		# Udev tries to mount the partition immediately if there is an
		# old filesystem on it when fdisk reloads the partition table.
		# To prevent that, we overwrite the first 3 sectors of the
		# partition, if the partition existed before. That's enough for
		# ext3 at least.
		self.killPartition("1")

		if self.createPartition() != 0:
			return -1

		if self.mkfs() != 0:
			return -2

		if self.mount() != 0:
			return -3

		if self.createMovieFolder() != 0:
			return -4

		return 0

	def check(self):
		self.unmount()

		res = self.fsck()
		if res & 2 == 2:
			return -6

		if res & 4 == 4:
			return -7

		if res != 0 and res != 1:
			# A sum containing 1 will also include a failure
			return -5

		if self.mount() != 0:
			return -3

		return 0

	def getDeviceDir(self):
		return self.dev_path

	def getDeviceName(self):
		return self.disk_path

	# the HDD idle poll daemon.
	# as some harddrives have a buggy standby timer, we are doing this by hand here.
	# first, we disable the hardware timer. then, we check every now and then if
	# any access has been made to the disc. If there has been no access over a specifed time,
	# we set the hdd into standby.
	def readStats(self):
		try:
			l = open("/sys/block/%s/stat" % self.device).read()
		except IOError:
			return -1,-1
		(nr_read, _, _, _, nr_write) = l.split()[:5]
		return int(nr_read), int(nr_write)

	def startIdle(self):
		self.last_access = time.time()
		self.last_stat = 0
		self.is_sleeping = False
		from enigma import eTimer

		# disable HDD standby timer
		Console().ePopen(("hdparm", "hdparm", "-S0", self.disk_path))
		self.timer = eTimer()
		self.timer.callback.append(self.runIdle)
		self.idle_running = True
		self.setIdleTime(self.max_idle_time) # kick the idle polling loop

	def runIdle(self):
		if not self.max_idle_time:
			return
		t = time.time()

		idle_time = t - self.last_access

		stats = self.readStats()

		if stats == -1:
			self.setIdleTime(0)
			return
		print "nr_read", stats[0], "nr_write", stats[1]
		l = sum(stats)
		print "sum", l, "prev_sum", self.last_stat

		if l != self.last_stat and l >= 0: # access
			print "hdd was accessed since previous check!"
			self.last_stat = l
			self.last_access = t
			idle_time = 0
			self.is_sleeping = False
		else:
			print "hdd IDLE!"

		print "[IDLE]", idle_time, self.max_idle_time, self.is_sleeping
		if idle_time >= self.max_idle_time and not self.is_sleeping:
			self.setSleep()
			self.is_sleeping = True

	def setSleep(self):
		Console().ePopen(("hdparm", "hdparm", "-y", self.disk_path))

	def setIdleTime(self, idle):
		self.max_idle_time = idle
		if self.idle_running:
			if not idle:
				self.timer.stop()
			else:
				self.timer.start(idle * 100, False)  # poll 10 times per period.

	def isSleeping(self):
		return self.is_sleeping

class Partition:
	def __init__(self, mountpoint, device = None, description = "", force_mounted = False):
		self.mountpoint = mountpoint
		self.description = description
		self.force_mounted = force_mounted
		self.is_hotplug = force_mounted # so far; this might change.
		self.device = device

	def stat(self):
		return statvfs(self.mountpoint)

	def free(self):
		try:
			s = self.stat()
			return s.f_bavail * s.f_bsize
		except OSError:
			return None

	def total(self):
		try:
			s = self.stat()
			return s.f_blocks * s.f_bsize
		except OSError:
			return None

	def mounted(self):
		# THANK YOU PYTHON FOR STRIPPING AWAY f_fsid.
		# TODO: can os.path.ismount be used?
		if self.force_mounted:
			return True

		try:
			mounts = open("/proc/mounts")
		except IOError:
			return False

		lines = mounts.readlines()
		mounts.close()

		for line in lines:
			if line.split(' ')[1] == self.mountpoint:
				return True
		return False

DEVICEDB_SR = \
	{"dm8000":
		{
			"/devices/pci0000:01/0000:01:00.0/host0/target0:0:0/0:0:0:0": _("DVD Drive"),
			"/devices/pci0000:01/0000:01:00.0/host1/target1:0:0/1:0:0:0": _("DVD Drive"),
			"/devices/platform/brcm-ehci-1.1/usb2/2-1/2-1:1.0/host3/target3:0:0/3:0:0:0": _("DVD Drive"),
		},
	"dm800":
	{
	},
	"dm7025":
	{
	}
	}

DEVICEDB = \
	{"dm8000":
		{
			"/devices/platform/brcm-ehci.0/usb1/1-1/1-1.1/1-1.1:1.0": _("Front USB Slot"),
			"/devices/platform/brcm-ehci.0/usb1/1-1/1-1.2/1-1.2:1.0": _("Back, upper USB Slot"),
			"/devices/platform/brcm-ehci.0/usb1/1-1/1-1.3/1-1.3:1.0": _("Back, lower USB Slot"),
			"/devices/platform/brcm-ehci.0/usb1/1-1/1-1.1/1-1.1:1.0": _("Front USB Slot"),
			"/devices/platform/brcm-ehci-1.1/usb2/2-1/2-1:1.0/": _("Internal USB Slot"),
			"/devices/platform/brcm-ohci-1.1/usb4/4-1/4-1:1.0/": _("Internal USB Slot"),
		},
	"dm800":
	{
		"/devices/platform/brcm-ehci.0/usb1/1-2/1-2:1.0": "Upper USB Slot",
		"/devices/platform/brcm-ehci.0/usb1/1-1/1-1:1.0": "Lower USB Slot",
	},
	"dm7025":
	{
		"/devices/pci0000:00/0000:00:14.1/ide1/1.0": "CF Card Slot", #hdc
		"/devices/pci0000:00/0000:00:14.1/ide0/0.0": "Internal Harddisk"
	}
	}

class HarddiskManager:
	def __init__(self):
		self.hdd = [ ]
		self.cd = ""
		self.partitions = [ ]
		self.devices_scanned_on_init = [ ]

		self.on_partition_list_change = CList()

		self.enumerateBlockDevices()

		# currently, this is just an enumeration of what's possible,
		# this probably has to be changed to support automount stuff.
		# still, if stuff is mounted into the correct mountpoints by
		# external tools, everything is fine (until somebody inserts
		# a second usb stick.)
		p = [
					("/media/hdd", _("Harddisk")),
					("/media/card", _("Card")),
					("/media/cf", _("Compact Flash")),
					("/media/mmc1", _("MMC Card")),
					("/media/net", _("Network Mount")),
					("/media/upnp", _("DLNA")),
					("/media/ram", _("Ram Disk")),
					("/media/usb", _("USB Stick")),
					("/", _("Internal Flash"))
				]

		self.partitions.extend([ Partition(mountpoint = x[0], description = x[1]) for x in p ])

	def getBlockDevInfo(self, blockdev):
		devpath = "/sys/block/" + blockdev
		error = False
		removable = False
		blacklisted = False
		is_cdrom = False
		partitions = []
		try:
			removable = bool(int(readFile(devpath + "/removable")))
			dev = int(readFile(devpath + "/dev").split(':')[0])
			if dev in (7, 31, 179): # loop, mtdblock, mmcblock
				blacklisted = True
			if blockdev[0:2] == 'sr':
				is_cdrom = True
			if blockdev[0:2] == 'hd':
				try:
					media = readFile("/proc/ide/%s/media" % blockdev)
					if "cdrom" in media:
						is_cdrom = True
				except IOError:
					error = True
			# check for partitions
			if not is_cdrom:
				for partition in listdir(devpath):
					if partition[0:len(blockdev)] != blockdev:
						continue
					partitions.append(partition)
			else:
				self.cd = blockdev
		except IOError:
			error = True
		# check for medium
		medium_found = True
		try:
			open("/dev/" + blockdev).close()
		except IOError, err:
			if err.errno == 159: # no medium present
				medium_found = False

		return error, blacklisted, removable, is_cdrom, partitions, medium_found

	def enumerateBlockDevices(self):
		print "enumerating block devices..."
		for blockdev in listdir("/sys/block"):
			error, blacklisted, removable, is_cdrom, partitions, medium_found = self.addHotplugPartition(blockdev)
			if not error and not blacklisted:
				if medium_found:
					for part in partitions:
						self.addHotplugPartition(part)
				self.devices_scanned_on_init.append((blockdev, removable, is_cdrom, medium_found))

	def getAutofsMountpoint(self, device):
		return "/autofs/%s/" % (device)


	def is_hard_mounted(self, device):
		mounts = file('/proc/mounts').read().split('\n')
		for x in mounts:
			if x.find('/autofs') == -1 and x.find(device) != -1:
				return True
		return False

	def addHotplugPartition(self, device, physdev = None):
		if not physdev:
			dev, part = self.splitDeviceName(device)
			try:
				physdev = path.realpath('/sys/block/' + dev + '/device')[4:]
			except OSError:
				physdev = dev
				print "couldn't determine blockdev physdev for device", device

		error, blacklisted, removable, is_cdrom, partitions, medium_found = self.getBlockDevInfo(device)
		print "found block device '%s':" % device,

		if blacklisted:
			print "blacklisted"
		else:
			if error:
				print "error querying properties"
			elif not medium_found:
				print "no medium"
			else:
				print "ok, removable=%s, cdrom=%s, partitions=%s" % (removable, is_cdrom, partitions)

			l = len(device)
			if l:
				# see if this is a harddrive
				if not device[l-1].isdigit() and not removable and not is_cdrom:
					self.hdd.append(Harddisk(device))
					self.hdd.sort()
					SystemInfo["Harddisk"] = len(self.hdd) > 0

				if (not removable or medium_found) and not self.is_hard_mounted(device):
					# device is the device name, without /dev
					# physdev is the physical device path, which we (might) use to determine the userfriendly name
					description = self.getUserfriendlyDeviceName(device, physdev)
					p = Partition(mountpoint = self.getAutofsMountpoint(device), description = description, force_mounted = True, device = device)
					self.partitions.append(p)
					self.on_partition_list_change("add", p)

		return error, blacklisted, removable, is_cdrom, partitions, medium_found

	def removeHotplugPartition(self, device):
		mountpoint = self.getAutofsMountpoint(device)
		for x in self.partitions[:]:
			if x.mountpoint == mountpoint:
				self.partitions.remove(x)
				self.on_partition_list_change("remove", x)
		l = len(device)
		if l and not device[l-1].isdigit():
			for hdd in self.hdd:
				if hdd.device == device:
					hdd.stop()
					self.hdd.remove(hdd)
					break
			SystemInfo["Harddisk"] = len(self.hdd) > 0

	def HDDCount(self):
		return len(self.hdd)

	def HDDList(self):
		list = [ ]
		for hd in self.hdd:
			if hd.model() == -1:
				continue
			hdd = hd.model() + " - " + hd.bus()
			cap = hd.capacity()
			if cap != "":
				hdd += " (" + cap + ")"
			list.append((hdd, hd))
		return list

	def getCD(self):
		return self.cd

	def getMountedPartitions(self, onlyhotplug = False):
		parts = [x for x in self.partitions if (x.is_hotplug or not onlyhotplug) and x.mounted()]
		devs = set([x.device for x in parts])
		for devname in devs.copy():
			if not devname:
				continue
			dev, part = self.splitDeviceName(devname)
			if part and dev in devs: # if this is a partition and we still have the wholedisk, remove wholedisk
				devs.remove(dev)

		# return all devices which are not removed due to being a wholedisk when a partition exists
		return [x for x in parts if not x.device or x.device in devs]

	def splitDeviceName(self, devname):
		# this works for: sdaX, hdaX, sr0 (which is in fact dev="sr0", part=""). It doesn't work for other names like mtdblock3, but they are blacklisted anyway.
		dev = devname[:3]
		part = devname[3:]
		for p in part:
			if not p.isdigit():
				return devname, 0
		return dev, part and int(part) or 0

	def getUserfriendlyDeviceName(self, dev, phys):
		dev, part = self.splitDeviceName(dev)
		description = "External Storage %s" % dev
		have_model_descr = False
		try:
			description = readFile("/sys" + phys + "/model")
			have_model_descr = True
		except IOError, s:
			print "couldn't read model: ", s
		from Tools.HardwareInfo import HardwareInfo
		if dev.find('sr') == 0 and dev[2].isdigit():
			devicedb = DEVICEDB_SR
		else:
			devicedb = DEVICEDB
		for physdevprefix, pdescription in devicedb.get(HardwareInfo().device_name,{}).items():
			if phys.startswith(physdevprefix):
				if have_model_descr:
					description = pdescription + ' - ' + description
				else:
					description = pdescription
		# not wholedisk and not partition 1
		if part and part != 1:
			description += " (Partition %d)" % part
		return description

	def addMountedPartition(self, device, desc):
		already_mounted = False
		for x in self.partitions[:]:
			if x.mountpoint == device:
				already_mounted = True
		if not already_mounted:
			self.partitions.append(Partition(mountpoint = device, description = desc))

	def removeMountedPartition(self, mountpoint):
		for x in self.partitions[:]:
			if x.mountpoint == mountpoint:
				self.partitions.remove(x)
				self.on_partition_list_change("remove", x)

harddiskmanager = HarddiskManager()
