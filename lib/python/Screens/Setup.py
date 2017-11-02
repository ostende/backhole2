from Screen import Screen
from Components.ActionMap import NumberActionMap
from Components.config import config, ConfigNothing
from Components.SystemInfo import SystemInfo
from Components.ConfigList import ConfigListScreen
from Components.Sources.StaticText import StaticText
from enigma import eEnv

import xml.etree.cElementTree

# FIXME: use resolveFile!
# read the setupmenu
try:
	# first we search in the current path
	setupfile = file('data/setup.xml', 'r')
except:
	# if not found in the current path, we use the global datadir-path
	setupfile = file(eEnv.resolve('${datadir}/enigma2/setup.xml'), 'r')
setupdom = xml.etree.cElementTree.parse(setupfile)
setupfile.close()

def getConfigMenuItem(configElement):
	for item in setupdom.getroot().findall('./setup/item/.'):
		if item.text == configElement:
			return _(item.attrib["text"]), eval(configElement)
	return "", None

class SetupError(Exception):
    def __init__(self, message):
        self.msg = message

    def __str__(self):
        return self.msg

class SetupSummary(Screen):

	def __init__(self, session, parent):

		Screen.__init__(self, session, parent = parent)
		self["SetupTitle"] = StaticText(_(parent.setup_title))
		self["SetupEntry"] = StaticText("")
		self["SetupValue"] = StaticText("")
		self.onShow.append(self.addWatcher)
		self.onHide.append(self.removeWatcher)

	def addWatcher(self):
		self.parent.onChangedEntry.append(self.selectionChanged)
		self.parent["config"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def removeWatcher(self):
		self.parent.onChangedEntry.remove(self.selectionChanged)
		self.parent["config"].onSelectionChanged.remove(self.selectionChanged)

	def selectionChanged(self):
		self["SetupEntry"].text = self.parent.getCurrentEntry()
		self["SetupValue"].text = self.parent.getCurrentValue()

class Setup(ConfigListScreen, Screen):

	ALLOW_SUSPEND = True

	def removeNotifier(self):
		config.usage.setup_level.notifiers.remove(self.levelChanged)

	def levelChanged(self, configElement):
		list = []
		self.refill(list)
		self["config"].setList(list)

	def removeEntryNotifier(self):
		if self.needEntryChange:
			for item in self.needEntryChange:
				if self.entryChanged in item.notifiers:
					item.notifiers.remove(self.entryChanged)

	def entryChanged(self, configElement):
		list = []
		self.refill(list)
		self["config"].setList(list)

	def refill(self, list):
		xmldata = setupdom.getroot()
		for x in xmldata.findall("setup"):
			if x.get("key") != self.setup:
				continue
			self.addItems(list, x);
			self.setup_title = x.get("title", "").encode("UTF-8")

	def __init__(self, session, setup):
		Screen.__init__(self, session)
		# for the skin: first try a setup_<setupID>, then Setup
		self.skinName = ["setup_" + setup, "Setup" ]

		self.onChangedEntry = [ ]

		self.needEntryChange = [ ]

		self.setup = setup
		list = []
		self.refill(list)

		#check for list.entries > 0 else self.close
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))

		self["actions"] = NumberActionMap(["SetupActions"], 
			{
				"cancel": self.keyCancel,
				"save": self.keySave,
			}, -2)

		ConfigListScreen.__init__(self, list, session = session, on_change = self.changedEntry)

		self.changedEntry()
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(_(self.setup_title))

	# for summary:
	def changedEntry(self):
		for x in self.onChangedEntry:
			x()

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())

	def createSummary(self):
		return SetupSummary

	def addItems(self, list, parentNode):
		self.needEntryChange = [ ]
		for x in parentNode:
			if x.tag == 'item':
				item_level = int(x.get("level", 0))

				if not self.levelChanged in config.usage.setup_level.notifiers:
					config.usage.setup_level.notifiers.append(self.levelChanged)
					self.onClose.append(self.removeNotifier)

				if item_level > config.usage.setup_level.index:
					continue

				requires = x.get("requires")
				if requires and not SystemInfo.get(requires, False):
					continue;

				item_text = _(x.get("text", "??").encode("UTF-8"))
				b = eval(x.text or "");
				if b == "":
					continue
				#add to configlist
				item = b
				# the first b is the item itself, ignored by the configList.
				# the second one is converted to string.
				if not isinstance(item, ConfigNothing):
					list.append( (item_text, item) )

					needentrychange = x.get("entrychange")
					if needentrychange == "yes":
						self.needEntryChange.append(item)
						if not self.entryChanged in item.notifiers:
							item.notifiers.append(self.entryChanged)
						if not self.removeEntryNotifier in self.onClose:
							self.onClose.append(self.removeEntryNotifier)

def getSetupTitle(id):
	xmldata = setupdom.getroot()
	for x in xmldata.findall("setup"):
		if x.get("key") == id:
			return x.get("title", "").encode("UTF-8")
	raise SetupError("unknown setup id '%s'!" % repr(id))
