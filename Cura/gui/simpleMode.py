__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import wx
import ConfigParser as configparser
from collections import defaultdict
import itertools
from itertools import chain
import os
import re
import os.path
from Cura.util import profile
from Cura.gui import sceneView
from Cura.util import resources		
from wx.lib.pubsub import pub

class simpleModePanel(wx.Panel):
	"Main user interface window for Quickprint mode"
	def __init__(self, parent, callback):
		super(simpleModePanel, self).__init__(parent)
		self._callback = callback
		self.profileSettingsList = {}
		self.materialProfileText = wx.TextDataObject(text=profile.getPreference("simpleModeMaterial"))
		self.lastOpenedFileName = "No File Currently Open"

		# Panel 1: Last File Loaded
		currentFilePanel = wx.Panel(self)
		self.currentFileName = wx.StaticText(currentFilePanel, -1, label = "No File Currently Open")
		
		# Panel 2: Material Profile Select
		materialSelectorPanel = wx.Panel(self)
		self.selectedMaterial = wx.StaticText(materialSelectorPanel, -1, label=self.materialProfileText.GetText())
		self.materialLoadButton = wx.Button(materialSelectorPanel, 4, _("Load Material"))
		self.printSupport = wx.CheckBox(self, -1, _("Print support structure"))
		self.printSupport.SetValue(True)
		self.returnProfile = self.selectedMaterial.GetLabel()

		pub.subscribe(self.displayAndLoadMaterialData, 'settings.update')
		pub.subscribe(self.refreshSimpleMode, 'settings.refresh')
		
		# Panel 3: Select Quality
		printQualityPanel = wx.Panel(self)
		self.quality_items = resources.getSimpleModeQualityProfiles()
		self.quality_buttonslist = self.buttonCreator(self.quality_items, setValue="Normal", panel_name=printQualityPanel)
		
		# Panel 4: Structural Strength
		structuralStrengthPanel = wx.Panel(self)
		self.structStrength_items = resources.getSimpleModeStrengthProfiles()
		self.structStrength_buttonslist = self.buttonCreator(self.structStrength_items, setValue="Low", panel_name=structuralStrengthPanel)
		
		# Panel 5: Print Support/Adhesion
		supportSelectionPanel = wx.Panel(self)
		support_raft = wx.RadioButton(supportSelectionPanel, -1, label="Raft")
		support_brim = wx.RadioButton(supportSelectionPanel, -1, label="Brim")
		support_disabled = wx.RadioButton(supportSelectionPanel, -1, label="None")
		support_raft.SetValue(True)
		
		#----------- Panel Items Populate Below ----------- #
		
		sizer = wx.GridBagSizer()
		self.SetSizer(sizer)
		
		# Panel 0: Last File Loaded
		sb = wx.StaticBox(currentFilePanel, label=_("Last File Opened"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		currentFilePanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		boxsizer.Add(self.currentFileName)
		currentFilePanel.GetSizer().Add(boxsizer, flag=wx.EXPAND)
		sizer.Add(currentFilePanel, (0,0), flag=wx.EXPAND)
		
		# Panel 1: Material Profile Select
		sb = wx.StaticBox(materialSelectorPanel, label=_("Material Profile"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		materialSelectorPanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		boxsizer.Add(self.selectedMaterial)
		boxsizer.Add(self.materialLoadButton)
		materialSelectorPanel.GetSizer().Add(boxsizer, flag=wx.EXPAND)
		sizer.Add(materialSelectorPanel, (1,0), flag=wx.EXPAND)
		
		# Panel 2: Select Quality
		sb = wx.StaticBox(printQualityPanel, label=_("Quality"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		# haxxy fix for list order
		for button, path in reversed(self.quality_buttonslist.items()):
			boxsizer.Add(button)
		printQualityPanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		printQualityPanel.GetSizer().Add(boxsizer, flag=wx.EXPAND)
		sizer.Add(printQualityPanel, (2,0), flag=wx.EXPAND)

		# Panel 3: Structural Strength		
		sb = wx.StaticBox(structuralStrengthPanel, label=_("Structural Strength"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		for button, path in self.structStrength_buttonslist.items():
			boxsizer.Add(button)
		structuralStrengthPanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		structuralStrengthPanel.GetSizer().Add(boxsizer, flag=wx.EXPAND)
		sizer.Add(structuralStrengthPanel, (3,0), flag=wx.EXPAND)

		# Panel 4: Support
		# *temporary panel; will be combined with adhesion
		sb = wx.StaticBox(self, label=_("Support"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		boxsizer.Add(self.printSupport)
		sizer.Add(boxsizer, (4,0), flag=wx.EXPAND)

		# Panel 5: Adhesion
		sb = wx.StaticBox(supportSelectionPanel, label=_("Adhesion"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		supportSelectionPanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		boxsizer.Add(support_raft)
		boxsizer.Add(support_brim)
		boxsizer.Add(support_disabled)
		supportSelectionPanel.GetSizer().Add(boxsizer, flag=wx.EXPAND)
		sizer.Add(supportSelectionPanel, (5,0), flag=wx.EXPAND)
		
		for button in self.quality_buttonslist:
			button.Bind(wx.EVT_RADIOBUTTON,  lambda e: self.updateInfo(self.quality_buttonslist, self.quality_items),  self._callback())
		for button in self.structStrength_buttonslist:
			button.Bind(wx.EVT_RADIOBUTTON, lambda e: self.updateInfo(self.structStrength_buttonslist, self.structStrength_items), self._callback())	
		
		self.Bind(wx.EVT_BUTTON, self.OnSelectBtn, id=4)
		
	
	# Overrides particular profile settings with settings corresponding to the selected radio button
	def updateInfo(self, buttonsList, directory):
		toUpdate = []
		for button, path in buttonsList.items():
			if button.GetValue():
				chosenProfile = os.path.splitext(os.path.basename(path))[0]
				toUpdate = self.parseDirectoryItems(chosenProfile, directory, hasName=True)
		for k, v in toUpdate.items():
			if profile.isProfileSetting(k):
				profile.putProfileSetting(k, v)

	# Refreshes simple mode when the user hits select within the materials selection tool
	def refreshSimpleMode(self, refresh=False):
		if refresh:
			self._callback()
		
	# Parses name from the filename
	def parseDirectoryItemNames(self, directoryItems):
		names = []
		for filename in directoryItems:
			settingName = os.path.splitext(os.path.basename(filename))[0]
			names.append(settingName)
		return names
	
	# Reads in key/value pairs from one of the directories located in the resources/quickprint folder 
	def parseDirectoryItems(self, chosenProfile, directory, hasName=False):
		settingsKeyValuePairs = {}
		# reads out all files in the specified directory
		for file in directory:
			base_filename = os.path.splitext(os.path.basename(file))[0]
			# matches base file name to selected profile
			if base_filename.lower() == chosenProfile.lower():
				cp = configparser.ConfigParser()
				# reads items within the matched file
				cp.read(file)
				for name, value in cp.items('profile'):
					settingsKeyValuePairs[name] = value
					
		return settingsKeyValuePairs
		
	def buttonCreator(self, names, setValue, panel_name):
		buttonsList = []
		filePaths = []
		buttons = {}
		namesList = self.parseDirectoryItemNames(names)
		
		for name in namesList:
			button = wx.RadioButton(panel_name, -1, name, style=wx.RB_GROUP)
			if name == setValue:
				button.SetValue(True)
			buttonsList.append(button)
		for name in names:
			filePaths.append(name)
		for n in range(0, len(names)):
			buttons[buttonsList[n]] = filePaths[n]	
		return buttons
			
	def displayAndLoadMaterialData(self, mat):
		profile.putPreference('simpleModeMaterial', mat)
		mainWindow = self.GetParent().GetParent().GetParent()
		self.selectedMaterial.SetLabel(mat)
		self.materialProfileText.SetText(mat)
		settings = {}
		
		for filename in resources.getSimpleModeMaterialsProfiles():	
			n = re.search(r"%s" % mat, filename, re.IGNORECASE)
			if n:
				cp = configparser.ConfigParser()
				cp.read(filename)
				for setting in profile.settingsList:
					# Each material profile within the quickprint materials directory has two sections: 'profile' and 'alterations'
					# The profile section contains not only its respective settings, but also material and preference settings, which should
					# be sections of their own.
					# Below, we load and filter each setting into its respective "sections"
					if cp.has_option('profile', setting.getName()):
						settingName = setting.getName()
						settingValue = cp.get('profile', setting.getName())
						if setting.isProfile():
							profile.putProfileSetting(settingName, settingValue)
							settings[settingName] = settingValue
						elif setting.isPreference():
							profile.putPreference(settingName, settingValue)
						elif setting.isMachineSetting():
							profile.putMachineSetting(settingName, settingValue)
		
		# make sure that the simple mode panel quality/strength overrides are applied
		self.updateInfo(self.quality_buttonslist, self.quality_items)
		self.updateInfo(self.structStrength_buttonslist, self.structStrength_items)
		
		mainWindow.updateProfileToAllControls()
		
		self._callback()
		
	def displayLoadedFileName(self):
		# Displays file names as they are loaded into sceneView
		# and references them directly from that source
		mainWindow = self.GetParent().GetParent().GetParent()
		sceneView = mainWindow.scene
		filename = str(os.path.basename(str(sceneView.filename)))
		if str(filename) != "None":
			if self.lastOpenedFileName != filename:
				self.lastOpenedFilename = filename
				self.currentFileName.SetLabel(filename)
		
	def OnSelectBtn(self, event):
		frame = MaterialSelectorFrame()
		frame.Show()

	def getSettingOverrides(self):
		self.displayLoadedFileName()
		chosenProfile = self.materialProfileText.GetText()
		materials_items = resources.getSimpleModeMaterialsProfiles()

		overrideSettings = self.parseDirectoryItems(chosenProfile, materials_items)
		return overrideSettings
			
	def updateProfileToControls(self):
		pass
		
	def getMaterialProfiles(self):
		return self.sortedMaterialsProfiles


class MaterialSelectorFrame(wx.Frame):
	def __init__(self):
		wx.Frame.__init__(self, None, wx.ID_ANY, "Materials Selection")
		list = resources.getSimpleModeMaterialsProfiles()
		self.Brand = None
		self.Material = None
		self.materialProfile = ""
		self.sortedMaterialsProfiles = {}
		materialsProfilesList = []

		for filename in list:
			cp = configparser.ConfigParser()
			cp.read(filename)
			if cp.has_option('info', 'name'):
				materialProfile = cp.get('info', 'name')
				materialsProfilesList.append(materialProfile)
		
		for item in materialsProfilesList:
			profiles = item.split()
			count =	len(profiles)									
			floatCount = float(count)
			self.sortedMaterialsProfiles.setdefault(profiles[0].title(), []).append(profiles[1])
	
		vbox = wx.BoxSizer(wx.VERTICAL)
		hbox1 = wx.BoxSizer(wx.HORIZONTAL)
		hbox2 = wx.BoxSizer(wx.HORIZONTAL)
		panel = wx.Panel(self, -1)
		self.brandNames = []
		materialNames = []

		for brands, materials in self.sortedMaterialsProfiles.items():
			self.brandNames.append(brands)
			materialNames.append(materials)
			
		self.materialsListBox = wx.ListBox(panel, 27, wx.DefaultPosition, (200, 130), materialNames[0])			
		self.brandsListBox = wx.ListBox(panel, 26, wx.DefaultPosition, (170,130), self.brandNames)
		# highlights first brand options upon window open
		self.brandsListBox.SetSelection(0)
		
		self.btn = wx.Button(panel, 25, 'Select', (150, 130), (110, -1))
		self.btn.Enable(False)
		
		hbox1.Add(self.brandsListBox, 0, wx.TOP, 40)
		hbox1.Add(self.materialsListBox, 1, wx.LEFT | wx.TOP, 40)
		hbox2.Add(self.btn, 26, wx.ALIGN_CENTRE)
		vbox.Add(hbox1, 0, wx.ALIGN_CENTRE)
		vbox.Add(hbox2, 1, wx.ALIGN_CENTRE)
		panel.SetSizer(vbox)
			
		self.Bind(wx.EVT_BUTTON, self.OnSelectMaterialProfile, id=25)
		self.Bind(wx.EVT_LISTBOX, self.OnBrandSelect, id=26)
		self.Bind(wx.EVT_LISTBOX, self.OnMaterialSelect, id=27)

	def OnClose(self, event):
		self.Close()	
		
	def OnEnable(self, enable):
		if enable:
			self.btn.Enable(True)
				
	def OnSelectMaterialProfile(self, event):
		myObject = event.GetEventObject()
		if self.Brand is None:
			self.Brand = self.brandNames[0]
		if self.Brand and self.Material is not None:
			self.materialProfile = str(self.Brand) + "__" + self.Material
			pub.sendMessage('settings.update', mat=self.materialProfile)
			print("Mat: %s" % self.materialProfile)
			pub.sendMessage('settings.refresh', refresh=True)	
		self.Close()

	def OnBrandSelect(self, event):
		self.materialsListBox.Clear()
		self.materials = []
		panel = wx.Panel(self)
		index = event.GetSelection()
		brandSelection = self.brandsListBox.GetString(index)
		
		for x, y in self.sortedMaterialsProfiles.items():
			if x == brandSelection:
				self.materials.append(itertools.chain(y))
				
		materialsList = itertools.chain.from_iterable(self.materials)
		self.materials = materialsList
		self.materialsListBox.Set(list(self.materials))
		self.Brand = brandSelection
		
	# Displays specific material selection
	def OnMaterialSelect(self, event):
		index = event.GetSelection()
		materialSelection = self.materialsListBox.GetString(index)
		
		self.Material = materialSelection
		self.OnEnable(True)
