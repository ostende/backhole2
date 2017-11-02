installdir = $(pkglibdir)/python/Plugins/Extensions

SUBDIRS = TuxboxPlugins CutListEditor PicturePlayer MediaScanner MediaPlayer GraphMultiEPG SocketMMI DVDBurn Modem WebBrowser \
	StreamTV DLNABrowser DLNAServer HbbTV BackupSuiteUSB BackupSuiteHDD SatipClient MiniTV QuadPiP

if HAVE_LIBDDVD
SUBDIRS += DVDPlayer
endif

install_PYTHON =	\
	__init__.py
