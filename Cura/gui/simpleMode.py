__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import wx

from Cura.util import profile

class simpleModePanel(wx.Panel):
	"Main user interface window for Quickprint mode"
	def __init__(self, parent, callback):
		super(simpleModePanel, self).__init__(parent)
		self._callback = callback

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
		self.printMaterialDiameter = wx.TextCtrl(printMaterialPanel, -1, profile.getProfileSetting('filament_diameter'))
		if profile.getMachineSetting('gcode_flavor') == 'UltiGCode':
			printMaterialPanel.Show(False)
		
		self.printSupport = wx.CheckBox(self, -1, _("Print support structure"))

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
		boxsizer.Add(wx.StaticText(printMaterialPanel, -1, _("Diameter:")))
		boxsizer.Add(self.printMaterialDiameter)
		printMaterialPanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		printMaterialPanel.GetSizer().Add(boxsizer, flag=wx.EXPAND)
		sizer.Add(printMaterialPanel, (1,0), flag=wx.EXPAND)

		sb = wx.StaticBox(self, label=_("Support:"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		boxsizer.Add(self.printSupport)
		sizer.Add(boxsizer, (2,0), flag=wx.EXPAND)

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
		self.printMaterialDiameter.Bind(wx.EVT_TEXT, lambda e: self._callback())

		self.printSupport.Bind(wx.EVT_CHECKBOX, lambda e: self._callback())

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

		nozzle_size = float(get('nozzle_size'))
		if self.printTypeNormal.GetValue():
			put('wall_thickness', nozzle_size * 2.0)
			put('layer_height', '0.15')
			put('fill_density', '10')
			put('print_speed', '100')
			put('cool_min_layer_time', '3')
			put('bottom_layer_speed', '30')
		elif self.printTypeLow.GetValue():
			put('wall_thickness', nozzle_size * 2.0)
			put('layer_height', '0.20')
			put('fill_density', '10')
			put('print_speed', '120')
			put('cool_min_layer_time', '3')
			put('bottom_layer_speed', '45')
		elif self.printTypeHigh.GetValue():
			put('wall_thickness', nozzle_size * 2.0)
			put('layer_height', '0.10')
			put('fill_density', '15')
			put('print_speed', '90')
			put('bottom_layer_speed', '30')
		elif self.printTypeBest.GetValue():
			put('wall_thickness', nozzle_size * 2.0)
			put('layer_height', '0.05')
			put('fill_density', '20')
			put('print_speed', '80')
			put('bottom_layer_speed', '25')
		elif self.printTypeDraft.GetValue():
			put('wall_thickness', nozzle_size * 2.0)
			put('layer_height', '0.25')
			put('fill_density', '8')
			put('print_speed', '135')
			put('bottom_layer_speed', '45')
		elif self.printTypeJoris.GetValue():
			put('wall_thickness', nozzle_size * 1.5)

		put('filament_diameter', self.printMaterialDiameter.GetValue())
		if self.printMaterialPLA.GetValue():
			if machine_type == 'WinG1_Series1':
				put('print_temperature', '195')
			else:
				put('print_temperature', '220')
			put('fan_full_height','0.0')
		if self.printMaterialFlex.GetValue():
			put('print_temperature', '245')
			put('print_speed', '40')
			put('retraction_amount', '1')
			put('fan_full_height','0.0')
		if self.printMaterialPET.GetValue():
			put('print_temperature', '260')
			put('fan_full_height','0.0')
		if self.printMaterialCFPLA.GetValue():
			put('print_temperature', '230')
			put('print_speed', '45')
			put('retraction_amount', '2')
			put('fan_full_height','0.0')
                # if self.printMaterialABS.GetValue():
                #         put('print_bed_temperature', '100')
                #         put('platform_adhesion', 'Brim')
                #         put('filament_flow', '107')
                #         put('print_temperature', '245')
		put('plugin_config', '')

	def updateProfileToControls(self):
		pass