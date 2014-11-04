__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import wx
import os

from Cura.util import profile
from Cura.gui import sceneView


class simpleModePanel(wx.Panel):
	"Main user interface window for Quickprint mode"
	def __init__(self, parent, callback):
		super(simpleModePanel, self).__init__(parent)
		self._callback = callback
		

		# below are key-value pairs used for simple mode info list
		self.QChoice = 1 
		self.mChoice = 'a'
		self.QNum = -1
		self.mLetter = 'z'
		self.QVList = {}
		self.fileNameCallBack = 0

		printQualityPanel = wx.Panel(self)	
		self.layerHeight = wx.StaticText(printQualityPanel, -1, label= '')
		self.printSpeed = wx.StaticText(printQualityPanel, -1, label = '')
		self.printTemperature = wx.StaticText(printQualityPanel, -1, label = '')	
		self.fillDensity = wx.StaticText(printQualityPanel, -1, label = '', style=wx.ALIGN_RIGHT) 
	
		currentFilePanel = wx.Panel(self)
		self.currentFileName = wx.StaticText(currentFilePanel, -1, label = '')

		#toolsMenu = wx.Menu()
		#i = toolsMenu.Append(-1, 'Switch to Normal mode...')
		#self.Bind(wx.EVT_MENU, self.OnNormalSwitch, i)
		#self.menubar.Insert(1, toolsMenu, 'Normal mode')

		printTypePanel = wx.Panel(self)
		self.printTypeHigh = wx.RadioButton(printTypePanel, -1, _("High quality"), style=wx.RB_GROUP)
		self.printTypeBest = wx.RadioButton(printTypePanel, -1, _("Final quality"))
		self.printTypeNormal = wx.RadioButton(printTypePanel, -1, _("Normal quality"))
		self.printTypeLow = wx.RadioButton(printTypePanel, -1, _("Low quality"))
		self.printTypeDraft = wx.RadioButton(printTypePanel, -1, _("Draft quality"))
		self.printTypeJoris = wx.RadioButton(printTypePanel, -1, _("Thin walled cup or vase"))
		self.printTypeJoris.Hide()

		printMaterialPanel = wx.Panel(self)
		self.printMaterialPLA = wx.RadioButton(printMaterialPanel, -1, 'PLA', style=wx.RB_GROUP)
		self.printMaterialFlex = wx.RadioButton(printMaterialPanel, -1, 'FlexiblePLA')
		self.printMaterialCFPLA = wx.RadioButton(printMaterialPanel, -1, 'CFPLA')
		self.printMaterialPET = wx.RadioButton(printMaterialPanel, -1, 'PET')
		#self.printMaterialABS = wx.RadioButton(printMaterialPanel, -1, 'ABS')
		#self.printMaterialDiameter = wx.TextCtrl(printMaterialPanel, -1, profile.getProfileSetting('filament_diameter'))
		if profile.getMachineSetting('gcode_flavor') == 'UltiGCode':
			printMaterialPanel.Show(False)
		
		self.printSupport = wx.CheckBox(self, -1, _("Print support structure"))
		self.printBrim = wx.CheckBox(self, -1, _("Print Brim"))

		sizer = wx.GridBagSizer()
		self.SetSizer(sizer)

		sb = wx.StaticBox(printTypePanel, label=_("Print Quality:"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		boxsizer.Add(self.printTypeBest)
		boxsizer.Add(self.printTypeHigh)
		boxsizer.Add(self.printTypeNormal)
		boxsizer.Add(self.printTypeLow)
		boxsizer.Add(self.printTypeDraft)
		boxsizer.Add(self.printTypeJoris, border=5, flag=wx.TOP)
		printTypePanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		printTypePanel.GetSizer().Add(boxsizer, flag=wx.EXPAND)
		sizer.Add(printTypePanel, (0,0), flag=wx.EXPAND)

		sb = wx.StaticBox(printMaterialPanel, label=_("Material:"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		boxsizer.Add(self.printMaterialPLA)
		boxsizer.Add(self.printMaterialFlex)
		boxsizer.Add(self.printMaterialCFPLA)
		boxsizer.Add(self.printMaterialPET)
                #boxsizer.Add(self.printMaterialABS)
		#boxsizer.Add(wx.StaticText(printMaterialPanel, -1, _("Diameter:")))
		#boxsizer.Add(self.printMaterialDiameter)
		printMaterialPanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		printMaterialPanel.GetSizer().Add(boxsizer, flag=wx.EXPAND)
		sizer.Add(printMaterialPanel, (1,0), flag=wx.EXPAND)

		sb = wx.StaticBox(self, label=_("Support:"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		boxsizer.Add(self.printSupport)
		boxsizer.Add(self.printBrim)
		sizer.Add(boxsizer, (2,0), flag=wx.EXPAND)
		
		"""------Start-Quality-Details-Panel---------"""

		sb = wx.StaticBox(printQualityPanel, label=_("Print Quality Values:"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		gs = wx.GridSizer(4,2,2,0)		
		labelFont = wx.Font(15, wx.SWISS, wx.NORMAL, wx.ITALIC)

		layerHeightLabel = wx.StaticText(printQualityPanel, -1, "Layer Height")
		printSpeedLabel = wx.StaticText(printQualityPanel, -1, "Print Speed")
		tempLabel = wx.StaticText(printQualityPanel, -1, "Temperature")
		fillDensityLabel = wx.StaticText(printQualityPanel, -1, "Fill Density")

		gs.Add(layerHeightLabel)
		gs.Add(self.layerHeight)
		gs.Add(printSpeedLabel)
		gs.Add(self.printSpeed)	
		gs.Add(tempLabel)
		gs.Add(self.printTemperature)
		gs.Add(fillDensityLabel)
		gs.Add(self.fillDensity)
		
		printQualityPanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		boxsizer.Add(gs, proportion = 0)
		printQualityPanel.GetSizer().Add(boxsizer)
		sizer.Add(printQualityPanel, (3,0))

		"""------End-Quality-Details-Panel---------"""

		sb = wx.StaticBox(currentFilePanel, label=_("Last File Opened"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		currentFilePanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		boxsizer.Add(self.currentFileName)
		currentFilePanel.GetSizer().Add(boxsizer, flag=wx.EXPAND)
		sizer.Add(currentFilePanel, (4,0), flag=wx.EXPAND)

		self.printTypeNormal.SetValue(True)
		self.printMaterialPLA.SetValue(True)

		self.printTypeBest.Bind(wx.EVT_RADIOBUTTON, lambda e: self._callback())
		self.printTypeHigh.Bind(wx.EVT_RADIOBUTTON, lambda e: self._callback())
		self.printTypeNormal.Bind(wx.EVT_RADIOBUTTON, lambda e: self._callback())
		self.printTypeLow.Bind(wx.EVT_RADIOBUTTON, lambda e: self._callback())
		self.printTypeDraft.Bind(wx.EVT_RADIOBUTTON, lambda e: self._callback())
		#self.printTypeJoris.Bind(wx.EVT_RADIOBUTTON, lambda e: self._callback())

		self.printMaterialPLA.Bind(wx.EVT_RADIOBUTTON, lambda e: self._callback())
		self.printMaterialFlex.Bind(wx.EVT_RADIOBUTTON, lambda e: self._callback())
		self.printMaterialCFPLA.Bind(wx.EVT_RADIOBUTTON, lambda e: self._callback())
		self.printMaterialPET.Bind(wx.EVT_RADIOBUTTON, lambda e: self._callback())
		#self.printMaterialABS.Bind(wx.EVT_RADIOBUTTON, lambda e: self._callback())
		#self.printMaterialDiameter.Bind(wx.EVT_TEXT, lambda e: self._callback())

		self.printSupport.Bind(wx.EVT_CHECKBOX, lambda e: self._callback())
		self.printBrim.Bind(wx.EVT_CHECKBOX, lambda e: self._callback())
		

	def setupSlice(self):
		put = profile.setTempOverride
		get = profile.getProfileSetting

		for setting in profile.settingsList:
			if not setting.isProfile():
				continue
			profile.setTempOverride(setting.getName(), setting.getDefault())

		machine_type = profile.getMachineSetting('machine_type')

		if self.printSupport.GetValue():
			put('support', _("Exterior Only"))
		if self.printBrim.GetValue():
			put('platform_adhesion', _("Brim"))
		nozzle_size = float(get('nozzle_size'))
		if self.printTypeBest.GetValue():
			put('wall_thickness', nozzle_size * 2.0)
			put('layer_height', '0.05')
			put('fill_density', '25')
			put('solid_layer_thickness', '0.4')
			put('bottom_thickness', '0.25')
			put('print_speed', '80')
			put('bottom_layer_speed', '25')
			self.QChoice = 1
		elif self.printTypeHigh.GetValue():
			put('wall_thickness', nozzle_size * 2.0)
			put('layer_height', '0.10')
			put('fill_density', '18')
			put('solid_layer_thickness', '0.6')
			put('bottom_thickness', '0.25')
			put('print_speed', '90')
			put('bottom_layer_speed', '30')
			self.QChoice = 2
		elif self.printTypeNormal.GetValue():
			put('wall_thickness', nozzle_size * 2.0)
			put('layer_height', '0.15')
			put('fill_density', '12')
			put('solid_layer_thickness', '0.75')
			put('bottom_thickness', '0.25')
			put('print_speed', '100')
			put('cool_min_layer_time', '3')
			put('bottom_layer_speed', '30')
			self.QChoice = 3
		elif self.printTypeLow.GetValue():
			put('wall_thickness', nozzle_size * 2.0)
			put('layer_height', '0.20')
			put('fill_density', '12')
			put('solid_layer_thickness', '0.8')
			put('bottom_thickness', '0.25')
			put('print_speed', '120')
			put('cool_min_layer_time', '3')
			put('bottom_layer_speed', '45')
			self.QChoice = 4
		elif self.printTypeDraft.GetValue():
			put('wall_thickness', nozzle_size * 2.0)
			put('layer_height', '0.25')
			put('fill_density', '12')
			put('solid_layer_thickness', '1.0')
			put('bottom_thickness', '.25')
			put('print_speed', '135')
			put('bottom_layer_speed', '45')
			self.QChoice = 5
		elif self.printTypeJoris.GetValue():
			put('wall_thickness', nozzle_size * 1.5)
		self.qualityValues()

		#put('filament_diameter', self.printMaterialDiameter.GetValue())
		if self.printMaterialPLA.GetValue():
			if machine_type == 'WinG1_2014Series1':
				put('print_temperature', '195')
			else:
				put('print_temperature', '220')
			put('fan_full_height','0.0')
			self.mChoice = 'a'
		if self.printMaterialFlex.GetValue():
			put('print_temperature', '245')
			put('print_speed', '40')
			put('retraction_amount', '1')
			put('fan_full_height','0.0')
			self.mChoice = 'b'
		if self.printMaterialPET.GetValue():
			put('print_temperature', '260')
			put('fan_full_height','0.0')
			self.mChoice = 'c'
		if self.printMaterialCFPLA.GetValue():
			put('print_temperature', '230')
			put('print_speed', '45')
			put('retraction_amount', '2')
			put('fan_full_height','0.0')
			self.mChoice = 'd'
                # if self.printMaterialABS.GetValue():
                #         put('print_bed_temperature', '100')
                #         put('platform_adhesion', 'Brim')
                #         put('filament_flow', '107')
                #         put('print_temperature', '245')
		put('plugin_config', '')
		self.materialValues()
		print self.mChoice
		
		
	def qualityValues(self):
		put = profile.setTempOverride
		get = profile.getProfileSetting
		filePath = profile.getPreference('lastFile')
		self.fileName = str(os.path.basename(filePath))

		#printQualityPanel = wx.Panel(self)
		self.QVList['layerHeight'] = get('layer_height')
		self.QVList['printSpeed'] = get('print_speed')	
		self.QVList['printTemperature'] = get('print_temperature')
		self.QVList['fillDensity'] = get('fill_density')

		if self.fileNameCallBack == 0:
			self.QVList['fileName'] = "No file currently open"
		else: 
			self.QVList['fileName'] = str(self.fileName)
		self.QNum = self.QChoice

	
	def materialValues(self):
		put = profile.setTempOverride
		get = profile.getProfileSetting
		filePath = profile.getPreference('lastFile')
		fileName = str(os.path.basename(filePath))

		degree_sign= u'\N{DEGREE SIGN}'
		
		if self.mLetter != self.mChoice:
			if self.QVList['printTemperature'] != get('print_temperature'):
				self.QVList['printTemperature'] = get('print_temperature')
			if self.QVList['printSpeed'] != get('print_speed'):
				self.QVList['printSpeed'] = get('print_speed')
			self.mLetter = self.mChoice

		if self.fileNameCallBack != 0:
			if self.QVList['fileName'] != fileName:
				self.fileName = os.path.basename(fileName)
				self.QVList['fileName'] = self.fileName
		
		self.layerHeight.SetLabel("\t" + str(self.QVList['layerHeight']) + " mm")
		self.printSpeed.SetLabel(str("\t" + self.QVList['printSpeed']) + " mm/s")
		self.printTemperature.SetLabel("\t" + str(self.QVList['printTemperature']) +  degree_sign + "C")
		self.fillDensity.SetLabel("\t" + str(self.QVList['fillDensity']) + "%")
		self.currentFileName.SetLabel(str(self.QVList['fileName']))

		self.fileNameCallBack += 1
	def updateProfileToControls(self):
		pass
