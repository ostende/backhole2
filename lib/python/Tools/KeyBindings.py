
keyBindings = { }

from keyids import KEYIDS
from Components.config import config

deviceName = None

keyDescriptions = [{
		KEYIDS["BTN_0"]: ("UP", "fp"),
		KEYIDS["BTN_1"]: ("DOWN", "fp"),
		KEYIDS["KEY_OK"]: ("OK", ""),
		KEYIDS["KEY_UP"]: ("UP",),
		KEYIDS["KEY_DOWN"]: ("DOWN",),
		KEYIDS["KEY_POWER"]: ("POWER",),
		KEYIDS["KEY_RED"]: ("RED",),
		KEYIDS["KEY_BLUE"]: ("BLUE",),
		KEYIDS["KEY_GREEN"]: ("GREEN",),
		KEYIDS["KEY_YELLOW"]: ("YELLOW",),
		KEYIDS["KEY_MENU"]: ("MENU",),
		KEYIDS["KEY_LEFT"]: ("LEFT",),
		KEYIDS["KEY_RIGHT"]: ("RIGHT",),
		KEYIDS["KEY_VIDEO"]: ("PVR",),
		KEYIDS["KEY_INFO"]: ("INFO",),
		KEYIDS["KEY_AUDIO"]: ("YELLOW",),
		KEYIDS["KEY_TV"]: ("TV",),
		KEYIDS["KEY_RADIO"]: ("RADIO",),
		KEYIDS["KEY_TEXT"]: ("TEXT",),
		KEYIDS["KEY_NEXT"]: ("ARROWRIGHT",),
		KEYIDS["KEY_PREVIOUS"]: ("ARROWLEFT",),
		KEYIDS["KEY_PREVIOUSSONG"]: ("REWIND",),
		KEYIDS["KEY_PLAYPAUSE"]: ("PLAYPAUSE",),
		KEYIDS["KEY_PLAY"]: ("PLAY",),
		KEYIDS["KEY_NEXTSONG"]: ("FORWARD",),
		KEYIDS["KEY_CHANNELUP"]: ("BOUQUET+",),
		KEYIDS["KEY_CHANNELDOWN"]: ("BOUQUET-",),
		KEYIDS["KEY_0"]: ("0",),
		KEYIDS["KEY_1"]: ("1",),
		KEYIDS["KEY_2"]: ("2",),
		KEYIDS["KEY_3"]: ("3",),
		KEYIDS["KEY_4"]: ("4",),
		KEYIDS["KEY_5"]: ("5",),
		KEYIDS["KEY_6"]: ("6",),
		KEYIDS["KEY_7"]: ("7",),
		KEYIDS["KEY_8"]: ("8",),
		KEYIDS["KEY_9"]: ("9",),
		KEYIDS["KEY_EXIT"]: ("EXIT",),
		KEYIDS["KEY_STOP"]: ("STOP",),
		KEYIDS["KEY_RECORD"]: ("RECORD",),
		KEYIDS["KEY_SUBTITLE"]: ("SUBTITLE",)
	},
	{
		KEYIDS["BTN_0"]: ("UP", "fp"),
		KEYIDS["BTN_1"]: ("DOWN", "fp"),
		KEYIDS["KEY_OK"]: ("OK", ""),
		KEYIDS["KEY_UP"]: ("UP",),
		KEYIDS["KEY_DOWN"]: ("DOWN",),
		KEYIDS["KEY_POWER"]: ("POWER",),
		KEYIDS["KEY_RED"]: ("RED",),
		KEYIDS["KEY_BLUE"]: ("BLUE",),
		KEYIDS["KEY_GREEN"]: ("GREEN",),
		KEYIDS["KEY_YELLOW"]: ("YELLOW",),
		KEYIDS["KEY_MENU"]: ("MENU",),
		KEYIDS["KEY_LEFT"]: ("LEFT",),
		KEYIDS["KEY_RIGHT"]: ("RIGHT",),
		KEYIDS["KEY_VIDEO"]: ("VIDEO",),
		KEYIDS["KEY_INFO"]: ("INFO",),
		KEYIDS["KEY_AUDIO"]: ("AUDIO",),
		KEYIDS["KEY_TV"]: ("TV",),
		KEYIDS["KEY_RADIO"]: ("RADIO",),
		KEYIDS["KEY_TEXT"]: ("TEXT",),
		KEYIDS["KEY_NEXT"]: ("ARROWRIGHT",),
		KEYIDS["KEY_PREVIOUS"]: ("ARROWLEFT",),
		KEYIDS["KEY_PREVIOUSSONG"]: ("BLUE", "SHIFT"),
		KEYIDS["KEY_PLAYPAUSE"]: ("YELLOW", "SHIFT"),
		KEYIDS["KEY_PLAY"]: ("PLAY",),
		KEYIDS["KEY_NEXTSONG"]: ("RED", "SHIFT"),
		KEYIDS["KEY_CHANNELUP"]: ("BOUQUET+",),
		KEYIDS["KEY_CHANNELDOWN"]: ("BOUQUET-",),
		KEYIDS["KEY_0"]: ("0",),
		KEYIDS["KEY_1"]: ("1",),
		KEYIDS["KEY_2"]: ("2",),
		KEYIDS["KEY_3"]: ("3",),
		KEYIDS["KEY_4"]: ("4",),
		KEYIDS["KEY_5"]: ("5",),
		KEYIDS["KEY_6"]: ("6",),
		KEYIDS["KEY_7"]: ("7",),
		KEYIDS["KEY_8"]: ("8",),
		KEYIDS["KEY_9"]: ("9",),
		KEYIDS["KEY_EXIT"]: ("EXIT",),
		KEYIDS["KEY_STOP"]: ("TV", "SHIFT"),
		KEYIDS["KEY_RECORD"]: ("RECORD",),
		KEYIDS["KEY_SUBTITLE"]: ("SUBTITLE",)
	}
]
def getRCUName():
	rcu_name = None
	f = open("/proc/bus/input/devices")
	for line in f:
		if line.startswith("N: Name="):
			try:
				line = line.strip()
				name = line.split("=")[1][1:-1]
				if name.find("remote control (native)"):
					rcu_name = name
			except:
				rcu_name = None
	return rcu_name

def addKeyBinding(domain, key, context, action, flags, device):
	keyBindings.setdefault((context, action), []).append((key, domain, flags, device))

# returns a list of (key, flags) for a specified action
def queryKeyBinding(context, action):
	global deviceName

	if deviceName == None:
		deviceName = getRCUName()

	buttons = []
	if (context, action) in keyBindings:
		for x in keyBindings[(context, action)]:
			if x[3] == deviceName or x[3] == "generic":
				buttons.append((x[0],x[2]))
		return buttons
	else:
		return [ ]

def getKeyDescription(key):
	if key in keyDescriptions[config.misc.rcused.value]:
		return keyDescriptions[config.misc.rcused.value].get(key, [ ])

def removeKeyBindings(domain):
	# remove all entries of domain 'domain'
	for x in keyBindings:
		keyBindings[x] = filter(lambda e: e[1] != domain, keyBindings[x])
