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
import struct

from string import hexdigits
from binascii import hexlify

# Internal dependencies
import globalData
import hsdStructures
import standaloneStructs

from fileBases import DatFile
from basicFunctions import toInt, msg, uHex, reverseDictLookup


def findBytes( bytesRange, target ): # Searches a bytearray for a given (target) set of bytes, and returns the location (index)
	targetLength = len( target )

	for index, _ in enumerate( bytesRange ):
		if bytesRange[index:index+targetLength] == target: return index
	else: return -1


class CssFile( DatFile ):

	""" Special subclass for the Character Select Screen. """

	randomNeutralStageNameTables = { # Offsets for pointer tables (relative to data section start) used in 20XX
			'GrNBa': 	0x3C10C0, 	# Battlefield
			'GrNLa': 	0x3C1320, 	# Final Destination
			'GrSt':		0x3C1580, 	# Yoshi's Story
			'GrIz':		0x3C17E0, 	# Fountain
			'GrOp':		0x3C1A40, 	# Dream Land
			'GrP':		0x3C1CA0 } 	# Stadium

	cspBaseOffset = 0x4CA40 # The start of the first CSP's data. Includes file header offset
	cspStride = 0x6600 # Texture data size + palette data/header
	cspIndexes = {	# key = External Char ID x 0x10 + Costume ID, value = CSP index
		0x00: 33, 0x01: 62, 0x02: 81, 0x03: 102, 0x04: 43, 0x05: 10, 	# Captain Falcon - 0x0
		0x10: 36, 0x11: 7, 0x12: 83, 0x13: 12, 0x14: 44, 		# DK
		0x20: 40, 0x21: 87, 0x22: 15, 0x23: 48, 				# Fox
		0x30: 5, 0x31: 80, 0x32: 4, 0x33: 42, 					# Game & Watch
		0x40: 66, 0x41: 111, 0x42: 19, 0x43: 91, 0x44: 52, 0x45: 105, 	# Kirby
		0x50: 67, 0x51: 92, 0x52: 20, 0x53: 1,					# Bowser
		0x60: 68, 0x61: 93, 0x62: 21, 0x63: 2, 0x64: 106,		# Link
		0x70: 69, 0x71: 107, 0x72: 22, 0x73: 94, 				# Luigi
		0x80: 70, 0x81: 112, 0x82: 3, 0x83: 23, 0x84: 53, 		# Mario - 0x8
		0x90: 38, 0x91: 85, 0x92: 46, 0x93: 0, 0x94: 104, 		# Marth
		0xA0: 71, 0xA1: 95, 0xA2: 24, 0xA3: 54, 				# Mewtwo
		0xB0: 72, 0xB1: 113, 0xB2: 25, 0xB3: 55, 				# Ness
		0xC0: 74, 0xC1: 35, 0xC2: 108, 0xC3: 26, 0xC4: 56, 		# Peach
		0xD0: 78, 0xD1: 97, 0xD2: 28, 0xD3: 58, 				# Pikachu
		0xE0: 63, 0xE1: 50, 0xE2: 17, 0xE3: 89, 				# Ice Climbers
		0xF0: 79, 0xF1: 98, 0xF2: 29, 0xF3: 59, 0xF4: 114, 		# Jigglypuff
		0x100: 101, 0x101: 76, 0x102: 9, 0x103: 60, 0x104: 30, 	# Samus - 0x10
		0x110: 116, 0x111: 99, 0x112: 31, 0x113: 115, 0x114: 77, 0x115: 65, 	# Yoshi
		0x120: 117, 0x121: 100, 0x122: 32, 0x123: 61, 0x124: 109, 	# Zelda
		#0x130: , 0x131: , 0x132: , 0x133: , 0x134: , 			# Sheik		# Someday :)
		0x140: 39, 0x141: 86, 0x142: 14, 0x143: 47, 			# Falco
		0x150: 34, 0x151: 82, 0x152: 11, 0x153: 103, 0x154: 6, 	# Young Link
		0x160: 37, 0x161: 84, 0x162: 13, 0x163: 45, 0x164: 8, 	# Doc
		0x170: 64, 0x171: 90, 0x172: 18, 0x173: 51, 0x174: 110, # Roy
		0x180: 75, 0x181: 96, 0x182: 27, 0x183: 57, 			# Pichu - 0x18
		0x190: 41, 0x191: 88, 0x192: 16, 0x193: 49, 0x194: 73 	# Ganondorf
	}

	# These will be shared across CSS files; so if one file checks, they'll all know
	_hasRandomNeutralTables = False
	_checkedForRandomNeutralTables = False

	def validate( self ):

		""" Verifies whether this is actually a CSS file by checking the string table. """

		self.initialize()

		# Check for the expected symbol
		for symbolString in self.stringDict.values():
			if symbolString == 'MnSelectChrDataTable':
				break
		else: # The loop above didn't break; symbol not found
			raise Exception( 'Invalid character select file; MnSelectChrDataTable symbol not found.' )

	def hintRootClasses( self ):

		# Add class hints for structures with known root/reference node labels
		for offset, string in self.rootStructNodes:
			if string == 'MnSelectChrDataTable':
				self.structs[offset] = 'CharSelectScreenDataTable'
				break

	def hasRandomNeutralTables( self ):

		""" Checks the disc and the version of 20XX HP loaded (if any), to see whether 
			the random neutrals stage name pointer tables should be in the file. """

		if self._checkedForRandomNeutralTables:
			return self._hasRandomNeutralTables

		# Nothing to see here if it's not 20XX
		v20XX = self.disc.is20XX
		if not v20XX:
			self._hasRandomNeutralTables = False
			self._checkedForRandomNeutralTables = True
			return False

		# Convert the 20XX game version to a float
		try:
			majorMinor = '.'.join( v20XX.split('.')[:2] ) # Excludes version.patch if present (e.g. 5.0.0)
			normalizedVersion = float( majorMinor.replace( '+', '' ) ) # removes some non-numbers and typecasts it
		except:
			normalizedVersion = 0
		
		if 'BETA' not in v20XX and normalizedVersion >= 4.06: # This version and up use a table in MnSlChr
			self._hasRandomNeutralTables = True
		else:
			self._hasRandomNeutralTables = False

		self._checkedForRandomNeutralTables = True

		return self._hasRandomNeutralTables

	def getRandomNeutralName( self, filename ):

		""" Recognizes stages within the set of 'Random Neutrals' (The sets of 16 stages for each legal neutral stage), 
			and then returns the MnSlChr file offset of the stage name table for the stage in question, as well as the 
			base stage name (e.g. a string of "Dream Land (N64)"). Returns -1 for offset if the stage is not recognized. """

		# Make sure this is applicable
		if not self.hasRandomNeutralTables():
			return ''

		# Parse the file name string for the custom stage index
		fileName, fileExt = os.path.splitext( filename )
		if fileName.startswith( 'GrP' ) and fileName[3] in hexdigits: # For Pokemon Stadium, which follows a slighly different convention (e.g. "GrP2.usd")
			index = int( fileName[-1], 16 )
			nameOffset = self.randomNeutralStageNameTables['GrP'] + 0x50 + ( index * 0x20 )

		elif fileName in self.randomNeutralStageNameTables and fileExt[1] in hexdigits:
			index = int( fileExt[1], 16 )
			nameOffset = self.randomNeutralStageNameTables[fileName] + 0x50 + ( index * 0x20 )

		else:
			return ''

		stageName = self.getData( nameOffset, 0x20 ).split( '\x00' )[0].decode( 'ascii' )

		return stageName

	def setRandomNeutralName( self, filename, newStageName ):

		""" Sets a new stage name string in the respective string table. Only used with 20XX. """

		# Make sure this is applicable
		if not self.hasRandomNeutralTables():
			raise Exception( 'Operation not applicable to this disc' )

		# Parse the file name string for the custom stage index
		fileName, fileExt = os.path.splitext( filename )
		if fileName.startswith( 'GrP' ) and fileName[3] in hexdigits: # For Pokemon Stadium, which follows a slighly different convention (e.g. "GrP2.usd")
			index = int( fileName[-1], 16 )
			nameOffset = self.randomNeutralStageNameTables['GrP'] + 0x50 + ( index * 0x20 )

		elif fileName in self.randomNeutralStageNameTables and fileExt[1] in hexdigits:
			index = int( fileExt[1], 16 )
			nameOffset = self.randomNeutralStageNameTables[fileName] + 0x50 + ( index * 0x20 )
		else:
			raise Exception( 'Operation not applicable for this filename' )

		# Convert the given string to bytes (should have already been validated)
		try:
			nameBytes = bytearray()
			nameBytes.extend( newStageName )
			if len( nameBytes ) > 0x1F:
				raise Exception( 'New stage name is too long after encoding (' + str(len(nameBytes)) + ' bytes).' )
		except Exception as err:
			raise Exception( 'Unable to convert the string to bytes ({})'.format(err) )

		# Add null data to fill the remaining space for this string (erasing pre-existing characters)
		padding = bytearray( 0x20 - len(nameBytes) ) # +1 to byte limit to add the null byte

		self.setData( nameOffset, nameBytes+padding )
		self.recordChange( 'Random Neutral stage name updated for ' + newStageName )

	def checkMaxHexTrackNameLen( self, trackNumber, fileOffset=0 ):

		""" Checks how much space is available for custom names for 20XX hex tracks. 
			Note that these are title names, as seen in the Debug Menu, not file names. 
			These names are the same ones used for music files' "description" property. 
			Pointers to these strings are in the CSS tail data, in a table at 0x3EDDA8. 
			Songs up to hex track 48 are vanilla songs, and their strings are end-to-end, 
			with no extra space for longer names. However, songs beyond that are custom 
			songs with extra padding following their strings, allowing for longer names. """

		if trackNumber < 0 or trackNumber > 0xFF:
			print( 'Unrecognized track ID! ' + hex(trackNumber) )
			return -1

		elif trackNumber < 49: # Original stage string; space for this varies
			if not fileOffset:
				fileOffset = self.getHexTrackNameOffset( trackNumber )
				if not fileOffset:
					return -1

			# Get 0x20 bytes at this offset and look for the stop byte
			data = self.getData( fileOffset, 0x20 )
			return data.index( '\x00' )

		else: # New song; consistent space
			return 0x1F

	def getHexTrackNameOffset( self, trackNumber, addPointerIfNotFound=False ):

		""" The song names for 20XX HP's extra songs, the "Hex Tracks", (i.e. 00.hps, 01.hps, etc.) 
			are stored in this file's tail data, in a table at 0x3EDDA8. This method gets the specified 
			track name's exact offset (relative to data section). Note that these are description/title 
			names, as seen in the Debug Menu, not file names. This will also add a new pointer to the 
			table if one does not already exist, which must be removed if the track is not ultimately added. """

		# Get the pointer for the string name from the pointer table at 0x3edda8
		namePointerOffset = 0x3EDD88 + ( trackNumber * 4 ) # Relative to data section (accounting for no header)
		nameAddress = toInt( self.getData(namePointerOffset, 4) ) # The address of the name string in RAM

		# If this pointer has not been added yet, add it (should be removed again if the track is not added!)
		if nameAddress == 0:
			if not addPointerIfNotFound:
				return 0

			previousAddress = toInt( self.getData(namePointerOffset-4, 4) ) # The address of the name string in RAM
			assert previousAddress != 0, 'Illegal operation; must add hex tracks in order! 0x{:X} does not exist.'.format( trackNumber-1 )

			# Add the new pointer to the table
			print( 'Adding new hex track song name pointer table entry' )
			nameAddress = previousAddress - 0x20
			addressBytes = struct.pack( '>I', nameAddress )
			self.setData( namePointerOffset, addressBytes )
			self.recordChange( 'Hex Track name pointer added for track 0x{:02X}'.format(trackNumber) )

		return nameAddress - 0x80BEC720 - 0x20 # Subtracting the address of this file in RAM and the file header length

	def validateHexTrackNameTable( self ):

		""" Iterates through the pointers in the table used for hex track name/description look-up, 
			and attempts to make sure there are not pointers to non-existant files. Extra data such 
			as pointers beyond the first null pointer, and hex track name strings, are not removed. """

		assert self.disc, 'Unable to validate hex track name table; no disc reference available.'

		# Unpack the pointer values so we can iterate over them
		pointers = struct.unpack( '>256I', self.getData(0x3EDD88, 0x400) )

		for trackNumber, nameAddress in enumerate( pointers ):
			isoPath = '{}/audio/{:02X}.hps'.format( self.disc.gameId, trackNumber )
			hpsFile = self.disc.files.get( isoPath )
			if not hpsFile:
				# There shouldn't be a corresponding pointer
				if nameAddress:
					namePointerOffset = 0x3EDD88 + ( trackNumber * 4 )
					nullPointer = bytearray( 4 )
					self.setData( namePointerOffset, nullPointer )
					self.recordChange( 'Hex Track name pointer removed for track 0x{:02X}'.format(trackNumber) )
				break

	def get20XXHexTrackName( self, trackNumber ):

		""" Retrieves the 20XX Hex Track title name (as seen in the Debug Menu, not file name) from this file. """

		# Get and decode the track name string, which is a max of 31 characters plus a stop byte
		fileOffset = self.getHexTrackNameOffset( trackNumber )
		nameBytes = self.getData( fileOffset, 0x20 ).split( '\x00' )[0]
		return nameBytes.decode( 'ascii' )

	def set20XXHexTrackName( self, trackNumber, newName ):

		""" Sets the 20XX Hex Track name from this file. """

		if trackNumber < 1 or trackNumber > 0xFF:
			raise Exception( 'Invalid track ID given to .set20XXHexTrackName(): ' + uHex( trackNumber ) )

		fileOffset = self.getHexTrackNameOffset( trackNumber, True )
		byteLimit = self.checkMaxHexTrackNameLen( trackNumber, fileOffset )
		
		# Convert the given string to bytes (failsafe; should have already been validated)
		try:
			nameBytes = bytearray()
			nameBytes.extend( newName )
		except Exception as err:
			print( 'Unable to convert the song name to bytes; ' + str(err) )
			raise Exception( 'Unable to convert the string to bytes' )

		if len( nameBytes ) > byteLimit:
			raise Exception( 'New song name is too long after encoding ({} bytes).'.format(len(nameBytes)) )

		# Add null data to fill the remaining space for this string (erasing pre-existing characters)
		padding = bytearray( byteLimit + 1 - len(nameBytes) ) # +1 to add the null byte

		self.setData( fileOffset, nameBytes+padding )
		self.recordChange( 'Hex Track name updated for {} (track 0x{:02X})'.format(newName, trackNumber) )

	def getCsp( self, charId, costumeId ):

		""" Returns a CSP texture as an ImageTk.PhotoImage """

		# Translate Sheik to Zelda
		if charId == 0x13:
			charId = 0x12

		# Get the index of this Char/Costume CSP in the file
		indexKey = charId * 0x10 | costumeId
		cspIndex = self.cspIndexes[indexKey]

		# Calculate the offset of the CSP texture and get the texture there
		cspOffset = self.cspBaseOffset + ( cspIndex * self.cspStride ) - 0x20
		return self.getTexture( cspOffset, 136, 188, 9 )

	def importCsp( self, filepath, charId, costumeId, textureName='' ):

		""" Use the character and costume IDs to look up the texture offset, 
			and import the given texture to that location in the file. 
			Same return information as .setTexture() """

		# Translate Sheik to Zelda
		if charId == 0x13:
			charId = 0x12

		# Get the index of this Char/Costume CSP in the file
		indexKey = charId * 0x10 | costumeId
		cspIndex = self.cspIndexes[indexKey]
		
		if not textureName:
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

		# Calculate the offset of the CSP texture and import the texture there
		cspOffset = self.cspBaseOffset + ( cspIndex * self.cspStride ) - 0x20
		returnInfo = self.setTexture( cspOffset, None, None, filepath, textureName, 1 )

		return returnInfo

	def get20xxVersion( self ):

		""" Checks this file to see if it's for the 20XX Training Hack Pack, and gets its version if it is. 
			The returned value will be a string of the version number, or an empty string if it's not 20XX.
			The version string went through many different variations over the years; return values may be:
				
			3.02, 3.02.01, 3.03, BETA 01, BETA 02, BETA 03, BETA 04, 4.07+, 4.07++, or [majorVersion].[minorVersion] """

		is20XX = ''

		# Check the file length of MnSlChr (the CSS); if it's abnormally larger than vanilla, it's 20XX post-v3.02
		cssData = self.getData()
		fileSize = toInt( cssData[:4] )

		if fileSize > 0x3A2849: # Comparing against the vanilla file size.
			# Isolate a region in the file that may contain the version string.
			versionStringRange = cssData[0x3a4cd0:0x3a4d00]

			# Create a bytearray representing "VERSION " to search for in the region defined above
			versionBytes = bytearray.fromhex( '56455253494f4e20' ) # The hex for "VERSION "
			versionStringPosition = findBytes( versionStringRange, versionBytes )

			if versionStringPosition != -1: # The string was found
				versionValue = versionStringRange[versionStringPosition+8:].split(b'\x00')[0].decode( 'ascii' )

				if versionValue == 'BETA': # Determine the specific beta version; 01, 02, or 03 (BETA 04 identified separately)
					firstDifferentByte = cssData[0x3a47b5]

					if firstDifferentByte == 249 and hexlify( cssData[0x3b905e:0x3b9062] ) == '434f4445': # Hex for the string "CODE"
						versionValue += ' 01'
					elif firstDifferentByte == 249: versionValue += ' 02'
					elif firstDifferentByte == 250: versionValue += ' 03'
					else: versionValue = ''

				elif versionValue == 'BETA04': versionValue = 'BETA 04'
				
				is20XX = versionValue

			elif fileSize == 0x3a5301: is20XX = '3.03'
			elif fileSize == 0x3a3bcd: is20XX = '3.02.01' # Source: https://smashboards.com/threads/the-20xx-melee-training-hack-pack-v4-05-update-3-17-16.351221/page-68#post-18090881

		elif cssData[0x310f9] == 0x33: # In vanilla Melee, this value is '0x48'
			is20XX = '3.02'

		return is20XX


class SssFile( DatFile ):

	""" Special subclass for the Stage Select Screen. """

	def validate( self ):

		""" Verifies whether this is actually a SSS file by checking the string table. """

		self.initialize()

		# Check for the expected symbol
		for symbolString in self.stringDict.values():
			if symbolString == 'MnSelectStageDataTable':
				break
		else: # The loop above didn't break; symbol not found
			raise Exception( 'Invalid stage select file; MnSelectStageDataTable symbol not found.' )


#class EffectsFile( DatFile ):

	# Shared Effects files:
	#
	# EfMrData:		Mario & Dr. Mario
	# EfFxData:		Fox & Falco
	# EfIcData:		Popo & Nana
	# EfZdData:		Zelda & Sheik
	# EfLkData:		Link & Y. Link
	# EfPkData:		Pikachu & Pichu


class SisFile( DatFile ):

	""" For 'pre-made' menu text files. """

	# Random Stage Select Screen pointer table lookup; correlates a pointer index to a stage string struct
	RSSS_pointerLookup = [ # indexed by int stage ID, value = SIS ID (pointer table index)
		-1, # 0x00 - Dummy
		-1, # 0x01 - TEST
		8, # 0x02 - Princess Peach's Castle
		15, # 0x03 - Rainbow Cruise
		9, # 0x04 - Kongo Jungle
		16, # 0x05 - Jungle Japes
		17, # 0x06 - Great Bay
		18, # 0x07 - Hyrule Temple
		10, # 0x08 - Brinstar
		19, # 0x09 - Brinstar Depths
		12, # 0x0A - Yoshi's Story
		20, # 0x0B - Yoshi's Island
		6, # 0x0C - Fountain of Dreams
		21, # 0x0D - Green Greens
		11, # 0x0E - Corneria
		26, # 0x0F - Venom
		7, # 0x10 - Pokemon Stadium
		27, # 0x11 - Poke Floats
		14, # 0x12 - Mute City
		28, # 0x13 - Big Blue
		13, # 0x14 - Onett
		22, # 0x15 - Fourside
		29, # 0x16 - Icicle Mountain
		-1, # 0x17 - Unused?
		23, # 0x18 - Mushroom Kingdom
		24, # 0x19 - Mushroom Kingdom II
		-1, # 0x1A - Akaneia (Deleted Stage)
		31, # 0x1B - Flat Zone
		34, # 0x1C - Dream Land (N64)
		35, # 0x1D - Yoshi's Island (N64)
		36, # 0x1E - Kongo Jungle (N64)
		-1, # 0x1F - Mushroom Kingdom Adventure
		-1, # 0x20 - Underground Maze
		-1, # 0x21 - Brinstar Escape Shaft
		-1, # 0x22 - F-Zero Grand Prix
		-1, # 0x23 - TEST; In other words, not used (same as 0x01)
		32, # 0x24 - Battlefield
		33  # 0x25 - Final Destination
	]
	# See here for details on the string format opCodes: 
	#			https://github.com/Ploaj/HSDLib/blob/master/HSDRaw/Tools/Melee/MeleeMenuText.cs 

	def validate( self ):

		""" Verifies whether this is actually a menu text file by checking the string table. """

		self.initialize()

		# Check for a SIS data table symbol
		for symbolString in self.stringDict.values():
			if symbolString.startswith( 'SIS_' ):
				break
		else: # The loop above didn't break; no SIS string found
			raise Exception( 'Invalid menu text file; no SIS_ symbol node found.' )

	def getTextStruct( self, sisId ):

		""" Uses the SIS data table to look up a pointer to the target struct. """

		self.initialize()

		# Get the text struct
		sisTable = self.initGenericStruct( 0, structDepth=(3, 0), asPointerTable=True )
		textStructOffset = sisTable.getValues()[sisId]

		return self.initDataBlock( hsdStructures.DataBlock, textStructOffset )

	def getText( self, sisId ):

		textStruct = self.getTextStruct( sisId )

		if self.ext == '.dat':
			specialCharDict = globalData.SdCharacters_2
		else: # For .usd files
			specialCharDict = globalData.SdCharacters_1

		# Parse the text struct's data for the text string
		chars = []
		byte = textStruct.data[0]
		position = 0
		while byte: # Breaks on byte value of 0, or no byte remaining
			if byte == 0x3:
				chars.append( '\n' ) # Line break
				position += 1
			elif byte == 0x5: # Text Pause; the next short is for this opCode
				position += 3
			elif byte == 0x6: # Fade-in; the next 2 shorts are for this opCode
				position += 5
			elif byte == 0x7: # Offset; the next 2 shorts are for this opCode
				position += 5
			elif byte == 0xA: # Kerning (was SCALING); the next 2 shorts are for this opCode
				position += 5
			elif byte == 0xC: # Color; the next 3 bytes are for this opCode
				position += 4
			elif byte == 0xE: # Scaling (was SET_TEXTBOX); the next 2 shorts are for this opCode
				position += 5
			elif byte == 0x1A:
				chars.append( ' ' ) # Space
				position += 1
			elif byte == 0x20: # Regular characters (from DOL)
				key = '20{:02x}'.format( textStruct.data[position+1] )
				char = globalData.DolCharacters.get( key, '?' )
				chars.append( char )
				position += 2
			elif byte == 0x40: # Special characters (from this file)
				key = '40{:02x}'.format( textStruct.data[position+1] )
				char = specialCharDict.get( key, '?' )
				chars.append( char )
				position += 2
			else:
				position += 1
			
			if position >= len( textStruct.data ):
				break
			else:
				byte = textStruct.data[position]

		return ''.join( chars )

	def setText( self, sisId, newText, description='', endBytes=b'\x00' ):

		textStruct = self.getTextStruct( sisId )

		if self.ext == '.dat':
			specialCharDict = globalData.SdCharacters_2
		else: # For .usd files
			specialCharDict = globalData.SdCharacters_1

		# Convert the given stage menu text to bytes and add the ending bytes
		byteStrings = []
		for char in newText:
			sBytes = reverseDictLookup( globalData.DolCharacters, char )

			# Check special characters (defined in this file) if a normal one wasn't found (defined in the DOL)
			if not sBytes:
				sBytes = reverseDictLookup( specialCharDict, char, defaultValue='20eb' ) # Default to question mark
			
			byteStrings.append( sBytes )
		hexString = ''.join( byteStrings )
		textData = bytearray.fromhex( hexString ) + endBytes

		# Add space to the file structure, if needed, and add padding to the string data to fill the remaining structure space
		textStartRelOffset = textStruct.data.find( b'\x20' ) # Exclude formatting preceding the text
		requiredStructLength = textStartRelOffset + len( textData )
		stringFileOffset = textStruct.offset + textStartRelOffset
		if requiredStructLength > textStruct.length:
			extraSpaceNeeded = requiredStructLength - textStruct.length
			self.extendDataSpace( stringFileOffset, extraSpaceNeeded )
			
			# Add padding to overwrite the data shifted above as well (the above method will round to nearest 0x20 bytes)
			amountAdjustment = 0x20 - ( extraSpaceNeeded % 0x20 )
			textData += bytearray( amountAdjustment )
		elif textStruct.length > requiredStructLength:
			paddingLength = textStruct.length - requiredStructLength
			textData += bytearray( paddingLength )

		# Save the string data to file
		if not description:
			description = u'Updated "{}" text (SIS ID 0x{:X})'.format( newText, sisId )
		self.updateData( stringFileOffset, textData, description )

	def getStageMenuName( self, intStageId ):

		""" Gets the stage name for a given internal stage ID to be displayed on the Random Stage Select Screen. """

		# Get the text struct pointer
		sisId = self.RSSS_pointerLookup[intStageId]
		assert sisId > 0, 'Invalid stage ID given to SIS file stage name look-up: ' + str( sisId )
		
		return self.getText( sisId )

	def setStageMenuName( self, intStageId, newName ):

		""" Sets the stage name for a given internal stage ID to be displayed on the Random Stage Select Screen. """

		# Get the text struct pointer and struct
		sisId = self.RSSS_pointerLookup[intStageId]
		assert sisId > 0, 'Invalid stage ID given to SIS file stage name look-up: ' + str( sisId )

		self.setText( sisId, newName, 'Updated stage name for ' + newName, b'\x0F\x00' )

	def identifyTextures( self ):

		""" Returns a list of tuples containing texture info. Each tuple is of the following form: 
				( imageDataOffset, imageHeaderOffset, paletteDataOffset, paletteHeaderOffset, width, height, imageType, mipmapCount ) """

		self.initialize()

		# Get the first pointer in the SIS table
		sisTable = self.initGenericStruct( 0, asPointerTable=True )
		imageDataStart = sisTable.getValues()[0]

		# Check whether this points to a valid struct (some don't!)
		imageDataLength = self.getStructLength( imageDataStart )
		if imageDataLength < 0x200 or imageDataStart >= self.headerInfo['rtStart']:
			return []

		imageDataEnd = imageDataStart + imageDataLength
		texturesInfo = []

		for imageDataOffset in range( imageDataStart, imageDataEnd, 0x200 ):
			texturesInfo.append( (imageDataOffset, -1, -1, -1, 32, 32, 0, 0) )

		return texturesInfo


class StageFile( DatFile ):

	""" Subclass of .dat and .usd files, specifically for stage files. """
	
	def __init__( self, *args, **kwargs ):
		DatFile.__init__( self, *args, **kwargs )

		self.shortName = ''
		self.longName = ''

		self._externalId = -1 # External Stage ID
		self._internalId = -1 # Internal Stage ID
		self._randomNeutralChecked = False
		self._isRandomNeutralStage = False
		self._stageInfoStruct = None
		self._randomNeutralId = -1

	@property
	def externalId( self ):

		""" Gets the stage's external ID from the first entry in its Music Table struct. """

		if self._externalId == -1:
			# Make sure file data has been retrieved, and contents sufficiently parsed
			self.initialize()

			# Get and return the first value in the music table struct
			musicTableStruct = self.getMusicTableStruct()
			self._externalId = musicTableStruct.getValues()[0]

		return self._externalId

	@property
	def internalId( self ):

		""" Converts the external ID from within this file to an internal ID via DOL table lookup. """

		if self._internalId == -1:
			assert self.disc, 'Unable to get stage internal ID without a disc/dol reference.'
			dol = self.disc.dol
			self._internalId = dol.getIntStageIdFromExt( self.externalId )

		return self._internalId

	@property
	def randomNeutralId( self ):
		if not self.isRandomNeutral():
			return -1
		else:
			return self._randomNeutralId

	@property
	def initFunction( self ):
		self.getStageInfoStruct()
		return self._stageInfoStruct.getValues( 'StageInit_Function_Pointer' )

	@property
	def onGoFunction( self ):
		self.getStageInfoStruct()
		return self._stageInfoStruct.getValues( 'OnGo_Function_Pointer' )

	def validate( self ):

		""" Verifies whether this is actually a stage file by checking the string table. """

		self.initialize()

		if 'map_head' not in self.stringDict.values():
			raise Exception( 'Invalid stage file; no "map_head" symbol node found.' )

	def hintRootClasses( self ):

		validated = False

		# Add class hints for structures with known root/reference node labels
		for offset, string in self.rootStructNodes:
			if string == 'map_head':
				validated = True
				self.structs[offset] = 'MapHeadObjDesc'
			elif string == 'coll_data':
				self.structs[offset] = 'MapCollisionData'
			elif string == 'grGroundParam':
				self.structs[offset] = 'MapGroundParameters'

		if not validated:
			raise Exception( 'Invalid stage file; no "map_head" symbol node found.' )

	def getStageInfoStruct( self ):

		""" Looks up and initializes a structure in the DOL containing info on this stage. """

		if not self._stageInfoStruct:
			assert self.disc, 'Unable to get stage info struct without a disc/dol reference.'
			dol = self.disc.dol
			
			# Unpack the DOL's stage info pointer table if it has not already been done
			if not dol._stageInfoStructPointers:
				pointerTableData = dol.getData( 0x3DCEDC, 0x6F*4 )
				dol._stageInfoStructPointers = struct.unpack( '>111I', pointerTableData )

			# Get this stage's external/internal IDs, and offset of the stage info struct in the DOL
			if self._internalId == -1:
				self._internalId = dol.getIntStageIdFromExt( self.externalId )
			stageStructPointer = dol._stageInfoStructPointers[self._internalId]
			structOffset = dol.offsetInDOL( stageStructPointer )

			# Init and store the stage info structure
			self._stageInfoStruct = standaloneStructs.StageInfoTable( dol, structOffset )

		return self._stageInfoStruct

	def getMusicTableStruct( self ):

		""" Initializes a structure in this file containing info on this stage's music options. """

		grGroundParamStruct = self.getStructByLabel( 'grGroundParam' )
		musicTableOffset = grGroundParamStruct.getValues( 'Music_Table_Pointer' )

		return self.getStruct( musicTableOffset )

	def isRandomNeutral( self ):

		""" Modern versions of 20XX (4.06+) have multiple variations of each neutral stage, the 'Random Neutrals' (e.g. GrSt.0at through GrSt.eat).
			This method simply checks whether or not is one of these stages. """

		if not self.disc.is20XX: # This would have been checked when the disc was loaded, before initializing the filesystem
			return False

		# Shortcut, in case it's already been checked (which it probably has if it was loaded in the Disc File Tree)
		elif self._randomNeutralChecked:
			return self._isRandomNeutralStage

		longName = ''

		# Check for Stadium first, since that stage's file naming is handled differently
		if self.filename.startswith( 'GrP' ) and self.filename[3] in hexdigits: # Latter part checking for, e.g., "GrP2.usd"
			self._randomNeutralId = int( self.filename[3], 16 )
			shortName = 'GrP'
			longName = 'Pokemon Stadium'

		# Check the other tournament neutral stages
		elif self.ext[1] in hexdigits: # e.g. a file extension of ".2at"
			self._randomNeutralId = int( self.ext[1], 16 )
			stageNameLookup = { 'GrNBa': 'Battlefield', 
								'GrNLa': 'Final Destination', 
								'GrSt': "Yoshi's Story", 
								'GrIz': 'Fountain of Dreams [Izumi]', 
								'GrOp': 'Dream Land (N64)' }

			for shortName, fullName in stageNameLookup.items():
				if self.filename.startswith( shortName ):
					longName = fullName
					break

		# If we have a longname, the file matched with a key stage name above (and has 
		# something like a .2at file extension), and thus should be a Random Neutral.
		if longName:
			self._isRandomNeutralStage = True
			self.shortName = shortName
			self.longName = longName
		else:
			self._isRandomNeutralStage = False

		self._randomNeutralChecked = True
		
		return self._isRandomNeutralStage

	def getDescription( self ):

		""" Attempts to find a description for this file using multiple methods:
			 -> Check the yaml from the File Descriptions folder for the current Game ID
			 -> If 20XX, check for 'Random Neutrals' stage names (contained within the CSS)
			 -> Check for any other special 20XX stage files
			 -> Check if it's a Target Test stage
			 -> Check other vanilla file names """
			 
		self._shortDescription = ''
		self._longDescription = ''

		# Try to recognize stages within the set of 'Random Neutrals' (The sets of 16 stages for each legal neutral stage)
		if self.isRandomNeutral():
			# Get the CSS file (which may contain random neutral names)
			try:
				cssFile = self.disc.files[self.disc.gameId + '/MnSlChr.0sd']
				self._shortDescription = cssFile.getRandomNeutralName( self.filename )

				if self._shortDescription:
					self._longDescription = self.longName + ', ' + self._shortDescription

			except Exception as err:
				print( 'Unable to get Random Neutral stage name from CSS file; {}'.format(err) )
			
			return
		
		# Check if there's a file explicitly defined in the file descriptions config file
		stageName = self.yamlDescriptions.get( self.filename, '' )

		# If this is a usd file, check if there's a dat equivalent description
		if not stageName and self.ext == '.usd':
			filenameOnly = os.path.splitext( self.filename )[0]
			stageName = self.yamlDescriptions.get( filenameOnly + '.dat', '' )
			if stageName:
				stageName += ' (English)'

		if stageName:
			self._shortDescription = stageName
			self._longDescription = stageName
			return

		# Check for Target Test stages
		elif self.filename[2] == 'T':
			characterName = globalData.charNameLookup.get( self.filename[3:5], '' )

			if characterName:
				if characterName.endswith( 's' ):
					stageName = characterName + "'"
				else:
					stageName = characterName + "'s"
				
				self._shortDescription = stageName
				self._longDescription = stageName + " Target Test stage"

	def setDescription( self, description, gameId='' ):

		""" Sets a description for a file defined in the CSS file, or in the yaml config file, and saves it. 
			Returns these exit codes: 
				0: Success
				1: Unable to save to the description yaml file
				2: Unable to find the CSS file in the disc
				3: Unable to save to the CSS file """

		if self.isRandomNeutral() and self.disc:
			self._shortDescription = description
			self._longDescription = description

			try:
				# Names for these are stored in the CSS file... update it there
				cssFile = self.disc.files[self.disc.gameId + '/MnSlChr.0sd']
				cssFile.setRandomNeutralName( self.filename, description )
				returnCode = 0

			except KeyError:
				msg( 'Unable to find the CSS file (MnSlChr.0sd) in the disc!' )
				return 2

			except Exception as err:
				msg( 'Unable to update the CSS file (MnSlChr.0sd) with the new name; ' + str(err) )
				return 3
		
		else:
			returnCode = super( StageFile, self ).setDescription( description, gameId )

		return returnCode

	def identifyTextures( self ):

		""" Returns a list of tuples containing texture information. Each tuple is of the following form: 
				( imageDataOffset, imageHeaderOffset, paletteDataOffset, paletteHeaderOffset, width, height, imageType, mipmapCount ) """

		self.initialize()

		texturesInfo = []
		
		# tic = time.clock()

		try:
			# Check for particle effect textures
			for offset, string in self.rootNodes:
				if string == 'map_texg':
					structStart = offset
					break
			else: # The above loop didn't break; no effects structure found
				structStart = -1

			if structStart != -1:
				# Get the entry count of the table (number of table pointers it contains), and the entries themselves
				mainTableEntryCount = toInt( self.data[structStart:structStart+4] )
				headerTableData = self.data[structStart+4:structStart+4+(mainTableEntryCount*4)]
				headerTablePointers = struct.unpack( '>' + str(mainTableEntryCount) + 'I', headerTableData )

				for pointer in headerTablePointers: # These are all relative to the start of this structure
					# Process the E2E header
					e2eHeaderOffset = structStart + pointer

					textureCount, imageType, _, width, height = struct.unpack( '>5I', self.data[e2eHeaderOffset:e2eHeaderOffset+0x14] )
					imageDataPointersStart = e2eHeaderOffset + 0x18
					imageDataPointersEnd = imageDataPointersStart + ( 4 * textureCount )
					imageDataPointerValues = struct.unpack( '>' + textureCount * 'I', self.data[imageDataPointersStart:imageDataPointersEnd] )

					if imageType == 9:
						paletteDataPointersEnd = imageDataPointersEnd + ( 4 * textureCount )
						paletteDataPointerValues = struct.unpack( '>' + textureCount * 'I', self.data[imageDataPointersEnd:paletteDataPointersEnd] )

					for i, offset in enumerate( imageDataPointerValues ):
						imageDataOffset = structStart + offset

						if imageType == 9:
							# Need to get the palette data's offset too. Its pointer is within a list following the image data pointer list
							paletteDataOffset = structStart + paletteDataPointerValues[i]
							texturesInfo.append( (imageDataOffset, e2eHeaderOffset, paletteDataOffset, e2eHeaderOffset, width, height, imageType, 0) )
						else:
							texturesInfo.append( (imageDataOffset, e2eHeaderOffset, -1, -1, width, height, imageType, 0) )

			# Call the original DatFile method to check for the usual texture headers
			texturesInfo.extend( super(StageFile, self).identifyTextures() )
			
		except Exception as err:
			print( 'Encountered an error during texture identification: {}'.format(err) )
		
		# toc = time.clock()
		# print 'image identification time:', toc - tic

		# Sort the texture info tuples by offset
		texturesInfo.sort()

		return texturesInfo

