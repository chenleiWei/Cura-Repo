__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"
#encode UTF-8
import wx
import wx.animate
import numpy
import time
import os
import webbrowser
import traceback
import threading
import math
import cStringIO as StringIO
import OpenGL
import sys
OpenGL.ERROR_CHECKING = False
from OpenGL.GLUT import *
from OpenGL.GLU import *
from OpenGL.GLE import *
from OpenGL.GL import *

import ConfigParser as configparser

try:
    from io import BytesIO
except ImportError:
    from StringIO import StringIO as BytesIO
    
try: 
	from wx.lib.pubsub import pub
except ImportError:
	from wx.lib.pubsub import Publisher as pub

from Cura.gui import printWindow
from Cura.util import printerConnect
from Cura.util import profile
from Cura.util import meshLoader
from Cura.util import objectScene
from Cura.util import resources
from Cura.util import sliceEngine
from Cura.util import pluginInfo
from Cura.util import removableStorage
from Cura.util import explorer
from Cura.util.printerConnection import printerConnectionManager
from Cura.gui.util import previewTools
from Cura.gui.util import openglHelpers
from Cura.gui.util import openglGui
from Cura.gui.util import engineResultView
from Cura.gui.tools import imageToMesh
from Cura.util import analytics


class SceneView(openglGui.glGuiPanel):
	def __init__(self, parent):
		super(SceneView, self).__init__(parent)
		self._yaw = 30
		self._pitch = 60
		self._zoom = 800
		self._scene = objectScene.Scene(self)
		self._objectShader = None
		self._objectLoadShader = None
		self._focusObj = None
		self._selectedObj = None
		self._objColors = [None,None,None,None]
		self._mouseX = -1
		self._mouseY = -1
		self._mouseState = None
		self._viewTarget = numpy.array([0,0,0], numpy.float32)
		self._animView = None
		self._animZoom = None
		self._lastObjectSink = None
		self._platformMesh = {}
		self._platformTexture = None
		self._isSimpleMode = True

		self.layerSelect = openglGui.glSlider(self, 1, 1, 305, (-1,-2), lambda : self.QueueRefresh())
		self.layerSelectCondition = False
		
		self._printerConnectionManager = printerConnectionManager.PrinterConnectionManager()
		
		self.printGcode = "false"
		self.openBrowser = False
		self.gcodePath = None
		pub.subscribe(self.SendToPrinter, 'gcode.update')
		pub.subscribe(self.PrintUponUpload, 'print.gcode')
		pub.subscribe(self.UploadButtonStatus, 'upload.enabled')
		pub.subscribe(self.browserOpenOption, 'browser.open')

		self._viewport = None
		self._modelMatrix = None
		self._projMatrix = None
		self.tempMatrix = None

		self.openFileButton        = openglGui.glButton(self, 4, _("Load"), (0,0), self.showLoadModel)
		self.printButton           = openglGui.glButton(self, 6, _("Print"), (1,0), self.OnPrintButton)
		self.octoPrintButton	   = openglGui.glButton(self, 6, _("Send to Series 1"), (2,0), self.OnOctoPrintButton)
		self.printButton.setDisabled(True)
		self.win = middleMan

		group = []
		self.rotateToolButton = openglGui.glRadioButton(self, 8, _("Rotate"), (0,-1), group, self.OnToolSelect)
		self.scaleToolButton  = openglGui.glRadioButton(self, 9, _("Scale"), (1,-1), group, self.OnToolSelect)
		self.mirrorToolButton  = openglGui.glRadioButton(self, 10, _("Mirror"), (2,-1), group, self.OnToolSelect)

		self.resetRotationButton = openglGui.glButton(self, 12, _("Reset"), (0,-2), self.OnRotateReset)
		self.layFlatButton       = openglGui.glButton(self, 16, _("Lay flat"), (0,-3), self.OnLayFlat)

		self.resetScaleButton    = openglGui.glButton(self, 13, _("Reset"), (1,-2), self.OnScaleReset)
		self.scaleMaxButton      = openglGui.glButton(self, 17, _("To max"), (1,-3), self.OnScaleMax)

		self.mirrorXButton       = openglGui.glButton(self, 14, _("Mirror X"), (2,-2), lambda button: self.OnMirror(0))
		self.mirrorYButton       = openglGui.glButton(self, 18, _("Mirror Y"), (2,-3), lambda button: self.OnMirror(1))
		self.mirrorZButton       = openglGui.glButton(self, 22, _("Mirror Z"), (2,-4), lambda button: self.OnMirror(2))

		self.filename = None
			
		self.rotateToolButton.setExpandArrow(True)
		self.scaleToolButton.setExpandArrow(True)
		self.mirrorToolButton.setExpandArrow(True)

		self.scaleForm = openglGui.glFrame(self, (2, -2))
		openglGui.glGuiLayoutGrid(self.scaleForm)
		openglGui.glLabel(self.scaleForm, _("Scale X"), (0,0))
		self.scaleXctrl = openglGui.glNumberCtrl(self.scaleForm, '1.0', (1,0), lambda value: self.OnScaleEntry(value, 0))
		openglGui.glLabel(self.scaleForm, _("Scale Y"), (0,1))
		self.scaleYctrl = openglGui.glNumberCtrl(self.scaleForm, '1.0', (1,1), lambda value: self.OnScaleEntry(value, 1))
		openglGui.glLabel(self.scaleForm, _("Scale Z"), (0,2))
		self.scaleZctrl = openglGui.glNumberCtrl(self.scaleForm, '1.0', (1,2), lambda value: self.OnScaleEntry(value, 2))
		openglGui.glLabel(self.scaleForm, _("Size X (mm)"), (0,4))
		self.scaleXmmctrl = openglGui.glNumberCtrl(self.scaleForm, '0.0', (1,4), lambda value: self.OnScaleEntryMM(value, 0))
		openglGui.glLabel(self.scaleForm, _("Size Y (mm)"), (0,5))
		self.scaleYmmctrl = openglGui.glNumberCtrl(self.scaleForm, '0.0', (1,5), lambda value: self.OnScaleEntryMM(value, 1))
		openglGui.glLabel(self.scaleForm, _("Size Z (mm)"), (0,6))
		self.scaleZmmctrl = openglGui.glNumberCtrl(self.scaleForm, '0.0', (1,6), lambda value: self.OnScaleEntryMM(value, 2))
		openglGui.glLabel(self.scaleForm, _("Uniform scale"), (0,8))
		self.scaleUniform = openglGui.glCheckbox(self.scaleForm, True, (1,8), None)

		self.viewSelection = openglGui.glComboButton(self, _("View mode"), [7,19,11,15,23], [_("Normal"), _("Overhang"), _("Transparent"), _("X-Ray"), _("Layers")], (-1,0), self.OnViewChange)

		self.infillGridButton = openglGui.glButton(self, 2, _("Infill"), (-1,-1), self.OninfillGridButton)
		
		if profile.getProfileSetting('infill_type') == 'Line' or profile.getProfileSetting('infill_type') == 'Grid':
			self.infillGridButton.setHidden(False)
		else:
			self.infillGridButton.setHidden(True)

		self.notification = openglGui.glNotification(self, (0, 0))

		self._engine = sliceEngine.Engine(self._updateEngineProgress)
		self._engineResultView = engineResultView.engineResultView(self)
		self._sceneUpdateTimer = wx.Timer(self)
		self.Bind(wx.EVT_TIMER, self._onRunEngine, self._sceneUpdateTimer)
		self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
		self.Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseLeave)

		self.OnViewChange()
		self.OnToolSelect(0)
		self.updateToolButtons()
		self.updateProfileToControls()

	def PrintUponUpload(self, printGcode):
		if printGcode == "true":
			self.printGcode = "true"
		else:
			self.printGcode = "false"
		
	def browserOpenOption(self, openBrowser):
		self.openBrowser = openBrowser
#		if b == True:
#			self.openOctoPrintInBrowser = True
#		else:
#			self.openOctoPrintInBrowser = False
		
	def UploadButtonStatus(self, enable):
		print "Upload Enabled event caller activated."
		print enable
		pub.sendMessage('transfer.response', enable=enable)
		pub.sendMessage('enable.upload', enable=enable)
		
	def loadGCodeFile(self, filename):
		self.OnDeleteAll(None)
		#Cheat the engine results to load a GCode file into it.
		self._engine._result = sliceEngine.EngineResult()
		with open(filename, "r") as f:
			self._engine._result.setGCode(f.read())
		self._engine._result.setFinished(True)
		self._engineResultView.setResult(self._engine._result)
		self.printButton.setBottomText('')
		self.viewSelection.setValue(4)
		self.printButton.setDisabled(False)
		pub.sendMessage('upload.enabled', enable=True)
		self.OnViewChange()
		self.gcodePath = filename

	def loadSceneFiles(self, filenames):
		#if self.viewSelection.getValue() == 4:
		#	self.viewSelection.setValue(0)
		#	self.OnViewChange()
		return self.loadScene(filenames)

	def loadFiles(self, filenames):
		mainWindow = self.GetParent().GetParent().GetParent()
		# only one GCODE file can be active
		# so if single gcode file, process this
		# otherwise ignore all gcode files
		gcodeFilename = None
		if len(filenames) == 1:
			filename = filenames[0]
			ext = os.path.splitext(filename)[1].lower()
			if ext == '.g' or ext == '.gcode':
				gcodeFilename = filename
				mainWindow.addToModelMRU(filename)
		if gcodeFilename is not None:
			self.loadGCodeFile(gcodeFilename)
		else:
			# process directories and special file types
			# and keep scene files for later processing
			scene_filenames = []
			ignored_types = dict()
			# use file list as queue
			# pop first entry for processing and append new files at end
			while filenames:
				filename = filenames.pop(0)
				self.filename = filename
				profile.putPreference('lastFile', str(filename))
				if os.path.isdir(filename):
					# directory: queue all included files and directories
					filenames.extend(os.path.join(filename, f) for f in os.listdir(filename))
				else:
					ext = os.path.splitext(filename)[1].lower()
					if ext == '.ini':
						profile.loadProfile(filename)
						mainWindow.addToProfileMRU(filename)
					elif ext in meshLoader.loadSupportedExtensions() or ext in imageToMesh.supportedExtensions():
						scene_filenames.append(filename)
						mainWindow.addToModelMRU(filename)
					else:
						ignored_types[ext] = 1
			if ignored_types:
				ignored_types = ignored_types.keys()
				ignored_types.sort()
				self.notification.message("ignored: " + " ".join("*" + type for type in ignored_types))
			mainWindow.updateProfileToAllControls()
			# now process all the scene files
			if scene_filenames:
				objs = self.loadSceneFiles(scene_filenames)
				if len(objs) > 0:
					self._selectObject(objs[-1])
				else:
					self._selectObject(None)
				self.sceneUpdated()
				newZoom = numpy.max(self._machineSize)
				self._animView = openglGui.animation(self, self._viewTarget.copy(), numpy.array([0,0,0], numpy.float32), 0.5)
				self._animZoom = openglGui.animation(self, self._zoom, newZoom, 0.5)

	def reloadScene(self, e):
		# Copy the list before DeleteAll clears it
		fileList = []
		pms_transforms = [] #position, rotation matrix, scale
		for obj in self._scene.objects():
			fileList.append(obj.getOriginFilename())
			pms_transforms.append((obj.getPosition(), obj.getMatrix(), obj.getScale()))

		self.OnDeleteAll(None)
		self.loadScene(fileList, pms_transforms)
		self.sceneUpdated()

	def OnResetPositions(self, e):

		self._scene.arrangeAll(True)
		self._scene.centerAll()
		self.sceneUpdated()

	def OnResetTransformations(self, e):
		for obj in self._scene.objects():
			obj.resetScale()
			obj.resetRotation()

		self._scene.arrangeAll()
		self._scene.centerAll()
		self.sceneUpdated()

	def showLoadModel(self, button = 1):
		if button == 1:
			dlg=wx.FileDialog(self, _("Open 3D model"), os.path.split(profile.getPreference('lastFile'))[0], style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST|wx.FD_MULTIPLE)

			wildcardList = ';'.join(map(lambda s: '*' + s, meshLoader.loadSupportedExtensions() + imageToMesh.supportedExtensions() + ['.g', '.gcode']))
			wildcardFilter = "All (%s)|%s;%s" % (wildcardList, wildcardList, wildcardList.upper())
			wildcardList = ';'.join(map(lambda s: '*' + s, meshLoader.loadSupportedExtensions()))
			wildcardFilter += "|Mesh files (%s)|%s;%s" % (wildcardList, wildcardList, wildcardList.upper())
			wildcardList = ';'.join(map(lambda s: '*' + s, imageToMesh.supportedExtensions()))
			wildcardFilter += "|Image files (%s)|%s;%s" % (wildcardList, wildcardList, wildcardList.upper())
			wildcardList = ';'.join(map(lambda s: '*' + s, ['.g', '.gcode']))
			wildcardFilter += "|GCode files (%s)|%s;%s" % (wildcardList, wildcardList, wildcardList.upper())

			dlg.SetWildcard(wildcardFilter)
			if dlg.ShowModal() != wx.ID_OK:
				dlg.Destroy()
				return
			filenames = dlg.GetPaths()
			dlg.Destroy()
			if len(filenames) < 1:
				return False
			profile.putPreference('lastFile', filenames[0])
			self.loadFiles(filenames)

	def showSaveModel(self):
		if len(self._scene.objects()) < 1:
			return

		firstPrintPath = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'resources', 'example'))
		lastFilePath = os.path.dirname(os.path.abspath(profile.getPreference('lastFile')))
		homeDirectory = os.path.expanduser('~')
		documentsDirectory =  os.path.join(homeDirectory, 'Documents')

		docsDirectoryExists = os.path.isdir(documentsDirectory)

		if docsDirectoryExists == True:	
			initialSavePath = documentsDirectory
		else:
			initialSavePath = homeDirectory
				
		# Don't save to Cura example directory path
		if (lastFilePath == firstPrintPath):
			dlg = wx.FileDialog(self, _("Save as AMF"), os.path.dirname(initialSavePath), style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
		else:
			dlg = wx.FileDialog(self, _("Save as AMF"), lastFilePath, style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)

		fileExtensions = meshLoader.saveSupportedExtensions()
		wildcardList = ';'.join(map(lambda s: '*' + s, fileExtensions))
		wildcardFilter = "Mesh files (%s)|%s;%s" % (wildcardList, wildcardList, wildcardList.upper())
		dlg.SetWildcard(wildcardFilter)
		if dlg.ShowModal() != wx.ID_OK:
			dlg.Destroy()
			return
		filename = dlg.GetPath()
		dlg.Destroy()
		meshLoader.saveMeshes(filename, self._scene.objects())

	def OnOctoPrintButton(self, callback):
		try: 
			infoTransfer = middleMan(self.printButton)
			infoTransfer.OpenPrinterSelector()
			filenames = []
			for count in range(0, len(self._scene._objectList)):
				filenames.append(self._scene._objectList[count].getName())
			pub.sendMessage('file.isopen', filenames=filenames)
		except Exception as e:
			raise e

	def SendToPrinter(self, serial):
		import re
		#Temporary file handling
		resourceBasePath = resources.resourceBasePath
		file = self._scene._objectList[0].getName()
		# Make a directory called 'temp' in ./resources
		resourceBasePath = resources.resourceBasePath
		suffix = '.gcode'
		filename = file + suffix
		# Path to temporary file
		key = profile.OctoPrintConfigAPI(serial)
		tempFilePath = os.path.join(profile.getBasePath(), '.temp', filename)
		self._createTempFiles(tempFilePath)
		self._uploadToOctoPrint(key, serial, tempFilePath)
		
	def _createTempFiles(self, gcodeFile):
		# gets gcode from the engine
		gcode = self._engine.getResult().getGCode()
		try:
			size = float(len(gcode))
			read_pos = 0
			# writes gcode to targetFileName
			with open(gcodeFile, 'wb+') as fdst:
				while 1:
					buf = gcode.read(16*1024)
					if len(buf) < 1:
						break
					read_pos += len(buf)
					fdst.write(buf)
					
					self._queueRefresh()
		except:
			import sys, traceback
			traceback.print_exc()
			self.notification.message("Failed to save")
		
		if explorer.hasExplorer():
			self.notification.message("Saved as %s" % (gcodeFile), lambda : explorer.openExplorer(gcodeFile), 4, 'Open folder')
		else:
			self.notification.message("Saved as %s" % (gcodeFile))
		
	def _uploadToOctoPrint(self, key, serial, tempFilePath):
		# Notify the user that the file is attempting to be uploaded
		self.notification.message("Uploading....")
		

		upload = printerConnect.GcodeUpload(key, serial, tempFilePath, self.openBrowser, self.notification, self.printGcode)
		upload.start()
#		if self.openOctoPrintInBrowser == True:
#			self.openOctoPrintInBrowser = False
		
					
	def OnPrintButton(self, button):
		mainWindow = self.GetParent().GetParent().GetParent()
		
		if button == 1:
			connectionGroup = self._printerConnectionManager.getAvailableGroup()
			"""
			if len(removableStorage.getPossibleSDcardDrives()) > 0 and (connectionGroup is None or connectionGroup.getPriority() < 0):
				drives = removableStorage.getPossibleSDcardDrives() 
				if len(drives) > 1:
					dlg = wx.SingleChoiceDialog(self, "Select SD drive", "Multiple removable drives have been found,\nplease select your SD card drive", map(lambda n: n[0], drives))
					if dlg.ShowModal() != wx.ID_OK:
						dlg.Destroy()
						return
					drive = drives[dlg.GetSelection()]
					dlg.Destroy()
				else:
					drive = drives[0]
				filename = self._scene._objectList[0].getName() + profile.getGCodeExtension()
				
				#check if the file is part of the root folder. If so, create folders on sd card to get the same folder hierarchy.
				repDir = profile.getPreference("sdcard_rootfolder")
				try:
					if os.path.exists(repDir) and os.path.isdir(repDir):
						repDir = os.path.abspath(repDir)
						originFilename = os.path.abspath( self._scene._objectList[0].getOriginFilename() )
						if os.path.dirname(originFilename).startswith(repDir):
							new_filename = os.path.splitext(originFilename[len(repDir):])[0] + profile.getGCodeExtension()
							sdPath = os.path.dirname(os.path.join(drive[1], new_filename))
							if not os.path.exists(sdPath):
								print "Creating replication directory:", sdPath
								os.makedirs(sdPath)
							filename = new_filename
				except:
					pass

				threading.Thread(target=self._saveGCode,args=(drive[1] + filename, drive[1])).start()
			elif connectionGroup is not None:
				connections = connectionGroup.getAvailableConnections()
				if len(connections) < 2:
					connection = connections[0]
				else:
					dlg = wx.SingleChoiceDialog(self, "Select the %s connection to use" % (connectionGroup.getName()), "Multiple %s connections found" % (connectionGroup.getName()), map(lambda n: n.getName(), connections))
					if dlg.ShowModal() != wx.ID_OK:
						dlg.Destroy()
						return
					connection = connections[dlg.GetSelection()]
					dlg.Destroy()
				self._openPrintWindowForConnection(connection)
			else:
			"""
			self.showSaveGCode()
		if button == 3:
			directUpload = mainWindow.OnDirectUploadSettings(True)

			menu = wx.Menu()
			connections = self._printerConnectionManager.getAvailableConnections()
			menu.connectionMap = {}
			"""
			for connection in connections:
				i = menu.Append(-1, _("Print with %s") % (connection.getName()))
				menu.connectionMap[i.GetId()] = connection
				self.Bind(wx.EVT_MENU, lambda e: self._openPrintWindowForConnection(e.GetEventObject().connectionMap[e.GetId()]), i)
			"""
			self.Bind(wx.EVT_MENU, lambda e: self.showSaveGCode(), menu.Append(-1, _("Save GCode...")))
			self.Bind(wx.EVT_MENU, lambda e: self._showEngineLog(), menu.Append(-1, _("Slice engine log...")))
			self.PopupMenu(menu)
			menu.Destroy()

	def _openPrintWindowForConnection(self, connection):
		if connection.window is None or not connection.window:
			connection.window = None
			windowType = profile.getPreference('printing_window')
			for p in pluginInfo.getPluginList('printwindow'):
				if p.getName() == windowType:
					connection.window = printWindow.printWindowPlugin(self, connection, p.getFullFilename())
					break
			if connection.window is None:
				connection.window = printWindow.printWindowBasic(self, connection)
		connection.window.Show()
		connection.window.Raise()
		if not connection.loadGCodeData(self._engine.getResult().getGCode()):
			if connection.isPrinting():
				self.notification.message("Cannot start print, because other print still running.")
			else:
				self.notification.message("Failed to start print...")

	def showSaveGCode(self):
		if len(self._scene._objectList) < 1:
			self.printButton.setDisabled(True)
			return
		if not self._engine.getResult().isFinished():
			return
		
		firstPrintPath = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'resources', 'example'))
		lastFilePath = os.path.dirname(os.path.abspath(profile.getPreference('lastFile')))
		homeDirectory = os.path.expanduser('~')
		documentsDirectory =  os.path.join(homeDirectory, 'Documents')
		docsDirectoryExists = os.path.isdir(documentsDirectory)
		
		if docsDirectoryExists == True:	
			initialSavePath = documentsDirectory
		else:
			initialSavePath = homeDirectory
				
		# Don't save to Cura example directory path
		if (lastFilePath == firstPrintPath):
			dlg = wx.FileDialog(self, _("Save GCode"), os.path.dirname(initialSavePath), style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
		else:
			dlg = wx.FileDialog(self, _("Save GCode"), lastFilePath, style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)

		filename = self._scene._objectList[0].getName() + profile.getGCodeExtension()
		dlg.SetFilename(filename)
		dlg.SetWildcard('Toolpath (*%s)|*%s;*%s' % (profile.getGCodeExtension(), profile.getGCodeExtension(), profile.getGCodeExtension()[0:2]))
		if dlg.ShowModal() != wx.ID_OK:
			dlg.Destroy()
			return
		filename = dlg.GetPath()
		
		profile.putPreference('lastFile', filename)
		dlg.Destroy()

		threading.Thread(target=self._saveGCode,args=(filename,)).start()

	def _saveGCode(self, targetFilename, ejectDrive = False):
		# gets gcode from the engine
		gcode = self._engine.getResult().getGCode()
		try:
			size = float(len(gcode))
			read_pos = 0
			# writes gcode to targetFileName
			with open(targetFilename, 'wb') as fdst:
				while 1:
					buf = gcode.read(16*1024)
					if len(buf) < 1:
						break
					read_pos += len(buf)
					fdst.write(buf)
					self.printButton.setProgressBar(read_pos / size)
					self._queueRefresh()
			pub.sendMessage('upload.enabled', enable=True)
		except:
			import sys, traceback
			traceback.print_exc()
			self.notification.message("Failed to save")
			pub.sendMessage('upload.enabled', enable=False)
			print "Upload button disabled. Failed to save."
		else:
			if ejectDrive:
				self.notification.message("Saved as %s" % (targetFilename), lambda : self._doEjectSD(ejectDrive), 31, 'Eject')
			elif explorer.hasExplorer():
				self.notification.message("Saved as %s" % (targetFilename), lambda : explorer.openExplorer(targetFilename), 4, 'Open folder')
			else:
				self.notification.message("Saved as %s" % (targetFilename))
		t = threading.Timer(2, self.closeNotification)
		t.start()
		self.printButton.setProgressBar(None)
		self._engine.getResult().submitInfoOnline()


	def closeNotification(self):
			self.notification.onClose(True)
		
	def _saveGCodeTemp(self, tempFilePath, ejectDrive = False):
		# gets gcode from the engine
		gcode = self._engine.getResult().getGCode()
	#	fd = tempfile.NamedTemporaryFile(suffix='.gcode', prefix=filename, dir=tempD)
		try:
			size = float(len(gcode))
			read_pos = 0
			with open(tempFilePath, 'w+b') as fdst:
				print("FDST name: %s" % fdst.name)
				while 1:
					buf = gcode.read(16*1024)
					if len(buf) < 1:
						break
					read_pos += len(buf)
					fdst.write(buf)
					self.printButton.setProgressBar(read_pos / size)
					self._queueRefresh()
			pub.sendMessage('upload.enabled', enable=True)
		except:
			import sys, traceback
			traceback.print_exc()
			self.notification.message("Failed to save")
			pub.sendMessage('upload.enabled', enable=False)

		# Clear progress bar
		self.printButton.setProgressBar(None)
		
	def _saveToDocuments(self):
		targetFilename = profile._getMyDocumentsFolder() + "CuraGCode"
		self._saveGCode(targetFilename)
	
	def _doEjectSD(self, drive):
		if removableStorage.ejectDrive(drive):
			self.notification.message('You can now eject the card.')
		else:
			self.notification.message('Safe remove failed...')

	def _showEngineLog(self):
		dlg = wx.TextEntryDialog(self, _("The slicing engine reported the following"), _("Engine log..."), '\n'.join(self._engine.getResult().getLog()), wx.TE_MULTILINE | wx.OK | wx.CENTRE)
		dlg.ShowModal()
		dlg.Destroy()

	def OnToolSelect(self, button):
		if self.rotateToolButton.getSelected():
			self.tool = previewTools.toolRotate(self)
		elif self.scaleToolButton.getSelected():
			self.tool = previewTools.toolScale(self)
		elif self.mirrorToolButton.getSelected():
			self.tool = previewTools.toolNone(self)
		else:
			self.tool = previewTools.toolNone(self)
		self.resetRotationButton.setHidden(not self.rotateToolButton.getSelected())
		self.layFlatButton.setHidden(not self.rotateToolButton.getSelected())
		self.resetScaleButton.setHidden(not self.scaleToolButton.getSelected())
		self.scaleMaxButton.setHidden(not self.scaleToolButton.getSelected())
		self.scaleForm.setHidden(not self.scaleToolButton.getSelected())
		self.mirrorXButton.setHidden(not self.mirrorToolButton.getSelected())
		self.mirrorYButton.setHidden(not self.mirrorToolButton.getSelected())
		self.mirrorZButton.setHidden(not self.mirrorToolButton.getSelected())

	def updateToolButtons(self):
		if self._selectedObj is None:
			hidden = True
		else:
			hidden = False
		self.rotateToolButton.setHidden(hidden)
		self.scaleToolButton.setHidden(hidden)
		self.mirrorToolButton.setHidden(hidden)
		if hidden:
			self.rotateToolButton.setSelected(False)
			self.scaleToolButton.setSelected(False)
			self.mirrorToolButton.setSelected(False)
			self.OnToolSelect(0)

	def OnViewChange(self):
		if self.viewSelection.getValue() == 4:
			self.viewMode = 'gcode'
			self.tool = previewTools.toolNone(self)
		elif self.viewSelection.getValue() == 1:
			self.viewMode = 'overhang'
		elif self.viewSelection.getValue() == 2:
			self.viewMode = 'transparent'
		elif self.viewSelection.getValue() == 3:
			self.viewMode = 'xray'
		else:
			self.viewMode = 'normal'
		self._engineResultView.setEnabled(self.viewMode == 'gcode')
		self.QueueRefresh()

	def OnRotateReset(self, button):
		if self._selectedObj is None:
			return
		self._selectedObj.resetRotation()
		self._scene.pushFree(self._selectedObj)
		self._selectObject(self._selectedObj)
		self.sceneUpdated()

	def OnLayFlat(self, button):
		if self._selectedObj is None:
			return
		self._selectedObj.layFlat()
		self._scene.pushFree(self._selectedObj)
		self._selectObject(self._selectedObj)
		self.sceneUpdated()

	def OnScaleReset(self, button):
		if self._selectedObj is None:
			return
		self._selectedObj.resetScale()
		self._selectObject(self._selectedObj)
		self.updateProfileToControls()
		self.sceneUpdated()

	def OnScaleMax(self, button):
		if self._selectedObj is None:
			return
		machine = profile.getMachineSetting('machine_type')
		self._selectedObj.setPosition(numpy.array([0.0, 0.0]))
		self._scene.pushFree(self._selectedObj)
		#self.sceneUpdated()
		if machine == "ultimaker2":
			#This is bad and Jaime should feel bad!
			self._selectedObj.setPosition(numpy.array([0.0,-10.0]))
			self._selectedObj.scaleUpTo(self._machineSize - numpy.array(profile.calculateObjectSizeOffsets() + [0.0], numpy.float32) * 2 - numpy.array([3,3,3], numpy.float32))
			self._selectedObj.setPosition(numpy.array([0.0,0.0]))
			self._scene.pushFree(self._selectedObj)
		else:
			self._selectedObj.setPosition(numpy.array([0.0, 0.0]))
			self._scene.pushFree(self._selectedObj)
			self._selectedObj.scaleUpTo(self._machineSize - numpy.array(profile.calculateObjectSizeOffsets() + [0.0], numpy.float32) * 2 - numpy.array([3,3,3], numpy.float32))
		self._scene.pushFree(self._selectedObj)
		self._selectObject(self._selectedObj)
		self.updateProfileToControls()
		self.sceneUpdated()

	def OnMirror(self, axis):
		if self._selectedObj is None:
			return
		self._selectedObj.mirror(axis)
		self.sceneUpdated()

	def OninfillGridButton(self, button = 4):
		if profile.getPreference('show_infill') == 'True':
			profile.putPreference('show_infill',False)
		else:
			profile.putPreference('show_infill',True)

	def OnScaleEntry(self, value, axis):
		if self._selectedObj is None:
			return
		try:
			value = float(value)
		except:
			return
		self._selectedObj.setScale(value, axis, self.scaleUniform.getValue())
		self.updateProfileToControls()
		self._scene.pushFree(self._selectedObj)
		self._selectObject(self._selectedObj)
		self.sceneUpdated()

	def OnScaleEntryMM(self, value, axis):
		if self._selectedObj is None:
			return
		try:
			value = float(value)
		except:
			return
		self._selectedObj.setSize(value, axis, self.scaleUniform.getValue())
		self.updateProfileToControls()
		self._scene.pushFree(self._selectedObj)
		self._selectObject(self._selectedObj)
		self.sceneUpdated()

	def OnDeleteAll(self, e):
		while len(self._scene.objects()) > 0:
			self._deleteObject(self._scene.objects()[0])
		self._animView = openglGui.animation(self, self._viewTarget.copy(), numpy.array([0,0,0], numpy.float32), 0.5)
		self._engineResultView.setResult(None)

	def OnMultiply(self, e):
		if self._focusObj is None:
			return
		obj = self._focusObj
		dlg = wx.NumberEntryDialog(self, _("How many copies do you want?"), _("Number of copies"), _("Multiply"), 1, 1, 100)
		if dlg.ShowModal() != wx.ID_OK:
			dlg.Destroy()
			return
		cnt = dlg.GetValue()
		dlg.Destroy()

		# 0:unrequested arrange all. Objects should not move.
		# 1:requested arrange all but refused.
		# 2:arrange all and center from now on.
		requestedArrangeAll = 0

		n = 0
		while True:
			n += 1
			newObj = obj.copy()
			self._scene.add(newObj)
			if requestedArrangeAll == 2:
				self._scene.centerAll()

			if not self._scene.checkPlatform(newObj):
				if requestedArrangeAll == 0:
					requestedArrangeAll = 1
					dlg = wx.MessageDialog(self, _("Cannot fit all the requested duplicates. Do you want to try and reset object positions?"), _("Reset Positions"), wx.YES_NO)

					if dlg.ShowModal() == wx.ID_YES:
						dlg.Destroy()
						requestedArrangeAll = 2
						self._scene.remove(newObj)
						self.OnResetPositions(None)
						n -= 1
						continue

					dlg.Destroy()

				break
			if n > cnt:
				break
		if n <= cnt:
			self.notification.message("Could not create more than %d items" % (n - 1))
		self._scene.remove(newObj)
		if requestedArrangeAll == 2:
			self._scene.centerAll()

		self.sceneUpdated()

	def OnSplitObject(self, e):
		if self._focusObj is None:
			return
		self._scene.remove(self._focusObj)
		for obj in self._focusObj.split(self._splitCallback):
			if numpy.max(obj.getSize()) > 2.0:
				self._scene.add(obj)
		self._scene.centerAll()
		self._selectObject(None)
		self.sceneUpdated()

	def OnCenter(self, e):
		if self._focusObj is None:
			return
		self._focusObj.setPosition(numpy.array([0.0, 0.0]))
		self._scene.pushFree(self._selectedObj)
		newViewPos = numpy.array([self._focusObj.getPosition()[0], self._focusObj.getPosition()[1], self._focusObj.getSize()[2] / 2])
		self._animView = openglGui.animation(self, self._viewTarget.copy(), newViewPos, 0.5)
		self.sceneUpdated()

	def _splitCallback(self, progress):
		print progress

	def OnMergeObjects(self, e):
		if self._selectedObj is None or self._focusObj is None or self._selectedObj == self._focusObj:
			if len(self._scene.objects()) == 2:
				self._scene.merge(self._scene.objects()[0], self._scene.objects()[1])
				self.sceneUpdated()
			return
		self._scene.merge(self._selectedObj, self._focusObj)
		self.sceneUpdated()

	def sceneUpdated(self):
		if profile.getProfileSetting('infill_type') == 'Line' or profile.getProfileSetting('infill_type') == 'Grid':
			self.infillGridButton.setHidden(False)
		else:
			self.infillGridButton.setHidden(True)

		objectSink = profile.getProfileSettingFloat("object_sink")
		if self._lastObjectSink != objectSink:
			self._lastObjectSink = objectSink
			self._scene.updateHeadSize()

		wx.CallAfter(self._sceneUpdateTimer.Start, 500, True)
		self._engine.abortEngine()
		self._scene.updateSizeOffsets()
		self.updatePrinterSelectorControls()
		self.QueueRefresh()
		
		
	def updatePrinterSelectorControls(self):
		filenames = []		
		for count in range(0, len(self._scene._objectList)):
			filenames.append(self._scene._objectList[count].getName())
		pub.sendMessage('file.isopen', filenames=filenames)

	def flowrateFix(self):
#		extrusionWidth = float (profile.getProfileSetting('nozzle_size'))
		extrusionWidth = float (profile.calculateEdgeWidth())
		layerHeight = float(profile.getProfileSettingFloat('layer_height'))
		rectangularArea = extrusionWidth * layerHeight
		circularArea    = math.pi * layerHeight * layerHeight/4
		diffArea = (rectangularArea + circularArea - (layerHeight*layerHeight))
		flowReduction = round(100 - ((rectangularArea - diffArea) / diffArea * 100),2) 
		if float(profile.getProfileSetting('filament_flow')) != float(flowReduction) and profile.getMachineSetting('flowrate_correction') == 'True':
			profile.putProfileSetting('filament_flow', flowReduction)
			self.GetParent().GetParent().GetParent().normalSettingsPanel.updateProfileToControls()		

	def _onRunEngine(self, e):

		self.flowrateFix()

		if profile.getProfileSettingFloat('fill_distance') > 0:
			equivalent_percentage = round(float(profile.calculateEdgeWidth() * 100 / profile.getProfileSettingFloat('fill_distance')),2)
			if profile.getProfileSettingFloat('infill_percentage') != equivalent_percentage: #Only update if a change was made
				profile.putProfileSetting('infill_percentage',equivalent_percentage)
				self.GetParent().GetParent().GetParent().normalSettingsPanel.updateProfileToControls()
		if profile.getProfileSettingFloat('extrusion_width') != profile.calculateEdgeWidth(): #Only update if a change was made
				profile.putProfileSetting('extrusion_width',profile.calculateEdgeWidth())
		if profile.getProfileSettingFloat('shell_numbers') != profile.calculateLineCount(): #Only update if a change was made
				profile.putProfileSetting('shell_numbers',profile.calculateLineCount())
				self.GetParent().GetParent().GetParent().normalSettingsPanel.updateProfileToControls()
		if self._isSimpleMode:
			self._engine.runEngine(self._scene, self.GetTopLevelParent().simpleSettingsPanel.getSettingOverrides())
		else:
			self._engine.runEngine(self._scene)

	def _updateEngineProgress(self, progressValue):
		result = self._engine.getResult()
		finished = result is not None and result.isFinished()
		if not finished:
			if self.printButton.getProgressBar() is not None and progressValue >= 0.0 and abs(self.printButton.getProgressBar() - progressValue) < 0.01:
				return
		self.printButton.setDisabled(not finished)
		
		if progressValue >= 0.0:
			self.printButton.setProgressBar(progressValue)
		else:
			self.printButton.setProgressBar(None)
		self.QueueRefresh()
		self._engineResultView.setResult(result)
		if finished:
			pub.sendMessage('upload.enabled', enable=True)
			self.printButton.setProgressBar(None)
			text = '%s' % (result.getPrintTime())
			for e in xrange(0, int(profile.getMachineSetting('extruder_amount'))):
				amount = result.getFilamentAmount(e)
				if amount is None:
					continue
				text += '\n%s' % (amount)
#				cost = result.getFilamentCost(e)
#				if cost is not None:
#					text += '\n%s' % (cost)
			self.printButton.setProgressBar(None)
			self.printButton.setBottomText(text)
		self.QueueRefresh()

	def loadScene(self, fileList, pms_transforms=None):
		ret = []
		objIndex = -1
		for filename in fileList:
			objIndex += 1
			try:
				ext = os.path.splitext(filename)[1].lower()
				if ext in imageToMesh.supportedExtensions():
					imageToMesh.convertImageDialog(self, filename).Show()
					objList = []
				else:
					objList = meshLoader.loadMeshes(filename)
			except:
				traceback.print_exc()
			else:
				for obj in objList:
					if self._objectLoadShader is not None:
						obj._loadAnim = openglGui.animation(self, 1, 0, 1.5)
					else:
						obj._loadAnim = None
					ret.append(obj)
					self._scene.add(obj)
					if pms_transforms is not None and len(pms_transforms) == len(fileList):
						obj.setPosition(pms_transforms[objIndex][0])
						obj.applyMatrix(pms_transforms[objIndex][1])
						obj.setScale(pms_transforms[objIndex][2][0], 0, False)
						obj.setScale(pms_transforms[objIndex][2][1], 1, False)
						obj.setScale(pms_transforms[objIndex][2][2], 2, False)
					else:
						if not self._scene.checkPlatform(obj):
							self._scene.centerAll()
						self._selectObject(obj)
						if obj.getScale()[0] < 1.0:
							self.notification.message("Warning: Object scaled down.")
		self.sceneUpdated()
		return ret

	def _deleteObject(self, obj):
		if obj == self._selectedObj:
			self._selectObject(None)
		if obj == self._focusObj:
			self._focusObj = None
		self._scene.remove(obj)
		for m in obj._meshList:
			if m.vbo is not None and m.vbo.decRef():
				self.glReleaseList.append(m.vbo)
		if len(self._scene.objects()) == 0:
			self._engineResultView.setResult(None)
		import gc
		gc.collect()
		self.sceneUpdated()

	def _selectObject(self, obj, zoom = True):
		if obj != self._selectedObj:
			self._selectedObj = obj
			self.updateModelSettingsToControls()
			self.updateToolButtons()
		if zoom and obj is not None:
			newViewPos = numpy.array([obj.getPosition()[0], obj.getPosition()[1], obj.getSize()[2] / 2])
			self._animView = openglGui.animation(self, self._viewTarget.copy(), newViewPos, 0.5)
			newZoom = obj.getBoundaryCircle() * 6
			if newZoom > numpy.max(self._machineSize) * 3:
				newZoom = numpy.max(self._machineSize) * 3
			self._animZoom = openglGui.animation(self, self._zoom, newZoom, 0.5)

	def updateProfileToControls(self):
		oldSimpleMode = self._isSimpleMode
		self._isSimpleMode = profile.getPreference('startMode') == 'Simple'
		if self._isSimpleMode != oldSimpleMode:
			self._scene.arrangeAll()
			self.sceneUpdated()
		self._scene.updateSizeOffsets(True)
		self._machineSize = numpy.array([profile.getMachineSettingFloat('machine_width'), profile.getMachineSettingFloat('machine_depth'), profile.getMachineSettingFloat('machine_height')])
		self._objColors[0] = profile.getPreferenceColour('model_colour')
		self._objColors[1] = profile.getPreferenceColour('model_colour2')
		self._objColors[2] = profile.getPreferenceColour('model_colour3')
		self._objColors[3] = profile.getPreferenceColour('model_colour4')
		self._scene.updateMachineDimensions()
		if self._zoom > numpy.max(self._machineSize) * 3:
			self._animZoom = openglGui.animation(self, self._zoom, numpy.max(self._machineSize) * 3, 0.5)
		self.updateModelSettingsToControls()

	def updateModelSettingsToControls(self):
		if self._selectedObj is not None:
			scale = self._selectedObj.getScale()
			size = self._selectedObj.getSize()
			self.scaleXctrl.setValue(round(scale[0], 2))
			self.scaleYctrl.setValue(round(scale[1], 2))
			self.scaleZctrl.setValue(round(scale[2], 2))
			self.scaleXmmctrl.setValue(round(size[0], 2))
			self.scaleYmmctrl.setValue(round(size[1], 2))
			self.scaleZmmctrl.setValue(round(size[2], 2))

	def OnKeyChar(self, keyCode):
		if self._engineResultView.OnKeyChar(keyCode):
			return
		if keyCode == wx.WXK_DELETE or keyCode == wx.WXK_NUMPAD_DELETE or (keyCode == wx.WXK_BACK and sys.platform.startswith("darwin")):
			if self._selectedObj is not None:
				self._deleteObject(self._selectedObj)
				self.QueueRefresh()
		if keyCode == wx.WXK_UP:
			if wx.GetKeyState(wx.WXK_SHIFT):
				self._zoom /= 1.2
				if self._zoom < 1:
					self._zoom = 1
			else:
				self._pitch -= 15
			self.QueueRefresh()
		elif keyCode == wx.WXK_DOWN:
			if wx.GetKeyState(wx.WXK_SHIFT):
				self._zoom *= 1.2
				if self._zoom > numpy.max(self._machineSize) * 3:
					self._zoom = numpy.max(self._machineSize) * 3
			else:
				self._pitch += 15
			self.QueueRefresh()
		elif keyCode == wx.WXK_LEFT:
			self._yaw -= 15
			self.QueueRefresh()
		elif keyCode == wx.WXK_RIGHT:
			self._yaw += 15
			self.QueueRefresh()
		elif keyCode == wx.WXK_NUMPAD_ADD or keyCode == wx.WXK_ADD or keyCode == ord('+') or keyCode == ord('='):
			self._zoom /= 1.2
			if self._zoom < 1:
				self._zoom = 1
			self.QueueRefresh()
		elif keyCode == wx.WXK_NUMPAD_SUBTRACT or keyCode == wx.WXK_SUBTRACT or keyCode == ord('-'):
			self._zoom *= 1.2
			if self._zoom > numpy.max(self._machineSize) * 3:
				self._zoom = numpy.max(self._machineSize) * 3
			self.QueueRefresh()
		elif keyCode == wx.WXK_HOME:
			self._yaw = 30
			self._pitch = 60
			self.QueueRefresh()
		elif keyCode == wx.WXK_PAGEUP:
			self._yaw = 0
			self._pitch = 0
			self.QueueRefresh()
		elif keyCode == wx.WXK_PAGEDOWN:
			self._yaw = 0
			self._pitch = 90
			self.QueueRefresh()
		elif keyCode == wx.WXK_END:
			self._yaw = 90
			self._pitch = 90
			self.QueueRefresh()
		# CGC - Still need to add print screen

		if keyCode == wx.WXK_F3 and wx.GetKeyState(wx.WXK_SHIFT):
			shaderEditor(self, self.ShaderUpdate, self._objectLoadShader.getVertexShader(), self._objectLoadShader.getFragmentShader())
		if keyCode == wx.WXK_F4 and wx.GetKeyState(wx.WXK_SHIFT):
			from collections import defaultdict
			from gc import get_objects
			self._beforeLeakTest = defaultdict(int)
			for i in get_objects():
				self._beforeLeakTest[type(i)] += 1
		if keyCode == wx.WXK_F5 and wx.GetKeyState(wx.WXK_SHIFT):
			from collections import defaultdict
			from gc import get_objects
			self._afterLeakTest = defaultdict(int)
			for i in get_objects():
				self._afterLeakTest[type(i)] += 1
			for k in self._afterLeakTest:
				if self._afterLeakTest[k]-self._beforeLeakTest[k]:
					print k, self._afterLeakTest[k], self._beforeLeakTest[k], self._afterLeakTest[k] - self._beforeLeakTest[k]
					
	def ShaderUpdate(self, v, f):
		s = openglHelpers.GLShader(v, f)
		if s.isValid():
			self._objectLoadShader.release()
			self._objectLoadShader = s
			for obj in self._scene.objects():
				obj._loadAnim = openglGui.animation(self, 1, 0, 1.5)
			self.QueueRefresh()

	def OnMouseDown(self,e):
		self._mouseX = e.GetX()
		self._mouseY = e.GetY()
		self._mouseClick3DPos = self._mouse3Dpos
		self._mouseClickFocus = self._focusObj
		if e.ButtonDClick():
			self._mouseState = 'doubleClick'
		else:
			if self._mouseState == 'dragObject' and self._selectedObj is not None:
				self._scene.pushFree(self._selectedObj)
				self.sceneUpdated()
			self._mouseState = 'dragOrClick'
		p0, p1 = self.getMouseRay(self._mouseX, self._mouseY)
		p0 -= self.getObjectCenterPos() - self._viewTarget
		p1 -= self.getObjectCenterPos() - self._viewTarget
		if self.tool.OnDragStart(p0, p1):
			self._mouseState = 'tool'
		if self._mouseState == 'dragOrClick':
			if e.GetButton() == 1:
				if self._focusObj is not None:
					self._selectObject(self._focusObj, False)
					self.QueueRefresh()

	def OnMouseUp(self, e):
		if e.LeftIsDown() or e.MiddleIsDown() or e.RightIsDown():
			return
		if self._mouseState == 'dragOrClick':
			if e.GetButton() == 1:
				self._selectObject(self._focusObj)
			if e.GetButton() == 3:
					menu = wx.Menu()
					if self._focusObj is not None:

						self.Bind(wx.EVT_MENU, self.OnCenter, menu.Append(-1, _("Center on platform")))
						self.Bind(wx.EVT_MENU, lambda e: self._deleteObject(self._focusObj), menu.Append(-1, _("Delete object")))
						self.Bind(wx.EVT_MENU, self.OnMultiply, menu.Append(-1, _("Multiply object")))
						self.Bind(wx.EVT_MENU, self.OnSplitObject, menu.Append(-1, _("Split object into parts")))

					if ((self._selectedObj != self._focusObj and self._focusObj is not None and self._selectedObj is not None) or len(self._scene.objects()) == 2) and int(profile.getMachineSetting('extruder_amount')) > 1:
						self.Bind(wx.EVT_MENU, self.OnMergeObjects, menu.Append(-1, _("Dual extrusion merge")))
					if len(self._scene.objects()) > 0:
						self.Bind(wx.EVT_MENU, self.OnDeleteAll, menu.Append(-1, _("Delete all objects")))
						self.Bind(wx.EVT_MENU, self.reloadScene, menu.Append(-1, _("Reload all objects")))
						self.Bind(wx.EVT_MENU, self.OnResetPositions, menu.Append(-1, _("Reset all objects positions")))
						self.Bind(wx.EVT_MENU, self.OnResetTransformations, menu.Append(-1, _("Reset all objects transformations")))

					if menu.MenuItemCount > 0:
						self.PopupMenu(menu)
					menu.Destroy()
		elif self._mouseState == 'dragObject' and self._selectedObj is not None:
			self._scene.pushFree(self._selectedObj)
			self.sceneUpdated()
		elif self._mouseState == 'tool':
			if self.tempMatrix is not None and self._selectedObj is not None:
				self._selectedObj.applyMatrix(self.tempMatrix)
				self._scene.pushFree(self._selectedObj)
				self._selectObject(self._selectedObj)
			self.tempMatrix = None
			self.tool.OnDragEnd()
			self.sceneUpdated()
		self._mouseState = None

	def OnMouseMotion(self,e):
		p0, p1 = self.getMouseRay(e.GetX(), e.GetY())
		p0 -= self.getObjectCenterPos() - self._viewTarget
		p1 -= self.getObjectCenterPos() - self._viewTarget

		if e.Dragging() and self._mouseState is not None:
			if self._mouseState == 'tool':
				self.tool.OnDrag(p0, p1)
			elif not e.LeftIsDown() and e.RightIsDown():
				self._mouseState = 'drag'
				if wx.GetKeyState(wx.WXK_SHIFT):
					a = math.cos(math.radians(self._yaw)) / 3.0
					b = math.sin(math.radians(self._yaw)) / 3.0
					self._viewTarget[0] += float(e.GetX() - self._mouseX) * -a
					self._viewTarget[1] += float(e.GetX() - self._mouseX) * b
					self._viewTarget[0] += float(e.GetY() - self._mouseY) * b
					self._viewTarget[1] += float(e.GetY() - self._mouseY) * a
				else:
					self._yaw += e.GetX() - self._mouseX
					self._pitch -= e.GetY() - self._mouseY
				if self._pitch > 170:
					self._pitch = 170
				if self._pitch < 10:
					self._pitch = 10
			elif (e.LeftIsDown() and e.RightIsDown()) or e.MiddleIsDown():
				self._mouseState = 'drag'
				self._zoom += e.GetY() - self._mouseY
				if self._zoom < 1:
					self._zoom = 1
				if self._zoom > numpy.max(self._machineSize) * 3:
					self._zoom = numpy.max(self._machineSize) * 3
			elif e.LeftIsDown() and self._selectedObj is not None and self._selectedObj == self._mouseClickFocus:
				self._mouseState = 'dragObject'
				z = max(0, self._mouseClick3DPos[2])
				p0, p1 = self.getMouseRay(self._mouseX, self._mouseY)
				p2, p3 = self.getMouseRay(e.GetX(), e.GetY())
				p0[2] -= z
				p1[2] -= z
				p2[2] -= z
				p3[2] -= z
				cursorZ0 = p0 - (p1 - p0) * (p0[2] / (p1[2] - p0[2]))
				cursorZ1 = p2 - (p3 - p2) * (p2[2] / (p3[2] - p2[2]))
				diff = cursorZ1 - cursorZ0
				self._selectedObj.setPosition(self._selectedObj.getPosition() + diff[0:2])
		if not e.Dragging() or self._mouseState != 'tool':
			self.tool.OnMouseMove(p0, p1)

		self._mouseX = e.GetX()
		self._mouseY = e.GetY()

	def OnMouseWheel(self, e):
		delta = float(e.GetWheelRotation()) / float(e.GetWheelDelta())
		delta = max(min(delta,4),-4)
		self._zoom *= 1.0 - delta / 10.0
		if self._zoom < 1.0:
			self._zoom = 1.0
		if self._zoom > numpy.max(self._machineSize) * 3:
			self._zoom = numpy.max(self._machineSize) * 3
		self.Refresh()

	def OnMouseLeave(self, e):
		#self._mouseX = -1
		pass

	def getMouseRay(self, x, y):
		if self._viewport is None:
			return numpy.array([0,0,0],numpy.float32), numpy.array([0,0,1],numpy.float32)
		p0 = openglHelpers.unproject(x, self._viewport[1] + self._viewport[3] - y, 0, self._modelMatrix, self._projMatrix, self._viewport)
		p1 = openglHelpers.unproject(x, self._viewport[1] + self._viewport[3] - y, 1, self._modelMatrix, self._projMatrix, self._viewport)
		p0 -= self._viewTarget
		p1 -= self._viewTarget
		return p0, p1

	def _init3DView(self):
		# set viewing projection
		size = self.GetSize()
		glViewport(0, 0, size.GetWidth(), size.GetHeight())
		glLoadIdentity()

		glLightfv(GL_LIGHT0, GL_POSITION, [0.2, 0.2, 1.0, 0.0])

		glDisable(GL_RESCALE_NORMAL)
		glDisable(GL_LIGHTING)
		glDisable(GL_LIGHT0)
		glEnable(GL_DEPTH_TEST)
		glDisable(GL_CULL_FACE)
		glDisable(GL_BLEND)
		glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

		glClearColor(0.8, 0.8, 0.8, 1.0) #BACKGROUND COLOR 
		glClearStencil(0)
		glClearDepth(1.0)

		glMatrixMode(GL_PROJECTION)
		glLoadIdentity()
		aspect = float(size.GetWidth()) / float(size.GetHeight())
		gluPerspective(45.0, aspect, 1.0, numpy.max(self._machineSize) * 4)

		glMatrixMode(GL_MODELVIEW)
		glLoadIdentity()
		glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT)

	def OnPaint(self,e):
		connectionGroup = self._printerConnectionManager.getAvailableGroup()
		"""
		if len(removableStorage.getPossibleSDcardDrives()) > 0 and (connectionGroup is None or connectionGroup.getPriority() < 0):
			self.printButton._imageID = 2
			self.printButton._tooltip = _("Toolpath to SD")
		elif connectionGroup is not None:
			self.printButton._imageID = connectionGroup.getIconID()
			self.printButton._tooltip = _("Print with %s") % (connectionGroup.getName())
		else:
		"""
		self.printButton._imageID = 3
		self.printButton._tooltip = _("Save toolpath")

		if self._animView is not None:
			self._viewTarget = self._animView.getPosition()
			if self._animView.isDone():
				self._animView = None
		if self._animZoom is not None:
			self._zoom = self._animZoom.getPosition()
			if self._animZoom.isDone():
				self._animZoom = None
		if self._objectShader is None: #TODO: add loading shaders from file(s)
			if openglHelpers.hasShaderSupport():
				self._objectShader = openglHelpers.GLShader("""
					varying float light_amount;

					void main(void)
					{
						gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;
						gl_FrontColor = gl_Color;

						light_amount = abs(dot(normalize(gl_NormalMatrix * gl_Normal), normalize(gl_LightSource[0].position.xyz)));
						light_amount += 0.2;
					}
									""","""
					varying float light_amount;

					void main(void)
					{
						gl_FragColor = vec4(gl_Color.xyz * light_amount, gl_Color[3]);
					}
				""")
				self._objectOverhangShader = openglHelpers.GLShader("""
					uniform float cosAngle;
					uniform mat3 rotMatrix;
					varying float light_amount;

					void main(void)
					{
						gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;
						gl_FrontColor = gl_Color;

						light_amount = abs(dot(normalize(gl_NormalMatrix * gl_Normal), normalize(gl_LightSource[0].position.xyz)));
						light_amount += 0.2;
						if (normalize(rotMatrix * gl_Normal).z < -cosAngle)
						{
							light_amount = -10.0;
						}
					}
				""","""
					varying float light_amount;

					void main(void)
					{
						if (light_amount == -10.0)
						{
							gl_FragColor = vec4(1.0, 0.0, 0.0, gl_Color[3]);
						}else{
							gl_FragColor = vec4(gl_Color.xyz * light_amount, gl_Color[3]);
						}
					}
									""")
				self._objectLoadShader = openglHelpers.GLShader("""
					uniform float intensity;
					uniform float scale;
					varying float light_amount;

					void main(void)
					{
						vec4 tmp = gl_Vertex;
						tmp.x += sin(tmp.z/5.0+intensity*30.0) * scale * intensity;
						tmp.y += sin(tmp.z/3.0+intensity*40.0) * scale * intensity;
						gl_Position = gl_ModelViewProjectionMatrix * tmp;
						gl_FrontColor = gl_Color;

						light_amount = abs(dot(normalize(gl_NormalMatrix * gl_Normal), normalize(gl_LightSource[0].position.xyz)));
						light_amount += 0.2;
					}
			""","""
				uniform float intensity;
				varying float light_amount;

				void main(void)
				{
					gl_FragColor = vec4(gl_Color.xyz * light_amount, 1.0-intensity);
				}
				""")
			if self._objectShader is None or not self._objectShader.isValid(): #Could not make shader.
				self._objectShader = openglHelpers.GLFakeShader()
				self._objectOverhangShader = openglHelpers.GLFakeShader()
				self._objectLoadShader = None
		self._init3DView()
		glTranslate(0,0,-self._zoom)
		glRotate(-self._pitch, 1,0,0)
		glRotate(self._yaw, 0,0,1)
		glTranslate(-self._viewTarget[0],-self._viewTarget[1],-self._viewTarget[2])

		self._viewport = glGetIntegerv(GL_VIEWPORT)
		self._modelMatrix = glGetDoublev(GL_MODELVIEW_MATRIX)
		self._projMatrix = glGetDoublev(GL_PROJECTION_MATRIX)

		glClearColor(1,1,1,1)
		glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT)

		if self.viewMode != 'gcode':
			for n in xrange(0, len(self._scene.objects())):
				obj = self._scene.objects()[n]
				glColor4ub((n >> 16) & 0xFF, (n >> 8) & 0xFF, (n >> 0) & 0xFF, 0xFF)
				self._renderObject(obj)

		if self._mouseX > -1: # mouse has not passed over the opengl window.
			glFlush()
			n = glReadPixels(self._mouseX, self.GetSize().GetHeight() - 1 - self._mouseY, 1, 1, GL_RGBA, GL_UNSIGNED_INT_8_8_8_8)[0][0] >> 8
			if n < len(self._scene.objects()):
				self._focusObj = self._scene.objects()[n]
			else:
				self._focusObj = None
			f = glReadPixels(self._mouseX, self.GetSize().GetHeight() - 1 - self._mouseY, 1, 1, GL_DEPTH_COMPONENT, GL_FLOAT)[0][0]
			#self.GetTopLevelParent().SetTitle(hex(n) + " " + str(f))
			self._mouse3Dpos = openglHelpers.unproject(self._mouseX, self._viewport[1] + self._viewport[3] - self._mouseY, f, self._modelMatrix, self._projMatrix, self._viewport)
			self._mouse3Dpos -= self._viewTarget

		self._init3DView()
		glTranslate(0,0,-self._zoom)
		glRotate(-self._pitch, 1,0,0)
		glRotate(self._yaw, 0,0,1)
		glTranslate(-self._viewTarget[0],-self._viewTarget[1],-self._viewTarget[2])

		self._objectShader.unbind()
		self._engineResultView.OnDraw()
		if self.viewMode != 'gcode':
			glStencilFunc(GL_ALWAYS, 1, 1)
			glStencilOp(GL_INCR, GL_INCR, GL_INCR)

			if self.viewMode == 'overhang':
				self._objectOverhangShader.bind()
				self._objectOverhangShader.setUniform('cosAngle', math.cos(math.radians(90 - profile.getProfileSettingFloat('support_angle'))))
			else:
				self._objectShader.bind()
			for obj in self._scene.objects():
				if obj._loadAnim is not None:
					if obj._loadAnim.isDone():
						obj._loadAnim = None
					else:
						continue
				brightness = 1.0
				if self._focusObj == obj:
					brightness = 1.2
				elif self._focusObj is not None or self._selectedObj is not None and obj != self._selectedObj:
					brightness = 0.8

				if self._selectedObj == obj or self._selectedObj is None:
					#If we want transparent, then first render a solid black model to remove the printer size lines.
					if self.viewMode == 'transparent':
						glColor4f(0, 0, 0, 0)
						self._renderObject(obj)
						glEnable(GL_BLEND)
						glBlendFunc(GL_ONE, GL_ONE)
						glDisable(GL_DEPTH_TEST)
						brightness *= 0.5
					if self.viewMode == 'xray':
						glColorMask(GL_FALSE, GL_FALSE, GL_FALSE, GL_FALSE)
					glStencilOp(GL_INCR, GL_INCR, GL_INCR)
					glEnable(GL_STENCIL_TEST)

				if self.viewMode == 'overhang':
					if self._selectedObj == obj and self.tempMatrix is not None:
						self._objectOverhangShader.setUniform('rotMatrix', obj.getMatrix() * self.tempMatrix)
					else:
						self._objectOverhangShader.setUniform('rotMatrix', obj.getMatrix())

				if not self._scene.checkPlatform(obj):
					glColor4f(0.5 * brightness, 0.5 * brightness, 0.5 * brightness, 0.8 * brightness)
					self._renderObject(obj)
				else:
					self._renderObject(obj, brightness)
				glDisable(GL_STENCIL_TEST)
				glDisable(GL_BLEND)
				glEnable(GL_DEPTH_TEST)
				glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE)

			if self.viewMode == 'xray':
				glPushMatrix()
				glLoadIdentity()
				glEnable(GL_STENCIL_TEST)
				glStencilOp(GL_KEEP, GL_KEEP, GL_KEEP) #Keep values
				glDisable(GL_DEPTH_TEST)
				for i in xrange(2, 15, 2): #All even values
					glStencilFunc(GL_EQUAL, i, 0xFF)
					glColor(float(i)/10, float(i)/10, float(i)/5)
					glBegin(GL_QUADS)
					glVertex3f(-1000,-1000,-10)
					glVertex3f( 1000,-1000,-10)
					glVertex3f( 1000, 1000,-10)
					glVertex3f(-1000, 1000,-10)
					glEnd()
				for i in xrange(1, 15, 2): #All odd values
					glStencilFunc(GL_EQUAL, i, 0xFF)
					glColor(float(i)/10, 0, 0)
					glBegin(GL_QUADS)
					glVertex3f(-1000,-1000,-10)
					glVertex3f( 1000,-1000,-10)
					glVertex3f( 1000, 1000,-10)
					glVertex3f(-1000, 1000,-10)
					glEnd()
				glPopMatrix()
				glDisable(GL_STENCIL_TEST)
				glEnable(GL_DEPTH_TEST)

			self._objectShader.unbind()

			glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
			glEnable(GL_BLEND)
			if self._objectLoadShader is not None:
				self._objectLoadShader.bind()
				glColor4f(0.2, 0.6, 1.0, 1.0)
				for obj in self._scene.objects():
					if obj._loadAnim is None:
						continue
					self._objectLoadShader.setUniform('intensity', obj._loadAnim.getPosition())
					self._objectLoadShader.setUniform('scale', obj.getBoundaryCircle() / 10)
					self._renderObject(obj)
				self._objectLoadShader.unbind()
				glDisable(GL_BLEND)

		self._drawMachine()
	
		sparseInfillLineDistance = profile.getProfileSettingFloat('fill_distance')
		sparseInfillLineDistance = sparseInfillLineDistance
		if profile.getProfileSetting('infill_type') == 'Cube':
			sparseInfillLineDistance = sparseInfillLineDistance  / 0.816138	

		
		self.layerSelect.setHidden(True)
		#self.layerSelectCondition = (self.viewMode != 'gcode' and sparseInfillLineDistance != 0 and profile.getProfileSetting('show_infill') == 'True' and (profile.getProfileSetting('infill_type') == 'Line' or profile.getProfileSetting('infill_type') == 'Grid'))
		self.layerSelectCondition = (self.viewMode != 'gcode' and sparseInfillLineDistance != 0 and profile.getPreference('show_infill') == 'True' and (profile.getProfileSetting('infill_type') == 'Line' or profile.getProfileSetting('infill_type') == 'Grid'))
#		self.layerSelectCondition = (self.viewMode != 'gcode' and sparseInfillLineDistance != 0 and profile.getProfileSetting('show_infill') == 'True' and profile.getProfileSetting('infill_type') != 'None' and profile.getProfileSetting('infill_type') != 'Concentric' and profile.getProfileSetting('infill_type') != 'Gradient concentric')
		for i in range(0,2):
			if self.layerSelectCondition:
				self.layerSelect.setHidden(False)
				homeX = -float(profile.getMachineSetting('machine_width'))/2 #  -305/2 
				homeY = -float(profile.getMachineSetting('machine_height'))/2

				if i==1:
					glLineWidth(4)
					glColor3f(1, 0,0)
					glBegin(GL_LINES)
				if i==0:
					glLineWidth(1)
					glColor3f(0, 0,0)
					glBegin(GL_LINES)
				
				#print homeX, -homeX, sparseInfillLineDistance
				subdivisions = numpy.arange(homeX, -homeX, sparseInfillLineDistance)
#				print subdivisions

				for index,value in enumerate(subdivisions):
					if profile.getProfileSetting('infill_type') == 'Line':
#						A = [-homeX, value, self.layerSelect.getValue()],[-homeX,value,self.layerSelect.getValue()],[homeX,value,self.layerSelect.getValue()],[homeX,value,self.layerSelect.getValue()]
#						color = [0.5, 0.5, 0.5],[0.5,0.5,0.5],[0.5,0.5,0.5],[0.5,0.5,0.5]

						if self.layerSelect.getValue() % 2 == 0:
							glVertex3f(homeX , value , self.layerSelect.getValue())
							glVertex3f(-homeX, value , self.layerSelect.getValue())
#							A = [-homeX, value, self.layerSelect.getValue()],[-homeX,value,self.layerSelect.getValue()],[homeX,value,self.layerSelect.getValue()],[homeX,value,self.layerSelect.getValue()]
#							glePolyCylinder (A, color, 0.8)
						else :				
#							A = [value, homeY, self.layerSelect.getValue()],[value,homeY,self.layerSelect.getValue()],[value,-homeY,self.layerSelect.getValue()],[value,-homeY,self.layerSelect.getValue()]
#							glePolyCylinder (A, color, 0.8)
							glVertex3f(value , homeY , self.layerSelect.getValue())
							glVertex3f(value ,-homeY , self.layerSelect.getValue())

					elif profile.getProfileSetting('infill_type') == 'Grid':
						glVertex3f(homeX  , value  , self.layerSelect.getValue())
						glVertex3f(-homeX , value  , self.layerSelect.getValue())
						glVertex3f(value  , homeY  , self.layerSelect.getValue())
						glVertex3f(value  , -homeY , self.layerSelect.getValue())

					elif profile.getProfileSetting('infill_type') == 'Cube':						
						#glRotatef(45, 0,0, 0.00)
						#glRotatef(45, 0,1, 0.00)
						#glColor3f(1, 0,0)
						#glutSolidCube(20)
						#glColor3f(0, 0,0)
						#glutWireCube(20)
						#glPopMatrix()
						if value > homeX and value < - homeX:
							glVertex3f(value, homeY  , self.layerSelect.getValue())
							glVertex3f(value , -homeY , self.layerSelect.getValue())
				glEnd()



		if self.viewMode != 'gcode':
			#Draw the object box-shadow, so you can see where it will collide with other objects.
			if self._selectedObj is not None:
				glEnable(GL_BLEND)
				glEnable(GL_CULL_FACE)
				glColor4f(0,0,0,0.16)
				glDepthMask(False)
				for obj in self._scene.objects():
					glPushMatrix()
					glTranslatef(obj.getPosition()[0], obj.getPosition()[1], 0)
					glBegin(GL_TRIANGLE_FAN)
					for p in obj._boundaryHull[::-1]:
						glVertex3f(p[0], p[1], 0)
					glEnd()
					glPopMatrix()
				if self._scene.isOneAtATime(): #Check print sequence mode.
					glPushMatrix()
					glColor4f(0,0,0,0.06)
					glTranslatef(self._selectedObj.getPosition()[0], self._selectedObj.getPosition()[1], 0)
					glBegin(GL_TRIANGLE_FAN)
					for p in self._selectedObj._printAreaHull[::-1]:
						glVertex3f(p[0], p[1], 0)
					glEnd()
					glBegin(GL_TRIANGLE_FAN)
					for p in self._selectedObj._headAreaMinHull[::-1]:
						glVertex3f(p[0], p[1], 0)
					glEnd()
					glPopMatrix()
				glDepthMask(True)
				glDisable(GL_CULL_FACE)

			#Draw the outline of the selected object on top of everything else except the GUI.
			if self._selectedObj is not None and self._selectedObj._loadAnim is None:
				glDisable(GL_DEPTH_TEST)
				glEnable(GL_CULL_FACE)
				glEnable(GL_STENCIL_TEST)
				glDisable(GL_BLEND)
				glStencilFunc(GL_EQUAL, 0, 255)

				glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
				glLineWidth(2)
				glColor4f(1,1,1,0.5)
				self._renderObject(self._selectedObj)
				glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

				glViewport(0, 0, self.GetSize().GetWidth(), self.GetSize().GetHeight())
				glDisable(GL_STENCIL_TEST)
				glDisable(GL_CULL_FACE)
				glEnable(GL_DEPTH_TEST)

			if self._selectedObj is not None:
				glPushMatrix()
				pos = self.getObjectCenterPos()
				glTranslate(pos[0], pos[1], pos[2])
				self.tool.OnDraw()
				glPopMatrix()
		if self.viewMode == 'overhang' and not openglHelpers.hasShaderSupport():
			glDisable(GL_DEPTH_TEST)
			glPushMatrix()
			glLoadIdentity()
			glTranslate(0,-4,-10)
			glColor4ub(60,60,60,255)
			openglHelpers.glDrawStringCenter(_("Overhang view not working due to lack of OpenGL shaders support."))
			glPopMatrix()

	def _renderObject(self, obj, brightness = 0, addSink = True):
		glPushMatrix()
		if addSink:
			glTranslate(obj.getPosition()[0], obj.getPosition()[1], obj.getSize()[2] / 2 - profile.getProfileSettingFloat('object_sink'))
		else:
			glTranslate(obj.getPosition()[0], obj.getPosition()[1], obj.getSize()[2] / 2)

		if self.tempMatrix is not None and obj == self._selectedObj:
			glMultMatrixf(openglHelpers.convert3x3MatrixTo4x4(self.tempMatrix))

		offset = obj.getDrawOffset()
		glTranslate(-offset[0], -offset[1], -offset[2] - obj.getSize()[2] / 2)

		glMultMatrixf(openglHelpers.convert3x3MatrixTo4x4(obj.getMatrix()))

		n = 0
		for m in obj._meshList:
			if m.vbo is None:
				m.vbo = openglHelpers.GLVBO(GL_TRIANGLES, m.vertexes, m.normal)
			if brightness != 0:
				glColor4fv(map(lambda idx: idx * brightness, self._objColors[n]))
				n += 1
			m.vbo.render()
		glPopMatrix()

	def _drawMachine(self):
		glEnable(GL_CULL_FACE)
		glEnable(GL_BLEND)

		size = [profile.getMachineSettingFloat('machine_width'), profile.getMachineSettingFloat('machine_depth'), profile.getMachineSettingFloat('machine_height')]

		machine_type = profile.getMachineSetting('machine_type')
		if machine_type not in self._platformMesh:
			self._platformMesh[machine_type] = None

			filename = None
			texture_name = None
			offset = [0,0,0]
			texture_offset = [0,0,0]
			texture_scale = 1.0
			if machine_type == 'ultimaker2' or machine_type == 'ultimaker2extended':
				filename = resources.getPathForMesh('ultimaker2_platform.stl')
				offset = [-9,-37,145]
				texture_name = 'Ultimaker2backplate.png'
				texture_offset = [9,150,-5]
			elif machine_type == 'ultimaker2go':
				filename = resources.getPathForMesh('ultimaker2go_platform.stl')
				offset = [0,-42,145]
				texture_offset = [0,105,-5]
				texture_name = 'Ultimaker2backplate.png'
				texture_scale = 0.9
			elif machine_type == 'ultimaker_plus':
				filename = resources.getPathForMesh('ultimaker2_platform.stl')
				offset = [0,-37,145]
				texture_offset = [0,150,-5]
				texture_name = 'UltimakerPlusbackplate.png'
			elif machine_type == 'ultimaker':
				filename = resources.getPathForMesh('ultimaker_platform.stl')
				offset = [0,0,2.5]
			elif machine_type == 'Witbox':
				filename = resources.getPathForMesh('Witbox_platform.stl')
				offset = [0,-37,145]

			if filename is not None:
				meshes = meshLoader.loadMeshes(filename)
				if len(meshes) > 0:
					self._platformMesh[machine_type] = meshes[0]
					self._platformMesh[machine_type]._drawOffset = numpy.array(offset, numpy.float32)
					self._platformMesh[machine_type].texture = None
					if texture_name is not None:
						self._platformMesh[machine_type].texture = openglHelpers.loadGLTexture(texture_name)
						self._platformMesh[machine_type].texture_offset = texture_offset
						self._platformMesh[machine_type].texture_scale = texture_scale
		if self._platformMesh[machine_type] is not None:
			mesh = self._platformMesh[machine_type]
			glColor4f(1,1,1,0.5)
			self._objectShader.bind()
			self._renderObject(mesh, False, False)
			self._objectShader.unbind()

			#For the Ultimaker 2 render the texture on the back plate to show the Ultimaker2 text.
			if mesh.texture is not None:
				glBindTexture(GL_TEXTURE_2D, mesh.texture)
				glEnable(GL_TEXTURE_2D)
				glPushMatrix()
				glColor4f(1,1,1,1)

				glTranslate(mesh.texture_offset[0], mesh.texture_offset[1], mesh.texture_offset[2])
				glScalef(mesh.texture_scale, mesh.texture_scale, mesh.texture_scale)
				h = 50
				d = 8
				w = 100
				glEnable(GL_BLEND)
				glBlendFunc(GL_DST_COLOR, GL_ONE_MINUS_SRC_ALPHA)
				glEnable(GL_ALPHA_TEST)
				glAlphaFunc(GL_GREATER, 0.0)
				glBegin(GL_QUADS)
				glTexCoord2f(1, 0)
				glVertex3f( w, 0, h)
				glTexCoord2f(0, 0)
				glVertex3f(-w, 0, h)
				glTexCoord2f(0, 1)
				glVertex3f(-w, 0, 0)
				glTexCoord2f(1, 1)
				glVertex3f( w, 0, 0)

				glTexCoord2f(1, 0)
				glVertex3f(-w, d, h)
				glTexCoord2f(0, 0)
				glVertex3f( w, d, h)
				glTexCoord2f(0, 1)
				glVertex3f( w, d, 0)
				glTexCoord2f(1, 1)
				glVertex3f(-w, d, 0)
				glEnd()
				glDisable(GL_TEXTURE_2D)
				glDisable(GL_ALPHA_TEST)
				glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
				glPopMatrix()
		else:
			glColor4f(0,0,0,1)
			glLineWidth(3)
			glBegin(GL_LINES)
			glVertex3f(-size[0] / 2, -size[1] / 2, 0)
			glVertex3f(-size[0] / 2, -size[1] / 2, 10)
			glVertex3f(-size[0] / 2, -size[1] / 2, 0)
			glVertex3f(-size[0] / 2+10, -size[1] / 2, 0)
			glVertex3f(-size[0] / 2, -size[1] / 2, 0)
			glVertex3f(-size[0] / 2, -size[1] / 2+10, 0)
			glEnd()

		glDepthMask(False)

		polys = profile.getMachineSizePolygons()
		height = profile.getMachineSettingFloat('machine_height')
		circular = profile.getMachineSetting('machine_shape') == 'Circular'
		glBegin(GL_QUADS)
		# Draw the sides of the build volume.
		for n in xrange(0, len(polys[0])):
			if not circular:
				if n % 2 == 0:
					glColor4ub(233, 232, 234, 96)
				else:
					glColor4ub(233, 232, 234, 64)
			else:
				glColor4ub(233, 232, 234, 96)

			glVertex3f(polys[0][n][0], polys[0][n][1], height)
			glVertex3f(polys[0][n][0], polys[0][n][1], 0)
			glVertex3f(polys[0][n-1][0], polys[0][n-1][1], 0)
			glVertex3f(polys[0][n-1][0], polys[0][n-1][1], height)
		glEnd()

		#Draw top of build volume.
		glColor4ub(233, 232, 234, 128)
		glBegin(GL_TRIANGLE_FAN)
		for p in polys[0][::-1]:
			glVertex3f(p[0], p[1], height)
		glEnd()

		#Draw checkerboard
		if self._platformTexture is None:
			self._platformTexture = openglHelpers.loadGLTexture('buildplate.png')
			glBindTexture(GL_TEXTURE_2D, self._platformTexture)
		#	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
		#	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
		glColor4f(1,1,1,70)
		glBindTexture(GL_TEXTURE_2D, self._platformTexture)
		glEnable(GL_TEXTURE_2D)
#		glCullFace(GL_FRONT_AND_BACK)
		glBegin(GL_TRIANGLE_FAN)
		glTexCoord2f(0, 1)
		glVertex3f(-153, 153, 0)
		glTexCoord2f(0, 0)     
		glVertex3f(-153, -153, 0)
		glTexCoord2f(1, 0)     
		glVertex3f(153, -153, 0)
		glTexCoord2f(1, 1)     
		glVertex3f(153, 153, 0)
		
		glEnd()

		#Draw no-go zones. (clips in case of UM2)
		glDisable(GL_TEXTURE_2D)
		glColor4ub(127, 127, 127, 0)
		for poly in polys[1:]:
			glBegin(GL_TRIANGLE_FAN)
			for p in poly:
				glTexCoord2f(p[0]/20, p[1]/20)
				glVertex3f(p[0], p[1], 0)
			glEnd()

		glDepthMask(True)
		glDisable(GL_BLEND)
		glDisable(GL_CULL_FACE)

	def getObjectCenterPos(self):
		if self._selectedObj is None:
			return [0.0, 0.0, 0.0]
		pos = self._selectedObj.getPosition()
		size = self._selectedObj.getSize()
		return [pos[0], pos[1], size[2]/2 - profile.getProfileSettingFloat('object_sink')]

	def getObjectBoundaryCircle(self):
		if self._selectedObj is None:
			return 0.0
		return self._selectedObj.getBoundaryCircle()

	def getObjectSize(self):
		if self._selectedObj is None:
			return [0.0, 0.0, 0.0]
		return self._selectedObj.getSize()

	def getObjectMatrix(self):
		if self._selectedObj is None:
			return numpy.matrix(numpy.identity(3))
		return self._selectedObj.getMatrix()

#TODO: Remove this or put it in a seperate file
class shaderEditor(wx.Frame):
	def __init__(self, parent, callback, v, f):
		super(shaderEditor, self).__init__(parent, title="Shader editor", style=wx.DefaultPosition)
		self._callback = callback
		s = wx.BoxSizer(wx.VERTICAL)
		self.SetSizer(s)
		self._vertex = wx.TextCtrl(self, -1, v, style=wx.TE_MULTILINE)
		self._fragment = wx.TextCtrl(self, -1, f, style=wx.TE_MULTILINE)
		s.Add(self._vertex, 1, flag=wx.EXPAND)
		s.Add(self._fragment, 1, flag=wx.EXPAND)

		self._vertex.Bind(wx.EVT_TEXT, self.OnText, self._vertex)
		self._fragment.Bind(wx.EVT_TEXT, self.OnText, self._fragment)

		self.SetPosition(self.GetParent().GetPosition())
		self.SetSize((self.GetSize().GetWidth(), self.GetParent().GetSize().GetHeight()))
		self.Show()

	def OnText(self, e):
		self._callback(self._vertex.GetValue(), self._fragment.GetValue())

# middleMan should inherit printButton
# Check printButton's status
# Then initialize printerSelector with that variable as one of its parameters

class middleMan(SceneView):
	def __init__(self, printButton):
		#--gcode upload--#
		# Second part of data handoff: listens to and then sends response acquired from sceneView and sends it to printerSelector
		try:
			pub.subscribe(self.uploadStatus, 'transfer.response')
			pub.subscribe(self.updateFilename, 'file.name')
		except Exception as e:
			print e
	
		self.enableUpload = True
		self.printButtonStatus = printButton

	def OpenPrinterSelector(self):
		# Send analytic data
		analytics.featureAnalytics('','','1','','direct_upload')
		if self.printButtonStatus.isDisabled():
			self.enableUpload = False
		else:
			self.enableUpload = True
		
	#	print "scene object quantity: %s" % self.sceneObjectQuantity
		win = printerSelector(self.enableUpload)
		win.Show(True)

	def uploadStatus(self, enable):
		# Sends message to printerSelector window to enable the upload button
		pub.sendMessage('enable.upload', enable=enable)		

	def updateFilename(self, filenames):
		pub.sendMessage('file.isopen', filenames=filenames)

class printerSelector(wx.Frame):
	def __init__(self, enableUpload):
		wx.Frame.__init__(self, None, wx.ID_ANY, "Printer Select", wx.DefaultPosition, style=wx.DEFAULT_DIALOG_STYLE |  wx.STAY_ON_TOP)

		self.gcodeFilename = None
	
		# Text Related
		font = wx.Font(10, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
		bigFont = wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
		# OctoPrint API Config Path
		printerListPath = os.path.join(profile.getBasePath(), 'octoprint_api_config.ini')
		
		# Add-New-Printer Event-listener
		pub.subscribe(self.AddToPrinterList,'printer.add')
		# Enable-Upload Event-Listener
		pub.subscribe(self.enableUploadButton, 'enable.upload')
		# File Load Status Event-Listener
		pub.subscribe(self.initializeOpenFileObject, 'file.isopen')
		
		contentBox = wx.BoxSizer(wx.VERTICAL)
		layoutGrid = wx.GridBagSizer(vgap=10, hgap=10)
		
		# Reads and parses the OctoPrintAPIConfig file for:
		#	- printers
		#	- api keys
		printerList = []
		cp = configparser.ConfigParser()
		
	#	self.openOctoPrintInBrowser = False
		self.startPrintOnUpload = "false"
		
		if os.path.lexists(printerListPath):
			cp.read(printerListPath)
			listSections = cp.sections()
			for item in listSections:
				printerList.append("Series 1 %s" % item)		
				
		# Text labels
		filenameLabel = wx.StaticText(self, -1, "Filename")
		printerLabel = wx.StaticText(self, -1, "Printer")
		
		# Consequent text controls
		self.filenameTextCtrl = wx.TextCtrl(self)
		self.availPrinters = wx.ComboBox(self, choices=printerList, style=wx.CB_READONLY)

		# Option checkboxes
		openInterfaceOption = wx.CheckBox(self, 1, "Open Interface")
		startPrintAfterUploadOption =  wx.CheckBox(self, 2, "Start Print")

		# Send to printer button
		self.sendToPrinterButton = wx.Button(self, -1, "Send To Printer")
		self.sendToPrinterButton.Enable(enableUpload)

		# filename text ctrl
		layoutGrid.Add(filenameLabel, pos=(1,2), flag=wx.ALIGN_CENTRE_VERTICAL)
		layoutGrid.Add(self.filenameTextCtrl, pos=(1,3), span=(0,7), flag=wx.EXPAND)
		
		# add new printer button
		addPrinterButton = wx.Button(self, -1, "Add Printer")
		addPrinterButton.Bind(wx.EVT_BUTTON, lambda e: self.OnAddNew(e))
		
		# printer combobox
		layoutGrid.Add(printerLabel, pos=(2,2), flag=wx.ALIGN_CENTRE_VERTICAL)
		layoutGrid.Add(self.availPrinters, pos=(2,3), span=(0,7), flag=wx.EXPAND)
		
		# option checkboxes
		layoutGrid.Add(openInterfaceOption, pos=(4,7), flag=wx.EXPAND)
		layoutGrid.Add(startPrintAfterUploadOption, pos=(5,7), flag=wx.EXPAND)
		layoutGrid.Add(addPrinterButton, pos=(7,2))
		layoutGrid.Add(self.sendToPrinterButton, pos=(7,8), span=(1,1), flag=wx.EXPAND)
		layoutGrid.AddGrowableRow(7)
		layoutGrid.AddGrowableCol(3)
		
		newBox = wx.BoxSizer(wx.VERTICAL)
		newBox.Add(layoutGrid, flag=wx.RIGHT|wx.BOTTOM, border=30)
		self.SetSizerAndFit(newBox)
		
		self.filenameTextCtrl.Bind(wx.EVT_TEXT, self.onEditFilename)
		
		startPrintAfterUploadOption.Bind(wx.EVT_CHECKBOX, self.StartPrint)
		if startPrintAfterUploadOption.IsChecked():
			pub.sendMessage('print.gcode', printGcode='true')
		else:
			pub.sendMessage('print.gcode', printGcode='false')
		"""
		# ------------
		#Checkboxes
		openInBrowser = 
		openInBrowser.SetFont(bigFont)
		openInBrowser.Bind(wx.EVT_CHECKBOX, self.OnChecked)		
		printAfterUpload = wx.CheckBox(self, -1, "Start Print")
		printAfterUpload.SetFont(bigFont)
		startPrintAfterUploadOption.Bind(wx.EVT_CHECKBOX, self.StartPrint)
		#--------------
	#	filenameLabel = wx.StaticText(self, -1, "Filename: ")
	#	self.filenameInput = wx.TextCtrl(self, -1, " ")

		layoutGrid.Add(openInBrowser, pos=(3,4))
		self.SetSizerAndFit(layoutGrid)

		# --- Cancel and upload buttons --- #
		self.cancel = wx.Button(self, 1, "Cancel")
		self.sendToPrinterButton = wx.Button(self, 10, "Upload")
		self.sendToPrinterButton.Enable(enableUpload)
		
		#Font-size
		self.cancel.SetFont(bigFont)
		self.sendToPrinterButton.SetFont(bigFont)
		

		
		if printAfterUpload.IsChecked():
			pub.sendMessage('print.gcode', printGcode='true')
		else:
			pub.sendMessage('print.gcode', printGcode='false')
	"""			
	
	def onEditFilename(self, e):
		if self.filenameTextCtrl.GetValue() == "":
			self.sendToPrinterButton.Enable(False)
		self.gcodeFilename = self.filenameTextCtrl.GetValue()
		print self.gcodeFilename
	
	def initializeOpenFileObject(self, filenames):
		if filenames:
			print "Filename total: ", len(filenames)
			print "\nstart list\n", "-"*60
			for file in filenames:
				print file
		
			print "filenames[-1]: "	
			print filenames[-1]
			gcodeFilename = str(filenames[-1]) + '.gcode'
			cursorInsertionPoint = len(filenames[-1])
			self.filenameTextCtrl.SetValue(gcodeFilename)
			self.filenameTextCtrl.SetInsertionPoint(cursorInsertionPoint)
			print "-"*60
		else:
			print "No filename data."
			self.filenameTextCtrl.SetValue("")
			self.sendToPrinterButton.Enable(False)

	def StartPrint(self, e):
		if e.IsChecked():
			self.startPrintOnUpload = "true"
			print "Start print checked"
			pub.sendMessage('print.gcode', printGcode="true")
		else:
			self.startPrintOnUpload = "false"
			pub.sendMessage('print.gcode', printGcode="false")
			print "Start print not checked."
			

	def enableUploadButton(self, enable):
		print "enableUpload Function; enable: %s" % enable
		self.sendToPrinterButton.Enable(True)
		
	def OnEdit(self, e):
		index = self.availPrinters.GetSelection()
		printerString = self.availPrinters.GetString(index)
		series, one, serial = printerString.split()
	
		editPrinter = EditPrinter(serial)
		editPrinter.Show()
		
	#	pub.sendMessage('load.serial', serial=serialNum)

	def OnUpload(self, e):
		index = self.availPrinters.GetSelection()
		printerString = self.availPrinters.GetString(index)
		series, one, serial = printerString.split()
		# this sends the selected serial number to the octoPrint setup
		pub.sendMessage('gcode.update', serial=serial)

		self.Destroy()
		
	def OnAddNew(self, e):
		print("Adding new printer")
		newPrinter = AddNewPrinter(self)
		newPrinter.Show()

	def AddToPrinterList(self, serial):
		printerList = []
		total = self.availPrinters.GetCount()
		
		# put items in a list if there is more than 1 printer
		if total >= 0:
			for x in range(0,total):
				printerList.append(self.availPrinters.GetString(x))
		printer = "Series 1 " + str(serial)
		if printer in printerList:
			return

		# if there are no items in the list or the serial isn't already in the list
		# add it and save it
		if len(printerList) == 0 or not printer in printerList:
			self.availPrinters.Append(printer)
			printerIndex = self.availPrinters.FindString(printer)
			self.availPrinters.SetSelection(printerIndex)
				
		if profile.printerExists(serial) is True:
			pass
		else:
			key = profile.OctoPrintConfigAPI(serial)
			profile.initializeOctoPrintAPIConfig(serial, key)
			
		if profile.printerExists(serial) is True and serial in printerList:
			return

	# We need to create a function in profile - or somewhere -  that goes about deleting the item from the octoprint_api.ini (or equivalently named) file.
	def OnRemove(self, e):

		index = self.availPrinters.GetSelection()
		if index >= 0:
			printerString = self.availPrinters.GetString(index)
			series, one, serial = printerString.split()
			profile.OctoPrintAPIRemoveSerial(serial)
			self.availPrinters.Delete(index)
		
	def OnChecked(self, e):
		if e.IsChecked():
			openBrowser = True
		else:
			openBrowser = False

		pub.sendMessage('browser.open', openBrowser=openBrowser)

	def OnCancel(self, e):
		self.Destroy()
		
	def OnClose(self, e):
		self.Destroy()

class AddNewPrinter(wx.Frame):
	def __init__(self, parent):
		wx.Frame.__init__(self, parent, wx.ID_ANY, "New Printer", size=(475,350), style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)
		
		mainmainBox = wx.BoxSizer(wx.VERTICAL)
		
		mainBox = wx.BoxSizer(wx.HORIZONTAL)
		iconBox = wx.BoxSizer(wx.VERTICAL)
		inputBox = wx.BoxSizer(wx.VERTICAL)
		inputFeedbackBox = wx.BoxSizer(wx.VERTICAL)
		tipBox = wx.BoxSizer(wx.VERTICAL)
		buttonBox = wx.BoxSizer(wx.HORIZONTAL)
		
		self.validSerial = False
		self.validKey = False
		

		panel = wx.Panel(self, -1)
	#	otherPanel = wx.Panel(self, -2)
		# Upload Icon
		uploadIconPath = resources.getPathForImage('uploadIcon.png')
		uploadIconConvert = wx.Image(uploadIconPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
		uploadIcon = wx.StaticBitmap(panel, -1, uploadIconConvert)
		
		# Input box variables
		serialPrompt = wx.StaticText(panel, -1, "Serial Number:")
		self.serialInput = wx.TextCtrl(panel, -1, "", size=(200, 25))
		
		self.serialError = wx.StaticText(panel, -1, "")
		self.serialError.SetForegroundColour('Red')
		
		self.keyError = wx.StaticText(panel, -1, "")
		self.keyError.SetForegroundColour('Red')
		keyPrompt = wx.StaticText(panel, -1, "API Key:")
		self.keyInput = wx.TextCtrl(panel, -1, "", size=(200, 25))
		
		#buttons
	#	self.cancelButton = wx.Button(panel, -1, "Cancel")
		self.addPrinterButton = wx.Button(panel, -1, "Add Printer")

		#Bindings
		self.serialInput.Bind(wx.EVT_TEXT, self.checkSerial)
		self.keyInput.Bind(wx.EVT_TEXT, self.checkKey)
		self.addPrinterButton.Bind(wx.EVT_BUTTON, self.OnAddPrinter)
		self.addPrinterButton.Disable()
		# Tip text
		self.informativeLabel = wx.StaticText(panel, -1, "Tip")
		self.informativeText = wx.StaticText(panel, -1, "You can find your printer's API Key in OctoPrint by selecting the settings icon and selecting the tab called 'API'. Make sure 'Enable' is turned on.")
		self.informativeLabel.SetForegroundColour('Red')
	#	self.informativeText.SetFont(font)
		self.informativeText.Wrap(425)
		# Loading icon box
		iconBox.Add(uploadIcon, flag=wx.LEFT, border=20)
		
		# Loading input box
		inputBox.Add(serialPrompt, flag=wx.TOP, border=20)
		inputBox.Add(self.serialInput)
		inputBox.Add(self.serialError)
		inputBox.Add(keyPrompt, flag=wx.TOP, border=5)
		inputBox.Add(self.keyInput)
		inputBox.Add(self.keyError)
		buttonBox.Add(self.addPrinterButton, flag=wx.ALIGN_CENTER)
		
		self.successText = wx.StaticText(panel, -1, "", style=wx.ALIGN_LEFT)
		self.successText.Wrap(100)
		self.successText.SetForegroundColour('blue')
		# Loading tip box
		tipBox.Add(self.informativeLabel, flag=wx.CENTER)
		tipBox.Add(self.informativeText, flag=wx.CENTER)
		inputFeedbackBox.Add(self.successText)

		# Loading main box
		mainBox.Add(iconBox, -1, flag=wx.LEFT | wx.TOP, border=20)
		mainBox.Add(inputBox, -1, flag= wx.RIGHT, border=20)
		mainmainBox.Add(mainBox, flag=wx.EXPAND)
		mainmainBox.Add(inputFeedbackBox, flag=wx.CENTER)
		mainmainBox.Add(tipBox, flag= wx.CENTER)
		mainmainBox.Add(buttonBox, flag=wx.CENTER)

		panel.SetSizer(mainmainBox)
		
	def checkSerial(self, e):
		inputValidation = printerConnect.InputValidation()
		serial = self.serialInput.GetValue()
		# check inputs
		serialValResult = inputValidation.verifySerial(serial)

		if serialValResult == 0:
			self.serialError.SetLabel("")
			self.validSerial = True
		
		if serialValResult == -1:
			self.serialError.SetLabel("Serial number is 4-6 digits")
			self.validSerial = False
		else:
			self.serialError.SetLabel("")
		self.passCheck()
			
	def checkKey(self, e):
		inputValidation = printerConnect.InputValidation()
		key = self.keyInput.GetValue()
		keyValResult = inputValidation.verifyKey(key)
		
		if keyValResult == 0:
			self.keyError.SetLabel("")
			self.validKey = True
		
		if keyValResult == -1:
			self.keyError.SetLabel("API key is 32 characters")
			self.validKey = False
		else:
			self.keyError.SetLabel("")
			
		self.passCheck()
			
	def passCheck(self):
		if self.validSerial and self.validKey:
			self.addPrinterButton.Enable()
		
	def OnAddPrinter(self, e):
		self.addPrinterButton.Disable()
		serialNum = self.serialInput.GetValue()
		serialNumLength = len(serialNum)
		apiKey = self.keyInput.GetValue()
		apiKeyLength = len(apiKey)
		configWiz = False
		
		if not serialNum or not apiKey:
			return
		else:
			serial = self.serialInput.GetValue()
			key = self.keyInput.GetValue()
			self.successText.SetLabel("Configuring....")
			self.informativeText.SetLabel("")
			self.informativeLabel.SetLabel("")
			thread = printerConnect.ConfirmCredentials(self, configWiz, apiKey, serialNum, self.informativeText)
			
			try:
				thread.start()
			except Exception as e:
				"Cura/gui/sceneView: ", e
				
	def OnClose(self, e):
		self.Destroy()

	def OnCancel(self, e):
		self.Destroy()
		
class EditPrinter(wx.Frame):
	def __init__(self, serial):
		wx.Frame.__init__(self, None, wx.ID_ANY, "Edit Printer", size=(500,500), style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)

		# Boxsizers
		mainBox = wx.BoxSizer(wx.VERTICAL)
		imageBox = wx.BoxSizer(wx.HORIZONTAL)
		serialBox = wx.BoxSizer(wx.HORIZONTAL)
		apiBox = wx.BoxSizer(wx.HORIZONTAL)
		buttonsBox = wx.BoxSizer(wx.HORIZONTAL)
		
		# Panel
		panel = wx.Panel(self, -1)
		
		# Text
		serialNumberText = wx.StaticText(panel, -1, "Series 1")
		self.self.serialInput = wx.TextCtrl(panel, -1, serial)
		
		printerLogoPath = resources.getPathForImage('series1_icon_100x105.png')
		printerLogoConvert = wx.Image(printerLogoPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
		printerLogoImage = wx.StaticBitmap(panel, -1, printerLogoConvert)
		
		# API input
		apiInputText = wx.StaticText(panel, -1, "API Key:")
		self.apiself.keyInput = wx.TextCtrl(panel, -1, self.getAPIKey(serial))
		
		# Buttons 
		self.cancelButton = wx.Button(panel, -1, "Cancel")
		self.addPrinterButton = wx.Button(panel, -1, "Edit Printer")
		
		self.addPrinterButton.Bind(wx.EVT_BUTTON, self.OnAddPrinter)
		self.cancelButton.Bind(wx.EVT_BUTTON, self.OnCancel)
		# Adding to boxsizers
		imageBox.Add(printerLogoImage)
		
		serialBox.Add(serialNumberText, 1, wx.TOP, 10)
		serialBox.Add(self.self.serialInput, 1, wx.TOP, 10)
		
		apiBox.Add(apiInputText, 1, wx.TOP, 10)
		apiBox.Add(self.apiself.keyInput, 1, wx.TOP|wx.EXPAND, 10)
		
		buttonsBox.Add(self.cancelButton, 1, wx.RIGHT, 100)
		buttonsBox.Add(self.addPrinterButton)
		
		mainBox.Add(imageBox, flag=wx.ALIGN_CENTRE)
		mainBox.Add(serialBox, flag=wx.ALIGN_CENTRE)
		mainBox.Add(apiBox, flag=wx.ALIGN_CENTRE)
		mainBox.Add(buttonsBox, flag=wx.ALIGN_CENTRE | wx.TOP, border=100)
		
		panel.SetSizer(mainBox)
		
	def loadSerial(self, serial):
		self.serial = serial
		
	def getAPIKey(self, serial):
		return profile.OctoPrintConfigAPI(serial) 
		
	def OnAddPrinter(self, e):
		if not self.self.serialInput.GetValue() and not self.apiself.keyInput.GetValue():
			print("No Value")
			return
		else:
			serial = self.self.serialInput.GetValue()
			key = self.apiself.keyInput.GetValue()
			pub.sendMessage('printer.add', serial=serial)
			profile.initializeOctoPrintAPIConfig(serial, key)
			profile.OctoPrintConfigAPI(serial)
		self.Destroy()

	def OnCancel(self, e):
		self.Destroy()

