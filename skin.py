from Tools.Profile import profile
profile("LOAD:ElementTree")
import xml.etree.cElementTree
from os import path

profile("LOAD:enigma_skin")
from enigma import eSize, ePoint, gFont, eWindow, eLabel, ePixmap, eWindowStyleManager, \
	addFont, gRGB, eWindowStyleSkinned
from Components.config import ConfigSubsection, ConfigText, ConfigInteger, config
from Components.Converter.Converter import Converter
from Components.Sources.Source import Source, ObsoleteSource
from Tools.Directories import resolveFilename, SCOPE_SKIN, SCOPE_SKIN_IMAGE, SCOPE_FONTS, SCOPE_CURRENT_SKIN, SCOPE_CONFIG, fileExists
from Tools.Import import my_import
from Tools.LoadPixmap import LoadPixmap

colorNames = dict()

fonts = {
	"Body": ("Regular", 18, 22, 16),
	"ChoiceList": ("Regular", 20, 25, 18),
}

parameters = {}

def dump(x, i=0):
	print " " * i + str(x)
	try:
		for n in x.childNodes:
			dump(n, i + 1)
	except:
		None

class SkinError(Exception):
	def __init__(self, message):
		self.msg = message

	def __str__(self):
		return "{%s}: %s" % (config.skin.primary_skin.value, self.msg)

dom_skins = [ ]

def loadSkin(name, scope = SCOPE_SKIN):
	# read the skin
	filename = resolveFilename(scope, name)
	mpath = path.dirname(filename) + "/"
	dom_skins.append((mpath, xml.etree.cElementTree.parse(filename).getroot()))

# we do our best to always select the "right" value
# skins are loaded in order of priority: skin with
# highest priority is loaded last, usually the user-provided
# skin.

# currently, loadSingleSkinData (colors, bordersets etc.)
# are applied one-after-each, in order of ascending priority.
# the dom_skin will keep all screens in descending priority,
# so the first screen found will be used.

# example: loadSkin("nemesis_greenline/skin.xml")
config.skin = ConfigSubsection()
config.skin.primary_skin = ConfigText(default = "skin.xml")
config.skin.xres = ConfigInteger(default = 0)

profile("LoadSkin")
try:
	loadSkin('skin_user.xml', SCOPE_CONFIG)
except (SkinError, IOError, AssertionError), err:
	print "not loading user skin: ", err

try:
	loadSkin(config.skin.primary_skin.value)
except (SkinError, IOError, AssertionError), err:
	print "SKIN ERROR:", err
	print "defaulting to standard skin..."
	config.skin.primary_skin.value = 'skin.xml'
	loadSkin('skin.xml')

profile("LoadSkinDefault")
loadSkin('skin_default.xml')
profile("LoadSkinDefaultDone")

def parseCoordinate(str, e, size = 0):
	str = str.strip()
	if str == "center":
		val = (e - size)/2
	else:
		sl = len(str)
		l = 1

		if str[0] is 'e':
			val = e
		elif str[0] is 'c':
			val = e/2
		else:
			val = 0;
			l = 0

		if sl - l > 0:
			if str[sl-1] is '%':
				val += e * int(str[l:sl-1]) / 100
			else:
				val += int(str[l:sl])
	if val < 0:
		val = 0
	return val

def evalPos(pos, wsize, ssize, scale):
	if pos == "center":
		pos = (ssize - wsize) / 2
	else:
		sl = len(str)
		l = 1

		if str[0] is 'e':
			val = e
		elif str[0] is 'c':
			val = e/2
		else:
			val = 0;
			l = 0

		if sl - l > 0:
			if str[sl-1] is '%':
				val += e * int(str[l:sl-1]) / 100
			else:
				val += int(str[l:sl])
	if val < 0:
		val = 0
	return val

def getParentSize(object, desktop):
	size = eSize()
	if object:
		parent = object.getParent()
		# For some widgets (e.g. ScrollLabel) the skin attributes are applied to
		# a child widget, instead of to the widget itself. In that case, the parent
		# we have here is not the real parent, but it is the main widget.
		# We have to go one level higher to get the actual parent.
		# We can detect this because the 'parent' will not have a size yet
		# (the main widget's size will be calculated internally, as soon as the child
		# widget has parsed the skin attributes)
		if parent and parent.size().isEmpty():
			parent = parent.getParent()
		if parent:
			size = parent.size()
		elif desktop:
			#widget has no parent, use desktop size instead for relative coordinates
			size = desktop.size()
	return size

def parsePosition(str, scale, object = None, desktop = None, size = None):
	x, y = str.split(',')
	parentsize = eSize()
	if object and (x[0] in ['c', 'e'] or y[0] in ['c', 'e']):
		parentsize = getParentSize(object, desktop)
	xval = parseCoordinate(x, parentsize.width(), size and size.width())
	yval = parseCoordinate(y, parentsize.height(), size and size.height())
	return ePoint(xval * scale[0][0] / scale[0][1], yval * scale[1][0] / scale[1][1])

def parseSize(str, scale, object = None, desktop = None):
	x, y = str.split(',')
	parentsize = eSize()
	if object and (x[0] in ['c', 'e'] or y[0] in ['c', 'e']):
		parentsize = getParentSize(object, desktop)
	xval = parseCoordinate(x, parentsize.width())
	yval = parseCoordinate(y, parentsize.height())
	return eSize(xval * scale[0][0] / scale[0][1], yval * scale[1][0] / scale[1][1])

def parseFont(s, scale):
	try:
		f = fonts[s]
		name = f[0]
		size = f[1]
	except:
		name, size = s.split(';')
	return gFont(name, int(size) * scale[0][0] / scale[0][1])

def parseColor(str):
	if str[0] != '#':
		try:
			return colorNames[str]
		except:
			raise SkinError("color '%s' must be #aarrggbb or valid named color" % (str))
	return gRGB(int(str[1:], 0x10))

def collectAttributes(skinAttributes, node, context, skin_path_prefix=None, ignore=[]):
	# walk all attributes
	size = None
	pos = None
	for attrib, value in node.items():
		if attrib not in ignore:
			if attrib in ("pixmap", "pointer", "seek_pointer", "backgroundPixmap", "selectionPixmap"):
				value = resolveFilename(SCOPE_SKIN_IMAGE, value, path_prefix=skin_path_prefix)

			# Bit of a hack this, really. When a window has a flag (e.g. wfNoBorder)
			# it needs to be set at least before the size is set, in order for the
			# window dimensions to be calculated correctly in all situations.
			# If wfNoBorder is applied after the size has been set, the window will fail to clear the title area.
			# Similar situation for a scrollbar in a listbox; when the scrollbar setting is applied after
			# the size, a scrollbar will not be shown until the selection moves for the first time

			if attrib == 'size':
				size = value.encode("utf-8")
			elif attrib == 'position':
				pos = value.encode("utf-8")
			else:
				skinAttributes.append((attrib, value.encode("utf-8")))

	if pos is not None:
		pos, size = context.parse(pos, size)
		skinAttributes.append(('position', pos))
	if size is not None:
		skinAttributes.append(('size', size))

def loadPixmap(path, desktop):
	cached = False
	option = path.find("#")
	if option != -1:
		options = path[option+1:].split(',')
		path = path[:option]
		cached = "cached" in options
	ptr = LoadPixmap(path, desktop, cached)
	if ptr is None:
		raise SkinError("pixmap file %s not found!" % (path))
	return ptr

class AttributeParser:
	def __init__(self, guiObject, desktop, scale = ((1,1),(1,1))):
		self.guiObject = guiObject
		self.desktop = desktop
		self.scaleTuple = scale
	def applyOne(self, attrib, value):
		try:
			getattr(self, attrib)(value)
		except AttributeError:
			print "[Skin] Attribute not implemented:", attrib, "value:", value
		except SkinError, ex:
			print "[Skin] Error:", ex
	def applyAll(self, attrs):
		for attrib, value in attrs:
			try:
				getattr(self, attrib)(value)
			except AttributeError:
				print "[Skin] Attribute not implemented:", attrib, "value:", value
			except SkinError, ex:
				print "[Skin] Error:", ex
	def position(self, value):
		if isinstance(value, tuple):
			self.guiObject.move(ePoint(*value))
		else:
			self.guiObject.move(parsePosition(value, self.scaleTuple, self.desktop, self.guiObject.csize()))
	def size(self, value):
		if isinstance(value, tuple):
			self.guiObject.resize(eSize(*value))
		else:
			self.guiObject.resize(parseSize(value, self.scaleTuple))
	def animationPaused(self, value):
		pass
	def animationPaused(self, value):
		self.guiObject.setAnimationMode(
			{ "disable": 0x00,
				"off": 0x00,
				"offshow": 0x10,
				"offhide": 0x01,
				"onshow": 0x01,
				"onhide": 0x10,
			}[value])
	def title(self, value):
		self.guiObject.setTitle(_(value))
	def text(self, value):
		self.guiObject.setText(_(value))
	def font(self, value):
		self.guiObject.setFont(parseFont(value, self.scaleTuple))
	def zPosition(self, value):
		self.guiObject.setZPosition(int(value))
	def itemHeight(self, value):
		self.guiObject.setItemHeight(int(value))
	def pixmap(self, value):
		ptr = loadPixmap(value, self.desktop)
		self.guiObject.setPixmap(ptr)
	def backgroundPixmap(self, value):
		ptr = loadPixmap(value, self.desktop)
		self.guiObject.setBackgroundPicture(ptr)
	def selectionPixmap(self, value):
		ptr = loadPixmap(value, self.desktop)
		self.guiObject.setSelectionPicture(ptr)
	def itemHeight(self, value):
		self.guiObject.setItemHeight(int(value))
	def alphatest(self, value):
		self.guiObject.setAlphatest(
			{ "on": 1,
			  "off": 0,
			  "blend": 2,
			}[value])
	def scale(self, value):
		self.guiObject.setScale(1)
	def orientation(self, value):
		try:
			self.guiObject.setOrientation(*
				{ "orVertical": (self.guiObject.orVertical, False),
					"orTopToBottom": (self.guiObject.orVertical, False),
					"orBottomToTop": (self.guiObject.orVertical, True),
					"orHorizontal": (self.guiObject.orHorizontal, False),
					"orLeftToRight": (self.guiObject.orHorizontal, False),
					"orRightToLeft": (self.guiObject.orHorizontal, True),
				}[value])
		except KeyError:
			print "oprientation must be either orVertical or orHorizontal!"
	def valign(self, value):
		try:
			self.guiObject.setVAlign(
				{ "top": self.guiObject.alignTop,
					"center": self.guiObject.alignCenter,
					"bottom": self.guiObject.alignBottom
				}[value])
		except KeyError:
			print "valign must be either top, center or bottom!"
	def halign(self, value):
		try:
			self.guiObject.setHAlign(
				{ "left": self.guiObject.alignLeft,
					"center": self.guiObject.alignCenter,
					"right": self.guiObject.alignRight,
					"block": self.guiObject.alignBlock
				}[value])
		except KeyError:
			print "halign must be either left, center, right or block!"
	def flags(self, value):
		flags = value.split(',')
		for f in flags:
			try:
				fv = eWindow.__dict__[f]
				self.guiObject.setFlag(fv)
			except KeyError:
				print "illegal flag %s!" % f
	def backgroundColor(self, value):
		self.guiObject.setBackgroundColor(parseColor(value))
	def backgroundColorSelected(self, value):
		self.guiObject.setBackgroundColorSelected(parseColor(value))
	def foregroundColor(self, value):
		self.guiObject.setForegroundColor(parseColor(value))
	def foregroundColorSelected(self, value):
		self.guiObject.setForegroundColorSelected(parseColor(value))
	def shadowColor(self, value):
		self.guiObject.setShadowColor(parseColor(value))
	def selectionDisabled(self, value):
		self.guiObject.setSelectionEnable(0)
	def transparent(self, value):
		self.guiObject.setTransparent(int(value))
	def borderColor(self, value):
		self.guiObject.setBorderColor(parseColor(value))
	def borderWidth(self, value):
		self.guiObject.setBorderWidth(int(value))
	def scrollbarMode(self, value):
		self.guiObject.setScrollbarMode(
			{ "showOnDemand": self.guiObject.showOnDemand,
				"showAlways": self.guiObject.showAlways,
				"showNever": self.guiObject.showNever
			}[value])
	def enableWrapAround(self, value):
		self.guiObject.setWrapAround(True)
	def pointer(self, value):
		(name, pos) = value.split(':')
		pos = parsePosition(pos, self.scaleTuple)
		ptr = loadPixmap(name, self.desktop)
		self.guiObject.setPointer(0, ptr, pos)
	def seek_pointer(self, value):
		(name, pos) = value.split(':')
		pos = parsePosition(pos, self.scaleTuple)
		ptr = loadPixmap(name, self.desktop)
		self.guiObject.setPointer(1, ptr, pos)
	def shadowOffset(self, value):
		self.guiObject.setShadowOffset(parsePosition(value, self.scaleTuple))
	def noWrap(self, value):
		self.guiObject.setNoWrap(1)
	def id(self, value):
		pass

def applySingleAttribute(guiObject, desktop, attrib, value, scale = ((1,1),(1,1))):
	# Someone still using applySingleAttribute?
	AttributeParser(guiObject, desktop, scale).applyOne(attrib, value)

def applyAllAttributes(guiObject, desktop, attributes, scale):
	AttributeParser(guiObject, desktop, scale).applyAll(attributes)

def loadSingleSkinData(desktop, skin, path_prefix):
	"""loads skin data like colors, windowstyle etc."""
	assert skin.tag == "skin", "root element in skin must be 'skin'!"

	#print "***SKIN: ", path_prefix

	for c in skin.findall("output"):
		id = c.attrib.get('id')
		if id:
			id = int(id)
		else:
			id = 0
		if id == 0: # framebuffer
			for res in c.findall("resolution"):
				get_attr = res.attrib.get
				xres = get_attr("xres")
				if xres:
					xres = int(xres)
				else:
					xres = 720
				yres = get_attr("yres")
				if yres:
					yres = int(yres)
				else:
					yres = 576
				bpp = get_attr("bpp")
				if bpp:
					bpp = int(bpp)
				else:
					bpp = 32
				#print "Resolution:", xres,yres,bpp
				config.skin.xres.value = xres
				from enigma import gMainDC
				gMainDC.getInstance().setResolution(xres, yres)
				desktop.resize(eSize(xres, yres))
				if bpp != 32:
					# load palette (not yet implemented)
					pass

	for c in skin.findall("colors"):
		for color in c.findall("color"):
			get_attr = color.attrib.get
			name = get_attr("name")
			color = get_attr("value")
			if name and color:
				colorNames[name] = parseColor(color)
				#print "Color:", name, color
			else:
				raise SkinError("need color and name, got %s %s" % (name, color))

	for c in skin.findall("fonts"):
		for font in c.findall("font"):
			get_attr = font.attrib.get
			filename = get_attr("filename", "<NONAME>")
			name = get_attr("name", "Regular")
			scale = get_attr("scale")
			if scale:
				scale = int(scale)
			else:
				scale = 100
			is_replacement = get_attr("replacement") and True or False
			resolved_font = resolveFilename(SCOPE_FONTS, filename, path_prefix=path_prefix)
			if not fileExists(resolved_font): #when font is not available look at current skin path
				skin_path = resolveFilename(SCOPE_CURRENT_SKIN, filename)
				if fileExists(skin_path):
					resolved_font = skin_path
			addFont(resolved_font, name, scale, is_replacement)
			#print "Font: ", resolved_font, name, scale, is_replacement
		for alias in c.findall("alias"):
		        get = alias.attrib.get
		        try:
				name = get("name")
				font = get("font")
				size = int(get("size"))
				height = int(get("height", size)) # to be calculated some day
				width = int(get("width", size))
				global fonts
				fonts[name] = (font, size, height, width)
			except Exception, ex:
				print "[SKIN] bad font alias", ex

		for alias in c.findall("alias"):
			get = alias.attrib.get
			try:
				name = get("name")
				font = get("font")
				size = int(get("size"))
				height = int(get("height", size)) # to be calculated some day
				width = int(get("width", size))
				global fonts
				fonts[name] = (font, size, height, width)
			except Exception, ex:
				print "[SKIN] bad font alias", ex

	for c in skin.findall("parameters"):
		for parameter in c.findall("parameter"):
			get = parameter.attrib.get
			try:
				name = get("name")
				value = get("value")
				parameters[name] = map(int, value.split(","))
			except Exception, ex:
				print "[SKIN] bad parameter", ex

	for c in skin.findall("subtitles"):
		from enigma import eWidget, eSubtitleWidget
		scale = ((1,1),(1,1))
		for substyle in c.findall("sub"):
			get_attr = substyle.attrib.get
			font = parseFont(get_attr("font"), scale)
			col = get_attr("foregroundColor")
			if col:
				foregroundColor = parseColor(col)
				haveColor = 1
			else:
				foregroundColor = gRGB(0xFFFFFF)
				haveColor = 0
			col = get_attr("shadowColor")
			if col:
				shadowColor = parseColor(col)
			else:
				shadowColor = gRGB(0)
			shadowOffset = parsePosition(get_attr("shadowOffset"), scale)
			face = eSubtitleWidget.__dict__[get_attr("name")]
			eSubtitleWidget.setFontStyle(face, font, haveColor, foregroundColor, shadowColor, shadowOffset)

	for windowstyle in skin.findall("windowstyle"):
		style = eWindowStyleSkinned()
		id = windowstyle.attrib.get("id")
		if id:
			id = int(id)
		else:
			id = 0
		#print "windowstyle:", id

		# defaults
		font = gFont("Regular", 20)
		offset = eSize(20, 5)

		for title in windowstyle.findall("title"):
			get_attr = title.attrib.get
			offset = parseSize(get_attr("offset"), ((1,1),(1,1)))
			font = parseFont(get_attr("font"), ((1,1),(1,1)))

		style.setTitleFont(font);
		style.setTitleOffset(offset)
		#print "  ", font, offset

		for borderset in windowstyle.findall("borderset"):
			bsName = str(borderset.attrib.get("name"))
			for pixmap in borderset.findall("pixmap"):
				get_attr = pixmap.attrib.get
				bpName = get_attr("pos")
				filename = get_attr("filename")
				if filename and bpName:
					png = loadPixmap(resolveFilename(SCOPE_SKIN_IMAGE, filename, path_prefix=path_prefix), desktop)
					style.setPixmap(eWindowStyleSkinned.__dict__[bsName], eWindowStyleSkinned.__dict__[bpName], png)
				#print "  borderset:", bpName, filename

		for color in windowstyle.findall("color"):
			get_attr = color.attrib.get
			colorType = get_attr("name")
			color = parseColor(get_attr("color"))
			try:
				style.setColor(eWindowStyleSkinned.__dict__["col" + colorType], color)
			except:
				raise SkinError("Unknown color %s" % (colorType))
				#pass

			#print "  color:", type, color

		x = eWindowStyleManager.getInstance()
		x.setStyle(id, style)

display_skin_id = 1
dom_screens = {}

def loadSkinData(desktop):
	global dom_skins, dom_screens, display_skin_id
	skins = dom_skins[:]
	skins.reverse()
	for (path, dom_skin) in skins:
		loadSingleSkinData(desktop, dom_skin, path)

		for elem in dom_skin:
			if elem.tag == 'screen':
				name = elem.attrib.get('name', None)
				if name:
					sid = elem.attrib.get('id', None)
					if sid and (int(sid) != display_skin_id):
						# not for this display
						elem.clear()
						continue
					if name in dom_screens:
						# Kill old versions, save memory
						dom_screens[name][0].clear()
					dom_screens[name] = (elem, path)
				else:
					# without name, it's useless!
					elem.clear()
			else:
				# non-screen element, no need for it any longer
				elem.clear()
	# no longer needed, we know where the screens are now.
	#del dom_skins

def lookupScreen(name, style_id):
	if dom_screens.has_key(name):
		elem, path = dom_screens[name]
		screen_style_id = elem.attrib.get('id', '-1')
		if screen_style_id == '-1' and name.find('summary') > 0:
			screen_style_id = '1'
		if (style_id != 2 and int(screen_style_id) == -1) or int(screen_style_id) == style_id:
			return elem, path

	else:
		for (path, skin) in dom_skins:
			for x in skin.findall("screen"):
				if x.attrib.get('name', '') == name:
					screen_style_id = x.attrib.get('id', '-1')
					if screen_style_id == '-1' and name.find('summary') > 0:
						screen_style_id = '1'
					if (style_id != 2 and int(screen_style_id) == -1) or int(screen_style_id) == style_id:
						dom_screens[name] = (x, path)
						return x, path
	return None, None

class additionalWidget:
	pass

# Class that makes a tuple look like something else. Some plugins just assume
# that size is a string and try to parse it. This class makes that work.
class SizeTuple(tuple):
	def split(self, *args):
		return (str(self[0]), str(self[1]))
	def strip(self, *args):
		return '%s,%s' % self
	def __str__(self):
		return '%s,%s' % self

class SkinContext:
	def __init__(self, parent=None, pos=None, size=None):
	        if parent is not None:
			if pos is not None:
				pos, size = parent.parse(pos, size)
				self.x, self.y = pos
				self.w, self.h = size
			else:
				self.x = None
				self.y = None
				self.w = None
				self.h = None
	def __str__(self):
	        return "Context (%s,%s)+(%s,%s) " % (self.x, self.y, self.w, self.h)
	def parse(self, pos, size):
	        if pos == "fill":
	                pos = (self.x, self.y)
	                size = (self.w, self.h)
	                self.w = 0
	                self.h = 0
		elif pos == "bottom":
			w,h = size.split(',')
			h = int(h)
		        pos = (self.x, self.y + self.h - h)
		        size = (self.w, h)
		        self.h -= h
		elif pos == "top":
			w,h = size.split(',')
			h = int(h)
		        pos = (self.x, self.y)
		        size = (self.w, h)
		        self.h -= h
		        self.y += h
		elif pos == "left":
			w,h = size.split(',')
			w = int(w)
			pos = (self.x, self.y)
			size = (w, self.h)
			self.x += w
			self.w -= w
		elif pos == "right":
			w,h = size.split(',')
			w = int(w)
			pos = (self.x + self.w - w, self.y)
			size = (w, self.h)
			self.w -= w
		else:
			size = size.split(',')
			size = (parseCoordinate(size[0], self.w), parseCoordinate(size[1], self.h)) 
			pos = pos.split(',')
			pos = (self.x + parseCoordinate(pos[0], self.w, size[0]), self.y + parseCoordinate(pos[1], self.h, size[1])) 		
		return (SizeTuple(pos), SizeTuple(size))

class SkinContextStack(SkinContext):
	# A context that stacks things instead of aligning them
	def parse(self, pos, size):
	        if pos == "fill":
	                pos = (self.x, self.y)
	                size = (self.w, self.h)
		elif pos == "bottom":
			w,h = size.split(',')
			h = int(h)
		        pos = (self.x, self.y + self.h - h)
		        size = (self.w, h)
		elif pos == "top":
			w,h = size.split(',')
			h = int(h)
		        pos = (self.x, self.y)
		        size = (self.w, h)
		elif pos == "left":
			w,h = size.split(',')
			w = int(w)
			pos = (self.x, self.y)
			size = (w, self.h)
		elif pos == "right":
			w,h = size.split(',')
			w = int(w)
			pos = (self.x + self.w - w, self.y)
			size = (w, self.h)
		else:
			size = size.split(',')
			size = (parseCoordinate(size[0], self.w), parseCoordinate(size[1], self.h))
			pos = pos.split(',')
			pos = (self.x + parseCoordinate(pos[0], self.w, size[0]), self.y + parseCoordinate(pos[1], self.h, size[1]))
		return (SizeTuple(pos), SizeTuple(size))

def readSkin(screen, skin, names, desktop):
	if not isinstance(names, list):
		names = [names]

	name = "<embedded-in-'%s'>" % screen.__class__.__name__

	style_id = desktop.getStyleID();

	# try all skins, first existing one have priority
	for n in names:
		myscreen, path = lookupScreen(n, style_id)
		if myscreen is not None:
			# use this name for debug output
			name = n
			break

	# otherwise try embedded skin
	if myscreen is None:
		myscreen = getattr(screen, "parsedSkin", None)

	# try uncompiled embedded skin
	if myscreen is None and getattr(screen, "skin", None):
		print "Looking for embedded skin"
		skin_tuple = screen.skin
		if not isinstance(skin_tuple, tuple):
			skin_tuple = (skin_tuple,)
		for sskin in skin_tuple:
			parsedSkin = xml.etree.cElementTree.fromstring(sskin)
			screen_style_id = parsedSkin.attrib.get('id', '-1')
			if (style_id != 2 and int(screen_style_id) == -1) or int(screen_style_id) == style_id:
				myscreen = screen.parsedSkin = parsedSkin
				break

	#assert myscreen is not None, "no skin for screen '" + repr(names) + "' found!"
	if myscreen is None:
		print "No skin to read..."
		emptySkin = "<screen></screen>"
		myscreen = screen.parsedSkin = xml.etree.cElementTree.fromstring(emptySkin)

	screen.skinAttributes = [ ]

	skin_path_prefix = getattr(screen, "skin_path", path)

#	collectAttributes(screen.skinAttributes, myscreen, skin_path_prefix, ignore=["name"])

	context = SkinContext()
	s = desktop.size()
	context.x = 0
	context.y = 0
	context.w = s.width()
	context.h = s.height()
	del s
	collectAttributes(screen.skinAttributes, myscreen, context, skin_path_prefix, ignore=("name",))
	context = SkinContext(context, myscreen.attrib.get('position'), myscreen.attrib.get('size'))

#

	screen.additionalWidgets = [ ]
	screen.renderer = [ ]

	visited_components = set()

	# now walk all widgets and stuff
	def process_none(widget, context):
		pass

	def process_widget(widget, context):
		get_attr = widget.attrib.get
		# ok, we either have 1:1-mapped widgets ('old style'), or 1:n-mapped
		# widgets (source->renderer).

		wname = get_attr('name')
		wsource = get_attr('source')

		if wname is None and wsource is None:
			print "widget has no name and no source!"
			return

		if wname:
			#print "Widget name=", wname
			visited_components.add(wname)

			# get corresponding 'gui' object
			try:
				attributes = screen[wname].skinAttributes = [ ]
			except:
				raise SkinError("component with name '" + wname + "' was not found in skin of screen '" + name + "'!")
				#print "WARNING: component with name '" + wname + "' was not found in skin of screen '" + name + "'!"

#			assert screen[wname] is not Source

			# and collect attributes for this
			collectAttributes(attributes, widget, context, skin_path_prefix, ignore=['name'])
		elif wsource:
			# get corresponding source
			#print "Widget source=", wsource

			while True: # until we found a non-obsolete source

				# parse our current "wsource", which might specifiy a "related screen" before the dot,
				# for example to reference a parent, global or session-global screen.
				scr = screen

				# resolve all path components
				path = wsource.split('.')
				while len(path) > 1:
					scr = screen.getRelatedScreen(path[0])
					if scr is None:
						#print wsource
						#print name
						raise SkinError("specified related screen '" + wsource + "' was not found in screen '" + name + "'!")
					path = path[1:]

				# resolve the source.
				source = scr.get(path[0])
				if isinstance(source, ObsoleteSource):
					# however, if we found an "obsolete source", issue warning, and resolve the real source.
					print "WARNING: SKIN '%s' USES OBSOLETE SOURCE '%s', USE '%s' INSTEAD!" % (name, wsource, source.new_source)
					print "OBSOLETE SOURCE WILL BE REMOVED %s, PLEASE UPDATE!" % (source.removal_date)
					if source.description:
						print source.description

					wsource = source.new_source
				else:
					# otherwise, use that source.
					break

			if source is None:
				raise SkinError("source '" + wsource + "' was not found in screen '" + name + "'!")

			wrender = get_attr('render')

			if not wrender:
				raise SkinError("you must define a renderer with render= for source '%s'" % (wsource))

			for converter in widget.findall("convert"):
				ctype = converter.get('type')
				assert ctype, "'convert'-tag needs a 'type'-attribute"
				#print "Converter:", ctype
				try:
					parms = converter.text.strip()
				except:
					parms = ""
				#print "Params:", parms
				converter_class = my_import('.'.join(("Components", "Converter", ctype))).__dict__.get(ctype)

				c = None

				for i in source.downstream_elements:
					if isinstance(i, converter_class) and i.converter_arguments == parms:
						c = i

				if c is None:
					print "allocating new converter!"
					c = converter_class(parms)
					c.connect(source)
				else:
					print "reused converter!"

				source = c

			renderer_class = my_import('.'.join(("Components", "Renderer", wrender))).__dict__.get(wrender)

			renderer = renderer_class() # instantiate renderer

			renderer.connect(source) # connect to source
			attributes = renderer.skinAttributes = [ ]
			collectAttributes(attributes, widget, context, skin_path_prefix, ignore=['render', 'source'])

			screen.renderer.append(renderer)

	def process_applet(widget, context):
		try:
			codeText = widget.text.strip()
		except:
			codeText = ""

		#print "Found code:"
		#print codeText
		widgetType = widget.attrib.get('type')

		code = compile(codeText, "skin applet", "exec")

		if widgetType == "onLayoutFinish":
			screen.onLayoutFinish.append(code)
			#print "onLayoutFinish = ", codeText
		else:
			raise SkinError("applet type '%s' unknown!" % widgetType)
			#print "applet type '%s' unknown!" % type

	def process_elabel(widget, context):
		w = additionalWidget()
		w.widget = eLabel
		w.skinAttributes = [ ]
		collectAttributes(w.skinAttributes, widget, context, skin_path_prefix, ignore=['name'])
		screen.additionalWidgets.append(w)

	def process_epixmap(widget, context):
		w = additionalWidget()
		w.widget = ePixmap
		w.skinAttributes = [ ]
		collectAttributes(w.skinAttributes, widget, context, skin_path_prefix, ignore=['name'])
		screen.additionalWidgets.append(w)

	def process_screen(widget, context):
		for w in widget.findall("widget"):
			process_widget(w, context)
	
		for w in widget.getchildren():
			if w.tag == "widget":
				continue

			p = processors.get(w.tag, process_none)
			p(w, context)

	def process_panel(widget, context):
		n = widget.attrib.get('name')
		if n:
			try:
				s = dom_screens.get(n, None)
			except KeyError:
				print "[SKIN] Unable to find screen '%s' referred in screen '%s'" % (n, name)
			else:
				process_screen(s[0], context)

		layout = widget.attrib.get('layout')
		if layout == 'stack':
			cc = SkinContextStack
		else:
		        cc = SkinContext
		try:
			c = cc(context, widget.attrib.get('position'), widget.attrib.get('size'))
		except Exception, ex:
		        raise SkinError("Failed to create skincontext (%s,%s) in %s: %s" % (widget.attrib.get('position'), widget.attrib.get('size'), context, ex) )

		process_screen(widget, c)

	processors = {
		None: process_none,
		"widget": process_widget,
		"applet": process_applet,
		"eLabel": process_elabel,
		"ePixmap": process_epixmap,
		"panel": process_panel
	}

	try:
		context.x = 0 # reset offsets, all components are relative to screen
		context.y = 0 # coordinates.
		process_screen(myscreen, context)
	except SkinError, e:
			print "[Skin] SKIN ERROR:", e

	from Components.GUIComponent import GUIComponent
	nonvisited_components = [x for x in set(screen.keys()) - visited_components if isinstance(x, GUIComponent)]
	assert not nonvisited_components, "the following components in %s don't have a skin entry: %s" % (name, ', '.join(nonvisited_components))
	# This may look pointless, but it unbinds 'screen' from the nested scope. A better
	# solution is to avoid the nested scope above and use the context object to pass
	# things around.
	screen = None
	visited_components = None

