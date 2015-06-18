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
		self.profileSettingsList = [profile.settingsList]
		self.materialProfileText = wx.TextDataObject(text=profile.getPreference("simpleModeMaterial"))
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
		
		# Panel 1, which dynamically shows the user the name of the last file loaded
		currentFilePanel = wx.Panel(self)
		self.currentFileName = wx.StaticText(currentFilePanel, -1, label = "No File Currently Open")
		
		# Panel 2 of simple mode tools that displays information about loaded filament
		materialSelectorPanel = wx.Panel(self)
		self.selectedMaterial = wx.StaticText(materialSelectorPanel, -1, label=self.materialProfileText.GetText())
		self.materialLoadButton = wx.Button(materialSelectorPanel, 4, _("Load Materials"))
		self.printSupport = wx.CheckBox(self, -1, _("Print support structure"))
		self.printSupport.SetValue(True)
		self.returnProfile = self.selectedMaterial.GetLabel()

		pub.subscribe(self.displayAndLoadMaterialData, 'settings.update')

		# Panel 3 titled "Advanced"; contains print support
		supportSelectionPanel = wx.Panel(self)
		support_raft = wx.RadioButton(supportSelectionPanel, -1, label="Raft")
		support_brim = wx.RadioButton(supportSelectionPanel, -1, label="Brim")
		support_disabled = wx.RadioButton(supportSelectionPanel, -1, label="No Support")
		support_raft.SetValue(True)
		
		sizer = wx.GridBagSizer()
		self.SetSizer(sizer)
		
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
		
		
		#The data here isn't being populated correctly
		sb = wx.StaticBox(printTypePanel, label=_("Quality"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		for button in self._print_profile_options:
			boxsizer.Add(button)
		printTypePanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		printTypePanel.GetSizer().Add(boxsizer, flag=wx.EXPAND)
		sizer.Add(printTypePanel, (2,0), flag=wx.EXPAND)
		
		sb = wx.StaticBox(supportSelectionPanel, label=_("Adhesion"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		supportSelectionPanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		boxsizer.Add(support_raft)
		boxsizer.Add(support_brim)
		boxsizer.Add(support_disabled)
		supportSelectionPanel.GetSizer().Add(boxsizer, flag=wx.EXPAND)
		sizer.Add(supportSelectionPanel, (3,0), flag=wx.EXPAND)
		
		sb = wx.StaticBox(self, label=_("Support"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		boxsizer.Add(self.printSupport)
		sizer.Add(boxsizer, (4,0), flag=wx.EXPAND)
		self.Bind(wx.EVT_BUTTON, self.OnSelectBtn, id=4)
		
	
	def OnSelectBtn(self, event):
		frame = MaterialSelectorFrame()
		frame.Show()
	
		
	def displayAndLoadMaterialData(self, mat):
		profile.putPreference('simpleModeMaterial', mat)
		mainWindow = self.GetParent().GetParent().GetParent()
		self.selectedMaterial.SetLabel(mat)
		self.materialProfileText.SetText(mat)
		self.profileSettingsList = []
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
		self.profileSettingsList = settings			
		self._callback()
		
	def displayLoadedFileName(self):
		# Displays file names as they are loaded into sceneView
		# and references them directly from that source
		mainWindow = self.GetParent().GetParent().GetParent()
		sceneView = mainWindow.scene
		filename = str(os.path.basename(sceneView.filename))
		print("Filename within displayLoadedFileName: %s" %filename)
		if self.lastOpenedFileName != filename:
			self.lastOpenedFileName = filename
			self.currentFileName.SetLabel(str(self.lastOpenedFileName))
		else:
			pass
		self._callback()

	def getSettingOverrides(self):
		self.displayLoadedFileName()
		if self.profileSettingsList is not profile.settingsList:
			return self.profileSettingsList
			
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
	
# -----------material profiles organization end-----------
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
		self.Close()
		
		
	def ReturnMaterialProfile(self):
		return self.materialProfile


	def OnBrandSelect(self, event):
		self.text.Clear()
		self.materials = []
		panel = wx.Panel(self)
		index = event.GetSelection()
		brandSelection = self.exampleListBox.GetString(index)
		
		for x, y in self.sortedMaterialsProfiles.iteritems():
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
