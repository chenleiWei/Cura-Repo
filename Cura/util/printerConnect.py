import threading
import requests
import os
import wx
import webbrowser
from wx.lib.pubsub import pub
from Cura.util import profile
import json

try:
    from io import BytesIO
except ImportError:
    from StringIO import StringIO as BytesIO
    
from Cura.util import resources

class InputValidation():
	def __init__(self):
		self = self
		
	def verifySerial(self, serial):
		serialLength = len(serial)
		if (serialLength < 4 or serialLength > 6) or not serial.isdigit() or int(serial) < 1:						
			return -1					
		else:
			return 0								
				
	def verifyKey(self, key):
		keyLength = len(key)
		if not keyLength == 32:						
			self.validKey = False
			if keyLength > 0 and keyLength < 32:
				return -1
		else:
			self.validKey = True
			return 0

class ConfirmCredentials(threading.Thread):
	def __init__(self, parent, configWizard, key, serial, errorMessage1):
		threading.Thread.__init__(self)
		
		self.parent = parent
		self.configWizard = configWizard
		self.key = key
		self.serial = serial
		self.errorMessage1 = errorMessage1		
		self.success = False
		self.status = None

	def run(self):
		r = requests.Session()
		resourceBasePath = resources.resourceBasePath
		filepath = os.path.join(resourceBasePath, 'example/dummy_code.gcode')
		filename = os.path.basename(filepath)
		files = [('file', (filename, open(filepath, 'rb'), 'multipart/form-data'))]
		header = {'X-Api-Key':self.key}
		url = 'http://series1-%s.local:5000/api/files/local' % self.serial

		try:
			r = requests.post(url, headers=header, files=files)
		except requests.exceptions.RequestException as e:
			print e
			wx.CallAfter(self.conveyError)

		print r.text
		status = r.status_code
		
		wx.CallAfter(self.setStatusBasedText(status))

	def setConfigText(self):
		self.errorMessage1.SetLabel("Configuring...")
		self.errorMessage1.SetForegroundColour('Blue')

	def conveyError(self):
		self.errorMessage1.SetLabel("Please check that your printer is connected to the network and that your inputs are correct.")
		self.errorMessage1.Wrap(350)
		self.errorMessage1.SetForegroundColour('Red')
		if self.configWizard:
			self.parent.configurePrinterButton.Enable()

	def setStatusBasedText(self, status):
		# 201 - File uploaded
		print "Status line 86", status
		if status == 201:
			if self.configWizard:
				self.parent.GetParent().FindWindowById(wx.ID_FORWARD).Enable()
				self.errorMessage1.SetLabel("Your printer is configured.")
			else:
				self.parent.addPrinterButton.SetLabel('Done')
				self.parent.addPrinterButton.Bind(wx.EVT_BUTTON, self.parent.OnClose)
				self.errorMessage1.SetLabel("Your printer is configured")
				self.parent.addPrinterButton.Enable()
				
			self.errorMessage1.SetForegroundColour('Blue')
			pub.sendMessage('printer.add', serial=self.serial)
			profile.initializeOctoPrintAPIConfig(self.serial, self.key)
				
			self.removeFile()
			print "Removing file"

		# 401 - Authentication error
		elif status == 401: 
			self.errorMessage1.SetLabel("Invalid serial or API Key. Please try again.")
			self.errorMessage1.SetForegroundColour('Red')
		else:
			if self.configWizard:			
				self.errorMessage1.Wrap(350)
			else:
				self.errorMessage1.Wrap(200)

			self.errorMessage1.SetLabel("Please check that your printer is connected to the network.")

	
	# For removing the dummy file used in configuring connection to printer
	def removeFile(self):
		r = requests.Session()
		url = 'http://series1-%s.local:5000/api/files/local/dummy_code.gcode' % self.serial
		header = {"X-Api-Key":"%s"% self.key}
		r = requests.delete(url=url, headers=header)
		print r.text
		status = r.status_code
		print status


class  GcodeUpload(threading.Thread):
	def __init__(self, key, serial, tempFilePath, openBrowser, notification, printOnUpload):
		threading.Thread.__init__(self)
		
		self.key = key
		self.serial = serial
		self.tempFilePath = tempFilePath
		self.openBrowser = openBrowser
		self.notification = notification
		self.printOnUpload = printOnUpload
		self.filename = os.path.basename(tempFilePath)

	def run(self):
		r = requests.Session()
		resourceBasePath = resources.resourceBasePath
		
		# File name and path
		filepath = self.tempFilePath
		filename = self.filename
		
		# Printer information
		url = 'http://series1-%s.local:5000/api/files/local'  % self.serial
		header = {'X-Api-Key':self.key}
		files = {'file': (filename, open(filepath, 'rb'), 'multipart/form-data')}
		data = {'select': 'true', 'print': self.printOnUpload}
		
		
		try:
			r = requests.post('http://series1-%s.local:5000/api/files/local' % self.serial, headers=header, data=data, files=files)
		except requests.exceptions.RequestException as e:
			wx.CallAfter(self.conveyStatus(e))

		try:
			os.remove(self.tempFilePath)
			print "Removed file"
		except:
			print "error"

		status = r.status_code
			
		wx.CallAfter(self.conveyStatus(status))
	
	def conveyStatus(self, status):
		if status == 201: 
			if self.openBrowser:
				webbrowser.open_new('http://series1-%s.local:5000' % self.serial)
			self.notification.message("Successfully uploaded as %s!" % self.filename, lambda : webbrowser.open_new('http://series1-%s.local:5000' % self.serial), 6, 'Open In Browser')
		else:
			self.notification.message("Error: Please check that your Series 1 is connected to the internet")
			
