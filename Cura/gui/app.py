__copyright__ = "Copyright (C) 2016 David Braam and Cat Casuat - Released under terms of the AGPLv3 License"

import sys
import os
import platform
import shutil
import glob
import warnings

try:
	#Only try to import the _core to save import time
	import wx._core
except ImportError:
	import wx


class CuraApp(wx.App):
	def __init__(self, files):
		if platform.system() == "Windows" and not 'PYCHARM_HOSTED' in os.environ:
	
			try:
				from Cura.util import profile
			except Exception as e:
				print e
			try:	
				super(CuraApp, self).__init__(redirect=True, filename=os.path.join(profile.getBasePath(), 'output_log.txt'))
			except Exception as e:
				print e
		else:
			super(CuraApp, self).__init__(redirect=False)


		self.mainWindow = None
		self.splash = None
		self.loadFiles = files

		self.Bind(wx.EVT_ACTIVATE_APP, self.OnActivate)

		if sys.platform.startswith('win'):
			#Check for an already running instance, if another instance is running load files in there
			from Cura.util import version
			from ctypes import windll
			import ctypes
			import socket
			import threading

			portNr = 0xCA00 + sum(map(ord, version.getVersion(False)))
			if len(files) > 0:
				try:
					other_hwnd = windll.user32.FindWindowA(None, ctypes.c_char_p('Cura - ' + version.getVersion()))
					if other_hwnd != 0:
						sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
						sock.sendto('\0'.join(files), ("127.0.0.1", portNr))

						windll.user32.SetForegroundWindow(other_hwnd)
						return
				except:
					pass

			socketListener = threading.Thread(target=self.Win32SocketListener, args=(portNr,))
			socketListener.daemon = True
			socketListener.start()



		if sys.platform.startswith('darwin'):
			#Do not show a splashscreen on OSX, as by Apple guidelines
			self.afterSplashCallback()
		else:
			from Cura.util.resources import getPathForImage
	#		from Cura.gui import splashScreen
	#		self.splash = splashScreen.splashScreen(self.afterSplashCallback)
			splashBitmap = wx.Image(getPathForImage('splash.png')).ConvertToBitmap()
			splashStyle = wx.SPLASH_CENTRE_ON_SCREEN | wx.SPLASH_TIMEOUT
			splashDuration = 500

			splash = wx.SplashScreen(splashBitmap, splashStyle, splashDuration, None)
			splash.Show()

			self.afterSplashCallback()

	def MacOpenFile(self, path):
		try:
			self.mainWindow.OnDropFiles([path])
		except Exception as e:
			warnings.warn("File at {p} cannot be read: {e}".format(p=path, e=str(e)))

	def MacReopenApp(self, event):
		self.GetTopWindow().Raise()

	def MacHideApp(self, event):
		self.GetTopWindow().Show(False)

	def MacNewFile(self):
		pass

	def MacPrintFile(self, file_path):
		pass

	def OnActivate(self, e):
		if e.GetActive():
			self.GetTopWindow().Raise()
		e.Skip()

	def Win32SocketListener(self, port):
		import socket
		try:
			sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			sock.bind(("127.0.0.1", port))
			while True:
				data, addr = sock.recvfrom(2048)
				try:
					wx.CallAfter(self.mainWindow.OnDropFiles, data.split('\0'))
				except Exception as e:
					warnings.warn("File at {p} cannot be read: {e}".format(p=data, e=str(e)))
		except:
			pass

	def afterSplashCallback(self):
		#These imports take most of the time and thus should be done after showing the splashscreen
		import webbrowser
		from Cura.gui import mainWindow
		from Cura.gui import configWizard
		from Cura.gui import newVersionDialog
		from Cura.util import profile
		from Cura.util import resources
		from Cura.util import version

		resources.setupLocalization(profile.getPreference('language'))  # it's important to set up localization at very beginning to install _

		"""
		#If we do not have preferences yet, try to load it from a previous Cura install
		if profile.getMachineSetting('machine_type') == 'unknown':
			try:
				otherCuraInstalls = profile.getAlternativeBasePaths()
				for path in otherCuraInstalls[::-1]:
					try:
						print 'Loading old settings from %s' % (path)
						profile.loadPreferences(os.path.join(path, 'preferences.ini'))
						profile.loadProfile(os.path.join(path, 'current_profile.ini'))
						break
					except:
						import traceback
						print traceback.print_exc()
			except:
				import traceback
				print traceback.print_exc()
		"""
		#If we haven't run it before, run the configuration wizard.
		if profile.getMachineSetting('machine_type') == 'unknown' or profile.getPreference('configured') == 'False':
			configWizard.ConfigWizard(False)
			#Check if we need to copy our examples
			exampleFile = os.path.normpath(os.path.join(resources.resourceBasePath, 'example', 'FirstPrintCone.stl'))
			self.loadFiles = [exampleFile]

		if profile.getPreference('configured') == 'True':
	#		if self.splash is not None:
	#			self.splash.Show(False)
			

			if self.splash is not None:
				try:
					self.splash.Show(False)
				except Exception as e:
					print e

			
	#		if self.splash is not None:
	#			print "Splash is none"
	#			try:
	#				from Cura.gui import splashScreen
	#			#	self.splash()
	#				self.splash = splashScreen.splashScreen(self.afterSplashCallback)
	#				self.splash(self.afterSplashCallback)
				#	self.splash.Show(False)
	#			except Exception as e:
	#				print e


#					try:
#						from Cura.gui import splashScreen
#						self.splash = splashScreen.splashScreen(self.afterSplashCallback)
#						self.splash.Show(False)
#					except Exception as e:
#						print e

			try:
				self.mainWindow = mainWindow.mainWindow()
			except Exception as e:
				print e
		#	if self.splash is not None:
		#		self.splash.Show(False)
		#		"print line 179 in app.py"
			self.SetTopWindow(self.mainWindow)
			self.mainWindow.Show()
			self.mainWindow.OnDropFiles(self.loadFiles)
		
			if profile.getPreference('last_run_version') != version.getVersion(False):
				profile.putPreference('last_run_version', version.getVersion(False))
				newVersion = newVersionDialog.newVersionDialog()
				newVersion.Show()
				if newVersion.ShowModal() == wx.ID_OK:
					print 'closed'
				newVersion.Destroy()
			
			setFullScreenCapable(self.mainWindow)
			
			if sys.platform.startswith('darwin'):
				wx.CallAfter(self.StupidMacOSWorkaround)
			# Version check	
		
			if profile.getPreference('check_for_updates') == 'True':
				self.newVersionCheck()
		
	def newVersionCheck(self):
		try:
			self.mainWindow.OnCheckForUpdate(False)
		except Exception as e:
			print "Attempted to check for newer version, got error:\n", e
	

	def StupidMacOSWorkaround(self):
		"""
		On MacOS for some magical reason opening new frames does not work until you opened a new modal dialog and closed it.
		If we do this from software, then, as if by magic, the bug which prevents opening extra frames is gone.
		"""
		dlg = wx.Dialog(None)
		wx.PostEvent(dlg, wx.CommandEvent(wx.EVT_CLOSE.typeId))
		dlg.ShowModal()
		dlg.Destroy()

if platform.system() == "Darwin": #Mac magic. Dragons live here. THis sets full screen options.
	try:
		import ctypes, objc
		_objc = ctypes.PyDLL(objc._objc.__file__)

		# PyObject *PyObjCObject_New(id objc_object, int flags, int retain)
		_objc.PyObjCObject_New.restype = ctypes.py_object
		_objc.PyObjCObject_New.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]

		def setFullScreenCapable(frame):
			frameobj = _objc.PyObjCObject_New(frame.GetHandle(), 0, 1)

			NSWindowCollectionBehaviorFullScreenPrimary = 1 << 7
			window = frameobj.window()
			newBehavior = window.collectionBehavior() | NSWindowCollectionBehaviorFullScreenPrimary
			window.setCollectionBehavior_(newBehavior)
	except:
		def setFullScreenCapable(frame):
			pass

else:
	def setFullScreenCapable(frame):
		pass
