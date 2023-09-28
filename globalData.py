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

""" Container for global data that all program files or modules may access. 
	Contains settings, settings-related load/save functions, and look-up tables. """

programVersion = '0.9.8'

# External Dependencies
import os
import csv
import time
#import enum
import ConfigParser
import tkMessageBox
import Tkinter as Tk

from datetime import datetime
from collections import OrderedDict

# Internal Dependencies
import FileSystem
import codeRegionSettings

from FileSystem.dol import Dol
from FileSystem.disc import Disc, MicroMelee, isExtractedDirectory
from codeMods import CommandProcessor
from basicFunctions import msg, printStatus
from guiSubComponents import PopupEntryWindow, VanillaDiscEntry
from tools import DolphinController

resamplingFilters = { 
	'nearest': 0, 
	'lanczos': 1, 
	'bilinear': 2, 
	'bicubic': 3, 
	'box': 4,
	'hamming': 5
}


def init( programArgs ):

	""" If any check on settings will be required, call 'globalData.loadProgramSettings()' first to fully initialize them. """

	global scriptHomeFolder, paths, defaultSettings, defaultBoolSettings, settings, boolSettings, overwriteOptions
	global codeProcessor, dolphinController, gui, disc, dol, codeMods, standaloneFunctions, fileStructureClasses

	scriptHomeFolder = os.path.abspath( os.path.dirname(programArgs[0]) ) # Can't use __file__; incompatible with cx_freeze process

	# Internal paths (these typically don't change), and will not appear in the settings.ini file
	# Custom/user paths that should be remembered in the settings file should be in the other two settings dicts
	paths = {
		# Root paths
		'fontsFolder': os.path.join( scriptHomeFolder, 'fonts' ),
		'imagesFolder': os.path.join( scriptHomeFolder, 'imgs' ),
		'audioFolder': os.path.join( scriptHomeFolder, 'sfx' ),
		'settingsFile': os.path.join( scriptHomeFolder, 'settings.ini' ),
		
		# Bin (binary) paths
		'tempFolder': os.path.join( scriptHomeFolder, 'bin', 'tempFiles' ),
		'meleeMedia': os.path.join( scriptHomeFolder, 'bin', 'MeleeMedia', 'MeleeMedia.exe' ),
		'triCsps': os.path.join( scriptHomeFolder, 'bin', 'Tri-CSP Creation' ),
		'microMelee': os.path.join( scriptHomeFolder, 'bin', 'Micro Melee.iso' ),
		'eabi': os.path.join( scriptHomeFolder, 'bin', 'eabi' ),
		'coreCodes': os.path.join( scriptHomeFolder, 'bin', 'Core Codes' ),
		'xDelta': os.path.join( scriptHomeFolder, 'bin', 'xdelta3-3.0.11-x86_64.exe' ), # todo: make this dynamic
		'maps': os.path.join( scriptHomeFolder, 'bin', 'maps' ),
		'charDataTranslations': os.path.join( scriptHomeFolder, 'bin', 'CharDataTranslations.json' ),
		'codehandler': os.path.join( scriptHomeFolder, 'bin', 'codehandler.bin' ),
	}

	# These are default settings to be used when they are not defined in the user's settings.ini file
	defaultSettings = {
		'codeLibraryPath': os.path.join( scriptHomeFolder, 'Code Library' ),
		'codeLibraryIndex': '0',
		'vanillaDiscPath': '',
		'hexEditorPath': '',
		'emulatorPath': '',
		'maxFilesToRemember': '7',
		'paddingBetweenFiles': '0x40',
		'dolSource': 'vanilla',
		'offsetView': 'ramAddress', # Alternate acceptable value=dolOffset (not case sensitive or affected by spaces)
		'volume': '.7',
		'textureExportFormat': 'png', 
		'resampleFilter': 'lanczos'
	}
	defaultBoolSettings = { # Same as above, but for bools, which are initialized slightly differently (must be strings of 0 or 1!)
		'useDiscConvenienceFolders': '1',
		'useConvenienceFoldersOnExport': '0',
		'backupOnRebuild': '1',
		'alwaysAddFilesAlphabetically': '0',
		'exportDescriptionsInFilename': '1', # Music files only ATM (hps & wav)
		'runDolphinInDebugMode': '0',
		'createHiResCSPs': '0',
		'disableMainMenuAnimations': '0',

		# Code related
		'alwaysEnableCrashReports': '1',
		'useCodeCache': '1',
		'offerToConvertGeckoCodes': '1',

		# Filters used on the Moves Editor's Action States list
		'actionStateFilterAttacks': '1',
		'actionStateFilterMovement': '0',
		'actionStateFilterItems': '0',
		'actionStateFilterCharSpecific': '1',
		'actionStateFilterEmpty': '0',

		# Texture editing interface
		'showCanvasGrid': '1',
		'showTextureBoundary': '0',
		'useDolphinNaming': '0',
		'obscureNonSelected': '1',
	}

	settings = ConfigParser.SafeConfigParser()
	settings.optionxform = str # Tells the settings parser to preserve case sensitivity
	boolSettings = {}
	overwriteOptions = OrderedDict() # For code-based mods. Populates with key=customCodeRegionName, value=BooleanVar (to describe whether the regions should be used.)
	
	codeProcessor = CommandProcessor() # Must be initialized after gettings general settings, so the base include paths are set correctly
	dolphinController = DolphinController()

	gui = None
	disc = None
	dol = None # A vanilla DOL not associated with a disc

	codeMods = []
	standaloneFunctions = {} # Key='functionName', value=( functionRamAddress, codeChangeObj )
	
	# All internal file structure classes should be registered in this dictionary
	fileStructureClasses = {}
	FileSystem.registerStructureClasses()


def getUniqueWindow( windowTitle, topLevelWindow=None ):

	""" Used to get an instance of a "unique" window, meant to be persistent or reused. 
		These are created by the BasicWindow class when 'unique' is True. 
		This will also make sure the window is not minimized and bring it to the foreground
		if it's found. If that fails, this returns None and erases that windowTitle entry. """

	if not topLevelWindow:
		topLevelWindow = gui.root
	
	# Bring into view an existing instance of this window, if already present
	if hasattr( topLevelWindow, 'uniqueWindows' ):
		existingWindow = topLevelWindow.uniqueWindows.get( windowTitle )

		if existingWindow:
			try:
				# The window already exist. Make sure it's not minimized, and bring it to the foreground
				existingWindow.window.deiconify()
				existingWindow.window.lift()
				return existingWindow
			except: # Failsafe against bad window name (existing window somehow destroyed without proper clean-up); move on to create new instance
				topLevelWindow.uniqueWindows[windowTitle] = None
				return None


def loadProgramSettings( useBooleanVars=False ):

	""" Check for user defined settings / persistent memory, from the "settings.ini" file. 
		If values don't exist in it for particular settings, defaults are loaded from the global 'defaultSettings' dictionary. 
		This is preferred over having a default file already created to contain the settings so that the file may be deleted, 
		either to reset all defaults, or re-create the file in case of potential corruption. 
		Usage of BooleanVars can only be done in the presence of the GUI. """

	# Read the file if it exists
	if os.path.exists( paths['settingsFile'] ):
		settings.read( paths['settingsFile'] )

	# Add the 'General Settings' section if it's not already present
	if not settings.has_section( 'General Settings' ):
		settings.add_section( 'General Settings' )

	# Add the 'Default Search Directories' section if it's not already present
	if not settings.has_section( 'Default Search Directories' ):
		settings.add_section( 'Default Search Directories' )
		settings.set( 'Default Search Directories', 'default', os.path.expanduser('~') )
		settings.set( 'Default Search Directories', 'lastCategory', 'default' )

	# Set default [hardcoded] settings only if their values don't exist in the settings file
	for settingName, initialDefault in defaultSettings.items():
		if not settings.has_option( 'General Settings', settingName ):
			settings.set( 'General Settings', settingName, initialDefault )

	# Booleans are handled a little differently, so that they may easily be kept in sync with the GUI (when booleanVars are used)
	for settingName in defaultBoolSettings:
		if not settings.has_option( 'General Settings', settingName ):
			settings.set( 'General Settings', settingName, defaultBoolSettings[settingName] )

		if useBooleanVars:
			if settingName not in boolSettings:
				boolSettings[settingName] = Tk.BooleanVar() # Should only occur on initial program start

			# These are a special set of control variables, BooleanVars(), which must be created separately/anew from the settings in the configParser settings object
			boolSettings[settingName].set( settings.getboolean('General Settings', settingName) )
		else:
			# Set the value to a normal True/False bool
			boolSettings[settingName] = settings.getboolean( 'General Settings', settingName )


def loadRegionOverwriteOptions( useBooleanVars=False ):

	""" Checks saved options (the settings.ini file) for whether or not custom code regions are selected for use 
		(i.e. can be overwritten). This is called from the dol class when a DOL file is loaded. Creates new BooleanVars 
		only on first run, which should exist for the life of the program (they will only be updated after that). """

	# Check for options file / persistent memory.
	if not settings.has_section( 'Region Overwrite Settings' ):
		settings.add_section( 'Region Overwrite Settings' )

	processed = [] # Used to skip regions after it has been been checked for the first game revision

	# Create BooleanVars for each defined region. These will be used to track option changes
	for fullRegionName in codeRegionSettings.customCodeRegions.keys():
		regionName = fullRegionName.split( '|' )[1]
		if regionName in processed: continue

		# If the options file contains an option for this region, use it.
		if settings.has_option( 'Region Overwrite Settings', regionName ):
			regionEnabled = settings.getboolean( 'Region Overwrite Settings', regionName )
		elif regionName in ( 'Common Code Regions', 'Tournament Mode Region', 'Screenshot Regions' ):
			regionEnabled = True
		else: # Otherwise, by default, don't enable this region
			regionEnabled = False

		if useBooleanVars:
			if regionName not in overwriteOptions: # This function may have already been called (s)
				overwriteOptions[ regionName ] = Tk.BooleanVar()
			overwriteOptions[ regionName ].set( regionEnabled )
		else:
			overwriteOptions[ regionName ] = regionEnabled
		processed.append( regionName )


def checkSetting( settingName ):

	""" Used for checking general settings and bools. """

	# Make sure there are no naming conflicts
	if settingName in defaultSettings and settingName in defaultBoolSettings:
		raise Exception( 'Setting {} defined as both a regular setting and bool setting!'.format(settingName) )

	elif settingName in defaultSettings: # Not a bool or region overwrite setting
		settingValue = settings.get( 'General Settings', settingName )

		if settingName == 'resampleFilter':
			# Validate it
			if settingValue.lower() not in resamplingFilters:
				defaultValue = defaultSettings['resampleFilter']
				printStatus( 'Warning, {} is not a valid resampling filter! Defaulting to "{}"'.format(settingValue, defaultValue), warning=True )
				return 1
			else:
				settingValue = resamplingFilters[settingValue]

		return settingValue

	# Must be a bool or BooleanVar; check for it in the bools dict
	boolSetting = boolSettings.get( settingName, 'notFound' )
	if boolSetting == 'notFound':
		raise Exception( 'Setting name not found (may be misspelled): ' + settingName )

	elif isinstance( boolSetting, Tk.BooleanVar ):
		return boolSetting.get()
	else:
		return boolSetting


def setSetting( settingName, value ):

	""" Used for setting general settings and bools to the given value. 
		Does not include overwriteOptions, for custom code regions. """

	# Make sure there are no naming conflicts
	if settingName in defaultSettings and settingName in defaultBoolSettings:
		raise Exception( 'Setting {} defined as both a regular setting and bool setting!'.format(settingName) )

	elif settingName in defaultSettings: # Not a bool or region overwrite setting
		settings.set( 'General Settings', settingName, value )
		return

	# Must be a bool or BooleanVar; check for it in the bools dict
	boolSetting = boolSettings.get( settingName, 'notFound' )
	if boolSetting == 'notFound':
		raise Exception( 'Setting name not found (may be misspelled): ' + settingName )

	# Validate the input; should be a bool
	elif value != True and value != False:
		raise Exception( 'Invalid value given to bool setting, "{}": {}'.format(settingName, value) )

	# Set the value
	elif isinstance( boolSetting, Tk.BooleanVar ):
		boolSetting.set( value )
	else:
		boolSettings[settingName] = value


def checkRegionOverwrite( regionName ):

	""" Used specifically for checking region overwrite options. """

	# Must be a bool or BooleanVar; check for it in the bools dict
	boolSetting = overwriteOptions.get( regionName, 'notFound' )
	if boolSetting == 'notFound':
		print( 'Unable to find region in region overwrite options:', regionName )
		return False

	elif isinstance( boolSetting, Tk.BooleanVar ):
		return boolSetting.get()
	else:
		return boolSetting


def saveProgramSettings():

	""" Saves the current program settings to the "settings.ini" file. This will update a pre-existing 
		settings file, or will create a new one if it doesn't already exist. 

		String and alphanumeric settings are kept in the global settings object, while booleans 
		are kept in the boolSettings dictionary as BooleanVar objects, so that they can easily be 
		kept in sync with the GUI. Therefore they need to be synced with the settings object before saving. """

	if gui:
		# Convert the program's BooleanVars to strings and update them in the settings object
		for setting in defaultBoolSettings:
			settings.set( 'General Settings', setting, str( boolSettings[setting].get() ) )

		saveRegionOverwriteSettings()
		
	else: # The bool settings should be regular python bools
		for setting in defaultBoolSettings:
			settings.set( 'General Settings', setting, str( boolSettings[setting] ) )

	with open( paths['settingsFile'], 'w' ) as theOptionsFile:
		settings.write( theOptionsFile )


def saveRegionOverwriteSettings():
	
	""" Syncs the overwriteOptions (bools for whether or not each custom code region should be used) to 
		the "settings" object, and then saves these settings to file, i.e. the options.ini file. 
		Only expected to be used with the GUI, so only BooleanVars are expected. """

	if not settings.has_section( 'Region Overwrite Settings' ):
		settings.add_section( 'Region Overwrite Settings' )

	# Update settings with the currently selected checkbox variables.
	for regionName, boolVar in overwriteOptions.items():
		settings.set( 'Region Overwrite Settings', regionName, str(boolVar.get()) )

	# Save the above, and all other options currently saved to the settings object, to the options file
	#saveProgramSettings()


def getRecentFilesLists():
	
	""" Returns two lists of tuples (ISOs & DATs), where each tuple is a ( filepath, dateTimeObject ). """

	#settings = globalData.settings
	ISOs = []
	DATs = []
	
	if not settings.has_section( 'Recent Files'):
		return [], []

	for filepath in settings.options( 'Recent Files' ):
		try:
			# Create a datetime object, which can later be used to sort the lists
			newDatetimeObject = datetime.strptime( settings.get('Recent Files', filepath), "%Y-%m-%d %H:%M:%S.%f" )
			optionTuple = ( filepath, newDatetimeObject ) # Tuple of ( normalizedPath, dateTimeObject )

			# Add the file to the list for discs or dats
			ext = os.path.splitext( filepath )[1].lower()
			if ext == '.iso' or ext == '.gcm' or isExtractedDirectory( filepath.replace('|', ':'), showError=False ): 
				ISOs.append( optionTuple )
			else: DATs.append( optionTuple )
		except:
			# Error encountered; ask to remove the faulty file entry from the settings file
			removeEntry = tkMessageBox.askyesno( 'Error Parsing Settings File', 'The timestamp for one of the recently '
												 'opened files, "' + filepath.replace('|', ':') + '", could not be read. '
												 'The settings file, or just this entry within it, seems to be corrupted.'
												 '\n\nDo you want to remove this item from the list of recently opened files?' )
			if removeEntry: 
				settings.remove_option( 'Recent Files', filepath )

	return ISOs, DATs


def setLastUsedDir( savePath, category='default', fileExt='', saveSettings=True ):
	
	""" Normalizes the given path (and converts to a folder path if a file path was given) 
		and sets it as the default program directory. This can be used on a per-file-type 
		basis; for example, a last used dir for discs, or a last used dir for music files. """

	# Get the folder path if this is a path to a file
	if not os.path.isdir( savePath ):
		# Try to determine the category by the file extension
		if category == 'auto' and not fileExt:
			fileExt = os.path.splitext( savePath )[1].replace( '.', '' )

		savePath = os.path.dirname( savePath )
	
	if fileExt:
		if fileExt in ( 'hps', 'wav', 'dsp', 'mp3', 'aiff', 'wma', 'm4a' ): # Audio files
			category = 'hps'
		elif fileExt in ( 'iso', 'gcm' ): # Discs
			category = 'iso'
		elif fileExt.endswith( 'at' ) or fileExt.endswith( 'sd' ): # To match .dat/.usd as well as .0sd/.1at etc. variants
			category = 'dat'
		elif fileExt in ( 'mth', 'thp' ): # Video files
			category = 'mth'
		elif fileExt == 'dol':
			category = 'dol'
		elif fileExt in ( 'png', 'tpl' ): # Textures
			category = 'png'
		else:
			category = 'default'

	# Unable to determine a category without a file extension; use the default
	elif category == 'auto':
		category = 'default'

	# Normalize the path and make sure it's composed of legal characters
	savePath = os.path.normpath( savePath ).encode( 'utf-8' ).strip()

	# Save a default directory location for this specific kind of file
	category = category.replace( '.', '' ).lower()
	settings.set( 'Default Search Directories', category, savePath )
	settings.set( 'Default Search Directories', 'lastCategory', category )

	if saveSettings: # Should be avoided in some cases where it's redundant
		saveProgramSettings()


def getLastUsedDir( category='default', fileExt='' ):

	""" Fetches the default directory to start in for file/folder operations. 
		Can use the "category" argument to retrieve for a specific type or 
		class of files; e.g. for "dat" or "disc". """

	# If no category is specified, use the last saved directory out of all of them
	if category == 'default':
		category = settings.get( 'Default Search Directories', 'lastCategory' )

	if fileExt:
		if fileExt in ( 'hps', 'wav', 'dsp', 'mp3', 'aiff', 'wma', 'm4a' ): # Audio files
			category = 'hps'
		elif fileExt in ( 'iso', 'gcm' ): # Discs
			category = 'iso'
		elif fileExt.endswith( 'at' ) or fileExt.endswith( 'sd' ): # To match .dat/.usd as well as .0sd/.1at etc. variants
			category = 'dat'
		elif fileExt in ( 'mth', 'thp' ): # Video files
			category = 'mth'
		elif fileExt == 'dol':
			category = 'dol'
		else:
			category = 'default'
			
	# Unable to determine a category without a file extension; use the default
	elif category == 'auto':
		category = 'default'

	# Get a default directory location for this specific type of file
	try:
		directoryPath = settings.get( 'Default Search Directories', category.replace( '.', '' ).lower() )

		# For PNG directories, we can start off by assuming this texture will be saved with its dat
		if not directoryPath and category == 'png':
			directoryPath = settings.get( 'Default Search Directories', 'dat' )

	except ConfigParser.NoOptionError:
		if category == 'codeLibrary':
			directoryPath = getModsFolderPath()
		else:
			directoryPath = settings.get( 'Default Search Directories', 'default' )

	return os.path.normpath( directoryPath )


def rememberFile( filepath, updateDefaultDirectory=True ):

	""" Adds a filepath to the settings object's "Recent Files" section, so it can be recalled later 
		from the 'Open Recent' menu option (removing the oldest file if the max files to remember has 
		been reached). The settings are then saved to the settings file. """

	 # Normalize input (collapse redundant separators, and ensure consistent slash direction)
	filepath = os.path.normpath( filepath )
	extension = os.path.splitext( filepath )[1].lower()

	# Remove the oldest file entry if the max number of files to remember has already been reached
	if settings.has_section( 'Recent Files' ):
		# Get the current lists of recent ISOs and recent DAT (or other) files
		ISOs, DATs = getRecentFilesLists()

		# For the current filetype, arrange the list so that the oldest file is first, and then remove it from the settings file.
		if extension == '.iso' or extension == '.gcm' or isExtractedDirectory( filepath, showError=False ): targetList = ISOs
		else: targetList = DATs
		targetList.sort( key=lambda recentInfo: recentInfo[1] )

		# Remove the oldest file(s) from the settings file until the specified max number of files to remember is reached.
		while len( targetList ) > int( settings.get( 'General Settings', 'maxFilesToRemember' ) ) - 1:
			settings.remove_option( 'Recent Files', targetList[0][0] )
			targetList.pop( 0 )
	else:
		settings.add_section( 'Recent Files' )

	# Update the default search directory.
	if updateDefaultDirectory:
		if extension == '.iso' or extension == '.gcm':
			setLastUsedDir( filepath, 'iso', saveSettings=False )
		else:
			setLastUsedDir( filepath, 'dat', saveSettings=False )

	# Save this filepath with a timestamp
	timeStamp = str( datetime.today() )
	settings.set( 'Recent Files', filepath.replace(':', '|'), timeStamp ) # Colon is replaced because it confuses the settings parser.

	saveProgramSettings()


def getHexEditorPath():

	""" Only expected to be used with the GUI, and after globalData.init(). Checks for a specified hex editor 
		to open files in from the user settings, and prompts the user to enter one if a good path is not found. 
		Can't be contained in main because it's needed in guiDisc (which can't import from main). """

	hexEditorPath = settings.get( 'General Settings', 'hexEditorPath' )

	if not os.path.exists( hexEditorPath ):
		message = ( 'Please specify the full path to your hex editor. This path only needs to be given once, '
					'and can be changed at any time in the settings.ini file. If you have already set this, '
					"the path seems to have broken."
					"\n\nNote that this feature only shows you a copy of the data; any changes made will not be saved to the file or disc."
					'\n\nPro-tip: In Windows, if you hold Shift while right-clicking on a file, there appears a context menu '
					"""option called "Copy as path". This will copy the file's full path into your clipboard. Or if it's a shortcut, """
					"""you can quickly get the full file path by right-clicking on the icon and going to Properties.""" )

		popupWindow = PopupEntryWindow( gui.root, message=message, title='Set Hex Editor Path', validatePath=True )
		hexEditorPath = popupWindow.entryText.replace( '"', '' )

		if hexEditorPath != '': # A path was given (user didn't hit 'Cancel')
			# Update the path in the global variable and the settings file
			settings.set( 'General Settings', 'hexEditorPath', hexEditorPath )
			saveProgramSettings()

	return hexEditorPath


def getEmulatorPath():

	""" Only expected to be used with the GUI, and after globalData.init(). Checks for a specified emulator 
		to open files in from the user settings, and prompts the user to enter one if a good path is not found. """

	emulatorPath = settings.get( 'General Settings', 'emulatorPath' )

	if not os.path.exists( emulatorPath ) and gui: # todo: could have command-line input for this as well
		message = ( 'Please specify the full path to your emulator. This path only needs to be given once, '
					'and can be changed at any time in the settings.ini file. If you have already set this, '
					"the path seems to have broken."
					'\n\nPro-tip: In Windows, if you hold Shift while right-clicking on a file, there appears a context menu '
					"""option called "Copy as path". This will copy the file's full path into your clipboard. Or if it's a shortcut, """
					"""you can quickly get the full file path by right-clicking on the icon and going to Properties.""" )

		popupWindow = PopupEntryWindow( gui.root, message=message, title='Set Emulator Path', validatePath=True )
		emulatorPath = popupWindow.entryText.replace( '"', '' )

		if emulatorPath != '': # A path was given (user didn't hit 'Cancel')
			# Update the path in the settings file and global variable.
			settings.set( 'General Settings', 'emulatorPath', emulatorPath )
			saveProgramSettings()

	return emulatorPath


def getVanillaDiscPath():

	""" Only expected to be used after globalData.init(). Checks for a specified vanilla disc 
		file from the user settings, and prompts the user to enter one if a good path is not found. 
		Can't be contained in main because it's needed in other files (which can't import from main). """

	vanillaDiscPath = settings.get( 'General Settings', 'vanillaDiscPath' )

	if not vanillaDiscPath:
		message = ( 'Please specify the full path to a vanilla NTSC 1.02 SSBM game disc. This path only '
					'needs to be given once, and can be changed at any time in the settings.ini file. '
					"If you have already set this, the path seems to have broken." )
	elif not os.path.exists( vanillaDiscPath ):
		message = ( 'The path provided for a vanilla reference disc seems to be broken.'
					'\nPlease specify a new full path to a vanilla NTSC 1.02 SSBM game disc.' )
	else:
		message = ''

	if message:
		message += (
			'\n\nPro-tip: In Windows, if you hold Shift while right-clicking on a file, there appears a context menu '
			"""option called "Copy as path". This will copy the file's full path into your clipboard. Or if it's a shortcut, """
			"""you can quickly get the full file path by right-clicking on the icon and going to Properties.""" )

		if gui:
			popupWindow = VanillaDiscEntry( gui.root, message=message, title='Set Vanilla Disc Path' )
			vanillaDiscPath = popupWindow.entryText.replace( '"', '' )
		else:
			vanillaDiscPath = input( message )

		if vanillaDiscPath: # A path was given (user didn't hit 'Cancel')
			# Update the path in the settings file and global variable.
			settings.set( 'General Settings', 'vanillaDiscPath', vanillaDiscPath )
			saveProgramSettings()

	return vanillaDiscPath


def getVanillaDol( skipCache=False ):

	""" Retrieves and returns the Start.dol file from a vanilla disc. 
		Or, if a path is given for the 'dolSource' setting, that DOL is used. 
		May raise an exception if a DOL cannot be retrieved. """

	# Check for a cached copy to use
	global dol
	if dol and not skipCache:
		return dol
	
	dolPath = settings.get( 'General Settings', 'dolSource' )

	if dolPath == 'vanilla':
		# See if we can get a reference to vanilla DOL code from a disc
		vanillaDiscPath = getVanillaDiscPath()
		if not vanillaDiscPath: # User canceled path input
			raise Exception( 'no vanilla disc available for reference' )
		
		vanillaDisc = Disc( vanillaDiscPath )
		vanillaDisc.load() # This will also load/initialize the DOL
		dol = vanillaDisc.dol
		if not dol:
			raise Exception( 'unable to load DOL from vanilla disc')

		# No need for disc association anymore
		dol.disc = None
		dol.source = 'self'

	elif not os.path.exists( dolPath ):
		raise Exception( 'the source DOL could not be found' )

	else:
		# Initialize and return an external DOL file
		dol = Dol( None, -1, -1, '', 'Main game executable', dolPath, 'file' )
		dol.load()

	dol.readOnly = True # Triggers an assertion if an attempt is made to edit this file

	return dol


def getMicroMelee():

	""" Returns a Micro Melee disc object. Either from a pre-built file, 
		or if needed, creates a new one from a vanilla disc. """

	microMeleePath = paths['microMelee']

	# Check if a Micro Melee disc already exists
	if os.path.exists( microMeleePath ):
		microMelee = MicroMelee( microMeleePath )
		microMelee.loadGameCubeMediaFile()

	else: # Need to make a new MM build
		vanillaDiscPath = getVanillaDiscPath()
		if not vanillaDiscPath: # User canceled path input
			printStatus( 'Unable to build the Micro Melee test disc without a vanilla reference disc.' )
			return

		microMelee = MicroMelee( microMeleePath )
		microMelee.buildFromVanilla( vanillaDiscPath )

	return microMelee


def getModsFolderPath( getAll=False ):

	""" Gets the current code mods library path, as determined by the settings file. 
		The codeLibraryPath may be a comma-separated list of paths. If that's the case, the 
		current path, i.e. most recently used, is determined by the library index setting. """

	pathsString = settings.get( 'General Settings', 'codeLibraryPath' )
	pathsList = csv.reader( [pathsString] ).next()

	if getAll:
		return pathsList
		
	pathIndex = int( settings.get('General Settings', 'codeLibraryIndex') )

	if pathIndex < 0 or pathIndex >= len( pathsList ):
		msg( 'Invalid code library path index: ' + str(pathIndex) )
		return pathsList[0]

	return pathsList[pathIndex]


charNameLookup = {
	'Bo': '[Boy] Male Wireframe',
	'Ca': 'Captain Falcon',
	'Ch': 'Crazy Hand',
	'Cl': 'Child/Young Link',
	'Co': 'Common to the cast',
	'Dd': 'Diddy Kong',
	'Dk': 'Donkey Kong',
	'Dr': 'Dr. Mario',
	'Fc': 'Falco',
	'Fe': '[Fire Emblem] Roy',
	'Fx': 'Fox',
	'Gk': '[GigaKoopa] GigaBowser',
	'Gl': '[Girl] Female Wireframe',
	'Gn': 'Ganondorf',
	'Gw': "Game 'n Watch",
	'Ic': 'Ice Climbers',
	'Kb': 'Kirby',
	'Kp': '[Koopa] Bowser',
	'Lg': 'Luigi',
	'Lk': 'Link',
	'Lz': 'Charizard',
	'Mh': 'Master Hand',
	'Mn': 'Menus Data',
	'Mr': 'Mario',
	'Ms': '[Mars] Marth',
	'Mt': 'Mewtwo',
	'Nn': '[Nana] Ice Climbers',
	'Ns': 'Ness',
	'Pc': 'Pichu',
	'Pe': 'Peach',
	'Pk': 'Pikachu',
	'Pn': '[Popo/Nana] Ice Climbers',
	'Pp': '[Popo] Ice Climbers',
	'Pr': '[Purin] Jigglypuff',
	'Sb': 'SandBag',
	'Sk': 'Sheik',
	'Ss': 'Samus',
	'Wf': 'Wolf',
	'Ys': 'Yoshi',
	'Zd': 'Zelda'
}


universeNames = {
	'Bo': 'SSB',
	'Ca': 'F-Zero',
	'Ch': 'SSB',
	'Cl': 'The Legend of Zelda',
	'Co': 'SSB',
	'Dk': 'Donkey Kong',
	'Dr': 'Mario',
	'Fc': 'Star Fox',
	'Fe': 'Fire Emblem',
	'Fx': 'Star Fox',
	'Gk': 'SSB',
	'Gl': 'SSB',
	'Gn': 'The Legend of Zelda',
	'Gw': 'Game & Watch',
	'Kb': 'Kirby',
	'Kp': 'Mario',
	'Lg': 'Mario',
	'Lk': 'The Legend of Zelda',
	'Mh': 'SSB',
	'Mr': 'Mario',
	'Ms': 'Fire Emblem',
	'Mt': 'Pokemon',
	'Nn': 'Ice Climber',
	'Ns': 'EarthBound',
	'Pc': 'Pokemon',
	'Pe': 'Mario',
	'Pk': 'Pokemon',
	'Pn': 'Ice Climber',
	'Pp': 'Ice Climber',
	'Pr': 'Pokemon',
	'Sb': 'SSB',
	'Sk': 'The Legend of Zelda',
	'Ss': 'Metroid',
	'Wf': 'Star Fox',
	'Ys': 'Yoshi',
	'Zd': 'The Legend of Zelda',
}


# intCharIds = {
# 	0: 'Mr', # Mario
# 	1: 'Fx', # Fox
# 	2: 'Ca', # C. Falcon
# 	3: 'Dk', # DK
# 	4: 'Kb', # Kirby
# 	5: 'Kp', # Bowser
# }


# class IntCharId( enum.IntEnum ): # Internal Character ID
# 	Mario = 0
# 	Fox = 1
# 	Falcon = 2


charList = [ # Indexed by External Character ID
	"Captain Falcon",	# 0x0
	"DK",
	"Fox",
	"Game & Watch",
	"Kirby",
	"Bowser",
	"Link",
	"Luigi",
	"Mario",			# 0x8
	"Marth",
	"Mewtwo",
	"Ness",
	"Peach",
	"Pikachu",
	"Ice Climbers",
	"Jigglypuff",
	"Samus",			# 0x10
	"Yoshi",
	"Zelda",
	"Sheik",
	"Falco",
	"Young Link",
	"Doc",
	"Roy",
	"Pichu",			# 0x18
	"Ganondorf",
	"Master Hand",
	"Male Wireframe",
	"Female Wireframe",
	"Giga Bowser",
	"Crazy Hand",
	"Sandbag",
	"Solo Popo"			# 0x20
]


charAbbrList = [ # Indexed by External Character ID
	'Ca',	# 0x0
	'Dk',
	'Fx',
	'Gw',
	'Kb',
	'Kp',
	'Lk',
	'Lg',
	'Mr',	# 0x8
	'Ms',
	'Mt',
	'Ns',
	'Pe',
	'Pk',
	'Pp',	# Both ICies
	'Pr',
	'Ss',	# 0x10
	'Ys',
	'Zd',
	'Sk',
	'Fc',
	'Cl',
	'Dr',
	'Fe',
	'Pc',	# 0x18
	'Gn',
	'Mh',
	'Bo',
	'Gl',
	'Gk',
	'Ch',
	'Sb',
	'Pp'	# Sopo; 0x20
]


charColorLookup = {
	# Vanilla Melee
	'Aq': 'aqua',
	'Bk': 'black',
	'Bu': 'blue',
	'Gr': 'green',
	'Gy': 'gray',
	'La': 'lavender',
	'Nr': 'neutral',
	'Or': 'orange',
	'Pi': 'pink',
	'Re': 'red',
	'Wh': 'white',
	'Ye': 'yellow',

	# 20XX (versions 4.0+) for Falcon's .usd variations
	'Rd': 'red',
	'Rl': 'red', # Red 'L' alt costume
	'Rr': 'red', # Red 'R' alt costume

	# m-ex
	'Cy': 'cyan',
	'Br': 'brown',
	'Pr': 'purple',
}


costumeSlots = { # Character Costuems indexed by Costume ID, for each character
	'Ca': ( 'Nr', 'Gy', 'Re', 'Wh', 'Gr', 'Bu' ),
	'Dk': ( 'Nr', 'Bk', 'Re', 'Bu', 'Gr' ),
	'Fx': ( 'Nr', 'Or', 'La', 'Gr' ),
	'Gw': ( 'Nr', ), # + Re, Bu, Gr
	'Kb': ( 'Nr', 'Ye', 'Bu', 'Re', 'Gr', 'Wh' ),
	'Kp': ( 'Nr', 'Re', 'Bu', 'Bk' ),
	'Lk': ( 'Nr', 'Re', 'Bu', 'Bk', 'Wh' ),
	'Lg': ( 'Nr', 'Wh', 'Aq', 'Pi' ),
	'Mr': ( 'Nr', 'Ye', 'Bk', 'Bu', 'Gr' ),
	'Ms': ( 'Nr', 'Re', 'Gr', 'Bk', 'Wh' ),
	'Mt': ( 'Nr', 'Re', 'Bu', 'Gr' ),
	'Ns': ( 'Nr', 'Ye', 'Bu', 'Gr' ),
	'Pe': ( 'Nr', 'Ye', 'Wh', 'Bu', 'Gr' ),
	'Pk': ( 'Nr', 'Re', 'Bu', 'Gr' ),
	'Pp': ( 'Nr', 'Gr', 'Or', 'Re' ),
	'Nn': ( 'Nr', 'Ye', 'Aq', 'Wh' ),
	'Pr': ( 'Nr', 'Re', 'Bu', 'Gr', 'Ye' ),
	'Ss': ( 'Nr', 'Pi', 'Bk', 'Gr', 'La' ),
	'Ys': ( 'Nr', 'Re', 'Bu', 'Ye', 'Pi', 'Aq' ),
	'Zd': ( 'Nr', 'Re', 'Bu', 'Gr', 'Wh' ),
	'Sk': ( 'Nr', 'Re', 'Bu', 'Gr', 'Wh' ),
	'Fc': ( 'Nr', 'Re', 'Bu', 'Gr' ),
	'Cl': ( 'Nr', 'Re', 'Bu', 'Wh', 'Bk' ),
	'Dr': ( 'Nr', 'Re', 'Bu', 'Gr', 'Bk' ),
	'Fe': ( 'Nr', 'Re', 'Bu', 'Gr', 'Ye' ),
	'Pc': ( 'Nr', 'Re', 'Bu', 'Gr' ),
	'Gn': ( 'Nr', 'Re', 'Bu', 'Gr', 'La' ),
	'Mh': ( 'Nr', ),
	'Bo': ( 'Nr', ),
	'Gl': ( 'Nr', ),
	'Gk': ( 'Nr', ),
	'Ch': ( 'Nr', ),
	'Sb': ( 'Nr', ),
}


onePlayerStages = (
	'EF1',		# Goomba Trophy Stage
	'EF2',		# Entei Trophy Stage
	'EF3',		# Majora Trophy Stage
	'He.',		# All-Star Rest Area
	'Hr.',		# Homerun Contest
	'NBr',		# F-Zero Grand Prix
	'NFg',		# Trophy Collector (Figure Get)
	'NKr',		# Mushroom Kingdom Adventure
	'NPo',		# Race to the Finish (Pushon)
	'NSr',		# Underground Maze
	'NZr',		# Brinstar Escape Shaft
	'Te.'		# TEST (Coffee Shop)
)


internalStageIds = { # Descriptions for Internal Stage ID (grkind)
	0x00: "Dummy",
	0x01: "TEST",
	0x02: "Princess Peach's Castle",
	0x03: "Rainbow Cruise",
	0x04: "Kongo Jungle",
	0x05: "Jungle Japes",
	0x06: "Great Bay",
	0x07: "Hyrule Temple",
	0x08: "Brinstar",
	0x09: "Brinstar Depths",
	0x0A: "Yoshi's Story",
	0x0B: "Yoshi's Island",
	0x0C: "Fountain of Dreams",
	0x0D: "Green Greens",
	0x0E: "Corneria",
	0x0F: "Venom",
	0x10: "Pokemon Stadium",
	0x11: "Poke Floats",
	0x12: "Mute City",
	0x13: "Big Blue",
	0x14: "Onett",
	0x15: "Fourside",
	0x16: "Icicle Mountain",
	0x17: "Unused?",
	0x18: "Mushroom Kingdom",
	0x19: "Mushroom Kingdom II",
	0x1A: "Akaneia (Deleted Stage)",
	0x1B: "Flat Zone",
	0x1C: "Dream Land (N64)",
	0x1D: "Yoshi's Island (N64)",
	0x1E: "Kongo Jungle (N64)",
	0x1F: "Mushroom Kingdom Adventure",
	0x20: "Underground Maze",
	0x21: "Brinstar Escape Shaft",
	0x22: "F-Zero Grand Prix",
	0x23: "TEST", # In other words, not used (same as 0x01)
	0x24: "Battlefield",
	0x25: 'Final Destination',
	0x26: 'Trophy Collector',
	0x27: "Pushon",
	0x28: "Mario's Target Test",
	0x29: "Captain Falcon's Target Test",
	0x2A: "Young Link's Target Test",
	0x2B: "Donkey Kong's Target Test",
	0x2C: "Dr. Mario's Target Test",
	0x2D: "Falco's Target Test",
	0x2E: "Fox's Target Test",
	0x2F: "Ice Climbers' Target Test",
	0x30: "Kirby's Target Test",
	0x31: "Bowser's Target Test",
	0x32: "Link's Target Test",
	0x33: "Luigi's Target Test",
	0x34: "Marth's Target Test",
	0x35: "Mewtwo's Target Test",
	0x36: "Ness' Target Test",
	0x37: "Peach's Target Test",
	0x38: "Pichu's Target Test",
	0x39: "Pikachu's Target Test",
	0x3A: "Jigglypuff's Target Test",
	0x3B: "Samus' Target Test",
	0x3C: "Sheik's Target Test",
	0x3D: "Yoshi's Target Test",
	0x3E: "Zelda's Target Test",
	0x3F: "Game 'n Watch's Target Test",
	0x40: "Roy's Target Test",
	0x41: "Ganondorf's Target Test",
	0x42: "All-Star Rest Area",
	0x43: "Homerun Contest",
	0x44: "Goomba Trophy Stage",
	0x45: "Entei Trophy Stage",
	0x46: "Majora Trophy Stage"
}


externalStageIds = { # Descriptions for External Stage ID (stkind)
	0x0: 'Dummy',
	0x1: 'TEST',

	# STANDARD
	0x2: 'Fountain of Dreams (Izumi)',
	0x3: 'Pokémon Stadium (Pstadium)',
	0x4: "Princess Peach's Castle (Castle)",
	0x5: 'Kongo Jungle (Kongo)',
	0x6: 'Brinstar (Zebes)',
	0x7: 'Corneria',
	0x8: "Yoshi's Story (Story)",
	0x9: 'Onett',
	0xA: 'Mute City',
	0xB: 'Rainbow Cruise (RCruise)',
	0xC: 'Jungle Japes (Garden)',
	0xD: 'Great Bay',
	0xE: 'Hyrule Temple (Shrine)',
	0xF: 'Brinstar Depths (Kraid)',
	0x10: "Yoshi's Island (Yoster)",
	0x11: 'Green Greens (Greens)',
	0x12: 'Fourside',
	0x13: 'Mushroom Kingdom I (Inishie1)',
	0x14: 'Mushroom Kingdom II (Inishie2)',
	0x15: 'Akaneia (Deleted Stage)',
	0x16: 'Venom',
	0x17: 'Poké Floats (Pura)',
	0x18: 'Big Blue',
	0x19: 'Icicle Mountain',
	0x1A: 'Icetop',
	0x1B: 'Flat Zone',
	0x1C: 'Dream Land N64',
	0x1D: "Yoshi's Island N64",
	0x1E: 'Kongo Jungle N64',
	0x1F: 'Battlefield (battle)',
	0x20: 'Final Destination (last)',

	# TARGET TEST
	0x21: "Mario's Target Test",
	0x22: "C. Falcon's Target Test", 
	0x23: "Young Link's Target Test", 
	0x24: "Donkey Kong's Target Test", 
	0x25: "Dr. Mario's Target Test",
	0x26: "Falco's Target Test", 
	0x27: "Fox's Target Test", 
	0x28: "Ice Climbers's Target Test", 
	0x29: "Kirby's Target Test", 
	0x2A: "Bowser's Target Test", 
	0x2B: "Link's Target Test", 
	0x2C: "Luigi's Target Test", 
	0x2D: "Marth's Target Test",
	0x2E: "Mewtwo's Target Test", 
	0x2F: "Ness's Target Test", 
	0x30: "Peach's Target Test", 
	0x31: "Pichu's Target Test", 
	0x32: "Pikachu's Target Test", 
	0x33: "Jigglypuff's Target Test", 
	0x34: "Samus's Target Test", 
	0x35: "Sheik's Target Test", 
	0x36: "Yoshi's Target Test",
	0x37: "Zelda's Target Test",
	0x38: "Mr. Game & Watch's Target Test",
	0x39: "Roy's Target Test",
	0x3A: "Ganondorf's Target Test",

	# ADVENTURE MODE
	0x3B: "Mushroom Kingdom Adventure (Kinoko)",
	0x3C: "Princess Peach's Castle (vs Peach & Mario [or Luigi])",
	0x3D: "Kongo Jungle (vs 2 mini Donkey Kongs)",
	0x3E: "Jungle Japes (vs Donkey Kong)",
	0x3F: "Underground Maze (Meiktu)",
	0x40: "Hyrule Temple (vs Zelda)",
	0x41: "Brinstar (vs Samus)",
	0x42: "Escape from Brinstar (Dassyut)",
	0x43: "Green Greens (vs Kirby)",
	0x44: "Green Greens (vs Kirby Team)",
	0x45: "Green Greens (vs Giant Kirby)",
	0x46: "Corneria (vs Fox (or Falco))",
	0x47: "Corneria (vs Fox (or Falco) with massive arwing attack)",
	0x48: "Pokémon Stadium (vs Pikachu Team [and 1 Jigglypuff if unlocked])",
	0x49: "F-Zero Grand Prix (B Route)",
	0x4A: "Mute City (vs Captain Falcon)",
	0x4B: "Onett (vs 3 Ness)",
	0x4C: "Icicle Mountain Adventure (Icemt)",
	0x4D: "Icicle Mountain (vs 2 Ice Climbers)", # Or at Icetop?
	0x4E: "Battlefield (vs Fighting Wireframe team [low gravity])",
	0x4F: "Battlefield (vs Metal Mario [and Metal Luigi if unlocked])",
	0x50: "Final Destination (vs Bowser)",
	0x51: "Final Destination (vs Giga Bowser)",

	# BONUS STAGE
	0x52: "Race to the Finish (Takisusume)",
	0x53: "Grab the Trophies (figureget)",
	0x54: "Homerun Contest (homerun)",
	0x55: "Heal (All-Star's Stage Inbetween Matches)",

	# CLASSIC (VS SINGLE CHARACTER)
	0x56: "Princess Peach's Castle (vs Mario)",
	0x57: "Rainbow Cruise (vs Mario)",
	0x58: "Kongo Jungle (vs Donkey Kong)",
	0x59: "Jungle Japes  (vs Donkey Kong)",
	0x5A: "Great Bay (vs Link)",
	0x5B: "Temple (vs Link)",
	0x5C: "Brinstar (vs Samus)",
	0x5D: "Brinstar Depths (vs Samus)",
	0x5E: "Yoshi's Story (vs Yoshi)",
	0x5F: "Yoshi's Island (vs Yoshi)",
	0x60: "Fountain of Dreams (vs Kirby)",
	0x61: "Green Greens (vs Kirby)",
	0x62: "Corneria (vs Fox)",
	0x63: "Venom (vs Fox)",
	0x64: "Pokémon Stadium (Only Pokeballs)(vs Pikachu)",
	0x65: "Mushroom Kingdom I (vs Luigi)",
	0x66: "Mushroom Kingdom II (vs Luigi)",
	0x67: "Mute City (vs Captain Falcon)",
	0x68: "Big Blue (vs Captain Falcon)",
	0x69: "Onett (vs Ness)",
	0x6A: "Fourside (vs Ness)",
	0x6B: "Pokémon Stadium (vs Jigglypuff)",
	0x6C: "Princess Peach's Castle (vs Bowser)",
	0x6D: "Battlefield (vs Bowser)",
	0x6E: "Princess Peach's Castle (vs Peach)",
	0x6F: "Mushroom Kingdom II (vs Peach)",
	0x70: "Temple (vs Zelda)",
	0x71: "Great Bay (vs Marth)",
	0x72: "Final Destination (vs Mewtwo)",
	0x73: "Pokémon Stadium (vs Mewtwo)",
	0x74: "Icicle Mountain (vs Ice Climbers)",
	0x75: "Icicle Mountain (vs Ice Climbers)",
	0x76: "Mushroom Kingdom I (Dr. Mario Music) (vs Dr. Mario)",
	0x77: "Great Bay (vs Young Link)",
	0x78: "Temple (vs Young Link)",
	0x79: "Corneria (vs Falco)",
	0x7A: "Venom (vs Falco)",
	0x7B: "Great Bay (Unused)",
	0x7C: "Pokémon Stadium (Pichu)",

	# CLASSIC (VS TWO CHARACTERS)
	0x7D: "Battlefield (Plays Mario Theme) (vs Team Mario & Bowser)",
	0x7E: "Mushroom Kingdom II (vs Team Mario & Peach)",
	0x7F: "Kongo Jungle (vs Team DK & Fox)",
	0x80: "Temple (vs Team Link & Zelda)",
	0x81: "Great Bay (vs Team Link & Young Link)",
	0x82: "Mushroom Kingdom I (vs Team Link & Luigi)",
	0x83: "Great Bay (Saria's Song) (vs Team Marth & Link)",
	0x84: "Big Blue (vs Team Samus & Captain Falcon)",
	0x85: "Brinstar (vs Team Samus & Fox)",
	0x86: "Yoshi's Story (vs Team Yoshi & Luigi)",
	0x87: "Yoshi's Island (vs Team Yoshi & Ness)",
	0x88: "Green Greens (vs Team Kirby & Pikachu)",
	0x89: "Fountain of Dreams (vs Team Kirby & Pichu)",
	0x8A: "Green Greens (vs Team Kirby & Jigglypuff)",
	0x8B: "Icicle Mountain (vs Team Kirby & Ice Climbers)",
	0x8C: "Corneria (vs Team Fox & Falco)",
	0x8D: "Mute City (vs Team Fox & Captain Falcon)",
	0x8E: "Pokémon Stadium (vs Team Pikachu & Pichu)",
	0x8F: "Pokémon Stadium (vs Team Pikachu & Jigglypuff)",
	0x90: "Mushroom Kingdom I (vs Team Luigi & Dr. Mario)",
	0x91: "Onett (alt music) (vs Team Ness & Peach)",
	0x92: "Fourside (vs Team Ness & Mewtwo)",
	0x93: "Big Blue (mRider song) (vs Team Captain Falcon & Falco)",
	0x94: "Battlefield (vs Team Bowser & Mewtwo)",
	0x95: "Battlefield (vs Team Bowser & Peach)",
	0x96: "Battlefield (vs Team Bowser & Zelda)",
	0x97: "Temple (vs Team Peach & Zelda)",
	0x98: "Great Bay (Saria's Song) (vs Team Zelda & Young Link)",
	0x99: "Temple (Emblem) (vs Team Zelda & Marth)",
	0x9A: "Great Bay (Unused)",

	# CLASSIC (VS GIANT CHARACTER)
	0x9B: "Princess Peach's Castle (vs Giant Mario)",
	0x9C: "Kongo Jungle (vs Giant DK)",
	0x9D: "Great Bay (vs vs Giant Link)",
	0x9E: "Yoshi's Story (vs Giant Yoshi)",
	0x9F: "Mushroom Kingdom II (vs Giant Luigi)",
	0xA0: "Mute City (vs Giant Captain Falcon)",
	0xA1: "Pokémon Stadium (vs Giant Jigglypuff)",
	0xA2: "Fountain of Dreams (vs Giant Bowser)",
	0xA3: "Mushroom Kingdom I (vs Giant Dr. Mario)",
	0xA4: "Temple (vs Giant Young Link)",

	# CLASSIC (VS TEAM CHARACTER)
	0xA5: "Rainbow Cruise (vs Team Mario)",
	0xA6: "Jungle Japes (vs Team Donkey Kong)",
	0xA7: "Fountain of Dreams (vs Team Kirby)",
	0xA8: "Mushroom Kingdom II (vs Team Luigi)",
	0xA9: "Onett (vs Team Ness)",
	0xAA: "Pokémon Stadium (vs Team Jigglypuff)",
	0xAB: "Icicle Mountain (Unused)",
	0xAC: "Pokémon Stadium (vs Team Pichu)",
	0xAD: "Flat Zone (vs Team Game & Watch)",
	0xAE: "Mute City (vs Team Captain Falcon)",

	# CLASSIC FINAL
	0xAF: "Battlefield (No items) (vs Metal Character)",
	0xB0: "Final Destination (No items) (vs Master Hand)",

	# ALL-STAR
	0xB1: "Rainbow Cruise (vs Mario)",
	0xB2: "Kongo Jungle (vs Donkey Kong)",
	0xB3: "Great Bay (vs Link)",
	0xB4: "Brinstar (vs Samus)", 
	0xB5: "Yoshi's Story (vs Yoshi)",
	0xB6: "Green Greens (vs Kirby)",
	0xB7: "Corneria (vs Fox)",
	0xB8: "Pokémon Stadium (vs Pikachu)",
	0xB9: "Mushroom Kingdom I (vs Luigi)",
	0xBA: "Mute City (vs Captain Falcon)",
	0xBB: "Onett (vs Ness)",
	0xBC: "Poké Floats (vs Jigglypuff)",
	0xBD: "Icicle Mountain (vs Ice Climbers)",
	0xBE: "Princess Peach's Castle (vs Peach)",
	0xBF: "Temple (vs Zelda)",
	0xC0: "Fountain of Dreams (Emblem Music) (vs Marth)",
	0xC1: "Battlefield (Poké Floats song) (vs Mewtwo)",
	0xC2: "Yoshi's Island (vs Bowser)",
	0xC3: "Mushroom Kingdom II (Dr Mario Music) (vs Dr Mario)",
	0xC4: "Jungle Japes (vs Young Link)",
	0xC5: "Venom (vs Falco)",
	0xC6: "Fourside (vs Pichu)",
	0xC7: "Final Destination (Emblem Music) (vs Roy)",
	0xC8: "Flat Zone (vs Team Game & Watch)",
	0xC9: "Brinstar Depths (vs Gannondorf)",

	# EVENT MATCH
	0xCA: "Battlefield (Event #01 - Trouble King)",
	0xCB: "Temple (Event #18 - Link's Adventure)",
	0xCC: "Princess Peach's Castle (Event #03 - Bomb-fest)",
	0xCD: "Yoshi's Story (Event #04 - Dino-wrangling)",
	0xCE: "Onett (Event #05 - Spare Change)",
	0xCF: "Fountain of Dreams (Event #06 - Kirbys on Parade)",
	0xD0: "Pokémon Stadium (Event #07 - Pokémon Battle)",
	0xD1: "Brinstar (Event #08 - Hot Date on Brinstar)",
	0xD2: "Great Bay (Event #09 - Hide 'n' Sheik)",
	0xD3: "Yoshi's Island (Event #10 - All-Star Match 1-1 /vs Mario)",
	0xD4: "Icicle Mountain (Event #11 - King of the Mountain)",
	0xD5: "Mute City (Event #12 - Seconds, Anyone?)",
	0xD6: "Rainbow Cruise  (Event #13 - Yoshi's Egg)",
	0xD7: "Goomba  (Event #14 - Trophy Tussle 1)",
	0xD8: "Battlefield (Event #44 - Mewtwo Strikes!)",
	0xD9: "Corneria (Event #16 - Kirby's Air-raid)",
	0xDA: "Jungle Japes (F-Zero Music) (Event #17 - Bounty Hunters)",
	0xDB: "Kongo Jungle (Event #2 - Lord of the Jungle)",
	0xDC: "Final Destination (Event #19 - Peach's Peril)",
	0xDD: "Brinstar (Event #20 - All-Star Match 2-1 /vs Samus)",
	0xDE: "Princess Peach's Castle (Event #21 - Ice Breaker)",
	0xDF: "Mushroom Kingdom II (Event #22 - Super Mario 128)",
	0xE0: "Brinstar Depths (Event #27 - Cold Armor)",
	0xE1: "Yoshi's Island (Event #24 - The Yoshi Herd)",
	0xE2: "Fourside (DK Rap) (Event #25 - Gargantuans)",
	0xE3: "Entei (Event #26 - Trophy Tussle 2)",
	0xE4: "Venom (Event #23 - Slippy's Invention)",
	0xE5: "Green Greens (Event #28 - Puffballs Unite)",
	0xE6: "Temple (Great Bay music - Event #29) (Triforce Gathering)",
	0xE7: "Fountain of Dreams (Event #15 - Girl Power)",
	0xE8: "Mushroom Kingdom I (Event #31 - Mario Bros. Madness)",
	0xE9: "Corneria (Many Arwings) (Event #32 - Target Acquired)",
	0xEA: "F-Zero Adventure Stage (Event #33 - Lethal Marathon)",
	0xEB: "Great Bay (Event #34 - Seven Years)",
	0xEC: "Dream Land (Event #35 - Time for a Checkup)",
	0xED: "Fourside (Event #36 - Space Travelers)",
	0xEE: "Fountain of Dreams (Event #30 - All-Star Match 3-1 /vs Kirby)",
	0xEF: "Mushroom Kingdom II (Event #38 - Super Mario Bros. 2)",
	0xF0: "Pokémon Stadium (Event #39 - Jigglypuff Live!)",
	0xF1: "Temple (Emblem Music) (Event #40 - All-Star Match 4-1 /vs Marth)",
	0xF2: "Temple (Emblem Music) (Event #41 - En Garde!)",
	0xF3: "Poké Floats (Event #42 - Trouble King 2)",
	0xF4: "Big Blue (Event #43 - Birds of Prey)",
	0xF5: "Battlefield (Event #37 - Legendary Pokemon)",
	0xF6: "Flat Zone (Event #45 - Game and Watch Forever!)",
	0xF7: "Temple (Emblem Music) (Event #46 - Fire Emblem Pride)",
	0xF8: "Majora's Mask (Event #47 - Trophy Tussle 3)",
	0xF9: "Yoshi's Story (Event #48 - Pikachu and Pichu)",
	0xFA: "Mushroom Kingdom I  (Event #49 - All-Star Match Deluxe 5-1 /vs Dr Mario)",
	0xFB: "Final Destination  (Event #50 - Final Destination Match)",
	0xFC: "Final Destination (Event #51 - The Showdown)",
	0xFD: "Jungle Japes (DK Rap) (Event #10 - All-Star Match 1-2 /vs DK)",
	0xFE: "Yoshi's Story (Event #10 - All-Star Match 1-3 /vs Yoshi)",
	0xFF: "Princess Peach's Castle (Event #10 - All-Star Match 1-4 /vs Peach)",
	0x101: "Great Bay  (All-Star Match 2-2, vs Link)",
	0x102: "Temple  (All-Star Match 2-3, vs Zelda)",
	0x103: "Mute City (All-Star Match 2-4, vs Captain Falcon)",
	0x104: "Corneria (All-Star Match 2-5, vs Fox)",
	0x105: "Pokémon Stadium (All-Star Match 3-2, vs Pikachu)",
	0x106: "Onett (All-Star Match 3-3, vs Ness)",
	0x107: "Icicle Mountain (All-Star Match 3-4, vs Ice Climbers)",
	0x108: "Mushroom Kingdom II (All-Star Match 4-2, vs Luigi)",
	0x109: "Poké Floats (All-Star Match 4-3, vs Jigglypuff)",
	0x10A: "Final Destination (All-Star Match 4-4, vs Mewtwo)",
	0x10B: "Flat Zone (All-Star Match 4-5, vs Mr Game & Watch)",
	0x10C: "Venom (All-Star Match Deluxe 5-2, vs Falco)",
	0x10D: "Pokémon Stadium (All-Star Match Deluxe 5-3, vs Pichu)",
	0x10E: "Great Bay (Saria's Song) (All-Star Match Deluxe 5-4, vs Young Link)",
	0x10F: "Temple (Emblem Music) (All-Star Match Deluxe 5-5, vs Roy)",
	0x110: "Final Destination (All-Star Match Deluxe 5-6, vs Gannondorf)",

	# UNLOCKABLES
	0x111: "Battlefield (NO CHARA)",
	0x112: "Pokémon Stadium, Unlocking Jigglypuff",
	0x113: "Final Destination, Unlocking Mewtwo",
	0x114: "Mushroom Kingdom II, Unlocking Luigi",
	0x115: "Fountain of Dreams, Unlocking Marth",
	0x116: "Flat Zone, Unlocking Mr Game and Watch",
	0x117: "Princess Peach's Castle (DR Mario song), Unlocking Dr Mario",
	0x118: "Final Destination (Great Bay music), Unlocking Gannondorf",
	0x119: "Great Bay (Saria's Song), Unlocking Young Link",
	0x11A: "Battlefield (Corneria Music), Unlocking Falco",
	0x11B: "Pokémon Stadium, Unlocking Pichu?",
	0x11C: "Temple (Emblem Music), Unlocking Roy?",

	# MULTI-MAN MELEE
	0x11D: "Battlefield (Multi-Man Melee)"
}


# musicIdNames = {
# 	0x00: "All-Star Rest Area",
# 	0x01: "Fire Emblem",
# 	0x02: "Balloon Fight",
# 	0x03: "Big Blue",
# 	0x04: "Princess Peach's Castle",
# 	0x05: "Continue",
# 	0x06: "Corneria",
# 	0x07: "Dr. Mario",
# 	0x08: "Ending Fanfare",
# 	0x09: "Demo Fanfare (Unused)",
# 	0x0a: "1P Mode Fanfare 1",
# 	0x0b: "1P Mode Fanfare 2",
# 	0x0c: "Unused Bad Fanfare",
# 	0x0d: "Donkey Kong Victory Theme",
# 	0x0e: "Fire Emblem Victory Theme",
# 	0x0f: "Game & Watch Victory Theme",
# 	0x10: "Star Fox Victory Theme",
# 	0x11: "F-Zero Victory Theme",
# 	0x12: "Unused Good Fanfare",
# 	0x13: "Ice Climber Victory Theme",
# 	0x14: "Kirby Victory Theme",
# 	0x15: "Legend of Zelda Victory Theme",
# 	0x16: "Super Mario Victory Theme",
# 	0x17: "Earthbound Victory Theme",
# 	0x18: "Pokemon Victory Theme",
# 	0x19: "Metroid Victory Theme",
# 	0x1a: "Unused Fanfare 1",
# 	0x1b: "Unused Fanfare 2",
# 	0x1c: "Unused Fanfare 3",
# 	0x1d: "Yoshi Victory Theme",
# 	0x1e: "Flat Zone",
# 	0x1f: "Fourside",
# 	0x20: "Game Over",
# 	0x21: "Kongo Jungle",
# 	0x22: "Great Bay",
# 	0x23: "Green Greens",
# 	0x24: "How to Play (music w/sound effects)",
# 	0x25: "How to Play (music only)",
# 	0x26: "Multi-Man Melee 1",
# 	0x27: "Multi-Man Melee 2",
# 	0x28: "Icicle Mountain",
# 	0x29: "Mushroom Kingdom",
# 	0x2a: "Mushroom Kingdom (Finale)",
# 	0x2b: "Mushroom Kingdom II",
# 	0x2c: "Mushroom Kingdom II (Finale)",
# 	0x2d: "Classic Fanfare",
# 	0x2e: "Adventure Fanfare",
# 	0x2f: "Hammer Theme",
# 	0x30: "Star Theme",
# 	0x31: "Fountain of Dreams",
# 	0x32: "Jungle Japes",
# 	0x33: "Brinstar Depths",
# 	0x34: "Main Menu (Default)",
# 	0x35: "Lottery",
# 	0x36: "Main Menu (Alternate)",
# 	0x37: "Mach Rider",
# 	0x38: "Mute City",
# 	0x39: "Kongo Jungle N64",
# 	0x3a: "Dream Land 64",
# 	0x3b: "Yoshi's Island 64",
# 	0x3c: "Onett",
# 	0x3d: "Mother 2",
# 	0x3e: "Opening (video audio)",
# 	0x3f: "Battle Theme (Pokemon)",
# 	0x40: "Pokemon Stadium",
# 	0x41: "Poke Floats",
# 	0x42: "Rainbow Cruise",
# 	0x43: "Info Fanfare 1",
# 	0x44: "Info Fanfare 2",
# 	0x45: "Info Fanfare 3",
# 	0x46: "Trophy Fanfare",
# 	0x47: "Unused Fanfare",
# 	0x48: "Challenger Approaching",
# 	0x49: "Unused Song (Hammer Theme)",
# 	0x4a: "Saria's Theme",
# 	0x4b: "Temple",
# 	0x4c: "Brinstar Escape",
# 	0x4d: "Super Mario Bros. 3",
# 	0x4e: "Final Destination",
# 	0x4f: "Giga Bowser",
# 	0x50: "Metal Battle",
# 	0x51: "Battlefield (Fighting Wire Frames)",
# 	0x52: "Special Movie (video audio)",
# 	0x53: "Targets!",
# 	0x54: "Venom",
# 	0x55: "Metal Mario Cutscene",
# 	0x56: "Luigi Adventure Cutscene",
# 	0x57: "Corneria Adventure Cutscene",
# 	0x58: "Space Adventure Cutscene",
# 	0x59: "Bowser Destroyed Cutscene",
# 	0x5a: "Giga Bowser Destroyed Cutscene",
# 	0x5b: "F-Zero Adventure Cutscene",
# 	0x5c: "Giga Bowser Cutscene",
# 	0x5d: "Tournament Mode 1",
# 	0x5e: "Tournament Mode 2",
# 	0x5f: "Yoshi's Island",
# 	0x60: "Yoshi's Story",
# 	0x61: "Brinstar",
# 	0x62: "testnz"
# }

# musicIdFilenames = {

# }


# stageFileNames = { # Key = internal stage ID	(assumes country code set to 1; using latin/.usd variations)
# 	#0x00: '' # Dummy/placeholder stage
# 	0x01: 'GrTe.dat', # TEST stage
# 	0x02: 'GrCs.dat', # Princess Peach's Castle
# 	0x03: 'GrRc.dat', # Rainbow Cruise
# 	0x04: 'GrKg.dat', # Kongo Jungle
# 	0x05: 'GrGd.dat', # Jungle Japes
# 	0x06: 'GrGb.dat', # Great Bay
# 	0x07: 'GrSh.dat', # Hyrule Temple
# 	0x08: 'GrZe.dat', # Brinstar
# 	0x09: 'GrKr.dat', # Brinstar Depths
# 	0x0A: 'GrSt.dat', # Yoshi's Story
# 	0x0B: 'GrYt.dat', # Yoshi's Island
# 	0x0C: 'GrIz.dat', # Fountain of Dreams
# 	0x0D: 'GrGr.dat', # Green Greens
# 	0x0E: 'GrCn.usd', # Corneria
# 	0x0F: 'GrVe.dat', # Venom
# 	0x10: 'GrPs.usd', # Pokemon Stadium
# 	0x11: 'GrPu.dat', # Poke Floats
# 	0x12: 'GrMc.dat', # Mute City
# 	0x13: 'GrBb.dat', # Big Blue
# 	0x14: 'GrOt.usd', # Onett
# 	0x15: 'GrFs.dat', # Fourside
# 	0x16: 'GrIm.dat', # Icicle Mountain
# 	#0x17: , # Unused?
# 	0x18: 'GrI1.dat', # Mushroom Kingdom
# 	0x19: 'GrI2.dat', # Mushroom Kingdom II
# 	#0x1A: , # Akaneia (Deleted Stage)
# 	0x1B: 'GrFz.dat', # Flat Zone
# 	0x1C: 'GrOp.dat', # Dream Land (N64)
# 	0x1D: 'GrOy.dat', # Yoshi's Island (N64)
# 	0x1E: 'GrOk.dat', # Kongo Jungle (N64)
# 	0x1F: 'GrNKr.dat', # Mushroom Kingdom Adventure
# 	0x20: "GrNSr.dat", # Underground Maze
# 	0x21: "GrNZr.dat", # Brinstar Escape Shaft
# 	0x22: "GrNBr.dat", # F-Zero Grand Prix

# 	0x24: 'GrNBa.dat', # Battlefield
# 	0x25: 'GrNLa.dat', # Final Destination
# 	#0x26: , # Unused?
# 	0x27: 'GrNPo.dat', # Race to the Finish (Pushon)
# 	0x28: 'GrTMr.dat', # Mario's Target Test
# 	0x29: 'GrTCa.dat', # Captain Falcon's Target Test
# 	0x2A: 'GrTCl.dat', # Young Link's Target Test
# 	0x2B: 'GrTDk.dat', # Donkey Kong's Target Test
# 	0x2C: 'GrTDr.dat', # Dr. Mario's Target Test
# 	0x2D: 'GrTFc.dat', # Falco's Target Test
# 	0x2E: 'GrTFx.dat', # Fox's Target Test
# 	0x2F: 'GrTIc.dat', # Ice Climbers' Target Test
# 	0x30: 'GrTKb.dat', # Kirby's Target Test
# 	0x31: 'GrTKp.dat', # Bowser's Target Test
# 	0x32: 'GrTLk.dat', # Link's Target Test
# 	0x33: 'GrTLg.dat', # Luigi's Target Test
# 	0x34: 'GrTMs.dat', # Marth's Target Test
# 	0x35: 'GrTMt.dat', # Mewtwo's Target Test
# 	0x36: 'GrTNs.dat', # Ness' Target Test
# 	0x37: 'GrTPe.dat', # Peach's Target Test
# 	0x38: 'GrTPc.dat', # Pichu's Target Test
# 	0x39: 'GrTPk.dat', # Pikachu's Target Test
# 	0x3A: 'GrTPr.dat', # Jigglypuff's Target Test
# 	0x3B: 'GrTSs.dat', # Samus' Target Test
# 	0x3C: 'GrTSk.dat', # Sheik's Target Test
# 	0x3D: 'GrTYs.dat', # Yoshi's Target Test
# 	0x3E: 'GrTZd.dat', # Zelda's Target Test
# 	0x3F: 'GrTGw.dat', # Game 'n Watch's Target Test
# 	0x40: 'GrTFe.dat', # Roy's Target Test
# 	0x41: 'GrTGn.dat', # Ganondorf's Target Test
# 	0x42: 'GrHe.dat', # All-Star Rest Area
# 	0x43: 'GrHr.dat', # Homerun Contest
# 	0x44: 'GrEF1.dat', # Goomba Trophy Stage
# 	0x45: 'GrEF2.dat', # Entei Trophy Stage
# 	0x46: 'GrEF3.dat', # Majora Trophy Stage
# }


# For Menu Text Conversion
DolCharacters = {

	# Single-Byte Characters
	'1a' : u' ',  '03' : u'\n', # Space, and newLine (line break)

	# English numbers & alphabet
	'2000': u'0', '2001': u'1', '2002': u'2', '2003': u'3', '2004': u'4', '2005': u'5', '2006': u'6', '2007': u'7', '2008': u'8', '2009': u'9',
	'200a': u'A', '200b': u'B', '200c': u'C', '200d': u'D', '200e': u'E', '200f': u'F', '2010': u'G', '2011': u'H', '2012': u'I', '2013': u'J',
	'2014': u'K', '2015': u'L', '2016': u'M', '2017': u'N', '2018': u'O', '2019': u'P', '201a': u'Q', '201b': u'R', '201c': u'S', '201d': u'T',
	'201e': u'U', '201f': u'V', '2020': u'W', '2021': u'X', '2022': u'Y', '2023': u'Z',
	'2024': u'a', '2025': u'b', '2026': u'c', '2027': u'd', '2028': u'e', '2029': u'f', '202a': u'g', '202b': u'h', '202c': u'i', '202d': u'j',
	'202e': u'k', '202f': u'l', '2030': u'm', '2031': u'n', '2032': u'o', '2033': u'p', '2034': u'q', '2035': u'r', '2036': u's', '2037': u't',
	'2038': u'u', '2039': u'v', '203a': u'w', '203b': u'x', '203c': u'y', '203d': u'z',

	# Japanese Hiragana
	'203e': u'ぁ', '203f': u'あ', '2040': u'ぃ', '2041': u'い', '2042': u'ぅ', '2043': u'う', '2044': u'ぇ', '2045': u'え', '2046': u'ぉ', '2047': u'お', 
	'2048': u'か', '2049': u'が', '204a': u'き', '204b': u'ぎ', '204c': u'く', '204d': u'ぐ', '204e': u'け', '204f': u'げ', '2050': u'こ', '2051': u'ご', 
	'2052': u'さ', '2053': u'ざ', '2054': u'し', '2055': u'じ', '2056': u'す', '2057': u'ず', '2058': u'せ', '2059': u'ぜ', '205a': u'そ', '205b': u'ぞ', 
	'205c': u'た', '205d': u'だ', '205e': u'ち', '205f': u'ぢ', '2060': u'っ', '2061': u'つ', '2062': u'づ', '2063': u'て', '2064': u'で', '2065': u'と', 
	'2066': u'ど', '2067': u'な', '2068': u'に', '2069': u'ぬ', '206a': u'ね', '206b': u'の', '206c': u'は', '206d': u'ば', '206e': u'ぱ', '206f': u'ひ', 
	'2070': u'び', '2071': u'ぴ', '2072': u'ふ', '2073': u'ぶ', '2074': u'ぷ', '2075': u'へ', '2076': u'べ', '2077': u'ぺ', '2078': u'ほ', '2079': u'ぼ', 
	'207a': u'ぽ', '207b': u'ま', '207c': u'み', '207d': u'む', '207e': u'め', '207f': u'も', '2080': u'ゃ', '2081': u'や', '2082': u'ゅ', '2083': u'ゆ', 
	'2084': u'ょ', '2085': u'よ', '2086': u'ら', '2087': u'り', '2088': u'る', '2089': u'れ', '208a': u'ろ', '208b': u'ゎ', '208c': u'わ', '208d': u'を', 
	'208e': u'ん',

	# Japanese Katakana
	'208f': u'ァ', '2090': u'ア', '2091': u'ィ', '2092': u'イ', '2093': u'ゥ', '2094': u'ウ', '2095': u'ェ', '2096': u'エ', '2097': u'ォ', '2098': u'オ', 
	'2099': u'カ', '209a': u'ガ', '209b': u'キ', '209c': u'ギ', '209d': u'ク', '209e': u'グ', '209f': u'ケ', '20a0': u'ゲ', '20a1': u'コ', '20a2': u'ゴ', 
	'20a3': u'サ', '20a4': u'ザ', '20a5': u'シ', '20a6': u'ジ', '20a7': u'ス', '20a8': u'ズ', '20a9': u'セ', '20aa': u'ゼ', '20ab': u'ソ', '20ac': u'ゾ', 
	'20ad': u'タ', '20ae': u'ダ', '20af': u'チ', '20b0': u'ヂ', '20b1': u'ッ', '20b2': u'ツ', '20b3': u'ヅ', '20b4': u'テ', '20b5': u'デ', '20b6': u'ト', 
	'20b7': u'ド', '20b8': u'ナ', '20b9': u'ニ', '20ba': u'ヌ', '20bb': u'ネ', '20bc': u'ノ', '20bd': u'ハ', '20be': u'バ', '20bf': u'パ', '20c0': u'ヒ', 
	'20c1': u'ビ', '20c2': u'ピ', '20c3': u'フ', '20c4': u'ブ', '20c5': u'プ', '20c6': u'ヘ', '20c7': u'ベ', '20c8': u'ペ', '20c9': u'ホ', '20ca': u'ボ', 
	'20cb': u'ポ', '20cc': u'マ', '20cd': u'ミ', '20ce': u'ム', '20cf': u'メ', '20d0': u'モ', '20d1': u'ャ', '20d2': u'ヤ', '20d3': u'ュ', '20d4': u'ユ', 
	'20d5': u'ョ', '20d6': u'ヨ', '20d7': u'ラ', '20d8': u'リ', '20d9': u'ル', '20da': u'レ', '20db': u'ロ', '20dc': u'ヮ', '20dd': u'ワ', '20de': u'ヲ', 
	'20df': u'ン', '20e0': u'ヴ', '20e1': u'ヵ', '20e2': u'ヶ',

	# Punctuation
	'20e3': u'　', '20e4': u'、', '20e5': u'。', # These are the "ideographic"/Japanese space, comma, and period (the space here is not the same space character found under '1a')
	'20e6': u',', '20e7': u'.', '20e8': u'•', '20e9': u':', '20ea': u';', '20eb': u'?', '20ec': u'!', '20ed': u'^', '20ee': u'_', '20ef': u'—', # '20ef' is an "em dash" (U+2014)
	'20f0': u'/', '20f1': u'~', '20f2': u'|', '20f3': "'", '20f4': u'"', '20f5': u'(', '20f6': u')', '20f7': u'[', '20f8': u']', '20f9': u'{', 
	'20fa': u'}', '20fb': u'+', '20fc': u'-', '20fd': u'×', '20fe': u'=', '20ff': u'<', '2100': u'>', '2101': u'¥', '2102': u'$', '2103': u'%', # '20fd' is not simply another x, but a multiplication sign (U+00D7)
	'2104': u'#', '2105': u'&', '2106': u'*', '2107': u'@',

	# Japanese Kanji
	'2108': u'扱', '2109': u'押', '210a': u'軍', '210b': u'源', '210c': u'個', '210d': u'込', '210e': u'指', '210f': u'示', '2110': u'取', '2111': u'書',
	'2112': u'詳', '2113': u'人', '2114': u'生', '2115': u'説', '2116': u'体', '2117': u'団', '2118': u'電', '2119': u'読', '211a': u'発', '211b': u'抜',
	'211c': u'閑', '211d': u'本', '211e': u'明',
}

SdCharacters_1 = {
	# Misc Items							Found in SdMenu.usd				(Only accessible if the game is set to English)
	'4000': u'é', '4001': u'〇', '4002': u'Ⅱ', '4003': u'王', '4004': u'国', '4005': u'山', '4006': u'頂', 	# 4002 seems to be a Roman numeral 2
}

SdCharacters_2 = {
	# Misc Items and Japanese Kanji			Found in SdMenu.dat				(Only accessible if the game is set to Japanese)
	'4000': u'々', '4001': u'「', '4002': u'」', '4003': u'『', '4004': u'』', '4005': u'♂', '4006': u'♀', '4007': u'〇', '4008': u'→', '4009': u'Ⅱ', # The corner brackets are quotation marks in East Asian languages
	
	'400a': u'亜', '400b': u'暗', '400c': u'以', '400d': u'位', '400e': u'意', '400f': u'医', '4010': u'ー', '4011': u'員', '4012': u'隠', '4013': u'右', # 4010 may instead be 一
	'4014': u'宇', '4015': u'影', '4016': u'映', '4017': u'液', '4018': u'越', '4019': u'円', '401a': u'援', '401b': u'演', '401c': u'炎', '401d': u'遠',
	'401e': u'奥', '401f': u'応', '4020': u'横', '4021': u'王', '4022': u'屋', '4023': u'俺', '4024': u'音', '4025': u'下', '4026': u'化', '4027': u'仮',

	'4028': u'何', '4029': u'価', '402a': u'加', '402b': u'可', '402c': u'果', '402d': u'歌', '402e': u'花', '402f': u'課', '4030': u'過', '4031': u'牙',
	'4032': u'画', '4033': u'介', '4034': u'会', '4035': u'解', '4036': u'回', '4037': u'壊', '4038': u'怪', '4039': u'悔', '403a': u'懐', '403b': u'界',
	'403c': u'開', '403d': u'外', '403e': u'崖', '403f': u'鎧', '4040': u'格', '4041': u'獲', '4042': u'学', '4043': u'楽', '4044': u'割', '4045': u'活',

	'4046': u'巻', '4047': u'看', '4048': u'管', '4049': u'観', '404a': u'間', '404b': u'含', '404c': u'器', '404d': u'基', '404e': u'期', '404f': u'棄',
	'4050': u'帰', '4051': u'気', '4052': u'記', '4053': u'貴', '4054': u'起', '4055': u'技', '4056': u'橘', '4057': u'客', '4058': u'逆', '4059': u'久',
	'405a': u'仇', '405b': u'休', '405c': u'宮', '405d': u'急', '405e': u'球', '405f': u'旧', '4060': u'牛', '4061': u'去', '4062': u'巨', '4063': u'距',

	'4064': u'競', '4065': u'共', '4066': u'協', '4067': u'強', '4068': u'恐', '4069': u'況', '406a': u'狂', '406b': u'狭', '406c': u'驚', '406d': u'玉',
	'406e': u'均', '406f': u'禁', '4070': u'近', '4071': u'金', '4072': u'銀', '4073': u'具', '4074': u'空', '4075': u'遇', '4076': u'群', '4077': u'兄',
	'4078': u'型', '4079': u'形', '407a': u'憩', '407b': u'系', '407c': u'経', '407d': u'計', '407e': u'軽', '407f': u'撃', '4080': u'激', '4081': u'決',
	
	'4082': u'結', '4083': u'月', '4084': u'剣', '4085': u'見', '4086': u'険', '4087': u'減', '4088': u'現', '4089': u'限', '408a': u'己', '408b': u'五',
	'408c': u'後', '408d': u'語', '408e': u'護', '408f': u'公', '4090': u'功', '4091': u'効', '4092': u'向', '4093': u'好', '4094': u'工', '4095': u'抗',
	'4096': u'攻', '4097': u'行', '4098': u'鋼', '4099': u'降', '409a': u'高', '409b': u'号', '409c': u'合', '409d': u'国', '409e': u'酷', '409f': u'黒',
	
	'40a0': u'今', '40a1': u'左', '40a2': u'差', '40a3': u'再', '40a4': u'最', '40a5': u'歳', '40a6': u'祭', '40a7': u'細', '40a8': u'菜', '40a9': u'在',
	'40aa': u'坂', '40ab': u'咲', '40ac': u'作', '40ad': u'削', '40ae': u'撮', '40af': u'殺', '40b0': u'参', '40b1': u'山', '40b2': u'算', '40b3': u'残',
	'40b4': u'使', '40b5': u'刺', '40b6': u'四', '40b7': u'士', '40b8': u'始', '40b9': u'姿', '40ba': u'子', '40bb': u'止', '40bc': u'鰤', '40bd': u'試',

	'40be': u'事', '40bf': u'字', '40c0': u'持', '40c1': u'時', '40c2': u'自', '40c3': u'失', '40c4': u'質', '40c5': u'実', '40c6': u'写', '40c7': u'射',
	'40c8': u'捨', '40c9': u'者', '40ca': u'邪', '40cb': u'若', '40cc': u'弱', '40cd': u'主', '40ce': u'守', '40cf': u'手', '40d0': u'殊', '40d1': u'種',
	'40d2': u'首', '40d3': u'受', '40d4': u'収', '40d5': u'拾', '40d6': u'終', '40d7': u'習', '40d8': u'襲', '40d9': u'集', '40da': u'住', '40db': u'十',
	
	'40dc': u'獣', '40dd': u'重', '40de': u'出', '40df': u'術', '40e0': u'瞬', '40e1': u'順', '40e2': u'初', '40e3': u'所', '40e4': u'女', '40e5': u'除',
	'40e6': u'傷', '40e7': u'勝', '40e8': u'商', '40e9': u'小', '40ea': u'少', '40eb': u'床', '40ec': u'晶', '40ed': u'消', '40ee': u'章', '40ef': u'賞',
	'40f0': u'上', '40f1': u'乗', '40f2': u'城', '40f3': u'場', '40f4': u'常', '40f5': u'情', '40f6': u'状', '40f7': u'心', '40f8': u'振', '40f9': u'新',
	
	'40fa': u'深', '40fb': u'真', '40fc': u'神', '40fd': u'身', '40fe': u'辛', '40ff': u'進', '4100': u'陣', '4101': u'水', '4102': u'数', '4103': u'寸',
	'4104': u'世', '4105': u'制', '4106': u'性', '4107': u'成', '4108': u'整', '4109': u'星', '410a': u'声', '410b': u'青', '410c': u'積', '410d': u'切',
	'410e': u'接', '410f': u'設', '4110': u'絶', '4111': u'先', '4112': u'専', '4113': u'戦', '4114': u'泉', '4115': u'選', '4116': u'前', '4117': u'然',
	
	'4118': u'全', '4119': u'狙', '411a': u'素', '411b': u'組', '411c': u'阻', '411d': u'壮', '411e': u'掃', '411f': u'操', '4120': u'早', '4121': u'祖',
	'4122': u'総', '4123': u'走', '4124': u'送', '4125': u'遭', '4126': u'像', '4127': u'増', '4128': u'足', '4129': u'速', '412a': u'賊', '412b': u'族',
	'412c': u'続', '412d': u'存', '412e': u'損', '412f': u'他', '4130': u'多', '4131': u'太', '4132': u'打', '4133': u'対', '4134': u'耐', '4135': u'待',
	
	'4136': u'態', '4137': u'替', '4138': u'隊', '4139': u'代', '413a': u'台', '413b': u'大', '413c': u'題', '413d': u'択', '413e': u'脱', '413f': u'誰',
	'4140': u'短', '4141': u'壇', '4142': u'弾', '4143': u'断', '4144': u'段', '4145': u'値', '4146': u'知', '4147': u'地', '4148': u'遅', '4149': u'蓄',
	'414a': u'着', '414b': u'中', '414c': u'宙', '414d': u'丁', '414e': u'挑', '414f': u'町', '4150': u'調', '4151': u'跳', '4152': u'長', '4153': u'頂',
	
	'4154': u'鳥', '4155': u'直', '4156': u'墜', '4157': u'追', '4158': u'通', '4159': u'定', '415a': u'底', '415b': u'弟', '415c': u'抵', '415d': u'程',
	'415e': u'敵', '415f': u'的', '4160': u'適', '4161': u'鉄', '4162': u'天', '4163': u'店', '4164': u'転', '4165': u'点', '4166': u'伝', '4167': u'殿',
	'4168': u'登', '4169': u'途', '416a': u'度', '416b': u'土', '416c': u'倒', '416d': u'島', '416e': u'投', '416f': u'盗', '4170': u'当', '4171': u'討',
	
	'4172': u'逃', '4173': u'透', '4174': u'頭', '4175': u'闘', '4176': u'動', '4177': u'同', '4178': u'道', '4179': u'得', '417a': u'特', '417b': u'毒',
	'417c': u'内', '417d': u'謎', '417e': u'二', '417f': u'肉', '4180': u'日', '4181': u'乳', '4182': u'入', '4183': u'年', '4184': u'能', '4185': u'破',
	'4186': u'敗', '4187': u'背', '4188': u'輩', '4189': u'配', '418a': u'倍', '418b': u'売', '418c': u'博', '418d': u'爆', '418e': u'箱', '418f': u'半',
	
	'4190': u'反', '4191': u'番', '4192': u'彼', '4193': u'飛', '4194': u'匹', '4195': u'必', '4196': u'百', '4197': u'氷', '4198': u'表', '4199': u'評',
	'419a': u'秒', '419b': u'不', '419c': u'付', '419d': u'婦', '419e': u'富', '419f': u'負', '41a0': u'部', '41a1': u'風', '41a2': u'復', '41a3': u'物',
	'41a4': u'分', '41a5': u'文', '41a6': u'聞', '41a7': u'兵', '41a8': u'平', '41a9': u'並', '41aa': u'別', '41ab': u'変', '41ac': u'編', '41ad': u'返',
	
	'41ae': u'保', '41af': u'歩', '41b0': u'報', '41b1': u'抱', '41b2': u'放', '41b3': u'方', '41b4': u'法', '41b5': u'砲', '41b6': u'訪', '41b7': u'豊',
	'41b8': u'暴', '41b9': u'冒', '41ba': u'摩', '41bb': u'魔', '41bc': u'枚', '41bd': u'毎', '41be': u'満', '41bf': u'味', '41c0': u'未', '41c1': u'密',
	'41c2': u'夢', '41c3': u'無', '41c4': u'名', '41c5': u'命', '41c6': u'迷', '41c7': u'滅', '41c8': u'面', '41c9': u'猛', '41ca': u'木', '41cb': u'目',
	
	'41cc': u'問', '41cd': u'紋', '41ce': u'野', '41cf': u'役', '41d0': u'優', '41d1': u'有', '41d2': u'由', '41d3': u'裕', '41d4': u'遊', '41d5': u'余',
	'41d6': u'与', '41d7': u'容', '41d8': u'用', '41d9': u'要', '41da': u'来', '41db': u'頼', '41dc': u'落', '41dd': u'乱', '41de': u'利', '41df': u'裏',
	'41e0': u'離', '41e1': u'率', '41e2': u'立', '41e3': u'竜', '41e4': u'了', '41e5': u'涼', '41e6': u'量', '41e7': u'力', '41e8': u'緑', '41e9': u'類',
	
	'41ea': u'冷', '41eb': u'烈', '41ec': u'裂', '41ed': u'恋', '41ee': u'練', '41ef': u'連', '41f0': u'路', '41f1': u'楼', '41f2': u'録', '41f3': u'惑',
	'41f4': u'慄'

	}
	# Info on finding/editing the in-game textures for these characters can be found here:
	# 	https://smashboards.com/threads/changing-menu-text.368452/page-2#post-21591476