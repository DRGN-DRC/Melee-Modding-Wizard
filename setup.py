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

import main
import sys, os
from cx_Freeze import setup, Executable

# Determine whether the host environment is 64 or 32 bit.
if sys.maxsize > 2**32: environIs64bit = True
else: environIs64bit = False

# Dependencies are typically automatically detected, but they might need fine tuning.
buildOptions = dict(
	packages = [], 
	excludes = [], 
	# include_files=[
	# 	#'bin',
	# 	'imgs',
	# 	#'Installers',
	# 	#'PNG to-from TPL.bat',
	# 	#'ReadMe.txt',
	# 	#'tk', # Includes a needed folder for drag 'n drop functionality.
	# ])
)

# Check whether to preserve the console window that opens with the GUI 
# (arg 1 should be "build", second should be %useConsole%)
if sys.argv[2].startswith( 'y' ):
	base = 'Console'
else:
	base = 'Win32GUI' if sys.platform == 'win32' else None

# Strip off extra command line arguments, because setup isn't expecting them and will throw an invalid command error.
sys.argv = sys.argv[:2]

# Normalize the version string for setup ('version' below must be a string, with only numbers or dots)
simpleVersion = '.'.join( [char for char in main.programVersion.split('.') if char.isdigit()] )

setup(
	name=programName,
	version = simpleVersion,
	description = 'Modding program for SSBM',
	options = dict( build_exe = buildOptions ),
	executables = [
		Executable(
			script="main.py", 
			targetName=programName + '.exe',
			#icon='appIcon5.ico', # For the executable icon. "appIcon.png" (in main) is for the running program's window icon.
			base=base)
		]
	)

# Perform file/folder renames
print '\nCompilation complete.'

# Get the name of the new program folder that will be created in '\build\'
scriptHomeFolder = os.path.abspath( os.path.dirname(sys.argv[0]) )
programFolder = ''
for directory in os.listdir( scriptHomeFolder + '\\build' ):
	if directory.startswith( 'exe.' ):
		programFolder = directory
		break
else: # The loop above didn't break; programFolder not found
	print '\nUnable to locate the new program folder!'
	exit( 1 )
	
# Set the new program name
if environIs64bit:
	newFolderName = '{} - v{} (x64)'.format( programName, main.programVersion )
else:
	newFolderName = '{} - v{} (x86)'.format( programName, main.programVersion )
oldFolderPath = os.path.join( scriptHomeFolder, 'build', programFolder )
newFolderPath = os.path.join( scriptHomeFolder, 'build', newFolderName )
os.rename( oldFolderPath, newFolderPath )
print '\nNew program folder successfully created and renamed to "' + newFolderName + '".'

# Open the new folder
os.startfile( newFolderPath )