__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import wx
import os

from Cura.util import profile
from Cura.gui import sceneView
from Cura.util import resources

#Add option for no infill
class simpleModePanel(wx.Panel):
	"Main user interface window for Quickprint mode"
	def __init__(self, parent, callback):
		super(simpleModePanel, self).__init__(parent)
		self.callback = callback
		
		# below are key-value pairs used for simple mode info list
		self.QChoice = 1 
		self.mChoice = 'a'
		self.QNum = -1
		self.mLetter = 'z'
		self.QVList = {}
		self.QVList['fileName'] = 'No File Currently Open'
		self.QVList['fillDensity'] = -1
		self.fillDensityOverride = -1
		
		# Print Quality Type Details Panel
		printQualityDetailsPanel = wx.Panel(self)	
		layerHeightLabel = wx.StaticText(printQualityDetailsPanel, -1, "Layer Height")
		printSpeedLabel = wx.StaticText(printQualityDetailsPanel, -1, "Print Speed")
		tempLabel = wx.StaticText(printQualityDetailsPanel, -1, "Temperature")
		
		# Because dynamic text cannot be passed as a wx.staticText argument, but can be passed through the label argument, label is set to nothing by default.
		# When values are picked through the 'Print Quality Type' panel below, the labels change with respect to the settings of the quality type in question		
		self.layerHeight = wx.StaticText(printQualityDetailsPanel, -1, label= '')
		self.printSpeed = wx.StaticText(printQualityDetailsPanel, -1, label = '')
		self.printTemperature = wx.StaticText(printQualityDetailsPanel, -1, label = '')	
	
		# Displays the file name of the model that is currently loaded in Cura
		currentFilePanel = wx.Panel(self)
		self.currentFileName = wx.StaticText(currentFilePanel, -1, label = 'No File Currently Open')
	
		# Print Quality Type Panel
		printTypePanel = wx.Panel(self)
		self.printTypeHigh = wx.RadioButton(printTypePanel, -1, _("High quality"), style=wx.RB_GROUP)
		self.printTypeBest = wx.RadioButton(printTypePanel, -1, _("Final quality"))
		self.printTypeNormal = wx.RadioButton(printTypePanel, -1, _("Normal quality"))
		self.printTypeLow = wx.RadioButton(printTypePanel, -1, _("Low quality"))
		self.printTypeDraft = wx.RadioButton(printTypePanel, -1, _("Draft quality"))
		self.printTypeJoris = wx.RadioButton(printTypePanel, -1, _("Thin walled cup or vase"))
		self.printTypeJoris.Hide()

# Print Material Panel
		printMaterialPanel = wx.Panel(self)
		self.printMaterialPLA = wx.RadioButton(printMaterialPanel, -1, 'PLA', style=wx.RB_GROUP)
		self.printMaterialFlex = wx.RadioButton(printMaterialPanel, -1, 'Flexible')
		self.printMaterialCFPLA = wx.RadioButton(printMaterialPanel, -1, 'CFPLA')
		self.printMaterialPET = wx.RadioButton(printMaterialPanel, -1, 'PET')
		
		# Infill Override Panel
		infillPanel = wx.Panel(self)
		self.infillPercentage = wx.StaticText(infillPanel, -1, label = '')
		literalInfillLabel = wx.StaticText(infillPanel, -1, " Infill\t\t")
		self.infillReset = wx.BitmapButton(infillPanel, -1, wx.Bitmap(resources.getPathForImage('resetButton.png')))
		self.infillSlider = wx.Slider(infillPanel, value=0, minValue=0, maxValue=100)
		self.infillOverride = False
		
		# Print Support and Adhesion-Type Panel
		self.printSupport = wx.CheckBox(self, -1, _("Print Support Structure"))
		self.printBrim = wx.CheckBox(self, -1, _("Print Brim"))
		self.printRaft = wx.CheckBox(self, -1, _("Print Raft"))
		sizer = wx.GridBagSizer()
		self.SetSizer(sizer)

		# Creates a box panel to display Print Quality Panel objects
		# Also proportions out space for all radio buttons
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

		# Material Box
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
		
		# Support Box
		sb = wx.StaticBox(self, label=_("Support:"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		boxsizer.Add(self.printSupport)
		boxsizer.Add(self.printBrim)
		boxsizer.Add(self.printRaft)
		sizer.Add(boxsizer, (2,0), flag=wx.EXPAND)
		
		# Print Quality Type Details Box
		sb = wx.StaticBox(printQualityDetailsPanel, label=_("Print Quality Details:"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		gs = wx.GridSizer(3,2,2,2)
		gs.Add(layerHeightLabel)
		gs.Add(self.layerHeight)
		gs.Add(printSpeedLabel)
		gs.Add(self.printSpeed)	
		gs.Add(tempLabel)
		gs.Add(self.printTemperature)
		printQualityDetailsPanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		boxsizer.Add(gs, proportion = 0)
		printQualityDetailsPanel.GetSizer().Add(boxsizer)
		sizer.Add(printQualityDetailsPanel, (3,0))
		
		# Infill Box
		sb = wx.StaticBox(infillPanel, label=_("Fill Density:"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		bs1 = wx.BoxSizer(wx.HORIZONTAL)
		bs2 = wx.BoxSizer(wx.HORIZONTAL)
		bs1.Add(self.infillSlider, flag=wx.ALIGN_LEFT | wx.TOP | wx.LEFT, border=5)
		bs1.Add(self.infillReset, flag=wx.ALIGN_RIGHT)
		bs2.Add(literalInfillLabel, flag = wx.ALIGN_LEFT | wx.TOP | wx.LEFT, border = 5)
		bs2.Add(self.infillPercentage, flag = wx.ALIGN_RIGHT)
		boxsizer.Add(bs1, wx.EXPAND)
		boxsizer.Add(bs2, wx.EXPAND)
		infillPanel.SetSizer(boxsizer)
		sizer.Add(infillPanel, (4,0), flag=wx.EXPAND)

		# Current File Loaded Box
		sb = wx.StaticBox(currentFilePanel, label=_("Last File Opened"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		currentFilePanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		boxsizer.Add(self.currentFileName)
		currentFilePanel.GetSizer().Add(boxsizer, flag=wx.EXPAND)
		sizer.Add(currentFilePanel, (5,0), flag=wx.EXPAND)

		# Preset set to normal
		self.printTypeNormal.SetValue(True)
		self.printMaterialPLA.SetValue(True)
		self.printBrim.SetValue(True)
		self.printSupport.SetValue(True)

		self.printTypeBest.Bind(wx.EVT_RADIOBUTTON, lambda e: self.callback())
		self.printTypeHigh.Bind(wx.EVT_RADIOBUTTON, lambda e: self.callback())
		self.printTypeNormal.Bind(wx.EVT_RADIOBUTTON, lambda e: self.callback())
		self.printTypeLow.Bind(wx.EVT_RADIOBUTTON, lambda e: self.callback())
		self.printTypeDraft.Bind(wx.EVT_RADIOBUTTON, lambda e: self.callback())
		#self.printTypeJoris.Bind(wx.EVT_RADIOBUTTON, lambda e: self._callback())

		self.printMaterialPLA.Bind(wx.EVT_RADIOBUTTON, lambda e: self.callback())
		self.printMaterialFlex.Bind(wx.EVT_RADIOBUTTON, lambda e: self.callback())
		self.printMaterialCFPLA.Bind(wx.EVT_RADIOBUTTON, lambda e: self.callback())
		self.printMaterialPET.Bind(wx.EVT_RADIOBUTTON, lambda e: self.callback())

		self.printSupport.Bind(wx.EVT_CHECKBOX, lambda e: self.callback())
		self.printBrim.Bind(wx.EVT_CHECKBOX, lambda e: self.callback())
		self.printSupport.Bind(wx.EVT_CHECKBOX, lambda e: self.callback())
		self.printRaft.Bind(wx.EVT_CHECKBOX, lambda e: self.callback())
		self.infillSlider.Bind(wx.EVT_SCROLL, self.OnSliderScroll)
		self.infillReset.Bind(wx.EVT_BUTTON, lambda e: self.callback())


	def OnSliderScroll(self, e):
		get = profile.getProfileSetting
		put = profile.setTempOverride
		obj = e.GetEventObject()
		self.fillDensityOverride = obj.GetValue()
		self.QVList['fillDensity'] = get('fill_density')
		self.infillPercentage.SetLabel('\t' + get('fill_density') + '%')
		put('fill_density', self.fillDensityOverride)
		self.infillOverride = True
		self.callback()

	# This function pulls filenames from the scene method whenever the user uploads a model
	def displayLoadedFileName(self):
		mainWindow = self.GetParent().GetParent().GetParent()
		sceneView = mainWindow.scene
		filename = str(os.path.basename(sceneView.filename))
		print("Filename within displayLoadedFileName: %s" %filename)
		
		if self.QVList['fileName'] != filename:
			self.QVList['fileName'] = filename
			self.currentFileName.SetLabel(str(self.QVList['fileName']))
		else:
			pass
	
	
	def setupSlice(self):
		put = profile.setTempOverride
		get = profile.getProfileSetting

		for setting in profile.settingsList:
			if not setting.isProfile():
				continue
			profile.setTempOverride(setting.getName(), setting.getDefault())

		machine_type = profile.getMachineSetting('machine_type')

		if self.printSupport.GetValue():
			put('support', _('Everywhere'))
		else:
			put('support', _('None'))
	
		if self.printBrim.GetValue():
			put('platform_adhesion', _("Brim"))
		if self.printRaft.GetValue():
			put('platform_adhesion', _("Raft"))
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
			put('print_temperature', '210')
			put('print_speed', '60')
			put('retraction_speed', '60')
			put('retraction_amount', '1.8')
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
		self.displayLoadedFileName()


	def qualityValues(self):
		put = profile.setTempOverride
		get = profile.getProfileSetting
		filePath = profile.getPreference('lastFile')
		self.fileName = str(os.path.basename(filePath))
		self.QVList['layerHeight'] = get('layer_height')
		self.QVList['printSpeed'] = get('print_speed')	
		self.QVList['printTemperature'] = get('print_temperature')
		self.QVList['fillDensity'] = get('fill_density')


	def materialValues(self):
		put = profile.setTempOverride
		get = profile.getProfileSetting
		degree_sign= u'\N{DEGREE SIGN}'

		if self.mLetter != self.mChoice:
			self.mLetter = self.mChoice
			if self.QVList['printTemperature'] != get('print_temperature'):
				self.QVList['printTemperature'] = get('print_temperature')
			if self.QVList['printSpeed'] != get('print_speed'):
				self.QVList['printSpeed'] = get('print_speed')
		if self.infillOverride == False:		
			if self.QVList['fillDensity'] != get('fill_density'):
				self.QVList['fillDensity'] = get('fill_density')
		if self.infillOverride == True:
			self.QVList['fillDensity'] = self.fillDensityOverride
			put('fill_density', self.QVList['fillDensity'])
			self.infillOverride = False
		else: 
			self.infillPercentage.SetLabel('\t' + get('fill_density') + '%')
			self.infillSlider.SetValue(int(get('fill_density')))


		self.layerHeight.SetLabel("\t" + str(self.QVList['layerHeight']) + " mm")
		self.printSpeed.SetLabel(str("\t" + self.QVList['printSpeed']) + " mm/s")
		self.printTemperature.SetLabel("\t" + str(self.QVList['printTemperature']) +  degree_sign + "C")



	def updateProfileToControls(self):
		pass
