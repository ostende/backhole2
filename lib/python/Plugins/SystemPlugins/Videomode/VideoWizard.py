from Screens.Wizard import WizardSummary
from Screens.WizardLanguage import WizardLanguage
from Screens.Rc import Rc
from Components.Pixmap import Pixmap
from Components.config import config, configfile, ConfigBoolean
from Tools.Directories import resolveFilename, SCOPE_PLUGINS

from VideoHardware import video_hw

config.misc.showtestcard = ConfigBoolean(default = False)

class VideoWizard(WizardLanguage, Rc):
	skin = """
		<screen name="VideoWizard" position="0,0" size="720,576" title="Welcome..." flags="wfNoBorder" >
			<widget name="text" position="153,50" size="340,270" font="Regular;23" />
			<widget source="list" render="Listbox" position="50,300" size="440,200" scrollbarMode="showOnDemand" >
				<convert type="StringList" />
			</widget>
			<widget name="config" position="50,300" size="440,200" scrollbarMode="showOnDemand" zPosition="1" transparent="1" />
			<ePixmap pixmap="skin_default/buttons/button_red.png" position="40,225" size="15,16" alphatest="on" />
			<widget name="languagetext" position="55,225" size="95,30" font="Regular;18" />
			<widget name="wizard" pixmap="skin_default/wizard.png" position="40,50" zPosition="10" size="110,174" alphatest="on"/>
			<widget name="rc" pixmaps="skin_default/rc.png,skin_default/rcold.png" position="500,50" zPosition="10" size="154,500" alphatest="on"/>
			<widget name="arrowdown" pixmap="skin_default/arrowdown.png" position="-100,-100" zPosition="11" size="37,70" alphatest="on"/>
			<widget name="arrowdown2" pixmap="skin_default/arrowdown.png" position="-100,-100" zPosition="11" size="37,70" alphatest="on"/>
			<widget name="arrowup" pixmap="skin_default/arrowup.png" position="-100,-100" zPosition="11" size="37,70" alphatest="on"/>
			<widget name="arrowup2" pixmap="skin_default/arrowup.png" position="-100,-100" zPosition="11" size="37,70" alphatest="on"/>
		</screen>
	"""

	def __init__(self, session):
		self.xmlfile = resolveFilename(SCOPE_PLUGINS, "SystemPlugins/Videomode/videowizard.xml")
		self.video_cfg = video_hw

		WizardLanguage.__init__(self, session)
		Rc.__init__(self)

		self["wizard"] = Pixmap()
		self["portpic"] = Pixmap()

		self.port = None
		self.mode = None
		self.rate = None
	
	def createSummary(self):
		from Screens.Wizard import WizardSummary
		return WizardSummary 
	
	def markDone(self):
		config.misc.videowizardenabled.setValue(False)
		config.misc.videowizardenabled.save()
		configfile.save()
	
	def portList(self):
		hw_type = self.video_cfg.getDeviceName()
		list = [ ]

		for port in self.video_cfg.getPortList():
			if self.video_cfg.isPortUsed(port):
				desc = port
				if desc == "DVI" and self.video_cfg.isHDMIAvailable(hw_type):
					desc = "HDMI"
				
				if port != "DVI-PC":
					list.append( (desc, port))

		list.sort(key = lambda x: x[0])
		return list

	def portSelectionMade(self, index):
		self.port = index
		self.video_cfg.setVideomode(self.port, self.mode, self.rate)
	
	def portSelectionMoved(self):
		self.video_cfg.setVideomode(self.selection, self.mode, self.rate)

	def modeList(self):
		list = [ ]
		for mode in self.video_cfg.getModeList(self.port):
			list.append( (mode[0], mode[0]))
		
		return list

	def modeSelectionMade(self, index):
		self.mode = index
		self.modeSelect(self.mode)
	
	def modeSelectionMoved(self):
		self.modeSelect(self.selection)
	
	def modeSelect(self, mode):
		if self.port == "DVI" and self.video_cfg.isWidescreenMode(mode):
			self.rate = "multi"
		else:
			self.rate = None
		self.video_cfg.setVideomode(self.port, mode, self.rate)

	def rateList(self):
		list = [ ]
		for rate in self.video_cfg.getRateList(self.port, self.mode):
			list.append( (rate, rate))
		
		return list

	def rateSelectionMade(self, index):
		self.rate = index
		self.video_cfg.setVideomode(self.port, self.mode, self.rate)
	
	def rateSelectionMoved(self):
		self.video_cfg.setVideomode(self.port, self.mode, self.selection)

	def showVideoTune(self, selection = None):
		if selection is None:
			selection = self.selection

		if selection == "yes":
			config.misc.showtestcard.value = True
		else:
			config.misc.showtestcard.value = False

