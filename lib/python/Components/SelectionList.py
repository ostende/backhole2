from MenuList import MenuList
from Components.config import config
from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN
from enigma import eListboxPythonMultiContent, eListbox, gFont, RT_HALIGN_LEFT
from Tools.LoadPixmap import LoadPixmap
import skin

selectionpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/icons/selectioncross.png"))

def SelectionEntryComponent(description, value, index, selected):
	if config.skin.xres.value == 1920:
		res = [
			(description, value, index, selected),
			(eListboxPythonMultiContent.TYPE_TEXT, 35, 3, 770, 40, 0, RT_HALIGN_LEFT, description)
		]
	else:
		res = [
			(description, value, index, selected),
			(eListboxPythonMultiContent.TYPE_TEXT, 30, 3, 500, 30, 0, RT_HALIGN_LEFT, description)
		]
	if selected:
		if config.skin.xres.value == 1920:
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 0, 5, 30, 30, selectionpng))
		else:
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 0, 0, 30, 30, selectionpng))
	return res

class SelectionList(MenuList):
	def __init__(self, list = None, enableWrapAround = False):
		MenuList.__init__(self, list or [], enableWrapAround, content = eListboxPythonMultiContent)
		font = skin.fonts.get("SelectionList", ("Regular", 20, 30))
		self.l.setFont(0, gFont(font[0], font[1]))
		self.l.setItemHeight(font[2])

	def addSelection(self, description, value, index, selected = True):
		self.list.append(SelectionEntryComponent(description, value, index, selected))
		self.setList(self.list)

	def toggleSelection(self):
		idx = self.getSelectedIndex()
		item = self.list[idx][0]
		self.list[idx] = SelectionEntryComponent(item[0], item[1], item[2], not item[3])
		self.setList(self.list)

	def getSelectionsList(self):
		return [ (item[0][0], item[0][1], item[0][2]) for item in self.list if item[0][3] ]

