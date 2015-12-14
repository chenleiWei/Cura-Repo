import wx
from wx.lib.pubsub import pub
import ConfigParser as configparser
from collections import defaultdict
import itertools
from itertools import chain
import os
import re

from Cura.util import profile
from Cura.util import resources


class simpleModePanel(wx.Panel):
	"Main user interface window for Quickprint mode"
	def __init__(self, parent, callback):
		super(simpleModePanel, self).__init__(parent)
		self._callback = callback

		self.matManufacturer = profile.getPreference('simpleModeMaterialSupplier')
		self.matName = profile.getPreference('simpleModeMaterialName')
		self.profileSettingsList = {}
		self.materialProfileText = wx.TextDataObject(profile.getPreference('simpleModeMaterial'))
		self.lastOpenedFileName = "No File Currently Open"

		pub.subscribe(self.displayAndLoadMaterialData, 'matProf.update')
		pub.subscribe(self.refresh, 'app.refresh')
		
		# Panel 0: Last File Loaded
		currentFilePanel = wx.Panel(self)
		self.currentFileName = wx.StaticText(currentFilePanel, -1, label = "No File Currently Open")
		
		# Panel 1: Material Profile Select
		materialSelectorPanel = wx.Panel(self)
		self.selectedMaterial = wx.StaticText(materialSelectorPanel, -1, label=self.materialProfileText.GetText())
		self.materialLoadButton = wx.Button(materialSelectorPanel, 4, _("Load Material"))
		self.printSupport = wx.CheckBox(self, 6, _("Print support structure"))
		self.printSupport.SetValue(True)
		self.returnProfile = self.selectedMaterial.GetLabel()
		
		# Panel 2: Select Quality
		printQualityPanel = wx.Panel(self)
		qualityDirectory = resources.getSimpleModeQualityProfiles()
		self.qualityOptions = self.createDataDict(qualityDirectory, panel=printQualityPanel)

		# Panel 3: Structural Strength
		strengthPanel = wx.Panel(self)
		strengthDirectory = resources.getSimpleModeStrengthProfiles()
		self.strengthOptions = self.createDataDict(strengthDirectory, panel=strengthPanel)
		
		# Panel 4/5: Print Support/Adhesion
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
		gridsizer = wx.FlexGridSizer(2,1,1,1)
		gridsizer.Add(self.selectedMaterial, flag=wx.EXPAND)
		gridsizer.Add(self.materialLoadButton)
		boxsizer.Add(gridsizer)
		materialSelectorPanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		materialSelectorPanel.GetSizer().Add(boxsizer, flag=wx.EXPAND)
		sizer.Add(materialSelectorPanel, (1,0), flag=wx.EXPAND)
		
		# Panel 2: Select Quality
		sb = wx.StaticBox(printQualityPanel, label=_("Quality"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		qualityInfo = {}
		qualityButtons = {}

		for button, info in self.qualityOptions.items():
			for name, path in info.items():
				qualityButtons[name] = button
				qualityInfo[name] = path
				
		boxsizer.Add(qualityButtons["Final"])
		boxsizer.Add(qualityButtons["Normal"])
		boxsizer.Add(qualityButtons["Draft"])
		qualityButtons["Normal"].SetValue(True)
		printQualityPanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		printQualityPanel.GetSizer().Add(boxsizer, flag=wx.EXPAND)
		sizer.Add(printQualityPanel, (2,0), flag=wx.EXPAND)
		
		# Panel 3: Select Strength
		sb = wx.StaticBox(strengthPanel, label=_("Strength"))
		strengthButtons = {}
		strengthInfo = {}
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		
		for button, info in self.strengthOptions.items():
			for name, path in info.items():
				strengthButtons[name] = button
				strengthInfo[name] = path
				
		boxsizer.Add(strengthButtons["High"])
		boxsizer.Add(strengthButtons["Medium"])
		boxsizer.Add(strengthButtons["Low"])
		strengthButtons["Low"].SetValue(True)
						
		strengthPanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		strengthPanel.GetSizer().Add(boxsizer, flag=wx.EXPAND)
		sizer.Add(strengthPanel, (3,0), flag=wx.EXPAND)

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
					gridsizer.Add(displayName, flag=wx.ALIGN_LEFT)
					gridsizer.Add(value, wx.ALIGN_LEFT, wx.RIGHT | wx.EXPAND, border=2)

		boxsizer.Add(gridsizer)
		infoPanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		infoPanel.GetSizer().Add(boxsizer, flag=wx.EXPAND)
		sizer.Add(infoPanel, (6,0))
		
		for name, button in strengthButtons.items():
			button.Bind(wx.EVT_RADIOBUTTON, self.strengthSelected)

		for name, button in qualityButtons.items():
			button.Bind(wx.EVT_RADIOBUTTON, self.qualitySelected)
		
		for name, button in self.platformAdhesionOptions.items():
			button.Bind(wx.EVT_RADIOBUTTON, lambda e: self.updateAdhesion(self.platformAdhesionOptions), self._callback())
			
		self.printSupport.Bind(wx.EVT_CHECKBOX, lambda e: self.updateSupport(self.printSupport), self._callback())

		self.materialLoadButton.Bind(wx.EVT_BUTTON, self.OnSelectBtn, id=4)
	
	def refresh(self, e):
		self._callback()
	
	def createDataDict(self, filePaths, panel):
		data = []
		dataDict = {}
		for filePath in filePaths:
			cp = configparser.ConfigParser()
			cp.read(filePath)
			if cp.has_section('info'):
				name = cp.get('info', 'name')
				button = wx.RadioButton(panel, -1, name)
				dataDict.setdefault(button, {})[name] = filePath
		return dataDict

	def strengthSelected(self, e):
		for button, info in self.strengthOptions.items():
			if button == e.GetEventObject():
				for name, path in info.items():
					self.updateInfo(path)
	
	def qualitySelected(self, e):
		for button, info in self.qualityOptions.items():
			if button == e.GetEventObject():
				for name, path in info.items():
					self.updateInfo(path)
				
	def updateInfo(self, path):
		settings = self.getSectionItems(path, 'profile')
		self.loadData(settings, 'info')
		self.loadData(settings, 'profile')
		self.infoPanelValueCheck(settings)
		
		self._callback()
		
	def loadData(self, data, profileType):
		for setting, value in data.items():
			if profileType == 'preference':
				profile.putPreference(setting, value)
			elif profileType == 'profile':
				profile.putProfileSetting(setting, value)
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
						
		self._callback()
		return settingsToDisplay

	# Communicates w/MaterialSelectorFrame via pubsub subscriptions/messages
	def displayAndLoadMaterialData(self, path):
		# material profile information
		strengthSettings = {}
		qualitySettings = {}
		infoSection = self.getSectionItems(path, 'info')
		self.matName = infoSection['name']
		self.matManufacturer = infoSection['manufacturer']
		materialLoaded = self.matManufacturer + " " + self.matName

		self.materialProfileText.SetText(materialLoaded)
		self.selectedMaterial.SetLabel(materialLoaded)

		profile.putPreference('simpleModeMaterialSupplier', self.matManufacturer)
		profile.putPreference('simpleModeMaterialName', self.matName)
		profile.putPreference('simpleModeMaterial', materialLoaded)
		
		# profile setting information update + info panel update
		profileSectionData = self.getSectionItems(path, 'profile')
		
		# Strength key-value pairs
		for button, info in self.strengthOptions.items():
			if button.GetValue():
				for name, path in info.items():
					strengthSettings = self.getSectionItems(path, 'profile')
				profileSectionData.update(strengthSettings)
				
		# Quality key-value pairs 
		for button, info in self.qualityOptions.items():
			if button.GetValue():
				for name, path in info.items():
					qualitySettings = self.getSectionItems(path, 'profile')
				profileSectionData.update(qualitySettings)
				
		# Make sure that the quality and strength items override the material values
		self.loadData(profileSectionData, profile)
		self.infoPanelValueCheck(profileSectionData)
		
		
		self._callback()
		# profile.putPreference(file_basename)
		
	def infoPanelValueCheck(self, data):
		degree_sign= u'\N{DEGREE SIGN}'
		temperatureUnit = degree_sign + "C" 
		infoPanelSettingsList = {"layer_height": "mm", "print_temperature": temperatureUnit, "print_bed_temperature": temperatureUnit, "wall_thickness": "mm", "fill_density":"%"}
		if profile.getMachineSetting('has_heated_bed') == "False": 
			del infoPanelSettingsList['print_bed_temperature']
		for setting, unit in infoPanelSettingsList.items():
			for name, value in data.items():
				if name == setting:
					self.infoPanelSettingsList[name].SetLabel(str(value) + unit)
							
	def getSectionItems(self, path, section):
		sectionSettings = {}
		cp = configparser.ConfigParser()
		cp.read(path)
		if cp.has_section(section):
			for setting, value in cp.items(section):
				sectionSettings[setting] = value
			return sectionSettings

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
		frame.Show(True)

	def getSettingOverrides(self):
		self.displayLoadedFileName()
		materialsDirectory = resources.getSimpleModeMaterialsProfiles()
		supportSettings = {'platform_adhesion': None, 'support': None}
		strengthSettings = {}
		qualitySettings = {}
		materialSettings = {}
		supplierToCompare = None
		materialToCompare = None
		
		# Raft/Brim/None
		for name, button in self.platformAdhesionOptions.items():
			if button.GetValue():
				supportSettings["platform_adhesion"] = name
		
		# Support	
		if self.printSupport.GetValue():
			supportSettings['support'] = "Everywhere"
		else: 
			supportSettings['support'] = "None"
		
		# Strength key-value pairs
		for button, info in self.strengthOptions.items():
			if button.GetValue():
				for name, path in info.items():
					strengthSettings = self.getSectionItems(path, 'profile')
		
		# Quality key-value pairs 
		for button, info in self.qualityOptions.items():
			if button.GetValue():
				for name, path in info.items():
					qualitySettings = self.getSectionItems(path, 'profile')
					
		# Materials
		selectedMat = self.selectedMaterial.GetLabel()
		print selectedMat
		
		# Alteration
		
		
		for material in materialsDirectory:
			cp = configparser.ConfigParser()
			cp.read(material)
			if cp.has_section('info'):
				supplierToCompare = cp.get('info', 'manufacturer')
				materialToCompare = cp.get('info', 'name')
				if self.matManufacturer is not None and self.matName is not None:
					if self.matManufacturer.lower() == supplierToCompare.lower() and self.matName.lower() == materialToCompare.lower():
						materialSettings = self.getSectionItems(material, 'profile')
						materialSettings.update(supportSettings)
						materialSettings.update(strengthSettings)
						materialSettings.update(qualitySettings)
		
			# This needs to be revisited if there are multiple extruders involved
			if profile.getMachineSetting('has_heated_bed') is False:
				profile.setAlterationFile('start.gcode',  """;-- START GCODE --
	;Sliced for Type A Machines Series 1
	;Sliced at: {day} {date} {time}
	;Basic settings: Layer height: {layer_height} Walls: {wall_thickness} Fill: {fill_density}
	;Print Speed: {print_speed} Support: {support}
	;Retraction Speed: {retraction_speed} Retraction Distance: {retraction_amount}
	;Print time: {print_time}
	;Filament used: {filament_amount}m {filament_weight}g
	;Filament cost: {filament_cost}
	G21        ;metric values
	G90        ;absolute positioning
	G28     ;move to endstops
	G29		;allows for auto-levelling
	G1 X150 Y5  Z15.0 F{travel_speed} ;center and move the platform down 15mm
	M109 S{print_temperature} ;Heat To temp
	G1 X150 Y5 Z0.3 ;move the platform to purge extrusion
	G92 E0 ;zero the extruded length
	G1 F200 X250 E30 ;extrude 30mm of feed stock
	G92 E0 ;zero the extruded length again
	G1 X150 Y150  Z25 F12000 ;recenter and begin
	G1 F{travel_speed}""")
				profile.setAlterationFile('end.gcode', """;-- END GCODE --
	M104 S0     ;extruder heater off
	G91         ;relative positioning
	G1 E-1 F300   ;retract the filament a bit before lifting the nozzle, to release some of the pressure
	G1 Z+0.5 E-5 X-20 Y-20 F9000 ;move Z up a bit and retract filament even more
	G28 X0 Y0     ;move X/Y to min endstops, so the head is out of the way
	M84           ;steppers off
	G90           ;absolute positioning""")	

		return materialSettings
		
	def updateProfileToControls(self):
		pass
		
class MaterialSelectorFrame(wx.Frame):
	def __init__(self):
		wx.Frame.__init__(self, None, wx.ID_ANY, "Materials Selection", size=(550,300), style=wx.DEFAULT_FRAME_STYLE | wx.STAY_ON_TOP)
		materialsDirectory = resources.getSimpleModeMaterialsProfiles()
		self.matProfsDict = self.createMaterialDict(materialsDirectory)
		self.chosenProfilePath = None
		self.selectedBrand = None
		manufctrs = []
		mats = []
		
		for manufacturer, materials in self.matProfsDict.items():
			manufctrs.append(manufacturer)
			for material, path in materials.items():
				mats.append(material)
		
		# pop-up window layout management initialization	
		mainVBox = wx.BoxSizer(wx.VERTICAL)
		listBoxes = wx.BoxSizer(wx.HORIZONTAL)
		closeBtnBox = wx.BoxSizer(wx.HORIZONTAL)
		titles = wx.GridSizer(1, 2, 0, 150)	
		listBoxPanel = wx.Panel(self, -1)
		self.closeButton = wx.Button(listBoxPanel, 9, 'Select', pos=(150, 100))
		self.closeButton.Enable(False)
		

		brandsTitle = wx.StaticText(listBoxPanel, 2, label = "Supplier", pos=wx.DefaultPosition)
		materialsTitle = wx.StaticText(listBoxPanel, 2, label="Name", pos=wx.DefaultPosition)
		brandsTitle.SetFont(wx.Font(20, wx.SWISS, wx.NORMAL, wx.NORMAL))
		materialsTitle.SetFont(wx.Font(20, wx.SWISS, wx.NORMAL, wx.NORMAL))


		# listboxes
		self.manufacturerListbox = wx.ListBox(listBoxPanel, 10, wx.DefaultPosition, size=(100, 100), choices=manufctrs, style=wx.LB_SORT)
		self.matListBox = wx.ListBox(listBoxPanel, 11, wx.DefaultPosition, size=(100, 100), style=wx.LB_SORT)
		self.manufacturerListbox.SetSelection(0)
		matchingMaterials = []
		
		# get matching materials to consequent brand
		index = self.manufacturerListbox.GetSelection()
		self.selectedBrand = self.manufacturerListbox.GetString(index)
		for manufacturer, materials in self.matProfsDict.items():
			if manufacturer == self.selectedBrand:
				for material, path in materials.items():
					matchingMaterials.append(material)
					
		self.matListBox.Set(matchingMaterials)
		
		titles.Add(brandsTitle, 2, wx.LEFT, 20)
		titles.Add(materialsTitle, 2, wx.LEFT, 17)
		listBoxes.Add(self.manufacturerListbox, wx.RIGHT, 15)
		listBoxes.Add(self.matListBox, wx.LEFT, wx.LEFT, 30)
		closeBtnBox.Add(self.closeButton, 9, wx.ALIGN_CENTRE)
		mainVBox.Add(titles, 0, wx.ALIGN_CENTER | wx.TOP, 10)
		mainVBox.Add(listBoxes, 0, wx.ALIGN_CENTRE)
		mainVBox.Add(closeBtnBox, 1, wx.ALIGN_CENTRE | wx.ALL, 10)
		listBoxPanel.SetSizer(mainVBox)
		
		self.manufacturerListbox.Bind(wx.EVT_LISTBOX, self.brandSelected, id=10)
		self.matListBox.Bind(wx.EVT_LISTBOX, self.materialSelected, id=11)
		self.closeButton.Bind(wx.EVT_BUTTON, self.closeWindow, id=9)
		
	
	def closeWindow(self, e):
		if self.chosenProfilePath is not None:
			pub.sendMessage('matProf.update', path=self.chosenProfilePath)
			pub.sendMessage('app.refresh', e=True)
		self.Close()

	# each profile is formated as:	manufacturer__material_base_polymer
	def createMaterialDict(self, files):
		data = []
		matProfsDict = {}
		for file in files:
			cp = configparser.ConfigParser()
			cp.read(file)
			if cp.has_section('info'):
				name = cp.get('info', 'name')
				manufacturer = cp.get('info', 'manufacturer')
				data.append((name, manufacturer, file))
		for name, manufacturer, path in data:
			matProfsDict.setdefault(manufacturer, {})[name] = path
				
		return matProfsDict

	def OnEnable(self, enable):
		self.closeButton.Enable(enable)
	

	def brandSelected(self, event):
		selectedBrand = event.GetString()
		self.selectedBrand = selectedBrand
		newMatsList = []
				
		# finds materials associated with the selected brand and adds them to newMatsList
		for manufacturer, materials, in self.matProfsDict.items():
			if manufacturer == selectedBrand: 
				for material, path in materials.items():
					newMatsList.append(material)

		# when a brand is selected, the materials listbox is updated to reflect materials under
		# the selected brand	
		self.matListBox.Set(newMatsList)
		self.OnEnable(False)
				
	def materialSelected(self, event):
		selectedMaterial = event.GetString()
		self.chosenProfilePath = self.matProfsDict.setdefault(self.selectedBrand, selectedMaterial)[selectedMaterial]
		
		self.OnEnable(True)
