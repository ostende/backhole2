from Components.Harddisk import harddiskmanager
from Components.NimManager import nimmanager
from config import ConfigSubsection, ConfigYesNo, config, ConfigSelection, ConfigText, ConfigNumber, ConfigSet, ConfigLocations
from Tools.Directories import resolveFilename, SCOPE_HDD
from enigma import eDVBDB, Misc_Options, eEnv
from enigma import setTunerTypePriorityOrder, setPreferredTuner
from SystemInfo import SystemInfo
import os

def InitUsageConfig():
	config.usage = ConfigSubsection();
	config.usage.showdish = ConfigYesNo(default = True)
	config.usage.multibouquet = ConfigYesNo(default = True)
	config.usage.multiepg_ask_bouquet = ConfigYesNo(default = False)

	config.usage.alternative_number_mode = ConfigYesNo(default = False)
	def alternativeNumberModeChange(configElement):
    		eDVBDB.getInstance().setNumberingMode(configElement.value)
    		refreshServiceList()
	config.usage.alternative_number_mode.addNotifier(alternativeNumberModeChange)

	config.usage.hide_number_markers = ConfigYesNo(default = False)
	config.usage.hide_number_markers.addNotifier(refreshServiceList)

	config.usage.quickzap_bouquet_change = ConfigYesNo(default = False)
	config.usage.e1like_radio_mode = ConfigYesNo(default = False)
	config.usage.infobar_timeout = ConfigSelection(default = "5", choices = [
		("0", _("no timeout")), ("1", "1 " + _("second")), ("2", "2 " + _("seconds")), ("3", "3 " + _("seconds")),
		("4", "4 " + _("seconds")), ("5", "5 " + _("seconds")), ("6", "6 " + _("seconds")), ("7", "7 " + _("seconds")),
		("8", "8 " + _("seconds")), ("9", "9 " + _("seconds")), ("10", "10 " + _("seconds"))])
	config.usage.show_infobar_on_zap = ConfigYesNo(default = True)
	config.usage.show_infobar_on_skip = ConfigYesNo(default = True)
	config.usage.show_infobar_on_event_change = ConfigYesNo(default = True)
	config.usage.show_eit_nownext = ConfigYesNo(default = True)
	config.usage.hide_zap_errors = ConfigYesNo(default = False)
	config.usage.hide_ci_messages = ConfigYesNo(default = False)
	config.usage.hdd_standby = ConfigSelection(default = "600", choices = [
		("0", _("no standby")), ("10", "10 " + _("seconds")), ("30", "30 " + _("seconds")),
		("60", "1 " + _("minute")), ("120", "2 " + _("minutes")),
		("300", "5 " + _("minutes")), ("600", "10 " + _("minutes")), ("1200", "20 " + _("minutes")),
		("1800", "30 " + _("minutes")), ("3600", "1 " + _("hour")), ("7200", "2 " + _("hours")),
		("14400", "4 " + _("hours")) ])
	config.usage.output_12V = ConfigSelection(default = "do not change", choices = [
		("do not change", _("do not change")), ("off", _("off")), ("on", _("on")) ])

	config.usage.pip_zero_button = ConfigSelection(default = "standard", choices = [
		("standard", _("standard")), ("swap", _("swap PiP and main picture")),
		("swapstop", _("move PiP to main picture")), ("stop", _("stop PiP")) ])

	config.usage.default_path = ConfigText(default = resolveFilename(SCOPE_HDD))
	config.usage.timer_path = ConfigText(default = "<default>")
	config.usage.instantrec_path = ConfigText(default = "<default>")
	config.usage.timeshift_path = ConfigText(default = "/media/hdd/")
	config.usage.allowed_timeshift_paths = ConfigLocations(default = ["/media/hdd/"])

	config.usage.on_movie_start = ConfigSelection(default = "ask", choices = [
		("ask", _("Ask user")), ("resume", _("Resume from last position")), ("beginning", _("Start from the beginning")) ])
	config.usage.on_movie_stop = ConfigSelection(default = "ask", choices = [
		("ask", _("Ask user")), ("movielist", _("Return to movie list")), ("quit", _("Return to previous service")) ])
	config.usage.on_movie_eof = ConfigSelection(default = "ask", choices = [
		("ask", _("Ask user")), ("movielist", _("Return to movie list")), ("quit", _("Return to previous service")), ("pause", _("Pause movie at end")) ])

	config.usage.setup_level = ConfigSelection(default = "intermediate", choices = [
		("simple", _("Simple")),
		("intermediate", _("Intermediate")),
		("expert", _("Expert")) ])

	config.usage.on_long_powerpress = ConfigSelection(default = "show_menu", choices = [
		("show_menu", _("show shutdown menu")),
		("shutdown", _("immediate shutdown")),
		("standby", _("Standby")) ] )
	
	config.usage.on_short_powerpress = ConfigSelection(default = "standby", choices = [
		("show_menu", _("show shutdown menu")),
		("shutdown", _("immediate shutdown")),
		("standby", _("Standby")) ] )


	config.usage.alternatives_priority = ConfigSelection(default = "0", choices = [
		("0", "DVB-S/-C/-T"),
		("1", "DVB-S/-T/-C"),
		("2", "DVB-C/-S/-T"),
		("3", "DVB-C/-T/-S"),
		("4", "DVB-T/-C/-S"),
		("5", "DVB-T/-S/-C") ])

	config.usage.service_icon_enable = ConfigYesNo(default = False)
	config.usage.service_icon_enable.addNotifier(refreshServiceList)

	config.usage.show_event_progress_in_servicelist = ConfigYesNo(default = True)
		
	config.usage.show_event_progress_in_servicelist.addNotifier(refreshServiceList)

	nims = [ ("-1", _("auto")) ]
	for x in nimmanager.nim_slots:
		nims.append( (str(x.slot), x.getSlotName()) )
	config.usage.frontend_priority = ConfigSelection(default = "-1", choices = nims)

	config.usage.blinking_display_clock_during_recording = ConfigYesNo(default = False)

	config.usage.show_message_when_recording_starts = ConfigYesNo(default = True)

	config.usage.load_length_of_movies_in_moviellist = ConfigYesNo(default = True)
	
	def TunerTypePriorityOrderChanged(configElement):
		setTunerTypePriorityOrder(int(configElement.value))
	config.usage.alternatives_priority.addNotifier(TunerTypePriorityOrderChanged, immediate_feedback=False)

	def PreferredTunerChanged(configElement):
		setPreferredTuner(int(configElement.value))
	config.usage.frontend_priority.addNotifier(PreferredTunerChanged)

	def setHDDStandby(configElement):
		for hdd in harddiskmanager.HDDList():
			hdd[1].setIdleTime(int(configElement.value))
	config.usage.hdd_standby.addNotifier(setHDDStandby, immediate_feedback=False)

	def set12VOutput(configElement):
		if configElement.value == "on":
			Misc_Options.getInstance().set_12V_output(1)
		elif configElement.value == "off":
			Misc_Options.getInstance().set_12V_output(0)
	config.usage.output_12V.addNotifier(set12VOutput, immediate_feedback=False)

	SystemInfo["12V_Output"] = Misc_Options.getInstance().detected_12V_output()

	config.usage.keymap = ConfigText(default = eEnv.resolve("${datadir}/enigma2/keymap.xml"))

	config.seek = ConfigSubsection()
	config.seek.selfdefined_13 = ConfigNumber(default=15)
	config.seek.selfdefined_46 = ConfigNumber(default=60)
	config.seek.selfdefined_79 = ConfigNumber(default=300)

	config.seek.speeds_forward = ConfigSet(default=[2, 4, 8, 16, 32, 64, 128], choices=[2, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128])
	config.seek.speeds_backward = ConfigSet(default=[2, 4, 8, 16, 32, 64, 128], choices=[1, 2, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128])
	config.seek.speeds_slowmotion = ConfigSet(default=[2, 4, 8], choices=[2, 4, 6, 8, 12, 16, 25])

	config.seek.enter_forward = ConfigSelection(default = "2", choices = ["2", "4", "6", "8", "12", "16", "24", "32", "48", "64", "96", "128"])
	config.seek.enter_backward = ConfigSelection(default = "1", choices = ["1", "2", "4", "6", "8", "12", "16", "24", "32", "48", "64", "96", "128"])

	config.seek.on_pause = ConfigSelection(default = "play", choices = [
		("play", _("Play")),
		("step", _("Singlestep (GOP)")),
		("last", _("Last speed")) ])

	config.usage.timerlist_finished_timer_position = ConfigSelection(default = "beginning", choices = [("beginning", _("at beginning")), ("end", _("at end"))])

	def updateEnterForward(configElement):
		if not configElement.value:
			configElement.value = [2]
		updateChoices(config.seek.enter_forward, configElement.value)

	config.seek.speeds_forward.addNotifier(updateEnterForward, immediate_feedback = False)

	def updateEnterBackward(configElement):
		if not configElement.value:
			configElement.value = [2]
		updateChoices(config.seek.enter_backward, configElement.value)

	config.seek.speeds_backward.addNotifier(updateEnterBackward, immediate_feedback = False)

	config.subtitles = ConfigSubsection()
	config.subtitles.subtitle_fontcolor = ConfigSelection(default = "0", choices = [
		("0", _("default")),
		("1", _("white")),
		("2", _("yellow")),
		("3", _("green")),
		("4", _("cyan")),
		("5", _("blue")),
		("6", _("magneta")),
		("7", _("red")),
		("8", _("black")) ])
	config.subtitles.subtitle_fontsize  = ConfigSelection(choices = ["%d" % x for x in range(16,101) if not x % 2], default = "40")
	config.subtitles.subtitle_bgcolor = ConfigSelection(default = "0", choices = [
		("0", _("black")),
		("1", _("red")),
		("2", _("magneta")),
		("3", _("blue")),
		("4", _("cyan")),
		("5", _("green")),
		("6", _("yellow")),
		("7", _("white"))])
	config.subtitles.subtitle_bgopacity = ConfigSelection(default = "225", choices = [
		("0", _("No transparency")),
		("25", "10%"),
		("50", "20%"),
		("75", "30%"),
		("100", "40%"),
		("125", "50%"),
		("150", "60%"),
		("175", "70%"),
		("200", "80%"),
		("225", "90%"),
		("255", _("full transparency"))])

	config.subtitles.subtitle_edgestyle = ConfigSelection(default = "2", choices = [
		("0", "None"),
		("1", "Raised"),
		("2", "Depressed"),
		("3", "Uniform")])
	config.subtitles.subtitle_edgestyle_level = ConfigSelection(choices = ["0", "1", "2", "3", "4", "5"], default = "3")
	config.subtitles.subtitle_opacity = ConfigSelection(default = "0", choices = [
		("0", _("No transparency")),
		("75", "25%"),
		("150", "50%")])
	config.subtitles.subtitle_original_position = ConfigYesNo(default = True)
	config.subtitles.subtitle_alignment = ConfigSelection(choices = [("left", _("left")), ("center", _("center")), ("right", _("right"))], default = "center")
	config.subtitles.subtitle_position = ConfigSelection( choices = ["0", "50", "100", "150", "200", "250", "300", "350", "400", "450", "500", "550", "600"], default = "100")

	config.subtitles.dvb_subtitles_centered = ConfigYesNo(default = False)

	subtitle_delay_choicelist = []
	for i in range(-900000, 1845000, 45000):
		if i == 0:
			subtitle_delay_choicelist.append(("0", _("No delay")))
		else:
			subtitle_delay_choicelist.append((str(i), "%2.1f sec" % (i / 90000.)))
	config.subtitles.subtitle_noPTSrecordingdelay = ConfigSelection(default = "315000", choices = subtitle_delay_choicelist)
	config.subtitles.subtitle_bad_timing_delay = ConfigSelection(default = "0", choices = subtitle_delay_choicelist)
	config.subtitles.subtitle_rewrap = ConfigYesNo(default = False)
	config.subtitles.colourise_dialogs = ConfigYesNo(default = False)
	config.subtitles.pango_subtitle_fontswitch = ConfigYesNo(default = True)
	config.subtitles.pango_subtitles_delay = ConfigSelection(default = "0", choices = subtitle_delay_choicelist)
	config.subtitles.pango_subtitles_fps = ConfigSelection(default = "1", choices = [
		("1", _("Original")),
		("23976", _("23.976")),
		("24000", _("24")),
		("25000", _("25")),
		("29970", _("29.97")),
		("30000", _("30"))])
	config.subtitles.pango_autoturnon = ConfigYesNo(default = True)
	
	config.autolanguage = ConfigSubsection()
	audio_language_choices=[
		("---", _("None")),
		("und", _("Undetermined")),
		("orj dos ory org esl qaa und mis mul ORY ORJ Audio_ORJ", _("Original")),
		("ara", _("Arabic")),
		("eus baq", _("Basque")),
		("bul", _("Bulgarian")),
		("hrv", _("Croatian")),
		("ces cze", _("Czech")),
		("dan", _("Danish")),
		("dut ndl nld Dutch", _("Dutch")),
		("eng qaa Englisch", _("English")),
		("est", _("Estonian")),
		("fin", _("Finnish")),
		("fra fre", _("French")),
		("deu ger", _("German")),
		("ell gre", _("Greek")),
		("heb", _("Hebrew")),
		("hun", _("Hungarian")),
		("ita", _("Italian")),
		("lav", _("Latvian")),
		("lit", _("Lithuanian")),
		("ltz", _("Luxembourgish")),
		("nor", _("Norwegian")),
		("pol", _("Polish")),
		("por", _("Portuguese")),
		("fas per", _("Persian")),
		("ron rum", _("Romanian")),
		("rus", _("Russian")),
		("srp", _("Serbian")),
		("slk slo", _("Slovak")),
		("slv", _("Slovenian")),
		("spa", _("Spanish")),
		("swe", _("Swedish")),
		("tha", _("Thai")),
		("tur Audio_TUR", _("Turkish")),
		("ukr Ukr", _("Ukrainian")),
		("NAR", _("Visual impaired commentary")),
		]
	
	config.autolanguage.audio_autoselect1 = ConfigSelection(choices=audio_language_choices, default="---")
	config.autolanguage.audio_autoselect2 = ConfigSelection(choices=audio_language_choices, default="---")
	config.autolanguage.audio_autoselect3 = ConfigSelection(choices=audio_language_choices, default="---")
	config.autolanguage.audio_autoselect4 = ConfigSelection(choices=audio_language_choices, default="---")
	config.autolanguage.audio_defaultac3 = ConfigYesNo(default = False)
	config.autolanguage.audio_usecache = ConfigYesNo(default = True)

	subtitle_language_choices = audio_language_choices[:1] + audio_language_choices [2:]
	config.autolanguage.subtitle_autoselect1 = ConfigSelection(choices=subtitle_language_choices, default="---")
	config.autolanguage.subtitle_autoselect2 = ConfigSelection(choices=subtitle_language_choices, default="---")
	config.autolanguage.subtitle_autoselect3 = ConfigSelection(choices=subtitle_language_choices, default="---")
	config.autolanguage.subtitle_autoselect4 = ConfigSelection(choices=subtitle_language_choices, default="---")
	config.autolanguage.subtitle_hearingimpaired = ConfigYesNo(default = False)
	config.autolanguage.subtitle_defaultimpaired = ConfigYesNo(default = False)
	config.autolanguage.subtitle_defaultdvb = ConfigYesNo(default = False)
	config.autolanguage.subtitle_usecache = ConfigYesNo(default = True)

def updateChoices(sel, choices):
	if choices:
		defval = None
		val = int(sel.value)
		if not val in choices:
			tmp = choices[:]
			tmp.reverse()
			for x in tmp:
				if x < val:
					defval = str(x)
					break
		sel.setChoices(map(str, choices), defval)

def preferredPath(path):
	if config.usage.setup_level.index < 2 or path == "<default>":
		return None  # config.usage.default_path.value, but delay lookup until usage
	elif path == "<current>":
		return config.movielist.last_videodir.value
	elif path == "<timer>":
		return config.movielist.last_timer_videodir.value
	else:
		return path

def preferredTimerPath():
	return preferredPath(config.usage.timer_path.value)

def preferredInstantRecordPath():
	return preferredPath(config.usage.instantrec_path.value)

def defaultMoviePath():
	return config.usage.default_path.value

def refreshServiceList(configElement = None):
	from Screens.InfoBar import InfoBar
	InfoBarInstance = InfoBar.instance
	if InfoBarInstance is not None:
		servicelist = InfoBarInstance.servicelist
		if servicelist:
			servicelist.setMode()
