from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen
from Components.config import config, getConfigListEntry, ConfigSubsection, ConfigSelection
from Components.ActionMap import ActionMap
from Screens.MessageBox import MessageBox
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Tools.Directories import fileExists

config.plugins.zappingModeSelection = ConfigSubsection()
config.plugins.zappingModeSelection.zappingMode = ConfigSelection(default = "mute", choices = [ ("mute", _("MUTE")), ("hold", _("HOLD"))] )

class ZappingModeSelectionInit:
	def __init__(self):
		self.setZappingMode(config.plugins.zappingModeSelection.zappingMode.value)

	def setZappingMode(self, mode = "mute"):
		if not fileExists("/proc/stb/video/zapping_mode"):
			return -1
		print "<ZappingModeSelection> set zapping mode : %s" % mode
		f = open("/proc/stb/video/zapping_mode", "w")
		f.write("%s" % mode)
		f.close()
		return 0

class ZappingModeSelection(Screen,ConfigListScreen,ZappingModeSelectionInit):
	skin = 	"""
		<screen position="center,center" size="400,250" title="Zapping Mode Selection" >
			<ePixmap pixmap="skin_default/buttons/red.png" position="30,10" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="230,10" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="30,10" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_green" render="Label" position="230,10" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="#ffffff" transparent="1" />
			<widget name="config" zPosition="2" position="5,70" size="380,180" scrollbarMode="showOnDemand" transparent="1" />
		</screen>
		"""

	def __init__(self,session):
		Screen.__init__(self,session)
		self.session = session
		self["shortcuts"] = ActionMap(["ShortcutActions", "SetupActions" ],
		{
			"ok": self.keySave,
			"cancel": self.keyCancel,
			"red": self.keyCancel,
			"green": self.keySave,
		}, -2)
		self.list = []
		ConfigListScreen.__init__(self, self.list,session = self.session)
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Ok"))
		self.createSetup()

	def createSetup(self):
		self.list = []
		self.rcsctype = getConfigListEntry(_("Zapping Mode"), config.plugins.zappingModeSelection.zappingMode)
		self.list.append( self.rcsctype )
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def keySave(self):
		print "<ZappingModeSelection> Zapping Code : ",config.plugins.zappingModeSelection.zappingMode.value
		ret = self.setZappingMode(config.plugins.zappingModeSelection.zappingMode.value)
		if ret == -1:
			self.resetConfig()
			self.session.openWithCallback(self.close, MessageBox, _("SET FAILED!\nPlease update to the latest driver"), MessageBox.TYPE_ERROR)
		else:
			self.saveAll()
			self.close()

	def resetConfig(self):
		for x in self["config"].list:
			x[1].cancel()

def main(session, **kwargs):
	session.open(ZappingModeSelection)

def Plugins(**kwargs):
	return [PluginDescriptor(name=_("ZappingModeSelection"), description="Zapping Mode Selection", where = PluginDescriptor.WHERE_PLUGINMENU, needsRestart = False, fnc=main)]

zappingmodeselectioninit = ZappingModeSelectionInit()
