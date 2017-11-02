from GUIComponent import GUIComponent
from Tools.FuzzyDate import FuzzyTime
from ServiceReference import ServiceReference
from Components.MultiContent import MultiContentEntryText
from Components.config import config

from enigma import eListboxPythonMultiContent, eListbox, gFont, iServiceInformation, \
	RT_HALIGN_LEFT, RT_HALIGN_RIGHT, eServiceReference, eServiceCenter

class MovieList(GUIComponent):
	SORT_ALPHANUMERIC = 1
	SORT_RECORDED = 2

	LISTTYPE_ORIGINAL = 1
	LISTTYPE_COMPACT_DESCRIPTION = 2
	LISTTYPE_COMPACT = 3
	LISTTYPE_MINIMAL = 4

	HIDE_DESCRIPTION = 1
	SHOW_DESCRIPTION = 2

	def __init__(self, root, list_type=None, sort_type=None, descr_state=None):
		GUIComponent.__init__(self)
		self.list_type = list_type or self.LISTTYPE_ORIGINAL
		self.descr_state = descr_state or self.HIDE_DESCRIPTION
		self.sort_type = sort_type or self.SORT_RECORDED

		self.fontName = "Regular"
		self.fontSizesOriginal = (22,18,16)
		self.fontSizesCompact = (20,14)
		self.fontSizesMinimal = (20,16)
		self.itemHeights = (75,37,25)
		self.columnsOriginal = (180,200)
		self.columnsCompactDescription = (120,154,58)
		self.compactColumn = (75,200)

		self.l = eListboxPythonMultiContent()
		self.tags = set()
		
		if root is not None:
			self.reload(root)
		
#		self.redrawList()
		self.l.setBuildFunc(self.buildMovieListEntry)
		
		self.onSelectionChanged = [ ]

	def connectSelChanged(self, fnc):
		if not fnc in self.onSelectionChanged:
			self.onSelectionChanged.append(fnc)

	def disconnectSelChanged(self, fnc):
		if fnc in self.onSelectionChanged:
			self.onSelectionChanged.remove(fnc)

	def selectionChanged(self):
		for x in self.onSelectionChanged:
			x()

	def setListType(self, type):
		self.list_type = type

	def setDescriptionState(self, val):
		self.descr_state = val

	def setSortType(self, type):
		self.sort_type = type

	def applySkin(self, desktop, parent):
		def warningWrongSkinParameter(string):
			print "[MovieList] wrong '%s' skin parameters" % string
		def fontName(value):
			self.fontName = value
		def fontSizesOriginal(value):
			self.fontSizesOriginal = map(int, value.split(","))
			if len(self.fontSizesOriginal) != 3:
				warningWrongSkinParameter(attrib)
		def fontSizesCompact(value):
			self.fontSizesCompact = map(int, value.split(","))
			if len(self.fontSizesCompact) != 2:
				warningWrongSkinParameter(attrib)
		def fontSizesMinimal(value):
			self.fontSizesMinimal = map(int, value.split(","))
			if len(self.fontSizesMinimal) != 2:
				warningWrongSkinParameter(attrib)
		def itemHeights(value):
			self.itemHeights = map(int, value.split(","))
			if len(self.itemHeights) != 3:
				warningWrongSkinParameter(attrib)
		def columnsOriginal(value):
			self.columnsOriginal = map(int, value.split(","))
			if len(self.columnsOriginal) != 2:
				warningWrongSkinParameter(attrib)
		def columnsCompactDescription(value):
			self.columnsCompactDescription = map(int, value.split(","))
			if len(self.columnsCompactDescription) != 3:
				warningWrongSkinParameter(attrib)
		def compactColumn(value):
			self.compactColumn = map(int, value.split(","))
			if len(self.compactColumn) != 2:
				warningWrongSkinParameter(attrib)
		for (attrib, value) in self.skinAttributes[:]:
			try:
				locals().get(attrib)(value)
				self.skinAttributes.remove((attrib, value))
			except:
				pass
		self.redrawList()
		return GUIComponent.applySkin(self, desktop, parent)

	def redrawList(self):
		if self.list_type == MovieList.LISTTYPE_ORIGINAL:
			for i in range(3):
				self.l.setFont(i, gFont(self.fontName, self.fontSizesOriginal[i]))
			self.itemHeight = self.itemHeights[0]
		elif self.list_type == MovieList.LISTTYPE_COMPACT_DESCRIPTION or self.list_type == MovieList.LISTTYPE_COMPACT:
			for i in range(2):
				self.l.setFont(i, gFont(self.fontName, self.fontSizesCompact[i]))
			self.itemHeight = self.itemHeights[1]
		else:
			for i in range(2):
				self.l.setFont(i, gFont(self.fontName, self.fontSizesMinimal[i]))
			self.itemHeight = self.itemHeights[2]
		self.l.setItemHeight(self.itemHeight)

	#
	# | name of movie              |
	#
	def buildMovieListEntry(self, serviceref, info, begin, len):
		if serviceref.flags & eServiceReference.mustDescent:
			return None

		width = self.l.getItemSize().width()
		
		iconSize = 0

		if len <= 0: #recalc len when not already done
			cur_idx = self.l.getCurrentSelectionIndex()
			x = self.list[cur_idx]
			if config.usage.load_length_of_movies_in_moviellist.value:
				len = x[1].getLength(x[0]) #recalc the movie length...
			else:
				len = 0 #dont recalc movielist to speedup loading the list
			self.list[cur_idx] = (x[0], x[1], x[2], len) #update entry in list... so next time we don't need to recalc
		
		if len > 0:
			len = "%d:%02d" % (len / 60, len % 60)
		else:
			len = ""
		
		res = [ None ]
		
		txt = info.getName(serviceref)
		service = ServiceReference(info.getInfoString(serviceref, iServiceInformation.sServiceref))
		description = info.getInfoString(serviceref, iServiceInformation.sDescription)
		tags = info.getInfoString(serviceref, iServiceInformation.sTags)

		begin_string = ""
		if begin > 0:
			t = FuzzyTime(begin)
			begin_string = t[0] + ", " + t[1]
		ih = self.itemHeight
		if self.list_type == MovieList.LISTTYPE_ORIGINAL:
			fc, sc = self.columnsOriginal[0], self.columnsOriginal[1]
			ih1 = (ih * 2) / 5 # 75 -> 30
			ih2 = (ih * 2) / 3 # 75 -> 50
			res.append(MultiContentEntryText(pos=(0, 0), size=(width-fc-2, ih1), font = 0, flags = RT_HALIGN_LEFT, text=txt))
			if self.tags:
				res.append(MultiContentEntryText(pos=(width-fc, 0), size=(fc, ih1), font = 2, flags = RT_HALIGN_RIGHT, text = tags))
				if service is not None:
					res.append(MultiContentEntryText(pos=(sc, ih2), size=(sc, ih2-ih1), font = 1, flags = RT_HALIGN_LEFT, text = service.getServiceName()))
			else:
				if service is not None:
					res.append(MultiContentEntryText(pos=(width-fc, 0), size=(fc, ih1), font = 2, flags = RT_HALIGN_RIGHT, text = service.getServiceName()))
			res.append(MultiContentEntryText(pos=(0, ih1), size=(width, ih2-ih1), font=1, flags=RT_HALIGN_LEFT, text=description))
			res.append(MultiContentEntryText(pos=(0, ih2), size=(sc, ih2-ih1), font=1, flags=RT_HALIGN_LEFT, text=begin_string))
			res.append(MultiContentEntryText(pos=(width-sc, ih2), size=(sc-2, ih2-ih1), font=1, flags=RT_HALIGN_RIGHT, text=len))
		elif self.list_type == MovieList.LISTTYPE_COMPACT_DESCRIPTION:
			ih1 = ((ih * 8) + 14) / 15 # 37 -> 20, round up
			fc, sc, lc = self.columnsCompactDescription[0], self.columnsCompactDescription[1], self.columnsCompactDescription[2]
			res.append(MultiContentEntryText(pos=(0, 0), size=(width-fc, ih1), font = 0, flags = RT_HALIGN_LEFT, text = txt))
			res.append(MultiContentEntryText(pos=(0, ih1), size=(width-sc-lc, ih-ih1), font=1, flags=RT_HALIGN_LEFT, text=description))
			res.append(MultiContentEntryText(pos=(width-fc, 6), size=(fc, ih1), font=1, flags=RT_HALIGN_RIGHT, text=begin_string))
			if service is not None:
				res.append(MultiContentEntryText(pos=(width-sc-lc, ih1), size=(sc, ih-ih1), font = 1, flags = RT_HALIGN_RIGHT, text = service.getServiceName()))
			res.append(MultiContentEntryText(pos=(width-lc, ih1), size=(lc, ih1), font=1, flags=RT_HALIGN_RIGHT, text=len))
		elif self.list_type == MovieList.LISTTYPE_COMPACT:
			ih1 = ((ih * 8) + 14) / 15 # 37 -> 20, round up
			lc, col = self.compactColumn[0], self.compactColumn[1]
			res.append(MultiContentEntryText(pos=(0, 0), size=(width-lc-2, ih1), font = 0, flags = RT_HALIGN_LEFT, text = txt))
			if self.tags:
				res.append(MultiContentEntryText(pos=(width-col, ih1), size=(col, ih-ih1), font = 1, flags = RT_HALIGN_RIGHT, text = tags))
				if service is not None:
					res.append(MultiContentEntryText(pos=(col, ih1), size=(col, ih-ih1), font = 1, flags = RT_HALIGN_LEFT, text = service.getServiceName()))
			else:
				if service is not None:
					res.append(MultiContentEntryText(pos=(width-col, ih1), size=(col, ih-ih1), font = 1, flags = RT_HALIGN_RIGHT, text = service.getServiceName()))
			res.append(MultiContentEntryText(pos=(0, ih1), size=(col, ih-ih1), font=1, flags=RT_HALIGN_LEFT, text=begin_string))
			res.append(MultiContentEntryText(pos=(width-lc, 0), size=(lc, ih1), font=0, flags=RT_HALIGN_RIGHT, text=len))
		else:
			assert(self.list_type == MovieList.LISTTYPE_MINIMAL)
			if self.descr_state == MovieList.SHOW_DESCRIPTION:
				dateSize = ih * 145 / 20   # 20 -> 145
				res.append(MultiContentEntryText(pos=(0, 0), size=(width-dateSize, ih), font = 0, flags = RT_HALIGN_LEFT, text = txt))
				res.append(MultiContentEntryText(pos=(width-dateSize, 4), size=(dateSize, ih), font=1, flags=RT_HALIGN_RIGHT, text=begin_string))
			else:
				lenSize = ih * 75 / 20 # 20 -> 75
				res.append(MultiContentEntryText(pos=(0, 0), size=(width-lenSize-2, ih), font = 0, flags = RT_HALIGN_LEFT, text = txt))
				res.append(MultiContentEntryText(pos=(width-lenSize, 0), size=(lenSize, ih), font=0, flags=RT_HALIGN_RIGHT, text=len))
		
		return res

	def moveToIndex(self, index):
		self.instance.moveSelectionTo(index)

	def getCurrentIndex(self):
		return self.instance.getCurrentIndex()

	def getCurrentEvent(self):
		l = self.l.getCurrentSelection()
		return l and l[0] and l[1] and l[1].getEvent(l[0])

	def getCurrent(self):
		l = self.l.getCurrentSelection()
		return l and l[0]

	GUI_WIDGET = eListbox

	def postWidgetCreate(self, instance):
		instance.setContent(self.l)
		instance.selectionChanged.get().append(self.selectionChanged)

	def preWidgetRemove(self, instance):
		instance.setContent(None)
		instance.selectionChanged.get().remove(self.selectionChanged)

	def reload(self, root = None, filter_tags = None):
		if root is not None:
			self.load(root, filter_tags)
		else:
			self.load(self.root, filter_tags)
		self.l.setList(self.list)

	def removeService(self, service):
		for l in self.list[:]:
			if l[0] == service:
				self.list.remove(l)
		self.l.setList(self.list)

	def __len__(self):
		return len(self.list)

	def load(self, root, filter_tags):
		# this lists our root service, then building a 
		# nice list
		
		self.list = [ ]
		self.serviceHandler = eServiceCenter.getInstance()
		
		self.root = root
		list = self.serviceHandler.list(root)
		if list is None:
			print "listing of movies failed"
			list = [ ]	
			return
		tags = set()
		
		while 1:
			serviceref = list.getNext()
			if not serviceref.valid():
				break
			if serviceref.flags & eServiceReference.mustDescent:
				continue
		
			info = self.serviceHandler.info(serviceref)
			if info is None:
				continue
			begin = info.getInfo(serviceref, iServiceInformation.sTimeCreate)
		
			# convert space-seperated list of tags into a set
			this_tags = info.getInfoString(serviceref, iServiceInformation.sTags).split(' ')
			if this_tags == ['']:
				this_tags = []
			this_tags = set(this_tags)
			tags |= this_tags
		
			# filter_tags is either None (which means no filter at all), or 
			# a set. In this case, all elements of filter_tags must be present,
			# otherwise the entry will be dropped.			
			if filter_tags is not None and not this_tags.issuperset(filter_tags):
				continue
		
			self.list.append((serviceref, info, begin, -1))
		
		if self.sort_type == MovieList.SORT_ALPHANUMERIC:
			self.list.sort(key=self.buildAlphaNumericSortKey)
		else:
			# sort: key is 'begin'
			self.list.sort(key=lambda x: -x[2])
		
		# finally, store a list of all tags which were found. these can be presented
		# to the user to filter the list
		self.tags = tags

	def buildAlphaNumericSortKey(self, x):
		ref = x[0]
		info = self.serviceHandler.info(ref)
		name = info and info.getName(ref)
		return (name and name.lower() or "", -x[2])

	def moveTo(self, serviceref):
		count = 0
		for x in self.list:
			if x[0] == serviceref:
				self.instance.moveSelectionTo(count)
				return True
			count += 1
		return False
	
	def moveDown(self):
		self.instance.moveSelection(self.instance.moveDown)
