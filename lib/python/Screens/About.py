from Screen import Screen
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.Harddisk import harddiskmanager
from Components.NimManager import nimmanager
from Components.About import about
import os

from Tools.DreamboxHardware import getFPVersion

class About(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		bhVer = "Black Hole"
		f = open("/etc/bhversion",'r')
		bhVer = f.readline().strip()
		f.close()
		
		bhRev = ""
		f = open("/etc/bhrev",'r')
		bhRev = f.readline().strip()
		f.close()
		

		self["EnigmaVersion"] = StaticText("Firmware: " + bhVer + " " + bhRev)
#		self["ImageVersion"] = StaticText("Image: " + about.getImageVersionString())
		
		self["ImageVersion"] = StaticText("Build: " + about.getEnigmaVersionString())
		driverdate = self.getDriverInstalledDate()
		if driverdate == "unknown":
			driverdate = self.getDriverInstalledDate_proxy()
		self["DriverVersion"] =  StaticText(_("DVB drivers: ") + driverdate)
		self["KernelVersion"] =  StaticText(_("Kernel version: ") + self.getKernelVersionString())
		
		self["FPVersion"] = StaticText("Team Homesite: vuplus-community.net")
		
		self["CpuInfo"] =  StaticText(_("CPU: ") + self.getCPUInfoString())
		self["TunerHeader"] = StaticText(_("Detected NIMs:"))
		
		


		nims = nimmanager.nimList()
		if len(nims) <= 4 :
			for count in (0, 1, 2, 3):
				if count < len(nims):
					self["Tuner" + str(count)] = StaticText(nims[count])
				else:
					self["Tuner" + str(count)] = StaticText("")
		else:
			desc_list = []
			count = 0
			cur_idx = -1
			while count < len(nims):
				data = nims[count].split(":")
				idx = data[0].strip('Tuner').strip()
				desc = data[1].strip()
				if desc_list and desc_list[cur_idx]['desc'] == desc:
					desc_list[cur_idx]['end'] = idx
				else:
					desc_list.append({'desc' : desc, 'start' : idx, 'end' : idx})
					cur_idx += 1
				count += 1

			for count in (0, 1, 2, 3):
				if count < len(desc_list):
					if desc_list[count]['start'] == desc_list[count]['end']:
						text = "Tuner %s: %s" % (desc_list[count]['start'], desc_list[count]['desc'])
					else:
						text = "Tuner %s-%s: %s" % (desc_list[count]['start'], desc_list[count]['end'], desc_list[count]['desc'])
				else:
					text = ""

				self["Tuner" + str(count)] = StaticText(text)

		self["HDDHeader"] = StaticText(_("Detected HDD:"))
		hddlist = harddiskmanager.HDDList()
		hdd = hddlist and hddlist[0][1] or None
		if hdd is not None and hdd.model() != "":
			self["hddA"] = StaticText(_("%s\n(%s, %d MB free)") % (hdd.model(), hdd.capacity(),hdd.free()))
		else:
			self["hddA"] = StaticText(_("none"))

		self["actions"] = ActionMap(["SetupActions", "ColorActions"], 
			{
				"cancel": self.close,
				"ok": self.close,
			})


	def getCPUInfoString(self):
		try:
			cpu_count = 0
			cpu_speed = "n/a"
			for line in open("/proc/cpuinfo").readlines():
				line = [x.strip() for x in line.strip().split(":")]
				if line[0] == "model name":
					processor = line[1].split()[0]
				if line[0] == "system type":
					processor = line[1].split()[0]
				if line[0] == "cpu MHz":
					cpu_speed = "%1.0f" % float(line[1])
				if line[0] == "processor":
					cpu_count += 1
			return "%s %s MHz %d cores" % (processor, cpu_speed, cpu_count)
		except:
			return _("undefined")

	def getDriverInstalledDate(self):
		try:
			driver = os.popen("opkg list-installed | grep vuplus-dvb").read().strip()
			driver = driver.split("-")
			#return driver[:4] + "-" + driver[4:6] + "-" + driver[6:]
			return driver[5]
		except:
			return "unknown"
			
	def getDriverInstalledDate_proxy(self):
		try:
			driver = os.popen("opkg list-installed | grep vuplus-dvb-proxy").read().strip()
			driver = driver.split("-")
			driver = driver[4].split(".")
			#return driver[:4] + "-" + driver[4:6] + "-" + driver[6:]
			return driver[0]
		except:
			return _("unknown")
	
		
			
	def getKernelVersionString(self):
		try:
			return open("/proc/version","r").read().split(' ', 4)[2].split('-',2)[0]
		except:
			return _("unknown")


