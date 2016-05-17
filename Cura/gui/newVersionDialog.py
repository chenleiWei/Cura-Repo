__copyright__ = "Copyright (C) 2016 David Braam and Cat Casuat (Cura Type A)- Released under terms of the AGPLv3 License"

import wx
import wx.lib.agw.hyperlink as hl
from Cura.gui import firmwareInstall
from Cura.util import version
from Cura.util import profile






class newVersionDialog(wx.Dialog):
	def __init__(self):
		super(newVersionDialog, self).__init__(None, title="Welcome to the New Version!", style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)

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
		newHere = wx.StaticText(p, -1, "New Features and Enhancements")
		newHere.SetFont(titleFont)
		degree_sign = u'\N{DEGREE SIGN}'
		s.Add(newHere, flag=wx.TOP, border=10)

		featuresAndEnhancements = [
			wx.StaticText(p, -1, "* Absolute Dimensions\n\t- Specifying infill by millimeter rather than percentage"),
			wx.StaticText(p, -1, "* 3D Cubic Structure\n\t- Delivering axis-independent interior structure"),
			wx.StaticText(p, -1, "* Flow rate corrections\n\t- Providing more accurate results and improved tolerances"),
			wx.StaticText(p, -1, "* New Concentric Infill pattern introduced"),
			wx.StaticText(p, -1, "Infill Visualizer\n\t - Toggles the display of infill in-place"),
			wx.StaticText(p, -1, "* Expert Mode side panel now displays:\n\t- Extrusion Width, Number of Shells, Infill and Flow Percentage"),
			wx.StaticText(p, -1, "* Cmd/Ctrl-P now brings up the \"Send to Printer\" dialog"),
			wx.StaticText(p, -1, "* Tag added to GCode files including which profile was used to generate the GCode"),
			wx.StaticText(p, -1, "* User Notification for available Software Updates is now included"),
		]
		
		for item in featuresAndEnhancements:
			item.SetFont(textFont)
			s.Add(item, flag=wx.BOTTOM | wx.EXPAND, border=10)
		
		# Bug fixes
		issuesAddressed = wx.StaticText(p, -1, "Issues Addressed")
		issuesAddressed.SetFont(titleFont)
		degree_sign = u'\N{DEGREE SIGN}'
		s.Add(issuesAddressed, flag=wx.TOP, border=10)
		issues = wx.StaticText(p, -1, "* Custom start/end GCode no longer ignored under some conditions")
		issues.SetFont(textFont)
		s.Add(issues, flag=wx.BOTTOM, border=20)
		
		newMaterialProfiles = wx.StaticText(p, -1, "New Material Profiles")
		newMaterialProfiles.SetFont(titleFont)
		s.Add(newMaterialProfiles, flag=wx.BOTTOM)
		materials = wx.StaticText(p, -1, "* Over 75 total")
		materials.SetFont(textFont)
		s.Add(materials, flag=wx.BOTTOM, border=10)
		hyperlink = hl.HyperLinkCtrl(p, -1, "* Complete list here", URL='https://docs.google.com/document/d/1jeOaJq3sqIv2bwnXVx3CSOUpI3yewPhzjAgBPw7mYaA')
		hyperlink.SetFont(textFont)
		s.Add(hyperlink)
		
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
