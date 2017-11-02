from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen
from Components.config import config, getConfigListEntry, ConfigSubsection, ConfigSelection, ConfigInteger
from Components.ActionMap import ActionMap
from Screens.MessageBox import MessageBox
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Tools.Directories import fileExists
from enigma import eTimer, quitMainloop

def getModel():
	ret = None
	if fileExists("/proc/stb/info/vumodel"):
		vumodel = open("/proc/stb/info/vumodel")
		info=vumodel.read().strip()
		vumodel.close()
		ret = info

	return ret

def getRcuDefaultType():
	if getModel() in ["ultimo4k"]:
		return "new"
	return "legacy"

config.plugins.remotecontrolcode = ConfigSubsection()
config.plugins.remotecontrolcode.systemcode = ConfigSelection(default = "2", choices = 
	[ ("1", "1 "), ("2", "2 "), ("3", "3 "), ("4", "4 ") ] )
config.plugins.remotecontrolcode.replytimeout = ConfigInteger(default = 30, limits = (15,9999))
config.plugins.remotecontrolcode.rcuType = ConfigSelection(default = getRcuDefaultType(), choices = 
	[ ("legacy", "Legacy Vu+ Universal RCU"), ("new", "New Vu+ Bluetooth RCU") ] )

class RemoteControlCodeInit:
	def __init__(self):
		self.setSystemCode(int(config.plugins.remotecontrolcode.systemcode.value))

	def setSystemCode(self, type = 2):
		if not fileExists("/proc/stb/fp/remote_code"):
			return -1
		print "<RemoteControlCode> Write Remote Control Code : %d" % type
		f = open("/proc/stb/fp/remote_code", "w")
		f.write("%d" % type)
		f.close()
		return 0

	def checkModelSupport(self):
		ret = None
		model = getModel()
		if model not in ["duo", "solo"]:
			ret = True

		return ret

class RemoteControlCode(Screen,ConfigListScreen,RemoteControlCodeInit):
	skin = 	"""
		<screen position="center,center" size="400,250" title="Remote Control System Code Setting" >
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
		self.replytext_1 ="The remote control code will be reset to previous setting, set your R/C's code and select 'keep'"
		self.replytext_2 ="\n\n<Code set manual>"
		self.replytext_2 +="\n1. Press Digit 2 and Digit 7 simultaneously for 3 seconds. After 3 seconds LED turns on. "
		self.replytext_2 +="\n2. Press the <HELP> key. LED is blinked and turns on."
		self.replytext_2 +="\n3. Enter a 4 digit code(ex. code 2 is '0002')"

		self.replytext_newrcu_2 ="\n\n<Code set manual>"
		self.replytext_newrcu_2 +="\n1. Press <OK> and <STB> simultaneously for 3 seconds. After 3 seconds LED turns on. "
		self.replytext_newrcu_2 +="\n2. Enter a 5 digit code(ex. code 2 is '00002')"
		self.replytext_newrcu_2 +="\n3. Press the <OK> key. LED is blinked and turns on."

		self.createSetup()
		self.onLayoutFinish.append(self.checkModel)
		self.checkModelTimer = eTimer()
		self.checkModelTimer.callback.append(self.invalidmodel)

	def checkModel(self):
		if not self.checkModelSupport():
			self.checkModelTimer.start(1000,True)

	def invalidmodel(self):
			self.session.openWithCallback(self.close, MessageBox, _("This Plugin doesn't support on SOLO/DUO"), MessageBox.TYPE_ERROR)

	def createSetup(self):
		self.list = []
		self.rcuTypeEntry = getConfigListEntry(_("Remote Control Type"), config.plugins.remotecontrolcode.rcuType)
		self.rcsctype = getConfigListEntry(_("Remote Control System Code"), config.plugins.remotecontrolcode.systemcode)
		self.replytimeout = getConfigListEntry(_("Reply timeout"), config.plugins.remotecontrolcode.replytimeout)
		self.list.append( self.rcuTypeEntry )
		self.list.append( self.rcsctype )
		self.list.append( self.replytimeout )
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def keySave(self):
		print "<RemoteControlCode> Selected System Code : ",config.plugins.remotecontrolcode.systemcode.value
		ret = self.setSystemCode(int(config.plugins.remotecontrolcode.systemcode.value))
		if ret == -1:
			self.restoreCode()
			self.session.openWithCallback(self.close, MessageBox, _("FILE NOT EXIST : /proc/stb/fp/remote_code"), MessageBox.TYPE_ERROR)
		else:
			timeout = config.plugins.remotecontrolcode.replytimeout.value
			text1 = self.replytext_1
			text2 = self.replytext_2
			if config.plugins.remotecontrolcode.rcuType.value == "new":
				text2 = self.replytext_newrcu_2

			self.session.openWithCallback(self.MessageBoxConfirmCodeCallback, MessageBoxConfirmCode, text1, text2, MessageBox.TYPE_YESNO, timeout = timeout, default = False)

	def restoreCode(self):
		for x in self["config"].list:
			x[1].cancel()

	def MessageBoxConfirmCodeCallback(self,ret):
		if ret:
			self.saveAll()
			self.session.openWithCallback(self.restartCallback, MessageBox, _("GUI restart now, press 'OK' button."), MessageBox.TYPE_INFO)
		else:
			self.restoreCode()
			self.setSystemCode(int(config.plugins.remotecontrolcode.systemcode.value))

	def restartCallback(self,result):
		quitMainloop(3)

class MessageBoxConfirmCode(MessageBox):
	skin = 	"""
		<screen position="center,center" size="620,10" title="Message">
			<widget name="text" position="65,8" size="420,0" font="Regular;20" />
			<widget name="ErrorPixmap" pixmap="skin_default/icons/input_error.png" position="5,5" size="53,53" alphatest="blend" />
			<widget name="QuestionPixmap" pixmap="skin_default/icons/input_question.png" position="5,5" size="53,53" alphatest="blend" />
			<widget name="InfoPixmap" pixmap="skin_default/icons/input_info.png" position="5,5" size="53,53" alphatest="blend" />
			<widget name="list" position="100,100" size="380,375" transparent="1" />
			<applet type="onLayoutFinish">
# this should be factored out into some helper code, but currently demonstrates applets.
from enigma import eSize, ePoint

orgwidth  = self.instance.size().width()
orgheight = self.instance.size().height()
orgpos    = self.instance.position()
textsize  = self[&quot;text&quot;].getSize()

# y size still must be fixed in font stuff...
textsize = (textsize[0] + 50, textsize[1] + 50)
offset = 0
if self.type == self.TYPE_YESNO:
	offset = 60
wsizex = textsize[0] + 60
wsizey = textsize[1] + offset
if (280 &gt; wsizex):
	wsizex = 280
wsize = (wsizex, wsizey)

# resize
self.instance.resize(eSize(*wsize))

# resize label
self[&quot;text&quot;].instance.resize(eSize(*textsize))

# move list
listsize = (wsizex, 50)
self[&quot;list&quot;].instance.move(ePoint(0, textsize[1]))
self[&quot;list&quot;].instance.resize(eSize(*listsize))

# center window
newwidth = wsize[0]
newheight = wsize[1]
window_posx = orgpos.x() + (orgwidth - newwidth)/2
window_posy = orgpos.y() + (orgheight - newheight)/2
if (150 &gt; window_posy):
        window_posy = 150
self.instance.move(ePoint(window_posx, window_posy))
			</applet>
		</screen>
		"""

	def __init__(self, session, replytext_1="", replytext_2="", type = MessageBox.TYPE_YESNO, timeout = -1, close_on_any_key = False, default = True, enable_input = True, msgBoxID = None):
		self.replytext_1 = replytext_1
		self.replytext_2 = replytext_2
		MessageBox.__init__(self,session,self.replytext_1 + "\n" + self.replytext_2,type,timeout,close_on_any_key,default,enable_input,msgBoxID)
		if type == MessageBox.TYPE_YESNO:
			self.list = [ (_("Keep"), 0), (_("Restore"), 1) ]
			self["list"].setList(self.list)

	def timerTick(self):
		if self.execing:
			self.timeout -= 1
			self["text"].setText(self.replytext_1 + " in %d seconds."%self.timeout + self.replytext_2)
			if self.timeout == 0:
				self.timer.stop()
				self.timerRunning = False
				self.timeoutCallback()

	def move(self, direction):
		if self.close_on_any_key:
			self.close(True)
		self["list"].instance.moveSelection(direction)
		if self.list:
			self["selectedChoice"].setText(self["list"].getCurrent()[0])
#		self.stopTimer()

	def timeoutCallback(self):
		self.close(False)

def main(session, **kwargs):
	session.open(RemoteControlCode)

def Plugins(**kwargs):
	return [PluginDescriptor(name=_("RemoteControlCode"), description="setup Remote Control System Code Type", where = PluginDescriptor.WHERE_PLUGINMENU, needsRestart = True, fnc=main)]

remotecontrolcodeinit = RemoteControlCodeInit()
