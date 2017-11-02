from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen
from Components.config import config, getConfigListEntry, ConfigSubsection, ConfigSlider
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.Label import Label
from Plugins.Plugin import PluginDescriptor
from Screens.MessageBox import MessageBox
from Tools.Directories import fileExists
from enigma import eTimer
import fcntl

config.plugins.brightnesssetup = ConfigSubsection()
config.plugins.brightnesssetup.brightness = ConfigSlider(default = 1, increment = 1, limits = (0,15))
config.plugins.brightnesssetup.brightnessdeepstandby = ConfigSlider(default = 5, increment = 1, limits = (0,15))
config.plugins.brightnesssetup.blinkingtime = ConfigSlider(default = 5, increment = 1, limits = (0,15))

class LEDOption:
	BRIGHTNESS = 0
	DEEPSTANDBY = 1
	BLINKINGTIME = 2

class LEDSetup:
	LED_IOCTL_BRIGHTNESS_NORMAL = 0X10
	LED_IOCTL_BRIGHTNESS_DEEPSTANDBY = 0X11
	LED_IOCTL_BLINKING_TIME = 0X12
	LED_IOCTL_SET_DEFAULT = 0X13

	def __init__(self):
		self.led_fd = open("/dev/dbox/oled0",'rw')
		self.initLEDSetup()

	def initLEDSetup(self):
		brightness = int(config.plugins.brightnesssetup.brightness.value)
		brightnessstandby = int(config.plugins.brightnesssetup.brightnessdeepstandby.value)
		blinkingtime = int(config.plugins.brightnesssetup.blinkingtime.value)
		self.setLEDDefault(brightness, brightnessstandby, blinkingtime)

	def setLEDDefault(self, brightness = 1, brightnessstandby = 5, blinkingtime = 5):
		default_value = (blinkingtime<<16) + (brightnessstandby<<8) + brightness
		fcntl.ioctl(self.led_fd , self.LED_IOCTL_SET_DEFAULT, default_value)

	def setLED(self, value, option):
		if option == LEDOption.BRIGHTNESS:
			cmd = self.LED_IOCTL_BRIGHTNESS_NORMAL
		elif option == LEDOption.DEEPSTANDBY:
			cmd = self.LED_IOCTL_BRIGHTNESS_DEEPSTANDBY
		elif option == LEDOption.BLINKINGTIME:
			cmd = self.LED_IOCTL_BLINKING_TIME
		else:
			return
		fcntl.ioctl(self.led_fd, cmd, value)

	def __del__(self):
		self.led_fd.close()

ledsetup = LEDSetup()

class LEDBrightnessSetup(Screen,ConfigListScreen):
	skin = 	"""
		<screen position="center,center" size="560,300" title="LED Brightness Setup">
			<ePixmap pixmap="skin_default/buttons/red.png" position="40,10" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="210,10" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="380,10" size="140,40" alphatest="on" />

			<widget source="key_red" render="Label" position="40,10" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_green" render="Label" position="210,10" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_yellow" render="Label" position="380,10" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" foregroundColor="#ffffff" transparent="1" />

			<widget name="config" zPosition="2" position="5,70" size="550,200" scrollbarMode="showOnDemand" transparent="1"/>
			<widget name="current_entry" position="130,240" size="300,30" font="Regular;18" halign="center" valign="center"/>
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
			"yellow": self.keyDefault,
		}, -2)
		self.list = []
		ConfigListScreen.__init__(self, self.list,session = self.session)
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Ok"))
		self["key_yellow"] = StaticText(_("Defalut"))
		self["current_entry"]=Label("")
		self.createSetup()
		self.onLayoutFinish.append(self.checkModel)
		self.checkModelTimer = eTimer()
		self.checkModelTimer.callback.append(self.invalidmodel)
		if not self.displayText in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.displayText)

	def displayText(self):
		if self["config"].getCurrent() == self.brightness:
			self["current_entry"].setText("Touch LED Brightness at Normal state")
		elif self["config"].getCurrent() == self.brightness_deepstandby:
			self["current_entry"].setText("Touch LED Brightness at Deep Standby")
		elif self["config"].getCurrent() == self.blinkingtime:
			self["current_entry"].setText("Touch LED Blinking time")
		self.setCurrentValue()

	def getModel(self):
		if fileExists("/proc/stb/info/vumodel"):
			vumodel = open("/proc/stb/info/vumodel")
			info=vumodel.read().strip()
			vumodel.close()
			if info == "ultimo":
				return True
			else:
				return False
		else:
			return False

	def checkModel(self):
		if not self.getModel():
			self.checkModelTimer.start(100,True)

	def invalidmodel(self):
			self.session.openWithCallback(self.close, MessageBox, _("This Plugin only support for ULTIMO"), MessageBox.TYPE_ERROR, timeout = 30)

	def createSetup(self):
		self.list = []
		self.brightness = getConfigListEntry(_("Normal state"), config.plugins.brightnesssetup.brightness)
		self.brightness_deepstandby = getConfigListEntry(_("Deep Standby"), config.plugins.brightnesssetup.brightnessdeepstandby)
		self.blinkingtime = getConfigListEntry(_("Blinking time"), config.plugins.brightnesssetup.blinkingtime)
		self.list.append( self.brightness )
		self.list.append( self.brightness_deepstandby )
		self.list.append( self.blinkingtime )
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def setCurrentValue(self):
		if self["config"].getCurrent() == self.blinkingtime:
			ledsetup.setLED(1 ,LEDOption.BRIGHTNESS)
			ledsetup.setLED(self["config"].getCurrent()[1].value ,LEDOption.BLINKINGTIME)
		else:
			ledsetup.setLED(self["config"].getCurrent()[1].value ,LEDOption.BRIGHTNESS)

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.setCurrentValue()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.setCurrentValue()

	def saveLEDSetup(self):
		brightness = config.plugins.brightnesssetup.brightness.value
		brightnessstandby = config.plugins.brightnesssetup.brightnessdeepstandby.value
		blinkingtime = config.plugins.brightnesssetup.blinkingtime.value
		ledsetup.setLED(brightness ,LEDOption.BRIGHTNESS)
		ledsetup.setLED(brightnessstandby ,LEDOption.DEEPSTANDBY)
		ledsetup.setLED(blinkingtime ,LEDOption.BLINKINGTIME)

	def keySave(self):
		if self["config"].isChanged():
			self.saveLEDSetup()
		ConfigListScreen.keySave(self)

	def keyDefault(self):
		config.plugins.brightnesssetup.brightness.setValue(1)
		config.plugins.brightnesssetup.brightnessdeepstandby.setValue(5)
		config.plugins.brightnesssetup.blinkingtime.setValue(5)
		for entry in self["config"].getList():
			self["config"].l.invalidateEntry(self["config"].getList().index(entry))

		if self["config"].getCurrent() == self.blinkingtime:
			self.setCurrentValue()
		else:
			ledsetup.setLED(5 ,LEDOption.BLINKINGTIME)
			ledsetup.setLED(self["config"].getCurrent()[1].value ,LEDOption.BRIGHTNESS)

	def cancelConfirm(self, result):
		if not result:
			return
		for x in self["config"].list:
			x[1].cancel()
		self.saveLEDSetup()
		self.close()

def main(session, **kwargs):
	session.open(LEDBrightnessSetup)

def Plugins(**kwargs):
	return [PluginDescriptor(name=_("LED Brightness Setup"), description="Setup LED brightness and blink interval", where = PluginDescriptor.WHERE_PLUGINMENU, needsRestart = False, fnc=main)]

