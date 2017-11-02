from Plugins.Plugin import PluginDescriptor

from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Sources.StaticText import StaticText

from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.Standby import TryQuitMainloop

from Components.SystemInfo import SystemInfo
from Components.PluginComponent import plugins

from Components.ConfigList import ConfigListScreen
from Components.config import config, getConfigListEntry, ConfigSubsection, ConfigYesNo, ConfigSelection
from Components.Network import iNetwork

import os

_deviseWOL = "/proc/stb/fp/wol"

_flagForceEnable = False
_flagSupportWol = _flagForceEnable and True or os.path.exists(_deviseWOL)

_tryQuitTable = {"deepstandby":1, "reboot":2, "guirestart":3}

_ethDevice = "eth0"
if SystemInfo.get("WOWLSupport", False):
	_ethDevice = "wlan3"

config.plugins.wolconfig = ConfigSubsection()
config.plugins.wolconfig.activate = ConfigYesNo(default = False)
config.plugins.wolconfig.location = ConfigSelection(default = "menu", choices = [("menu", _("Show on the Standby Menu")), ("deepstandby", _("Run at the Deep Standby"))])

import socket
class NetTool:
	@staticmethod
	def GetHardwareAddr(ethname):
		macaddr = ""
		try:
			sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
			sock.bind((ethname, 9999))

			macaddr = ":".join(["%02X" % ord(x) for x in sock.getsockname()[-1]])
		except Exception, Message:
			print Message
			macaddr = "Unknown"
		return macaddr

class WOLSetup(ConfigListScreen, Screen):
	skin = 	"""
		<screen name="WOLSetup" position="center,center" size="600,390" title="WakeOnLan Setup">
			<ePixmap pixmap="skin_default/buttons/red.png" position="5,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="155,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="305,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="455,0" size="140,40" alphatest="on" />

			<widget source="key_red" render="Label" position="5,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_green" render="Label" position="155,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_yellow" render="Label" position="305,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_blue" render="Label" position="455,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" foregroundColor="#ffffff" transparent="1" />

			<widget name="config" position="5,70" size="590,260" scrollbarMode="showOnDemand" />
			<widget name="introduction" position="5,345" size="590,40" font="Regular;24" halign="center" />
		</screen>
		"""
	def __init__(self, session):
		self.configlist = []
		self.session = session
		Screen.__init__(self, session)
		ConfigListScreen.__init__(self, self.configlist)

		self["actions"]  = ActionMap(["OkCancelActions", "ColorActions", "WizardActions"], {
			"cancel": self.OnKeyCancel,
			"green" : self.OnKeyGreen,
			"red"   : self.OnKeyRed,
			"blue"  : self.OnKeyBlue,
		}, -1)

		self["key_red"]    = StaticText(_("Close"))
		self["key_green"]  = StaticText(_("Save"))
		self["key_yellow"] = StaticText(_(" "))
		self["key_blue"]   = StaticText(_("Default"))
		self["introduction"] = Label(" ")

		self.default = {"activate":False, "location":"menu"}
		self.backup = {
			"activate":config.plugins.wolconfig.activate.value,
			"location":config.plugins.wolconfig.location.value,
			}

		self.MakeConfigList()

	def MakeConfigList(self):
		self.UpdateConfigList()

	def UpdateConfigList(self):
		self.configlist = []
		if _flagSupportWol:
			macaddr = " "
			self.configlist.append(getConfigListEntry(_("WakeOnLan Enable"), config.plugins.wolconfig.activate))
			if config.plugins.wolconfig.activate.value:
				self.configlist.append(getConfigListEntry(_("Location"), config.plugins.wolconfig.location))
				if SystemInfo.get("WOWLSupport", False):
					if iNetwork.getAdapterAttribute(_ethDevice, 'up'):
						macaddr = "HWaddr of %s is %s" % (_ethDevice, NetTool.GetHardwareAddr(_ethDevice))
					else:
						macaddr = "Wireless lan is not activated."
				else:
					macaddr = "HWaddr of %s is %s" % (_ethDevice, NetTool.GetHardwareAddr(_ethDevice))
			else:	macaddr = "Wake on Lan disabled"
			self["introduction"].setText(macaddr)

		self["config"].list = self.configlist
		self["config"].l.setList(self.configlist)

	def Save(self):
		config.plugins.wolconfig.activate.save()
		config.plugins.wolconfig.location.save()
		config.plugins.wolconfig.save()
		config.plugins.save()
		config.save()

	def Restore(self):
		print "[WOLSetup] Restore :", self.backup
		config.plugins.wolconfig.activate.value = self.backup["activate"]
		config.plugins.wolconfig.location.value = self.backup["location"]

	def OnKeyGreenCB(self, answer):
		if not answer:
			self.Restore()
			return
		self.Save()
		self.close()

	def OnKeyGreen(self):
		if config.plugins.wolconfig.activate.value == self.backup["activate"] and config.plugins.wolconfig.location.value == self.backup["location"]:
			self.close()
			return
		if not config.plugins.wolconfig.activate.value:
			WOLSetup.ActivateWOL(False, True)
			self.OnKeyBlue()
			self.Save()
			self.close()
			return
		message = _("If WOL is enabled, power consumption will be around 2W.\nErP Standby Power Regulation (<0.5W at standby) cannot be met.\nProceed?")
		self.session.openWithCallback(self.OnKeyGreenCB, MessageBox, message, MessageBox.TYPE_YESNO, default = True)

	def OnKeyCancel(self):
		self.Restore()
		self.close()

	def OnKeyRed(self):
		self.OnKeyCancel()

	def OnKeyBlue(self):
		print "[WOLSetup] Set Default :", self.default
		config.plugins.wolconfig.activate.value = self.default["activate"]
		config.plugins.wolconfig.location.value = self.default["location"]
		self.UpdateConfigList()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.UpdateConfigList()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.UpdateConfigList()

	@staticmethod
	def ActivateWOL(self=None, enable=True, writeDevice=False):
		print "[WOLSetup] Support :", _flagSupportWol, " Enable :", enable ," WriteDevice :", writeDevice
		if not _flagSupportWol:
			return
		if writeDevice:
			os.system('echo "%s" > %s' % (enable and "enable" or "disble",_deviseWOL))

	@staticmethod
	def DeepStandbyNotifierCB(self=None):
		if config.plugins.wolconfig.activate.value:
			if config.plugins.wolconfig.location.value == "deepstandby":
				print "[WOLSetup] Deep Standby with WOL."
				WOLSetup.ActivateWOL(writeDevice=True)
			else:	print "[WOLSetup] Deep Standby without WOL."
		else:	print "[WOLSetup] Nomal Deep Standby."

def SessionStartMain(session, **kwargs):
	config.misc.DeepStandbyOn.addNotifier(WOLSetup.DeepStandbyNotifierCB, initial_call=False)

def PluginMain(session, **kwargs):
	session.open(WOLSetup)

def DeepStandbyWOLMain(session, **kwargs):
	WOLSetup.ActivateWOL(session, writeDevice=True)
	session.open(TryQuitMainloop, _tryQuitTable["deepstandby"])

def MenuSelected(selected, **kwargs):
	if selected == "system":
		return [(_("WakeOnLan Setup"), PluginMain, "wolconfig", 80)]
	if selected == "shutdown" and config.plugins.wolconfig.activate.value and config.plugins.wolconfig.location.value == "menu":
		return [(_("Deep Standby with WOL"), DeepStandbyWOLMain, "deep_standby_wol", 80)]
	return []

def Plugins(**kwargs):
	if not _flagSupportWol: return []
	l = []
	l.append(PluginDescriptor(name=_("WakeOnLan Setup"), where=PluginDescriptor.WHERE_EXTENSIONSMENU, needsRestart=True, fnc=PluginMain))
	l.append(PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, fnc=SessionStartMain))
	l.append(PluginDescriptor(where=PluginDescriptor.WHERE_MENU, fnc=MenuSelected))
	return l
