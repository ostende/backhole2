from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen
from Components.config import ConfigSelection, getConfigListEntry
from Components.Sources.StaticText import StaticText
from Screens.MessageBox import MessageBox
from Screens.Standby import TryQuitMainloop
import os

BOXMODE_BINNAME = "/usr/bin/nvram"

description_list = {}
description_list["1"] = "current box mode : 1"
description_list["2"] = "current box mode : 2"
description_list["3"] = "current box mode : 3"
description_list["4"] = "current box mode : 4"
description_list["5"] = "current box mode : 5"

class BoxModeConfig(Screen, ConfigListScreen):
	skin = 	"""
		<screen position="center,center" size="400,190" title="BoxModeConfig" >
			<ePixmap pixmap="skin_default/buttons/red.png" position="30,10" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="230,10" size="140,40" alphatest="on" />

			<widget source="key_red" render="Label" position="30,10" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_green" render="Label" position="230,10" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="#ffffff" transparent="1" />

			<widget name="config" zPosition="2" position="5,70" size="380,90" scrollbarMode="showOnDemand" transparent="1" />
			<widget source="description" render="Label" position="30,160" size="380,30" font="Regular;24" halign="center" valign="center" />
		</screen>
		"""

	def __init__(self, session):
		self.skin = BoxModeConfig.skin
		Screen.__init__(self, session)

		from Components.ActionMap import ActionMap
		from Components.Button import Button
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["description"] = StaticText(_("starting..."))

		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"ok": self.keyOk,
			"save": self.keyOk,
			"cancel": self.keyCancel,
			"green": self.keyOk,
			"red": self.keyCancel,
		}, -2)

		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session)
		setmodelist = [ ("1", "1 "), ("2", "2 "), ("3", "3 "), ("4", "4 "), ("5", "5 ") ]
		self.oldconfig = self.getCurrentValue()
		self.boxmode = ConfigSelection(choices = setmodelist, default = self.oldconfig)
		self.list.append(getConfigListEntry(_("BoxMode : "), self.boxmode))
		self["config"].list = self.list
		self["config"].l.setList(self.list)

		if not self.showDescription in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.showDescription)

	def getCurrentValue(self):
		global BOXMODE_BINNAME
		cmd = "%s getenv BOXMODE" % (BOXMODE_BINNAME)
		print "CMD : ", cmd
		current_value = os.popen(cmd).read().strip()
		try:
			if int(current_value) < 1:
				current_value = "1"
			elif int(current_value) > 5:
				current_value = "5"
		except:
			print '%s -> failed, force to set "3"' % cmd
			current_value = "3"
		return current_value

	def showDescription(self):
		global description_list
		current_value = self["config"].getCurrent()[1].value
		if current_value:
			text = description_list[current_value]
			self["description"].setText( _(text) )

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.showDescription()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.showDescription()

	def keyOk(self):
		current_value = self["config"].getCurrent()[1].value
		if self.oldconfig != current_value:		
			cmd = "%s setenv BOXMODE %s" % (BOXMODE_BINNAME, current_value)
			print "CMD : ", cmd
			os.system(cmd)

			msg = "You should reboot your STB now.\n Press OK Button."
			self.session.openWithCallback(self.doReboot, MessageBox, _(msg), type = MessageBox.TYPE_INFO)
		else:
			self.close()

	def doReboot(self, res = None):
		self.session.open(TryQuitMainloop, 2)

	def keyCancel(self):
		self.close()

def main(session, **kwargs):
	session.open(BoxModeConfig)

def Plugins(**kwargs):
	descriptors = []
	from os import path
	global BOXMODE_BINNAME
	if path.exists(BOXMODE_BINNAME):
		from Plugins.Plugin import PluginDescriptor
		descriptors.append(PluginDescriptor(name = "BoxModeConfig", description = _("BoxMode Configuration."), where = PluginDescriptor.WHERE_PLUGINMENU, fnc = main))
	return descriptors