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
		self.printSupport = wx.CheckBox(self, 6, _("Print support structure"))
		self.printSupport.SetValue(True)
		self.returnProfile = self.selectedMaterial.GetLabel()

		pub.subscribe(self.displayAndLoadMaterialData, 'settings.update')
		pub.subscribe(self.refreshSimpleMode, 'settings.refresh')
		pub.subscribe(self.updateInfoPanelData, 'data.update')
		
		# Panel 3: Select Quality
		printQualityPanel = wx.Panel(self)
		self.quality_items = resources.getSimpleModeQualityProfiles()
		initialQualityValue = profile.getPreference('simpleModeQuality')
		self.quality_buttonslist = self.buttonCreator(self.quality_items, panel_name=printQualityPanel)
		
		# Panel 4: Structural Strength
		structuralStrengthPanel = wx.Panel(self)
		self.structStrength_items = resources.getSimpleModeStrengthProfiles()
		initialStrengthValue = profile.getPreference('simpleModeStrength')
		self.structStrength_buttonslist = self.buttonCreator(self.structStrength_items, panel_name=structuralStrengthPanel)
		
		# Panel 5: Print Support/Adhesion
		supportSelectionPanel = wx.Panel(self)
		support_raft = wx.RadioButton(supportSelectionPanel, -1, label="Raft")
		support_brim = wx.RadioButton(supportSelectionPanel, -1, label="Brim")
		support_disabled = wx.RadioButton(supportSelectionPanel, -1, label="None")
		support_raft.SetValue(True)
		
		# Panel 6: Info Panel
		infoPanel = wx.Panel(self)
		self.infoPanelSettingsList = self.InitializeInfoPanelList(infoPanel)
		
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
		gridsizer = wx.FlexGridSizer(1,1,0,0)
		gridsizer.Add(self.selectedMaterial)
		gridsizer.Add(self.materialLoadButton)
		boxsizer.Add(gridsizer)
		materialSelectorPanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		materialSelectorPanel.GetSizer().Add(boxsizer, flag=wx.EXPAND)
		sizer.Add(materialSelectorPanel, (1,0), flag=wx.EXPAND)
		
		# Panel 2: Select Quality
		sb = wx.StaticBox(printQualityPanel, label=_("Quality"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		for button, path in self.quality_buttonslist.items():
			basename = os.path.splitext(os.path.basename(path))[0]
			if basename == "Final":
				final = button
			elif basename == "Normal":
				normal = button
				normal.SetValue(True)
			elif basename == "Draft":
				draft = button
		boxsizer.Add(final)
		boxsizer.Add(normal)
		boxsizer.Add(draft)
		printQualityPanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		printQualityPanel.GetSizer().Add(boxsizer, flag=wx.EXPAND)
		sizer.Add(printQualityPanel, (2,0), flag=wx.EXPAND)

		# Panel 3: Structural Strength		
		sb = wx.StaticBox(structuralStrengthPanel, label=_("Strength"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		for button, path in self.structStrength_buttonslist.items():
			basename = os.path.splitext(os.path.basename(path))[0]
			if basename == "High":
				high = button
			elif basename == "Medium":
				medium = button
			elif basename == "Low":
				low = button
				low.SetValue(True)
		boxsizer.Add(high)
		boxsizer.Add(medium)
		boxsizer.Add(low)
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

		self.platformAdhesionOptions = {'Raft': support_raft, 'Brim': support_brim, 'None':support_disabled}
		settingOrder = ["Layer Height", "Print Temperature", "Print Bed Temperature", "Wall Thickness", "Fill Density"]
		if profile.getMachineSetting('has_heated_bed') == "False":
			settingOrder.remove("Print Bed Temperature")
		# Panel 6: Info Box
		# make a list of units to add as a third column
		sb = wx.StaticBox(infoPanel, label=_("Settings Info"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		gridsizer = wx.FlexGridSizer(6,2,7,10)
		
		for item in range(len(settingOrder)):
			for setting, value in self.infoPanelSettingsList.items():
				# replaces double-underscore with a space
				rx = '[' + re.escape(''.join(["\_\_"])) + ']'
				settingName = re.sub(rx, ' ', setting.title())
				if settingOrder[item] == settingName:
					displayName = wx.StaticText(infoPanel, -1, label = (settingName + ": "))
					displayName.SetFont(wx.Font(12, wx.SWISS, wx.NORMAL, wx.NORMAL))
					gridsizer.Add(displayName, flag=wx.ALIGN_LEFT)
					value.SetFont(wx.Font(14, wx.SWISS, wx.NORMAL, wx.NORMAL))
					gridsizer.Add(value, wx.ALIGN_LEFT, wx.BOTTOM, border=0)

		boxsizer.Add(gridsizer)
		infoPanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		infoPanel.GetSizer().Add(boxsizer)
		sizer.Add(infoPanel, (6,0))
		
		for button in self.quality_buttonslist:
			button.Bind(wx.EVT_RADIOBUTTON,  lambda e: self.updateInfo(self.quality_buttonslist, self.quality_items, preference="quality"),  self._callback())
		for button in self.structStrength_buttonslist:
			button.Bind(wx.EVT_RADIOBUTTON, lambda e: self.updateInfo(self.structStrength_buttonslist, self.structStrength_items, preference="strength"), self._callback())
		self.Bind(wx.EVT_BUTTON, self.OnSelectBtn, id=4)
		for name, button in self.platformAdhesionOptions.items():
			button.Bind(wx.EVT_RADIOBUTTON, lambda e: self.updateAdhesion(self.platformAdhesionOptions), self._callback())
			
		self.printSupport.Bind(wx.EVT_CHECKBOX, lambda e: self.updateSupport(self.printSupport), self._callback())
	
	def InitializeInfoPanelList(self, infoPanel):
		mainWindow = self.GetParent().GetParent().GetParent()
		settingsToDisplay = {}
		settingNames = ['layer_height', 'print_temperature', 'print_bed_temperature', 'fill_density', 'wall_thickness']
		newValue = None
		degree_sign= u'\N{DEGREE SIGN}'
		# Check to see if heated bed and retraction are enabled; if not, remove them from display list
		if profile.getMachineSetting('has_heated_bed') == "False": settingNames.remove('print_bed_temperature')
		
		# dictionary key is set to setting name, dictionary value is set to static text object with label specific to what is set in profile at that point;
		# quality and strength panels need to override this
		for setting in settingNames:
			if setting == "fill_density":
				fill_density_display = str(profile.getProfileSetting(setting) + "%")
				settingsToDisplay[setting] = wx.StaticText(infoPanel, -1, label=fill_density_display)
			elif setting == "print_temperature": 
				print_temperature_display = str(profile.getProfileSetting(setting)) + degree_sign + "C"
				settingsToDisplay[setting] =  wx.StaticText(infoPanel, -1, label=print_temperature_display)
			elif setting == "print_bed_temperature":
				bed_temperature_display = str(profile.getProfileSetting(setting)) + degree_sign + "C"
				settingsToDisplay[setting] =  wx.StaticText(infoPanel, -1, label=bed_temperature_display)
			else:
				mm_display = str(profile.getProfileSetting(setting) + "mm")
				settingsToDisplay[setting] = wx.StaticText(infoPanel, -1, label=mm_display)
				
		for setting in settingNames:
			for button, path in self.quality_buttonslist.items():
				if button.GetValue():
					cp = configparser.ConfigParser()
					cp.read(path)
					if cp.has_section('profile'):
						for name, value in cp.items('profile'):
							if name == setting:
								profile.putProfileSetting(name, value)
								if name == "fill_density":
									settingsToDisplay[name].SetLabel(str(value) + "%")
								elif name == "print_temperature" or name == "bed_temperature":
									settingsToDisplay[name].SetLabel(value + degree_sign + "C")
								else:
									settingsToDisplay[name].SetLabel(str(value) + "mm")
							
			for button, path in self.structStrength_buttonslist.items():
				if button.GetValue():
					cp = configparser.ConfigParser()
					cp.read(path)
					if cp.has_section('profile'):
						for name, value in cp.items('profile'):
							if name == setting:
								profile.putProfileSetting(name, value)
								if name == "fill_density":
									settingsToDisplay[name].SetLabel(str(value) + "%")
								elif name == "print_temperature" or name == "bed_temperature":
									settingsToDisplay[name].SetLabel(str(value) + degree_sign + "C")
								else:
									settingsToDisplay[name].SetLabel(str(value) + "mm")
									
		self._callback()
		return settingsToDisplay
	
	# Overrides particular profile settings with settings corresponding to the selected radio button
	def updateInfo(self, buttonsList, directory, preference):
		mainWindow = self.GetParent().GetParent().GetParent()
		toUpdate = {}
		updatePanelValues = {}
		for button, path in buttonsList.items():
			if button.GetValue():
				chosenProfile = os.path.splitext(os.path.basename(path))[0]
				if preference == "quality":
					profile.putPreference('simpleModeQuality', chosenProfile)
				if preference == "strength":
					profile.putPreference('simpleModeStrength', chosenProfile)
				toUpdate = self.parseDirectoryItems(chosenProfile, directory, hasName=True)
		for k, v in toUpdate.items():
				updatePanelValues[k] = v
				profile.putProfileSetting(k, v)
						
		pub.sendMessage('data.update', settings=updatePanelValues)
		mainWindow.updateProfileToAllControls()
		self._callback()
						
	def updateAdhesion(self, options):
		for name, button in options.items():
			if button.GetValue():
				profile.putProfileSetting('platform_adhesion', name)
		self._callback()
	
	def updateSupport(self, button):
		if button.GetValue() or button.IsChecked():
			profile.putProfileSetting('support', 'Everywhere')
		else: 
			profile.putProfileSetting('support', 'None')
		self._callback()

												
	def updateInfoPanelData(self, settings):
		mainWindow = self.GetParent().GetParent().GetParent()
		degree_sign= u'\N{DEGREE SIGN}'
		for k, v in settings.items():
			for name, textObject in self.infoPanelSettingsList.items():
				if k == name:
					if k == "fill_density":
						self.infoPanelSettingsList[k].SetLabel(v + "%")
					elif k == "print_temperature": 
						self.infoPanelSettingsList[k].SetLabel(str(v) + degree_sign + "C")
					elif k == "print_bed_temperature":
						self.infoPanelSettingsList[k].SetLabel(str(v) + degree_sign + "C")
					else:
						self.infoPanelSettingsList[k].SetLabel(v + "mm")
		mainWindow.updateProfileToAllControls()
		self._callback()

	"""
	# overrides for support and adhesion
	def updateSupportAndAdhesion(self, buttonsList):
		mainWindow = self.GetParent().GetParent().GetParent()
		for k, v in buttonsList.items():
			if k == 'Everywhere':
				if v.IsChecked():
					profile.putProfileSetting('support', k)
				else:
					profile.putProfileSetting('support', 'None')
				mainWindow.updateProfileToAllControls()
			else:
				if v.GetValue():
					if k == 'Raft':
						profile.putProfileSetting('platform_adhesion', k)
					elif k == 'Brim':
						profile.putProfileSetting('platform_adhesion', k)
					elif k =='None':
							profile.putProfileSetting('platform_adhesion', k)
					mainWindow.updateProfileToAllControls()

		self._callback()
	"""
	
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
		
	def buttonCreator(self, names, panel_name):
		buttonsList = []
		filePaths = []
		buttons = {}
		namesList = self.parseDirectoryItemNames(names)
		
		for name in namesList:
			button = wx.RadioButton(panel_name, -1, name)
			buttonsList.append(button)
		for name in names:
			filePaths.append(name)
		for n in range(0, len(names)):
			buttons[buttonsList[n]] = filePaths[n]	
		return buttons
			
	def displayAndLoadMaterialData(self, mat):
	#	profile.putPreference('simpleModeMaterial', mat)
		mainWindow = self.GetParent().GetParent().GetParent()
		degree_sign= u'\N{DEGREE SIGN}'
	#	self.selectedMaterial.SetLabel(mat)
	#	self.materialProfileText.SetText(mat)
		settings = {}
		profile_filename = None
		manufacturer = mat["manufacturer"]
		materialName = mat["name"]
	
		for filename in resources.getSimpleModeMaterialsProfiles():	
			cp = configparser.ConfigParser()
			cp.read(filename)
			if cp.has_section('info'):
				if cp.get('info', 'manufacturer') == manufacturer and cp.get('info', 'name') == materialName:
					profile_filename = os.path.splitext(os.path.basename(filename))[0]
					self.materialProfileText.SetText(profile_filename)
					self.selectedMaterial.SetLabel(profile_filename)
					profile.putPreference('simpleModeMaterial', profile_filename)
					for setting, value in cp.items('profile'):
						profile.putProfileSetting(setting, value)
						settings[setting] = value

		"""
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
		"""
		# updates info display
		for setting, value in settings.items():
			for name, textObject in self.infoPanelSettingsList.items():
				if setting == name: 
					if setting == "fill_density":
						self.infoPanelSettingsList[setting].SetLabel(value + "%")
					elif setting == "print_temperature": 
						self.infoPanelSettingsList[setting].SetLabel(value + degree_sign + "C")
					elif setting == "print_bed_temperature":
						self.infoPanelSettingsList[setting].SetLabel(value + degree_sign + "C")
					else:
						self.infoPanelSettingsList[setting].SetLabel(value + "mm")				
		mainWindow.updateProfileToAllControls()
		self._callback()

							
		 # make sure that the simple mode panel quality/strength overrides are applied
		self.updateInfo(self.quality_buttonslist, self.quality_items, preference="quality")
		self.updateInfo(self.structStrength_buttonslist, self.structStrength_items, preference="strength")
		self.updateAdhesion(self.platformAdhesionOptions)
		self.updateSupport(self.printSupport)
		

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
		quality_items = resources.getSimpleModeQualityProfiles()
		strength_items = resources.getSimpleModeStrengthProfiles()
		materials_items = resources.getSimpleModeMaterialsProfiles()
		
		chosenProfile = self.materialProfileText.GetText()
		chosenStrengthQuality = profile.getPreference('simpleModeStrength')
		chosenPrintQuality = profile.getPreference('simpleModeQuality')
				
		qualitySettings = self.parseDirectoryItems(chosenPrintQuality, quality_items)
		strengthSettings = self.parseDirectoryItems(chosenStrengthQuality, strength_items)
		overrideSettings = self.parseDirectoryItems(chosenProfile, materials_items)
		overrideSettings.update(strengthSettings)
		overrideSettings.update(qualitySettings)
		
		for adhesion, button in  self.platformAdhesionOptions.items():
			if button.GetValue():
				overrideSettings['platform_adhesion'] = adhesion
				
		if self.printSupport.GetValue():
			overrideSettings['support'] = 'Everywhere'
		else:
			overrideSettings['support'] = 'None'
			
		return overrideSettings
			
	def updateProfileToControls(self):
		pass
		

class MaterialSelectorFrame(wx.Frame):
	def __init__(self):
		wx.Frame.__init__(self, None, wx.ID_ANY, "Materials Selection", size=(500,350))
		self.list = resources.getSimpleModeMaterialsProfiles()
		self.Brand = None
		self.Material = None
		self.materialProfile = {"manufacturer": None, "name": None}
		self.sortedMaterialsProfiles = {}
		materialsProfilesList = []
		splitList = []
		brandsList = []
		materialsList = []
		for filename in self.list:
			cp = configparser.ConfigParser()
			cp.read(filename)
			if cp.has_option('info', 'manufacturer') and cp.has_option('info', 'name'):
				manufacturer = cp.get('info', 'manufacturer')
				name = cp.get('info', 'name')
				self.sortedMaterialsProfiles.setdefault(manufacturer, []).append(name)
		
		"""
		for item in materialsProfilesList:
			name = str(item)
			splitList.append(name.split(None, 2))
			# search for brand (first word in name)
			m = re.compile(r"^\s*([a-zA-Z0-9]+)")
			# search for material (second word in name)
			n = re.compile(r"^(?:\S+\s){1}(\S+)")
			
			brand = m.match(item)
			material = n.match(item)
			# if matched, then sort into dictionary
			if material and brand: 
				pass	
		"""
			
		vbox = wx.BoxSizer(wx.VERTICAL)
		hbox0 = wx.BoxSizer(wx.HORIZONTAL)
		titles = wx.GridSizer(1, 2, 0, 150)
		hbox1 = wx.BoxSizer(wx.HORIZONTAL)
		hbox2 = wx.BoxSizer(wx.HORIZONTAL)
		panel = wx.Panel(self, -1)
		self.brandNames = []
		materialNames = []

		for brands, materials in self.sortedMaterialsProfiles.items():
			self.brandNames.append(brands)
			materialNames.append(materials)
			
		self.materialsListBox = wx.ListBox(panel, 27, wx.DefaultPosition, (200, 200), style=wx.LB_SORT)
		self.brandsListBox = wx.ListBox(panel, 26, wx.DefaultPosition, (200, 200), choices = self.brandNames, style=wx.LB_SORT)
		self.brandsListBox.SetSelection(0)
		self.Brand = self.brandsListBox.GetString(0)
		self.materialsListBox.Set(self.sortedMaterialsProfiles[self.Brand])
		brandsTitle = wx.StaticText(panel, 2, label = "Supplier", pos=wx.DefaultPosition)
		materialsTitle = wx.StaticText(panel, 2, label="Name", pos=wx.DefaultPosition)
		brandsTitle.SetFont(wx.Font(20, wx.SWISS, wx.NORMAL, wx.NORMAL))
		materialsTitle.SetFont(wx.Font(20, wx.SWISS, wx.NORMAL, wx.NORMAL))
		# highlights first brand options upon window open
		self.brandsListBox.SetSelection(0)
		self.btn = wx.Button(panel, 25, 'Select', pos=(150, 150), size=(110, -1))
		self.btn.SetFont(wx.Font(20, wx.SWISS, wx.NORMAL, wx.NORMAL))
		self.btn.GetDefaultSize()
		self.btn.Enable(False)
		
		titles.Add(brandsTitle, 2)
		titles.Add(materialsTitle, 2)
		hbox1.Add(self.brandsListBox, 26, wx.RIGHT, 15)
		hbox1.Add(self.materialsListBox, 27, wx.LEFT, 15)
		hbox2.Add(self.btn, 26, wx.ALIGN_CENTRE)
		vbox.Add(titles, 0, wx.ALIGN_CENTER | wx.TOP, 10)
		vbox.Add(hbox1, 0, wx.ALIGN_CENTRE)
		vbox.Add(hbox2, 1, wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, 10)
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
		if self.Brand is None:
			self.Brand = self.brandNames[0]
		if self.Brand and self.Material is not None:
			self.materialProfile["manufacturer"] = self.Brand
			self.materialProfile["name"] = self.Material
			pub.sendMessage('settings.update', mat=self.materialProfile)
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
