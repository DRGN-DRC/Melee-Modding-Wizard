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


# External dependencies
import os
import time
import codecs
#import psutil
import subprocess
from ruamel import yaml

# Internal dependencies
import globalData
from basicFunctions import msg, cmdChannel, printStatus
from guiSubComponents import BasicWindow


#class NumberConverter( BasicWindow ):


class ImageDataLengthCalculator( BasicWindow ):

	def __init__( self, root ):
		BasicWindow.__init__( self, root, 'Image Data Length Calculator' )

		# Set up the input elements
		# Width
		ttk.Label( self.window, text='Width:' ).grid( column=0, row=0, padx=5, pady=2, sticky='e' )
		self.widthEntry = ttk.Entry( self.window, width=5, justify='center' )
		self.widthEntry.grid( column=1, row=0, padx=5, pady=2 )
		# Height
		ttk.Label( self.window, text='Height:' ).grid( column=0, row=1, padx=5, pady=2, sticky='e' )
		self.heightEntry = ttk.Entry( self.window, width=5, justify='center' )
		self.heightEntry.grid( column=1, row=1, padx=5, pady=2 )
		# Input Type
		ttk.Label( self.window, text='Image Type:' ).grid( column=0, row=2, padx=5, pady=2, sticky='e' )
		self.typeEntry = ttk.Entry( self.window, width=5, justify='center' )
		self.typeEntry.grid( column=1, row=2, padx=5, pady=2 )
		# Result Multiplier
		ttk.Label( self.window, text='Result Multiplier:' ).grid( column=0, row=3, padx=5, pady=2, sticky='e' )
		self.multiplierEntry = ttk.Entry( self.window, width=5, justify='center' )
		self.multiplierEntry.insert( 0, '1' ) # Default
		self.multiplierEntry.grid( column=1, row=3, padx=5, pady=2 )

		# Bind the event listeners for calculating the result
		for inputWidget in [ self.widthEntry, self.heightEntry, self.typeEntry, self.multiplierEntry ]:
			inputWidget.bind( '<KeyRelease>', self.calculateResult )

		# Set the output elements
		ttk.Label( self.window, text='Required File or RAM space:' ).grid( column=0, row=4, columnspan=2, padx=20, pady=5 )
		# In hex bytes
		self.resultEntryHex = ttk.Entry( self.window, width=20, justify='center' )
		self.resultEntryHex.grid( column=0, row=5, padx=5, pady=5 )
		ttk.Label( self.window, text='bytes (hex)' ).grid( column=1, row=5, padx=5, pady=5 )
		# In decimal bytes
		self.resultEntryDec = ttk.Entry( self.window, width=20, justify='center' )
		self.resultEntryDec.grid( column=0, row=6, padx=5, pady=5 )
		ttk.Label( self.window, text='(decimal)' ).grid( column=1, row=6, padx=5, pady=5 )

	def calculateResult( self, event ):
		try: 
			widthValue = self.widthEntry.get()
			if not widthValue: return
			elif '0x' in widthValue: width = int( widthValue, 16 )
			else: width = int( widthValue )

			heightValue = self.heightEntry.get()
			if not heightValue: return
			elif '0x' in heightValue: height = int( heightValue, 16 )
			else: height = int( heightValue )

			typeValue = self.typeEntry.get()
			if not typeValue: return
			elif '0x' in typeValue: _type = int( typeValue, 16 )
			else: _type = int( typeValue )

			multiplierValue = self.multiplierEntry.get()
			if not multiplierValue: return
			elif '0x' in multiplierValue: multiplier = int( multiplierValue, 16 )
			else: multiplier = float( multiplierValue )

			# Calculate the final amount of space required.
			imageDataLength = hsdStructures.ImageDataBlock.getDataLength( width, height, _type )
			finalSize = int( math.ceil(imageDataLength * multiplier) ) # Can't have fractional bytes, so we're rounding up

			self.resultEntryHex.delete( 0, 'end' )
			self.resultEntryHex.insert( 0, uHex(finalSize) )
			self.resultEntryDec.delete( 0, 'end' )
			self.resultEntryDec.insert( 0, humansize(finalSize) )
		except:
			self.resultEntryHex.delete( 0, 'end' )
			self.resultEntryHex.insert( 0, 'Invalid Input' )
			self.resultEntryDec.delete( 0, 'end' )


class TriCspCreator( object ):

	def __init__( self ):

		self.gimpDir = ''
		self.gimpExe = ''
		self.cspConfig = {}

		# Analyze the version of GIMP installed, and check for needed plugins
		self.determineGimpPath()
		gimpVersion = self.getGimpProgramVersion()
		pluginDir = self.getGimpPluginDirectory( gimpVersion )
		createCspScriptVersion = self.getScriptVersion( pluginDir, 'python-fu-create-tri-csp.py' )
		finishCspScriptVersion = self.getScriptVersion( pluginDir, 'python-fu-finish-csp.py' )
		
		# Print out version info
		print ''
		print '            Version info:'
		print ''
		print '  GIMP:                    ', gimpVersion
		print '  create-tri-csp script:   ', createCspScriptVersion
		print '  finish-csp script:       ', finishCspScriptVersion
		print ''
		print 'GIMP executable directory: ', self.gimpDir
		print 'GIMP Plug-ins directory:   ', pluginDir
		print ''
		
		# Load the CSP Configuration file
		try:
			cspConfigFilePath = os.path.join( globalData.paths['coreCodes'], 'CSP Configuration.yml' )
			with codecs.open( cspConfigFilePath, 'r', encoding='utf-8' ) as stream: # Using a different read method to accommodate UTF-8 encoding
				#cls.yamlDescriptions = yaml.safe_load( stream ) # Vanilla yaml module method (loses comments when saving/dumping back to file)
				self.cspConfig = yaml.load( stream, Loader=yaml.RoundTripLoader )
		except IOError: # Couldn't find the file
			msg( "Couldn't find the CSP config file at " + cspConfigFilePath, warning=True )
		except Exception as err: # Problem parsing the file
			msg( 'There was an error while parsing the yaml config file:\n\n{}'.format(err) )

	def determineGimpPath( self ):

		""" Determines the absolute file path to the GIMP console executable 
			(the exe itself varies based on program version). """
		
		# Check for the expected program folder
		directory = "C:\\Program Files\\GIMP 2\\bin"
		if not os.path.exists( directory ):
			msg( 'GIMP does not appear to be installed; unable to find the GIMP program directory at "{}".'.format(directory) )
			self.gimpDir = ''
			self.gimpExe = ''
			return
		
		# Check the files in the program folder for a 'console' executable
		for fileOrFolderName in os.listdir( directory ):
			if fileOrFolderName.startswith( 'gimp-console' ) and fileOrFolderName.endswith( '.exe' ):
				self.gimpDir = directory
				self.gimpExe = fileOrFolderName
				return

		else: # The loop above didn't break; unable to find the exe
			msg( 'Unable to find the GIMP console executable in "{}".'.format(directory) )
			self.gimpDir = ''
			self.gimpExe = ''
			return

	def getGimpProgramVersion( self ):
		#_, versionText = cmdChannel( 'start /B /D "{}" {} --version'.format(self.gimpDir, self.gimpExe), shell=True )
		_, versionText = cmdChannel( '"{}\{}" --version'.format(self.gimpDir, self.gimpExe) )
		return versionText.split()[-1]
		
	def getGimpPluginDirectory( self, gimpVersion ):

		""" Checks known directory paths for GIMP versions 2.8 and 2.10. If both appear 
			to be installed, we'll check the version of the executable that was found. """

		userFolder = os.path.expanduser( '~' ) # Resolves to "C:\Users\[userName]"
		v8_Path = os.path.join( userFolder, '.gimp-2.8\\plug-ins' )
		v10_Path = os.path.join( userFolder, 'AppData\\Roaming\\GIMP\\2.10\\plug-ins' )

		if os.path.exists( v8_Path ) and os.path.exists( v10_Path ):
			# Both versions seem to be installed. Use Gimp's version to decide which to use
			major, minor, _ = gimpVersion.split( '.' )
			if major != '2':
				return ''
			if minor == '8':
				return v8_Path
			else: # Hoping this path is good for other versions as well
				return v10_Path

		elif os.path.exists( v8_Path ): return v8_Path
		elif os.path.exists( v10_Path ): return v10_Path
		else: return ''

	def getScriptVersion( self, pluginDir, scriptFile ):

		""" Scans the given script (a file name) for a line like "version = 2.2\n" and parses it. """

		scriptPath = os.path.join( pluginDir, scriptFile )

		if os.path.exists( scriptPath ):
			with open( scriptPath, 'r' ) as script:
				for line in script:
					line = line.strip()

					if line.startswith( 'version' ) and '=' in line:
						return line.split( '=' )[-1].strip()
			
		return '-1'


class DolphinController( object ):

	""" Wrapper the Dolphin emulator, to handle starting/stopping 
		the game, file I/O, and option configuration. """

	def __init__( self ):
		self._exePath = ''
		self.rootFolder = ''
		self.userFolder = ''
		self.process = None

	@property
	def exePath( self ):

		""" Set up initial filepaths. This should be done just once, on the first path request. 
			This is not done in the init method because program settings were not loaded then. """

		if self._exePath:
			return self._exePath
		
		self._exePath = globalData.getEmulatorPath()
		self.rootFolder = os.path.dirname( self._exePath )
		self.userFolder = os.path.join( self.rootFolder, 'User' )

		# Make sure that Dolphin is in 'portable' mode
		portableFile = os.path.join( self.rootFolder, 'portable.txt' )
		if not os.path.exists( portableFile ):
			print 'Dolphin is not in portable mode! Attempting to create portable.txt'
			try:
				with open( portableFile, 'w' ) as newFile:
					pass
			except:
				msg( "Dolphin is not in portable mode, and 'portable.txt' could not be created. Be sure that this program "
					 "has write permissions in the Dolphin root directory.", 'Non-portable Dolphin', globalData.gui.root, warning=True )
				return

		if not os.path.exists( self.userFolder ):
			self.start( '' ) # Will open, create the user folder, and close? todo: needs testing
			# time.sleep( 4 )
			# self.stop()

		return self._exePath

	@property
	def isRunning( self ):
		# Check for a running instances of Dolphin
		# for process in psutil.process_iter():
		# 	if process.name() == 'Dolphin.exe':
		# 		process.terminate()
		# 		printStatus( 'Stopped Dolphin process' )
		# 		time.sleep( 3 )
		# 		return True

		# return False
		if not self.process: # Hasn't been started
			return False

		return ( self.process.poll() == None ) # None means the process is still running; anything else is an exit code

	def getVersion( self ):
		
		if not self.exePath:
			return '' # User may have canceled the prompt

		returnCode, output = cmdChannel( '{} --version'.format(self.exePath) )

		if returnCode == 0:
			return output
		else:
			return 'N/A'
	
	def start( self, discObj ):
		
		# Get the path to the user's emulator of choice
		#emulatorPath = globalData.getEmulatorPath() # Will also validate the path

		#print 'is running:', self.isRunning
		if not self.exePath:
			return # User may have canceled the prompt

		# Make sure there are no prior instances of Dolphin running
		if self.isRunning:
			self.stop()

		# print 'Booting', discObj.filePath
		# print 'In', self.exePath
		
		# Send the disc filepath to Dolphin
		# '--exec' loads the specified file. (Using '--exec' because '/e' is incompatible with Dolphin 5+, while '-e' is incompatible with Dolphin 4.x)
		# '--batch' will prevent dolphin from unnecessarily scanning game/ISO directories, and will shut down Dolphin when the game is stopped.
		printStatus( 'Booting in emulator....' )
		if globalData.checkSetting( 'runDolphinInDebugMode' ):
			command = '"{}" --debugger --exec="{}"'.format( self.exePath, discObj.filePath )
		else:
			command = '"{}" --batch --exec="{}"'.format( self.exePath, self.filePath )
		self.process = subprocess.Popen( command, stderr=subprocess.STDOUT, creationflags=0x08000000 )

		#print 'is running:', self.isRunning

	def stop( self ):

		""" Stop an existing Dolphin process that was spawned from this controller. """

		self.process.terminate()
		time.sleep( 3 )