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

# DTW's Structural Analysis tab or the following thread/post are useful for more details on structures:
# 		https://smashboards.com/threads/melee-dat-format.292603/post-21913374

import struct
import codecs
import os, sys
import time, math
import tkMessageBox
import ruamel.yaml
from PIL import Image, ImageTk

# Internal dependencies
import globalData
import hsdStructures
from tplCodec import TplDecoder, TplEncoder
from basicFunctions import uHex, msg, printStatus, createFolders



					# = ---------------------------- = #
					#  [   Disc Base File Classes   ]  #
					# = ---------------------------- = #

class FileBase( object ):

	""" This is a superclass to every other [non-disc] file class. """

	yamlDescriptions = {}

	def __init__( self, disc, offset, size, isoPath, description='', extPath='', source='disc' ):

		self.ext = os.path.splitext( isoPath )[1].lower()		# File extension. Includes '.' (dot)
		self.disc = disc
		self.size = size				# Current size of the file in bytes
		self.data = bytearray()
		self.readOnly = False
		self.source = source			# One of 'disc', 'file' (external file), or 'self' (exists only in memory)
		self.offset = offset			# Disc offset. An offset of -1 indicates a file not yet given a location
		self.isoPath = isoPath			# e.g. 'GALE01/audio/1padv.ssm' if this is for a file in a disc
		self.extPath = extPath			# External path. I.e. a full (absolute) system file path if this is a standalone file
		self.origSize = size			# Should always be the original size of the file (even if its data changes size)
		self._shortDescription = description
		self._longDescription = description
		self.unsavedChanges = []		# Detailed list of all specific changes to this file

		if isoPath:
			self.filename = os.path.basename( isoPath )		# Includes file extension
		elif extPath:
			if size == -1:
				self.size = self.origSize = os.path.getsize( extPath )
			self.filename = os.path.basename( extPath )		# Includes file extension
		else:
			raise Exception( 'Invalid input to initialize file; no isoPath or extPath given.' )

		if disc:
			# Add this file to the disc's file dictionary
			assert isoPath, 'No isoPath given to disc file {}!'.format( self.filename )
			disc.files[isoPath] = self

	@property
	def shortDescription( self ):
		if not self._shortDescription:
			self.getDescription()
		
		return self._shortDescription

	@shortDescription.setter
	def shortDescription( self, newDesc ):
		self._shortDescription = newDesc

	@property
	def longDescription( self ):
		if not self._longDescription:
			self.getDescription()
		
		return self._longDescription

	@longDescription.setter
	def longDescription( self, newDesc ):
		self._longDescription = newDesc

	@classmethod
	def setupDescriptions( cls, gameId ):

		""" Attempts to load file descriptions from a file in './File Descriptions/[gameID].yaml'
			Should only occur once; typically after a disc file or root folder has been instantiated as a disc,
			but before the disc has been loaded into the GUI. """

		descriptionsFile = os.path.join( globalData.scriptHomeFolder, 'File Descriptions', gameId + '.yaml' )
		
		try:
			with codecs.open( descriptionsFile, 'r', encoding='utf-8' ) as stream: # Using a different read method to accommodate UTF-8 encoding
			#with codecs.open( descriptionsFile, 'r' ) as stream: # Using a different read method to accommodate UTF-8 encoding
				#cls.yamlDescriptions = ruamel.yaml.safe_load( stream ) # Vanilla yaml module method (loses comments when saving/dumping back to file)
				cls.yamlDescriptions = ruamel.yaml.load( stream, Loader=ruamel.yaml.RoundTripLoader )
		except IOError: # Couldn't find the file
			printStatus( "Couldn't find a yaml config file for " + gameId, warning=True )
		except Exception as err: # Problem parsing the file
			msg( 'There was an error while parsing the yaml config file:\n\n{}'.format(err) )

	def getData( self, dataOffset=0, dataLength=-1 ):

		""" Gets and returns binary data for this file (also storing it to .data for future use). 
			If no arguments are given, the whole file's data is returned. 
			If only an offset is given, the data length is assumed to be 1. """

		if not self.data:
			try:
				if self.source == 'disc':
					assert self.offset != -1, 'Unable to get file data for {}; disc offset has not been set'.format( self.filename )
					
					# Open the disc image and retrieve the binary for the target file.
					with open( self.disc.filePath, 'rb' ) as isoBinary:
						isoBinary.seek( self.offset )
						self.data = bytearray( isoBinary.read(self.size) )

				elif self.source == 'file':
					with open( self.extPath, 'rb' ) as externalFile:
						self.data = bytearray( externalFile.read() )

					# Set size & origSize if uninitialized
					if self.size == -1:
						self.size = len( self.data )
					if self.origSize == -1:
						self.origSize = self.size

				else: # Source must be 'self'
					return bytearray()
			
			except IOError:
				msg( "Unable to read the source file. Be sure that the path to it is "
					 "correct and that the file hasn't been moved, renamed, or deleted." )
			except Exception as err:
				msg( "Unable to read the source file; {}".format(err) )
				
		# Return all of the data if no args were given
		if dataOffset == 0 and dataLength == -1:
			return self.data

		# Assume data length of 1 if it's still -1
		if dataLength == -1:
			dataLength = 1

		return self.data[ dataOffset:dataOffset+dataLength ]

	def setData( self, dataOffset, newData ):

		""" Directly updates (replaces) data in this file. The data input should be a single int (if the data 
			is only one byte) or a bytearray. Unlike with DAT files (which override this), the offset in this 
			case is relative to the start of the file. Does not record the change to self.unsavedChanges. """

		assert not self.readOnly, 'Warning! Attempting to edit data of a read-only file ({})! You should probably make a copy of this file first.'.format( self.filename )

		if type( newData ) == int: # Just a single byte/integer value (0-255)
			assert newData >= 0 and newData < 256, 'Invalid input to FileBase.setData(): ' + str(newData)
			newData = ( newData, ) # Need to make it an iterable, for the splicing operation
			dataLength = 1
		else:
			dataLength = len( newData )

		assert dataOffset + dataLength <= len( self.data ), '0x{:X} is too much data to set at offset 0x{:X}.'.format( dataLength, dataOffset )
		self.data[dataOffset:dataOffset+dataLength] = newData # This will also work for bytearrays of length 1

	def getString( self, offset, dataLength=0x40 ):

		return self.getData( offset, dataLength ).split( b'\x00' )[0].decode( 'ascii' )

	def recordChange( self, description ):

		#self.source = 'self'

		if description not in self.unsavedChanges:
			self.unsavedChanges.append( description )

		# If the Disc File Tree is present, indicate this file has changes waiting to be saved there
		if globalData.gui and globalData.gui.discTab:
			globalData.gui.discTab.isoFileTree.item( self.isoPath, tags='changed' )

	def export( self, savePath ):

		""" Simple method to export this file's data (regardless of source) to
			an external/standalone file. Returns True/False depending on success. """

		try:
			# Make sure the folders exist for the given output path
			createFolders( os.path.split(savePath)[0] )

			# Save the data to a new file.
			with open( savePath, 'wb' ) as newFile:
				newFile.write( self.getData() )

			return True

		except Exception as err:
			printStatus( 'An error occurred while exporting {}: {}'.format(self.filename, err), error=True )
			return False

	def getDescription( self ):

		""" Gets a file description; attempts to pull from the GALE01 yaml, or dynamicallys build it. """

		self._shortDescription = ''
		self._longDescription = ''

		try:
			# Check if there's a file explicitly defined in the file descriptions config file
			description = self.yamlDescriptions.get( self.filename, '' )

			# If this is a usd file, check if there's a dat equivalent description
			if not description and self.ext == '.usd' and not self.filename.startswith( 'PlCa' ): # Excluding Falcon's red costume
				filenameOnly = os.path.splitext( self.filename )[0]
				description = self.yamlDescriptions.get( filenameOnly + '.dat', '' )
				if description:
					description += ' (English)'

			if description:
				self._shortDescription = description
				self._longDescription = description
				return

			else: # Let's see if we can dynamically build one
				if self.filename.startswith( 'Ef' ): # Effects files
					charAbbr = self.filename[2:4]
					if charAbbr == 'Fx':
						charName = 'Fox & Falco'
					else:
						charName = globalData.charNameLookup.get( charAbbr, 'Unknown ({})'.format(charAbbr) )
					self._shortDescription = charName
					self._longDescription = 'Effects file for ' + charName
				elif self.filename.startswith( 'GmRegend' ): # Congratulations screens
					#if not inConvenienceFolder: description = 'Congratulations screen'
					self._shortDescription = 'Congratulations screen'
					self._longDescription = 'Congratulations screen'
				elif self.filename.startswith( 'GmRstM' ): # Results screen animations
					# if inConvenienceFolder: description = globalData.charNameLookup.get( self.filename[6:8], '' )
					# else: description = 'Results screen animations for ' + globalData.charNameLookup.get( self.filename[6:8], '' )
					charAbbr = self.filename[6:8]
					charName = globalData.charNameLookup.get( charAbbr, 'Unknown ({})'.format(charAbbr) )
					self._shortDescription = charName
					self._longDescription = 'Results screen animations for ' + charName
				elif self.filename.startswith( 'MvEnd' ): # 1-P Ending Movies
					#if not inConvenienceFolder: description = '1-P Ending Movie'
					self._shortDescription = '1-P Ending Movie'
					self._longDescription = '1-P Ending Movie'
				elif self.filename.startswith( 'Pl' ):
					charAbbr = self.filename[2:4]
					colorKey = self.filename[4:6]
					charName = globalData.charNameLookup.get( charAbbr, 'Unknown ({})'.format(charAbbr) )

				# 	if charName:
				# 		color = globalData.charColorLookup.get( colorKey, '' )

				# 		if inConvenienceFolder: # No need to show the name, since it's already displayed
				# 			description = ''
				# 		elif charName.endswith('s'):
				# 			description = charName + "' "
				# 		else:
				# 			description = charName + "'s "
					if charName.endswith( 's' ):
						self._longDescription = charName + "' "
					else:
						self._longDescription = charName + "'s "

				# 		if color: # It's a character costume (model & textures) file
				# 			description += color + ' costume'
				# 			if self.ext == '.lat' or colorKey == 'Rl': description += " ('L' alt)" # For 20XX
				# 			elif self.ext == '.rat' or colorKey == 'Rr': description += " ('R' alt)"
					if colorKey == '.d': self._shortDescription == 'NTSC data & shared textures' # e.g. "PlCa.dat"
					elif colorKey == '.p': self._shortDescription == 'PAL data & shared textures'
					elif colorKey == '.s': self._shortDescription == 'SDR data & shared textures'
					elif colorKey == 'AJ': self._shortDescription == 'animation data'
					elif colorKey == 'Cp': # Kirb's copy abilities
						copyChar = globalData.charNameLookup.get( self.filename[6:8], '' )
						if ']' in copyChar: copyChar = copyChar.split( ']' )[1]
						self._shortDescription == "copy power textures (" + copyChar + ")"
					elif colorKey == 'DV': self._shortDescription == 'idle animation data'
					else: self._shortDescription = ''

					# Ensure the first word is capitalized
					#if self._shortDescription and inConvenienceFolder:
					if self._shortDescription:
						self._shortDescription = self._shortDescription[0].upper() + self._shortDescription[1:]

					self._longDescription += self._shortDescription

		except Exception as err:
			#description = ''
			self._shortDescription = ''
			self._longDescription = ''
			printStatus( 'Error in getting a description for {}; {}'.format(self.filename, err), error=True )
			
		#self.description = description.encode( 'utf-8' )
		# if description:
		# 	self.description = description

		#return self.description

	def setDescription( self, description, gameId='' ):

		""" Sets a description for a file defined in the yaml config file, and saves it. 
			Returns an exit code of 0 for success, or 1 for failure. """

		if not gameId:
			assert self.disc, 'No discId provided to set yaml file description!'
			gameId = self.disc.gameId

		#self.description = description
		self._shortDescription = description
		self._longDescription = description
		self.yamlDescriptions[self.filename] = description

		descriptionsFile = os.path.join( globalData.scriptHomeFolder, 'File Descriptions', gameId + '.yaml' )

		try:
			with codecs.open( descriptionsFile, 'w', encoding='utf-8' ) as stream:
				#ruamel.yaml.safe_dump( self.yamlDescriptions, stream ) # Vanilla yaml module method (loses comments when saving/dumping back to file)
				ruamel.yaml.dump( self.yamlDescriptions, stream, Dumper=ruamel.yaml.RoundTripDumper )
			return 0
		except Exception as err: # Problem parsing the file
			msg( 'Unable to save the new name to the yaml config file:\n\n{}'.format(err) )
			return 1

	def validate( self ):

		""" Verifies whether this file is of a specific type.
			Expected to be overridden by subclasses with specific checks. """


class BootBin( FileBase ):

	""" First file in the disc; boot.bin. """
	
	def __init__( self, *args, **kwargs ):
		FileBase.__init__( self, *args, **kwargs )

	@property
	def imageName( self ):
		titleBytes = self.getData( 0x20, 0x3E0 ).split( '\x00' )[0]
		return titleBytes.decode( 'utf-8' )

	@imageName.setter
	def imageName( self, name ):
		# Convert the name string to a bytearray
		nameBytes = bytearray()
		nameBytes.extend( name )

		# Truncate if too long
		if len( nameBytes ) > 0x3E0:
			nameBytes = nameBytes[:0x3E0]

		self.setData( 0x20, nameBytes )


class BannerFile( FileBase ):

	""" Subclass for opening.bnr GCM disc files, which contain the 
		disc banner and certain title and maker information. """

	def __init__( self, *args, **kwargs ):
		FileBase.__init__( self, *args, **kwargs )

		# Determine encoding, prioritizing a given encoding, if present, or disc info
		if 'encoding' in kwargs:
			self.encoding = kwargs.pop( 'encoding' )
		elif self.disc and self.disc.countryCode == 1:
			self.encoding = 'latin_1'
		elif self.disc:
			self.encoding = 'shift_jis'
		else:
			self.encoding = 'latin_1'

	@property
	def shortTitle( self ):
		titleBytes = self.getData( 0x1820, 0x20 ).split( '\x00' )[0]
		return titleBytes.decode( self.encoding )

	@property
	def shortMaker( self ):
		titleBytes = self.getData( 0x1840, 0x20 ).split( '\x00' )[0]
		return titleBytes.decode( self.encoding )

	@property
	def longTitle( self ):
		titleBytes = self.getData( 0x1860, 0x40 ).split( '\x00' )[0]
		return titleBytes.decode( self.encoding )

	@property
	def longMaker( self ):
		titleBytes = self.getData( 0x18A0, 0x40 ).split( '\x00' )[0]
		return titleBytes.decode( self.encoding )

	def validate( self ):

		""" Checks the first 4 bytes of the file for a magic word. """

		magicWord = self.getData( 0, 0x4 )

		#return ( magicWord == bytearray(b'BNR1') or magicWord == bytearray(b'BNR2') )
		if not magicWord == bytearray( b'BNR1' ) and not magicWord == bytearray( b'BNR2' ):
			raise Exception( 'Invalid banner file; no magic word of BNR1|BNR2.' )


					# = ------------------------- = #
					#  [   DAT File Base Class   ]  #
					# = ------------------------- = #

class DatFile( FileBase ):

	""" Subclass for .dat and .usd files. """

	# def __init__( self, disc, offset, size, isoPath, description='', extPath='', source='disc' ):
	# 	#super( DatFile, self ).__init__( self, disc, offset, size, isoPath, description=description, extPath=extPath, source=source )
	# 	FileBase.__init__( self, disc, offset, size, isoPath, description, extPath, source )
		
	def __init__( self, *args, **kwargs ):
		FileBase.__init__( self, *args, **kwargs )

		# File data groups
		self.headerData = bytearray()		# First 0x20 bytes of most DAT files
		self.rtData = bytearray()			# Relocation Table data
		self.nodeTableData = bytearray()	# Root Nodes and Reference Nodes
		self.stringTableData = bytearray()	# String Table data
		self.tailData = bytearray()			# Extra custom/hacked data appearing after then normal end of the file

		# Parsing determinations
		self.headerInfo = {}
		self.stringDict = {}			# Populated by key=stringOffset, value=string (string offset is relative to the string table start)
		self.rootNodes = []				# These node lists will contain tuples of the form ( structOffset, string )
		self.referenceNodes = []
		self.rootStructNodes = []		# This and the next 3 lists' contents are the above lists' entries, but separated by purpose;
		self.rootLabelNodes = []		# into those that point to root structures in the data section (rootStructNodes),
		self.refStructNodes = []		# or those that are just labels to some of those structs (rootLabelNodes).
		self.refLabelNodes = []
		self.pointerOffsets = [] 		# List of file offsets of all pointers in the file, including root/ref node pointers
		self.pointerValues = [] 		# List of values found at the target locations of the above pointers
		self.pointers = []				# Sorted list of (pointerOffset, pointerValue) tuples, useful for looping both together
		self.structureOffsets = []		# A list formed from the above pointerValues list, excluding duplicate entries
		self.orphanStructures = set()	# These are not attached to the rest of the file heirarchy/tree in the usual manner (i.e. no parents)
		self.structs = {}				# key = structOffset, value = HSD structure object
		self.deepDiveStats = {}			# After parsing the data section, this will contain pairs of key=structClassName, value=instanceCount

		self.headerNeedsRebuilding = False
		self.rtNeedsRebuilding = False
		self.nodesNeedRebuilding = False
		self.stringsNeedRebuilding = False

	def initialize( self ):

		""" Separates file data into primary groups (header, data section, rtData, nodeTables, stringTable, tailData), 
			parses the relocation table (RT)/node tables/string table, and sets up pointer and structure offset lists. """

		if self.headerData:
			return # This file has already been initialized!

		# Make sure file data has been loaded
		self.getData()

		# Separate out the file header and parse it
		self.headerData = self.data[:0x20]
		self.data = self.data[0x20:]
		self.parseHeader()
		
		# Other file sections can now be separated out, using information from the header
		stringTableStart = self.headerInfo['stringTableStart']
		self.rtData = self.data[ self.headerInfo['rtStart'] : self.headerInfo['rtEnd'] ]
		self.nodeTableData = self.data[ self.headerInfo['rtEnd'] : stringTableStart ]

		# Parse the RT and String Table
		self.parseRelocationTable()
		stringTableLength = self.parseStringTable()
		
		# Separate out other file sections using the info gathered above
		self.stringTableData = self.data[ stringTableStart : stringTableStart + stringTableLength ]
		self.tailData = self.data[ stringTableStart + stringTableLength : ]
		self.data = self.data[ : self.headerInfo['rtStart'] ]

		# Parse the file's root/reference node tables (must be parsed after parsing the string table)
		self.parseNodeTables()

		# Organize the information parsed above
		self.evaluateStructs()
		self.separateNodeLists()

		# Assign structure class hints on root structures
		self.hintRootClasses()

	def printPath( self ):
		if self.source == 'disc': return self.isoPath
		elif self.source == 'file': return self.extPath
		else: return self.filename

	def parseHeader( self ):

		""" All of the positional values obtained here are relative to the data section (-0x20 from the actual/absolute file offset). """

		filesize, rtStart, rtEntryCount, rootNodeCount, referenceNodeCount = struct.unpack( '>5I', self.headerData[:0x14] )
		rtEnd = rtStart + ( rtEntryCount * 4 )
		rootNodesEnd = rtEnd + ( rootNodeCount * 8 ) # Each root/reference node table entry is 8 bytes

		# Assume no DAT file is larger than 10 MB, or has more than 100 K pointers
		assert filesize <= 10485760, 'Invalid DAT file; unexpectedly large filesize value: ' + str( filesize )
		assert rtEntryCount <= 100000, 'Invalid DAT file; unexpectedly high number of pointers: ' + str( rtEntryCount )

		self.headerInfo = {
			'filesize': filesize,
			'rtStart': rtStart, # Also the size of the data block
			'rtEntryCount': rtEntryCount,
			'rootNodeCount': rootNodeCount,
			'referenceNodeCount': referenceNodeCount,
			'magicNumber': self.headerData[20:24].decode( 'ascii' ),
			'rtEnd': rtEnd,
			'rootNodesEnd': rootNodesEnd,
			'stringTableStart': rootNodesEnd + ( referenceNodeCount * 8 ), # Each root/reference node table entry is 8 bytes
		}

	def parseRelocationTable( self ):

		""" Create a list of all pointer locations in the file, as well as a list of the offset values pointed to by those pointers,
			as described by the relocation table. Each RT entry is a 4-byte integer. """

		try:
			# Convert all entries as 4-byte ints (unpack returns a tuple, but we need a list in order to add to it later)
			unpackFormat = '>{}I'.format( self.headerInfo['rtEntryCount'] )
			self.pointerOffsets = list( struct.unpack(unpackFormat, self.rtData) )
			self.pointerValues = bytearray() # Will only be a bytearray temporarily, during this processing

			for offset in self.pointerOffsets:
				self.pointerValues.extend( self.data[offset:offset+4] )
			self.pointerValues = list( struct.unpack(unpackFormat, self.pointerValues) )

		except Exception as errorMessage:
			self.pointerOffsets = []
			self.pointerValues = []
			raise Exception( 'Unable to parse the DAT file relocation table of {}; {}'.format(self.printPath(), errorMessage) )

	def parseStringTable( self ):

		""" Creates a dictionary for the string table, where keys=dataSectionOffsets, and values=stringLabels. 
			Returns the length of the string table (in bytes), or -1 if there was a parsing error. """

		stringTable = self.data[self.headerInfo['stringTableStart']:] # Can't separate this out beforehand, without knowing its length
		totalStrings = self.headerInfo['rootNodeCount'] + self.headerInfo['referenceNodeCount']

		self.stringDict = {}
		stringTableLength = 0
		strings = stringTable.split( b'\x00' )[:totalStrings] # End splicing eliminates an empty string, and/or extra additions at the end of the file.

		for stringBytes in strings:
			string = stringBytes.decode( 'ascii' ) # Convert the bytearray to a text string
			self.stringDict[stringTableLength] = string
			stringTableLength += len( string ) + 1 # +1 to account for null terminator

		assert stringTableLength > 0, 'Invalid string table length; unable to parse string table.'

		return stringTableLength

	def getStringTableSize( self ):

		""" Need this method (rather than just doing 'header[filesize] - totalFilesize') because 
			there may be extra custom data added after the end of the file. """

		if not self.stringsNeedRebuilding:
			return len( self.stringTableData )

		# Start the size off by accounting for 1 byte for each null-byte terminator
		size = len( self.stringDict )

		for string in self.stringDict.values():
			size += len( string ) # The string is in ascii; 1 byte per character

		return size

	def parseNodeTables( self ):

		""" Creates two lists (for root/reference nodes) to define structure locations. 
			Both are a list of tuples of the form ( structOffset, string ), 
			where the string is from the file's string table. """

		#try:
		rootNodes = []; referenceNodes = []
		nodePointerOffset = self.headerInfo['rtEnd']
		nodesTable = [ self.nodeTableData[i:i+8] for i in xrange(0, len(self.nodeTableData), 8) ] # separates the data into groups of 8 bytes

		for i, entry in enumerate( nodesTable ):
			structOffset, stringOffset = struct.unpack( '>II', entry ) # Struct offset is the first 4 bytes; string offset is the second 4 bytes
			string = self.stringDict[ stringOffset ]

			# Store the node
			if i < self.headerInfo['rootNodeCount']: rootNodes.append( ( structOffset, string ) )
			else: referenceNodes.append( ( structOffset, string ) )

			# Remember the pointer and struct offsets (these aren't included in the RT!)
			self.pointerOffsets.append( nodePointerOffset ) # Absolute file offset for this node's pointer
			self.pointerValues.append( structOffset )

			nodePointerOffset += 8

		rootNodes.sort()
		referenceNodes.sort()

		self.rootNodes = rootNodes
		self.referenceNodes = referenceNodes

		# except Exception as errorMessage:
		#	print "Unable to parse the root/reference nodes table of", self.printPath()
		#	print errorMessage

	def evaluateStructs( self ):

		""" Sorts the lists of pointer offsets and pointer values (by offset), and creates a sorted list 
			of all [unique] structure offsets in the data section, which includes offsets for the file 
			header (at -0x20), RT, root nodes table, reference nodes table (if present), and string table. """

		# Sort the lists of pointers and their values found in the RT and node tables
		self.pointers = sorted( zip(self.pointerOffsets, self.pointerValues) ) # Creates a sorted list of (pointerOffset, pointerValue) tuples

		# Create a list of unique structure offsets, sorted by file order.
		# The data section's primary assumption is that no pointer points into the middle of a struct, and thus must be to the start of one.
		self.structureOffsets = [ -0x20 ] # For the file header. Negative, not 0, because these offsets are relative to the start of the data section
		self.structureOffsets.extend( set(self.pointerValues) ) # Using a set to eliminate duplicates
		self.structureOffsets.append( self.headerInfo['rtStart'] )
		self.structureOffsets.append( self.headerInfo['rtEnd'] ) # For the root nodes table
		if self.headerInfo['rootNodesEnd'] != self.headerInfo['stringTableStart']: # Might not have a reference nodes table
			self.structureOffsets.append( self.headerInfo['rootNodesEnd'] ) # For the reference nodes table
		self.structureOffsets.append( self.headerInfo['stringTableStart'] )
		self.structureOffsets.sort()

		# The following helps provide an efficient means for determining the structure owner of an offset (used by the .getPointerOwner() function)
		self.structStartRanges = zip( self.structureOffsets, self.structureOffsets[1:] )

	def separateNodeLists( self ):

		""" Separates the node lists into root structures (highest level entry into data section) or labels (those used just for identification). 
			This works by checking whether a structure pointed to by a root/ref node also has another pointer to it within the data section. """

		try:
			# tic = time.clock()

			# Get a list of the pointer values in the data section (structure offsets)
			self.rootStructNodes = []; self.rootLabelNodes = []; self.refStructNodes = []; self.refLabelNodes = []
			totalNodePointers = self.headerInfo['rootNodeCount'] + self.headerInfo['referenceNodeCount']
			dataSectionPointerValues = self.pointerValues[:-totalNodePointers] # Excludes pointer values from nodes table
			# todo: test performance of making above variable a set for this function

			# For each node, check if there's already a pointer value (pointing to its struct) somewhere else in the data section
			for entry in self.rootNodes: # Each entry is a ( structOffset, string ) tuple pair
				if entry[0] in dataSectionPointerValues:
					self.rootLabelNodes.append( entry )
				else:
					self.rootStructNodes.append( entry )

			for entry in self.referenceNodes:
				if entry[0] in dataSectionPointerValues:
					self.refLabelNodes.append( entry )
				else:
					self.refStructNodes.append( entry )

			# toc = time.clock()
			# print '\ttime to separate node lists:', toc-tic
			# print 'dspv:', len( dataSectionPointerValues )

		except Exception as errorMessage:
			print "Unable to separate the root/reference nodes lists of", self.printPath()
			print errorMessage

	def parseDataSection( self ):

		""" This method uses the root and reference nodes to identify structures 
			within the data section of the DAT file. Some root/reference nodes point
			to the start of a hierarchical branch into the file, while others simply
			serve as labels for parts of branches or for specific structures. """

		hI = self.headerInfo

		try:
			for i, ( structOffset, _ ) in enumerate( self.rootNodes + self.referenceNodes ):
				# Determine the parent root/ref node table offset
				if i < hI['rootNodeCount']: parentOffset = hI['rtEnd']
				else: parentOffset = hI['rootNodesEnd']

				# Get the target struct if it has already been initialized
				childStruct = self.structs.get( structOffset, None )

				if childStruct and not childStruct.__class__ == str:
					""" This struct/branch has already been created! Which likely means this is part of another structure 
						branch, and this root or reference node association must just be a label for the structure.
						So just update the target structure's parent structs list with this item. """
					childStruct.parents.add( parentOffset )

				else: # Create the new struct
					childStruct = self.getStruct( structOffset, parentOffset, (2, 0) ) # Using this rather than the factory so we can still process hints
				
				childStruct.initDescendants()

			# Identify and group orphan structures. (Some orphans will be recognized/added by the struct initialization functions.)
			dataSectionStructureOffsets = set( self.structureOffsets ).difference( (-0x20, hI['rtStart'], hI['rtEnd'], hI['rootNodesEnd'], hI['stringTableStart']) )
			self.orphanStructures = dataSectionStructureOffsets.difference( self.structs.keys() )
			
		except Exception as errorMessage:
			print 'Unable to parse the DAT file data section of', self.printPath()
			print errorMessage

	def hintRootClasses( self ):

		""" Adds class hints for structures with known root/reference node labels. This is the same 
			hinting procedure enacted by structure classes' "provideChildHints" method, but done on file 
			load in order to identify top-level structures. Expected to be overridden by subclasses. """

		# for structOffset, string in self.rootNodes:
		# 	specificStructClassFound = hsdStructures.SpecificStructureClasses.get( string )
		# 	if specificStructClassFound:
		# 		self.structs[structOffset] = specificStructClassFound.__name__

	def validate( self ):

		""" Verifies whether this is actually a DAT file by affirming existance of basic file analysis.
			Expected to be overridden by subclasses with more specific checks. """

		self.initialize()

		if not self.headerInfo or not self.pointers:
			raise Exception( 'Invalid DAT file; header info and file structures could not be parsed.' )

	def getStructLength( self, targetStructOffset ):

		""" The value returned is a count in bytes.
			The premise of this method is that pointers (what structureOffsets is based on) should 
			always point to the beginning of a structure, and never into the middle of one. 
			However, padding which follows the struct to preserve alignment will be included. """

		# Look for the first file offset pointer value following this struct's start offset
		for offset in self.structureOffsets:

			if offset > targetStructOffset:
				structLength = offset - targetStructOffset
				break

		else: # The loop above did not break; no struct start offsets found beyond this offset. So the struct must end at the RT
			print 'ad-hoc struct detected in tail data (after string table); unable to calculate length for struct', hex(0x20+targetStructOffset)
			structLength = self.headerInfo['filesize'] - 0x20 - targetStructOffset

		return structLength

	def getStructLabel( self, dataSectionOffset ):

		""" Returns a struct's name/label, found in the String Table. 
			Returns an empty string if the given offset isn't found. """

		for structOffset, string in self.rootNodes + self.referenceNodes:
			if structOffset == dataSectionOffset: return string
		else: # The loop above didn't return; no match was found
			return ''

	def getPointerOwner( self, pointerOffset, offsetOnly=False ):

		""" Returns the offset of the structure which owns/contains a given pointer (or a given offset).
			This includes 'structures' such as the relocation table, root/reference node tables, and the string table. 
			If offsetOnly is True, the returned item is an int, and if it's False, the returned item is a structure object. """
		
		for structOffset, nextStructOffset in self.structStartRanges:
			if pointerOffset >= structOffset and pointerOffset < nextStructOffset:
				structOwnerOffset = structOffset
				break
		else: # The above loop didn't break; the pointer is after the last structure
			structOwnerOffset = self.structureOffsets[-1]

		if offsetOnly:
			return structOwnerOffset
		else: # Get and return the structure which owns the found offset
			return self.getStruct( structOwnerOffset )

	def checkForOrphans( self, structure ):
		
		""" If a parent offset wasn't provided, check for parents. This is done so that 
			even if orphaned structs are somehow initialized, they're still found. 
			There shouldn't be any need to check initialized data blocks, which must've
			had a parent in order to have a class hint, which leads to their creation. """

		structure.getParents( True )

		if not structure.parents:
			print 'orphan found (no parents);', hex( 0x20 + structure.offset )
			self.orphanStructures.add( structure.offset )

		elif len( structure.parents ) == 1 and structure.offset in structure.parents:
			print 'orphan found (self referencing);', hex( 0x20 + structure.offset )
			self.orphanStructures.add( structure.offset )

	def getStruct( self, structOffset, parentOffset=-1, structDepth=None ):

		""" The 'lazy' method for getting a structure. Uses multiple methods, and should return 
			some kind of structure class in all cases (resorting to a generic one if need be). """

		# Attempt to get an existing struct first
		structure = self.structs.get( structOffset, None )

		# Check if the object is an instantiated object, or just a string hint (indicating what the struct should be)
		if structure and isinstance( structure, str ):
			#newStructClass = getattr( sys.modules[hsdStructures.__name__], structure, None ) # Changes a string into a class by that name
			newStructClass = globalData.fileStructureClasses[structure]

			if not newStructClass: # Unable to find a structure by that name
				print 'Unable to find a structure class of', structure
				structure = None # We'll let the structure factory handle this

			elif issubclass( newStructClass, hsdStructures.DataBlock ):
				#print 'creating new data block from', structure, 'hint for Struct', hex(0x20+structOffset)
				structure = self.initDataBlock( newStructClass, structOffset, parentOffset, structDepth )

			else:
				#print 'Struct', hex(0x20+structOffset), 'insinuated to be', structure, 'attempting to init specifically'
				structure = self.initSpecificStruct( newStructClass, structOffset, parentOffset, structDepth )

		if not structure: # If there was a hint, it may have been bad (above initialization failed)
			structure = self.structureFactory( structOffset, parentOffset, structDepth )

		return structure

	def getStructByLabel( self, label ):

		""" Gets a structure by a string from the strings table. """

		for structOffset, string in self.rootNodes + self.referenceNodes:
			if string == label:
				return self.getStruct( structOffset )

		# The loop above didn't break; no match found!
		return None

	def structureFactory( self, structOffset, parentOffset=-1, structDepth=None ):

		""" This is a factory method to determine what kind of structure is at a given offset, 
			and instantiate the respective class for that particular structure. 
			If a structure class/type cannot be determined, a general one will be created. 
			The resulting behavior is similar to getStruct(), while ignoring structure hints. """

		# If the requested struct has already been created, return that
		existingStruct = self.structs.get( structOffset, None )
		if existingStruct and not existingStruct.__class__ == str: # If it's a string, it's a class hint
			return existingStruct

		# Validation; make sure a struct begins at the given offset
		elif structOffset not in self.structureOffsets:
			print 'Unable to create a struct object; invalid offset given:', hex(0x20 + structOffset)
			return None

		# Get parent struct offsets, to attempt to use them to determine this struct 
		# Try to get a parent struct to help with identification
		# if parentOffset != -1:
		# 	parents = set( [parentOffset] )
		# else:
		# 	# This is a basic methodology and will get [previous] siblings as well.
		# 	parents = set()
		# 	for pointerOffset, pointerValue in self.pointers:
		# 		if structOffset == pointerValue:
		# 			# The matched pointerOffset points to this structure; get the structure that owns this pointer
		# 			parents.add( self.getPointerOwner(pointerOffset).offset )
		# parents.difference_update( [self.headerInfo['rtEnd'], self.headerInfo['rootNodesEnd']] ) # Remove instance of the root/reference node if present

		# Get information on this struct
		deducedStructLength = self.getStructLength( structOffset ) # May include padding
		if deducedStructLength < 0:
			print 'Unable to create a struct object; unable to get a struct length for', hex(0x20 + structOffset)
			return None

		# Look at the available structures, and determine whether this structure matches any of them
		for structClass in hsdStructures.CommonStructureClasses + hsdStructures.AnimationStructureClasses:

			newStruct = structClass( self, structOffset, parentOffset, structDepth )

			if newStruct.validated( deducedStructLength=deducedStructLength ): break

		else: # The loop above didn't break; no structure match found
			# Use the base arbitrary class, which will work for any struct
			newStruct = hsdStructures.StructBase( self, structOffset, parentOffset, structDepth )

			newStruct.data = self.getData( structOffset, deducedStructLength )
			newStruct.formatting = '>' + 'B' * deducedStructLength # Assume a basic formatting if this is an unknown struct
			newStruct.fields = ()
			newStruct.length = deducedStructLength
			newStruct.padding = 0

		# Add this struct to the DAT's structure dictionary
		self.structs[structOffset] = newStruct

		# Ensure that even if orphaned structs are somehow initialized, they're still found.
		if not newStruct.parents:
			self.checkForOrphans( newStruct )

		return newStruct

	def initGenericStruct( self, offset, parentOffset=-1, structDepth=None, deducedStructLength=-1, asPointerTable=False ):

		existingStruct = self.structs.get( offset, None )
		if existingStruct:
			return existingStruct

		if deducedStructLength == -1:
			deducedStructLength = self.getStructLength( offset ) # This length will include any padding too

		newStruct = hsdStructures.StructBase( self, offset, parentOffset, structDepth )

		newStruct.data = self.getData( offset, deducedStructLength )
		if asPointerTable:
			newStruct.formatting = '>' + 'I' * ( deducedStructLength / 4 ) # Assume a basic formatting if this is an unknown struct
		else:
			newStruct.formatting = '>' + 'B' * deducedStructLength # Assume a basic formatting if this is an unknown struct
		newStruct.fields = ()
		newStruct.length = deducedStructLength
		newStruct.padding = 0

		# Add this struct to the DAT's structure dictionary
		self.structs[offset] = newStruct

		# Ensure that even if orphaned structs are somehow initialized, they're still found.
		if not newStruct.parents:
			self.checkForOrphans( newStruct )

		return newStruct

	# def initPointerTable( self, offset, parentOffset=-1, structDepth=None, deducedStructLength=-1 ):

	# 	if deducedStructLength == -1:
	# 		deducedStructLength = self.getStructLength( offset ) # This length will include any padding too

	# 	newStruct = hsdStructures.StructBase( self, offset, parentOffset, structDepth )

	# 	newStruct.data = self.getData( offset, deducedStructLength )
	# 	newStruct.formatting = '>' + 'I' * ( deducedStructLength / 4 ) # Assume a basic formatting if this is an unknown struct
	# 	newStruct.fields = ()
	# 	newStruct.length = deducedStructLength
	# 	newStruct.padding = 0

	# 	# Add this struct to the DAT's structure dictionary
	# 	self.structs[offset] = newStruct

	# 	# Ensure that even if orphaned structs are somehow initialized, they're still found.
	# 	if not newStruct.parents:
	# 		self.checkForOrphans( newStruct )

	# 	return newStruct

	def initSpecificStruct( self, newStructClass, offset, parentOffset=-1, structDepth=None, printWarnings=True ):

		""" Attempts to validate and initialize a structure as a specific class (if it doesn't already exist).
			If unable to do so, this method returns None. 
			Do not use this to initialize a generic (StructBase) class. """

		# Perform some basic validation
		assert newStructClass != hsdStructures.StructBase, 'Invalid "StructBase" class provided for specific initialization.'
		assert offset in self.structureOffsets, 'Invalid offset given to initSpecificStruct (not in structure offsets): ' + hex(0x20+offset)

		# If the requested struct has already been created, return it
		hintPresent = False
		existingStruct = self.structs.get( offset, None )

		if existingStruct:
			if existingStruct.__class__ == str:
				hintPresent = True

			else: # A class instance was found (not a string hint)
				if existingStruct.__class__ == newStructClass:
					return existingStruct

				# If the existing struct is generic, allow it to be overridden by the new known/specific class
				elif existingStruct.__class__ == hsdStructures.StructBase:
					pass
				
				else: # If the struct has already been initialized as something else, return None
					if printWarnings:
						print 'Attempted to initialize a {} for Struct 0x{:X}, but a {} already existed'.format( newStructClass.__name__, 0x20+offset, existingStruct.__class__.__name__)
					return None

		# Create the new structure
		try:
			newStructure = newStructClass( self, offset, parentOffset, structDepth )
		except Exception as err:
			print 'Unable to initSpecificStruct;', err
			return None

		# Validate it
		if not newStructure.validated():
			# Check if the hint provided actually suggested the class we just tried
			if hintPresent and existingStruct == newStructClass.__name__:
				del self.structs[offset] # Assume the hint is bad and remove it
				if printWarnings:
					print 'Failed to init hinted', newStructClass.__name__, 'for offset', hex(0x20+offset) + '; appears to have been a bad hint'
			elif printWarnings:
				print 'Failed to init', newStructure.__class__.__name__, 'for offset', hex(0x20+offset)

			return None

		# Valid struct of this class. Add it to the DAT's structure dictionary
		self.structs[offset] = newStructure

		# Ensure that even if orphaned structs are somehow initialized, they're still found.
		if not newStructure.parents:
			self.checkForOrphans( newStructure )

		return newStructure

	def initDataBlock( self, newDataClass, offset, parentOffset=-1, structDepth=None, dataLength=-1 ):

		""" Initializes a raw block of image/palette/etc. data without validation; these will have mostly 
			the same methods as a standard struct and can be handled similarly. """

		assert offset in self.structureOffsets, 'Invalid offset to initDataBlock; 0x{:x} does not appear to be a valid struct'.format( offset )

		# If the requested struct has already been created, return it
		existingStruct = self.structs.get( offset, None )

		if existingStruct and not existingStruct.__class__ == str: # A class instance was found (not a string hint)
			if existingStruct.__class__ == newDataClass:
				return existingStruct

			# If the existing struct is generic, allow it to be overridden by the new known/specific class
			elif existingStruct.__class__ == hsdStructures.StructBase:
				pass
			
			else: # If the struct has already been initialized as something else, return None
				print 'Attempted to initialize a {} for Struct 0x{:X}, but a {} already existed'.format( newDataClass.__name__, 0x20+offset, existingStruct.__class__.__name__)
				return None

		deducedStructLength = self.getStructLength( offset ) # This length will include any padding too
		newStructure = newDataClass( self, offset, parentOffset, structDepth )

		# Get the data length, if not provided; deterimined by a parent struct, if possible
		if dataLength == -1 and parentOffset != -1:
			if newDataClass == hsdStructures.ImageDataBlock:
				# Try to initialize an image data header, and get info from that
				imageDataHeader = self.initSpecificStruct( hsdStructures.ImageObjDesc, parentOffset )

				if imageDataHeader:
					width, height, imageType = imageDataHeader.getValues()[1:4]
					dataLength = hsdStructures.ImageDataBlock.getDataLength( width, height, imageType )

			elif newDataClass == hsdStructures.FrameDataBlock:
				# Try to initialize a parent frame object, and get info from that
				frameObj = self.initSpecificStruct( hsdStructures.FrameObjDesc, parentOffset )
				dataLength = frameObj.getValues( specificValue='Data_String_Length' )

		# Exact data length undetermined. Assume the full space before the next struct start.
		if dataLength == -1:
			dataLength = deducedStructLength

		# Add the final properties
		newStructure.data = self.getData( offset, dataLength )
		newStructure.formatting = '>' + 'B' * dataLength
		newStructure.length = dataLength
		newStructure.padding = deducedStructLength - dataLength
		newStructure._siblingsChecked = True
		newStructure._childrenChecked = True

		# Add this struct to the DAT's structure dictionary
		self.structs[offset] = newStructure

		return newStructure

	# def findDataSectionRoot( self, offset ):

	# 	""" Seeks upwards through structures towards the first/root entry point into the data section, for the given offset. """

	# 	# Check if there's only one option
	# 	if len( self.rootStructNodes ) == 1 and len( self.refStructNodes ) == 0:
	# 		return self.rootStructNodes[0]
	# 	elif len( self.refStructNodes ) == 1 and len( self.rootStructNodes ) == 0:
	# 		return self.refStructNodes[0]

	# 	def getNextHigherRelative( offset ):
	# 		for pointerOffset, pointerValue in self.pointers:
	# 			if pointerValue == offset:
	# 				#assert pointerOffset < self.dat.headerInfo['rtEnd'], '.getImmediateParent() unable to find a data section parent for ' + hex(0x20+offset)
	# 				if pointerOffset > self.dat.headerInfo['rtEnd']

	# 				# Pointer found; get the structure that owns this pointer
	# 				parentOffset = self.dat.getPointerOwner( pointerOffset, offsetOnly=True )

	# 	# Multiple options; we'll have to walk the branches
	# 	nextParentOffset = offset
	# 	while nextParentOffset not in ( self.dat.headerInfo['rtEnd'], self.dat.headerInfo['rootNodesEnd'] ):

	# def initBranchToTrunk( self, structOffset ):

	# 	""" Initializes the structure at the given offset, as well as the entire structure branch above it. 
	# 		This is done in reverse order (highest level root structure first) so that the last structure 
	# 		can be more accurately determined. """

	# 	# Get the closest upward relative/branch offset to this structure; either from an existing struct, or by scanning the file's pointers.
	# 	existingEntity = self.structs.get( structOffset )
	# 	if existingEntity not isinstance( existingEntity, (str, hsdStructures.StructBase) ): # Found a known struct, not a hint or generic struct
	# 		parentOffset = existingEntity.getParents()
	# 	else:
	# 		for pointerOffset, pointerValue in self.pointers:
	# 			if pointerValue == structOffset:
	# 				parentOffset = self.getPointerOwner( pointerOffset )
	# 				break # For once, we don't care if this is a sibling

	# 	# See if a parent structure has been initialized as a known struct, and get it if it has
	# 	if parentOffset == self.headerInfo['rtEnd'] or parentOffset == self.headerInfo['rootNodesEnd']: # Reached the base of the trunk
	# 		rootStruct = self.structureFactory( structOffset, parentOffset, (2, 0) ) # todo: fix this if label checking is removed from this method (in favor of hints)

	def getData( self, dataOffset=0, dataLength=-1 ):

		""" Returns file data from either the data section or tail data. The offset is 
			relative to the data section (i.e. does not account for file header). 
			If no arguments are given, the entire file data is returned. 
			If only an offset is given, the data length is assumed to be 1. """

		# Call the superclass method to make sure this file's data has been loaded from disc/file
		super( DatFile, self ).getData()

		# Return all file data if no args were given
		if dataOffset == 0 and dataLength == -1:
			return self.getFullData()

		# Assume data length of 1 if still -1
		if dataLength == -1:
			dataLength = 1

		# Make the offset relative to the data section if the file hasn't been initialized yet
		if not self.headerData:
			dataOffset += 0x20

		dataSectionLength = len( self.data )

		if dataOffset < dataSectionLength:
			assert dataOffset + dataLength <= dataSectionLength, 'Unable to get 0x{:X} byte(s) from offset 0x{:X}; it bleeds into the RT.'.format( dataLength, dataOffset + 0x20 )
			return self.data[ dataOffset : dataOffset+dataLength ]

		else: # Need to get it from the tail data
			tailOffset = dataOffset - dataSectionLength - len( self.rtData ) - len( self.nodeTableData ) - len( self.stringTableData )
			assert tailOffset >= 0, 'Unable to get 0x{:X} byte(s) from offset 0x{:X}; it falls between the data and tail sections!'.format( dataLength, dataOffset )
			return self.tailData[ tailOffset : tailOffset+dataLength ]

	def getFullData( self ):

		""" Assembles all of the file's data groups from internal references, to get all of the latest data for the file. """

		if self.headerNeedsRebuilding:
			hI = self.headerInfo
			self.headerData[:0x14] = struct.pack( '>5I', hI['filesize'], hI['rtStart'], hI['rtEntryCount'], hI['rootNodeCount'], hI['referenceNodeCount'] )
			self.headerNeedsRebuilding = False

		if self.rtNeedsRebuilding:
			rtEntryCount = self.headerInfo['rtEntryCount']
			self.rtData = struct.pack( '>{}I'.format(rtEntryCount), *self.pointerOffsets[:rtEntryCount] )
			self.rtNeedsRebuilding = False

		if self.nodesNeedRebuilding or self.stringsNeedRebuilding:
			self.rebuildNodeAndStringTables()

		return self.headerData + self.data + self.rtData + self.nodeTableData + self.stringTableData + self.tailData

	def rebuildNodeAndStringTables( self ):

		""" Rebuilds the root nodes table, reference nodes table, and string table. """

		self.stringTableData = bytearray()
		nodeValuesList = []

		self.rootNodes.sort()
		self.referenceNodes.sort()

		for structOffset, string in self.rootNodes + self.referenceNodes:
			# Collect values for this node to be encoded in the finished table
			nodeValuesList.extend( [structOffset, len(self.stringTableData)] )

			# Add the string for this node to the string table
			self.stringTableData.extend( string.encode('ascii') )
			self.stringTableData.append( 0 ) # Add a null terminator for this string

		# Encode both node tables together
		self.nodeTableData = struct.pack( '>{}I'.format(len(nodeValuesList)), *nodeValuesList )

		# Clear the flags indicating that these needed to be rebuilt
		self.nodesNeedRebuilding = False
		self.stringsNeedRebuilding = False

	def setData( self, dataOffset, newData ):

		""" Directly updates (replaces) data in this file, in either the data section or tail data. The data 
			input should be a single int (if the data is only one byte) or a bytearray. The offset is relative 
			to the start of that section. Data in pre-initialized structs will not be updated. Does not record 
			the change in self.unsavedChanges; for that, see .recordChange() or the .updateData() method. 
			If you're not sure which to use, you should probably be using .updateData(). """

		if type( newData ) == int: # Just a single byte/integer value (0-255)
			assert newData >= 0 and newData < 256, 'Invalid input to DatFile.setData(): ' + str(newData)
			newData = ( newData, ) # Need to make it an iterable, for the splicing operation
			dataLength = 1
		else:
			dataLength = len( newData )

		# Make the offset relative to the data section if the file hasn't been initialized yet
		if not self.headerData:
			dataOffset += 0x20

		if dataOffset < len( self.data ):
			assert dataOffset + dataLength <= len( self.data ), '0x{:X} is too much data to set at offset 0x{:X}.'.format( dataLength, dataOffset )
			self.data[dataOffset:dataOffset+dataLength] = newData # This will also work for bytearrays of length 1
		else:
			tailOffset = dataOffset - len( self.data ) - len( self.rtData ) - len( self.nodeTableData ) - len( self.stringTableData )
			assert tailOffset + dataLength <= len( self.tailData ), '0x{:X} is too much tail data to set at offset 0x{:X}.'.format( dataLength, tailOffset )
			self.tailData[tailOffset:tailOffset+dataLength] = newData # This will also work for bytearrays of length 1

	def updateData( self, offset, newData, description='', trackChange=True ):

		""" Directly updates (replaces) data in this file, in either the data section or tail data. The 
			data input should be a single int (if the data is only one byte) or a bytearray. The offset is 
			relative to the start of that section. Will also update any structs that have already been 
			initialized for that location in the file. This method will then also record that this 
			change was made (updating self.unsavedChanges). """

		# Perform a bit of validation on the input
		if type( newData ) == int: # Just a single byte/integer value (0-255)
			assert newData >= 0 and newData < 256, 'Invalid input to DatFile.updateData(): ' + str(newData)
			dataLength = 1
		else:
			dataLength = len( newData )
		self.setData( offset, newData )

		# If a structure has been initialized that contains the modifications, update it too
		structOffset = self.getPointerOwner( offset, offsetOnly=True )
		targetStruct = self.structs.get( structOffset, None )
		if targetStruct and not isinstance( targetStruct, str ):
			# Pull new data for the structure
			targetStruct.data = self.getData( targetStruct.offset, targetStruct.length )

			# Update its values as well, as long as it's not a block of raw data
			if not issubclass( targetStruct.__class__, hsdStructures.DataBlock ):
				targetStruct.values = ()
				targetStruct.getValues()

		# Record these changes
		if trackChange:
			# Create a description if one isn't provided. Amend it with e.g. ' at 0x1234'
			if not description:
				if dataLength == 1:
					description = 'Single byte updated'
				else:
					description = '0x{:X} bytes of data updated'.format( dataLength )
			description += ' at 0x{:X}.'.format( 0x20 + offset ) # Accounting for file header

			self.recordChange( description )

	def updateStructValue( self, structure, valueIndex, newValue, description='', trackChange=True, entryIndex=0 ):
		
		""" Performs a similar function as the updateData method. However, this requires a known structure to exist, 
			and makes the appropriate modifications through it first before updating self.data. """

		# Change the value in the struct
		if entryIndex != 0:
			assert isinstance( structure, hsdStructures.TableStruct ), 'Invalid usage of updateStructValue; must operate on a TableStruct if using an entryIndex.'
			valueIndex = ( structure.entryValueCount * entryIndex ) + valueIndex
		structure.setValue( valueIndex, newValue )
		
		# Update the file's data with that of the modified structure
		structure.data = struct.pack( structure.formatting, *structure.values )
		self.setData( structure.offset, structure.data )
		
		# Record these changes
		if trackChange:
			# Create a description if one isn't provided. Amend it with e.g. ' at 0x1234'
			if not description:
				fieldName = structure.fields[valueIndex].replace( '_', ' ' )
				description = '{} modified for {}'.format( fieldName, structure.name )
			offset = 0x20 + structure.valueIndexToOffset( valueIndex ) # Accounting for file header
			description += ' at 0x{:X}.'.format( offset )

			self.recordChange( description )

	# def updateStructEntryValue( self, structure, valueIndex, newValue, description='', trackChange=True ):
		
	# 	""" Performs a similar function as the updateData method. However, this requires a known structure to exist, 
	# 		and makes the appropriate modifications through it first before updating self.data. """

	# 	# Change the value in the struct
	# 	structure.setValue( valueIndex, newValue )
		
	# 	# Update the file's data with that of the modified structure
	# 	structure.data = struct.pack( structure.formatting, *structure.values )
	# 	self.setData( structure.offset, structure.data )
		
	# 	# Record these changes
	# 	if trackChange:
	# 		# Create a description if one isn't provided. Amend it with e.g. ' at 0x1234'
	# 		if not description:
	# 			fieldName = structure.fields[valueIndex].replace( '_', ' ' )
	# 			description = '{} modified for {}'.format( fieldName, structure.name )
	# 		offset = 0x20 + structure.valueIndexToOffset( valueIndex ) # Accounting for file header
	# 		description += ' at 0x{:X}.'.format( offset )

	# 		self.recordChange( description )

	def updateFlag( self, structure, valueIndex, bitNumber, flagState, trackChange=True ):
		
		""" Performs a similar function as the updateData method. However, this requires a known structure, 
			and makes the appropriate modifications through it first before updating self.data. """

		# Check if the flag even needs updating (if it's already set as desired)
		flagsValue = structure.getValues()[valueIndex]
		if flagState:
			if flagsValue & (1 << bitNumber):
				#print 'Bit {} of {} flags already set!'.format( bitNumber, structure.name )
				return # Flag already set as desired
		elif not flagsValue & (1 << bitNumber):
			#print 'Bit {} of {} flags already cleared!'.format( bitNumber, structure.name )
			return # Flag already clear as desired

		# Set or clear the flag, based on the desired flag state
		if flagState:
			structure.setFlag( valueIndex, bitNumber ) # Arguments are value index and bit number
		else:
			structure.clearFlag( valueIndex, bitNumber )

		# Update the file's data with that of the modified structure
		structure.data = struct.pack( structure.formatting, *structure.values )
		self.setData( structure.offset, structure.data )

		# Record these changes
		if trackChange:
			# Create a description if one isn't provided. Amend it with e.g. ' at 0x1234'
			offset = 0x20 + structure.valueIndexToOffset( valueIndex ) # Accounting for file header
			description = 'Flag modified for {} (bit {}) at 0x{:X}.'.format( structure.name, bitNumber, offset )
			
			self.recordChange( description )

	def noChangesToBeSaved( self, programClosing ):

		""" Checks and returns whether there are any unsaved changes that the user would like to save.
			If there are any unsaved changes, this prompts the user on whether they would like to keep them, 
			and if they don't, the changes are discarded and this method then returns False. """

		noChangesNeedSaving = True

		if self.unsavedChanges:
			if programClosing:
				warning = "The changes below haven't been saved to the currently loaded file. Are you sure you want to close?\n\n"
			else: warning = 'The changes below will be forgotten if you change or reload the currently loaded file before saving. Are you sure you want to do this?\n\n'
			warning += '\n'.join( self.unsavedChanges )

			noChangesNeedSaving = tkMessageBox.askyesno( 'Unsaved Changes', warning )

		if noChangesNeedSaving: # Forget the past changes
			self.unsavedChanges = []

			# If the Disc File Tree is present, remove indication that this file had changes waiting to be saved there
			if globalData.gui and globalData.gui.discTab:
				globalData.gui.discTab.isoFileTree.item( self.isoPath, tags=() )

		return noChangesNeedSaving

	def removePointer( self, offset ):

		""" Removes a pointer from the data section (setting 4 null bytes) and from the Relocation Table (removing
			it entirely). The offset argument is relative to the start of the data section, even if it's in tail data. 
			Beware that structures that have already determined their parents/siblings/children due to the pointer
			will still have those references. """

		# Make sure this is a valid pointer offset, and get the index for this pointer's location and value
		try:
			pointerValueIndex = self.pointerOffsets.index( offset )
		except ValueError:
			print 'Invalid offset given to removePointer;', hex(0x20+offset), 'is not a valid pointer offset.'
		except Exception as err:
			print err

		# Update header values
		self.headerInfo['filesize'] -= 4
		self.headerInfo['rtEntryCount'] -= 1
		self.headerInfo['rtEnd'] -= 4
		self.headerInfo['rootNodesEnd'] -= 4
		self.headerInfo['stringTableStart'] -= 4
		self.headerNeedsRebuilding = True
		self.size -= 4

		# Remove the value from the Relocation Table and the various structure/pointer lists
		self.pointerOffsets.remove( offset )
		del self.pointerValues[pointerValueIndex]
		self.evaluateStructs() # Rebuilds the pointers tuple list and the structure offsets set
		self.rtNeedsRebuilding = True

		# Null the pointer in the file/structure data and structure values
		self.setData( offset, bytearray(4) ) # Bytearray initialized with 4 null bytes
		structOffset = self.getPointerOwner( offset, offsetOnly=True )
		targetStruct = self.structs.get( structOffset, None )
		if targetStruct and not isinstance( targetStruct, str ):
			# Update the structure's data
			targetStruct.data = self.getData( targetStruct.offset, targetStruct.length )

			# Update its values as well, as long as it's not a block of raw data
			if not issubclass( targetStruct.__class__, hsdStructures.DataBlock ):
				targetStruct.values = ()
				targetStruct.getValues()

		# Record this change
		description = 'Pointer removed at 0x{:X}.'.format( 0x20 + offset )
		self.recordChange( description )

	def collapseDataSpace( self, collapseOffset, amount ):

		""" Erases data space, starting at the given offset, including pointers and structures (and their references) in the affected area. """

		# Perform some validation on the input
		if amount == 0: return
		elif collapseOffset > len( self.data ):
			if not self.tailData:
				print 'Invalid offset provided for collapse; offset is too large'
				return

			tailDataStart = self.headerInfo['stringTableStart'] + self.getStringTableSize()
			if collapseOffset < tailDataStart:
				print 'Invalid collapse offset provided; offset falls within RT, node tables, or string table'
				return
			elif collapseOffset + amount > self.headerInfo['filesize'] - 0x20:
				amount = self.headerInfo['filesize'] - 0x20 - collapseOffset
				print 'Collapse space falls outside of the range of the file! The amount to remove is being adjusted to', hex(amount)
		elif collapseOffset < len( self.data ) and collapseOffset + amount > len( self.data ):
			amount = len( self.data ) - collapseOffset
			print 'Collapse space overlaps into the Relocation Table! The amount to remove is being adjusted to', hex(amount)
			
		# Reduce the amount, if necessary, to preserve file alignment
		if amount < 0x20:
			print 'Collapse amount should be >= 0x20 bytes, to preserve file alignment.'
			return
		elif amount % 0x20 != 0:
			adjustment = amount % 0x20
			amount -= adjustment
			print 'Collapse amount decreased by', hex(adjustment) + ', to preserve file alignment'

			if amount == 0: return

		# Make sure we're only removing space from one structure
		targetStructOffset = self.getPointerOwner( collapseOffset, offsetOnly=True )
		structSize = self.getStructLength( targetStructOffset )
		if collapseOffset + amount > targetStructOffset + structSize:
			print 'Unable to collapse file space. Amount is greater than structure size'
			return

		print 'Collapsing file data at', hex(0x20+collapseOffset), 'by', hex(amount)

		# Adjust the values in the pointer offset and structure offset lists (these changes are later saved to the Relocation table)
		rtEntryCount = self.headerInfo['rtEntryCount']
		pointersToRemove = [] # Must be removed after the following loop (since we're iterating over one of the lists these are in)
		for i, (pointerOffset, pointerValue) in enumerate( self.pointers ):
			# Reduce affected pointer offset values
			if pointerOffset >= collapseOffset and pointerOffset < collapseOffset + amount: # This falls within the space to be removed
				pointersToRemove.append( i )
				continue

			elif pointerOffset > collapseOffset: # These offsets need to be reduced
				self.pointerOffsets[i] = pointerOffset - amount

			# If the place that the pointer points to is after the space change, update the pointer value accordingly
			if pointerValue >= collapseOffset and pointerValue < collapseOffset + amount: # This points to within the space to be removed
				pointersToRemove.append( i )

				# Null the pointer value in the file and structure data
				if i < rtEntryCount: # Still within the data section; not looking at node table pointers
					print 'Nullifying pointer at', hex( 0x20+pointerOffset ), 'as it pointed into the area to be removed'
					self.setData( pointerOffset, bytearray(4) ) # Bytearray initialized with 4 null bytes

			elif pointerValue > collapseOffset:
				newPointerValue = pointerValue - amount
				self.pointerValues[i] = newPointerValue

				# Update the pointer value in the file and structure data
				if i < rtEntryCount: # Still within the data section; not looking at node table pointers
					print 'Set pointer value at', hex(0x20+pointerOffset), 'to', hex(newPointerValue)
					self.setData( pointerOffset, struct.pack('>I', newPointerValue) )

		# Remove pointers and their offsets from their respective lists, and remove structs that fall in the area to be removed
		pointersToRemove.sort( reverse=True ) # Needed so we don't start removing the wrong indices after the first
		if pointersToRemove:
			print 'Removing', len(pointersToRemove), 'pointers:'
			print [ hex(0x20+self.pointerOffsets[i]-amount) for i in pointersToRemove ]
		for pointerIndex in pointersToRemove:
			del self.pointerOffsets[pointerIndex]
			del self.pointerValues[pointerIndex]
		self.structs = {}
		self.hintRootClasses()
		self.rtNeedsRebuilding = True

		# Update root nodes
		newRootNodes = []
		nodesModified = False
		for structOffset, string in self.rootNodes:
			# Collect unaffected nodes
			if structOffset < collapseOffset:
				newRootNodes.append( (structOffset, string) )
			# Skip nodes that point to within the affected area, since they no longer point to anything
			elif structOffset >= collapseOffset and structOffset < collapseOffset + amount:
				self.stringDict = { key: val for key, val in self.stringDict.items() if val != string }
				print 'Removing root node,', string
				nodesModified = True
			else: # Struct offset is past the affected area; just needs to be reduced
				newRootNodes.append( (structOffset - amount, string) )
				nodesModified = True
		if nodesModified:
			print 'Modified root nodes'
			self.rootNodes = newRootNodes
			self.nodesNeedRebuilding = True

		# Update reference nodes
		newRefNodes = []
		nodesModified = False
		for structOffset, string in self.referenceNodes:
			# Collect unaffected nodes
			if structOffset < collapseOffset:
				newRefNodes.append( (structOffset, string) )
			# Skip nodes that point to within the affected area, since they no longer point to anything
			elif structOffset >= collapseOffset and structOffset < collapseOffset + amount:
				self.stringDict = { key: val for key, val in self.stringDict.items() if val != string }
				print 'Removing reference node,', string
				nodesModified = True
			else: # Struct offset is past the affected area; just needs to be reduced
				newRefNodes.append( (structOffset - amount, string) )
				nodesModified = True
		if nodesModified:
			print 'Modified reference nodes'
			self.referenceNodes = newRefNodes
			self.nodesNeedRebuilding = True

		# Recreate the root/ref struct/label node lists
		if self.nodesNeedRebuilding:
			self.separateNodeLists()

		# Update header values
		rtSizeReduction = len( pointersToRemove ) * 4
		rootNodesSize = len( self.rootNodes ) * 8
		refNodesSize = len( self.referenceNodes ) * 8
		self.headerInfo['filesize'] -= ( amount + rtSizeReduction )
		self.headerInfo['rtStart'] -= amount
		self.headerInfo['rtEntryCount'] -= len( pointersToRemove )
		self.headerInfo['rootNodeCount'] = len( self.rootNodes )
		self.headerInfo['referenceNodeCount'] = len( self.referenceNodes )
		rtEnd = self.headerInfo['rtStart'] + ( self.headerInfo['rtEntryCount'] * 4 )
		self.headerInfo['rtEnd'] = rtEnd
		self.headerInfo['rootNodesEnd'] = rtEnd + rootNodesSize
		self.headerInfo['stringTableStart'] = rtEnd + rootNodesSize + refNodesSize
		self.headerNeedsRebuilding = True
		self.size -= ( amount + rtSizeReduction )

		# Rebuild the and structure offsets and pointers lists
		self.evaluateStructs()

		# Remove the data
		if collapseOffset < len( self.data ):
			self.data = self.data[ :collapseOffset ] + self.data[ collapseOffset+amount: ]
		else: # Falls within tail data
			self.tailData = self.tailData[ :collapseOffset ] + self.tailData[ collapseOffset+amount: ]

		# Record this change
		description = '0x{:X} bytes of data removed at 0x{:X}.'.format( amount, 0x20 + collapseOffset )
		self.recordChange( description )

	def extendDataSpace( self, extensionOffset, amount ):

		""" Increases the amount of file/data space at the given offset. 
			This will also clear the .structs dictionary, since their data will be bad. """

		# Perform some validation on the input
		if amount == 0: return
		elif extensionOffset >= len( self.data ):
			if not self.tailData:
				print 'Invalid offset provided for file extension; offset is too large'
				return

			tailDataStart = self.headerInfo['stringTableStart'] + self.getStringTableSize()
			if extensionOffset < tailDataStart:
				print 'Invalid extension offset provided; offset falls within RT, node tables, or string table'
				return

		# Adjust the amount, if necessary, to preserve file alignment (rounding up)
		if amount % 0x20 != 0:
			amountAdjustment = 0x20 - ( amount % 0x20 )
			amount += amountAdjustment
			print 'Exension amount increased by', hex(amountAdjustment) + ' bytes, to preserve other potential structure alignments'

		# Adjust the values in the pointer offset and structure offset lists (these changes are later saved to the Relocation table)
		rtEntryCount = self.headerInfo['rtEntryCount']
		for i, (pointerOffset, pointerValue) in enumerate( self.pointers ):
			# Increase affected pointer offset values
			if pointerOffset >= extensionOffset:
				self.pointerOffsets[i] = pointerOffset + amount

			# If the place that the pointer points to is after the space change, update the pointer value accordingly
			if pointerValue >= extensionOffset:
				newPointerValue = pointerValue + amount
				self.pointerValues[i] = newPointerValue

				# Update the pointer value in the file and structure data
				if i < rtEntryCount: # Still within the data section; not looking at node table pointers
					#print 'Set pointer value at', hex(0x20+pointerOffset), 'to', hex(newPointerValue)
					self.setData( pointerOffset, struct.pack('>I', newPointerValue) )
		self.structs = {}
		self.hintRootClasses()
		self.rtNeedsRebuilding = True

		# Update root nodes
		newRootNodes = []
		nodesModified = False
		for structOffset, string in self.rootNodes:
			# Collect unaffected nodes
			if structOffset < extensionOffset:
				newRootNodes.append( (structOffset, string) )
			else: # Struct offset is past the affected area; needs to be increased
				newRootNodes.append( (structOffset + amount, string) )
				nodesModified = True
		if nodesModified:
			self.rootNodes = newRootNodes
			self.nodesNeedRebuilding = True

		# Update reference nodes
		newRefNodes = []
		nodesModified = False
		for structOffset, string in self.referenceNodes:
			# Collect unaffected nodes
			if structOffset < extensionOffset:
				newRefNodes.append( (structOffset, string) )
			else: # Struct offset is past the affected area; needs to be reduced
				newRefNodes.append( (structOffset + amount, string) )
				nodesModified = True
		if nodesModified:
			self.referenceNodes = newRefNodes
			self.nodesNeedRebuilding = True

		# Recreate the root/ref struct/label node lists
		if self.nodesNeedRebuilding:
			self.separateNodeLists()

		# Update header values
		self.headerInfo['filesize'] += amount
		self.headerInfo['rtStart'] += amount
		self.headerInfo['rtEnd'] += amount
		self.headerInfo['rootNodesEnd'] += amount
		self.headerInfo['stringTableStart'] += amount
		self.headerNeedsRebuilding = True
		self.size += amount

		# Rebuild the structure offset and pointer lists
		self.evaluateStructs()

		# Add the new bytes to .data
		newBytes = bytearray( amount )
		if extensionOffset < len( self.data ):
			self.data = self.data[ :extensionOffset ] + newBytes + self.data[ extensionOffset: ]
		else: # Falls within tail data
			self.tailData = self.tailData[ :extensionOffset ] + newBytes + self.tailData[ extensionOffset: ]

		# Record this change
		description = '0x{:X} bytes of data added at 0x{:X}.'.format( amount, 0x20 + extensionOffset )
		self.recordChange( description )

	def identifyTextures( self ):

		""" Returns a list of tuples containing texture info. Each tuple is of the following form: 
				( imageDataOffset, imageHeaderOffset, paletteDataOffset, paletteHeaderOffset, width, height, imageType, mipmapCount ) """

		imageDataOffsetsFound = set()
		texturesInfo = []
		
		# tic = time.clock()

		try:
			# Get the data section structure offsets, and separate out main structure references
			hI = self.headerInfo
			dataSectionStructureOffsets = set( self.structureOffsets ).difference( (-0x20, hI['rtStart'], hI['rtEnd'], hI['rootNodesEnd'], hI['stringTableStart']) )

			# Scan the data section by analyzing generic structures and looking for standard image data headers
			for structureOffset in dataSectionStructureOffsets:
				if structureOffset in imageDataOffsetsFound: continue # This is a structure of raw image data, which has already been added

				# Get the image data header struct's data.
				try: # Using a try block because the last structure offsets may raise an error (unable to get 0x18 bytes) which is fine
					structData = self.getData( structureOffset, 0x18 )
				except:
					continue

				# Unpack the values for this structure, assuming it's an image data header
				fieldValues = struct.unpack( '>IHHIIff', structData )
				imageDataOffset, width, height, imageType, mipmapFlag, minLOD, maxLOD = fieldValues

				if imageDataOffset in imageDataOffsetsFound: continue # Already added this one
				elif imageDataOffset not in dataSectionStructureOffsets: continue # Not a valid pointer/struct offset!

				# Check specific data values for known restrictions
				if width < 1 or height < 1: continue
				elif width > 1024 or height > 1024: continue
				elif imageType not in ( 0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 14 ): continue
				elif mipmapFlag > 1: continue
				elif minLOD > 10 or maxLOD > 10: continue
				elif minLOD > maxLOD: continue

				# Check for a minimum size on the image data block. Most image types require at least 0x20 bytes for even just a 1x1 pixel image
				childStructLength = self.getStructLength( imageDataOffset )
				if childStructLength == -1: pass # Can't trust this; unable to calculate the length (data must be after the string table)
				elif imageType == 6 and childStructLength < 0x40: continue
				elif childStructLength < 0x20: continue

				# Check if the child (image data) has any children (which it shouldn't)
				childFound = False
				for pointerOffset in self.pointerOffsets:
					if pointerOffset >= imageDataOffset:
						if pointerOffset < imageDataOffset + childStructLength: # Pointer found in data block
							childFound = True
						break
				if childFound: continue

				# Finally, check that the struct length makes sense (doing this last to avoid the performance hit)
				structLength = self.getStructLength( structureOffset ) # This length will include any padding too
				if structLength < 0x18 or structLength > 0x38: continue # 0x18 + 0x20

				texturesInfo.append( (imageDataOffset, structureOffset, -1, -1, width, height, imageType, int(maxLOD)) ) # Palette info will be found later
				imageDataOffsetsFound.add( imageDataOffset )

		except Exception as err:
			print 'Encountered an error during texture identification:'
			print err
		
		# toc = time.clock()
		# print 'image identification time:', toc - tic

		return texturesInfo

	def getTexture( self, imageDataOffset, width=-1, height=-1, imageType=-1, imageDataLength=-1, getAsPilImage=False ):

		""" Decodes texture data at a given offset and creates an image out of it. 
			Width/height/imageType/imageDataLength can be provided to improve performance. 
			getAsPilImage can be set to True if the user would like to get the PIL image instead. """

		# Make sure file data has been initialized
		self.initialize()

		#tic = time.clock()

		assert type( imageDataOffset ) == int, 'Invalid input to getTexture; image data offset is not an int.'

		# Need to find image details if they weren't provided, so look for the image data header
		if imageType == -1:
			# Get the data section structure offsets, and separate out main structure references
			hI = self.headerInfo
			dataSectionStructureOffsets = set( self.structureOffsets ).difference( (-0x20, hI['rtStart'], hI['rtEnd'], hI['rootNodesEnd'], hI['stringTableStart']) )

			# Scan the data section by analyzing generic structures and looking for standard image data headers
			for structureOffset in dataSectionStructureOffsets:
				# Get the image data header struct's data.
				try: # Using a try block because the last structure offsets may raise an error (unable to get 0x18 bytes) which is fine
					structData = self.getData( structureOffset, 0x18 )
				except:
					continue

				# Unpack the values for this structure, assuming it's an image data header
				fieldValues = struct.unpack( '>IHHIIff', structData )
				headerImageDataOffset, width, height, imageType, _, _, _ = fieldValues

				if headerImageDataOffset == imageDataOffset:
					#print 'header seek time:', time.clock() - tic
					imageDataLength = hsdStructures.ImageDataBlock.getDataLength( width, height, imageType )
					break

			else: # The loop above didn't break; unable to find the header!
				print 'Unable to find an image data header for the imageDataOffset', hex( imageDataOffset+0x20 )
				return None

		# try:
		assert imageDataLength > 0x20, 'Invalid imageDataLength given to getTexture(): ' + hex( imageDataLength )
		imageData = self.getData( imageDataOffset, imageDataLength )

		if imageType == 8 or imageType == 9 or imageType == 10: # Gather info on the palette.
			paletteData, paletteType = self.getPaletteData( imageDataOffset )
		else:
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

	def setTexture( self, imageDataOffset, pilImage=None, imagePath='', textureName='Texture', paletteQuality=3 ): # subsequentMipmapPass=False

		""" Encodes image data into TPL format (if needed), and write it into the file at the given offset. 
			Accepts a PIL image, or a filepath to a PNG or TPL texture file. 
			The offset given should be relative to the start of the data section. 
			Returns a tuple of 3 values; an exit code, and two extra values in the following cases: 
			Return/exit codes:									Extra info:
				0: Success; no problems								None (0, '', '')
				1: Unable to find palette information 				None (1, '', '')
				2: The new image data is too large 					origImageDataLength, newImageDataLength
				3: The new palette data is too large 				maxPaletteColorCount, newPaletteColorCount
		"""
		
		self.initialize()

		# Gather info on the texture currently in the file
		imageDataStruct = self.initDataBlock( hsdStructures.ImageDataBlock, imageDataOffset )
		_, origWidth, origHeight, origImageType, _, _, _ = imageDataStruct.getAttributes()
		origImageDataLength = imageDataStruct.getDataLength( origWidth, origHeight, origImageType )

		# Gather palette information on the texture currently in the file
		if origImageType in ( 8, 9, 10 ):
			# Find information on the associated palette (if unable to, return)
			paletteDataOffset, paletteHeaderOffset, paletteLength, origPaletteType, origPaletteColorCount = self.getPaletteInfo( imageDataOffset )
			if paletteDataOffset == -1: return 1, '', ''

			# If not updating data headers, assume the current palette format must be preserved, and prevent the tplCodec from choosing one (if it creates a palette)
			# In other words, if there are data headers, leave this unspecified so that the codec may intelligently choose the best palette type.
			# if updateDataHeaders and headersAvailable:
			# 	origPaletteType = None # No known value descriptiong for palette type in effects files

			maxPaletteColorCount = paletteLength / 2
		else:
			#origPaletteType = None
			origPaletteColorCount = 255
			maxPaletteColorCount = 255

		# Initialize a TPL image object (and create a new palette for it, if needed)
		if pilImage:
			pilImage = pilImage.convert( 'RGBA' )
			newImage = TplEncoder( '', pilImage.size, origImageType, None, maxPaletteColors=origPaletteColorCount, paletteQuality=paletteQuality )
			newImage.imageDataArray = pilImage.getdata()
			newImage.rgbaPaletteArray = pilImage.getpalette()
			width, height = pilImage.size

		elif imagePath:
			newImage = TplEncoder( imagePath, imageType=origImageType, paletteType=None, maxPaletteColors=origPaletteColorCount, paletteQuality=paletteQuality )
			width, height = newImage.width, newImage.height
			
		else:
			raise IOError( 'Invalid input to .setTexture(); no PIL image or texture filepath provided.' )

		# Decode the image into TPL format
		newImage.blockify()
		newImageData = newImage.encodedImageData
		newPaletteData = newImage.encodedPaletteData

		# Make sure the new image isn't too large
		newImageDataLength = len( newImage.encodedImageData )
		if newImageDataLength > origImageDataLength:
			return 2, origImageDataLength, newImageDataLength
		
		# Replace the palette data in the file
		if origImageType in ( 8, 9, 10 ):
			# Make sure there is space for the new palette, and update the dat's data with it.
			newPaletteColorCount = len( newPaletteData ) / 2 # All of the palette types (IA8, RGB565, and RGB5A3) are 2 bytes per color entry
			if newPaletteColorCount > maxPaletteColorCount:
				return 3, maxPaletteColorCount, newPaletteColorCount

			entriesToFill = origPaletteColorCount - newPaletteColorCount
			nullBytes = bytearray( entriesToFill )
			
			# Update the palette data headers
			if origPaletteType != newImage.paletteType:
				#descriptionOfChange = 'Palette data header updated'
				#self.updateData( paletteHeaderOffset+7, newImage.paletteType, descriptionOfChange ) # sets the palette type
				self.updateData( paletteHeaderOffset+7, newImage.paletteType, trackChange=False )
				
			# Update the palette data
			#self.updateData( paletteDataOffset, newPaletteData + nullBytes, 'Palette data updated' )
			self.updateData( paletteDataOffset, newPaletteData + nullBytes, trackChange=False )

		# Update the image data header(s)
		newHeaderData = struct.pack( '>HHI', width, height, origImageType )
		for offset in imageDataStruct.getParents():
			#self.updateData( offset+4, newHeaderData, 'Image data header updated' )
			self.updateData( offset+4, newHeaderData, trackChange=False )

		# If the new texture is smaller than the original, fill the extra space with zeroes
		if newImageDataLength < origImageDataLength:
			newImageData.extend( bytearray(origImageDataLength - newImageDataLength) ) # Adds n bytes of null data

		# Update the texture image data in the file
		#self.updateData( imageDataOffset, newImageData, 'Image data updated' )
		self.updateData( imageDataOffset, newImageData, trackChange=False )
		self.recordChange( '{} updated at 0x{:X}'.format(textureName, 0x20+imageDataOffset) )

		return 0, '', ''

	def getPaletteInfo( self, imageDataOffset ):

		""" Doesn't get the palette data itself, but attempts to find/return information on it. There is hardcoded information for certain files, 
			which are checked first, followed by checks for effects files. Standard DAT/USD files are then checked using two different methods, 
			by looking through the structure hierarchy from the bottom upwards. The first method looks for a path from Image Headers to Texture 
			structures, in order to get the palette header's offset and other info. The second method (if the first fails), checks for a Image 
			Data Array structure, and then the parent Texture Animation Struct. From there, the palette header array structure and respective
			palette header for the target image can be found. 
			
			This returns a tuple of info in the form ( paletteDataOffset, paletteHeaderOffset, paletteLength, paletteType, paletteColorCount ) """

		# Handle special cases for certain files
		# if (0x1E00, 'MemSnapIconData') in datFile.rootNodes: # The file is LbMcSnap.usd or LbMcSnap.dat (Memory card banner/icon file from SSB Melee)
		# 	# There's only one palette that might be desired in here (no headers available).
		# 	return 0x1C00, -1, 0x200, 2, 256

		# elif (0x4E00, 'MemCardIconData') in datFile.rootNodes: # The file is LbMcGame.usd or LbMcGame.dat (Memory card banner/icon file from SSB Melee)
		# 	return 0x4C00, -1, 0x200, 2, 256

		# elif isEffectsFile( datFile ): # These have normal structuring as well as some unique table structuring
		# 	imageDataStruct = datFile.getStruct( imageDataOffset )

		# 	# The unique structuring should have already saved the palette info
		# 	if imageDataStruct and imageDataStruct.paletteDataOffset != -1 and imageDataStruct.paletteHeaderOffset != -1:
		# 		return ( imageDataStruct.paletteDataOffset, imageDataStruct.paletteHeaderOffset, 0x200, 2, 256 )

		# Proceeding to check within standard DAT/USD files
		headerOffsets = self.getStruct( imageDataOffset ).getParents()
		paletteHeaderStruct = None

		for imageHeaderOffset in headerOffsets:
			imageDataHeader = self.initSpecificStruct( hsdStructures.ImageObjDesc, imageHeaderOffset, printWarnings=False )
			if not imageDataHeader: continue

			for headerParentOffset in imageDataHeader.getParents():
				# Test for a Texture Struct
				textureStruct = self.initSpecificStruct( hsdStructures.TextureObjDesc, headerParentOffset, printWarnings=False )
				
				if textureStruct:
					# Texture Struct Found; initialize the child palette header structure
					paletteHeaderOffset = textureStruct.getValues()[22]
					paletteHeaderStruct = self.initSpecificStruct( hsdStructures.PaletteObjDesc, paletteHeaderOffset, textureStruct.offset )
					break
				else:
					# Test for an Image Data Array structure
					imageHeaderArrayStruct = self.initSpecificStruct( hsdStructures.ImageHeaderArray, headerParentOffset, printWarnings=False )

					if imageHeaderArrayStruct:
						# Get the parent Texture Animation Struct, to get the palette header array offset
						texAnimStructOffset = imageHeaderArrayStruct.getAnyDataSectionParent()
						texAnimStruct = self.initSpecificStruct( hsdStructures.TexAnimDesc, texAnimStructOffset, printWarnings=False )

						if texAnimStruct:
							paletteIndex = imageHeaderArrayStruct.getValues().index( imageHeaderOffset )

							# Make sure there is a palette header array structure (there may not be one if a palette is shared!)
							if texAnimStruct.offset + 0x10 in self.pointerOffsets:
								# Palette header array struct present. Get the corresponding palette header offset and structure
								paletteHeaderArrayOffset = texAnimStruct.getValues()[4]
								paletteHeaderPointerOffset = paletteHeaderArrayOffset + ( paletteIndex * 4 )
								paletteHeaderOffset = struct.unpack( '>I', self.getData(paletteHeaderPointerOffset, 4) )[0] # Grabbing 4 bytes and unpacking them
								paletteHeaderStruct = self.initSpecificStruct( hsdStructures.PaletteObjDesc, paletteHeaderOffset, paletteHeaderArrayOffset )
							elif paletteIndex == 0: # The first texture should have a normal Texture struct as well, so just move on to that.
								continue
							else: # Must share a palette with the first texture
								# Get the image data structure for the first texture in the array
								imageDataHeader = self.initSpecificStruct( hsdStructures.ImageObjDesc, imageHeaderArrayStruct.values[0] )
								imageDataOffset = imageDataHeader.getValues()[0]
								imageDataStruct = self.initDataBlock( hsdStructures.ImageDataBlock, imageDataOffset, imageDataHeader.offset )

								# Check the image data's parents to get the other image data header (the one that leads to a Texture Struct)
								for headerOffset in imageDataStruct.getParents().difference( (imageDataHeader.offset,) ): # Excluding the image data header above
									imageDataHeader = self.initSpecificStruct( hsdStructures.ImageObjDesc, headerOffset, printWarnings=False )
									if not imageDataHeader: continue
									
									for headerParentOffset in imageDataHeader.getParents():
										textureStruct = self.initSpecificStruct( hsdStructures.TextureObjDesc, headerParentOffset, printWarnings=False )
										if not textureStruct: continue
										
										# Texture Struct Found; initialize the child palette header structure
										paletteHeaderOffset = textureStruct.getValues()[22]
										paletteHeaderStruct = self.initSpecificStruct( hsdStructures.PaletteObjDesc, paletteHeaderOffset, textureStruct.offset )
										break
									if paletteHeaderStruct: break
							break

			if paletteHeaderStruct: break

		if paletteHeaderStruct:
			paletteDataOffset, paletteType, _, colorCount = paletteHeaderStruct.getValues()
			paletteLength = self.getStructLength( paletteDataOffset )
			return ( paletteDataOffset, paletteHeaderStruct.offset, paletteLength, paletteType, colorCount )
		else:
			return ( -1, -1, None, None, None )

	def getPaletteData( self, imageDataOffset=-1, paletteDataOffset=-1, imageData=None, imageType=-1 ):

		""" Gets palette data from the file, looking up palette info if needed. If image data is provided, it is checked 
			to determine how many colors are actually used (colorCount from the palette data header can't be trusted). """

		# Get the offset of the palette data, if not provided
		if paletteDataOffset == -1:
			assert imageDataOffset != -1, 'Image data offset not provided to get palette data!'
			paletteDataOffset, _, paletteLength, paletteType, colorCount = self.getPaletteInfo( imageDataOffset )
		else:
			paletteLength = self.getStructLength( paletteDataOffset )
			paletteType = -1
			colorCount = -1

		if imageData:
			if imageType == 8: # Break up every byte into two 4-bit values
				paletteIndexArray = [ x for i in imageData for x in (i>>4, i&0b1111) ]
			elif imageType == 9: # Can just use the original bytearray (each entry is 1 byte)
				paletteIndexArray = imageData
			elif imageType == 10: # Combine half-word bytes
				paletteIndexArray = struct.unpack( '>{}H'.format(len(imageData)/2), imageData )
			else:
				raise Exception( 'Invalid image type given to getPaletteData: ' + str(imageType) )

			colorCount = max( paletteIndexArray ) + 1
			paletteData = self.getData( paletteDataOffset, colorCount * 2 ) # All palette types are two bytes per color
			
		else:
			# Without the image data, we can't really trust the color count, especially for some older texture hacks
			assert paletteLength, 'Invalid palette length to get palette data: ' + str(paletteLength)
			paletteData = self.getData( paletteDataOffset, paletteLength )

		return paletteData, paletteType

	def getBranch( self, offset ):

		""" Returns all structures that make up a given branch of a dat file
			(i.e. a structure and all of its children/siblings/decendants). """

		parentStruct = self.getStruct( offset )
		# print( 'parent: ' + hex(0x20 + parentStruct.offset) )
		structs = [ parentStruct ]

		structs.extend( parentStruct.getBranchDescendants() )

		# print( [hex(0x20+s.offset) for s in structs] )
		# print( 'total size: ' + hex(parentStruct.getBranchSize()) )

		return structs

	def exportBranch( self, offset, savePath ):

		""" Exports all structures that make up a given branch of a dat file
			(i.e. a structure and all of its children/siblings/decendants)
			and creates a dat file out of it for saving it externally. """

		structs = self.getBranch( offset )
		structs.sort( key=lambda s: s.offset )

		# Create a new, empty DAT file
		newDat = DatFile( None, -1, -1, '', source='self' )
		
		newStructOffsets = {}
		#pointers = []
		oldPointerValues = []
		#data = bytearray()
		#pointersData = bytearray

		# Collect the structs into a new data section
		for structure in structs:
			dataPosition = len( newDat.data )

			# Collect pointer offsets for the new relocation table; iterate over all pointers in this 
			# file's data section, looking for those that are within the offset range of this structure.
			for pointerOffset, pointerValue in self.pointers:
				# Ensure we're only looking in range of this struct
				if pointerOffset < structure.offset: continue
				elif pointerOffset >= structure.offset + structure.length: break

				# Store the new pointer offset
				pointerRelOffset = pointerOffset - structure.offset
				newDat.pointerOffsets.append( dataPosition + pointerRelOffset )
				#pointersData.append( structure.data[pointerRelOffset:pointerRelOffset+4] )
				oldPointerValues.append( pointerValue )

			# Collect the struct's data, ensuring 4-byte alignment
			newDat.data.extend( structure.data )
			padding = len( newDat.data ) % 4
			newDat.data.extend( bytearray(padding) )
			newStructOffsets[structure.offset] = dataPosition
		newDat.rtNeedsRebuilding = True

		# pointersFormatting = '>{}I'.format( len(pointersData)/4 )
		# oldPointerValues = struct.unpack( pointersFormatting, pointersData )

		# Update the pointer values in this new data section; point to new struct offsets
		for pointer, oldValue in zip( newDat.pointerOffsets, oldPointerValues ):
			newValue = newStructOffsets[oldValue]
			newDat.data[pointer:pointer+4] = struct.pack( '>I', newValue )

		# Create a root node string (symbol)
		if self.isoPath:
			filename = os.path.basename( self.isoPath )
			nodeString = filename + '_Branch_'
		else:
			nodeString = 'Branch_'
		label = self.getStructLabel( offset )
		if label:
			nodeString += label
		else:
			nodeString += '0x{:X}'.format( 0x20 + offset )

		# Add data that will become the root nodes and strings tables
		newDat.rootNodes = [ (0, nodeString) ]
		#newDat.rebuildNodeAndStringTables()
		newDat.nodesNeedRebuilding = True

		# Add header info and trigger it to be built
		newDat.headerInfo = {
			'filesize': 0x20 + len( newDat.data ) + ( len(newDat.pointerOffsets) * 4 ) + 8 + len( newDat.stringTableData ),
			'rtStart': len( newDat.data ), # Also the size of the data block
			'rtEntryCount': len( newDat.pointerOffsets ),
			'rootNodeCount': 1,
			'referenceNodeCount': 0,
			#'magicNumber': u'\x00\x00\x00\x00',
			# 'rtEnd': -1,
			# 'rootNodesEnd': -1,
			# 'stringTableStart': -1, # Each root/reference node table entry is 8 bytes
		}
		self.headerData = bytearray( 0x20 )
		newDat.headerNeedsRebuilding = True

		newDat.export( savePath )

	def importBranch( datFileObj, importOffset, node=0, offset=0 ):

		""" Imports a whole or part (a branch) of the data section of a DAT file into 
			the given offset of this file. If both node and offset are unspecified (0), 
			then the entire data section of the file will be imported. """



	def structuresEquivalent( self, struct1, struct2, checkWholeBranch=True, blacklist=None, whitelist=None ):

		""" Compares two structures to see if they are equivalent. Differences in 
			pointer values are ignored. If 'checkWholeBranch' is True, the entire 
			branch (the given structs and all of their decendants) are checked. """

		if struct1.length != struct2.length:
			print( '{} and {} not equivalent; lengths mismatch: 0x{:X} != 0x{:X}'.format(struct1.name, struct2.name, struct1.length, struct2.length) )
			return False

		struct1Children = struct1.getChildren( includeSiblings=True )
		struct2Children = struct2.getChildren( includeSiblings=True )

		if len( struct1Children ) != len( struct2Children ):
			print( '{} and {} not equivalent; child count mismatch: {} != {}'.format(struct1.name, struct2.name, len(struct1Children), len(struct2Children)) )
			return False

		# Get pointer offsets within this struct
		pointerOffsets1 = []
		for pointerOffset, _ in struct1.dat.pointers:
			# Ensure we're only looking in range of this struct
			if pointerOffset < struct1.offset: continue
			elif pointerOffset >= struct1.offset + struct1.length: break
			pointerOffsets1.append( pointerOffset - struct1.offset )
		pointerOffsets2 = []
		for pointerOffset, _ in struct2.dat.pointers:
			# Ensure we're only looking in range of this struct
			if pointerOffset < struct2.offset: continue
			elif pointerOffset >= struct2.offset + struct2.length: break
			pointerOffsets2.append( pointerOffset - struct2.offset )

		# These are relative at this point, so these should be equal
		if pointerOffsets1 != pointerOffsets2:
			print( '{} and {} not equivalent; child pointers mismatch'.format(struct1.name, struct2.name) )
			return False

		# Scan the structures' data, looking for differences
		position = 0
		for byte1, byte2 in zip( struct1.data, struct2.data ):
			# Check if at the boundary of a 4-byte multiple
			if position % 4 == 0:
				# Check if this (this and next 3 bytes) is a pointer
				if position in pointerOffsets1:
					checkingPointer = True
					
					# Look ahead to the full pointer value and compare them
					pointer1 = struct1.data[position:position+4]
					pointer2 = struct2.data[position:position+4]

					# Check if only one of the pointers is null (no, this is not redundant to child count check!)
					if pointer1 == bytearray( 4 ) or pointer2 == bytearray( 4 ):
						if pointer1 != pointer2: # Only one pointer is null
							print( '{} and {} not equivalent; children differ'.format(struct1.name, struct2.name) )
							return False
				else:
					checkingPointer = False

			# Check non-pointer bytes for differences
			if not checkingPointer and byte1 != byte2:
				print( '{} and {} not equivalent; data differs'.format(struct1.name, struct2.name) )
				return False

			position += 1

		if not checkWholeBranch:
			return True

		# These structs are the same so far; check decendants
		for child1Offset, child2Offset in zip( struct1Children, struct2Children ):
			child1Struct = struct1.dat.getStruct( child1Offset )
			child2Struct = struct2.dat.getStruct( child2Offset )

			if not child1Struct or not child2Struct:
				if child1Struct and not child2Struct:
					print( '{} and {} not equivalent; null pointer mismatch (invalid s2)'.format(struct1.name, struct2.name) )
					return False
				elif child2Struct and not child1Struct:
					print( '{} and {} not equivalent; null pointer mismatch (invalid s1)'.format(struct1.name, struct2.name) )
					return False
				else:
					# At least the structs match. Continue on but give a warning
					print( 'Warning! Invalid pointer detected in structs {} and {}'.format(struct1.name, struct2.name) )

			# Only check whitelisted structs if those were specified
			if whitelist and child1Struct.__class__ not in whitelist:
				#print( 'Skipping {}, as its class is {}'.format(child1Struct.name, child1Struct.__class__.__name__) )
				continue

			# Ignore blacklisted structs
			elif blacklist and child1Struct.__class__ in blacklist:
				#print( 'Skipping {}'.format(child1Struct.name) )
				continue

			elif not self.structuresEquivalent( child1Struct, child2Struct, True, blacklist, whitelist ):
				#print( '{} and {} not equivalent; child diff between '.format(struct1.name, struct2.name, child1Struct.name, child2Struct.name) )
				return False

		return True