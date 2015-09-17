__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import wx
import ConfigParser as configparser
from collections import defaultdict
import itertools
from itertools import chain
import os
import re

from Cura.util import profile
from Cura.gui import sceneView
from Cura.util import resources		
from wx.lib.pubsub import Publisher as pub


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
		self.printSupport.SetValue(True)
		
		pub.subscribe(self.refreshSimpleMode, 'settings.refresh')

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
		
		# 1st Panel: Last file loaded
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
		
		# 2nd Panel: Select Quality
		sb = wx.StaticBox(printQualityPanel, label=_("Quality"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		for button, path in self.quality_buttonslist.items():
			basename = os.path.splitext(os.path.basename(path))[0]
			if basename == "final":
				final = button
			elif basename == "normal":
				normal = button
				normal.SetValue(True)
			elif basename == "draft":
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
			if basename == "1_high":
				high = button
			elif basename == "2_medium":
				medium = button
			elif basename == "3_low":
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
	
	def refreshSimpleMode(self, refresh=False):
		if refresh:
			self._callback()
	
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
		
	def updateAdhesion(self, options):
		for name, button in options.items():
			if button.GetValue():
				profile.putProfileSetting('platform_adhesion', name)
		self._callback()

	# Parses name from the filename
	def parseDirectoryItemNames(self, directoryItems):
		names = []
		for filename in directoryItems:
			settingName = os.path.splitext(os.path.basename(filename))[0]
			names.append(settingName)
		return names


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
		filename = str(os.path.basename(str(sceneView.filename)))
		if str(filename) != "None":
			if self.lastOpenedFileName != filename:
				self.lastOpenedFilename = filename
				self.currentFileName.SetLabel(filename)
			
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
		pub.sendMessage('settings.refresh', refresh=True)
		for x, y in self.sortedMaterialsProfiles.items():
			if x.strip('\'[]\'') == brandSelection:
				self.text.Append(str(y))
				
	#	self.text.Append(str(self.materials))
