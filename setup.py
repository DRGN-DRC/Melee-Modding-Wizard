#!/usr/bin/python
# This file's encoding: UTF-8, so that non-ASCII characters can be used in strings.
#
#		███╗   ███╗ ███╗   ███╗ ██╗    ██╗			-------                                                   -------
#		████╗ ████║ ████╗ ████║ ██║    ██║		 # -=======---------------------------------------------------=======- #
#		██╔████╔██║ ██╔████╔██║ ██║ █╗ ██║		# ~ ~ Written by DRGN of SmashBoards (Daniel R. Cappel);  May, 2020 ~ ~ #
#		██║╚██╔╝██║ ██║╚██╔╝██║ ██║███╗██║		 #            [ Built with Python v2.7.16 and Tkinter 8.5 ]            #
#		██║ ╚═╝ ██║ ██║ ╚═╝ ██║ ╚███╔███╔╝		  # -======---------------------------------------------------======- #
#		╚═╝     ╚═╝ ╚═╝     ╚═╝  ╚══╝╚══╝ 			 ------                                                   ------
#		  -  - Melee Modding Wizard -  -  

programName = "Melee Modding Wizard"

import globalData
import sys, os, shutil
from cx_Freeze import setup, Executable

# Determine whether the host environment is 64 or 32 bit.
if sys.maxsize > 2**32: environIs64bit = True
else: environIs64bit = False


# Define what files and folders to include with the build.
# Dependencies are typically automatically detected, but they might need fine tuning.
buildOptions = dict(
	packages = [], 
	excludes = [], 
	namespace_packages = [ 
		"ruamel.yaml", # Must have ruamel.base installed as well

		# The following are for pyglet, and might not be needed after transition to Python 3
		'UserList',
		'UserString',
		'pyglet.clock'
	],
	include_files = [
		'.include',
		'bin',
		'Code Library',
		'File Descriptions',
		'fonts',
		'imgs',
		'sfx',
		'- - Asset Test.bat',
		'Code Library Manual.txt',
		'Command-Line Usage.txt',
		'MMW Manual.txt'
	]
)


if len( sys.argv ) > 2:
	# Check whether to preserve the console window that opens with the GUI 
	# (arg 1 should be "build", second should be %useConsole%)
	if sys.argv[2].startswith( 'y' ):
		base = 'Console'
	else:
		base = 'Win32GUI' if sys.platform == 'win32' else None

	# Strip off extra command line arguments, because setup isn't 
	# expecting them and will throw an invalid command error.
	sys.argv = sys.argv[:2]

else:
	base = 'Win32GUI' if sys.platform == 'win32' else None

# Normalize the version string for setup ('version' below must be a string, with only numbers or dots)
simpleVersion = '.'.join( [char for char in globalData.programVersion.split('.') if char.isdigit()] )


# Compile the program!
setup(
	name = programName,
	version = simpleVersion,
	description = 'Modding program for SSBM',
	options = dict( build_exe = buildOptions ),
	executables = [
		Executable(
			script = "main.py", 
			targetName = programName + '.exe',
			icon = '.\\imgs\\appIcon.ico', # For the executable icon. "appIcon.png" is for the running program's window icon.
			base = base)
		]
	)
print( '\nCompilation complete.' )


# Get the name of the new program folder that will be created in '\build\'
scriptHomeFolder = os.path.abspath( os.path.dirname(sys.argv[0]) )
programFolder = ''
for directory in os.listdir( scriptHomeFolder + '\\build' ):
	if directory.startswith( 'exe.' ):
		programFolder = directory
		break
else: # The loop above didn't break; programFolder not found
	print( '\nUnable to locate the new program folder!' )
	exit( 1 )


# Set the new program name
if environIs64bit:
	newFolderName = '{} - v{} (x64)'.format( programName, globalData.programVersion )
else:
	newFolderName = '{} - v{} (x86)'.format( programName, globalData.programVersion )
oldFolderPath = os.path.join( scriptHomeFolder, 'build', programFolder )
newFolderPath = os.path.join( scriptHomeFolder, 'build', newFolderName )
nameIndex = 2
while os.path.exists( newFolderPath ):
	if nameIndex > 2: # Count already added; split it off first
		newFolderPath = newFolderPath.rsplit( None, 1 )[0] # Split on first whitepace instance only
	newFolderPath += ' (' + str(nameIndex) + ')'
	nameIndex += 1
os.rename( oldFolderPath, newFolderPath )
print( '\nNew program folder successfully created and renamed to "' + os.path.basename(newFolderPath) + '".' )


# Rename the Asset Test script (the dashes are no longer that useful in the new folder)
os.chdir( newFolderPath )
os.rename( '- - Asset Test.bat', 'Asset Test.bat' )


# Delete the Micro Melee disc and temp files, if present
try:
	microMeleePath = os.path.join( newFolderPath, 'bin', "Micro Melee.iso" )
	os.remove( microMeleePath )
except: pass
try:
	tmpFilesFolder = os.path.join( newFolderPath, 'bin', 'tempFiles' )
	shutil.rmtree( tmpFilesFolder )
except: pass


# Open the new folder
os.startfile( newFolderPath )