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

# Find the official thread here: 


from __future__ import print_function # Use print with (); preparation for moving to Python 3

# External dependencies
import math
import time
import struct
import random
import tkFont
import os, sys
import argparse
import Tkinter as Tk
import ttk, tkMessageBox, tkFileDialog

from threading import Thread
from subprocess import Popen, PIPE, CalledProcessError
from sys import argv as programArgs 	# Access command line arguments, and files given (drag-and-dropped) to the program icon
from binascii import hexlify, unhexlify 	# Convert from bytearrays to strings (and vice verca via unhexlify)
from PIL import Image, ImageTk, ImageDraw, ImageFilter, ImageChops
from ctypes import windll, byref, create_unicode_buffer, create_string_buffer
FR_PRIVATE  = 0x10
FR_NOT_ENUM = 0x20

# Internal dependencies
import globalData

from tools import TriCspCreator, AsmToHexConverter, CodeLookup
from disc import Disc, isExtractedDirectory
from hsdFiles import StageFile, CharCostumeFile
from basicFunctions import msg, openFolder, printStatus
from guiSubComponents import (
		cmsg, importGameFiles, DisguisedEntry, VerticalScrolledFrame,
		HexEditEntry, CharacterChooser
	)
from guiDisc import DiscTab, DiscDetailsTab
from codesManager import CodeManagerTab
from debugMenuEditor import DebugMenuEditor
from stageManager import StageManager
from audioManager import AudioManager, AudioEngine
from newTkDnD.tkDnD import TkDnD 		# Access files given (drag-and-dropped) onto the running program GUI


class FileMenu( Tk.Menu, object ):

	def __init__( self, parent, tearoff=True, *args, **kwargs ):
		super( FileMenu, self ).__init__( parent, tearoff=tearoff, *args, **kwargs )
		self.open = False
		#self.populated = False
		self.recentFilesMenu = Tk.Menu( self, tearoff=True ) # tearoff is the ability to basically turn the menu into a tools window

		self.add_cascade( label="Open Recent", menu=self.recentFilesMenu )												# Key shortcut (holding alt)
		self.add_command( label='Open Last Used Directory', underline=5, command=self.openLastUsedDir )								# L
		self.add_command( label='Open Dolphin Screenshots Folder', underline=15, command=self.openDolphinScreenshots )				# R
		self.add_command( label='Open Disc (ISO/GCM)', underline=11, command=lambda: globalData.gui.promptToOpenFile('iso') )		# I
		self.add_command( label='Open Root (Disc Directory)', underline=6, command=lambda: globalData.gui.promptToOpenRoot() )		# O		(lambda required)
		self.add_command( label='Open DAT (or USD, etc.)', underline=5, command=lambda: globalData.gui.promptToOpenFile('dat') )	# D
		self.add_command( label='Browse Code Library', underline=0, command=self.browseCodeLibrary )								# B
		self.add_separator()
		self.add_command( label='View Unsaved Changes', underline=0, command=self.showUnsavedChanges )								# V
		self.add_command( label='Save  (CTRL-S)', underline=0, command=self.save )													# S
		#self.add_command( label='Save DAT As...', underline=9, command=globalData.gui.saveDatAs )									# A
		# self.add_command( label='Save Banner As...', underline=5, command=saveBannerAs )											# B
		self.add_command( label='Run in Emulator  (CTRL-R)', underline=0, command=self.runInEmulator )								# R
		self.add_command( label='Save Disc As...', underline=10, command=self.saveDiscAs )											# A
		self.add_command( label='Close', underline=0, command=self.closeProgram )													# C

	@staticmethod
	def loadRecentFile( filepath ):

		""" This is the callback for clicking on a recent file to load from the recent files menu. 
			Verifies the file exists before loading. If it doesn't, ask to remove it from the list. """

		if os.path.exists( filepath ):
			globalData.gui.fileHandler( [filepath] ) # fileHandler expects a list.

		else: # If the file wasn't found above, prompt if they'd like to remove it from the remembered files list, and save settings to file
			if tkMessageBox.askyesno( 'Remove Broken Path?', 'The following file could not be '
										'found:\n"' + filepath + '" .\n\nWould you like to remove it from the list of recent files?' ):
				# Update the list of recent ISOs in the settings object and settings file.
				globalData.settings.remove_option( 'Recent Files', filepath.replace(':', '|') )
				with open( globalData.paths['settingsFile'], 'w') as theSettingsFile:
					globalData.settings.write( theSettingsFile )

	def repopulate( self ):

		""" This will refresh the 'Open Recent' files menu. """

		# Depopulate the whole recent files menu
		self.recentFilesMenu.delete( 0, 'last' )

		# Collect the current [separate] lists of recent ISOs, and recent DAT (or other) files, and sort their contents in order of newest to oldest.
		ISOs, DATs = globalData.getRecentFilesLists() # Returns two lists of tuples (ISOs & DATs), where each tuple is a ( filepath, dateTimeObject )
		ISOs.sort( key=lambda recentInfo: recentInfo[1], reverse=True )
		DATs.sort( key=lambda recentInfo: recentInfo[1], reverse=True )

		# Add the recent ISOs to the dropdown menu.
		self.recentFilesMenu.add_command( label='   -   Disc Images and Root Folders:', background='#d0e0ff', activeforeground='#000000', activebackground='#d0e0ff' ) # default color: 'SystemMenu'
		for isosPath in ISOs:
			filepath = isosPath[0].replace( '|', ':' )
			parentDirPlusFilename = '\\' + os.path.split( os.path.dirname( filepath ) )[-1] + '\\' + os.path.basename( filepath )
			self.recentFilesMenu.add_command( label=parentDirPlusFilename, command=lambda pathToLoad=filepath: self.loadRecentFile(pathToLoad) )

		self.recentFilesMenu.add_separator()

		# Add the recent DATs to the dropdown menu.
		self.recentFilesMenu.add_command( label='   -   DATs and Other Data Files:', background='#d0e0ff', activeforeground='#000000', activebackground='#d0e0ff' )
		for datsPath in DATs:
			filepath = datsPath[0].replace( '|', ':' )
			parentDirPlusFilename = '\\' + os.path.split( os.path.dirname( filepath ) )[-1] + '\\' + os.path.basename( filepath )
			self.recentFilesMenu.add_command( label=parentDirPlusFilename, command=lambda pathToLoad=filepath: self.loadRecentFile(pathToLoad) )

	def openLastUsedDir( self ):
		openFolder( globalData.getLastUsedDir() )

	def openDolphinScreenshots( self ):
		if globalData.disc:
			targetFolder = os.path.join( globalData.dolphinController.userFolder, 'ScreenShots', globalData.disc.gameId )
		else:
			targetFolder = os.path.join( globalData.dolphinController.userFolder, 'ScreenShots' )

		openFolder( targetFolder )

	def browseCodeLibrary( self ):

		""" Loads the Code Manager tab if it's not already present. """

		mainGui = globalData.gui

		if not mainGui.codeManagerTab:
			mainGui.codeManagerTab = CodeManagerTab( mainGui.mainTabFrame, mainGui )
		mainGui.codeManagerTab.scanCodeLibrary()

	def save( self ):			globalData.gui.save()
	def saveDiscAs( self ):		globalData.gui.saveDiscAs()
	def closeProgram( self ):	globalData.gui.onProgramClose()
	def runInEmulator( self ):	globalData.gui.runInEmulator()

	def showUnsavedChanges( self ):
		if not globalData.disc:
			msg( 'No disc has been loaded!' )
			return

		unsavedFiles = globalData.disc.getUnsavedChangedFiles()

		# Scan for code-related changes
		if globalData.gui.codeManagerTab:
			pendingCodeChanges = False
			for mod in globalData.codeMods:
				if mod.state == 'pendingEnable':
					pendingCodeChanges = True
					break
				elif mod.state == 'pendingDisable':
					pendingCodeChanges = True
					break
		
		if not pendingCodeChanges and not unsavedFiles and not globalData.disc.unsavedChanges and not globalData.disc.rebuildReason:
			msg( 'There are no changes to be saved.', 'No Unsaved Changes' )
		else:
			msg( globalData.disc.concatUnsavedChanges(unsavedFiles, basicSummary=False), 'Unsaved Changes' )


class SettingsMenu( Tk.Menu, object ):

	""" Once the checkbuttons have been created, they will stay updated in real time, since they're set using BoolVars. """

	def __init__( self, parent, tearoff=True, *args, **kwargs ): # Create the menu and its contents
		super( SettingsMenu, self ).__init__( parent, tearoff=tearoff, *args, **kwargs )
		self.open = False

		#self.add_command( label='Adjust Texture Filters', underline=15, command=setImageFilters )								# F
		
		# Disc related options
		#self.add_separator()		
		# self.add_command(label='Set General Preferences', command=setPreferences)
		self.add_checkbutton( label='Use Disc Convenience Folders', underline=9, 												# C
											variable=globalData.boolSettings['useDiscConvenienceFolders'], command=globalData.saveProgramSettings )
		# self.add_checkbutton( label='Avoid Rebuilding Disc', underline=0, 														# A
		# 									variable=globalData.boolSettings['avoidRebuildingIso'], command=globalData.saveProgramSettings )
		self.add_checkbutton( label='Back-up Disc When Rebuilding', underline=0, 												# B
											variable=globalData.boolSettings['backupOnRebuild'], command=globalData.saveProgramSettings )
		# self.add_checkbutton( label='Auto-Generate CSP Trim Colors', underline=5, 												# G
		# 									variable=globalData.boolSettings['autoGenerateCSPTrimColors'], command=globalData.saveProgramSettings )
		self.add_checkbutton( label='Always Enable Crash Reports', underline=20, 												# R
											variable=globalData.boolSettings['alwaysEnableCrashReports'], command=globalData.saveProgramSettings )
		self.add_checkbutton( label='Always Add Files Alphabetically', underline=11, 												# F
											variable=globalData.boolSettings['alwaysAddFilesAlphabetically'], command=globalData.saveProgramSettings )
		self.add_checkbutton( label='Run Dolphin in Debug Mode', underline=15, 												# D
											variable=globalData.boolSettings['runDolphinInDebugMode'], command=globalData.saveProgramSettings )
		self.add_checkbutton( label='Create Hi-Res CSPs', underline=7, 												# H
											variable=globalData.boolSettings['createHiResCSPs'], command=globalData.saveProgramSettings )
		
		# Image-editing related options
		#self.add_separator()
		# self.add_checkbutton( label='Cascade Mipmap Changes', underline=8, 
		# 									variable=globalData.boolSettings['cascadeMipmapChanges'], command=globalData.saveProgramSettings )				# M
		# self.add_checkbutton( label="Export Textures using Dolphin's Naming Convention", underline=32, 
		# 									variable=globalData.boolSettings['useDolphinNaming'], command=globalData.saveProgramSettings )					# N

	# def repopulate( self ):
	# 	# Check the settings file, in case anything has been changed manually/externally.
	# 	# Any changes from within the program will have updated these here as well.
	# 	loadSettings()


class ToolsMenu( Tk.Menu, object ):

	def __init__( self, parent, tearoff=True, *args, **kwargs ):
		super( ToolsMenu, self ).__init__( parent, tearoff=tearoff, *args, **kwargs )
		self.statusUpdateFrequency = 2000 # How frequent the GUI updates xDelta patch progress, in milliseconds
		self.open = False

	def repopulate( self ):

		# Clear all current population
		self.delete( 0, 'last' )

		""" This will refresh the 'Open Recent' files menu. """
																								# Key shortcut (holding alt)
		self.add_cascade( label="ASM <-> HEX Converter", command=lambda: AsmToHexConverter(), underline=0 )			# A
		#self.add_cascade( label="Number and Address Conversion", command=lambda: AsmToHexConverter(), underline=0 )	# N
		self.add_cascade( label='Code Lookup', command=lambda: CodeLookup(), underline=5 )							# L
		self.add_separator()
		self.add_cascade( label="Test External Stage File", command=self.testStage, underline=14 )					# S
		self.add_cascade( label="Test External Character File", command=self.testCharacter, underline=14 )			# C
		self.add_separator()
		self.add_cascade( label="Build xDelta Patch", command=self.buildPatch, underline=6 )						# X
		self.add_cascade( label="Build from Patch", command=self.notDone, underline=11 )							# P

		if globalData.disc and globalData.disc.is20XX:
			self.add_separator()
			self.add_cascade( label="Create Tri-CSP", command=self.createTriCsp, underline=1 )						# T
			self.add_cascade( label="Find Unused Stage Files", command=self.findUnusedStages, underline=0 )			# F
			#self.add_cascade( label="Parse FSM List", command=self.parseFsmList, underline=0 )						# F

	def testStage( self ):

		""" Asset Test feature. Prompts the user to choose an external stage file, initializes it, 
			fetches the Micro Melee disc build, and then sends the stage file to it for testing (booting). """

		# Prompt the user to choose a file, and get its filepath
		fileTypeOptions = [ ('Stage files', '*.dat *.usd *.0at *.1at *.2at *.3at *.4at *.5at *.6at *.7at *.8at *.9at *.aat *.bat *.cat *.dat *.eat'),
							('All files', '*.*') ]
		stageFilePath = importGameFiles( title='Choose a stage', fileTypeOptions=fileTypeOptions, category='dat' )
		if not stageFilePath: return # User canceled
		globalData.setLastUsedDir( stageFilePath, 'dat' )

		# Initialize the file and verify it's a stage
		try:
			newFileObj = StageFile( None, -1, -1, '', extPath=stageFilePath, source='file' )
			newFileObj.validate()

		except Exception as err:
			if ';' in str( err ):
				details = err.split( ';' )[1]
				msg( 'This does not appear to be a valid stage file; {}'.format(details), 'Invalid file' )
				globalData.gui.updateProgramStatus( str(err), error=True )
			else:
				msg( 'This does not appear to be a valid stage file!', 'Invalid file' )
				globalData.gui.updateProgramStatus( 'Unable to load file; ' + str(err), error=True )
			return

		# Get the micro melee disc object, and use it to test the stage
		microMelee = globalData.getMicroMelee()
		if not microMelee: return # User may have canceled the vanilla melee disc prompt
		microMelee.testStage( newFileObj )

	def testCharacter( self ):

		""" Asset Test feature. Prompts the user to choose an external character file, initializes it, 
			fetches the Micro Melee disc build, and then sends the character file to it for testing (booting). """

		# Prompt the user to choose a file, and get its filepath
		fileTypeOptions = [ ('Character files', '*.dat *.usd *.lat *.rat'), ('All files', '*.*') ]
		charFilePath = importGameFiles( title='Choose your character', fileTypeOptions=fileTypeOptions, category='dat' )
		if not charFilePath: return # User canceled
		globalData.setLastUsedDir( charFilePath, 'dat' )

		# Initialize the file and verify it's a character
		try:
			newFileObj = CharCostumeFile( None, -1, -1, '', extPath=charFilePath, source='file' )
			newFileObj.validate()

		except Exception as err:
			if ';' in str( err ):
				details = err.split( ';' )[1]
				msg( 'This does not appear to be a valid character costume file; {}'.format(details), 'Invalid file' )
				globalData.gui.updateProgramStatus( str(err), error=True )
			else:
				msg( 'This does not appear to be a valid character costume file!', 'Invalid file' )
				globalData.gui.updateProgramStatus( 'Unable to load file; ' + str(err), error=True )
			return

		# Get the micro melee disc object, and use it to test the character
		microMelee = globalData.getMicroMelee()
		if not microMelee: return # User may have canceled the vanilla melee disc prompt
		microMelee.testCharacter( newFileObj )

	def buildPatch( self ):

		""" Builds an xDelta patch from a vanilla 1.02 disc and the disc currently loaded in the GUI. """

		if not globalData.disc:
			msg( 'No disc has been loaded!' )
			return

		# Get the vanilla disc path
		vanillaDiscPath = globalData.getVanillaDiscPath()
		if not vanillaDiscPath:
			return

		# Get the xDelta executable and path to the current disc
		xDeltaPath = globalData.paths['xDelta']
		currentDiscPath = globalData.disc.filePath
		currentDiscFolder = os.path.dirname( currentDiscPath )

		# Get the disc's short title from the banner file
		bannerFile = globalData.disc.getBannerFile()
		defaultPatchName = os.path.splitext( bannerFile.shortTitle )[0] + ' patch.xdelta'

		# Get the output directory and file name for the patch
		savePath = tkFileDialog.asksaveasfilename(
			title="Where would you like to export the patch?",
			parent=globalData.gui.root,
			initialdir=currentDiscFolder,
			initialfile=defaultPatchName,
			defaultextension='.xdelta',
			filetypes=[( "xDelta patch files", '*.xdelta' ), ( "All files", "*.*" )] )

		if not savePath: # User canceled
			return

		# Send the build command to the xDelta executable
		#command = '"{}" -V "{}" "{}" "{}"'.format( xDeltaPath, vanillaDiscPath, currentDiscPath, savePath )
		command = '"{}" -B 1363148800 -e -9 -f -v -S djw -s "{}" "{}" "{}"'.format( xDeltaPath, vanillaDiscPath, currentDiscPath, savePath )
		print(command)
		
		builderThread = Thread( target=self._patchBuilderHelper, args=(currentDiscPath, command) )
		builderThread.daemon = True # Causes the thread to be stopped when the main program stops
		builderThread.start()

	def _patchBuilderHelper( self, currentDiscPath, command ):

		""" Helper method to run the xDelta build command in a separate thread (so the GUI remains responsive). 
			Build progress is captured from stderr (not stdout!) and updated to the GUI via event queue. """

		process = Popen( command, shell=False, stderr=PIPE, creationflags=0x08000000, universal_newlines=True, bufsize=1 )

		# Display initial build progress message in the program's status bar
		globalData.gui.patchBuildProgress = 0
		globalData.gui.root.after( 0, self.updatePatchBuildProgress )

		# While the process is still running, read output from it to check its progress
		discSize = os.path.getsize( currentDiscPath ) / 1048576 # Getting the size in MB
		try:
			while process.poll() is None:
				# Read the line output from the program and get how many bytes have been processed so far
				output = process.stderr.readline() # Looking for lines like "xdelta3: 127: in 8.00 MiB: out 18.7 KiB: total in 1.00 GiB: out 619 MiB: 41 ms"
				if not output or 'total in' not in output:
					continue

				totalProcessed = output.split( 'total in' )[-1]
				megaBytesProcessed, units, _ = totalProcessed.split( None, 2 )

				# Check percentage of bytes processed to total bytes to process (the size of the current disc)
				megaBytesProcessed = float( megaBytesProcessed )
				if units == 'GiB:': # Units default to MB, and switch to GB if the current disc is >= 1 GB
					megaBytesProcessed *= 1024
				globalData.gui.patchBuildProgress = megaBytesProcessed / discSize * 100
		except CalledProcessError:
			pass
		except: # Should be a parsing error
			process.returncode = 101

		if process.returncode == 0:
			globalData.gui.patchBuildProgress = 100
		else:
			globalData.gui.patchBuildProgress = process.returncode * -1

	# def updatePatchBuildProgress( self, event, progress ):
	# 	event.message = 'Building xDelta patch ({}%)'.format( round(progress, 1) )
	# 	globalData.gui.root.event_generate( '<<ProgressUpdate>>', when='tail' )
	
	def updatePatchBuildProgress( self ):
		progress = globalData.gui.patchBuildProgress

		if progress < 0: # Return code
			message = 'Unable to build xDelta patch; return code {}'.format( abs(progress) )
		elif progress == 0:
			message = 'Initializing xDelta patch creation (this may take a minute)'
			globalData.gui.root.after( 4000, self.updatePatchBuildProgress )
		elif progress < 100:
			message = 'Building xDelta patch ({}%)'.format( round(progress, 1) )
			globalData.gui.root.after( 2000, self.updatePatchBuildProgress )
		else: # Progress at or over 100%; operation complete
			message = 'Building xDelta patch ({}%)'.format( round(progress, 1) )
			globalData.gui.root.after( 3000, lambda m='xDelta patch complete': globalData.gui.updateProgramStatus( m ) )

		globalData.gui.updateProgramStatus( message )

	def notDone( self ):
		print( 'not yet supported' )

	def createTriCsp( self ):

		""" Creates a Tri-CSP (Character Select Portrait) for the CSS. """

		cspCreator = TriCspCreator()
		if not cspCreator.gimpExe or not cspCreator.config:
			return # Unable to find GIMP, or unable to load the CSP configuration file
		
		# Get the micro melee disc object
		microMelee = globalData.getMicroMelee()
		if not microMelee: return # User may have canceled the vanilla melee disc prompt

		# Prompt the user to choose a character to update
		selectionWindow = CharacterChooser( "Select a character and costume color for CSP creation:", combineZeldaSheik=True ) # References External ID
		if selectionWindow.charId == -1: return # User may have canceled selection
		charId = selectionWindow.charId
		costumeId = selectionWindow.costumeId

		# Warn of kinks that still need ironing out
		warning = ''
		if charId == 0x2: # Fox
			warning = 'gun not visible'
		elif charId == 0x9: # Marth
			warning = 'cape in incorrect position'
		
		if warning:
			warning = ( 'CSP creation for this costume has issues ({}), '.format( warning ) + \
						'so it will probably be better to use the Tri-CSP Creator program for this slot. '
						'\n\nWould you like to continue anyway?' )
			continueWithIssues = tkMessageBox.askyesno( 'Continue?', warning )
			if not continueWithIssues:
				return

		# Get CSP configuration info for this character
		charConfigDict = cspCreator.config.get( charId )
		if not charConfigDict: # Couldn't find the character dictionary
			msg( 'Unable to find CSP configuration info for external character ID 0x{:X} in "CSP Configuration.yml".'.format(charId), 'CSP Config Error' )
			globalData.gui.updateProgramStatus( 'Missing CSP configuration info', error=True )
			return

		# Backup Dolphin's current settings files and replace with new settings files
		globalData.dolphinController.backupAndReplaceSettings( cspCreator.settingsFiles )

		# Construct the path to the center screenshot
		centerScreenshotFilename = globalData.disc.constructCharFileName( charId, costumeId )[:-4] + '.png'
		centerScreenshot = os.path.join( globalData.paths['imagesFolder'], 'CSP Center Images', centerScreenshotFilename )

		# Generate the Left/Right screenshots
		leftScreenshot = cspCreator.createSideImage( microMelee, charId, costumeId, 'lat' )
		#leftScreenshot = os.path.join( globalData.paths['tempFolder'], 'left.png' ) # for testing
		if not leftScreenshot: return # Error should have already been reported
		rightScreenshot = cspCreator.createSideImage( microMelee, charId, costumeId, 'rat' )
		#rightScreenshot = os.path.join( globalData.paths['tempFolder'], 'right.png' ) # for testing
		if not rightScreenshot: return # Error should have already been reported

		# Restore previous Dolphin settings
		globalData.dolphinController.restoreSettings( cspCreator.settingsFiles )

		# Save the image in the folder with the disc if it's meant to be high-res, otherwise save it in the temp folder
		saveHighRes = globalData.checkSetting( 'createHiResCSPs' )
		if saveHighRes:
			discFolder = os.path.dirname( globalData.disc.filePath )
			outputPath = os.path.join( discFolder, 'csp.png' )
		else:
			outputPath = os.path.join( globalData.paths['tempFolder'], 'csp.png' )

		# Assemble arguments for the external GIMP Tri-CSP Creator script, and send the command to GIMP
		returnCode = cspCreator.createTriCsp( leftScreenshot, centerScreenshot, rightScreenshot, charConfigDict, outputPath, saveHighRes )
		if returnCode != 0: return # Message to the user should have already been raised
		
		if saveHighRes:
			globalData.gui.updateProgramStatus( 'High-Res CSP Created (cannot be installed to disc)' )
			return
		
		# Get the character and costume color names
		charAbbreviation = globalData.charAbbrList[charId]
		colorAbbr = globalData.costumeSlots[charAbbreviation][costumeId]
		colorName = globalData.charColorLookup[colorAbbr]

		# Build a human-readable texture name
		textureName = globalData.charList[charId]
		if textureName.endswith( 's' ):
			textureName += "' {} CSP".format( colorName )
		else:
			textureName += "'s {} CSP".format( colorName )
		
		# Import the CSP texture created above into MnSlChr
		returnCode, err1, err2 = globalData.disc.css.importCsp( outputPath, charId, costumeId, textureName )

		# Update program status and warn user of errors
		if returnCode == 0:
			globalData.gui.updateProgramStatus( '{} successfully created and installed to disc'.format(textureName) )
		elif returnCode == 1:
			globalData.gui.updateProgramStatus( '{} could not be installed; unable to find palette information'.format(textureName), error=True )
			msg( 'The CSP was successfully created, however it could not be installed to the disc because the palette could not be found in the CSS file. '
				 'This may be due to a corrupt CSS file ({}).'.format(globalData.disc.css.filename), 'CSP Installation Error', error=True )
		elif returnCode == 2:
			globalData.gui.updateProgramStatus( '{} could not be installed; the new image data is too large'.format(textureName), error=True )
			msg( 'The CSP was successfully created, however it could not be installed to the disc because the new image data is too large. '
				 'The available space for this texture is 0x{:X} bytes, however the new texture data is 0x{:X} bytes.'.format(err1, err2), 'CSP Installation Error', error=True )
		elif returnCode == 3:
			globalData.gui.updateProgramStatus( '{} could not be installed; the new palette data is too large'.format(textureName), error=True )
			msg( 'The CSP was successfully created, however it could not be installed to the disc because the new palette data is too large. '
				 "The max number of colors for this texture's palette is {} colors, however the new palette has {} colors.".format(err1, err2), 'CSP Installation Error', error=True )

	def findUnusedStages( self ):

		""" Searches a disc or root directory for stage files that won't be used by the game.
			This is done by checking for files referenced by the DOL (and 20XX Stage Swap Table 
			if it's 20XX) to determine what file names are referenced, and checking if those stage 
			files are present. """

		# The following set of stages are some that are referenced/enabled by code, and wouldn't be found in the search below
		stagesFromCodes = set([
			'GrPs1.dat', 'GrPs2.dat', 'GrPs3.dat', 'GrPs4.dat', # Pokemon Stadium transformations
			'GrNFg.0at', 'GrNFg.1at', 'GrNFg.2at', # Mount Olympus (FigureGet/Greece) variations (20XX)
			'GrGd.1at', 'GrGd.2at', # Jungle Japes Hacked variations (20XX)
			'GrNKr.1at', 'GrNKr.2at', # Mushroom Kingdom Adventure variations (20XX)
		])

		# Check for files referenced by the game
		referecedFiles = globalData.disc.checkReferencedStageFiles()

		# Check for stages in the disc
		discFiles = set()
		for fileObj in globalData.disc.files.itervalues():
			if fileObj.__class__ == StageFile:
				discFiles.add( fileObj.filename )

		# Cross reference stages defined in the DOL and SST with those found in the disc
		nonReferencedFiles = discFiles - referecedFiles - stagesFromCodes

		if nonReferencedFiles:
			message = 'These stage files are in the disc, but do\nnot appear to be referenced by the game:\n\n' + ', '.join( nonReferencedFiles )
			cmsg( message, 'Non-Referenced Stage Files' )
		else:
			cmsg( 'No files were found in the disc that do not appear to be referenced by the game.', 'Non-Referenced Stage Files' )

	def parseFsmList( self ):

		""" Currently just a quick ad-hoc function for testing. """

		print( 'FSM List at 0x19D0' )
		fsmList = globalData.disc.dol.getData( 0x19D0, 0x498 )
		offset = 0

		while True:
			entry = fsmList[offset:offset+8]
			if not entry:
				break
			offset += 8

			charId, timerStart, actionInfo, speedMultiplier = struct.unpack( '>BBHf', entry )
			actionTag = actionInfo & 0xF000
			actionId = actionInfo & 0xFFF

			if charId == 0xFF:
				charName = 'All'
			else:
				charName = globalData.charList[charId] # Using external character ID

			print( charName, '', timerStart, actionTag, actionId, speedMultiplier )


class MainMenuCanvas( Tk.Canvas ):

	imageSets = set( ['ABG00', 'ABG01'] ) # Animated Backgrounds; will be selected randomly during image loading

	def __init__( self, mainGui, width, height ):
		Tk.Canvas.__init__( self, mainGui.mainTabFrame, width=width, height=height, borderwidth=0, highlightthickness=0, background='black' )
		def noScroll( arg1, arg2 ): pass
		self.yview_scroll = noScroll

		self.mainMenuFolder = os.path.join( globalData.paths['imagesFolder'], 'Main Menu' )
		self.mainGui = mainGui
		self.imageSet = ''
		self.afterId = -1
		self.minIdleTime = 5 # Before next animation (character swap or wireframe effect)
		self.maxIdleTime = 12
		self.borderImgs = {}
		self.borderParts = {}	# key=partName, value=canvasID
		self.optionInfo = {}	# key=canvasId, value=( borderColor, clickCallback )

		self.mainBorderWidth = 800 # Keep this an even number
		self.mainBorderHeight = 530
		self.bottomTextWidth = 290

		# Load and apply the main background image
		self.create_image( 500, 375, image=mainGui.imageBank('bg', 'Main Menu'), anchor='center' )

		# Load the mask used to create the wireframe effect
		maskPath = os.path.join( self.mainMenuFolder, "ABGM.png" )
		self.origMask = Image.open( maskPath )

		# Load menu items
		self.loadBorderImages( '#394aa6' ) # Blue
		#self.loadBorderImages( '#a13728' ) # Red
		self.initMainBorder()
		self.initOptionImages()
		self.menuOptionCount = 5
		self.addMenuOption( 'Disc Management', '#394aa6', self.loadDiscManagement ) # blue
		self.addMenuOption( 'Code Manager', '#a13728', self.loadDiscManagement ) # red
		self.addMenuOption( 'Stage Manager', '#077523', self.loadDiscManagement ) # green
		self.addMenuOption( 'Audio Manager', '#9f853b', self.loadDiscManagement ) # yellow
		self.addMenuOption( 'Purple Option', '#582493', self.loadDiscManagement ) # purple

		# Load the character image
		self.loadImageSet()

		# Add click and hover event handlers
		self.tag_bind( 'menuOptions', '<1>', self.menuOptionClicked )
		self.tag_bind( 'menuOptions', '<Enter>', self.menuOptionHovered )
		self.tag_bind( 'menuOptions', '<Leave>', self.menuOptionUnhovered )

		# Start a timer to count down to creating the wireframe effect or swap images
		timeTilNextAnim = random.randint( self.minIdleTime, self.maxIdleTime / 2 ) # Shorter first idle
		print( 'first anim should trigger in', timeTilNextAnim, 'seconds' )
		self.afterId = self.after( timeTilNextAnim*1000, self.updateBg )

		# Bind events
		self.mainGui.root.bind( '<<wireframePass>>', self.updateWireframePass )

	def initFont( self, fontName, private=True, enumerable=False ):
		
		""" Makes fonts located in file `fontpath` available to the font system.

			`private`     if True, other processes cannot see this font, and this 
						font will be unloaded when the process dies
			`enumerable`  if True, this font will appear when enumerating fonts

			See https://msdn.microsoft.com/en-us/library/dd183327(VS.85).aspx
		"""

		# This function was taken from:
		# https://github.com/ifwe/digsby/blob/f5fe00244744aa131e07f09348d10563f3d8fa99/digsby/src/gui/native/win/winfonts.py#L15
		# This function is written for Python 2.x. For 3.x, you have to convert the isinstance checks to bytes and str

		fontpath = os.path.join( globalData.paths['fontsFolder'], fontName )

		if isinstance(fontpath, str):
			pathbuf = create_string_buffer(fontpath)
			AddFontResourceEx = windll.gdi32.AddFontResourceExA
		elif isinstance(fontpath, unicode):
			pathbuf = create_unicode_buffer(fontpath)
			AddFontResourceEx = windll.gdi32.AddFontResourceExW
		else:
			raise TypeError('fontpath must be of type str or unicode')

		flags = (FR_PRIVATE if private else 0) | (FR_NOT_ENUM if not enumerable else 0)
		numFontsAdded = AddFontResourceEx(byref(pathbuf), flags, 0)

		return bool( numFontsAdded )

	def loadImageSet( self, loadTransparent=False ):
		# Randomly select an image set (without selecting the current one)
		self.imageSet = random.choice( list(self.imageSets.difference( [self.imageSet] )) )
		print( 'Loading image set', self.imageSet )

		# Load the necessary images (not using the imageBank because we want to work with these as PIL Image objects)
		wireframePath = os.path.join( self.mainMenuFolder, self.imageSet + "W.png" )
		topImgPath = os.path.join( self.mainMenuFolder, self.imageSet + ".png" )

		self.wireframeLayer = Image.open( wireframePath ).convert( 'RGBA' )
		self.origTopLayer = Image.open( topImgPath ).convert( 'RGBA' )
		self.topLayer = ImageTk.PhotoImage( self.origTopLayer )

		# Add the top and wireframe images to the canvas
		originY = ( int(self['height']) - self.mainBorderHeight ) / 2
		originX = ( int(self['width']) - self.mainBorderWidth ) / 2
		print('originX:', originX)
		bottomBorderY = originY + self.mainBorderHeight - 18
		# if not loadTransparent:
		#self.wireframeLayerId = self.create_image( 635, bottomBorderY, image=ImageTk.PhotoImage( self.wireframeLayer ), anchor='center' )
		self.topLayerId = self.create_image( 635, bottomBorderY, image=self.topLayer, anchor='s' )

		# Load the alpha channel as a new image (for use with the mask)
		self.fullSizeMask = self.wireframeLayer.getchannel( 'A' ) # Returns a new image, in 'L' mode, of the given channel
		#self.maskBase = Image.new( 'L', self.origTopLayer.size, 255 )
	
	def colorizeImage( self, image, color ):

		""" Applies the given color to a given black-and-white image, and retuns it. """

		blankImage = Image.new( 'RGBA', image.size, (0, 0, 0, 0) )
		colorScreen = Image.new( 'RGBA', image.size, color )
		return Image.composite( colorScreen, blankImage, image )

	def loadBorderImages( self, color ):

		""" Cuts up the primary border image into multiple pieces, colorizes them, 
			and converts them into images Tkinter can use on the canvas. Storage is 
			needed to prevent garbage collection of the images, however this also 
			means this function can just be called again with a different color 
			to automatically update the images used in the canvas widget. """

		imagePath = os.path.join( self.mainMenuFolder, "mainBorder.png" )
		image = Image.open( imagePath )

		# Add color to the image, and combine it with the 'shadow' portion (dark middle part)
		colorized = self.colorizeImage( image, color )


		widthFillTop = self.mainBorderWidth - 118 # -26 - 66 - 26
		widthFillBot = self.mainBorderWidth - self.bottomTextWidth - 76 # -26 - 26 - 12 - 12
		widthFillBotLeft = int( math.floor(widthFillBot / 7.0) )
		widthFillBotRight = widthFillBot - widthFillBotLeft
		#print( widthFillBot, '-', widthFillBotLeft, '=', widthFillBotRight )
		heightFill = self.mainBorderHeight - 102 # -70 - 32

		cropped = colorized.crop( (0, 70, 26, 88) )
		resized = cropped.resize( (26, heightFill) )
		self.borderImgs['borderLeft'] = ImageTk.PhotoImage( resized )

		cropped = colorized.crop( (0, 0, 26, 70) )
		self.borderImgs['borderTopLeft'] = ImageTk.PhotoImage( cropped )

		cropped = colorized.crop( (26, 0, 48, 70) )
		resized = cropped.resize( (widthFillTop/2, 70) )
		self.borderImgs['borderTopLeftFill'] = ImageTk.PhotoImage( resized )

		cropped = colorized.crop( (48, 0, 114, 70) )
		self.borderImgs['borderTopCenter'] = ImageTk.PhotoImage( cropped )

		cropped = colorized.crop( (114, 0, 150, 70) )
		resized = cropped.resize( (widthFillTop/2, 70) )
		self.borderImgs['borderTopRightFill'] = ImageTk.PhotoImage( resized )

		cropped = colorized.crop( (150, 0, 176, 70) )
		self.borderImgs['borderTopRight'] = ImageTk.PhotoImage( cropped )

		cropped = colorized.crop( (150, 70, 176, 88) )
		resized = cropped.resize( (26, heightFill) )
		self.borderImgs['borderRight'] = ImageTk.PhotoImage( resized )

		cropped = colorized.crop( (150, 88, 176, 120) )
		self.borderImgs['borderBottomRight'] = ImageTk.PhotoImage( cropped )

		cropped = colorized.crop( (138, 88, 150, 120) )
		resized = cropped.resize( (widthFillBotRight, 32) )
		self.borderImgs['borderBottomRightFill'] = ImageTk.PhotoImage( resized )
		resized = cropped.resize( (widthFillBotLeft, 32) )
		flipped = resized.transpose( Image.FLIP_LEFT_RIGHT )
		self.borderImgs['borderBottomLeftFill'] = ImageTk.PhotoImage( flipped )

		cropped = colorized.crop( (126, 88, 138, 120) )
		self.borderImgs['borderBottomRightInner'] = ImageTk.PhotoImage( cropped )
		flipped = cropped.transpose( Image.FLIP_LEFT_RIGHT )
		self.borderImgs['borderBottomLeftInner'] = ImageTk.PhotoImage( flipped )

		cropped = colorized.crop( (50, 88, 126, 120) )
		resized = cropped.resize( (self.bottomTextWidth, 32) )
		self.borderImgs['borderBottomCenter'] = ImageTk.PhotoImage( resized )

		cropped = colorized.crop( (0, 88, 26, 120) )
		self.borderImgs['borderBottomLeft'] = ImageTk.PhotoImage( cropped )
		
		cropped = colorized.crop( (26, 70, 150, 88) )
		resized = cropped.resize( (self.mainBorderWidth-52, heightFill) )
		self.borderImgs['borderMiddle'] = ImageTk.PhotoImage( resized )

	def refreshBorderImages( self ):

		self.itemconfig( self.borderParts['borderLeft'], image=self.borderImgs['borderLeft'] )

		self.itemconfig( self.borderParts['borderTopLeft'], image=self.borderImgs['borderTopLeft'] )
		self.itemconfig( self.borderParts['borderTopLeftFill'], image=self.borderImgs['borderTopLeftFill'] )
		self.itemconfig( self.borderParts['borderTopCenter'], image=self.borderImgs['borderTopCenter'] )
		self.itemconfig( self.borderParts['borderTopRightFill'], image=self.borderImgs['borderTopRightFill'] )
		self.itemconfig( self.borderParts['borderTopRight'], image=self.borderImgs['borderTopRight'] )

		self.itemconfig( self.borderParts['borderRight'], image=self.borderImgs['borderRight'] )

		self.itemconfig( self.borderParts['borderBottomRight'], image=self.borderImgs['borderBottomRight'] )
		self.itemconfig( self.borderParts['borderBottomRightFill'], image=self.borderImgs['borderBottomRightFill'] )
		self.itemconfig( self.borderParts['borderBottomRightInner'], image=self.borderImgs['borderBottomRightInner'] )
		self.itemconfig( self.borderParts['borderBottomCenter'], image=self.borderImgs['borderBottomCenter'] )
		self.itemconfig( self.borderParts['borderBottomLeftInner'], image=self.borderImgs['borderBottomLeftInner'] )
		self.itemconfig( self.borderParts['borderBottomLeftFill'], image=self.borderImgs['borderBottomLeftFill'] )
		self.itemconfig( self.borderParts['borderBottomLeft'], image=self.borderImgs['borderBottomLeft'] )

		self.itemconfig( self.borderParts['borderMiddle'], image=self.borderImgs['borderMiddle'] )

	def initMainBorder( self ):

		""" Places all images for the main background on the canvas. """

		originX = ( int(self['width']) - self.mainBorderWidth ) / 2
		originY = ( int(self['height']) - self.mainBorderHeight ) / 2
		widthFillTop = self.mainBorderWidth - 118 # -26 - 66 - 26
		widthFillBot = self.mainBorderWidth - self.bottomTextWidth - 76 # -26 - 26 - 12 - 12
		widthFillBotLeft = int( math.floor(widthFillBot / 7.0) )
		widthFillBotRight = widthFillBot - widthFillBotLeft
		heightFill = self.mainBorderHeight - 102 # -70 - 32
		rightSideX = originX + 92 + widthFillTop # 26 + 66
		bottomY = originY + 70 + heightFill

		# Left
		self.borderParts['borderLeft'] = self.create_image( originX, originY+70, image=self.borderImgs['borderLeft'], anchor='nw', tags=('mainBorder',) )

		# Top
		self.borderParts['borderTopLeft'] = self.create_image( originX, originY, image=self.borderImgs['borderTopLeft'], anchor='nw', tags=('mainBorder',) )
		self.borderParts['borderTopLeftFill'] = self.create_image( originX+26, originY, image=self.borderImgs['borderTopLeftFill'], anchor='nw', tags=('mainBorder',) )
		self.borderParts['borderTopCenter'] = self.create_image( originX+26+(widthFillTop/2), originY, image=self.borderImgs['borderTopCenter'], anchor='nw', tags=('mainBorder',) )
		self.borderParts['borderTopRightFill'] = self.create_image( originX+26+(widthFillTop/2)+66, originY, image=self.borderImgs['borderTopRightFill'], anchor='nw', tags=('mainBorder',) )
		self.borderParts['borderTopRight'] = self.create_image( rightSideX, originY, image=self.borderImgs['borderTopRight'], anchor='nw', tags=('mainBorder',) )
		
		# Right
		self.borderParts['borderRight'] = self.create_image( rightSideX, originY+70, image=self.borderImgs['borderRight'], anchor='nw', tags=('mainBorder',) )

		# Bottom
		self.borderParts['borderBottomRight'] = self.create_image( rightSideX, bottomY, image=self.borderImgs['borderBottomRight'], anchor='nw', tags=('mainBorder',) )
		self.borderParts['borderBottomRightFill'] = self.create_image( rightSideX, bottomY, image=self.borderImgs['borderBottomRightFill'], anchor='ne', tags=('mainBorder',) )
		self.borderParts['borderBottomRightInner'] = self.create_image( rightSideX-widthFillBotRight, bottomY, image=self.borderImgs['borderBottomRightInner'], anchor='ne', tags=('mainBorder',) )
		self.borderParts['borderBottomCenter'] = self.create_image( originX+38+widthFillBotLeft, bottomY, image=self.borderImgs['borderBottomCenter'], anchor='nw', tags=('mainBorder',) )
		self.borderParts['borderBottomLeftInner'] = self.create_image( originX+26+widthFillBotLeft, bottomY, image=self.borderImgs['borderBottomLeftInner'], anchor='nw', tags=('mainBorder',) )
		self.borderParts['borderBottomLeftFill'] = self.create_image( originX+26, bottomY, image=self.borderImgs['borderBottomLeftFill'], anchor='nw', tags=('mainBorder',) )
		self.borderParts['borderBottomLeft'] = self.create_image( originX, bottomY, image=self.borderImgs['borderBottomLeft'], anchor='nw', tags=('mainBorder',) )
		
		# Middle
		self.borderParts['borderMiddle'] = self.create_image( originX+26, originY+70, image=self.borderImgs['borderMiddle'], anchor='nw', tags=('mainBorder',) )

		# Calculate position of the bottom text and its background
		textXCoord = originX + 38 + widthFillBotLeft + (self.bottomTextWidth/2)
		textYCoord = bottomY + 7

		# Create the bottom text background bracket
		imagePath = os.path.join( self.mainMenuFolder, "borderCenterBracket.png" )
		image = Image.open( imagePath )
		side = image.crop( (0, 0, 10, 32) )
		middle = image.crop( (10, 0, 38, 32) )
		bracketImage = middle.resize( (self.bottomTextWidth+12, 32) )
		bracketImage.paste( side, (0, 0) )
		bracketImage.paste( side.transpose(Image.FLIP_LEFT_RIGHT), (self.bottomTextWidth+2, 0) )
		self.borderImgs['borderCenterBracket'] = ImageTk.PhotoImage( bracketImage )
		self.create_image( textXCoord, textYCoord, image=self.borderImgs['borderCenterBracket'], anchor='n', tags=('mainBorder',) )

		# Add top text
		self.initFont( 'A-OTF Folk Pro, Bold.otf' ) # Family = 'A-OTF Folk Pro B'; find family names with 'tkFont.families()'
		text = u'Main Menu'
		text = u'\u2009'.join( list(text) ) # Rejoin with the unicode 'Thin Space' to add some kerning (https://www.fileformat.info/info/unicode/category/Zs/list.htm)
		italicFont = tkFont.Font( family='A-OTF Folk Pro B', size=12, slant='italic', weight='bold' )
		self.create_text( originX+26+widthFillTop/4, originY+4, text=text, anchor='n', tags=('mainBorder',), font=italicFont, fill='#aaaaaa' )

		# Add bottom text
		text = 'Choose a category to begin.'
		text = u'\u200A'.join( list(text) )
		self.create_text( textXCoord, textYCoord+4, text=text, anchor='n', tags=('mainBorder',), font=('A-OTF Folk Pro B', 11), fill='#aaaaaa' )

	def initOptionImages( self ):
		
		""" Image storage for option background images, to prevent 
			garbage collection and redundant image processing. """

		self.optionBgMiddleImages = {}

		# Load the option background image
		imagePath = os.path.join( self.mainMenuFolder, "optionBg.png" )
		image = Image.open( imagePath )

		# Add color to the image, and split it into parts
		colorized = self.colorizeImage( image, '#cc9933' )
		self.optionBgLeftImage = colorized.crop( (0, 0, 20, 48) )
		self.optionBgMiddlebase = colorized.crop( (20, 0, 23, 48) ) # Width modified later
		self.optionBgRightImage = colorized.crop( (23, 0, 64, 48) )

		self.optionBgLeftImage = ImageTk.PhotoImage( self.optionBgLeftImage )
		self.optionBgRightImage = ImageTk.PhotoImage( self.optionBgRightImage )

	def addMenuOption( self, text, borderColor, clickCallback ):

		xOffset = 70 # From the main border left origin
		yOffset = -12
		
		# Calculate main menu border position
		originX = ( int(self['width']) - self.mainBorderWidth ) / 2
		originY = ( int(self['height']) - self.mainBorderHeight ) / 2
		heightFill = self.mainBorderHeight - 102 # -70 - 32

		# Add the text object
		spacingBetweenOptions = heightFill / ( self.menuOptionCount + 1 )
		y = originY + 70 + spacingBetweenOptions * ( len( self.find_withtag('menuOptions') ) + 1 )
		textObj = self.create_text( originX+xOffset, y, text=text, anchor='w', tags=('menuOptions',), font=('A-OTF Folk Pro B', 11), fill='#aaaaaa' )

		# Finish creating the middle background element and store it
		boundingBox = self.bbox( textObj )
		textWidth = boundingBox[2] - boundingBox[0]
		bgMiddle = self.optionBgMiddleImages.get( textWidth )
		if not bgMiddle: # Need to create a new image for this width
			resizedImage = self.optionBgMiddlebase.resize( (textWidth+8, 48) )
			self.optionBgMiddleImages[textWidth] = bgMiddle = ImageTk.PhotoImage( resizedImage )

		# Add the option background image objects
		self.create_image( originX+xOffset-26, y+yOffset, image=self.optionBgLeftImage, anchor='nw', tags=('menuOptionsBg',) )
		self.create_image( originX+xOffset-4, y+yOffset, image=bgMiddle, anchor='nw', tags=('menuOptionsBg',) )
		self.create_image( originX+xOffset+textWidth+4, y+yOffset, image=self.optionBgRightImage, anchor='nw', tags=('menuOptions',) )
		self.tag_raise( textObj, 'menuOptionsBg' )

		# Store info on this canvas object to be recovered by events later
		self.optionInfo[textObj] = ( borderColor, clickCallback )

	def menuOptionClicked( self, event ):

		""" Initial method called when a canvas stage icon is clicked on. Determines and 
			sets the internal stage ID of the icon that was clicked on, and calls the main
			stage selection method. """
		
		globalData.gui.updateProgramStatus( '' )

		# Determine which canvas item was clicked on, and use that to look up the stage
		canvas = event.widget
		itemId = canvas.find_closest( event.x, event.y )[0]
		borderColor, clickCallback = self.optionInfo[itemId]

		clickCallback()

	def menuOptionHovered( self, event ):

		# Determine which canvas item was clicked on, and use that to look up the stage
		canvas = event.widget
		itemId = canvas.find_closest( event.x, event.y )[0]
		borderColor, clickCallback = self.optionInfo.get( itemId, (None, None) )
		if not borderColor: return

		self['cursor'] = 'hand2'
		self.loadBorderImages( borderColor )
		self.refreshBorderImages()
	
	def menuOptionUnhovered( self, event ):
		self['cursor'] = ''

	def loadDiscManagement( self ):
		print( 'testing' )

	def updateBg( self ):
		if not self.winfo_ismapped():
			return

		try:
			if random.choice( (0, 1, 2) ): # 2/3 chance to do a wireframe pass
				#self.doWireframePass()
				self._maskPosition = -self.origMask.height
				#self.updateWireframePass()
				#self.mainGui.root.event_generate( '<<wireframePass>>', when='tail' )
			else:
				self.fadeInNewBgImage()

			if self.winfo_ismapped():
				timeTilNextAnim = random.randint( self.minIdleTime, self.maxIdleTime )
				print( 'next anim should trigger in', timeTilNextAnim, 'seconds' )
				self.afterId = self.after( timeTilNextAnim*1000, self.updateBg )
		
		except: # If an error occurred, the widget is likely no longer attached to the GUI
			print( 'Exited bg animation edit' )
			pass

	def remove( self ):

		""" Cancel the next pending animation, and remove the menu from the GUI. """
		
		self.after_cancel( self.afterId )

		geomManager = self.winfo_manager()

		if geomManager == 'grid':
			self.grid_remove()
		elif geomManager == 'pack':
			self.pack_forget()
		elif geomManager == 'place':
			self.place_forget()

	def doWireframePass( self ):
		maskPosition = -self.origMask.height
		processTimes = []
		sleepsSkipped = 0

		while maskPosition < (self.origMask.height + self.origTopLayer.height):
			tic = time.clock()

			# Copy the mask of the top layer's alpha channel, and combine it with the mask
			mask = self.fullSizeMask.copy()
			mask.paste( self.origMask, (0, maskPosition) )
			self.topLayer = ImageTk.PhotoImage( Image.composite(self.origTopLayer, self.wireframeLayer, mask) )

			# mask = Image.new( 'L', self.origTopLayer.size, 255 )
			# mask.paste( self.origMask, (0, maskPosition) )
			# mask = ImageChops.multiply( self.fullSizeMask, mask )
			# self.origTopLayer.putalpha( mask )
			# self.topLayer = ImageTk.PhotoImage( self.origTopLayer )

			maskPosition += 2
			toc = time.clock()
			
			# Sleep for a short amount of time before displaying the new image
			processTimes.append( toc-tic )
			timeToSleep = .040 - (toc - tic)
			if timeToSleep > 0:
				time.sleep( timeToSleep )
			else:
				sleepsSkipped += 1

			# Update the display with the new image
			self.itemconfigure( self.topLayerId, image=self.topLayer )
			self.update()

		# print( 'sleeps skipped:', sleepsSkipped, 'out of', len(processTimes) )
		# print( 'ave frame processing time:', sum(processTimes) / len(processTimes) )

	def updateWireframePass( self, event ):
		# Copy the mask of the top layer's alpha channel, and combine it with the mask
		mask = self.fullSizeMask.copy()
		mask.paste( self.origMask, (0, self._maskPosition) )
		self.topLayer = ImageTk.PhotoImage( Image.composite(self.origTopLayer, self.wireframeLayer, mask) )

		# Update the display with the new image
		self.itemconfigure( self.topLayerId, image=self.topLayer )
		print('processed at', self._maskPosition)

		self._maskPosition += 2

		if self._maskPosition < (self.origMask.height + self.origTopLayer.height):
			self.mainGui.root.event_generate( '<<wireframePass>>', when='tail' )

	def fadeInNewBgImage( self ):
		transparentMask = Image.new( 'RGBA', self.origTopLayer.size, (0,0,0,0) )
		sleepTime = .03
		stepSize = 2
		#fadeTimes = []

		# Temporarily remove the back layer for the fade
		# self.delete( self.wireframeLayerId )

		# Fade out the current image
		for i in range( 100, -stepSize, -stepSize ):
			tic = time.clock()
			# Update the layer's alpha
			#self.origTopLayer.putalpha( i )
			#self.topLayer = ImageTk.PhotoImage( self.origTopLayer )
			self.topLayer = ImageTk.PhotoImage( Image.blend(transparentMask, self.origTopLayer, float(i)/100) )
			self.itemconfigure( self.topLayerId, image=self.topLayer )
			self.update()
			toc = time.clock()
			#fadeTimes.append( toc-tic )
			timeToSleep = sleepTime - (toc - tic)
			if timeToSleep > 0:
				time.sleep( timeToSleep )
		# print( 'ave fade time:', sum(fadeTimes) / len(fadeTimes) )
		# fadeTimes = []

		# Load the images for the new image set
		self.loadImageSet( loadTransparent=True )

		for i in range( 0, 100+stepSize, stepSize ):
			tic = time.clock()
			# Update the layer's alpha
			#self.origTopLayer.putalpha( i )
			#self.topLayer = ImageTk.PhotoImage( self.origTopLayer )
			self.topLayer = ImageTk.PhotoImage( Image.blend(transparentMask, self.origTopLayer, float(i)/100) )
			self.itemconfigure( self.topLayerId, image=self.topLayer )
			self.update()
			toc = time.clock()
			#fadeTimes.append( toc-tic )
			timeToSleep = sleepTime - (toc - tic)
			if timeToSleep > 0:
				time.sleep( timeToSleep )

		# self.wireframeLayerId = self.create_image( 500, 375, image=self.mainGui.imageBank(self.imageSet + 'W'), anchor='center' )
		# self.tag_lower( self.wireframeLayerId, self.topLayerId )
		#print( 'ave fade time:', sum(fadeTimes) / len(fadeTimes) )


#																		/------------\
#	====================================================================   Main GUI   =========
#																		\------------/

class MainGui( Tk.Frame, object ):

	def __init__( self ): # Build the interface

		self.root = Tk.Tk()
		self.root.withdraw() # Keeps the GUI minimized until it is fully generated
		self.style = ttk.Style()

		globalData.loadProgramSettings( True ) # Load using BooleanVars. Must be done after creating Tk.root

		self._imageBank = {} # Repository for all GUI related images
		self.audioEngine = None
		self.patchBuildProgress = -1

		self.defaultWindowWidth = 1000
		self.defaultWindowHeight = 750
		self.defaultSystemBgColor = self.root.cget( 'background' )

		# Font control/adjustments
		default_font = tkFont.nametofont( "TkDefaultFont" )
		#print(default_font.actual())
		self.defaultFontSize = default_font.actual()['size']
		#default_font.configure( size=30 ) # Use negative values to specify in pixel height
		#self.root.option_add( "*Font", default_font ) # Use this to apply the default font to be used everywhere
		
		# Build the main program window
		self.root.tk.call( 'wm', 'iconphoto', self.root._w, self.imageBank('appIcon') )
		self.root.geometry( str(self.defaultWindowWidth) + 'x' + str(self.defaultWindowHeight) + '+100+50' )
		self.root.title( "Melee Modding Wizard - v" + globalData.programVersion )
		self.root.minsize( width=500, height=400 )
		self.dnd = TkDnD( self.root )
		self.root.protocol( 'WM_DELETE_WINDOW', self.onProgramClose ) # Overrides the standard window close button.
		
		# Main Menu Bar & Context Menus
		self.menubar = Tk.Menu( self.root )																						# Keyboard shortcut:
		self.menubar.add_cascade( label='File', menu=FileMenu( self.menubar ), underline=0 )							# File 			[F]
		self.menubar.add_cascade( label='Settings', menu=SettingsMenu( self.menubar ), underline=0 )					# Settings 		[S]
		self.menubar.add_cascade( label='Tools', menu=ToolsMenu( self.menubar ), underline=0 )							# Tools			[T]
		#self.menubar.add_cascade( label='About', menu=AboutMenu( self.menubar ), underline=0 )							# File 			[A]

		#self.style.configure( 'MainMenuBg.TNotebook', background='black' )
		self.mainTabFrame = ttk.Notebook( self.root ) # , style='MainMenuBg.TNotebook'
		self.dnd.bindtarget( self.mainTabFrame, self.dndHandler, 'text/uri-list' )

		self.discTab = None
		self.discDetailsTab = None
		self.codeManagerTab = None
		self.menuEditorTab = None
		self.stageManagerTab = None
		self.audioManagerTab = None

		self.mainTabFrame.grid( column=0, row=0, sticky='nsew' )
		self.mainTabFrame.bind( '<<NotebookTabChanged>>', self.onMainTabChanged )

		# Set the bottom status message
		self.statusLabel = ttk.Label( self.root, text='Ready' )
		self.statusLabel.grid( column=0, row=1, sticky='w', pady=2, padx=7 )

		# Set the background and main menu
		self.mainMenu = MainMenuCanvas( self, self.defaultWindowWidth, self.defaultWindowHeight )
		self.mainMenu.place( relx=0.5, rely=0.5, anchor='center' )
		# self.style.configure( 'MainMenuBg', background='black' )
		# self['style'] = 'MainMenuBg'

		# Configure resize behavior
		self.root.columnconfigure( 'all', weight=1 )
		self.root.rowconfigure( 0, weight=1 )
		self.root.rowconfigure( 1, weight=0 ) # No vertical resize allocation for status bar

		# Set up the scroll handler. Unbinding native scroll functionality on some classes to prevent problems when scrolling on top of other widgets
		self.root.unbind_class( 'Text', '<MouseWheel>' ) # Allows onMouseWheelScroll below to handle this
		self.root.unbind_class( 'Treeview', '<MouseWheel>' ) # Allows onMouseWheelScroll below to handle this
		self.root.bind_all( "<MouseWheel>", self.onMouseWheelScroll )
		#self.root.bind( '<<ProgressUpdate>>', self.updateProgressDisplay )
		
		# Keyboard hotkeys
		self.root.bind( '<Control-s>', lambda event: self.save() ) # Using lambda to prevent passing on the event arg to the method
		self.root.bind( '<Control-S>', lambda event: self.save() ) # Using lambda to prevent passing on the event arg to the method

		# 'Select all' functionality in text entry widgets
		self.root.bind_class( "Text", "<Control-a>", self.selectAll )
		self.root.bind_class( "Text", "<Control-A>", self.selectAll )
		self.root.bind_class( "TEntry", "<Control-a>", self.selectAll )
		self.root.bind_class( "TEntry", "<Control-A>", self.selectAll )

		# Run-in-Emulator feature
		self.root.bind( '<Control-r>', self.runInEmulator )
		self.root.bind( '<Control-R>', self.runInEmulator )
		self.root.bind( '<F5>', self.saveAndRun )
		
		# Finish configuring the main menu bar
		self.root.config( menu=self.menubar )
		self.menubar.bind( "<<MenuSelect>>", self.updateMainMenuOptions )

		self.root.deiconify() # GUI has been minimized until rendering was complete. This brings it to the foreground

	# def updateProgressDisplay( self, event ):

	# 	""" Used to handle progress updates from other threads using the event queue.
	# 		(Other threads should not directly update the GUI themselves.) """

	# 	self.updateProgramStatus( event.message )

	def updateProgramStatus( self, newStatus, warning=False, error=False, success=False, forceUpdate=False ):

		""" Updates the status bar at the very bottom of the interface. """

		if warning:
			statusColor = '#992' # yellow
		elif error:
			statusColor = '#a34343' # red; some change(s) not yet saved.
		elif success:
			statusColor = '#292' # A green color, indicating no changes awaiting save.
		else:
			statusColor = 'black'

		# Update the label widget's color and message
		self.statusLabel['foreground'] = statusColor
		self.statusLabel['text'] = newStatus

		# Force the GUI to update now rather than waiting for idle tasks
		if forceUpdate:
			self.statusLabel.update()

	def imageBank( self, imageName, subFolder='', showWarnings=True ):

		""" Loads and stores images required by the GUI. This allows all of the images to be 
			stored together in a similar manner, and ensures references to all of the loaded 
			images are stored, which prevents them from being garbage collected (which would 
			otherwise cause them to disappear from the GUI after rendering is complete). The 
			images are only loaded when first requested, and then kept for future reference. 
			
			One or more subFolders may be provided as 'subFolder' or 'subFolder/deeperSubs'. """

		image = self._imageBank.get( imageName, None )

		if not image: # Hasn't yet been loaded
			# Build the file path
			if subFolder:
				lowerParts = subFolder.split( '/' )
				lowerParts.append( imageName + ".png" )
				imagePath = os.path.join( globalData.paths['imagesFolder'], *lowerParts )
			else:
				imagePath = os.path.join( globalData.paths['imagesFolder'], imageName + ".png" )
			
			# Get the image
			try:
				image = self._imageBank[imageName] = ImageTk.PhotoImage( Image.open(imagePath) )
			except:
				if showWarnings:
					print( 'Unable to load the image, "' + imagePath + '"' )

		return image

	def updateMainMenuOptions( self, event ):

		""" This method is used as an efficiency improvement over using the Menu postcommand argument.

			Normally, all postcommand callbacks for all submenus that have one are called when the 
			user clicks to expand any one submenu, or even if they only click on the menubar itself,
			when no submenu needs to be displayed. So this method works to call the callback
			of only one specific submenu when it needs to be displayed. Details here:
			https://stackoverflow.com/questions/55753828/how-can-i-execute-different-callbacks-for-different-tkinter-sub-menus

			Note that event.widget is a tk/tcl path string in this case, rather than a widget instance. """

		activeMenuIndex = self.root.call( event.widget, "index", "active" )

		if isinstance( activeMenuIndex, int ):
			activeMenu = self.menubar.winfo_children()[activeMenuIndex]

			# Check if this menu has a repopulate method (in which case it will also have an open attribute), and call it if the menu is to be opened
			if getattr( activeMenu, 'repopulate', None ) and not activeMenu.open:
				# Repopulate the menu's contents
				activeMenu.repopulate()
				activeMenu.open = True

		else: # The active menu index is 'none'; all menus are closed, so reset the open state for all of them
			for menuWidget in self.menubar.winfo_children():
				menuWidget.open = False

	def onMainTabChanged( self, event ):

		""" This function adjusts the height of rows in the treeview widgets, since the two treeviews can't be individually configured.
			It also starts DAT file structural analysis or image searching when switching to the SA tab or DAT File Tree tab if a DAT file is loaded. 
			If an attempt is made to switch to a tab that is already the current tab, this function will not be called. """

		#global globalDatFile

		currentTab = self.root.nametowidget( self.mainTabFrame.select() )
		currentTab.focus() # Don't want keyboard/widget focus at any particular place yet

		if currentTab == self.codeManagerTab:
			# Need to populate the initial tab and align the control panel
			self.codeManagerTab.onTabChange()
		elif self.codeManagerTab: # Not selected, but it exists
			self.codeManagerTab.emptyModsPanels() # For improved GUI performance

		# if currentTab == self.datTab:
		# 	ttk.Style().configure( 'Treeview', rowheight=76 )

		# 	if globalDatFile and not self.datTextureTree.get_children():
		# 		# May not have been scanned for textures yet (or none were found).
		# 		scanDat()

		# else:
		# 	ttk.Style().configure( 'Treeview', rowheight=20 )

		# 	if globalDatFile and currentTab == self.savTab and not self.fileStructureTree.get_children():
		# 		# SAV tab hasn't been populated yet. Perform analysis.
		# 		analyzeDatStructure()

	def onMouseWheelScroll( self, event ):

		""" Checks the widget under the mouse when a scroll event occurs, and then looks upward through the 
			GUI geometry for widgets (or parents of those widgets, etc.) that may have scroll wheel support. """

		# Cross-platform resources on scrolling:
			# - http://stackoverflow.com/questions/17355902/python-tkinter-binding-mousewheel-to-scrollbar
			# - https://www.daniweb.com/programming/software-development/code/217059/using-the-mouse-wheel-with-tkinter-python

		# Get the widget currently under the mouse
		widget = self.root.winfo_containing( event.x_root, event.y_root )

		# Traverse upwards through the parent widgets, looking for a scrollable widget
		while widget:
			# Check for a scrollable frame (winfo_class sees this as a regular Frame)
			if widget.__class__.__name__ == 'VerticalScrolledFrame':
				widget = widget.canvas
				break

			elif widget.winfo_class() in ( 'Text', 'Treeview', 'Canvas' ):
				break

			widget = widget.master

		# If the above loop didn't break (no scrollable found), "widget" will reach the top level item and become 'None'.
		if widget:
			widget.yview_scroll( -1*(event.delta/30), "units" )

	def selectAll( self, event ):

		""" Adds bindings for normal CTRL-A functionality. """

		if event.widget.winfo_class() == 'Text': event.widget.tag_add( 'sel', '1.0', 'end' )
		elif event.widget.winfo_class() == 'TEntry': event.widget.selection_range( 0, 'end' )

	def dndHandler( self, event, dropTarget=None ):

		""" Processes files that are drag-and-dropped onto the GUI. The paths that this event recieves are in one string, 
			each enclosed in {} brackets (if they contain a space) and separated by a space. Turn this into a list. """

		paths = event.data.replace('{', '').replace('}', '')
		drive = paths[:2]

		filepaths = [drive + path.strip() for path in paths.split(drive) if path != '']

		self.root.deiconify() # Brings the main program window to the front (application z-order).
		self.fileHandler( filepaths, dropTarget=dropTarget )

	def fileHandler( self, filepaths, dropTarget='', updateDefaultDirectory=True, updateDetailsTab=True ):

		""" All opened standalone ISO & DAT files should pass through this (regardless of whether it was from drag-and-drop,
			file menu, or other methods), with the exception of files viewed with the 'prev/next DAT' buttons. Standalone meaning 
			that the file is not within a disc. """

		if filepaths == [] or filepaths == ['']: return
		elif len( filepaths ) > 1:
			msg( 'Please only provide one file to load at a time.' )
			self.updateProgramStatus( 'Too many files recieved.', warning=True )
			return

		# Normalize the path (prevents discrepancies between paths with forward vs. back slashes, etc.)
		filepath = os.path.normpath( filepaths[0] )
		#currentTab = self.root.nametowidget( self.mainTabFrame.select() )

		# Validate the path (make sure it's valid)
		if not os.path.exists( filepath ):
			msg( 'The given path does not seem to exist!' )
			self.updateProgramStatus( 'Invalid path provided.', error=True )

		# Check if it's a disc root directory.
		elif os.path.isdir( filepath ):
			if isExtractedDirectory( filepath, showError=False ):
				# Check whether there are changes that the user wants to save for files that must be unloaded
				if globalData.disc and globalData.disc.changesNeedSaving():
					return

				self.loadRootOrDisc( filepath, updateDefaultDirectory )

			else:
				msg( 'Only extracted root directories are able to opened in this way.' )
				self.updateProgramStatus( 'Invalid input.', error=True )

		else: # Valid file path given
			extension = os.path.splitext( filepath )[1].lower()
			if extension == '.iso' or extension == '.gcm':
				# Check whether there are changes that the user wants to save for files that must be unloaded
				if globalData.disc and globalData.disc.changesNeedSaving():
					return

				self.loadRootOrDisc( filepath, updateDefaultDirectory )

			else: # Assuming it's some form of DAT
				# Perform some rudimentary validation; if the file passes, remember it and load it
				if os.path.getsize( filepath ) > 20971520: # i.e. 20 MB
					msg("The recieved file doesn't appear to be a DAT or other type of texture file, as it's larger than 20 MB. "
						"If this is actually supposed to be a disc image, rename the file with an extension of '.ISO' or '.GCM'.")
					self.updateProgramStatus( 'Invalid file input', error=True )
				
				# Check if there's a file open that has unsaved changes and belongs in the currently loaded disc
				# elif globalData.dat and globalData.dat.source == 'disc':
				# 	if not globalData.dat.noChangesToBeSaved( globalData.programEnding ): return
				# 	else: # No changes that the user wants to save; OK to clear the DAT file.
				# 		globalData.dat = None

				else:
					#restoreEditedEntries( editedDatEntries )
					# rememberFile( filepath, updateDefaultDirectory )
					# print( 'not yet supported' )
					self.updateProgramStatus( 'Invalid file input; no support for opening this file directly', error=True )

	def promptToOpenFile( self, typeToOpen ):

		""" This is primarily a wrapper for the 'Open Disc' and 'Open DAT' options in the main menu. """

		if typeToOpen == 'iso':
			titleString = "Choose an ISO or GCM file to open."
			filetypes = [('Disc image files', '*.iso *.gcm'), ('All files', '*.*')]
			initDir = globalData.getLastUsedDir( 'iso' )
		else:
			titleString = "Choose a texture data file to open."
			filetypes = [('Texture data files', '*.dat *.usd *.lat *.rat'), ('All files', '*.*')]
			initDir = globalData.getLastUsedDir( 'dat' )

		filepath = tkFileDialog.askopenfilename(
			title=titleString,
			parent=self.root,
			initialdir=initDir,
			filetypes=filetypes
			)
		
		if filepath:
			self.fileHandler( [filepath] ) # Will handle validation of the filepath and opening of the file.

	def promptToOpenRoot( self ):
		# Prompt for a directory to retrieve files from.
		rootPath = tkFileDialog.askdirectory(
			title='Choose a root directory (folder of disc files).',
			parent=self.root,
			initialdir=globalData.getLastUsedDir(),
			mustexist=True )

		# Check if a path was chosen above and it's a disc root directory
		if rootPath and isExtractedDirectory( rootPath ):
			self.fileHandler( [rootPath] ) # Will handle validation of the filepath and opening of the file.

	def onProgramClose( self ):
		self.root.destroy() # Stops the GUI's mainloop and destroys all widgets. https://stackoverflow.com/a/42928131/8481154

	def saveDiscAs( self ):

		""" Creates a new file (via dialog prompt to user), and then saves 
			changes to the currently loaded ISO/GCM disc image or root folder. """

		origDiscName = os.path.basename( globalData.disc.filePath )
		fileNameWithoutExt, ext = origDiscName.rsplit( '.', 1 )
		newFilenameSuggestion = '{} - Copy'.format( fileNameWithoutExt )

		# Prompt the user for a save directory and filename
		newPath = tkFileDialog.asksaveasfilename(
			title="Where would you like to save the new disc?",
			initialdir=globalData.getLastUsedDir( 'iso' ),
			initialfile=newFilenameSuggestion,
			defaultextension=ext[1:],
			filetypes=[('Standard disc image', '*.iso'), ('GameCube disc image', '*.gcm'), ("All files", "*.*")]
			)
		if not newPath: # User canceled the operation
			return

		# Normalize the path, and set the default program directory
		globalData.setLastUsedDir( newPath, 'iso' )

		# Save the disc to a new path
		self.save( newPath )

	def save( self, newPath='' ):

		""" Saves changes to the currently loaded ISO/GCM disc image or root folder. 
			If newPath is provided, e.g. from .saveAs() a new file is created. """

		if not globalData.disc:
			return -1

		# Save code mods if that tab is open
		if self.codeManagerTab:
			returnCode = self.codeManagerTab.saveCodeChanges()

			if not returnCode == 0:
				msg( 'A problem occurred while saving codes to the game. Error code: {}'.format(returnCode), 'Unable to Save', error=True )
				self.updateProgramStatus( 'Unable to save. There was an error while saving codes to the game', error=True )
				return -1

		# Save all file changes to the disc
		returnCode, updatedFiles = globalData.disc.save( newPath )

		if returnCode == 0:
			# Reload the disc and show a save confirmation
			self.loadRootOrDisc( globalData.disc.filePath, True, False, True, False, updatedFiles )
			self.updateProgramStatus( 'Save Successful', success=True )

		elif returnCode == 1:
			self.updateProgramStatus( 'There were no changes to be saved' )
		elif returnCode == 2:
			self.updateProgramStatus( 'Unable to save the disc; there are missing system files!', error=True ) # todo: report which are missing
		elif returnCode == 3:
			self.updateProgramStatus( 'Unable to create a new disc file. Be sure the program has write permissions', error=True )
		elif returnCode == 4:
			self.updateProgramStatus( 'Unable to open the original disc. Be sure that it has not been moved or renamed', error=True )
		elif returnCode == 5:
			self.updateProgramStatus( 'Unable to save the disc; there was an unrecognized error during file writing', error=True )
		elif returnCode == 6:
			self.updateProgramStatus( 'Unable to save the disc; unable to overwrite existing file', error=True )
		elif returnCode == 7:
			self.updateProgramStatus( 'Unable to save the disc; could not rename discs or rename original', error=True )
		else:
			self.updateProgramStatus( 'Unable to save the disc; unrecognized save method return code: ' + str(returnCode) , error=True )
		
		return returnCode

	def loadRootOrDisc( self, targetPath, updateDefaultDirectory, updateStatus=True, preserveTreeState=False, switchTab=True, updatedFiles=None ):
		
		# Remember this file for future recall
		globalData.rememberFile( targetPath, updateDefaultDirectory )

		self.mainMenu.remove()

		# Load the disc, and load the disc's info into the GUI
		tic = time.clock()
		globalData.disc = Disc( targetPath )
		globalData.disc.load()
		toc = time.clock()
		print( 'disc load time:', toc-tic )
		
		# Add/initialize the Disc File Tree tab
		if not self.discTab:
			self.discTab = DiscTab( self.mainTabFrame, self )
			#self.mainTabFrame.update_idletasks()
			#self.mainTabFrame.update()
		self.discTab.loadDisc( updateStatus=updateStatus, preserveTreeState=preserveTreeState, switchTab=switchTab, updatedFiles=updatedFiles )
		self.mainTabFrame.update_idletasks()

		# Add/initialize the Disc Details tab, and load the disc's info into it
		if not self.discDetailsTab:
			self.discDetailsTab = DiscDetailsTab( self.mainTabFrame, self )
			self.mainTabFrame.update_idletasks()
		self.discDetailsTab.loadDiscDetails()

		if not self.codeManagerTab:
			self.codeManagerTab = CodeManagerTab( self.mainTabFrame, self )
			self.mainTabFrame.update_idletasks()
		self.codeManagerTab.autoSelectCodeRegions()
		self.codeManagerTab.scanCodeLibrary()
		self.codeManagerTab.updateControls()

		if globalData.disc.isMelee:
			# If this is 20XX, add/initialize the Debug Menu Editor tab
			if globalData.disc.is20XX:
				if not self.menuEditorTab:
					self.menuEditorTab = DebugMenuEditor( self.mainTabFrame, self )
					self.mainTabFrame.update_idletasks()
				self.menuEditorTab.loadTopLevel()

			# Remove the Debug Menu Editor if this isn't 20XX and it's present
			elif self.menuEditorTab:
				self.menuEditorTab.destroy()
				self.menuEditorTab = None

			# Load the stage info/editor
			if not self.stageManagerTab:
				self.stageManagerTab = StageManager( self.mainTabFrame, self )
				self.mainTabFrame.update_idletasks()
			if globalData.disc.is20XX:
				self.stageManagerTab.load20XXStageLists()
			else:
				self.stageManagerTab.loadVanillaStageLists()

			# Load the audio tab
			if not self.audioManagerTab:
				self.audioManagerTab = AudioManager( self.mainTabFrame, self )
			self.audioManagerTab.loadFileList()

	def runInEmulator( self, event=None ):

		""" Runs the currently loaded disc or root folder structure in Dolphin. """

		if not globalData.disc:
			msg( 'No disc has been loaded!' )
			return

		globalData.dolphinController.start( globalData.disc )

	def saveAndRun( self, event=None ):

		""" Saves current changes, and then runs the disc or root folder in Dolphin. """

		# Shut down Dolphin in case the game is running (can't save ot it otherwise)
		globalData.dolphinController.stopAllDolphinInstances()

		# Save
		returnCode = self.save()

		# Boot
		if returnCode == 0 or returnCode == 1: # Success or no changes to save
			self.runInEmulator()


#																		/---------------------------------\
#	====================================================================   Command Line Argument Parsing   =========
#																		\---------------------------------/

def set_default_subparser(self, name, args=None, positional_args=0):

	""" default subparser selection. Call after setup, just before parse_args()
		name: is the name of the subparser to call by default
		args: if set is the argument list handed to parse_args()

		tested with 2.7, 3.2, 3.3, 3.4
		it works with 2.6 assuming argparse is installed 
		
		Source: https://stackoverflow.com/questions/6365601/default-sub-command-or-handling-no-sub-command-with-argparse """

	subparser_found = False
	existing_default = False # check if default parser previously defined
	for arg in sys.argv[1:]:
		if arg in ['-h', '--help']:  # global help if no subparser
			break
	else:
		for x in self._subparsers._actions:
			if not isinstance(x, argparse._SubParsersAction):
				continue
			for sp_name in x._name_parser_map.keys():
				if sp_name in sys.argv[1:]:
					subparser_found = True
				if sp_name == name: # check existance of default parser
					existing_default = True
		if not subparser_found:
			# If the default subparser is not among the existing ones,
			# create a new parser.
			# As this is called just before 'parse_args', the default
			# parser created here will not pollute the help output.

			if not existing_default:
				for x in self._subparsers._actions:
					if not isinstance(x, argparse._SubParsersAction):
						continue
					x.add_parser(name)
					break # this works OK, but should I check further?

			# insert default in last position before global positional
			# arguments, this implies no global options are specified after
			# first positional argument
			if args is None:
				sys.argv.insert(len(sys.argv) - positional_args, name)
			else:
				args.insert(len(args) - positional_args, name)


def parseArguments(): # Parses command line arguments

	# Override the default method for setting a default subparser (operation group)
	# This prevents an error if the user doesn't provide a subparser
	argparse.ArgumentParser.set_default_subparser = set_default_subparser

	try:
		parser = argparse.ArgumentParser( description='Program for modding SSBM. The GUI will be opened by default if no command line arguments are given.' )

		# Build a disc/root folder (ISO created in same directory as target folder, unless -o option is specified)
		# parser.add_argument( '-b', '--buildDisc', dest='rootFolderPath', help='Builds a disc file (ISO or GCM) from a given root folder path. '
		# 			'The folder should contain a "files" folder and a "sys" folder. The disc will be built in the path given, unless the -o option is also given.' )
		# parser.add_argument( '-o', '--output', dest='outputFilePath', help='Provides an output path for various operations. May be just a folder path, or it may '
		# 			'include the file name in order to name the finished file.' )

		# Allow for filepaths to be provided without a flag (this will also catch files drag-and-dropped onto the program icon)
		parser.add_argument( 'filePath', nargs='?', help='If no operation or option flags are given, but a filepath is provided, '
														 'the GUI will be loaded and that file will automatically be loaded into it.' )

		parser.add_argument( '-v', '--version', action='version', version=globalData.programVersion )

		# Set up sub-parsers for operation groups
		subparsers = parser.add_subparsers( title='operations', dest='opsParser',
											description=('Most command-line features are available within various operation groups. '
														 'To see the features available within a specific operation group, enter '
														 '"{} [operationGroupName] -h". The following are the current option '
														 'groups available:').format(parser.prog) )

		# Define "disc" options
		discOpsParser = subparsers.add_parser( 'disc', help='Perform operations on ISO/GCM files, such as adding or getting files.' )
		discOpsParser.add_argument( '-d', '--discPath', help='Provide a filepath for a target disc for the program to operate on.' )
		discOpsParser.add_argument( '-i', '--info', action="store_true", help='Show various information on the given disc.' )
		discOpsParser.add_argument( '-l', '--listFiles', action="store_true", help='List the files within the given disc.' )
		discOpsParser.add_argument( '-b', '--build', dest='rootFolderPath', help='Builds a disc file (ISO or GCM) from a given root folder path. '
					'The folder should contain a "sys" folder, and optionally a "files" folder (or files will be taken from the same root folder). '
					'The disc will be built in the root path given, unless the -o option is also provided.' )
		discOpsParser.add_argument( '-o', '--output', dest='outputFilePath', help='Provides an output path for various operations. May be just a folder path, '
																				  'or it may include the file name in order to name the finished file.' )
		
		# Define "test" options
		testOpsParser = subparsers.add_parser( 'test', help='Asset test tool. Uses Micro Melee to test assets such as characters or stages.' )
		testOpsParser.add_argument( '-d', '--debug', action="store_true", help='If included, Dolphin will run in Debug Mode.' )
		testOpsParser.add_argument( '-p', '--path', required=True, help='Provide a filepath for a character/stage/etc. for the program to load.' )
		
		# Define "code" options
		codeOpsParser = subparsers.add_parser( 'code', help='Add custom code to a DOL or ISO, or examine one for installed codes.' )
		testOpsParser.add_argument( '-l', '--library', help='A path to a Code Library directory. If not provided, the current default will be used.' )
		testOpsParser.add_argument( '-i', '--install', help='Install code to a given DOL or ISO. Input should be a line-separated list of mod names.' )

	except Exception as err:
		# Exit the program on error (with exit code 1)
		print( err )
		parser.exit( status=1, message='There was an error in parsing the command line arguments.' )
		
	parser.set_default_subparser( 'none' )

	return parser.parse_args()


def buildDiscFromRoot():

	""" Function from command-line usage.debug
	
		Exit codes (should be the same as program exit codes):

			0: All operations completed successfully
			1: A problem occurred in parsing command line arguments
			2: Invalid input path given (file/folder not found, or invalid root folder)
			3: Unable to initialize the given input file or root folder
			4: Unable to build output disc or save root folder """

	# Load and initialize a new disc image and the files presented in the root folder
	try:
		newDisc = Disc( args.rootFolderPath )
		
		print( '' ) # For readability
		systemFilePaths = isExtractedDirectory( args.rootFolderPath, showError=True )

		if systemFilePaths:
			newDisc.loadRootFolder( systemFilePaths )
		else:
			sys.exit( 2 )

	except Exception as err:
		print( '\nUnable to initialize and load the root files.' )
		print( err )
		sys.exit( 3 )

	# Determine the new disc filepath output
	if args.outputFilePath:
		savePath = args.outputFilePath
	else:
		# Build in the same directory as the root folder
		rootFolderParent = os.path.dirname( args.rootFolderPath )

		# Try to use the Long Title for the default filename if the banner file is present (which it should be!)
		bannerFile = newDisc.files.get( newDisc.gameId + '/opening.bnr', None )
		fileName = ''

		if bannerFile:
			if newDisc.countryCode == 1:
				fileName = bannerFile.getData()[0x1860:(0x18A0)].split('\x00')[0].decode('latin_1') + '.iso'
			else: # The country code is for Japanese
				fileName = bannerFile.getData()[0x1860:(0x18A0)].split('\x00')[0].decode('shift_jis') + '.iso'
		
		if not fileName: # Just use the Game ID
			fileName = newDisc.gameId + '.iso'

		savePath = os.path.join( rootFolderParent, fileName )
	print( '\nDisc output path set to "' + savePath + '".' )
	print( '' )

	# Build the new disc (the progress bar will be printed by the following method)
	tic = time.clock()
	fileWriteSuccessful = newDisc.buildNewDisc( savePath )[0]
	toc = time.clock()

	# Check for problems
	if not fileWriteSuccessful:
		print( '\nUnable to build the disc.' )
		sys.exit( 4 )

	print( '\nDisc built successfully.  Build time:', toc-tic )


def performAssetTest( assetPath ):

	""" Function from command-line usage. Boots an instance of the game with the given asset. 
		Currently supported are stage and character files. """

	# Perform some quick/basic validation based on file extension
	ext = os.path.splitext( assetPath )[1]
	if ext in ( '.png', '.jpg', '.jpeg', '.gif' ):
		print( 'This appears to be an image file! This feature expects a stage or character file.' )
		sys.exit( 3 )
	elif ext == '.dol':
		print( 'This appears to be a DOL file! This feature expects a stage or character file.' )
		sys.exit( 3 )
	elif ext in ( '.iso', '.gcm' ):
		print( 'This appears to be a disc image file! This feature expects a stage or character file.' )
		sys.exit( 3 )
	elif ext in ( '.hps', '.ssm', 'wav', 'dsp', 'mp3', 'aiff', 'wma', 'm4a' ):
		print( 'This appears to be an audio file! This feature expects a stage or character file.' )
		sys.exit( 3 )
	elif ext in ( '.mth', '.thp' ):
		print( 'This appears to be a video file! This feature expects a stage or character file.' )
		sys.exit( 3 )

	# See if this is a stage file
	try:
		newFileObj = StageFile( None, -1, -1, '', extPath=assetPath, source='file' )
		newFileObj.validate()
	except:
		newFileObj = None

	if not newFileObj:
		# See if this is a character file
		try:
			newFileObj = CharCostumeFile( None, -1, -1, '', extPath=assetPath, source='file' )
			newFileObj.validate()
		except:
			newFileObj = None

	# Exit if unable to initialize the given file as one of the above classes
	if not newFileObj:
		print( 'Unable to initialize and validate the given file; it does not appear to be a stage or character file.' )
		sys.exit( 3 )

	# Get the micro melee disc object, and use it to test the given file
	microMelee = globalData.getMicroMelee()
	if not microMelee:
		sys.exit( 5 )

	# Set whether to run Dolphin in Debug mode if the --debug option is present
	if args.debug:
		globalData.setSetting( 'runDolphinInDebugMode', True )
	else:
		globalData.setSetting( 'runDolphinInDebugMode', False )
	
	if isinstance( newFileObj, StageFile ):
		microMelee.testStage( newFileObj )
	else:
		microMelee.testCharacter( newFileObj )


# Function & class definitions complete
if __name__ == '__main__':

	# Initialize the program globals and settings
	globalData.init( programArgs )

	# Parse command line arguments
	args = parseArguments()

	# Check for "disc" operation group
	if args.opsParser == 'disc':

		if args.info or args.listFiles:
			disc = Disc( args.discPath )
			disc.load()
			if not disc.files:
				if not os.path.exists( args.discPath ): # A warning will have already been given if this is the case
					sys.exit( 2 )
				else:
					print( 'Unable to load the disc.' )
					sys.exit( 3 )

			if args.info:
				print( disc.listInfo() )
			if args.listFiles:
				print( disc.listFiles() )
			
		elif args.rootFolderPath: # The --build parameter was given; the user wants to build a disc from a root folder
			globalData.loadProgramSettings()
			buildDiscFromRoot()

		else:
			print( 'Insufficient command line aguments given. No operation pending.' )

	# Check for "test" operation group
	elif args.opsParser == 'test':
		globalData.loadProgramSettings()
		performAssetTest( args.path )

	elif args.opsParser == 'code':
		print( 'todo' )
	
	# No option group or other command line arguments (flags) detected; start the GUI
	else:
		# Load the program settings and initialize the GUI
		globalData.gui = gui = MainGui()
		gui.audioEngine = AudioEngine()

		# Process any file provided on start-up (drag-and-dropped onto the program's .exe file, or provided via command line)
		if args.filePath:
			gui.fileHandler( [args.filePath] )

		# for testing:
		#gui.fileHandler( ["D:\\Games\\GameCube\\- - SSB Melee - -\\Hacks\\20XX Hack Pack\\20XXHP 5.0\\SSBM, 20XXHP 5.0 - Rebuilt, v3.iso"] )
		#gui.fileHandler( [r"D:\Games\GameCube\- - SSB Melee - -\Hacks\TEST Build\Super Smash Bros. Melee (v1.02).iso"] )
		#gui.fileHandler( ["D:\\Games\\GameCube\\- - SSB Melee - -\\Hacks\\Injection Method 2\\Super Smash Bros. Melee (v1.02) - Rebuilt, v3.iso"] )
		#gui.fileHandler( ["D:\\Games\\GameCube\\- - SSB Melee - -\\Hacks\\Injection Method 2\\Super Smash Bros. Melee (v1.02).iso"] )
		#gui.fileHandler( ["D:\\Games\\GameCube\\- - SSB Melee - -\\Hacks\\20XX Hack Pack\\20XXHP 5.0\\SSBM, 20XXHP 5.0 - Rebuilt, v3 - Backup.iso"] )

		# Start the GUI's mainloop (blocks until the GUI is taken down by .destroy or .quit)
		gui.root.mainloop()


# Program exit codes:
#
#	0: All operations completed successfully
#	1: A problem occurred in parsing command line arguments
#	2: Invalid input path given (file/folder not found)
#	3: Unable to initialize the given input file or root folder
#	4: Unable to build output disc or save root folder
#	5: Unable to initialize Micro Melee disc image