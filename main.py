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
#		https://smashboards.com/threads/melee-modding-wizard-beta-v0-9-4.517823/


# External dependencies
import math
import time
import json
import struct
import random
import tkFont
import pyglet
import os, sys
import argparse
import pyaudio, wave
import Tkinter as Tk
import ttk, tkMessageBox, tkFileDialog

from threading import Thread, Event
from collections import OrderedDict
from subprocess import Popen, PIPE, CalledProcessError
from sys import argv as programArgs 	# Access command line arguments, and files given (drag-and-dropped) to the program icon
from PIL import Image, ImageTk
from ctypes import windll, byref, create_unicode_buffer, create_string_buffer

# Internal dependencies
#tic = time.clock()
import globalData

from codeMods import CodeLibraryParser
from tools import CharacterColorConverter, TriCspCreator, AsmToHexConverter, CodeLookup
from FileSystem import DatFile, CharDataFile, CharAnimFile, CharCostumeFile
from FileSystem import CssFile, SssFile, StageFile, MusicFile
from FileSystem.dol import Dol
from FileSystem.disc import Disc, isExtractedDirectory
from basicFunctions import grammarfyList, msg, openFolder
from guiSubComponents import (
		ToolTip, importGameFiles, cmsg, CharacterChooser, 
		GeneralHelpWindow, SupportWindow, AboutWindow
	)
from guiDisc import DiscTab
from codesManager import CodeManagerTab, CodeConstructor
from debugMenuEditor import DebugMenuEditor
from stageManager import StageManager
from audioManager import AudioManager, AudioEngine
from characterModding import CharModding
from newTkDnD.tkDnD import TkDnD
# toc = time.clock()
# print('internal module load time: ' + str(toc-tic))

DEBUGMODE = False


class FileMenu( Tk.Menu, object ):

	def __init__( self, parent, tearoff=True, *args, **kwargs ):
		super( FileMenu, self ).__init__( parent, tearoff=tearoff, *args, **kwargs )
		self.open = False
		self.recentFilesMenu = Tk.Menu( self, tearoff=True ) # tearoff is the ability to basically turn the menu into a tools window

		self.add_cascade( label="Open Recent", menu=self.recentFilesMenu )												# Key shortcut (holding alt)
		self.add_command( label='Open Last Used Directory', underline=5, command=self.openLastUsedDir )								# L
		self.add_command( label='Open Dolphin Screenshots Folder', underline=15, command=self.openDolphinScreenshots )				# R
		self.add_command( label='Open Disc (ISO/GCM)', underline=11, command=lambda: globalData.gui.promptToOpenFile('iso') )		# I
		self.add_command( label='Open Root (Disc Directory)', underline=6, command=lambda: globalData.gui.promptToOpenRoot() )		# O		(gui nonexistant on init; lambda required)
		#self.add_command( label='Open DAT (or USD, etc.)', underline=5, command=lambda: globalData.gui.promptToOpenFile('dat') )	# D
		self.add_command( label='Browse Code Library', underline=0, command=self.browseCodeLibrary )								# B
		self.add_separator()
		self.add_command( label='View Unsaved Changes', underline=0, command=self.showUnsavedChanges )								# V
		self.add_command( label='Save  (CTRL-S)', underline=0, command=self.save )													# S
		#self.add_command( label='Save DAT As...', underline=9, command=globalData.gui.saveDatAs )									# A
		# self.add_command( label='Save Banner As...', underline=5, command=saveBannerAs )											# B
		self.add_command( label='Run in Emulator  (CTRL-R)', underline=0, command=self.runInEmulator )								# R
		self.add_command( label='Save Disc As...', underline=10, command=self.saveAs )												# A
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

		""" Adds the Code Manager tab to the GUI and selects it. """

		mainGui = globalData.gui

		if not mainGui.codeManagerTab:
			mainGui.codeManagerTab = CodeManagerTab( mainGui.mainTabFrame, mainGui )

		mainGui.codeManagerTab.autoSelectCodeRegions()
		mainGui.codeManagerTab.scanCodeLibrary()

		# Switch to the tab
		mainGui.mainTabFrame.select( mainGui.codeManagerTab )

	def save( self ):			globalData.gui.save()
	def saveAs( self ):			globalData.gui.saveAs()
	def closeProgram( self ):	globalData.gui.onProgramClose()
	def runInEmulator( self ):	globalData.gui.runInEmulator()

	def showUnsavedChanges( self ):

		""" Displays a pop-up message to the user, showing unsaved changes awaiting a save. """

		if not globalData.disc:
			msg( 'No disc has been loaded!' )
			return

		changes = globalData.gui.concatAllUnsavedChanges( basicSummary=False )
		msg( '\n'.join(changes), 'Unsaved Changes' )


class SettingsMenu( Tk.Menu, object ):

	""" The checkbuttons in these menus are the same objects used internally by the 
		program (BooleanVars) to track these settings (so there's no extra syncing required). """

	def __init__( self, parent, tearoff=True, *args, **kwargs ): # Create the menu and its contents
		super( SettingsMenu, self ).__init__( parent, tearoff=tearoff, *args, **kwargs )
		self.open = False
		
	def repopulate( self ):

		# Clear all current population
		self.delete( 0, 'last' )

		# Disc related options
		self.add_checkbutton( label='Use Disc Convenience Folders', underline=9, 												# C
				variable=globalData.boolSettings['useDiscConvenienceFolders'], command=globalData.saveProgramSettings )
		self.add_checkbutton( label='Use Disc Convenience Folders with File Exports', underline=39, 							# E
				variable=globalData.boolSettings['useConvenienceFoldersOnExport'], command=globalData.saveProgramSettings )
		# self.add_checkbutton( label='Avoid Rebuilding Disc', underline=0, 													# A
		# 		variable=globalData.boolSettings['avoidRebuildingIso'], command=globalData.saveProgramSettings )
		self.add_checkbutton( label='Back-up Disc When Rebuilding', underline=0, 												# B
				variable=globalData.boolSettings['backupOnRebuild'], command=globalData.saveProgramSettings )
		# self.add_checkbutton( label='Auto-Generate CSP Trim Colors', underline=5, 											# G
		# 		variable=globalData.boolSettings['autoGenerateCSPTrimColors'], command=globalData.saveProgramSettings )
		self.add_checkbutton( label='Always Add Files to Discs Alphabetically', underline=11, 									# F
				variable=globalData.boolSettings['alwaysAddFilesAlphabetically'], command=globalData.saveProgramSettings )

		self.add_checkbutton( label='Run Dolphin in Debug Mode', underline=15, 													# D
				variable=globalData.boolSettings['runDolphinInDebugMode'], command=globalData.saveProgramSettings )
		
		if globalData.disc and globalData.disc.is20XX:
			self.add_checkbutton( label='Create Hi-Res CSPs', underline=7, 														# H
					variable=globalData.boolSettings['createHiResCSPs'], command=globalData.saveProgramSettings )
		
		self.add_separator()

		# Code related options
		self.add_checkbutton( label='Use Code Cache', underline=9, 																# C
				variable=globalData.boolSettings['useCodeCache'], command=globalData.saveProgramSettings )
		self.add_checkbutton( label='Offer to Convert Gecko Codes', underline=9, 												# G
				variable=globalData.boolSettings['offerToConvertGeckoCodes'], command=globalData.saveProgramSettings )
		self.add_checkbutton( label='Always Enable Crash Reports', underline=20, 												# R
				variable=globalData.boolSettings['alwaysEnableCrashReports'], command=globalData.saveProgramSettings )

		# Image-editing related options
		#self.add_separator()
		# self.add_checkbutton( label='Cascade Mipmap Changes', underline=8, 
		# 		variable=globalData.boolSettings['cascadeMipmapChanges'], command=globalData.saveProgramSettings )				# M
		# self.add_checkbutton( label="Export Textures using Dolphin's Naming Convention", underline=32, 
		# 		variable=globalData.boolSettings['useDolphinNaming'], command=globalData.saveProgramSettings )					# N

		self.add_separator()
		self.add_command( label='Open Settings File', underline=0, command=self.openSettingsFile )								# O

	def openSettingsFile( self ):

		""" Open the settings file in the user's default text editor. """

		try:
			os.startfile( globalData.paths['settingsFile'] )
		except:
			filename = os.path.basename( globalData.paths['settingsFile'] )
			msg( "Unable to find and open the '{}' file!".format(filename), error=True )


class ToolsMenu( Tk.Menu, object ):

	def __init__( self, parent, tearoff=True, *args, **kwargs ):
		super( ToolsMenu, self ).__init__( parent, tearoff=tearoff, *args, **kwargs )
		self.statusUpdateFrequency = 2000 # How frequent the GUI updates xDelta patch progress, in milliseconds
		self.open = False
		self.buildingPatch = False
		self.patchBuildProgress = -1

	def repopulate( self ):

		# Clear all current population
		self.delete( 0, 'last' )
																									# Key shortcut (using alt key)
		self.add_cascade( label="Character Color Converter", command=self.characterColorConverter, underline=1 )		# H
		self.add_cascade( label="ASM <-> HEX Converter", command=lambda: AsmToHexConverter(), underline=0 )				# A
		#self.add_cascade( label="Number and Address Conversion", command=lambda: AsmToHexConverter(), underline=0 )	# N
		self.add_separator()
		self.add_cascade( label='Code Lookup', command=lambda: CodeLookup(), underline=5 )								# L
		self.add_cascade( label='New Code Mod', command=self.createCodeMod )							# 
		self.add_cascade( label='Save Code Library As', command=self.saveCodeLibraryAs, underline=6 )					# O
		self.add_separator()
		self.add_cascade( label="Test External Stage File", command=self.testStage, underline=14 )						# S
		self.add_cascade( label="Test External Character File", command=self.testCharacter, underline=14 )				# C
		self.add_separator()
		self.add_cascade( label="Build xDelta Patch", command=self.buildPatch, underline=6 )							# X
		self.add_cascade( label="Build from Patch", command=self.notDone, underline=11 )								# P

		if globalData.disc and globalData.disc.is20XX:
			self.add_separator()
			self.add_cascade( label="Create Tri-CSP", command=self.createTriCsp, underline=1 )							# T
			self.add_cascade( label="Find Unused Stage Files", command=self.findUnusedStages, underline=0 )				# F
			#self.add_cascade( label="Parse FSM List", command=self.parseFsmList, underline=0 )							# F

	def createCodeMod( self ):

		""" Adds the Code Construction tab to the main GUI, and creates a tab within it for a new code mod to work on. """
		
		# Add the Code Construction tab if it's not present, and select it
		mainGui = globalData.gui
		mainGui.addCodeConstructionTab()
		mainGui.mainTabFrame.select( mainGui.codeConstructionTab )

		# Create a new tab for the Mod Construction tab, and create a new construction module within it
		newTab = CodeConstructor( mainGui.codeConstructionTab )
		mainGui.codeConstructionTab.add( newTab, text='New Mod' )

		# Bring the new tab into view for the user.
		mainGui.codeConstructionTab.select( newTab )

	def saveCodeLibraryAs( self ):

		# Load the Code Library (if not already loaded) and switch to that tab
		if not globalData.gui.codeManagerTab:
			globalData.gui.fileMenu.browseCodeLibrary()

		globalData.gui.codeManagerTab.saveCodeLibraryAs()

	def characterColorConverter( self ):
		if not globalData.getUniqueWindow( 'CharacterColorConverter' ):
			# Create a new instance of the window
			CharacterColorConverter()

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
		elif self.buildingPatch: # Prevent multiple simultaneous builds
			msg( 'Patch building is already in-progress!' )
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
		defaultPatchName = bannerFile.shortTitle + ' patch.xdelta'

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

		# Build the build command for the xDelta executable
		#command = '"{}" -V "{}" "{}" "{}"'.format( xDeltaPath, vanillaDiscPath, currentDiscPath, savePath )
		command = '"{}" -B 1363148800 -e -9 -f -v -S djw -s "{}" "{}" "{}"'.format( xDeltaPath, vanillaDiscPath, currentDiscPath, savePath )
		self.buildingPatch = True
		
		# Run the command in a new thread, so the program is responsive while waiting for it
		builderThread = Thread( target=self._patchBuilderHelper, args=(currentDiscPath, command) )
		builderThread.daemon = True # Causes the thread to be stopped when the main program stops
		builderThread.start()

	def _patchBuilderHelper( self, currentDiscPath, command ):

		""" Helper method to run the xDelta build command in a separate thread (so the GUI remains responsive). 
			Build progress is captured from stderr (not stdout!) and updated to the GUI via event queue. """

		process = Popen( command, shell=False, stderr=PIPE, creationflags=0x08000000, universal_newlines=True, bufsize=1 )

		# Display initial build progress message in the program's status bar
		self.patchBuildProgress = 0
		globalData.gui.root.after_idle( self.updatePatchBuildProgress )

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
				self.patchBuildProgress = megaBytesProcessed / discSize * 100
		except CalledProcessError:
			pass
		except: # Should be a parsing error
			process.returncode = 101

		# External command process has finished
		if process.returncode == 0:
			self.patchBuildProgress = 100
		else:
			self.patchBuildProgress = process.returncode * -1

		self.buildingPatch = False

	# def updatePatchBuildProgress( self, event, progress ):
	# 	event.message = 'Building xDelta patch ({}%)'.format( round(progress, 1) )
	# 	globalData.gui.root.event_generate( '<<ProgressUpdate>>', when='tail' )
	
	def updatePatchBuildProgress( self ):

		""" Print the current xDelta patch build progress, then recursively calls itself every 
			few seconds from the GUI's mainloop until the build process is complete. """

		progress = self.patchBuildProgress

		if progress < 0: # There was an error; progress is now the process return code
			message = 'Unable to build xDelta patch; return code {}'.format( abs(progress) )
		elif progress == 0:
			message = 'Initializing xDelta patch creation (this may take a minute)'
			globalData.gui.root.after( 4000, self.updatePatchBuildProgress )
		elif progress < 100:
			message = 'Building xDelta patch ({}%)'.format( round(progress, 1) )
			globalData.gui.root.after( 2000, self.updatePatchBuildProgress )
		else: # Progress at or over 100%; operation complete
			message = 'Building xDelta patch ({}%)'.format( round(progress, 1) )

			# Allow the above to display for a few seconds, then display the following
			globalData.gui.root.after( 3000, lambda m='xDelta patch complete': globalData.gui.updateProgramStatus( m ) )

		globalData.gui.updateProgramStatus( message )

	def notDone( self ):
		print( 'not yet supported' )

	def createTriCsp( self ):

		""" Creates a Tri-CSP (Character Select Portrait) for the CSS. """

		cspCreator = TriCspCreator()

		# Check for any problems
		initErrors = cspCreator.initError()
		if initErrors:
			msg( initErrors, 'Unable to Initialize Tri-CSP Creator', error=True )
			return
		
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

		# Temporarily disable main menu animations
		globalData.gui.mainMenu.pauseAnimations = True

		# Backup Dolphin's current settings files and replace with new settings files
		globalData.dolphinController.backupAndReplaceSettings( cspCreator.settingsFiles )

		# Construct the path to the center screenshot
		centerScreenshotFilename = globalData.disc.constructCharFileName( charId, costumeId )[:-4] + '.png'
		centerScreenshot = os.path.join( globalData.paths['imagesFolder'], 'CSP Center Images', centerScreenshotFilename )

		# Generate the Left/Right screenshots
		leftScreenshot = cspCreator.createSideImage( microMelee, charId, costumeId, 'lat' )
		#leftScreenshot = os.path.join( globalData.paths['tempFolder'], 'left.png' ) # for testing
		
		if leftScreenshot:
			rightScreenshot = cspCreator.createSideImage( microMelee, charId, costumeId, 'rat' )
			#rightScreenshot = os.path.join( globalData.paths['tempFolder'], 'right.png' ) # for testing
		else:
			rightScreenshot = None

		# Restore animations state and exit if there were any problems getting the screenshots
		if not leftScreenshot or not rightScreenshot:
			globalData.gui.mainMenu.pauseAnimations = False
			return # Message to the user should have already been raised

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
		if returnCode != 0:
			# Restore animations state and exit
			globalData.gui.mainMenu.pauseAnimations = False
			return # Message to the user should have already been raised
		
		if saveHighRes:
			globalData.gui.updateProgramStatus( 'High-Res CSP Created (cannot be installed to disc)' )

			# Restore animations state and exit
			globalData.gui.mainMenu.pauseAnimations = False
			return # Message to the user should have already been raised
		
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

		# Restore animations state
		globalData.gui.mainMenu.pauseAnimations = False

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


class AboutMenu( Tk.Menu, object ):

	def __init__( self, parent, tearoff=False, *args, **kwargs ): # Create the menu and its contents
		super( AboutMenu, self ).__init__( parent, tearoff=tearoff, *args, **kwargs )
		self.open = False
																									# Key shortcut (using alt key)
		self.add_cascade( label="General Help", command=self.showGeneralHelp, underline=8 )				# H
		self.add_cascade( label="View the Manual", command=self.showManual, underline=9 )				# M
		self.add_cascade( label="Support", command=self.showSupport, underline=1 )						# S
		self.add_cascade( label="About", command=self.showAbout, underline=1 )							# A

	def showGeneralHelp( self ):
		GeneralHelpWindow()

	def showManual( self ):

		""" Open the manual file in the user's default text editor. """

		usageFilePath = os.path.join( globalData.scriptHomeFolder, 'MMW Manual.txt' )

		try:
			os.startfile( usageFilePath )
		except:
			filename = os.path.basename( usageFilePath )
			msg( "Unable to find and open the '{}' file!".format(filename), error=True )

	def showSupport( self ):
		SupportWindow()

	def showAbout( self ):
		AboutWindow()


class MainMenuOption( object ):

	""" A primary menu option button on the Main Menu tab.
		e.g. for the 'Disc Management' or 'Disc Management' buttons. """

	def __init__( self, canvas, coords, text, hoverColor, clickCallback, currentMenuOptionCount, hoverText='' ):

		# Store parameters
		self.canvas = canvas
		self.coords = coords
		self.color = hoverColor
		self.callback = clickCallback
		self.font = ( 'A-OTF Folk Pro H', 11 )
		self.mouseHovered = False
		self.selfTag = selfTag = 'menuOpt' + str( currentMenuOptionCount + 1 )

		# Rejoin text with the unicode 'Hair Space' to add some kerning (https://jkorpela.fi/chars/spaces.html)
		self.text = u'\u200A'.join( list(text) )
		self.hoverText = u'\u200A'.join( list(hoverText) )

		# Create black text for the hover effect (using two objects rather than just changing color of the other text object to make a bolder font)
		self.blackText1 = canvas.create_text( coords[0]+24, coords[1]+12, text=self.text, anchor='w', tags=('blackText', selfTag,), font=self.font, fill='black' )
		self.blackText2 = canvas.create_text( coords[0]+24, coords[1]+12, text=self.text, anchor='w', tags=('blackText', selfTag,), font=self.font, fill='black' )

		# Create the default orange text
		self.textObj = canvas.create_text( coords[0]+24, coords[1]+12, text=self.text, anchor='w', tags=('menuOptions', selfTag), font=self.font, fill='#cb9832' )

		# Finish creating the middle background elements and store them
		boundingBox = canvas.bbox( self.textObj )
		textWidth = boundingBox[2] - boundingBox[0]
		resizedImage = canvas.optionBgMiddlebase.resize( (textWidth+8, 30) )
		self.bgMiddle = ImageTk.PhotoImage( resizedImage )
		resizedImageH = canvas.optionBgMiddlebaseH.resize( (textWidth+8, 30) )
		self.bgMiddleH = ImageTk.PhotoImage( resizedImageH )

		# Add the option background image objects to the canvas
		self.bdLeft = canvas.create_image( coords[0], coords[1], image=canvas.optionBgLeftImage, anchor='nw', tags=('menuOptionsBg', selfTag) )
		self.bdMiddle = canvas.create_image( coords[0]+20, coords[1], image=self.bgMiddle, anchor='nw', tags=('menuOptionsBg', selfTag) )
		self.bdRight = canvas.create_image( coords[0]+28+textWidth, coords[1], image=canvas.optionBgRightImage, anchor='nw', tags=('menuOptionsBg', selfTag) )

		# Layer the menu option background elements over the character image, and the text over the menu option background elements
		if not canvas.debugMode:
			canvas.lower( self.blackText1, 'charImage' )
			canvas.lower( self.blackText2, 'charImage' )
			canvas.tag_raise( 'menuOptionsBg', 'charImage' )
		canvas.tag_raise( 'menuOptions', 'menuOptionsBg' )

		# Add click and hover event handlers
		canvas.tag_bind( selfTag, '<1>', self.clicked )
		canvas.tag_bind( selfTag, '<Enter>', self.hovered )

	def clicked( self, event ):

		""" Initial method called when an option is clicked on. """

		if self.color == '#7b5467': return # Sound Effect Editor; temporarily disabled

		self.callback( event )
		self.unhovered() # todo: fix; not working in this case?

	def unhoverOthers( self ):

		""" Secondary method to "unhover" main menu options from mouse interaction.
			Because the main menu options are made of multiple canvas items, there
			are usually multiple hover/unhover events when the user interacts with it. 
			Thus, instead of binding an unhover event to the option's canvas items, an 
			unhover method is fired when hovering over the background. And this method is 
			fired whenever an option is hovered, ensuring all other options are unhovered. """

		for menuOption in self.canvas.options:
			if menuOption != self and menuOption.mouseHovered:
				menuOption.unhovered()

	def hovered( self, event=None ):
		# Ignore redundant calls (there may be quite a few)
		if self.mouseHovered:
			return

		# Ensure other options are unhovered
		self.unhoverOthers()
		self.mouseHovered = True

		# Update the text at the bottom of the main border
		self.canvas.itemconfigure( self.canvas.bottomText, text=self.hoverText )

		if self.color == '#7b5467': return # Sound Effect Editor; temporarily disabled

		self.canvas['cursor'] = 'hand2'

		# Swap to the hover image and change the font color
		self.canvas.itemconfig( self.bdLeft, image=self.canvas.optionBgLeftImageH )
		self.canvas.itemconfig( self.bdMiddle, image=self.bgMiddleH )
		self.canvas.itemconfig( self.bdRight, image=self.canvas.optionBgRightImageH )
		#self.canvas.itemconfig( self.textObj, fill='black' )

		# Update black text position
		#self.canvas.create_text( self.coords[0]+24, self.coords[1]+12, text=self.text, anchor='w', tags=('menuOptions'), font=self.font, fill='black' )
		self.canvas.tag_raise( self.blackText1, 'menuOptions' )
		self.canvas.tag_raise( self.blackText2, 'menuOptions' )

		# Update the border color (if it's different from the current color)
		if self.color != self.canvas.currentBorderColor:
			self.canvas.loadBorderImages( self.color )

		globalData.gui.playSound( 'menuChange' )

	def unhovered( self, event=None ):

		self.canvas['cursor'] = ''

		# Swap to the default image and change the font color
		self.canvas.itemconfig( self.bdLeft, image=self.canvas.optionBgLeftImage )
		self.canvas.itemconfig( self.bdMiddle, image=self.bgMiddle )
		self.canvas.itemconfig( self.bdRight, image=self.canvas.optionBgRightImage )
		#self.canvas.itemconfig( self.textObj, fill='#cb9832' )

		# Update black text position
		self.canvas.tag_lower( self.blackText1, 'menuOptions' )
		self.canvas.tag_lower( self.blackText2, 'menuOptions' )

		self.mouseHovered = False


class MainMenuCanvas( Tk.Canvas ):

	def __init__( self, mainGui, canvasFrame, width, height ):
		Tk.Canvas.__init__( self, canvasFrame, width=width, height=height, borderwidth=0, highlightthickness=0 )

		# Prevent the canvas from being scrollable
		def noScroll( arg1, arg2 ): return
		self.yview_scroll = noScroll

		self.debugMode = DEBUGMODE
		self.testSet = '' # For testing. Set to 'ABGxx' to test a specific character image, or to '' for no testing
		self.charImageOffsets = { # Used to adjust the X offset of character images (those not included default to 0)
			'ABG01': 4, # C. Falcon
			'ABG02': 28 # Bowser
		}

		self.mainMenuFolder = os.path.join( globalData.paths['imagesFolder'], 'Main Menu' )
		self.mainGui = mainGui
		self.imageSet = ''
		self.topLayerId = -1
		self.afterId = -1
		self.animId = -1
		self.minIdleTime = 16 # Before next animation (character swap or wireframe effect)
		self.maxIdleTime = 34 # Must be at least double the minimum (due to halving in first use)
		self.pauseAnimations = False

		self.currentBorderColor = ''
		self.borderImgs = {}	# key=color, value=imagesDict (key=imageName, value=image)
		self.borderParts = {}	# key=partName, value=canvasID
		self.options = []
		self.menuOptionCount = 0

		self.mainBorderWidth = 800 # Keep this an even number
		self.mainBorderHeight = 530
		self.bottomTextWidth = 308
		self.bottomText = -1 # Item ID for the main menu bottom text

		self.initFonts()

		# Load and apply the main background image
		if not self.debugMode:
			self.create_image( 500, 375, image=mainGui.imageBank('bg', 'Main Menu'), anchor='center' )

		# Load the mask used to create the wireframe effect
		maskPath = os.path.join( self.mainMenuFolder, "ABGM.png" )
		self.origMask = Image.open( maskPath )

		# Load primary menu options
		self.loadBorderImages( '#394aa6' ) # Blue
		self.initOptionImages()

		# Load the character image
		if not self.debugMode:
			self.imageSets = { 'ABG{:02}'.format(i) for i in range(4) } # ABG = Animated BackGrounds
			self.loadImageSet()

			if not globalData.checkSetting( 'disableMainMenuAnimations' ):
				self.queueNewAnimation( shortFirstIdle=True )

		# Add some test buttons if testing/debugging
		if self.debugMode or self.testSet:
			self.create_text( width-40, 80, text='Fade', fill='silver', tags=('testFade',) )
			self.create_text( width-40, 120, text='Wireframe\nPass', fill='silver', tags=('testWireframe',) )
			self.tag_bind( 'testFade', '<1>', self.testFade )
			self.tag_bind( 'testWireframe', '<1>', self.testWireframe )

		# Show current coordinates of mouse in debug mode
		if self.debugMode:
			self.mouseCoordsVar = Tk.StringVar()
			ToolTip( self, textvariable=self.mouseCoordsVar )
			self.bind( '<Motion>', self.showCoords )

	def showCoords( self, event ):

		""" Displays mouse coordinates at the top of the canvas when in debug mode. """

		self.mouseCoordsVar.set( '{} x {}'.format(event.x, event.y) )

	def initFonts( self ):

		""" Load fonts from the fonts folder into Tkinter. These fonts will be referred to 
			by family name (e.g. 'A-OTF Folk Pro H'). To find the exact name of a font, you 
			may use 'tkFont.families()'. """

		self.initFont( 'A-OTF Folk Pro, Bold.otf' ) # For the main menu buttons/options text
		self.initFont( 'A-OTF Folk Pro, Heavy.otf' ) # For the main menu top text
		self.initFont( 'A-OTF Folk Pro, Medium.otf' ) # For the main menu bottom text
		#print( tkFont.families() )

	def initFont( self, fontName, private=True, enumerable=True ):

		""" Makes fonts located in file `fontpath` available to the font system.

			`private`     if True, other processes cannot see this font, and this 
						font will be unloaded when the process dies.
			`enumerable`  if True, this font will appear when enumerating fonts.
						 (this is necessary if you want the font to appear with tkFont.families().)

			See https://msdn.microsoft.com/en-us/library/dd183327(VS.85).aspx
		"""

		# This function was taken from:
		# https://github.com/ifwe/digsby/blob/f5fe00244744aa131e07f09348d10563f3d8fa99/digsby/src/gui/native/win/winfonts.py#L15
		# This function is written for Python 2.x. For 3.x, you have to convert the isinstance checks to bytes and str

		FR_PRIVATE  = 0x10
		FR_NOT_ENUM = 0x20

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

		if numFontsAdded != 2:
			filename = os.path.basename( fontpath )
			print( 'Unable to load two fonts from {}.'.format(filename) )

		return bool( numFontsAdded )

	def loadImageSet( self ):

		""" Loads the images necessary for a character background (main + wireframe), and creates an alpha mask for it. """

		# Randomly select an image set (without selecting the current one), unless doing testing
		if self.testSet:
			self.imageSet = self.testSet
		else:
			self.imageSet = random.choice( list(self.imageSets.difference( [self.imageSet] )) )

		# Load the necessary images (not using the imageBank because we want to work with these as PIL Image objects)
		wireframePath = os.path.join( self.mainMenuFolder, self.imageSet + "W.png" )
		topImgPath = os.path.join( self.mainMenuFolder, self.imageSet + ".png" )

		self.wireframeLayer = Image.open( wireframePath ).convert( 'RGBA' )
		self.origTopLayer = Image.open( topImgPath ).convert( 'RGBA' )
		self._transparentMask = Image.new( 'RGBA', self.origTopLayer.size, (0,0,0,0) )
		self.topLayer = ImageTk.PhotoImage( self.origTopLayer )

		# Add the top and wireframe images to the canvas
		originY = ( int(self['height']) - self.mainBorderHeight ) / 2
		bottomBorderY = originY + self.mainBorderHeight - 18

		# Create the canvas image element, or reconfigure an existing one
		defaultXOffset = 635
		xOffset = defaultXOffset + self.charImageOffsets.get( self.imageSet, 0 )
		if self.topLayerId == -1:
			self.topLayerId = self.create_image( xOffset, bottomBorderY, image=self.topLayer, anchor='s', tags=('charImage',) )
			self.tag_bind( self.topLayerId, '<Enter>', self.menuOptionsUnhovered )
		else:
			# The canvas item already exists; reconfigure it
			self.itemconfig( self.topLayerId, image=self.topLayer )

			# Update position (negate the old character-specific xOffset shift, while adding the new one)
			currentX = self.coords( self.topLayerId )[0]
			self.move( self.topLayerId, xOffset-currentX, 0 )

		# Ensure the bottom-text border is over the image
		# self.tag_raise( 'bottomTextBorder', 'charImage' )
		# self.tag_raise( self.bottomText, 'bottomTextBorder' )

		# Load the alpha channel as a new image (for use with the mask)
		self.fullSizeMask = self.wireframeLayer.getchannel( 'A' ) # Returns a new image, in 'L' mode, of the given channel

	def colorizeImage( self, image, color ):

		""" Applies the given color to a given black-and-white image, and returns it. """

		blankImage = Image.new( 'RGBA', image.size, (0, 0, 0, 0) )
		colorScreen = Image.new( 'RGBA', image.size, color )

		return Image.composite( colorScreen, blankImage, image )

	def loadBorderImages( self, color ):

		""" Cuts up the primary border image into multiple pieces, colorizes them, 
			and converts them into images Tkinter can use on the canvas. Storage is 
			needed to prevent garbage collection of the images. """

		# If images for this border color have already been created, just switch to those
		if color in self.borderImgs:
			self.currentBorderColor = color
			self.refreshBorderImages()
			return

		# Load the main border image
		imagePath = os.path.join( self.mainMenuFolder, "mainBorder.png" )
		image = Image.open( imagePath )
		self.borderImgs[color] = imgsDict = {}

		# Load the main border shadow
		shadowImagePath = os.path.join( self.mainMenuFolder, "mainBorderShadow.png" )
		shadowImage = Image.open( shadowImagePath )

		# Add color to the image, and combine it with the 'shadow' portion (dark middle part)
		colorized = self.colorizeImage( image, color )
		shadowImage.paste( colorized, mask=colorized )

		# Calculate sizes for the fill sections
		widthFillTop = self.mainBorderWidth - 118 # -26 - 66 - 26
		widthFillBot = self.mainBorderWidth - self.bottomTextWidth - 76 # -26 - 26 - 12 - 12
		widthFillBotLeft = int( math.floor(widthFillBot / 7.0) )
		widthFillBotRight = widthFillBot - widthFillBotLeft
		heightFill = self.mainBorderHeight - 102 # -70 - 32

		cropped = shadowImage.crop( (0, 70, 26, 88) )
		resized = cropped.resize( (26, heightFill) )
		imgsDict['borderLeft'] = ImageTk.PhotoImage( resized )

		cropped = shadowImage.crop( (0, 0, 26, 70) )
		imgsDict['borderTopLeft'] = ImageTk.PhotoImage( cropped )

		cropped = shadowImage.crop( (26, 0, 48, 70) )
		resized = cropped.resize( (widthFillTop/2, 70) )
		imgsDict['borderTopLeftFill'] = ImageTk.PhotoImage( resized )

		cropped = shadowImage.crop( (48, 0, 114, 70) )
		imgsDict['borderTopCenter'] = ImageTk.PhotoImage( cropped )

		cropped = shadowImage.crop( (114, 0, 150, 70) )
		resized = cropped.resize( (widthFillTop/2, 70) )
		imgsDict['borderTopRightFill'] = ImageTk.PhotoImage( resized )

		cropped = shadowImage.crop( (150, 0, 176, 70) )
		imgsDict['borderTopRight'] = ImageTk.PhotoImage( cropped )

		cropped = shadowImage.crop( (150, 70, 176, 88) )
		resized = cropped.resize( (26, heightFill) )
		imgsDict['borderRight'] = ImageTk.PhotoImage( resized )

		cropped = shadowImage.crop( (150, 88, 176, 120) )
		imgsDict['borderBottomRight'] = ImageTk.PhotoImage( cropped )

		cropped = shadowImage.crop( (138, 88, 150, 120) )
		resized = cropped.resize( (widthFillBotRight, 32) )
		imgsDict['borderBottomRightFill'] = ImageTk.PhotoImage( resized )
		resized = cropped.resize( (widthFillBotLeft, 32) )
		flipped = resized.transpose( Image.FLIP_LEFT_RIGHT )
		imgsDict['borderBottomLeftFill'] = ImageTk.PhotoImage( flipped )

		cropped = shadowImage.crop( (126, 88, 138, 120) )
		imgsDict['borderBottomRightInner'] = ImageTk.PhotoImage( cropped )
		flipped = cropped.transpose( Image.FLIP_LEFT_RIGHT )
		imgsDict['borderBottomLeftInner'] = ImageTk.PhotoImage( flipped )

		cropped = shadowImage.crop( (50, 88, 126, 120) )
		resized = cropped.resize( (self.bottomTextWidth, 32) )
		imgsDict['borderBottomCenter'] = ImageTk.PhotoImage( resized )

		cropped = shadowImage.crop( (0, 88, 26, 120) )
		imgsDict['borderBottomLeft'] = ImageTk.PhotoImage( cropped )
		
		cropped = shadowImage.crop( (26, 70, 150, 88) )
		resized = cropped.resize( (self.mainBorderWidth-52, heightFill) )
		imgsDict['borderMiddle'] = ImageTk.PhotoImage( resized )

		# Add the canvas elements for the first time, or reconfigure their images
		if not self.currentBorderColor:
			# First time this has been called; add the canvas elements
			self.currentBorderColor = color
			self.initMainBorder()
		else:
			self.currentBorderColor = color
			self.refreshBorderImages()

	def refreshBorderImages( self ):

		""" Updates the border images to the 'current' color (based on what was last selected). 
			This reconfigures canvas image objects using cached images from the borderImgs dict. """

		imgsDict = self.borderImgs[self.currentBorderColor]

		self.itemconfig( self.borderParts['borderLeft'], image=imgsDict['borderLeft'] )

		self.itemconfig( self.borderParts['borderTopLeft'], image=imgsDict['borderTopLeft'] )
		self.itemconfig( self.borderParts['borderTopLeftFill'], image=imgsDict['borderTopLeftFill'] )
		self.itemconfig( self.borderParts['borderTopCenter'], image=imgsDict['borderTopCenter'] )
		self.itemconfig( self.borderParts['borderTopRightFill'], image=imgsDict['borderTopRightFill'] )
		self.itemconfig( self.borderParts['borderTopRight'], image=imgsDict['borderTopRight'] )

		self.itemconfig( self.borderParts['borderRight'], image=imgsDict['borderRight'] )

		self.itemconfig( self.borderParts['borderBottomRight'], image=imgsDict['borderBottomRight'] )
		self.itemconfig( self.borderParts['borderBottomRightFill'], image=imgsDict['borderBottomRightFill'] )
		self.itemconfig( self.borderParts['borderBottomRightInner'], image=imgsDict['borderBottomRightInner'] )
		self.itemconfig( self.borderParts['borderBottomCenter'], image=imgsDict['borderBottomCenter'] )
		self.itemconfig( self.borderParts['borderBottomLeftInner'], image=imgsDict['borderBottomLeftInner'] )
		self.itemconfig( self.borderParts['borderBottomLeftFill'], image=imgsDict['borderBottomLeftFill'] )
		self.itemconfig( self.borderParts['borderBottomLeft'], image=imgsDict['borderBottomLeft'] )

		self.itemconfig( self.borderParts['borderMiddle'], image=imgsDict['borderMiddle'] )

	def initMainBorder( self ):

		""" Places all images for the main background's border on the canvas. 
			This will only be done once on initial program load; subsequent 
			updates to these objects are made by the refresh method above. """

		imgsDict = self.borderImgs[self.currentBorderColor]

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
		self.borderParts['borderLeft'] = self.create_image( originX, originY+70, image=imgsDict['borderLeft'], anchor='nw', tags=('mainBorder',) )

		# Top
		self.borderParts['borderTopLeft'] = self.create_image( originX, originY, image=imgsDict['borderTopLeft'], anchor='nw', tags=('mainBorder',) )
		self.borderParts['borderTopLeftFill'] = self.create_image( originX+26, originY, image=imgsDict['borderTopLeftFill'], anchor='nw', tags=('mainBorder',) )
		self.borderParts['borderTopCenter'] = self.create_image( originX+26+(widthFillTop/2), originY, image=imgsDict['borderTopCenter'], anchor='nw', tags=('mainBorder',) )
		self.borderParts['borderTopRightFill'] = self.create_image( originX+26+(widthFillTop/2)+66, originY, image=imgsDict['borderTopRightFill'], anchor='nw', tags=('mainBorder',) )
		self.borderParts['borderTopRight'] = self.create_image( rightSideX, originY, image=imgsDict['borderTopRight'], anchor='nw', tags=('mainBorder',) )

		# Right
		self.borderParts['borderRight'] = self.create_image( rightSideX, originY+70, image=imgsDict['borderRight'], anchor='nw', tags=('mainBorder',) )

		# Bottom
		self.borderParts['borderBottomRight'] = self.create_image( rightSideX, bottomY, image=imgsDict['borderBottomRight'], anchor='nw', tags=('mainBorder',) )
		self.borderParts['borderBottomRightFill'] = self.create_image( rightSideX, bottomY, image=imgsDict['borderBottomRightFill'], anchor='ne', tags=('mainBorder',) )
		self.borderParts['borderBottomRightInner'] = self.create_image( rightSideX-widthFillBotRight, bottomY, image=imgsDict['borderBottomRightInner'], anchor='ne', tags=('mainBorder',) )
		self.borderParts['borderBottomCenter'] = self.create_image( originX+38+widthFillBotLeft, bottomY, image=imgsDict['borderBottomCenter'], anchor='nw', tags=('mainBorder',) )
		self.borderParts['borderBottomLeftInner'] = self.create_image( originX+26+widthFillBotLeft, bottomY, image=imgsDict['borderBottomLeftInner'], anchor='nw', tags=('mainBorder',) )
		self.borderParts['borderBottomLeftFill'] = self.create_image( originX+26, bottomY, image=imgsDict['borderBottomLeftFill'], anchor='nw', tags=('mainBorder',) )
		self.borderParts['borderBottomLeft'] = self.create_image( originX, bottomY, image=imgsDict['borderBottomLeft'], anchor='nw', tags=('mainBorder',) )

		# Middle-fill area (shadow)
		self.borderParts['borderMiddle'] = self.create_image( originX+26, originY+70, image=imgsDict['borderMiddle'], anchor='nw', tags=('mainBorder',) )
		self.tag_bind( self.borderParts['borderMiddle'], '<Enter>', self.menuOptionsUnhovered )

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
		imgsDict['borderCenterBracket'] = ImageTk.PhotoImage( bracketImage )
		self.create_image( textXCoord, textYCoord, image=imgsDict['borderCenterBracket'], anchor='n', tags=('mainBorder', 'bottomTextBorder') )

		# Add top text
		text = u'Main Menu'
		text = u'\u2009'.join( list(text) ) # Rejoin with the unicode 'Thin Space' to add some kerning (https://jkorpela.fi/chars/spaces.html)
		italicFont = tkFont.Font( family='A-OTF Folk Pro H', size=16, slant='italic', weight='bold' )
		self.create_text( originX+26+widthFillTop/4, originY-4, text=text, anchor='n', tags=('mainBorder',), font=italicFont, fill='#aaaaaa' )

		# Add bottom text
		text = 'Open a disc or root folder.'
		text = u'\u200A'.join( list(text) )
		self.bottomText = self.create_text( textXCoord, textYCoord+4, text=text, anchor='n', tags=('mainBorder',), font=('A-OTF Folk Pro M', 11), fill='#aaaaaa' )

	def initOptionImages( self ):
		
		""" Stores option background images to prevent 
			garbage collection and redundant image processing. """

		# Load the option background images
		imagePath = os.path.join( self.mainMenuFolder, "optionBg.png" )
		imagePathH = os.path.join( self.mainMenuFolder, "optionBgHover.png" )
		image = Image.open( imagePath )
		imageH = Image.open( imagePathH )

		# Add color to the image, and split it into parts
		self.optionBgLeftImage = image.crop( (0, 0, 20, 30) )
		self.optionBgMiddlebase = image.crop( (20, 0, 23, 30) ) # Width modified later
		self.optionBgRightImage = image.crop( (23, 0, 56, 30) )
		self.optionBgLeftImageH = imageH.crop( (0, 0, 20, 30) )
		self.optionBgMiddlebaseH = imageH.crop( (20, 0, 23, 30) ) # Width modified later
		self.optionBgRightImageH = imageH.crop( (23, 0, 56, 30) )

		self.optionBgLeftImage = ImageTk.PhotoImage( self.optionBgLeftImage )
		self.optionBgRightImage = ImageTk.PhotoImage( self.optionBgRightImage )
		self.optionBgLeftImageH = ImageTk.PhotoImage( self.optionBgLeftImageH )
		self.optionBgRightImageH = ImageTk.PhotoImage( self.optionBgRightImageH )

	def menuOptionsUnhovered( self, event=None ):

		""" Primary method to "unhover" main menu options from mouse interaction.
			Because the main menu options are made of multiple canvas items, there
			are usually multiple hover/unhover events when the user interacts with it. 
			Thus, instead of binding an unhover event to the option's canvas items, this 
			method is fired when hovering over the background. And another secondary/failsafe 
			method is fired whenever an option is hovered, ensuring all other options are unhovered. """

		for menuOption in self.options:
			if menuOption.mouseHovered:
				menuOption.unhovered()

	def addMenuOption( self, text, borderColor, xOffset, clickCallback, pause=False, hoverText='' ):
		
		# Calculate main menu border position (top-left edges of border)
		originX = ( int(self['width']) - self.mainBorderWidth ) / 2
		originY = ( int(self['height']) - self.mainBorderHeight ) / 2

		# Calculate position of this menu option
		optOriginX = originX + 90 + xOffset
		verticalSpace = self.mainBorderHeight - 80 # -48 - 32
		leftoverSpace = verticalSpace - ( 30 * self.menuOptionCount )
		if leftoverSpace > 310: # Make the grouping a little tighter if there's a ton of extra space
			originY += 60
			leftoverSpace -= 120
		spaceBetweenOptions = leftoverSpace / ( self.menuOptionCount + 1 )
		currentMenuOptionCount = len( self.find_withtag('menuOptions') )
		optOriginY = originY + 48 + spaceBetweenOptions + (spaceBetweenOptions + 30) * ( currentMenuOptionCount )

		# Add the text object
		option = MainMenuOption( self, (optOriginX, optOriginY), text, borderColor, clickCallback, currentMenuOptionCount, hoverText )
		self.options.append( option )

		if pause:
			# Used to animate option additions (adds a slight delay between displaying multiple options)
			self.update_idletasks()
			time.sleep( .03 )

	def testFade( self, event ):
		self.after_cancel( self.afterId )
		self.after_cancel( self.animId )
		self._fadeProgress = -99
		self.animId = self.after_idle( self.updateBgFadeSwap )

	def testWireframe( self, event ):
		self.after_cancel( self.afterId )
		self.after_cancel( self.animId )
		self.startWireframePass()

	def queueNewAnimation( self, shortFirstIdle=False ):

		# Exit if in testing mode
		if self.testSet:
			return

		# Start a timer to count down to creating the wireframe effect or swap images
		if shortFirstIdle:
			maxIdle = self.maxIdleTime / 2 # Shorter first idle
		else:
			maxIdle = self.maxIdleTime

		timeTilNextAnim = random.randint( self.minIdleTime, maxIdle )
		self.afterId = self.after( timeTilNextAnim*1000, self.animateCharImage )

	def animateCharImage( self ):

		""" Begins a new animation for the character image. Has a 2/3 chance to 
			start a wireframe pass, or a 1/3 chance to swap the character image. 
			Certain conditions may delay (re-queue) the animation for a later time. """

		# If the main menu isn't currently visible, skip this animation and queue a new one
		if not self.showAnimations():
			self.queueNewAnimation()
			return

		# If the About window is open, prevent Main Menu animations to preserve performance
		elif self.mainGui.getOpenWindow( 'About MMW' ):
			self.queueNewAnimation()
			return

		# Decide on an animation and start it
		if random.choice( (0, 1, 2) ): # Wireframe pass (2/3 chance)
			self.startWireframePass()

		else: # Character fade & swap
			self._fadeProgress = -99
			self.animId = self.after_idle( self.updateBgFadeSwap )

	def remove( self ):

		""" Cancel the next pending animation and any current animations, 
			and remove the whole menu from the GUI. """
		
		self.after_cancel( self.afterId )
		self.after_cancel( self.animId )

		geomManager = self.winfo_manager()

		if geomManager == 'grid':
			self.grid_remove()
		elif geomManager == 'pack':
			self.pack_forget()
		elif geomManager == 'place':
			self.place_forget()

	def startWireframePass( self ):
		self._maskPosition = -self.origMask.height
		self.animId = self.after_idle( self.updateWireframePass )

	def updateWireframePass( self ):
		# Copy the mask of the top layer's alpha channel, and combine it with the mask
		tic = time.clock()
		mask = self.fullSizeMask.copy()
		mask.paste( self.origMask, (0, self._maskPosition) )
		self.topLayer = ImageTk.PhotoImage( Image.composite(self.origTopLayer, self.wireframeLayer, mask) )

		# Update the display with the new image
		self.itemconfigure( self.topLayerId, image=self.topLayer )

		self._maskPosition += 2

		if self._maskPosition < (self.origMask.height + self.origTopLayer.height):
			# Check how much time was needed to perform the pass, and subtract that from the target iteration duration
			toc = time.clock()
			timeToSleep = int( (.040 - (toc - tic)) * 1000 )
			if timeToSleep < 0:
				timeToSleep = 0
			self.animId = self.after( timeToSleep, self.updateWireframePass )
		else:
			# This animation is complete
			self.queueNewAnimation()

	def updateBgFadeSwap( self ):
		sleepTime = .04
		stepSize = 3

		tic = time.clock()
		self._fadeProgress += stepSize

		if self._fadeProgress < 0:
			opacity = abs( self._fadeProgress ) / 100.0
		elif self._fadeProgress == 0:
			# Load the images for the new image set
			self.loadImageSet()
			opacity = 0
		else:
			opacity = self._fadeProgress / 100.0

		# Update the layer's alpha
		self.topLayer = ImageTk.PhotoImage( Image.blend(self._transparentMask, self.origTopLayer, opacity) )
		self.itemconfigure( self.topLayerId, image=self.topLayer )

		if self._fadeProgress < 100:
			toc = time.clock()
			timeToSleep = int( (sleepTime - (toc - tic)) * 1000 )
			if opacity == 0:
				timeToSleep = 300
			elif timeToSleep < 0:
				timeToSleep = 0
			self.animId = self.after( timeToSleep, self.updateBgFadeSwap )
		else:
			# This animation is complete
			self.queueNewAnimation()

	def displayPrimaryMenu( self ):
		self.menuOptionCount = 4
		self.addMenuOption( 'Load Recent', '#394aa6', 25, self.loadRecentMenu, hoverText='Return to your latest work.' ) # blue
		self.addMenuOption( 'Load Disc', '#a13728', -19, self.openDisc, hoverText='Load an ISO or GCM file.' ) # red
		self.addMenuOption( 'Load Root Folder', '#077523', -47, self.openRoot, hoverText='Load an extracted filesystem.' ) # green
		self.addMenuOption( 'Browse Code Library', '#9f853b', -35, self.browseCodes, hoverText='Browse code-based game mods.' ) # yellow

	def removeOptions( self, showAnimations=True, callBack=None ):

		""" Remove existing menu options (slide left). This is recursive until the options are fully hidden; 
			uses the GUI mainloop to iterate animation steps rather than a loop in this method in order to 
			keep the GUI responsive throughout. When this is done, the callback is called. """

		# Slide-left existing options; skip the animation if this tab isn't visible
		if showAnimations:
			stepDistance = 90

			self.move( 'menuOptions', -stepDistance, 0 )
			self.move( 'menuOptionsBg', -stepDistance, 0 )
			self.move( 'blackText', -stepDistance, 0 )

			# Check if the options have been fully hidden
			for itemId in self.find_withtag( 'menuOptionsBg' ):
				if self.bbox( itemId )[2] > 0:
					# One of the options is still visible; need another iteration
					self.after( 16, self.removeOptions, showAnimations, callBack )
					return

		# Remove existing options
		self.delete( 'menuOptions' )
		self.delete( 'menuOptionsBg' )
		self.delete( 'blackText' )
		self.menuOptionCount = 0
		self.options = []

		if showAnimations:
			self.update_idletasks()
			time.sleep( .05 )

		if callBack:
			callBack()

	def displayDiscOptions( self ):

		""" Remove existing options, and display a new set of options for disc or root folder operations. """

		showAnimations = self.showAnimations()

		# Remove any existing options
		if self.menuOptionCount > 0:
			self.removeOptions( showAnimations, self.displayDiscOptions )
			return

		# Add new options
		if globalData.disc.isMelee and globalData.disc.is20XX:
			self.menuOptionCount = 7
			self.addMenuOption( 'Disc Management', '#394aa6', 74, self.mainGui.loadDiscManagement, showAnimations, 'View or change files in the disc.' ) # blue
			self.addMenuOption( 'Code Manager', '#a13728', 21, self.browseCodes, showAnimations, 'Make code-based modifications.' ) # red
			self.addMenuOption( 'Stage Manager', '#077523', -19, self.mainGui.loadStageEditor, showAnimations, 'Configure stage loading.' ) # green
			self.addMenuOption( 'Music Manager', '#9f853b', -40, self.loadMusicManager, showAnimations, 'Listen to and configure music.' ) # yellow
			self.addMenuOption( 'Sound Effect Editor', '#7b5467', 0, self.mainGui.loadDiscManagement, showAnimations, 'WIP!' ) # pinkish (blended)
			self.addMenuOption( 'Character Modding', '#53c6b8', -35, self.loadCharacterModder, showAnimations, 'Modify character properties.' ) # teal
			self.addMenuOption( 'Debug Menu Editor', '#582493', -22, self.loadDebugMenuEditor, showAnimations, 'Modify the in-game Debug Menu.' ) # purple

		elif globalData.disc.isMelee:
			self.menuOptionCount = 6
			self.addMenuOption( 'Disc Management', '#394aa6', 60, self.mainGui.loadDiscManagement, showAnimations, 'View or change files in the disc.' ) # blue
			self.addMenuOption( 'Code Manager', '#a13728', 14, self.browseCodes, showAnimations, 'Make code-based modifications.' ) # red
			self.addMenuOption( 'Stage Manager', '#077523', -22, self.mainGui.loadStageEditor, showAnimations, 'Configure stage loading.' ) # green
			self.addMenuOption( 'Music Manager', '#9f853b', -40, self.loadMusicManager, showAnimations, 'Listen to and configure music.' ) # yellow
			self.addMenuOption( 'Sound Effect Editor', '#7b5467', 0, self.mainGui.loadDiscManagement, showAnimations, 'WIP!' ) # pinkish (blended)
			self.addMenuOption( 'Character Modding', '#53c6b8', -30, self.loadCharacterModder, showAnimations, 'Modify character properties.' ) # teal

		else:
			self.menuOptionCount = 3
			self.addMenuOption( 'Disc Management', '#394aa6', 21, self.mainGui.loadDiscManagement, showAnimations, 'View or change files in the disc.' ) # blue
			self.addMenuOption( 'Code Manager', '#a13728', -34, self.browseCodes, showAnimations, 'Make code-based modifications.' ) # red
			self.addMenuOption( 'Music Manager', '#9f853b', -14, self.loadMusicManager, showAnimations, 'Listen to and configure music.' ) # yellow

		# Set the main menu bottom text
		text = 'Choose a category to begin.'
		text = u'\u200A'.join( list(text) )
		self.itemconfigure( self.bottomText, text=text )

	def loadRecentMenu( self, event ):

		""" Spawns a context menu at the mouse's current location. """

		#globalData.gui.playSound( 'menuChange' )

		guiFileMenu = self.mainGui.fileMenu
		guiFileMenu.repopulate() # Rebuilds the 'recent' submenu
		guiFileMenu.recentFilesMenu.post( event.x_root+10, event.y_root - 60 )

	def openDisc( self, event ):
		self.mainGui.promptToOpenFile( 'iso' )

	def openRoot( self, event ):
		self.mainGui.promptToOpenRoot()
		
	def browseCodes( self, event ):
		self.mainGui.fileMenu.browseCodeLibrary()

		self.mainGui.root.update()
		self.mainGui.updateProgramStatus( 'Ready' )

	def loadMusicManager( self, event=None ):

		""" Add the Music Manager tab to the GUI and select it. """
		
		# Load the audio tab
		if not self.mainGui.audioManagerTab:
			self.mainGui.audioManagerTab = AudioManager( self.mainGui.mainTabFrame, self.mainGui )
			self.mainGui.audioManagerTab.loadFileList()

		# Switch to the tab
		self.mainGui.mainTabFrame.select( self.mainGui.audioManagerTab )

		# self.mainGui.root.update()
		# globalData.gui.updateProgramStatus( 'Ready' )
		self.mainGui.playSound( 'menuSelect' )

	def loadCharacterModder( self, event=None ):

		# Load the tab
		if not self.mainGui.charModTab:
			self.mainGui.addCharModdingTab()

		# Switch to the tab
		self.mainGui.mainTabFrame.select( self.mainGui.charModTab )

		# self.mainGui.root.update()
		# globalData.gui.updateProgramStatus( 'Ready' )
		self.mainGui.playSound( 'menuSelect' )

	def loadDebugMenuEditor( self, event=None ):

		""" Add the Debug Menu Editor tab to the GUI and select it. """
		
		# Add/initialize the Debug Menu Editor tab
		if not self.mainGui.menuEditorTab:
			self.mainGui.menuEditorTab = DebugMenuEditor( self.mainGui.mainTabFrame, self.mainGui )
		self.mainGui.menuEditorTab.loadTopLevel()

		# Switch to the tab
		self.mainGui.mainTabFrame.select( self.mainGui.menuEditorTab )
		
		# self.mainGui.root.update()
		# globalData.gui.updateProgramStatus( 'Ready' )
		self.mainGui.playSound( 'menuSelect' )

	def isVisible( self ):

		""" Returns whether this widget is visible (top-level non-child window focused, relative to other programs). """

		width, height, x, y = self.winfo_width(), self.winfo_height(), self.winfo_rootx(), self.winfo_rooty()

		if (width, height, x, y) == (1, 1, 0, 0):
			is_toplevel = False
		else:
			is_toplevel = self.winfo_containing( x + (width // 2), y + (height // 2) ) is not None

		return is_toplevel

	def mainMenuSelected( self ):

		""" Returns True/False for whether the Main Menu tab is currently selected in the GUI. """

		currentlySelectedTab = self.mainGui.root.nametowidget( self.mainGui.mainTabFrame.select() )
		if currentlySelectedTab == self.mainGui.mainMenu.master:
			return True
		else:
			return False

	def showAnimations( self ):

		""" Should return true if the Main Menu of the GUI is selected and the option to allow 
			them is enabled. This avoids extra processing if the animation wouldn't be visible. """

		if self.debugMode or not self.mainMenuSelected():
			return False
		elif not self.isVisible() or self.pauseAnimations:
			return False
		else:
			return not globalData.checkSetting( 'disableMainMenuAnimations' )


#																		/------------\
#	====================================================================   Main GUI   =========
#																		\------------/

class MainGui( Tk.Frame, object ):

	def __init__( self, showPrimaryMenu=True ): # Build the interface

		self.root = Tk.Tk()
		self.root.withdraw() # Keeps the GUI minimized until it is fully generated
		self.style = ttk.Style()

		globalData.loadProgramSettings( True ) # Load using BooleanVars. Must be done after creating Tk.root

		self.loadVolume()

		self._imageBank = {} # Repository for GUI related images
		self._soundBank = {}
		self.audioEngine = None
		self.audioGate = Event()
		self.audioGate.set()

		self.defaultWindowWidth = 1000
		self.defaultWindowHeight = 750
		self.defaultSystemBgColor = self.root.cget( 'background' )

		# Font control/adjustments
		default_font = tkFont.nametofont( "TkDefaultFont" )
		#print(tkFont.families())
		#print(default_font.actual())
		self.defaultFontSize = default_font.actual()['size']
		#default_font.configure( size=30 ) # Use negative values to specify in pixel height
		#self.root.option_add( "*Font", default_font ) # Use this to apply the default font to be used everywhere
		
		# Build the main program window
		#self.root.tk.call( 'wm', 'iconphoto', self.root._w, self.imageBank('appIcon') )
		self.root.iconbitmap( os.path.join(globalData.paths['imagesFolder'], 'appIcon.ico') )
		self.root.geometry( str(self.defaultWindowWidth) + 'x' + str(self.defaultWindowHeight) + '+100+50' )
		self.root.title( "Melee Modding Wizard - v" + globalData.programVersion )
		self.root.minsize( width=500, height=400 )
		self.dnd = TkDnD( self.root )
		self.root.protocol( 'WM_DELETE_WINDOW', self.onProgramClose ) # Overrides the standard window close button.
		
		# Main Menu Bar & Context Menus
		self.menubar = Tk.Menu( self.root )																			# Keyboard shortcuts:
		self.fileMenu = FileMenu( self.menubar ) # Storing this on the GUI so we can later easily access the 'recent' submenu
		self.menubar.add_cascade( label='File', menu=self.fileMenu, underline=0 )										# File			[F]
		self.menubar.add_cascade( label='Settings', menu=SettingsMenu( self.menubar ), underline=0 )					# Settings		[S]
		self.menubar.add_cascade( label='Tools', menu=ToolsMenu( self.menubar ), underline=0 )							# Tools			[T]
		self.menubar.add_cascade( label='About', menu=AboutMenu( self.menubar ), underline=0 )							# About			[A]

		self.mainTabFrame = ttk.Notebook( self.root )
		self.dnd.bindtarget( self.mainTabFrame, self.dndHandler, 'text/uri-list' )

		self.discTab = None				# ttk.Frame
		self.discDetailsTab = None		# ttk.Frame
		self.codeManagerTab = None		# ttk.Frame
		self.codeConstructionTab = None # ttk.Frame
		self.menuEditorTab = None		# ttk.Frame
		self.stageManagerTab = None		# ttk.Frame
		self.audioManagerTab = None		# ttk.Frame
		self.charModTab = None			# ttk.Notebook
		self.texturesTab = None			# ttk.Notebook
		self.currentTab = None

		self.mainTabFrame.grid( column=0, row=0, sticky='nsew' )
		self.mainTabFrame.bind( '<<NotebookTabChanged>>', self.onMainTabChanged )

		# Set the bottom status message
		self.statusLabel = ttk.Label( self.root, text='Ready' )
		self.statusLabel.grid( column=0, row=1, sticky='w', pady=2, padx=7 )

		# Configure resize behavior
		self.root.columnconfigure( 'all', weight=1 )
		self.root.rowconfigure( 0, weight=1 )
		self.root.rowconfigure( 1, weight=0 ) # No vertical resize allocation for status bar

		# Set up the scroll handler. Unbinding native scroll functionality on some classes to prevent problems when scrolling on top of other widgets
		self.root.unbind_class( 'Text', '<MouseWheel>' ) # Allows onMouseWheelScroll below to handle this
		self.root.unbind_class( 'Treeview', '<MouseWheel>' ) # Allows onMouseWheelScroll below to handle this
		self.root.unbind_class( 'Listbox', '<MouseWheel>' ) # Allows onMouseWheelScroll below to handle this
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
		self.menubar.bind( "<<MenuSelect>>", self.updateMenuBarMenus )

		# GUI has been minimized until rendering was complete. This brings it to the foreground
		self.root.deiconify() # Must be done before checking widget widths/heights below

		# Add a frame for the main menu canvas, and use its height to determine the canvas' height
		canvasFrame = ttk.Frame( self.mainTabFrame )
		self.mainTabFrame.add( canvasFrame, text=' Main Menu ' )
		self.root.update_idletasks()
		mainMenuWidth = canvasFrame.winfo_width()
		mainMenuHeight = canvasFrame.winfo_height()
		self.lastSelectedTab = canvasFrame

		# Initialize and add the Main Menu
		self.mainMenu = MainMenuCanvas( self, canvasFrame, mainMenuWidth, mainMenuHeight )
		self.mainMenu.place( relx=0.5, rely=0.5, anchor='center' )

		if showPrimaryMenu:
			self.mainMenu.displayPrimaryMenu()

	# def updateProgressDisplay( self, event ):

	# 	""" Used to handle progress updates from other threads using the event queue.
	# 		(Other threads should not directly update the GUI themselves.) """

	# 	self.updateProgramStatus( event.message )

	def updateProgramStatus( self, newStatus='', warning=False, error=False, success=False, forceUpdate=False ):

		""" Updates the status bar at the very bottom of the interface. 
			'newStatus' can be left empty if only the color needs to be updated. """

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
		if newStatus:
			self.statusLabel['text'] = newStatus

		# Force the GUI to update now rather than waiting for idle tasks
		if forceUpdate:
			self.statusLabel.update()

	def getOpenWindow( self, windowName ):
		if hasattr( self.root, 'uniqueWindows' ):
			return self.root.uniqueWindows.get( windowName, None )
		else:
			return None

	def imageBank( self, imageName, subFolder='', showWarnings=True, getAsPilImage=False ):

		""" Loads and stores images required by the GUI. This allows all of the images to be 
			stored together in a similar manner, and ensures references to all of the loaded 
			images are stored, which prevents them from being garbage collected (which would 
			otherwise cause them to disappear from the GUI after rendering is complete). The 
			images are only loaded when first requested, and then kept for future reference. 
			
			One or more subFolders may be provided as 'subFolder' or 'subFolder/deeperSubs'. """

		key = subFolder + '/' + imageName
		image = self._imageBank.get( key )

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
				if getAsPilImage:
					image = self._imageBank[key] = Image.open(imagePath)
				else:
					image = self._imageBank[key] = ImageTk.PhotoImage( Image.open(imagePath) )
			except:
				if showWarnings:
					print( 'Unable to load the image, "' + imagePath + '"' )

		return image

	def loadVolume( self ):

		""" Validates program volume (for sound effects and music) from the settings.ini file; 
			ensures it's a float between 0 and 1, and sets a default value instead if it's not. """

		volume = globalData.checkSetting( 'volume' )
		try:
			self.volume = float( volume )
			if self.volume < 0 or self.volume > 1.0:
				raise Exception()
		except:
			self.volume = float( globalData.defaultSettings['volume'] )
			message = ( 'The settings.ini file contails a bad value for "volume": {}. '
						'The program volume should be set as a float between 0 (off) and 1.0 (full volume). The volume will be set to the default volume of {}.'.format(volume, self.volume) )
			tkMessageBox.showwarning( message=message, title='Invalid Volume Setting', parent=self.root )

	def playSound( self, soundName ):

		# Cancel if sound is disabled
		if self.volume == 0:
			return

		audioFilePath = self._soundBank.get( soundName )

		if not audioFilePath:
			audioFilePath = os.path.join( globalData.paths['audioFolder'], soundName + ".wav" )
			if not os.path.exists( audioFilePath ):
				print( 'Invalid or missing sound file for', soundName )
				return
			self._soundBank[soundName] = audioFilePath

		# Play the audio clip in a separate thread so that this function is non-blocking
		audioThread = Thread( target=self._playSoundHelper, args=(audioFilePath,) )
		audioThread.start()

	def _playSoundHelper( self, soundFilePath ):

		""" Helper (thread-target) function for playSound(). Runs in a separate 
			thread to prevent audio playback from blocking anything else. """

		p = None
		wf = None
		stream = None

		try:
			# Prevent race conditions on multiple sounds playing at once (can cause a crash); 
			# Only allow one file to begin playing (create a stream) at a time.
			self.audioGate.wait() # Blocks until the following is done (event is re-set)
			self.audioGate.clear()

			# Instantiate PyAudio and open the target audio file
			p = pyaudio.PyAudio()
			wf = wave.open( soundFilePath, 'rb' )

			# Open an audio data stream
			stream = p.open( format=p.get_format_from_width(wf.getsampwidth()),
							channels=wf.getnchannels(),
							rate=wf.getframerate(),
							output=True )

			self.audioGate.set() # Allow a new sound to be opened/initialized

			# Continuously read/write data from the file to the stream until there is no data left
			data = wf.readframes( 1024 )
			while len( data ) > 0:
				# Unpack the bytes data (series of halfwords) so we can modify the values
				chunkFormat = '<' + str( len(data)/2 ) + 'h'
				unpackedData = struct.unpack( chunkFormat, data )

				# Adjust the volume. Multiply each value by the current volume (0-1.0 value)
				unpackedData = [sample * self.volume for sample in unpackedData]

				# Re-pack the data as raw bytes
				data = struct.pack( chunkFormat, *unpackedData )

				stream.write( data )
				data = wf.readframes( 1024 )

		except AttributeError:
			pass # Program probably closed while playing audio

		except Exception as err:
			soundFileName = os.path.basename( soundFilePath )
			print( 'Unable to play "{}" sound.'.format(soundFileName) )
			print( err )

		# Stop the stream
		if stream:
			stream.stop_stream()
			stream.close()

		# Close PyAudio
		if p:
			p.terminate()
		
		# Close the wav file
		if wf:
			wf.close()

	def updateMenuBarMenus( self, event ):

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

		""" This function adjusts the height of rows in the treeview widgets, since multiple treeviews can't be individually configured.
			It also starts DAT file structural analysis or image searching when switching to the SA tab or DAT File Tree tab if a DAT file is loaded. 
			If an attempt is made to switch to a tab that is already the current tab, this function will not be called. """

		# Get the widget of the currently selected tab (a ttk.Frame or ttk.Notebook)
		self.lastSelectedTab = self.currentTab
		self.currentTab = self.root.nametowidget( self.mainTabFrame.select() )
		self.currentTab.focus() # Don't want keyboard/widget focus at any particular place yet

		if self.currentTab == self.codeManagerTab:
			# Need to populate the initial tab and align the control panel
			self.codeManagerTab.onTabChange()
		elif self.codeManagerTab: # Not selected, but it exists
			self.codeManagerTab.emptyModsPanels() # For improved GUI performance

		# Update the height for entries in Treeview widgets, which can't be specified per-widget-instance
		if self.currentTab == self.texturesTab:
			self.style.configure( 'Treeview', rowheight=76 )

			# if globalDatFile and not self.datTextureTree.get_children():
			# 	# May not have been scanned for textures yet (or none were found).
			# 	scanDat()

		else:
			self.style.configure( 'Treeview', rowheight=20 )

			# if globalDatFile and self.currentTab == self.savTab and not self.fileStructureTree.get_children():
			# 	# SAV tab hasn't been populated yet. Perform analysis.
			# 	analyzeDatStructure()

	def onMouseWheelScroll( self, event ):

		""" Checks the widget under the mouse when a scroll event occurs, and then looks upward through the 
			GUI geometry for widgets (or parents of those widgets, etc.) that may have scroll wheel support. """

		# Cross-platform resources on scrolling:
			# - http://stackoverflow.com/questions/17355902/python-tkinter-binding-mousewheel-to-scrollbar
			# - https://www.daniweb.com/programming/software-development/code/217059/using-the-mouse-wheel-with-tkinter-python

		# Get the widget currently under the mouse
		widget = self.root.winfo_containing( event.x_root, event.y_root )

		if not widget:
			# Might be over a render window
			for window in pyglet.app.windows:
				if window._mouse_in_window:
					window.on_mouse_scroll( event )
					break
			return

		# Traverse upwards through the parent widgets, looking for a scrollable widget
		while widget:
			# Check for a rendering window (winfo_class sees this as a regular Frame)
			# if widget.__class__.__name__ == 'RenderEngine':
			# 	widget.zoom( event )
			# 	return

			if widget.winfo_class() in ( 'Text', 'Treeview', 'Canvas', 'Listbox' ):
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
		elif len( filepaths ) > 1: # todo: allow for specific features later
			msg( 'Please only provide one file to load at a time.', 'File Import Error' )
			self.updateProgramStatus( 'Too many files recieved', warning=True )
			return

		# Normalize the path (prevents discrepancies between paths with forward vs. back slashes, etc.)
		filepath = os.path.normpath( filepaths[0] )

		# Validate the path
		if not os.path.exists( filepath ): # Failsafe; unsure how this might happen
			msg( 'The given path does not seem to exist!', 'File Import Error' )
			self.updateProgramStatus( 'Invalid path provided', error=True )

		# Check if it's a disc root directory.
		elif os.path.isdir( filepath ):
			if isExtractedDirectory( filepath, showError=False ):
				# Check whether there are changes that the user wants to save for files that must be unloaded
				if self.changesNeedSaving( globalData.disc ):
					return

				self.loadRootOrDisc( filepath, updateDefaultDirectory )

			else:
				msg( 'Only extracted root directories are able to opened in this way.' )
				self.updateProgramStatus( 'Invalid input', error=True )

		else: # Valid file path given
			extension = os.path.splitext( filepath )[1].lower()

			if extension == '.iso' or extension == '.gcm':
				# Check whether there are changes that the user wants to save for files that must be unloaded
				if self.changesNeedSaving( globalData.disc ):
					return

				self.loadRootOrDisc( filepath, updateDefaultDirectory )

			else: # Likely some form of DAT or an image file for the texture editing tabs
				# Get the widget of the currently selected tab (a ttk.Frame or ttk.Notebook)
				currentTab = self.root.nametowidget( self.mainTabFrame.select() )

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

				elif currentTab == self.texturesTab and extension in ( '.tpl', '.png' ):
					# Get the sub-tab that's currently selected
					texturesSubTab = self.root.nametowidget( self.texturesTab.select() )
					iids = texturesSubTab.datTextureTree.selection() # Returns a tuple of iids, or an empty string if nothing is selected.
					if not iids:
						msg( 'Please select a texture to replace!', 'No Textures Selected', warning=True )
						return
					
					# Load the image and replace the texture currently in the file
					try:
						newImage = Image.open( filepath ) # Loads the texture as a PIL image
					except Exception as err:
						self.updateProgramStatus( 'Unable to open the texture due to an unrecognized error. Check the log for details', error=True )
						print( 'Unable to load image for preview text; {}'.format(err) )
						return

					# Check the texture(s) currently selected to replace it(them)
					if len( iids ) > 1:
						imageDataOffsets = [ int(iid) for iid in iids ]
						texturesSubTab.replaceMultipleTextures( newImage, imageDataOffsets )
					else: # Only replacing one texture (one texture selected)
						texturesSubTab.replaceSingleTexture( newImage, int(iids[0]) )

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

	def loadRootOrDisc( self, targetPath, updateDefaultDirectory, updateStatus=True, preserveTreeState=False, switchTab=False, updatedFiles=None ):
		
		# Remember this file for future recall
		globalData.rememberFile( targetPath, updateDefaultDirectory )

		# Load the disc, and load the disc's info into the GUI
		# tic = time.clock()
		globalData.disc = Disc( targetPath )
		globalData.disc.load()
		# toc = time.clock()
		# print( 'disc load time:', toc-tic )
		
		# Update the Disc File Tree and Disc Details tabs
		if self.discTab:
			self.discTab.loadDisc( updateStatus=updateStatus, preserveTreeState=preserveTreeState, switchTab=switchTab, updatedFiles=updatedFiles )
			self.mainTabFrame.update_idletasks() # Update the GUI immediately before moving on to update other tabs
		if self.discDetailsTab:
			self.discDetailsTab.loadDiscDetails()

		# Update the Code Manager
		if self.codeManagerTab:
			self.codeManagerTab.autoSelectCodeRegions()
			self.codeManagerTab.scanCodeLibrary( playAudio=False )

		if globalData.disc.isMelee:
			# If this is 20XX, add/initialize the Debug Menu Editor tab
			if globalData.disc.is20XX:
				if self.menuEditorTab:
					self.menuEditorTab.loadTopLevel()

			# Remove the Debug Menu Editor if this isn't 20XX and it's present
			elif self.menuEditorTab:
				self.menuEditorTab.destroy()
				self.menuEditorTab = None

			# Update Stage Manager
			if self.stageManagerTab:
				if globalData.disc.is20XX:
					self.stageManagerTab.load20XXStageLists()
				else:
					self.stageManagerTab.loadVanillaStageLists()

			# Update Music Manager
			if self.audioManagerTab:
				self.audioManagerTab.loadFileList()

			# Re-load the Character Modding tabs
			if self.charModTab:
				self.charModTab.repopulate()

		self.mainMenu.displayDiscOptions()

		self.playSound( 'menuSelect' )
		
		# Start the banner animation now that everything is done loading
		if self.discTab:
			self.discTab.updateBanner( self.discTab )
			if self.discDetailsTab:
				self.discTab.updateBanner( self.discDetailsTab )

	def saveAs( self ):

		""" Creates a new file (via dialog prompt to user), and then saves 
			changes to the currently loaded ISO/GCM disc image or root folder. 
			
			If saving (exporting) the DOL, any changes made to it will not be saved to 
			the current disc, and will only be saved to the new DOL file. """

		disc = globalData.disc
		if not disc:
			return -1

		origDiscName = os.path.basename( disc.filePath )

		if disc.isRootFolder:
			fileNameWithoutExt = newFilenameSuggestion = origDiscName
			ext = 'iso'
		else:
			fileNameWithoutExt, ext = origDiscName.rsplit( '.', 1 )
			newFilenameSuggestion = '{} - Copy'.format( fileNameWithoutExt )

		# Prompt the user for a save directory and filename
		newPath = tkFileDialog.asksaveasfilename(
			parent=self.root,
			title="Where would you like to save the new disc?",
			initialdir=globalData.getLastUsedDir( 'iso' ),
			initialfile=newFilenameSuggestion,
			defaultextension=ext[1:],
			filetypes=[('Standard disc image', '*.iso'), ('GameCube disc image', '*.gcm'), ('DOL files', '*.dol'), ("All files", "*.*")]
			)
		if not newPath: # User canceled the operation
			return

		# Check if saving the DOL (if so, save it to a new external file) or a disc
		fileExt = newPath.rsplit( '.', 1 )[1]
		if fileExt.lower() in ( 'dol' ):
			# Set the default program directory
			globalData.setLastUsedDir( newPath, 'dol' )

			self.saveDol( disc, newPath )

		else: # Assume it's a disc
			# Set the default program directory
			globalData.setLastUsedDir( newPath, 'iso' )

			# Save the disc to a new path
			self.save( newPath )

	def saveDol( self, disc, savePath ):

		""" Saves currently selected codes to the DOL if the Code Manager tab is open, 
			and then saves the DOL to a new external file. The dol in the currently 
			opened disc should be unaffected. """

		# Check if the Codes Manager tab is open
		if self.codeManagerTab:
			# Make a backup copy of the DOL that's currently in the disc (so we can replace the original when done)
			origDol = disc.dol
			dolBackup = disc.copyFile( origDol )

			# Save codes to the current DOL
			returnCode = self.codeManagerTab.saveCodesToDol()

			# Check for an error, and ask whether to save other changes anyway
			if not returnCode == 0:
				if returnCode == 1:
					message = ( 'Code changes could not be saved, because the DOL could not be restored ' 
								'from a vanilla copy of the game. You may want to double check the file '
								'paths for your current disc and the vanilla reference disc.' )
					msg( message, 'Unable to Save Codes', error=True )
					return
				elif returnCode == 2:
					message = ( 'Some code changes could not be saved to the DOL.' 
								'\n\nWould you like to continue and save it anyway?' )
					if not tkMessageBox.askyesno( 'Unable to Save Some Codes', message ):
						return
				elif returnCode == 3:
					msg( 'No code changes could not be saved!', 'Unable to Save Codes', error=True )
					return
				elif returnCode == 4:
					# Mod internal conflicts found; user was notified and aborted save operation
					return
				elif returnCode == 5:
					# User aborted save operation (on Gecko code conversion prompt)
					return
				else:
					raise Exception( 'Unrecognized return code from code manager save method! {}'.format(returnCode) )

			# Restore the backed-up DOL
			disc.replaceFile( origDol, dolBackup, False )

			# Rescan for codes installed to reflect the current disc rather than the saved DOL
			self.codeManagerTab.scanCodeLibrary( playAudio=False )

		# Write the file to an external/standalone file
		successful = disc.dol.export( savePath )

		if successful:
			# Attempt to save the codes.bin file with the DOL if successful and it's present
			codesFile = disc.getFile( 'codes.bin' )

			if codesFile:
				# Save the codes file
				saveDir = os.path.dirname( savePath )
				codesPath = os.path.join( saveDir, 'codes.bin' )
				successful = codesFile.export( codesPath )

				if successful:
					self.updateProgramStatus( 'DOL and codes.bin files saved successfully', success=True )
				else:
					self.updateProgramStatus( 'DOL saved successfully; error saving codes.bin', warning=True )
			
			# Only DOL file present, which was exported successfully
			else:
				self.updateProgramStatus( 'DOL saved successfully', success=True )

			self.playSound( 'menuChange' )
		else:
			self.updateProgramStatus( 'Unable to export. Check the error log file for details', error=True )

	def save( self, newPath='' ):

		""" Saves changes to the currently loaded ISO/GCM disc image or root folder. 
			If newPath is provided, e.g. from .saveAs(), a new disc file is created. """

		disc = globalData.disc
		if not disc:
			return -1

		# Save code mods if that tab is open
		if self.codeManagerTab:
			returnCode = self.codeManagerTab.saveCodesToDol()

			# Check for an error, and ask whether to save other changes anyway
			if not returnCode == 0:
				if returnCode == 1:
					message = ( 'Code changes could not be saved, because the DOL could not be restored.' 
								'\n\nWould you like to continue and save other changes anyway?' )
				elif returnCode == 2:
					message = ( 'Some code changes could not be saved.' 
								'\n\nWould you like to continue and save other changes anyway?' )
				elif returnCode == 3:
					message = ( 'No code changes could not be saved.' 
								'\n\nWould you like to continue and save other changes anyway?' )
				elif returnCode == 4:
					# Mod internal conflicts found; user was notified and aborted save operation
					return -1
				elif returnCode == 5:
					# User aborted save operation (on Gecko code conversion prompt)
					return -1
				else:
					raise Exception( 'Unrecognized return code from code manager save method: {}'.format(returnCode) )

				if not tkMessageBox.askyesno( 'Unable to Save Code Changes', message ):
					return -1

		# Save all file changes to the disc
		returnCode, updatedFiles = disc.save( newPath )

		if returnCode == 0:
			# Reload the disc and show a save confirmation
			self.loadRootOrDisc( disc.filePath, True, False, True, False, updatedFiles )
			self.updateProgramStatus( 'Save Successful', success=True )
		else:
			# Update the status bar, and generate a more detailed message for the pop-up below
			message = translateDiscSaveError( returnCode, disc )

			# For most errors, ask if the user would like to try saving again
			if returnCode > 2:
				if tkMessageBox.askretrycancel( 'Problem While Saving', message ):
					returnCode = self.save( newPath )

		return returnCode

	def concatAllUnsavedChanges( self, basicSummary ):

		""" Creates and returns a list of unsaved changes throughout the program that are pending a save operation. """
		
		changes = []

		# Check for disc changes
		disc = globalData.disc
		unsavedFiles = disc.getUnsavedChangedFiles()
		if unsavedFiles or disc.unsavedChanges or disc.rebuildReason or not basicSummary:
			changes.extend( disc.concatUnsavedChanges(unsavedFiles, basicSummary) )

		# Scan for code-related changes
		if self.codeManagerTab:
			pendingCodeChanges = self.codeManagerTab.summarizeChanges()
			if len( pendingCodeChanges ) > 1:
				if changes:
					changes.append( '' ) # Results in extra line breaks in the finished report after .join()
				changes.extend( pendingCodeChanges )

		# Check the Character Modding tab if it's open
		if self.charModTab:
			charsModified = self.charModTab.hasUnsavedChanges()
			if charsModified:
				if changes:
					changes.append( '' ) # Results in extra line breaks in the finished report after .join()
				if len( charsModified ) == 1:
					changes.append( charsModified[0] + ' has unsaved subAction changes in the Character Modding tab.' )
				elif len( charsModified ) < 5:
					chars = grammarfyList( charsModified )
					changes.append( chars + ' have unsaved subAction changes in the Character Modding tab.' )
				else:
					charCount = str( len(charsModified) )
					changes.append( charCount + ' characters in the Character Modding tab have unsaved subAction changes.' )

		return changes
		
	def changesNeedSaving( self, disc, programClosing=False ):

		""" Asks the user if they would like to forget any unsaved disc changes. 
			Used in order to close the program or load a new file. Returns True 
			if the user has unsaved changes pending a save operation. """

		if not disc:
			return False

		try:
			changes = self.concatAllUnsavedChanges( basicSummary=True )
			if not changes:
				return False

			# Changes have been recorded. Ask the user if they'd like to discard them
			if programClosing:
				warning = [ "It looks like the changes below haven't been saved to disc.", 'Are you sure you want to close?', '' ]
			else:
				warning = [ 'The changes below will be forgotten if you change or reload the disc before saving. Are you sure you want to do this?', '' ]
			warning.extend( changes )

			forgetChanges = tkMessageBox.askyesno( 'Unsaved Changes', '\n'.join(warning) )

			return ( not forgetChanges )

		except Exception as err:
			print( 'Encountered an error while attempting to close: {}'.format(err) )
			return False

	def onProgramClose( self ):
		globalData.saveProgramSettings()

		if not self.changesNeedSaving( globalData.disc, True ):
			# if self.texturesTab:
			# 	self.texturesTab.haltAllScans( programClosing=True )
			# else:
			self.root.destroy() # Stops the GUI's mainloop and destroys all widgets. https://stackoverflow.com/a/42928131/8481154

	def loadDiscManagement( self, event=None ):
		
		""" Adds the Disc File Tree tab to the GUI, populates it, and switches to it. """

		# Add/initialize the Disc File Tree tab
		if not self.discTab:
			self.discTab = DiscTab( self.mainTabFrame, self )
			self.discTab.debugMode = DEBUGMODE
		self.discTab.loadDisc( switchTab=True )

		# self.root.update() # Flush pending hover events that will try to change the program status
		# globalData.gui.updateProgramStatus( 'Ready' )

		# Play a sound effect and start the banner animation
		self.playSound( 'menuSelect' )
		self.discTab.updateBanner( self.discTab )

	def loadStageEditor( self, event=None, targetStage=None ):

		""" Adds the Stage Manager tab to the GUI and selects it. If a specific file is provided, 
			that stage will be added as a new tab as well and will be switched to instead of the main tab. """
	
		# Load the stage info/editor
		if not self.stageManagerTab:
			self.stageManagerTab = StageManager( self.mainTabFrame, self )

		# Switch to the main Stage Manager tab
		self.mainTabFrame.select( self.stageManagerTab )

		if targetStage:
			# Create a tab for the specific requested stage and switch to it
			self.stageManagerTab.addStageFileTab( targetStage )
		else:
			# Population will take a second; so switch first to show that something is happening
			self.stageManagerTab.update_idletasks()

		if globalData.disc.is20XX:
			self.stageManagerTab.load20XXStageLists()
		else:
			self.stageManagerTab.loadVanillaStageLists()

		# self.root.update() # Flush pending hover events that will try to change the program status
		# globalData.gui.updateProgramStatus( 'Ready' )
		self.playSound( 'menuSelect' )

	def addCodeConstructionTab( self ):
		
		if not self.codeConstructionTab:
			self.codeConstructionTab = ttk.Notebook( self.mainTabFrame )
			
			self.mainTabFrame.add( self.codeConstructionTab, text=' Code Construction ' )
			#self.codeConstructionTab.pack( fill='both', expand=1, pady=7 )

	def addCharModdingTab( self ):

		if not self.charModTab:
			self.charModTab = CharModding( self.mainTabFrame, self )

	def runInEmulator( self, event=None ):

		""" Runs the currently loaded disc or root folder structure in Dolphin. """

		if not globalData.disc:
			msg( 'No disc has been loaded!' )
			return

		globalData.dolphinController.start( globalData.disc )

	def saveAndRun( self, event=None ):

		""" Saves current changes, and then runs the disc or root folder in Dolphin. """

		# Shut down Dolphin in case the game is running (can't save to it otherwise)
		globalData.dolphinController.stopAllDolphinInstances()

		# Save
		returnCode = self.save()

		# Boot
		if returnCode == 0 or returnCode == 1: # Success or no changes to save
			self.runInEmulator()


def translateDiscSaveError( returnCode, disc ):

	""" Translates the given returnCode from the disc's save method into two human-
		readable messages. One is a short message output to the status bar, if the 
		GUI is initialized. The second is a longer, more detailed message which 
		should be reported to the user in some way, and is returned by this function. 
		This function is used by both the GUI and by command-line functions. """

	# Generate a short message for the status bar
	if returnCode == 1:
		shortMessage = 'There were no changes to be saved'
		longMessage = 'There are no changes to be saved.'
	elif returnCode == 2:
		shortMessage = longMessage = 'Unable to save the disc; there are missing system files!' # todo: report which are missing
	elif returnCode == 3:
		shortMessage = 'Unable to create a new disc file. Be sure this program has write permissions'
		longMessage = ( "Unable to create a new copy of the disc. Be sure there is write access to the destination, and if there is a file being "
					 "replaced, be sure it's not write-locked (meaning another program has it open, preventing it from being written to)." )
	elif returnCode == 4:
		if not os.path.exists( disc.filePath ):
			shortMessage = 'Unable to find the original disc file for saving'
			longMessage = ( 'Unable to find the original disc file for saving. Be sure that it has not been moved or deleted.' )
		elif not disc.rebuildReason:
			shortMessage = 'Unable to open the original disc file for saving'
			longMessage = ( 'Unable to open the original disc file for saving. Be sure that '
				  			'the file is not being used by another program (like Dolphin :P).' )
		else: # Only opening in read mode in this case (not sure how this might fail)
			shortMessage = 'Unable to open the original disc file for reading'
			longMessage = shortMessage + '.'
	elif returnCode == 5:
		shortMessage = 'Unable to save the disc; there was an unrecognized error during file writing'
		longMessage = shortMessage + '.'
	elif returnCode == 6:
		shortMessage = 'Unable to save the disc; unable to overwrite existing file'
		longMessage = ( 'The disc file to replace could not be overwritten.\n\n'
					"Be sure there is write access to the destination, and that the file isn't write-"
					"locked (meaning another program has it open, preventing it from being overwritten)." )
	elif returnCode == 7:
		shortMessage = 'Unable to save the disc; could not rename discs or rename original'
		longMessage = ( 'A back-up file was successfully created, however there was an error while attempting to rename the files and remove the original.\n\n'
					"This can happen if the original file is locked for editing (for example, if it's open in another program)." )
	else:
		shortMessage = 'Unable to save the disc; unrecognized save method return code: ' + str( returnCode )
		longMessage = shortMessage + '.'

	# Update the program's status bar
	if globalData.gui:
		if returnCode == 1:
			globalData.gui.updateProgramStatus( shortMessage )
		else:
			globalData.gui.updateProgramStatus( shortMessage, error=True )

	return longMessage


#																		/-----------------------------------\
#	====================================================================   Command Line Parsing & Functions  =========
#																		\-----------------------------------/

def set_default_subparser(self, name, args=None, positional_args=0):

	""" Default subparser selection. Call after setup, just before parse_args()
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
		parser = argparse.ArgumentParser( description='Program for modding SSBM (Super Smash Bros. Melee), offering '
													  'a GUI as well as command-line support. Other GameCube and Wii '
													  'games are also supported with some features.' )

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
		discOpsParser.add_argument( '-b', '--build', dest='rootFolderPath', help='Builds a disc file (ISO or GCM) from a given root folder path. '
											'The folder should contain a "sys" folder, and optionally a "files" folder (or else files will be taken from '
											'the same root folder). The disc will be built in the root path given, unless the --output option is also provided.' )
		discOpsParser.add_argument( '-d', '--discPath', help='Provide a filepath for a target disc or root folder for the program to '
															 'operate on. This is required for most of the disc operations (particularly, '
															 'those that say they operate on a "given disc").' )
		discOpsParser.add_argument( '-e', '--export', help='Export one or more files from a given disc. Use an ISO path to target a specific file '
														   'within the disc: \ne.g. "--export PlSsNr.dat" or "--export ./audio/us/mario.ssm" '
														   'If operating on multiple files, this should be a list of ISO paths (separated by spaces). '
														   'Alternatively, you may instead provide a text file containing a list of ISO paths (one on each line). '
														   'If the --output command is not also used, files are output to the current working directory.', nargs='+', metavar='ISOPATH' )
		discOpsParser.add_argument( '-i', '--import', dest='_import', help='Provide one or more filepaths for external/standalone files to be imported '
														   'into a given disc. Supplement this with the --isoPath (-p) command to define what file(s) '
														   'in the disc to replace. The given filepath may be a single path, or a list of paths for '
														   'multiple files (separated by spaces). If operating on multiple files, the list of paths '
														   'should be in the same order as those in the --isoPath argument.', nargs='+', metavar='FILEPATH' )
		discOpsParser.add_argument( '-l', '--listFiles', action="store_true", help='List the files within a given disc. May be used with --info.' )
		discOpsParser.add_argument( '-n', '--info', action="store_true", help='Show various information on a given disc. May be used with --listFiles.' )
		discOpsParser.add_argument( '-nbu', '--no-backup-on-rebuild', dest='noBackupOnRebuild', action="store_true", help='Do not back up (create a copy of) '
																	'the disc in cases where it needs to be rebuilt. Instead, the original disc will be '
																	'replaced by a new file by the same name.' )
		discOpsParser.add_argument( '-o', '--output', dest='outputFilePath', help='Provides an output path for various operations. May be just a folder path, '
																				  'or it may include the file name in order to name the finished file.' )
		discOpsParser.add_argument( '-p', '--isoPath', help='Used to target one or more specific files within a disc for other various operations. '
															'e.g. "PlSsNr.dat" or "./audio/us/mario.ssm". If operating on multiple files, this should '
															'be a list of ISO paths (separated by spaces). Alternatively, you may instead provide a text '
															'file containing a list of ISO paths (one on each line). ', nargs='+' )

		# Define "test" options
		testOpsParser = subparsers.add_parser( 'test', help='Asset test tool. Used to validate or boot-test assets such as character or stage files.' )
		testOpsParser.add_argument( '-b', '--boot', metavar='FILEPATH', help='Provide a filepath for a character/stage/etc., to have boot-tested in Dolphin.' )
		testOpsParser.add_argument( '-d', '--debug', action="store_true", help='Use this flag to run Dolphin in Debug Mode when using the --boot command.' )
		testOpsParser.add_argument( '-v', '--validate', metavar='FILEPATH', help='Validate files to determine if they are of an expected type. '
															 'By default, this will attempt to validate them as "dat" files, however you may change '
															 'this using the --validationType command to be more specific. You may pass one or more '
															 'file paths to this command. Or you may instead provide a JSON file or JSON-formatted '
															 'string for input (see the Command-Line Usage doc for details and examples). By default, '
															 'this feature will print results to stdout, in a basic human-readable format. '
															 'However, you may instead output results to a JSON file or to stdout as a JSON-'
															 'formatted string by using the --outputJsonFile and/or --outputJsonString arguments.'
															 'The exit code when using this feature can also tell you the result of the operation. '
															 'If you convert the exit code to binary, the resulting 1s and 0s indicate a pass with 0, '
															 'or a fail with 1. Thus, the number will be 0 if all test cases passed. Or for example '
															 'if the exit code is 6, and three files were provided, 6 = 110 in binary, so the first '
															 'two files failed validation, while the last file passed.', nargs='+' )
		testOpsParser.add_argument( '-vt', '--validationType', metavar='TYPE', help='Provide the expected file type(s) for the --validate command. '
																	'If only one type is given, all of the given paths will be expected to be that '
																	'type. Or you may provide a list of types; one for each file path given. The '
																	'default if this command is not used is "dat". Other allowable validation types '
																	'are "music", "menu", "stage", and "character". This argument is ignored when '
																	'using JSON input.', default=['dat'], nargs='+' )
		testOpsParser.add_argument( '-ojf', '--outputJsonFile', metavar='FILEPATH', help='Provide a filepath to output a JSON results file for the '
																				'--validate command.' )
		testOpsParser.add_argument( '-ojs', '--outputJsonString', action="store_true", help='Output JSON results on stdout as a string when using '
																				'the --validate command. Usage of this option will disable the '
																				'normal, human-readable results printout.' )

		# Define "code" options
		codeOpsParser = subparsers.add_parser( 'code', help='Add custom code to a DOL or ISO, or examine one to print out information.' )
		codeOpsParser.add_argument( '-d', '--discPath', help='Provide a filepath for a target disc or root folder for the program to operate on.' )
		codeOpsParser.add_argument( '-dol', '--dolPath', help='Provide a filepath for a DOL file for the program to operate on.' )
		codeOpsParser.add_argument( '-i', '--install', metavar='MODNAME', help='Install code to a given DOL or ISO. Input should be a list of mod names, '
																	'separated by spaces (wrap mod names that have spaces in them with double-quotes). '
																	'Alternatively, you may instead provide a text file containing a list of ISO paths '
																	'(one on each line). Or you may provide the keyword "ALL" to install all mods in '
																	'the given code library.', nargs='+' )
		codeOpsParser.add_argument( '-l', '--library', metavar='FOLDERPATH', help='A path to a Code Library directory. If not provided, '
																					'the default program library will be used.' )
		codeOpsParser.add_argument( '-o', '--output', dest='outputFilePath', help='Provides an output path for various operations. May be just a folder '
																				  'path, or it may include the file name in order to also name the '
																				  'finished file. If this is not used, codes will be saved to the disc '
																				  'or DOL in-place, modifying the existing file. If this argument is '
																				  'used, any changes will be saved to a new copy of the file. If this '
																				  'path is a DOL filepath, then the output file will be a DOL file, '
																				  'even if the input was a disc.' )
		codeOpsParser.add_argument( '-r', '--region', help='Specify the region that the DOL is built for; one of "NTSC" or "PAL". '
							 								'This argument is only required if the region cannot be auto-detected. Typically, the '
															"region can easily be auto-detected if you're providing a disc to operate on, or the "
															"DOL you're providing is for SSBM. So you would likely only need this if you are "
															"providing a non-SSBM DOL and not a disc." )
		codeOpsParser.add_argument( '-v', '--version', help='Specify the version of the DOL; as a string like "1.02". '
							 								'This argument is only required if the version cannot be auto-detected. Typically, the '
															"version can easily be auto-detected if you're providing a disc to operate on, or the "
															"DOL you're providing is for SSBM. So you would likely only need this if you are "
															"providing a non-SSBM DOL and not a disc." )
		codeOpsParser.add_argument( '-cr', '--codeRegions', metavar='REGIONNAME', help='Specify the regions in the DOL where custom code will be installed. '
																	'Input should be a list of region names, as seen in the codeRegionSettings.py file. '
																	'(A name is the portion after the vertical bar, i.e. "|", and thus excludes the '
																	'revision portion.)', nargs='+' )
		codeOpsParser.add_argument( '-cfg', '--configs', metavar='CONFIG', help='Set code configurations (see the Code Library Manual for what these are). '
																	'The format for one config change should be [modName]|[valueName]|[value].', nargs='+' )
		codeOpsParser.add_argument( '-ccr', '--checkCodeRegions', help='Prints out information on available code regions defined in the '
																	'codeRegionSettings.py file. You can filter this list if you also provide '
																	'the --region, --version, and/or --codeRegions arguments. Or you may filter '
																	'by providing the disc or DOL that you intend to install to, which in most '
																	'cases will auto-detect the region and version. If you provide none of these '
																	'other arguments, this will print out information on all defined code regions.', 
																	action="store_true" )
		codeOpsParser.add_argument( '-cd', '--checkDol', help='Prints out information on the given DOL file, or the DOL in the '
																'given disc. This includes the region, version, filesize, and '
																'text/data section information.', action="store_true" )

		# Define "make" options
		#makeOpsParser = subparsers.add_parser( 'make', help='Create specific game assets, such as CSPs or stage preview text.' )

	except Exception as err:
		# Exit the program on error (with exit code 1)
		parser.exit( status=1, message='There was an error in parsing the command line arguments:\n' + str(err) )

	parser.set_default_subparser( 'none' )

	return parser.parse_args()


def determineSavePath( disc ):

	""" Determines a filepath for saving a disc image. 
		This function is used with command-line only. """

	filename = ''
	
	# Determine the new disc filepath output
	if args.outputFilePath:
		# Determine if this is a folder or file path
		if os.path.isdir( args.outputFilePath ):
			directory = args.outputFilePath
		else: # No extension
			directory, filename = os.path.split( args.outputFilePath )

	elif hasattr( args, 'rootFolderPath' ) and args.rootFolderPath: # Only present with 'disc' operations
		# Build in the same directory as the root folder
		directory = os.path.dirname( args.rootFolderPath )

	else: # No output path specified; output to the same directory as the original disc
		assert not disc.isRootFolder, 'Expected to be able to get a file name from a non-root-folder path.'

		return '' # Returning no specific path, the save method will determine a new name by itself

	# Determine a filename from the disc if one has not been given
	if not filename:
		if disc.isRootFolder:
			# Try to use the Long Title for the default filename if the banner file is present (which it should be!)
			bannerFile = disc.files.get( disc.gameId + '/opening.bnr', None )
			if bannerFile:
				stringData = bannerFile.getData( 0x1860, 0x40 ).split( '\x00' )[0]

				if disc.countryCode == 1:
					filename = stringData.decode( 'latin_1' ) + '.iso'
				else: # The country code is for Japanese
					filename = stringData.decode( 'shift_jis' ) + '.iso'
			
			else: # Just use the Game ID
				filename = disc.gameId + '.iso'

		else: # Use the original file name of the disc
			filename = os.path.split( disc.filePath )[1]

	savePath = os.path.join( directory, filename )

	return savePath


def importFilesToDisc():

	""" Function for command-line usage. """

	if not args.isoPath:
		print( 'No --isoPath argument provided! This is required in order to specify the file(s) to replace.' )
		sys.exit( 2 )

	disc = loadDisc( args.discPath )

	# Parse and normalize the isoPaths and filePath input
	isoPaths = parseInputList( args.isoPath, disc.gameId )
	filePaths = parseInputList( args._import )

	if len( isoPaths ) != len( filePaths ):
		print( 'The number of filepaths given does not match the number of ISO paths given for replacement.' )
		sys.exit( 2 )

	# Import the given files
	failedImports = disc.importFiles( isoPaths, filePaths )

	# Load settings (will be referenced for disc saving/rebuilding)
	globalData.loadProgramSettings()
	if args.noBackupOnRebuild:
		globalData.setSetting( 'backupOnRebuild', False )

	# Save the disc
	savePath = determineSavePath( disc )
	returnCode = disc.save( savePath )[0]

	if returnCode == 0:
		print( 'Disc successfully saved to "' + disc.filePath + '"' )

		if failedImports: # Notice of failed imports already reported by .importFiles()
			sys.exit( 6 )
		else:
			sys.exit( 0 )

	else:
		print( translateDiscSaveError(returnCode, disc) )
		sys.exit( returnCode + 100 )


def buildDiscFromRoot():

	""" Function for command-line usage. """

	# Load and initialize a new disc image and the files presented in the root folder
	try:
		newDisc = Disc( args.rootFolderPath )
		
		print( '' ) # For readability
		systemFilePaths = isExtractedDirectory( args.rootFolderPath, showError=True )

		if systemFilePaths:
			newDisc.loadRootFolder( systemFilePaths )
		else:
			sys.exit( 3 )

	except Exception as err:
		print( '\nUnable to initialize and load the root files.' )
		print( err )
		sys.exit( 4 )

	savePath = determineSavePath( newDisc )
	print( 'Disc output path: "' + savePath + '"' )

	# Build the new disc (the progress bar will be printed by the following method)
	globalData.loadProgramSettings()
	tic = time.clock()
	returnCode = newDisc.buildNewDisc( savePath )[0]
	toc = time.clock()

	# Print result message
	if returnCode == 0:
		print( '\nDisc built successfully.  Build time: ' + str(toc-tic) )
		sys.exit( 0 )
	else:
		print( '\n' + translateDiscSaveError(returnCode, newDisc) )
		sys.exit( returnCode + 100 )


def validateAssets():

	""" Function for command-line usage. Validates that a list of given files is of an expected type. """

	# Check if input is a JSON file
	if args.validate[0].lower().endswith( '.json' ):
		isJsonFile = True
	else:
		isJsonFile = False

	# Check for a JSON file or string to parse
	if isJsonFile or '{' in args.validate[0]:
		if isJsonFile:
			try:
				with open( args.validate[0], 'r' ) as jsonFile:
					dictionary = json.load( jsonFile, object_pairs_hook=OrderedDict )
			except Exception as err:
				print( 'Unable to read the given JSON file; {}'.format(err) )
				sys.exit( 1 )

		else: # Must be a json string to parse
			try:
				dictionary = json.loads( args.validate[0], object_pairs_hook=OrderedDict )
			except Exception as err:
				print( 'Unable to parse the given JSON string; {}'.format(err) )
				sys.exit( 1 )

		# Normalize the input (may be a list of dicts)
		if type( dictionary ) == list:
			filePaths = []
			validationTypes = []
			for entry in dictionary:
				filePath = entry.get( 'Path' )
				expectedType = entry.get( 'Expected Type' )
				if not filePath or not expectedType:
					print( 'Invalid JSON formatting. Each entry should have a "Path" and "Expected Type" key.' )
					sys.exit( 2 )
				filePaths.append( filePath )
				validationTypes.append( expectedType )
		
		else:
			# Separate the keys/values into two lists
			filePaths, validationTypes = zip( *dictionary.items() )

	else: # Input is purely in the form of CMD args (file paths to --validate, with or without --validationType)
		# Validate arguments; if validation type is more than one, it should match 1-to-1 with the filepaths list
		if len( args.validationType ) > 1 and len( args.validationType ) != len( args.validate ):
			print( 'Invalid command line aguments. There must be only one validation' )
			print( 'type parameter, or it must match the number of filepaths given.' )
			sys.exit( 2 )

		# Expand the validation type list if only one type is present
		if len( args.validate ) > 1 and len( args.validationType ) == 1:
			filePaths = args.validate
			validationTypes = [ args.validationType[0] ] * len( args.validate )

		# File paths and types should already be available as 1-1 lists
		else:
			filePaths = args.validate
			validationTypes = args.validationType

	# More input validation; check for valid validation types
	for vType in validationTypes:
		if vType not in ( 'dat', 'music', 'menu', 'stage', 'character' ):
			print( 'Invalid command line agument; unrecognized validationType parameter: {}'.format(vType) )
			sys.exit( 2 )

	jsonOutput = []
	statusList = []
	nameColumnWidth = 25
	expectedColumnWidth = 9

	# Test the files and build JSON results
	for filePath, expectedType in zip( filePaths, validationTypes ):

		if expectedType == 'dat':
			fileObj = DatFile( None, -1, -1, '', extPath=filePath, source='file' )

		#elif expectedType == 'dol':
			#fileObj = Dol( None, -1, -1, '', extPath=filePath, source='file' )

		elif expectedType == 'music':
			fileObj = MusicFile( None, -1, -1, '', extPath=filePath, source='file' )

		elif expectedType == 'menu':
			for MenuClass in ( CssFile, SssFile ):
				try:
					fileObj = MenuClass( None, -1, -1, '', extPath=filePath, source='file' )
					fileObj.validate()
					break
				except:
					continue # Last fileObj will fail again in the main check below and status will be FAIL

		elif expectedType == 'stage':
			fileObj = StageFile( None, -1, -1, '', extPath=filePath, source='file' )

		# elif expectedType == 'charData':
		# 	fileObj = CharDataFile( None, -1, -1, '', extPath=filePath, source='file' )

		# elif expectedType == 'charAnim':
		# 	fileObj = CharAnimFile( None, -1, -1, '', extPath=filePath, source='file' )

		# elif expectedType == 'costume':
		# 	fileObj = CharCostumeFile( None, -1, -1, '', extPath=filePath, source='file' )

		elif expectedType == 'character':
			for CharClass in ( CharCostumeFile, CharDataFile, CharAnimFile ):
				try:
					fileObj = CharClass( None, -1, -1, '', extPath=filePath, source='file' )
					fileObj.validate()
					break # Found a valid character file
				except:
					continue # Last fileObj will fail again in the main check below and status will be FAIL
			
		else:
			if not args.outputJsonString:
				filename = os.path.basename( filePath )
				print( '{} | Status: N/A | Validation type not supported'.format(filename) )
			else:
				print( 'Validation type "{}" not yet supported'.format(expectedType) )
			continue

		# File init complete; test for type
		try:
			fileObj.validate()
			status = 'PASS'
			statusList.append( '0' )
			details = ''
		except Exception as err:
			status = 'FAIL'
			statusList.append( '1' )
			err = str( err )

			# Assemble a user message for details output
			if ';' in err:
				details = err.split( ';' )[1].lstrip()
			else:
				details = err
			details = details[0].upper() + details[1:] # Capitalize first letter

		# Construct an entry for a .json file if that flag is set
		if args.outputJsonFile or args.outputJsonString:
			newDict = OrderedDict([])

			newDict['Path'] = filePath
			newDict['Expected Type'] = expectedType
			newDict['Status'] = status
			newDict['Details'] = details

			jsonOutput.append( newDict )

		# Do standard prints if JSON string output is not enabled
		if not args.outputJsonString:
			filename = os.path.basename( filePath )
			if len( filename ) < nameColumnWidth:
				filename += ' ' * ( nameColumnWidth - len(filename) )
			elif len( filename ) > nameColumnWidth:
				filename = filename[:nameColumnWidth-3] + '...'
			if len( expectedType ) < expectedColumnWidth:
				expectedType += ' ' * ( expectedColumnWidth - len(expectedType) )
			print( '{} | Expected: {} | Status: {} - {}'.format(filename, expectedType, status, details) )

	# Write the JSON output file
	if args.outputJsonFile:
		with open( args.outputJsonFile, 'w' ) as newJsonFile:
			json.dump( jsonOutput, newJsonFile, indent=4 )
		print( '\nJSON results output to "{}".'.format(args.outputJsonFile) )

	# Write the JSON output string
	if args.outputJsonString:
		print( json.dumps(jsonOutput) )

	# Create a return code based on pass/fail status of each file
	binaryString = ''.join( statusList )
	sys.exit( int(binaryString, 2) )


def applyExplicitRevision( dol ):

	""" If a specific revision (region and version arguments) was given, 
		validate the input here and update the DOL. """
	
	# Validate the region and version arguments
	if args.region not in ( 'NTSC', 'PAL' ):
		print( 'Invalid region string. Acceptable values are "NTSC" or "PAL".' )
		sys.exit( 2 )
	try:
		major, minor = args.version.split( '.' )
		int( major ); int( minor )
	except:
		print( 'Invalid version string. The version should be a two-number string, like "1.02" or "1.00".' )
		sys.exit( 2 )

	# Check if this was a change from the auto-detect
	if dol.region + ' ' + dol.version == dol.revision:
		# Give a note to the user if this wasn't needed
		if args.discPath:
			print( "This disc's revision (region and version) are already auto-detected as {}.".format(dol.revision) )
		else:
			print( "This DOL's revision (region and version) are already auto-detected as {}.".format(dol.revision) )
		print( "You don't need to specify the --region and --version options for this DOL." )
	else:
		dol.region = args.region
		dol.version = args.version
		dol.revision = dol.region + ' ' + dol.version

		# Re-load region options
		dol.loadCustomCodeRegions()
		globalData.loadRegionOverwriteOptions()


def printRegionInfo( dol ):
	
	""" Prints out information on a custom code regions defined in 
		the codeRegionSettings.py fil. This function is only used 
		for the command-line feature, --checkCodeRegions """

	from basicFunctions import uHex

	# Load custom code regions from the codeRegionSettings.py file, and collect the requested regions
	codeRegions = []
	if args.codeRegions:
		# The user has given us a list of region names to filter by
		dol.loadCustomCodeRegions( collectAll=True )

		# Iterate over the regions collected
		for regionName, regions in dol.customCodeRegions.items():
			if regionName in args.codeRegions:
				for regionStart, regionEnd in regions:
					codeRegions.append( (regionStart, regionEnd, regionName) )
		checkForConflicts = True

	elif dol.revision:
		# Collect only applicable regions
		dol.loadCustomCodeRegions()
		codeRegions = dol.getCustomCodeRegions( searchDisabledRegions=True )
		checkForConflicts = True

	else:
		# Collect all regions
		dol.loadCustomCodeRegions( collectAll=True )
		codeRegions = dol.getCustomCodeRegions( searchDisabledRegions=True )
		checkForConflicts = False # Don't bother, as it's assumed there will be conflicts

	# Check for conflicts among the code regions selected for use
	# if checkForConflicts:
	# 	print( 'Checking if regions overlap...' )
	# 	dol.regionsOverlap( codeRegions ) # A warning will have been given to the user if they overlap
	# else:
	# 	print( 'Skipping check for overlapping regions.' )

	if codeRegions:
		print( '\n    Name:                       Region Start:  Region End:     Length:' )
		lastName = ''
		total = 0
		for regionStart, regionEnd, regionName in codeRegions:
			length = regionEnd - regionStart

			# Add a total for the last region's space if this is the start of a new set of regions
			if lastName and regionName != lastName:
				print( '                                                    Total: {:>10}'.format(uHex(total)) )
				total = 0

			# Print info for this region
			total += length
			print( '{:<32}{:>11}{:>13}{:>13}'.format(regionName, uHex(regionStart), uHex(regionEnd), uHex(length)) )
			lastName = regionName
		print( '                                                    Total: {:>10}'.format(uHex(total)) )
	else:
		print( 'No code regions could be found or determined.' ) # :O


def printDolInfo( dol ):
	
	""" Prints out information on a DOL. This function is 
		only used for the command-line feature, --checkDol """

	from basicFunctions import humansize, uHex

	if dol.region:
		print( 'Region:               ' + dol.region )
	else:
		print( 'Region:               Unknown       (use the --region argument when working with this DOL)' )

	if dol.version:
		print( 'Version:              ' + dol.version )
	else:
		print( 'Version:              Unknown       (use the --version argument when working with this DOL)' )

	print( 'BSS Memory Address:   ' + uHex(dol.bssMemAddress) )
	print( 'BSS Size:             ' + uHex(dol.bssSize) )
	print( 'Execution Entrypoint: ' + uHex(dol.entryPoint) )

	print( 'Detected as Melee:    ' + str(dol.isMelee) )

	if dol.project == -1:
		print( 'Project Designation:  N/A' )
		print( 'Project Version:      N/A' )
	elif dol.project == 0:
		print( 'Project Designation:  20XX HP' )
		print( 'Project Version:      {}.{}.{}'.format(dol.major, dol.minor, dol.patch) )

	totalTextSections = 0
	totalDataSections = 0
	totalData = 0
	headerAdded = False
	sectionLines = [ 'Text Sections:', '           File Offset:  RAM Address:  Section Size:' ]

	for sectionName, ( fileOffset, memAddress, size ) in dol.sectionInfo.items():
		if sectionName.startswith( 'text' ):
			totalTextSections += 1
		else:
			totalDataSections += 1
			if not headerAdded:
				# Add the total size for text sections
				sectionLines.append( '                                 Total: {:>10}'.format(uHex(totalData)) )
				totalData = 0

				# Prepare to start collecting for data sections
				sectionLines.append( 'Data Sections:' )
				sectionLines.append( '           File Offset:  RAM Address:  Section Size:' )
				headerAdded = True

		# Pad the name to 6 characters (align left), and pad all other values to 10 (align right)
		sectionLines.append( '    {:<6}  {:>10}    {:>10}    {:>10}'.format(sectionName, uHex(fileOffset), uHex(memAddress), uHex(size)) )
		totalData += size
	sectionLines.append( '                                 Total: {:>10}'.format(uHex(totalData)) )

	print( 'Size:                 {}  ({:,} bytes)'.format(humansize(dol.size), dol.size) )
	print( 'Total Text Sections:  ' + str(totalTextSections) )
	print( 'Total Data Sections:  ' + str(totalDataSections) )
	print( '-----------------------------------------------------' )

	for line in sectionLines:
		print( line )

	print( '-----------------------------------------------------' )
	print( 'Compatible Custom-Code Regions:' )
	for region in dol.customCodeRegions:
		print( region )


def installCodes( dol ):

	""" Installs code-based mods into a DOL file. """

	import shutil

	# Determine a code library path and validate it
	if args.library:
		libraryPath = args.library
		includePaths = [ os.path.join(libraryPath, '.include') ]
	else: # Use the program's default library
		libraryPath = os.path.join( globalData.scriptHomeFolder, 'Code Library' )
		includePaths = [ os.path.join(libraryPath, '.include'), os.path.join(globalData.scriptHomeFolder, '.include') ]
	if not os.path.exists( libraryPath ):
		print( 'Unable to find the given code library folder: "{}"'.format(libraryPath) )
		sys.exit( 3 )

	# Load the code library
	try:
		parser = CodeLibraryParser()
		parser.processDirectory( libraryPath, includePaths )
		assert parser.codeMods, 'no mods could be parsed.'
	except Exception as err:
		print( 'Unable to load the code library; {}'.format(err) )
		sys.exit( 202 )

	# Parse and normalize the mod names to install
	missingMods = []
	if len( args.install ) == 1 and args.install[0].upper() == 'ALL':
		modsToInstall = parser.codeMods
	else:
		modNames = parseInputList( args.install )

		# Collect the mods to install
		modsToInstall = []
		for mod in parser.codeMods:
			if mod.name in modNames:
				modsToInstall.append( mod )

		# Ensure we have a list of mods to install
		if not modsToInstall:
			print( 'Unable to find the given mods in the library.' )
			sys.exit( 203 )

		# Check for any missing mods
		if len( modsToInstall ) != len( modNames ):
			modsFound = [ mod.name for mod in modsToInstall ]
			for mod in modNames:
				if mod not in modsFound:
					missingMods.append( mod )

	# Check if we need custom code space for injection mods
	codeSpaceNeeded = False
	for mod in modsToInstall:
		if mod.type != 'static':
			codeSpaceNeeded = True
			break

	if codeSpaceNeeded:
		if not args.codeRegions:
			print( 'No custom code regions were defined to be used!' )
			print( 'These are required in this case in order to store custom code, '
					'and should be provided by the --codeRegions argument.' )
			sys.exit( 6 ) #todo: we don't need to fail here once codes.bin is hooked up

		# Set the code regions to use
		regionsAvailable = globalData.overwriteOptions.keys()
		regionsRequested = parseInputList( args.codeRegions )
		regionsFound = 0
		for regionName in regionsAvailable:
			if regionName in regionsRequested:
				globalData.overwriteOptions[regionName] = True
				regionsFound += 1
			else:
				globalData.overwriteOptions[regionName] = False

		# Check if we should continue (any regions were found)
		if regionsFound == 0:
			if len( regionsRequested ) == 1:
				print( 'The code region "{}" could not be found among the '
						'regions available for this DOL.'.format(regionsRequested[0]) )
			else:
				print( 'The requested code regions could not be found among the '
						'regions available for this DOL.' )
			sys.exit( 6 ) #todo: we don't need to fail here once codes.bin is hooked up

		# Check whether all requested regions were found
		elif regionsFound != len( regionsRequested ):
			print( "Warning: The following code regions couldn't be found:" )
			for region in regionsRequested:
				if region not in regionsAvailable:
					print( region )

	elif args.codeRegions:
		print( 'It appears that none of the codes you have listed for '
			   'installation require custom code space in the DOL for '
			   'overwrites. Therefore you do not need to provide custom '
			   'code regions to use for these mods (i.e. --codeRegions).' )

	# Load program settings (defaults or those set in settings.ini)
	globalData.loadProgramSettings()

	# Parse mod configurations, and set given values (#todo)

	# Set mod revisions and check for mod errors or conflicts
	for mod in modsToInstall:
		mod.setCurrentRevision( dol.revision )
		mod.diagnostics( 1, dol )
		
		# Disable mods with problems
		if mod.assemblyError or mod.parsingError:
			mod.state = 'unavailable'

		# Disable mods that are not applicable to the currently loaded DOL
		elif dol.revision not in mod.data:
			mod.state = 'unavailable'

	# Save codes to the DOL
	disc = dol.disc
	modsNotInstalled = disc.installCodeMods( modsToInstall )
	modInstallCount = len( modsToInstall ) - len( modsNotInstalled )

	# Check for and report any problems
	if modInstallCount == 0:
		print( 'None of the requested mods could be installed!' )
		sys.exit( 205 )

	# Save the disc or DOL file
	if disc.filePath:
		savePath = determineSavePath( disc )

		# Determine if we'll save the whole disc, or just export the DOL
		if savePath.lower().endswith( '.dol' ):
			# Save the dol to an external/standalone file (and codes.bin, if present)
			successful = disc.dol.export( savePath )

			if successful:
				print( 'DOL saved successfully' )
			else:
				print( 'Unable to export the DOL file' )
				sys.exit( 207 )

			# Attempt to save the codes.bin file if it's present
			codesFile = disc.getFile( 'codes.bin' )

			if codesFile:
				# Save the codes file
				saveDir = os.path.dirname( savePath )
				codesPath = os.path.join( saveDir, 'codes.bin' )
				successful = codesFile.export( codesPath )

				if successful:
					print( 'DOL and codes.bin files saved successfully' )
				else:
					print( 'DOL saved successfully; error saving codes.bin' )
					sys.exit( 207 )
		else:
			# Save the whole disc
			returnCode = disc.save( savePath )[0]

			if returnCode != 0: # Unable to save the disc!
				print( '\n' + translateDiscSaveError(returnCode, disc) )
				sys.exit( returnCode )

		outputDir = os.path.dirname( disc.filePath )

	else:
		# Saving a DOL file, not a disc.
		# Determine the output filepath.
		if args.outputFilePath:
			if os.path.isdir( args.outputFilePath ):
				# User didn't specify a filename; create one
				oldPath, ext = os.path.splitext( args.dolPath )
				savePath = oldPath + ' - NEW' + ext # .\folder\Start.dol -> .\folder\Start - NEW.dol
			else:
				savePath = args.outputFilePath
		else:
			savePath = args.dolPath

		# Write the file to an external/standalone file
		successful = disc.dol.export( savePath )

		if successful:
			print( 'DOL saved to "{}"'.format(savePath) )
		else: # Error already reported; just need to exit
			sys.exit( 207 )

		outputDir = os.path.dirname( savePath )

	if not outputDir: # May be empty if the save path was just a filename
		outputDir = os.getcwd()

	# Copy over the map file to the destination folder, if it was generated
	mapSaveDir = os.path.dirname( disc.mapSavePath )
	if mapSaveDir != outputDir and os.path.exists( disc.mapSavePath ):
		try:
			shutil.copy2( disc.mapSavePath, outputDir )
		except Exception as err:
			print( 'Unable to copy the map file; {}'.format(err) )

	# Save succeeded; assess code installation failures
	if modsNotInstalled:
		if modInstallCount == 1:
			print( '1 mod was successfully installed. However, the ' )
		else:
			print( '{} mods were successfully installed. However, the '.format(len(modInstallCount)) )
		print( 'following mods could not be installed:' )
		for mod in modsNotInstalled:
			print( mod.name )
		sys.exit( 206 )

	else:
		sys.exit( 0 )


def loadAssetTest():

	""" Function for command-line usage. Boots an instance of the game with the given asset. 
		Currently supported are stage and character files. """

	# Perform some quick and basic validation based on the file extension
	ext = os.path.splitext( args.boot )[1]
	validExtension = False
	if ext in ( '.png', '.jpg', '.jpeg', '.gif' ):
		print( 'This appears to be an image file! This feature expects a stage or character file.' )
	elif ext == '.dol':
		print( 'This appears to be a DOL file! This feature expects a stage or character file.' )
	elif ext in ( '.iso', '.gcm' ):
		print( 'This appears to be a disc image file! This feature expects a stage or character file.' )
	elif ext in ( '.hps', '.ssm', 'wav', 'dsp', 'mp3', 'aiff', 'wma', 'm4a' ):
		print( 'This appears to be an audio file! This feature expects a stage or character file.' )
	elif ext in ( '.mth', '.thp' ):
		print( 'This appears to be a video file! This feature expects a stage or character file.' )
	else:
		validExtension = True

	if not validExtension:
		sys.exit( 4 )

	# See if this is a stage file
	try:
		newFileObj = StageFile( None, -1, -1, '', extPath=args.boot, source='file' )
		newFileObj.validate()
	except:
		newFileObj = None

	if not newFileObj:
		# See if this is a character file
		try:
			newFileObj = CharCostumeFile( None, -1, -1, '', extPath=args.boot, source='file' )
			newFileObj.validate()
		except:
			newFileObj = None

	# Exit if unable to initialize the given file as one of the above classes
	if not newFileObj:
		print( 'Unable to initialize and validate the given file; it does not appear to be a stage or character file.' )
		sys.exit( 4 )

	# Get the micro melee disc object, and use it to test the given file
	globalData.loadProgramSettings()
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


def loadDisc( discPath ):

	""" Simple function to load/return a disc image for a given filepath. Only used by command-line features. 
		This will give an error message and exit the program if a problem is detected. """

	try:
		disc = Disc( discPath )
		returnCode = disc.load()
	except Exception as err:
		print( 'There was an unexpected error when attempting to load the disc; {}'.format(err) )
		sys.exit( 4 )

	if not disc.files:
		# A warning will have already been given if returnCode == 1 or 2
		if returnCode == 1: # File/folder path not found
			sys.exit( 3 )
		elif returnCode == 2: # Invalid file extension?
			print( 'You may want to check that you have the correct path (and extension) for a disc or root folder input.' )
		else: # No exception; but there are no files either!
			print( 'Unable to load the disc (empty or corrupt filesystem).' )
		sys.exit( 4 )

	return disc


def parseInputList( inputList, gameId='' ):

	""" Input list is expected to be a string; either a colon-separated list, 
		or a path to a file to open containing items. Returns a list of items. """

	# Check if it's a standalone text file containing items
	if len( inputList ) == 1 and inputList[0].lower().endswith( '.txt' ) and os.path.exists( inputList[0] ):
		with open( inputList[0], 'r' ) as listFile:
			paths = listFile.read().splitlines()
	else:
		paths = inputList

	# If this is to process ISO paths, restore the Game ID in the path (initially will likely be e.g. './PlSsNr.dat')
	if gameId:
		gameId += '/'
		fullPaths = []

		#paths = [ gameId + '/' + '/'.join( path.split('/')[1:] ) for path in paths ]
		for path in paths:
			path = path.replace( '\\', '/' )

			if not '/' in path:
				fullPaths.append( gameId + path )
			else:
				endPath = '/'.join( path.split('/')[1:] )
				fullPaths.append( gameId + endPath )

		paths = fullPaths

	# Ensure the list isn't empty
	if not paths:
		print( 'Invalid input; an input list appears to be empty.' )
		sys.exit( 2 )

	return paths


# Function & class definitions complete
if __name__ == '__main__':

	# Initialize the program globals and settings
	globalData.init( programArgs )

	# Parse command line arguments
	args = parseArguments()

	# Check for "disc" operation group
	if args.opsParser == 'disc':

		# Make sure required arguments are present
		if not args.discPath:
			print( 'No disc path or root folder path provided to operate on.' )
			print( """Please provide one via -d or --discPath""" )
			print( """For example, 'MMW.exe disc -d "C:\\folder\\game.iso"'""" )
			sys.exit( 2 )

		# Check for informational commands
		elif args.info or args.listFiles:
			disc = loadDisc( args.discPath )

			if args.info:
				print( disc.listInfo() )
			if args.listFiles:
				print( disc.listFiles() )

		elif args.export:
			disc = loadDisc( args.discPath )

			# Parse and normalize the isoPaths input
			isoPaths = parseInputList( args.export, disc.gameId )

			# Check for --output arg, or use CWD
			if args.outputFilePath:
				outputFolder = args.outputFilePath
			else:
				outputFolder = os.getcwd()

			# Export the files
			failedExports = disc.exportFiles( isoPaths, outputFolder )

			if failedExports:
				sys.exit( 6 )

		elif args._import:
			importFilesToDisc()
		
		# Build a disc from root (the --build parameter was given)
		elif args.rootFolderPath:
			buildDiscFromRoot()

		# Not enough args
		else:
			print( 'Insufficient command line aguments given. No operation pending.' )
			sys.exit( 2 )

	# Check for "test" operation group
	elif args.opsParser == 'test':
		if args.validate:
			validateAssets()
		elif args.boot:
			loadAssetTest()
		else:
			print( 'Insufficient command line aguments given; no validation or boot path(s).' )
			sys.exit( 2 )

	# Check for "code" operation group
	elif args.opsParser == 'code':

		# Get the target DOL file to operate on
		if args.discPath:
			disc = loadDisc( args.discPath )
			dol = disc.dol # Already initialized with disc load

		elif args.dolPath:
			# External/standalone DOL file provided. Initialize a new file object
			dol = Dol( None, -1, -1, '', '', args.dolPath, 'file' )

			# Initialize the DOL file (parse header to get regions, determine revision, and get custom code regions)
			try:
				dol.load()
			except Exception as err:
				print( 'Unable to load the DOL file; {}'.format(err) )
				sys.exit( 201 )

		elif args.checkCodeRegions:
			# Not performing any modifications on a DOL file, but we still need a DOL object for its methods
			dol = Dol( None, -1, -1, 'dol' )
			# Spoof checks/warnings for regions being outside of the DOL's codespace
			dol.maxDolOffset = float( "inf" )

		else:
			print( 'No disc path or DOL file provided to operate on.' )
			print( """Please provide one via -d or --discPath""" )
			print( """For example, 'MMW.exe disc -d "C:\\folder\\game.iso"'""" )
			sys.exit( 2 )

		# If a region and version were given, validate and apply them
		if args.region and args.version:
			applyExplicitRevision( dol )

		if args.checkCodeRegions:
			printRegionInfo( dol )

		elif args.checkDol:
			printDolInfo( dol )

		else:
			if not dol.disc:
				# Initialize an empty disc object (so we can tap into its code-saving methods)
				disc = Disc( '' )
				disc.gameId = 'GALE01'
				disc.files['GALE01/Start.dol'] = dol
				dol.disc = disc

			installCodes( dol )

	# If [non-h/-v] arguments are detected but no opGroup is specified, it's likely a disc filepath
	elif args.filePath:
	
		if os.path.exists( args.filePath ): # Ensure the given argument string is a filepath

			# Load the program settings and initialize the GUI (skipping the initial main/primary menu)
			globalData.gui = gui = MainGui( showPrimaryMenu=False )
			gui.audioEngine = AudioEngine()

			# Temporarily disable animations on the main menu for initial program loading
			animsDisabled = globalData.checkSetting( 'disableMainMenuAnimations' )
			if not animsDisabled:
				globalData.setSetting( 'disableMainMenuAnimations', True )

			# Process any file provided on start-up (drag-and-dropped onto the program's .exe file, or provided via command line)
			gui.fileHandler( [args.filePath] )

			# Reenable main menu animations now that program initialization is done
			if not animsDisabled:
				globalData.setSetting( 'disableMainMenuAnimations', False )
				globalData.saveProgramSettings()

			# Start the GUI's mainloop (blocks until the GUI is taken down by .destroy or .quit)
			gui.root.mainloop()

		else: # Bad input (probably not even a filepath)
			print( 'Unrecognized command-line arguments; no operation group or valid filepath was provided.' )
			print( '' )
			print( 'Use "{}" --help (or -h) to see usage instructions.'.format(sys.argv[0]) )
			sys.exit( 1 )

	# No option group or other command line arguments detected; start the GUI
	else:
		# Load the program settings and initialize the GUI
		globalData.gui = gui = MainGui()
		gui.audioEngine = AudioEngine()

		# For testing...
		# print('gui load time: ' + str(time.clock()-toc))
		# print('program load time: ' + str(time.clock()-tic))
		# gui.fileHandler( [r"D:\Tex\SSBM ISO\vanilla test iso\Super Smash Bros. Melee (v1.02).iso"] )
		# gui.fileMenu.browseCodeLibrary()
		# gui.loadStageEditor()
		# gui.loadDiscManagement()
		# gui.discTab.scrollToSection( 'GALE01/PlClNr.dat' )

		# Start the GUI's mainloop (blocks until the GUI is taken down by .destroy or .quit)
		gui.root.mainloop()


# Program exit codes:
#
#	0: All operations completed successfully
#	1: A problem occurred in parsing command line arguments
#	2: Invalid or incomplete combination of input arguments
#	3: Invalid input path given (file/folder not found)
#	4: Unable to initialize the given input file or root folder
#	5: Unable to initialize Micro Melee disc image
#	6: One or more operations failed to complete
#
#	[Exception to this is the --validate command; exit code is based on pass/fail of individual files.]
#
# 100 series codes 		(disc save failure; from disc.save, disc.saveFilesToDisc, or disc.buildNewDisc):
#	101: No changes to be saved
#	102: Missing system files
#	103: Unable to create a new disc file
#	104: Unable to open the original disc
#	105: Unrecognized error during file writing
#	106: Unable to overwrite existing file
#	107: Could not rename discs or remove original
#
# 200 series codes		(for code-based mod operations)
#	201: Unable to load the DOL (disc loaded successfully)
#	202: Unable to load the code library
#	203: Unable to find the given mods in the library
#	204: Conflicts detected among the requested mods
# 	205: None of the requested mods could not be installed
# 	206: Some of the requested mods could not be installed
# 	207: Unable to save the finished DOL or codes.bin file