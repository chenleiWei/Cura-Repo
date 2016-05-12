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
from Cura.util import analytics



class MaterialProfileSelector(wx.Frame):
	def __init__(self):
		wx.Frame.__init__(self, None, wx.ID_ANY, "Materials Selection", size=(500,400), style=wx.DEFAULT_FRAME_STYLE | wx.STAY_ON_TOP)
		
		analytics.submitFeatureAnalytics('1','','','','material_selector')
		
		# boxsizer initializations 
		mainBox = wx.BoxSizer(wx.VERTICAL)
		topBox = wx.BoxSizer(wx.VERTICAL)
		middleBox = wx.BoxSizer(wx.HORIZONTAL)
		listbox_Box1 = wx.BoxSizer(wx.VERTICAL)
		listbox_Box2 = wx.BoxSizer(wx.VERTICAL)
		bottomBox = wx.BoxSizer(wx.HORIZONTAL)
		
		# panel initialization
		listBoxPanel = wx.Panel(self, -1)
		
		# dict and option list initializations 
		materialsDirectory = resources.getSimpleModeMaterialsProfiles()
		self.materialsDict = self.createMaterialDict(materialsDirectory)
		brandsList = []
		materialsList = []
		
		# sort manufacturers and materials in their own lists
		for brand, materials in self.materialsDict.items():
			brandsList.append(brand)
			for material, path in materials.items():
				materialsList.append(material)
		
		brandsList = sorted(brandsList)
		# listbox initializations
		self.brandsBox = wx.ComboBox(listBoxPanel, -1, choices=sorted(brandsList), style=wx.CB_READONLY)
		self.matsBox = wx.ComboBox(listBoxPanel, -1, size=(150,-1), choices=sorted(materialsList), style=wx.CB_READONLY)
		
		self.brandsBox.SetSelection(0)
		
		matchingMaterials = []
		
		# manufacturer/mat matching logic
		index = self.brandsBox.GetSelection()
		matIndex = self.matsBox.GetSelection()
		
		if profile.getPreference('material_supplier') is None:
			self.selectedBrand = self.brandsBox.GetString(index)
		else:
			self.selectedBrand = profile.getPreference('material_supplier')
			newIndex = self.brandsBox.FindString(self.selectedBrand)
			self.brandsBox.SetSelection(newIndex)
				
		for brand, materials in self.materialsDict.items():
			if brand == self.selectedBrand:
				for material, path in materials.items():
					matchingMaterials.append(material)
					
		self.matsBox.Clear()

		for n in range(0, len(matchingMaterials)):
			self.matsBox.Append(matchingMaterials[n])

		self.matsBox.SetSelection(0)
		self.selectedMaterial = self.matsBox.GetString(0)
		
		if profile.getPreference('material_name') is None:
			self.selectedMaterial = self.matsBox.GetString(0)
		else:
			self.selectedMaterial = profile.getPreference('material_name')
			newIndex = self.matsBox.FindString(self.selectedMaterial)
			self.matsBox.SetSelection(newIndex)
			
		font = wx.Font(15, family=wx.SWISS, style=wx.NORMAL, weight=wx.NORMAL)
		
		# brand/title labels
		brandsLabel = wx.StaticText(listBoxPanel, -1, "Manufacturer")
		brandsLabel.SetFont(font)
		materialLabel = wx.StaticText(listBoxPanel, -1, "Material")
		materialLabel.SetFont(font)
		
		# select button
		self.selectButton = wx.Button(listBoxPanel, -1, 'Select')
		
		# load topBox
		logoPath = resources.getPathForImage('CuraTAMIcon.png')
		logoBitmap = wx.Bitmap(logoPath)
		logoBitmap.SetHeight(125)
		logoBitmap.SetWidth(125)
		logo = wx.StaticBitmap(listBoxPanel, -1, logoBitmap)
		titleText = wx.StaticText(listBoxPanel, -1, "Material Profile Selector")
		font = wx.Font(20, family=wx.SWISS, style=wx.NORMAL, weight=wx.NORMAL)
		titleText.SetFont(font)
		
		topBox.Add(logo, flag= wx.ALIGN_CENTER| wx.TOP, border=20)
		topBox.Add(titleText, flag=wx.BOTTOM | wx.TOP, border=10)

		
		# load listbox_Box1 with labels
		listbox_Box1.Add(brandsLabel, flag=wx.ALIGN_RIGHT)
		listbox_Box1.Add(materialLabel, flag=wx.TOP | wx.ALIGN_RIGHT, border=15)
		
		# load listBox2
		listbox_Box2.Add(self.brandsBox)
		listbox_Box2.Add(self.matsBox, flag=wx.TOP, border=10)
		
		# load bottomBox with 'Select' button
		bottomBox.Add(self.selectButton, flag=wx.ALIGN_CENTER)

		# load mainBox with all loaded boxsizers
		mainBox.Add(topBox, flag=wx.ALIGN_CENTER)
		middleBox.Add(listbox_Box1, flag=wx.LEFT)
		middleBox.Add(listbox_Box2, flag=wx.LEFT, border=10)
		mainBox.Add(middleBox, flag=wx.ALIGN_CENTER | wx.TOP, border=20)
		mainBox.Add(bottomBox, flag=wx.ALIGN_CENTER | wx.TOP, border=50)
		listBoxPanel.SetSizer(mainBox)
		
		# bindings
		self.brandsBox.Bind(wx.EVT_COMBOBOX, self.brandSelected)
		self.matsBox.Bind(wx.EVT_COMBOBOX, self.materialSelected)
		self.selectButton.Bind(wx.EVT_BUTTON, self.closeWindow)
	
	def closeWindow(self, e):
		wx.CallAfter(self.relayEvent)
		
		self.Destroy()

	def relayEvent(self):
		if self.selectedBrand and self.selectedMaterial is not None:
			self.chosenProfilePath = self.materialsDict.setdefault(self.selectedBrand, self.selectedMaterial)[self.selectedMaterial]
			try:
				pub.sendMessage('matProf.update', path=self.chosenProfilePath)
			except Exception as e:
				print "ERROR: ", e

	# each profile is formated as:	manufacturer__material__base_polymer
	def createMaterialDict(self, files):
		data = []
		materialsDict = {}
		for file in files:
			cp = configparser.ConfigParser()
			cp.read(file)
			if cp.has_section('info'):
				name = cp.get('info', 'name')
				manufacturer = cp.get('info', 'manufacturer')
				data.append((name, manufacturer, file))
		for name, manufacturer, path in data:
			materialsDict.setdefault(manufacturer, {})[name] = path
				
		return materialsDict

	def OnEnable(self, enable):
		self.selectButton.Enable(enable)

	def brandSelected(self, event):
		selectedBrand = event.GetString()
		self.selectedBrand = selectedBrand
		newMatsList = []
		
		# finds materials associated with the selected brand and adds them to newMatsList
		for brand, materials, in self.materialsDict.items():
			if brand == selectedBrand: 
				for material, path in materials.items():
					newMatsList.append(material)

		# when a brand is selected, the materials listbox is updated to reflect materials under
		# the selected brand
		self.matsBox.Clear()

		if len(newMatsList) > 0:
			sortedMatsList = sorted(newMatsList)
			for n in range(0, len(sortedMatsList)):
				self.matsBox.Append(sortedMatsList[n])

		self.matsBox.SetSelection(0)
		index = self.matsBox.GetSelection()
		self.selectedMaterial = self.matsBox.GetString(index)

	def materialSelected(self, event):
		selectedMaterial = event.GetString()
		self.selectedMaterial = selectedMaterial
