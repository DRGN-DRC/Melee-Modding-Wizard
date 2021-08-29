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

""" Container for global data that all scripts may access. 
	Contains settings, settings-related load/save functions, and look-up tables. """

programVersion = '0.8.8'

# External Dependencies
import os
import csv
#import enum
import ConfigParser
import tkMessageBox
import Tkinter as Tk

from datetime import datetime
from collections import OrderedDict

# Internal Dependencies
import disc
import codeRegionSettings

#from disc import MicroMelee, isExtractedDirectory
from codeMods import CommandProcessor
from basicFunctions import msg, printStatus
from guiSubComponents import PopupEntryWindow, VanillaDiscEntry


def init( programArgs ):

	global scriptHomeFolder, paths, defaultSettings, defaultBoolSettings, settings, boolSettings
	global overwriteOptions, codeProcessor, gui, disc, codeMods, standaloneFunctions, programEnding

	scriptHomeFolder = os.path.abspath( os.path.dirname(programArgs[0]) ) # Can't use __file__; incompatible with cx_freeze process

	paths = { # Special internal paths (other custom/user paths that should be remembered in the settings file should be in the other two settings dicts)
		'fontsFolder': os.path.join( scriptHomeFolder, 'fonts' ),
		'imagesFolder': os.path.join( scriptHomeFolder, 'imgs' ),
		'tempFolder': os.path.join( scriptHomeFolder, 'bin', 'tempFiles' ),
		'settingsFile': os.path.join( scriptHomeFolder, 'settings.ini' ),
		'meleeMedia': os.path.join( scriptHomeFolder, 'bin', 'MeleeMedia', 'MeleeMedia.exe' ),
		'microMelee': os.path.join( scriptHomeFolder, 'bin', 'Micro Melee.iso' ),
		'eabi': os.path.join( scriptHomeFolder, 'bin', 'eabi' ),
		'coreCodes': os.path.join( scriptHomeFolder, 'bin', 'Core Codes' ),
	}

	# These are default settings if they are not defined in the user's settings.ini file
	defaultSettings = {
		#'defaultSearchDirectory': os.path.expanduser( '~' ),
		'codeLibraryPath': os.path.join( scriptHomeFolder, 'Code Library' ),
		'codeLibraryIndex': '0',
		'vanillaDiscPath': '',
		'hexEditorPath': '',
		'emulatorPath': '',
		'maxFilesToRemember': '7',
		'paddingBetweenFiles': '0x40',
	}
	defaultBoolSettings = { # Same as above, but for bools, which are initialized slightly differently (must be strings of 0 or 1!)
		'useDiscConvenienceFolders': '1',
		'backupOnRebuild': '1',
		'alwaysEnableCrashReports': '1',
		'alwaysAddFilesAlphabetically': '0',
		'exportDescriptionsInFilename': '1',
	}
	# regionOverwriteDefaults = {
	# 	'Common Code Regions': True,
	# 	'20XXHP 4.07 Regions': False,
	# 	'20XXHP 5.0 Regions': False,
	# 	'Tournament Mode Region'
	# }

	settings = ConfigParser.SafeConfigParser()
	settings.optionxform = str # Tells the settings parser to preserve case sensitivity
	boolSettings = {}
	overwriteOptions = OrderedDict() # For code-based mods. Populates with key=customCodeRegionName, value=BooleanVar (to describe whether the regions should be used.)
	
	codeProcessor = CommandProcessor() # Must be initialized after gettings general settings, so the base include paths are set correctly

	gui = None
	disc = None

	codeMods = []
	standaloneFunctions = {} # Key='functionName', value=( functionRamAddress, functionCustomCode, functionPreProcessedCustomCode )

	programEnding = False


def checkSetting( settingName ):

	""" Used for checking general settings and bools. """

	# Make sure there are no naming conflicts
	if settingName in defaultSettings and settingName in defaultBoolSettings:
		raise Exception( 'Setting {} defined as both a regular setting and bool setting!'.format(settingName) )

	elif settingName in defaultSettings: # Not a bool or region overwrite setting
		return settings.get( 'General Settings', settingName )

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
		print 'Unable to find region in region overwrite options:', regionName
		return False

	elif isinstance( boolSetting, Tk.BooleanVar ):
		return boolSetting.get()
	else:
		return boolSetting


def loadProgramSettings( useBooleanVars=False ):

	""" Check for user defined settings / persistent memory, from the "settings.ini" file. 
		If values don't exist in it for particular settings, defaults are loaded from the global 'defaultSettings' dictionary. 
		This is preferred over having a default file already created to contain the settings so that the file may be deleted, 
		either to reset all defaults, or re-create the file in case of potential corruption. 
		Usage of BooleanVars can only be done in the presence of the GUI. """

	#settings = globalData.settings

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


def saveProgramSettings():

	""" Saves the current program settings to the "settings.ini" file. This will update a pre-existing settings file, 
		or will create a new one if it doesn't already exist. 

		String and alphanumeric settings are kept in the global settings object, while booleans 
		are kept in the boolSettings dictionary, as BooleanVar objects, so that they can easily be 
		kept in sync with the GUI. Therefore they need to be combined with the settings object before saving. """

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
			if ext == '.iso' or ext == '.gcm' or disc.isExtractedDirectory( filepath.replace('|', ':'), showError=False ): 
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


def setLastUsedDir( savePath, category='default', saveSettings=True ):
	
	""" Normalizes the give path (and converts to a folder path if a file path was given) 
		and sets it as the default program directory. This can be used on a per-file-type 
		basis; for example, a last used dir for discs, or a last used dir for music files. 
		If category is not given, "default" will be used. However, this should be avoided. """

	# Get the folder path if this is a path to a file
	if not os.path.isdir( savePath ):
		# Try to determine the category by the file extension
		if category == 'auto':
			fileExt = os.path.splitext( savePath )[1].replace( '.', '' )

			if fileExt in ( 'hps', 'wav', 'dsp', 'mp3', 'aiff', 'wma', 'm4a' ):
				category = 'hps'
			elif fileExt in ( 'iso', 'gcm' ):
				category = 'iso'
			elif fileExt.endswith( 'at' ) or fileExt.endswith( 'sd' ): # To match .dat/.usd as well as .0at/etc variants
				category = 'dat'
			elif fileExt in ( 'mth', 'thp' ): # Video files
				category = 'mth'
			else:
				category = 'default'

		savePath = os.path.dirname( savePath )

	# Normalize the path and make sure it's composed of legal characters
	savePath = os.path.normpath( savePath ).encode( 'utf-8' ).strip()

	# Save a default directory location for this specific kind of file
	category = category.replace( '.', '' ).lower()
	settings.set( 'Default Search Directories', category, savePath )
	settings.set( 'Default Search Directories', 'lastCategory', category )

	if saveSettings: # Should be avoided in some cases where it's redundant
		saveProgramSettings()


def getLastUsedDir( category='default' ):

	""" Fetches the default directory to start in for file/folder operations. 
		Can use the "category" argument to retrieve for a specific type or 
		class of files; e.g. for "dat" or "disc". """

	# If no category is specified, use the last saved directory out of all of them
	if category == 'default':
		category = settings.get( 'Default Search Directories', 'lastCategory' )

	# Get a default directory location for this specific type of file
	try:
		directoryPath = settings.get( 'Default Search Directories', category.replace( '.', '' ).lower() )
	except ConfigParser.NoOptionError:
		directoryPath = settings.get( 'Default Search Directories', 'default' )

	return directoryPath


def rememberFile( filepath, updateDefaultDirectory=True ):

	""" Adds a filepath to the settings object's "Recent Files" section, so it can be recalled later 
		from the 'Open Recent' menu option (removing the oldest file if the max files to remember has 
		been reached). The settings are then saved to the settings file. """

	 # Normalize input (collapse redundant separators, and ensure consistent slash direction)
	filepath = os.path.normpath( filepath )
	
	# Remove the oldest file entry if the max number of files to remember has already been reached
	if settings.has_section( 'Recent Files' ):
		# Get the current lists of recent ISOs and recent DAT (or other) files
		ISOs, DATs = getRecentFilesLists()

		# For the current filetype, arrange the list so that the oldest file is first, and then remove it from the settings file.
		extension = os.path.splitext( filepath )[1].lower()
		if extension == '.iso' or extension == '.gcm' or disc.isExtractedDirectory( filepath, showError=False ): targetList = ISOs
		else: targetList = DATs
		targetList.sort( key=lambda recentInfo: recentInfo[1] )

		# Remove the oldest file(s) from the settings file until the specified max number of files to remember is reached.
		while len( targetList ) > int( settings.get( 'General Settings', 'maxFilesToRemember' ) ) - 1:
			settings.remove_option( 'Recent Files', targetList[0][0] )
			targetList.pop( 0 )
	else:
		settings.add_section('Recent Files')

	# Update the default search directory.
	if updateDefaultDirectory:
		if extension == '.iso' or extension == '.gcm':
			setLastUsedDir( filepath, 'iso', False )
		else:
			setLastUsedDir( filepath, 'dat', False )

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

	if not os.path.exists( emulatorPath ):
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

	if not os.path.exists( vanillaDiscPath ):
		message = ( 'Please specify the full path to a vanilla NTSC 1.02 SSBM game disc. This path only '
					'needs to be given once, and can be changed at any time in the settings.ini file. '
					"If you have already set this, the path seems to have broken."
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


def getMicroMelee():

	""" Returns a Micro Melee disc object. Either from a pre-built file, 
		or if needed, creates a new one from a vanilla disc. """

	microMeleePath = paths['microMelee']

	# Check if a Micro Melee disc already exists
	if os.path.exists( microMeleePath ):
		print 'using existing MM'
		microMelee = disc.MicroMelee( microMeleePath )
		microMelee.loadGameCubeMediaFile()

	else: # Need to make a new MM build
		vanillaDiscPath = getVanillaDiscPath()
		if not vanillaDiscPath: # User canceled path input
			#gui.updateProgramStatus( 'Unable to build the Micro Melee test disc without a vanilla reference disc.' )
			printStatus( 'Unable to build the Micro Melee test disc without a vanilla reference disc.' )
			return

		microMelee = disc.MicroMelee( microMeleePath )
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


charList = [ # By External Character ID
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


charAbbrList = [ # By External Character ID
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


charColorLookup = { # 12 Unique color slots
	'Aq': 'aqua',
	'Bk': 'black',
	'Br': 'brown', # So far just for Brown Wolf in Mex
	'Bu': 'blue',
	'Gr': 'green',
	'Gy': 'gray',
	'La': 'lavender',
	'Nr': 'neutral',
	'Or': 'orange',
	'Pi': 'pink',
	'Rd': 'red', # Unique to 20XX 4.0+ for Falcon's .usd variation
	'Re': 'red',
	'Rl': 'red', # Unique to 20XX 4.0+ for Falcon's .usd variation (red 'L')
	'Rr': 'red', # Unique to 20XX 4.0+ for Falcon's .usd variation (red 'R')
	'Wh': 'white',
	'Ye': 'yellow'
}


costumeSlots = { # Character Costuems indexed by Costume ID, for each character
	'Ca': ( 'Nr', 'Gy', 'Re', 'Wh', 'Gr', 'Bu' ),
	'Dk': ( 'Nr', 'Bk', 'Re', 'Bu', 'Gr' ),
	'Fx': ( 'Nr', 'Or', 'La', 'Gr' ),
	'Gw': ( 'Nr', ),
	'Kb': ( 'Nr', 'Ye', 'Bu', 'Re','Gr', 'Wh' ),
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


# For the Menu Text Converter:
menuTextDictionary = {

	# Single-Byte Characters
	'1a' : ' ',  '03' : '\n', # Space, and newLine (line break)

	# English numbers & alphabet			Found in Start.dol
	'2000': '0', '2001': '1', '2002': '2', '2003': '3', '2004': '4', '2005': '5', '2006': '6', '2007': '7', '2008': '8', '2009': '9',
	'200a': 'A', '200b': 'B', '200c': 'C', '200d': 'D', '200e': 'E', '200f': 'F', '2010': 'G', '2011': 'H', '2012': 'I', '2013': 'J',
	'2014': 'K', '2015': 'L', '2016': 'M', '2017': 'N', '2018': 'O', '2019': 'P', '201a': 'Q', '201b': 'R', '201c': 'S', '201d': 'T',
	'201e': 'U', '201f': 'V', '2020': 'W', '2021': 'X', '2022': 'Y', '2023': 'Z',
	'2024': 'a', '2025': 'b', '2026': 'c', '2027': 'd', '2028': 'e', '2029': 'f', '202a': 'g', '202b': 'h', '202c': 'i', '202d': 'j',
	'202e': 'k', '202f': 'l', '2030': 'm', '2031': 'n', '2032': 'o', '2033': 'p', '2034': 'q', '2035': 'r', '2036': 's', '2037': 't',
	'2038': 'u', '2039': 'v', '203a': 'w', '203b': 'x', '203c': 'y', '203d': 'z',

	# Japanese Hiragana						Found in Start.dol
	'203e': 'ぁ', '203f': 'あ', '2040': 'ぃ', '2041': 'い', '2042': 'ぅ', '2043': 'う', '2044': 'ぇ', '2045': 'え', '2046': 'ぉ', '2047': 'お', 
	'2048': 'か', '2049': 'が', '204a': 'き', '204b': 'ぎ', '204c': 'く', '204d': 'ぐ', '204e': 'け', '204f': 'げ', '2050': 'こ', '2051': 'ご', 
	'2052': 'さ', '2053': 'ざ', '2054': 'し', '2055': 'じ', '2056': 'す', '2057': 'ず', '2058': 'せ', '2059': 'ぜ', '205a': 'そ', '205b': 'ぞ', 
	'205c': 'た', '205d': 'だ', '205e': 'ち', '205f': 'ぢ', '2060': 'っ', '2061': 'つ', '2062': 'づ', '2063': 'て', '2064': 'で', '2065': 'と', 
	'2066': 'ど', '2067': 'な', '2068': 'に', '2069': 'ぬ', '206a': 'ね', '206b': 'の', '206c': 'は', '206d': 'ば', '206e': 'ぱ', '206f': 'ひ', 
	'2070': 'び', '2071': 'ぴ', '2072': 'ふ', '2073': 'ぶ', '2074': 'ぷ', '2075': 'へ', '2076': 'べ', '2077': 'ぺ', '2078': 'ほ', '2079': 'ぼ', 
	'207a': 'ぽ', '207b': 'ま', '207c': 'み', '207d': 'む', '207e': 'め', '207f': 'も', '2080': 'ゃ', '2081': 'や', '2082': 'ゅ', '2083': 'ゆ', 
	'2084': 'ょ', '2085': 'よ', '2086': 'ら', '2087': 'り', '2088': 'る', '2089': 'れ', '208a': 'ろ', '208b': 'ゎ', '208c': 'わ', '208d': 'を', 
	'208e': 'ん',

	# Japanese Katakana						Found in Start.dol
	'208f': 'ァ', '2090': 'ア', '2091': 'ィ', '2092': 'イ', '2093': 'ゥ', '2094': 'ウ', '2095': 'ェ', '2096': 'エ', '2097': 'ォ', '2098': 'オ', 
	'2099': 'カ', '209a': 'ガ', '209b': 'キ', '209c': 'ギ', '209d': 'ク', '209e': 'グ', '209f': 'ケ', '20a0': 'ゲ', '20a1': 'コ', '20a2': 'ゴ', 
	'20a3': 'サ', '20a4': 'ザ', '20a5': 'シ', '20a6': 'ジ', '20a7': 'ス', '20a8': 'ズ', '20a9': 'セ', '20aa': 'ゼ', '20ab': 'ソ', '20ac': 'ゾ', 
	'20ad': 'タ', '20ae': 'ダ', '20af': 'チ', '20b0': 'ヂ', '20b1': 'ッ', '20b2': 'ツ', '20b3': 'ヅ', '20b4': 'テ', '20b5': 'デ', '20b6': 'ト', 
	'20b7': 'ド', '20b8': 'ナ', '20b9': 'ニ', '20ba': 'ヌ', '20bb': 'ネ', '20bc': 'ノ', '20bd': 'ハ', '20be': 'バ', '20bf': 'パ', '20c0': 'ヒ', 
	'20c1': 'ビ', '20c2': 'ピ', '20c3': 'フ', '20c4': 'ブ', '20c5': 'プ', '20c6': 'ヘ', '20c7': 'ベ', '20c8': 'ペ', '20c9': 'ホ', '20ca': 'ボ', 
	'20cb': 'ポ', '20cc': 'マ', '20cd': 'ミ', '20ce': 'ム', '20cf': 'メ', '20d0': 'モ', '20d1': 'ャ', '20d2': 'ヤ', '20d3': 'ュ', '20d4': 'ユ', 
	'20d5': 'ョ', '20d6': 'ヨ', '20d7': 'ラ', '20d8': 'リ', '20d9': 'ル', '20da': 'レ', '20db': 'ロ', '20dc': 'ヮ', '20dd': 'ワ', '20de': 'ヲ', 
	'20df': 'ン', '20e0': 'ヴ', '20e1': 'ヵ', '20e2': 'ヶ',

	# Punctuation							Found in Start.dol
	'20e3': '　', '20e4': '、', '20e5': '。', # These are the "ideographic"/Japanese space, comma, and period (the space here is not the same space character found under '1a')
	'20e6': ',', '20e7': '.', '20e8': '•', '20e9': ':', '20ea': ';', '20eb': '?', '20ec': '!', '20ed': '^', '20ee': '_', '20ef': '—', # '20ef' is an "em dash" (U+2014)
	'20f0': '/', '20f1': '~', '20f2': '|', '20f3': "'", '20f4': '"', '20f5': '(', '20f6': ')', '20f7': '[', '20f8': ']', '20f9': '{', 
	'20fa': '}', '20fb': '+', '20fc': '-', '20fd': '×', '20fe': '=', '20ff': '<', '2100': '>', '2101': '¥', '2102': '$', '2103': '%', # '20fd' is not simply another x, but a multiplication sign (U+00D7)
	'2104': '#', '2105': '&', '2106': '*', '2107': '@',

	# Japanese Kanji						Group 1, Found in Start.dol
	'2108': '扱', '2109': '押', '210a': '軍', '210b': '源', '210c': '個', '210d': '込', '210e': '指', '210f': '示', '2110': '取', '2111': '書',
	'2112': '詳', '2113': '人', '2114': '生', '2115': '説', '2116': '体', '2117': '団', '2118': '電', '2119': '読', '211a': '発', '211b': '抜',
	'211c': '閑', '211d': '本', '211e': '明',

	# Misc Items, Set 1						Found in SdMenu.usd				(Only accessible if the game is set to English)
	#'4000': 'é', '4001': '〇', '4002': 'Ⅱ', '4003': '王', '4004': '国', '4005': '山', '4006': '頂', 	# 4002 seems to be a Roman numeral 2

	# Misc Items, Set 2						Found in SdMenu.dat				(Only accessible if the game is set to Japanese)
	'4000': '々', '4001': '「', '4002': '」', '4003': '『', '4004': '』', '4005': '♂', '4006': '♀', '4007': '〇', '4008': '→', '4009': 'Ⅱ', # The corner brackets are quotation marks in East Asian languages

	# Japanese Kanji						Group 2, Found in SdMenu.dat 	(Only accessible if the game is set to Japanese)
	'400a': '亜', '400b': '暗', '400c': '以', '400d': '位', '400e': '意', '400f': '医', '4010': 'ー', '4011': '員', '4012': '隠', '4013': '右', # 4010 may instead be 一
	'4014': '宇', '4015': '影', '4016': '映', '4017': '液', '4018': '越', '4019': '円', '401a': '援', '401b': '演', '401c': '炎', '401d': '遠',
	'401e': '奥', '401f': '応', '4020': '横', '4021': '王', '4022': '屋', '4023': '俺', '4024': '音', '4025': '下', '4026': '化', '4027': '仮',

	'4028': '何', '4029': '価', '402a': '加', '402b': '可', '402c': '果', '402d': '歌', '402e': '花', '402f': '課', '4030': '過', '4031': '牙',
	'4032': '画', '4033': '介', '4034': '会', '4035': '解', '4036': '回', '4037': '壊', '4038': '怪', '4039': '悔', '403a': '懐', '403b': '界',
	'403c': '開', '403d': '外', '403e': '崖', '403f': '鎧', '4040': '格', '4041': '獲', '4042': '学', '4043': '楽', '4044': '割', '4045': '活',

	'4046': '巻', '4047': '看', '4048': '管', '4049': '観', '404a': '間', '404b': '含', '404c': '器', '404d': '基', '404e': '期', '404f': '棄',
	'4050': '帰', '4051': '気', '4052': '記', '4053': '貴', '4054': '起', '4055': '技', '4056': '橘', '4057': '客', '4058': '逆', '4059': '久',
	'405a': '仇', '405b': '休', '405c': '宮', '405d': '急', '405e': '球', '405f': '旧', '4060': '牛', '4061': '去', '4062': '巨', '4063': '距',

	'4064': '競', '4065': '共', '4066': '協', '4067': '強', '4068': '恐', '4069': '況', '406a': '狂', '406b': '狭', '406c': '驚', '406d': '玉',
	'406e': '均', '406f': '禁', '4070': '近', '4071': '金', '4072': '銀', '4073': '具', '4074': '空', '4075': '遇', '4076': '群', '4077': '兄',
	'4078': '型', '4079': '形', '407a': '憩', '407b': '系', '407c': '経', '407d': '計', '407e': '軽', '407f': '撃', '4080': '激', '4081': '決',
	
	'4082': '結', '4083': '月', '4084': '剣', '4085': '見', '4086': '険', '4087': '減', '4088': '現', '4089': '限', '408a': '己', '408b': '五',
	'408c': '後', '408d': '語', '408e': '護', '408f': '公', '4090': '功', '4091': '効', '4092': '向', '4093': '好', '4094': '工', '4095': '抗',
	'4096': '攻', '4097': '行', '4098': '鋼', '4099': '降', '409a': '高', '409b': '号', '409c': '合', '409d': '国', '409e': '酷', '409f': '黒',
	
	'40a0': '今', '40a1': '左', '40a2': '差', '40a3': '再', '40a4': '最', '40a5': '歳', '40a6': '祭', '40a7': '細', '40a8': '菜', '40a9': '在',
	'40aa': '坂', '40ab': '咲', '40ac': '作', '40ad': '削', '40ae': '撮', '40af': '殺', '40b0': '参', '40b1': '山', '40b2': '算', '40b3': '残',
	'40b4': '使', '40b5': '刺', '40b6': '四', '40b7': '士', '40b8': '始', '40b9': '姿', '40ba': '子', '40bb': '止', '40bc': '鰤', '40bd': '試',

	'40be': '事', '40bf': '字', '40c0': '持', '40c1': '時', '40c2': '自', '40c3': '失', '40c4': '質', '40c5': '実', '40c6': '写', '40c7': '射',
	'40c8': '捨', '40c9': '者', '40ca': '邪', '40cb': '若', '40cc': '弱', '40cd': '主', '40ce': '守', '40cf': '手', '40d0': '殊', '40d1': '種',
	'40d2': '首', '40d3': '受', '40d4': '収', '40d5': '拾', '40d6': '終', '40d7': '習', '40d8': '襲', '40d9': '集', '40da': '住', '40db': '十',
	
	'40dc': '獣', '40dd': '重', '40de': '出', '40df': '術', '40e0': '瞬', '40e1': '順', '40e2': '初', '40e3': '所', '40e4': '女', '40e5': '除',
	'40e6': '傷', '40e7': '勝', '40e8': '商', '40e9': '小', '40ea': '少', '40eb': '床', '40ec': '晶', '40ed': '消', '40ee': '章', '40ef': '賞',
	'40f0': '上', '40f1': '乗', '40f2': '城', '40f3': '場', '40f4': '常', '40f5': '情', '40f6': '状', '40f7': '心', '40f8': '振', '40f9': '新',
	
	'40fa': '深', '40fb': '真', '40fc': '神', '40fd': '身', '40fe': '辛', '40ff': '進', '4100': '陣', '4101': '水', '4102': '数', '4103': '寸',
	'4104': '世', '4105': '制', '4106': '性', '4107': '成', '4108': '整', '4109': '星', '410a': '声', '410b': '青', '410c': '積', '410d': '切',
	'410e': '接', '410f': '設', '4110': '絶', '4111': '先', '4112': '専', '4113': '戦', '4114': '泉', '4115': '選', '4116': '前', '4117': '然',
	
	'4118': '全', '4119': '狙', '411a': '素', '411b': '組', '411c': '阻', '411d': '壮', '411e': '掃', '411f': '操', '4120': '早', '4121': '祖',
	'4122': '総', '4123': '走', '4124': '送', '4125': '遭', '4126': '像', '4127': '増', '4128': '足', '4129': '速', '412a': '賊', '412b': '族',
	'412c': '続', '412d': '存', '412e': '損', '412f': '他', '4130': '多', '4131': '太', '4132': '打', '4133': '対', '4134': '耐', '4135': '待',
	
	'4136': '態', '4137': '替', '4138': '隊', '4139': '代', '413a': '台', '413b': '大', '413c': '題', '413d': '択', '413e': '脱', '413f': '誰',
	'4140': '短', '4141': '壇', '4142': '弾', '4143': '断', '4144': '段', '4145': '値', '4146': '知', '4147': '地', '4148': '遅', '4149': '蓄',
	'414a': '着', '414b': '中', '414c': '宙', '414d': '丁', '414e': '挑', '414f': '町', '4150': '調', '4151': '跳', '4152': '長', '4153': '頂',
	
	'4154': '鳥', '4155': '直', '4156': '墜', '4157': '追', '4158': '通', '4159': '定', '415a': '底', '415b': '弟', '415c': '抵', '415d': '程',
	'415e': '敵', '415f': '的', '4160': '適', '4161': '鉄', '4162': '天', '4163': '店', '4164': '転', '4165': '点', '4166': '伝', '4167': '殿',
	'4168': '登', '4169': '途', '416a': '度', '416b': '土', '416c': '倒', '416d': '島', '416e': '投', '416f': '盗', '4170': '当', '4171': '討',
	
	'4172': '逃', '4173': '透', '4174': '頭', '4175': '闘', '4176': '動', '4177': '同', '4178': '道', '4179': '得', '417a': '特', '417b': '毒',
	'417c': '内', '417d': '謎', '417e': '二', '417f': '肉', '4180': '日', '4181': '乳', '4182': '入', '4183': '年', '4184': '能', '4185': '破',
	'4186': '敗', '4187': '背', '4188': '輩', '4189': '配', '418a': '倍', '418b': '売', '418c': '博', '418d': '爆', '418e': '箱', '418f': '半',
	
	'4190': '反', '4191': '番', '4192': '彼', '4193': '飛', '4194': '匹', '4195': '必', '4196': '百', '4197': '氷', '4198': '表', '4199': '評',
	'419a': '秒', '419b': '不', '419c': '付', '419d': '婦', '419e': '富', '419f': '負', '41a0': '部', '41a1': '風', '41a2': '復', '41a3': '物',
	'41a4': '分', '41a5': '文', '41a6': '聞', '41a7': '兵', '41a8': '平', '41a9': '並', '41aa': '別', '41ab': '変', '41ac': '編', '41ad': '返',
	
	'41ae': '保', '41af': '歩', '41b0': '報', '41b1': '抱', '41b2': '放', '41b3': '方', '41b4': '法', '41b5': '砲', '41b6': '訪', '41b7': '豊',
	'41b8': '暴', '41b9': '冒', '41ba': '摩', '41bb': '魔', '41bc': '枚', '41bd': '毎', '41be': '満', '41bf': '味', '41c0': '未', '41c1': '密',
	'41c2': '夢', '41c3': '無', '41c4': '名', '41c5': '命', '41c6': '迷', '41c7': '滅', '41c8': '面', '41c9': '猛', '41ca': '木', '41cb': '目',
	
	'41cc': '問', '41cd': '紋', '41ce': '野', '41cf': '役', '41d0': '優', '41d1': '有', '41d2': '由', '41d3': '裕', '41d4': '遊', '41d5': '余',
	'41d6': '与', '41d7': '容', '41d8': '用', '41d9': '要', '41da': '来', '41db': '頼', '41dc': '落', '41dd': '乱', '41de': '利', '41df': '裏',
	'41e0': '離', '41e1': '率', '41e2': '立', '41e3': '竜', '41e4': '了', '41e5': '涼', '41e6': '量', '41e7': '力', '41e8': '緑', '41e9': '類',
	
	'41ea': '冷', '41eb': '烈', '41ec': '裂', '41ed': '恋', '41ee': '練', '41ef': '連', '41f0': '路', '41f1': '楼', '41f2': '録', '41f3': '惑',
	'41f4': '慄'

	}
	# Info on finding/editing the in-game textures for these characters can be found here:
	# 	https://smashboards.com/threads/changing-menu-text.368452/page-2#post-21591476