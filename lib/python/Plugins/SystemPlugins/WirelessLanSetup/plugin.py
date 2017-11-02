from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.InputBox import InputBox
from Screens.Standby import *
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Screens.HelpMenu import HelpableScreen
from Components.Network import iNetwork
from Screens.NetworkSetup import NameserverSetup
from Components.Sources.StaticText import StaticText
from Components.Sources.Boolean import Boolean
from Components.Sources.List import List
from Components.Label import Label,MultiColorLabel
from Components.Pixmap import Pixmap,MultiPixmap
from Components.MenuList import MenuList
from Components.config import config, ConfigYesNo, ConfigIP, NoSave, ConfigText, ConfigPassword, ConfigSelection, getConfigListEntry, ConfigNothing
from Components.config import ConfigInteger, ConfigSubsection
from Components.ConfigList import ConfigListScreen
from Components.PluginComponent import plugins
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from Components.ActionMap import ActionMap, NumberActionMap, HelpableActionMap
from Components.Console import Console
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_CURRENT_SKIN
from Tools.LoadPixmap import LoadPixmap
from Plugins.Plugin import PluginDescriptor
from enigma import eTimer, ePoint, eSize, RT_HALIGN_LEFT, eListboxPythonMultiContent, gFont
from os import path as os_path, system as os_system, unlink, listdir, access, R_OK, popen
from re import compile as re_compile, search as re_search
from Tools.Directories import fileExists
import time
from pythonwifi.iwlibs import Wireless
from pythonwifi import flags as wifi_flags

class WlanSelection(Screen,HelpableScreen):
	skin = 	"""
		<screen position="center,center" size="510,400" title="Wireless Network Adapter Selection..." >
			<ePixmap pixmap="skin_default/div-h.png" position="0,350" zPosition="1" size="560,2" />
			<ePixmap pixmap="skin_default/border_menu.png" position="10,10" zPosition="1" size="250,300" transparent="1" alphatest="on" />

			<ePixmap pixmap="skin_default/buttons/red.png" position="10,360" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="360,360" size="140,40" alphatest="on" />

			<widget source="key_red" render="Label" position="10,360" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_green" render="Label" position="360,360" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="#ffffff" transparent="1" />

			<widget name="menulist" position="20,20" size="230,260" transparent="1" backgroundColor="#371e1c1a" zPosition="10" scrollbarMode="showOnDemand" />
			<widget source="description" render="Label" position="305,10" size="195,300" font="Regular;19" halign="center" valign="center" />
		</screen>
		"""
	def __init__(self, session):
		Screen.__init__(self,session)
		HelpableScreen.__init__(self)
		self.mainmenu = self.getWlandevice()
		self["menulist"] = MenuList(self.mainmenu)
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Select"))
		self["description"] = StaticText()
		self["description"].setText(_("Select Wireless Lan module. \n" ))
		self["OkCancelActions"] = HelpableActionMap(self, "OkCancelActions",
		{
			"ok": (self.ok, _("select interface")),
			"cancel": (self.close, _("exit network interface list")),
		})

		self["ColorActions"] = HelpableActionMap(self, "ColorActions",
		{
			"green": (self.ok, _("select interface")),
			"red": (self.close, _("exit network interface list")),
		})
		self.updateInterfaces()
		self.onClose.append(self.cleanup)

	def updateInterfaces(self):
		iNetwork.config_ready = False
		iNetwork.msgPlugins()
		iNetwork.getInterfaces()

	def checkIfaceMode(self, iface = None):
		try:
			obj = Wireless(iface)
			if obj.getMode() == 'Master':
				return -1
			else:
				return 0
		except:
			return -2

	def ok(self):
#		print len(self["menulist"].list)
		if len(self["menulist"].list) == 0:
			self.session.open(MessageBox, (_("Can not find any WirelessLan Module\n")),MessageBox.TYPE_ERROR,5 )
			return
		iface=self["menulist"].getCurrent()[1]
		if iface == None:
			return
		elif iNetwork.getAdapterAttribute(iface, "up") == True:
			ret = self.checkIfaceMode(iface)
			if ret == -2:
				self.session.open(MessageBox, (_("Invalid WirelessLan Module.\n")),MessageBox.TYPE_ERROR,5 )
				return
			elif ret == -1:
				self.session.open(MessageBox, (_("Can not setup WirelessLan Module in 'AP Mode'\n")),MessageBox.TYPE_ERROR,5 )
				return
		self.session.open(WlanSetup, iface)

	def getWlandevice(self):
		list = []
		for x in iNetwork.getInstalledAdapters():
			if x.startswith('eth') or x.startswith('br') or x.startswith('mon'):
				continue
			description=self.getAdapterDescription(x)
			if description == "Unknown network adapter":
				list.append((description,x))
			else:
				list.append((description + " (%s)"%x,x))
		return list

	def getAdapterDescription(self, iface):
		classdir = "/sys/class/net/" + iface + "/device/"
		driverdir = "/sys/class/net/" + iface + "/device/driver/"
		if os_path.exists(classdir):
			files = listdir(classdir)
			if 'driver' in files:
				if os_path.realpath(driverdir).endswith('rtw_usb_drv'):
					return _("Realtek")+ " " + _("WLAN adapter.")
				elif os_path.realpath(driverdir).endswith('ath_pci'):
					return _("Atheros")+ " " + _("WLAN adapter.")
				elif os_path.realpath(driverdir).endswith('zd1211b'):
					return _("Zydas")+ " " + _("WLAN adapter.")
				elif os_path.realpath(driverdir).endswith('rt73'):
					return _("Ralink")+ " " + _("WLAN adapter.")
				elif os_path.realpath(driverdir).endswith('rt73usb'):
					return _("Ralink")+ " " + _("WLAN adapter.")
				elif self.isRalinkModule(iface):
					return _("Ralink")+ " " + _("WLAN adapter.")
				else:
					return str(os_path.basename(os_path.realpath(driverdir))) + " " + _("WLAN adapter")
			else:
				return _("Unknown network adapter")
		elif os_path.exists("/tmp/bcm/%s"%iface):
			return _("BroadCom WLAN adapter")
		else:
			return _("Unknown network adapter")

	def isRalinkModule(self, iface):
# check vendor ID for lagacy driver
		vendorID = "148f" # ralink vendor ID
		idVendorPath = "/sys/class/net/%s/device/idVendor" % iface
		if access(idVendorPath, R_OK):
			fd = open(idVendorPath, "r")
			data = fd.read().strip()
			fd.close()

#			print "Vendor ID : %s" % data

			if data == vendorID:
				return True

# check sys driver path for kernel driver
		ralinkKmod = "rt2800usb" # ralink kernel driver name
		driverPath = "/sys/class/net/%s/device/driver/" % iface
		if os_path.exists(driverPath):
			driverName = os_path.basename(os_path.realpath(driverPath))

#			print "driverName : %s" % driverName

			if driverName == ralinkKmod:
				return True

		return False

	def cleanup(self):
		iNetwork.stopGetInterfacesConsole()

class WlanSetup(Screen,HelpableScreen):
	skin = 	"""
		<screen position="center,center" size="510,400" title="Wireless Network Setup Menu..." >
			<ePixmap pixmap="skin_default/div-h.png" position="0,350" zPosition="1" size="560,2" />
			<ePixmap pixmap="skin_default/border_menu.png" position="10,10" zPosition="1" size="250,300" transparent="1" alphatest="on" />

			<ePixmap pixmap="skin_default/buttons/red.png" position="10,360" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="360,360" size="140,40" alphatest="on" />

			<widget source="key_red" render="Label" position="10,360" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_green" render="Label" position="360,360" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="#ffffff" transparent="1" />

			<widget name="menulist" position="20,20" size="230,260" transparent="1" backgroundColor="#371e1c1a" zPosition="10" scrollbarMode="showOnDemand" />
			<widget source="description" render="Label" position="305,10" size="195,300" font="Regular;19" halign="center" valign="center" />
		</screen>
		"""
	def __init__(self, session, ifaces):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		self.session = session
		self.iface = ifaces
		self.restartLanRef = None
		self.LinkState = None
		self.mainmenu = self.MakeMenu()
		self["menulist"] = MenuList(self.mainmenu)
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Select"))
		self["description"] = StaticText()
		self["IFtext"] = StaticText()
		self["IF"] = StaticText()
		self.onLayoutFinish.append(self.loadDescription)
		
		self.oktext = _("Press OK on your remote control to continue.")
		
		self["WizardActions"] = HelpableActionMap(self, "WizardActions",
			{
			"up": (self.up, _("move up to previous entry")),
			"down": (self.down, _("move down to next entry")),
			"left": (self.left, _("move up to first entry")),
			"right": (self.right, _("move down to last entry")),
			})
		
		self["OkCancelActions"] = HelpableActionMap(self, "OkCancelActions",
			{
			"cancel": (self.close, _("exit networkadapter setup menu")),
			"ok": (self.ok, _("select menu entry")),
			})

		self["ColorActions"] = HelpableActionMap(self, "ColorActions",
			{
			"red": (self.close, _("exit networkadapter setup menu")),
			"green": (self.ok, _("select menu entry")),
			})

		self["actions"] = NumberActionMap(["WizardActions","ShortcutActions"],
		{
			"ok": self.ok,
			"back": self.close,
			"up": self.up,
			"down": self.down,
			"red": self.close,
			"left": self.left,
			"right": self.right,
		}, -2)
		self.onClose.append(self.cleanup)

	def loadDescription(self):
		if self["menulist"].getCurrent()[1] == 'setting':
			self["description"].setText(_("Edit the network configuration of your STB.\n" ) + self.oktext )
		if self["menulist"].getCurrent()[1] == 'scanap':
			self["description"].setText(_("Scan your network for wireless access points and connect to them using your selected wireless device.\n" ) + self.oktext )
		if self["menulist"].getCurrent()[1] == 'dns':
			self["description"].setText(_("Edit the Nameserver configuration of your STB.\n" ) + self.oktext )
		if self["menulist"].getCurrent()[1] == 'status':
			self["description"].setText(_("Shows the state of your wireless LAN connection.\n" ) + self.oktext )
		if self["menulist"].getCurrent()[1] == 'test':
			self["description"].setText(_("Test the network configuration of your STB.\n" ) + self.oktext )
		if self["menulist"].getCurrent()[1] == 'restart':
			self["description"].setText(_("Restart your network connection and interfaces.\n" ) + self.oktext )

	def up(self):
		self["menulist"].up()
		self.loadDescription()

	def down(self):
		self["menulist"].down()
		self.loadDescription()

	def left(self):
		self["menulist"].pageUp()
		self.loadDescription()

	def right(self):
		self["menulist"].pageDown()
		self.loadDescription()

	def ok(self):
		self.cleanup()
		if self["menulist"].getCurrent()[1] == 'setting':
			self.session.openWithCallback(self.checklist, WlanConfig, self.iface)
		elif self["menulist"].getCurrent()[1] == 'scanap':
			self.session.openWithCallback(self.WlanScanApCallback, WlanScanAp, self.iface)
		elif self["menulist"].getCurrent()[1] == 'dns':
			self.session.open(NameserverSetup)
		elif self["menulist"].getCurrent()[1] == 'status':
			self.session.open(Wlanstatus, self.iface)
		elif self["menulist"].getCurrent()[1] == 'test':
			self.session.openWithCallback(self.checklist,NetworkAdapterTest,self.iface)
		elif self["menulist"].getCurrent()[1] == 'restart':
			self.session.openWithCallback(self.restartLan, MessageBox, (_("Are you sure you want to restart your network interfaces?\n\n") + self.oktext ) )

	def checklist(self):
		self["menulist"].setList(self.MakeMenu())

	def MakeMenu(self):
		menu = []
		menu.append((_("Adapter settings"), "setting"))
		menu.append((_("Scan Wireless AP"), "scanap"))
#		menu.append((_("Nameserver settings"), "dns"))
		if iNetwork.getAdapterAttribute(self.iface, "up"):
			menu.append((_("Show WLAN Status"), "status"))
		menu.append((_("Network test"), "test"))
		menu.append((_("Restart network"), "restart"))

		return menu

	def WlanScanApCallback(self, essid = None):
		if essid is not None:
			self.session.openWithCallback(self.checklist, WlanConfig, self.iface)

	def restartLan(self, ret = False):
		if ret:
			iNetwork.restartNetwork(self.restartLanDataAvail)
			self.restartLanRef = self.session.openWithCallback(self.restartfinishedCB, MessageBox, _("Please wait while your network is restarting..."), type = MessageBox.TYPE_INFO, enable_input = False)

	def restartLanDataAvail(self, data):
		if data:
			iNetwork.getInterfaces(self.getInterfacesDataAvail)

	def getInterfacesDataAvail(self, data):
		if data:
			self.restartLanRef.close(True)

	def restartfinishedCB(self,data):
		if data:
			self.session.open(MessageBox, _("Finished restarting your network"), type = MessageBox.TYPE_INFO, timeout = 5, default = False)

	def cleanup(self):
		iNetwork.stopRestartConsole()
		iNetwork.stopGetInterfacesConsole()

ESSID_SELECTED_IN_APLIST = None
CHECK_NETWORK_SHARE = False

class WlanConfig(Screen, ConfigListScreen, HelpableScreen):
	skin = 	"""
		<screen position="center,center" size="510,400" title="Wireless Network Configuration..." >
			<ePixmap pixmap="skin_default/buttons/red.png" position="10,360" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="360,360" size="140,40" alphatest="on" />

			<widget source="key_red" render="Label" position="10,360" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_green" render="Label" position="360,360" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="#ffffff" transparent="1" />

			<widget name="config" position="10,10" backgroundColor="#371e1c1a" transparent="1" size="480,195" scrollbarMode="showOnDemand" />
			<ePixmap pixmap="skin_default/div-h.png" position="0,210" zPosition="1" size="560,2" />
			<widget source="ipaddresstext" render="Label" position="100,220" zPosition="1" size="190,21" font="Regular;19" halign="Left" valign="center" />
			<widget source="ipaddress" render="Label" position="300,220" zPosition="1" size="150,26" font="Regular;20" halign="Left" valign="center" />
			<widget source="netmasktext" render="Label" position="100,245" zPosition="1" size="190,21" font="Regular;19" halign="Left" valign="center" />
			<widget source="netmask" render="Label" position="300,245" zPosition="1" size="150,26" font="Regular;20" halign="Left" valign="center" />
			<widget source="gatewaytext" render="Label" position="100,270" zPosition="1" size="190,21" font="Regular;19" halign="Left" valign="center" />
			<widget source="gateway" render="Label" position="300,270" zPosition="1" size="150,26" font="Regular;20" halign="Left" valign="center" />
			<widget source="DNS1text" render="Label" position="100,295" zPosition="1" size="190,21" font="Regular;19" halign="Left" valign="center" />
			<widget source="DNS1" render="Label" position="300,295" zPosition="1" size="150,26" font="Regular;20" halign="Left" valign="center" />
			<widget source="DNS2text" render="Label" position="100,320" zPosition="1" size="190,21" font="Regular;19" halign="Left" valign="center" />
			<widget source="DNS2" render="Label" position="300,320" zPosition="1" size="150,26" font="Regular;20" halign="Left" valign="center" />
			<widget name="VKeyIcon" pixmap="skin_default/buttons/key_text.png" position="460,230" zPosition="10" size="35,25" transparent="1" alphatest="on" />
			<widget name="HelpWindow" pixmap="skin_default/buttons/key_text.png" position="383,420" zPosition="1" size="1,1" transparent="1" alphatest="on" />
		</screen>
		"""
	def __init__(self, session, iface):
		Screen.__init__(self,session)
		self.session = session
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Ok"))
		self["ipaddresstext"] = StaticText(_("IP Address"))
		self["ipaddress"] = StaticText(_("[ N/A ]"))
		self["netmasktext"] = StaticText(_("NetMask"))
		self["netmask"] = StaticText(_("[ N/A ]"))
		self["gatewaytext"] = StaticText(_("Gateway"))
		self["gateway"] = StaticText(_("[ N/A ]"))
		self["DNS1text"] = StaticText(_("Primary DNS"))
		self["DNS1"] = StaticText(_("[ N/A ]"))
		self["DNS2text"] = StaticText(_("Secondary DNS"))
		self["DNS2"] = StaticText(_("[ N/A ]"))
		self["OkCancelActions"] = ActionMap(["ShortcutActions", "SetupActions" ],
		{
			"ok": self.saveWlanConfig,
			"green": self.saveWlanConfig,
			"cancel": self.keyCancel,
			"red": self.keyCancel,
		}, -2)
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self["VKeyIcon"] = Pixmap()
		self["VKeyIcon"].hide()
		self.iface = iface

		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session)
		self.oldInterfaceState = iNetwork.getAdapterAttribute(self.iface, "up")

		self.updateInterfaces(self.updateInterfaceCB)
		self.onClose.append(self.cleanup)

		self.useWlCommand = os_path.exists("/tmp/bcm/%s"%iface)

	def updateInterfaces(self,callback = None):
		iNetwork.config_ready = False
		iNetwork.msgPlugins()
		iNetwork.getInterfaces(callback)

	def updateInterfaceCB(self, ret=None):
		if ret is not True:
			print "getInterfaces Fail... "

		self.createConfig()
		self.createSetup()

	def getWlConfName(self, iface):
		return "/etc/wl.conf.%s" % iface

	def readWlConf(self):
		wsconf = {}
		wsconf["ssid"] = "Vuplus AP"
		wsconf["hidden_ssid"] = False # not used
		wsconf["encrypt_mothod"] = "wpa2"
		wsconf["wep_keytype"] = "ascii" # not used
		wsconf["key"] = "XXXXXXXX"

		wlConfName = self.getWlConfName(self.iface)

		if fileExists(wlConfName):
			fd = open(wlConfName, "r")
			lines = fd.readlines()
			fd.close()

			for line in lines:
				try:
					(key, value) = line.strip().split('=',1)
				except:
					continue

				if key == 'ssid':
					wsconf["ssid"] = value.strip()
				if key == 'method':
					wsconf["encrypt_mothod"] = value.strip()
				elif key == 'key':
					wsconf["key"] = value.strip()
				else:
					continue

		print ""
		for (k,v) in wsconf.items():
			print "[wsconf][%s] %s" % (k , v)

		return wsconf

	def getWpaSupplicantName(self, iface):
		return "/etc/wpa_supplicant.conf.%s" % iface

	def readWpaSupplicantConf(self):
		wpaSupplicantName = self.getWpaSupplicantName(self.iface)
		wsconf = {}
		try:
			if fileExists(wpaSupplicantName):
				wpafd = open(wpaSupplicantName, "r")
				lines = wpafd.readlines()
				wpafd.close()
				data = {}
				for line in lines:
					try:
						(key, value) = line.strip().split('=',1)
					except:
						continue

#					if key not in ('ssid', 'ap_scan', 'scan_ssid', 'key_mgmt', 'proto', 'wep_key0', 'psk', '#psk'):
					if key not in ('ssid', 'scan_ssid', 'key_mgmt', 'proto', 'wep_key0', 'psk', '#psk'):
						continue

					elif key == 'ssid':
						data[key] = value.strip('"')

					else:
						data[key] = value.strip()

				wsconf["ssid"] = data.get("ssid", "INPUTSSID")
				wsconf["hidden_ssid"] = data.get("scan_ssid") == '1' and True or False

				key_mgmt = data.get("key_mgmt")
				if key_mgmt == "NONE":
					wep_key = data.get("wep_key0")

					if wep_key is None:
						wsconf["encrypt_mothod"] = "None"
					else:
						wsconf["encrypt_mothod"] = "wep"

						if wep_key.startswith('"') and wep_key.endswith('"'):
							wsconf["wep_keytype"] = "ascii"
							wsconf["key"] = wep_key.strip('"')
						else:
							wsconf["wep_keytype"] = "hex"
							wsconf["key"] = wep_key

				elif key_mgmt == "WPA-PSK":
					proto = data.get("proto")

					if proto == "WPA":
						wsconf["encrypt_mothod"] = "wpa"

					elif proto == "RSN":
						wsconf["encrypt_mothod"] = "wpa2"

					elif proto in ( "WPA RSN", "WPA WPA2"):
						wsconf["encrypt_mothod"] = "wpa/wpa2"

					else:
						wsconf["encrypt_mothod"] = "wpa2"

					psk = data.get("#psk")
					if psk:
						wsconf["key"] = psk.strip('"')
					else:
						wsconf["key"] = data.get("psk")
				else:
					wsconf["encrypt_mothod"] = "wpa2"
		except:
			pass

		if wsconf.get("ssid") is None:
			wsconf["ssid"] = "INPUTSSID"
		if wsconf.get("hidden_ssid") is None:
			wsconf["hidden_ssid"] = False
		if wsconf.get("encrypt_mothod") is None:
			wsconf["encrypt_mothod"] = "wpa2"
		if wsconf.get("wep_keytype") is None:
			wsconf["wep_keytype"] = "ascii"
		if wsconf.get("key") is None:
			wsconf["key"] = "XXXXXXXX"

#		print ""
#		for (k,v) in wsconf.items():
#			print "[wsconf][%s] %s" % (k , v)

		return wsconf

	def displayIP(self, domain, entry):
		text = entry.getText()
		if text is not None and text != "0.0.0.0":
			self[domain].setText(entry.getText())
		else:
			self[domain].setText(_("N/A"))

	def createConfig(self):
# activate Interface setup
		self.activateInterfaceEntry = NoSave(ConfigYesNo(default=iNetwork.getAdapterAttribute(self.iface, "up") or False))
# dhcp setup
		self.usedhcpConfigEntry = NoSave(ConfigYesNo(default=iNetwork.getAdapterAttribute(self.iface, "dhcp") or False))

# gateway setup
		if iNetwork.getAdapterAttribute(self.iface, "gateway"):
			usegatewayDefault=True
		else:
			usegatewayDefault=False
		self.usegatewayConfigEntry = NoSave(ConfigYesNo(default=usegatewayDefault))

		self.gatewayConfigEntry = NoSave(ConfigIP(default=iNetwork.getAdapterAttribute(self.iface, "gateway") or [0,0,0,0]))

# IP, Netmask setup
		self.IPConfigEntry = NoSave(ConfigIP(default=iNetwork.getAdapterAttribute(self.iface, "ip") or [0,0,0,0]))
		self.netmaskConfigEntry = NoSave(ConfigIP(default=iNetwork.getAdapterAttribute(self.iface, "netmask") or [255,0,0,0]))

# DNS setup
		if iNetwork.getAdapterAttribute(self.iface, "dns-nameservers"):
			dnsDefault = True
		else:
			dnsDefault = False
		self.useDNSConfigEntry = NoSave(ConfigYesNo(default=dnsDefault or False))

		nameserver = (iNetwork.getNameserverList() + [[0,0,0,0]] * 2)[0:2]
		self.primaryDNS = NoSave(ConfigIP(default=nameserver[0]))
		self.secondaryDNS = NoSave(ConfigIP(default=nameserver[1]))

		self.displayIP("ipaddress", self.IPConfigEntry)
		self.displayIP("netmask", self.netmaskConfigEntry)
		self.displayIP("gateway", self.gatewayConfigEntry)
		self.displayIP("DNS1", self.primaryDNS)
		self.displayIP("DNS2", self.secondaryDNS)

# read old configuration
		if self.useWlCommand:
			wsconf = self.readWlConf()
		else:
			wsconf = self.readWpaSupplicantConf()

# method setup
		encryptionChoices = [("wep", _("WEP")), ("wpa", _("WPA")), ("wpa2", _("WPA2")), ("None", _("No Encrypt"))  ]
		if not self.useWlCommand:
			encryptionChoices.append( ("wpa/wpa2", _("WPA/WPA2")) )
		self.methodConfigEntry = NoSave(ConfigSelection(default = wsconf["encrypt_mothod"], choices = encryptionChoices))

# key type setup
		keytypeChoices = [("ascii", _("ASCII")), ("hex", _("HEX"))]
		self.keytypeConfigEntry = NoSave(ConfigSelection(default = wsconf["wep_keytype"], choices = keytypeChoices))

# key setup
		self.keyConfigEntry = NoSave(ConfigPassword(default = wsconf["key"], visible_width = 50, fixed_size = False))

# hidden ssid setup
		self.hiddenssidConfigEntry = NoSave(ConfigYesNo(default = wsconf["hidden_ssid"]))

# ssid setup

		global ESSID_SELECTED_IN_APLIST
		if ESSID_SELECTED_IN_APLIST:
			essidDefault = ESSID_SELECTED_IN_APLIST
		else:
			essidDefault = wsconf["ssid"]

		self.ssidConfigEntry = NoSave(ConfigText(default = essidDefault, visible_width = 50, fixed_size = False))

	def createSetup(self):
		self.configList=[]
		self.usedeviceEntry = getConfigListEntry(_("Use Device"), self.activateInterfaceEntry)
		self.usedhcpEntry = getConfigListEntry(_("Use DHCP"), self.usedhcpConfigEntry)
		self.essidEntry = getConfigListEntry(_("SSID"), self.ssidConfigEntry)
		if not self.useWlCommand:
			self.hiddenessidEntry = getConfigListEntry(_("Hidden Network"), self.hiddenssidConfigEntry)
		self.methodEntry = getConfigListEntry(_("Encrypt Method"), self.methodConfigEntry)
		if not self.useWlCommand:
			self.keytypeEntry = getConfigListEntry(_("Key Type"), self.keytypeConfigEntry)
		self.keyEntry = getConfigListEntry(_("KEY"), self.keyConfigEntry)

		self.ipEntry = getConfigListEntry(_("IP"), self.IPConfigEntry)
		self.netmaskEntry = getConfigListEntry(_("NetMask"), self.netmaskConfigEntry)

		self.usegatewayEntry = getConfigListEntry(_("Use Gateway"), self.usegatewayConfigEntry)
		self.gatewayEntry = getConfigListEntry(_("Gateway"), self.gatewayConfigEntry)

		manualNameservers = (iNetwork.getInterfacesNameserverList(self.iface) + [[0,0,0,0]] * 2)[0:2]
		self.manualPrimaryDNS = NoSave(ConfigIP(default=manualNameservers[0]))
		self.manualSecondaryDNS = NoSave(ConfigIP(default=manualNameservers[1]))

		self.usednsEntry =  getConfigListEntry(_("Use Manual dns-nameserver"), self.useDNSConfigEntry)
		self.primaryDNSConfigEntry = getConfigListEntry(_('Primary DNS'), self.manualPrimaryDNS)
		self.secondaryDNSConfigEntry = getConfigListEntry(_('Secondary DNS'), self.manualSecondaryDNS)

		self.configList.append( self.usedeviceEntry )
		if self.activateInterfaceEntry.value is True:
			self.configList.append( self.usedhcpEntry )

			if self.usedhcpConfigEntry.value is True:
				self.configList.append(self.usednsEntry)
			else:
				self.configList.append(self.ipEntry)
				self.configList.append(self.netmaskEntry)
				self.configList.append(self.usegatewayEntry)

				if self.usegatewayConfigEntry.value is True:
					self.configList.append(self.gatewayEntry)

			if self.useDNSConfigEntry.value is True or self.usedhcpConfigEntry.value is False:
				self.configList.append(self.primaryDNSConfigEntry)
				self.configList.append(self.secondaryDNSConfigEntry)

			if not self.useWlCommand:
				self.configList.append( self.hiddenessidEntry )

			self.configList.append( self.essidEntry )
			self.configList.append( self.methodEntry )

			if self.methodConfigEntry.value =="wep":
				if not self.useWlCommand:
					self.configList.append( self.keytypeEntry )

			if self.methodConfigEntry.value != "None":
				self.configList.append( self.keyEntry )

		self["config"].list = self.configList
		self["config"].l.setList(self.configList)
		if not self.showTextIcon in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.showTextIcon)

	def showTextIcon(self):
		if isinstance(self["config"].getCurrent()[1], ConfigText) or isinstance(self["config"].getCurrent()[1], ConfigPassword):
			self["VKeyIcon"].show()
		else:
			self["VKeyIcon"].hide()

	def onSelectHelpWindow(self, ret = False):
		if isinstance(self["config"].getCurrent()[1], ConfigText) or isinstance(self["config"].getCurrent()[1], ConfigPassword):
			self["config"].getCurrent()[1].onSelect(self.session)

	def onDeselectHelpWindow(self, ret = False):
		if isinstance(self["config"].getCurrent()[1], ConfigText) or isinstance(self["config"].getCurrent()[1], ConfigPassword):
			self["config"].getCurrent()[1].onDeselect(self.session)

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.newConfig()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.newConfig()

	def newConfig(self):
		if self["config"].getCurrent() == self.usedeviceEntry or self["config"].getCurrent() == self.usedhcpEntry \
			or self["config"].getCurrent() == self.usegatewayEntry or self["config"].getCurrent() == self.methodEntry \
			or self["config"].getCurrent() == self.methodEntry or self["config"].getCurrent() == self.usednsEntry:
			self.createSetup()

	def saveWlanConfig(self):
		try:
			self.onDeselectHelpWindow()

			if self["config"].isChanged():
				self.session.openWithCallback(self.checkNetworkConfig, MessageBox, (_("Are you sure you want to restart your network interfaces?\n") ) )
			else:
				self.session.openWithCallback(self.checkNetworkConfig, MessageBox, (_("Network configuration is not changed....\n\nAre you sure you want to restart your network interfaces?\n") ) )
		except:
			pass

	def checkNetworkConfig(self, ret = False):
		if ret == False:
			self.onSelectHelpWindow()

		elif len(self.ssidConfigEntry.value) == 0:
			self.session.open(MessageBox, ("PLEASE INPUT SSID"), type = MessageBox.TYPE_ERROR, timeout = 10)

		elif len(self.keyConfigEntry.value) == 0:
			self.session.open(MessageBox, ("PLEASE INPUT ENCRYPT KEY"), type = MessageBox.TYPE_ERROR, timeout = 10)

		else:
			global CHECK_NETWORK_SHARE
			if CHECK_NETWORK_SHARE:
				self.checkNetworkShares(self.confirmAnotherIfaces)
			else:
				self.confirmAnotherIfaces()

	def checkNetworkShares(self, callback):
		cmd = "cat /proc/mounts"
		data = popen(cmd).readlines()
		networks = ['nfs','smbfs','ncp','coda']
		for line in data:
			split = line.strip().split(' ',3)
			if split[2] in networks:
				self.session.openWithCallback(self.onSelectHelpWindow, MessageBox, ("NOT deconfiguring network interfaces :\n network shares still mounted\n"), type = MessageBox.TYPE_ERROR, timeout = 10)
				return
		callback()

	def confirmAnotherIfaces(self):
		num_configured_if = len(iNetwork.getConfiguredAdapters())
		if num_configured_if >= 1:
			if num_configured_if == 1 and self.iface in iNetwork.getConfiguredAdapters():
				self.confirmAnotherIfacesCB(False)
			else:
				self.session.openWithCallback(self.confirmAnotherIfacesCB, MessageBox, _("A second configured interface has been found.\n\nDo you want to disable the second network interface?"), default = True)
		else:
			self.confirmAnotherIfacesCB(False)

	def isWPAMethod(self, method):
		if method in ("wep", "None"):
			return False
		else:
			return True

	def confirmAnotherIfacesCB(self, ret):
		if ret == True:
			configuredInterfaces = iNetwork.getConfiguredAdapters()
			for interface in configuredInterfaces:
				if interface == self.iface:
					continue
				iNetwork.setAdapterAttribute(interface, "up", False)
				iNetwork.deactivateInterface(interface)

		plainpwd = None
		psk = None

		if self.isWPAMethod(self.methodConfigEntry.value) and (not self.useWlCommand):
			(psk, plainpwd) = self.getWpaPhrase()

		res = False
		if self.useWlCommand:
			res = self.writeWlConf()
		else:
			res = self.writeWpasupplicantConf(psk, plainpwd)

		if res:
			self.writeNetConfig()

	def writeWlConf(self):
		wsconf = {}
		wsconf["ssid"] = "Vuplus AP"
		wsconf["hidden_ssid"] = False # not used
		wsconf["encrypt_mothod"] = "None"
		wsconf["wep_keytype"] = "ascii" # not used
		wsconf["key"] = "XXXXXXXX"
		
		wlConfName = self.getWlConfName(self.iface)

		try:
			fd = open(wlConfName, "w")
		except:
			self.session.open(MessageBox, _("%s open error." % wlConfName ), type = MessageBox.TYPE_ERROR, timeout = 10)
			return False

		contents = ""
		contents += "ssid="+self.ssidConfigEntry.value+"\n"
		contents += "method="+self.methodConfigEntry.value+"\n"
		contents += "key="+self.keyConfigEntry.value+"\n"

		print "content = \n"+contents
		fd.write(contents)
		fd.close()

		return True

	def getWpaPhrase(self):
		cmd = "wpa_passphrase '%s' '%s'" % (self.ssidConfigEntry.value, self.keyConfigEntry.value)
#		print cmd
		data = popen(cmd).readlines()
		plainpwd = None
		psk = None
		for line in data:
#			print line,
			try:
				(key, value) = line.strip().split('=',1)
			except:
				continue

			if key == '#psk':
				plainpwd = line
			elif key == 'psk':
				psk = line

		return (psk, plainpwd)

	def writeWpasupplicantConf(self, passphrasekey=None, plainpwd=None):
		wpaSupplicantName = self.getWpaSupplicantName(self.iface)
		try:
			wpafd = open(wpaSupplicantName, "w")
		except:
			self.session.open(MessageBox, _("%s open error." % wpaSupplicantName ), type = MessageBox.TYPE_ERROR, timeout = 10)
			return False

		contents = "#WPA Supplicant Configuration by STB\n"
		contents += "ctrl_interface=/var/run/wpa_supplicant\n"
		contents += "eapol_version=1\n"
		contents += "fast_reauth=1\n"
		contents += "ap_scan=1\n"
		contents += "network={\n"
# ssid
		contents += "\tssid=\""+self.ssidConfigEntry.value+"\"\n"
# hidden ssid
		if self.hiddenssidConfigEntry.value is True:
			contents += "\tscan_ssid=1\n"
		else:
			contents += "\tscan_ssid=0\n"

		if self.methodConfigEntry.value == "None":
			contents += "\tkey_mgmt=NONE\n"

		elif self.methodConfigEntry.value == "wep":
			contents += "\tkey_mgmt=NONE\n"
			contents += "\twep_key0="
			if self.keytypeConfigEntry.value == "ascii":
				contents += "\""+self.keyConfigEntry.value+"\"\n"
			else:
				contents += self.keyConfigEntry.value+"\n"

		else:
			if self.methodConfigEntry.value == "wpa":
				contents += "\tkey_mgmt=WPA-PSK\n"
				contents += "\tproto=WPA\n"
				contents += "\tpairwise=CCMP TKIP\n"
				contents += "\tgroup=CCMP TKIP\n"
			elif self.methodConfigEntry.value == "wpa2":
				contents += "\tkey_mgmt=WPA-PSK\n"
				contents += "\tproto=RSN\n"
				contents += "\tpairwise=CCMP TKIP\n"
				contents += "\tgroup=CCMP TKIP\n"
			else:
				contents += "\tkey_mgmt=WPA-PSK\n"
				contents += "\tproto=WPA RSN\n"
				contents += "\tpairwise=CCMP TKIP\n"
				contents += "\tgroup=CCMP TKIP\n"

#				print "plainpwd : ",plainpwd
#				print "passphrasekey : ",passphrasekey
			if plainpwd is not None and passphrasekey is not None:
				contents += plainpwd
				contents += passphrasekey
			else:
				contents += "\tpsk=%s\n" % self.keyConfigEntry.value

		contents += "}\n"
#		print "content = \n"+contents
		wpafd.write(contents)
		wpafd.close()

		return True

	def writeNetConfig(self):
		if self.activateInterfaceEntry.value is True:
			iNetwork.setAdapterAttribute(self.iface, "up", True)
			if self.usedhcpConfigEntry.value is True:
				iNetwork.setAdapterAttribute(self.iface, "dhcp", True)
			else:
				iNetwork.setAdapterAttribute(self.iface, "dhcp", False)
				iNetwork.setAdapterAttribute(self.iface, "ip", self.IPConfigEntry.value)
				iNetwork.setAdapterAttribute(self.iface, "netmask", self.netmaskConfigEntry.value)
				if self.usegatewayConfigEntry.value is True:
					iNetwork.setAdapterAttribute(self.iface, "gateway", self.gatewayConfigEntry.value)
			if self.useDNSConfigEntry.value is True or self.usedhcpConfigEntry.value is False:
				interfacesDnsLines = self.makeLineDnsNameservers([self.manualPrimaryDNS.value, self.manualSecondaryDNS.value])
				if interfacesDnsLines == "" :
					interfacesDnsLines = False
				iNetwork.setAdapterAttribute(self.iface, "dns-nameservers", interfacesDnsLines)
			else:
				iNetwork.setAdapterAttribute(self.iface, "dns-nameservers", False)
		else:
			iNetwork.setAdapterAttribute(self.iface, "up", False)
			iNetwork.deactivateInterface(self.iface)

		if self.useWlCommand:
			contents = '\tpre-up wl-config.sh -m %s -k %s -s "%s" \n' % (self.methodConfigEntry.value, self.keyConfigEntry.value, self.ssidConfigEntry.value)
			contents += '\tpost-down wl-down.sh\n'
		else:
			wpaSupplicantName = self.getWpaSupplicantName(self.iface)
			contents = "\tpre-up wpa_supplicant -i"+self.iface+" -c%s -B -D" % (wpaSupplicantName)  +iNetwork.detectWlanModule(self.iface)+"\n"
			contents += "\tpost-down wpa_cli terminate\n"
		iNetwork.setAdapterAttribute(self.iface, "configStrings", contents)
		iNetwork.writeNetworkConfig()
		iNetwork.restartNetwork(self.updateCurrentInterfaces)
		self.configurationmsg = None
		self.configurationmsg = self.session.openWithCallback(self.configFinished, MessageBox, _("Please wait for activation of your network configuration..."), type = MessageBox.TYPE_INFO, enable_input = False)

	def makeLineDnsNameservers(self, nameservers = []):
		line = "" 
		entry = ' '.join([("%d.%d.%d.%d" % tuple(x)) for x in nameservers if x != [0, 0, 0, 0] ])
		if len(entry):
			line+="\tdns-nameservers %s\n" % entry
		return line

	def updateCurrentInterfaces(self, ret):
		if ret is True:
			iNetwork.getInterfaces(self.configurationMsgClose)
		elif self.configurationmsg is not None:
			self.configurationmsg.close(False)

	def configurationMsgClose(self,ret):
		if self.configurationmsg is not None:
			if ret is True:
				self.configurationmsg.close(True)
			else:
				self.configurationmsg.close(False)

	def configFinished(self,data):
		if data is True:
			self.session.openWithCallback(self.configFinishedCB, MessageBox, _("Your network configuration has been activated."), type = MessageBox.TYPE_INFO, timeout = 10)
			global ESSID_SELECTED_IN_APLIST
			ESSID_SELECTED_IN_APLIST = None
		else:
			self.session.openWithCallback(self.configFinishedCB, MessageBox, _("Network configuration is failed."), type = MessageBox.TYPE_INFO, timeout = 10)

	def configFinishedCB(self, data):
		if data is True:
			self.close()
			
	def keyCancelConfirm(self, result):
		if not result:
			self.onSelectHelpWindow()
			return

		if self.oldInterfaceState is False:
			iNetwork.deactivateInterface(self.iface, self.keyCancelCB)
		else:
			self.close()

	def keyCancel(self,yesno = True):
		if self["config"].isChanged():
			self.onDeselectHelpWindow()
			self.session.openWithCallback(self.keyCancelConfirm, MessageBox, _("Really close without saving settings?"))
		else:
			self.close()

	def keyCancelCB(self,data):
		if data is True:
			self.close()

	def cleanup(self):
		iNetwork.stopRestartConsole()
		iNetwork.stopGetInterfacesConsole()
		iNetwork.stopDeactivateInterfaceConsole()

SHOW_HIDDEN_NETWORK = False
class WlanScanAp(Screen,HelpableScreen):
	skin = 	"""
		<screen position="center,center" size="510,400" title="Wireless Network AP Scan..." >
			<ePixmap pixmap="skin_default/div-h.png" position="0,350" zPosition="1" size="560,2" />
			<ePixmap pixmap="skin_default/border_menu.png" position="10,10" zPosition="1" size="250,300" transparent="1" alphatest="on" />

			<ePixmap pixmap="skin_default/buttons/red.png" position="10,360" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="185,360" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="360,360" size="140,40" alphatest="on" />

			<widget source="key_red" render="Label" position="10,360" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_green" render="Label" position="185,360" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_blue" render="Label" position="360,360" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" foregroundColor="#ffffff" transparent="1" />

			<widget name="aplist" position="20,20" size="230,275" backgroundColor="#371e1c1a" transparent="1" zPosition="10" scrollbarMode="showOnDemand" />

			<widget source="ESSID" render="Label" position="265,70" zPosition="1" size="240,30" font="Regular;18" halign="center" valign="center" />
			<widget source="Address" render="Label" position="265,100" zPosition="1" size="240,30" font="Regular;18" halign="center" valign="center" />
			<widget source="Protocol" render="Label" position="265,130" zPosition="1" size="240,30" font="Regular;18" halign="center" valign="center" />
			<widget source="Frequency" render="Label" position="265,160" zPosition="1" size="240,30" font="Regular;18" halign="center" valign="center" />
			<widget source="Channel" render="Label" position="265,190" zPosition="1" size="240,30" font="Regular;18" halign="center" valign="center" />
			<widget source="Encryption key" render="Label" position="265,220" zPosition="1" size="240,30" font="Regular;18" halign="center" valign="center" />
			<widget source="BitRate" render="Label" position="265,250" zPosition="1" size="240,30" font="Regular;18" halign="center" valign="center" />
			<widget source="Status" render="Label" position="115,310" zPosition="1" size="300,30" font="Regular;18" halign="center" valign="center" />
		</screen>
		"""

	def __init__(self, session, iface):
		Screen.__init__(self,session)
		HelpableScreen.__init__(self)
		self.session = session
		self.iface = iface
		self.wlanscanap = None
		self.apList = {}
		self.setApList = []

		self["WizardActions"] = HelpableActionMap(self, "WizardActions",
		{
			"up": (self.up, _("move up to previous entry")),
			"down": (self.down, _("move down to next entry")),
			"left": (self.left, _("move up to first entry")),
			"right": (self.right, _("move down to last entry")),
		}, -2)

		self["OkCancelActions"] = HelpableActionMap(self, "OkCancelActions",
		{
			"cancel": (self.close, _("exit")),
			"ok": (self.ok, "select AP"),
		})

		self["ColorActions"] = HelpableActionMap(self, "ColorActions",
		{
			"red": (self.close, _("exit")),
			"green": (self.ok, "select AP"),
			"blue": (self.startWlanConfig, "Edit Wireless settings"),
		})

		self["aplist"] = MenuList(self.setApList)
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Select"))
		self["key_blue"] = StaticText(_("EditSetting"))
		self["Status"] = StaticText(_(" "))
		self["ESSID"] = StaticText(" ")
		self["Address"] = StaticText(" ")
		self["Protocol"] = StaticText(" ")
		self["Frequency"] = StaticText(" ")
		self["Channel"] = StaticText(" ")
		self["Encryption key"] = StaticText(" ")
		self["BitRate"] = StaticText(" ")
		self.oldInterfaceState = iNetwork.getAdapterAttribute(self.iface, "up")

		self.startupTimer = eTimer()
		self.startupTimer.callback.append(self.startup)

		self.activateIfaceTimer = eTimer()
		self.activateIfaceTimer.callback.append(self.activateIface)

		self.updateStatusTimer = eTimer()
		self.updateStatusTimer.callback.append(self.updateStatus)
		
		self.scanAplistTimer = eTimer()
		self.scanAplistTimer.callback.append(self.scanApList)
		
		self.apList = {}
		self.onClose.append(self.__onClose)
		self.onShown.append(lambda: self.startupTimer.start(10, True))

		self.useWlCommand = os_path.exists("/tmp/bcm/%s"%iface)

	def startup(self):
		if self.oldInterfaceState is not True:
			self["Status"].setText(("Please wait for activating interface..."))
			self.activateIfaceTimer.start(10, True)
		else:
			self.updateStatusTimer.start(10, True)

	def activateIface(self):
		os_system("ifconfig "+self.iface+" up")
		iNetwork.setAdapterAttribute(self.iface, "up", True)

		if self.useWlCommand:
			os_system("wl up")

		self.updateStatusTimer.start(10, True)
		

	def updateStatus(self):
		self["Status"].setText(("Please wait for scanning AP..."))
		self.scanAplistTimer.stop()
		self.scanAplistTimer.start(10, True)

	def updateAPList(self):
		self.updateStatusTimer.stop()
		self.updateStatusTimer.start(5000, True)

	def left(self):
		self["aplist"].pageUp()
		self.displayApInfo()
	
	def right(self):
		self["aplist"].pageDown()
		self.displayApInfo()

	def up(self):
		self["aplist"].up()
		self.displayApInfo()
		
	def down(self):
		self["aplist"].down()
		self.displayApInfo()

	def ok(self):
		global ESSID_SELECTED_IN_APLIST
		if self["aplist"].getCurrent() is not None:
			ESSID_SELECTED_IN_APLIST = self["aplist"].getCurrent()[0]
		self.close()

	def startWlanConfig(self): # key blue
		global ESSID_SELECTED_IN_APLIST
		if self["aplist"].getCurrent() is not None:
			ESSID_SELECTED_IN_APLIST = self["aplist"].getCurrent()[0]
			self.close(True)

	def getScanResult(self, wirelessObj):
		Iwscanresult  = None
		try:
			Iwscanresult  = wirelessObj.scan()
		except IOError:
			print "%s Interface doesn't support scanning.."%self.iface
		return Iwscanresult

	def scanApList(self):
		self.apList = {}
		self.setApList = []

		wirelessObj = Wireless(self.iface)
		Iwscanresult=self.getScanResult(wirelessObj)

		if Iwscanresult is None or len(Iwscanresult.aplist) == 0:
			self["Status"].setText(("NO AP detected"))
			self.updateAPList()
			return

		try:
			(num_channels, frequencies) = wirelessObj.getChannelInfo()
		except:
			pass

		index = 1
		for ap in Iwscanresult:
			self.apList[index] = {}
			self.apList[index]["Address"] = ap.bssid
			if len(ap.essid) == 0:
				self.apList[index]["ESSID"] = None
			else:
				self.apList[index]["ESSID"] = ap.essid

			self.apList[index]["Protocol"] = ap.protocol
			self.apList[index]["Frequency"] = wirelessObj._formatFrequency(ap.frequency.getFrequency())
			try:
				self.apList[index]["Channel"] = frequencies.index(self.apList[index]["Frequency"]) + 1
			except:
				self.apList[index]["Channel"] = "Unknown"

			self.apList[index]["Quality"] = "%s/%s" % \
				( ap.quality.quality, wirelessObj.getQualityMax().quality )
			self.apList[index]["Signal Level"] = "%s/%s" % \
				( ap.quality.getSignallevel(), "100" )
			self.apList[index]["Noise Level"] = "%s/%s" % \
				( ap.quality.getNoiselevel(), "100" )

# get encryption key on/off
			key_status = "Unknown"
			if (ap.encode.flags & wifi_flags.IW_ENCODE_DISABLED):
				key_status = "off"
			elif (ap.encode.flags & wifi_flags.IW_ENCODE_NOKEY):
				if (ap.encode.length <= 0):
					key_status = "on"
			self.apList[index]["Encryption key"] = key_status

# get bitrate
			if len(ap.rate) > 0:
				if len(ap.rate[0]) > 0:
					self.apList[index]["BitRate"] = wirelessObj._formatBitrate(ap.rate[0][0])
			else:
				self.apList[index]["BitRate"] = ""
			index += 1

#		print self.apList

		# update menu list
		ap_index = 0
		for (ap_index, ap_info) in self.apList.items():
			essid = ap_info.get("ESSID", None)
			if essid is None:
				global SHOW_HIDDEN_NETWORK
				if SHOW_HIDDEN_NETWORK:
					essid = "# Hidden Network"
				else:
					continue
			self.setApList.append( (essid, int(ap_index)) )

		self["aplist"].setList(self.setApList)
#		print "menu aplist : ", self.setApList
		self["Status"].setText(("%d AP detected" % len(self.setApList)))
		self.displayApInfo()

		self.updateAPList()

	def displayApInfo(self):
		if self["aplist"].getCurrent() is not None:
			index = self["aplist"].getCurrent()[1]
			for key in ["Address", "ESSID", "Protocol", "Frequency", "Encryption key", "BitRate", "Channel"]:
				if self.apList[index].has_key(key) and self.apList[index][key] is not None:
					value = str(self.apList[index][key])
				else:
					value = "None"
				self[key].setText(( "%s:  %s" % (key, value) ))	

	def __onClose(self):
		if self.oldInterfaceState is not True:
			os_system("ifconfig "+self.iface+" down")
			iNetwork.setAdapterAttribute(self.iface, "up", False)

			if self.useWlCommand:
				os_system("wl down")

class NetworkAdapterTest(Screen):
	def __init__(self, session,iface):
		Screen.__init__(self, session)
		self.iface = iface
		self.oldInterfaceState = iNetwork.getAdapterAttribute(self.iface, "up")
		self.setLabels()
		self.onClose.append(self.cleanup)
		self.onHide.append(self.cleanup)
		
		self["updown_actions"] = NumberActionMap(["WizardActions","ShortcutActions"],
		{
			"ok": self.KeyOK,
			"blue": self.KeyOK,
			"up": lambda: self.updownhandler('up'),
			"down": lambda: self.updownhandler('down'),
		
		}, -2)
		
		self["shortcuts"] = ActionMap(["ShortcutActions","WizardActions"],
		{
			"red": self.cancel,
			"back": self.cancel,
		}, -2)
		self["infoshortcuts"] = ActionMap(["ShortcutActions","WizardActions"],
		{
			"red": self.closeInfo,
			"back": self.closeInfo,
		}, -2)
		self["shortcutsgreen"] = ActionMap(["ShortcutActions"],
		{
			"green": self.KeyGreen,
		}, -2)
		self["shortcutsgreen_restart"] = ActionMap(["ShortcutActions"],
		{
			"green": self.KeyGreenRestart,
		}, -2)
		self["shortcutsyellow"] = ActionMap(["ShortcutActions"],
		{
			"yellow": self.KeyYellow,
		}, -2)
		
		self["shortcutsgreen_restart"].setEnabled(False)
		self["updown_actions"].setEnabled(False)
		self["infoshortcuts"].setEnabled(False)
		self.onClose.append(self.delTimer)	
		self.onLayoutFinish.append(self.layoutFinished)
		self.steptimer = False
		self.nextstep = 0
		self.activebutton = 0
		self.nextStepTimer = eTimer()
		self.nextStepTimer.callback.append(self.nextStepTimerFire)

	def cancel(self):
		if self.oldInterfaceState is False:
			iNetwork.setAdapterAttribute(self.iface, "up", self.oldInterfaceState)
			iNetwork.deactivateInterface(self.iface)
		self.close()

	def closeInfo(self):
		self["shortcuts"].setEnabled(True)		
		self["infoshortcuts"].setEnabled(False)
		self["InfoText"].hide()
		self["InfoTextBorder"].hide()
		self["key_red"].setText(_("Close"))

	def delTimer(self):
		del self.steptimer
		del self.nextStepTimer

	def nextStepTimerFire(self):
		self.nextStepTimer.stop()
		self.steptimer = False
		self.runTest()

	def updownhandler(self,direction):
		if direction == 'up':
			if self.activebutton >=2:
				self.activebutton -= 1
			else:
				self.activebutton = 6
			self.setActiveButton(self.activebutton)
		if direction == 'down':
			if self.activebutton <=5:
				self.activebutton += 1
			else:
				self.activebutton = 1
			self.setActiveButton(self.activebutton)

	def setActiveButton(self,button):
		if button == 1:
			self["EditSettingsButton"].setPixmapNum(0)
			self["EditSettings_Text"].setForegroundColorNum(0)
			self["NetworkInfo"].setPixmapNum(0)
			self["NetworkInfo_Text"].setForegroundColorNum(1)
			self["AdapterInfo"].setPixmapNum(1) 		  # active
			self["AdapterInfo_Text"].setForegroundColorNum(2) # active
		if button == 2:
			self["AdapterInfo_Text"].setForegroundColorNum(1)
			self["AdapterInfo"].setPixmapNum(0)
			self["DhcpInfo"].setPixmapNum(0)
			self["DhcpInfo_Text"].setForegroundColorNum(1)
			self["NetworkInfo"].setPixmapNum(1) 		  # active
			self["NetworkInfo_Text"].setForegroundColorNum(2) # active
		if button == 3:
			self["NetworkInfo"].setPixmapNum(0)
			self["NetworkInfo_Text"].setForegroundColorNum(1)
			self["IPInfo"].setPixmapNum(0)
			self["IPInfo_Text"].setForegroundColorNum(1)
			self["DhcpInfo"].setPixmapNum(1) 		  # active
			self["DhcpInfo_Text"].setForegroundColorNum(2) 	  # active
		if button == 4:
			self["DhcpInfo"].setPixmapNum(0)
			self["DhcpInfo_Text"].setForegroundColorNum(1)
			self["DNSInfo"].setPixmapNum(0)
			self["DNSInfo_Text"].setForegroundColorNum(1)
			self["IPInfo"].setPixmapNum(1)			# active
			self["IPInfo_Text"].setForegroundColorNum(2)	# active		
		if button == 5:
			self["IPInfo"].setPixmapNum(0)
			self["IPInfo_Text"].setForegroundColorNum(1)
			self["EditSettingsButton"].setPixmapNum(0)
			self["EditSettings_Text"].setForegroundColorNum(0)
			self["DNSInfo"].setPixmapNum(1)			# active
			self["DNSInfo_Text"].setForegroundColorNum(2)	# active
		if button == 6:
			self["DNSInfo"].setPixmapNum(0)
			self["DNSInfo_Text"].setForegroundColorNum(1)
			self["EditSettingsButton"].setPixmapNum(1) 	   # active
			self["EditSettings_Text"].setForegroundColorNum(2) # active
			self["AdapterInfo"].setPixmapNum(0)
			self["AdapterInfo_Text"].setForegroundColorNum(1)
			
	def runTest(self):
		next = self.nextstep
		if next == 0:
			self.doStep1()
		elif next == 1:
			self.doStep2()
		elif next == 2:
			self.doStep3()
		elif next == 3:
			self.doStep4()
		elif next == 4:
			self.doStep5()
		elif next == 5:
			self.doStep6()
		self.nextstep += 1

	def doStep1(self):
		self.steptimer = True
		self.nextStepTimer.start(3000)
		self["key_yellow"].setText(_("Stop test"))

	def doStep2(self):
		self["Adapter"].setText(iNetwork.getFriendlyAdapterName(self.iface))
		self["Adapter"].setForegroundColorNum(2)
		self["Adaptertext"].setForegroundColorNum(1)
		self["AdapterInfo_Text"].setForegroundColorNum(1)
		self["AdapterInfo_OK"].show()
		self.steptimer = True
		self.nextStepTimer.start(3000)

	def doStep3(self):
		self["Networktext"].setForegroundColorNum(1)
		self["Network"].setText(_("Please wait..."))
		self.AccessPointInfo(self.iface)
		self["NetworkInfo_Text"].setForegroundColorNum(1)
		self.steptimer = True
		self.nextStepTimer.start(3000)

	def doStep4(self):
		self["Dhcptext"].setForegroundColorNum(1)
		if iNetwork.getAdapterAttribute(self.iface, 'dhcp') is True:
			self["Dhcp"].setForegroundColorNum(2)
			self["Dhcp"].setText(_("enabled"))
			self["DhcpInfo_Check"].setPixmapNum(0)
		else:
			self["Dhcp"].setForegroundColorNum(1)
			self["Dhcp"].setText(_("disabled"))
			self["DhcpInfo_Check"].setPixmapNum(1)
		self["DhcpInfo_Check"].show()
		self["DhcpInfo_Text"].setForegroundColorNum(1)
		self.steptimer = True
		self.nextStepTimer.start(3000)

	def doStep5(self):
		self["IPtext"].setForegroundColorNum(1)
		self["IP"].setText(_("Please wait..."))
		iNetwork.checkNetworkState(self.NetworkStatedataAvail)

	def doStep6(self):
		self.steptimer = False
		self.nextStepTimer.stop()
		self["DNStext"].setForegroundColorNum(1)
		self["DNS"].setText(_("Please wait..."))
		iNetwork.checkDNSLookup(self.DNSLookupdataAvail)

	def KeyGreen(self):
		self["shortcutsgreen"].setEnabled(False)
		self["shortcutsyellow"].setEnabled(True)
		self["updown_actions"].setEnabled(False)
		self["key_yellow"].setText("")
		self["key_green"].setText("")
		self.steptimer = True
		self.nextStepTimer.start(1000)

	def KeyGreenRestart(self):
		self.nextstep = 0
		self.layoutFinished()
		self["Adapter"].setText((""))
		self["Network"].setText((""))
		self["Dhcp"].setText((""))
		self["IP"].setText((""))
		self["DNS"].setText((""))
		self["AdapterInfo_Text"].setForegroundColorNum(0)
		self["NetworkInfo_Text"].setForegroundColorNum(0)
		self["DhcpInfo_Text"].setForegroundColorNum(0)
		self["IPInfo_Text"].setForegroundColorNum(0)
		self["DNSInfo_Text"].setForegroundColorNum(0)
		self["shortcutsgreen_restart"].setEnabled(False)
		self["shortcutsgreen"].setEnabled(False)
		self["shortcutsyellow"].setEnabled(True)
		self["updown_actions"].setEnabled(False)
		self["key_yellow"].setText("")
		self["key_green"].setText("")
		self.steptimer = True
		self.nextStepTimer.start(1000)

	def KeyOK(self):
		self["infoshortcuts"].setEnabled(True)
		self["shortcuts"].setEnabled(False)
		if self.activebutton == 1: # Adapter Check
			self["InfoText"].setText(_("This test detects your configured Wireless LAN-Adapter."))
			self["InfoTextBorder"].show()
			self["InfoText"].show()
			self["key_red"].setText(_("Back"))
		if self.activebutton == 2: #LAN Check
			self["InfoText"].setText(_("This test checks whether a network cable is connected to your Wireless LAN-Adapter."))
			self["InfoTextBorder"].show()
			self["InfoText"].show()
			self["key_red"].setText(_("Back"))
		if self.activebutton == 3: #DHCP Check
			self["InfoText"].setText(_("This test checks whether your Wireless LAN Adapter is set up for automatic IP Address configuration with DHCP.\nIf you get a \"disabled\" message:\n - then your Wireless LAN Adapter is configured for manual IP Setup\n- verify thay you have entered correct IP informations in the AdapterSetup dialog.\nIf you get an \"enabeld\" message:\n-verify that you have a configured and working DHCP Server in your network."))
			self["InfoTextBorder"].show()
			self["InfoText"].show()
			self["key_red"].setText(_("Back"))
		if self.activebutton == 4: # IP Check
			self["InfoText"].setText(_("This test checks whether a valid IP Address is found for your LAN Adapter.\nIf you get a \"unconfirmed\" message:\n- no valid IP Address was found\n- please check your DHCP, cabling and adapter setup"))
			self["InfoTextBorder"].show()
			self["InfoText"].show()
			self["key_red"].setText(_("Back"))
		if self.activebutton == 5: # DNS Check
			self["InfoText"].setText(_("This test checks for configured Nameservers.\nIf you get a \"unconfirmed\" message:\n- please check your DHCP, cabling and Adapter setup\n- if you configured your Nameservers manually please verify your entries in the \"Nameserver\" Configuration"))
			self["InfoTextBorder"].show()
			self["InfoText"].show()
			self["key_red"].setText(_("Back"))
		if self.activebutton == 6: # Edit Settings
			self.cleanup()
			self.session.open(WlanConfig, self.iface)
			self["shortcuts"].setEnabled(True)		
			self["infoshortcuts"].setEnabled(False)

	def KeyYellow(self):
		self.nextstep = 0
		self["shortcutsgreen_restart"].setEnabled(True)
		self["shortcutsgreen"].setEnabled(False)
		self["shortcutsyellow"].setEnabled(False)
		self["key_green"].setText(_("Restart test"))
		self["key_yellow"].setText("")
		self.steptimer = False
		self.nextStepTimer.stop()

	def layoutFinished(self):
		self.setTitle(_("Network test: ") + iNetwork.getFriendlyAdapterName(self.iface) )
		self["shortcutsyellow"].setEnabled(False)
		self["AdapterInfo_OK"].hide()
		self["NetworkInfo_Check"].hide()
		self["DhcpInfo_Check"].hide()
		self["IPInfo_Check"].hide()
		self["DNSInfo_Check"].hide()
		self["EditSettings_Text"].hide()
		self["EditSettingsButton"].hide()
		self["InfoText"].hide()
		self["InfoTextBorder"].hide()
		self["key_yellow"].setText("")

	def setLabels(self):
		self["Adaptertext"] = MultiColorLabel(_("LAN Adapter"))
		self["Adapter"] = MultiColorLabel()
		self["AdapterInfo"] = MultiPixmap()
		self["AdapterInfo_Text"] = MultiColorLabel(_("Show Info"))
		self["AdapterInfo_OK"] = Pixmap()
		
		if self.iface in iNetwork.wlan_interfaces:
			self["Networktext"] = MultiColorLabel(_("Wireless Network"))
		else:
			self["Networktext"] = MultiColorLabel(_("Local Network"))
		
		self["Network"] = MultiColorLabel()
		self["NetworkInfo"] = MultiPixmap()
		self["NetworkInfo_Text"] = MultiColorLabel(_("Show Info"))
		self["NetworkInfo_Check"] = MultiPixmap()
		
		self["Dhcptext"] = MultiColorLabel(_("DHCP"))
		self["Dhcp"] = MultiColorLabel()
		self["DhcpInfo"] = MultiPixmap()
		self["DhcpInfo_Text"] = MultiColorLabel(_("Show Info"))
		self["DhcpInfo_Check"] = MultiPixmap()
		
		self["IPtext"] = MultiColorLabel(_("IP Address"))
		self["IP"] = MultiColorLabel()
		self["IPInfo"] = MultiPixmap()
		self["IPInfo_Text"] = MultiColorLabel(_("Show Info"))
		self["IPInfo_Check"] = MultiPixmap()
		
		self["DNStext"] = MultiColorLabel(_("Nameserver"))
		self["DNS"] = MultiColorLabel()
		self["DNSInfo"] = MultiPixmap()
		self["DNSInfo_Text"] = MultiColorLabel(_("Show Info"))
		self["DNSInfo_Check"] = MultiPixmap()
		
		self["EditSettings_Text"] = MultiColorLabel(_("Edit settings"))
		self["EditSettingsButton"] = MultiPixmap()
		
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Start test"))
		self["key_yellow"] = StaticText(_("Stop test"))
		
		self["InfoTextBorder"] = Pixmap()
		self["InfoText"] = Label()

	def NetworkStatedataAvail(self,data):
		if data <= 2:
			self["IP"].setForegroundColorNum(2)
			self["IP"].setText(_("confirmed"))
			self["IPInfo_Check"].setPixmapNum(0)
		else:
			self["IP"].setForegroundColorNum(1)
			self["IP"].setText(_("unconfirmed"))
			self["IPInfo_Check"].setPixmapNum(1)
		self["IPInfo_Check"].show()
		self["IPInfo_Text"].setForegroundColorNum(1)		
		self.steptimer = True
		self.nextStepTimer.start(3000)		
		
	def DNSLookupdataAvail(self,data):
		if data <= 2:
			self["DNS"].setForegroundColorNum(2)
			self["DNS"].setText(_("confirmed"))
			self["DNSInfo_Check"].setPixmapNum(0)
		else:
			self["DNS"].setForegroundColorNum(1)
			self["DNS"].setText(_("unconfirmed"))
			self["DNSInfo_Check"].setPixmapNum(1)
		self["DNSInfo_Check"].show()
		self["DNSInfo_Text"].setForegroundColorNum(1)
		self["EditSettings_Text"].show()
		self["EditSettingsButton"].setPixmapNum(1)
		self["EditSettings_Text"].setForegroundColorNum(2) # active
		self["EditSettingsButton"].show()
		self["key_yellow"].setText("")
		self["key_green"].setText(_("Restart test"))
		self["shortcutsgreen"].setEnabled(False)
		self["shortcutsgreen_restart"].setEnabled(True)
		self["shortcutsyellow"].setEnabled(False)
		self["updown_actions"].setEnabled(True)
		self.activebutton = 6

	def getInfoCB(self,status):
		if status is not None:
			if status.startswith("No Connection") or status.startswith("Not-Associated") or status == False:
				self["Network"].setForegroundColorNum(1)
				self["Network"].setText(_("disconnected"))
				self["NetworkInfo_Check"].setPixmapNum(1)
				self["NetworkInfo_Check"].show()
			else:
				self["Network"].setForegroundColorNum(2)
				self["Network"].setText(_("connected"))
				self["NetworkInfo_Check"].setPixmapNum(0)
				self["NetworkInfo_Check"].show()
						
	def cleanup(self):
		iNetwork.stopLinkStateConsole()
		iNetwork.stopPingConsole()
		iNetwork.stopDNSConsole()

	def AccessPointInfo(self,iface):
		cmd = "iwconfig %s"%iface
		self.iwconfigConsole = Console()
		self.iwconfigConsole.ePopen(cmd,self.readAP,self.getInfoCB)

	def readAP(self,result,retval,extra_args):
		(callback) = extra_args
		self.apState = None
		if self.iwconfigConsole is not None:
			if retval == 0:
				self.iwconfigConsole = None
				for content in result.splitlines():
					if 'Access Point' in content:
						self.apState = content.strip().split('Access Point: ')[1]
						callback(self.apState)
						return
		callback(self.apState)
		
class Wlanstatus(Screen):
	skin =  """
		<screen position="center,center" size="510,400" title="Wireless Network Status..." >
			<widget source="status" render="Label" position="5,15" size="500,350" font="Regular;18" zPosition="1" />

			<ePixmap pixmap="skin_default/buttons/red.png" position="185,360" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="185,360" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="#ffffff" transparent="1" />
		</screen>
		"""
	def __init__(self, session,iface):
		Screen.__init__(self,session)
		self.session = session
		self.iface = iface
		self["status"] = StaticText(_("Wait a moment..."))
		self["key_red"] = StaticText(_("Close"))
		self["OkCancelActions"] = ActionMap(["ShortcutActions", "SetupActions" ],
		{
			"ok": self.ok,
			"cancel": self.close,
			"red": self.close,
		}, -2)
		self.readstatus()
		self.onClose.append(self.cleanup)

	def readstatus(self):
		self.wlanstatus = Console()
		cmd1 = "iwconfig "+self.iface
		self.wlanstatus.ePopen(cmd1, self.iwconfigfinnished,self.statusdisplay)

	def iwconfigfinnished(self, result, retval,extra_args):
		try:
			(statecallback) = extra_args
			if self.wlanstatus is not None:
				if retval == 0:
					statecallback(result)
				else:
					statecallback(0)
		except:
			self.close()


	def statusdisplay(self,data):
		if data == 0:
			self["status"].setText(_("No information..."))
		else:
			self["status"].setText(data)

	def ok(self):
		pass

	def cleanup(self):
		self.stopWlanStatusConsole()

	def stopWlanStatusConsole(self):
		if self.wlanstatus is not None:
			if len(self.wlanstatus.appContainers):
				for name in self.wlanstatus.appContainers.keys():
					self.wlanstatus.kill(name)

def openconfig(session, **kwargs):
	session.open(WlanSelection)

def selSetup(menuid, **kwargs):
	list=[]
	if menuid != "system":
		return [ ]
	else:
		for x in iNetwork.getInstalledAdapters():
			if x.startswith('eth'):
				continue
			list.append(x)
		if len(list):
			return [(_("Wireless LAN Setup"), openconfig, "wlansetup_config", 80)]
		else:
			return [ ]
	return [ ]

def Plugins(**kwargs):
	return 	PluginDescriptor(name=_("Wireless LAN Setup"), description="Wireless LAN Setup", where = PluginDescriptor.WHERE_MENU, fnc=selSetup)
