from enigma import eDVBResourceManager
from Tools.Directories import fileExists
from Tools.HardwareInfo import HardwareInfo

SystemInfo = { }

#FIXMEE...
def getNumVideoDecoders():
	idx = 0
	while fileExists("/dev/dvb/adapter0/video%d"%(idx), 'f'):
		idx += 1
	return idx

SystemInfo["NumVideoDecoders"] = getNumVideoDecoders()
SystemInfo["CanMeasureFrontendInputPower"] = eDVBResourceManager.getInstance().canMeasureFrontendInputPower()


def countFrontpanelLEDs():
	leds = 0
	if fileExists("/proc/stb/fp/led_set_pattern"):
		leds += 1

	while fileExists("/proc/stb/fp/led%d_pattern" % leds):
		leds += 1

	return leds

SystemInfo["NumFrontpanelLEDs"] = countFrontpanelLEDs()
SystemInfo["FrontpanelDisplay"] = fileExists("/dev/dbox/oled0") or fileExists("/dev/dbox/lcd0")
SystemInfo["FrontpanelDisplayGrayscale"] = fileExists("/dev/dbox/oled0")
SystemInfo["DeepstandbySupport"] = HardwareInfo().get_device_name() != "dm800"
SystemInfo["HdmiInSupport"] = HardwareInfo().get_vu_device_name() == "ultimo4k"
SystemInfo["WOWLSupport"] = HardwareInfo().get_vu_device_name() == "ultimo4k"
SystemInfo["ScrambledPlayback"] = HardwareInfo().get_vu_device_name() in ("solo4k", "ultimo4k")
SystemInfo["FastChannelChange"] =  fileExists("/proc/stb/frontend/fbc/fcc")
SystemInfo["MiniTV"] = fileExists("/proc/stb/lcd/live_enable")

