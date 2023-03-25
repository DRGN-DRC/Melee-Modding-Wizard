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

import ttk
import time
import struct
import tkMessageBox
import Tkinter as Tk

from PIL import Image, ImageTk
from binascii import hexlify
from itertools import izip, count
from collections import OrderedDict

# Internal dependencies
import globalData
import codeRegionSettings

from fileBases import FileBase
from codeMods import ConfigurationTypes
from tplCodec import TplDecoder, TplEncoder
from basicFunctions import uHex, toInt, validHex, printStatus, grammarfyList, findAll, msg
from guiSubComponents import BasicWindow


def normalizeRegionString( revisionString ):
	
	""" Should produce something like 'NTSC 1.02', 'PAL 1.00', etc., or 'ALL' 
		from strings that may be a slight variation of this. """

	revisionString = revisionString.upper()
	if 'ALL' in revisionString: return 'ALL'

	# Check for a game/dol version
	verIdPosition = revisionString.find( '.' )
	if verIdPosition == -1: ver = '1.00' # The default assumption
	else: ver = revisionString[verIdPosition-1:verIdPosition+3]

	# Check for the region
	if 'PAL' in revisionString: region = 'PAL '
	else: region = 'NTSC ' # The default assumption

	return region + ver


def parseSettingsFileRegionName( fullRegionName ):

	""" Parses region names specifically from the custom code settings file, 
		and gets their respective regions list. """

	revisionList = []
	regionName = ''

	if '|' in fullRegionName: # Using new naming convention (MCM version 4+); should start with something like 'NTSC 1.02', or 'PAL 1.00', or 'NTSC 1.02, PAL 1.00'
		revisionString, regionName = fullRegionName.split( '|' )
		revisionStringList = revisionString.split( ',' )

		for revisionString in revisionStringList: 
			normalizedRevisionString = normalizeRegionString( revisionString )

			if normalizedRevisionString == 'ALL': 
				revisionList = [ 'ALL' ]
				break
			else:
				revisionList.append( normalizedRevisionString.upper() )

	 # Attempt to match using the old (MCM v3) naming convention
	elif fullRegionName.startswith( 'v10' ):
		revisionList = [ 'NTSC 1.' + fullRegionName[2:4] ]
		regionName = fullRegionName[4:]

	elif fullRegionName.startswith( 'vPAL' ): # Using the old naming convention (MCM version 3.x)
		revisionList = [ 'PAL 1.00' ]
		regionName = fullRegionName[4:]

	elif fullRegionName.startswith( 'vAll' ):
		revisionList = [ 'ALL' ]
		regionName = fullRegionName[4:]

	else: msg( 'Warning! Invalid code region name, "' + fullRegionName + '", defined in the settings.py file.' )

	return revisionList, regionName


class RevisionPromptWindow( BasicWindow ):

	""" Prompts the user to select a DOL region and version (together, these are the dol 'revision'). """

	def __init__( self, labelMessage, regionSuggestion='', versionSuggestion='' ):
		BasicWindow.__init__( self, globalData.gui.root, 'Select DOL Revision' )

		regionOptions = [ 'NTSC', 'PAL' ]
		if regionSuggestion not in regionOptions:
			regionOptions.append( regionSuggestion )

		ttk.Label( self.window, wraplength=240, text=labelMessage ).pack( padx=20, pady=12 )

		# Create variables for the region/version details
		self.regionChoice = Tk.StringVar()
		self.versionChoice = Tk.StringVar()
		self.regionChoice.set( regionSuggestion )
		self.versionChoice.set( '1.' + versionSuggestion )
		self.region = self.version = ''

		# Display the input widgets
		inputWrapper = ttk.Frame( self.window )
		Tk.OptionMenu( inputWrapper, self.regionChoice, *regionOptions ).pack( side='left', padx=8 )
		Tk.Spinbox( inputWrapper, textvariable=self.versionChoice, from_=1.0, to=1.99, increment=.01, width=4, format='%1.2f' ).pack( side='left', padx=8 )
		inputWrapper.pack( pady=(0,12) )

		# OK / Cancel buttons
		buttonsWrapper = ttk.Frame( self.window )
		ttk.Button( buttonsWrapper, text='OK', width=16, command=self.confirm ).pack( side='left', padx=8 )
		ttk.Button( buttonsWrapper, text='Cancel', width=16, command=self.close ).pack( side='left', padx=8 )
		buttonsWrapper.pack( pady=(0,12) )
		
		# Force focus away from the parent window and wait until the new window is closed to continue.
		self.window.grab_set()
		globalData.gui.root.wait_window( self.window )

	# Define button functions
	def confirm( self ):
		self.region = self.regionChoice.get()
		self.version = self.versionChoice.get()
		self.window.destroy()


class Dol( FileBase ):

	""" File object for the main game executable code. """

	def __init__( self, *args, **kwargs ):
		FileBase.__init__( self, *args, **kwargs )
		
		self.region = ''
		self.version = ''
		self.revision = ''
		self.isMelee = False 					# Will only be true for Super Smash Bros. Melee
		self.is20XX = ''						# Will be a string such as '4.07++'/'5.0.0', but may still be evaluated as a bool
		self.sectionInfo = OrderedDict()		# Will be a dict of key='text0', value=( fileOffset, memAddress, size )
		self.maxDolOffset = -1
		self.maxRamAddress = -1
		self.customCodeRegions = OrderedDict()

		self._musicFilePointers = ()
		self._stageInfoStructPointers = ()
		# self._externalCodelistData = ()
		# self._externalInjectionData = ()

		self.project = -1
		self.major = -1
		self.minor = -1
		self.patch = -1

	def load( self ):

		# Skip this method if the file has already been loaded
		if self.sectionInfo:
			return

		# Load the file's binary from disc or standalone file
		self.getData()

		# Check if this is a revision of Super Smash Bros. Melee for the Nintendo GameCube (includes check for 20XX HP)
		self.checkIfMelee()
		if self.isMelee:
			self.checkIf20XX()

		# If not found above, check for DOL revision (region + version). This will prompt the user if it cannot be determined.
		if not self.region or not self.version:
			self.getDolVersion()

		if ( self.region == 'NTSC' or self.region == 'PAL' ) and '.' in self.version: 
			self.revision = self.region + ' ' + self.version

		self.parseHeader()
		self.loadCustomCodeRegions()

		# Load program settings pertaining to allowable region overwrites
		if globalData.gui:
			globalData.loadRegionOverwriteOptions( True )
		else: # Load without booleanVars
			globalData.loadRegionOverwriteOptions( False )

	# def validate( self ):


	def parseHeader( self ):

		self.maxDolOffset = 0
		self.maxRamAddress = 0

		# Unpack data for text sections (3 regions of 0x1C bytes each)
		textFileOffsets = struct.unpack( '>7I', self.data[:0x1C] )
		textMemAddresses = struct.unpack( '>7I', self.data[0x48:0x64] )
		textSizes = struct.unpack( '>7I', self.data[0x90:0xAC] )

		# Unpack data for data sections (3 regions of 0x2C bytes each)
		dataFileOffsets = struct.unpack( '>11I', self.data[0x1C:0x48] )
		dataMemAddresses = struct.unpack( '>11I', self.data[0x64:0x90] )
		dataSizes = struct.unpack( '>11I', self.data[0xAC:0xD8] )

		self.bssMemAddress, self.bssSize, self.entryPoint = struct.unpack( '>III', self.data[0xD8:0xE4] )

		# Assemble text section tuples, and check for max file offsets and ram addresses
		for i, fileOffset, memAddress, size in izip( count(), textFileOffsets, textMemAddresses, textSizes ):
			# If any of the above values are 0, there are no more sections
			if fileOffset == 0 or memAddress == 0 or size == 0: break
			
			self.sectionInfo['text'+str(i)] = ( fileOffset, memAddress, size )

			# Find the max possible dol offset and ram address for this game's dol
			if fileOffset + size > self.maxDolOffset: self.maxDolOffset = fileOffset + size
			if memAddress + size > self.maxRamAddress: self.maxRamAddress = memAddress + size

		# Assemble data section tuples, and check for max file offsets and ram addresses
		for i, fileOffset, memAddress, size in izip( count(), dataFileOffsets, dataMemAddresses, dataSizes ):
			# If any of the above values are 0, there are no more sections
			if fileOffset == 0 or memAddress == 0 or size == 0: break
			
			self.sectionInfo['data'+str(i)] = ( fileOffset, memAddress, size )

			# Find the max possible dol offset and ram address for this game's dol
			if fileOffset + size > self.maxDolOffset: self.maxDolOffset = fileOffset + size
			if memAddress + size > self.maxRamAddress: self.maxRamAddress = memAddress + size

	def checkIfMelee( self ):
		
		""" Checks the DOL for a string of "Super Smash Bros. Melee" at specific locations (for various game versions). """

		self.isMelee = True
		ssbmStringBytes = bytearray( b"Super Smash Bros. Melee" )

		if self.data[0x3B78FB:0x3B7912] == ssbmStringBytes: self.region = 'NTSC'; self.version = '1.02' # most common, so checking for it first
		elif self.data[0x3B6C1B:0x3B6C32] == ssbmStringBytes: self.region = 'NTSC'; self.version = '1.01'
		elif self.data[0x3B5A3B:0x3B5A52] == ssbmStringBytes: self.region = 'NTSC'; self.version = '1.00'
		elif self.data[0x3B75E3:0x3B75FA] == ssbmStringBytes: self.region = 'PAL'; self.version = '1.00'
		else: 
			self.region = self.version = ''
			self.isMelee = False

	def checkIf20XX( self ):

		""" 20XX has a version string in the DOL at 0x0x3F7158, preceded by an ASCII string of '20XX'.
			Versions up to 4.07++ used an ASCII string for the version as well (v4.07/4.07+/4.07++ have the same string).
			Starting with v5 there's a new method of 'project code, major version, minor version, and patch' (one byte each). """

		# Check for the '20XX' string
		if self.data[0x3F7154:0x3F7158] != bytearray( b'\x32\x30\x58\x58' ):
			self.is20XX = ''
			return

		versionData = self.data[0x3F7158:0x3F715C]
		
		# Check if using the new v5+ format
		if versionData[0] == 0:
			self.project, self.major, self.minor, self.patch = struct.unpack( 'BBBB', versionData )
			self.is20XX = '{}.{}.{}'.format( self.major, self.minor, self.patch )
		
		else: # Using the old string format, with just major and minor
			self.is20XX = versionData.decode( 'ascii' )
			self.project = 0

			# Parse out major/minor versions
			major, minor = self.is20XX.split( '.' )
			self.major = int( major )
			self.minor = int( minor )

			# May be able to be more accurate
			if self.is20XX == '4.07' and len( self.data ) == 0x438800 and self.data[-4:] == bytearray( b'\x00\x43\x88\x00' ):
				self.is20XX = '4.07++'
				self.patch = 2
			else:
				self.patch = 0

	def getDolVersion( self ):

		""" Checks the game version of the DOL by checking a custom string within the DOL's header, the 
			name of the file, or by prompting the user (using disc region and version as predictors). """

		# The range 0xE4 to 0x100 in the DOL is normally unused padding. This is used to specify DOL revision. (last 4 bytes are for project version)
		customVersionString = self.data[0xE4:0x100].split(b'\x00')[0].decode( 'ascii' )

		# If a custom string exists, validate and use that, or else prompt the user (using disc region/version for predictors)
		if customVersionString and ' ' in customVersionString: # Highest priority for determining version
			apparentRegion, apparentVersion = normalizeRegionString( customVersionString ).split() # Should never return 'ALL' in this case

			if ( apparentRegion == 'NTSC' or apparentRegion == 'PAL' ) and apparentVersion.find( '.' ) != -1:
				print( 'DOL revision determined from metadata: {} {}'.format(self.region, self.version) )
				self.region, self.version = apparentRegion, apparentVersion
		
		if self.region and self.version:
			return

		# Attempt to predict details based on the disc, if present
		regionSuggestion = 'NTSC'
		versionSuggestion = '02'
		
		if self.disc:
			# Try looking at the region code in the Game ID (See here for more info on region code: https://wiki.dolphin-emu.org/index.php?title=GameIDs#Region_Code)
			if self.disc.gameId[3] in ( 'A', 'E', 'J', 'K', 'R', 'W' ):
				regionSuggestion = 'NTSC'
			else:
				regionSuggestion = 'PAL'

			versionSuggestion = '{:02}'.format( self.disc.version )

			userMessage = ( "The revision of the DOL within this disc is being predicted from the disc's details. Please verify them below. "
							"(If this disc has not been altered, these predictions can be trusted.)" )
		else:
			userMessage = "This DOL's revision could not be determined. Please select a region and game version below."
		userMessage += ' Note that codes may not be able to be installed or detected properly if these are set incorrectly.'

		# Prompt the user (using the disc region/version above for predictors)
		revisionWindow = RevisionPromptWindow( userMessage, regionSuggestion, versionSuggestion )

		if revisionWindow.region and revisionWindow.version: # Save the user-confirmed revision
			self.region = revisionWindow.region
			self.version = revisionWindow.version
			self.writeMetaData()

			# Write the new DOL data to file/disc
			if self.source == 'file':
				with open( self.extPath, 'wb') as dolBinary:
					dolBinary.write( self.data )
					
			elif self.source == 'disc' and self.offset != 0:
				with open( self.disc.filePath, 'r+b') as isoBinary:
					isoBinary.seek( self.offset )
					isoBinary.write( self.data )

		else: # User canceled
			self.region = regionSuggestion
			self.version = '1.' + versionSuggestion
			msg( 'Without confirmation, the DOL file will be assumed to be ' + self.region + ' ' + self.version + '. '
				 'If this is incorrect, you may run into problems detecting currently installed mods or with adding/removing mods. '
				 'And installing mods may break game functionality.', 'Revision Uncertainty' )

	def writeMetaData( self ):
		
		""" Saves the DOL's determined revision (and the program version used) to the file 
			in an unused area, so that subsequent loads don't have to ask about it. """

		# Create the hex string, [DOL Revision]00[Program Version], and then convert it to bytes
		metaString = ( self.region + ' ' + self.version ).encode( "hex" ) + '00'
		metaString += ( 'MMW v' + globalData.programVersion ).encode( "hex" )
		metaData = bytearray.fromhex( metaString )

		# Ensure the data length never exceeds 0x1C bytes
		if len( metaData ) > 0x1C:
			metaData = metaData[:0x1C]
		else:
			metaData = metaData + bytearray( 0x1C - len(metaData) )

		# Write the string to the file data
		self.data[0xE4:0x100] = metaData
	
	def offsetInRAM( self, dolOffset ):

		""" Converts the given DOL offset (int) to the equivalent location in RAM once the DOL file is loaded. """

		ramAddress = -1

		# Determine which section the DOL offset is in, and then get that section's starting offsets in both the dol and RAM.
		for fileOffset, memAddress, size in self.sectionInfo.values():
			if dolOffset >= fileOffset and dolOffset < (fileOffset + size):
				sectionOffset = dolOffset - fileOffset # Get the offset from the start of the DOL section.
				ramAddress = memAddress + sectionOffset # Add the section offset to the RAM's start point for that section.
				break

		return ramAddress

	def offsetInDOL( self, ramAddress ):

		""" Converts the given integer RAM address (location in memory) to the equivalent DOL file integer offset. """

		dolOffset = -1

		# Determine which section the address belongs in, and then get that section's starting offsets.
		for fileOffset, memAddress, size in self.sectionInfo.values():
			if ramAddress >= memAddress and ramAddress < (memAddress + size):
				sectionOffset = ramAddress - memAddress # Get the offset from the start of the section.
				dolOffset = fileOffset + sectionOffset # Add the section offset to the RAM's start point for that section.
				break

		return dolOffset

	def calcBranchDistance( self, fromDOL, toDOL ):

		""" Calculates the distance from one DOL location to another, accounting 
			for where their respective locations would end up in RAM. """

		start = self.offsetInRAM( fromDOL )
		end = self.offsetInRAM( toDOL )

		if start == -1:
			msg( 'Invalid input for branch calculation: "from" value (' + hex(fromDOL) + ') is out of range.' )
			return -1
		elif end == -1:
			msg( 'Invalid input for branch calculation: "to" value (' + hex(toDOL) + ') is out of range.' )
			return -1
		else:
			return end - start

	def normalizeDolOffset( self, offsetString, returnType='int' ):

		""" Converts a hex offset string to an int, and converts it to a DOL offset if it's a RAM address. 
			Set returnType to "string" (or technically anything else) to get the return value as a string. """

		offsetString = offsetString.replace( '0x', '' ).strip()
		problemDetails = ''
		dolOffset = -1

		if len( offsetString ) == 8 and offsetString.startswith( '8' ): # Must be a RAM address
			address = int( offsetString, 16 )
			if address >= 0x80003100:
				if address < self.maxRamAddress:
					dolOffset = self.offsetInDOL( address )
					
					# Check that the offset was found (it's possible the address is between text/data sections)
					if dolOffset == -1:
						problemDetails = ', because the RAM address does not have an equivalent location in the DOL.'
				else: problemDetails = ', because the RAM address is too big.'
			else: problemDetails = ', because the RAM address is too small.'

			if returnType != 'int' and not problemDetails:
				dolOffset = uHex( dolOffset )

		else: # Appears to already be a DOL offset
			if returnType != 'int': # Already a string; no need for conversion
				dolOffset = '0x' + offsetString.upper()

			else: # Convert to int
				offset = int( offsetString, 16 )
				if offset >= 0x100:
					if offset < self.maxDolOffset: dolOffset = offset
					else: problemDetails = ', because the DOL offset is too big.'
				else: problemDetails = ', because the DOL offset is too small.'

		if problemDetails:
			return -1, 'Problem detected with offset 0x' + offsetString + '; it could not be converted to a DOL offset' + problemDetails

		return dolOffset, ''

	def normalizeRamAddress( self, offsetString, returnType='int' ):

		""" Converts a hex offset string to an int, and converts it to a RAM address if it's a DOL offset. 
			Set returnType to "string" (or technically anything else) to get the return value as a string. """

		offsetString = offsetString.replace( '0x', '' ).strip()
		problemDetails = ''
		ramAddress = -1

		if len( offsetString ) == 8 and offsetString.startswith( '8' ): # Must be a RAM address
			if returnType != 'int': # Already a string; no need for conversion
				ramAddress = '0x' + offsetString.upper()

			else: # Convert to int
				address = int( offsetString, 16 )
				if address >= 0x80003100:
					if address < self.maxRamAddress:
						ramAddress = address
					else: problemDetails = ', because the RAM address is too big.'
				else: problemDetails = ', because the RAM address is too small.'

		else: # Looks like it's a DOL offset; convert it to a RAM address int
			offset = int( offsetString, 16 )
			if offset >= 0x100:
				if offset < self.maxDolOffset:
					ramAddress = self.offsetInRAM( offset )
				else: problemDetails = ', because the DOL offset is too big.'
			else: problemDetails = ', because the DOL offset is too small.'

			if returnType != 'int' and not problemDetails:
				ramAddress = uHex( ramAddress )

		if problemDetails:
			return -1, 'Problem detected while processing the offset 0x' + offsetString + '; it could not be converted to a RAM address' + problemDetails

		return ramAddress, ''

	def getBranchDistance( self, branchBytes ):

		""" Get and return the distance encoded in a standard, unconditional branch command. 
			The input should be 4 bytes. Output is a signed int. """

		# Get the raw branch distance value, and mask out the top byte (opcode and friends) and lower two bits (AA/LK flags)
		rawValue = struct.unpack( '>I', branchBytes )[0]
		branchDistance = rawValue & 0xFFFFFC

		# Apply distance modifiers based on the op code
		opCode = branchBytes[0]
		if opCode == 0x48: pass # Branching forward
		elif opCode == 0x49:
			branchDistance += 0x1000000

		# Move backwards if branching back
		elif opCode == 0x4A:
			branchDistance = -( 0x2000000 - branchDistance )
		elif opCode == 0x4B:
			branchDistance = -( 0x1000000 - branchDistance )
		else:
			raise Exception( 'Invalid input for getBranchDistance (unrecognized opcode):' + hexlify(branchBytes) )

		return branchDistance

	def getBranchTargetDolOffset( self, branchOffset, branchBytes ):

		""" Calculates a target DOL offset for a given branch. """

		branchDistance = self.getBranchDistance( branchBytes )
		ramOffset = self.offsetInRAM( branchOffset )

		return self.offsetInDOL( ramOffset + branchDistance )

	def getIntStageIdFromExt( self, externalStageId ):

		""" Uses the DOL's own "GrInstance" table to convert from external stage ID to internal stage ID. 
			- Table exists @ 803e9960|0x3E6960
			- Indexed by external ID
			- Stride is 0xC
			- Struct values:
				0x0 = internal stage ID
				0x04 = 0
				0x08 = 0 """

		entryOffset = 0x3E6960 + ( externalStageId * 0xC )
		return toInt( self.getData(entryOffset, 4) )

	def getMusicFilename( self, musicId ):

		""" Looks up a music file name (disc file name), using a pointer table at 0x3B9314. 
			Uses the musicId as an index in this table to get a pointer, which points to the 
			string. The table contains 0x63 entries. Note that this method does not handle 
			hex track IDs (bit 0x10000 set), which are not equivalent. """
		
		if musicId < 0 or musicId > 0x62:
			print( 'Invalid music ID given to getMusicFilename(): ' + hex(musicId) )
			return ''

		# Get the pointer for the string name from the pointer table
		if self._musicFilePointers: # These have already been unpacked
			stringAddress = self._musicFilePointers[musicId]
		else:
			namePointerOffset = 0x3B9314 + ( musicId * 4 )
			stringAddress = toInt( self.getData(namePointerOffset, 4) )

		# Convert the pointer (RAM address of the string) to a file offset
		fileOffset = self.offsetInDOL( stringAddress )
		assert fileOffset != -1, "Unable to find a music file name in the DOL for music ID " + hex( musicId )

		# Get and decode the track name string
		nameBytes = self.getData( fileOffset, 0x10 ).split( '\x00' )[0]
		return nameBytes.decode( 'ascii' )

	def getMusicId( self, filename ):

		""" Looks up a song's music ID using the pointer table at 0x3B9314. 
			Searches through the table and looks for the index of the given filename. """

		# Unpack all the pointer values in the table, to improve the loop's efficiency for this and subsequent calls
		if not self._musicFilePointers:
			self._musicFilePointers = struct.unpack( '>99I', self.getData(0x3B9314, 0x63*4) ) # 0x63 = 99

		for pointer in self._musicFilePointers:
			fileOffset = self.offsetInDOL( pointer )
			nameBytes = self.getData( fileOffset, 0x10 ).split( '\x00' )[0]
			if nameBytes.decode( 'ascii' ) == filename:
				return self._musicFilePointers.index( pointer )

		else: # The loop above didn't break; filename not found
			print( 'Dol.getMusicId() unable to look up musicId for "{}"'.format(filename) )
			return -1

	def getStageFileName( self, internalStageId, forceExtension=True, defaultToUsd=True ):

		""" Looks up a stage file name (disc file name), using a pointer table at 0x3DCEDC. 
			The table contains 0x6F (111) entries; though entry 0 is the "Dummy" placeholder, 
			and entries 1, 0x23, and 0x48 onward (to the end of the table) are the "TEST" stage.
			Uses internal stage ID as an index in this table to get a pointer, which points to 
			a structure containing multiple properties of the stage, including a file name pointer. 
			Returns two values: the offset of the file name string in the DOL, and the decoded string. 
			
			Note that for some stages, which have alternate variations based on the game's region 
			(i.e. .usd vs .dat), the file extension will not be included unless forceExtension is True. """

		if internalStageId <= 0 or internalStageId >= 0x6F:
			print( 'Invalid index to stage file name look-up: ' + hex(internalStageId) )
			return -1, ''

		# Unpack all of the pointers to the stage table structs
		if not self._stageInfoStructPointers:
			tic = time.clock()
			pointerTableData = self.getData( 0x3DCEDC, 0x6F*4 )
			self._stageInfoStructPointers = struct.unpack( '>111I', pointerTableData )
			toc = time.clock()
			print( 'time to unpack stage info struct: ' + str(toc-tic) )

		structOffset = self.offsetInDOL( self._stageInfoStructPointers[internalStageId] )

		# Get the offset for the filename string, and the string data
		nameAddress = toInt( self.data[structOffset+8:structOffset+0xC] )
		nameOffset = self.offsetInDOL( nameAddress ) + 1 # Plus 1 to skip past "/" path character

		# Decode and return the file name string
		stringData = self.data[nameOffset:nameOffset+10]
		nameString = stringData.split( '\x00' )[0].decode( 'ascii' )

		# Add a file extension to those that don't have them
		if forceExtension and '.' not in nameString:
			if self.disc and self.disc.countryCode == 1: # Banner file encoding = latin_1
				nameString += '.usd'
			elif self.disc: # Country code must be 0. Banner file encoding = shift_jis
				nameString += '.dat'

			# No disc available to check
			elif defaultToUsd:
				nameString += '.usd'
			else:
				nameString += '.dat'

		return nameOffset, nameString

	def loadCustomCodeRegions( self ):

		""" Loads and validates the custom code regions available for this DOL revision.
			Filters out regions pertaining to other revisions, and those that fail basic validation. """

		incompatibleRegions = []

		# Load all regions (even if disabled in options) applicable to this DOL
		for fullRegionName, regions in codeRegionSettings.customCodeRegions.items():
			revisionList, regionName = parseSettingsFileRegionName( fullRegionName )

			# Check if the region/version of these regions are relavant to the currently loaded DOL revision
			if 'ALL' in revisionList or self.revision in revisionList:

				# Validate the regions; perform basic checks that they're valid ranges for this DOL
				for i, ( regionStart, regionEnd ) in enumerate( regions ):

					# Check that the region start is actually smaller than the region end
					if regionStart >= regionEnd:
						msg( 'Warning! The starting offset for region ' + str(i+1) + ' of "' + regionName + '" for ' + self.revision + ' is greater or '
							 "equal to the ending offset. A region's starting offset must be smaller than the ending offset.", 'Invalid Custom Code Region', error=True )
						incompatibleRegions.append( regionName )
						break

					# Check that the region start is within the DOL's code or data sections
					elif regionStart < 0x100 or regionStart >= self.maxDolOffset:
						print( "Region start (0x{:X}) for {} is outside of the DOL's code/data sections.".format(regionStart, regionName) )
						incompatibleRegions.append( regionName )
						break

					# Check that the region end is within the DOL's code or data sections
					elif regionEnd > self.maxDolOffset:
						print( "Region end (0x{:X}) for {} is outside of the DOL's code/data sections.".format(regionEnd, regionName) )
						incompatibleRegions.append( regionName )
						break

				# Regions validated; allow them to show up in the GUI (Code-Space Options)
				if regionName not in incompatibleRegions:
					self.customCodeRegions[regionName] = regions

		if incompatibleRegions:
			msg( '\nThe following regions are incompatible with the ' + self.revision + ' DOL, because one or both offsets fall '
				 'outside of the offset range of its text/data sections:\n\n\t' + '\n\t'.join(incompatibleRegions) + '\n', error=True )

	def getCustomCodeRegions( self, searchDisabledRegions=False, specificRegion='', useRamAddresses=False ):

		""" This gets the regions defined for custom code use (regions permitted for overwrites) in codeRegionSettings.py. 
			Returned as a list of tuples of the form (regionStart, regionEnd). Note that the region names in the dictionary 
			are not the "full" region names; i.e. they don't include revision. """

		codeRegions = []

		for regionName, regions in self.customCodeRegions.items():

			# Check if this dol region should be included by its BooleanVar option value (or if that's overridden, which is the first check)
			if searchDisabledRegions or globalData.checkRegionOverwrite( regionName ):

				if specificRegion and regionName != specificRegion:
					continue

				elif useRamAddresses:
					for regionStart, regionEnd in regions:
						codeRegions.append( (self.offsetInRAM(regionStart), self.offsetInRAM(regionEnd), regionName) )
				else:
					#codeRegions.extend( regions )
					for regionStart, regionEnd in regions:
						codeRegions.append( (regionStart, regionEnd, regionName) )

				# If only looking for a specific revision, there's no need to iterate futher.
				if specificRegion: break

		return codeRegions
		
	def regionsOverlap( self, regionList ):

		""" Checks given custom code regions to make sure they do not overlap one another. 
			Presents a warning message pop-up to the user if an overlap is detected. 
			Returns True/False on whether the regions overlap. """

		overlapDetected = False

		# Compare each region to every other region
		for i, ( regionStart, regionEnd, regionName ) in enumerate( regionList, start=1 ):

			# Loop over the remaining items in the list (starting from second entry on first iteration, third entry from second iteration, etc),
			# so as not to compare to itself, or make any repeated comparisons.
			for nextRegionStart, nextRegionEnd, nextRegionName in regionList[i:]:
				# Check if these two regions overlap by any amount
				if nextRegionStart < regionEnd and regionStart < nextRegionEnd: # The regions overlap by some amount.
					overlapDetected = True

					rS = self.offsetInDOL( regionStart )
					rE = self.offsetInDOL( regionEnd )
					nrs = self.offsetInDOL( nextRegionStart )
					nre = self.offsetInDOL( nextRegionEnd )

					# Determine the names of the overlapping regions, and report this to the user
					msg( 'Warning! One or more regions enabled for custom code overlap each other. The first overlapping areas detected '
						'are {} and {}; i.e. (0x{:X}, 0x{:X}) and (0x{:X}, 0x{:X}). '.format( regionName, nextRegionName, rS, rE, nrs, nre ) + \
						'(There may be more; resolve this case and try again to find others.) '
						'\n\nThese regions cannot be used in tandem. In the Code-Space Options window, please choose other regions, '
						'or deselect one of the regions that uses one of the areas shown above.', 'Region Overlap Detected' )
					break

			if overlapDetected: break

		return overlapDetected

	def offsetInEnabledRegions( self, dolOffset ):
		
		""" Checks if a DOL offset falls within an area reserved for custom code. 
			Returns a tuple of ( bool:inEnabledRegion, string:regionNameFoundIn ) """
			
		inEnabledRegion = False
		regionNameFoundIn = ''

		for regionName, regions in self.customCodeRegions.items():
			# Scan the regions for the offset
			for regionStart, regionEnd in regions:
				if dolOffset < regionEnd and dolOffset >= regionStart: # Target region found

					if not inEnabledRegion:
						inEnabledRegion = globalData.checkRegionOverwrite( regionName )
						regionNameFoundIn = regionName
					# In a perfect world, we could break from the loop here, but it may still 
					# be in another region that is enabled (i.e. there's some region overlap).

		return ( inEnabledRegion, regionNameFoundIn )

	@staticmethod
	def getOptionWidth( optionType ):

		""" Returns how many bytes a configuration option of the given type is expected to fill. """

		if optionType.endswith( '32' ) or optionType == 'float':
			return 4
		elif optionType.endswith( '16' ):
			return 2
		elif optionType.endswith( '8' ):
			return 1
		else:
			return -1

	def findCustomCode( self, mod, codeChange, searchArea ):

		""" Searches for custom code from the given code change within the given search area (code from 
			custom code regions) and returns the offset of matching code. This is used to search for Gecko 
			codes and standalone functions, since we won't have a branch to locate them. """
		
		customCode = codeChange.preProcessedCode
		if not customCode: # Pre-processing may have failed
			return -1
		
		# If no custom syntax is used in this code, check for it as one block
		elif not codeChange.syntaxInfo:
			matches = findAll( searchArea, bytearray.fromhex(customCode), charIncrement=1 ) # charIncrement set to 1 in order to increment by byte
			
			if matches:
				if len( matches ) > 1:
					print( 'Warning: Found multiple matches of {} code change at {}.'.format(mod.name, codeChange.offset))
				return matches[0]
			else:
				return -1

		# Check for blocks of code separated by custom syntaxes
		readOffset = 0
		for syntaxOffset, length, _, _, _ in codeChange.syntaxInfo:

			# Check for and process custom code preceding this custom syntax instance
			if readOffset != syntaxOffset:
				sectionLength = syntaxOffset - readOffset
				assert sectionLength > 0, 'Read position error in .findCustomCode()! Read offset: {}, Next syntax offset: {}'.format( readOffset, syntaxOffset )

				codeSection = customCode[readOffset:syntaxOffset]
				
				matches = findAll( searchArea, bytearray.fromhex(codeSection), charIncrement=1 ) # charIncrement set to 1 in order to increment by byte

				# Iterate over the possible locations/matches, and check if each may be the code we're looking for (note that starting offsets will be known in these checks)
				for matchingOffset in matches:
					codeStart = matchingOffset - readOffset # Accomodates for potential preceding special branches

					if self.customCodeInDOL( mod, codeChange, codeStart, searchArea ):
						return codeStart
				else: # Loop above didn't return; no matches for this section found in the given code area
					return -1
			
			readOffset += length

		return 0 # If this is reached, the custom code is entirely special syntaxes; going to have to assume installed. todo: fix

	def customCodeInDOL( self, mod, codeChange, startingOffset, searchArea, excludeLastCommand=False ):

		""" Checks if custom code from the given code change is installed within the given code area. 
			Essentially tries to mismatch any of a code change's custom code with code currently in the DOL. 
			If custom code is mostly or entirely composed of custom syntaxes, we'll have to give it the benefit of the 
			doubt and assume it's installed (since at this point there is no way to know what bytes a custom syntax may resolve to). """

		customCode = codeChange.preProcessedCode
		if not customCode: # Pre-processing may have failed
			return False

		if excludeLastCommand: # Exclude the branch back on injection mods.
			customCode = customCode[:-8] # Removing the last 4 bytes
			codeLength = codeChange.length - 4
		else:
			codeLength = codeChange.length

		# With no custum syntax, there is just one chunk of code to compare
		if not codeChange.syntaxInfo:
			codeInDol = searchArea[startingOffset:startingOffset+codeLength]

			if bytearray.fromhex( customCode ) == codeInDol: # Comparing via bytearrays rather than strings prevents worrying about upper/lower-case
				return True
			else: # Mismatch detected, meaning this is not the same (custom) code in the DOL.
				return False

		readOffset = 0

		for syntaxOffset, length, syntaxType, codeLine, names in codeChange.syntaxInfo:

			# Check for and process custom code preceding this custom syntax instance
			if readOffset != syntaxOffset:
				sectionLength = syntaxOffset - readOffset
				dolCodeStart = startingOffset + readOffset
				dolCodeEnd = dolCodeStart + sectionLength
				assert sectionLength > 0, 'Read position error in .customCodeInDOL()! Read offset: {}, Next syntax offset: {}'.format( readOffset, syntaxOffset )
				
				codeSection = customCode[readOffset*2:syntaxOffset*2] # Splicing a string, so *2 to splice by bytes rather than nibbles
				codeInDol = searchArea[dolCodeStart:dolCodeEnd]
				test = hexlify( codeInDol )

				# Check whether the custom code is in the same as what's currently in the DOL
				if bytearray.fromhex( codeSection ) != codeInDol: # Comparing via bytearrays rather than strings prevents worrying about upper/lower-case
					return False
				else: # Same so far...
					readOffset += sectionLength

			# Skip matching custom syntaxes
			if syntaxType == 'sbs' or syntaxType == 'sym':
				readOffset += 4

			# If this section contains a configuration option, get the current value stored in the DOL
			elif syntaxType == 'opt':
				# If this source custom code is assembly, check bytes from the END of the instruction
				if codeChange.isAssembly:
					valueOffset = startingOffset + syntaxOffset + 4 - length # Need an absolute DOL offset. The option offset is relative to the code start
					readOffset += 4 # Move to the next instruction
				else:
					valueOffset = startingOffset + syntaxOffset # Need an absolute DOL offset. The option offset is relative to the code start
					readOffset += length

				codeInDol = searchArea[valueOffset:valueOffset+length]

				if len( names ) == 1:
					optionDict = mod.getConfiguration( names[0] )
					optType = optionDict['type']
					value = struct.unpack( ConfigurationTypes[optType], codeInDol )[0]
					mod.configure( names[0], value )

				else: # Multiple values were ANDed or ORed into this space
					for name in names:
						optionDict = mod.getConfiguration( name )
						optType = optionDict['type']
						mask = optionDict.get( 'mask' )

						tic = time.clock()

						if mask:
							maskValue = mod.parseConfigValue( optType, mask )
							value = struct.unpack( '>I', codeInDol )[0]
							maskedCodeInDol = struct.pack( '>I', value & maskValue )
							value = struct.unpack( ConfigurationTypes[optType], maskedCodeInDol )[0]
						else:
							value = struct.unpack( ConfigurationTypes[optType], codeInDol )[0]
							
						toc = time.clock()

						mod.configure( name, value )
						
						print( 'method 1 value: ', value )
						print( 'in', toc-tic )
						
						tic = time.clock()

						if mask:
							maskValue = mod.parseConfigValue( optType, mask )
							maskBytes = struct.pack( ConfigurationTypes[optType], maskValue )
						
							i = 0
							for dolByte, maskByte in zip( codeInDol, maskBytes ):
								codeInDol[i] = dolByte & maskByte
								i += 1
						
						value = struct.unpack( ConfigurationTypes[optType], codeInDol )[0]
						
						toc = time.clock()
						print( 'method 2 value: ', value )
						print( 'in', toc-tic )

				#readOffset += length

			# else:
			# 	sectionLength = len( section ) / 2
			# 	codeInDol = searchArea[readOffset:readOffset+sectionLength]

			# 	if bytearray.fromhex( section ) != codeInDol: # Comparing bytearrays rather than strings prevents worrying about upper/lower-case
			# 		matchOffset = -1
			# 		break # Mismatch detected, meaning this is not the same (custom) code in the DOL.
			# 	else:
			# 		readOffset += sectionLength

		# Test last section (or whole section if there was no custom syntax)
		if readOffset != codeLength:
			codeSection = customCode[readOffset*2:] # Splicing a string, so *2 to splice by bytes rather than nibbles
			sectionLength = len( codeSection ) / 2
			dolCodeStart = startingOffset + readOffset
			dolCodeEnd = dolCodeStart + sectionLength

			codeInDol = searchArea[dolCodeStart:dolCodeEnd]

			# Check whether the custom code is in the same as what's currently in the DOL
			if not bytearray.fromhex( codeSection ) == codeInDol: # Comparing via bytearrays rather than strings prevents worrying about upper/lower-case
				return False

		return True

	def checkForEnabledCodes( self, modsToCheckFor ):

		""" Checks the currently loaded DOL file for which mods are installed, and sets their states accordingly.
			'userPromptedForGeckoUsage' will only come into play if there are Gecko codes detected as installed. """

		self.load()

		#clearSummaryTab() # Clears the summary tab's lists of installed mods/SFs.
		codeRegions = self.getCustomCodeRegions()

		# Preliminary attempts to get injection code and gecko code data external to the dol (from gecko.bin/codes.bin)
		# self._externalCodelistData = self.disc.getGeckoData()
		# self._externalInjectionData = self.disc.getInjectionData()

		standaloneFunctionsInstalled = set()
		functionOnlyModules = [] # Remember some info on modules composed of only standalone functions
		requiredDisabledRegions = []
		
		tic = time.clock()

		# Primary Mod-Detection pass. Set the state (highlighting & notes) of each module based on whether its codes are found in the DOL.
		for mod in modsToCheckFor:
			mod.setCurrentRevision( self.revision )
			# Cancel this scan if a new scan of the Mods Library is queued
			# if modsLibraryNotebook.stopToRescan: 
			# 	break

			# Skip unavailable non-gecko mods (gecko mods are a special case, to be re-evaluated)
			#if mod.state == 'unavailable' and mod.type != 'gecko':
			if mod.state == 'unavailable':
				continue

			# Disable mods with problems
			elif mod.assemblyError or mod.parsingError:
				mod.state = 'unavailable'
				continue

			# Disable mods that are not applicable to the currently loaded DOL
			elif self.revision not in mod.data:
				mod.state = 'unavailable'
				continue

			# Determine if the mod is in the DOL, and set the state of the module respectively.
			included = True
			functionsOnly = True
			functionsIncluded = []
			summaryReport = [] # Used to track and report installation locations/offsets to the Summary tab

			for codeChange in mod.getCodeChanges():
				if functionsOnly and not codeChange.type == 'standalone':
					functionsOnly = False

				# Convert the offset to a DOL Offset integer (even if it was a RAM Address)
				if codeChange.type != 'standalone' and codeChange.type != 'gecko':
					offset, errorMsg = self.normalizeDolOffset( codeChange.offset )

					# Validate the offset
					if offset == -1:
						userMessage = 'A problem was detected with an offset, {}, for the mod "{}";{}'.format( codeChange.offset, mod.name, errorMsg.split(';')[1] )
						msg( userMessage, 'Invalid DOL Offset or RAM Address', error=True )
						mod.parsingError = True
						mod.stateDesc = 'Parsing error; bad offset: {}'.format( codeChange.offset )
						included = False
						break

					# Validate the original game code, removing whitespace if necessary
					# elif not validHex( codeChange.origCode ):
					# 	# Get rid of whitepace and try it again
					# 	codeChange.origCode = ''.join( codeChange.origCode.split() )

					# 	if not validHex( codeChange.origCode ):
					# 		msg( 'A problem was detected with the mod "' + mod.name + '"; it appears that one of its static overwrites '
					# 			'or injection points contains invalid hex (or could not be assembled). It will be assumed that this mod is disabled.' )
					# 		included = False
					# 		break # Even though there is "if not included: break" at the end of this loop, this is still needed here to prevent checking the next if block

				if codeChange.type == 'static':
					codeChange.evaluate()

					# Check whether the vanilla hex for this code change matches what's in the DOL
					# matchOffset = self.customCodeInDOL( mod, codeChange, offset, self.data )
					# if matchOffset == -1: included = False
					if not self.customCodeInDOL( mod, codeChange, offset, self.data ):
						included = False
					else:
						# Check whether this overwrite would land in an area reserved for custom code. If so, assume it should be disabled.
						for codeRegion in codeRegions:
							if offset >= codeRegion[0] and offset < codeRegion[1]:
								included = False
								break
						else: # loop above didn't break; all checks out
							summaryReport.append( ('Code overwrite', codeChange.type, offset, codeChange.length) ) # changeName, changeType, dolOffset, changeLength

				elif codeChange.type == 'injection':
					codeChange.evaluate()

					# Test the injection point against the original, vanilla game code.
					injectionPointCode = self.data[offset:offset+4]

					if injectionPointCode == bytearray.fromhex( codeChange.origCode ):
						included = False

					elif injectionPointCode[0] not in ( 0x48, 0x49, 0x4A, 0x4B ):
						included = False # Not a branch added by MCM! Something else must have changed this location.

					else: # Look's like there's a branch at the injection site (and it isn't original hex). Check to see if it leads to the expected custom code.
						customCodeOffset = self.getBranchTargetDolOffset( offset, injectionPointCode )

						inEnabledRegion, regionNameFoundIn = self.offsetInEnabledRegions( customCodeOffset )

						if inEnabledRegion:
							if not self.customCodeInDOL( mod, codeChange, customCodeOffset, self.data, excludeLastCommand=True ): #todo narrow search field to improve performance?
								included = False
							else:
								# Remember where this code change is for a summary on this mod's installation
								summaryReport.append( ('Branch', 'static', offset, 4) ) # changeName, changeType, dolOffset, changeLength
								summaryReport.append( ('Injection code', codeChange.type, customCodeOffset, codeChange.length) )

						else:
							included = False
							print( '\nPossible phantom mod; {} may have custom code installed to a disabled region: "{}"'.format(mod.name, regionNameFoundIn) )
							print( 'It was led to by an injection point hex of {} at 0x{:X} which points to DOL offset 0x{:X}'.format(injectionPointCode, offset, customCodeOffset) )

							if regionNameFoundIn != '':
								if regionNameFoundIn not in requiredDisabledRegions:
									requiredDisabledRegions.append( regionNameFoundIn )
							else:
								print( 'Custom code at 0x{:X} seems to be pointing to a region not defined for custom code!'.format(offset) )

				elif codeChange.type == 'gecko':
					codeChange.evaluate()
					# if not gecko.environmentSupported: # These aren't available for this DOL
					# 	included = False
					# if not self._externalCodelistData: # Not installed
					# 	included = False

					# else: # Check if the code is installed (present in the codelist area)
						#matchOffset = self.findCustomCode( mod, codeChange, self._externalCodelistData )

					# Scan all regions for the code (even disabled ones)
					matchOffset = -1
					regionNameFoundIn = ''
					for regionStart, regionEnd, regionNameFoundIn in codeRegions:
						data = self.data[regionStart:regionEnd]
						matchOffset = self.findCustomCode( mod, codeChange, data )

						if matchOffset != -1: # Found a match
							matchOffset += regionStart # Make relative to the start of the DOL file
							break

					if matchOffset != -1: # Found the code installed
						# inEnabledRegion, regionNameFoundIn = self.offsetInEnabledRegions( matchOffset )
						# # Check that it's installed to an enabled region
						# if inEnabledRegion:
						summaryReport.append( ('Gecko code', codeChange.type, matchOffset, codeChange.length) )
						# else:
						# 	included = False
						# 	print( '\nPossible phantom mod; {} may have gecko code installed to a disabled region: "{}"'.format(mod.name, regionNameFoundIn) )

						# 	if regionNameFoundIn != '':
						# 		if regionNameFoundIn not in requiredDisabledRegions:
						# 			requiredDisabledRegions.append( regionNameFoundIn )
						# 	else:
						# 		print( 'Gecko code at 0x{:X} seems to be pointing to a region not defined for custom code!'.format(matchOffset) )
					else:
						included = False

				elif codeChange.type == 'standalone':
					functionsIncluded.append( codeChange.offset ) # The offset will be a name in this case

				if not included:
					break

			# Prepare special processing for the unique case of this module being composed of ONLY standalone functions (at least for this dol revision)
			if functionsOnly:
				functionOnlyModules.append( (mod, functionsIncluded) )
				continue

			# Check that all standalone functions this mod requires are present.
			elif included:
				requiredStandaloneFunctions, missingFunctions = mod.getRequiredStandaloneFunctionNames()

				if missingFunctions:
					included = False
					msg( 'These standalone functions required for "' + mod.name + '" could not be found in the Mods Library:\n\n' + grammarfyList(missingFunctions) )

				elif requiredStandaloneFunctions:
					# First, check whether the required SFs can be found in the enabled custom code regions
					for functionName in requiredStandaloneFunctions:
						functionCodeChange = globalData.standaloneFunctions[ functionName ][1]

						for areaStart, areaEnd, _ in codeRegions:
							matchOffset = self.findCustomCode( mod, functionCodeChange, self.data[areaStart:areaEnd] )

							if matchOffset != -1: # Function found
								summaryReport.append( ('SF: ' + functionName, 'standalone', areaStart + matchOffset, functionCodeChange.length) )
								break

						else: # The loop scanning through the free code regions above didn't break; SF was not found.
							# Check whether the function is in a disabled region
							found = False
							for regionName, regions in self.customCodeRegions.items():
								if globalData.checkRegionOverwrite( regionName ):
									# Scan the regions for the offset
									for regionStart, regionEnd in regions:
										matchOffset = self.findCustomCode( mod, functionCodeChange, self.data[regionStart:regionEnd] )

										if matchOffset != -1: # Function found (in a disabled region!)
											print( 'SF for {}, "{}", found in a disabled region.'.format(mod.name, functionName) )
											if not regionName in requiredDisabledRegions: requiredDisabledRegions.append( regionName )
											found = True
											break
								if found: break

							# Even if found in a disabled region, consider not installed for now. User will be prompted for a rescan if custom code is in disabled regions
							included = False
							break

			if included:
				mod.state = 'enabled'
				standaloneFunctionsInstalled.update( requiredStandaloneFunctions ) # This is a set, so only new names are added.
				#addToInstallationSummary( mod.name, mod.type, summaryReport )

			elif globalData.checkSetting( 'alwaysEnableCrashReports' ) and mod.name == "Enable OSReport Print on Crash":
				# Queue this to be installed
				if mod.state != 'pendingEnable':
					mod.state = 'pendingEnable'

			else:
				# Restore configuration values, as some could have been updated while checking for installation status
				mod.restoreConfigDefaults()

				if mod.state != 'unavailable': # Might have been set to this in the loop above
					mod.state = 'disabled'

		# Finished checking for mods (end of allMods loop).
		toc = time.clock()
		print( 'Time to check for installed codes: ' + str(toc-tic) )

		# Ask to enable regions that appear to have custom code
		if requiredDisabledRegions:
			if len( requiredDisabledRegions ) == 1:
				enableDisabledRegionsMessage = ( "It looks like mods may be installed to the " + requiredDisabledRegions[0] 
													+ ", which is currently disabled.\n\nWould you like to enable it?" )
			else:
				enableDisabledRegionsMessage = ( "It looks like mods may be installed to the following custom code regions, which "
									'are currently disabled:\n\n' + ', '.join(requiredDisabledRegions) + '\n\nWould you like to enable them?' )

			# Prompt with the above message and wait for an answer
			enableSuspectRegions = tkMessageBox.askyesno( 'Enable Custom Code Regions?', enableDisabledRegionsMessage )

			if enableSuspectRegions:
				# Enable the required regions and re-scan
				for regionName in requiredDisabledRegions:
					globalData.overwriteOptions[regionName].set( True )

				# Save these region options to file (since this file is read before scanning for codes), and then re-scan
				#globalData.saveRegionOverwriteSettings()
				globalData.saveProgramSettings()

				# Re-scan the Mods Library if that's what this function call was a result of, or if not, just re-check for mods
				# if modsLibraryNotebook.isScanning:
				# 	modsLibraryNotebook.stopToRescan = True
				# else:
				self.checkForEnabledCodes( modsToCheckFor )
				return

		# Check modules that ONLY have standalone functions. Check if they have any functions that are installed
		for mod, functionNames in functionOnlyModules:
			for name in functionNames:
				if name in standaloneFunctionsInstalled: # This module contains a used function!
					mod.state = 'enabled' # Already automatically added to the Standalone Functions table in the Summary Tab
					break # only takes one to make it count
			else: # loop didn't break; no functions in this mod used
				mod.state = 'disabled'

		# print 'all SFs:', len(globalData.standaloneFunctions.keys()), globalData.standaloneFunctions.keys()
		# print 'used:', len(standaloneFunctionsInstalled), standaloneFunctionsInstalled

		# notUsed = set( globalData.standaloneFunctions.keys() ) - standaloneFunctionsInstalled
		# print 'not used:', len(notUsed), notUsed

		# Make sure a new scan isn't queued before finalizing
		# if not modsLibraryNotebook.stopToRescan:
		#updateSummaryTabTotals()

		# If this is SSBM, enable the Default Game Settings tab and update it with what is currently set in this DOL
		# if self.isMelee:
		# 	if not self.currentRevision in settingsTableOffset: 
		# 		msg( '"' + self.currentRevision + '" is an unrecognized SSBM revision.' )
		# 		return

		# 	else:
		# 		mainNotebook.tab( 2, state='normal' ) # The Default Game Settings tab
		# 		updateDefaultGameSettingsTab( 'fromDOL' )

		# else: # Default Game Settings can't be set
		# 	mainNotebook.tab( 2, state='disabled' ) # The Default Game Settings tab
		# 	mainNotebook.select( 0 )

	def identifyTextures( self ):

		""" The DOL does not have image data headers or other structs like DAT files, yet 
			still contains some texture data. For the most part these are textures for 
			displaying character sets (alphanumeric and other symbols). """

		# There are no headers for these images, but they all have the same properties.
		width = 32
		height = 32
		imageType = 0
		imageDataLength = 0x200
		texturesInfo = []

		if self.region == 'PAL':
			imageDataOffset = 0x040C4E0
			totalTextures = 146
		elif self.version == '1.02':
			imageDataOffset = 0x409d40
			totalTextures = 287
		elif self.version == '1.01':
			imageDataOffset = 0x409060
			totalTextures = 287
		elif self.version == '1.00':
			imageDataOffset = 0x407D80
			totalTextures = 287
		else: # Failsafe
			printStatus( "The DOL file doesn't have a recognized revision! ({})".format(self.revision), error=True )
			return []

		# Construct the list in the same was as for DAT files, with tuples of this form:
		# ( imageDataOffset, imageHeaderOffset, paletteDataOffset, paletteHeaderOffset, width, height, imageType, mipmapCount )
		for _ in range( totalTextures ):
			texturesInfo.append( (imageDataOffset, -1, -1, -1, width, height, imageType, 0) )
			imageDataOffset += imageDataLength

		return texturesInfo

	def getTexture( self, imageDataOffset, width=32, height=32, imageType=0, imageDataLength=0x200, getAsPilImage=False ):

		""" Decodes texture data at a given offset and creates an image out of it. 
			getAsPilImage can be set to True if the user would like to get the PIL image instead. """

		assert type( imageDataOffset ) == int, 'Invalid input to getTexture; image data offset is not an int.'

		# Need to find image details if they weren't provided, so look for the image data header
		# if imageType == -1:
		# 	# Get the data section structure offsets, and separate out main structure references
		# 	hI = self.headerInfo
		# 	dataSectionStructureOffsets = set( self.structureOffsets ).difference( (-0x20, hI['rtStart'], hI['rtEnd'], hI['rootNodesEnd'], hI['stringTableStart']) )

		# 	# Scan the data section by analyzing generic structures and looking for standard image data headers
		# 	for structureOffset in dataSectionStructureOffsets:
		# 		# Get the image data header struct's data.
		# 		try: # Using a try block because the last structure offsets may raise an error (unable to get 0x18 bytes) which is fine
		# 			structData = self.getData( structureOffset, 0x18 )
		# 		except:
		# 			continue

		# 		# Unpack the values for this structure, assuming it's an image data header
		# 		fieldValues = struct.unpack( '>IHHIIff', structData )
		# 		headerImageDataOffset, width, height, imageType, _, _, _ = fieldValues

		# 		if headerImageDataOffset == imageDataOffset:
		# 			#print 'header seek time:', time.clock() - tic
		# 			break

		# 	else: # The loop above didn't break; unable to find the header!
		# 		print( 'Unable to find an image data header for the imageDataOffset 0x{:X}'.format(imageDataOffset+0x20) )
		# 		return None

		# Should have details on the texture by now; calculate length if still needed
		# if imageDataLength == -1:
		# 	imageDataLength = hsdStructures.ImageDataBlock.getDataLength( width, height, imageType )

		# try:
		# assert imageDataLength > 0x20, 'Invalid imageDataLength given to getTexture(): ' + hex( imageDataLength )
		imageData = self.getData( imageDataOffset, imageDataLength )

		# if imageType == 8 or imageType == 9 or imageType == 10: # Gather info on the palette.
		# 	paletteData, paletteType = self.getPaletteData( imageDataOffset )
		# else:
		paletteData = ''
		paletteType = None

		newImg = TplDecoder( '', (width, height), imageType, paletteType, imageData, paletteData )
		newImg.deblockify() # This decodes the image data, creating an rgbaPixelArray.

		# Create an image with the decoded data
		textureImage = Image.new( 'RGBA', (width, height) )
		textureImage.putdata( newImg.rgbaPixelArray )

		# except Exception as errMessage:
		# 	print 'Unable to make out a texture for data at', hex(0x20+imageDataOffset)
		# 	print errMessage

		if getAsPilImage:
			return textureImage
		else:
			return ImageTk.PhotoImage( textureImage )

	def setTexture( self, imageDataOffset, pilImage=None, imagePath='', textureName='Texture', paletteQuality=3 ):

		""" Encodes image data into TPL format (if needed), and writes it into the file at the given offset. 
			Input must be a data offset and either a PIL image or a file path to a texture file (PNG or TPL). 
			The offset given should be relative to the start of the data section. 

			Returns a tuple of 3 values; an exit code, and two extra values in the following cases: 
			Return/exit codes:									Extra info:
				0: Success; no problems								( 0, '', '' )
				1: Unable to find palette information 				( 1, '', '' )
				2: The new image data is too large 					( 2, origImageDataLength, newImageDataLength )
				3: The new palette data is too large 				( 3, maxPaletteColorCount, newPaletteColorCount )
		"""

		# Initialize a TPL image object (and create a new palette for it, if needed)
		if pilImage:
			newImage = TplEncoder( '', pilImage, 0 )

		elif imagePath:
			newImage = TplEncoder( imagePath, imageType=0 )
			
		else:
			raise IOError( 'Invalid input to .setTexture(); no PIL image or texture filepath provided.' )

		# Decode the image into TPL format
		newImage.blockify()
		newImageData = newImage.encodedImageData

		# Make sure the new image isn't too large
		newImageDataLength = len( newImage.encodedImageData )
		if newImageDataLength > 0x200:
			return 2, 0x200, newImageDataLength

		# Update the texture image data in the file
		self.updateData( imageDataOffset, newImageData, trackChange=False )
		self.recordChange( '{} updated at 0x{:X}'.format(textureName, 0x20+imageDataOffset) )

		return 0, '', ''