__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

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
		titleFont = wx.Font(13, wx.SWISS, wx.NORMAL, wx.BOLD)
		headerFont = wx.Font(12, wx.SWISS, wx.NORMAL, wx.BOLD)
		textFont = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL)

		# Title text
		title = wx.StaticText(p, -1, 'Cura Type A - Beta ' + version.getVersion())
		title.SetFont(titleFont)
		versionForked = wx.StaticText(p, -1, 'Based On Daid/Ultimaker\'s Cura v15.02.')
		versionForked.SetFont(textFont)
		s.Add(title, flag=wx.ALIGN_CENTRE|wx.EXPAND|wx.BOTTOM, border=5)
		s.Add(versionForked)
		s.Add(wx.StaticLine(p), flag=wx.EXPAND|wx.TOP|wx.BOTTOM, border=5)
	
		bugFixTitle = wx.StaticText(p, -1, "Recent Bug Fixes")
		bugFixTitle.SetFont(titleFont)
		bugsFixed = [
			wx.StaticText(p, -1, "* Configuration wizard copy edits (SLIC-313/315)"),
			wx.StaticText(p, -1, "* Edits to material profile tour text (SLIC-314)"),
			wx.StaticText(p, -1, "* Exiting Expert Mode will no longer result in a crash (SLIC-318)"),
			wx.StaticText(p, -1, "* Revised retraction distance tooltip text (SLIC-319)"),
			wx.StaticText(p, -1, "* Slicing engine issue in Windows addressed (SLIC-328)"),
			wx.StaticText(p, -1, "* Removed 'Legacy' and 'Other' from machine select page (SLIC-332)"),
			wx.StaticText(p, -1, "* Printer interface will only show if option is checked (SLIC-335)"),
			wx.StaticText(p, -1, "* Release notes and bug reporter now available under 'Help' dropdown (SLIC-336)")]
	
		s.Add(bugFixTitle, flag=wx.TOP, border=5)
		for count in bugsFixed:
			s.Add(count, flag=wx.TOP | wx.EXPAND, border=5)
		
		
		

		# "New in This Version" label
		newHere = wx.StaticText(p, -1, "New in Cura 1.4.0")
		newHere.SetFont(titleFont)
		s.Add(newHere, flag=wx.TOP, border=10)
	
		# Bullet point list
		# Add or remove static text objects as needed
		changesAndAdditions = [
			wx.StaticText(p, -1, "* Send Gcode from Cura Type A directly to your Series 1 and start printing"),
			wx.StaticText(p, -1, "* Material profiles now also available in Expert mode via the Expert menu"),
			wx.StaticText(p, -1, "* Selecting a heated bed no longer requires application relaunching"),
			wx.StaticText(p, -1, "* New optimized material profiles added: PolyMaker PC Plus, 3DOM PLA")
		]
			
		# Add bullet points
		for item in changesAndAdditions:
			item.Wrap(600)
			s.Add(item, flag=wx.TOP, border=5)

		# Note for Beta Testers
		s.Add(wx.StaticLine(p), flag=wx.EXPAND|wx.TOP|wx.BOTTOM, border=5)
		feedbackTitle = wx.StaticText(p, -1, 'Bugs and Feedback')
		feedbackTitle.SetFont(titleFont)
		font = wx.StaticText(p, -1, "")
		bugReportLink = hl.HyperLinkCtrl(p, -1, "typeamachines.com/cura-beta", URL="http://www.typeamachines.com/cura-beta")
		s.Add(feedbackTitle)
		s.Add(bugReportLink)
		
		self.hasUltimaker = None
		self.hasUltimaker2 = None

	#	s.Add(wx.StaticLine(p), flag=wx.EXPAND|wx.TOP|wx.BOTTOM, border=10)
		button = wx.Button(p, -1, 'Ok')
		button.Bind(wx.EVT_BUTTON, self.OnOk)
		s.Add(button, flag=wx.TOP|wx.ALIGN_CENTRE | wx.ALL, border=5)

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
