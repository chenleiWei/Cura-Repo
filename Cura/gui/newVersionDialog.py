__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import wx
from Cura.gui import firmwareInstall
from Cura.util import version
from Cura.util import profile

class newVersionDialog(wx.Dialog):
	def __init__(self):
		super(newVersionDialog, self).__init__(None, title="Welcome to the new version!")

		wx.EVT_CLOSE(self, self.OnClose)

		p = wx.Panel(self)
		self.panel = p
		s = wx.BoxSizer()
		self.SetSizer(s)
		s.Add(p, flag=wx.ALL, border=15)
		s = wx.BoxSizer(wx.VERTICAL)
		p.SetSizer(s)

		title = wx.StaticText(p, -1, 'Cura - ' + version.getVersion())
		title.SetFont(wx.Font(18, wx.SWISS, wx.NORMAL, wx.BOLD))
		s.Add(title, flag=wx.ALIGN_CENTRE|wx.EXPAND|wx.BOTTOM, border=5)
		s.Add(wx.StaticText(p, -1, 'Welcome to the new version of Cura.'))
		s.Add(wx.StaticText(p, -1, '(This dialog is only shown once)'))
		s.Add(wx.StaticLine(p), flag=wx.EXPAND|wx.TOP|wx.BOTTOM, border=10)
		s.Add(wx.StaticText(p, -1, 'New in this version:'))
		s.Add(wx.StaticText(p, -1, '* Completely up-to-date with upstream Cura'))
		s.Add(wx.StaticText(p, -1, '* Implemented material profile selection in Simple Mode'))
		s.Add(wx.StaticText(p, -1, '* 41 material profiles to choose from'))
		s.Add(wx.StaticText(p, -1, '* Option to port Simple Mode profile settings to Expert Mode'))


		self.hasUltimaker = None
		self.hasUltimaker2 = None

		s.Add(wx.StaticLine(p), flag=wx.EXPAND|wx.TOP|wx.BOTTOM, border=10)
		button = wx.Button(p, -1, 'Ok')
		self.Bind(wx.EVT_BUTTON, self.OnOk, button)
		s.Add(button, flag=wx.TOP|wx.ALIGN_RIGHT, border=5)

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
