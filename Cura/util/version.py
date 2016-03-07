"""
The version utility module is used to get the current Cura version, and check for updates.
It can also see if we are running a development build of Cura.
"""
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import os
import sys
import urllib2
import platform
import subprocess
try:
	from xml.etree import cElementTree as ElementTree
except:
	from xml.etree import ElementTree

from Cura.util import resources

def getVersion(getGitVersion = True):
	gitPath = os.path.abspath(os.path.join(os.path.split(os.path.abspath(__file__))[0], "../.."))
	if hasattr(sys, 'frozen'):
		versionFile = os.path.normpath(os.path.join(resources.resourceBasePath, "version"))
	else:
		versionFile = os.path.abspath(os.path.join(os.path.split(os.path.abspath(__file__))[0], "../version"))

	if getGitVersion:
		try:
			gitProcess = subprocess.Popen(args = "git show -s --pretty=format:%H", shell = True, cwd = gitPath, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
			(stdoutdata, stderrdata) = gitProcess.communicate()

			if gitProcess.returncode == 0:
				return stdoutdata
		except:
			pass

	gitHeadFile = gitPath + "/.git/refs/heads/devel"
	if os.path.isfile(gitHeadFile):
		if not getGitVersion:
			return "dev"
		f = open(gitHeadFile, "r")
		version = f.readline()
		f.close()
		return version.strip()
	if os.path.exists(versionFile):
		f = open(versionFile, "r")
		version = f.readline()
		f.close()
		return version.strip()
	versionFile = os.path.abspath(os.path.join(os.path.split(os.path.abspath(__file__))[0], "../../version"))
	if os.path.exists(versionFile):
		f = open(versionFile, "r")
		version = f.readline()
		f.close()
		return version.strip()
	return "UNKNOWN" #No idea what the version is. TODO:Tell the user.

def isDevVersion():
	gitPath = os.path.abspath(os.path.join(os.path.split(os.path.abspath(__file__))[0], "../../.git"))
	hgPath  = os.path.abspath(os.path.join(os.path.split(os.path.abspath(__file__))[0], "../../.hg"))
	return os.path.exists(gitPath) or os.path.exists(hgPath)

def checkForNewerVersion():
	# current version list
	CVL= {}
	# latest version list
	LVL = {}


	# current 
	currentVersionURL = 'https://dl.dropboxusercontent.com/s/knr8667zlffnq9n/checkVersion.xml'
	#currentFile = urllib2.urlopen("%s" % (currentVersionURL))
	currentFile = open('/Users/catherinecasuat/CuraDevelopment/checkVersion.xml')
	currentXml = currentFile.read()
	currentFile.close()
	currentXmlTree = ElementTree.fromstring(currentXml)

	for release in currentXmlTree.iter('release'):
		os = str(release.attrib['os'])
		# get matching operating system
		if sys.platform.lower() == os.lower():
			CVL = {"major": int(release.attrib['major']),
						"minor": int(release.attrib['minor']),
						"revision": str(release.attrib['revision']),
						"type": str(release.attrib['type']),
						"testRev": str(release.attrib['testRev'])
						}

	# latest		
	updateBaseURL = 'https://dl.dropboxusercontent.com/s/b2td8x9kfj3ckrv/LatestCura.xml'
	#latestFile = urllib2.urlopen("%s" % (updateBaseURL))
	latestFile = open('/Users/catherinecasuat/Downloads/latestCura.xml')
	latestXml = latestFile.read()
	latestFile.close()
	latestXmlTree = ElementTree.fromstring(latestXml)

	for release in latestXmlTree.iter('release'):
		os = str(release.attrib['os'])
		# get matching operating system
		if sys.platform.lower() == os.lower():	
			LVL = {"major": int(release.attrib['major']),
						"minor": int(release.attrib['minor']),
						"revision": str(release.attrib['revision']),
						"type": str(release.attrib['type']),
						"testRev": str(release.attrib['testRev'])
						}
	
	# Comparison
	"""
	if CVL and LVL:
		print "lists full"
	else:
		print "List error"
	print "----------------------"
	print "Current version"
	for x, y in CVL.items():
		print "\t", x, ": ", y 
	print "----------------------"
	print "Latest version"
	for x, y in LVL.items():
		print "\t", x, ": ", y
	"""
	updateVersion = False

	# Compare major number(s)
	if LVL["major"] > CVL["major"]:
		updateVersion = True
	else:
		# Compare minor number(s)
		# CVL = current version list
		# LVL = latest version list
		if LVL["minor"] > CVL["minor"]:
			updateVersion = True
		elif LVL["minor"] <= CVL["minor"]:
			# Compare rev number(s)
			if LVL["revision"] > CVL["revision"]:
				updateVersion = True
			elif LVL["revision"] <= CVL["revision"]:
				# Compare rev type
				if LVL["type"] == "GM":
					if CVL["type"] != "GM":
						updateVersion = True
					else:
						updateVersion = False
				# If not GM:
				# 	Compare betas and alphas
				else:
					if CVL["type"] == "Beta" and LVL["type"] == "GM":
						updateVersion = True
					if LVL["type"] == "Beta":
						if CVL["type"] != "Beta":
							updateVersion = True
					elif LVL["type"] == "Alpha":
						if CVL["type"] == "Beta":
							updateVersion = True
					# Compares testing (beta or alpha) rev number		
					if updateVersion == False:
						if LVL["testRev"] > CVL["testRev"]:
							updateVersion = True
			else:
				updateVersion = False
		
		else:
			updateVersion = False

		return updateVersion
	


if __name__ == '__main__':
	print(getVersion())
