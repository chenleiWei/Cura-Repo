import threading
import os
import pycurl
import wx
import webbrowser
from wx.lib.pubsub import pub
from Cura.util import profile

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
			return 0								# Return 0
				
	def verifyKey(self, key):
			keyLength = len(key)
			
			if not keyLength == 32:						# Input check for 32 characters
				self.validKey = False
				if keyLength > 0 and keyLength < 32:	# For if the user decides to manually input values
					return -1
			else:
				self.validKey = True
				return 0
	

class ConfirmCredentials(threading.Thread):
	def __init__(self, parent, configWizard, key, serial, errorMessage1):
		threading.Thread.__init__(self)
		
		self.key = key
		self.serial = serial
		self.success = False
		self.status = None
		self.configWizard = configWizard
		self.parent = parent
	#	self.errorMessage0 = errorMessage0
		self.errorMessage1 = errorMessage1
		
	def run(self):
		c = pycurl.Curl()
		buffer = BytesIO()
		# File name and path
		resourceBasePath = resources.resourceBasePath
		filepath = os.path.join(resourceBasePath, 'example/dummy_code.gcode')

		filename = os.path.basename(filepath)
		
		# Printer information
		url = 'http://series1-%s.local:5000/api/files/local'  % self.serial
		apiKey = 'X-Api-Key: %s' % self.key
		contentType = "Content-Type: multipart/form-data"
		header = [apiKey, contentType]
		
		# Pycurl options
		c.setopt(c.URL, url)
		c.setopt(c.WRITEDATA, buffer)
		c.setopt(c.HTTPHEADER, header)
		c.setopt(c.HTTPPOST, [
			("file",
			(c.FORM_FILE, filepath,
			c.FORM_CONTENTTYPE, "multipart/form-data")),
			("print","False")])
		c.setopt(c.VERBOSE, True)
		
		try:
	#		self.errorMessage0.SetForegroundColour('Blue')
	#		self.errorMessage0.SetLabel("Configuring...")
			if self.configWizard:
				self.errorMessage1.SetLabel("\tConfiguring...")
			else:
				self.errorMessage1.SetLabel("Configuring...")
			self.errorMessage1.SetForegroundColour('Blue')
			c.perform()
			self.success = True
		except pycurl.error, error:
			errno, errstr = error
		
		status = c.getinfo(c.RESPONSE_CODE)
		
		if status == 201:
			if self.configWizard:
				self.parent.GetParent().FindWindowById(wx.ID_FORWARD).Enable()
				self.errorMessage1.SetLabel("\tYour printer is configured")
			else:
				self.parent.addPrinterButton.SetLabel('Done')
				self.parent.addPrinterButton.Bind(wx.EVT_BUTTON, self.parent.OnClose)
				self.errorMessage1.SetLabel("Your printer is configured")
	#		self.errorMessage0.SetLabel("Success")
	#		self.errorMessage0.SetForegroundColour('Blue')
			
			self.errorMessage1.SetForegroundColour('Blue')
			pub.sendMessage('printer.add', serial=self.serial)
			
	#		else:
	#			self.parent.successLabel.SetLabel("Success")
	#			self.parent.successText.SetLabel("Your printer is configured.")

			profile.initializeOctoPrintAPIConfig(self.serial, self.key)
				
			self.removeFile()
			print "Removing file"
		elif status == 401: 
#			self.errorMessage0.SetForegroundColour('Red')
#			self.errorMessage0.SetLabel("Error")
			self.errorMessage1.SetLabel("Invalid serial or API Key. Please try again.")
			self.errorMessage1.SetForegroundColour('Red')
		else:
#			self.errorMessage0.SetForegroundColour('Red')
#			self.errorMessage0.SetLabel("Error")
			self.errorMessage1.SetLabel("Please check that your printer is connected to the network")
			if self.configWizard:
				self.errorMessage1.Wrap(350)
			else:
				self.errorMessage1.Wrap(200)
			
		if not self.configWizard:
			self.parent.addPrinterButton.Enable()
		c.close()
		
	def removeFile(self):
		c = pycurl.Curl()
		buffer = BytesIO()
		# File name and path
		resourceBasePath = resources.resourceBasePath
		filepath = os.path.join(resourceBasePath, 'example/dummy_code.gcode')
		filename = os.path.basename(filepath)
	
		# Printer information
		url = 'http://series1-%s.local:5000/api/files/local/dummy_code.gcode' % self.serial
		apiKey = 'X-Api-Key: %s' % self.key
		contentType = "Content-Type: multipart/form-data"
		header = [apiKey, contentType]
	
		# Pycurl options
		c.setopt(c.URL, url)
		c.setopt(c.WRITEDATA, buffer)
		c.setopt(pycurl.CUSTOMREQUEST,"DELETE")
		c.setopt(c.HTTPHEADER, header)
		c.setopt(c.VERBOSE, True)
	
		try:
			c.perform()
		except pycurl.error, error:
			errno, errstr = error
			return errno
	
		status = c.getinfo(c.RESPONSE_CODE)
		c.close()
			

class  GcodeUpload(threading.Thread):
	def __init__(self, key, serial, tempFilePath, openBrowser, notification, printOnUpload):
		threading.Thread.__init__(self)
		
		self.key = key
		self.serial = serial
		self.tempFilePath = tempFilePath
		self.openBrowser = openBrowser
		self.notification = notification
		self.printOnUpload = printOnUpload
		
		print self.printOnUpload
		
	def run(self):
		# Pycurl
		c = pycurl.Curl()
		buffer = BytesIO()
		
		# File name and path
		filepath = self.tempFilePath
		filename = os.path.basename(filepath)
		
		# Printer information
		url = 'http://series1-%s.local:5000/api/files/local'  % self.serial
		apiKey = 'X-Api-Key: %s' % self.key
		contentType = "Content-Type: multipart/form-data"
		header = [apiKey, contentType]
		
		# Pycurl options
		c.setopt(c.URL, url)
		c.setopt(c.WRITEDATA, buffer)
		c.setopt(c.HTTPHEADER, header)
		c.setopt(c.HTTPPOST, [
			("file",
			(c.FORM_FILE, filepath,
			c.FORM_CONTENTTYPE, "multipart/form-data")),
			("print", "%s" % self.printOnUpload)])
		c.setopt(c.VERBOSE, True)
		
		try:
			# Perform http POST request in new thread to prevent UI lag
		#	threading.Thread(target=c.perform()).start()
			c.perform()
			# Open OctoPrint in web browser if user so chooses
			if self.openBrowser:
				webbrowser.open_new('http://series1-%s.local:5000' % self.serial)
			self.notification.message("Successfully uploaded as %s!" % filename, lambda : webbrowser.open_new('http://series1-%s.local:5000' % self.serial), 6, 'Open In Browser')
		except pycurl.error, error:
			errno, errstr = error
			print 'An error occured: ', errstr
			self.notification.message("Error: %s" % errstr)
		
		c.close()
		
		try: 
			os.remove(self.tempFilePath)
			print "Removed file"
		except:
			print "error"		
		
class getFilenames(threading.Thread):
	def __init__(self, serial, key, file):
		threading.Thread.__init__(self)
		
		self.serial = serial
		self.key = key
		self.file = file
	
	def run(self):
		c = pycurl.Curl()
		buffer = BytesIO()
		
		# File name and path
		
		# Printer information
		url = 'http://series1-%s.local:5000/api/files/local'  % self.serial
		apiKey = 'X-Api-Key: %s' % self.key
	#	contentType = "Content-Type: multipart/form-data"
		header = [apiKey]
		
		# Pycurl options
		c.setopt(c.URL, url)
		with open(self.file, 'wb') as f:
			c.setopt(c.WRITEDATA, f)
			c.setopt(c.HTTPHEADER, header)
			c.setopt(c.VERBOSE, True)

			try:
				c.perform()
			except:
				print "error"
			c.close()
		f.close()
		
