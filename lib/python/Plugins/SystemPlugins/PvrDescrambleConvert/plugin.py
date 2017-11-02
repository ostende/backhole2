from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.config import config, getConfigListEntry
from PvrDescrambleConvert import pvr_descramble_convert

class PvrDescrambleConvertSetup(Screen, ConfigListScreen):
	skin = 	"""
		<screen position="center,center" size="590,320" >
			<ePixmap pixmap="skin_default/buttons/red.png" position="90,15" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="360,15" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="90,15" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_green" render="Label" position="360,15" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="#ffffff" transparent="1" />
			<widget name="config" zPosition="2" position="15,80" size="560,140" scrollbarMode="showOnDemand" transparent="1" />
			<widget source="description" render="Label" position="30,240" size="530,60" font="Regular;24" halign="center" valign="center" />
		</screen>
		"""

	def __init__(self,session):
		Screen.__init__(self,session)
		self.title = _("Pvr Descramble Convert Setup")
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
		self["key_green"] = StaticText(_("Save"))

		self["description"] = StaticText("")
		self.createConfig()
		self.createSetup()

	def createConfig(self):
		self.enableEntry = getConfigListEntry(_("Enable PVR Descramble in standby"), config.plugins.pvrdesconvertsetup.activate)

	def createSetup(self):
		self.list = []
		self.list.append( self.enableEntry )
		self["config"].list = self.list
		self["config"].l.setList(self.list)

def main(session, **kwargs):
	session.open(PvrDescrambleConvertSetup)

def Plugins(**kwargs):
	list = []
	list.append(
		PluginDescriptor(name=_("PVR Descramble Convert Setup"),
		description=_("PVR descramble in standby"),
		where = [PluginDescriptor.WHERE_PLUGINMENU],
		needsRestart = False,
		fnc = main))

	return list

