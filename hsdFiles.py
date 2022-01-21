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
from ruamel import yaml
from string import hexdigits
from PIL import Image, ImageTk

# Internal dependencies
import dol
import globalData
import hsdStructures
import standaloneStructs
from tplCodec import TplDecoder, TplEncoder
#from globalData import globalData.charNameLookup, globalData.charColorLookup
from basicFunctions import allAreEqual, uHex, msg, dictReverseLookup, printStatus, toInt, createFolders, cmdChannel

showLogs = True


def findBytes( bytesRange, target ): # Searches a bytearray for a given (target) set of bytes, and returns the location (index)
	targetLength = len( target )

	for index, _ in enumerate( bytesRange ):
		if bytesRange[index:index+targetLength] == target: return index
	else: return -1


def isValidReplacement( origFileObj, newFileObj ):

	""" Attempts to determine if two files could be valid replacements for one another. """

	# First, a simple check on file class
	fileMismatch = False
	if origFileObj.__class__ != newFileObj.__class__:
		fileMismatch = True

	# If the files (which are the same class) are a sub-class of DAT files....
	elif issubclass( origFileObj.__class__, (DatFile,) ):
		orig20xxVersion = globalData.disc.is20XX

		# Initialize the files so we can get their string dictionaries (and make sure they're not corrupted)
		try:
			origFileObj.initialize()
			origFileStrings = sorted( origFileObj.stringDict.values() )
		except: # The file appears to be corrupted
			origFileStrings = [] # Should still check on the second file
		try:
			newFileObj.initialize()
			newFileStrings = sorted( newFileObj.stringDict.values() )
		except:
			# The file appears to be corrupted; cannot compare further, so just warn the user now
			if not tkMessageBox.askyesno( 'File Corruption Warning', "The file you're importing, {}, could not be initialized, which means "
											"it may be corrupted.\n\nAre you sure you want to continue?".format(newFileObj.filename) ):
				return False
			else:
				return True
		
		# Compare the files' string dictionaries. They're sorted into the same order above (we only care that the same ones exist)
		if origFileStrings != newFileStrings:
			fileMismatch = True
			
		# If the file being imported is the CSS. Check if it's for the right game version
		#elif issubclass( origFileObj, (CssFile,) ):
		elif origFileObj.__class__.__name__ == 'CssFile' and orig20xxVersion:

			# Check if this is a version of 20XX, and if so, get its main build number
			#orig20xxVersion = globalData.disc.is20XX
			if orig20xxVersion:
				if 'BETA' in orig20xxVersion: origMainBuildNumber = int( orig20xxVersion[-1] )
				else: origMainBuildNumber = int( orig20xxVersion[0] )
			else: origMainBuildNumber = 0

			#cssfileSize = os.path.getsize( newExternalFilePath )
			#proposed20xxVersion = globalDiscDetails['is20XX']
			proposed20xxVersion = globalData.disc.get20xxVersion( newFileObj.getData() )
			if proposed20xxVersion:
				if 'BETA' in proposed20xxVersion: proposedMainBuildNumber = int( proposed20xxVersion[-1] )
				else: proposedMainBuildNumber = int( proposed20xxVersion[0] )
			else: proposedMainBuildNumber = 0

			if orig20xxVersion == '3.02': pass # Probably all CSS files will work for this, even the extended 3.02.01 or 4.0x+ files

			elif newFileObj.size < 0x3A3BCD: # importing a vanilla CSS over a 20XX CSS
				if not tkMessageBox.askyesno( 'Warning! 20XX File Version Mismatch', """The CSS file you're """ + 'importing, "' + newFileObj.filename + """", is for a standard copy """
											'of Melee (or a very early version of 20XX), and will not natively work for post-v3.02 versions of 20XX. Alternatively, you can extract '
											"textures from this file and import them manually if you'd like.\n\nAre you sure you want to continue with this import?" ):
					return False

			elif origMainBuildNumber != proposedMainBuildNumber: # These are quite different versions
				if not tkMessageBox.askyesno( 'Warning! 20XX File Version Mismatch', """The CSS file you're """ + 'importing, "' + newFileObj.filename + """", was """
											'not designed for to be used with this version of 20XX and may not work. Alternatively, you can extract '
											"textures from this file and import them manually if that's what you're after.\n\nAre you sure you want to continue with this import?" ):
					return False

	# Check file extension as a last resort
	elif origFileObj.ext != newFileObj.ext:
		fileMismatch = True

	if fileMismatch: # Return false if the user doesn't OK this mismatch
		if not tkMessageBox.askyesno( 'File Mismatch Warning', "The file you're importing, {}, doesn't appear to be a valid replacement "
										"for {}.\n\nAre you sure you want to do this?".format(newFileObj.filename, origFileObj.filename) ):
			return False
		# else return True, below
	
	return True


def fileFactory( *args, **kwargs ):

	""" Parse out the file name from isoPath, and use that to 
		determine what class to initialize the file as. If the keyword 
		argument "trustNames" is given, filenames will be trusted to 
		determine what kind of file to initialize as. """

	trustyFilenames = kwargs.pop( 'trustNames', None ) # Also removes it from kwargs
	filepath, ext = os.path.splitext( args[3] )
	filename = os.path.basename( filepath ) # Without extension

	# Attempt to determine by file type
	if ext == '.dol':
		return dol.Dol( *args, **kwargs )

	elif ext == '.bin':
		return FileBase( *args, **kwargs )

	elif ext == '.hps':
		return MusicFile( *args, **kwargs )

	elif filename.startswith( 'opening' ) and ext == '.bnr': # May support openingUS.bnr, openingEU.bnr, etc. in the future
		return BannerFile( *args, **kwargs )

	elif ext in ( '.mth', '.ssm', '.sem', '.ini' ):
		return FileBase( *args, **kwargs )

	# If this is initializing an external/standalone file, we may not be able to trust the file name
	elif not trustyFilenames and kwargs.get( 'extPath' ) and kwargs.get( 'source' ) == 'file': # A slower but more thorough check.

		try:
			# Assume it's a DAT file by this point
			fileObj = DatFile( *args, **kwargs )
			fileObj.initialize()

			if 'map_head' in fileObj.stringDict.values():
				return StageFile( *args, **kwargs )

			elif len( fileObj.rootNodes ) == 1 and fileObj.rootNodes[0][1].startswith( 'SIS_' ): # Indexing a list of tuples
				return SisFile( *args, **kwargs )

			elif fileObj.rootNodes[0][1].endswith( '_Share_joint' ): # Indexing a list of tuples
				return CharCostumeFile( *args, **kwargs )

			elif 'MnSelectChrDataTable' in fileObj.stringDict.values():
				return CssFile( *args, **kwargs )
			else:
				return fileObj

		except Exception as err:
			message = 'Unrecognized file:' + kwargs['extPath'] + '\n' + str( err )
			printStatus( message, error=True )
			
			return FileBase( *args, **kwargs )

	else: # A fast check that doesn't require getting the file data (ideal if the file name can be trusted)
		
		if filename.startswith( 'Gr' ):
			return StageFile( *args, **kwargs )

		elif filename.startswith( 'Sd' ):
			return SisFile( *args, **kwargs )

		# Character costume files; excludes 'PlBo.dat'/'PlCa.dat'/etc. and character animation files
		elif filename.startswith( 'Pl' ) and len( filename ) == 6 and filename[-2:] != 'AJ':

			if filename[2:6] == 'KbCp': pass # Oh, Kirby.... (these are copy powers; ftData)
			else:
				charFile = CharCostumeFile( *args, **kwargs )
				charFile._charAbbr = filename[2:4] # Save some work later
				charFile._colorAbbr = filename[4:6]

				return charFile

		elif filename.startswith( 'MnSlChr' ):
			return CssFile( *args, **kwargs )

		return DatFile( *args, **kwargs )


					# = ----------------------- = #
					#  [   Disc File Classes   ]  #
					# = ----------------------- = #

class FileBase( object ):

	""" This is a superclass to every other [non-disc] file class. """

	yamlDescriptions = {}

	def __init__( self, disc, offset, size, isoPath, description='', extPath='', source='disc' ):

		self.ext = os.path.splitext( isoPath )[1].lower()		# File extension. Includes '.' (dot)
		self.disc = disc
		self.size = size				# Current size of the file in bytes
		self.data = bytearray()
		self.source = source			# One of 'disc', 'file' (external file), or 'self' (exists only in memory)
		self.offset = offset			# Disc offset. An offset of -1 indicates a file not yet given a location
		self.isoPath = isoPath			# e.g. 'GALE01/audio/1padv.ssm' if this is for a file in a disc
		self.extPath = extPath			# External path. I.e. a full (absolute) system file path if this is a standalone file
		self.origSize = size			# Should always be the original size of the file (even if its data changes size)
		#self.description = description
		self._shortDescription = description
		self._longDescription = description
		#self.updateSummary = set()		# Summary of changes done to this file
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

	@property
	def longDescription( self ):
		if not self._longDescription:
			self.getDescription()
		
		return self._longDescription

	@classmethod
	def setupDescriptions( cls, gameId ):

		""" Attempts to load file descriptions from a file in './File Descriptions/[gameID].yaml'
			Should only occur once; typically after a disc file or root folder has been instantiated as a disc,
			but before the disc has been loaded into the GUI. """

		descriptionsFile = os.path.join( globalData.scriptHomeFolder, 'File Descriptions', gameId + '.yaml' )
		
		try:
			with codecs.open( descriptionsFile, 'r', encoding='utf-8' ) as stream: # Using a different read method to accommodate UTF-8 encoding
			#with codecs.open( descriptionsFile, 'r' ) as stream: # Using a different read method to accommodate UTF-8 encoding
				#cls.yamlDescriptions = yaml.safe_load( stream ) # Vanilla yaml module method (loses comments when saving/dumping back to file)
				cls.yamlDescriptions = yaml.load( stream, Loader=yaml.RoundTripLoader )
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
					#self.source = 'self'

				elif self.source == 'file':
					with open( self.extPath, 'rb' ) as externalFile:
						self.data = bytearray( externalFile.read() )
					#self.source = 'self'

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

		if type( newData ) == int: # Just a single byte/integer value (0-255)
			assert newData >= 0 and newData < 256, 'Invalid input to FileBase.setData(): ' + str(newData)
			newData = ( newData, ) # Need to make it an iterable, for the splicing operation
			dataLength = 1
		else:
			dataLength = len( newData )

		assert dataOffset + dataLength <= len( self.data ), '0x{:X} is too much data to set at offset 0x{:X}.'.format( dataLength, dataOffset )
		self.data[dataOffset:dataOffset+dataLength] = newData # This will also work for bytearrays of length 1

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
				#yaml.safe_dump( self.yamlDescriptions, stream ) # Vanilla yaml module method (loses comments when saving/dumping back to file)
				yaml.dump( self.yamlDescriptions, stream, Dumper=yaml.RoundTripDumper )
			return 0
		except Exception as err: # Problem parsing the file
			msg( 'Unable to save the new name to the yaml config file:\n\n{}'.format(err) )
			return 1


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

		return ( magicWord == bytearray(b'BNR1') or magicWord == bytearray(b'BNR2') )


					# = ---------------------- = #
					#  [   HSD File Classes   ]  #
					# = ---------------------- = #

class DatFile( FileBase ):

	""" Subclass for .dat and .usd files. """

	# def __init__( self, disc, offset, size, isoPath, description='', extPath='', source='disc' ):
	# 	#super( DatFile, self ).__init__( self, disc, offset, size, isoPath, description=description, extPath=extPath, source=source )
	# 	FileBase.__init__( self, disc, offset, size, isoPath, description, extPath, source )
		
	def __init__( self, *args, **kwargs ):
		FileBase.__init__( self, *args, **kwargs )

		# File data groups
		self.headerData = bytearray()		# First 0x20 bytes of most DAT files
		#	self.data = bytearray()				# Of just the data section (unless a DOL or banner file)
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
		assert stringTableLength != -1, 'Invalid string table length; unable parse string table'
		
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

		try:
			filesize, rtStart, rtEntryCount, rootNodeCount, referenceNodeCount = struct.unpack( '>5I', self.headerData[:0x14] )
			rtEnd = rtStart + ( rtEntryCount * 4 )
			rootNodesEnd = rtEnd + ( rootNodeCount * 8 ) # Each root/reference node table entry is 8 bytes

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

		except Exception as errorMessage:
			if showLogs:
				print 'Unable to parse the DAT file header of', self.printPath()
				print errorMessage

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
			if showLogs:
				print 'Unable to parse the DAT file relocation table of', self.printPath()
				print errorMessage

	def parseStringTable( self ):

		""" Creates a dictionary for the string table, where keys=dataSectionOffsets, and values=stringLabels. """

		try:
			stringTable = self.data[self.headerInfo['stringTableStart']:] # Can't separate this out beforehand, without knowing its length
			totalStrings = self.headerInfo['rootNodeCount'] + self.headerInfo['referenceNodeCount']

			self.stringDict = {}
			stringTableLength = 0
			strings = stringTable.split( b'\x00' )[:totalStrings] # End splicing eliminates an empty string, and/or extra additions at the end of the file.

			for stringBytes in strings:
				string = stringBytes.decode( 'ascii' ) # Convert the bytearray to a text string
				self.stringDict[stringTableLength] = string
				stringTableLength += len( string ) + 1 # +1 to account for null terminator

			return stringTableLength

		except Exception as errorMessage:
			self.stringDict = {}
			if showLogs:
				print "Unable to parse the string table of", self.printPath()
				print errorMessage
			return -1

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

		try:
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

		except Exception as errorMessage:
			if showLogs:
				print "Unable to parse the root/reference nodes table of", self.printPath()
				print errorMessage

	def evaluateStructs( self ):

		""" Sorts the lists of pointer offsets and pointer values (by offset), and creates a sorted list 
			of all [unique] structure offsets in the data section, which includes offsets for the file 
			header (at -0x20), RT, root nodes table, reference nodes table (if present), and string table. """

		try:
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

		except Exception as errorMessage:
			if showLogs:
				print "Unable to evaluate the file's structs;"
				print errorMessage

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
			if showLogs:
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
			if showLogs:
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
			newStructClass = getattr( sys.modules[hsdStructures.__name__], structure, None ) # Changes a string into a class by that name

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

		# Return just the data section if no args were given
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
		for structOffset, stringOffset in self.rootNodes:
			# Collect unaffected nodes
			if structOffset < extensionOffset:
				newRootNodes.append( (structOffset, stringOffset) )
			else: # Struct offset is past the affected area; needs to be increased
				newRootNodes.append( (structOffset + amount, stringOffset) )
				nodesModified = True
		if nodesModified:
			self.rootNodes = newRootNodes
			self.nodesNeedRebuilding = True

		# Update reference nodes
		newRefNodes = []
		nodesModified = False
		for structOffset, stringOffset in self.referenceNodes:
			# Collect unaffected nodes
			if structOffset < extensionOffset:
				newRefNodes.append( (structOffset, stringOffset) )
			else: # Struct offset is past the affected area; needs to be reduced
				newRefNodes.append( (structOffset + amount, stringOffset) )
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
		# updateSummaryMsg = 
		# if updateSummaryMsg not in self.updateSummary:
		#self.updateSummary.add( 'Texture updated at ' + uHex(0x20+imageDataOffset) )
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


class CssFile( DatFile ):

	""" Special subclass for the Character Select Screen. """

	randomNeutralStageNameTables = { # Offsets for pointer tables (relative to data section start)
			'GrNBa': 	0x3C10C0, 	# Battlefield
			'GrNLa': 	0x3C1320, 	# Final Destination
			'GrSt':		0x3C1580, 	# Yoshi's Story
			'GrIz':		0x3C17E0, 	# Fountain
			'GrOp':		0x3C1A40, 	# Dream Land
			'GrP':		0x3C1CA0 } 	# Stadium

	cspIndexes = {	# key = External Char ID x 0x10 + Costume ID, value = CSP index
		0x00: 33, 0x01: 62, 0x02: 81, 0x03: 102, 0x04: 43, 0x05: 10, 	# Captain Falcon - 0x0
		0x10: 36, 0x11: 7, 0x12: 83, 0x13: 12, 0x14: 44, 	# DK
		0x20: 40, 0x21: 87, 0x22: 15, 0x23: 48, 	# Fox
		0x30: 5, 0x31: 80, 0x32: 4, 0x33: 42, 	# Game & Watch
		0x40: 66, 0x41: 111, 0x42: 19, 0x43: 91, 0x44: 52, 0x45: 105, 	# Kirby
		0x50: 67, 0x51: 92, 0x52: 20, 0x53: 1,	# Bowser
		0x60: 68, 0x61: 93, 0x62: 21, 0x63: 2, 0x64: 106,	# Link
		0x70: 69, 0x71: 107, 0x72: 22, 0x73: 94, 	# Luigi
		0x80: 70, 0x81: 112, 0x82: 3, 0x83: 23, 0x84: 53, # Mario - 0x8
		0x90: 38, 0x91: 85, 0x92: 46, 0x93: 0, 0x94: 104, 	# Marth
		0xA0: 71, 0xA1: 95, 0xA2: 24, 0xA3: 54, 	# Mewtwo
		0xB0: 72, 0xB1: 113, 0xB2: 25, 0xB3: 55, 	# Ness
		0xC0: 74, 0xC1: 35, 0xC2: 108, 0xC3: 26, 0xC4: 56, 	# Peach
		0xD0: 78, 0xD1: 97, 0xD2: 28, 0xD3: 58, 	# Pikachu
		0xE0: 63, 0xE1: 50, 0xE2: 17, 0xE3: 89, 	# Ice Climbers
		0xF0: 79, 0xF1: 98, 0xF2: 29, 0xF3: 59, 0xF4: 114, 	# Jigglypuff
		0x100: 101, 0x101: 76, 0x102: 9, 0x103: 60, 0x104: 30, # Samus - 0x10
		0x110: 116, 0x111: 99, 0x112: 31, 0x113: 115, 0x114: 77, 0x115: 65, 	# Yoshi
		0x120: 117, 0x121: 100, 0x122: 32, 0x123: 61, 0x124: 109, 	# Zelda
		#0x130: , 0x131: , 0x132: , 0x133: , 0x134: , 	# Sheik		# Someday :)
		0x140: 39, 0x141: 86, 0x142: 14, 0x143: 47, 	# Falco
		0x150: 34, 0x151: 82, 0x152: 11, 0x153: 103, 0x154: 6, # Young Link
		0x160: 37, 0x161: 84, 0x162: 13, 0x163: 45, 0x164: 8, # Doc
		0x170: 64, 0x171: 90, 0x172: 18, 0x173: 51, 0x174: 110, 	# Roy
		0x180: 75, 0x181: 96, 0x182: 27, 0x183: 57, # Pichu - 0x18
		0x190: 41, 0x191: 88, 0x192: 16, 0x193: 49, 0x194: 73 # Ganondorf
	}

	# These will be shared across CSS files; so if one file checks, they'll all know
	_hasRandomNeutralTables = False
	_checkedForRandomNeutralTables = False

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
			normalizedVersion = float( ''.join([char for char in v20XX if char.isdigit() or char == '.']) ) # removes non-numbers and typecasts it
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

		stageName = self.getData( nameOffset, 0x20 ).split('\x00')[0].decode( 'ascii' )

		return stageName

	def setRandomNeutralName( self, filename, newStageName ):

		""" Sets a new stage name string in the respective string table. May return the following codes:
				0: Success; no problems
				1: Not applicable to this disc (it's not 20XX or not the right version)
				2: Not applicable to this filename 
				3: Invalid stage name input """

		# Make sure this is applicable
		if not self.hasRandomNeutralTables():
			#return 1
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
			#return 2
			raise Exception( 'Operation not applicable for this filename' )

		# Convert the given string to bytes (should have already been validated)
		try:
			nameBytes = bytearray()
			nameBytes.extend( newStageName )
			if len( nameBytes ) > 0x1F:
				raise Exception( 'New stage name is too long after encoding (' + str(len(nameBytes)) + ' bytes).' )
		except Exception as err:
			print 'Unable to convert the stage name to bytes; ' + err
			#return 3
			raise Exception( 'Unable to convert the string to bytes' )

		# Add null data to fill the remaining space for this string (erasing pre-existing characters)
		padding = bytearray( 0x20 - len(nameBytes) ) # +1 to byte limit to add the null byte

		self.setData( nameOffset, nameBytes+padding )
		self.recordChange( 'Random Neutral stage name updated for ' + newStageName )

		#return 0

	def checkMaxHexTrackNameLen( self, trackNumber, fileOffset=0 ):

		""" Checks how much space is available for custom names for 20XX hex tracks. 
			Note that these are title names, as seen in the Debug Menu, not file names. 
			These names are the same ones used for music files' "description" property. 
			Pointers to these strings are in the CSS tail data, in a table at 0x3EDDA8. 
			Songs up to hex track 48 are vanilla songs, and their strings are end-to-end, 
			with no extra space for longer names. However, songs beyond that are custom 
			songs with extra padding following their strings, allowing for longer names. """

		if trackNumber < 0 or trackNumber > 0xFF:
			print 'Unrecognized track ID!', hex( trackNumber )
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

			print 'Adding new hex track song name pointer table entry'
			# Add the new pointer to the table
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
			print 'Unable to convert the song name to bytes; ' + str( err )
			raise Exception( 'Unable to convert the string to bytes' )

		if len( nameBytes ) > byteLimit:
			raise Exception( 'New song name is too long after encoding ({} bytes).'.format(len(nameBytes)) )

		# Add null data to fill the remaining space for this string (erasing pre-existing characters)
		padding = bytearray( byteLimit + 1 - len(nameBytes) ) # +1 to add the null byte

		self.setData( fileOffset, nameBytes+padding )
		self.recordChange( 'Hex Track name updated for {} (track 0x{:02X})'.format(newName, trackNumber) )

	def importCsp( self, filepath, charId, costumeId, textureName='' ):

		""" Use the character and costume IDs to look up the texture offset, 
			and import the given texture to that location in the file. 
			Same return information as .setTexture() """

		baseOffset = 0x4CA40
		stride = 0x6600 # Texture size + palette data/header

		# Make sure Sheik isn't given
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
		cspOffset = ( baseOffset + cspIndex * stride ) - 0x20
		returnInfo = self.setTexture( cspOffset, None, filepath, textureName, 1 )

		return returnInfo


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

	# Random Stage Select Screen pointer table lookup; correlates a pointer to a stage string struct
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
			if symbolString.startswith( 'SIS_'):
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
				char = globalData.SdCharacters_1.get( key, '?' )
				chars.append( char )
				position += 2
			else:
				position += 1
			
			byte = textStruct.data[position]

		return ''.join( chars )

	def setText( self, sisId, newText, description='', endBytes=b'\x00' ):

		textStruct = self.getTextStruct( sisId )

		# Convert the given stage menu text to bytes and add the ending bytes
		byteStrings = []
		for char in newText:
			sBytes = dictReverseLookup( globalData.DolCharacters, char )

			# Check special characters (defined in this file) if a normal one wasn't found (defined in the DOL)
			if not sBytes:
				sBytes = dictReverseLookup( globalData.SdCharacters_1, char, defaultValue='20eb' ) # Default to question mark
			
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
			description = 'Updated "{}" text at 0x{:X} (SIS ID 0x{:X})'.format( newText, stringFileOffset, sisId )
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

		# Get the first pointer in the SIS table
		#imageDataStart = self.getStruct( 0 ).getValues()[0]
		sisTable = self.initGenericStruct( 0, structDepth=(3, 0), asPointerTable=True )
		imageDataStart = sisTable.getValues()[0]
		imageDataStruct = self.getStruct( imageDataStart )
		#imageCount = imageDataStruct.length / 0x380
		imageDataEnd = imageDataStart + imageDataStruct.length

		for imageDataOffset in range( imageDataStart, imageDataEnd, 0x380 ):
			print hex(imageDataOffset+0x20)


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

				# if stageName and not inConvenienceFolder:
				# 	# Get the vanilla stage name as a base for the descriptive name
				# 	stageName = self.longName + ', ' + stageName
				if self._shortDescription:
					self._longDescription = self.longName + ', ' + self._shortDescription

			except Exception as err:
				print 'Unable to get Random Neutral stage name from CSS file;'
				print err
			
			return
		
		# Check if there's a file explicitly defined in the file descriptions config file
		#if not stageName:
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
		#if not stageName and self.filename[2] == 'T':
		elif self.filename[2] == 'T':
			characterName = globalData.charNameLookup.get( self.filename[3:5], '' )

			if characterName:
				if characterName.endswith( 's' ):
					stageName = characterName + "'"
				else:
					stageName = characterName + "'s"

				# If convenience folders aren't turned on this name should have more detail
				# if not inConvenienceFolder:
				# 	stageName += " Target Test stage"
				self._shortDescription = stageName
				self._longDescription = stageName + " Target Test stage"
		
		# if updateInternalRef:
		# 	self.description = stageName

		# return stageName

	def setDescription( self, description, gameId='' ):

		""" Sets a description for a file defined in the CSS file, or in the yaml config file, and saves it. 
			Returns these exit codes: 
				0: Success
				1: Unable to save to the description yaml file
				2: Unable to find the CSS file in the disc
				3: Unable to save to the CSS file """

		if self.isRandomNeutral() and self.disc:
			#self.description = description
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

		#imageDataOffsetsFound = set()
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
			print 'Encountered an error during texture identification:'
			print err
		
		# toc = time.clock()
		# print 'image identification time:', toc - tic

		return texturesInfo


class CharCostumeFile( DatFile ):

	""" Subclass of .dat and .usd files, specifically for character files. """

	# Character file abbreviations; the key comes from the root node of the character file
	charAbbrs = { 	'Boy': 'Bo', 'Crazyhand': 'Ch', 'Gkoopa': 'Gk', 'Girl': 'Gl', 'Masterhand': 'Mh', 'Sandbag': 'Sb',
					'KirbyDk': 'KbDk', 'KirbyFc': 'KbFc', 'KirbyGw': 'KbGw', 'KirbyMt': 'KbMt', 'KirbyPr': 'KbPr', 

					'Captain': 'Ca', 'Clink': 'Cl', 'Donkey': 'Dk', 'Drmario': 'Dr', 'Falco': 'Fc', 'Emblem': 'Fe', 
					'Fox': 'Fx', 'Ganon': 'Gn', 'Gamewatch': 'Gw', 'Kirby': 'Kb', 'Koopa': 'Kp', 'Luigi': 'Lg', 
					'Link': 'Lk', 'Mario': 'Mr', 'Mars': 'Ms', 'Mewtwo': 'Mt', 'Nana': 'Nn', 'Ness': 'Ns', 
					'Pichu': 'Pc', 'Peach': 'Pe', 'Pikachu': 'Pk', 'Popo': 'Pp', 'Purin': 'Pr', 
					'Seak': 'Sk', 'Samus': 'Ss', 'Yoshi': 'Ys', 'Zelda': 'Zd' }

	# Character Abbreviation (key) to Internal Character ID (value)
	intCharIds = { 	'Mr': 0x00, 'Fx': 0x01, 'Ca': 0x02, 'Dk': 0x03, 'Kb': 0x04, 'Kp': 0x05, 'Lk': 0x06,
					'Sk': 0x07, 'Ns': 0x08, 'Pe': 0x09, 'Pp': 0x0A, 'Nn': 0x0B, 'Pk': 0x0C, 'Ss': 0x0D,
					'Ys': 0x0E, 'Pr': 0x0F, 'Mt': 0x10, 'Lg': 0x11, 'Ms': 0x12, 'Zd': 0x13, 'Cl': 0x14,
					'Dr': 0x15, 'Fc': 0x16, 'Pc': 0x17, 'Gw': 0x18, 'Gn': 0x19, 'Fe': 0x1A, 'Mh': 0x1B,
					'Ch': 0x1C, 'Bo': 0x1D, 'Gl': 0x1E, 'Gk': 0x1F, 'Sb': 0x20 }

	# Character Abbreviation (key) to External Character ID (value)
	extCharIds = { 	'Ca': 0x00, 'Dk': 0x01, 'Fx': 0x02, 'Gw': 0x03, 'Kb': 0x04, 'Kp': 0x05, 'Lk': 0x06,
					'Lg': 0x07, 'Mr': 0x08, 'Ms': 0x09, 'Mt': 0x0A, 'Ns': 0x0B, 'Pe': 0x0C, 'Pk': 0x0D,
					'Pp': 0x0E, 'Pr': 0x0F, 'Ss': 0x10, 'Ys': 0x11, 'Zd': 0x12, 'Sk': 0x13, 'Fc': 0x14,
					'Cl': 0x15, 'Dr': 0x16, 'Fe': 0x17, 'Pc': 0x18, 'Gn': 0x19, 'Mh': 0x1A, 'Bo': 0x1B,
					'Gl': 0x1C, 'Gk': 0x1D, 'Ch': 0x1E, 'Sb': 0x1F, 'Nn': 0x0E } # Excluding 0x20 (Solo Popo)
	
	def __init__( self, *args, **kwargs ):
		DatFile.__init__( self, *args, **kwargs )

		self._intCharId = -2
		self._extCharId = -2
		self._charAbbr = ''
		self._colorAbbr = ''

	@property
	def intCharId( self ):
		if self._intCharId == -2:
			self._intCharId = self.intCharIds.get( self.charAbbr, -1 )
		return self._intCharId
	@property
	def extCharId( self ):
		if self._extCharId == -2:
			self._extCharId = self.extCharIds.get( self.charAbbr, -1 )
		return self._extCharId
		
	@property
	def charAbbr( self ):
		if not self._charAbbr:
			self._charAbbr = self.getCharAbbr()
		return self._charAbbr
	@property
	def colorAbbr( self ):
		if not self._colorAbbr:
			self._colorAbbr = self.getColorAbbr()
		return self._colorAbbr

	def validate( self ):

		""" Verifies whether this is actually a character costume file by checking the string table. """

		self.initialize()
		rootNodeName = self.rootNodes[0][1]

		if not rootNodeName.endswith( '_Share_joint' ):
			raise Exception( "Invalid character costume file; no '..._Share_joint' symbol node found." )

	def getCharAbbr( self ):

		""" Analyzes the file's root nodes / string table to determine the character, rather than trusting the file name. """

		# Ensure root nodes and the string table have been parsed
		self.initialize()
		
		rootNodeName = self.rootNodes[0][1]
		nameParts = rootNodeName.split( '5K' )

		if not rootNodeName.startswith( 'Ply' ):
			print 'Unrecognized root node name:', rootNodeName, 'from', self.filename
			return ''

		if len( nameParts ) == 1: # Must be a character like Master Hand or a Wireframe (no 5K string portion), or a Kirby copy costume
			charShorthand = rootNodeName.split( '_' )[0][3:]

			# If this is Kirby, strip off the color abbreviation
			if charShorthand.startswith( 'Kirby' ) and charShorthand[-2:] in ( 'Bu', 'Gr', 'Re', 'Wh', 'Ye' ):
				charShorthand = charShorthand[:-2]

		else:
			charShorthand = nameParts[0][3:] # Excludes beginning 'Ply'

		return self.charAbbrs.get( charShorthand, '' )

	def getColorAbbr( self ):

		""" Analyzes the file's root nodes / string table to determine the costume color, rather than trusting the file name. """

		# Ensure root nodes and the string table have been parsed
		self.initialize()
		
		rootNodeName = self.rootNodes[0][1]
		nameParts = rootNodeName.split( '5K' )

		if not rootNodeName.startswith( 'Ply' ):
			print 'Unrecognized root node name:', rootNodeName, 'from', self.filename
			return ''

		if len( nameParts ) == 1: # Must be a character like Master Hand or a Wireframe (no 5K string portion), or a Kirby copy costume
			charShorthand = rootNodeName.split( '_' )[0]

			if charShorthand.startswith( 'PlyKirby' ):
				colorAbbr = charShorthand[-2:] # Gets last two characters of this section
				if colorAbbr not in ( 'Bu', 'Gr', 'Re', 'Wh', 'Ye' ):
					colorAbbr = 'Nr'
			else:
				colorAbbr = 'Nr'
		else:
			colorAbbr = nameParts[1].split( '_' )[0]

			if not colorAbbr:
				colorAbbr = 'Nr'

		return colorAbbr

	def getDescription( self ):
		
		# Attempt to get the character name this file is for
		charName = globalData.charNameLookup.get( self.charAbbr, '' )
		if not charName:
			self._shortDescription = 'Unknown ({})'.format( self.charAbbr )
			self._longDescription = self._shortDescription
			return

		if charName.endswith( 's' ):
			self._longDescription = charName + "' "
		else:
			self._longDescription = charName + "'s "

		colorKey = self.colorAbbr
		color = globalData.charColorLookup.get( colorKey, '' )
		assert color, 'Unable to get a color look-up from ' + colorKey

		# if inConvenienceFolder: # No need to show the name, since it's already displayed
		# 	description = ''
		# elif charName.endswith('s'):
		# 	description = charName + "' "
		# else:
		# 	description = charName + "'s "

		#if color: # It's a character costume (model & textures) file
		self._shortDescription = color + ' costume'
		if self.ext == '.lat' or colorKey == 'Rl': self._shortDescription += " ('L' alt)" # For 20XX
		elif self.ext == '.rat' or colorKey == 'Rr': self._shortDescription += " ('R' alt)"
		# elif colorKey == '.d': description += 'NTSC data & shared textures' # e.g. "PlCa.dat"
		# elif colorKey == '.p': description += 'PAL data & shared textures'
		# elif colorKey == '.s': description += 'SDR data & shared textures'
		# elif colorKey == 'AJ': description += 'animation data'
		# elif colorKey == 'Cp': # Kirb's copy abilities
		# 	copyChar = globalData.charNameLookup.get( self.filename[6:8], '' )
		# 	if ']' in copyChar: copyChar = copyChar.split( ']' )[1]
		# 	description += "copy power textures (" + copyChar + ")"
		# elif colorKey == 'DV': description += 'idle animation data'

		self._longDescription += self._shortDescription

		# Ensure the first word is capitalized
		self._shortDescription = self._shortDescription[0].upper() + self._shortDescription[1:]

	def buildDiscFileName( self, defaultToUsd=True ):	# todo: depricate in favor of disc.constructCharFileName( self, charId, colorId, ext='dat', defaultToUsd=True )

		""" Determines the disc file name for this file, using the root nodes / string table. """

		char = self.charAbbr
		color = self.colorAbbr

		if len( char ) == 4: # Kirby copy power costumes
			filename = 'PlKb{}Cp{}.dat'.format( color, char[2:] )
		elif char == 'Ca' and color == 'Re': # Falcon's Red Costume
			if defaultToUsd or ( self.disc and self.disc.countryCode == 1 ):
				filename = 'PlCaRe.usd'
			else:
				filename = 'PlCaRe.dat'
		else:
			filename = 'Pl{}{}.dat'.format( char, color )

		return filename

	def getCostumeId( self ):

		""" Converts this file's costume color to an index or costume ID, 
			which the game uses to choose a costume file. This will default 
			to 0 (the neutral/Nr slot) if the character is not found, which 
			is fine for "extra" characters such as Master Hand or Wireframes. """

		char = self.charAbbr
		color = self.colorAbbr

		colorSlots = globalData.costumeSlots.get( char, ('Nr',) )
		return colorSlots.index( color )


class MusicFile( FileBase ):

	""" For HPS files. """
	
	def __init__( self, *args, **kwargs ):
		FileBase.__init__( self, *args, **kwargs )

		self.externalWavFile = ''
		self.sampleRate = -1
		self.channels = -1
		self.channelMetaData = [] 	# A list of metadata values for each channel
		self.duration = -1			# In milliseconds
		self.loopPoint = -1			# Point in the song (in ms) where the track should restart after reaching the end

		self.musicId = -1			# ID used by the game to reference this file
		self.isHexTrack = False		# Songs in 20XX such as '00.hps', '01.hps', etc.
		self.trackNumber = -1		# Number from the file name, if this is a 20XX hex track

		if self.disc and self.disc.is20XX:
			# If a file is being initialized as this MusicFile class, it can be assumed that the filename includes the .hps extension
			if len( self.filename ) == 6 and self.isoPath.split( '/' )[1] == 'audio': # Thus, the filename excluding extension is only 2 characters
				if self.filename[0] in hexdigits and self.filename[1] in hexdigits:
					self.isHexTrack = True
					self.trackNumber = int( self.filename[:2], 16 )
					assert self.trackNumber < 255, 'Invalid track number detected: ' + hex( self.trackNumber )

	@property
	def musicId( self ):

		""" Gets the music ID for this file, i.e. the ID the game would use to reference it. 
			Note that a hex track number does not correspond to a music ID for that file.
			All hex tracks may be referenced if a flag of 0x10000 is set in the ID, with the 
			rest of the value being the track number (with v1.1 of the 20XX Playlist Code). 
			Since some hex tracks are actually vanilla songs (up to and including 0x30), they 
			may be referenced with either the vanilla music ID or the hex track flag + number. 
			In those cases, the vanilla music ID is prioritized by this method. """

		if self._musicId == -1:
			# Prioritize vanilla music ID over hex track ID for those that may be referenced by either
			if self.isHexTrack and ( self.trackNumber == 0 or self.trackNumber > 0x30 ):
				self._musicId = 0x10000 | self.trackNumber
			elif self.disc:
				self._musicId = self.disc.dol.getMusicId( self.filename )
			else:
				print 'Unable to determine musicId without the host disc.'

		return self._musicId

	@musicId.setter
	def musicId( self, newValue ):
		self._musicId = newValue
	
	def readHeader( self ):

		""" Read the header for the magic word (first 8 bytes), sample rate (next 4 bytes), and number of channels (next 4 bytes). """

		# Header:
		#   0: Magic number
		# 0x8: Sample Rate
		# 0xC: Number of channels
		headerData = self.getData( 0, 0x10 )
		assert headerData[:8] == ' HALPST\x00', 'Invalid HPS magic word! This does not appear to be an HPS file.'
		self.sampleRate, self.channels = struct.unpack( '>II', headerData[8:] )
		if self.channels != 2: print 'Found an HPS file that does not have 2 tracks!', self.filename

		# Channel Info/Metadata Chunks; 0x38 bytes per channel. Starts at 0x10:
		#   0: Loop flag (seems unused by the game; always 1?)
		# 0x2: Format
		# 0x4: SA	(always 2?)
		# 0x8: EA
		# 0xC: CA	(always 2?)
		# 0x10: Decoder Coefficients (0x10 halfwords / 0x20 bytes)
		# 0x30: Gain
		# 0x32: Initial Predictor Scale
		# 0x34: Initial Sample History 1
		# 0x36: Initial Sample History 2
		for channel in range( self.channels ):
			offset = 0x10 + ( channel * 0x38 )
			values = list( struct.unpack('>HHIII', self.getData( offset, 0x10 )) )
			values.extend( struct.unpack('>HHHH', self.getData( offset+0x30, 0x8 )) )
			# print 'loop flag :', values[0]
			# print 'format    :', values[1]
			# print 'StartAddr :', values[2]
			# print 'EndAddr   :', hex(values[3])
			# print 'CurrentAdr:', values[4]
			# print 'gain      :', values[5]
			# print 'pScale    :', values[6]
			# print 'initSH1   :', values[7]
			# print 'initSH1   :', values[8]
			# print 'byteCount :', hex(( values[3] - values[4] ) / 2)
			# print 'loopStart :', values[2] - values[4], hex(values[2] - values[4])
			# print ''
			self.channelMetaData.append( values )

		# Compare like values (not needed; just looking for descrepencies)
		#valueNames = 
		# for likeValues in zip( *self.channelMetaData ):
		# 	if not allAreEqual( likeValues ):
		# 		print 'Found differing channel metadata!'
		# 		print likeValues

	def readBlocks( self ):

		# Make sure the file header has be read
		if self.channels == -1:
			self.readHeader()

		# Block Structure (header, followed by data):
		#	0		Block Length (excluding 0x20 byte block header)
		# 0x4		Data Length (excluding 0x20 byte block header; usually block length -1, except in last block)
		# 0x8		Next Block Offset (absolute file offset); -1 if last block and track doesn't loop. or offset of a previous block if it loops
		# 0xC		Left DSP decoder state
		#	0xC			initPS
		#	0xE			initsh1 (Hist 1)
		#	0x10		initsh2 (Hist 2)
		#	0x12		gain (scale? always 0)
		# 0x14		Right DSP decoder state
		#	0x14		initPS
		#	0x16		initsh1 (Hist 1)
		#	0x18		initsh2 (Hist 2)
		#	0x1A		gain (scale? always 0)
		# 0x1C		Padding (always null)
		# 0x20		Data/DSP frames start
		#			Each block is capped/ended with one or more bytes of null data/padding

		blockOffset = 0x10 + ( self.channels * 0x38 ) # Typically 0x80 in a 2-channel file

		excludedLoopBlocks = []
		blockOffsets = []
		blockLengths = []
		dataLengths = []
		loops = False

		while True:
			blockLen, dataLen, nextBlockOffset = struct.unpack( '>IIi', self.getData(blockOffset, 0xC) )
			blockOffsets.append( blockOffset )
			blockLengths.append( blockLen )
			dataLengths.append( dataLen )

			if nextBlockOffset == -1:
				#print 'found last block at:', hex(blockOffset)
				break
			elif nextBlockOffset < blockOffset:
				#print 'looping back'
				loops = True
				break
			elif nextBlockOffset + 0xC > self.size:
				print 'Invalid next block offset!:', hex(nextBlockOffset + 0xC)
				break
			else:
				#print 'next block offset:', hex(nextBlockOffset)
				blockOffset = nextBlockOffset

		#print '\n', len( blockOffsets ), 'total blocks'
		# print 'block offsets:', [ hex(o) for o in blockOffsets ]
		# print 'block lengths:', [ hex(o) for o in blockLengths ]
		# print 'data lengths:', [ hex(o) for o in dataLengths ]
		#print 'total block length:', sum( blockLengths )
		# print 'total data length :', sum( dataLengths )
		# print 'final block offset:', hex(blockOffsets[-1])

		totalDataBytes = sum( dataLengths ) / 2 # For one channel
		self.duration = math.ceil( totalDataBytes / float(self.sampleRate) * 1.75 * 1000 )
		#print 'duration by block l'

		if loops:
			# Determine how much data will be excluded by the loop
			excludedDataLen = 0
			for offset, dataLen in zip( blockOffsets, dataLengths ):
				if offset == nextBlockOffset: # Found the loop block
					break
				excludedDataLen += dataLen

			# Calculate the duration of the excluded data
			if excludedDataLen == 0: # Loops back to the first block
				self.loopPoint = 0
			else:
				self.loopPoint = math.ceil( excludedDataLen / 2 / float(self.sampleRate) * 1.75 * 1000 )
		else:
			self.loopPoint = -1

	# def isHexTrack( self ):

	# 	""" These are 20XX's added custom tracks, e.g. 01.hps, 02.hps, etc. """

	# 	if not self._isHexTrackDetermined:
	# 		if len( self.filename ) == 6 and self.isoPath.split( '/' )[1] == 'audio': # Filename includes ".hps"
	# 			if self.filename[0] in hexdigits and self.filename[1] in hexdigits:
	# 				self._isHexTrack = True
				
	# 		self._isHexTrackDetermined = True

	# 	return self._isHexTrack

	def getDescription( self ):

		description = ''

		# For 20XX's hex tracks, get the track name from the CSS file
		if self.isHexTrack:
			try:
				cssFile = self.disc.files[self.disc.gameId + '/MnSlChr.0sd']
				trackNumber = int( self.filename[:2], 16 )
				description = cssFile.get20XXHexTrackName( trackNumber )
			except: pass

		else: # Check if there's a file explicitly defined in the file descriptions yaml config file
			description = self.yamlDescriptions.get( self.filename, '' )

		# if description:
		# 	self.description = description
		self._shortDescription = description
		self._longDescription = description
		
		#return self.description

	def setDescription( self, description, gameId='' ):

		""" Sets a description for a file defined in the CSS file, or in the yaml config file, and saves it. 
			Returns these exit codes: 
				0: Success
				1: Unable to save to the description yaml file
				2: Unable to find the CSS file in the disc
				3: Unable to save to the CSS file """

		if self.isHexTrack and self.disc:
			#self.description = description
			self._shortDescription = description
			self._longDescription = description

			# Names for these are stored in the CSS file... store it there
			cssFile = self.disc.files.get( self.disc.gameId + '/MnSlChr.0sd' )
			if not cssFile:
				msg( 'Unable to find the CSS file (MnSlChr.0sd) in the disc!' )
				return 2

			try:
				assert self.trackNumber != -1, 'Unable to set file description; Hex track {} does not have its track number set.'.format( self.filename )
				cssFile.set20XXHexTrackName( self.trackNumber, description )
				returnCode = 0

			except Exception as err:
				# Remove any hex track name pointer that may have been added if the above failed
				cssFile.validateHexTrackNameTable()

				msg( 'Unable to update the CSS file (MnSlChr.0sd) with the new name: ' + str(err) )
				return 3
		else:
			returnCode = super( MusicFile, self ).setDescription( description, gameId )

		return returnCode

	def getAsWav( self ):

		""" Dumps this file to the temp folder as an HPS, uses MeleeMedia to convert it 
			to a WAV file, and then returns the filepath to the WAV. """

		#tic = time.clock()

		# Export this file in its current HPS form to the temp folder
		tempInputFilepath = os.path.join( globalData.paths['tempFolder'], self.filename )
		saveSuccessful = self.export( tempInputFilepath )
		if not saveSuccessful: return '' # Failsafe

		# Get the path to the converter executable and construct the output wav filepath
		meleeMediaExe = globalData.paths['meleeMedia']
		newFilename = self.filename.rsplit( '.', 1 )[0] + '.wav'
		outputPath = os.path.join( globalData.paths['tempFolder'], newFilename )
		
		# Convert the file
		returnCode, output = cmdChannel( [meleeMediaExe, tempInputFilepath, outputPath] )
		if returnCode != 0:
			print 'Unable to convert', self.filename, 'to wav format.'
			return ''

		# Delete the temporary HPS file
		os.remove( tempInputFilepath )

		# toc = time.clock()
		# print 'time to get as wav:', toc-tic

		self.externalWavFile = outputPath

		return outputPath