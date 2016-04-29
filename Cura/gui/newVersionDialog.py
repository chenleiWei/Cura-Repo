__copyright__ = "Copyright (C) 2016 David Braam and Cat Casuat (Cura Type A)- Released under terms of the AGPLv3 License"

import wx
import wx.lib.agw.hyperlink as hl
from Cura.gui import firmwareInstall
from Cura.util import version
from Cura.util import profile


class newVersionDialog(wx.Dialog):
	def __init__(self):
		super(newVersionDialog, self).__init__(None, title="Welcome to the new version!", style=wx.STAY_ON_TOP)

		p = wx.Panel(self)
		self.panel = p
		s = wx.BoxSizer()
		self.SetSizer(s)
		s.Add(p, flag=wx.ALL, border=15)
		s = wx.BoxSizer(wx.VERTICAL)
		p.SetSizer(s)
		
		# Fonts
		titleFont = wx.Font(18, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
		headerFont = wx.Font(14, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
		textFont = wx.Font(14, wx.DEFAULT, wx.NORMAL, wx.NORMAL)

		# Title text
		title = wx.StaticText(p, -1, 'Cura Type A - ' + version.getVersion())
		title.SetFont(titleFont)
		versionForked = wx.StaticText(p, -1, 'Based On Daid/Ultimaker\'s Cura v15.02.')
		versionForked.SetFont(headerFont)
		s.Add(title, flag=wx.ALIGN_CENTRE|wx.EXPAND|wx.BOTTOM, border=5)
		s.Add(versionForked)
		s.Add(wx.StaticLine(p), flag=wx.EXPAND|wx.TOP|wx.BOTTOM, border=5)
	
	
		# New in this version
		newHere = wx.StaticText(p, -1, "New in Cura " + version.getVersion())
		newHere.SetFont(titleFont)
		degree_sign = u'\N{DEGREE SIGN}'
		s.Add(newHere, flag=wx.TOP, border=10)

		changesAndAdditions = [
			wx.StaticText(p, -1, "* Introducing cubic and concentric infill types (bug has been fixed!)"),
			wx.StaticText(p, -1, "* New infill visualizer"),
			wx.StaticText(p, -1, "* Added user analytics"),
			wx.StaticText(p, -1, "* Fill density setting is now fill distance"),
			wx.StaticText(p, -1, "* Added a new version update notification"),
			wx.StaticText(p, -1, "")
		]
		
		for item in changesAndAdditions:
			item.Wrap(600)
			item.SetFont(textFont)
			s.Add(item, flag=wx.TOP, border=5)
		
		# Materials
		materialsLabel = wx.StaticText(p, -1, "New Material Profiles")
		materialsLabel.SetFont(titleFont)
		s.Add(materialsLabel, flag=wx.BOTTOM, border=10)
		
		newMaterialsDict = {}
		newMaterialsDict['3DElements'] = ['FireResist Nylon']
		newMaterialsDict['3DXTech'] = ['ABSCF', 'ABSCNT', 'CFPETG']
		newMaterialsDict['3Dom'] = ['CoffeePLA', 'GlassPLA']
		newMaterialsDict['Biome'] = ['Linen', 'Silk']
		newMaterialsDict['Generic'] = ['BPet', 'WoodfilledPLA']
		newMaterialsDict['Proto-pasta'] = ['AromaticCoffee HTPLA', 'Brass PLA','Bronze PLA', 'Carbon Fiber HTPLA', 'Copper PLA', 'IridescantIce HTPLA', 'SolidSmoke HTPLA', 'SSPLA']
		newMaterialsDict['RigidInk'] = ['PLA']
		newMaterialsDict['TonerPlastics'] = ['PLA']
		newMaterialsDict['Colorfabb'] = ['XT Copolyester']
		
		self.addMaterialList(newMaterialsDict, p, s)
		


		s.Add(wx.StaticLine(p), flag=wx.EXPAND|wx.TOP|wx.BOTTOM, border=10)
		button = wx.Button(p, -1, 'OK')
		button.Bind(wx.EVT_BUTTON, self.OnOk)
		s.Add(button, flag=wx.TOP|wx.ALIGN_CENTRE | wx.ALL, border=5)

		self.Fit()
		self.Centre()
	
	def addMaterialList(self, list, p, s):
	
		leftBoxSizer = wx.BoxSizer(wx.VERTICAL)
		rightBoxSizer = wx.BoxSizer(wx.VERTICAL)
		
		gs = wx.GridBagSizer(5, 5)
		row = 0
		column = 0

		# Fonts
		titleFont = wx.Font(14, wx.DEFAULT, wx.NORMAL, wx.BOLD)
		headerFont = wx.Font(14, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
		textFont = wx.Font(14, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
		addCount = 0

		for label, materials in list.items():
			if len(materials) > 3 and column > 0:
				column += 1
				row = 0
			materialLabel = wx.StaticText(p, -1, str(label))
			materialLabel.SetFont(titleFont)
			gs.Add(materialLabel, pos=(row, column), flag=wx.RIGHT, border=5)
			row += 1
			addCount += 1
			for material in materials:
				material = wx.StaticText(p, -1, str(material))
				gs.Add(material, pos=(row, column), flag=wx.RIGHT, border=5)
				row += 1
			row += 1
			if addCount == 3:
				column += 1
				row = 0
				addCount = 0

		s.Add(gs)

	def addMaterial(self, s, material, materialUpdates):
		# Fonts
		titleFont = wx.Font(14, wx.DEFAULT, wx.NORMAL, wx.BOLD)
		headerFont = wx.Font(14, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
		textFont = wx.Font(13, wx.DEFAULT, wx.NORMAL, wx.NORMAL)

		material.SetFont(headerFont)
		s.Add(material, flag=wx.TOP, border=10)
		for update in materialUpdates:
			update.SetFont(textFont)
			s.Add(update, flag=wx.TOP | wx.LEFT, border=5)
		
	def OnUltimakerFirmware(self, e):
		firmwareInstall.InstallFirmware(machineIndex=self.hasUltimaker)

	def OnUltimaker2Firmware(self, e):
		firmwareInstall.InstallFirmware(machineIndex=self.hasUltimaker2)

	def OnOk(self, e):
		self.Close()
		
	def OnClose(self, e):
		self.Destroy()
