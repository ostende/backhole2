from HTMLComponent import HTMLComponent
from GUIComponent import GUIComponent
from skin import parseFont

from Tools.FuzzyDate import FuzzyTime

from enigma import eListboxPythonMultiContent, eListbox, gFont, \
	RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_CENTER
from Tools.LoadPixmap import LoadPixmap
from Components.config import config
from timer import TimerEntry
from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN

class TimerList(HTMLComponent, GUIComponent, object):
#
#  | <Service>     <Name of the Timer>  |
#  | <start, end>              <state>  |
#
	def buildTimerEntry(self, timer, processed):
		width = self.l.getItemSize().width()
		res = [ None ]
		print "timer.service_ref.getServiceName() : ", timer.service_ref.getServiceName()
		print "timer.name : ", timer.name
		ih = self.itemHeight
		ih1 = ih * 30 / 70 # 70 -> 30
		ih2 = ih * 20 / 70 # 70 -> 20
		stateSize = ih * 150 / 70   # 20 -> 145
		res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, 0, width, ih1, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, timer.service_ref.getServiceName()))
		res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, ih1, width, ih2, 1, RT_HALIGN_LEFT|RT_VALIGN_CENTER, timer.name))

		repeatedtext = ""
		days = ( _("Mon"), _("Tue"), _("Wed"), _("Thu"), _("Fri"), _("Sat"), _("Sun") )
		if timer.repeated:
			flags = timer.repeated
			count = 0
			for x in (0, 1, 2, 3, 4, 5, 6):
					if (flags & 1 == 1):
						if (count != 0):
							repeatedtext += ", "
						repeatedtext += days[x]
						count += 1
					flags = flags >> 1
			if timer.justplay:
				if timer.end - timer.begin < 4: # rounding differences
					res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, ih1+ih2, width-stateSize, ih2, 1, RT_HALIGN_LEFT|RT_VALIGN_CENTER, repeatedtext + ((" %s "+ _("(ZAP)")) % (FuzzyTime(timer.begin)[1]))))
				else:
					res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, ih1+ih2, width-stateSize, ih2, 1, RT_HALIGN_LEFT|RT_VALIGN_CENTER, repeatedtext + ((" %s ... %s (%d " + _("mins") + ") ") % (FuzzyTime(timer.begin)[1], FuzzyTime(timer.end)[1], (timer.end - timer.begin) / 60)) + _("(ZAP)")))
			else:
				res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, ih1+ih2, width-stateSize, ih2, 1, RT_HALIGN_LEFT|RT_VALIGN_CENTER, repeatedtext + ((" %s ... %s (%d " + _("mins") + ")") % (FuzzyTime(timer.begin)[1], FuzzyTime(timer.end)[1], (timer.end - timer.begin) / 60))))
		else:
			if timer.justplay:
				if timer.end - timer.begin < 4:
					res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, ih1+ih2, width-stateSize, ih2, 1, RT_HALIGN_LEFT|RT_VALIGN_CENTER, repeatedtext + (("%s, %s " + _("(ZAP)")) % (FuzzyTime(timer.begin)))))
				else:
					res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, ih1+ih2, width-stateSize, ih2, 1, RT_HALIGN_LEFT|RT_VALIGN_CENTER, repeatedtext + (("%s, %s ... %s (%d " + _("mins") + ") ") % (FuzzyTime(timer.begin) + FuzzyTime(timer.end)[1:] + ((timer.end - timer.begin) / 60,))) + _("(ZAP)")))
			else:
				res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, ih1+ih2, width-stateSize, ih2, 1, RT_HALIGN_LEFT|RT_VALIGN_CENTER, repeatedtext + (("%s, %s ... %s (%d " + _("mins") + ")") % (FuzzyTime(timer.begin) + FuzzyTime(timer.end)[1:] + ((timer.end - timer.begin) / 60,)))))

		if not processed:
			if timer.state == TimerEntry.StateWaiting:
				state = _("waiting")
			elif timer.state == TimerEntry.StatePrepared:
				state = _("about to start")
			elif timer.state == TimerEntry.StateRunning:
				if timer.justplay:
					state = _("zapped")
				else:
					state = _("recording...")
			elif timer.state == TimerEntry.StateEnded:
				state = _("done!")
			else:
				state = _("<unknown>")
		else:
			state = _("done!")

		if timer.disabled:
			state = _("disabled")

		res.append((eListboxPythonMultiContent.TYPE_TEXT, width-stateSize, ih1+ih2, stateSize, ih2, 1, RT_HALIGN_RIGHT|RT_VALIGN_CENTER, state))

		if timer.disabled:
			iconPosX = width * 490 / 740
			png = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/icons/redx.png"))
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, iconPosX, 5, 40, 40, png))
		return res

	def __init__(self, list):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.l.setBuildFunc(self.buildTimerEntry)
		self.serviceNameFont = gFont("Regular", 20)
		self.font = gFont("Regular", 18)
		self.itemHeight = 70
		self.l.setList(list)

	def applySkin(self, desktop, parent):
		def itemHeight(value):
			self.itemHeight = int(value)
		def setServiceNameFont(value):
			self.serviceNameFont = parseFont(value, ((1,1),(1,1)))
		def setFont(value):
			self.font = parseFont(value, ((1,1),(1,1)))

		for (attrib, value) in list(self.skinAttributes):
			try:
				locals().get(attrib)(value)
				self.skinAttributes.remove((attrib, value))
			except:
				pass
		self.l.setFont(0, self.serviceNameFont)
		self.l.setFont(1, self.font)
		self.l.setItemHeight(self.itemHeight)
		return GUIComponent.applySkin(self, desktop, parent)
	
	def getCurrent(self):
		cur = self.l.getCurrentSelection()
		return cur and cur[0]
	
	GUI_WIDGET = eListbox
	
	def postWidgetCreate(self, instance):
		instance.setContent(self.l)

	def moveToIndex(self, index):
		self.instance.moveSelectionTo(index)

	def getCurrentIndex(self):
		return self.instance.getCurrentIndex()

	currentIndex = property(getCurrentIndex, moveToIndex)
	currentSelection = property(getCurrent)

	def moveDown(self):
		self.instance.moveSelection(self.instance.moveDown)

	def invalidate(self):
		self.l.invalidate()

	def entryRemoved(self, idx):
		self.l.entryRemoved(idx)

