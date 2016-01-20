__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import wx
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
		titleFont = wx.Font(13, wx.SWISS, wx.NORMAL, wx.BOLD)
		headerFont = wx.Font(12, wx.SWISS, wx.NORMAL, wx.BOLD)
		textFont = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL)

		# Title text
		title = wx.StaticText(p, -1, 'Cura - ' + version.getVersion())
		title.SetFont(titleFont)
		versionForked = wx.StaticText(p, -1, 'Based On Daid/Ultimaker\'s Cura v15.02.')
		versionForked.SetFont(textFont)
		s.Add(title, flag=wx.ALIGN_CENTRE|wx.EXPAND|wx.BOTTOM, border=5)
		s.Add(versionForked)
		s.Add(wx.StaticLine(p), flag=wx.EXPAND|wx.TOP|wx.BOTTOM, border=10)
	
		# "New in This Version" label
		newHere = wx.StaticText(p, -1, 'New in this version:')
		newHere.SetFont(headerFont)
		s.Add(newHere)
	
		# Bullet point list
		# Add or remove static text objects as needed
		changesAndAdditions = [
			wx.StaticText(p, -1, "* Send Gcode from Cura Type A directly to your Series 1 and start printing, all with a single click"),
			wx.StaticText(p, -1, "* Material profiles now also available in Expert mode via the Expert menu."),
			wx.StaticText(p, -1, "* Selecting a heated bed no longer requires application relaunching"),
			wx.StaticText(p, -1, "* New optimized material profiles added: PolyMaker PC Plus, 3DOM PLA."),
		]
			
	
		# Add bullet points
		for item in changesAndAdditions:
			item.SetFont(textFont)
			item.Wrap(600)
			s.Add(item, flag=wx.TOP, border=10)


		self.hasUltimaker = None
		self.hasUltimaker2 = None

	#	s.Add(wx.StaticLine(p), flag=wx.EXPAND|wx.TOP|wx.BOTTOM, border=10)
		button = wx.Button(p, -1, 'Ok')
		button.Bind(wx.EVT_BUTTON, self.OnOk)
		s.Add(button, flag=wx.TOP|wx.ALIGN_RIGHT, border=7)

		self.Fit()
		self.Centre()

	def OnUltimakerFirmware(self, e):
		firmwareInstall.InstallFirmware(machineIndex=self.hasUltimaker)

	def OnUltimaker2Firmware(self, e):
		firmwareInstall.InstallFirmware(machineIndex=self.hasUltimaker2)

	def OnOk(self, e):
		self.Close()
		
	def OnClose(self, e):
		self.Destroy()
