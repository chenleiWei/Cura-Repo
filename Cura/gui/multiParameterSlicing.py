__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import wx
import platform

class multiParameterSlicing(wx.Frame):
	def __init__(self):
		super(multiParameterSlicing, self).__init__(None, title="Multi-Parameter Slicing", style = wx.DEFAULT_DIALOG_STYLE)

		wx.EVT_CLOSE(self, self.OnClose)

		p = wx.Panel(self)
		self.panel = p
		s = wx.BoxSizer()
		self.SetSizer(s)
		s.Add(p, flag=wx.ALL, border=15)
		s = wx.BoxSizer(wx.VERTICAL)
		p.SetSizer(s)

		title = wx.StaticText(p, -1, 'Cura')
		title.SetFont(wx.Font(18, wx.SWISS, wx.NORMAL, wx.BOLD))
		s.Add(title, flag=wx.ALIGN_CENTRE|wx.EXPAND|wx.BOTTOM, border=5)

		self.listctrl = wx.ListCtrl(p, size=(-1,100),style=wx.LC_REPORT|wx.BORDER_SUNKEN)
		self.listctrl.InsertColumn(0, 'Model')
	#Translations done by:
		#Dutch: Charlotte Jansen
		#German: Gregor Luetolf, Lars Potter
		#Polish: Piotr Paczynski
		#French: Jeremie Francois
		#Spanish: Jose Gemez
		self.Fit()

	def addComponent(self, name, description, license, url):
		p = self.panel
		s = p.GetSizer()
		s.Add(wx.StaticText(p, -1, '* %s - %s' % (name, description)), flag=wx.TOP, border=5)
		s.Add(wx.StaticText(p, -1, '   License: %s - Website: %s' % (license, url)))

	def OnClose(self, e):
		self.Destroy()
