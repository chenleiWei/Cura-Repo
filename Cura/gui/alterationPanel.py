__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import wx, wx.stc

from Cura.gui.util import gcodeTextArea
from Cura.util import profile

#Panel to change the start & endcode of the gcode.
class alterationPanel(wx.Panel):
	def __init__(self, parent, callback):
		wx.Panel.__init__(self, parent,-1)
		self.callback = callback
		self.alterationFileList = ['start.gcode', 'end.gcode']#, 'nextobject.gcode', 'replace.csv'
		if int(profile.getMachineSetting('extruder_amount')) > 1:
			self.alterationFileList += ['preSwitchExtruder.gcode', 'postSwitchExtruder.gcode']
			self.alterationFileList += ['start2.gcode', 'end2.gcode']
		if int(profile.getMachineSetting('extruder_amount')) > 2:
			self.alterationFileList += ['start3.gcode', 'end3.gcode']
		if int(profile.getMachineSetting('extruder_amount')) > 3:
			self.alterationFileList += ['start4.gcode', 'end4.gcode']
		if int(profile.getMachineSetting('extruder_amount')) > 4:
			self.alterationFileList += ['start5.gcode', 'end5.gcode']
		self.currentFile = None
		self.selected = None
		self.textArea = gcodeTextArea.GcodeTextArea(self)
		self.list = wx.ListBox(self, choices=self.alterationFileList, style=wx.LB_SINGLE)
		self.list.SetSelection(0)
		self.Bind(wx.EVT_LISTBOX, self.OnSelect, self.list)
		self.textArea.Bind(wx.EVT_KILL_FOCUS, self.OnFocusLost, self.textArea)
		self.textArea.Bind(wx.stc.EVT_STC_CHANGE, self.OnFocusLost, self.textArea)

		refreshButton = wx.Button(self, -1, "Save Start/End GCode Changes")
		refreshButton.Bind(wx.EVT_BUTTON, self.OnRefresh)

		sizer = wx.GridBagSizer(5,5)
		sizer.Add(self.list, (0,0), span=(2,0), flag=wx.EXPAND)
		sizer.Add(refreshButton, (3,0), span=(1,0), flag=wx.EXPAND)
		sizer.Add(self.textArea, (4,0), span=(3,0), flag=wx.EXPAND)
		sizer.AddGrowableCol(0)
		sizer.AddGrowableRow(4)
		self.SetSizer(sizer)
		
		self.loadFile(self.alterationFileList[self.list.GetSelection()])
		self.currentFile = self.list.GetSelection()

	def OnSelect(self, e):
		self.loadFile(self.alterationFileList[self.list.GetSelection()])
		self.currentFile = self.list.GetSelection()
		
	def OnRefresh(self, e):
		if self.selected != None:	
			profile.setAlterationFile(self.selected, self.textArea.GetValue())		
		try:
			self.GetParent().GetParent().GetParent().GetParent().GetParent().scene.sceneUpdated()
		except Exception as e:
			raise e		
	def loadFile(self, filename):
		self.textArea.SetValue(profile.getAlterationFile(filename))

	def OnFocusLost(self, e):
		if self.currentFile == self.list.GetSelection():
			self.selected = self.alterationFileList[self.list.GetSelection()]
				
	def updateProfileToControls(self):
		self.OnSelect(None)
