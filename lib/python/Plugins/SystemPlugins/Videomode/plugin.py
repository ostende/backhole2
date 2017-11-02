from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import NumberActionMap
from Components.config import config, ConfigNothing, ConfigBoolean, getConfigListEntry
from Components.Sources.StaticText import StaticText
from Components.SystemInfo import SystemInfo
from Plugins.Plugin import PluginDescriptor

from VideoHardware import video_hw

config.misc.videowizardenabled = ConfigBoolean(default = True)

class avSetupScreen(ConfigListScreen, Screen):
	avSetupItems = [
		{"idx":1, "level":0, "text":"Video Output", "item":"config.av.videoport"},
		{"idx":2, "level":0, "text":"Mode", "item":"config.av.videomode[config.av.videoport.value]"},
		{"idx":3, "level":0, "text":"Refresh Rate", "item":"config.av.videorate[config.av.videomode[config.av.videoport.value].value]"},
		{"idx":4, "level":0, "text":"Aspect Ratio", "item":"config.av.aspect"},
		{"idx":5, "level":0, "text":"Display 4:3 content as", "item":"config.av.policy_43"},
		{"idx":6, "level":0, "text":"Display > 16:9 content as", "item":"config.av.policy_169"},
		{"idx":7, "level":0, "text":"Color Format", "item":"config.av.colorformat"},
		{"idx":8, "level":1, "text":"WSS on 4:3", "item":"config.av.wss"},
		{"idx":9, "level":1, "text":"Auto scart switching", "requires":"ScartSwitch", "item":"config.av.vcrswitch"},
		{"idx":10, "level":1, "text":"HDMI Colorspace", "item":"config.av.hdmicolorspace"},
		{"idx":11, "level":1, "text":"HDMI Colordepth", "item":"config.av.hdmicolordepth"},
		{"idx":0, "level":1, "text":"Dolby Digital default", "item":"config.av.defaultac3"},
		{"idx":0, "level":1, "text":"Dolby Digital / DTS downmix", "requires":"CanDownmixAC3", "item":"config.av.downmix_ac3"},
		{"idx":0, "level":1, "text":"PCM Multichannel", "requires":"CanPcmMultichannel", "item":"config.av.pcm_multichannel"},
		{"idx":0, "level":1, "text":"AAC downmix", "requires":"CanDownmixAAC", "item":"config.av.downmix_aac"},
		{"idx":0, "level":1, "text":"General Dolby Digital delay(ms)", "item":"config.av.generalAC3delay"},
		{"idx":0, "level":1, "text":"General PCM delay(ms)", "item":"config.av.generalPCMdelay"},
		{"idx":0, "level":0, "text":"OSD visibility", "requires":"CanChangeOsdAlpha", "item":"config.av.osd_alpha"},
		{"idx":0, "level":0, "text":"Scaler sharpness", "item":"config.av.scaler_sharpness"},
	]

	def __init__(self, session):
		Screen.__init__(self, session)
		# for the skin: first try a setup_avsetup, then Setup
		self.skinName = ["setup_avsetup", "Setup"]
		self.setup_title = _("A/V Settings")

		self.video_cfg = video_hw
		self.audio_cfg = [ ]

		self.onChangedEntry = [ ]

		# handle hotplug by re-createing setup
		self.onShow.append(self.startHotplug)
		self.onHide.append(self.stopHotplug)

		self.list = [ ]

		self["key_red"] = StaticText( _("Cancel"))
		self["key_green"] = StaticText( _("OK"))

		self["action"] = NumberActionMap(["SetupActions"],
			{
				"cancel": self.keyCancel,
				"save": self.keySave,
			}, -2)

		ConfigListScreen.__init__(self, self.list, session = session, on_change = self.changedEntry)
		
		self.createScreen()

		self.onLayoutFinish.append(self.layoutFinished)
	
	def layoutFinished(self):
		self.setTitle(self.setup_title)
	
	# for summary:
	def changedEntry(self):
		for x in self.onChangedEntry:
			x()
	
	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())

	def createSummary(self):
		from Screens.Setup import SetupSummary
		return SetupSummary
	
	def createScreen(self):
		self.list = [ ]
		self.audio_cfg = [ ]

		for x in self.avSetupItems:
			item_level = int(x.get("level", 0))
			if item_level > config.usage.setup_level.index:
				continue

			requires = x.get("requires")
			if requires and not SystemInfo.get(requires, False):
				continue

			item_text = _(x.get("text", "??").encode("UTF-8"))

			item_str = x.get("item", None)
			if item_str is None:
				continue
			item = eval(item_str)

			idx = x.get("idx", 0)
			if idx > 0:
				if idx == 1: # Video Output
					current_port = item.value
				elif idx == 2: # Mode
					item = config.av.videomode[current_port]
					current_mode = item.value
					# some modes (720p, 1080i, 1080p) are always widescreen.
					force_wide = self.video_cfg.isWidescreenMode(current_mode)
				elif idx == 3: # Refresh Rate
					item = config.av.videorate[current_mode]
					current_rate = item.value
					if current_mode == "PC":
						item_text = _("Resolution")
				elif idx == 4: # Aspect Ratio
					current_aspect = item.value
					if force_wide:
						continue
				elif idx == 5: # Display 4:3 content as
					if current_aspect == "auto" and not force_wide:
						continue
					elif current_aspect == "4_3":
						continue
				elif idx == 6: # Display 16:9 > content as
					if current_aspect == "auto" and not force_wide:
						continue
				# Color Format, WSS on 4:3, Auto scart switching
				elif (idx == 7 or idx == 8 or idx == 9) and not current_port == "Scart":
					continue
				elif (idx == 10 or idx == 11) and not current_port == "DVI": # HDMI Colorspace/Colordepth
					continue
			if idx == 0 and item_level == 1: # audio
				self.audio_cfg.append(item_text)

			# add to configlist
			if not isinstance(item, ConfigNothing):
				self.list.append(getConfigListEntry(item_text, item))

		self["config"].setList(self.list)
	
	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.createScreen()
		# show current value on VFD
		if self.getCurrentEntry() not in self.audio_cfg:
			self.summaries[0]["SetupTitle"].text = self.getCurrentValue()
	
	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.createScreen()
		# show current value on VFD
		if self.getCurrentEntry() not in self.audio_cfg:
			self.summaries[0]["SetupTitle"].text = self.getCurrentValue()

	def startHotplug(self):
		self.video_cfg.on_hotplug.append(self.createScreen)

	def stopHotplug(self):
		self.video_cfg.on_hotplug.remove(self.createScreen)


def avSetupMain(session, **kwargs):
	session.open(avSetupScreen)

def startAVsetup(menuid):
	if menuid != "system":
		return []

	return [( _("A/V Settings"), avSetupMain, "av_setup", 40)]

def startVideoWizard(*args, **kwargs):
	from VideoWizard import VideoWizard
	return VideoWizard(*args, **kwargs)

def Plugins(**kwargs):
	plugin_list = [ 
		PluginDescriptor(
			name = "Videomode-K",
			description = "Videomode-K based videomode",
			where = PluginDescriptor.WHERE_MENU,
			needsRestart = False,
			fnc = startAVsetup)
	]

	if config.misc.videowizardenabled.value:
		plugin_list.append(
			PluginDescriptor(
				name = "Video Wizard",
				where = PluginDescriptor.WHERE_WIZARD,
				fnc=(0, startVideoWizard)
			)
		)
	
	return plugin_list

