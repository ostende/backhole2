from MenuList import MenuList
from Tools.Directories import SCOPE_CURRENT_SKIN, resolveFilename
from enigma import RT_HALIGN_LEFT, eListboxPythonMultiContent, gFont
from Tools.LoadPixmap import LoadPixmap
import skin

def ChoiceEntryComponent(key = "", text = ["--"]):
	font = skin.fonts["ChoiceList"]
	res = [ text ]
	if text[0] == "--":
		x, y, w, h = skin.parameters.get("ChoicelistDash",(0, 0, 800, 25))
		res.append((eListboxPythonMultiContent.TYPE_TEXT, x, y, w, h, 0, RT_HALIGN_LEFT, "-"*200))
	else:
		x, y, w, h = skin.parameters.get("ChoicelistName",(45, 0, 800, 25))
		res.append((eListboxPythonMultiContent.TYPE_TEXT, x, y, w, h, 0, RT_HALIGN_LEFT, text[0]))
	
		png = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/buttons/key_" + key + ".png"))
		if png is not None:
			x, y, w, h = skin.parameters.get("ChoicelistIcon",(5, 0, 35, 25))
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, x, y, w, h, png))
	
	return res

class ChoiceList(MenuList):
	def __init__(self, list, selection = 0, enableWrapAround=False):
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		font = skin.fonts.get("ChoiceList", ("Regular", 20, 25))
		self.l.setFont(0, gFont(font[0], font[1]))
		self.l.setItemHeight(font[2])
		self.selection = selection

	def postWidgetCreate(self, instance):
		MenuList.postWidgetCreate(self, instance)
		self.moveToIndex(self.selection)
