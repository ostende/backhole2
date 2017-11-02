import struct
from config import config, ConfigSelection, ConfigYesNo, ConfigSubsection, ConfigText
from enigma import eHdmiCEC, eTimer
from Screens.Standby import inStandby
import Screens.Standby
from Tools import Notifications
import time
from os import system
from Tools.Directories import fileExists


class HdmiCec:
	def __init__(self):
		config.hdmicec = ConfigSubsection()
		config.hdmicec.enabled = ConfigYesNo(default = False)
		config.hdmicec.logenabledserial = ConfigYesNo(default = False)
		config.hdmicec.logenabledfile = ConfigYesNo(default = False)
		config.hdmicec.tvstandby = ConfigYesNo(default = False)
		config.hdmicec.tvwakeup = ConfigYesNo(default = False)
		config.hdmicec.boxstandby = ConfigYesNo(default = False)
		config.hdmicec.enabletvrc = ConfigYesNo(default = True)
		config.hdmicec.active_source_reply = ConfigYesNo(default = True)
		config.hdmicec.standby_message = ConfigSelection(
			choices = {
			"standby,inactive": _("TV standby"),
			"standby,avpwroff,inactive,": _("TV + A/V standby"),
			"inactive": _("Source inactive"),
			"nothing": _("Nothing"),
			},
			default = "standby,inactive")
		config.hdmicec.deepstandby_message = ConfigSelection(
			choices = {
			"standby,inactive": _("TV standby"),
			"standby,avdeeppwroff,inactive": _("TV + A/V standby"),
			"inactive": _("Source inactive"),
			"nothing": _("Nothing"),
			},
			default = "standby,inactive")
		config.hdmicec.wakeup_message = ConfigSelection(
			choices = {
			"wakeup,active,activevu": _("TV wakeup"),
			"wakeup,avpwron,active,activevu": _("TV + A/V wakeup"),
			"active": _("Source active"),
			"nothing": _("Nothing"),
			},
			default = "wakeup,active,activevu")
		config.hdmicec.vustandby_message = ConfigSelection(
			choices = {
			"vustandby": _("VU standby"),
			"vudeepstandby": _("VU DeepStandby"),
			"vunothing": _("Nothing"),
			},
			default = "vustandby")
		config.hdmicec.vuwakeup_message = ConfigSelection(
			choices = {
			"vuwakeup": _("VU wakeup"),
			"vunothing": _("Nothing"),
			},
			default = "vuwakeup")
		config.hdmicec.tvinput = ConfigSelection(default = "1",
			choices = [
			("1", _("HDMI 1")),
			("2", _("HDMI 2")),
			("3", _("HDMI 3")),
			("4", _("HDMI 4")),
			("5", _("HDMI 5"))])
		config.hdmicec.avinput = ConfigSelection(default ="0",
			choices = [
			("0", _("no A/V Receiver")),
			("1", _("HDMI 1")),
			("2", _("HDMI 2")),
			("3", _("HDMI 3")),
			("4", _("HDMI 4")),
			("5", _("HDMI 5"))])
		config.hdmicec.devicename = ConfigText(default = self.getDeviceName(), visible_width = 50, fixed_size = False)
		config.misc.standbyCounter.addNotifier(self.enterStandby, initial_call = False)
		config.misc.DeepStandbyOn.addNotifier(self.enterDeepStandby, initial_call = False)
		self.leaveDeepStandby()

	def getDeviceName(self):
		deviceList = {
			"duo": "VU+ Duo",
			"solo": "VU+ Solo",
			"uno": "VU+ Uno",
			"ultimo": "VU+ Ultimo",
			"solo2": "VU+ Solo2",
			"duo2": "VU+ Duo2",
			"solose": "VU+ SoloSE",
			"zero": "VU+ Zero",
		}
		if fileExists("/proc/stb/info/vumodel"):
			vumodel = open("/proc/stb/info/vumodel")
			info=vumodel.read().strip()
			vumodel.close()
			return deviceList.setdefault(info, "VU+")
		else:
			return "VU+"

	def sendMessages(self, messages):
		for message in messages.split(','):
			cmd = None
			logcmd = None
			addressvaluebroadcast = int("0F",16)
			addressvalue = int("0",16)
			addressvalueav = int("5",16)
			wakeupmessage = int("04",16)
			standbymessage=int("36",16)
			activesourcemessage=int("82",16)
			inactivesourcemessage=int("9D",16)
			sendkeymessage = int("44",16)
			sendkeypwronmessage = int("6D",16)
			sendkeypwroffmessage = int("6C",16)
			activevumessage=int("85",16)
			physaddress1 = int("0x" + str(config.hdmicec.tvinput.value) + str(config.hdmicec.avinput.value),16)
			physaddress2 = int("0x00",16)

			if message == "wakeup":
				cmd = struct.pack('B', wakeupmessage)
				logcmd = "[HDMI-CEC] ** WakeUpMessage ** send message: %x to address %x" % (wakeupmessage, addressvalue)
			elif message == "active":
				addressvalue = addressvaluebroadcast
				cmd = struct.pack('BBB', activesourcemessage,physaddress1,physaddress2)
				logcmd = "[HDMI-CEC] ** ActiveSourceMessage ** send message: %x:%x:%x to address %x" % (activesourcemessage,physaddress1,physaddress2,addressvalue)
			elif message == "standby":
				cmd = struct.pack('B', standbymessage)
				logcmd = "[HDMI-CEC] ** StandByMessage ** send message: %x to address %x" % (standbymessage, addressvalue)
			elif message == "inactive":
				addressvalue = addressvaluebroadcast
				cmd = struct.pack('BBB', inactivesourcemessage,physaddress1,physaddress2)
				logcmd = "[HDMI-CEC] ** InActiveSourceMessage ** send message: %x:%x:%x to address %x" % (inactivesourcemessage,physaddress1,physaddress2,addressvalue)
			elif message == "avpwron":
				cmd = struct.pack('BB', sendkeymessage,sendkeypwronmessage)
				addressvalue = addressvalueav
				logcmd = "[HDMI-CEC] ** Power on A/V ** send message: %x:%x to address %x" % (sendkeymessage, sendkeypwronmessage, addressvalue)
			elif message == "avdeeppwroff":
				cmd = struct.pack('BB',sendkeymessage,sendkeypwroffmessage)
				addressvalue = addressvalueav
				logcmd = "[HDMI-CEC] ** Standby A/V (Deepstandby)** send message: %x:%x to address %x" % (sendkeymessage,sendkeypwroffmessage, addressvalue)
			elif message == "avpwroff":
				addressvalue = addressvalueav
				cmd = struct.pack('BB',sendkeymessage,sendkeypwroffmessage)
				logcmd = "[HDMI-CEC] ** Standby A/V ** send message: %x:%x to address %x" % (sendkeymessage,sendkeypwroffmessage, addressvalue)
			elif message == "activevu":
				addressvalue = addressvaluebroadcast
				cmd = struct.pack('B', activevumessage)
				logcmd = "[HDMI-CEC] ** Active VU Message ** send message: %x to address %x" % (activevumessage,addressvalue)
			if cmd:
				eHdmiCEC.getInstance().sendMessage(addressvalue, len(cmd), str(cmd))
				time.sleep(1)
			if logcmd:
				if config.hdmicec.logenabledserial.value:
					print logcmd
					if config.hdmicec.logenabledfile.value:
						filelog = "echo %s >> /tmp/hdmicec.log" % (logcmd)
						system(filelog)


	def leaveStandby(self):
		if config.hdmicec.enabled.value is True:
			self.sendMessages(config.hdmicec.wakeup_message.value)

	def enterStandby(self, configElement):
		from Screens.Standby import inStandby
		inStandby.onClose.append(self.leaveStandby)
		if config.hdmicec.enabled.value is True:
			self.sendMessages(config.hdmicec.standby_message.value)

	def enterDeepStandby(self,configElement):
		if config.hdmicec.enabled.value is True:
			self.sendMessages(config.hdmicec.deepstandby_message.value)

	def leaveDeepStandby(self):
		if config.hdmicec.enabled.value is True:
			self.sendMessages(config.hdmicec.wakeup_message.value)
			
## not used
	def activeSource(self):
		if config.hdmicec.enabled.value is True:
			physadress1 = "0x" + str(config.hdmicec.tvinput.value) + str(config.hdmicec.avinput.value)
			physadress2 = "0x00"
			cecmessage = int('0x82',16)
			address = int('0x0F',16)
			valuethree = int(physadress1,16)
			valuefour = int(physadress2,16)
			cmd = struct.pack('BBB',cecmessage,valuethree,valuefour)
			eHdmiCEC.getInstance().sendMessage(address, len(cmd), str(cmd))
			if config.hdmicec.enabletvrc.value:
					cecmessage = int('0x8E',16)
					address = int('0',16)
					valuethree = int('0',16)
					cmd = struct.pack('BB',cecmessage,valuethree)
					eHdmiCEC.getInstance().sendMessage(address, len(cmd), str(cmd))

hdmi_cec = HdmiCec()
