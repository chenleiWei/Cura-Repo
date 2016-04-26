__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"
##BATCHSLICE PANEL
import wx
import os
import webbrowser
import multiprocessing
import threading
import time
from wx.lib import scrolledpanel
import  wx.gizmos   as  gizmos

from Cura.util import profile
from Cura.util import pluginInfo
from Cura.util import explorer
from Cura.util import meshLoader
#from Cura.gui import mainWindow
from Cura.util import sliceEngine


class bsPanel(wx.Panel):
	def __init__(self, parent):
		wx.Panel.__init__(self, parent,-1)
		#Initialize variables
		self.fileList = []
		self.panelList = []
		
		self.models = []

		self.doneFlag = False
		self.mainWindow = self.GetParent().GetParent().GetParent().GetParent().GetParent()
		self.scene = self.mainWindow.scene
		self.engines()

		sizer = wx.GridBagSizer(2, 2)
		self.SetSizer(sizer)

#		self.index = 0

		self.listctrl = wx.ListCtrl(self, size=(-1,100),style=wx.LC_REPORT|wx.BORDER_SUNKEN)
		self.listctrl.InsertColumn(0, 'Model')
		self.listctrl.InsertColumn(1, 'Print Time')

		
		title = wx.StaticText(self, -1, _("Models:"))
		title.SetFont(wx.Font(wx.SystemSettings.GetFont(wx.SYS_ANSI_VAR_FONT).GetPointSize(), wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.FONTWEIGHT_BOLD))
		addButton = wx.Button(self, -1, 'Add Files', style=wx.BU_EXACTFIT)
		#remButton = wx.Button(self, -1, '-', style=wx.BU_EXACTFIT)
		
		self.sliceButton = wx.Button(self, -1, _("Slice Now"))
		sb = wx.StaticBox(self, label=_("Progress"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		self.progressEnabledPanel = scrolledpanel.ScrolledPanel(self)
		self.progressEnabledPanel.SetupScrolling(False, True)

		sizer.Add(title, (0,0), border=10, flag=wx.ALIGN_CENTER_VERTICAL|wx.LEFT|wx.TOP)
		#sizer.Add(addButton, (0,1), border=10, flag=wx.ALIGN_RIGHT|wx.RIGHT|wx.TOP)
		sizer.Add(addButton, (0,1), border=10, flag=wx.ALIGN_RIGHT|wx.RIGHT|wx.TOP)
		#sizer.Add(remButton, (0,2), border=10, flag=wx.RIGHT|wx.TOP)
		sizer.Add(self.listctrl, (1,0), span=(2,2), border=10, flag=wx.EXPAND|wx.LEFT|wx.RIGHT)



	#	sizer.Add(addButton, (3,0), span=(1,2), border=5, flag=wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_BOTTOM)
		
		sizer.Add(boxsizer, (4,0), span=(4,2), border=10, flag=wx.EXPAND|wx.LEFT|wx.RIGHT)
		sizer.Add(self.sliceButton, (8, 0), border=10, flag=wx.LEFT|wx.BOTTOM)
		boxsizer.Add(self.progressEnabledPanel, 1, flag=wx.EXPAND)

		sizer.AddGrowableCol(0)
		sizer.AddGrowableRow(2) # Plugins list box
		sizer.AddGrowableRow(6) # Enabled plugins

		sizer = wx.BoxSizer(wx.VERTICAL)
		self.progressEnabledPanel.SetSizer(sizer)

	#	self.Bind(wx.EVT_BUTTON, self.OnAdd, addButton)
		self.Bind(wx.EVT_BUTTON, self.OnAddButton, addButton)
		self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.OnRemButton)
		self.Bind(wx.EVT_BUTTON, self.OnSliceButton, self.sliceButton)
		self.listctrl.Bind(wx.EVT_LEFT_DCLICK, self.OnDoubleClick)
		self.initialize()
		#self.updateProfileToControls()


	def OnRemButton(self, e):
		model = self.models[self.listctrl.GetFocusedItem()]
		self.models.remove(model)		
		self.listctrl.DeleteItem(self.listctrl.GetFocusedItem())


	def OnDoubleClick(self, e):
		model = self.models[self.listctrl.GetFocusedItem()].filename		
		self.scene.OnDeleteAll(None)
		self.scene.loadScene([model])

	def OnAddButton(self, e):
		dlg=wx.FileDialog(self, _("Open 3D model"), os.path.split(profile.getPreference('lastFile'))[0], style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST|wx.FD_MULTIPLE)
		wildcardList = ';'.join(map(lambda s: '*' + s, meshLoader.loadSupportedExtensions()))# + imageToMesh.supportedExtensions() + ['.g', '.gcode']))
		wildcardFilter = "All (%s)|%s;%s" % (wildcardList, wildcardList, wildcardList.upper())
		wildcardList = ';'.join(map(lambda s: '*' + s, meshLoader.loadSupportedExtensions()))
		wildcardFilter += "|Mesh files (%s)|%s;%s" % (wildcardList, wildcardList, wildcardList.upper())

		dlg.SetWildcard(wildcardFilter)
		if dlg.ShowModal() != wx.ID_OK:
			dlg.Destroy()
			return
		filenames = dlg.GetPaths()
		dlg.Destroy()
		if len(filenames) < 1:
			return False
		fileList = filenames
#		print self.fileList
		self.listctrl.ClearAll()
		self.listctrl.InsertColumn(0, 'Model')
		self.listctrl.InsertColumn(1, 'Print Time')

		self.models = [None]*len(fileList)
		
		for index,filename in enumerate(fileList):
			base_filename = os.path.splitext(os.path.basename(filename))[0]
			self.models[index] = self.modelData(filename,base_filename,None)	
			self.listctrl.InsertStringItem(index, base_filename)
			self.listctrl.SetStringItem(index, 1, " ")
		self.listctrl.Focus(-1)
		self.lowergauge.SetRange(len(fileList))
		self.mainWindow.scene.notification.message("Loaded %d files for batch slice" %(len(fileList)))

	def OnOpenPluginLocation(self, e):
		self.OnDSVButton()

	class modelData():
		def __init__(self, filename, base_filename,print_time):
			self.filename = filename
			self.base_filename = base_filename
			self.print_time = print_time


	def initialize(self):
		progressPanel = wx.Panel(self.progressEnabledPanel)
		s = wx.GridBagSizer(6, 1)
		progressPanel.SetSizer(s)
		title = wx.StaticText(progressPanel, -1, 'Progress Report')
		title.SetFont(wx.Font(wx.SystemSettings.GetFont(wx.SYS_ANSI_VAR_FONT).GetPointSize(), wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.FONTWEIGHT_BOLD))
		s.Add(title, pos=(0,0), span=(1,2), flag=wx.ALIGN_BOTTOM|wx.TOP|wx.LEFT|wx.RIGHT, border=5)
		s.Add(wx.StaticLine(progressPanel), pos=(1,0), span=(1,4), flag=wx.EXPAND|wx.LEFT|wx.RIGHT,border=3)
		info = wx.StaticText(progressPanel, -1, "Progress in set")
		info.Wrap(300)
		s.Add(info, pos=(2,0), span=(1,4), flag=wx.EXPAND|wx.LEFT|wx.RIGHT,border=3)
		s.Add(wx.StaticLine(progressPanel), pos=(2,0), span=(1,4), flag=wx.EXPAND|wx.LEFT|wx.RIGHT,border=3)
		self.uppergauge = wx.Gauge(progressPanel, id=-1, range=5) 
		s.Add(self.uppergauge, pos=(3,0), span=(1,4), flag=wx.EXPAND|wx.LEFT|wx.RIGHT,border=3)
		s.AddGrowableRow(1)
		info = wx.StaticText(progressPanel, -1, "Progress overall")
		s.Add(info, pos=(4,0), span=(1,4), flag=wx.EXPAND|wx.LEFT|wx.RIGHT,border=3)
		self.lowergauge = wx.Gauge(progressPanel, id=-1, range=20) 
		s.Add(self.lowergauge, pos=(5,0), span=(1,4), flag=wx.EXPAND|wx.LEFT|wx.RIGHT,border=3)
		s.AddGrowableCol(1)
		progressPanel.SetBackgroundColour(self.GetParent().GetBackgroundColour())
		self.progressEnabledPanel.GetSizer().Add(progressPanel, flag=wx.EXPAND)
		self.progressEnabledPanel.Layout()
		self.progressEnabledPanel.SetSize((1,1))
		self.Layout()
		self.progressEnabledPanel.ScrollChildIntoView(progressPanel)
		self.panelList.append(progressPanel)
		return True


	def engines(self):
		self.numberOfEngines = 5
		self._bsengine = [None]*self.numberOfEngines
		for i,item in enumerate(self._bsengine):
			self._bsengine[i] = sliceEngine.Engine(self.scene._updateEngineProgress)

	def onUpperUpdateThread(self,i):
		self.uppergauge.SetValue(i+1)
#		self.mainWindow.scene.notification.message("Loaded %d files for batch slice" %(len(fileList)))
#		self.mainWindow.scene.notification.message("Sliced %d files in batch slice" %(i+1))


	def onLowerUpdateThread(self,print_time):
		self.lowergauge.SetValue(self.counter)
		self.listctrl.SetStringItem(self.counter, 1, print_time)



	def loadModel(self,i):
		p = self.models[i].filename
		self.scene.OnDeleteAll(None)
		self.scene.loadScene([p])

	def OnRun(self,i):
#		p = self.fileList[i]
		self._bsengine[i].runEngine(self.scene._scene)

	def _saveGCode(self, targetFilename,engine, ejectDrive = False):
	# gets gcode from the engine
		gcode = engine.getResult().getGCode()
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
		except:
			import sys, traceback
			traceback.print_exc()
			print "Upload button disabled. Failed to save."
		print 'SAVED'


	def OnSliceButton(self,e):
		if len(self.models) > 0:
			mainWindow = self.mainWindow		
			self.counter = -1
			limit = len(self.models) - 1
			self.lowergauge.SetRange(limit)
			self.uppergauge.SetRange(self.numberOfEngines)
			while self.counter < limit:
				if 1:
					engineLim = limit - self.counter
	#				print "engineLim %d " %engineLim
					for i,engine in enumerate(self._bsengine):
						if i < engineLim:
							self.counter = self.counter + 1	
							self._updateThread = threading.Timer(1,self.onUpperUpdateThread,args = (i,))
							self._updateThread.start()
							self._updateThread.join()
							self._addThread = threading.Timer(1,self.loadModel,args = (self.counter,))
							self._addThread.start()
							self._addThread.join()
							self._runThread = threading.Timer(1,self.OnRun,args = (i,))
							self._runThread.start()
							print 'File ' + self.scene._scene._objectList[0].getName()
						else :
							self.counter = self.counter + 1
					self.counter = self.counter - len(self._bsengine)	
					for i,engine in enumerate(self._bsengine):
						if i < engineLim:
							self.counter = self.counter + 1	
							self._bsengine[i].wait()
	#						print [i,self.counter]
							result = self._bsengine[i].getResult()
							text = 'Engine #%d %s' % (i,result.getPrintTime())
	#						print text
							self._updateThread = threading.Timer(1,self.onLowerUpdateThread,args=(result.getPrintTime(),))
							self._updateThread.start()
							self._updateThread.join()
							text = 'Engine #%d %s' % (i,result.getPrintTime())
	#						filename = os.path.splitext(self.models[self.counter].filename)[0] + ' PrintTime ' + result.getPrintTime().replace(" ","") +'.gcode'
							filename = os.path.splitext(self.models[self.counter].filename)[0] +'.gcode'
							self.saveGCodeThread = threading.Timer(1,self._saveGCode,args=(filename,self._bsengine[i]))
							self.saveGCodeThread.start()
							self.saveGCodeThread.join()
							print "Sliced file %d of %d" %(self.counter,limit)
						else :
							self.counter = self.counter + 1
					print '***************** \n'

			self.doneFlag = True
			self.uppergauge.SetValue(0)
			mainWindow.scene.notification.message("Batch sliced %d files" %(limit+1))
		
			#self.lowergauge.SetValue(0)
#		self.scene.OnDeleteAll(None)


	
	


