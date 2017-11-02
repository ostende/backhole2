from Components.config import config, ConfigSubsection, ConfigSelection
from Components.UsageConfig import preferredInstantRecordPath, defaultMoviePath

from enigma import eTimer, eServiceReference, eServiceCenter, iServiceInformation, iRecordableService
from RecordTimer import RecordTimerEntry, RecordTimer
from Tools.Directories import fileExists
from ServiceReference import ServiceReference

from Tools import Notifications
from Screens.MessageBox import MessageBox

import os
import glob
import time

config.plugins.pvrdesconvertsetup = ConfigSubsection()
config.plugins.pvrdesconvertsetup.activate = ConfigSelection(default = "disable", choices = [ ("enable", _("Enable")), ("disable", _("Disable"))] )

# lib/dvb/pmt.h
SERVICETYPE_PVR_DESCRAMBLE = 11

def fileExist(fileName, flag = os.W_OK):
	return os.access(fileName, flag)

def sync():
	if hasattr(os, 'sync'):
		os.sync()
	else:
		import ctypes
		libc = ctypes.CDLL("libc.so.6")
		libc.sync()

# iStaticServiceInformation
class StubInfo:
	def getName(self, sref):
		return os.path.split(sref.getPath())[1]
	def getLength(self, sref):
		return -1
	def getEvent(self, sref, *args):
		return None
	def isPlayable(self):
		return True
	def getInfo(self, sref, w):
		if w == iServiceInformation.sTimeCreate:
			return os.stat(sref.getPath()).st_ctime
		if w == iServiceInformation.sFileSize:
			return os.stat(sref.getPath()).st_size
		if w == iServiceInformation.sDescription:
			return sref.getPath()
		return 0
	def getInfoString(self, sref, w):
		return ''
stubInfo = StubInfo()

class PVRDescrambleConvertInfos:
	def __init__(self):
		self.navigation = None

	def getNavigation(self):
		if not self.navigation:
			import NavigationInstance
			if NavigationInstance:
				self.navigation = NavigationInstance.instance

		return self.navigation

	def getRecordings(self):
		recordings = []
		nav = self.getNavigation()
		if nav:
			recordings = nav.getRecordings()
			print "getRecordings : ", recordings

		return recordings

	def getInstandby(self):
		from Screens.Standby import inStandby
		return inStandby

	def getCurrentMoviePath(self):
		if not fileExists(config.movielist.last_videodir.value):
			config.movielist.last_videodir.value = defaultMoviePath()
			config.movielist.last_videodir.save()

		curMovieRef = eServiceReference("2:0:1:0:0:0:0:0:0:0:" + config.movielist.last_videodir.value)
		return curMovieRef

class PVRDescrambleConvert(PVRDescrambleConvertInfos):
	def __init__(self):
		PVRDescrambleConvertInfos.__init__(self)
		config.misc.standbyCounter.addNotifier(self.enterStandby, initial_call = False)

		self.convertTimer = eTimer()
		self.convertTimer.callback.append(self.startConvert)

		self.stopConvertTimer = eTimer()
		self.stopConvertTimer.callback.append(self.stopConvert)

		self.converting = None
		self.convertFilename = None
		self.currentPvr = None

		self.pvrLists = []

		self.oldService = None

	def enterStandby(self, configElement):
		if config.plugins.pvrdesconvertsetup.activate.value == "enable":
			instandby = self.getInstandby()
			instandby.onClose.append(self.leaveStandby)

			self.loadScrambledPvrList()

			# register record callback
			self.appendRecordEventCB()

			self.startConvertTimer()

	def leaveStandby(self):
		self.removeRecordEventCB()
		self.convertTimer.stop()
		self.stopConvert()

	def startConvertTimer(self):
		self.convertTimer.start(3000, True)

	def startStopConvertTimer(self):
		self.stopConvertTimer.start(500, True)

	def appendRecordEventCB(self):
		nav = self.getNavigation()
		if nav:
			if self.gotRecordEvent not in nav.record_event:
				nav.record_event.append(self.gotRecordEvent)

	def removeRecordEventCB(self):
		nav = self.getNavigation()
		if nav:
			if self.gotRecordEvent in nav.record_event:
				nav.record_event.remove(self.gotRecordEvent)

	def gotRecordEvent(self, service, event):
		if service.getServiceType() == SERVICETYPE_PVR_DESCRAMBLE:
			if event == iRecordableService.evEnd:
				if self.getInstandby():
					self.startConvertTimer()
			elif event == iRecordableService.evPvrEof:
				self.stopConvert(convertFinished = True)
			elif event == iRecordableService.evRecordFailed:
				self.startStopConvertTimer()
		else:
			if event in (iRecordableService.evPvrTuneStart, iRecordableService.evTuneStart):
				if self.currentPvr:
					self.pvrLists.insert(0, self.currentPvr)
					self.currentPvr = None
					self.startStopConvertTimer()
			elif event == iRecordableService.evEnd:
				if self.getInstandby():
					self.startConvertTimer()

	def loadScrambledPvrList(self):
		self.pvrLists = []

		serviceHandler = eServiceCenter.getInstance()
		curMovieRef = self.getCurrentMoviePath()
		movieRefList = serviceHandler.list(curMovieRef)

		if movieRefList is None:
			print "Load pvr list failed!"
			return

		while 1:
			sref = movieRefList.getNext()
			if not sref.valid():
				break

			if config.ParentalControl.servicepinactive.value and config.ParentalControl.storeservicepin.value != "never":
				from Components.ParentalControl import parentalControl
				if not parentalControl.sessionPinCached and parentalControl.isProtected(sref):
					continue

			if sref.flags & eServiceReference.mustDescent:
				continue

			if not sref.getPath():
				return

			info = serviceHandler.info(sref)

			real_sref = "1:0:0:0:0:0:0:0:0:0:"
			if info is not None:
				real_sref = info.getInfoString(sref, iServiceInformation.sServiceref)

			if info is None:
				info = stubInfo

			begin = info.getInfo(sref, iServiceInformation.sTimeCreate)

			# convert separe-separated list of tags into a set
			name = info.getName(sref)
			scrambled = info.getInfo(sref, iServiceInformation.sIsScrambled)
			length = info.getLength(sref)

			if scrambled == 1:
				#print "====" * 30
				#print "[loadScrambledPvrList] sref.toString() : ", sref.toString()
				#print "[loadScrambledPvrList] sref.getPath() : ", sref.getPath()
				#print "[loadScrambledPvrList] name : ", name
				#print "[loadScrambledPvrList] begin : ", begin
				#print "[loadScrambledPvrList] length : ", length
				#print "[loadScrambledPvrList] scrambled : ", scrambled
				#print ""
				rec = (begin, sref, name, length, real_sref)
				if rec not in self.pvrLists:
					self.pvrLists.append( rec )

		self.pvrLists.sort()

	def checkBeforeStartConvert(self):
		return self.pvrLists and (not bool(self.getRecordings())) and (not self.converting) and self.getInstandby()

	def startConvert(self):
		if not self.checkBeforeStartConvert():
			return

		self.currentPvr = self.pvrLists.pop(0)
		if self.currentPvr is None:
			return

		(_begin, sref, name, length, real_ref) = self.currentPvr

		m_path = sref.getPath()
		sref = eServiceReference(real_ref + m_path)

		begin = int(time.time())
		end = begin + 3600	# dummy
		#end = begin + int(length) + 2
		description = ""
		eventid = None

		if isinstance(sref, eServiceReference):
			sref = ServiceReference(sref)

		if m_path.endswith('.ts'):
			m_path = m_path[:-3]

		filename = m_path + "_pvrdesc"

		recording = RecordTimerEntry(sref, begin, end, name, description, eventid, dirname = preferredInstantRecordPath(), filename=filename)
		recording.dontSave = True
		recording.autoincrease = True
		recording.setAutoincreaseEnd()
		recording.pvrConvert = True # do not handle evStart event

		nav = self.getNavigation()
		simulTimerList = nav.RecordTimer.record(recording)
		if simulTimerList is None:	# no conflict
			recordings = self.getRecordings()
			if len(recordings) == 1:
				self.converting = recording
				self.convertFilename = (sref.getPath(), filename + ".ts")
			else:
				print "[PVRDescrambleConvert] error, wrong recordings info."
		else:
			self.currentPvr = None
			self.startConvertTimer()

			if len(simulTimerList) > 1: # with other recording
				print "[PVRDescrambleConvert] conflicts !"
			else:
				print "[PVRDescrambleConvert] Couldn't record due to invalid service %s" % sref
			recording.autoincrease = False

		print "[PVRDescrambleConvert] startConvert, self.converting : ", self.converting

	def removeStr(self, fileName, s):
		if fileName.find(s) == -1:
			return fileName

		sp = fileName.split(s)

		return sp[0] + sp[1]

	def renameDelPvr(self, pvrName, subName):
		targetName = pvrName + subName
		outName = self.removeStr(pvrName, ".ts") + "_del" + ".ts" + subName

		if fileExist(targetName):
			#print "RENAME %s -> %s" % (targetName, outName)
			os.rename(targetName, outName)
			return outName

		return None

	def renameConvertPvr(self, pvrName, subName):
		targetName = pvrName + subName
		outName = self.removeStr(pvrName, "_pvrdesc") + subName

		if fileExist(targetName):
			#print "RENAME %s -> %s" % (targetName, outName)
			os.rename(targetName, outName)
			return outName

		return None

	def renamePvr(self, pvr_ori, pvr_convert):
		pvr_ori_del = self.renameDelPvr(pvr_ori, "")
		if not pvr_ori_del:
			return None

		self.renameDelPvr(pvr_ori, ".meta")
		self.renameDelPvr(pvr_ori, ".ap")
		self.renameDelPvr(pvr_ori, ".sc")
		self.renameDelPvr(pvr_ori, ".cuts")

		pvr_convert_fixed = self.renameConvertPvr(pvr_convert, "")
		if not pvr_convert_fixed:
			return None

		self.renameConvertPvr(pvr_convert, ".meta")
		self.renameConvertPvr(pvr_convert, ".ap")
		self.renameConvertPvr(pvr_convert, ".sc")
		self.renameConvertPvr(pvr_convert, ".cuts")

		if os.path.exists(pvr_convert[:-3] + '.eit'):
			os.remove(pvr_convert[:-3] + '.eit')

		return pvr_ori_del

	def stopConvert(self, convertFinished = False):
		name = "Unknown"
		if self.currentPvr:
			(_begin, sref, name, length, real_ref) = self.currentPvr
			self.currentPvr = None

		if self.converting:
			nav = self.getNavigation()
			nav.RecordTimer.removeEntry(self.converting)
			convertFilename = self.convertFilename
			self.converting = None
			self.convertFilename = None

			if convertFilename:
				(pvr_ori, pvr_convert) = convertFilename
				if convertFinished:
					# check size
					if fileExist(pvr_convert, os.F_OK) and os.stat(pvr_convert).st_size:
						pvr_ori_del = self.renamePvr(pvr_ori, pvr_convert)
						if pvr_ori_del:
							self.deletePvr(pvr_ori_del)
						self.addNotification(_("A PVR descramble converting is finished.\n%s") % name)
					else:
						self.deletePvr(pvr_convert)
				else:
					self.deletePvr(pvr_convert)

		sync()

	def deletePvr(self, filename):
		serviceHandler = eServiceCenter.getInstance()
		ref = eServiceReference(1, 0, filename)
		offline = serviceHandler.offlineOperations(ref)
		if offline.deleteFromDisk(0):
			print "[PVRDescrambleConvert] delete failed : ", filename

	def addNotification(self, text):
		Notifications.AddNotification(MessageBox, text, type=MessageBox.TYPE_INFO, timeout=5)

pvr_descramble_convert = PVRDescrambleConvert()

