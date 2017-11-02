from Components.config import config, ConfigSubDict, ConfigSelection, ConfigNothing, NoSave
from Tools.CList import CList
from Tools.HardwareInfo import HardwareInfo
import os

# VideoHardware is the interface to /proc/stb/video.
class VideoHardware:
	is_init = True

	modes = { # a list of modes for available port
		"Scart" : ["PAL", "NTSC", "Multi"],
		"YPbPr" : ["720p", "1080i", "576p", "480p", "576i", "480i"],
		"DVI"   : ["720p", "1080i", "576p", "480p", "576i", "480i"],
		"DVI-PC": ["PC"]
	}
	rates = { # list of rates for available mode
		"PAL":   { "50Hz" : {50: "pal"},
				   "60Hz" : {60: "pal60"},
				   "multi": {50: "pal", 60: "pal60"}
		},
		"NTSC":  { "60Hz" : {60: "ntsc"} },
		"Multi": { "multi": {50: "pal", 60: "ntsc"} },
		"480i":  { "60Hz" : {60: "480i"} },
		"576i":  { "50Hz" : {50: "576i"} },
		"480p":  { "60Hz" : {60: "480p"} },
		"576p":  { "50Hz" : {50: "576p"} },
		"720p":  {
			"50Hz" : {50: "720p50"},
			"60Hz" : {60: "720p"},
			"multi": {50: "720p50", 60: "720p"}
		},
		"1080i": {
			"50Hz" : {50: "1080i50"},
			"60Hz" : {60: "1080i"},
			"multi": {50: "1080i50", 60: "1080i"}
		},
		"1080p": {
			"50Hz" : {50: "1080p50"},
			"60Hz" : {60: "1080p"},
			"multi": {50: "1080p50", 60: "1080p"}
		},
		"2160p": {
			"50Hz" : {50: "2160p50"},
			"60Hz" : {60: "2160p"},
			"multi": {50: "2160p50", 60: "2160p"}
		},
		"PC": {
			"1024x768": {60: "1024x768"},
			"800x600" : {60: "800x600"},
			"720x480" : {60: "720x480"},
			"720x576" : {60: "720x576"},
			"1280x720": {60: "1280x720"},
			"1280x720 multi": {50: "1280x720_50", 60: "1280x720"},
			"1920x1080": {60: "1920x1080"},
			"1920x1080 multi": {50: "1920x1080", 60: "1920x1080_50"},
			"1280x1024": {60: "1280x1024"},
			"1366x768": {60: "1366x768"},
			"1366x768 multi": {50: "1366x768", 60: "1366x768_50"},
			"1280x768": {60: "1280x768"},
			"640x480" : {60: "640x480"}
		}
	}

	widescreen_modes = set(["720p", "1080i", "1080p", "2160p"])
	hdmi_hw_types = set(["dm500", "dm800se", "dm7020hd", "bm750", "solo", "uno", "ultimo", "solo2", "duo2", "solose", "zero", "solo4k", "ultimo4k", "uno4k"])
	hdmi_pc_hw_types = set(["dm500", "dm800se", "dm7020hd", "bm750", "solo", "uno", "ultimo", "solo2", "duo2", "solose", "zero", "solo4k", "ultimo4k", "uno4k"])
	noscart_hw_types = set(["zero", "solo4k", "ultimo4k", "uno4k"])
	noypbpr_hw_types = set(["solose", "zero", "solo4k", "ultimo4k", "uno4k"])

	def getDeviceName(self):
		device_name = "unknown"
		try:
			file = open("/proc/stb/info/vumodel", "r")
			device_name = file.readline().strip()
			file.close()
		except IOError:
			from Tools.HardwareInfo import HardwareInfo
			device_name = HardwareInfo.get_device_name()

		return device_name

	def isVumodel(self, hw_type):
		return hw_type in set(["bm750", "solo", "uno", "ultimo", "solo2", "duo2", "solose", "zero", "solo4k", "ultimo4k", "uno4k"])

	def isVumodel4K(self, hw_type):
		return hw_type in set(["solo4k", "ultimo4k", "uno4k"])

	# re-define AVSwitch.getOutputAspect
	def getOutputAspect(self):
		ret = (16,9)
		port = config.av.videoport.value
		if port not in config.av.videomode:
			print "current port is not available. force 16:9"
		else:
			mode = config.av.videomode[port].value
			force_wide = self.isWidescreenMode(mode)
			valstr = config.av.aspect.value

			if force_wide:
				pass
			elif valstr == "16_10":
				ret = (16,10)
			elif valstr == "auto":
				try:
					aspect_str = open("/proc/stb/vmpeg/0/aspect", "r").read()
					if aspect_str == "1": # 4:3
						ret = (4,3)
				except IOError:
					pass
			elif valstr == "4_3":
				ret = (4,3)
		return ret

	def __init__(self):
		self.last_modes_preferred = [ ]
		self.on_hotplug = CList()

		self.readAvailableModes()

		if self.modes.has_key("DVI-PC") and not self.getModeList("DVI-PC"):
			print "remove DVI-PC because it does not exist."
			del self.modes["DVI-PC"]

		if self.isNoScart(self.getDeviceName()):
			if self.modes.has_key("Scart"):
				print "remove Scart because it does not exist."
				del self.modes["Scart"]

		if self.isNoYPbPr(self.getDeviceName()):
			if self.modes.has_key("YPbPr"):
				print "remove YPbPr because it does not exist."
				del self.modes["YPbPr"]

		self.createConfig()

		self.readPreferredModes()

		# re-define AVSwitch components
		from Components.AVSwitch import AVSwitch
		config.av.aspectratio.notifiers = [ ]
		config.av.tvsystem.notifiers = [ ]
		config.av.wss.notifiers = [ ]
		AVSwitch.getOutputAspect = self.getOutputAspect

		config.av.aspect.addNotifier(self.changedAspect)
		config.av.wss.addNotifier(self.changedAspect)
		config.av.policy_169.addNotifier(self.changedAspect)
		config.av.policy_43.addNotifier(self.changedAspect)

		# addNotifiers for port, mode, rate
		config.av.videoport.addNotifier(self.changedVideomode)
		for port in self.getPortList():
			config.av.videomode[port].addNotifier(self.changedVideomode)
			for mode in self.getModeList(port):
				config.av.videorate[mode[0]].addNotifier(self.changedVideomode)

		self.is_init = False

	def readAvailableModes(self):
		try:
			modes = open("/proc/stb/video/videomode_choices").read()[:-1]
			self.modes_available = modes.split(' ')
		except IOError:
			print "failed to read video_choices."
			self.modes_available = [ ]

	def readPreferredModes(self):
		try:
			modes = open("/proc/stb/video/videomode_preferred").read()[:-1]
			self.modes_preferred = modes.split(' ')
		except IOError:
			print "failed to read video_preferred."
			self.modes_preferred = self.modes_available

		if self.modes_preferred != self.last_modes_preferred:
			self.last_modes_preferred = self.modes_preferred
			print "hotplug on DVI"
			self.on_hotplug("DVI") # must be DVI

	# check if HDMI is available
	def isHDMIAvailable(self, hw_type):
		return hw_type in self.hdmi_hw_types

	# check if HDMI-PC is available
	def isHDMI_PCAvailable(self, hw_type):
		return hw_type in self.hdmi_pc_hw_types

	# check if mode is always widescreen
	def isWidescreenMode(self, mode):
		return mode in self.widescreen_modes

	# check if Scart is not available
	def isNoScart(self, hw_type):
		return hw_type in self.noscart_hw_types

	# check if YPbPr is not available
	def isNoYPbPr(self, hw_type):
		return hw_type in self.noypbpr_hw_types

	# check if rate is available for mode
	def isModeAvailable(self, port, mode, rate):
		rate = self.rates[mode][rate]
		for mode in rate.values():
			if mode not in self.modes_available:
				return False

		return True

	# check isModeAvailable in this port
	def isPortAvailable(self, port):
		for mode in self.getModeList(port):
			if len(self.getRateList(port, mode[0])):
				return True

		return False

	# get a list of all available port
	def getPortList(self):
		return [port for port in self.modes if self.isPortAvailable(port)]

	# get a list of all available mode for a given port
	def getModeList(self, port):
		modelist = [ ]
		for mode in self.modes[port]:
			rates = self.getRateList(port, mode)

			if len(rates):
				modelist.append( (mode, rates))

		return modelist

	# get a list of all available rate for a given port, mode
	def getRateList(self, port, mode):
		return [rate for rate in self.rates[mode] if self.isModeAvailable(port, mode, rate)]

	def createConfig(self):
		config.av.videomode = ConfigSubDict()
		config.av.videorate = ConfigSubDict()

		hw_type = self.getDeviceName()
		# vu+ support 1080p
		if self.isVumodel(hw_type):
			self.modes["DVI"].insert(self.modes["DVI"].index("1080i")+1, "1080p")
			# 4K support 2160p
			if self.isVumodel4K(hw_type):
				self.modes["DVI"].insert(self.modes["DVI"].index("1080p")+1, "2160p")

		portlist = [ ]
		port_choices = self.getPortList()

		for port in port_choices:
			desc = port
			if desc == 'DVI' and self.isHDMIAvailable(hw_type):
				desc = 'HDMI'
			if desc == 'DVI-PC' and self.isHDMI_PCAvailable(hw_type):
				desc = 'HDMI-PC'
			portlist.append( (port, desc))

			# create list of available modes
			modelist = [ ]
			mode_choices = self.getModeList(port)

			for mode in mode_choices:
				modelist.append( (mode[0], mode[0]))

				# create list of available rates
				ratelist = [ ]
				rate_choices = self.getRateList(port, mode[0])

				for rate in rate_choices:
					ratelist.append( (rate, rate))

				config.av.videorate[mode[0]] = ConfigSelection(choices = ratelist)
			config.av.videomode[port] = ConfigSelection(choices = modelist)
		config.av.videoport = ConfigSelection(choices = portlist)

		if os.path.exists("/proc/stb/video/hdmi_colorspace"):
			def setHdmiColorspace(config):
				try:
					print "set HDMI Colorspace : ",config.value
					f = open("/proc/stb/video/hdmi_colorspace", "w")
					f.write(config.value)
					f.close()
				except IOError:
					print "set HDMI Colorspace failed!"
			hdmicolorspace_choices = {}
			hdmicolorspace_choices["Edid(Auto)"] = _("Auto")
			hdmicolorspace_choices["Hdmi_Rgb"] = _("RGB")
			hdmicolorspace_choices["444"] = _("YCbCr444")
			hdmicolorspace_choices["422"] = _("YCbCr422")
			hdmicolorspace_choices["420"] = _("YCbCr420")
			config.av.hdmicolorspace = ConfigSelection(choices = hdmicolorspace_choices, default = "Edid(Auto)")
			config.av.hdmicolorspace.addNotifier(setHdmiColorspace)
		else:
			config.av.hdmicolorspace = NoSave(ConfigNothing())

		if os.path.exists("/proc/stb/video/hdmi_colordepth"):
			def setHdmiColordepth(config):
				try:
					print "set HDMI Colordepth : ",config.value
					f = open("/proc/stb/video/hdmi_colordepth", "w")
					f.write(config.value)
					f.close()
				except IOError:
					print "set HDMI Colordepth failed!"
			hdmicolordepth_choices = {}
			hdmicolordepth_choices["auto"] = _("Auto")
			hdmicolordepth_choices["8bit"] = _("8bit")
			hdmicolordepth_choices["10bit"] = _("10bit")
			hdmicolordepth_choices["12bit"] = _("12bit")
			config.av.hdmicolordepth = ConfigSelection(choices = hdmicolordepth_choices, default = "auto")
			config.av.hdmicolordepth.addNotifier(setHdmiColordepth)
		else:
			config.av.hdmicolordepth = NoSave(ConfigNothing())

	def changedVideomode(self, configElement):
		if self.is_init:
			return

		self.setConfiguredMode()

	def setConfiguredMode(self):
		port = config.av.videoport.value
		mode = config.av.videomode[port].value
		rate = config.av.videorate[mode].value

		self.setVideomode(port, mode, rate)

	def setVideomode(self, port, mode, rate):
		if port is None or port not in config.av.videomode:
			print "current port not available. couldn't set videomode"
			return

		if mode not in config.av.videorate:
			print "current mode not available. couldn't set videomode"
			return

		if mode is None:
			modelist = self.getModeList(port)
			mode = modelist[0][0]

			ratelist = self.getRateList(port, mode)
			rate = ratelist[0]

		if rate is None:
			ratelist = self.getRateList(port, mode)
			rate = ratelist[0]

		print "set Videomode", port, mode, rate

		modes = self.rates[mode][rate]
		mode_50 = modes.get(50)
		mode_60 = modes.get(60)
		if mode_50 is None:
			mode_50 = mode_60
		if mode_60 is None:
			mode_60 = mode_50

		if (mode_50 != mode_60):
			try:
				open("/proc/stb/video/videomode_50hz", "w").write(mode_50)
				open("/proc/stb/video/videomode_60hz", "w").write(mode_60)
			except IOError:
				print "cannot open /proc/stb/vide/videomode_50hz or videomode_60hz"

			# Too slow moving to Scart/multi in modeSelectionMoved
			#try:
			#	open("/proc/stb/video/videomode_50hz", "w").write(mode_60)
			#except IOError:
			#	print "cannot open /proc/stb/vide/videomode_60Hz"

		else:
			try:
				open("/proc/stb/video/videomode", "w").write(mode_50)
			except IOError:
				print "cannot open /proc/stb/vide/videomode"

		self.changedAspect(None)

	def changedAspect(self, configElement):
		if self.is_init:
			return
		# config.av.aspect:
		#	4:3			use policy_169
		#	16:9, 16:10	use policy_43
		#	auto		always "bestfit"
		# config.av.policy_169:
		#	letterbox	use letterbox
		#	panscan 	use panscan
		#	scale		use bestfit
		# config.av.policy_43:
		#	pillarbox	use panscan
		#	pansca		use letterbox ("panscan" is just a bad term, it is inverse-panscan)
		#	nonlinear	use nonlinear
		#	scale		use bestfit

		port = config.av.videoport.value
		if port not in config.av.videomode:
			print "current port not available. couldn't set aspect"
			return

		mode = config.av.videomode[port].value
		force_wide = self.isWidescreenMode(mode)
		valstr = config.av.aspect.value

		policy2 = "policy" # use main policy

		if force_wide or valstr == "16_9" or valstr == "16_10":
			if force_wide or valstr == "16_9":
				aspect = "16:9"
			elif valstr == "16_10":
				aspect = "16:10"

			policy = {"pillarbox": "panscan", "panscan": "letterbox", "nonlinear": "nonlinear", "scale": "bestfit"}[config.av.policy_43.value]
			policy2 = {"letterbox": "letterbox", "panscan": "panscan", "scale": "bestfit"}[config.av.policy_169.value]
		elif valstr == "auto":
			aspect = "any"
			policy = "bestfit"
		else:
			aspect = "4:3"
			policy = {"letterbox": "letterbox", "panscan": "panscan", "scale": "bestfit"}[config.av.policy_169.value]

		if not config.av.wss.value:
			wss = "auto(4:3_off)"
		else:
			wss = "auto"

		self.setAspect(aspect, policy, policy2, wss)

	def setAspect(self, aspect, policy, policy2, wss):
		print "set aspect, policy, policy2, wss", aspect, policy, policy2, wss

		open("/proc/stb/video/aspect", "w").write(aspect)
		open("/proc/stb/video/policy", "w").write(policy)
		open("/proc/stb/denc/0/wss", "w").write(wss)
		try:
			open("/proc/stb/video/policy2", "w").write(policy2)
		except IOError:
			pass

	def isPortUsed(self, port):
		if port == "DVI":
			self.readPreferredModes()
			return len(self.modes_preferred) != 0
		else:
			return True

	def saveVideomode(self, port, mode, rate):
		print "save Videomode", port, mode, rate
		config.av.videoport.value = port
		config.av.videoport.save()
		if port in config.av.videomode:
			config.av.videomode[port].value = mode
			config.av.videomode[port].save()
		if mode in config.av.videorate:
			config.av.videorate[mode].value = rate
			config.av.videorate[mode].save()

	# for dependency
	def setMode(self, port, mode, rate):
		self.setVideomode(port, mode, rate)

	def saveMode(self, port, mode, rate):
		self.saveVideomode(port, mode, rate)

	def updateAspect(self, configElement):
		self.changedAspect(configElement)

video_hw = VideoHardware()
video_hw.setConfiguredMode()

