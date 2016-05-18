import threading
import requests
import os
import wx
import webbrowser
import sys
import json

from Cura.util import profile
import json

try: 
	from wx.lib.pubsub import pub
except ImportError:
	from wx.lib.pubsub import Publisher as pub

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
		if (serialLength ==0):
			return -1					
		else:
			return 0								
				
	def verifyKey(self, key):
		keyLength = len(key)
		if keyLength == 0:
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

	def run(self):
		status = None
		r = requests.Session()
		resourceBasePath = resources.resourceBasePath
		filepath = os.path.join(resourceBasePath, 'example/dummy_code.gcode')
		filename = os.path.basename(filepath)
		files = [('file', (filename, open(filepath, 'rb'), 'multipart/form-data'))]
		header = {'X-Api-Key':self.key}
		url = 'http://series1-%s.local:5000/api/files/local' % self.serial

		try:
			r = requests.post(url, headers=header, files=files, timeout=6)
		except requests.exceptions.RequestException as e:
			print e
			self.conveyError("Connection could not be made. Please try again later.")
		try: 
			print r.text
		except Exception as e:
			print e
		
		try: 	
			status = r.status_code
		except Exception as e:
			print e
			
		self.setStatusBasedText(status)

	def setConfigText(self):
		self.errorMessage1.SetLabel("Configuring...")
		self.errorMessage1.SetForegroundColour('Blue')

	def conveyError(self, e):
		self.errorMessage1.SetForegroundColour('Red')
		self.errorMessage1.SetLabel(str(e))
		if self.configWizard: 
			self.errorMessage1.Wrap(200)
		else:
			self.errorMessage1.Wrap(420)

		if self.configWizard:
			self.parent.configurePrinterButton.Enable()
		else:
			self.parent.successText.SetLabel("")

	def setStatusBasedText(self, status):
		# 201 - File uploaded
		if status is None:
			pass
		elif status == 201:
			profile.initializeOctoPrintAPIConfig(self.serial, self.key)
			if self.configWizard:
				self.parent.GetParent().FindWindowById(wx.ID_FORWARD).Enable()
				self.errorMessage1.SetForegroundColour('Blue')
				self.errorMessage1.SetLabel("Your Series 1 is now configured.")
			else:
				self.parent.successText.SetLabel("Your Series 1 is now configured.")
				self.parent.addPrinterButton.SetLabel('Done')
				self.parent.addPrinterButton.Bind(wx.EVT_BUTTON, self.parent.OnClose)
				self.parent.addPrinterButton.Enable()	
				pub.sendMessage('printer.add', serial=self.serial)
			self.removeFile()
			print "Removing file"
		# 401 - Authentication error
		elif status == 401:
			self.errorMessage1.SetLabel("Invalid serial or API Key. Please try again.")
			self.errorMessage1.SetForegroundColour('Red')

			if not self.configWizard:
				self.parent.successText.SetLabel("")
			else:
				self.parent.configurePrinterButton.Enable()
		else:
			self.errorMessage1.SetLabel(status)
			if not self.configWizard:			
				self.parent.successText.SetLabel("")
			else:
				self.parent.configurePrinterButton.Enable()
			self.errorMessage1.Wrap(200)

	# For removing the dummy file used in configuring connection to printer
	def removeFile(self):
		r = requests.Session()
		url = 'http://series1-%s.local:5000/api/files/local/dummy_code.gcode' % self.serial
		header = {"X-Api-Key":"%s"% self.key}
		r = requests.delete(url=url, headers=header)
		print r.text
		status = r.status_code
		print status
			
class GcodeUpload(threading.Thread):
	def __init__(self, key, serial, tempFilePath, openBrowser, notification, printOnUpload):
		threading.Thread.__init__(self)
		
		self.key = key
		self.serial = serial
		self.tempFilePath = tempFilePath
		self.openBrowser = openBrowser
		self.notification = notification
		self.printOnUpload = printOnUpload
		self.filename = os.path.basename(tempFilePath)
		
		if ' ' in self.filename: 
			self.checkFilename(tempFilePath)
		

	# Whitespaces occasionally affect user experience on 
	# Windows, will sometimes not send.
	# Plan to have a better fix for this soon.
	def checkFilename(self, filePath):
		filename = os.path.basename(filePath)
		fileDirectory = os.path.dirname(filePath)
		gcodeFileList = os.listdir(fileDirectory)

		if os.path.isdir(fileDirectory) and filename in gcodeFileList:
			newFilename = filename.replace(' ', '')
			newFilePath = os.path.join(fileDirectory, newFilename)
			# Checks if file already exists
			try: 
				if os.path.exists(newFilePath):
					os.unlink(newFilePath)
				os.rename(filePath, newFilePath)
				self.filename = newFilename
				self.tempFilePath = newFilePath
			except Exception as e:
				print "Attempted to convert %s to %s\nRan into error: %s\n\n" % (filename, newFilename, e)
				
	def run(self):
		r = requests.Session()
		resourceBasePath = resources.resourceBasePath
		
		# File name and path
		filepath = self.tempFilePath
		filename = self.filename
		openedFilePath = open(filepath, 'rb')
		# Printer information
		url = 'http://series1-%s.local:5000/api/files/local' % self.serial
		header = {'X-Api-Key':self.key}
		files = {'file': (filename, openedFilePath, 'multipart/form-data')}
		data = {'select': 'true', 'print': self.printOnUpload}
		
		try:
			r = requests.post('http://series1-%s.local:5000/api/files/local' % self.serial, headers=header, data=data, files=files, timeout=6)
		except requests.exceptions.RequestException as e:
			self.notification.message("Upload failed, please check your network connection or try again later.")

		
		try:
			openedFilePath.close()
			os.remove(filepath)
			print "Removed file %s " % filepath
		except Exception as e:
			print "\n\nAttempted to remove temporary file: ", filepath
			print "Error: ", e
		try: 
			status = r.status_code
			self.conveyStatus(status)		
		except Exception as e:
			print e	
		
	
	def conveyStatus(self, status):
		if status == 201: 
			if self.openBrowser:
				webbrowser.open_new('http://series1-%s.local:5000' % self.serial)
			self.notification.message("Successfully uploaded to Series 1 " + str(self.serial) + " as %s!" % self.filename, lambda : webbrowser.open_new('http://series1-%s.local:5000' % self.serial), 6, 'Open In Browser')
		else:
			self.notification.message("Error: Please check that your Series 1 is connected to the internet")
			

def GetAllFilesOnPrinter(serial):
	print "Getting all files..."
	url = 'http://series1-'+ str(serial) + '.local:5000/api/files'
	header = {'X-Api-Key': 'pod'}
	requestData = None
	try:
		r = requests.get(url, headers=header, timeout=6)
	except requests.exceptions.RequestException as e:
		print e
		return

	try:
		allFilenames = []		
		for x in r.json()['files']:
			allFilenames.append(x['name'])
		return allFilenames
	except Exception as e:
		print e
		return
