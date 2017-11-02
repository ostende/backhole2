from Screen import Screen
from Components.Language import language
from enigma import eConsoleAppContainer

from Components.ActionMap import ActionMap
from Components.PluginComponent import plugins
from Components.PluginList import *
from Components.Label import Label
from Screens.MessageBox import MessageBox
from Screens.Console import Console
from Plugins.Plugin import PluginDescriptor
from Tools.Directories import resolveFilename, fileExists, SCOPE_PLUGINS, SCOPE_SKIN_IMAGE
from Tools.LoadPixmap import LoadPixmap

from time import time

import os
import glob

def languageChanged():
	plugins.clearPluginList()
	plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))

class PluginBrowser(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		
		self["red"] = Label()
		self["green"] = Label()
		
		self.list = []
		self["list"] = PluginList(self.list)
		
		self["actions"] = ActionMap(["WizardActions"],
		{
			"ok": self.save,
			"back": self.close,
		})
		self["PluginDownloadActions"] = ActionMap(["ColorActions"],
		{
			"red": self.delete,
			"green": self.download
		})
		self["SoftwareActions"] = ActionMap(["ColorActions"],
		{
			"red": self.openExtensionmanager
		})
		self["PluginDownloadActions"].setEnabled(False)
		self["SoftwareActions"].setEnabled(False)
		self.onFirstExecBegin.append(self.checkWarnings)
		self.onShown.append(self.updateList)
		self.onLayoutFinish.append(self.saveListsize)

	def saveListsize(self):
		listsize = self["list"].instance.size()
		self.listWidth = listsize.width()
		self.listHeight = listsize.height()
	
	def checkWarnings(self):
		if len(plugins.warnings):
			text = _("Some plugins are not available:\n")
			for (pluginname, error) in plugins.warnings:
				text += _("%s (%s)\n") % (pluginname, error)
			plugins.resetWarnings()
			self.session.open(MessageBox, text = text, type = MessageBox.TYPE_WARNING)

	def save(self):
		self.run()
	
	def run(self):
		plugin = self["list"].l.getCurrentSelection()[0]
		plugin(session=self.session)
		
	def updateList(self):
		self.pluginlist = plugins.getPlugins(PluginDescriptor.WHERE_PLUGINMENU)
		self.list = [PluginEntryComponent(plugin, self.listWidth) for plugin in self.pluginlist]
		self["list"].l.setList(self.list)
		if fileExists(resolveFilename(SCOPE_PLUGINS, "SystemPlugins/SoftwareManager/plugin.py")):
			self["red"].setText(_("Manage extensions"))
			self["green"].setText("")
			self["SoftwareActions"].setEnabled(True)
			self["PluginDownloadActions"].setEnabled(False)
		else:
			self["red"].setText(_("Remove Plugins"))
			self["green"].setText(_("Download Plugins"))
			self["SoftwareActions"].setEnabled(False)
			self["PluginDownloadActions"].setEnabled(True)
			
	def delete(self):
		self.session.openWithCallback(self.PluginDownloadBrowserClosed, PluginDownloadBrowser, PluginDownloadBrowser.REMOVE)
	
	def download(self):
		self.session.openWithCallback(self.PluginDownloadBrowserClosed, PluginDownloadBrowser, PluginDownloadBrowser.DOWNLOAD)

	def PluginDownloadBrowserClosed(self):
		self.updateList()
		self.checkWarnings()

	def openExtensionmanager(self):
		if fileExists(resolveFilename(SCOPE_PLUGINS, "SystemPlugins/SoftwareManager/plugin.py")):
			try:
				from Plugins.SystemPlugins.SoftwareManager.plugin import PluginManager
			except ImportError:
				self.session.open(MessageBox, _("The Softwaremanagement extension is not installed!\nPlease install it."), type = MessageBox.TYPE_INFO,timeout = 10 )
			else:
				self.session.openWithCallback(self.PluginDownloadBrowserClosed, PluginManager)

class PluginDownloadBrowser(Screen):
	DOWNLOAD = 0
	REMOVE = 1
	lastDownloadDate = None

	def __init__(self, session, type):
		Screen.__init__(self, session)
		
		self.type = type
		
		self.container = eConsoleAppContainer()
		self.container.appClosed.append(self.runFinished)
		self.container.dataAvail.append(self.dataAvail)
		self.onLayoutFinish.append(self.startRun)
		self.onShown.append(self.setWindowTitle)
		
		self.list = []
		self["list"] = PluginList(self.list)
		self.pluginlist = []
		self.expanded = []
		self.installedplugins = []
		
		if self.type == self.DOWNLOAD:
			self["text"] = Label(_("Downloading plugin information. Please wait..."))
		elif self.type == self.REMOVE:
			self["text"] = Label(_("Getting plugin information. Please wait..."))
		
		self.run = 0

		self.remainingdata = ""

		self["actions"] = ActionMap(["WizardActions"], 
		{
			"ok": self.go,
			"back": self.close,
		})
		
	def go(self):
		sel = self["list"].l.getCurrentSelection()

		if sel is None:
			return

		sel = sel[0]
		if isinstance(sel, str): # category
			if sel in self.expanded:
				self.expanded.remove(sel)
			else:
				self.expanded.append(sel)
			self.updateList()
		else:
			if self.type == self.DOWNLOAD:
				self.session.openWithCallback(self.runInstall, MessageBox, _("Do you really want to download\nthe plugin \"%s\"?") % sel.name)
			elif self.type == self.REMOVE:
				self.session.openWithCallback(self.runInstall, MessageBox, _("Do you really want to REMOVE\nthe plugin \"%s\"?") % sel.name)

	def runInstall(self, val):
		if val:
			if self.type == self.DOWNLOAD:
				self.session.openWithCallback(self.installFinished, Console, cmdlist = ["opkg install " + "enigma2-plugin-" + self["list"].l.getCurrentSelection()[0].name])
			elif self.type == self.REMOVE:
				self.session.openWithCallback(self.installFinished, Console, cmdlist = ["opkg remove " + "enigma2-plugin-" + self["list"].l.getCurrentSelection()[0].name])

	def setWindowTitle(self):
		if self.type == self.DOWNLOAD:
			self.setTitle(_("Downloadable new plugins"))
		elif self.type == self.REMOVE:
			self.setTitle(_("Remove plugins"))

	def startIpkgListInstalled(self):
		self.container.execute("opkg list_installed enigma2-plugin-*")

	def startIpkgListAvailable(self):
		self.container.execute("opkg list enigma2-plugin-*")

	def startRun(self):
		listsize = self["list"].instance.size()
		self["list"].instance.hide()
		self.listWidth = listsize.width()
		self.listHeight = listsize.height()
		if self.type == self.DOWNLOAD:
			if not PluginDownloadBrowser.lastDownloadDate or (time() - PluginDownloadBrowser.lastDownloadDate) > 3600:
				# Only update from internet once per hour
				self.container.execute("opkg update")
				PluginDownloadBrowser.lastDownloadDate = time()
			else:
				self.run = 1
				self.startIpkgListInstalled()
		elif self.type == self.REMOVE:
			self.run = 1
			self.startIpkgListInstalled()

	def installFinished(self):
		plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))
		self.container.appClosed.remove(self.runFinished)
		self.container.dataAvail.remove(self.dataAvail)
		self.close()

	def runFinished(self, retval):
		self.remainingdata = ""
		if self.run == 0:
			self.run = 1
			if self.type == self.DOWNLOAD:
				self.startIpkgListInstalled()
		elif self.run == 1 and self.type == self.DOWNLOAD:
			self.run = 2
			for x in self.getPluginListAvailable():
				if x[0] not in self.installedplugins:
					self.pluginlist.append(x)

			if self.pluginlist:
				self.pluginlist.sort()
				self.updateList()
				self["list"].instance.show()
			else:
				self["text"].setText(_("No new plugins found"))
		else:
			if len(self.pluginlist) > 0:
				self.updateList()
				self["list"].instance.show()
			else:
				self["text"].setText("No new plugins found")

	def dataAvail(self, str):
		#prepend any remaining data from the previous call
		str = self.remainingdata + str
		#split in lines
		lines = str.split('\n')
		#'str' should end with '\n', so when splitting, the last line should be empty. If this is not the case, we received an incomplete line
		if len(lines[-1]):
			#remember this data for next time
			self.remainingdata = lines[-1]
			lines = lines[0:-1]
		else:
			self.remainingdata = ""

		for x in lines:
			plugin = x.split(" - ", 2)
			if len(plugin) >= 2:
				if plugin[0].startswith('enigma2-plugin-') and not plugin[0].endswith('-dev') and not plugin[0].endswith('-staticdev') and not plugin[0].endswith('-dbg') and not plugin[0].endswith('-doc') and not plugin[0].endswith('-src'):
					if plugin[0] not in self.installedplugins:
						if self.run == 1 and self.type == self.DOWNLOAD:
							self.installedplugins.append(plugin[0])
						else:
							if len(plugin) == 2:
								plugin.append('')
							plugin.append(plugin[0][15:])
							self.pluginlist.append(plugin)

	def updateList(self):
		list = []
		expandableIcon = LoadPixmap(resolveFilename(SCOPE_SKIN_IMAGE, "skin_default/expandable-plugins.png"))
		expandedIcon = LoadPixmap(resolveFilename(SCOPE_SKIN_IMAGE, "skin_default/expanded-plugins.png"))
		verticallineIcon = LoadPixmap(resolveFilename(SCOPE_SKIN_IMAGE, "skin_default/verticalline-plugins.png"))
		
		self.plugins = {}
		for x in self.pluginlist:
			split = x[3].split('-', 1)
			if len(split) < 2:
				continue
			if not self.plugins.has_key(split[0]):
				self.plugins[split[0]] = []
				
			self.plugins[split[0]].append((PluginDescriptor(name = x[3], description = x[2], icon = verticallineIcon), split[1]))
			
		for x in self.plugins.keys():
			if x in self.expanded:
				list.append(PluginCategoryComponent(x, expandedIcon, self.listWidth))
				list.extend([PluginDownloadComponent(plugin[0], plugin[1], self.listWidth) for plugin in self.plugins[x]])
			else:
				list.append(PluginCategoryComponent(x, expandableIcon, self.listWidth))
		self.list = list
		self["list"].l.setList(list)

	def getPluginListAvailable(self):
			plugin_list = []
			# get feed names
			feeds = []
			for fn in glob.glob("/etc/opkg/*-feed.conf"):
				feeds.append(open(fn, 'r').read().split()[1])

			#get list_dir
			list_dir = "/var/lib/opkg"
			for line in open("/etc/opkg/opkg.conf", 'r'):
				if line.startswith('lists_dir'):
					list_dir = line.split()[-1]

			for feed in feeds:
				Package = None

				fn = os.path.join(list_dir, feed)
				if not os.path.exists(fn):
					continue

				for line in open(fn, 'r'):
					if line.startswith("Package:"):
						pkg = line.split(":", 1)[1].strip()
						if pkg.startswith('enigma2-plugin-') and not pkg.endswith('-dev') and not pkg.endswith('-staticdev') and not pkg.endswith('-dbg') and not pkg.endswith('-doc') and not pkg.endswith('-src'):
							Package = pkg
							Version = ''
							Description = ''
						continue

					if Package is None:
						continue

					if line.startswith("Version:"):
						Version = line.split(":", 1)[1].strip()

					elif line.startswith("Description:"):
						Description = line.split(":", 1)[1].strip()

					elif Description and line.startswith(' '):
						Description += line[:-1]

					elif len(line) <= 1:
						sp = Description.split(' ', 3)
						if sp[1] == "version":
							Description = sp[3].strip()

						pn = Package.split('enigma2-plugin-')[1]

						sp = Description.split(' ', 1)
						if sp[0] == pn and len(sp[1]) > 0:
							Description = sp[1].strip()

						plugin_list.append((Package, Version, Description, pn))
						Package = None

			return plugin_list

language.addCallback(languageChanged)
