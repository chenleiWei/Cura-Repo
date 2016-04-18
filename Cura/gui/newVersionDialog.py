__copyright__ = "Copyright (C) 2013 David Braam and Cat Casuat (Cura Type A)- Released under terms of the AGPLv3 License"

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
		titleFont = wx.Font(14, wx.DEFAULT, wx.NORMAL, wx.BOLD)
		headerFont = wx.Font(14, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
		textFont = wx.Font(13, wx.DEFAULT, wx.NORMAL, wx.NORMAL)

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
			wx.StaticText(p, -1, "* Updated print head size values"),
			wx.StaticText(p, -1, "* Processes involving printer communication improved"),
			wx.StaticText(p, -1, "* The Fill Amount setting updated from 25mm to 30mm"),
			wx.StaticText(p, -1, "* Airgap (Distance Z) setting updated from 0.15mm to 0.3mm"),
			wx.StaticText(p, -1, "* Name of the material profile used included in start gcode"),
			wx.StaticText(p, -1, "* GUI text is now in black"),
			wx.StaticText(p, -1, "* Processes involving printer communication improved"),
			wx.StaticText(p, -1, "* Fill amount setting updated from 25 to 30"),
			wx.StaticText(p, -1, "* Airgap (Distance Z) updated from 0.15 to 0.3")
		]
		
		for item in changesAndAdditions:
			item.Wrap(600)
			item.SetFont(textFont)
			s.Add(item, flag=wx.TOP, border=5)
		
		# Materials
		materialsLabel = wx.StaticText(p, -1, "Material Profile Updates")
		materialsLabel.SetFont(titleFont)
		s.Add(materialsLabel)
		
		# --- ProMatte --- #
		material = wx.StaticText(p, -1, "Type A Machines ProMatte")
		materialUpdates = [
			wx.StaticText(p, -1, "* Print bed temperature decreased from 75%sC to 60%sC" % (degree_sign, degree_sign)),
			wx.StaticText(p, -1, "* Print head temperature increase from 180%sC to 220%sC" % (degree_sign, degree_sign)),
			wx.StaticText(p, -1, "* Retraction disabled"),
		]
		self.addMaterial(s, material, materialUpdates)	
	
		# --- Polymaker PC-Plus --- #
		material = wx.StaticText(p, -1, "Polymaker PC-Plus")
		materialUpdates = [
			wx.StaticText(p, -1, "* Fan disabled")
		]
		self.addMaterial(s, material, materialUpdates)	
		
		# -- PET Profiles (All) -- #
		material = wx.StaticText(p, -1, "All PET Profiles")	
		materialUpdates = [
			wx.StaticText(p, -1, "* Retraction speeds have been decreased from ~90mm/s to 35mm/s"),
			wx.StaticText(p, -1, "* Retraction amounts have decreased from 9.5mm to 0.5mm")
		]
		self.addMaterial(s, material, materialUpdates)			

		# -- Generic PLA -- #
		material = wx.StaticText(p, -1, "Generic PLA")	
		materialUpdates = [
			wx.StaticText(p, -1, "* Print speed reduced from 100mm/s to 60mm/s")
		]
		self.addMaterial(s, material, materialUpdates)	
		
		"""
		# Recent Additions
		recentAdditions = wx.StaticText(p, -1, "Recent Additions")
		recentAdditions.SetFont(titleFont)
		s.Add(recentAdditions)
				
		recentAdditionsList = [
			wx.StaticText(p, -1, "* Optimized material profiles: PolyMaker PC-Plus, 3DOM PLA"),
			wx.StaticText(p, -1, "* Send Gcode from Cura Type A directly to your Series 1 and start printing"),
			wx.StaticText(p, -1, "* Material profiles now also available in Expert mode via the Expert menu"),
			wx.StaticText(p, -1, "* Selecting a heated bed no longer requires application relaunching"),
			wx.StaticText(p, -1, "")
		]
		
		for item in recentAdditionsList:
			item.Wrap(600)
			item.SetFont(textFont)
			s.Add(item, flag=wx.TOP, border=5)
		
		self.hasUltimaker = None
		self.hasUltimaker2 = None
		"""
		s.Add(wx.StaticLine(p), flag=wx.EXPAND|wx.TOP|wx.BOTTOM, border=10)
		button = wx.Button(p, -1, 'OK')
		button.Bind(wx.EVT_BUTTON, self.OnOk)
		s.Add(button, flag=wx.TOP|wx.ALIGN_CENTRE | wx.ALL, border=5)

		self.Fit()
		self.Centre()

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
