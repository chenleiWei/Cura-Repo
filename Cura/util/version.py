"""
The version utility module is used to get the current Cura version, and check for updates.
It can also see if we are running a development build of Cura.
"""
__copyright__ = "Copyright (C) 2016 Cat Casuat and David Braam - Released under terms of the AGPLv3 License"

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

def getVersion(getGitVersion = False):
	gitPath = os.path.abspath(os.path.join(os.path.split(os.path.abspath(__file__))[0], "../.."))
	if hasattr(sys, 'frozen'):
		versionFile = os.path.normpath(os.path.join(resources.resourceBasePath, "version"))
	else:
		versionFile = os.path.abspath(os.path.join(os.path.split(os.path.abspath(__file__))[0], "../version"))

	if getGitVersion:
		try:
			gitProcess = subprocess.Popen(args = "git show -s --pretty=format:%H", shell = True, cwd = gitPath, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
			(stdoutdata, stderrdata) = gitProcess.communicate()
			print "stdout: ", stdoutdata, "stderr: ", stderrdata, " = git process"
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
		print version.strip()
	return "UNKNOWN" #No idea what the version is. TODO:Tell the user.
	
def isDevVersion():
	gitPath = os.path.abspath(os.path.join(os.path.split(os.path.abspath(__file__))[0], "../../.git"))
	hgPath  = os.path.abspath(os.path.join(os.path.split(os.path.abspath(__file__))[0], "../../.hg"))
	return os.path.exists(gitPath) or os.path.exists(hgPath)

def checkForNewerVersion():
	releaseData = getCuraVersionXMLTree()
	latestReleaseDict = {}
	
	print "is development version?: ", isDevVersion()
	print "version: ", getVersion()
	for release in releaseData:
	
		os = str(release.attrib['os'])
		if sys.platform.lower() == os.lower():
			latestReleaseDict = {"major": int(release.attrib['major']),
													"minor": int(release.attrib['minor']),
													"patch": str(release.attrib['patch']),
													"preReleaseType": str(release.attrib['preReleaseType']),
													"preReleaseVersion": str(release.attrib['preReleaseVersion'])
													}
	
	thisVersion = getVersion()
	if thisVersion != 'dev':
		thisVersionDict = getThisVersionDataForComparison(thisVersion)
		needsUpdate = compareLocalToLatest(thisVersionDict, latestReleaseDict)
		print needsUpdate
	
		return needsUpdate
	else:
		return ''
			
def compareLocalToLatest(thisVersionDict, latestReleaseDict):
	updateVersion = False
	
	for x, y in thisVersionDict.items():
		print "thisVersion Label: ", x
		print "thisVersion Value: ", y


	for label, localValue in thisVersionDict.items():

		if localValue < latestReleaseDict[label] and "preRelease" not in label:
			updateVersion = True
		
		if updateVersion != True and label == "preReleaseType":
			if localValue < latestReleaseDict[label]:
				updateVersion = True
	
		if label == "preReleaseVersion" and updateVersion != True:
			if localValue < latestReleaseDict[label]:
				updateVersion = True

	return updateVersion

def getThisVersionDataForComparison(thisVersion):	
	thisVersionList = []
	thisVersionDict = {}

	versionInThirds = thisVersion.split('.')	
	if len(versionInThirds) == 3:
		pass
	else:
		print "versionInThirds is not in thirds."
			
	# Gets details on the last part of the version number, i.e., <major>.<minor>.2a10
	# parses that last bit to figure out the patch, preReleaseType, and preRelease version if they apply
	if 'a' or 'b' in thisVersionList:
		preReleaseValue = versionInThirds[-1]

		if 'a' in preReleaseValue:
			alphaVersion = preReleaseValue.split('a')
			if len(alphaVersion) == 2:
				thisVersionDict['preReleaseType'] = 'a'		
				thisVersionDict['patch'] = alphaVersion[0]
				thisVersionDict['preReleaseVersion'] = alphaVersion[1]
			else:
				print "Version number error. Check Cura/util/version for details."
		elif 'b' in preReleaseValue:
			betaVersion = preReleaseValue.split('b')
			thisVersionDict['preReleaseType'] = 'b'
	else:
		thisVersionDict['minor'] == thisVersionDict[2]
		print 'This version of Cura is a GM release.'
			
	return thisVersionDict
			
def getCuraVersionXMLTree():	
	# latest		
	versionURL = 'https://dl.dropboxusercontent.com/s/b2td8x9kfj3ckrv/LatestCura.xml'
	versionXML = urllib2.urlopen("%s" % (versionURL))
	versionData = versionXML.read()
	versionXML.close()
	latestXMLTree = ElementTree.fromstring(versionData)
	
	return latestXMLTree

if __name__ == '__main__':
	print(getVersion())
