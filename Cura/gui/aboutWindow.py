__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import wx
import platform
from Cura.util import profile

class aboutWindow(wx.Frame):
	def __init__(self):
		super(aboutWindow, self).__init__(None, title="About", style = wx.DEFAULT_DIALOG_STYLE)

		wx.EVT_CLOSE(self, self.OnClose)

		p = wx.Panel(self)
		self.panel = p
		s = wx.BoxSizer()
		self.SetSizer(s)
		s.Add(p, flag=wx.ALL, border=15)
		s = wx.BoxSizer(wx.VERTICAL)
		p.SetSizer(s)
		currentVersion = '1.2.1a1'
		print ("CURRENT VERSION: %s"%currentVersion)
		title = wx.StaticText(p, -1, 'Cura Type A')
		title.SetFont(wx.Font(18, wx.SWISS, wx.NORMAL, wx.BOLD))
		s.Add(title, flag=wx.ALIGN_CENTRE|wx.EXPAND|wx.BOTTOM, border=5)
		
		title = wx.StaticText(p, -1, _('Version %s'%currentVersion))
		title.SetFont(wx.Font(12, wx.SWISS, wx.NORMAL, wx.BOLD))
		s.Add(title, flag=wx.ALIGN_CENTRE|wx.EXPAND|wx.BOTTOM, border=5)

		s.Add(wx.StaticText(p, -1, 'Cura Type A version %s has been optimized for the Type A Machines Series 1 3D Printer.'%currentVersion))
		s.Add(wx.StaticText(p, -1, 'This version is for use with the late-2014 Series 1 print head only.'))
		s.Add(wx.StaticText(p, -1, 'Cura Type A is based on Cura 14.07.'))
		s.Add(wx.StaticText(p, -1, 'Cura is a solution for Open Source Fused Filament Fabrication 3D printing.'))
		s.Add(wx.StaticText(p, -1, 'Cura is currently developed and maintained by Type A Machines, Daid, and Ultimaker.'))

		s.Add(wx.StaticText(p, -1, 'Cura is built with the following components:'), flag=wx.TOP, border=10)
		self.addComponent('Cura Type A', 'Graphical user interface for Series 1', 'AGPLv3', 'https://bitbucket.org/typeamachines/cura')
		self.addComponent('Cura', 'Original graphical user interface', 'AGPLv3', 'https://github.com/daid/Cura')
		self.addComponent('CuraEngine', 'GCode Generator', 'AGPLv3', 'https://github.com/Ultimaker/CuraEngine')
		self.addComponent('Clipper', 'Polygon clipping library', 'Boost', 'http://www.angusj.com/delphi/clipper.php')

		self.addComponent('Python 2.7', 'Framework', 'Python', 'http://python.org/')
		self.addComponent('wxPython', 'GUI Framework', 'wxWindows', 'http://www.wxpython.org/')
		self.addComponent('PyOpenGL', '3D Rendering Framework', 'BSD', 'http://pyopengl.sourceforge.net/')
		self.addComponent('PySerial', 'Serial communication library', 'Python license', 'http://pyserial.sourceforge.net/')
		self.addComponent('NumPy', 'Support library for faster math', 'BSD', 'http://www.numpy.org/')
		if platform.system() == "Windows":
			self.addComponent('VideoCapture', 'Library for WebCam capture on windows', 'LGPLv2.1', 'http://videocapture.sourceforge.net/')
			#self.addComponent('ffmpeg', 'Support for making timelapse video files', 'GPL', 'http://www.ffmpeg.org/')
			self.addComponent('comtypes', 'Library to help with windows taskbar features on Windows 7', 'MIT', 'http://starship.python.net/crew/theller/comtypes/')
			self.addComponent('EjectMedia', 'Utility to safely remove SD cards', 'Freeware', 'http://www.uwe-sieber.de/english.html')
		self.addComponent('Pymclevel', 'Python library for reading Minecraft levels.', 'ISC', 'https://github.com/mcedit/pymclevel')

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
