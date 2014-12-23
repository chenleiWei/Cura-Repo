import argparse, sys, os, crypt, stat

# This is a file to be initiated instead of manually writing ./package.sh
# It updates the version number to all Cura related file
# It also inititates OSX codesigning if the user chooses the option
# This script does pre-processing prior to packaging Cura

parser = argparse.ArgumentParser()
parser.add_argument("-v", "--version", help="Version of this package")
parser.add_argument("-c", "--codesign", help="Codesign identity")
parser.add_argument("-p", "--package", choices=['darwin', 'win32', 'debian_amd64', 'debian_i386'], help="Package Cura") #win32, linux, darwin?

args = parser.parse_args()

if args.version:
	print("Updating Cura version to " + args.version)
	#function that changes current version parameter within profile settings
	v = open('currentVersion', 'w+')
	v.write(args.version)
	v.close()

	# Gets the path of the just created currentVersion file and sets it to hidden
	# This file is what is referenced when version numbers are updated
	# profile.py, package.sh pull from this file for version number
	currentVersion = os.path.join(os.path.dirname(__file__), "currentVersion")
	os.chflags(currentVersion, stat.UF_HIDDEN)

if args.codesign:
	f = open('identityFile', 'w+')
	f.write(args.codesign)
	f.close()

	os.system("[ -f identityFile ] && echo \"File exists\" || echo \"File does not exist\"")
	print("Codesigning package...")


if args.package:
	os.system("~/src/Cura/cura/package.sh " + args.package)
	print("\nGetting Cura ready for packaging with system: " + args.package)
