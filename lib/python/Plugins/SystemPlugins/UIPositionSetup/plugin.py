from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen
from Components.config import config, getConfigListEntry, ConfigSubsection, ConfigSelection, ConfigInteger, ConfigSlider
from Components.ActionMap import ActionMap
from Screens.MessageBox import MessageBox
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Tools.Directories import fileExists
from enigma import eTimer
from Plugins.Plugin import PluginDescriptor

config.plugins.UIPositionSetup = ConfigSubsection()
config.plugins.UIPositionSetup.dst_left = ConfigInteger(default = 0)
config.plugins.UIPositionSetup.dst_width = ConfigInteger(default = 720)
config.plugins.UIPositionSetup.dst_top = ConfigInteger(default = 0)
config.plugins.UIPositionSetup.dst_height = ConfigInteger(default = 576)

class UIPositionSetupInit:
	def __init__(self):
		self.setPosition(int(config.plugins.UIPositionSetup.dst_left.value), int(config.plugins.UIPositionSetup.dst_width.value), int(config.plugins.UIPositionSetup.dst_top.value), int(config.plugins.UIPositionSetup.dst_height.value))

	def setPosition(self,dst_left, dst_width, dst_top, dst_height):
		if dst_left + dst_width > 720 or dst_top + dst_height > 576 :
			return
		else:
			print "[UIPositionSetup] write dst_left : ",dst_left
			print "[UIPositionSetup] write dst_width : ",dst_width
			print "[UIPositionSetup] write dst_top : ",dst_top
			print "[UIPositionSetup] write dst_height : ",dst_height
			try:
				file = open("/proc/stb/fb/dst_left", "w")
				file.write('%X' % dst_left)
				file.close()
				file = open("/proc/stb/fb/dst_width", "w")
				file.write('%X' % dst_width)
				file.close()
				file = open("/proc/stb/fb/dst_top", "w")
				file.write('%X' % dst_top)
				file.close()
				file = open("/proc/stb/fb/dst_height", "w")
				file.write('%X' % dst_height)
				file.close()
			except:
				return

uipositionsetupinit = UIPositionSetupInit()

class UIPositionSetup(Screen, ConfigListScreen, UIPositionSetupInit):
	skin = 	"""
		<screen position="0,0" size="%d,%d" title="Screen Position Setup" backgroundColor="#27d8dee2" >
			<ePixmap pixmap="skin_default/buttons/red.png" position="%d,%d" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="%d,%d" size="140,40" alphatest="on" />"

			<widget source="key_red" render="Label" position="%d,%d" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_green" render="Label" position="%d,%d" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="#ffffff" transparent="1" />

			<widget name="config" zPosition="2" position="%d,%d" size="500,200" scrollbarMode="showOnDemand" foregroundColor="#1c1c1c" transparent="1" />
		</screen>
		"""
	def __init__(self,session):
		w,h   = session.desktop.size().width(), session.desktop.size().height()
		cw,ch = w/2, h/2
		#                             btn_red        btn_green     lb_red         lb_green      config
		self.skin = self.skin % (w,h, cw-190,ch-110, cw+50,ch-110, cw-190,ch-110, cw+50,ch-110, cw-250,ch-50)

		Screen.__init__(self,session)
		self.session = session
		self["shortcuts"] = ActionMap(["ShortcutActions", "SetupActions" ],
		{
			"ok": self.keyOk,
			"cancel": self.keyCancel,
			"red": self.keyCancel,
			"green": self.keyOk,
		}, -2)
		self.list = []
		ConfigListScreen.__init__(self, self.list,session = self.session)

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["current"] = StaticText(_(" "))
		self.createSetup()

	def createSetup(self):
		self.list = []

		left   = config.plugins.UIPositionSetup.dst_left.value
		width  = config.plugins.UIPositionSetup.dst_width.value
		top    = config.plugins.UIPositionSetup.dst_top.value
		height = config.plugins.UIPositionSetup.dst_height.value

		self.dst_left   = ConfigSlider(default = left, increment = 5, limits = (0, 720))
		self.dst_width  = ConfigSlider(default = width, increment = 5, limits = (0, 720))
		self.dst_top    = ConfigSlider(default = top, increment = 5, limits = (0, 576))
		self.dst_height = ConfigSlider(default = height, increment = 5, limits = (0, 576))

		self.dst_left_entry   = getConfigListEntry(_("left"), self.dst_left)
		self.dst_width_entry  = getConfigListEntry(_("width"), self.dst_width)
		self.dst_top_entry    = getConfigListEntry(_("top"), self.dst_top)
		self.dst_height_entry = getConfigListEntry(_("height"), self.dst_height)

		self.list.append(self.dst_left_entry)
		self.list.append(self.dst_width_entry)
		self.list.append(self.dst_top_entry)
		self.list.append(self.dst_height_entry)

		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def resetDisplay(self):
		for entry in self["config"].getList():
			self["config"].l.invalidateEntry(self["config"].getList().index(entry))

	def adjustBorder(self):
		if self["config"].getCurrent() == self.dst_left_entry:
			if self.dst_left.value + self.dst_width.value >720:
				self.dst_width.setValue(720-self.dst_left.value)
				self.resetDisplay()
		elif self["config"].getCurrent() == self.dst_width_entry:
			if self.dst_left.value + self.dst_width.value >720:
				self.dst_left.setValue(720-self.dst_width.value)
				self.resetDisplay()
		elif self["config"].getCurrent() == self.dst_top_entry:
			if self.dst_top.value + self.dst_height.value >576:
				self.dst_height.setValue(576-self.dst_top.value)
				self.resetDisplay()
		elif self["config"].getCurrent() == self.dst_height_entry:
			if self.dst_top.value + self.dst_height.value >576:
				self.dst_top.setValue(576-self.dst_height.value)
				self.resetDisplay()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.adjustBorder()
		self.setPosition(int(self.dst_left.value), int(self.dst_width.value), int(self.dst_top.value), int(self.dst_height.value))

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.adjustBorder()
		self.setPosition(int(self.dst_left.value), int(self.dst_width.value), int(self.dst_top.value), int(self.dst_height.value))

	def keyOk(self):
		config.plugins.UIPositionSetup.dst_left.value = self.dst_left.value
		config.plugins.UIPositionSetup.dst_width.value = self.dst_width.value
		config.plugins.UIPositionSetup.dst_top.value = self.dst_top.value
		config.plugins.UIPositionSetup.dst_height.value = self.dst_height.value
		config.plugins.UIPositionSetup.save()
		self.close()

	def keyCancel(self):
		if self["config"].isChanged():
			self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"))
		else:
			self.close()

	def cancelConfirm(self,ret):
		if ret:
			self.setPosition(int(config.plugins.UIPositionSetup.dst_left.value), int(config.plugins.UIPositionSetup.dst_width.value), int(config.plugins.UIPositionSetup.dst_top.value), int(config.plugins.UIPositionSetup.dst_height.value))
			self.close()

def main(session, **kwargs):
	session.open(UIPositionSetup)

def Plugins(**kwargs):
	if fileExists("/proc/stb/fb/dst_left"):
		return [PluginDescriptor(name = "UI position setup", description = "Adjust screen position", where = PluginDescriptor.WHERE_PLUGINMENU, fnc = main)]
	return []

