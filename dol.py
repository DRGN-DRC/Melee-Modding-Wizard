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

import os
import ttk
import time
import struct
import globalData
import tkMessageBox
import Tkinter as Tk
import codeRegionSettings

from binascii import hexlify
from hsdFiles import FileBase
from itertools import izip, count
from collections import OrderedDict
#from codeMods import getCustomSectionLength
from codeMods import ConfigurationTypes
from basicFunctions import uHex, toHex, toInt, validHex, grammarfyList, findAll, msg
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


class revisionPromptWindow( BasicWindow ):

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
		self._externalCodelistData = ()
		self._externalInjectionData = ()

		self.project = -1
		self.major = -1
		self.minor = -1
		self.patch = -1

	def load( self ):

		# Skip this method if the file has already been loaded
		if self.sectionInfo:
			#print 'already initialized'
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
			#memAddress = int( memAddress - 0x80000000 )
			self.sectionInfo['text'+str(i)] = ( fileOffset, memAddress, size )

			# Find the max possible dol offset and ram address for this game's dol
			if fileOffset + size > self.maxDolOffset: self.maxDolOffset = fileOffset + size
			if memAddress + size > self.maxRamAddress: self.maxRamAddress = memAddress + size

		# Assemble data section tuples, and check for max file offsets and ram addresses
		for i, fileOffset, memAddress, size in izip( count(), dataFileOffsets, dataMemAddresses, dataSizes ):
			# If any of the above values are 0, there are no more sections
			if fileOffset == 0 or memAddress == 0 or size == 0: break
			#memAddress = int( memAddress - 0x80000000 )
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
			Versions 5.x.x use a new method of project code, major version, minor version, and patch, respectively (one byte each). """

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
				print 'DOL revision determined from metadata:', self.region, self.version
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

			# if '.' in self.disc.revision:
			# 	versionSuggestion = self.disc.revision.split('.')[1]
			versionSuggestion = '{:02}'.format( self.disc.revision )

			userMessage = ( "The revision of the DOL within this disc is being predicted from the disc's details. Please verify them below. "
								"(If this disc has not been altered, these predictions can be trusted.)" )
		else:
			userMessage = "This DOL's revision could not be determined. Please select a region and game version below."
		userMessage += ' Note that codes may not be able to be installed or detected properly if these are set incorrectly.'

		# Prompt the user (using the disc region/version above for predictors)
		revisionWindow = revisionPromptWindow( userMessage, regionSuggestion, versionSuggestion )

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
					'And installing mods may break game functionality.', 'Revision Uncertainty', globalData.gui.root )

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

		#return 0x80000000 + ramAddress
		return ramAddress

	def offsetInDOL( self, ramAddress ):

		""" Converts the given integer RAM address (location in memory) to the equivalent DOL file integer offset. """

		dolOffset = -1

		# Mask out the base address
		#ramAddress = ramAddress & ~0x80000000

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
			msg( 'Invalid input for branch calculation: "to" value (' + hex(toDOL) + ') is out of range.' ) #.\n\nTarget DOL Offset: ' + hex(toDOL) )
			return -1
		else:
			return end - start

	def normalizeDolOffset( self, offsetString, returnType='int' ):

		""" Converts a hex offset string to an int, and converts it to a DOL offset if it's a RAM address. """

		offsetString = offsetString.replace( '0x', '' ).strip()
		problemDetails = ''
		dolOffset = -1

		if len( offsetString ) == 8 and offsetString.startswith( '8' ): # Looks like it's a RAM address; convert it to a DOL offset
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
			#msg( 'Problem detected while processing the offset 0x' + offsetString + '; it could not be converted to a DOL offset' + problemDetails )
			return -1, 'Problem detected while processing the offset 0x' + offsetString + '; it could not be converted to a DOL offset' + problemDetails

		return dolOffset, ''

	def normalizeRamAddress( self, offsetString, returnType='int' ):

		""" Converts a hex offset string to an int, and converts it to a RAM address if it's a DOL offset. """

		offsetString = offsetString.replace( '0x', '' ).strip()
		problemDetails = ''
		ramAddress = -1

		if len( offsetString ) == 8 and offsetString.startswith( '8' ):
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
				#ramAddress = '0x8' + toHex( ramAddress, 7 )
				ramAddress = uHex( ramAddress )

		if problemDetails:
			#msg( 'Problem detected while processing the offset, 0x' + offsetString + '; it could not be converted to a RAM address' + problemDetails )
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
			print 'Invalid music ID given to getMusicFilename(): ' + hex( musicId )
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
			print 'Dol.getMusicId() unable to look up musicId for "{}"'.format( filename )
			return -1

	def getStageFileName( self, internalStageId, forceExtension=True, defaultToDat=False ):

		""" Looks up a stage file name (disc file name), using a pointer table at 0x3DCEDC. 
			The table contains 0x6F (111) entries; though entry 0 is the "Dummy" placeholder, 
			and entries 1, 0x23, and 0x48 onward (to the end of the table) are the "TEST" stage.
			Uses the internal stage ID as an index in this table to get a pointer, which points to 
			a structure containing multiple properties of the stage, including a file name pointer. 
			Returns two values: the offset of the file name string in the DOL, and the decoded string. 
			
			Note that for some stages, which have alternate variations based on the game's region 
			(i.e. .usd vs .dat), the file extension will not be included unless forceExtension is True. """

		if internalStageId <= 0 or internalStageId >= 0x6F:
			print 'Invalid index to stage file name look-up: ' + hex(internalStageId)
			return -1, ''

		# Unpack all of the pointers to the stage table structs
		if not self._stageInfoStructPointers:
			tic = time.clock()
			pointerTableData = self.getData( 0x3DCEDC, 0x6F*4 )
			self._stageInfoStructPointers = struct.unpack( '>111I', pointerTableData )
			toc = time.clock()
			print 'time to unpack stage info struct:', toc-tic

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
			elif defaultToDat:
				nameString += '.dat'
			else:
				nameString += '.usd'

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
						print "Region start (0x{:X}) for {} is outside of the DOL's code/data sections.".format( regionStart, regionName )
						incompatibleRegions.append( regionName )
						break

					# Check that the region end is within the DOL's code or data sections
					elif regionEnd > self.maxDolOffset:
						print "Region end (0x{:X}) for {} is outside of the DOL's code/data sections.".format( regionEnd, regionName )
						incompatibleRegions.append( regionName )
						break

				# Regions validated; allow them to show up in the GUI (Code-Space Options)
				if regionName not in incompatibleRegions:
					self.customCodeRegions[regionName] = regions

		if incompatibleRegions:
			msg( '\nThe following regions are incompatible with the ' + self.revision + ' DOL, because one or both offsets fall '
				 'outside of the offset range of its text/data sections:\n\n\t' + '\n\t'.join(incompatibleRegions) + '\n', error=True )

	def getCustomCodeRegions( self, searchDisabledRegions=False, specificRegion='', codelistStartPosShift=0, codehandlerStartPosShift=0, useRamAddresses=False ):

		""" This gets the regions defined for custom code use (regions permitted for overwrites) in codeRegionSettings.py. 
			Returned as a list of tuples of the form (regionStart, regionEnd). The start position shifts (space reservations 
			for the Gecko codelist/codehandler) should be counted in bytes. Note that the region names in the dictionary 
			are not the "full" region names; i.e. they don't include revision. """

		codeRegions = []

		for regionName, regions in self.customCodeRegions.items():

			# Check if this dol region should be included by its BooleanVar option value (or if that's overridden, which is the first check)
			if searchDisabledRegions or globalData.checkRegionOverwrite( regionName ):

				if specificRegion and regionName != specificRegion:
					continue

				# Get all regions if specificRegion is not defined, or get only that region (or that group of regions)
				#if not specificRegion or regionName == specificRegion:

				# Offset the start of (thus excluding) areas that will be partially used by the Gecko codelist or codehandler
				# if codelistStartPosShift != 0 and gecko.environmentSupported and regionName == gecko.codelistRegion:
				# 	codelistRegionStart, codelistRegionEnd = regions[0]
				# 	codelistRegionStart += codelistStartPosShift

				# 	if codelistRegionEnd - codelistRegionStart > 0: # This excludes the first area if it was sufficiently shrunk
				# 		codeRegions.append( (codelistRegionStart, codelistRegionEnd) )
				# 	codeRegions.extend( regions[1:] ) # If there happen to be any more regions that have been added for this.

				# elif codehandlerStartPosShift != 0 and gecko.environmentSupported and regionName == gecko.codehandlerRegion:
				# 	codehandlerRegionStart, codehandlerRegionEnd = regions[0]
				# 	codehandlerRegionStart += codehandlerStartPosShift

				# 	if codehandlerRegionEnd - codehandlerRegionStart > 0: # This excludes the first area if it was sufficiently shrunk
				# 		codeRegions.append( (codehandlerRegionStart, codehandlerRegionEnd) )
				# 	codeRegions.extend( regions[1:] ) # If there happen to be any more regions that have been added for this.

				# else:
				if useRamAddresses:
					for regionStart, regionEnd in regions:
						codeRegions.append( (self.offsetInRAM(regionStart), self.offsetInRAM(regionEnd)) )
				else:
					codeRegions.extend( regions )

				# If only looking for a specific revision, there's no need to iterate futher.
				if specificRegion: break

		return codeRegions

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

	# def codeMatches( self, codeToMatch, freeSpaceCodeArea, offset ):

	# 	sectionLength = len( codeToMatch ) / 2
		
	# 	codeInDol = freeSpaceCodeArea[offset:offset+sectionLength]

	# 	if bytearray.fromhex( codeToMatch ) != codeInDol: # Comparing bytearrays rather than strings prevents worrying about upper/lower-case
	# 		return -1 # Mismatch detected, meaning this is not the same (custom) code in the DOL.
	# 	else:
	# 		return offset

	def findCustomCode_( self, mod, codeChange, freeSpaceCodeArea ):

		""" Occurs with Gecko codes & standalone functions, since we may not have a branch to locate them.
			This is the first normal (non-special-branch) section for this code. Since the offset is unknown,
			use this section to find all possible locations/matches for this code within the region. """
		
		customCode = codeChange.preProcessedCode
		if not customCode: # Pre-processing may have failed
			return -1

		offset = 0
		customSyntaxIndex = 0
		matchOffset = 0

		# Map each code section to the code in the DOL to see if they match up.
		for section in customCode.split( '|S|' ):
			if section == '': continue

			# Skip matching custom syntaxes for now
			elif section.startswith( 'sbs__' ) or section.startswith( 'sym__' ) or section.startswith( 'opt__' ):
				#offset += 4
				#offset += getCustomSectionLength( section )
				offset += codeChange.syntaxInfo[customSyntaxIndex][1]
				customSyntaxIndex += 1

			else: # First section of non-special syntax found
				matches = findAll( freeSpaceCodeArea, bytearray.fromhex(section), charIncrement=2 ) # charIncrement set to 2 so we increment by byte rather than by nibble

				# Iterate over the possible locations/matches, and check if each may be the code we're looking for (note that starting offsets will be known in these checks)
				for matchingOffset in matches:
					subMatchOffset = self.customCodeInDOL( mod, codeChange, matchingOffset - offset, freeSpaceCodeArea ) # "- offset" accomodates for potential preceding special branches

					if subMatchOffset != -1: # The full code was found
						return subMatchOffset
				else: # Loop above didn't return; no matches for this section found in the given code area
					return matchOffset

		return matchOffset

	def customCodeInDOL_( self, mod, codeChange, startingOffset, freeSpaceCodeArea, excludeLastCommand=False ):

		""" Checks if the given custom code (a hex string) is installed within the given code area (a bytearray).
			Essentially tries to mismatch any of a code change's custom code with the custom code in the DOL. Besides simply
			checking injection site code, this can check custom injection code, even if it includes unknown special branch syntaxes.

			This is much more reliable than simply checking whether the hex at an injection site is vanilla or not because it's 
			possible that more than one mod could target the same location (so we have to see which mod the installed custom code 
			belongs to). If custom code is mostly or entirely composed of custom syntaxes, we'll have to give it the benefit of the 
			doubt and assume it's installed (since at this point there is no way to know what bytes a custom syntax may resolve to). """

		customCode = codeChange.preProcessedCode
		if not customCode: # Pre-processing may have failed
			return -1

		if excludeLastCommand: # Exclude the branch back on injection mods.
			customCode = customCode[:-8] # Removing the last 4 bytes

		offset = startingOffset
		matchOffset = startingOffset
		customSyntaxIndex = 0

		# Map each code section to the code in the DOL to see if they match up.
		for section in customCode.split( '|S|' ):
			if section == '': continue

			# Skip matching custom syntaxes
			elif section.startswith( 'sbs__' ) or section.startswith( 'sym__' ):
				# optionOffset, optionWidth, codeLine, names = codeChange.syntaxInfo[customSyntaxIndex]
				# offset += optionWidth
				offset += 4
				customSyntaxIndex += 1

				# If this section contains a configuration option, get the current value in the game
			elif section.startswith( 'opt__' ):
				optionOffset, optionWidth, _, names = codeChange.syntaxInfo[customSyntaxIndex]

				# Parse the custom code line and compare its non-option parts to what's in the DOL
				codeMatches = self.compareCustomOptionCode( section, offset, freeSpaceCodeArea, codeChange.isAssembly, mod )
				if not codeMatches:
					matchOffset = -1
					break # Mismatch detected, meaning this is not the same (custom) code in the DOL.

				absOffsetStart = startingOffset + optionOffset # Need an absolute DOL offset. The option offset is relative to the code start
				codeInDol = freeSpaceCodeArea[absOffsetStart:absOffsetStart+optionWidth]
				for name in names: # Last item in the list is a list of option names
					optionType = mod.configurations[name]['type']
					value = struct.unpack( ConfigurationTypes[optionType], codeInDol )[0]
					mod.configure( name, value )

				offset += optionWidth
				customSyntaxIndex += 1

			# elif startOffsetUnknown: # Occurs with Gecko codes & standalone functions, since we may not have a branch to locate them.
			# 	# This is the first normal (non-special-branch) section for this code. Since the offset is unknown,
			# 	# use this section to find all possible locations/matches for this code within the region.
			# 	matches = findAll( freeSpaceCodeArea, bytearray.fromhex(section), charIncrement=2 ) # charIncrement set to 2 so we increment by byte rather than by nibble
			# 	matchOffset = -1

			# 	# Iterate over the possible locations/matches, and check if each may be the code we're looking for (note that starting offsets will be known in these checks)
			# 	for matchingOffset in matches:
			# 		subMatchOffset = self.customCodeInDOL( mod, codeChange, matchingOffset - offset, freeSpaceCodeArea ) # "- offset" accomodates for potential preceding special branches
			# 		#subMatchOffset = self.codeMatches( customCode, freeSpaceCodeArea, matchingOffset - offset )

			# 		if subMatchOffset != -1: # The full code was found
			# 			matchOffset = subMatchOffset
			# 			break
			# 	break

			else:
				sectionLength = len( section ) / 2
				codeInDol = freeSpaceCodeArea[offset:offset+sectionLength]

				if bytearray.fromhex( section ) != codeInDol: # Comparing bytearrays rather than strings prevents worrying about upper/lower-case
					matchOffset = -1
					break # Mismatch detected, meaning this is not the same (custom) code in the DOL.
				else:
					offset += sectionLength

		return matchOffset

	def compareCustomOptionCode( self, section, sectionStart, freeSpaceCodeArea, isAssembly, mod ):

		""" Parses a section of custom code for its non-option/value parts, and compares 
			them to what's in the DOL to see if the code matches and is installed. """

		section = section[5:]
		sectionChunks = section.split( '[[' )

		if isAssembly: # This is expected to be one ASM command. Just use the opCode to compare
			# Substitute name placeholders for values for the assembly process
			for i, chunk in enumerate( sectionChunks ):
				if ']]' in chunk:# Contains a config/variable name and maybe other code
					optName, theRest = chunk.split( ']]' )
					sectionChunks[i] = chunk.replace( optName + ']]', '0' )

			assemblyCode = ''.join( sectionChunks )
			conversionOutput, errors = globalData.codeProcessor.assemble( assemblyCode, False, mod.includePaths, True, False )
			if errors:
				return False
			
			# Compare the opCode of the assembled code and the code in the DOL
			hexCode = bytearray.fromhex( conversionOutput )
			codeInDol = freeSpaceCodeArea[sectionStart:sectionStart+4]
			if hexCode[0] == codeInDol[0]:
				return True
			else:
				return False
		
		else: # Processing hex code
			sectionPos = 0 # Offset/position within this section

			for chunk in sectionChunks:
				if ']]' in chunk: # Contains a config/variable name and maybe other code
					_, chunk = chunk.split( ']]' )

					# Return True if there are any non-hex characters (meaning assembly was found)
					# if not theRest: pass # Empty string
					# else:
					# 	chunkLength = len( theRest ) / 2

					# 	# Check for DOL code mismatch
					# 	dolChunkStart = sectionStart + sectionPos
					# 	dolChunk = freeSpaceCodeArea[dolChunkStart:dolChunkStart+chunkLength]
					# 	if bytearray.fromhex( theRest ) != dolChunk:
					# 		return False

					# 	sectionPos += chunkLength
				
				# No config/variable name in this chunk; expected to be hex at this point.
				if not chunk: pass # Empty string
				else:
					chunkLength = len( chunk ) / 2

					# Check for DOL code mismatch
					dolChunkStart = sectionStart + sectionPos
					dolChunk = freeSpaceCodeArea[dolChunkStart:dolChunkStart+chunkLength]
					print 'comparing', chunk, 'to', hexlify( dolChunk )
					if bytearray.fromhex( chunk ) != dolChunk:
						return False

					sectionPos += chunkLength

			return True

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

	def findCustomCode( self, mod, codeChange, freeSpaceCodeArea ):

		""" Occurs with Gecko codes and standalone functions, since we may not have a branch to locate them.
			This is the first normal (non-special-branch) section for this code. Since the offset is unknown,
			use this section to find all possible locations/matches for this code within the region. """
		
		customCode = codeChange.preProcessedCode
		if not customCode: # Pre-processing may have failed
			return -1
			
		elif not codeChange.syntaxInfo:
			matches = findAll( freeSpaceCodeArea, bytearray.fromhex(customCode), charIncrement=1 ) # charIncrement set to 1 in order to increment by byte
			
			if matches:
				return True
			else:
				return False

		readOffset = 0
		#customSyntaxIndex = 0
		#matchOffset = 0

		for syntaxOffset, length, _, _, _ in codeChange.syntaxInfo:

			# Check for and process custom code preceding this custom syntax instance
			if readOffset != syntaxOffset:
				sectionLength = syntaxOffset - readOffset
				# dolCodeStart = startingOffset + readOffset
				# dolCodeEnd = dolCodeStart + sectionLength
				assert sectionLength > 0, 'Read position error in .customCodeInDOL()! Read offset: {}, Next syntax offset: {}'.format( readOffset, syntaxOffset )

				codeSection = customCode[readOffset:syntaxOffset]
				
				matches = findAll( freeSpaceCodeArea, bytearray.fromhex(codeSection), charIncrement=1 ) # charIncrement set to 1 in order to increment by byte
				
				#codeInDol = freeSpaceCodeArea[dolCodeStart:dolCodeEnd]
				#lastSyntaxOffset = syntaxOffset + length

				# Iterate over the possible locations/matches, and check if each may be the code we're looking for (note that starting offsets will be known in these checks)
				for matchingOffset in matches:
					codeStart = matchingOffset - readOffset # Accomodates for potential preceding special branches

					if self.customCodeInDOL( mod, codeChange, codeStart, freeSpaceCodeArea ):
						return codeStart
				else: # Loop above didn't return; no matches for this section found in the given code area
					return -1

			# Skip matching custom syntaxes for now
			#elif section.startswith( 'sbs__' ) or section.startswith( 'sym__' ) or section.startswith( 'opt__' ):
				#offset += 4
				#offset += getCustomSectionLength( section )
				# readOffset += codeChange.syntaxInfo[customSyntaxIndex][1]
				# customSyntaxIndex += 1
			readOffset += length

			# else: # First section of non-special syntax found
			# 	matches = findAll( freeSpaceCodeArea, bytearray.fromhex(section), charIncrement=2 ) # charIncrement set to 2 so we increment by byte rather than by nibble

			# 	# Iterate over the possible locations/matches, and check if each may be the code we're looking for (note that starting offsets will be known in these checks)
			# 	for matchingOffset in matches:
			# 		subMatchOffset = self.customCodeInDOL( mod, codeChange, matchingOffset - readOffset, freeSpaceCodeArea ) # "- readOffset" accomodates for potential preceding special branches

			# 		if subMatchOffset != -1: # The full code was found
			# 			return subMatchOffset
			# 	else: # Loop above didn't return; no matches for this section found in the given code area
			# 		return matchOffset

		return 0 # If this is reached, the custom code is entirely special syntaxes; going to have to assume installed. todo: fix

	#def getMask( self, syntaxInfo, mod ):

	# def parseConfigurationOption( self, syntaxInfo, mod ):

	# 	for syntaxOffset, length, syntaxType, codeLine, names in syntaxInfo:
	# 		for name in names:
	# 			optionDict = mod.getConfiguration( name )

	def customCodeInDOL( self, mod, codeChange, startingOffset, freeSpaceCodeArea, excludeLastCommand=False ):

		""" Checks if the given custom code (a hex string) is installed within the given code area (a bytearray).
			Essentially tries to mismatch any of a code change's custom code with the custom code in the DOL. Besides simply
			checking injection site code, this can check custom injection code, even if it includes unknown special branch syntaxes.

			This is much more reliable than simply checking whether the hex at an injection site is vanilla or not because it's 
			possible that more than one mod could target the same location (so we have to see which mod the installed custom code 
			belongs to). If custom code is mostly or entirely composed of custom syntaxes, we'll have to give it the benefit of the 
			doubt and assume it's installed (since at this point there is no way to know what bytes a custom syntax may resolve to). """

		customCode = codeChange.preProcessedCode
		if not customCode: # Pre-processing may have failed
			return False

		if excludeLastCommand: # Exclude the branch back on injection mods.
			customCode = customCode[:-8] # Removing the last 4 bytes
		codeLength = len( customCode ) / 2

		# With no custum syntax, there is just one chunk of code to compare
		if not codeChange.syntaxInfo:
			codeInDol = freeSpaceCodeArea[startingOffset:startingOffset+codeLength]

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
				codeInDol = freeSpaceCodeArea[dolCodeStart:dolCodeEnd]
				test = hexlify( codeInDol )

				if bytearray.fromhex( codeSection ) != codeInDol: # Comparing via bytearrays rather than strings prevents worrying about upper/lower-case
					# matchOffset = -1
					# break # Mismatch detected, meaning this is not the same (custom) code in the DOL.
					return False
				else:
					readOffset += sectionLength

			# Skip matching custom syntaxes
			if syntaxType == 'sbs' or syntaxType == 'sym':
				readOffset += 4

			# If this section contains a configuration option, get the current value stored in the DOL
			elif syntaxType == 'opt':
				#optionOffset, optionWidth, _, names = codeChange.syntaxInfo[customSyntaxIndex]

				# Parse the custom code line and compare its non-option parts to what's in the DOL
				# codeMatches = self.compareCustomOptionCode( section, readOffset, freeSpaceCodeArea, codeChange.isAssembly, mod )
				# if not codeMatches:
				# 	matchOffset = -1
				# 	break # Mismatch detected, meaning this is not the same (custom) code in the DOL.

				absOffsetStart = startingOffset + syntaxOffset # Need an absolute DOL offset. The option offset is relative to the code start
				codeInDol = freeSpaceCodeArea[absOffsetStart:absOffsetStart+length]

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
							
						mod.configure( name, value )
						
						toc = time.clock()
						print 'method 1 value: ', value
						print 'in', toc-tic
						
						tic = time.clock()

						if mask:
							maskValue = mod.parseConfigValue( optType, mask )
							maskBytes = struct.pack( ConfigurationTypes[optType], maskValue )
						
							i = 0
							for dolByte, maskByte in zip( codeInDol, maskBytes ):
								codeInDol[i] = dolByte & maskByte
						
						value = struct.unpack( ConfigurationTypes[optType], codeInDol )[0]
						
						toc = time.clock()
						print 'method 2 value: ', value
						print 'in', toc-tic

				readOffset += length

			# else:
			# 	sectionLength = len( section ) / 2
			# 	codeInDol = freeSpaceCodeArea[readOffset:readOffset+sectionLength]

			# 	if bytearray.fromhex( section ) != codeInDol: # Comparing bytearrays rather than strings prevents worrying about upper/lower-case
			# 		matchOffset = -1
			# 		break # Mismatch detected, meaning this is not the same (custom) code in the DOL.
			# 	else:
			# 		readOffset += sectionLength

		# Test last section
		if readOffset != codeLength:
			codeSection = customCode[readOffset*2:] # Splicing a string, so *2 to splice by bytes rather than nibbles
			sectionLength = len( codeSection ) / 2
			dolCodeStart = startingOffset + readOffset
			dolCodeEnd = dolCodeStart + sectionLength

			codeInDol = freeSpaceCodeArea[dolCodeStart:dolCodeEnd]

			if not bytearray.fromhex( codeSection ) == codeInDol: # Comparing via bytearrays rather than strings prevents worrying about upper/lower-case
				# Mismatch detected, meaning this is not the same (custom) code in the DOL.
				return False

		return True

	def checkForEnabledCodes( self, modsToCheckFor ):

		""" Checks the currently loaded DOL file for which mods are installed, and sets their states accordingly.
			'userPromptedForGeckoUsage' will only come into play if there are Gecko codes detected as installed. """

		self.load()

		#clearSummaryTab() # Clears the summary tab's lists of installed mods/SFs.
		allEnabledCodeRegions = self.getCustomCodeRegions()

		# Preliminary attempts to get injection code and gecko code data external to the dol (from gecko.bin/codes.bin)
		self._externalCodelistData = self.disc.getGeckoData()
		self._externalInjectionData = self.disc.getInjectionData()

		standaloneFunctionsInstalled = set()
		functionOnlyModules = [] # Remember some info on modules composed of only standalone functions
		#geckoCodesAllowed = overwriteOptions[ 'EnableGeckoCodes' ].get()
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
				mod.setState( 'unavailable' )
				continue

			# Disable mods that are not applicable to the currently loaded DOL
			elif self.revision not in mod.data:
				mod.setState( 'unavailable' )
				continue

			# if mod.category == 'TEST':
			# #if mod.name == 'Dreamland - Disable Wind':
			# 	pass

			# Determine if the mod is in the DOL, and set the state of the module respectively.
			included = True
			functionsOnly = True
			functionsIncluded = []
			summaryReport = [] # Used to track and report installation locations/offsets to the Summary tab

			#for change.type, change.length, change.offset, change.origCode, _, change.preProcessedCode, _ in mod.getCodeChanges():
			for codeChange in mod.getCodeChanges():
				if functionsOnly and not codeChange.type == 'standalone':
					functionsOnly = False

				# Piggy-back on the codeChange module to remember configuration options found while checking for custom code
				#codeChange.options = {}

				# Convert the offset to a DOL Offset integer (even if it was a RAM Address)
				if codeChange.type != 'standalone' and codeChange.type != 'gecko':
					offset, errorMsg = self.normalizeDolOffset( codeChange.offset )

					# Validate the offset
					if offset == -1:
						userMessage = 'A problem was detected with an offset, {}, for the mod "{}";{}'.format( codeChange.offset, mod.name, errorMsg.split(';')[1] )
						# msg( 'A problem was detected with the mod "' + mod.name + '"; an offset for one of its code changes (' + codeChange.offset + ') could '
						# 	 "not be parsed or processed. If you're sure it's written correctly, it appears to fall out of range of this game's DOL." )
						msg( userMessage )
						#mod.setState( 'unavailable' )
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
						for codeRegion in allEnabledCodeRegions:
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
							# matchOffset = self.customCodeInDOL( mod, codeChange, customCodeOffset, self.data, excludeLastCommand=True ) #todo narrow search field to improve performance

							# # If there was a good match on the custom code, remember where this code change is for a summary on this mod's installation
							# if matchOffset == -1: included = False
							if not self.customCodeInDOL( mod, codeChange, customCodeOffset, self.data, excludeLastCommand=True ): #todo narrow search field to improve performance?
								included = False
							else:
								summaryReport.append( ('Branch', 'static', offset, 4) ) # changeName, changeType, dolOffset, changeLength
								summaryReport.append( ('Injection code', codeChange.type, customCodeOffset, codeChange.length) )

						else:
							included = False
							print '\nPossible phantom mod;', mod.name, 'may have custom code installed to a disabled region: "' + regionNameFoundIn + '"'
							print 'it was led to by an injection point hex of', injectionPointCode, 'at', hex(offset), 'which points to DOL offset', hex(customCodeOffset)

							if regionNameFoundIn != '':
								if regionNameFoundIn not in requiredDisabledRegions:
									requiredDisabledRegions.append( regionNameFoundIn )
							else:
								print 'Custom code at', hex(offset), 'seems to be pointing to a region not defined for custom code!'

				elif codeChange.type == 'gecko':
					codeChange.evaluate()
					# if not gecko.environmentSupported: # These aren't available for this DOL
					# 	included = False
					if not self._externalCodelistData: # Not installed
						included = False

					else: # Check if the code is installed (present in the codelist area)
						matchOffset = self.findCustomCode( mod, codeChange, self._externalCodelistData )

						if matchOffset == -1: # Code not found in the DOL
							included = False

						else: # Code found to be installed!
							# If using the Gecko regions is not enabled, ask the user if they'd like to allow Gecko codes.
							# if not geckoCodesAllowed and not userPromptedForGeckoUsage: # The second boolean here ensure this message only appears once throughout all of these loops.
							# 	userPromptedForGeckoUsage = True

							# 	# If this is Melee, add some details to the message
							# 	if dol.isMelee and ( gecko.codelistRegion == 'DebugModeRegion' or gecko.codehandlerRegion == 'DebugModeRegion' 
							# 						or gecko.codelistRegion == 'Debug Mode Region' or gecko.codehandlerRegion == 'Debug Mode Region' ):
							# 		meleeDetails = ( "Mostly, this just means that you wouldn't be able to use the vanilla Debug Menu "
							# 							"(if you're not sure what that means, then you're probably not using the Debug Menu, and you can just click yes). " )
							# 	else: meleeDetails = ''

							# 	promptToUser = ( 'Gecko codes have been found to be installed, however the "Enable Gecko Codes" option is not selected.'
							# 		'\n\nEnabling Gecko codes means that the regions defined for Gecko codes, ' + gecko.codelistRegion + ' and ' + gecko.codehandlerRegion + ', will be reserved '
							# 		"(i.e. may be partially or fully overwritten) for custom code. " + meleeDetails + 'Regions that you have '
							# 		'enabled for use can be viewed and modified by clicking on the "Code-Space Options" button. '
							# 		'\n\nIf you do not enable Gecko codes, those that are already installed will be removed upon saving! Would you like to enable '
							# 		'these regions for overwrites in order to use Gecko codes?' )

							# 	geckoCodesAllowed = willUserAllowGecko( promptToUser, False, root )

							# 	if geckoCodesAllowed: # This option has been toggled! Re-run this function to ensure all Gecko mod states are properly set
							# 		print 'performing gecko codes re-scan'
							# 		checkForEnabledCodes( True )
							# 		return

							# if geckoCodesAllowed:
							# self.disc.files[self.disc.gameId + '/gecko.bin']
							# dolOffset = gecko.codelistRegionStart + 8 + matchOffset
							summaryReport.append( ('Gecko code', codeChange.type, matchOffset, codeChange.length) )
							# else:
							# 	included = False

				elif codeChange.type == 'standalone':
					functionsIncluded.append( codeChange.offset ) # The offset will be a name in this case

				if not included:
					break

				# The mod is considered included so far. Store configuration options found
				# elif codeChange.options:
				# 	for optionName, value in codeChange.options:
				# 		mod.configure( optionName, value )

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

						for areaStart, areaEnd in allEnabledCodeRegions:
							matchOffset = self.findCustomCode( mod, functionCodeChange, self.data[areaStart:areaEnd] )

							if matchOffset != -1: # Function found
								summaryReport.append( ('SF: ' + functionName, 'standalone', areaStart + matchOffset, functionCodeChange.length) )
								break

						else: # The loop scanning through the free code regions above didn't break; SF was not found.
							# Check whether the function is in a disabled region
							found = False
							for regionName, regions in self.customCodeRegions.items():
								#if regionName in globalData.overwriteOptions and not globalData.overwriteOptions[regionName].get():
								if globalData.checkRegionOverwrite( regionName ):
									# Scan the regions for the offset
									for regionStart, regionEnd in regions:
										matchOffset = self.findCustomCode( mod, functionCodeChange, self.data[regionStart:regionEnd] )

										if matchOffset != -1: # Function found (in a disabled region!)
											print 'SF for', mod.name + ', "' + functionName + '", found in a disabled region.'
											if not regionName in requiredDisabledRegions: requiredDisabledRegions.append( regionName )
											found = True
											break
								if found: break

							# Even if found in a disabled region, consider not installed for now. User will be prompted for a rescan if custom code is in disabled regions
							included = False
							break

			if included:
				mod.setState( 'enabled' )
				standaloneFunctionsInstalled.update( requiredStandaloneFunctions ) # This is a set, so only new names are added.
				#addToInstallationSummary( mod.name, mod.type, summaryReport )

			# elif codeChange.type == 'gecko' and not geckoCodesAllowed:
			# 	mod.setState( 'unavailable' )

			elif globalData.checkSetting( 'alwaysEnableCrashReports' ) and mod.name == "Enable OSReport Print on Crash":
				# Queue this to be installed
				if mod.state != 'pendingEnable':
					mod.setState( 'pendingEnable' )

			elif mod.state != 'unavailable': # Might have been set to this in the loop above
				mod.setState( 'disabled' )

		# Finished checking for mods (end of allMods loop).
		toc = time.clock()
		print 'time to check for installed codes:', toc-tic

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
					mod.setState( 'enabled' ) # Already automatically added to the Standalone Functions table in the Summary Tab
					break # only takes one to make it count
			else: # loop didn't break; no functions in this mod used
				mod.setState( 'disabled' )

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
