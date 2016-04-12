__copyright__ = "Copyright (C) 2013 David Braam and Cat Casuat (Cura Type A Machines) - Released under terms of the AGPLv3 License"

import os
import webbrowser
from wx.lib.pubsub import pub
import wx.lib.agw.hyperlink as hl
import threading
import time
import math
import wx
import re
import wx.wizard
import ConfigParser as configparser
try:
    from io import BytesIO
except ImportError:
    from StringIO import StringIO as BytesIO

from Cura.gui import firmwareInstall
from Cura.gui import printWindow
from Cura.gui import sceneView
from Cura.util import machineCom
from Cura.util import profile
from Cura.util import gcodeGenerator
from Cura.util import resources
from Cura.util import printerConnect

class InfoBox(wx.Panel):
	def __init__(self, parent):
		super(InfoBox, self).__init__(parent)
		self.SetBackgroundColour('#FFFF80')

		self.sizer = wx.GridBagSizer(5, 5)
		self.SetSizer(self.sizer)

		self.attentionBitmap = wx.Bitmap(resources.getPathForImage('attention.png'))
		self.errorBitmap = wx.Bitmap(resources.getPathForImage('error.png'))
		self.readyBitmap = wx.Bitmap(resources.getPathForImage('ready.png'))
		self.busyBitmap = [
			wx.Bitmap(resources.getPathForImage('busy-0.png')),
			wx.Bitmap(resources.getPathForImage('busy-1.png')),
			wx.Bitmap(resources.getPathForImage('busy-2.png')),
			wx.Bitmap(resources.getPathForImage('busy-3.png'))
		]

		self.bitmap = wx.StaticBitmap(self, -1, wx.EmptyBitmapRGBA(24, 24, red=255, green=255, blue=255, alpha=1))
		self.text = wx.StaticText(self, -1, '')
		self.extraInfoButton = wx.Button(self, -1, 'i', style=wx.BU_EXACTFIT)
		self.sizer.Add(self.bitmap, pos=(0, 0), flag=wx.ALL, border=5)
		self.sizer.Add(self.text, pos=(0, 1), flag=wx.TOP | wx.BOTTOM | wx.ALIGN_CENTER_VERTICAL, border=5)
		self.sizer.Add(self.extraInfoButton, pos=(0,2), flag=wx.ALL|wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)
		self.sizer.AddGrowableCol(1)

		self.extraInfoButton.Show(False)

		self.extraInfoUrl = ''
		self.busyState = None
		self.timer = wx.Timer(self)
		self.Bind(wx.EVT_TIMER, self.doBusyUpdate, self.timer)
		self.Bind(wx.EVT_BUTTON, self.doExtraInfo, self.extraInfoButton)
		self.timer.Start(100)

	def SetInfo(self, info):
		self.SetBackgroundColour('#FFFF80')
		self.text.SetLabel(info)
		self.extraInfoButton.Show(False)
		self.Refresh()

	def SetError(self, info, extraInfoUrl):
		self.extraInfoUrl = extraInfoUrl
		self.SetBackgroundColour('#FF8080')
		self.text.SetLabel(info)
		self.extraInfoButton.Show(True)
		self.Layout()
		self.SetErrorIndicator()
		self.Refresh()

	def SetAttention(self, info):
		self.SetBackgroundColour('#FFFF80')
		self.text.SetLabel(info)
		self.extraInfoButton.Show(False)
		self.SetAttentionIndicator()
		self.Layout()
		self.Refresh()

	def SetBusy(self, info):
		self.SetInfo(info)
		self.SetBusyIndicator()

	def SetBusyIndicator(self):
		self.busyState = 0
		self.bitmap.SetBitmap(self.busyBitmap[self.busyState])

	def doExtraInfo(self, e):
		webbrowser.open(self.extraInfoUrl)

	def doBusyUpdate(self, e):
		if self.busyState is None:
			return
		self.busyState += 1
		if self.busyState >= len(self.busyBitmap):
			self.busyState = 0
		self.bitmap.SetBitmap(self.busyBitmap[self.busyState])

	def SetReadyIndicator(self):
		self.busyState = None
		self.bitmap.SetBitmap(self.readyBitmap)

	def SetErrorIndicator(self):
		self.busyState = None
		self.bitmap.SetBitmap(self.errorBitmap)

	def SetAttentionIndicator(self):
		self.busyState = None
		self.bitmap.SetBitmap(self.attentionBitmap)


class InfoPage(wx.wizard.WizardPageSimple):
	def __init__(self, parent, title):
		wx.wizard.WizardPageSimple.__init__(self, parent)

		sizer = wx.GridBagSizer(5, 5)
		self.sizer = sizer
		self.SetSizer(sizer)
		self.rowNr = 1
		self.sizer.AddGrowableCol(0)
		
	def AddLogo(self):
		curaTAMLogo = resources.getPathForImage('TAMLogoAndText.png')
		self.AddImage(curaTAMLogo)
		self.AddTextTagLine('v1.4.1')

	def AddHyperlink(self, text, url):
		hyper1 = hl.HyperLinkCtrl(self, -1, text, URL=url)
		font = wx.Font(pointSize=11, family = wx.DEFAULT,
               style = wx.NORMAL, weight = wx.LIGHT)
		hyper1.SetFont(font)
		self.GetSizer().Add(hyper1, pos=(self.rowNr,0), span=(1, 2), flag=wx.ALIGN_CENTER)
		self.rowNr += 1
		return hyper1

	def GuidedTourLogo(self):
		curaTAMLogo = resources.getPathForImage('TAMLogoAndText.png')
		self.AddImage(curaTAMLogo)
		self.AddTextTagLine('Guided Tour')
		
	def JustIconLogo(self):
		curaTAMLogo = resources.getPathForImage('TAMLogoAndText.png')
		self.AddImage(curaTAMLogo)
		
	# Left-aligned text
	def AddText(self, info):
		text = wx.StaticText(self, -1, info, style=wx.ALIGN_LEFT)
		font = wx.Font(pointSize=11, family = wx.DEFAULT, style=wx.NORMAL, weight=wx.LIGHT)
		text.SetFont(font)
		text.Wrap(340)
		self.GetSizer().Add(text, pos=(self.rowNr, 0), span=(1, 2), flag=wx.ALIGN_CENTER)
		self.rowNr += 1
		return text
		
	# Center-aligned text
	def AddCenteredText(self, info):
		text = wx.StaticText(self, -1, info, style=wx.ALIGN_CENTER)
		font = wx.Font(pointSize=11, family = wx.DEFAULT, style=wx.NORMAL, weight=wx.LIGHT)
		text.SetFont(font)
		text.Wrap(340)
		self.GetSizer().Add(text, pos=(self.rowNr, 0), span=(1, 2), flag=wx.ALIGN_CENTER)
		self.rowNr += 1
		return text
	
	def AddTextTip(self,info):
		text = wx.StaticText(self, -1, info)
		font = wx.Font(pointSize=11, family = wx.DEFAULT, style=wx.NORMAL, weight=wx.NORMAL)
		text.SetFont(font)
		text.Wrap(340)
		self.GetSizer().Add(text, pos=(self.rowNr,0), span=(1, 2), flag=wx.ALIGN_CENTER)
		self.rowNr += 1
		return text
		
	def AddTextTagLine(self, info):
		text = wx.StaticText(self, -1, info, style=wx.ALIGN_LEFT)
		font = wx.Font(pointSize=11, family = wx.DEFAULT,
               style = wx.NORMAL, weight = wx.LIGHT)
		text.SetFont(font)
		text.Wrap(340)
		self.GetSizer().Add(text, pos=(self.rowNr, 0), span=(1, 2), flag=wx.ALIGN_CENTER | wx.BOTTOM, border=10)
		self.rowNr += 1
		return text
		
	def AddTextDescription(self, info):
		text = wx.StaticText(self, -1, info, style=wx.ALIGN_LEFT)
		font = wx.Font(pointSize=11, family = wx.DEFAULT,
               style = wx.NORMAL, weight = wx.NORMAL)
		text.SetFont(font)
		text.Wrap(300)
		self.GetSizer().Add(text, pos=(self.rowNr, 0), span=(1, 2), flag=wx.LEFT, border=160)
		self.rowNr += 1
		return text
		
	def AddSeries1OptionsDescription(self, info):
		text = wx.StaticText(self, -1, info, style=wx.ALIGN_LEFT)
		font = wx.Font(pointSize=11, family = wx.DEFAULT,
               style = wx.NORMAL, weight = wx.NORMAL)
		text.SetFont(font)
		text.Wrap(200)
		self.GetSizer().Add(text, pos=(self.rowNr, 0), span=(1, 2), flag=wx.LEFT | wx.EXPAND, border=130)
		self.rowNr += 1
		return text

	def AddTextLarge(self, info):
		text = wx.StaticText(self, -1, info, style=wx.ALIGN_CENTER)
		font = wx.Font(pointSize=11, family = wx.DEFAULT,
               style = wx.NORMAL, weight = wx.LIGHT)
		text.SetFont(font)
		text.Wrap(400)
		self.GetSizer().Add(text, pos=(self.rowNr, 0), span=(1, 2), flag=wx.ALIGN_CENTER | wx.BOTTOM, border=7)
		self.rowNr += 1
		return text

	def AddTextTitle(self, info):
		text = wx.StaticText(self, -1, info, style=wx.ALIGN_RIGHT)
		font = wx.Font(pointSize=13, family = wx.DEFAULT, style = wx.NORMAL, weight = wx.NORMAL)
		text.SetFont(font)
		text.Wrap(340)
		self.GetSizer().Add(text, pos=(self.rowNr, 0), span=(1, 2), flag=wx.ALIGN_CENTER | wx.BOTTOM, border=7)
		self.rowNr += 1
		return text
		
	def AddErrorText(self, info, red=False):
		text = wx.StaticText(self, -1, info, style=wx.ALIGN_LEFT)
		font = wx.Font(pointSize=11, family = wx.DEFAULT,
               style = wx.NORMAL, weight = wx.NORMAL)
		text.SetFont(font)
		if red:
			text.SetForegroundColour('Red')
		else:
			text.SetForegroundColour('Blue')
			
		self.GetSizer().Add(text, pos=(self.rowNr, 0), span=(1,2), flag= wx.ALIGN_CENTER | wx.LEFT | wx.EXPAND, border=148)
		self.rowNr += 1
		return text
		
	def AddImage(self, imagePath):
		image = wx.Image(imagePath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
		self.GetSizer().Add(wx.StaticBitmap(self, -1, image), pos=(self.rowNr, 0), span=(1, 2), flag=wx.LEFT| wx.RIGHT | wx.ALIGN_CENTER, border=30)
		self.rowNr += 1
		return image
		
	def AddMachineImage(self, imagePath):
		image = wx.Image(imagePath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
		self.GetSizer().Add(wx.StaticBitmap(self, -1, image), pos=(self.rowNr+3, 1), span=(1, 2), flag=wx.ALIGN_RIGHT)
		return image

	def AddLabelImage(self, imagePath):
		image = wx.Image(imagePath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
		self.GetSizer().Add(wx.StaticBitmap(self, -1, image), pos=(self.rowNr, 0), span=(1, 2), flag=wx.ALIGN_CENTER)
		self.rowNr += 1
		return image

	def AddGif(self, imagePath):
		#Loading gif 
		loadingGif = wx.animate.GIFAnimationCtrl(self, -1, imagePath)
		loadingGif.Play()
		
		self.GetSizer().Add(loadingGif, pos=(self.rowNr, 0), span=(1, 2), flag=wx.ALIGN_CENTER)
		self.rowNr += 1
		return loadingGif

	def AddSeperator(self):
		self.GetSizer().Add(wx.StaticLine(self, -1), pos=(self.rowNr, 0), span=(1, 2), flag=wx.EXPAND | wx.ALL)
		self.rowNr += 1

	def AddHiddenSeperator(self, count):
		if count < 1: 
			count = 1
		for x in range(0, count):
			self.AddText("")

	def AddInfoBox(self):
		infoBox = InfoBox(self)
		self.GetSizer().Add(infoBox, pos=(self.rowNr, 0), span=(1, 2), flag=wx.LEFT | wx.RIGHT | wx.EXPAND)
		self.rowNr += 1
		return infoBox

	def AddRadioButton(self, label, style=0):
		radio = wx.RadioButton(self, -1, label, style=wx.ALIGN_LEFT)
		font = wx.Font(pointSize=11, family = wx.DEFAULT, style = wx.NORMAL | wx.LEFT, weight=wx.NORMAL)
		radio.SetFont(font)
		self.GetSizer().Add(radio, pos=(self.rowNr, 0), span=(1, 2), flag=wx.LEFT | wx.ALIGN_LEFT, border=130)
		self.rowNr += 1
		return radio
		
	def AddCheckbox(self, label, checked=False):
		check = wx.CheckBox(self, -1, label)
		font = wx.Font(pointSize=11, family = wx.DEFAULT, style = wx.NORMAL, weight = wx.NORMAL)
		check.SetFont(font)
		check.SetValue(checked)
		self.GetSizer().Add(check, pos=(self.rowNr, 0), span=(1, 2), flag=wx.ALIGN_CENTER)
		self.rowNr += 1
		return check

	def AddMachineOptionCheckbox(self, label, checked=False):
		check = wx.CheckBox(self, -1, label)
		font = wx.Font(pointSize=11, family = wx.DEFAULT, style = wx.NORMAL, weight = wx.NORMAL)
		check.SetFont(font)
		check.SetValue(checked)
		self.GetSizer().Add(check, pos=(self.rowNr, 0), span=(1, 2), flag=wx.ALIGN_LEFT | wx.LEFT, border=130)
		self.rowNr += 1
		return check

	def AddButton(self, label):
		button = wx.Button(self, -1, str(label))
		font = wx.Font(pointSize=11, family = wx.DEFAULT, style = wx.NORMAL, weight = wx.NORMAL)
		button.SetFont(font)
		self.GetSizer().Add(button, pos=(self.rowNr, 0), span=(1, 2), flag=wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, border = 5)
		self.rowNr += 1
		return button

	def AddDualButton(self, label1, label2):
		button1 = wx.Button(self, -1, label1)
		self.GetSizer().Add(button1, pos=(self.rowNr, 0), flag=wx.RIGHT)
		button2 = wx.Button(self, -1, label2)
		self.GetSizer().Add(button2, pos=(self.rowNr, 1))
		self.rowNr += 1
		return button1, button2

	def AddTextCtrl(self, value):
		ret = wx.TextCtrl(self, -1, value, size=(200, 25))
		font = wx.Font(pointSize=11, family = wx.DEFAULT, style=wx.NORMAL, weight = wx.LIGHT)
		ret.SetFont(font)
		self.GetSizer().Add(ret, pos=(self.rowNr, 0), span=(1, 2), flag=wx.ALIGN_CENTER)
		self.rowNr += 1
		return ret

	def AddLabelTextCtrl(self, info, value):
		text = wx.StaticText(self, -1, info)
		ret = wx.TextCtrl(self, -1, value)
		font = wx.Font(pointSize=11, family = wx.DEFAULT,
		style = wx.NORMAL, weight = wx.LIGHT)
		text.SetFont(font)
		self.GetSizer().Add(text, pos=(self.rowNr, 0), span=(1, 1), flag=wx.ALIGN_RIGHT | wx.LEFT, border=75)
		self.GetSizer().Add(ret, pos=(self.rowNr, 1), span=(1, 1), flag=wx.CENTER)
		self.rowNr += 1
		return ret

	def AddTextCtrlButton(self, value, buttonText):
		text = wx.TextCtrl(self, -1, value)
		button = wx.Button(self, -1, buttonText)
		self.GetSizer().Add(text, pos=(self.rowNr, 0), span=(1, 1), flag=wx.LEFT)
		self.GetSizer().Add(button, pos=(self.rowNr, 1), span=(1, 1), flag=wx.LEFT)
		self.rowNr += 1
		return text, button

	def AddBitmap(self, bitmap):
		bitmap = wx.StaticBitmap(self, -1, bitmap)
		self.GetSizer().Add(bitmap, pos=(self.rowNr, 0), span=(1, 2), flag=wx.LEFT | wx.RIGHT)
		self.rowNr += 1
		return bitmap
		

	def AddCheckmark(self, label, bitmap):
		check = wx.StaticBitmap(self, -1, bitmap)
		text = wx.StaticText(self, -1, label)
		self.GetSizer().Add(text, pos=(self.rowNr, 0), span=(1, 1), flag=wx.LEFT | wx.RIGHT)
		self.GetSizer().Add(check, pos=(self.rowNr, 1), span=(1, 1), flag=wx.ALL)
		self.rowNr += 1
		return check

	def AddCombo(self, options):
		combo = wx.ComboBox(self, -1, options[0], choices=options, style=wx.CB_DROPDOWN|wx.CB_READONLY)
		self.GetSizer().Add(combo, pos=(self.rowNr, 1), span=(1, 0), flag=wx.LEFT)
		self.rowNr += 1
		return combo

	def AllowNext(self):
		return True

	def AllowBack(self):
		return True

	def StoreData(self):
		pass


class FirstInfoPage(InfoPage):
	def __init__(self, parent, addNew):
		if addNew:
			super(FirstInfoPage, self).__init__(parent, _("Printer Selection"))
			
		else:
			super(FirstInfoPage, self).__init__(parent, _("Welcome"))
			
		self.AddLogo()
		self.AddHiddenSeperator(5)
		self.AddTextLarge("Select 'Next' to begin configuration.")		

	def AllowBack(self):
		return False

	def StoreData(self):
		pass


class MachineSelectPage(InfoPage):
	def __init__(self, parent):
		super(MachineSelectPage, self).__init__(parent, _("Select your machine"))
		self.AddLogo()
		self.AddHiddenSeperator(1)
		self.AddTextTitle('Select Printer')
		self.AddHiddenSeperator(1)
		self.Series1_Pro_Radio = self.AddRadioButton("Series 1 Pro", style=wx.RB_SINGLE)
		self.Series1_Pro_Radio.SetValue(True)
		self.AddTextDescription(_("#10000-99999"))
		self.AddHiddenSeperator(1)
		self.Series1_Radio = self.AddRadioButton("Series 1")
		self.Series1_Radio.Bind(wx.EVT_RADIOBUTTON, self.OnSeries1)
		self.AddTextDescription(_("#1000-9999"))
		self.AddHiddenSeperator(1)
		self.Series1_Radio.Bind(wx.EVT_RADIOBUTTON, self.OnSeries1)
		self.Series1_Pro_Radio.Bind(wx.EVT_RADIOBUTTON, self.OnSeries1Pro)

	def OnSeries1(self, e):
		wx.wizard.WizardPageSimple.Chain(self, self.GetParent().TAM_select_options)
	
	def OnSeries1Pro(self, e):
		profile.putMachineSetting('has_print_bed', "True")
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
	M140 S{print_bed_temperature} ;Prep Heat Bed
	M109 S{print_temperature} ;Heat To temp
	M190 S{print_bed_temperature} ;Heat Bed to temp
	G1 X150 Y5 Z0.3 ;move the platform to purge extrusion
	G92 E0 ;zero the extruded length
	G1 F200 X250 E30 ;extrude 30mm of feed stock
	G92 E0 ;zero the extruded length again
	G1 X150 Y150  Z25 F12000 ;recenter and begin
	G1 F{travel_speed}""")
		profile.setAlterationFile('end.gcode', """;-- END GCODE --
	M104 S0     ;extruder heater off
	G91         ;relative positioning
	M109 S0			;heated bed off
	G1 E-1 F300   ;retract the filament a bit before lifting the nozzle, to release some of the pressure
	G1 Z+0.5 E-5 X-20 Y-20 F9000 ;move Z up a bit and retract filament even more
	G28 X0 Y0     ;move X/Y to min endstops, so the head is out of the way
	M84           ;steppers off
	G90           ;absolute positioning""")
		wx.wizard.WizardPageSimple.Chain(self, self.GetParent().tamReadyPage)
		
	def StoreData(self):
		allMachineProfiles = resources.getDefaultMachineProfiles()
		machSettingsToStore = {}
		n = None
		
		# loop through list of buttons to find selected
		for machineProfile in allMachineProfiles:
			if self.Series1_Radio.GetValue():
				n = re.search(r'Series1\.ini', machineProfile)
			elif self.Series1_Pro_Radio.GetValue():
				n = re.search(r'Series1Pro', machineProfile)
			
			if n is not None:
				machProfile = machineProfile
				cp = configparser.ConfigParser()
				cp.read(machProfile)
				if cp.has_section('machine'):
					for setting, value in cp.items('machine'):
						machSettingsToStore[setting] = value
		
		# if Series 1 Pro, load the appropriate alteration file
		if self.Series1_Pro_Radio.GetValue():
			alterationDirectoryList = resources.getAlterationFiles()		
			for filename in alterationDirectoryList:
				alterationFileExists = re.search(r'series1_hasBed', filename)
				if alterationFileExists:
					profile.setAlterationFileFromFilePath(filename)
		
		if machSettingsToStore:	
			for setting, value in machSettingsToStore.items():
				profile.putMachineSetting(setting, value)
				

class TAMSelectOptions(InfoPage):
	def __init__(self, parent):
		super(TAMSelectOptions, self).__init__(parent, _("Options and Upgrades"))
		self.AddLogo()
		
		for n in range(0,3):
			self.AddHiddenSeperator(1)
		
		# G2 extruder
		g2ExtruderImage = resources.getPathForImage('g2Extruder.png')
		self.AddImage(g2ExtruderImage)
		self.G2ExtruderCheckBox = self.AddMachineOptionCheckbox("G2 Extruder")
		self.AddSeries1OptionsDescription("If you have an extruder that's not the G2, please uncheck this option.")
		self.G2ExtruderCheckBox.SetValue(True)
		
		# Spacer
		for n in range(0,3):
			self.AddHiddenSeperator(1)

		# Heated bed
		self.HeatedBedCheckBox = self.AddMachineOptionCheckbox("Heated Bed Installed")
		self.AddSeries1OptionsDescription("The heated bed is available\nas an upgrade. Contact sales@typeamachines.com\nfor more information.")
		
		# Spacer
		for n in range(0,2):
			self.AddHiddenSeperator(1)
			
		wx.wizard.WizardPageSimple.Chain(self, self.GetParent().TAM_octoprint_config)
	
	def StoreData(self):
		# Print temp 185 for non-G2
		if not self.G2ExtruderCheckBox.GetValue():
			profile.putProfileSetting('print_temperature', 185)
		# Heated bed item population
		if self.HeatedBedCheckBox.GetValue():
			profile.putMachineSetting("has_heated_bed", "True")
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
	M140 S{print_bed_temperature} ;Prep Heat Bed
	M109 S{print_temperature} ;Heat To temp
	M190 S{print_bed_temperature} ;Heat Bed to temp
	G1 X150 Y5 Z0.3 ;move the platform to purge extrusion
	G92 E0 ;zero the extruded length
	G1 F200 X250 E30 ;extrude 30mm of feed stock
	G92 E0 ;zero the extruded length again
	G1 X150 Y150  Z25 F12000 ;recenter and begin
	G1 F{travel_speed}""")
			profile.setAlterationFile('end.gcode', """;-- END GCODE --
	M104 S0     ;extruder heater off
	G91         ;relative positioning
	M109 S0			;heated bed off
	G1 E-1 F300   ;retract the filament a bit before lifting the nozzle, to release some of the pressure
	G1 Z+0.5 E-5 X-20 Y-20 F9000 ;move Z up a bit and retract filament even more
	G28 X0 Y0     ;move X/Y to min endstops, so the head is out of the way
	M84           ;steppers off
	G90           ;absolute positioning""")
		else:
			print("No heated bed")
			profile.putMachineSetting("has_heated_bed", "False")
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


class TAMReadyPage(InfoPage):
	def __init__(self, parent):
		super(TAMReadyPage, self).__init__(parent, _("Configuration Complete"))
		self.AddLogo()
		typeALogo = resources.getPathForImage('configScreen.png')	
		self.AddImage(typeALogo)
		self.AddHiddenSeperator(1)
		self.AddTextTitle(_("Configuration Complete"))
		self.AddCenteredText(_("Click 'Next' for a guided tour of\nCura Type A features."))
		self.AddHiddenSeperator(1)
		self.skipTut = self.AddCheckbox("Skip Tour")

		self.skipTut.Bind(wx.EVT_CHECKBOX, self.skipTutorial)

	def skipTutorial(self, e):
		if e.IsChecked():
			wx.wizard.WizardPageSimple.Chain(self, self.GetParent().TAM_first_print)
		else:
			wx.wizard.WizardPageSimple.Chain(self, self.GetParent().TAM_select_materials)
					
	def AllowBack(self):
		return False


class TAMOctoPrintInfo(InfoPage):
	def __init__(self, parent):
		super(TAMOctoPrintInfo, self).__init__(parent, _("Octoprint Configuration"))
		
		self.AddLogo()
		self.validSerial = False
		self.validKey = False
		self.saveInfo = False
		self.parent = parent
		self.configurationAttemptedOnce = False
		self.inputCheck = printerConnect.InputValidation()
		self.AddTextTitle("Enable Saving Directly to Series 1")	
		apiTip = resources.getPathForImage('apiTip.png')
		self.AddImage(apiTip)
		self.AddText("Enter the serial number found on the front panel of your Series 1. Then enter the printer's API key, found in the printer's web interface in settings.")
		self.AddHiddenSeperator(1)
		self.serialNumber = self.AddLabelTextCtrl("Serial Number", "")
		self.APIKey = self.AddLabelTextCtrl("API Key", "")
		self.AddHiddenSeperator(1)
		self.configurePrinterButton = self.AddButton("Configure")
		self.skipConfig = self.AddCheckbox("Skip Configuration", checked=False)
		self.errorMessageln1 = self.AddErrorText('\n\n')
		self.configurePrinterButton.Bind(wx.EVT_BUTTON, self.attemptConfiguration)
		self.skipConfig.Bind(wx.EVT_CHECKBOX, self.skipPage)
		self.configurePrinterButton.Disable()
		
		self.serialNumber.Bind(wx.EVT_TEXT, self.checkSerialValidity)
		
	def AllowBack(self):
		return True
		
	def AllowNext(self):
		return False
		
	def skipPage(self, e):
		if self.skipConfig.GetValue():
			self.GetParent().FindWindowById(wx.ID_FORWARD).Enable()
			self.configurePrinterButton.Disable()
			# If the user decides to skip configuration, but has already attempted configuration,
			# delete the printer from the archive
			serial = self.serialNumber.GetValue()
			profile.OctoPrintAPIRemoveSerial(serial)
		else:
			self.GetParent().FindWindowById(wx.ID_FORWARD).Disable()
			self.configurePrinterButton.Enable()
			self.passCheck()
		self.errorMessageln1.SetLabel('')
		

	def checkSerialValidity(self, e):
		id = self.serialNumber.GetValue()
		validityCheck =  self.inputCheck.verifySerial(id)
		
		if validityCheck == 0:
			self.validSerial = True
			self.errorMessageln1.SetLabel("")
			self.configurePrinterButton.Enable()
		else:
			self.errorMessageln1.SetForegroundColour('Red')
			self.errorMessageln1.SetLabel("Serial number consists of 4-6 digits")
			self.configurePrinterButton.Disable()

	def unSavePrinter(self):
		profile.OctoPrintAPIRemoveSerial(self.serialNumber)
	
	# Key check
	def checkKeyValidity(self, e):
		key = self.APIKey.GetValue()
		keyLength = len(key)
		
		validityCheck = self.inputCheck.verifyKey(key)
		
		if validityCheck == 0:
			self.validKey = True
			self.errorMessageln1.SetLabel("")
		else:
			self.validKey = False
	#		self.errorMessageln0.SetLabel("Error")
			self.errorMessageln1.SetForegroundColour('Red')
			self.errorMessageln1.SetLabel("API key consists of 32 characters")

		self.passCheck()

	def passCheck(self):
		if self.validSerial == True and self.validKey == True and not self.skipConfig.GetValue():
			self.saveInfo = True
		else:
			self.saveInfo = False
			
	def attemptConfiguration(self, e):
		key = self.APIKey.GetValue()
		serial = self.serialNumber.GetValue()
		saveInfo = self.saveInfo
		self.configurationAttemptedOnce = True
		self.errorMessageln1.SetForegroundColour('Blue')
		self.errorMessageln1.SetLabel("Configuring...")
		self.configurePrinterButton.Disable()

		thread = printerConnect.ConfirmCredentials(self, True, key, serial, self.errorMessageln1)
		thread.start()
		
	def StoreData(self):
		serial = self.serialNumber.GetValue()
		key = self.APIKey.GetValue()
		
		
		if 	self.skipConfig.GetValue() == True and self.configurationAttemptedOnce == True:
			if profile.configExists() is not None and serial is None and key is not None:
				profile.OctoPrintAPIRemoveSerial(serial)
				print "Config does not exist yet."
		else:
			self.GetParent().FindWindowById(wx.ID_FORWARD).Enable()


class TAMSelectMaterials(InfoPage):
	def __init__(self, parent):
		super(TAMSelectMaterials, self).__init__(parent, _("Material Selection"))
		self.GuidedTourLogo()
		materialProfileImage = resources.getPathForImage('0mp.png')
		self.AddImage(materialProfileImage)
		self.AddTextTitle("Optimized Material Profiles")
		self.AddText("Select from over 40 material profiles from our rapidly growing portfolio of material profiles.\n\nEvery material profile is tested and optimized for the Series 1, eliminating the time and effort necessary to determine optimal settings from scratch.")

class TAMSelectStrength(InfoPage):
	def __init__(self, parent):
		super(TAMSelectStrength, self).__init__(parent, _("Strength Selection"))
		self.GuidedTourLogo()
		typeALogo = resources.getPathForImage('2st.png')
		self.AddImage(typeALogo)
		self.addText()
	
	# General informative text
	def addText(self):
		self.AddTextTitle("Strength")
		self.AddText("The Strength setting specifies Wall Thickness and Fill Density. The High setting will use more filament and result in longer print times, but can produce much stronger objects.")

class TAMSelectQuality(InfoPage):
	def __init__(self, parent):
		super(TAMSelectQuality, self).__init__(parent, _("Quality Selection"))
		
		self.GuidedTourLogo()
		typeALogo = resources.getPathForImage('1qu.png')
		self.AddImage(typeALogo)
		self.addText()
	
	# General informative text
	def addText(self):
		self.AddTextTitle("Quality")
		self.AddText("The Quality setting specifies layer height determining detail. The Final setting determines the smallest layer height, producing the finest detail and longest print times.\n\nThe Draft setting determines the largest layer height resulting in much shorter print times. Draft is often sufficient for most needs.")

class TAMSelectSupport(InfoPage):
	def __init__(self, parent):
		super(TAMSelectSupport, self).__init__(parent, _("Support Selection"))
		self.GuidedTourLogo()
		typeALogo = resources.getPathForImage('3sa.png')
		self.AddImage(typeALogo)
		self.AddTextTitle("Support, Brims, and Rafts")
		self.AddText("Support includes structures added to the print to support overhangs or help with adherence, which are removed after printing is complete.\n\nA brim is a structure printed around the first layer to help prevent the edges of a print from lifting.\n\nA raft is a platform on to which the model is printed to assist with adhesion, especially with delicate prints.\n\nTo preview these structures, click the View Mode icon, then click Layers.")
		
class TAMFirstPrint(InfoPage):
	def __init__(self, parent):
		super(TAMFirstPrint, self).__init__(parent, _("Your First Print"))
		self.JustIconLogo()
		self.AddText("Click 'Finish' and Cura Type A will open and open an example model which you can use to become more familiar with the application.")
		self.AddHiddenSeperator(1)
		saveAndUploadImage = resources.getPathForImage('readyToGoPage.png')
		self.AddImage(saveAndUploadImage)
		gettingStarted = "Getting Started Page"
		self.AddHiddenSeperator(1)
		self.AddText("When you are ready to print, click the 'Save' or 'Upload' icon to save and start printing your 3D models.")
		self.AddCenteredText("For more information, visit our Getting Started page:")
		self.AddHyperlink("typeamachines.com/gettingstarted", "http://www.typeamachines.com/gettingstarted")
		
class NonTAM(InfoPage):
	def __init__(self, parent):
		super(NonTAM, self).__init__(parent, _("Select Machine"))
		self.GuidedTourLogo()
		self.Ultimaker2Radio = self.AddRadioButton("Ultimaker2", style=wx.RB_GROUP)
		self.Ultimaker2Radio.SetValue(True)
		self.Ultimaker2Radio.Bind(wx.EVT_RADIOBUTTON, self.OnUltimaker2Select)
		self.Ultimaker2ExtRadio = self.AddRadioButton("Ultimaker2extended")
		self.Ultimaker2ExtRadio.Bind(wx.EVT_RADIOBUTTON, self.OnUltimaker2Select)
		self.Ultimaker2GoRadio = self.AddRadioButton("Ultimaker2go")
		self.Ultimaker2GoRadio.Bind(wx.EVT_RADIOBUTTON, self.OnUltimaker2Select)
		self.UltimakerRadio = self.AddRadioButton("Ultimaker Original")
		self.UltimakerRadio.Bind(wx.EVT_RADIOBUTTON, self.OnUltimakerSelect)
		self.UltimakerOPRadio = self.AddRadioButton("Ultimaker Original+")
		self.UltimakerOPRadio.Bind(wx.EVT_RADIOBUTTON, self.OnUltimakerOPSelect)
		self.PrintrbotRadio = self.AddRadioButton("Printrbot")
		self.PrintrbotRadio.Bind(wx.EVT_RADIOBUTTON, self.OnPrintrbotSelect)
		self.LulzbotTazRadio = self.AddRadioButton("Lulzbot TAZ")
		self.LulzbotTazRadio.Bind(wx.EVT_RADIOBUTTON, self.OnLulzbotSelect)
		self.LulzbotMiniRadio = self.AddRadioButton("Lulzbot Mini")
		self.LulzbotMiniRadio.Bind(wx.EVT_RADIOBUTTON, self.OnLulzbotSelect)
		self.OtherRadio = self.AddRadioButton(_("Other (Ex: RepRap, MakerBot, Witbox)"))
		self.OtherRadio.Bind(wx.EVT_RADIOBUTTON, self.OnOtherSelect)
		self.AddSeperator()
		self.AddText(_("The collection of anonymous usage information helps with the continued improvement of Cura."))
		self.AddText(_("This does NOT submit your models online nor gathers any privacy related information."))
		self.SubmitUserStats = self.AddCheckbox(_("Submit anonymous usage information:"))
		self.AddText(_("For full details see: http://wiki.ultimaker.com/Cura:stats"))
		self.SubmitUserStats.SetValue(True)
		
	def OnUltimaker2Select(self, e):
		wx.wizard.WizardPageSimple.Chain(self, self.GetParent().ultimaker2ReadyPage)

	def OnUltimakerSelect(self, e):
		wx.wizard.WizardPageSimple.Chain(self, self.GetParent().ultimakerSelectParts)

	def OnUltimakerOPSelect(self, e):
		wx.wizard.WizardPageSimple.Chain(self, self.GetParent().ultimakerFirmwareUpgradePage)

	def OnPrintrbotSelect(self, e):
		wx.wizard.WizardPageSimple.Chain(self, self.GetParent().printrbotSelectType)

	def OnLulzbotSelect(self, e):
		wx.wizard.WizardPageSimple.Chain(self, self.GetParent().lulzbotReadyPage)

	def OnOtherSelect(self, e):
		wx.wizard.WizardPageSimple.Chain(self, self.GetParent().otherMachineSelectPage)

	def AllowNext(self):
		wx.wizard.WizardPageSimple.Chain(self, self.GetParent().ultimaker2ReadyPage)
		return True

	def StoreData(self):
		profile.putProfileSetting('retraction_enable', 'True')
		if self.Ultimaker2Radio.GetValue() or self.Ultimaker2GoRadio.GetValue() or self.Ultimaker2ExtRadio.GetValue():
			if self.Ultimaker2Radio.GetValue():
				profile.putMachineSetting('machine_width', '230')
				profile.putMachineSetting('machine_depth', '225')
				profile.putMachineSetting('machine_height', '205')
				profile.putMachineSetting('machine_name', 'ultimaker2')
				profile.putMachineSetting('machine_type', 'ultimaker2')
				profile.putMachineSetting('has_heated_bed', 'True')
			if self.Ultimaker2GoRadio.GetValue():
				profile.putMachineSetting('machine_width', '120')
				profile.putMachineSetting('machine_depth', '120')
				profile.putMachineSetting('machine_height', '115')
				profile.putMachineSetting('machine_name', 'ultimaker2go')
				profile.putMachineSetting('machine_type', 'ultimaker2go')
				profile.putMachineSetting('has_heated_bed', 'False')
			if self.Ultimaker2ExtRadio.GetValue():
				profile.putMachineSetting('machine_width', '230')
				profile.putMachineSetting('machine_depth', '225')
				profile.putMachineSetting('machine_height', '315')
				profile.putMachineSetting('machine_name', 'ultimaker2extended')
				profile.putMachineSetting('machine_type', 'ultimaker2extended')
				profile.putMachineSetting('has_heated_bed', 'False')
			profile.putMachineSetting('machine_center_is_zero', 'False')
			profile.putMachineSetting('gcode_flavor', 'UltiGCode')
			profile.putMachineSetting('extruder_head_size_min_x', '40.0')
			profile.putMachineSetting('extruder_head_size_min_y', '10.0')
			profile.putMachineSetting('extruder_head_size_max_x', '60.0')
			profile.putMachineSetting('extruder_head_size_max_y', '30.0')
			profile.putMachineSetting('extruder_head_size_height', '48.0')
			profile.putProfileSetting('nozzle_size', '0.4')
			profile.putProfileSetting('fan_full_height', '5.0')
			profile.putMachineSetting('extruder_offset_x1', '18.0')
			profile.putMachineSetting('extruder_offset_y1', '0.0')
		elif self.UltimakerRadio.GetValue():
			profile.putMachineSetting('machine_width', '205')
			profile.putMachineSetting('machine_depth', '205')
			profile.putMachineSetting('machine_height', '200')
			profile.putMachineSetting('machine_name', 'ultimaker original')
			profile.putMachineSetting('machine_type', 'ultimaker')
			profile.putMachineSetting('machine_center_is_zero', 'False')
			profile.putMachineSetting('gcode_flavor', 'RepRap (Marlin/Sprinter)')
			profile.putProfileSetting('nozzle_size', '0.4')
			profile.putMachineSetting('extruder_head_size_min_x', '75.0')
			profile.putMachineSetting('extruder_head_size_min_y', '18.0')
			profile.putMachineSetting('extruder_head_size_max_x', '18.0')
			profile.putMachineSetting('extruder_head_size_max_y', '35.0')
			profile.putMachineSetting('extruder_head_size_height', '55.0')
		elif self.UltimakerOPRadio.GetValue():
			profile.putMachineSetting('machine_width', '205')
			profile.putMachineSetting('machine_depth', '205')
			profile.putMachineSetting('machine_height', '200')
			profile.putMachineSetting('machine_name', 'ultimaker original+')
			profile.putMachineSetting('machine_type', 'ultimaker_plus')
			profile.putMachineSetting('machine_center_is_zero', 'False')
			profile.putMachineSetting('gcode_flavor', 'RepRap (Marlin/Sprinter)')
			profile.putProfileSetting('nozzle_size', '0.4')
			profile.putMachineSetting('extruder_head_size_min_x', '75.0')
			profile.putMachineSetting('extruder_head_size_min_y', '18.0')
			profile.putMachineSetting('extruder_head_size_max_x', '18.0')
			profile.putMachineSetting('extruder_head_size_max_y', '35.0')
			profile.putMachineSetting('extruder_head_size_height', '55.0')
			profile.putMachineSetting('has_heated_bed', 'True')
			profile.putMachineSetting('extruder_amount', '1')
			profile.putProfileSetting('retraction_enable', 'True')
		elif self.LulzbotTazRadio.GetValue() or self.LulzbotMiniRadio.GetValue():
			if self.LulzbotTazRadio.GetValue():
				profile.putMachineSetting('machine_width', '298')
				profile.putMachineSetting('machine_depth', '275')
				profile.putMachineSetting('machine_height', '250')
				profile.putProfileSetting('nozzle_size', '0.35')
				profile.putMachineSetting('machine_name', 'Lulzbot TAZ')
			else:
				profile.putMachineSetting('machine_width', '160')
				profile.putMachineSetting('machine_depth', '160')
				profile.putMachineSetting('machine_height', '160')
				profile.putProfileSetting('nozzle_size', '0.5')
				profile.putMachineSetting('machine_name', 'Lulzbot Mini')
			profile.putMachineSetting('machine_type', 'Aleph Objects')
			profile.putMachineSetting('machine_center_is_zero', 'False')
			profile.putMachineSetting('gcode_flavor', 'RepRap (Marlin/Sprinter)')
			profile.putMachineSetting('has_heated_bed', 'True')
			profile.putMachineSetting('extruder_head_size_min_x', '0.0')
			profile.putMachineSetting('extruder_head_size_min_y', '0.0')
			profile.putMachineSetting('extruder_head_size_max_x', '0.0')
			profile.putMachineSetting('extruder_head_size_max_y', '0.0')
			profile.putMachineSetting('extruder_head_size_height', '0.0')
		else:
			profile.putMachineSetting('machine_width', '305')
			profile.putMachineSetting('machine_depth', '305')
			profile.putMachineSetting('machine_height', '305')
			profile.putMachineSetting('machine_name', 'reprap')
			profile.putMachineSetting('machine_type', 'reprap')
			profile.putMachineSetting('gcode_flavor', 'RepRap (Marlin/Sprinter)')
			profile.putPreference('startMode', 'Normal')
			profile.putProfileSetting('nozzle_size', '0.4')
		profile.checkAndUpdateMachineName()
		profile.putProfileSetting('wall_thickness', float(profile.getProfileSetting('nozzle_size')) * 2)
		if self.SubmitUserStats.GetValue():
			profile.putPreference('submit_slice_information', 'True')
		else:
			profile.putPreference('submit_slice_information', 'False')

class PrintrbotPage(InfoPage):
	def __init__(self, parent):
		self._printer_info = [
			# X, Y, Z, Nozzle Size, Filament Diameter, PrintTemperature, Print Speed, Travel Speed, Retract speed, Retract amount, use bed level sensor
			("Simple Metal", 150, 150, 150, 0.4, 1.75, 208, 40, 70, 30, 1, True),
			("Metal Plus", 250, 250, 250, 0.4, 1.75, 208, 40, 70, 30, 1, True),
			("Simple Makers Kit", 100, 100, 100, 0.4, 1.75, 208, 40, 70, 30, 1, True),
			(":" + _("Older models"),),
			("Original", 130, 130, 130, 0.5, 2.95, 208, 40, 70, 30, 1, False),
			("Simple Maker's Edition v1", 100, 100, 100, 0.4, 1.75, 208, 40, 70, 30, 1, False),
			("Simple Maker's Edition v2 (2013 Printrbot Simple)", 100, 100, 100, 0.4, 1.75, 208, 40, 70, 30, 1, False),
			("Simple Maker's Edition v3 (2014 Printrbot Simple)", 100, 100, 100, 0.4, 1.75, 208, 40, 70, 30, 1, False),
			("Jr v1", 115, 120, 80, 0.4, 1.75, 208, 40, 70, 30, 1, False),
			("Jr v2", 150, 150, 150, 0.4, 1.75, 208, 40, 70, 30, 1, False),
			("LC v1", 150, 150, 150, 0.4, 1.75, 208, 40, 70, 30, 1, False),
			("LC v2", 150, 150, 150, 0.4, 1.75, 208, 40, 70, 30, 1, False),
			("Plus v1", 200, 200, 200, 0.4, 1.75, 208, 40, 70, 30, 1, False),
			("Plus v2", 200, 200, 200, 0.4, 1.75, 208, 40, 70, 30, 1, False),
			("Plus v2.1", 185, 220, 200, 0.4, 1.75, 208, 40, 70, 30, 1, False),
			("Plus v2.2 (Model 1404/140422/140501/140507)", 250, 250, 250, 0.4, 1.75, 208, 40, 70, 30, 1, True),
			("Go v2 Large", 505, 306, 310, 0.4, 1.75, 208, 35, 70, 30, 1, True),
		]

		super(PrintrbotPage, self).__init__(parent, _("Printrbot Selection"))
		self.AddBitmap(wx.Bitmap(resources.getPathForImage('Printrbot_logo.png')))
		self.AddText(_("Select which Printrbot machine you have:"))
		self._items = []
		for printer in self._printer_info:
			if printer[0].startswith(":"):
				self.AddSeperator()
				self.AddText(printer[0][1:])
			else:
				item = self.AddRadioButton(printer[0])
				item.data = printer[1:]
				self._items.append(item)

	def StoreData(self):
		profile.putMachineSetting('machine_name', 'Printrbot ???')
		for item in self._items:
			if item.GetValue():
				data = item.data
				profile.putMachineSetting('machine_name', 'Printrbot ' + item.GetLabel())
				profile.putMachineSetting('machine_width', data[0])
				profile.putMachineSetting('machine_depth', data[1])
				profile.putMachineSetting('machine_height', data[2])
				profile.putProfileSetting('nozzle_size', data[3])
				profile.putProfileSetting('filament_diameter', data[4])
				profile.putProfileSetting('print_temperature', data[5])
				profile.putProfileSetting('print_speed', data[6])
				profile.putProfileSetting('travel_speed', data[7])
				profile.putProfileSetting('retraction_speed', data[8])
				profile.putProfileSetting('retraction_amount', data[9])
				profile.putProfileSetting('wall_thickness', float(profile.getProfileSettingFloat('nozzle_size')) * 2)
				profile.putMachineSetting('has_heated_bed', 'False')
				profile.putMachineSetting('machine_center_is_zero', 'False')
				profile.putMachineSetting('extruder_head_size_min_x', '0')
				profile.putMachineSetting('extruder_head_size_min_y', '0')
				profile.putMachineSetting('extruder_head_size_max_x', '0')
				profile.putMachineSetting('extruder_head_size_max_y', '0')
				profile.putMachineSetting('extruder_head_size_height', '0')
				if data[10]:
					profile.setAlterationFile('start.gcode', """;Sliced at: {day} {date} {time}
;Basic settings: Layer height: {layer_height} Walls: {wall_thickness} Fill: {fill_density}
;Print time: {print_time}
;Filament used: {filament_amount}m {filament_weight}g
;Filament cost: {filament_cost}
;M190 S{print_bed_temperature} ;Uncomment to add your own bed temperature line
;M109 S{print_temperature} ;Uncomment to add your own temperature line
G21        ;metric values
G90        ;absolute positioning
M82        ;set extruder to absolute mode
M107       ;start with the fan off
G28 X0 Y0  ;move X/Y to min endstops
G28 Z0     ;move Z to min endstops
G29        ;Run the auto bed leveling
G1 Z15.0 F{travel_speed} ;move the platform down 15mm
G92 E0                  ;zero the extruded length
G1 F200 E3              ;extrude 3mm of feed stock
G92 E0                  ;zero the extruded length again
G1 F{travel_speed}
;Put printing message on LCD screen
M117 Printing...
""")

class OtherMachineSelectPage(InfoPage):
	def __init__(self, parent):
		super(OtherMachineSelectPage, self).__init__(parent, _("Other machine information"))
		self.AddText(_("The following pre-defined machine profiles are available"))
		self.AddText(_("Note that these profiles are not guaranteed to give good results,\nor work at all. Extra tweaks might be required.\nIf you find issues with the predefined profiles,\nor want an extra profile.\nPlease report it at the github issue tracker."))
		self.options = []
		machines = resources.getDefaultMachineProfiles()
		machines.sort()
		for filename in machines:
			name = os.path.splitext(os.path.basename(filename))[0]
			item = self.AddRadioButton(name)
			item.filename = filename
			item.Bind(wx.EVT_RADIOBUTTON, self.OnProfileSelect)
			self.options.append(item)
		self.AddSeperator()
		item = self.AddRadioButton(_('Custom...'))
		item.SetValue(True)
		item.Bind(wx.EVT_RADIOBUTTON, self.OnOtherSelect)

	def OnProfileSelect(self, e):
		wx.wizard.WizardPageSimple.Chain(self, self.GetParent().otherMachineInfoPage)

	def OnOtherSelect(self, e):
		wx.wizard.WizardPageSimple.Chain(self, self.GetParent().customRepRapInfoPage)

	def StoreData(self):
		for option in self.options:
			if option.GetValue():
				profile.loadProfile(option.filename)
				profile.loadMachineSettings(option.filename)

class OtherMachineInfoPage(InfoPage):
	def __init__(self, parent):
		super(OtherMachineInfoPage, self).__init__(parent, _("Cura Ready!"))
		self.AddText(_("Cura is now ready to be used!"))


class CustomRepRapInfoPage(InfoPage):
	def __init__(self, parent):
		super(CustomRepRapInfoPage, self).__init__(parent, _("Custom RepRap information"))
		self.AddText(_("RepRap machines can be vastly different, so here you can set your own settings."))
		self.AddText(_("Be sure to review the default profile before running it on your machine."))
		self.AddText(_("If you like a default profile for your machine added,\nthen make an issue on github."))
		self.AddSeperator()
		self.AddText(_("You will have to manually install Marlin or Sprinter firmware."))
		self.AddSeperator()
		self.machineName = self.AddLabelTextCtrl(_("Machine name"), "RepRap")
		self.machineWidth = self.AddLabelTextCtrl(_("Machine width X (mm)"), "80")
		self.machineDepth = self.AddLabelTextCtrl(_("Machine depth Y (mm)"), "80")
		self.machineHeight = self.AddLabelTextCtrl(_("Machine height Z (mm)"), "55")
		self.nozzleSize = self.AddLabelTextCtrl(_("Nozzle size (mm)"), "0.5")
		self.heatedBed = self.AddCheckbox(_("Heated bed"))
		self.HomeAtCenter = self.AddCheckbox(_("Bed center is 0,0,0 (RoStock)"))

	def StoreData(self):
		profile.putMachineSetting('machine_name', self.machineName.GetValue())
		profile.putMachineSetting('machine_width', self.machineWidth.GetValue())
		profile.putMachineSetting('machine_depth', self.machineDepth.GetValue())
		profile.putMachineSetting('machine_height', self.machineHeight.GetValue())
		profile.putProfileSetting('nozzle_size', self.nozzleSize.GetValue())
		profile.putProfileSetting('wall_thickness', float(profile.getProfileSettingFloat('nozzle_size')) * 2)
		profile.putMachineSetting('has_heated_bed', str(self.heatedBed.GetValue()))
		profile.putMachineSetting('machine_center_is_zero', str(self.HomeAtCenter.GetValue()))
		profile.putMachineSetting('extruder_head_size_min_x', '0')
		profile.putMachineSetting('extruder_head_size_min_y', '0')
		profile.putMachineSetting('extruder_head_size_max_x', '0')
		profile.putMachineSetting('extruder_head_size_max_y', '0')
		profile.putMachineSetting('extruder_head_size_height', '0')
		profile.checkAndUpdateMachineName()


class UltimakerFirmwareUpgradePage(InfoPage):
	def __init__(self, parent):
		super(UltimakerFirmwareUpgradePage, self).__init__(parent, _("Upgrade Ultimaker Firmware"))
		self.AddText(_("Firmware is the piece of software running directly on your 3D printer.\nThis firmware controls the step motors, regulates the temperature\nand ultimately makes your printer work."))
		self.AddHiddenSeperator(1)
		self.AddText(_("The firmware shipping with new Ultimakers works, but upgrades\nhave been made to make better prints, and make calibration easier."))
		self.AddHiddenSeperator(1)
		self.AddText(_("Cura requires these new features and thus\nyour firmware will most likely need to be upgraded.\nYou will get the chance to do so now."))
		upgradeButton, skipUpgradeButton = self.AddDualButton('Upgrade to Marlin firmware', 'Skip upgrade')
		upgradeButton.Bind(wx.EVT_BUTTON, self.OnUpgradeClick)
		skipUpgradeButton.Bind(wx.EVT_BUTTON, self.OnSkipClick)
		self.AddHiddenSeperator(1)
		if profile.getMachineSetting('machine_type') == 'ultimaker':
			self.AddText(_("Do not upgrade to this firmware if:"))
			self.AddText(_("* You have an older machine based on ATMega1280 (Rev 1 machine)"))
			self.AddText(_("* Build your own heated bed"))
			self.AddText(_("* Have other changes in the firmware"))
#		button = self.AddButton('Goto this page for a custom firmware')
#		button.Bind(wx.EVT_BUTTON, self.OnUrlClick)

	def AllowNext(self):
		return False

	def OnUpgradeClick(self, e):
		if firmwareInstall.InstallFirmware():
			self.GetParent().FindWindowById(wx.ID_FORWARD).Enable()

	def OnSkipClick(self, e):
		self.GetParent().FindWindowById(wx.ID_FORWARD).Enable()
		self.GetParent().ShowPage(self.GetNext())

	def OnUrlClick(self, e):
		webbrowser.open('http://marlinbuilder.robotfuzz.com/')


class UltimakerCheckupPage(InfoPage):
	def __init__(self, parent):
		super(UltimakerCheckupPage, self).__init__(parent, _("Ultimaker Checkup"))

		self.checkBitmap = wx.Bitmap(resources.getPathForImage('checkmark.png'))
		self.crossBitmap = wx.Bitmap(resources.getPathForImage('cross.png'))
		self.unknownBitmap = wx.Bitmap(resources.getPathForImage('question.png'))
		self.endStopNoneBitmap = wx.Bitmap(resources.getPathForImage('endstop_none.png'))
		self.endStopXMinBitmap = wx.Bitmap(resources.getPathForImage('endstop_xmin.png'))
		self.endStopXMaxBitmap = wx.Bitmap(resources.getPathForImage('endstop_xmax.png'))
		self.endStopYMinBitmap = wx.Bitmap(resources.getPathForImage('endstop_ymin.png'))
		self.endStopYMaxBitmap = wx.Bitmap(resources.getPathForImage('endstop_ymax.png'))
		self.endStopZMinBitmap = wx.Bitmap(resources.getPathForImage('endstop_zmin.png'))
		self.endStopZMaxBitmap = wx.Bitmap(resources.getPathForImage('endstop_zmax.png'))

		self.AddText(
			_("It is a good idea to do a few sanity checks now on your Ultimaker.\nYou can skip these if you know your machine is functional."))
		b1, b2 = self.AddDualButton(_("Run checks"), _("Skip checks"))
		b1.Bind(wx.EVT_BUTTON, self.OnCheckClick)
		b2.Bind(wx.EVT_BUTTON, self.OnSkipClick)
		self.AddSeperator()
		self.commState = self.AddCheckmark(_("Communication:"), self.unknownBitmap)
		self.tempState = self.AddCheckmark(_("Temperature:"), self.unknownBitmap)
		self.stopState = self.AddCheckmark(_("Endstops:"), self.unknownBitmap)
		self.AddSeperator()
		self.infoBox = self.AddInfoBox()
		self.machineState = self.AddText("")
		self.temperatureLabel = self.AddText("")
		self.errorLogButton = self.AddButton(_("Show error log"))
		self.errorLogButton.Show(False)
		self.AddSeperator()
		self.endstopBitmap = self.AddBitmap(self.endStopNoneBitmap)
		self.comm = None
		self.xMinStop = False
		self.xMaxStop = False
		self.yMinStop = False
		self.yMaxStop = False
		self.zMinStop = False
		self.zMaxStop = False

		self.Bind(wx.EVT_BUTTON, self.OnErrorLog, self.errorLogButton)

	def __del__(self):
		if self.comm is not None:
			self.comm.close()

	def AllowNext(self):
		self.endstopBitmap.Show(False)
		return False

	def OnSkipClick(self, e):
		self.GetParent().FindWindowById(wx.ID_FORWARD).Enable()
		self.GetParent().ShowPage(self.GetNext())

	def OnCheckClick(self, e=None):
		self.errorLogButton.Show(False)
		if self.comm is not None:
			self.comm.close()
			del self.comm
			self.comm = None
			wx.CallAfter(self.OnCheckClick)
			return
		self.infoBox.SetBusy(_("Connecting to machine."))
		self.commState.SetBitmap(self.unknownBitmap)
		self.tempState.SetBitmap(self.unknownBitmap)
		self.stopState.SetBitmap(self.unknownBitmap)
		self.checkupState = 0
		self.checkExtruderNr = 0
		self.comm = machineCom.MachineCom(callbackObject=self)

	def OnErrorLog(self, e):
		printWindow.LogWindow('\n'.join(self.comm.getLog()))

	def mcLog(self, message):
		pass

	def mcTempUpdate(self, temp, bedTemp, targetTemp, bedTargetTemp):
		if not self.comm.isOperational():
			return
		if self.checkupState == 0:
			self.tempCheckTimeout = 20
			if temp[self.checkExtruderNr] > 70:
				self.checkupState = 1
				wx.CallAfter(self.infoBox.SetInfo, _("Cooldown before temperature check."))
				self.comm.sendCommand("M104 S0 T%d" % (self.checkExtruderNr))
				self.comm.sendCommand('M104 S0 T%d' % (self.checkExtruderNr))
			else:
				self.startTemp = temp[self.checkExtruderNr]
				self.checkupState = 2
				wx.CallAfter(self.infoBox.SetInfo, _("Checking the heater and temperature sensor."))
				self.comm.sendCommand('M104 S200 T%d' % (self.checkExtruderNr))
				self.comm.sendCommand('M104 S200 T%d' % (self.checkExtruderNr))
		elif self.checkupState == 1:
			if temp[self.checkExtruderNr] < 60:
				self.startTemp = temp[self.checkExtruderNr]
				self.checkupState = 2
				wx.CallAfter(self.infoBox.SetInfo, _("Checking the heater and temperature sensor."))
				self.comm.sendCommand('M104 S200 T%d' % (self.checkExtruderNr))
				self.comm.sendCommand('M104 S200 T%d' % (self.checkExtruderNr))
		elif self.checkupState == 2:
			#print "WARNING, TEMPERATURE TEST DISABLED FOR TESTING!"
			if temp[self.checkExtruderNr] > self.startTemp + 40:
				self.comm.sendCommand('M104 S0 T%d' % (self.checkExtruderNr))
				self.comm.sendCommand('M104 S0 T%d' % (self.checkExtruderNr))
				if self.checkExtruderNr < int(profile.getMachineSetting('extruder_amount')):
					self.checkExtruderNr = 0
					self.checkupState = 3
					wx.CallAfter(self.infoBox.SetAttention, _("Please make sure none of the endstops are pressed."))
					wx.CallAfter(self.endstopBitmap.Show, True)
					wx.CallAfter(self.Layout)
					self.comm.sendCommand('M119')
					wx.CallAfter(self.tempState.SetBitmap, self.checkBitmap)
				else:
					self.checkupState = 0
					self.checkExtruderNr += 1
			else:
				self.tempCheckTimeout -= 1
				if self.tempCheckTimeout < 1:
					self.checkupState = -1
					wx.CallAfter(self.tempState.SetBitmap, self.crossBitmap)
					wx.CallAfter(self.infoBox.SetError, _("Temperature measurement FAILED!"), 'http://wiki.ultimaker.com/Cura:_Temperature_measurement_problems')
					self.comm.sendCommand('M104 S0 T%d' % (self.checkExtruderNr))
					self.comm.sendCommand('M104 S0 T%d' % (self.checkExtruderNr))
		elif self.checkupState >= 3 and self.checkupState < 10:
			self.comm.sendCommand('M119')
		wx.CallAfter(self.temperatureLabel.SetLabel, _("Head temperature: %d") % (temp[self.checkExtruderNr]))

	def mcStateChange(self, state):
		if self.comm is None:
			return
		if self.comm.isOperational():
			wx.CallAfter(self.commState.SetBitmap, self.checkBitmap)
			wx.CallAfter(self.machineState.SetLabel, _("Communication State: %s") % (self.comm.getStateString()))
		elif self.comm.isError():
			wx.CallAfter(self.commState.SetBitmap, self.crossBitmap)
			wx.CallAfter(self.infoBox.SetError, _("Failed to establish connection with the printer."), 'http://wiki.ultimaker.com/Cura:_Connection_problems')
			wx.CallAfter(self.endstopBitmap.Show, False)
			wx.CallAfter(self.machineState.SetLabel, '%s' % (self.comm.getErrorString()))
			wx.CallAfter(self.errorLogButton.Show, True)
			wx.CallAfter(self.Layout)
		else:
			wx.CallAfter(self.machineState.SetLabel, _("Communication State: %s") % (self.comm.getStateString()))

	def mcMessage(self, message):
		if self.checkupState >= 3 and self.checkupState < 10 and ('_min' in message or '_max' in message):
			for data in message.split(' '):
				if ':' in data:
					tag, value = data.split(':', 1)
					if tag == 'x_min':
						self.xMinStop = (value == 'H' or value == 'TRIGGERED')
					if tag == 'x_max':
						self.xMaxStop = (value == 'H' or value == 'TRIGGERED')
					if tag == 'y_min':
						self.yMinStop = (value == 'H' or value == 'TRIGGERED')
					if tag == 'y_max':
						self.yMaxStop = (value == 'H' or value == 'TRIGGERED')
					if tag == 'z_min':
						self.zMinStop = (value == 'H' or value == 'TRIGGERED')
					if tag == 'z_max':
						self.zMaxStop = (value == 'H' or value == 'TRIGGERED')
			if ':' in message:
				tag, value = map(str.strip, message.split(':', 1))
				if tag == 'x_min':
					self.xMinStop = (value == 'H' or value == 'TRIGGERED')
				if tag == 'x_max':
					self.xMaxStop = (value == 'H' or value == 'TRIGGERED')
				if tag == 'y_min':
					self.yMinStop = (value == 'H' or value == 'TRIGGERED')
				if tag == 'y_max':
					self.yMaxStop = (value == 'H' or value == 'TRIGGERED')
				if tag == 'z_min':
					self.zMinStop = (value == 'H' or value == 'TRIGGERED')
				if tag == 'z_max':
					self.zMaxStop = (value == 'H' or value == 'TRIGGERED')
			if 'z_max' in message:
				self.comm.sendCommand('M119')

			if self.checkupState == 3:
				if not self.xMinStop and not self.xMaxStop and not self.yMinStop and not self.yMaxStop and not self.zMinStop and not self.zMaxStop:
					if profile.getMachineSetting('machine_type') == 'ultimaker_plus':
						self.checkupState = 5
						wx.CallAfter(self.infoBox.SetAttention, _("Please press the left X endstop."))
						wx.CallAfter(self.endstopBitmap.SetBitmap, self.endStopXMinBitmap)
					else:
						self.checkupState = 4
						wx.CallAfter(self.infoBox.SetAttention, _("Please press the right X endstop."))
						wx.CallAfter(self.endstopBitmap.SetBitmap, self.endStopXMaxBitmap)
			elif self.checkupState == 4:
				if not self.xMinStop and self.xMaxStop and not self.yMinStop and not self.yMaxStop and not self.zMinStop and not self.zMaxStop:
					self.checkupState = 5
					wx.CallAfter(self.infoBox.SetAttention, _("Please press the left X endstop."))
					wx.CallAfter(self.endstopBitmap.SetBitmap, self.endStopXMinBitmap)
			elif self.checkupState == 5:
				if self.xMinStop and not self.xMaxStop and not self.yMinStop and not self.yMaxStop and not self.zMinStop and not self.zMaxStop:
					self.checkupState = 6
					wx.CallAfter(self.infoBox.SetAttention, _("Please press the front Y endstop."))
					wx.CallAfter(self.endstopBitmap.SetBitmap, self.endStopYMinBitmap)
			elif self.checkupState == 6:
				if not self.xMinStop and not self.xMaxStop and self.yMinStop and not self.yMaxStop and not self.zMinStop and not self.zMaxStop:
					if profile.getMachineSetting('machine_type') == 'ultimaker_plus':
						self.checkupState = 8
						wx.CallAfter(self.infoBox.SetAttention, _("Please press the top Z endstop."))
						wx.CallAfter(self.endstopBitmap.SetBitmap, self.endStopZMinBitmap)
					else:
						self.checkupState = 7
						wx.CallAfter(self.infoBox.SetAttention, _("Please press the back Y endstop."))
						wx.CallAfter(self.endstopBitmap.SetBitmap, self.endStopYMaxBitmap)
			elif self.checkupState == 7:
				if not self.xMinStop and not self.xMaxStop and not self.yMinStop and self.yMaxStop and not self.zMinStop and not self.zMaxStop:
					self.checkupState = 8
					wx.CallAfter(self.infoBox.SetAttention, _("Please press the top Z endstop."))
					wx.CallAfter(self.endstopBitmap.SetBitmap, self.endStopZMinBitmap)
			elif self.checkupState == 8:
				if not self.xMinStop and not self.xMaxStop and not self.yMinStop and not self.yMaxStop and self.zMinStop and not self.zMaxStop:
					if profile.getMachineSetting('machine_type') == 'ultimaker_plus':
						self.checkupState = 10
						self.comm.close()
						wx.CallAfter(self.infoBox.SetInfo, _("Checkup finished"))
						wx.CallAfter(self.infoBox.SetReadyIndicator)
						wx.CallAfter(self.endstopBitmap.Show, False)
						wx.CallAfter(self.stopState.SetBitmap, self.checkBitmap)
						wx.CallAfter(self.OnSkipClick, None)
					else:
						self.checkupState = 9
						wx.CallAfter(self.infoBox.SetAttention, _("Please press the bottom Z endstop."))
						wx.CallAfter(self.endstopBitmap.SetBitmap, self.endStopZMaxBitmap)
			elif self.checkupState == 9:
				if not self.xMinStop and not self.xMaxStop and not self.yMinStop and not self.yMaxStop and not self.zMinStop and self.zMaxStop:
					self.checkupState = 10
					self.comm.close()
					wx.CallAfter(self.infoBox.SetInfo, _("Checkup finished"))
					wx.CallAfter(self.infoBox.SetReadyIndicator)
					wx.CallAfter(self.endstopBitmap.Show, False)
					wx.CallAfter(self.stopState.SetBitmap, self.checkBitmap)
					wx.CallAfter(self.OnSkipClick, None)

	def mcProgress(self, lineNr):
		pass

	def mcZChange(self, newZ):
		pass


class UltimakerCalibrationPage(InfoPage):
	def __init__(self, parent):
		super(UltimakerCalibrationPage, self).__init__(parent, _("Ultimaker Calibration"))

		self.AddText("Your Ultimaker requires some calibration.")
		self.AddText("This calibration is needed for a proper extrusion amount.")
		self.AddSeperator()
		self.AddText("The following values are needed:")
		self.AddText("* Diameter of filament")
		self.AddText("* Number of steps per mm of filament extrusion")
		self.AddSeperator()
		self.AddText("The better you have calibrated these values, the better your prints\nwill become.")
		self.AddSeperator()
		self.AddText("First we need the diameter of your filament:")
		self.filamentDiameter = self.AddTextCtrl(profile.getProfileSetting('filament_diameter'))
		self.AddText(
			"If you do not own digital Calipers that can measure\nat least 2 digits then use 2.89mm.\nWhich is the average diameter of most filament.")
		self.AddText("Note: This value can be changed later at any time.")

	def StoreData(self):
		profile.putProfileSetting('filament_diameter', self.filamentDiameter.GetValue())


class UltimakerCalibrateStepsPerEPage(InfoPage):
	def __init__(self, parent):
		super(UltimakerCalibrateStepsPerEPage, self).__init__(parent, _("Ultimaker Calibration"))

		#if profile.getMachineSetting('steps_per_e') == '0':
		#	profile.putMachineSetting('steps_per_e', '865.888')

		self.AddText(_("Calibrating the Steps Per E requires some manual actions."))
		self.AddText(_("First remove any filament from your machine."))
		self.AddText(_("Next put in your filament so the tip is aligned with the\ntop of the extruder drive."))
		self.AddText(_("We'll push the filament 100mm"))
		self.extrudeButton = self.AddButton(_("Extrude 100mm filament"))
		self.AddText(_("Now measure the amount of extruded filament:\n(this can be more or less then 100mm)"))
		self.lengthInput, self.saveLengthButton = self.AddTextCtrlButton("100", _("Save"))
		self.AddText(_("This results in the following steps per E:"))
		self.stepsPerEInput = self.AddTextCtrl(profile.getMachineSetting('steps_per_e'))
		self.AddText(_("You can repeat these steps to get better calibration."))
		self.AddSeperator()
		self.AddText(
			_("If you still have filament in your printer which needs\nheat to remove, press the heat up button below:"))
		self.heatButton = self.AddButton(_("Heatup for filament removal"))

		self.saveLengthButton.Bind(wx.EVT_BUTTON, self.OnSaveLengthClick)
		self.extrudeButton.Bind(wx.EVT_BUTTON, self.OnExtrudeClick)
		self.heatButton.Bind(wx.EVT_BUTTON, self.OnHeatClick)

	def OnSaveLengthClick(self, e):
		currentEValue = float(self.stepsPerEInput.GetValue())
		realExtrudeLength = float(self.lengthInput.GetValue())
		newEValue = currentEValue * 100 / realExtrudeLength
		self.stepsPerEInput.SetValue(str(newEValue))
		self.lengthInput.SetValue("100")

	def OnExtrudeClick(self, e):
		t = threading.Thread(target=self.OnExtrudeRun)
		t.daemon = True
		t.start()

	def OnExtrudeRun(self):
		self.heatButton.Enable(False)
		self.extrudeButton.Enable(False)
		currentEValue = float(self.stepsPerEInput.GetValue())
		self.comm = machineCom.MachineCom()
		if not self.comm.isOpen():
			wx.MessageBox(
				_("Error: Failed to open serial port to machine\nIf this keeps happening, try disconnecting and reconnecting the USB cable"),
				'Printer error', wx.OK | wx.ICON_INFORMATION)
			self.heatButton.Enable(True)
			self.extrudeButton.Enable(True)
			return
		while True:
			line = self.comm.readline()
			if line == '':
				return
			if 'start' in line:
				break
			#Wait 3 seconds for the SD card init to timeout if we have SD in our firmware but there is no SD card found.
		time.sleep(3)

		self.sendGCommand('M302') #Disable cold extrusion protection
		self.sendGCommand("M92 E%f" % (currentEValue))
		self.sendGCommand("G92 E0")
		self.sendGCommand("G1 E100 F600")
		time.sleep(15)
		self.comm.close()
		self.extrudeButton.Enable()
		self.heatButton.Enable()

	def OnHeatClick(self, e):
		t = threading.Thread(target=self.OnHeatRun)
		t.daemon = True
		t.start()

	def OnHeatRun(self):
		self.heatButton.Enable(False)
		self.extrudeButton.Enable(False)
		self.comm = machineCom.MachineCom()
		if not self.comm.isOpen():
			wx.MessageBox(
				_("Error: Failed to open serial port to machine\nIf this keeps happening, try disconnecting and reconnecting the USB cable"),
				'Printer error', wx.OK | wx.ICON_INFORMATION)
			self.heatButton.Enable(True)
			self.extrudeButton.Enable(True)
			return
		while True:
			line = self.comm.readline()
			if line == '':
				self.heatButton.Enable(True)
				self.extrudeButton.Enable(True)
				return
			if 'start' in line:
				break
			#Wait 3 seconds for the SD card init to timeout if we have SD in our firmware but there is no SD card found.
		time.sleep(3)

		self.sendGCommand('M104 S200') #Set the temperature to 200C, should be enough to get PLA and ABS out.
		wx.MessageBox(
			'Wait till you can remove the filament from the machine, and press OK.\n(Temperature is set to 200C)',
			'Machine heatup', wx.OK | wx.ICON_INFORMATION)
		self.sendGCommand('M104 S0')
		time.sleep(1)
		self.comm.close()
		self.heatButton.Enable(True)
		self.extrudeButton.Enable(True)

	def sendGCommand(self, cmd):
		self.comm.sendCommand(cmd) #Disable cold extrusion protection
		while True:
			line = self.comm.readline()
			if line == '':
				return
			if line.startswith('ok'):
				break

	def StoreData(self):
		profile.putPreference('steps_per_e', self.stepsPerEInput.GetValue())


class Ultimaker2ReadyPage(InfoPage):
	def __init__(self, parent):
		super(Ultimaker2ReadyPage, self).__init__(parent, _("Ultimaker2"))
		self.AddText(_('Congratulations on your the purchase of your brand new Ultimaker2.'))
		self.AddText(_('Cura is now ready to be used with your Ultimaker2.'))
		self.AddSeperator()


class LulzbotReadyPage(InfoPage):
	def __init__(self, parent):
		super(LulzbotReadyPage, self).__init__(parent, _("Lulzbot TAZ/Mini"))
		self.AddText(_('Cura is now ready to be used with your Lulzbot.'))
		self.AddSeperator()
		
		
class SelectParts(InfoPage):
	def __init__(self, parent):
		super(SelectParts, self).__init__(parent, _("Select upgraded parts you have"))
		self.AddText(_("To assist you in having better default settings for your Ultimaker\nCura would like to know which upgrades you have in your machine."))
		self.AddSeperator()
		self.springExtruder = self.AddCheckbox(_("Extruder drive upgrade"))
		self.heatedBedKit = self.AddCheckbox(_("Heated printer bed (kit)"))
		self.heatedBed = self.AddCheckbox(_("Heated printer bed (self built)"))
		self.dualExtrusion = self.AddCheckbox(_("Dual extrusion (experimental)"))
		self.AddSeperator()
		self.AddText(_("If you have an Ultimaker bought after october 2012 you will have the\nExtruder drive upgrade. If you do not have this upgrade,\nit is highly recommended to improve reliability."))
		self.AddText(_("This upgrade can be bought from the Ultimaker webshop\nor found on thingiverse as thing:26094"))
		self.springExtruder.SetValue(True)

	def StoreData(self):
		profile.putMachineSetting('ultimaker_extruder_upgrade', str(self.springExtruder.GetValue()))
		if self.heatedBed.GetValue() or self.heatedBedKit.GetValue():
			profile.putMachineSetting('has_heated_bed', 'True')
		else:
			profile.putMachineSetting('has_heated_bed', 'False')
		if self.dualExtrusion.GetValue():
			profile.putMachineSetting('extruder_amount', '2')
			profile.putMachineSetting('machine_depth', '195')
		else:
			profile.putMachineSetting('extruder_amount', '1')
		if profile.getMachineSetting('ultimaker_extruder_upgrade') == 'True':
			profile.putProfileSetting('retraction_enable', 'True')
		else:
			profile.putProfileSetting('retraction_enable', 'False')
			
		
class ConfigWizard(wx.wizard.Wizard):
	def __init__(self, addNew = False):
		super(ConfigWizard, self).__init__(None, -1, _("Configuration Wizard"))
		
		
		# Get the number of the current machine and label it as the old index
		self._old_machine_index = int(profile.getPreferenceFloat('active_machine'))
		if addNew:
			profile.setActiveMachine(profile.getMachineCount())

		self.Bind(wx.wizard.EVT_WIZARD_PAGE_CHANGED, self.OnPageChanged)
		self.Bind(wx.wizard.EVT_WIZARD_PAGE_CHANGING, self.OnPageChanging)
		self.Bind(wx.wizard.EVT_WIZARD_CANCEL, self.OnCancel)

		self.firstInfoPage = FirstInfoPage(self, addNew)
		self.machineSelectPage = MachineSelectPage(self)
		self.tamReadyPage = TAMReadyPage(self)
		self.TAM_select_materials = TAMSelectMaterials(self)
		self.TAM_octoprint_config = TAMOctoPrintInfo(self)
		self.TAM_select_options = TAMSelectOptions(self)
		self.TAM_select_strength = TAMSelectStrength(self)
		self.TAM_select_quality = TAMSelectQuality(self)
		self.TAM_select_support = TAMSelectSupport(self)
		self.TAM_first_print = TAMFirstPrint(self)
		
		self.ultimakerSelectParts = SelectParts(self)
		self.ultimakerFirmwareUpgradePage = UltimakerFirmwareUpgradePage(self)
		self.ultimakerCheckupPage = UltimakerCheckupPage(self)
		self.ultimakerCalibrationPage = UltimakerCalibrationPage(self)
		self.ultimakerCalibrateStepsPerEPage = UltimakerCalibrateStepsPerEPage(self)
		self.bedLevelPage = bedLevelWizardMain(self)
		self.headOffsetCalibration = headOffsetCalibrationPage(self)
		self.printrbotSelectType = PrintrbotPage(self)
		self.otherMachineSelectPage = OtherMachineSelectPage(self)
		self.customRepRapInfoPage = CustomRepRapInfoPage(self)
		self.otherMachineInfoPage = OtherMachineInfoPage(self)
		self.ultimaker2ReadyPage = Ultimaker2ReadyPage(self)
		self.lulzbotReadyPage = LulzbotReadyPage(self)

		wx.wizard.WizardPageSimple.Chain(self.firstInfoPage, self.machineSelectPage)
		wx.wizard.WizardPageSimple.Chain(self.machineSelectPage, self.TAM_octoprint_config)
		wx.wizard.WizardPageSimple.Chain(self.TAM_octoprint_config, self.tamReadyPage)
		wx.wizard.WizardPageSimple.Chain(self.tamReadyPage, self.TAM_select_materials)
		wx.wizard.WizardPageSimple.Chain(self.TAM_select_materials, self.TAM_select_quality)
		wx.wizard.WizardPageSimple.Chain(self.TAM_select_quality, self.TAM_select_strength)
		wx.wizard.WizardPageSimple.Chain(self.TAM_select_strength, self.TAM_select_support)
		wx.wizard.WizardPageSimple.Chain(self.TAM_select_support, self.TAM_first_print)
		wx.wizard.WizardPageSimple.Chain(self.printrbotSelectType, self.otherMachineInfoPage)
		wx.wizard.WizardPageSimple.Chain(self.otherMachineSelectPage, self.customRepRapInfoPage)

		self.FitToPage(self.TAM_select_materials)
		self.GetPageAreaSizer().Add(self.firstInfoPage)

		self.RunWizard(self.firstInfoPage)
		self.Destroy()

	def OnPageChanging(self, e):
		e.GetPage().StoreData()

	def OnPageChanged(self, e):
		if e.GetPage().AllowNext():
			self.FindWindowById(wx.ID_FORWARD).Enable()
		else:
			self.FindWindowById(wx.ID_FORWARD).Disable()
		if e.GetPage().AllowBack():
			self.FindWindowById(wx.ID_BACKWARD).Enable()
		else:
			self.FindWindowById(wx.ID_BACKWARD).Disable()

	def OnCancel(self, e):
		profile.setActiveMachine(self._old_machine_index)

	def disableNext(self):
		self.FindWindowById(wx.ID_FORWARD).Disable()

class bedLevelWizardMain(InfoPage):
	def __init__(self, parent):
		super(bedLevelWizardMain, self).__init__(parent, _("Bed leveling wizard"))

		self.AddText(_('This wizard will help you in leveling your printer bed'))
		self.AddSeperator()
		self.AddText(_('It will do the following steps'))
		self.AddText(_('* Move the printer head to each corner'))
		self.AddText(_('  and let you adjust the height of the bed to the nozzle'))
		self.AddText(_('* Print a line around the bed to check if it is level'))
		self.AddSeperator()

		self.connectButton = self.AddButton(_('Connect to printer'))
		self.comm = None

		self.infoBox = self.AddInfoBox()
		self.resumeButton = self.AddButton(_('Resume'))
		self.upButton, self.downButton = self.AddDualButton(_('Up 0.2mm'), _('Down 0.2mm'))
		self.upButton2, self.downButton2 = self.AddDualButton(_('Up 10mm'), _('Down 10mm'))
		self.resumeButton.Enable(False)

		self.upButton.Enable(False)
		self.downButton.Enable(False)
		self.upButton2.Enable(False)
		self.downButton2.Enable(False)

		self.Bind(wx.EVT_BUTTON, self.OnConnect, self.connectButton)
		self.Bind(wx.EVT_BUTTON, self.OnResume, self.resumeButton)
		self.Bind(wx.EVT_BUTTON, self.OnBedUp, self.upButton)
		self.Bind(wx.EVT_BUTTON, self.OnBedDown, self.downButton)
		self.Bind(wx.EVT_BUTTON, self.OnBedUp2, self.upButton2)
		self.Bind(wx.EVT_BUTTON, self.OnBedDown2, self.downButton2)

	def OnConnect(self, e = None):
		if self.comm is not None:
			self.comm.close()
			del self.comm
			self.comm = None
			wx.CallAfter(self.OnConnect)
			return
		self.connectButton.Enable(False)
		self.comm = machineCom.MachineCom(callbackObject=self)
		self.infoBox.SetBusy(_('Connecting to machine.'))
		self._wizardState = 0

	def OnBedUp(self, e):
		feedZ = profile.getProfileSettingFloat('print_speed') * 60
		self.comm.sendCommand('G92 Z10')
		self.comm.sendCommand('G1 Z9.8 F%d' % (feedZ))
		self.comm.sendCommand('M400')

	def OnBedDown(self, e):
		feedZ = profile.getProfileSettingFloat('print_speed') * 60
		self.comm.sendCommand('G92 Z10')
		self.comm.sendCommand('G1 Z10.2 F%d' % (feedZ))
		self.comm.sendCommand('M400')

	def OnBedUp2(self, e):
		feedZ = profile.getProfileSettingFloat('print_speed') * 60
		self.comm.sendCommand('G92 Z10')
		self.comm.sendCommand('G1 Z0 F%d' % (feedZ))
		self.comm.sendCommand('M400')

	def OnBedDown2(self, e):
		feedZ = profile.getProfileSettingFloat('print_speed') * 60
		self.comm.sendCommand('G92 Z10')
		self.comm.sendCommand('G1 Z20 F%d' % (feedZ))
		self.comm.sendCommand('M400')

	def AllowNext(self):
		if self.GetParent().headOffsetCalibration is not None and int(profile.getMachineSetting('extruder_amount')) > 1:
			wx.wizard.WizardPageSimple.Chain(self, self.GetParent().headOffsetCalibration)
		return True

	def OnResume(self, e):
		feedZ = profile.getProfileSettingFloat('print_speed') * 60
		feedTravel = profile.getProfileSettingFloat('travel_speed') * 60
		if self._wizardState == -1:
			wx.CallAfter(self.infoBox.SetInfo, _('Homing printer...'))
			wx.CallAfter(self.upButton.Enable, False)
			wx.CallAfter(self.downButton.Enable, False)
			wx.CallAfter(self.upButton2.Enable, False)
			wx.CallAfter(self.downButton2.Enable, False)
			self.comm.sendCommand('M105')
			self.comm.sendCommand('G28')
			self._wizardState = 1
		elif self._wizardState == 2:
			if profile.getMachineSetting('has_heated_bed') == 'True':
				wx.CallAfter(self.infoBox.SetBusy, _('Moving head to back center...'))
				self.comm.sendCommand('G1 Z3 F%d' % (feedZ))
				self.comm.sendCommand('G1 X%d Y%d F%d' % (profile.getMachineSettingFloat('machine_width') / 2.0, profile.getMachineSettingFloat('machine_depth'), feedTravel))
				self.comm.sendCommand('G1 Z0 F%d' % (feedZ))
				self.comm.sendCommand('M400')
				self._wizardState = 3
			else:
				wx.CallAfter(self.infoBox.SetBusy, _('Moving head to back left corner...'))
				self.comm.sendCommand('G1 Z3 F%d' % (feedZ))
				self.comm.sendCommand('G1 X%d Y%d F%d' % (0, profile.getMachineSettingFloat('machine_depth'), feedTravel))
				self.comm.sendCommand('G1 Z0 F%d' % (feedZ))
				self.comm.sendCommand('M400')
				self._wizardState = 3
		elif self._wizardState == 4:
			if profile.getMachineSetting('has_heated_bed') == 'True':
				wx.CallAfter(self.infoBox.SetBusy, _('Moving head to front right corner...'))
				self.comm.sendCommand('G1 Z3 F%d' % (feedZ))
				self.comm.sendCommand('G1 X%d Y%d F%d' % (profile.getMachineSettingFloat('machine_width') - 5.0, 5, feedTravel))
				self.comm.sendCommand('G1 Z0 F%d' % (feedZ))
				self.comm.sendCommand('M400')
				self._wizardState = 7
			else:
				wx.CallAfter(self.infoBox.SetBusy, _('Moving head to back right corner...'))
				self.comm.sendCommand('G1 Z3 F%d' % (feedZ))
				self.comm.sendCommand('G1 X%d Y%d F%d' % (profile.getMachineSettingFloat('machine_width') - 5.0, profile.getMachineSettingFloat('machine_depth') - 25, feedTravel))
				self.comm.sendCommand('G1 Z0 F%d' % (feedZ))
				self.comm.sendCommand('M400')
				self._wizardState = 5
		elif self._wizardState == 6:
			wx.CallAfter(self.infoBox.SetBusy, _('Moving head to front right corner...'))
			self.comm.sendCommand('G1 Z3 F%d' % (feedZ))
			self.comm.sendCommand('G1 X%d Y%d F%d' % (profile.getMachineSettingFloat('machine_width') - 5.0, 20, feedTravel))
			self.comm.sendCommand('G1 Z0 F%d' % (feedZ))
			self.comm.sendCommand('M400')
			self._wizardState = 7
		elif self._wizardState == 8:
			wx.CallAfter(self.infoBox.SetBusy, _('Heating up printer...'))
			self.comm.sendCommand('G1 Z15 F%d' % (feedZ))
			self.comm.sendCommand('M104 S%d' % (profile.getProfileSettingFloat('print_temperature')))
			self.comm.sendCommand('G1 X%d Y%d F%d' % (0, 0, feedTravel))
			self._wizardState = 9
		elif self._wizardState == 10:
			self._wizardState = 11
			wx.CallAfter(self.infoBox.SetInfo, _('Printing a square on the printer bed at 0.3mm height.'))
			feedZ = profile.getProfileSettingFloat('print_speed') * 60
			feedPrint = profile.getProfileSettingFloat('print_speed') * 60
			feedTravel = profile.getProfileSettingFloat('travel_speed') * 60
			w = profile.getMachineSettingFloat('machine_width') - 10
			d = profile.getMachineSettingFloat('machine_depth')
			filamentRadius = profile.getProfileSettingFloat('filament_diameter') / 2
			filamentArea = math.pi * filamentRadius * filamentRadius
			ePerMM = (profile.calculateEdgeWidth() * 0.3) / filamentArea
			eValue = 0.0

			gcodeList = [
				'G1 Z2 F%d' % (feedZ),
				'G92 E0',
				'G1 X%d Y%d F%d' % (5, 5, feedTravel),
				'G1 Z0.3 F%d' % (feedZ)]
			eValue += 5.0
			gcodeList.append('G1 E%f F%d' % (eValue, profile.getProfileSettingFloat('retraction_speed') * 60))

			for i in xrange(0, 3):
				dist = 5.0 + 0.4 * float(i)
				eValue += (d - 2.0*dist) * ePerMM
				gcodeList.append('G1 X%f Y%f E%f F%d' % (dist, d - dist, eValue, feedPrint))
				eValue += (w - 2.0*dist) * ePerMM
				gcodeList.append('G1 X%f Y%f E%f F%d' % (w - dist, d - dist, eValue, feedPrint))
				eValue += (d - 2.0*dist) * ePerMM
				gcodeList.append('G1 X%f Y%f E%f F%d' % (w - dist, dist, eValue, feedPrint))
				eValue += (w - 2.0*dist) * ePerMM
				gcodeList.append('G1 X%f Y%f E%f F%d' % (dist, dist, eValue, feedPrint))

			gcodeList.append('M400')
			self.comm.printGCode(gcodeList)
		self.resumeButton.Enable(False)

	def mcLog(self, message):
		print 'Log:', message

	def mcTempUpdate(self, temp, bedTemp, targetTemp, bedTargetTemp):
		if self._wizardState == 1:
			self._wizardState = 2
			wx.CallAfter(self.infoBox.SetAttention, _('Adjust the front left screw of your printer bed\nSo the nozzle just hits the bed.'))
			wx.CallAfter(self.resumeButton.Enable, True)
		elif self._wizardState == 3:
			self._wizardState = 4
			if profile.getMachineSetting('has_heated_bed') == 'True':
				wx.CallAfter(self.infoBox.SetAttention, _('Adjust the back screw of your printer bed\nSo the nozzle just hits the bed.'))
			else:
				wx.CallAfter(self.infoBox.SetAttention, _('Adjust the back left screw of your printer bed\nSo the nozzle just hits the bed.'))
			wx.CallAfter(self.resumeButton.Enable, True)
		elif self._wizardState == 5:
			self._wizardState = 6
			wx.CallAfter(self.infoBox.SetAttention, _('Adjust the back right screw of your printer bed\nSo the nozzle just hits the bed.'))
			wx.CallAfter(self.resumeButton.Enable, True)
		elif self._wizardState == 7:
			self._wizardState = 8
			wx.CallAfter(self.infoBox.SetAttention, _('Adjust the front right screw of your printer bed\nSo the nozzle just hits the bed.'))
			wx.CallAfter(self.resumeButton.Enable, True)
		elif self._wizardState == 9:
			if temp[0] < profile.getProfileSettingFloat('print_temperature') - 5:
				wx.CallAfter(self.infoBox.SetInfo, _('Heating up printer: %d/%d') % (temp[0], profile.getProfileSettingFloat('print_temperature')))
			else:
				wx.CallAfter(self.infoBox.SetAttention, _('The printer is hot now. Please insert some PLA filament into the printer.'))
				wx.CallAfter(self.resumeButton.Enable, True)
				self._wizardState = 10

	def mcStateChange(self, state):
		if self.comm is None:
			return
		if self.comm.isOperational():
			if self._wizardState == 0:
				wx.CallAfter(self.infoBox.SetAttention, _('Use the up/down buttons to move the bed and adjust your Z endstop.'))
				wx.CallAfter(self.upButton.Enable, True)
				wx.CallAfter(self.downButton.Enable, True)
				wx.CallAfter(self.upButton2.Enable, True)
				wx.CallAfter(self.downButton2.Enable, True)
				wx.CallAfter(self.resumeButton.Enable, True)
				self._wizardState = -1
			elif self._wizardState == 11 and not self.comm.isPrinting():
				self.comm.sendCommand('G1 Z15 F%d' % (profile.getProfileSettingFloat('print_speed') * 60))
				self.comm.sendCommand('G92 E0')
				self.comm.sendCommand('G1 E-10 F%d' % (profile.getProfileSettingFloat('retraction_speed') * 60))
				self.comm.sendCommand('M104 S0')
				wx.CallAfter(self.infoBox.SetInfo, _('Calibration finished.\nThe squares on the bed should slightly touch each other.'))
				wx.CallAfter(self.infoBox.SetReadyIndicator)
				wx.CallAfter(self.GetParent().FindWindowById(wx.ID_FORWARD).Enable)
				wx.CallAfter(self.connectButton.Enable, True)
				self._wizardState = 12
		elif self.comm.isError():
			wx.CallAfter(self.infoBox.SetError, _('Failed to establish connection with the printer.'), 'http://wiki.ultimaker.com/Cura:_Connection_problems')

	def mcMessage(self, message):
		pass

	def mcProgress(self, lineNr):
		pass

	def mcZChange(self, newZ):
		pass


class headOffsetCalibrationPage(InfoPage):
	def __init__(self, parent):
		super(headOffsetCalibrationPage, self).__init__(parent, "Printer head offset calibration")

		self.AddText(_('This wizard will help you in calibrating the printer head offsets of your dual extrusion machine'))
		self.AddSeperator()

		self.connectButton = self.AddButton(_('Connect to printer'))
		self.comm = None

		self.infoBox = self.AddInfoBox()
		self.textEntry = self.AddTextCtrl('')
		self.textEntry.Enable(False)
		self.resumeButton = self.AddButton(_('Resume'))
		self.resumeButton.Enable(False)

		self.Bind(wx.EVT_BUTTON, self.OnConnect, self.connectButton)
		self.Bind(wx.EVT_BUTTON, self.OnResume, self.resumeButton)

	def AllowBack(self):
		return True

	def OnConnect(self, e = None):
		if self.comm is not None:
			self.comm.close()
			del self.comm
			self.comm = None
			wx.CallAfter(self.OnConnect)
			return
		self.connectButton.Enable(False)
		self.comm = machineCom.MachineCom(callbackObject=self)
		self.infoBox.SetBusy(_('Connecting to machine.'))
		self._wizardState = 0

	def OnResume(self, e):
		if self._wizardState == 2:
			self._wizardState = 3
			wx.CallAfter(self.infoBox.SetBusy, _('Printing initial calibration cross'))

			w = profile.getMachineSettingFloat('machine_width')
			d = profile.getMachineSettingFloat('machine_depth')

			gcode = gcodeGenerator.gcodeGenerator()
			gcode.setExtrusionRate(profile.getProfileSettingFloat('nozzle_size') * 1.5, 0.2)
			gcode.setPrintSpeed(profile.getProfileSettingFloat('bottom_layer_speed'))
			gcode.addCmd('T0')
			gcode.addPrime(15)
			gcode.addCmd('T1')
			gcode.addPrime(15)

			gcode.addCmd('T0')
			gcode.addMove(w/2, 5)
			gcode.addMove(z=0.2)
			gcode.addPrime()
			gcode.addExtrude(w/2, d-5.0)
			gcode.addRetract()
			gcode.addMove(5, d/2)
			gcode.addPrime()
			gcode.addExtrude(w-5.0, d/2)
			gcode.addRetract(15)

			gcode.addCmd('T1')
			gcode.addMove(w/2, 5)
			gcode.addPrime()
			gcode.addExtrude(w/2, d-5.0)
			gcode.addRetract()
			gcode.addMove(5, d/2)
			gcode.addPrime()
			gcode.addExtrude(w-5.0, d/2)
			gcode.addRetract(15)
			gcode.addCmd('T0')

			gcode.addMove(z=25)
			gcode.addMove(0, 0)
			gcode.addCmd('M400')

			self.comm.printGCode(gcode.list())
			self.resumeButton.Enable(False)
		elif self._wizardState == 4:
			try:
				float(self.textEntry.GetValue())
			except ValueError:
				return
			profile.putPreference('extruder_offset_x1', self.textEntry.GetValue())
			self._wizardState = 5
			self.infoBox.SetAttention(_('Please measure the distance between the horizontal lines in millimeters.'))
			self.textEntry.SetValue('0.0')
			self.textEntry.Enable(True)
		elif self._wizardState == 5:
			try:
				float(self.textEntry.GetValue())
			except ValueError:
				return
			profile.putPreference('extruder_offset_y1', self.textEntry.GetValue())
			self._wizardState = 6
			self.infoBox.SetBusy(_('Printing the fine calibration lines.'))
			self.textEntry.SetValue('')
			self.textEntry.Enable(False)
			self.resumeButton.Enable(False)

			x = profile.getMachineSettingFloat('extruder_offset_x1')
			y = profile.getMachineSettingFloat('extruder_offset_y1')
			gcode = gcodeGenerator.gcodeGenerator()
			gcode.setExtrusionRate(profile.getProfileSettingFloat('nozzle_size') * 1.5, 0.2)
			gcode.setPrintSpeed(25)
			gcode.addHome()
			gcode.addCmd('T0')
			gcode.addMove(50, 40, 0.2)
			gcode.addPrime(15)
			for n in xrange(0, 10):
				gcode.addExtrude(50 + n * 10, 150)
				gcode.addExtrude(50 + n * 10 + 5, 150)
				gcode.addExtrude(50 + n * 10 + 5, 40)
				gcode.addExtrude(50 + n * 10 + 10, 40)
			gcode.addMove(40, 50)
			for n in xrange(0, 10):
				gcode.addExtrude(150, 50 + n * 10)
				gcode.addExtrude(150, 50 + n * 10 + 5)
				gcode.addExtrude(40, 50 + n * 10 + 5)
				gcode.addExtrude(40, 50 + n * 10 + 10)
			gcode.addRetract(15)

			gcode.addCmd('T1')
			gcode.addMove(50 - x, 30 - y, 0.2)
			gcode.addPrime(15)
			for n in xrange(0, 10):
				gcode.addExtrude(50 + n * 10.2 - 1.0 - x, 140 - y)
				gcode.addExtrude(50 + n * 10.2 - 1.0 + 5.1 - x, 140 - y)
				gcode.addExtrude(50 + n * 10.2 - 1.0 + 5.1 - x, 30 - y)
				gcode.addExtrude(50 + n * 10.2 - 1.0 + 10 - x, 30 - y)
			gcode.addMove(30 - x, 50 - y, 0.2)
			for n in xrange(0, 10):
				gcode.addExtrude(160 - x, 50 + n * 10.2 - 1.0 - y)
				gcode.addExtrude(160 - x, 50 + n * 10.2 - 1.0 + 5.1 - y)
				gcode.addExtrude(30 - x, 50 + n * 10.2 - 1.0 + 5.1 - y)
				gcode.addExtrude(30 - x, 50 + n * 10.2 - 1.0 + 10 - y)
			gcode.addRetract(15)
			gcode.addMove(z=15)
			gcode.addCmd('M400')
			gcode.addCmd('M104 T0 S0')
			gcode.addCmd('M104 T1 S0')
			self.comm.printGCode(gcode.list())
		elif self._wizardState == 7:
			try:
				n = int(self.textEntry.GetValue()) - 1
			except:
				return
			x = profile.getMachineSettingFloat('extruder_offset_x1')
			x += -1.0 + n * 0.1
			profile.putPreference('extruder_offset_x1', '%0.2f' % (x))
			self.infoBox.SetAttention(_('Which horizontal line number lays perfect on top of each other? Front most line is zero.'))
			self.textEntry.SetValue('10')
			self._wizardState = 8
		elif self._wizardState == 8:
			try:
				n = int(self.textEntry.GetValue()) - 1
			except:
				return
			y = profile.getMachineSettingFloat('extruder_offset_y1')
			y += -1.0 + n * 0.1
			profile.putPreference('extruder_offset_y1', '%0.2f' % (y))
			self.infoBox.SetInfo(_('Calibration finished. Offsets are: %s %s') % (profile.getMachineSettingFloat('extruder_offset_x1'), profile.getMachineSettingFloat('extruder_offset_y1')))
			self.infoBox.SetReadyIndicator()
			self._wizardState = 8
			self.comm.close()
			self.resumeButton.Enable(False)

	def mcLog(self, message):
		print 'Log:', message

	def mcTempUpdate(self, temp, bedTemp, targetTemp, bedTargetTemp):
		if self._wizardState == 1:
			if temp[0] >= 210 and temp[1] >= 210:
				self._wizardState = 2
				wx.CallAfter(self.infoBox.SetAttention, _('Please load both extruders with PLA.'))
				wx.CallAfter(self.resumeButton.Enable, True)
				wx.CallAfter(self.resumeButton.SetFocus)

	def mcStateChange(self, state):
		if self.comm is None:
			return
		if self.comm.isOperational():
			if self._wizardState == 0:
				wx.CallAfter(self.infoBox.SetInfo, _('Homing printer and heating up both extruders.'))
				self.comm.sendCommand('M105')
				self.comm.sendCommand('M104 S220 T0')
				self.comm.sendCommand('M104 S220 T1')
				self.comm.sendCommand('G28')
				self.comm.sendCommand('G1 Z15 F%d' % (profile.getProfileSettingFloat('print_speed') * 60))
				self._wizardState = 1
			if not self.comm.isPrinting():
				if self._wizardState == 3:
					self._wizardState = 4
					wx.CallAfter(self.infoBox.SetAttention, _('Please measure the distance between the vertical lines in millimeters.'))
					wx.CallAfter(self.textEntry.SetValue, '0.0')
					wx.CallAfter(self.textEntry.Enable, True)
					wx.CallAfter(self.resumeButton.Enable, True)
					wx.CallAfter(self.resumeButton.SetFocus)
				elif self._wizardState == 6:
					self._wizardState = 7
					wx.CallAfter(self.infoBox.SetAttention, _('Which vertical line number lays perfect on top of each other? Leftmost line is zero.'))
					wx.CallAfter(self.textEntry.SetValue, '10')
					wx.CallAfter(self.textEntry.Enable, True)
					wx.CallAfter(self.resumeButton.Enable, True)
					wx.CallAfter(self.resumeButton.SetFocus)

		elif self.comm.isError():
			wx.CallAfter(self.infoBox.SetError, _('Failed to establish connection with the printer.'), 'http://wiki.ultimaker.com/Cura:_Connection_problems')

	def mcMessage(self, message):
		pass

	def mcProgress(self, lineNr):
		pass

	def mcZChange(self, newZ):
		pass


class bedLevelWizard(wx.wizard.Wizard):
	def __init__(self):
		super(bedLevelWizard, self).__init__(None, -1, _("Bed leveling wizard"))

		self.Bind(wx.wizard.EVT_WIZARD_PAGE_CHANGED, self.OnPageChanged)
		self.Bind(wx.wizard.EVT_WIZARD_PAGE_CHANGING, self.OnPageChanging)

		self.mainPage = bedLevelWizardMain(self)
		self.headOffsetCalibration = None

		self.FitToPage(self.mainPage)
		self.GetPageAreaSizer().Add(self.mainPage)

		self.RunWizard(self.mainPage)
		self.Destroy()

	def OnPageChanging(self, e):
		e.GetPage().StoreData()

	def OnPageChanged(self, e):
		if e.GetPage().AllowNext():
			self.FindWindowById(wx.ID_FORWARD).Enable()
		else:
			self.FindWindowById(wx.ID_FORWARD).Disable()
		if e.GetPage().AllowBack():
			self.FindWindowById(wx.ID_BACKWARD).Enable()
		else:
			self.FindWindowById(wx.ID_BACKWARD).Disable()


class headOffsetWizard(wx.wizard.Wizard):
	def __init__(self):
		super(headOffsetWizard, self).__init__(None, -1, _("Head offset wizard"))

		self.Bind(wx.wizard.EVT_WIZARD_PAGE_CHANGED, self.OnPageChanged)
		self.Bind(wx.wizard.EVT_WIZARD_PAGE_CHANGING, self.OnPageChanging)

		self.mainPage = headOffsetCalibrationPage(self)

		self.FitToPage(self.mainPage)
		self.GetPageAreaSizer().Add(self.mainPage)

		self.RunWizard(self.mainPage)
		self.Destroy()

	def OnPageChanging(self, e):
		e.GetPage().StoreData()

	def OnPageChanged(self, e):
		if e.GetPage().AllowNext():
			self.FindWindowById(wx.ID_FORWARD).Enable()
		else:
			self.FindWindowById(wx.ID_FORWARD).Disable()
		if e.GetPage().AllowBack():
			self.FindWindowById(wx.ID_BACKWARD).Enable()
		else:
			self.FindWindowById(wx.ID_BACKWARD).Disable()
			

