from Plugins.Plugin import PluginDescriptor

from Screens.Screen import Screen
from Screens.ServiceScan import ServiceScan
from Screens.MessageBox import MessageBox
from Screens.DefaultWizard import DefaultWizard

from Components.Label import Label
from Components.TuneTest import Tuner
from Components.ConfigList import ConfigListScreen
from Components.Sources.StaticText import StaticText
from Components.ActionMap import NumberActionMap, ActionMap
from Components.NimManager import nimmanager, getConfigSatlist
from Components.config import config, ConfigSubsection, ConfigSelection, ConfigYesNo, ConfigInteger, getConfigListEntry, ConfigSlider, ConfigEnableDisable

from Tools.HardwareInfo import HardwareInfo
from Tools.Directories import resolveFilename, SCOPE_DEFAULTPARTITIONMOUNTDIR, SCOPE_DEFAULTDIR, SCOPE_DEFAULTPARTITION

from enigma import eTimer, eDVBFrontendParametersSatellite, eComponentScan, eDVBSatelliteEquipmentControl, eDVBFrontendParametersTerrestrial, eDVBFrontendParametersCable, eConsoleAppContainer, eDVBResourceManager, getDesktop

_modelName = file('/proc/stb/info/vumodel').read().strip()
_supportNimType = { 'AVL1208':'', 'AVL6222':'6222_', 'AVL6211':'6211_', 'BCM7356':'bcm7346_'}

class Blindscan(ConfigListScreen, Screen):
	skin = 	"""
		<screen position="center,center" size="560,390" title="Blindscan">
			<ePixmap pixmap="skin_default/buttons/red.png" position="40,10" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="210,10" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="380,10" size="140,40" alphatest="on" />

			<widget source="key_red" render="Label" position="40,10" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="#ffffff" transparent="1"/>
			<widget source="key_green" render="Label" position="210,10" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="#ffffff" transparent="1"/>
			<widget source="key_blue" render="Label" position="380,10" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" foregroundColor="#ffffff" transparent="1"/>

			<widget name="config" position="5,70" size="550,280" scrollbarMode="showOnDemand" />
			<widget name="introduction" position="0,365" size="560,20" font="Regular;20" halign="center" />
		</screen>
		"""

	def __init__(self, session): 
		Screen.__init__(self, session)

		self.current_play_service = self.session.nav.getCurrentlyPlayingServiceReference()

		# update sat list
		self.satList = []
		for slot in nimmanager.nim_slots:
			if slot.isCompatible("DVB-S"):
				self.satList.append(nimmanager.getSatListForNim(slot.slot))
			else:
				self.satList.append(None)

		# make config
		self.createConfig()

		self.list = []
		self.status = ""

		ConfigListScreen.__init__(self, self.list)
		if self.scan_nims.value != None and self.scan_nims.value != "" :
			self["actions"] = ActionMap(["OkCancelActions", "ShortcutActions", "WizardActions", "ColorActions", "SetupActions", ],
			{
				"red": self.keyCancel,
				"green": self.keyGo,
				"blue":self.keyGoAll,
				"ok": self.keyGo,
				"cancel": self.keyCancel,
			}, -2)
			self["key_red"] = StaticText(_("Exit"))
			self["key_green"] = StaticText("Scan")
			self["key_blue"] = StaticText("Scan All")
			self["introduction"] = Label(_("Press Green/OK to start the scan"))
			self.createSetup()
		else :
			self["actions"] = ActionMap(["OkCancelActions", "ShortcutActions", "WizardActions", "ColorActions", "SetupActions", ],
			{
				"red": self.keyCancel,
				"green": self.keyNone,
				"blue":self.keyNone,
				"ok": self.keyNone,
				"cancel": self.keyCancel,
			}, -2)
			self["key_red"] = StaticText(_("Exit"))
			self["key_green"] = StaticText(" ")
			self["key_blue"] = StaticText(" ")
			self["introduction"] = Label(_("Please setup your tuner configuration."))

		self.i2c_mapping_table = None
		self.nimSockets = self.ScanNimsocket()
		self.makeNimSocket()

	def ScanNimsocket(self, filepath = '/proc/bus/nim_sockets'):
		_nimSocket = {}
		fp = file(filepath)

		sNo, sName, sI2C = -1, "", -1
		for line in fp:
			line = line.strip()
			if line.startswith('NIM Socket'):
				sNo, sName, sI2C = -1, '', -1
				try:    sNo = line.split()[2][:-1]
				except:	sNo = -1
			elif line.startswith('I2C_Device:'):
				try:    sI2C = line.split()[1]
				except: sI2C = -1
			elif line.startswith('Name:'):
				splitLines = line.split()
				try:
					if splitLines[1].startswith('BCM'):
						sName = splitLines[1]
					else:
						sName = splitLines[3][4:-1]
				except: sName = ""
			if sNo >= 0 and sName != "":
				if sName.startswith('BCM'):
					sI2C = sNo
				if sI2C != -1:
					_nimSocket[sNo] = [sName, sI2C]
				else:	_nimSocket[sNo] = [sName]
		fp.close()
		print "parsed nimsocket :", _nimSocket
		return _nimSocket

	def makeNimSocket(self, nimname=""):
		is_exist_i2c = False
		self.i2c_mapping_table = {0:2, 1:3, 2:1, 3:0}
		if self.nimSockets is not None:
			for XX in self.nimSockets.keys():
				nimsocket = self.nimSockets[XX]
				if len(nimsocket) > 1:
					try:	self.i2c_mapping_table[int(XX)] = int(nimsocket[1])
					except: continue
					is_exist_i2c = True
		print "i2c_mapping_table :", self.i2c_mapping_table, ", is_exist_i2c :", is_exist_i2c
		if is_exist_i2c: return

		if nimname == "AVL6222":
			model = _modelName #file('/proc/stb/info/vumodel').read().strip()
			if model == "uno":
				self.i2c_mapping_table = {0:3, 1:3, 2:1, 3:0}
			elif model == "duo2":
				nimdata = self.nimSockets['0']
				try:
					if nimdata[0] == "AVL6222":
						self.i2c_mapping_table = {0:2, 1:2, 2:4, 3:4}
					else:	self.i2c_mapping_table = {0:2, 1:4, 2:4, 3:0}
				except: self.i2c_mapping_table = {0:2, 1:4, 2:4, 3:0}
			else:	self.i2c_mapping_table = {0:2, 1:4, 2:0, 3:0}
		else:   self.i2c_mapping_table = {0:2, 1:3, 2:1, 3:0}

	def getNimSocket(self, slot_number):
		return self.i2c_mapping_table.get(slot_number, -1)

	def keyNone(self):
		None
	def callbackNone(self, *retval):
		None

	def openFrontend(self):
		res_mgr = eDVBResourceManager.getInstance()
		if res_mgr:
			self.raw_channel = res_mgr.allocateRawChannel(self.feid)
			if self.raw_channel:
				self.frontend = self.raw_channel.getFrontend()
				if self.frontend:
					return True
				else:
					print "getFrontend failed"
			else:
				print "getRawChannel failed"
		else:
			print "getResourceManager instance failed"
		return False

	def createConfig(self):
		self.feinfo = None
		frontendData = None
		defaultSat = {
			"orbpos": 192,
			"system": eDVBFrontendParametersSatellite.System_DVB_S,
			"frequency": 11836,
			"inversion": eDVBFrontendParametersSatellite.Inversion_Unknown,
			"symbolrate": 27500,
			"polarization": eDVBFrontendParametersSatellite.Polarisation_Horizontal,
			"fec": eDVBFrontendParametersSatellite.FEC_Auto,
			"fec_s2": eDVBFrontendParametersSatellite.FEC_9_10,
			"modulation": eDVBFrontendParametersSatellite.Modulation_QPSK 
		}

		self.service = self.session.nav.getCurrentService()
		if self.service is not None:
			self.feinfo = self.service.frontendInfo()
			frontendData = self.feinfo and self.feinfo.getAll(True)
		if frontendData is not None:
			ttype = frontendData.get("tuner_type", "UNKNOWN")
			if ttype == "DVB-S":
				defaultSat["system"] = frontendData.get("system", eDVBFrontendParametersSatellite.System_DVB_S)
				defaultSat["frequency"] = frontendData.get("frequency", 0) / 1000
				defaultSat["inversion"] = frontendData.get("inversion", eDVBFrontendParametersSatellite.Inversion_Unknown)
				defaultSat["symbolrate"] = frontendData.get("symbol_rate", 0) / 1000
				defaultSat["polarization"] = frontendData.get("polarization", eDVBFrontendParametersSatellite.Polarisation_Horizontal)
				if defaultSat["system"] == eDVBFrontendParametersSatellite.System_DVB_S2:
					defaultSat["fec_s2"] = frontendData.get("fec_inner", eDVBFrontendParametersSatellite.FEC_Auto)
					defaultSat["rolloff"] = frontendData.get("rolloff", eDVBFrontendParametersSatellite.RollOff_alpha_0_35)
					defaultSat["pilot"] = frontendData.get("pilot", eDVBFrontendParametersSatellite.Pilot_Unknown)
				else:
					defaultSat["fec"] = frontendData.get("fec_inner", eDVBFrontendParametersSatellite.FEC_Auto)
				defaultSat["modulation"] = frontendData.get("modulation", eDVBFrontendParametersSatellite.Modulation_QPSK)
				defaultSat["orbpos"] = frontendData.get("orbital_position", 0)
		del self.feinfo
		del self.service
		del frontendData
		
		self.scan_sat = ConfigSubsection()
		self.scan_networkScan = ConfigYesNo(default = False)
		
		# blindscan add
		self.blindscan_hi = ConfigSelection(default = "hi_low", choices = [("low", _("low")), ("high", _("high")), ("hi_low", _("hi_low"))])

		#ConfigYesNo(default = True)
		self.blindscan_start_frequency = ConfigInteger(default = 950*1000000)
		self.blindscan_stop_frequency = ConfigInteger(default = 2150*1000000)
		self.blindscan_start_symbol = ConfigInteger(default = 2*1000000)
		self.blindscan_stop_symbol = ConfigInteger(default = 45*1000000)
		self.scan_clearallservices = ConfigYesNo(default = False)
		self.scan_onlyfree = ConfigYesNo(default = False)

		# collect all nims which are *not* set to "nothing"
		nim_list = []
		for n in nimmanager.nim_slots:
			if n.config_mode == "nothing":
				continue
			if n.config_mode == "advanced" and len(nimmanager.getSatListForNim(n.slot)) < 1:
				continue
			if n.config_mode in ("loopthrough", "satposdepends"):
				root_id = nimmanager.sec.getRoot(n.slot_id, int(n.config.connectedTo.value))
				if n.type == nimmanager.nim_slots[root_id].type: # check if connected from a DVB-S to DVB-S2 Nim or vice versa
					continue
			if n.isCompatible("DVB-S"):
				nim_list.append((str(n.slot), n.friendly_full_description))
		self.scan_nims = ConfigSelection(choices = nim_list)

		# sat
		self.scan_sat.frequency = ConfigInteger(default = defaultSat["frequency"], limits = (1, 99999))
		#self.scan_sat.polarization = ConfigSelection(default = defaultSat["polarization"], choices = [
		self.scan_sat.polarization = ConfigSelection(default = eDVBFrontendParametersSatellite.Polarisation_CircularRight + 1, choices = [
			(eDVBFrontendParametersSatellite.Polarisation_CircularRight + 1, _("horizontal_vertical")),
			(eDVBFrontendParametersSatellite.Polarisation_Horizontal, _("horizontal")),
			(eDVBFrontendParametersSatellite.Polarisation_Vertical, _("vertical")),
			(eDVBFrontendParametersSatellite.Polarisation_CircularLeft, _("circular left")),
			(eDVBFrontendParametersSatellite.Polarisation_CircularRight, _("circular right"))])
		self.scan_scansat = {}
		for sat in nimmanager.satList:
			self.scan_scansat[sat[0]] = ConfigYesNo(default = False)
		
		self.scan_satselection = []
		for slot in nimmanager.nim_slots:
			if slot.isCompatible("DVB-S"):
				self.scan_satselection.append(getConfigSatlist(defaultSat["orbpos"], self.satList[slot.slot]))
		return True

	def getSelectedSatIndex(self, v):
		index    = 0
		none_cnt = 0
		for n in self.satList:
			if self.satList[index] == None:
				none_cnt = none_cnt + 1
			if index == int(v):
				return (index-none_cnt)
			index = index + 1
		return -1

	def createSetup(self):
		self.list = []
		self.multiscanlist = []
		index_to_scan = int(self.scan_nims.value)
		print "ID: ", index_to_scan

		self.tunerEntry = getConfigListEntry(_("Tuner"), self.scan_nims)
		self.list.append(self.tunerEntry)
		
		if self.scan_nims == [ ]:
			return
		
		self.systemEntry = None
		self.modulationEntry = None
		nim = nimmanager.nim_slots[index_to_scan]

		self.scan_networkScan.value = False
		if nim.isCompatible("DVB-S") :
			self.list.append(getConfigListEntry(_('Satellite'), self.scan_satselection[self.getSelectedSatIndex(index_to_scan)]))
			self.list.append(getConfigListEntry(_('Scan start frequency'), self.blindscan_start_frequency))
			self.list.append(getConfigListEntry(_('Scan stop frequency'), self.blindscan_stop_frequency))
			self.list.append(getConfigListEntry(_("Polarity"), self.scan_sat.polarization))
			self.list.append(getConfigListEntry(_("Scan band"), self.blindscan_hi))
			self.list.append(getConfigListEntry(_('Scan start symbolrate'), self.blindscan_start_symbol))
			self.list.append(getConfigListEntry(_('Scan stop symbolrate'), self.blindscan_stop_symbol))
			self.list.append(getConfigListEntry(_("Clear before scan"), self.scan_clearallservices))
			self.list.append(getConfigListEntry(_("Only Free scan"), self.scan_onlyfree))
			self["config"].list = self.list
			self["config"].l.setList(self.list)
			
	def newConfig(self):
		cur = self["config"].getCurrent()
		print "cur is", cur
		if cur == self.tunerEntry or \
			cur == self.systemEntry or \
			(self.modulationEntry and self.systemEntry[1].value == eDVBFrontendParametersSatellite.System_DVB_S2 and cur == self.modulationEntry):
			self.createSetup()

	def checkSettings(self):
		if self.blindscan_start_frequency.value < 950*1000000 or self.blindscan_start_frequency.value > 2150*1000000 :
			self.session.open(MessageBox, _("Please check again.\nStart frequency must be between 950 and 2150."), MessageBox.TYPE_ERROR)
			return False
		if self.blindscan_stop_frequency.value < 950*1000000 or self.blindscan_stop_frequency.value > 2150*1000000 :
			self.session.open(MessageBox, _("Please check again.\nStop frequency must be between 950 and 2150."), MessageBox.TYPE_ERROR)
			return False
		if self.blindscan_start_frequency.value > self.blindscan_stop_frequency.value :
			self.session.open(MessageBox, _("Please check again.\nFrequency : start value is larger than stop value."), MessageBox.TYPE_ERROR)
			return False
		if self.blindscan_start_symbol.value < 2*1000000 or self.blindscan_start_symbol.value > 45*1000000 :
			self.session.open(MessageBox, _("Please check again.\nStart symbolrate must be between 2MHz and 45MHz."), MessageBox.TYPE_ERROR)
			return False
		if self.blindscan_stop_symbol.value < 2*1000000 or self.blindscan_stop_symbol.value > 45*1000000 :
			self.session.open(MessageBox, _("Please check again.\nStop symbolrate must be between 2MHz and 45MHz."), MessageBox.TYPE_ERROR)
			return False
		if self.blindscan_start_symbol.value > self.blindscan_stop_symbol.value :
			self.session.open(MessageBox, _("Please check again.\nSymbolrate : start value is larger than stop value."), MessageBox.TYPE_ERROR)
			return False
		return True

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.newConfig()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.newConfig()
			
	def keyCancel(self):
		self.session.nav.playService(self.current_play_service)
		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def keyGo(self):
		if self.checkSettings() == False:
			return

		tab_pol = {
			eDVBFrontendParametersSatellite.Polarisation_Horizontal : "horizontal", 
			eDVBFrontendParametersSatellite.Polarisation_Vertical : "vertical",
			eDVBFrontendParametersSatellite.Polarisation_CircularLeft : "circular left",
			eDVBFrontendParametersSatellite.Polarisation_CircularRight : "circular right",
			eDVBFrontendParametersSatellite.Polarisation_CircularRight + 1 : "horizontal_vertical"
		}

		self.tmp_tplist=[]
		tmp_pol = []
		tmp_band = []
		idx_selected_sat = int(self.getSelectedSatIndex(self.scan_nims.value))
		tmp_list=[self.satList[int(self.scan_nims.value)][self.scan_satselection[idx_selected_sat].index]]

		if self.blindscan_hi.value == "hi_low" :
			tmp_band=["low","high"]
		else:
			tmp_band=[self.blindscan_hi.value]
			
		if self.scan_sat.polarization.value ==  eDVBFrontendParametersSatellite.Polarisation_CircularRight + 1 : 
			tmp_pol=["horizontal","vertical"]
		else:
			tmp_pol=[tab_pol[self.scan_sat.polarization.value]]

		self.doRun(tmp_list, tmp_pol, tmp_band)
		
	def keyGoAll(self):
		if self.checkSettings() == False:
			return
		self.tmp_tplist=[]
		tmp_list=[]
		tmp_band=["low","high"]
		tmp_pol=["horizontal","vertical"]
		
		for slot in nimmanager.nim_slots:
			device_name = "/dev/dvb/adapter0/frontend%d" % (slot.slot)
			if slot.isCompatible("DVB-S") and int(self.scan_nims.value) == slot.slot:
				for s in self.satList[slot.slot]:
					tmp_list.append(s)
		self.doRun(tmp_list, tmp_pol, tmp_band)
		
	def doRun(self, tmp_list, tmp_pol, tmp_band):
		def GetCommand(nimIdx):
			_nimSocket = self.nimSockets
			try:
				sName = _nimSocket[str(nimIdx)][0]
				sType = _supportNimType[sName]
				return "vuplus_%(TYPE)sblindscan"%{'TYPE':sType}, sName
			except: pass
			return "vuplus_blindscan", ""
		self.binName,nimName =  GetCommand(self.scan_nims.value)

		self.makeNimSocket(nimName)
		if self.binName is None:
			self.session.open(MessageBox, "Blindscan is not supported in " + nimName + " tuner.", MessageBox.TYPE_ERROR)
			print nimName + " is not support blindscan."
			return

		self.full_data = ""
		self.total_list=[]
		for x in tmp_list:
			for y in tmp_pol:
				for z in tmp_band:
					self.total_list.append([x,y,z])
					print "add scan item : ", x, ", ", y, ", ", z

		self.max_count = len(self.total_list)
		self.is_runable = True
		self.running_count = 0
		self.clockTimer = eTimer()
		self.clockTimer.callback.append(self.doClock)
		self.clockTimer.start(1000)

	def doClock(self):
		is_scan = False
		if self.is_runable :
			if self.running_count >= self.max_count:
				self.clockTimer.stop()
				del self.clockTimer
				self.clockTimer = None
				print "Done"
				return
			orb = self.total_list[self.running_count][0]
			pol = self.total_list[self.running_count][1]
			band = self.total_list[self.running_count][2]
			self.running_count = self.running_count + 1
			print "running status-[%d] : [%d][%s][%s]" %(self.running_count, orb[0], pol, band)
			if self.running_count == self.max_count:
				is_scan = True
			self.prepareScanData(orb, pol, band, is_scan)

	def prepareScanData(self, orb, pol, band, is_scan):
		self.is_runable = False
		self.orb_position = orb[0]
		self.feid = int(self.scan_nims.value)
		tab_hilow = {"high" : 1, "low" : 0}
		tab_pol = {
			"horizontal" : eDVBFrontendParametersSatellite.Polarisation_Horizontal, 
			"vertical" : eDVBFrontendParametersSatellite.Polarisation_Vertical,
			"circular left" : eDVBFrontendParametersSatellite.Polarisation_CircularLeft,
			"circular right" : eDVBFrontendParametersSatellite.Polarisation_CircularRight
		}

		returnvalue = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

		if not self.openFrontend():
			self.oldref = self.session.nav.getCurrentlyPlayingServiceReference()
			self.session.nav.stopService()
			if not self.openFrontend():
				if self.session.pipshown:
					self.session.pipshown = False
					del self.session.pip
					if not self.openFrontend():
						self.frontend = None
		self.tuner = Tuner(self.frontend)

		if tab_hilow[band]:
			self.scan_sat.frequency.value = 12515
		else:
			self.scan_sat.frequency.value = 11015
		returnvalue = (self.scan_sat.frequency.value,
					 0,
					 tab_pol[pol],
					 0,
					 0,
					 orb[0],
					 eDVBFrontendParametersSatellite.System_DVB_S,
					 0,
					 0,
					 0)
		self.tuner.tune(returnvalue)

		if self.getNimSocket(self.feid) < 0:
			print "can't find i2c number!!"
			return
		try:
			cmd = "%s %d %d %d %d %d %d %d %d" % (self.binName, self.blindscan_start_frequency.value/1000000, self.blindscan_stop_frequency.value/1000000, self.blindscan_start_symbol.value/1000000, self.blindscan_stop_symbol.value/1000000, tab_pol[pol], tab_hilow[band], self.feid, self.getNimSocket(self.feid))
		except: return
		print "prepared command : [%s]" % (cmd)
		self.blindscan_container = eConsoleAppContainer()
		self.blindscan_container.appClosed.append(self.blindscanContainerClose)
		self.blindscan_container.dataAvail.append(self.blindscanContainerAvail)
		self.blindscan_container.execute(cmd)

		tmpstr = "Look for available transponders.\nThis works will take several minutes.\n\n   - Current Status : %d/%d\n   - Orbital Positions : %s\n   - Polarization : %s\n   - Bandwidth : %s" %(self.running_count, self.max_count, orb[1], pol, band)
		if is_scan :
			self.blindscan_session = self.session.openWithCallback(self.blindscanSessionClose, MessageBox, _(tmpstr), MessageBox.TYPE_INFO)
		else:
			self.blindscan_session = self.session.openWithCallback(self.blindscanSessionNone, MessageBox, _(tmpstr), MessageBox.TYPE_INFO)

	def blindscanContainerClose(self, retval):
		lines = self.full_data.split('\n')
		for line in lines:
			data = line.split()
			print "cnt :", len(data), ", data :", data
			if len(data) >= 10:
				if data[0] == 'OK':
					parm = eDVBFrontendParametersSatellite()
					sys = { "DVB-S" : eDVBFrontendParametersSatellite.System_DVB_S,
						"DVB-S2" : eDVBFrontendParametersSatellite.System_DVB_S2}
					qam = { "QPSK" : parm.Modulation_QPSK,
						"8PSK" : parm.Modulation_8PSK}
					inv = { "INVERSION_OFF" : parm.Inversion_Off,
						"INVERSION_ON" : parm.Inversion_On,
						"INVERSION_AUTO" : parm.Inversion_Unknown}
					fec = { "FEC_AUTO" : parm.FEC_Auto,
						"FEC_1_2" : parm.FEC_1_2,
						"FEC_2_3" : parm.FEC_2_3,
						"FEC_3_4" : parm.FEC_3_4,
						"FEC_5_6": parm.FEC_5_6,
						"FEC_7_8" : parm.FEC_7_8,
						"FEC_8_9" : parm.FEC_8_9,
						"FEC_3_5" : parm.FEC_3_5,
						"FEC_9_10" : parm.FEC_9_10,
						"FEC_NONE" : parm.FEC_None}
					roll ={ "ROLLOFF_20" : parm.RollOff_alpha_0_20,
						"ROLLOFF_25" : parm.RollOff_alpha_0_25,
						"ROLLOFF_35" : parm.RollOff_alpha_0_35}
					pilot={ "PILOT_ON" : parm.Pilot_On,
						"PILOT_OFF" : parm.Pilot_Off,
						"PILOT_AUTO" : parm.Pilot_Unknown}
					pol = {	"HORIZONTAL" : parm.Polarisation_Horizontal,
						"VERTICAL" : parm.Polarisation_Vertical}
					try :
						parm.orbital_position = self.orb_position
						parm.polarisation = pol[data[1]]
						parm.frequency = int(data[2])
						parm.symbol_rate = int(data[3])
						parm.system = sys[data[4]]
						parm.inversion = inv[data[5]]
						parm.pilot = pilot[data[6]]
						parm.fec = fec[data[7]]
						parm.modulation = qam[data[8]]
						parm.rolloff = roll[data[9]]
						self.tmp_tplist.append(parm)
					except:	pass
		self.blindscan_session.close(True)

	def blindscanContainerAvail(self, str):
		print str
		#if str.startswith("OK"):
		self.full_data = self.full_data + str

	def blindscanSessionNone(self, *val):
		import time
		self.blindscan_container.sendCtrlC()
		self.blindscan_container = None
		time.sleep(2)

		if self.frontend:
			self.frontend = None
			del self.raw_channel

		if val[0] == False:
			self.tmp_tplist = []
			self.running_count = self.max_count

		self.is_runable = True

	def blindscanSessionClose(self, *val):
		self.blindscanSessionNone(val[0])

		if self.tmp_tplist != None and self.tmp_tplist != []:
			for p in self.tmp_tplist:
				print "data : [%d][%d][%d][%d][%d][%d][%d][%d][%d][%d]" % (p.orbital_position, p.polarisation, p.frequency, p.symbol_rate, p.system, p.inversion, p.pilot, p.fec, p.modulation, p.modulation)

			self.startScan(self.tmp_tplist, self.feid)
		else:
			msg = "No found transponders!!\nPlease check the satellite connection, or scan other search condition." 
			if val[0] == False:
				msg = "Blindscan was canceled by the user."
			self.session.openWithCallback(self.callbackNone, MessageBox, _(msg), MessageBox.TYPE_INFO, timeout=10)
			self.tmp_tplist = []

	def startScan(self, tlist, feid, networkid = 0):
		self.scan_session = None

		flags = 0
		if self.scan_clearallservices.value:
			flags |= eComponentScan.scanRemoveServices
		else:
			flags |= eComponentScan.scanDontRemoveUnscanned
		if self.scan_onlyfree.value:
			flags |= eComponentScan.scanOnlyFree
		self.session.open(ServiceScan, [{"transponders": tlist, "feid": feid, "flags": flags, "networkid": networkid}])

def main(session, **kwargs):
	session.open(Blindscan)
                                                           
def Plugins(**kwargs):            
	return PluginDescriptor(name=_("Blindscan"), description="scan type(DVB-S)", where = PluginDescriptor.WHERE_PLUGINMENU, fnc=main)

