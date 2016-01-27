# Available variables numberOfEngines, subvisions
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import wx
import os
import threading

from Cura.gui import configWizard
from Cura.gui import configBase
from Cura.util import machineCom
from Cura.util import profile
from Cura.util import pluginInfo
from Cura.util import resources
from Cura.util import sliceEngine

import math
import matplotlib
import numpy as np
import matplotlib.cm as cm
import matplotlib.mlab as mlab
#import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import scipy.interpolate
import time
import datetime
import seaborn as sns
import matplotlib.pyplot as plt


class dsvDialog(wx.Dialog):
	def __init__(self, parent):
		super(dsvDialog, self).__init__(None, title=_("Design Space Visualization" ))

		wx.EVT_CLOSE(self, self.OnClose)
		
		self.parent = parent
		self.engines()
		self.doneFlag = False
		self.tdsvData=[]
   		self.xdsvData=[]
   		self.ydsvData=[]
		
		profile.putProfileSetting('dsvXaxis','-')
		profile.putProfileSetting('dsvYaxis','-')

		self.panel = configBase.configPanelBase(self)

		left, right, main = self.panel.CreateConfigPanel(self)
		variables = ['-','Layer Height', 'Infill', 'Wall Thickness','Shells', 'Print Speed']
#		variableTypes = ['Layer Height']
		configBase.TitleRow(left, _(" "))
		configBase.SettingRow(left, 'dsvYaxis', variables)
		configBase.SettingRow(left, 'yLowerBound')
		configBase.SettingRow(left, 'yUpperBound')

		configBase.TitleRow(right, _(" "))
		configBase.SettingRow(right, 'dsvXaxis', variables)
		configBase.SettingRow(right, 'xLowerBound')
		configBase.SettingRow(right, 'xUpperBound')

		configBase.TitleRow(left, _("Progress"))
		configBase.BlankRow(left)
	
		self.okButton = wx.Button(right, -1, 'Ok')
		right.GetSizer().Add(self.okButton, (left.GetSizer().GetRows(), 0), flag=wx.BOTTOM, border=5)
		self.okButton.Bind(wx.EVT_BUTTON, lambda e: self.OKClose())

		self.cancelButton = wx.Button(right, -1, 'Close')
		right.GetSizer().Add(self.cancelButton, (right.GetSizer().GetRows()-1, 1), flag=wx.BOTTOM, border=5)
		self.cancelButton.Bind(wx.EVT_BUTTON, lambda e: self.Close())

		pointsize = wx.SystemSettings.GetFont(wx.SYS_ANSI_VAR_FONT).GetPointSize()

		self.uppergauge = wx.Gauge(left, id=-1, range=5,size = ((left.GetSize()[1]*pointsize)-(pointsize*5),pointsize),pos = (10,wx.SystemSettings.GetFont(wx.SYS_ANSI_VAR_FONT).GetPointSize()*(left.GetSizer().GetRows()+3))) 
		self.gauge = wx.Gauge(left, id=-1, range=24,size = ((left.GetSize()[1]*pointsize)-(pointsize*5),pointsize),pos = (10,wx.SystemSettings.GetFont(wx.SYS_ANSI_VAR_FONT).GetPointSize()*(left.GetSizer().GetRows()+4))) 

		self.nozzleSize = profile.getProfileSettingFloat('nozzle_size')
		#print self.nozzleSize
		main.Fit()
		self.Fit()

	def engines(self):
		scene = self.parent.scene
		self.numberOfEngines = 5
		self._dsvengine = [None]*self.numberOfEngines
		for i,item in enumerate(self._dsvengine):
			self._dsvengine[i] = sliceEngine.Engine(scene._updateEngineProgress)
	
	def delengines(self):
		for i in range(0,len(self._dsvengine)):
			self._dsvengine[i].cleanup()

	def OnClose(self, e):
		self.run = False
		self.Destroy()

	def OKClose(self):
		xAxis = profile.getProfileSetting('dsvXaxis')
		yAxis = profile.getProfileSetting('dsvYaxis')
		numberOfObjects = len(self.parent.scene._scene._objectList)
		if numberOfObjects == 0 or (str(xAxis) == '-'  and str(yAxis) == '-'):
			if numberOfObjects == 0:
				wx.MessageBox(' ', 'You need to load at least one model', wx.ICON_EXCLAMATION )	
			else :
				wx.MessageBox(' ', 'Choose at least one variable', wx.ICON_EXCLAMATION )	
		else:
			wx.CallAfter(self.Destroy)	
			if (str(xAxis) == str(yAxis)) or str(xAxis) == '-'  or str(yAxis) == '-' :
				if str(xAxis) == '-' : 
					profile.putProfileSetting('dsvXaxis',profile.getProfileSetting('dsvYaxis'))
					profile.putProfileSetting('xLowerBound',profile.getProfileSetting('yLowerBound'))
					profile.putProfileSetting('xUpperBound',profile.getProfileSetting('yUpperBound'))
				
				if str(yAxis) == '-' : 
					profile.putProfileSetting('dsvYaxis',profile.getProfileSetting('dsvXaxis'))
					profile.putProfileSetting('yLowerBound',profile.getProfileSetting('xLowerBound'))
					profile.putProfileSetting('yUpperBound',profile.getProfileSetting('xUpperBound'))
				
				self.OnDSVButton(2)
			else:
				self.OnDSVButton(3)
			self.parent.scene._engine.abortEngine()
			delThread = threading.Thread(target=self.delengines)
			delThread.start()
			delThread.join()
			del self.parent.dsvDialog

	def init(self):
		axis = ['Layer Height', 'Infill', 'Wall Thickness','Shells', 'Print Speed']

		datapoints = []

		x = profile.getProfileSetting('dsvXaxis')
		y = profile.getProfileSetting('dsvYaxis')

		self.xSetting = []
		self.ySetting = []

		if profile.getProfileSetting('dsvXaxis') == axis[0]: self.xSetting='layer_height'
		if profile.getProfileSetting('dsvXaxis') == axis[1]: self.xSetting='fill_density'
		if profile.getProfileSetting('dsvXaxis') == axis[2]: self.xSetting='wall_thickness'
		if profile.getProfileSetting('dsvXaxis') == axis[3]: self.xSetting='shells'
		if profile.getProfileSetting('dsvXaxis') == axis[4]: self.xSetting='print_speed'

		if profile.getProfileSetting('dsvYaxis') == axis[0]: self.ySetting='layer_height'
		if profile.getProfileSetting('dsvYaxis') == axis[1]: self.ySetting='fill_density'
		if profile.getProfileSetting('dsvYaxis') == axis[2]: self.ySetting='wall_thickness'
		if profile.getProfileSetting('dsvYaxis') == axis[3]: self.ySetting='shells'
		if profile.getProfileSetting('dsvYaxis') == axis[4]: self.ySetting='print_speed'

		yUB = float(profile.getProfileSetting('yUpperBound'))
		yLB = float(profile.getProfileSetting('yLowerBound'))
		yUnit = (yUB-yLB) / 4
		yRange =  np.around(np.arange(yLB, yUB+yUnit, yUnit),decimals = 2)

		xUB = float(profile.getProfileSetting('xUpperBound'))
		xLB = float(profile.getProfileSetting('xLowerBound'))
		xUnit = (xUB-xLB) / 4
		xRange = np.around(np.arange(xLB, xUB+xUnit, xUnit),decimals = 2)

		if self.ySetting is 'shells':
			yUB = float(profile.getProfileSetting('yUpperBound'))/self.nozzleSize
			yLB = float(profile.getProfileSetting('yLowerBound'))/self.nozzleSize
			yUnit = (yUB-yLB) / 4
			yRange = np.arange(yLB, yUB+yUnit, yUnit)
			yRange = np.around(yRange)
			yRange = yRange * self.nozzleSize

		if self.xSetting is 'shells':
			xUB = float(profile.getProfileSetting('xUpperBound'))/self.nozzleSize
			xLB = float(profile.getProfileSetting('xLowerBound'))/self.nozzleSize
			xUnit = (xUB-xLB) / 4
			xRange = np.arange(xLB, xUB+xUnit, xUnit)
			xRange = np.around(xRange)
			xRange = xRange * self.nozzleSize

		print xRange
		print yRange

		x = xRange
		y = yRange

		for i in x:
		  for j in y:
		      datapoints.append([None,i,j])
		return datapoints


	def run2d(self,X,Y,Z):
	  #import matplotlib.pyplot as plt
	  from scipy.interpolate import interp1d

	  sns.set_style("white")
	  #plt.plot(np.cumsum(np.random.randn(1000,1)))
	  #plt.show()

	
	  matplotlib.rcParams['toolbar'] = 'None'
 	  #matplotlib.rcParams['toolbar'] = 'toolbar2'	  

	  fig = plt.figure(facecolor='w')
 	  

	  x = np.asarray(X)
	  y = np.asarray(Y)
	  z = np.asarray(Z)

	  print x
	  print y
	  print z

	  xSubdivision = 40
	  ySubdivision = 40

	  xi, yi = np.linspace(x.min(), x.max(), xSubdivision), np.linspace(y.min(), y.max(), ySubdivision)

	  f2 = interp1d(y, z, kind='cubic')
	  zlabel = Z

	  for i,value in enumerate(z) : 
	  	print i
	  	print value
	  	#zlabel[i] = time.strftime("%H:%M:%S", time.gmtime(value))
	  	zlabel[i] = str(datetime.timedelta(seconds=value))


	  print zlabel
  #	  matplotlib.rcParams['toolbar'] = 'None'

	  plt.plot(y,z,'--')
	  plt.plot(y,z,'ko')
	  plt.plot(yi,f2(yi),'k')
	  plt.xlabel(profile.getProfileSetting('dsvXaxis'))
	  plt.ylabel('Print Time')
	  plt.yticks(z,zlabel)
	  #plt.ylim((6000,9000))
	  plt.gca().set_xticks(y)

	  plt.gca().xaxis.grid(True) 
	  plt.gca().yaxis.grid(True) 

	  plt.gca().spines["top"].set_visible(False)    
	  plt.gca().spines["bottom"].set_visible(True)    
	  plt.gca().spines["right"].set_visible(False)    
	  plt.gca().spines["left"].set_visible(True) 	

#	  def onclick(event):
#		print 'button=%d, xdata=%f, ydata=%f'%(event.button, event.xdata, event.ydata)
#		profile.putProfileSetting(profile.getProfileSetting('dsvXaxis'),event.xdata)
#		text = plt.text(event.x, event.y, "Some text")
#		print plt
#		plt.show(block = False)
#	  cid = fig.canvas.mpl_connect('button_press_event', onclick)

	  plt.show(block = False)
	  fig.canvas.manager.set_window_title('Design Space Visualization')
#	  print "fig.canvas",fig.canvas
#	  print "fig.canvas.manager", fig.canvas.manager
#	  print "fig.canvas.manager.toolbar", fig.canvas.manager.toolbar
#	  fig.canvas.manager.toolbar.set_message("")


	def run3d(self,X,Y,Z):
		import matplotlib.pyplot as plt
		sns.set_style("whitegrid")

		matplotlib.rcParams['toolbar'] = 'None'
		#matplotlib.rcParams['toolbar'] = 'toolbar2'
		fig = plt.figure(facecolor='w')

		x = np.asarray(X)
		y = np.asarray(Y)
		z = np.asarray(Z)

		xSubdivision = 20
		ySubdivision = 20

		if self.xSetting == 'shells' : xSubdivision = 5
		if self.ySetting == 'shells' : ySubdivision = 5

		xi, yi = np.linspace(x.min(), x.max(), xSubdivision), np.linspace(y.min(), y.max(), ySubdivision)
		xi, yi = np.meshgrid(xi, yi)

		# Interpolate
		rbf = scipy.interpolate.Rbf(x, y, z, function='thin_plate')
		zi = rbf(xi, yi)
		#zi = scipy.interpolate.NearestNDInterpolator(xi,yi)
		


		##	  im = plt.imshow(zi, interpolation='bilinear',cmap='winter_r', extent=[x.min(), x.max(), y.min(), y.max()],aspect = 'auto')
		##	  im = plt.imshow(zi,cmap='winter_r', extent=[x.min(), x.max(), y.min(), y.max()],aspect = 'auto')
		im = plt.imshow(zi, cmap = 'rainbow',vmin=z.min(), vmax=z.max(), origin='lower',extent=[x.min(), x.max(), y.min(), y.max()],aspect = 'auto')
		
		CS = plt.contour(xi, yi,zi,10,linewidths=2,colors='k')
		
		##plt.clabel(CS, inline=1, fontsize=10,color = 'k', fmt='%.2f')
		#plt.clabel(CS, inline=1, fontsize=10,color = 'k',fmt=lambda value: time.strftime("%H:%M:%S", time.gmtime(value))) #OLD TECHNIQUE
		plt.clabel(CS, inline=1, fontsize=10,color = 'k',fmt=lambda value: str(datetime.timedelta(seconds=value)))

		plt.title('Print Time')
		plt.xlabel(profile.getProfileSetting('dsvXaxis'))
		plt.ylabel(profile.getProfileSetting('dsvYaxis'))

		# plt.title('Effect of Layer Height and Shells on Print Time')
		plt.gca().xaxis.grid(True) 
		plt.gca().yaxis.grid(True) 
		plt.gca().set_xticks(x)
		plt.gca().set_yticks(y)
		plt.gca().set_xticklabels(X,size='small')
		plt.gca().set_yticklabels(Y,size='small')
		plt.gca().spines["top"].set_visible(False)    
		plt.gca().spines["bottom"].set_visible(False)    
		plt.gca().spines["right"].set_visible(False)    
		plt.gca().spines["left"].set_visible(False) 
		plt.show(block = False)
		fig.canvas.manager.set_window_title('Design Space Visualization')
		#fig.canvas.manager.toolbar.set_message("")



	def printCompletionListener(self,time,dp1,dp2):
		self.tdsvData.append(time)
		self.xdsvData.append(dp1)
		self.ydsvData.append(dp2)


	def OnDSVButton(self,dimension):
		DSVThread = threading.Thread(target=self.onDSVThread,args = (dimension,))
		DSVThread.start()
		DSVThread.join()
		mainWindow = self.parent
		
		if self.doneFlag is True:
			
			if dimension == 2 : self.run2d(self.xdsvData,self.ydsvData,self.tdsvData)
			if dimension == 3 : self.run3d(self.xdsvData,self.ydsvData,self.tdsvData)
			
			self.dsvcounter = -1	


	def onUpperUpdateThread(self,i):
		self.uppergauge.SetValue(i+1)

	def onUpdateThread(self):
		self.gauge.SetValue(self.dsvcounter)


	def onDSVThread(self,dimension):
		dp=[]
		mainWindow = self.parent
		datapoints = self.init()


		self.dsvcounter = -1
		if dimension == 2 : limit = (math.sqrt(len(datapoints)))-1
		if dimension == 3 : limit = len(datapoints)-1
		self.gauge.SetRange(limit)
		self.uppergauge.SetRange(self.numberOfEngines)
		while self.dsvcounter< limit :
			if 1:
				engineLim = limit - self.dsvcounter
				for i,a in enumerate(self._dsvengine):
					if i < engineLim:
						self.dsvcounter = self.dsvcounter + 1	
						self._updateThread = threading.Timer(1,self.onUpperUpdateThread,args = (i,))
						self._updateThread.start()
						self._updateThread.join()
						dp=datapoints[self.dsvcounter] 
						profile.putProfileSetting(self.xSetting,dp[1])
						profile.putProfileSetting(self.ySetting, dp[2])
						mainWindow.normalSettingsPanel.updateProfileToControls()
						self._dsvengine[i].runEngine(self.parent.scene._scene)
					else :
						self.dsvcounter = self.dsvcounter + 1

				

				self.dsvcounter = self.dsvcounter - len(self._dsvengine)	
				for i,a in enumerate(self._dsvengine):
					if i < engineLim:
						self.dsvcounter = self.dsvcounter + 1	
						dp=datapoints[self.dsvcounter]
						#print [i,self.dsvcounter]
						self._dsvengine[i].wait()
						result = self._dsvengine[i].getResult()
						text = 'Engine #%d %s' % (i,result.getPrintTime())
						self._updateThread = threading.Timer(1,self.onUpdateThread)
						self._updateThread.start()
						self._updateThread.join()
						self._addDataThread = threading.Timer(1,self.printCompletionListener, args=(result._printTimeSeconds, dp[1], dp[2]))
						self._addDataThread.start()
						self._addDataThread.join()
						print "Sliced file %d of %d" %(self.dsvcounter,limit)
					else :
						self.dsvcounter = self.dsvcounter + 1
			print '\n'

		self.doneFlag = True


		
		