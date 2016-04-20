from __future__ import division
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import wx, wx.lib.stattext, types
from wx.lib.agw import floatspin

from Cura.util import validators
from Cura.util import profile

class configPanelBase(wx.Panel):
	"A base class for configuration dialogs. Handles creation of settings, and popups"
	def __init__(self, parent, changeCallback = None):
		super(configPanelBase, self).__init__(parent)
		
		self.settingControlList = []
		
		#Create the popup window
		self.popup = wx.PopupWindow(self, flags=wx.BORDER_SIMPLE)
		self.popup.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_INFOBK))
		self.popup.setting = None
		self.popup.text = wx.StaticText(self.popup, -1, '')
		self.popup.text.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_INFOTEXT))
		self.popup.sizer = wx.BoxSizer()
		self.popup.sizer.Add(self.popup.text, flag=wx.EXPAND|wx.ALL, border=1)
		self.popup.SetSizer(self.popup.sizer)

		self._callback = changeCallback
	
	def CreateConfigTab(self, nb, name):
		leftConfigPanel, rightConfigPanel, configPanel = self.CreateConfigPanel(nb)
		nb.AddPage(configPanel, name)
		return leftConfigPanel, rightConfigPanel
	
	def CreateConfigPanel(self, parent):
		configPanel = wx.Panel(parent);
		leftConfigPanel = wx.Panel(configPanel)
		rightConfigPanel = wx.Panel(configPanel)

		sizer = wx.GridBagSizer(2, 2)
		leftConfigPanel.SetSizer(sizer)
		sizer = wx.GridBagSizer(2, 2)
		rightConfigPanel.SetSizer(sizer)

		sizer = wx.BoxSizer(wx.HORIZONTAL)
		configPanel.SetSizer(sizer)
		sizer.Add(leftConfigPanel, border=35, flag=wx.RIGHT)
		sizer.Add(rightConfigPanel)
		leftConfigPanel.main = self
		rightConfigPanel.main = self
		return leftConfigPanel, rightConfigPanel, configPanel

	def CreateDynamicConfigTab(self, nb, name):
		configPanel = wx.lib.scrolledpanel.ScrolledPanel(nb)	
		#configPanel = wx.Panel(nb);
		leftConfigPanel = wx.Panel(configPanel)
		rightConfigPanel = wx.Panel(configPanel)

		sizer = wx.GridBagSizer(2, 2)
		leftConfigPanel.SetSizer(sizer)
		#sizer.AddGrowableCol(1)

		sizer = wx.GridBagSizer(2, 2)
		rightConfigPanel.SetSizer(sizer)
		#sizer.AddGrowableCol(1)

		sizer = wx.BoxSizer(wx.HORIZONTAL)
		sizer.Add(leftConfigPanel, proportion=1, border=35, flag=wx.EXPAND)
		sizer.Add(rightConfigPanel, proportion=1, flag=wx.EXPAND)
		configPanel.SetSizer(sizer)

		configPanel.SetAutoLayout(1)
		configPanel.SetupScrolling(scroll_x=False, scroll_y=True)

		leftConfigPanel.main = self
		rightConfigPanel.main = self

		configPanel.leftPanel = leftConfigPanel
		configPanel.rightPanel = rightConfigPanel

		nb.AddPage(configPanel, name)

		return leftConfigPanel, rightConfigPanel, configPanel

	def OnPopupDisplay(self, setting):
		self.popup.setting = setting
		self.UpdatePopup(setting)
		self.popup.Show(True)
		
	def OnPopupHide(self, e):
		self.popup.Show(False)
	
	def UpdatePopup(self, setting):
		if self.popup.setting == setting:
			if setting.validationMsg != '':
				self.popup.text.SetLabel(setting.validationMsg + '\n\n' + setting.setting.getTooltip())
			else:
				self.popup.text.SetLabel(setting.setting.getTooltip())
			self.popup.text.Wrap(350)
			self.popup.Fit()
			x, y = setting.ctrl.ClientToScreenXY(0, 0)
			sx, sy = setting.ctrl.GetSizeTuple()
			#if platform.system() == "Windows":
			#	for some reason, under windows, the popup is relative to the main window... in some cases. (Wierd ass bug)
			#	wx, wy = self.ClientToScreenXY(0, 0)
			#	x -= wx
			#	y -= wy
			self.popup.SetPosition((x, y+sy))
	
	def updateProfileToControls(self):
		"Update the configuration wx controls to show the new configuration settings"
		for setting in self.settingControlList:
			setting.SetValue(setting.setting.getValue())
		self.Update()

	def _validate(self):
		for setting in self.settingControlList:
			setting._validate()
		if self._callback is not None:
			self._callback()

	def getLabelColumnWidth(self, panel):
		maxWidth = 0
		for child in panel.GetChildren():
			if isinstance(child, wx.lib.stattext.GenStaticText):
				maxWidth = max(maxWidth, child.GetSize()[0])
		return maxWidth
	
	def setLabelColumnWidth(self, panel, width):
		for child in panel.GetChildren():
			if isinstance(child, wx.lib.stattext.GenStaticText):
				size = child.GetSize()
				size[0] = width
				child.SetBestSize(size)
	
class TitleRow(object):
	def __init__(self, panel, name):
		"Add a title row to the configuration panel"
		sizer = panel.GetSizer()
		x = sizer.GetRows()
		self.title = wx.StaticText(panel, -1, name.replace('&', '&&'))
		self.title.SetFont(wx.Font(wx.SystemSettings.GetFont(wx.SYS_ANSI_VAR_FONT).GetPointSize(), wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.FONTWEIGHT_BOLD))
		sizer.Add(self.title, (x,0), (1,3), flag=wx.EXPAND|wx.TOP|wx.LEFT, border=10)
		sizer.Add(wx.StaticLine(panel), (x+1,0), (1,4), flag=wx.EXPAND|wx.LEFT,border=10)
		sizer.SetRows(x + 2)

class BlankRow(object):
	def __init__(self, panel, name=None):
		"Add a title row to the configuration panel"
		sizer = panel.GetSizer()
		x = sizer.GetRows()
		self.title = wx.StaticText(panel, -1, " ")
		sizer.Add(self.title, (x,0), (1,3), flag=wx.EXPAND|wx.TOP|wx.LEFT, border=10)
		sizer.SetRows(x + 2)

class TextRow(object):
	def __init__(self, panel, message):
		sizer = panel.GetSizer()
		x = sizer.GetRows()
		self.title = wx.StaticText(panel, -1, message)
		self.title.SetFont(wx.Font(12, wx.SWISS, wx.NORMAL, wx.NORMAL))
		self.title.Wrap(300)
		sizer.Add(self.title, (x,0), (1,3), flag=wx.LEFT, border=10)#, flag=wx.ALIGN_CENTER)
		sizer.SetRows(x + 1)

class StaticTopRow(object):
	def __init__(self, panel):
		sizer = panel.GetSizer()
		x = sizer.GetRows()
#		self.title = wx.StaticText(panel, -1, "")
#		self.title.SetFont(wx.Font(12, wx.SWISS, wx.ITALIC, wx.NORMAL))
		
#		sizer.Add(self.title, (x,0), (1,3), flag=wx.EXPAND|wx.TOP|wx.LEFT, border=10)
#		sizer.SetRows(x + 2)
		
class BoxedText(object):
	def __init__(self, panel, message):
		font = wx.Font(13, wx.SWISS, wx.NORMAL, wx.NORMAL)
		sizer = panel.GetSizer()
		x = sizer.GetRows() + 1
			
		sb = wx.StaticBox(panel)
		staticBoxSizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		message.SetFont(font)
		message.Wrap(330)
		staticBoxSizer.Add(message, flag=wx.ALIGN_LEFT)
		
		
		sizer.Add(staticBoxSizer, (x,0), (1,3), flag=wx.EXPAND)
	#	sizer.SetRows(x + 2)
	
	
class BottomRow(object):
	def __init__(self, panel):
		sizer = panel.GetSizer()
		x = sizer.GetRows()
		self.title = wx.StaticText(panel, -1, "")
		font = wx.Font(14, wx.SWISS, wx.NORMAL, wx.NORMAL)
		self.title.SetFont(font)
		self.title.Wrap(345)
		sizer.Add(self.title, (x,0), (1,3), flag=wx.EXPAND|wx.ALIGN_BOTTOM|wx.LEFT, border=10)
	#	sizer.SetRows(x + 2)
		
class SettingRow(object):
	def __init__(self, panel, configName, valueOverride = None, index = None):
		"Add a setting to the configuration panel"
		sizer = panel.GetSizer()
		x = sizer.GetRows()
		y = 0
		flag = 0
		has_expert_settings = False

		self.setting = profile.settingsDictionary[configName]

		self.settingIndex = index
		self.validationMsg = ''
		self.panel = panel

		#If a setting's label starts with an * , then treat it as a non-usereditable field.
		if self.setting.getLabel()[0]=='*':
			self.label = wx.lib.stattext.GenStaticText(panel, -1, self.setting.getLabel()[1:])
		else:
			self.label = wx.lib.stattext.GenStaticText(panel, -1, self.setting.getLabel())
		self.label.Bind(wx.EVT_ENTER_WINDOW, self.OnMouseEnter)
		self.label.Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseExit)

		#if self.setting.getType() is types.FloatType and False:
		#	digits = 0
		#	while 1 / pow(10, digits) > defaultValue:
		#		digits += 1
		#	self.ctrl = floatspin.FloatSpin(panel, -1, value=float(getSettingFunc(configName)), increment=defaultValue, digits=digits, min_val=0.0)
		#	self.ctrl.Bind(floatspin.EVT_FLOATSPIN, self.OnSettingChange)
		#	flag = wx.EXPAND
		if self.setting.getType() is types.BooleanType:
			self.ctrl = wx.CheckBox(panel, -1, style=wx.ALIGN_RIGHT)
			self.SetValue(self.setting.getValue(self.settingIndex))
			self.ctrl.Bind(wx.EVT_CHECKBOX, self.OnSettingChange)
		elif valueOverride is not None and valueOverride is wx.Colour:
			self.ctrl = wx.ColourPickerCtrl(panel, -1)
			self.SetValue(self.setting.getValue(self.settingIndex))
			self.ctrl.Bind(wx.EVT_COLOURPICKER_CHANGED, self.OnSettingChange)
		elif type(self.setting.getType()) is list or valueOverride is not None:
			value = self.setting.getValue(self.settingIndex)
			choices = self.setting.getType()
			if valueOverride is not None:
				choices = valueOverride
			choices = choices[:]
			self._englishChoices = choices[:]
			if value not in choices and len(choices) > 0:
				value = choices[0]
			for n in xrange(0, len(choices)):
				choices[n] = _(choices[n])
			value = _(value)
			self.ctrl = wx.ComboBox(panel, -1, value, choices=choices, style=wx.CB_DROPDOWN | wx.CB_READONLY)
			self.ctrl.SetBackgroundColour('white')
			self.ctrl.Bind(wx.EVT_COMBOBOX, self.OnSettingChange)
			self.ctrl.Bind(wx.EVT_LEFT_DOWN, self.OnMouseExit)
			flag = wx.EXPAND
		elif str(self.setting.getLabel())[0] == '*':#"Equivalent percentage":
			self.ctrl = wx.TextCtrl(panel, -1, str(self.setting.getValue()), style=wx.TE_READONLY)
			self.ctrl.SetBackgroundColour('#e2e2e2')
			self.ctrl.Bind(wx.EVT_TEXT, self.OnSettingChange)
			flag = wx.EXPAND
		else:
			self.ctrl = wx.TextCtrl(panel, -1, self.setting.getValue(self.settingIndex))
			self.ctrl.Bind(wx.EVT_TEXT, self.OnSettingChange)
			flag = wx.EXPAND

		sizer.Add(self.label, (x,y), flag=wx.ALIGN_CENTER_VERTICAL|wx.LEFT,border=10)
		sizer.Add(self.ctrl, (x,y+1), flag=wx.ALIGN_CENTER_VERTICAL|flag)
		if self.setting.getExpertSubCategory() is not None:
			self._expert_button = wx.Button(panel, -1, '...', style=wx.BU_EXACTFIT)
			self._expert_button.SetFont(wx.Font(wx.SystemSettings.GetFont(wx.SYS_ANSI_VAR_FONT).GetPointSize() * 0.8, wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.FONTWEIGHT_NORMAL))
			self._expert_button.Bind(wx.EVT_BUTTON, self.OnExpertOpen)
			sizer.Add(self._expert_button, (x,y+2), flag=wx.ALIGN_CENTER_VERTICAL)
		sizer.SetRows(x+1)

		self.ctrl.Bind(wx.EVT_ENTER_WINDOW, self.OnMouseEnter)
		self.ctrl.Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseExit)
		if isinstance(self.ctrl, floatspin.FloatSpin):
			self.ctrl.GetTextCtrl().Bind(wx.EVT_ENTER_WINDOW, self.OnMouseEnter)
			self.ctrl.GetTextCtrl().Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseExit)
			self.defaultBGColour = self.ctrl.GetTextCtrl().GetBackgroundColour()
		else:
			self.defaultBGColour = self.ctrl.GetBackgroundColour()
		
		panel.main.settingControlList.append(self)

	def OnMouseEnter(self, e):
		self.panel.main.OnPopupDisplay(self)

	def OnMouseExit(self, e):
		self.panel.main.OnPopupHide(self)
		e.Skip()

	def OnSettingChange(self, e):
		self.setting.setValue(self.GetValue(), self.settingIndex)
		self.panel.main._validate()

	def OnExpertOpen(self, e):
		from Cura.gui import expertConfig

		expert_sub_category = self.setting.getExpertSubCategory()
		if type(expert_sub_category) is list:
			expert_sub_category = expert_sub_category[self.ctrl.GetSelection()]
		ecw = expertConfig.expertConfigWindow(self.panel.main._callback, expert_sub_category)
		ecw.Centre()
		ecw.Show()

	def _validate(self):
		if type(self.setting.getExpertSubCategory()) is list:
			self._expert_button.Enable(self.setting.getExpertSubCategory()[self.ctrl.GetSelection()] is not None)
		result, msg = self.setting.validate()

		ctrl = self.ctrl
		if isinstance(ctrl, floatspin.FloatSpin):
			ctrl = ctrl.GetTextCtrl()
		if result == validators.ERROR:
			ctrl.SetBackgroundColour('Red')
		elif result == validators.DISABLED:
			ctrl.SetBackgroundColour('#e2e2e2')
			ctrl.Disable()
		elif result == validators.SUCCESS:
			ctrl.SetBackgroundColour('White')
			ctrl.Enable()
		elif result == validators.WARNING:
			ctrl.SetBackgroundColour('Yellow')
		else:
			ctrl.SetBackgroundColour(self.defaultBGColour)
		ctrl.Refresh()

		self.validationMsg = msg
		self.panel.main.UpdatePopup(self)

	def GetValue(self):
		if isinstance(self.ctrl, wx.ColourPickerCtrl):
			return str(self.ctrl.GetColour().GetAsString(wx.C2S_HTML_SYNTAX))
		elif isinstance(self.ctrl, wx.ComboBox):
			value = unicode(self.ctrl.GetValue())
			for ret in self._englishChoices:
				if _(ret) == value:
					return ret
			return value
		else:
			return str(self.ctrl.GetValue())

	def SetValue(self, value):
		if isinstance(self.ctrl, wx.CheckBox):
			self.ctrl.SetValue(str(value) == "True")
		elif isinstance(self.ctrl, wx.ColourPickerCtrl):
			self.ctrl.SetColour(value)
		elif isinstance(self.ctrl, floatspin.FloatSpin):
			try:
				self.ctrl.SetValue(float(value))
			except ValueError:
				pass
		elif isinstance(self.ctrl, wx.ComboBox):
			self.ctrl.SetValue(_(value))
		else:
			self.ctrl.SetValue(value)
