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
	try:
		releaseData = getCuraVersionXMLTree()
	except:
		releaseData = None
		
	if releaseData != None:
		latestReleaseDict = {}
	
		downloadLink = ''
		latestVersion = ''
		# When parsing xml file:
		# 	- .tag gets the name of the element i.e., <elementName>
		# 	- .text gets the data stored within that element
		if releaseData: 
			for release in releaseData:	
				os = str(release.attrib['os'])

				if sys.platform.lower() == os.lower():
					latestReleaseDict = {
						"major": int(release.attrib['major']),
						"minor": int(release.attrib['minor']),
						"patch": str(release.attrib['patch']),
						"preReleaseType": str(release.attrib['preReleaseType']),
						"preReleaseVersion": str(release.attrib['preReleaseVersion'])
					}
					# file name and version
					for item in release:
						if item.tag == 'filename':
							downloadLink = item.text
						if item.tag == 'version':
							latestVersion = item.text
						
			thisVersion = getVersion()
			
			# "arbitrary" version number
			if thisVersion == 'dev':
				thisVersion = '1.4.2'
				
			updateStatusDict = {"needsUpdate" : '',
													"downloadLink" : '',
													"updateVersion" : ''
													}

			thisVersionDict = getThisVersionDataForComparison(thisVersion)
			needsUpdate = compareLocalToLatest(thisVersionDict, latestReleaseDict)
			updateStatusDict['needsUpdate'] = needsUpdate	

			if needsUpdate == True:
				updateStatusDict['downloadLink'] = downloadLink
				updateStatusDict['updateVersion'] = latestVersion

			return updateStatusDict
	else:
		return None
		
def compareLocalToLatest(thisVersionDict, latestReleaseDict):
	updateVersion = False
	sameBaseVersion = True
	for label, localValue in thisVersionDict.items():
		# deals with the major, minor and patch values
		if "preRelease" not in label:
			if int(localValue) < int(latestReleaseDict[label]):
				updateVersion = True
			elif int(localValue) != int(latestReleaseDict[label]):
				sameBaseVersion = False
		
		# The conditional above will tell the user they'll need to update only if
		# the individual values for major, minor or patch of the latest version are 
		# greater than this current version; if the version numbers are the same, then
		# start comparing preRelease values
		if sameBaseVersion == True:
			if label == "preReleaseVersion" or label == "preReleaseType":
				# If the latest version doesn't have data in either the preReleaseVersion 
				# or preReleaseType variables, then that means that the version is a GM
				# and the this version is an alpha or beta
				if latestReleaseDict[label] == "":
					updateVersion = True
				else:
					# unicode comparison of 'a' to 'b' or vice versa
					if label == "preReleaseType":
						if localValue < latestReleaseDict[label]:
							updateVersion = True
					elif label == "preReleaseVersion":
						if int(localValue) < int(latestReleaseDict[label]):
							updateVersion = True
					
	return updateVersion

def getThisVersionDataForComparison(thisVersion):	
	thisVersionList = []
	thisVersionDict = {}
	versionInThirds = thisVersion.split('.')
	
	# [major, minor, patchPreReleaseType/Version]
	if len(versionInThirds) != 3:
		print "Error: Cura/util/version --> getThisVersionDataForComparison --> versionInThirds"
		print "len(versionInThirds) = ", len(versionInThirds)
		print "versionInThirds: ", versionInThirds

	# Gets details on the last part of the version number, i.e., <major>.<minor>.2a10
	# parses that last bit to figure out the patch, preReleaseType, and preRelease version if they apply
	thisVersionDict['major'] = versionInThirds[0]
	thisVersionDict['minor'] = versionInThirds[1]
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
			if len(betaVersion) == 2:
				thisVersionDict['patch'] = betaVersion[0]
				thisVersionDict['preReleaseVersion'] = betaVersion[1]
				thisVersionDict['preReleaseType'] = 'b'
			else:
				print "Version number error. Check Cura/util/version for details."
	else:
		thisVersionDict['patch'] == thisVersionDict[2]
			
	return thisVersionDict
			
def getCuraVersionXMLTree():	
	versionURL = "https://www.dropbox.com/s/d2c6quovpirtgwr/LatestCuraVersion.xml?dl=1"
	try: 
		versionXML = urllib2.urlopen("%s" % (versionURL), timeout=1)
		versionData = versionXML.read()
		versionXML.close()
		latestXMLTree = ElementTree.fromstring(versionData)	
		return latestXMLTree
	except ValueError as e:
		raise e
		return None

if __name__ == '__main__':
	print(getVersion())
