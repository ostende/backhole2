# for localized messages
from . import _
from Plugins.Plugin import PluginDescriptor
from Screens.Console import Console
from Screens.MessageBox import MessageBox 
from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_LANGUAGE
from os import environ as os_environ
import gettext

def localeInit():
	lang = language.getLanguage()[:2] # getLanguage returns e.g. "fi_FI" for "language_country"
	os_environ["LANGUAGE"] = lang # Enigma doesn't set this (or LC_ALL, LC_MESSAGES, LANG). gettext needs it!
	gettext.bindtextdomain("BackupSuite", resolveFilename(SCOPE_PLUGINS, "Extensions/BackupSuiteHDD/locale"))

def _(txt):
	t = gettext.dgettext("BackupSuite", txt)
	if t == txt:
		print "[BackupSuite] fallback to default translation for", txt
		t = gettext.gettext(txt)
	return t

localeInit()
language.addCallback(localeInit)


def runbackup(session, result):
	if result:
		session.open(Console, title = _("Full back-up to USB"), cmdlist = [_("sh '/usr/lib/enigma2/python/Plugins/Extensions/BackupSuiteUSB/backup.sh' en_EN")])


def main(session, **kwargs):
	session.openWithCallback(lambda r: runbackup(session, r), MessageBox, _("Do you want to make a back-up on USB?\n\nThis only takes a few minutes depending on the used filesystem and is fully automatic.\n\nMake sure you first insert an USB flash drive before you select Yes.") , MessageBox.TYPE_YESNO, timeout = 20, default = True)

def Plugins(**kwargs):
	return [PluginDescriptor(name=_("Full back-up to USB"), 
			description = _("Full 1:1 back-up direct on USB"), 
			where = PluginDescriptor.WHERE_PLUGINMENU, 
			fnc = main, 
			icon="plugin.png")]
