__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import wx
import ConfigParser as configparser
from collections import defaultdict
import os
import re

from Cura.util import profile
from Cura.gui import sceneView
from Cura.util import resources

class simpleModePanel(wx.Panel):
	"Main user interface window for Quickprint mode"
	def __init__(self, parent, callback):
		super(simpleModePanel, self).__init__(parent)
		self._callback = callback

		self._print_profile_options = []
		self._print_material_options = []
		self.lastOpenedFileName = "No File Currently Open"
		printTypePanel = wx.Panel(self)
		for filename in resources.getSimpleModeQualityProfiles():
			cp = configparser.ConfigParser()
			cp.read(filename)
			base_filename = os.path.splitext(os.path.basename(filename))[0]
			name = base_filename
			if cp.has_option('info', 'name'):
				name = cp.get('info', 'name')
			button = wx.RadioButton(printTypePanel, -1, name, style=wx.RB_GROUP if len(self._print_profile_options) == 0 else 0)
			button.base_filename = base_filename
			button.filename = filename
			self._print_profile_options.append(button)
			if profile.getPreference('simpleModeProfile') == base_filename:
				button.SetValue(True)
		
		"""
		printMaterialPanel = wx.Panel(self)
		for filename in resources.getSimpleModeMaterials():
			cp = configparser.ConfigParser()
			cp.read(filename)
			base_filename = os.path.splitext(os.path.basename(filename))[0]
			name = base_filename
			if cp.has_option('info', 'name'):
				name = cp.get('info', 'name')
			button = wx.RadioButton(printMaterialPanel, -1, name, style=wx.RB_GROUP if len(self._print_material_options) == 0 else 0)
			button.base_filename = base_filename
			button.filename = filename
			self._print_material_options.append(button)
			if profile.getPreference('simpleModeMaterial') == base_filename:
				button.SetValue(True)
		"""
		# Panel 1, which dynamically shows the user the name of the last file loaded
		currentFilePanel = wx.Panel(self)
		self.currentFileName = wx.StaticText(currentFilePanel, -1, label = "No File Currently Open")
		
		# Panel 2 of simple mode tools that displays information about loaded filament
		materialSelectorPanel = wx.Panel(self)
		self.selectedMaterial = wx.StaticText(materialSelectorPanel, -1, label = "No Material Profile Loaded")
		self.materialLoadButton = wx.Button(materialSelectorPanel, 4, _("Load Materials"))
		self.printSupport = wx.CheckBox(self, -1, _("Print support structure"))

		# Panel 3 titled "Advanced"; contains print support
		supportSelectionPanel = wx.Panel(self)
		support_raft = wx.RadioButton(supportSelectionPanel, -1, label="Raft")
		support_brim = wx.RadioButton(supportSelectionPanel, -1, label="Brim")
		support_disabled = wx.RadioButton(supportSelectionPanel, -1, label="No Support")
		
		sizer = wx.GridBagSizer()
		self.SetSizer(sizer)
		
		sb = wx.StaticBox(currentFilePanel, label=_("Last File Opened"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		currentFilePanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		boxsizer.Add(self.currentFileName)
		currentFilePanel.GetSizer().Add(boxsizer, flag=wx.EXPAND)
		sizer.Add(currentFilePanel, (0,0), flag=wx.EXPAND)
		
		sb = wx.StaticBox(materialSelectorPanel, label=_("Material Profile"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		materialSelectorPanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		boxsizer.Add(self.selectedMaterial)
		boxsizer.Add(self.materialLoadButton)
		materialSelectorPanel.GetSizer().Add(boxsizer, flag=wx.EXPAND)
		sizer.Add(materialSelectorPanel, (1,0), flag=wx.EXPAND)
		self.popUpBox = PopUpBox(None, -1, 'Materials')
		
		sb = wx.StaticBox(printTypePanel, label=_("Select a quickprint profile:"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		for button in self._print_profile_options:
			boxsizer.Add(button)
		printTypePanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		printTypePanel.GetSizer().Add(boxsizer, flag=wx.EXPAND)
		sizer.Add(printTypePanel, (2,0), flag=wx.EXPAND)
		
		"""
		sb = wx.StaticBox(printMaterialPanel, label=_("Material:"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		for button in self._print_material_options:
			boxsizer.Add(button)
		printMaterialPanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		printMaterialPanel.GetSizer().Add(boxsizer, flag=wx.EXPAND)
		sizer.Add(printMaterialPanel, (3,0), flag=wx.EXPAND)
		"""
		
		sb = wx.StaticBox(supportSelectionPanel, label=_("Support:"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		supportSelectionPanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		boxsizer.Add(support_raft)
		boxsizer.Add(support_brim)
		boxsizer.Add(support_disabled)
		supportSelectionPanel.GetSizer().Add(boxsizer, flag=wx.EXPAND)
		sizer.Add(supportSelectionPanel, (4,0), flag=wx.EXPAND)
		
		sb = wx.StaticBox(self, label=_("Other:"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		boxsizer.Add(self.printSupport)
		sizer.Add(boxsizer, (5,0), flag=wx.EXPAND)
	
		for button in self._print_profile_options:
			button.Bind(wx.EVT_RADIOBUTTON, self._update)
		for button in self._print_material_options:
			button.Bind(wx.EVT_RADIOBUTTON, self._update)

		self.printSupport.Bind(wx.EVT_CHECKBOX, self._update)
		self.Bind(wx.EVT_BUTTON, self.OnSelectBtn, id=4)
		
	def OnSelectBtn(self, event):
		self.popUpBox.Show()
		
	def _update(self, e):
		for button in self._print_profile_options:
			if button.GetValue():
				profile.putPreference('simpleModeProfile', button.base_filename)
		for button in self._print_material_options:
			if button.GetValue():
				profile.putPreference('simpleModeMaterial', button.base_filename)
		self._callback()
		
	def displayLoadedFileName(self):
		# Displays file names as they are loaded into sceneView
		# and references them directly from that source
		mainWindow = self.GetParent().GetParent().GetParent()
		sceneView = mainWindow.scene
		filename = str(os.path.basename(sceneView.filename))
		print("Filename within displayLoadedFileName: %s" %filename)
		if self.lastOpenedFileName != filename:
			self.lastOpenedFileName = filename
			self.currentFileName.SetLabel(str(self.lastOpenedFileName))
		else:
			pass
			
	def getSettingOverrides(self):
		self.displayLoadedFileName()
		settings = {}
		for setting in profile.settingsList:
			if not setting.isProfile():
				continue
			settings[setting.getName()] = setting.getDefault()

		for button in self._print_profile_options:
			if button.GetValue():
				cp = configparser.ConfigParser()
				cp.read(button.filename)
				for setting in profile.settingsList:
					if setting.isProfile():
						if cp.has_option('profile', setting.getName()):
							settings[setting.getName()] = cp.get('profile', setting.getName())
		if profile.getMachineSetting('gcode_flavor') != 'UltiGCode':
			for button in self._print_material_options:
				if button.GetValue():
					cp = configparser.ConfigParser()
					cp.read(button.filename)
					for setting in profile.settingsList:
						if setting.isProfile():
							if cp.has_option('profile', setting.getName()):
								settings[setting.getName()] = cp.get('profile', setting.getName())

		if self.printSupport.GetValue():
			settings['support'] = "Exterior Only"
		return settings

	def updateProfileToControls(self):
		pass
		
	def getMaterialProfiles(self):
		return self.sortedMaterialsProfiles

class PopUpBox(wx.Frame):
	def __init__(self, parent, id, title):
		wx.Frame.__init__(self, parent, id, title, wx.DefaultPosition)
# -----------material profiles organization start-----------
		list = []
		list = resources.getSimpleModeMaterialsProfiles()
				
		brandsList = []
		materialsList = []
		unsortedMaterialsProfiles = {}
		self.sortedMaterialsProfiles = {}
		self.materials = []
		for filename in list:
			m = re.search(r'(\w+)__', filename)
			n = re.search(r'__\w+', filename)
	
			# Takes the first part of filename string to the end of the double underscore
			if m:
				materialsDirectoryList = str(m.group())
				splitString = materialsDirectoryList.split("__")
				removeUnderscores = filter(None, splitString)
				brandsList.append(removeUnderscores)
			# Takes from underscore to second part of the filename string
			if n:
				materialsDirectoryList = str(n.group())
				splitString = materialsDirectoryList.split("__")
				removeUnderscores = filter(None, splitString)
				materialsList.append(removeUnderscores)


		for count in range(0, len(materialsList)):
			material = str(materialsList[count])
			brand = str(brandsList[count])
			# because there are multiple materials for every brand, but not the opposite: it made sense to have 
			# materials play the role of the keys and brands play the role of values
			unsortedMaterialsProfiles.update({material:brand})
	
		# materials are read in as keys and brands are read in as values; takes above info and creates a dictionary 
		# of brands lists containing either a single value or a list of materials belonging to that particular brand
		for materials, brands in unsortedMaterialsProfiles.items():
			self.sortedMaterialsProfiles.setdefault(brands.title(), []).append(materials.title())
	
# -----------material profiles organization end-----------
		vbox = wx.BoxSizer(wx.VERTICAL)
		hbox1 = wx.BoxSizer(wx.HORIZONTAL)
		hbox2 = wx.BoxSizer(wx.HORIZONTAL)
		panel = wx.Panel(self, -1)
		brandNames = []
	#	self.text = [wx.TextCtrl(panel, -1, '', size=(200, 130), style=wx.TE_MULTILINE)]
#		print("BrandNameKeys %s" % self.sortedMaterialsProfiles.items())

		self.text = wx.ListBox(panel, -1, wx.DefaultPosition, (200, 130), self.materials)
		for brands, materials in self.sortedMaterialsProfiles.items():
			brandNames.append(brands.strip('\'[]\''))
			
		self.exampleListBox = wx.ListBox(panel, 26, wx.DefaultPosition, (170,130), brandNames)
		btn = wx.Button(panel, wx.ID_CLOSE, 'Close')
		hbox1.Add(self.exampleListBox, 0, wx.TOP, 40)
		hbox1.Add(self.text, 1, wx.LEFT | wx.TOP, 40)
		hbox2.Add(btn, 1, wx.ALIGN_CENTRE)
		vbox.Add(hbox1, 0, wx.ALIGN_CENTRE)
		vbox.Add(hbox2, 1, wx.ALIGN_CENTRE)
		panel.SetSizer(vbox)
		
		
		self.Bind(wx.EVT_BUTTON, self.OnClose, id=wx.ID_CLOSE)
		self.Bind(wx.EVT_LISTBOX, self.OnSelect, id=26)

	def OnClose(self, event):
		self.Close()		
		
	
	
	def OnSelect(self, event):
		self.text.Clear()
		self.materials[:] = []
		panel = wx.Panel(self)
		index = event.GetSelection()
		brandSelection = self.exampleListBox.GetString(index)
		
		for x, y in self.sortedMaterialsProfiles.items():
			if x.strip('\'[]\'') == brandSelection:
				self.text.Append(str(y))
				
	#	self.text.Append(str(self.materials))
