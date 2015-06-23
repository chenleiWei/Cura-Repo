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
		self._print_profile_options = []
		self._print_material_options = []
		self.profileSettingsList = {}
		self.materialProfileText = wx.TextDataObject(text=profile.getPreference("simpleModeMaterial"))
		self.lastOpenedFileName = "No File Currently Open"

		# Panel 1: Last File Loaded
		currentFilePanel = wx.Panel(self)
		self.currentFileName = wx.StaticText(currentFilePanel, -1, label = "No File Currently Open")
		
		# Panel 2: Material Profile Select
		materialSelectorPanel = wx.Panel(self)
		self.selectedMaterial = wx.StaticText(materialSelectorPanel, -1, label=self.materialProfileText.GetText())
		self.materialLoadButton = wx.Button(materialSelectorPanel, 4, _("Load Materials"))
		self.printSupport = wx.CheckBox(self, -1, _("Print support structure"))
		self.printSupport.SetValue(True)
		self.returnProfile = self.selectedMaterial.GetLabel()

		pub.subscribe(self.displayAndLoadMaterialData, 'settings.update')
		pub.subscribe(self.refreshSimpleMode, 'settings.refresh')
		
		# Panel 3: Select Quality
		printQualityPanel = wx.Panel(self)
		quality_items = resources.getSimpleModeQualityProfiles()
		quality_ButtonsList = self.buttonCreator(quality_items, setValue="Normal", panel_name=printQualityPanel)
		
		print("Material Profile Text: %s" % self.materialProfileText.GetText())
		
		# Panel 4: Structural Strength
		structuralStrengthPanel = wx.Panel(self)
		structuralStrength_Items = resources.getSimpleModeStrengthProfiles()
		structuralStrength_ButtonsList = self.buttonCreator(structuralStrength_Items, setValue="Medium", panel_name=structuralStrengthPanel)
		
		chosenProfile = self.materialProfileText.GetText()
		materials_items = resources.getSimpleModeMaterialsProfiles()
		self.overrideSettings = self.parseDirectoryItems(chosenProfile, materials_items)
		
		# Panel 5: Print Support/Adhesion
		supportSelectionPanel = wx.Panel(self)
		support_raft = wx.RadioButton(supportSelectionPanel, -1, label="Raft")
		support_brim = wx.RadioButton(supportSelectionPanel, -1, label="Brim")
		support_disabled = wx.RadioButton(supportSelectionPanel, -1, label="No Support")
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
		# Items aren't being populated correctly here
		sb = wx.StaticBox(printQualityPanel, label=_("Quality"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		for button, path in quality_ButtonsList.items():
			boxsizer.Add(button)
		
		printQualityPanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		printQualityPanel.GetSizer().Add(boxsizer, flag=wx.EXPAND)
		sizer.Add(printQualityPanel, (2,0), flag=wx.EXPAND)

		# Panel 3: Structural Strength		
		sb = wx.StaticBox(structuralStrengthPanel, label=_("Structural Strength"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		for button, path in structuralStrength_ButtonsList.items():
			boxsizer.Add(button)
		structuralStrengthPanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		structuralStrengthPanel.GetSizer().Add(boxsizer, flag=wx.EXPAND)
		sizer.Add(structuralStrengthPanel, (3,0), flag=wx.EXPAND)

		# Panel 4: Adhesion
		sb = wx.StaticBox(supportSelectionPanel, label=_("Adhesion"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		supportSelectionPanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		boxsizer.Add(support_raft)
		boxsizer.Add(support_brim)
		boxsizer.Add(support_disabled)
		supportSelectionPanel.GetSizer().Add(boxsizer, flag=wx.EXPAND)
		sizer.Add(supportSelectionPanel, (4,0), flag=wx.EXPAND)
		
		# Panel 5: Support
		# *temporary panel; will be combined with adhesion
		sb = wx.StaticBox(self, label=_("Support"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		boxsizer.Add(self.printSupport)
		sizer.Add(boxsizer, (5,0), flag=wx.EXPAND)
		
		for button in quality_ButtonsList:
			button.Bind(wx.EVT_RADIOBUTTON,  lambda e: self.updateInfo(quality_ButtonsList, quality_items),  self._callback())
		for button in structuralStrength_ButtonsList:
			button.Bind(wx.EVT_RADIOBUTTON, lambda e: self.updateInfo(structuralStrength_ButtonsList, structuralStrength_Items), self._callback())	
		
		self.Bind(wx.EVT_BUTTON, self.OnSelectBtn, id=4)
		
	
	# Overrides particular profile settings with settings corresponding to the selected radio button
	def updateInfo(self, buttonsList, directory):
		toUpdate = []
		for button, path in buttonsList.items():
			if button.GetValue():
				chosenProfile = os.path.splitext(os.path.basename(path))[0]
				toUpdate = self.parseDirectoryItems(chosenProfile, directory, hasName=True)
		for k, v in toUpdate.items():
			if profile.isPreference(k):
				profile.putPreference(k, v)
			elif profile.isMachineSetting(k):
				profile.putMachineSetting(k, v)
			elif profile.isProfileSetting(k):
				profile.putProfileSetting(k, v)
	#			print("profile.putProfileSetting(%s, %s)" % (k, v))
			else:
				print "None of the above"
		
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
		mainWindow.updateProfileToAllControls()
		self._callback()
		
	def displayLoadedFileName(self):
		# Displays file names as they are loaded into sceneView
		# and references them directly from that source
		mainWindow = self.GetParent().GetParent().GetParent()
		sceneView = mainWindow.scene
		filename = str(os.path.basename(str(sceneView.filename)))
		print("Filename within displayLoadedFileName: %s" %filename)
		if self.lastOpenedFileName != filename:
			self.lastOpenedFileName = filename
			self.currentFileName.SetLabel(str(self.lastOpenedFileName))
		else:
			pass

	def OnSelectBtn(self, event):
		frame = MaterialSelectorFrame()
		frame.Show()

	def getSettingOverrides(self):
		self.displayLoadedFileName()
		return self.overrideSettings
			
	def updateProfileToControls(self):
		pass
		
	def getMaterialProfiles(self):
		return self.sortedMaterialsProfiles


class MaterialSelectorFrame(wx.Frame):
	def __init__(self):
		wx.Frame.__init__(self, None, wx.ID_ANY, "Secondary Frame")
		list = []
		list = resources.getSimpleModeMaterialsProfiles()
		self.Brand = None
		self.materialProfile = ""
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
	
		vbox = wx.BoxSizer(wx.VERTICAL)
		hbox1 = wx.BoxSizer(wx.HORIZONTAL)
		hbox2 = wx.BoxSizer(wx.HORIZONTAL)
		panel = wx.Panel(self, -1)
		brandNames = []

		self.text = wx.ListBox(panel, 27, wx.DefaultPosition, (200, 130), choices=str(self.materials).strip('\'[]\''))
		for brands, materials in self.sortedMaterialsProfiles.items():
			brandNames.append(brands.strip('\'[]\''))
			
		self.exampleListBox = wx.ListBox(panel, 26, wx.DefaultPosition, (170,130), brandNames)
		self.btn = wx.Button(panel, 25, 'Select', (150, 130), (110, -1))
		self.btn.Enable(False)
		hbox1.Add(self.exampleListBox, 0, wx.TOP, 40)
		hbox1.Add(self.text, 1, wx.LEFT | wx.TOP, 40)
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
		if self.Brand and self.Material is not None:
			self.materialProfile = str(self.Brand) + "__" + self.Material.strip('\'[]\'')
			pub.sendMessage('settings.update', mat=self.materialProfile)
			pub.sendMessage('settings.refresh', refresh=True)	
		self.Close()

	def OnBrandSelect(self, event):
		self.text.Clear()
		self.materials = []
		panel = wx.Panel(self)
		index = event.GetSelection()
		brandSelection = self.exampleListBox.GetString(index)
		
		for x, y in self.sortedMaterialsProfiles.items():
			if x.strip('\'[]\'') == brandSelection:
				self.materials.append(itertools.chain(y))
				
		materialsList = itertools.chain.from_iterable(self.materials)
		self.materials = materialsList
		self.text.Set(list(self.materials))
		self.Brand = brandSelection
		
	# Displays specific material selection
	def OnMaterialSelect(self, event):
		index = event.GetSelection()
		materialSelection = self.text.GetString(index)
		
		self.Material = materialSelection
		self.OnEnable(True)
