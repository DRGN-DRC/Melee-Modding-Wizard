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

# External Dependencies
import os
import sys
import math
import time
import copy
import struct
#import psutil
import tempfile
import subprocess
import tkMessageBox
import ConfigParser

from sys import argv as programArgs
from string import hexdigits 				# For checking that a string only consists of hexadecimal characters
from binascii import hexlify, unhexlify 	# Convert from bytearrays to strings (and vice verca via unhexlify)

# Internal Dependencies
import globalData

from dol import Dol
from stageManager import StageSwapTable
from codeMods import regionsOverlap, CodeLibraryParser
from hsdFiles import FileBase, fileFactory, MusicFile
from basicFunctions import roundTo32, uHex, toHex, toInt, toBytes, humansize, grammarfyList, createFolders, msg, printStatus, ListDict


defaultGameCubeMediaSize = 1459978240 # ~1.36 GB


def findBytes( bytesRange, target ): # Searches a bytearray for a given (target) set of bytes, and returns the location (index)
	targetLength = len( target )

	for index, _ in enumerate( bytesRange ):
		if bytesRange[index:index+targetLength] == target: return index
	else: return -1


def getInChunks( sourceFile, offset, totalFileSize, chunkSize=4194304 ):

	""" Generator to get a file (from a specific offset) piece by piece. Saves greatly on memory usage by
		preventing the whole file from needing to be loaded into memory at once. The default chunk size is 4 MB; 
		that's how much will be copied from file to file during the rebuild process. """

	sourceFile.seek( offset )
	bytesCopied = 0

	while True:
		if bytesCopied + chunkSize >= totalFileSize:
			remainingDataLength = totalFileSize - bytesCopied
			yield sourceFile.read( remainingDataLength )
			break # Ends this generator (conveys that it is exhausted).
		else:
			bytesCopied += chunkSize
			yield sourceFile.read( chunkSize ) # Come back to this function for the next chunk of data after this.


def getInterFilePaddingLength( totalFileSpace, totalNonSystemFiles ):

	""" Determines how much padding to add between files when building or rebuilding a disc image. First attempts
		to check user settings (may be 'auto' or an integer value); if that fails, the settings default is used. 
		Values for total system/non-system file space include 4 byte alignment adjustments. """

	paddingSetting = globalData.settings.get( 'General Settings', 'paddingBetweenFiles' ).lower()

	if paddingSetting == 'auto':
		# Determine the total amount of non-system file space that is available, and how much of it will be empty space
		totalInterFilePadding = defaultGameCubeMediaSize - totalFileSpace

		if totalInterFilePadding <= 0:
			interFilePaddingLength = 0
		else:
			interFilePaddingLength = totalInterFilePadding / ( totalNonSystemFiles + 1 ) # The +1 accounts for one more region of padding at the end of the disc.
		
		# Undercut (reduce) the padding length, if necessary, to guarantee it is aligned to 4 bytes
		#interFilePaddingLength -= interFilePaddingLength - int( 4 * math.floor(float(interFilePaddingLength) / 4) )
	else:
		try:
			if '0x' in paddingSetting: interFilePaddingLength = int( paddingSetting, 16 )
			else: interFilePaddingLength = int( paddingSetting )
		except Exception as err: # Use the program's default
			print 'Error interpreting paddingBetweenFiles setting:', paddingSetting
			print err
			interFilePaddingLength = int( globalData.defaultSettings['paddingBetweenFiles'], 16 )
			print 'Switching to default value of', hex( interFilePaddingLength )

		# Undercut (reduce) the padding length, if necessary, to guarantee it is aligned to 4 bytes
		# if not interFilePaddingLength % 4 == 0:
		# 	print 'Warning: inter-file padding length (paddingBetweenFiles) is not a multiple of 4. It will be adjusted to preserve file alignment.'
		# 	print 'Original inter-file padding length:', interFilePaddingLength
		# 	interFilePaddingLength -= interFilePaddingLength - int( 4 * math.floor(float(interFilePaddingLength) / 4) )
		# 	print 'New inter-file padding length:     ', interFilePaddingLength

	return interFilePaddingLength, paddingSetting


def isExtractedDirectory( folderPath, showError=True ): # Not part of the disc class so it can more easily be used in other scripts

	""" Checks a given file/folder path to see if it's a disc root directory (i.e. a folder of files needed to build a disc). 
		Should be able to detect the root structure used by Dolphin, DTW, or GCR (GameCube Rebuilder).
		The following are checked to meet that determination:
			- Given path must be a folder
			- Contains a subfolder called "sys", "System files", or "&&systemdata"
			- Within the above folder, contains the required system files (described below)

		If it's determined to be a root folder, this function returns a dictionary containing 
		the following keys, where the value is an absolute file path to the respective file:
			- 'apploader' 	(found from the file apploader.img or AppLoader.ldr)
			- 'boot' 		(from boot.bin or iso.hdr)
			- 'boot2' 		(from bi2.bin; only present if boot.bin was also found)
			- 'dol' 		(from main.dol or Start.dol)
		
		GCR extracts the following system files in a "&&systemdata" folder:
			AppLoader.ldr
			Game.toc
			ISO.hdr			(i.e. boot.bin + bi2.bin)
			Start.dol

		Dolphin (as of ~v5.0-12716) extracts the folllowing system files in a "sys" folder:
			apploader.img
			bi2.bin
			boot.bin
			fst.bin
			main.dol

		DTW extracts the following system files in a "System files" folder:
			AppLoader.ldr
			Bi2.bin
			Boot.bin
			Game.toc
			Start.dol
	"""

	if not os.path.isdir( folderPath ):
		if showError:
			# Check if it's an invalid path, or a valid path to a file
			if os.path.exists( folderPath ):
				msg( 'The given root directory path appears to be a file rather than a directory.' )
			else:
				msg( "The given root directory path doesn't appear to exist." )
		return {}

	# Confirm existance of the system files folder (and confirm its name)
	for sysFolder in ( 'sys', 'System files', '&&systemdata' ):
		if os.path.exists( folderPath + '/' + sysFolder ):
			systemFolder = os.path.join( folderPath, sysFolder )
			break
	else: # loop above didn't break; no system-files folder found!
		if showError:
			msg( 'No system files folder could be found!\n\nThe system files should be in a folder called "sys", "System files", or "&&systemdata".' )
		return {}

	systemFilePaths = {}
	missingSysFiles = []

	# Check for the apploader
	if os.path.exists( systemFolder + '/apploader.img' ):
		systemFilePaths['apploader'] = systemFolder + '/apploader.img'
	elif os.path.exists( systemFolder + '/AppLoader.ldr' ):
		systemFilePaths['apploader'] = systemFolder + '/AppLoader.ldr'
	else:
		missingSysFiles.append( 'Apploader (.img or .ldr)' )

	# Check for the disc header; either boot.bin + bi2.bin, or iso.hdr
	if os.path.exists( systemFolder + '/boot.bin' ):
		systemFilePaths['boot'] = systemFolder + '/boot.bin'

		if os.path.exists( systemFolder + '/bi2.bin' ):
			systemFilePaths['boot2'] = systemFolder + '/bi2.bin'
		else:
			missingSysFiles.append( 'bi2.bin' )
	elif os.path.exists( systemFolder + '/iso.hdr' ):
		systemFilePaths['boot'] = systemFolder + '/iso.hdr'
	else:
		missingSysFiles.append( 'ISO header (either "boot.bin" AND "bi2.bin", or "iso.hdr")' )

	# Check for the main executable/DOL file
	if os.path.exists( systemFolder + '/main.dol' ):
		systemFilePaths['dol'] = systemFolder + '/main.dol'
	elif os.path.exists( systemFolder + '/Start.dol' ):
		systemFilePaths['dol'] = systemFolder + '/Start.dol'
	else:
		missingSysFiles.append( 'DOL file ("main.dol" or "Start.dol")' )

	# Notify the user of any missing files and return
	if missingSysFiles:
		if showError:
			msg( 'The following system files could not be found, and are necessary for building the disc:\n\n' + '\n'.join(missingSysFiles) )
		return {}

	return systemFilePaths


class Disc( object ):

	systemFiles = ( 'Boot.bin', 'Bi2.bin', 'AppLoader.img', 'Start.dol', 'Game.toc' )

	def __init__( self, filePath ):

		#self.dol = None
		self.ext = os.path.splitext( filePath )[1]	# Includes '.'
		self.filePath = filePath
		self.files = ListDict([])		# System files will be first in this, while root files will be ordered by the FST, or the OS if opening a root
		self.gameId = ''
		self.is20XX = ''				# Will be an empty string, or if 20XX, a string like '3.02' or 'BETA 04' (see method for details)
		self.isMelee = ''				# Will be an empty string, or if Melee, a string of '02', '01', '00', or 'pal'
		self.imageName = ''				# A string; the contents of 0x20 to 0x400 of the disc.
		self.gameVersion = ''			# Byte 7 of the disc. Will be a string of something like '00', '01', '02', etc.
		self.countryCode = 1			# Determines the encoding used in the banner (BNR) file. 1 = 'latin_1', anything else = 'shift_jis'
		self.isRootFolder = False
		self.rebuildReason = ''
		#self.rebuildRequired = False
		self.fstRebuildRequired = False
		self.unsavedChanges = []		# Disc changes unrelated to a file, or regarding deleted files. Vestigial; remove?
		self.fstEntries = []			# A list of lists, each of the form [ folderFlag, stringOffset, entryOffset, entrySize, entryName, isoPath ]

	def load( self ):

		""" Determines whether the path to this entity is a disc file or root folder, and calls the respective loading method. """

		# Check if this is a root folder (folder of files rather than a disc), and get the system file paths
		systemFilePaths = isExtractedDirectory( self.filePath, showError=False )

		if systemFilePaths:
			self.loadRootFolder( systemFilePaths )
		
		# Not a directory; check that it's a valid file path
		elif not os.path.exists( self.filePath ):
			msg( "Unable to find the disc or root path. Check the path and make sure the file hasn't been moved or deleted." )

		elif self.ext.lower() in ( '.iso', '.gcm' ):
			self.loadGameCubeMediaFile()

		else:
			msg( 'Unable to load the given root folder or disc path. (Acceptable file extensions are .ISO and .GCM.)' )

	def loadRootFolder( self, systemFilePaths ):

		""" Instantiates an extracted root folder as a disc object. Collects information on this new "disc" and instantiates its files. """

		#self.rebuildRequired = True
		self.rebuildReason = 'to build from a root folder'
		self.isRootFolder = True
		self.fstRebuildRequired = True

		dolPath = systemFilePaths['dol']
		bootFilePath = systemFilePaths['boot']
		apploaderPath = systemFilePaths['apploader']

		# Open boot.bin or iso.hdr to get disc header data for game info
		with open( bootFilePath, 'rb' ) as bootBinary:
			bootFileData = bytearray( bootBinary.read() )

		# Get the Game ID and version
		self.gameId = bootFileData[:6].decode( 'utf-8' ) #todo: change to decoding with ascii?
		self.gameVersion = struct.unpack( 'B', bootFileData[7] )[0] # Reading just byte 7

		# Double check that this is a gamecube disc image
		if not bootFileData[0x1C:0x20] == b'\xC2\x33\x9F\x3D':
			msg( "The disc boot file doesn't appear to be for a GameCube disc!" )
			return

		self.imageName = bootFileData[0x20:0x410].split( '\x00' )[0].decode( 'ascii' ) # Splitting on the first stop byte. #todo: change to decoding with utf-8?

		# Get the DOL file data and check whether this is Melee
		with open( dolPath, 'rb' ) as dolBinary:
			dolData = bytearray( dolBinary.read() )
		self.checkMeleeVersion( dolData )

		# Instantiate the Boot.bin/Bi2.bin or ISO.hdr header files
		self.files = ListDict([])
		if bootFilePath.lower().endswith( 'boot.bin' ):
			FileBase( self, 0, 0x440, self.gameId + '/Boot.bin', 'Disc Header (.hdr), Part 1', bootFilePath, 'file' )
			FileBase( self, 0x440, 0x2000, self.gameId + '/Bi2.bin', 'Disc Header (.hdr), Part 2', systemFilePaths['boot2'], 'file' )

			# Get Bi2.bin's data to check the country code
			with open( systemFilePaths['boot2'], 'rb' ) as boot2Binary:
				boot2Binary.seek( 0x18 )
				self.countryCode = struct.unpack( '>I', boot2Binary.read(4) )[0]

		else: # ISO.hdr was loaded; need to split it up into Boot/Bi2
			boot1 = FileBase( self, 0, 0x440, self.gameId + '/Boot.bin', 'Disc Header (.hdr), Part 1', source='self' )
			boot1.data = bootFileData[:0x440] # First 0x440 bytes
			boot2 = FileBase( self, 0x440, 0x2000, self.gameId + '/Bi2.bin', 'Disc Header (.hdr), Part 2', source='self' )
			boot2.data = bootFileData[0x440:]
			self.countryCode = toInt( bootFileData[0x458:0x45C] ) # 0x18 bytes into Boot2 (0x440 + 0x18)

		# Instantiate the Apploader
		apploaderSize = os.path.getsize( apploaderPath )
		FileBase( self, 0x2440, apploaderSize, self.gameId + '/AppLoader.img', 'Executable bootloader', apploaderPath, 'file' )

		# Instantiate the DOL
		dolIsoPath = self.gameId + '/Start.dol'
		dolOffset = toInt( bootFileData[0x420:0x424] )
		dol = Dol( self, dolOffset, len(dolData), dolIsoPath, 'Main game executable', dolPath, 'file' )
		dol.data = dolData # Since we happen to have it atm
		dol.load()

		# Instantiate files from the main filesystem (look for a "files" folder, or just use files from the current root directory)
		if os.path.exists( self.filePath + '/files' ):
			rootFilesFolder = self.filePath + '/files'
		else:
			rootFilesFolder = self.filePath

		for item in os.listdir( rootFilesFolder ):
			if item in ( 'sys', 'System files', '&&systemdata' ): continue
			itemPath = os.path.join( rootFilesFolder, item )

			if os.path.isdir( itemPath ):
				self.loadRootSubFolder( itemPath, rootFilesFolder )
			else:
				self.loadRootFile( itemPath, rootFilesFolder )

		self.buildFstEntries()
		
		# If this is 20XX, check its version
		if self.isMelee:
			cssFile = self.files.get( self.gameId + '/MnSlChr.0sd' )
			if cssFile:
				self.is20XX = self.get20xxVersion( cssFile.getData() )

		# Now that we know the Game ID, we can look up disc file definitions
		FileBase.setupDescriptions( self.gameId )

	def loadRootSubFolder( self, folderPath, rootFilesFolder ):

		""" Helper method to instantiating folders and the files within them when loading an extracted root folder. """
		
		for item in os.listdir( folderPath ):
			itemPath = os.path.join( folderPath, item )

			if os.path.isdir( itemPath ):
				self.loadRootSubFolder( itemPath, rootFilesFolder )
			else:
				self.loadRootFile( itemPath, rootFilesFolder )

	def loadRootFile( self, filePath, rootFilesFolder ):

		""" Helper method to instantiate files when loading an extracted root folder. """

		# Get the relative difference between the root folder's "files" path and the current file path
		isoPath = self.gameId + filePath.replace( rootFilesFolder, '' ).replace( '\\', '/' )

		# Get the file's size
		fileSize = os.path.getsize( filePath )

		fileFactory( self, -1, fileSize, isoPath, extPath=filePath, source='file' )

	def loadGameCubeMediaFile( self ):

		""" Opens a ISO or GCM (GameCube Media) disc file, and builds a file list from it composed of its system files and FST files. """

		with open( self.filePath, 'rb' ) as isoBinary:
			# Get the Game ID and version, right at the start of the file
			self.gameId = isoBinary.read( 6 ).decode( 'utf-8' ) #todo: change to decoding with ascii?
			isoBinary.seek( 7 )
			self.gameVersion = struct.unpack( 'B', isoBinary.read(1) )[0] # Reading just byte 7

			# Check the disc's magic word to verify it's a GC disc
			isoBinary.seek( 0x1C )
			if isoBinary.read( 4 ) != b'\xC2\x33\x9F\x3D':
				msg( "This file doesn't appear to be a GameCube disc!" )
				return

			# Get the disc's image name
			isoBinary.seek( 0x20 )
			self.imageName = isoBinary.read( 0x3E0 ).split( '\x00' )[0].decode( 'ascii' ) # Splitting on the first stop byte. #todo: change to decoding with utf-8?

			# Get info on the DOL and FST
			isoBinary.seek( 0x420 )
			dolOffset, fstOffset, fstSize = struct.unpack( '>III', isoBinary.read(12) )
			dolSize = fstOffset - dolOffset

			# Check the disc's country code
			isoBinary.seek( 0x458 ) # 0x18 bytes into Boot2 (0x440 + 0x18)
			self.countryCode = struct.unpack( '>I', isoBinary.read(4) )[0]

			# Get the Apploader's size. The file starts in the disc at 0x2440; codeSize and trailerSize are at 0x14 and 0x18, respectively
			isoBinary.seek( 0x2454 )
			codeSize, trailerSize = struct.unpack( '>II', isoBinary.read(8) )
			apploaderSize = roundTo32( codeSize + trailerSize )

			# Get the DOL's data, and check whether or not this is SSBM
			isoBinary.seek( dolOffset )
			dolData = bytearray( isoBinary.read(dolSize) )
			self.checkMeleeVersion( dolData )

			# Get the FST's data and parse it (builds the fstEntries list)
			isoBinary.seek( fstOffset )
			fstData = bytearray( isoBinary.read(fstSize) )
			self.parseFST( fstData )
		
			# Instantiate the disc's header files
			self.files = ListDict([])
			FileBase( self, 0, 0x440, self.gameId + '/Boot.bin', 'Disc Header (.hdr), Part 1' )
			FileBase( self, 0x440, 0x2000, self.gameId + '/Bi2.bin', 'Disc Header (.hdr), Part 2' )
			FileBase( self, 0x2440, apploaderSize, self.gameId + '/AppLoader.img', 'Executable bootloader' )
			dol = Dol( self, dolOffset, dolSize, self.gameId + '/Start.dol', 'Main game executable' )
			fst = FileBase( self, fstOffset, fstSize, self.gameId + '/Game.toc', "The disc's file system table (FST)" )

			# If this is Melee, check if this is the 20XX HP (and get its version), by checking the CSS file
			cssData = None
			if self.isMelee:
				for _, _, entryOffset, entrySize, itemName, _ in self.fstEntries:
					if itemName.startswith( 'MnSlChr.' ): # Could be .usd or .0sd
						isoBinary.seek( entryOffset )
						cssData = bytearray( isoBinary.read(entrySize) )
						self.is20XX = self.get20xxVersion( cssData )
						break

			self.instantiateFilesystem()

			# Add the file's data to the file objects created above, since we have it (prevent having to open the disc again later)
			dol.data = dolData
			dol.load()
			fst.data = fstData
			if cssData: # Couldn't do this in the loop above because the file object hadn't been created yet
				cssFile = self.files.get( self.gameId + '/' + itemName )
				if cssFile:
					cssFile.data = cssData

		# Now that we know the Game ID, we can look up disc file definitions
		FileBase.setupDescriptions( self.gameId )

	@property
	def dol( self ):
		dol = self.files[self.gameId + '/Start.dol']
		# if not dol.sectionInfo:
		# 	print 'DOL HAS NOT BEEN LOADED!'
		#dol.load() # Ensure the file has always been loaded/parsed, so all of its methods are functional
		return dol

	# @property
	# def css( self ):
	# 	cssFile = self.files.get( self.gameId + '/MnSlChr.0sd' )
	# 	assert

	def parseFST( self, fstData ):

		""" Parses a GC disc's FST/TOC (File System Table/Table of Contents), and builds 
			a list of entries for files and folders. Each entry will be a list of 
			the form [ folderFlag, stringOffset, entryOffset, entrySize, entryName, isoPath ]. 
						  ^bool			^int		^int		^int		^string		^string	"""

		totalEntries = toInt( fstData[8:0xC] )
		entriesSectionLength = totalEntries * 0xC # Each entry consists of 12 bytes

		# Decode and separate the entry values and strings
		entryValues = struct.unpack( '>' + ('III' * totalEntries), fstData[:entriesSectionLength] )
		strings = ['root'] + fstData[entriesSectionLength:].decode( 'ascii' ).split( '\x00' )

		self.fstEntries = []
		stringsIndex = 0

		for folderFlagAndStringOffset, entryOffset, entrySize in zip( *[iter(entryValues)]*3 ):
			# Check whether this entry is a folder, and mask out the flag from the string offset value
			if 0xFF000000 & folderFlagAndStringOffset: # Checking top 8 bits
				isDir = True
				stringOffset = 0xFFFFFF & folderFlagAndStringOffset # Masks out top 8 bits
			else:
				isDir = False
				stringOffset = folderFlagAndStringOffset

			self.fstEntries.append( [isDir, stringOffset, entryOffset, entrySize, strings[stringsIndex], ''] )
			stringsIndex += 1
		
	def instantiateFilesystem( self ):

		""" Goes through the disc's FST entries, instantiates objects for each file, and builds their disc paths (isoPath). 
			In the cases of folders, the size value is actually the index of the first item not in the folder. """
		
		currentDirectoryPath = self.gameId
		dirEndIndexes = [ self.fstEntries[0][-3] ] # Initial value is the first (root) entry's size (end index)

		for i, ( isDir, _, offset, size, name, _ ) in enumerate( self.fstEntries[1:], start=1 ): # Skips the first (root) entry.
			
			# If the last directory has been exhausted, remove the last directory from the current path.
			while i == dirEndIndexes[-1]: # 'while' is used instead of 'if' in case multiple directories are ending (being backed out of) at once
				currentDirectoryPath = '/'.join( currentDirectoryPath.split('/')[:-1] )
				dirEndIndexes.pop()

			# Build this entry's isoPath
			isoPath = currentDirectoryPath + '/' + name
			self.fstEntries[i][-1] = isoPath
			
			if isDir: # Increase the folder depth in the directory path string, and track when this folder should be exited
				currentDirectoryPath += '/' + name
				dirEndIndexes.append( size ) # In the case of folders, length is the number of items in this folder
			else:
				# Instantiate a disc object for this file
				fileFactory( self, offset, size, isoPath )
	
	# def checkRegion( self ):

	# 	""" Uses the Game ID for the region code, to check whether the region is NTSC or PAL.
	# 		See here for a full list of region codes:
	# 			https://wiki.dolphin-emu.org/index.php?title=GameIDs#Region_Code """

	# 	if self.gameId[3] in ( 'A', 'E', 'J', 'K', 'R', 'W' ):
	# 		self.region = 'NTSC'
	# 	else:
	# 		self.region = 'PAL'
		
	def checkMeleeVersion( self, dolData ):

		""" Checks the loaded disc to see if it's "Super Smash Bros. Melee", by checking the DOL for that string. """
		
		ssbmStringBytes = bytearray()
		ssbmStringBytes.extend( "Super Smash Bros. Melee" )
		if dolData[0x3B78FB:0x3B7912] == ssbmStringBytes: self.isMelee = '02'   # i.e. version 1.02 (most common; so checking for it first)
		elif dolData[0x3B6C1B:0x3B6C32] == ssbmStringBytes: self.isMelee = '01' # i.e. version 1.01
		elif dolData[0x3B5A3B:0x3B5A52] == ssbmStringBytes: self.isMelee = '00' # i.e. version 1.00
		elif dolData[0x3B75E3:0x3B75FA] == ssbmStringBytes: self.isMelee = 'pal' # i.e. PAL

	# def check20xxVersion( self, cssData ):

	# 	""" Checks the loaded disc to see if it's the 20XX Training Hack Pack, and gets its version if it is. 
	# 		The returned value will be a string of the version number, or an empty string if it's not 20XX.
	# 		The version string went through many different variations over the years; return values may be:
				
	# 		3.02, 3.02.01, 3.03, BETA 01, BETA 02, BETA 03, BETA 04, 4.07+, 4.07++, or [majorVersion].[minorVersion] """

	# 	# Check the file length of MnSlChr (the CSS); if it's abnormally larger than vanilla, it's 20XX post-v3.02
	# 	fileSize = toInt( cssData[:4] )

	# 	if fileSize > 0x3a2849: # Comparing against the vanilla file size.
	# 		# Isolate a region in the file that may contain the version string.
	# 		versionStringRange = cssData[0x3a4cd0:0x3a4d00]

	# 		# Create a bytearray representing "VERSION " to search for in the region defined above
	# 		versionBytes = bytearray.fromhex( '56455253494f4e20' ) # the hex for "VERSION "
	# 		versionStringPosition = findBytes( versionStringRange, versionBytes )

	# 		if versionStringPosition != -1: # The string was found
	# 			versionValue = versionStringRange[versionStringPosition+8:].split(b'\x00')[0].decode( 'ascii' )

	# 			if versionValue == 'BETA': # Determine the specific beta version; 01, 02, or 03 (BETA 04 identified separately)
	# 				firstDifferentByte = cssData[0x3a47b5]

	# 				if firstDifferentByte == 249 and hexlify( cssData[0x3b905e:0x3b9062] ) == '434f4445': # Hex for the string "CODE"
	# 					versionValue += ' 01'
	# 				elif firstDifferentByte == 249: versionValue += ' 02'
	# 				elif firstDifferentByte == 250: versionValue += ' 03'
	# 				else: versionValue = ''

	# 			elif versionValue == 'BETA04': versionValue = 'BETA 04'
					
	# 			self.is20XX = versionValue

	# 		elif fileSize == 0x3a5301: self.is20XX = '3.03'
	# 		elif fileSize == 0x3a3bcd: self.is20XX = '3.02.01' # Source: https://smashboards.com/threads/the-20xx-melee-training-hack-pack-v4-05-update-3-17-16.351221/page-68#post-18090881
	# 		else: self.is20XX = ''

	# 	elif cssData[0x310f9] == 0x33: # In vanilla Melee, this value is '0x48'
	# 		self.is20XX = '3.02'

	# 	else:
	# 		self.is20XX = ''

	def get20xxVersion( self, cssData ):

		""" Checks the loaded disc to see if it's the 20XX Training Hack Pack, and gets its version if it is. 
			The returned value will be a string of the version number, or an empty string if it's not 20XX.
			The version string went through many different variations over the years; return values may be:
				
			3.02, 3.02.01, 3.03, BETA 01, BETA 02, BETA 03, BETA 04, 4.07+, 4.07++, or [majorVersion].[minorVersion] """

		is20XX = ''

		# Check the file length of MnSlChr (the CSS); if it's abnormally larger than vanilla, it's 20XX post-v3.02
		fileSize = toInt( cssData[:4] )

		if fileSize > 0x3a2849: # Comparing against the vanilla file size.
			# Isolate a region in the file that may contain the version string.
			versionStringRange = cssData[0x3a4cd0:0x3a4d00]

			# Create a bytearray representing "VERSION " to search for in the region defined above
			versionBytes = bytearray.fromhex( '56455253494f4e20' ) # the hex for "VERSION "
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

	def isoPathIsFolder( self, isoPath ):

		""" Will also return False if the isoPath does not exist in the disc. """

		for entry in self.fstEntries: # Entries are of the form [ folderFlag, stringOffset, entryOffset, entrySize, entryName, isoPath ]
			if entry[0] and entry[-1] == isoPath:
				return True
		else:
			return False

	# def getFolderContents( self, folderIsoPath, recursive=True ):

	# 	""" Returns all isoPaths for items in the given folder (also an isoPath). """

	# 	paths = []
	# 	endIndex = 0

	# 	for i, entry in enumerate( self.fstEntries ): # Entries are of the form [ folderFlag, stringOffset, entryOffset, entrySize, entryName, isoPath ]
	# 		if not endIndex:
	# 			# Skip files until we find the target folder
	# 			if entry[0] and entry[-1] == folderIsoPath:
	# 				endIndex = entry[3]

	# 		# If this is reached, we're in a folder. Check for a folder within this
	# 		elif recursive and entry[0]:
	# 			#paths.append( entry[-1] )
	# 			paths.extend( self.getFolderContents(entry[-1], True) )

	# 		# Folder is found; we're currently in it
	# 		elif i >= endIndex:
	# 			break
	# 		else:
	# 			paths.append( entry[-1] )

	# 	return paths

	def listInfo( self ):

		""" Returns a string describing disc information. """

		discSize = os.path.getsize( self.filePath )
		totalFiles = len( self.files )
		totalFilesSize = sum( [fileObj.size for fileObj in self.files.values()] )
		totalPadding = discSize - totalFilesSize

		string =  'Game ID:                ' + self.gameId
		string += '\nGame Version:           ' + str( self.gameVersion )
		string += '\nCountry Code:           ' + str( self.countryCode )
		string += '\nImage Name:             ' + self.imageName
		string += '\nDisc Size:              {} ({:,} bytes)'.format( humansize(discSize), discSize)
		string += '\nTotal Files:            {:,}'.format( totalFiles )
		string += '\nTotal Files Size:       {} ({:,} bytes)'.format( humansize(totalFilesSize), totalFilesSize )
		string += '\nTotal Padding:          {} ({:,} bytes)'.format( humansize(totalPadding), totalPadding )
		string += '\nAve. Padding per-File:  {:,} bytes'.format( totalPadding/(totalFiles-5) )

		return string

	def listFiles( self, includeHeader=True, includeSizes=True, useByteValues=False ):

		""" Returns a list of files from the disc's filesystem (with file sizes), including system files. """

		fileList = []
		totalFilesSize = 0

		# Get the max width of the first column
		maxIsoPathLen = max( [len(fileObj.isoPath) for fileObj in self.files.values()] )
		columnOneWidth = maxIsoPathLen + 5

		for isoPath, fileObj in self.files.iteritems():
			if includeSizes:
				if useByteValues:
					line = '{0:<{1}}{2:,}'.format( isoPath, columnOneWidth, fileObj.size ) # Left-aligning the text
				else:
					line = '{0:<{1}}{2}'.format( isoPath, columnOneWidth, humansize(fileObj.size) ) # Left-aligning the text
			else:
				line = isoPath
			fileList.append( line )
			totalFilesSize += fileObj.size

		if includeHeader:
			fileList.insert( 0, '' ) # Extra space, for readability
			fileList.insert( 0, '\tTotal Files Size:  {} ({:,} bytes)'.format( humansize(totalFilesSize), totalFilesSize ) ) # Extra space, for readability
			fileList.insert( 0, '\tTotal Files:       {:,}'.format(len(self.files)) )
			fileList.insert( 0, '' ) # Extra space, for readability
		
		return '\n'.join( fileList )

	def getSize( self ):

		""" Returns the expected size of the disc, taking into account disc changes if it needs to be rebuilt. """

		if not self.rebuildReason:
			# lastFile = next( reversed(self.files) )
			# return lastFile.offset + lastFile.size
			return os.path.getsize( self.filePath )

		else:
			return self.getDiscSizeCalculations()[0]

	def getDiscSizeCalculations( self ):
		# Make sure this is up to date
		self.buildFstEntries()
		
		# Calculate the FST file offset and size
		fstOffset = self.getFstOffset()
		fstStrings = [ entry[-2] for entry in self.fstEntries[1:] ] # Skips the root entry
		fstFileSize = len( self.fstEntries ) * 0xC + len( '.'.join(fstStrings) ) + 1 # Final +1 to account for last stop byte

		# Get space needed for all system files (ends at FST)
		totalSystemFileSpace = roundTo32( fstOffset + fstFileSize ) # roundTo will round up, to make sure subsequent files are aligned
		
		# Determine file space for non-system files
		totalNonSystemFiles = 0
		totalNonSystemFileSpace = 0
		for entry in self.fstEntries:
			if not entry[0] and entry[3] > 0: # Means it's a file, and bigger than 0 bytes
				totalNonSystemFiles += 1
				totalNonSystemFileSpace += roundTo32( entry[3], base=4 ) # Adding file size and post-file padding, rounding alignment up
		interFilePaddingLength, paddingSetting = getInterFilePaddingLength( totalSystemFileSpace+totalNonSystemFileSpace, totalNonSystemFiles )

		# Calculate the size of the disc
		if paddingSetting == 'auto':
			if interFilePaddingLength == 0: # Disc is greater than or equal to the max size
				projectedDiscSize = totalSystemFileSpace + totalNonSystemFileSpace
			else:
				projectedDiscSize = defaultGameCubeMediaSize
		else:
			projectedDiscSize = totalSystemFileSpace + totalNonSystemFileSpace + interFilePaddingLength * totalNonSystemFiles
		
		# print 'totalNonSystemFiles determined:', totalNonSystemFiles
		# print 'interFilePaddingLength:', hex(interFilePaddingLength)
		# print 'total system file space:', hex(totalSystemFileSpace)
		# print 'total non-system file space:', hex(totalNonSystemFileSpace)
		# print 'padding:', hex(interFilePaddingLength), 'paddingSetting:', paddingSetting
		# print 'projected disc size:', hex(projectedDiscSize), projectedDiscSize

		return projectedDiscSize, totalSystemFileSpace, fstOffset, interFilePaddingLength, paddingSetting

	def concatUnsavedChanges( self, unsavedFiles=None, basicSummary=True ):

		""" Concatenates changes throughout the disc into a string to be displayed to the user. """

		if unsavedFiles == None:
			# Build a list of files that have unsaved changes
			unsavedFiles = self.getUnsavedChangedFiles()

		lines = []

		if unsavedFiles:
			lines.append( 'Files to update: {}'.format(len( unsavedFiles )) )
		elif not basicSummary:
			lines.append( 'No file changes' )

		#if self.rebuildRequired:
		if self.rebuildReason:
			lines.append( 'Rebuild required ' + self.rebuildReason )
		elif not basicSummary:
			lines.append( 'Rebuild not required' )
		lines.append( '' )
		
		# Scan for code-related changes
		if globalData.gui and globalData.gui.codeManagerTab:
			modsToInstall = 0
			modsToUninstall = 0

			# Scan the library for mods to be installed or uninstalled
			for mod in globalData.codeMods:
				if mod.state == 'pendingEnable':
					modsToInstall += 1
				elif mod.state == 'pendingDisable':
					modsToUninstall += 1

			# Advanced Summary
			if not basicSummary and not modsToInstall and not modsToUninstall:
				lines.append( '0 code mods to install or uninstall\n' )
			elif not basicSummary:
				lines.append( '{} code mods to install'.format(modsToInstall) )
				lines.append( '{} code mods to uninstall\n'.format(modsToUninstall) )

			# Basic Summary
			elif modsToInstall:
				lines.append( '{} code mods to install'.format(modsToInstall) )
			elif modsToUninstall:
				lines.append( '{} code mods to uninstall\n'.format(modsToUninstall) )

		# for isoPath, (description, fileObj) in self.unsavedChanges.items():
		# 	if not fileObj or len( fileObj.unsavedChanges ) == 0:
		# 		lines.append( description )
		# 	elif len( fileObj.unsavedChanges ) == 1:
		# 		lines.append( description + '. ' + fileObj.unsavedChanges[0] )
		# 	else:
		# 		lines.append( description + ':' )
		# 		for fileChange in fileObj.unsavedChanges:
		# 			lines.append( '    ' + fileChange )
		# 		lines.append( '' )

		if self.unsavedChanges:
			for change in self.unsavedChanges:
				lines.append( change )
			lines.append( '' )

		for fileObj in unsavedFiles:
			# Get the file description or filename
			fileDesc = fileObj.description if fileObj.description else fileObj.filename

			if len( fileObj.unsavedChanges ) == 1:
				lines.append( '{}: {}'.format(fileDesc, fileObj.unsavedChanges[0]) )

			elif basicSummary:
				lines.append( '{} changes in {}'.format(len(fileObj.unsavedChanges), fileDesc) )

			else:
				lines.append( '{} changes in {}:'.format(len(fileObj.unsavedChanges), fileDesc) )
				for fileChange in fileObj.unsavedChanges:
					lines.append( '    ' + fileChange )
				lines.append( '' )

		return '\n'.join( lines )

	def getUnsavedChangedFiles( self ):

		""" Returns a list of file objects which have unsaved changes. """

		unsavedFiles = []

		for fileObj in self.files.itervalues():
			if fileObj.unsavedChanges:
				unsavedFiles.append( fileObj )

		return unsavedFiles

	def changesNeedSaving( self ):

		""" Asks the user if they would like to forget any unsaved disc changes. 
			Used in order to close the program or load a new file. Returns a 
			list of files that have unsaved changes. """

		# Build a list of files that have unsaved changes
		unsavedFiles = self.getUnsavedChangedFiles()
		if not unsavedFiles and not self.unsavedChanges and not self.rebuildReason:
			return []

		# Changes are recorded. Ask the user if they'd like to forget them
		if globalData.programEnding:
			warning = "The changes below haven't been saved to disc. Are you sure you \nwant to close?\n\n"
		else: warning = 'The changes below will be forgotten if you change or reload the disc before saving. Are you sure you want to do this?\n\n'
		warning += self.concatUnsavedChanges( unsavedFiles )
		forgetChanges = tkMessageBox.askyesno( 'Unsaved Changes', warning )

		if forgetChanges: # The disc should be reloaded (or program closed) if the user truly wishes to undo/discard changes
			# self.unsavedChanges = []
			# self.rebuildReason = ''
			#self.rebuildRequired = False
			return []

		#return ( not forgetChanges )
		return unsavedFiles

	def alphabetize( self ):

		""" Arranges the disc's files (except system files) in alphabetical order. """
	

	# def recordChange( self, description, fileObj=None ):

	# 	# if description not in self.unsavedChanges:
	# 	# 	self.unsavedChanges[description] = fileObj

	# 	if fileObj:
	# 		if fileObj.isoPath not in self.unsavedChanges:
	# 			self.unsavedChanges[fileObj.isoPath] = ( description, fileObj )

	# 	else: # General disc change
	# 		if not 'disc' in self.unsavedChanges:
	# 			self.unsavedChanges['disc'] = ( [], None )

	# 		self.unsavedChanges['disc'][0].append( description )

	# def makeChange( self, discFile, offset, newData, description='' ):

	# 	""" Updates new data in a disc's internal file, and records those changes for later,
	# 		either for saving purposes, or for undoing the change. """

	# 	# Get the original data, to store it, in case the user would like to undo this later
	# 	endOffset = offset + len( newData )
	# 	originalData = discFile.getData( offset, len(newData) )

	# 	assert offset < len( discFile.data ), 'Offset to makeChange is out of bounds: ' + uHex( offset )

	# 	# Swap in the new data
	# 	discFile.data[offset:endOffset] = newData

	# 	# Remember this change
	# 	if not description:
	# 		description = discFile.filename + ' updated at offset ' + uHex( offset )
	# 	self.unsavedChanges.append( UnsavedChange(discFile, offset, originalData, description ) )

	def getConveniencePath( self ): pass

	def exportFiles( self, fileList, outputDir ):

		""" Export file(s) by isoPath. Only opens the disc file once if multiple files are requested. 
			Returns True/False, on whether or not the operation was successful. """

		if len( fileList ) == 0:
			msg( 'No files given to export!' )
			return []
		
		elif len( fileList ) == 1:
			fileObj = self.files.get( fileList[0] )

			if not fileObj:
				msg( 'Unable to export; the file "{}" could not be found in the disc.'.format(fileList[0]) )
				return [ fileList[0] ]

			# Construct the output file path and export the file
			savePath = os.path.join( outputDir, '/'.join(fileList.split('/')[1:]) ) # Excludes the Game ID
			successful = fileObj.export( savePath )

			if successful: return []
			else: return [ fileList[0] ]
		
		else: # Multiple files to export
			#filesExported = 0
			failedExports = []

			# Open the disc and begin exporting files
			err = None
			with open( self.filePath, 'rb') as isoBinary:
				for isoPath in fileList:
					fileObj = self.files.get( isoPath )
					
					# Attempt to get the file data
					if not fileObj:
						failedExports.append( isoPath )
						continue
					elif fileObj.source == 'disc':
						assert fileObj.offset != -1, 'Invalid file offset for disc export: -1'
						isoBinary.seek( fileObj.offset )
						fileData = isoBinary.read( fileObj.size )
					else: # source == 'file' or 'self'
						fileData = fileObj.getData()

					# Attempt to export the data to file
					try:
						# Make sure the folders exist for the given output path
						savePath = os.path.join( outputDir, '/'.join(fileList.split('/')[1:]) ) # Excludes the Game ID
						createFolders( os.path.split(savePath)[0] )

						# Save the data to a new file
						with open( savePath, 'wb' ) as newFile:
							newFile.write( fileData )

					except Exception as err:
						failedExports.append( isoPath )

			if err:
				print 'Unable to export; ', err

			return failedExports

	def replaceFile( self, origFileObj, newFileObj ):

		""" An import operation. Replaces an existing file in the disc with a new external/standalone file. """

		# Ensure the file size values have been set and data retrieved
		if origFileObj.size == -1:
			origFileObj.size = origFileObj.origSize = len( origFileObj.getData() )
		if newFileObj.size == -1:
			newFileObj.size = newFileObj.origSize = len( newFileObj.getData() )

		# Replace the file
		self.files[origFileObj.isoPath] = newFileObj
		newFileObj.disc = self
		newFileObj.offset = origFileObj.offset
		newFileObj.isoPath = origFileObj.isoPath
		newFileObj.unsavedChanges.append( 'New file' )

		# If this is a MusicFile, copy over extra properties
		if newFileObj.__class__ == MusicFile:
			newFileObj.musicId = origFileObj.musicId
			newFileObj.isHexTrack = origFileObj.isHexTrack
			newFileObj.trackNumber = origFileObj.trackNumber

		# Refresh the description (may not have been retrievable during file initialization without a disc reference)
		newFileObj.getDescription()

		# Update this file's entry size if it's changed, and check if the disc will need to be rebuilt
		if newFileObj.size != origFileObj.size:
			
			if newFileObj.filename == 'Start.dol':
				newFileObj.load()
				self.rebuildReason = 'to import a larger DOL'

			elif newFileObj.filename in self.systemFiles:
				self.rebuildReason = 'to import system files larger than their original' # probably should make this illegal

			# Check if it's the last file, in which case size its doesn't matter (also, the following loop would encounter an error if that's the case)
			elif origFileObj.offset == self.fstEntries[-1][2]:
				self.fstEntries[-1][3] = newFileObj.size

			else: # Not the last file; check if the file following it needs to be moved
				for i, entry in enumerate( self.fstEntries ): # Entries are of the form [ folderFlag, stringOffset, entryOffset, entrySize, entryName, isoPath ]
					if entry[2] == origFileObj.offset:
						self.fstEntries[i][3] = newFileObj.size

						# Check if there is enough space for the new file
						nextFileOffset = self.fstEntries[i+1][2]
						if nextFileOffset < newFileObj.offset + newFileObj.size:
							self.rebuildReason = 'to import files larger than their original'
							#self.rebuildRequired = True
						break

			# Flag that the FST will need to be rebuilt upon saving
			self.fstRebuildRequired = True

		elif newFileObj.filename == 'Start.dol':
			newFileObj.load()

		# Update the DOL reference if this is a DOL file
		# if newFileObj.isoPath == self.gameId + '/Start.dol':
		# 	self.dol = newFileObj

	def determineInsertionKey( self, newIsoPath ):

		""" Looks for an iid/isoPath, i.e. .files() dictionary key, that should 
			alphanumerically follow the given isoPath. """

		newIsoPath = newIsoPath.lower()

		for fileObj in self.files.itervalues():
			if fileObj.filename in self.systemFiles: continue
			isoPath = fileObj.isoPath.lower()

			# Compare characters in this isoPath to the target path
			for newChar, char in zip( newIsoPath, isoPath ):
				if newChar == char: continue
				elif newChar < char: # Found the index
					return fileObj.isoPath
				else: break # Move on to the next isoPath
			else: # The loop above didn't break or return; the two paths are the same up until the last character of the shorter path
				if len( newIsoPath ) == len( isoPath ):
					raise Exception( 'New file isoPath shares an isoPath with an existing file: ' + isoPath )
				elif len( newIsoPath ) < len( isoPath ):
					return fileObj.isoPath
				else:
					return 'end'

	def addFiles( self, newFileObjects, insertAfter=False ):

		""" Adds one or more file objects to the disc's file system. The disc will need to be rebuilt after 
			this operation. A file's insertion key (may be an attribute of the given file) should be the 
			iid/isoPath of an existing file in the .files dict. Each file will be added before that iid. """

		for fileObj in newFileObjects:
			# Make sure this file has an isoPath
			if not fileObj.isoPath:
				fileObj.isoPath = self.gameId + '/' + fileObj.filename

			# Check for a property which may dictate where this file is placed relative to the rest
			insertionKey = getattr( fileObj, 'insertionKey', None )
			if not insertionKey:
				insertionKey = self.determineInsertionKey( fileObj.isoPath )

			# Failsafe
			if insertionKey not in self.files:
				msg( 'Unable to add {} to the intended location in the disc filesystem; invalid insertion key: {}'.format(fileObj.filename, insertionKey), warning=True )
				insertionKey = 'end'

			if insertionKey == 'end': # Just add the file normally; it will be at the end of the toc and disc
				self.files[fileObj.isoPath] = fileObj
			# elif insertionKey == 'start': #todo (if needed?)
			# 	self.files.insert_after( )
			elif insertAfter:
				self.files.insert_after( insertionKey, (fileObj.isoPath, fileObj) )
			else:
				print 'inserting file just before', insertionKey
				self.files.insert_before( insertionKey, (fileObj.isoPath, fileObj) )
			
			fileObj.disc = self
			fileObj.unsavedChanges.append( 'Newly added to disc' )

			# Ensure the file size values have been set and data retrieved
			if fileObj.size == -1:
				fileObj.size = fileObj.origSize = len( fileObj.getData() )

		# Rebuild the FST Entries list, and mark that the disc needs to be rebuilt
		self.buildFstEntries()
		self.rebuildReason = 'to add new files to the disc'

	def removeFiles( self, fileObjects ):

		""" Removes one or more file objects from the disc's file system. The disc will need to be rebuilt 
			after this operation. New FST Entries will be created when the disc is rebuilt. """

		hexTracksRemoved = False # For 20XX

		for fileObj in fileObjects:
			if self.is20XX and fileObj.filename.endswith( '.hps' ) and fileObj.isHexTrack:
				hexTracksRemoved = True
			del self.files[fileObj.isoPath]

		# Make sure the Music Name Pointer Table in 20XX is updated
		if hexTracksRemoved:
			cssFile = self.disc.files.get( self.disc.gameId + '/MnSlChr.0sd' )
			cssFile.validateHexTrackNameTable()
		
		# Rebuild the FST Entries list, and mark that the disc needs to be rebuilt
		self.buildFstEntries()
		self.rebuildReason = 'to remove files from the disc'

	def getFstOffset( self ):
		dol = self.dol
		return roundTo32( dol.offset + dol.size )

	def updateFstEntry( self, discOffset, newFileSize, isoPath='' ):

		""" Updates the file size/length value of an FST entry. Uses the file's disc offset 
			to locate the target entry, except in cases where an isoPath is provided (in cases 
			where the disc offset may be unknown or inaccurate). """

		for entry in self.fstEntries: # Each entry is of the form [ folderFlag, stringOffset, entryOffset, entrySize, entryName, isoPath ]
			if entry[0]: continue # Checking the directory flag to skip folders

			# If isoPath is provided, use that instead to determine a file match
			elif isoPath and entry[-1] == isoPath:
				entry[2] = discOffset
				entry[3] = newFileSize
				break

			# Check if this is the target entry by the offset value
			elif entry[2] == discOffset:
				entry[3] = newFileSize # i.e. Entry length
				break

		else: # The above loop didn't break; no matching entry found!
			if isoPath:
				raise Exception( 'No FST entry found for "{}"!'.format(isoPath) )
			else:
				raise Exception( 'No FST entry found for offset 0x{:X}!'.format(discOffset) )

		# Flag that the FST will need to be rebuilt upon saving
		self.fstRebuildRequired = True

	def buildFstEntries( self ):

		""" Creates data for a new FST/TOC (File System Table/Table of Contents), by analyzing the 
			self.files dict and building a list of entries for files and folders. Each entry will be a 
			list of the form [ folderFlag, stringOffset, entryOffset, entrySize, entryName, isoPath ]. 
								  ^bool			^int		^int		^int		^string		^string	
			The entries will not have a proper entryOffset yet; that is TBD upon building the disc. """
		
		entryIndex = 1
		dirEndIndexes = {}
		lastFileDepth = 0 # At root
		lastFolderPathParts = []
		
		# Pass 1: Collect information on folders; watch for directory changes to determine folder entry size values (entryEndIndexes)
		for fileObj in self.files.itervalues():
			# Ignore system files
			isoPathParts = fileObj.isoPath.split( '/' )
			if isoPathParts[-1] in self.systemFiles: continue

			# Check if the folder depth has changed since the last file
			thisFileDepth = len( isoPathParts ) - 2 # -2 to ignore game ID and file name
			depthDifference = thisFileDepth - lastFileDepth # If this >= 1, then we're backing out of a folder

			# Increase entryIndex if a folder has been encountered
			if depthDifference > 0:
				entryIndex += depthDifference # Adding the whole difference (not just +1) in case multiple folders are entered at once

			# Set directory end indexes upon backing out of a folder (i.e. this file is not in the last folder we were in)
			while depthDifference < 0: # Need a while loop since there might be multiple folder exits at once
				dirEndIndexes['/'.join(lastFolderPathParts)] = entryIndex
				lastFolderPathParts = lastFolderPathParts[:-1] # Removes the last directory, if there is one
				depthDifference += 1

			# Finished analyzing this path; add one to the entry index to count this file
			entryIndex += 1
			lastFileDepth = thisFileDepth
			lastFolderPathParts = isoPathParts[:-1] # Slicing won't raise an error if there are no elements to choose from

		stringTableOffset = 0
		folderEntriesCreated = set()
		
		# Start off the entries with the root entry
		self.fstEntries = [ [True, 0, 0, entryIndex, 'root', ''] ]

		# Pass 2: Create the entries
		for fileObj in self.files.itervalues():
			# Ignore system files
			isoPathParts = fileObj.isoPath.split( '/' )
			fileName = isoPathParts.pop() # Also removes the file name from the list
			if fileName in self.systemFiles: continue

			folderToAddIndex = 1

			# Loop over all of the folders in this path, starting with the highest level
			while folderToAddIndex < len( isoPathParts ):
				folderPath = '/'.join( isoPathParts[:folderToAddIndex+1] )

				if folderPath not in folderEntriesCreated:
					# New folder encountered; create an entry for it
					folderName = isoPathParts[folderToAddIndex]
					self.fstEntries.append( [True, stringTableOffset, 0, dirEndIndexes[folderPath], folderName, folderPath] )
					#print 'adding fst folder entry; name:', folderName, '  path:', folderPath
					stringTableOffset += len( folderName ) + 1 # +1 to account for end byte
					folderEntriesCreated.add( folderPath )

				folderToAddIndex += 1

			# Add an entry for the file (don't have location for these yet, so just set that to 0)
			self.fstEntries.append( [False, stringTableOffset, 0, fileObj.size, fileName, fileObj.isoPath] )
			stringTableOffset += len( fileName ) + 1 # +1 to account for end byte

	def buildFst( self ):

		""" Builds a new FST (File System Table) from an established list of FST entries. 
			This creates a new file and adds it to the self.files dictionary. """

		entriesData = bytearray()
		stringsTable = bytearray()

		# Create the first entry (root) manually, since it is slightly different (no associated string)
		# Excluding this from the loop prevents having to add extra logic to it for each iteration
		rootLength = self.fstEntries[0][3]
		entriesData.extend( struct.pack('>III', 0x1000000, 0, rootLength) )

		# Build the FST and string table data
		for folderFlag, stringOffset, entryOffset, entrySize, entryName, _ in self.fstEntries[1:]: # Skip root entry
			if folderFlag:
				folderFlagAndStringOffset = 0x1000000 | stringOffset
				entriesData.extend( struct.pack('>III', folderFlagAndStringOffset, 0, entrySize) )
			else:
				entriesData.extend( struct.pack('>III', stringOffset, entryOffset, entrySize) )
			stringsTable.extend( entryName.encode('latin_1') + '\x00' )
		
		# Check if the FST is in among the game's files (might not be if this is a root folder)
		fstSize = len(entriesData) + len(stringsTable)
		toc = self.files.get( self.gameId + '/Game.toc' )
		if not toc:
			# Calculate the FST file offset
			#dol = self.files[ self.gameId + '/Start.dol' ]

			# Create a new toc file (and add it to the disc)
			toc = FileBase( self, self.getFstOffset(), fstSize, self.gameId + '/Game.toc', "The disc's file system table (FST)", source='self' )

		# Add the file data created above to the file object
		toc.data = entriesData + stringsTable
		toc.source = 'self' # Still need to set this in case the file already existed
		toc.size = fstSize

	def updateProgressDisplay( self, operation, dataCopiedSinceLastUpdate, progressAmount, finalAmount ):

		""" Displays/updates progress of an operation in the program's status bar, 
			or in the console if the GUI is not being used. """
		
		guiUpdateInterval = 8388608 # 8 MB. Once this many bytes or more have been copied to the new disc, the gui should update the progress display
		percentDone = ( float(progressAmount) / finalAmount ) * 100

		# Output to the GUI or command line
		if globalData.gui:
			# Create a simple percentage display message like 'Rebuilding (42%)'
			message = '{} ({}%)'.format( operation, round(percentDone, 1) )

			globalData.gui.updateProgramStatus( message )
			globalData.gui.statusLabel.update() # Force the GUI to update

		else:
			# Display a progress bar 50 characters long (not counting end caps)
			barLength = int( percentDone / 2 )
			bar = '[' + '=' * barLength + ' ' * (50-barLength) + ']'
			line = '{}    {}    {}    '.format( operation, bar, round(percentDone, 1) )

			# Output to the command line, but not on a new line (overwrite the last one)
			sys.stdout.write( '\r' + line ) # Write directly to the output buffer
			sys.stdout.flush() # Write the output buffer to console to see the change

		# Reset how much data has been written if exceeding the update interval
		if dataCopiedSinceLastUpdate >= guiUpdateInterval:
			return 0
		else:
			return dataCopiedSinceLastUpdate

	def saveFilesToDisc( self, filesToSave ):

		""" Saves all changed/replaced files to disc in-place, i.e. without rebuilding the disc. 
			Return codes may be:
				0: Success; no problems detected
				4: Unable to open the original disc
				5: Unrecognized error during file writing """

		totalUnsavedChanges = len( filesToSave )
		fstOffset = self.getFstOffset()
		filesUpdated = set()

		# Save each file to the ISO directly, modifying the FST if required. Only FST file lengths may need to be updated.
		try:
			isoBinary = open( self.filePath, 'r+b' )
		except Exception as err:
			if os.path.exists( self.filePath ):
				msg( 'Unable to open the original disc binary. Be sure that it has not been moved or deleted.', 'Unable to Save', warning=True )
			else:
				msg( 'Unable to open the original disc binary. Be sure that the file is not being used by another program (like Dolphin :P).', 'Unable to Save', warning=True )
			return 4, []

		try:
			for updateIndex, fileObj in enumerate( filesToSave, start=1 ):
				if not fileObj.data:
					print 'Unable to update', fileObj.isoPath + '; no file data found'
					continue

				# Navigate to the location of the file in the disc and write the new data
				isoBinary.seek( fileObj.offset )
				isoBinary.write( fileObj.getData() )

				# Check if padding should be added after the file (i.e. the new file is smaller, and it's not the DOL
				# If it's the DOL, the FST should be moved/placed right after it, without padding.)
				if fileObj.size < fileObj.origSize and fileObj.filename != 'Start.dol':
					paddingLength = fileObj.origSize - fileObj.size
					isoBinary.write( bytearray(paddingLength) )

				# Update this file entry's size value in the FST if it's different
				if fileObj.size != fileObj.origSize:
					
					if fileObj.filename == 'Start.dol': # This file isn't in the FST. Need to adjust the FST's offset in the disc's header
						# Move the FST. It must directly follow the DOL as the FST's offset is the only indicator of the DOL file's size
						isoBinary.seek( 0x424 )
						isoBinary.write( toBytes( fstOffset ) )
					
					else: # The file is expected to be in the FST (other system file size changes aren't supported)
						self.updateFstEntry( fileObj.offset, fileObj.size )

					self.updateProgressDisplay( 'Updating disc files:', 0, updateIndex, totalUnsavedChanges )

					# Flag for the FST to be rebuilt. Must be done in the case of the DOL as well; but just to move it in that case
					self.fstRebuildRequired = True

				filesUpdated.add( fileObj.isoPath )

			if self.fstRebuildRequired:
				# Reassemble the FST and write it back into the game
				self.buildFst()
				fst = self.files[self.gameId + '/Game.toc']
				isoBinary.seek( fstOffset )
				isoBinary.write( fst.data )
				filesUpdated.add( fst.isoPath )

		except Exception as err:
			msg( 'Unrecognized error while writing the new disc files (rebuild required = False); ' + str(err) )
			print err
			return 5, []

		isoBinary.close()

		return 0, filesUpdated

	def buildNewDisc( self, newFilePath='', buildMsg='Building ISO:' ):

		""" Creates a new disc file, and saves all loaded files from this object to it, according to 
			the information in the FST entries list. If newFilePath is set, the new disc will be saved 
			to that location, overwriting any existing file.

			Returns two values; a return code, and a list of isoPaths for files in the disc that were updated. 
			Return codes may be:
				0: Success; no problems detected
				3: Unable to create a new (initial/empty) disc file
				4: Unable to open the original disc
				5: Unrecognized error during file writing
				6: Unable to overwrite existing file 
				7: Could not rename discs or remove original """
		
		self.updateProgressDisplay( buildMsg, 0, 0, 100 ) # Display the bar and percentage as starting (0%)

		#tic = time.clock() # for performance testing

		# Make sure this is up to date
		# self.buildFstEntries()
		
		# # Calculate the FST file offset and size
		# #dol = self.files[ self.gameId + '/Start.dol' ]
		# fstOffset = self.getFstOffset()
		# fstStrings = [ entry[-2] for entry in self.fstEntries[1:] ] # Skips the root entry
		# fstFileSize = len( self.fstEntries ) * 0xC + len( '.'.join(fstStrings) ) + 1 # Final +1 to account for last stop byte

		# # Determine how much padding to add between files
		# totalSystemFileSpace = roundTo32( fstOffset + fstFileSize ) # roundTo will round up, to make sure subsequent files are aligned
		# totalNonSystemFiles = 0
		# totalNonSystemFileSpace = 0
		# for entry in self.fstEntries:
		# 	if not entry[0] and entry[3] > 0: # Means it's a file, and bigger than 0 bytes
		# 		totalNonSystemFiles += 1
		# 		totalNonSystemFileSpace += roundTo32( entry[3], base=4 ) # Adding file size and post-file padding, rounding alignment up
		# interFilePaddingLength, paddingSetting = getInterFilePaddingLength( totalSystemFileSpace+totalNonSystemFileSpace, totalNonSystemFiles )

		# # Calculate the size of the disc
		# if paddingSetting == 'auto': projectedDiscSize = defaultGameCubeMediaSize
		# else: projectedDiscSize = totalSystemFileSpace + totalNonSystemFileSpace + interFilePaddingLength * totalNonSystemFiles

		projectedDiscSize, totalSystemFileSpace, fstOffset, interFilePaddingLength, paddingSetting = self.getDiscSizeCalculations()

		#projectedDiscSize, interFilePaddingLength, paddingSetting = self.calculateDiscSize(  )

		# print 'totalNonSystemFiles determined:', totalNonSystemFiles
		# print 'interFilePaddingLength:', hex(interFilePaddingLength)
		# print 'total system file space:', hex(totalSystemFileSpace)
		# print 'total non-system file space:', hex(totalNonSystemFileSpace)
		# print 'padding:', hex(interFilePaddingLength), 'paddingSetting:', paddingSetting
		print 'projected disc size:', hex(projectedDiscSize), projectedDiscSize

		dataCopiedSinceLastUpdate = 0
		fileWriteSuccessful = False
		filesUpdated = set()
		newIsoBinary = None

		# Create a new file to begin writing the new disc to
		try:
			newIsoBinary = tempfile.NamedTemporaryFile( mode='r+b', dir=os.path.dirname(self.filePath), suffix='.tmp', delete=False )
		except Exception as err:
			msg( "Unable to create a new copy of the disc. Be sure there is write access to the destination." )
			print err
			return 3, []

		# Open the original disc file for reading if this isn't a root folder, to get its files
		if self.isRootFolder:
			originalIsoBinary = None
		else:
			try:
				originalIsoBinary = open( self.filePath, 'rb' ) # Will only be referenced below when rebuilding an existing disc image.
			except Exception as err:
				if os.path.exists( self.filePath ):
					msg( 'Unable to open the original disc binary. Be sure that it has not been moved or deleted.', 'Unable to Save', warning=True )
				else:
					msg( 'Unable to open the original disc binary. Be sure that the file is not being used by another program (like Dolphin :P).', 'Unable to Save', warning=True )
				print err
				if newIsoBinary:
					newIsoBinary.close()
					try: # Save not successful; delete the temp file if it's present
						os.remove( newIsoBinary.name )
					except: pass
				return 4, []

		#try:
		if 1:
			# Write the new ISO's system files
			for systemFileName in ( '/Boot.bin', '/Bi2.bin', '/AppLoader.img', '/Start.dol' ):
				systemFile = self.files.get( self.gameId + systemFileName )
				assert systemFile, 'Missing a header file! Unable to get ' + systemFileName[1:] # Failsafe; should have already been validated

				# Add padding prior to the file, if needed to respect offsets (should be aligned in most cases)
				currentFilePosition = newIsoBinary.tell()
				if currentFilePosition < systemFile.offset:
					newIsoBinary.write( bytearray(systemFile.offset - currentFilePosition) ) # The bytearray will be initialized with n bytes of null data

				# Get the file's binary and write it to the new disc
				if systemFile.source == 'disc' and not systemFile.unsavedChanges:
					# Get the file data from the original disc
					originalIsoBinary.seek( systemFile.offset )
					fileData = originalIsoBinary.read( systemFile.size )
				else: # The file is being imported (source = 'file'), or it only exists in memory (source = 'self')
					fileData = systemFile.getData()
					filesUpdated.add( systemFile.isoPath )
				newIsoBinary.write( fileData )

				# Update the GUI's progress display.
				dataCopiedSinceLastUpdate += systemFile.size
				dataCopiedSinceLastUpdate = self.updateProgressDisplay( buildMsg, dataCopiedSinceLastUpdate, currentFilePosition+systemFile.size, projectedDiscSize )

			# Prepare space for the FST. Add padding between it and the DOL (last file above) if needed, 
			# and create space where the full FST will later be placed, once the fst entries' edits are complete.
			currentFilePosition = newIsoBinary.tell()
			fstPlaceholderPadding = totalSystemFileSpace - currentFilePosition # FST is the last file in here. This includes padding alignment to 32 bytes
			newIsoBinary.write( bytearray(fstPlaceholderPadding) )
			
			# Update the GUI's progress display.
			dataCopiedSinceLastUpdate += fstPlaceholderPadding
			dataCopiedSinceLastUpdate = self.updateProgressDisplay( buildMsg, dataCopiedSinceLastUpdate, currentFilePosition+fstPlaceholderPadding, projectedDiscSize )
			
			# Write the new disc's main file structure
			for fileObj in self.files.itervalues():
				if fileObj.filename in self.systemFiles: continue

				# Add padding before this file, to ensure that the file will be aligned to 4 bytes.
				currentFilePosition = newIsoBinary.tell()
				paddingByteCount = roundTo32( currentFilePosition + interFilePaddingLength, base=4 ) - currentFilePosition
				newEntryOffset = currentFilePosition + paddingByteCount # i.e. the new file offset within the disc
				newIsoBinary.write( bytearray(paddingByteCount) )

				# Get the file's binary and write it to the new disc
				if fileObj.source == 'disc' and not fileObj.unsavedChanges:
					originalIsoBinary.seek( fileObj.offset )
					fileData = originalIsoBinary.read( fileObj.size )
				else:
					fileData = fileObj.getData()
					filesUpdated.add( fileObj.isoPath )
				newIsoBinary.write( fileData )

				# Update the file/entry disc offset and size
				fileObj.offset = newEntryOffset
				self.updateFstEntry( newEntryOffset, fileObj.size, fileObj.isoPath )
				
				# Update the GUI's progress display.
				dataCopiedSinceLastUpdate += fileObj.size
				dataCopiedSinceLastUpdate = self.updateProgressDisplay( buildMsg, dataCopiedSinceLastUpdate, newEntryOffset+fileObj.size, projectedDiscSize )

			# If auto padding was used, there should be a bit of padding left over to bring the file up to the standard GameCube disc size.
			if paddingSetting == 'auto':
				finalPaddingSize = defaultGameCubeMediaSize - int( newIsoBinary.tell() )
				if finalPaddingSize > 0:
					newIsoBinary.write( bytearray(finalPaddingSize) )

			# Ensure the final file has padding rounded up to nearest 0x20 bytes (the file cannot be loaded without this!)
			lastFilePadding = roundTo32( int(newIsoBinary.tell()) - newEntryOffset ) - fileObj.size
			if lastFilePadding > 0 and lastFilePadding < 0x20:
				newIsoBinary.write( bytearray(lastFilePadding) )

			# Now that all files have been written, and FST entries updated, the new FST is ready to be assembled and written into the disc
			self.buildFst()
			fst = self.files[self.gameId + '/Game.toc']
			newIsoBinary.seek( fstOffset )
			newIsoBinary.write( fst.data )
			filesUpdated.add( fst.isoPath )

			# Update the offset and size of the FST in boot.bin
			newIsoBinary.seek( 0x424 )
			newIsoBinary.write( toBytes( fstOffset ) )
			newFstSizeBytes = toBytes( fst.size )
			newIsoBinary.write( newFstSizeBytes ) # Writes the value for FST size
			newIsoBinary.write( newFstSizeBytes ) # Writes the value for max FST size (the Apploader will be displeased if this is less than FST size)

			# Remember that the disc header file was updated with the above values
			filesUpdated.add( self.gameId + '/Boot.bin' )
			fileWriteSuccessful = True

		# except Exception as err:
		# 	print 'Unrecognized error while writing the new disc files (rebuild required = True);', err
		
		# Close files
		if newIsoBinary:
			newIsoBinary.close()
		if originalIsoBinary:
			originalIsoBinary.close()
		
		# toc = time.clock()
		# print 'Time to rebuild disc:', toc-tic

		if not fileWriteSuccessful:
			try: # Save not successful; delete the temp file if it's present
				os.remove( newIsoBinary.name )
			except: pass

			return 5, []

		# Display the bar and percentage as complete (%100)
		self.updateProgressDisplay( buildMsg, 0, 100, 100 )
		if not globalData.gui: print '\n' # Add an extra line for spacing/readability in the command prompt output

		# Rename the new binary file to the target name (removing existing files if needed)
		if newFilePath or self.isRootFolder: # Provided via "Save Disc As..." or due to a new generated filename because backupOnRebuild is True
			if self.isRootFolder and not newFilePath:
				newFilePath = self.filePath
				
			# Remove any existing file, and rename the temporary file to the desired name
			try:
				if os.path.exists( newFilePath ):
					os.remove( newFilePath )
			except:
				msg( 'The file to replace could not be overwritten.\n\n'
					 "Be sure there is write access to the destination, and that the file isn't write-"
					 "locked (another program has it open, preventing it from being overwritten)." )
				return 6, []
			os.rename( newIsoBinary.name, newFilePath )
			self.filePath = newFilePath

		else: # No new file path (e.g. for a back-up file) requested; Use the original filename
			# Rename the original file, rename the back-up to the original file's name. Then, if successful, delete the original file.
			try:
				os.rename( self.filePath, self.filePath + '.bak' ) # Change the name of the original file so the new file can be named to it. Not deleted first in case the op below fails.
				os.rename( newIsoBinary.name, self.filePath ) # Rename the new 'back-up' file to the original file's name.

				os.remove( self.filePath + '.bak' ) # Delete the original file.
			except:
				msg( 'A back-up file was successfully created, however there was an error while attempting to rename the files and remove the original.\n\n'
					 "This can happen if the original file is locked for editing (for example, if it's open in another program).")
				return 7, []

		self.rebuildReason = ''
		#self.rebuildRequired = False
		
		# Warn the user if an ISO is too large for certain loaders
		if os.path.getsize( self.filePath ) > defaultGameCubeMediaSize: # This is the default/standard size for GameCube discs.
			msg( 'The disc is larger than the standard size for GameCube discs (which is ~1.36 GB, or 1,459,978,240 bytes). '
				 'This will be a problem for Nintendont, but discs up to 4 GB should still work fine for both Dolphin and DIOS MIOS. '
				 '(Dolphin may even play discs larger than 4 GB, but some features may not work.)', 'Standard Disc Size Exceeded' )

		return 0, filesUpdated
	
	def save( self, newDiscPath='' ):
		
		""" Saves all changed files in an ISO to disc; either by replacing each 
			file in-place (and updating the FST), or rebuilding the whole disc. 
			
			May return the following return codes:
				0: Success; no problems detected
				1: No changes to be saved
				2: Missing system files
				3: Unable to create a new disc file
				4: Unable to open the original disc
				5: Unrecognized error during file writing
				6: Unable to overwrite existing file
				7: Could not rename discs or remove original """

		# Perform some clean-up operations for 20XXHP features
		if self.is20XX:
			# Check for CSS file changes
			cssFile = self.files.get( self.gameId + '/MnSlChr.0sd' )
			if cssFile and cssFile.unsavedChanges:
				# Check that the hex tracks music name table is valid
				print 'other CSS files need updating'

		# Build a list of files that have unsaved changes, and make sure there are changes to be saved
		filesToSave = self.getUnsavedChangedFiles()
		if not filesToSave and not self.unsavedChanges and not self.rebuildReason:
			return 1, []

		# Make sure all system files are present (you never know....)
		missingSysFiles = []
		for systemFile in self.systemFiles:
			if not self.files.get( self.gameId + '/' + systemFile ):
				missingSysFiles.append( systemFile )
		if missingSysFiles:
			msg( 'Unable to save the disc; missing these system files: ' + ', '.join(missingSysFiles) )
			return 2, []

		# Write the file(s) to the ISO.
		if not self.rebuildReason:
			# Create a copy of the file and operate on that instead if using the 'Save Disc As' option
			if newDiscPath:
				try:
					# Ensure containing folders exist
					folderPath = os.path.dirname( newDiscPath )
					createFolders( folderPath )

					# Copy the disc
					origFileSize = int( os.path.getsize(self.filePath) )
					dataCopiedSinceLastUpdate = 0
					with open( newDiscPath, 'wb' ) as newFile:
						with open( self.filePath, 'rb' ) as originalFile:
							for dataChunk in getInChunks( originalFile, 0, origFileSize ):
								newFile.write( dataChunk )
								dataCopiedSinceLastUpdate += len( dataChunk )
								dataCopiedSinceLastUpdate = self.updateProgressDisplay( 'Copying ISO:', dataCopiedSinceLastUpdate, newFile.tell(), origFileSize )

					# Switch to using this new file instead (the original shouldn't have been modified)
					self.filePath = newDiscPath
				except:
					msg( "Unable to create a new copy of the disc. Be sure there is write access to the destination, and that if there is "
						 "a file being replaced, it's not write-locked (meaning another program has it open, preventing it from being overwritten)." )
					return 3, []

			# Save each file to the ISO directly, modifying the FST if required. Only FST file lengths may need to be updated.
			returnCode, updatedFiles = self.saveFilesToDisc( filesToSave )

		# Disc needs to be rebuilt, or built anew (for the first time from a root folder)
		else:
			# Create a new filename for the disc, and make sure it's unique
			if not newDiscPath and globalData.checkSetting( 'backupOnRebuild' ):
				discExtOriginal = os.path.splitext( self.filePath )[1] # Inlucdes dot ('.')

				# Create a new, unique file name for the backup, with a version number based on the source file. e.g. '[original filename] - Rebuilt, v1.iso'
				discFileName = os.path.basename( self.filePath )
				if 'Rebuilt, v' in discFileName:
					newIsoFilepath = self.filePath
				else:
					newIsoFilepath = self.filePath[:-4] + ' - Rebuilt, v1' + discExtOriginal

				# Make sure this is a unique (new) file path
				if os.path.exists( newIsoFilepath ):
					nameBase, _, version = newIsoFilepath[:-4].rpartition( 'v' ) # Splits on last instance of the delimiter (once)

					if '.' in version: # e.g. "1.3"
						# Get the most minor number in the version
						versionBase, _, _ = version.rpartition( '.' )
						newIsoFilepath = '{}v{}.1{}'.format( nameBase, versionBase, discExtOriginal )

						newMinorVersion = 2
						while os.path.exists( newIsoFilepath ):
							newIsoFilepath = '{}v{}.{}{}'.format( nameBase, versionBase, newMinorVersion, discExtOriginal )
							newMinorVersion += 1

					else: # Single number version
						newIsoFilepath = '{}v1{}'.format( nameBase, discExtOriginal )
						newMajorVersion = 2
						while os.path.exists( newIsoFilepath ):
							newIsoFilepath = '{}v{}{}'.format( nameBase, newMajorVersion, discExtOriginal )
							newMajorVersion += 1
				
				# Rename the backup file to the above name.
				newDiscPath = newIsoFilepath

			# Rebuild the disc
			returnCode, updatedFiles = self.buildNewDisc( newDiscPath )

		if returnCode == 0: # Save was successful
			# Clear unsaved-changes lists
			self.unsavedChanges = []
			for fileObj in filesToSave:
				fileObj.source = 'disc'
				fileObj.unsavedChanges = []

			print 'updated files:', updatedFiles

		return returnCode, updatedFiles

	def getMusicFile( self, musicId ):

		""" Uses the DOL to look up a file name from a music ID, and then get and 
			return the file object. Returns None if the file can't be found. 
			Note that some hex tracks are vanilla songs, however a music ID does 
			not correlate to the same number hps file. """

		if musicId < 0:
			print 'Invalid music ID given to disc.getMusicFile():', hex( musicId )
			return None

		isHexTrack = ( musicId & 0x10000 == 0x10000 )
		trackNumber = musicId & 0xFF

		# Check if this is a hex track music ID (signified by flag at 0x10000)
		if isHexTrack and trackNumber <= 0xFF:
			musicFilename = '{:02X}.hps'.format( trackNumber )

		# Check for a vanilla file name for this ID using a table in the DOL
		elif musicId < 0x63:
			#dol = self.files.get( self.gameId + '/Start.dol' )
			musicFilename = self.dol.getMusicFilename( musicId )
			if not musicFilename:
				return None

		else:
			print 'Invalid music ID given to disc.getMusicFile():', hex( musicId )
			return None

		musicFile = globalData.disc.files.get( self.gameId + '/audio/' + musicFilename ) # May also be None, if it can't find the file

		if musicFile:
			musicFile.musicId = musicId

		return musicFile

	def getGeckoData( self ):

		""" Checks the disc for Gecko codes (a file containing the codehandler and codelist). """

		geckoCodesFile = self.files.get( self.gameId + '/gecko.bin' )
		if not geckoCodesFile: return bytearray()

		return geckoCodesFile.getData()

	def getInjectionData( self ):

		""" Checks the disc for the injection codes payload. """

		injectionsCodeFile = self.files.get( self.gameId + '/codes.bin' )
		if not injectionsCodeFile: return bytearray()

		return injectionsCodeFile.getData()

	def checkReferencedStageFiles( self ):

		""" Checks for files referenced by the DOL (and 20XX Stage Swap Table if 
			it's 20XX) to determine what file names are referenced by the game. """
		
		referencedFiles = set()
		swapTable = StageSwapTable()

		# Check for stage file names referenced in the DOL and/or Stage Swap Table
		for stageId in range( 0x1, 0x47 ): # Iterating via Internal Stage ID
			# Ignore Akaneia and other unused stage slots
			if stageId in ( 0x17, 0x1A, 0x22, 0x23, 0x26 ):
				continue

			# Check if the Stage Swap Table defines this stage
			elif stageId in StageSwapTable.stageOffsets:
				for page in range( 1, 5 ):
					# Get stage swap information on this stage slot for this SSS
					newExtStageId, _, byteReplacePointer, byteReplacement, randomByteValues = swapTable.getEntryInfo( stageId, page )

					# Determine the NEW internal stage ID to switch to for this slot
					if newExtStageId == 0:
						newIntStageId = stageId
					else:
						newIntStageId = self.dol.getIntStageIdFromExt( newExtStageId )

					# Determine what files may be loaded from this stage slot from this SSS page
					filenames = swapTable.determineStageFiles( newIntStageId, page, byteReplacePointer, byteReplacement, randomByteValues )[1]
					referencedFiles.update( filenames )
			else:
				referencedFiles.add( self.dol.getStageFileName(stageId)[1] )

		return referencedFiles

	def uninstallCodeMods( self, codeMods ):

		""" Uninstalls static overwrites and injection mods in the game. Gecko codes are handled separately. """
		
		# See if we can get a reference to vanilla DOL code
		vanillaDiscPath = globalData.getVanillaDiscPath()
		if vanillaDiscPath:
			vanillaDisc = Disc( vanillaDiscPath )
			vanillaDisc.load()
		else: # User canceled path input
			#vanillaDisc = None
			globalData.gui.updateProgramStatus( 'Unable to validate mod uninstallation', warning=True )
			return codeMods

		problematicMods = []

		for mod in codeMods:
			# Process each code change tuple (each representing one change in the file) given for this mod for the current game version.
			#for changeType, customCodeLength, offsetString, originalCode, _, preProcessedCode, _ in mod.getCodeChanges():
			for codeChange in mod.getCodeChanges():
				if codeChange.type == 'static' or codeChange.type == 'injection':
					dolOffset = self.dol.normalizeDolOffset( codeChange.offset )[0]
					if dolOffset == -1:
						problematicMods.append( mod.name ) # Unable to uninstall this
						break

					# Get the original data to be put back in the game
					originalHex = ''.join( codeChange.origCode.split() ) # Removes all line breaks & spaces. (Comments should already be removed.)
					if originalHex:
						originalData = bytearray.fromhex( originalHex )
					elif codeChange.type == 'static': # Might not have original hex
						originalData = vanillaDisc.dol.getData( dolOffset, codeChange.getLength() )
					else: # Just need 4 bytes for injection site code
						originalData = vanillaDisc.dol.getData( dolOffset, 4 )

					
					if not originalData:
						problematicMods.append( mod.name ) # Unable to uninstall this
						break

					self.dol.setData( dolOffset, originalData )
					# if validHex( originalHex ): replaceHex( dolOffset, originalHex )
					# else:
					# 	vanillaCode = getVanillaHex( dolOffset, byteCount=customCodeLength )
					# 	if not vanillaCode:
					# 		msg( 'Warning! Invalid hex was found in the original code for "' + mod.name + '", and no vanilla DOL was found in the Original DOLs folder! ' 
					# 				'Unable to refer to original code, which means that this mod could not be properly uninstalled.' )
					# 	else:
					# 		replaceHex( dolOffset, vanillaCode )
					# 		msg( 'Warning! Invalid hex was found in the original code for "' + mod.name + '". The original code from a vanilla DOL was used instead.')
					
				# elif codeChange.type == 'gecko' and mod.state == 'pendingDisable': 
				# 	removingSomeGeckoCodes = True # This state means they were previously enabled, which also means gecko.environmentSupported = True

			# Make sure Gecko mod states are correct
			if mod.state == 'pendingDisable':
				# if mod.type == 'gecko' and not overwriteOptions[ 'EnableGeckoCodes' ].get(): 
				# 	mod.setState( 'unavailable' )
				#else:
				mod.setState( 'disabled' )

		if problematicMods:
			modsUninstalled = len( codeMods ) - problematicMods
			msg( '{} code mods uninstalled. However, these mods could not be uninstalled:\n\n{}'.format(modsUninstalled, '\n'.join(problematicMods)) )
		else:
			modsUninstalled = len( codeMods )

		# Update or add to the DOL's list of unsaved changes
		for i, change in enumerate( self.dol.unsavedChanges ):
			if change.endswith( 'code mod uninstalled' ) or change.endswith( 'code mods uninstalled' ):
				del self.dol.unsavedChanges[i]
				break
		if modsUninstalled == 1:
			self.dol.unsavedChanges.append( '1 code mod uninstalled' )
		else:
			self.dol.unsavedChanges.append( '{} code mods uninstalled'.format(modsUninstalled) )
		self.files[self.gameId + '/Start.dol'] = self.dol

		return problematicMods

	def storeCodeChange( self, address, code, modName='', requiredChange=False ):

		""" Saves custom code to the DOL and/or to the codes.bin file (used to store custom code). 
			Also detects conflicts between mods during the mod installation operation, and notifies the user of conflicts. 
			Free space regions for injection code are organized independently and not considered by this."""

		newCodeLength = len( code ) / 2 # in bytes
		newCodeEnd = address + newCodeLength
		conflictDetected = False

		for regionStart, codeLength, modPurpose in self.modifiedRegions:
			regionEnd = regionStart + codeLength

			if address < regionEnd and regionStart < newCodeEnd: # The regions overlap by some amount.
				conflictDetected = True
				break

		if conflictDetected:
			if modName: # Case to silently fail when uninstalling a mod previously detected to have a problem
				oldCodeStart = self.dol.offsetInDOL( regionStart )
				newCodeStart = self.dol.offsetInDOL( address )
				oldChangeRegion = 'Code Start: 0x{:X},  Code End: 0x{:X}'.format( oldCodeStart, oldCodeStart + codeLength )
				newChangeRegion = 'Code Start: 0x{:X},  Code End: 0x{:X}'.format( newCodeStart, newCodeStart + newCodeLength )

				if requiredChange:
					warningMsg = ( 'A conflict (writing overlap) was detected between the {} and a '
								   'code change for {}: {}'
								   '\n\nThe latter has been partially overwritten and will likely no longer function correctly. '
								   "It's recommended to be uninstalled.".format(modName, modPurpose, oldChangeRegion) )
				else:
					warningMsg = ( 'A conflict (writing overlap) was detected between these two changes:\n\n"' + \
									modPurpose + '"\n\t' + oldChangeRegion + '\n\n"' + \
									modName + '"\n\t' + newChangeRegion + \
									'\n\nThese cannot both be enabled. "' + modName + '" will not be enabled. "' + \
									modPurpose + '" may need to be reinstalled.' )
				msg( warningMsg, 'Conflicting Changes Detected' )
		
		else: # No problems; save the code change to the DOL and remember this change
			dolOffset = self.dol.offsetInDOL( address )

			if dolOffset == -1: # Not in the DOL. Belongs in the codes.bin file
				# Prepend the data to the beginning of codes.bin
				_, arenaEnd, arenaSpaceUsed = self.allocationMatrix[-1]
				fileStartAddress = arenaEnd - arenaSpaceUsed - newCodeLength
				if address != fileStartAddress:
					conflictDetected = True
				else:
					self.injectionsCodeFile.data = bytearray.fromhex(code) + self.injectionsCodeFile.data

				# fileLength = len( self.injectionsCodeFile.data )
				# fileStart = arenaEnd - fileLength
				# if address > fileStart: # Address is in the file
				# else:
			else:
				self.dol.setData( dolOffset, bytearray.fromhex(code) )
			
			self.modifiedRegions.append( (address, newCodeLength, modName) )
		
		return conflictDetected

	def allocateSpaceInRam( self, customCodeLength ):

		""" Determines a location in RAM to store custom code. First checks for unused space among the custom 
			code regions enabled for use. And then if no usable space is found there, allocates space in the Arena. 
			Returns a RAM address for where the code is determined to be placed. """

		customCodeOffset = -1

		# for i, ( areaStart, areaEnd ) in enumerate( allCodeRegions ):
		# 	spaceRemaining = areaEnd - areaStart - dolSpaceUsedDict['area' + str(i + 1) + 'used'] # value in bytes

		# 	if customCodeLength <= spaceRemaining:
		# 		customCodeOffset = areaStart + dolSpaceUsedDict['area' + str(i + 1) + 'used']
		# 		dolSpaceUsedDict['area' + str(i + 1) + 'used'] += customCodeLength # Updates the used area reference.
		# 		break

		for codeSpace in self.allocationMatrix[:-1]:
			areaStart, areaEnd, spaceUsed = codeSpace # Not expanded in the above line so we can modify the last entry
			spaceRemaining = areaEnd - areaStart - spaceUsed

			if customCodeLength <= spaceRemaining:
				customCodeOffset = areaStart + spaceUsed
				codeSpace[2] += customCodeLength
				break

		# If space was found in the DOL, convert the location to a RAM address and return it
		if customCodeOffset != -1:
			return self.dol.offsetInRAM( customCodeOffset )

		# This code will go in the codes.bin file, placed just above the TOC in RAM during runtime
		# Add the file to the disc if it isn't already present
		if not self.injectionsCodeFile:
			# File not yet added to the disc; add it now
			self.injectionsCodeFile = FileBase( self, -1, -1, self.gameId + '/codes.bin', '', source='self' )
			if self.gameId + '/1padv.ssm' in self.files:
				self.injectionsCodeFile.insertionKey = self.gameId + '/1padv.ssm' # File will be added just before this path/key
			else:
				self.injectionsCodeFile.insertionKey = 'end' # File will be added to the end of the ordered dict
			self.addFiles( [self.injectionsCodeFile] )
		
		# Reserve space for this code and return the RAM address
		self.allocationMatrix[-1][-1] += customCodeLength # Adding to spaceUsed
		_, arenaEnd, arenaSpaceUsed = self.allocationMatrix[-1]
		#startOfToc = 0x81800000 - tocSize - 0x1E
		return arenaEnd - arenaSpaceUsed

	# def buildAllocationMatrix( self ):

	def installCodeMods( self, codeMods ):

		""" Installs static overwrites and injection mods to the game. Gecko codes are handled separately. """

		# Check for conflicts among the code regions selected for use
		allCodeRegions = self.dol.getCustomCodeRegions( useRamAddresses=False )
		if regionsOverlap( allCodeRegions ):
			return []

		# Notify the user of incompatibility between the crash printout code and the Aux Code Regions, if they're both enabled
		if globalData.checkSetting( 'alwaysEnableCrashReports' ) and globalData.checkRegionOverwrite( 'Aux Code Regions' ):
			for mod in codeMods:
				if mod.name == "Enable OSReport Print on Crash":
					msg( 'The Aux Code Regions are currently enabled for custom code, however this area is required for the "Enable '
						 'OSReport Print on Crash" code to function, which is very useful for debugging crashes and is therefore '
						 'enabled by default. \n\nYou can easily resolve this by one of three ways: 1) disable use of the Aux Code '
						 'Regions (and restore that area to vanilla code), 2) change the settings option "Always Enable Crash Reports" '
						 'to False, or 3) remove the "Enable OSReport Print on Crash" code '
						 "from your library (or comment it out so it's not picked up by this program).", 'Aux Code Regions Conflict' )
					return []

		self.modifiedRegions = [] # Used to track data changes in the DOL and watch for conflicts
		standaloneFunctionsUsed = [] # Tracks functions that will actually make it into the DOL
		totalModsToInstall = len( codeMods )
		totalModsInstalled = 0
		codesNotInstalled = []
		
		# Save the selected Gecko codes to the DOL, and determine the adjusted code regions to use for injection/standalone code.
		# if geckoCodes:
		# 	# Ensure that the codelist length will be a multiple of 4 bytes (so that injection code after it doesn't crash from bad branches).
		# 	wrappedGeckoCodes = '00D0C0DE00D0C0DE' + geckoCodes + 'F000000000000000'
		# 	finalGeckoCodelistLength = roundTo32( len(wrappedGeckoCodes)/2, base=4 ) # Rounds up to closest multiple of 4 bytes
		# 	paddingLength = finalGeckoCodelistLength - len(wrappedGeckoCodes)/2 # in bytes
		# 	padding = '00' * paddingLength
		# 	wrappedGeckoCodes += padding

		# 	# Need to get a new list of acceptable code regions; one that reserves space for the Gecko codelist/codehandler
		# 	allCodeRegions = getCustomCodeRegions( codelistStartPosShift=finalGeckoCodelistLength, codehandlerStartPosShift=gecko.codehandlerLength )

		# else: # No Gecko codes to be installed
		# 	wrappedGeckoCodes = ''

		# 	if removingSomeGeckoCodes: # Then the regions that were used for them should be restored.
		# 		if overwriteOptions[ 'EnableGeckoCodes' ].get(): 
		# 			restoreGeckoParts = True # If they've already enabled these regions, the following changes should be fine and we don't need to ask.
		# 		else:
		# 			restoreGeckoParts = tkMessageBox.askyesno( 'Gecko Parts Restoration', 'All Gecko codes have been removed. '
		# 				'Would you like to restore the regions used for the Gecko codehandler and codelist ({} and {}) to vanilla Melee?'.format(gecko.codehandlerRegion, gecko.codelistRegion) )

		# 		if restoreGeckoParts:
		# 			if not gecko.environmentSupported: # Failsafe; if removingSomeGeckoCodes, gecko.environmentSupported should be True
		# 				msg( 'The configuration for Gecko codes seems to be incorrect; unable to uninstall Gecko codes and restore the Gecko code regions.' )
		# 			else:
		# 				vanillaHexAtHookOffset = getVanillaHex( gecko.hookOffset )

		# 				vanillaCodelistRegion = getVanillaHex( gecko.codelistRegionStart, byteCount=gecko.spaceForGeckoCodelist )
		# 				vanillaCodehandlerRegion = getVanillaHex( gecko.codehandlerRegionStart, byteCount=gecko.spaceForGeckoCodehandler )

		# 				if not vanillaHexAtHookOffset or not vanillaCodelistRegion or not vanillaCodehandlerRegion:
		# 					msg( 'Unable to restore the original hex at the location of the codehandler hook, or the areas for the Gecko codelist and codehandler. '
		# 						 'This is likely due to a missing original copy of the DOL, which should be here:\n\n' + dolsFolder + '\n\nThe filename should be "[region] [version].dol", '
		# 						 'for example, "NTSC 1.02.dol". Some mods may have been uninstalled, however you will need to reselect and save the new [non-Gecko] codes that were to be installed.',
		# 						 'Unable to find an original copy of the DOL' )

		# 					# Unexpected failsafe scenario. We'll be ignoring the areas occupied by most of the Gecko stuff (hook and codehandler); it will remain in-place. 
		# 					# Inefficient, but what're ya gonna do. Should at least be functional.
		# 					wrappedGeckoCodes = '00D0C0DE00D0C0DEF000000000000000' # Empty codelist; still need this; maybe? #totest
		# 					allCodeRegions = getCustomCodeRegions( codelistStartPosShift=16, codehandlerStartPosShift=gecko.codehandlerLength )
		# 					addToInstallationSummary( geckoInfrastructure=True )
		# 				else:
		# 					# Remove the branch to the codehandler and return this point to the vanilla code instruction.
		# 					replaceHex( gecko.hookOffset, vanillaHexAtHookOffset)

		# 					# Restore the free space regions designated for the Gecko codelist and codehandler
		# 					replaceHex( gecko.codelistRegionStart, vanillaCodelistRegion )
		# 					replaceHex( gecko.codehandlerRegionStart, vanillaCodehandlerRegion )

		# Zero-out the regions that will be used for custom code.
		# for regionStart, regionEnd in allCodeRegions:
		# 	regionLength = regionEnd - regionStart # in bytes
		# 	#replaceHex( regionStart, '00' * regionLength )
		# 	self.dol.setData( regionStart, bytearray(regionLength) )
			
		# # Create a dictionary to keep track of space in the dol that's available for injection codes
		# dolSpaceUsed = {}
		# for i in range( len(allCodeRegions) ):
		# 	# Add a key/value pair to keep track of how much space is used up for each code range.
		# 	key = 'area' + str(i + 1) + 'used'
		# 	dolSpaceUsed[key] = 0
		# arenaSpace = 0

		# Calculate the size of the toc, assuming codes.bin is added
		if self.rebuildReason:
			self.buildFstEntries() # Ensuring the list is current (might be safe to remove here)
		tocSize = len( self.fstEntries ) * 0xC
		for each in self.fstEntries[1:]: # Skipping root entry
			tocSize += len( each[-2] ) + 1
		self.injectionsCodeFile = self.files.get( self.gameId + '/codes.bin' )
		if self.injectionsCodeFile:
			if self.injectionsCodeFile.data:
				self.injectionsCodeFile.data = bytearray() # Clearing existing data
				self.injectionsCodeFile.unsavedChanges = [ 'Data cleared' ]
		else: # The tocSize value will only be used if codes.bin will be added, so account for the added toc size
			tocSize += 0x16

		# Build the allocation matrix, and zero-out the DOL's regions that will be used for custom code (if any)
		self.allocationMatrix = []
		for regionStart, regionEnd in allCodeRegions:
			regionLength = regionEnd - regionStart # in bytes
			self.dol.setData( regionStart, bytearray(regionLength) )

			self.allocationMatrix.append( [regionStart, regionEnd, 0] )

		# Add one more section to the allocation matrix to track arena code space usage (i.e. size of codes.bin)
		tocSpace = roundTo32( tocSize ) # Some padding is added between the TOC and end of RAM
		tocStart = 0x81800000 - tocSpace # Also, the end of the arena space
		self.allocationMatrix.append( [-1, tocStart - 0x20, 0] ) # Adds some padding between codes.bin and the TOC
		print 'predicted start of toc:', hex( tocStart )

		# If this is Melee, nop branches required for using the USB Screenshot regions, if those regions are used.
		if self.dol.isMelee and globalData.checkRegionOverwrite( 'Screenshot Regions' ):
			screenshotRegionNopSites = { 'NTSC 1.03': (0x1a1b64, 0x1a1c50), 'NTSC 1.02': (0x1a1b64, 0x1a1c50), 'NTSC 1.01': (0x1a151c, 0x1a1608),
										 'NTSC 1.00': (0x1a0e1c, 0x1a0f08), 'PAL 1.00':  (0x1a2668, 0x1a2754) }
			nop1Address = self.dol.offsetInRAM( screenshotRegionNopSites[self.dol.revision][0] )
			nop2Address = self.dol.offsetInRAM( screenshotRegionNopSites[self.dol.revision][1] )
			problemWithNop = self.storeCodeChange( nop1Address, '60000000', 'Screenshot Region NOP' )
			problemWithNop2 = self.storeCodeChange( nop2Address, '60000000', 'Screenshot Region NOP' )
			if problemWithNop or problemWithNop2:
				msg( 'One or more NOPs for the Screenshot Region could not be added, most likely due to a conflicting mod.' )
			else:
				nopSummaryReport = []
				nopSummaryReport.append( ('Code overwrite', 'static', screenshotRegionNopSites[self.dol.revision][0], 4) )
				nopSummaryReport.append( ('Code overwrite', 'static', screenshotRegionNopSites[self.dol.revision][1], 4) )
				#addToInstallationSummary( 'USB Screenshot Region NOP', 'static', nopSummaryReport, isMod=False ) # , iid='screenshotRegionNops'

		# Install any Gecko codes that were collected
		# if geckoCodes: # gecko.environmentSupported must be True
		# 	# Replace the codehandler's codelist RAM address
		# 	codelistAddress = offsetInRAM( gecko.codelistRegionStart, dol.sectionInfo ) + 0x80000000
		# 	codelistAddrBytes = struct.pack( '>I', codelistAddress ) # Packing to bytes as a big-endian unsigned int (4 bytes)
		# 	codehandlerCodelistAddr = gecko.codehandler.find( b'\x3D\xE0' ) # Offset of the first instruction to load the codelist address
		# 	gecko.codehandler[codehandlerCodelistAddr+2:codehandlerCodelistAddr+4] = codelistAddrBytes[:2] # Update first two bytes
		# 	gecko.codehandler[codehandlerCodelistAddr+6:codehandlerCodelistAddr+8] = codelistAddrBytes[2:] # Update last two bytes

		# 	# Calculate branch distance from the hook to the destination of the Gecko codehandler's code start
		# 	geckoHookDistance = calcBranchDistance( gecko.hookOffset, gecko.codehandlerRegionStart )

		# 	# Look for the first instruction in the codehandler, to offset the hook distance, if needed
		# 	codehandlerStartOffset = gecko.codehandler.find( b'\x94\x21' )
		# 	if codehandlerStartOffset != -1:
		# 		geckoHookDistance += codehandlerStartOffset

		# 	# Add the Gecko codehandler hook
		# 	geckoHook = assembleBranch( 'b', geckoHookDistance )
		# 	modifyDol( gecko.hookOffset, geckoHook, 'Gecko Codehandler Hook' )

		# 	# Add the codehandler and codelist to the DOL
		# 	modifyDol( gecko.codelistRegionStart, wrappedGeckoCodes, 'Gecko codes list' )
		# 	modifyDol( gecko.codehandlerRegionStart, hexlify(gecko.codehandler), 'Gecko Codehandler' )

		# else:
		# 	geckoSummaryReport = [] # May have been added to. Clear it.

		# def allocateSpaceInRam( dolSpaceUsedDict, customCode, customCodeLength ): # The customCode input should be preProcessed

		# 	""" Determines a location in RAM to store custom code. First checks for unused space among the custom 
		# 		code regions enabled for use. And then if no usable space is found there, allocates space in the Arena. 
		# 		Returns a RAM address for where the code is determined to be placed. """

		# 	customCodeOffset = -1

		# 	for i, ( areaStart, areaEnd ) in enumerate( allCodeRegions ):
		# 		spaceRemaining = areaEnd - areaStart - dolSpaceUsedDict['area' + str(i + 1) + 'used'] # value in bytes

		# 		if customCodeLength <= spaceRemaining:
		# 			customCodeOffset = areaStart + dolSpaceUsedDict['area' + str(i + 1) + 'used']
		# 			dolSpaceUsedDict['area' + str(i + 1) + 'used'] += customCodeLength # Updates the used area reference.
		# 			break

		# 	# If space was found in the DOL, convert the location to a RAM address and return it
		# 	if customCodeOffset != -1:
		# 		return self.dol.offsetInRAM( customCodeOffset )

		# 	return 0x81800000 - tocSize - 0x1E - arenaSpace - customCodeLength

		# Create a dictionary to keep track of space in the dol that's available for injection codes
		# dolSpaceUsed = {}
		# for i in range( len(allCodeRegions) ):
		# 	# Add a key/value pair to keep track of how much space is used up for each code range.
		# 	key = 'area' + str(i + 1) + 'used'
		# 	dolSpaceUsed[key] = 0
		# arenaSpace = 0

		tic = time.clock()

		# Primary code-saving pass.
		#standaloneFunctions = genGlobals['allStandaloneFunctions'] # Dictionary. Key='functionName', value=( functionAddress, functionCustomCode, functionPreProcessedCustomCode )
		customCodeProcessor = globalData.codeProcessor
		standaloneFunctions = globalData.standaloneFunctions
		modInstallationAttempt = 0
		#noSpaceRemaining = False

		for mod in codeMods:
			#if mod.state == 'unavailable' or mod.type == 'gecko': continue # Gecko codes have already been processed.

			#elif mod.state == 'enabled' or mod.state == 'pendingEnable':
			modInstallationAttempt += 1
			# programStatus.set( 'Installing Mods (' + str( round( (float(modInstallationAttempt) / totalModsToInstall) * 100, 1 ) ) + '%)' )
			# programStatusLabel.update()
			self.updateProgressDisplay( 'Installing Mods', -1, modInstallationAttempt, totalModsToInstall )

			problemWithMod = False
			#dolSpaceUsedBackup = dolSpaceUsed.copy() # This copy is used to revert changes in case there is a problem with saving this mod.
			allocationMatrixBackup = copy.deepcopy( self.allocationMatrix ) # This copy is used to revert changes in case there is a problem with saving this mod.
			newlyMappedStandaloneFunctions = [] # Tracked so that if this mod fails any part of installation, the standalone functions dictionary can be restored (installation offsets restored to -1).
			summaryReport = []

			# Allocate space for required standalone functions
			#if not noSpaceRemaining:
			# SFs are not immediately added to the DOL because they too may reference unmapped functions.
			requiredStandaloneFunctions, missingFunctions = mod.getRequiredStandaloneFunctionNames()

			# Now that the required standalone functions for this mod have been assigned space, add them to the DOL.
			if missingFunctions:
				msg( mod.name + ' cannot not be installed because the following standalone functions are missing:\n\n' + grammarfyList(missingFunctions) )
				problemWithMod = True

			else:
				# Map any new required standalone functions to the DOL if they have not already been assigned space.
				for functionName in requiredStandaloneFunctions:
					#functionAddress, functionCustomCode, functionPreProcessedCustomCode = standaloneFunctions[functionName]
					functionAddress, codeChange = standaloneFunctions[functionName]

					if functionName not in standaloneFunctionsUsed: # Has not been added to the dol. Map it
						#customCodeLength = getCustomCodeLength( functionPreProcessedCustomCode )
						codeChange.evaluate()
						customCodeAddress = self.allocateSpaceInRam( codeChange.length )

						# if customCodeAddress == -1:
						# 	# No more space in the DOL. (Mods requiring custom code space up until this one will still be saved.)
						# 	# noSpaceRemaining = True
						# 	# problemWithMod = True
						# 	# msg( "There's not enough free space for all of the codes you've selected. "
						# 	# 		"\n\nYou might want to try again after selecting fewer Injection Mods and/or Gecko codes. "
						# 	# 		"\n\nThe regions currently designated as free space can be configured and viewed via the 'Code-Space Options' "
						# 	# 		'button, and the "settings.py" file.', "The DOL's regions for custom code are full" )
						# 	# break
						# 	standaloneFunctions[functionName] = ( customCodeAddress, functionCustomCode, functionPreProcessedCustomCode )
						# else:
						# Storage location determined; update the SF dictionary with an offset for it
						#standaloneFunctions[functionName] = ( customCodeAddress, functionCustomCode, functionPreProcessedCustomCode )
						standaloneFunctions[functionName] = ( customCodeAddress, codeChange )
						newlyMappedStandaloneFunctions.append( functionName )

					else: # This mod uses one or more functions that are already allocated to go into the DOL
						#functionLength = getCustomCodeLength( functionPreProcessedCustomCode )
						summaryReport.append( ('SF: ' + functionName, 'standalone', functionAddress, codeChange.getLength()) )

				if newlyMappedStandaloneFunctions:
					# Add this mod's SFs to the DOL
					for functionName in newlyMappedStandaloneFunctions:
						#functionAddress, functionCustomCode, functionPreProcessedCustomCode = standaloneFunctions[functionName]
						functionAddress, codeChange = standaloneFunctions[functionName]

						# Replace custom syntax, and perform any final processing on the code
						returnCode, finishedCode = codeChange.finalizeCode( functionAddress )
						if returnCode != 0 and returnCode != 100:
							problemWithMod = True
						else:
							problemWithMod = self.storeCodeChange( functionAddress, finishedCode, mod.name + ' standalone function' )

						if problemWithMod: break
						else: summaryReport.append( ('SF: ' + functionName, 'standalone', functionAddress, len(finishedCode)/2) )
			
			# Add this mod's code changes & custom code (non-SFs) to the dol.
			if not problemWithMod:
				for codeChange in mod.getCodeChanges():
					customCodeLength = codeChange.getLength()

					if codeChange.type == 'static':
						#dolOffset = self.dol.normalizeDolOffset( codeChange.offset )
						ramAddress, errorMsg = self.dol.normalizeRamAddress( codeChange.offset )
						if ramAddress == -1:
							userMsg = 'A problem was found while processing a code change at {} for {};{}.'.format( codeChange.offset, mod.name, errorMsg.split(';')[1] )
							msg( userMsg + '\n\nThis code will be omitted from saving.' )
							problemWithMod = True
							break

						# Replace custom syntax, and perform any final processing on the code
						returnCode, finishedCode = codeChange.finalizeCode( ramAddress )
						if returnCode != 0 and returnCode != 100:
							problemWithMod = True
						else:
							problemWithMod = self.storeCodeChange( ramAddress, finishedCode, mod.name + ' static overwrite' )

						if problemWithMod: break
						else: summaryReport.append( ('Code overwrite', codeChange.type, ramAddress, customCodeLength) )

					elif codeChange.type == 'injection':
						#injectionSite = self.dol.normalizeDolOffset( codeChange.offset )
						injectionSite, errorMsg = self.dol.normalizeRamAddress( codeChange.offset )

						# if injectionSite < 0x100 or injectionSite > self.dol.maxDolOffset:
						# 	problemWithMod = True
						# 	msg('The injection site, ' + codeChange.offset + ', for "' + mod.name + '" is out of range of the DOL.\n\nThis code will be omitted from saving.')
						# 	break
						if injectionSite == -1:
							userMsg = 'A problem was found while processing the injection site {} for {};{}.'.format( codeChange.offset, mod.name, errorMsg.split(';')[1] )
							msg( userMsg + '\n\nThis code will be omitted from saving.' )
							problemWithMod = True
							break
						#else:
						# elif codeChange.preProcessedCode == '':
						# 	msg( 'There was an error while processing an injection code for "' + mod.name + '".\n\nThis code will be omitted from saving.' )
						# 	problemWithMod = True
						# 	break
						#else:
						# Find a place for the custom code.
						customCodeAddress = self.allocateSpaceInRam( customCodeLength )
					
						# if customCodeAddress == -1:
						# 	# No more space in the DOL. Injection codes up to this one (and all other changes) will be still be saved.
						# 	# noSpaceRemaining = True
						# 	# usedSpaceString = ''
						# 	# for i, regionRange in enumerate( allCodeRegions ):
						# 	# 	( start, end ) = regionRange
						# 	# 	if i != ( len(allCodeRegions) - 1 ): usedSpaceString = usedSpaceString + hex(start) + ' to ' + hex(end) + ', '
						# 	# 	else: usedSpaceString = usedSpaceString + ' and ' + hex(start) + ' to ' + hex(end) + '.'
						# 	# msg( "There's not enough free space for all of the codes you've selected. "
						# 	# 		"\n\nYou might want to try again after selecting fewer Injection Mods. "
						# 	# 		"\n\n               -         -         -      \n\nThe regions currently designated as "
						# 	# 		"free space in the DOL are " + usedSpaceString, "The DOL's regions for custom code are full" )
						# 	# break
						# else:
						# Calculate the initial branch from the injection site
						branchDistance = customCodeAddress - injectionSite
						#branch = assembleBranch( 'b', calcBranchDistance( injectionSite, customCodeAddress) )
						branch = customCodeProcessor.assembleBranch( 'b', branchDistance )

						# If the calculation above was successful, write the created branch into the dol file at the injection site
						# if branch == -1: problemWithMod = True
						# else:
						problemWithMod = self.storeCodeChange( injectionSite, branch, mod.name + ' injection site' )
						if problemWithMod: break
						else: summaryReport.append( ('Branch', 'static', injectionSite, 4) ) # changeName, changeType, dolOffset, customCodeLength

						# Replace custom syntax, and perform any final processing on the code
						returnCode, finishedCode = codeChange.finalizeCode( customCodeAddress )
						if returnCode != 0 and returnCode != 100:
							problemWithMod = True
						else:
							# If the return code was 100, the last instruction was created by a custom branch syntax, which was deliberate and we don't want it replaced.
							if returnCode == 0:
								# Check if the last instruction in the custom code is a branch or zeros. If it is, replace it with a branch back to the injection site.
								commandByte = finishedCode[-8:][:-6].lower()
								if commandByte == '48' or commandByte == '49' or commandByte == '4a' or commandByte == '4b' or commandByte == '00':
									#branchBack = assembleBranch( 'b', calcBranchDistance( (customCodeAddress + len(finishedCode)/2 - 0x8), injectionSite) )
									branchBackAddress = customCodeAddress + customCodeLength - 8
									branchBack = customCodeProcessor.assembleBranch( 'b', injectionSite - branchBackAddress )

									if branchBack == -1:
										problemWithMod = True
										break
									else: # Success; replace the instruction with the branch created above
										finishedCode = finishedCode[:-8] + branchBack

							# Add the injection code to the DOL.
							problemWithMod = self.storeCodeChange( customCodeAddress, finishedCode, mod.name + ' injection code' )
							if problemWithMod: break
							else: summaryReport.append( ('Injection code', codeChange.type, customCodeAddress, customCodeLength) )

			if problemWithMod:
				# Revert all changes associated with this mod to the game's vanilla code.
				for codeChange in mod.getCodeChanges():
					if codeChange.type == 'static' or codeChange.type == 'injection':
						#offset = self.dol.normalizeDolOffset( codeChange[2] )
						address = self.dol.normalizeRamAddress( codeChange.offset )[0]
						if address == -1: continue
						self.storeCodeChange( address, codeChange.origCode ) # Should silently fail if attempting to overrite what was already changed by another mod (changes existing in modifiedRegions)
					# Any extra code left in the 'free space' regions will just be overwritten by further mods or will otherwise not be used.

				# Restore the lookup used for tracking free space in the DOL to its state before making changes for this mod.
				#dolSpaceUsed = dolSpaceUsedBackup
				self.allocationMatrix = allocationMatrixBackup

				# Restore the standalone functions dictionary to as it was before this mod (set addresses back to -1).
				for functionName in newlyMappedStandaloneFunctions:
					# _, functionCustomCode, functionPreProcessedCustomCode = standaloneFunctions[functionName]
					# standaloneFunctions[functionName] = ( -1, functionCustomCode, functionPreProcessedCustomCode )
					standaloneFunctions[functionName] = ( -1, standaloneFunctions[functionName][1] )
				
				# Update the GUI to reflect changes.
				mod.setState( 'disabled' )
				codesNotInstalled.append( mod.name )
			else:
				# Remember that the standalone functions used for this mod were added to the dol.
				standaloneFunctionsUsed.extend( newlyMappedStandaloneFunctions )

				# Update the GUI to reflect changes.
				mod.setState( 'enabled' )
				totalModsInstalled += 1
				#addToInstallationSummary( mod.name, mod.type, summaryReport )

		# End of primary code-saving pass. Finish updating the Summary tab.
		# if geckoSummaryReport:
		# 	addToInstallationSummary( geckoInfrastructure=True )

		# 	for geckoReport in geckoSummaryReport:
		# 		summaryReport = [ geckoReport[2:] ]
		# 		addToInstallationSummary( geckoReport[0], geckoReport[1], summaryReport )

		# Check for modules composed of only standalone functions; these won't be set as enabled by the above code
		if standaloneFunctionsUsed:
			for mod in codeMods:
				#if mod.state == 'unavailable': continue

				# Check if this is a SF-only module
				functionsOnly = True
				functionNames = []
				for codeChange in mod.getCodeChanges():
					if not codeChange.type == 'standalone':
						functionsOnly = False
						break
					else:
						functionNames.append( codeChange.offset )

				if functionsOnly:
					# Check if this module is used
					for funcName in functionNames:
						if funcName in standaloneFunctionsUsed:
							print 'SF-only module', mod.name, 'is detected in save routine'
							mod.setState( 'enabled' ) # Already automatically added to the Standalone Functions table in the Summary Tab
							#totalModsInstalled += 1
							break # only takes one to make it count
					else: # loop didn't break; no functions for this mod used
						print 'SF-only module', mod.name, 'not detected in save routine'
						mod.setState( 'disabled' )

		toc = time.clock()
		print '\nMod installation time:', toc-tic

		# End of the 'not onlyUpdateGameSettings' block
		#updateSummaryTabTotals()

		# If this is SSBM, check the Default Game Settings tab for changes to save. (function execution skips to here if onlyUpdateGameSettings=True)
		# if self.dol.isMelee and self.dol.revision in settingsTableOffset:
		# 	for widgetSettingID in gameSettingsTable:
		# 		selectedValue = currentGameSettingsValues[widgetSettingID].get()
		# 		valueInDOL = getGameSettingValue( widgetSettingID, 'fromDOL' )
		# 		if selectedValue != valueInDOL:
		# 			tableOffset = gameSettingsTable[widgetSettingID][0]
		# 			fileOffset = settingsTableOffset[self.dol.revision] + tableOffset

		# 			# If the game settings tuple is greater than 3, it means there are strings that need to be attributed to a number that the game uses.
		# 			if widgetSettingID == 'damageRatioSetting': newHex = toHex( round(float(selectedValue) * 10, 1), 2 )
		# 			elif widgetSettingID == 'stageToggleSetting' or widgetSettingID == 'itemToggleSetting': newHex = selectedValue
		# 			elif widgetSettingID == 'itemFrequencySetting':
		# 				if selectedValue == 'None': newHex = 'FF'
		# 				else:
		# 					for i, item in enumerate( gameSettingsTable['itemFrequencySetting'][4:] ):
		# 						if item == selectedValue:
		# 							newHex = toHex( i, 2 )
		# 							break
		# 			elif len( gameSettingsTable[widgetSettingID] ) > 3: # For cases where a string is used, get the index of the current value.
		# 				for i, item in enumerate( gameSettingsTable[widgetSettingID][3:] ):
		# 					if item == selectedValue: 
		# 						newHex = toHex( i, 2 )
		# 						break
		# 			else: newHex = toHex( selectedValue, 2 ) 

		# 			# Set the new values in the DOL and update the gui to show that this has been saved.
		# 			decameledName = convertCamelCase( widgetSettingID )
		# 			self.storeCodeChange( fileOffset, newHex, decameledName + ' (from the Default Game Settings tab)' )
		# 			widgetControlID = widgetSettingID[:-7]+'Control'
		# 			updateDefaultGameSettingWidget( widgetControlID, selectedValue, False )

		# 			# Update the stage and items selections windows (if they're open) with the new values.
		# 			if widgetSettingID == 'stageToggleSetting' and root.stageSelectionsWindow: root.stageSelectionsWindow.updateStates( selectedValue, True, False )
		# 			elif widgetSettingID == 'itemToggleSetting' and root.itemSelectionsWindow: root.itemSelectionsWindow.updateStates( selectedValue, True, False )

		# If the injection code file was used, add codes to the game required to load it on boot
		if self.injectionsCodeFile and self.injectionsCodeFile.data:
			returnCode = self.installMallocCodes()

			if returnCode == 0:
				self.injectionsCodeFile.unsavedChanges = [ 'New codes saved' ]
				totalModsInstalled += 2

		# Update or add to the DOL's list of unsaved changes
		for i, change in enumerate( self.dol.unsavedChanges ):
			if change.endswith( 'code mod installed' ) or change.endswith( 'code mods installed' ):
				del self.dol.unsavedChanges[i]
				break
		if totalModsInstalled == 1:
			self.dol.unsavedChanges.append( '1 code mod installed' )
		else:
			self.dol.unsavedChanges.append( '{} code mods installed'.format(totalModsInstalled) )
		self.dol.writeMetaData() # Writes the DOL's revision (region+version) and this program's version to the DOL
		#self.files[self.gameId + '/Start.dol'] = self.dol

		if codesNotInstalled:
			msg( '{} code mods installed. However, these mods could not be installed:\n\n{}'.format(totalModsInstalled, '\n'.join(codesNotInstalled)) )

		return codesNotInstalled

	def installMallocCodes( self ):
		
		""" Loads the mods used for installing codes to the Arena, and creates or clears the 
			codes.bin file on the disc to prepare it for new codes. 
			May return with these return codes:
				0: Success
				1: Unable to load/parse the required mods 
				2: Problem installing the Malloc code
				3: Problem installing the file load code"""

		summaryReport = []

		# Parse and get the core code mods
		parser = CodeLibraryParser()
		modsFilePath = globalData.paths['coreCodes']
		#mods = parser.parseModsLibraryFile( modsFilePath, [] )
		
		# Build the list of paths for .include script imports (this will be prepended by the folder housing each mod text file)
		parser.includePaths = [ os.path.join(modsFilePath, '.include'), os.path.join(globalData.scriptHomeFolder, '.include') ]
		parser.processDirectory( modsFilePath )

		# arenaHiMalloc = fileLoadCode = None
		# for mod in mods:
		# 	if mod.name == 'Static ArenaHi Malloc': arenaHiMalloc = mod
		# 	elif mod.name == 'Load codes.bin': fileLoadCode = mod
		# if not arenaHiMalloc or not fileLoadCode: return 1

		# Search for the arena/memory allocation mod
		# for mod in parser.codeMods:
		# 	if mod.name == 'Static ArenaHi Malloc':
		# 		mallocMod = mod
		# 		break
		# else: return 1 # Couldn't find the mod
		mallocMod = parser.getModByName( 'Static ArenaHi Malloc' )
		if not mallocMod: return 1

		# Determine how much space is needed
		# arenaHiMallocInjection = arenaHiMalloc.getCodeChanges()[0] # Should be the only code change
		# arenaHiMallocLength = getCustomCodeLength( arenaHiMallocInjection[-2] )
		# fileLoadInjection = fileLoadCode.getCodeChanges()[0] # Should be the only code change
		# fileLoadCodeLength = getCustomCodeLength( fileLoadInjection[-2] )
		# arenaSpaceRequired = len( self.injectionsCodeFile.data ) + arenaHiMallocLength + fileLoadCodeLength

		# Determine how much space is needed in the arena, and get the specific code changes to edit
		#arenaSpaceRequired = len( self.injectionsCodeFile.data )
		arenaHiMallocInjection = fileLoadInjection = None
		for codeChange in mallocMod.getCodeChanges():
			if codeChange.offset == '80375324': arenaHiMallocInjection = codeChange
			elif codeChange.offset == '803753E4': fileLoadInjection = codeChange
		assert arenaHiMallocInjection and fileLoadInjection, 'Missing a code change for {}'.format( mallocMod.name )
			#arenaSpaceRequired += codeChange.getLength()

		# Update the space allocation amount in the malloc code (values for the first two instructions)
		# mallocCode = arenaHiMallocInjection[-2]
		# assert mallocCode.startswith( '3C00000060040000' ), 'Invalid Malloc code; expected first instructions to be "lis r0" & "ori r4, r0".'
		# mallocCode = '3C00{:04X}6004{:04X}'.format( arenaSpaceRequired >> 16, arenaSpaceRequired & 0xFFFF ) + mallocCode[16:]

		arenaHiMallocLength = arenaHiMallocInjection.getLength()
		fileLoadCodeLength = fileLoadInjection.getLength()
		reservationSize = len( self.injectionsCodeFile.data ) + arenaHiMallocLength + fileLoadCodeLength
		_, arenaEnd, arenaSpaceUsed = self.allocationMatrix[-1]
		self.allocationMatrix[-1][-1] += arenaHiMallocLength + fileLoadCodeLength # Just in case anything else also wants to look at this
		reservationLocation = arenaEnd - reservationSize
		
		# Set allocation configurations on the mod
		try:
			mallocMod.configure( 'Reservation Size', reservationSize )
			mallocMod.configure( 'Reservation Location', reservationLocation )
		except Exception as err:
			msg( 'Unable to install {}; {}'.format(mallocMod.name, err) )
			return

		# Calculate the RAM address for the arena allocation injection code, and allocate space for it
		arenaSpaceUsed += arenaHiMallocLength
		#self.allocationMatrix[-1][-1] += arenaHiMallocLength
		mallocCodeAddress = arenaEnd - arenaSpaceUsed - arenaHiMallocLength
		#mallocInjectionSite = self.dol.normalizeRamAddress( arenaHiMallocInjection.offset )[0]
		mallocInjectionSite = int( arenaHiMallocInjection.offset, 16 )

		# Build and store the branch to the above address
		branchDistance = mallocCodeAddress - mallocInjectionSite
		branch = globalData.codeProcessor.assembleBranch( 'b', branchDistance )
		conflict = self.storeCodeChange( mallocInjectionSite, branch, mallocMod.name + ' injection site', True )
		if conflict:
			return 2
		else: summaryReport.append( ('Branch', 'static', mallocInjectionSite, 4) ) # changeName, changeType, dolOffset, customCodeLength

		# Install the memory allocation custom code
		#returnCode, finalizedCode = mallocMod.finalCodeProcessing( mallocCodeAddress, arenaHiMallocInjection )
		returnCode, finalizedCode = arenaHiMallocInjection.finalizeCode( mallocCodeAddress )
		assert returnCode != 0, 'Error in finalizing malloc code'
		conflict = self.storeCodeChange( mallocCodeAddress, finalizedCode, mallocMod.name + ' injection code', True )
		if conflict:
			return 2
		else: summaryReport.append( ('Injection code', 'injection', mallocInjectionSite, arenaHiMallocLength) ) # changeName, changeType, dolOffset, customCodeLength

		# Calculate RAM address for the injection code, and allocate space for it
		#self.allocationMatrix[-1][-1] += fileLoadCodeLength
		loadCodeAddress = arenaEnd - arenaSpaceUsed - fileLoadCodeLength
		assert reservationLocation == loadCodeAddress, 'Should be equal!'
		#fileLoadInjectionSite = self.dol.normalizeRamAddress( fileLoadInjection[2] )[0]
		fileLoadInjectionSite = int( fileLoadInjection.offset, 16 )

		# Update the memory location in the file load code (lis/ori instructions)
		# loadCode = fileLoadInjection[-2]
		# assert '3C00FFFFBB8100086004FFFF' in loadCode, 'Invalid Load code; expected to find 3C00FFFFBB8100086004FFFF within it.'
		# memoryLocation = arenaEnd - arenaSpaceUsed
		# instructionReplacement = '3C00{:04X}BB8100086004{:04X}'.format( memoryLocation >> 16, memoryLocation & 0xFFFF )
		# loadCode = loadCode.replace( '3C00FFFFBB8100086004FFFF', instructionReplacement )

		# Build and store the branch to the above address
		branchDistance = reservationLocation - fileLoadInjectionSite
		branch = globalData.codeProcessor.assembleBranch( 'b', branchDistance )
		conflict = self.storeCodeChange( fileLoadInjectionSite, branch, fileLoadInjection.name + ' injection site', True )
		if conflict:
			return 3
		else: summaryReport.append( ('Branch', 'static', fileLoadInjectionSite, 4) ) # changeName, changeType, dolOffset, customCodeLength

		# Install the memory allocation code
		#returnCode, finalizedCode = mallocMod.finalCodeProcessing( reservationLocation, fileLoadInjection )
		returnCode, finalizedCode = fileLoadInjection.finalizeCode( reservationLocation )
		assert returnCode != 0, 'Error in finalizing file load code'
		conflict = self.storeCodeChange( reservationLocation, finalizedCode, fileLoadInjection.name + ' injection code', True )
		if conflict:
			return 3
		else: summaryReport.append( ('Injection code', 'injection', fileLoadInjectionSite, fileLoadCodeLength) ) # changeName, changeType, dolOffset, customCodeLength
		
		return 0

	def restoreDol( self, vanillaDiscPath='' ):

		""" Replaces the Start.dol file with a vanilla copy from a vanilla disc. 
			Or, if a path is given for the 'dolSource' setting, that DOL is used. """
		
		dolPath = globalData.checkSetting( 'dolSource' )

		if dolPath == 'vanilla':
			if not vanillaDiscPath:
				# See if we can get a reference to vanilla DOL code
				vanillaDiscPath = globalData.getVanillaDiscPath()
				if not vanillaDiscPath: # User canceled path input
					printStatus( 'Unable to restore the DOL; no vanilla disc available for reference', error=True )
					return
			
			vanillaDisc = Disc( vanillaDiscPath )
			vanillaDisc.load()
			#self.files[self.gameId + '/Start.dol'] = copy.deepcopy( vanillaDisc.dol )
			self.replaceFile( self.dol, vanillaDisc.dol )

		elif not os.path.exists( dolPath ):
			printStatus( 'Unable to restore the DOL; the source DOL could not be found', error=True )

		else:
			print 'not yet supported'
			print dolPath

	# def runInEmulator( self ): #todo: add support for root folders
		
	# 	# Get the path to the user's emulator of choice
	# 	# emulatorPath = globalData.getEmulatorPath() # Will also validate the path
	# 	# if not emulatorPath: return # User may have canceled the prompt

	# 	# # Make sure there are no prior instances of Dolphin running
	# 	# for process in psutil.process_iter():
	# 	# 	if process.name() == 'Dolphin.exe':
	# 	# 		process.terminate()
	# 	# 		printStatus( 'Stopped Dolphin process' )
	# 	# 		time.sleep( 3 )
	# 	# 		break

	# 	# printStatus( 'Booting in emulator....' )
	# 	# print 'Booting', self.filePath
	# 	# print 'In', emulatorPath
		
	# 	# # Send the disc filepath to Dolphin
	# 	# # '--exec' loads the specified file. (Using '--exec' because '/e' is incompatible with Dolphin 5+, while '-e' is incompatible with Dolphin 4.x)
	# 	# # '--batch' will prevent dolphin from unnecessarily scanning game/ISO directories, and will shut down Dolphin when the game is stopped.
	# 	# #command = '"{}" --batch --exec="{}"'.format( emulatorPath, self.filePath )
	# 	# command = '"{}" --batch --debugger --exec="{}"'.format( emulatorPath, self.filePath )
	# 	# subprocess.Popen( command, stderr=subprocess.STDOUT, creationflags=0x08000000 )

	# 	dolphin = Dolphin()
	# 	dolphin.start( self )


class MicroMelee( Disc ):

	""" Special build of Melee used for testing assets such as characters and stages. 
		This is an extremely trimmed-down copy of the game, dynamically built from a vanilla 
		disc when needed, and dynamically modified for quickly testing specific assets. """

	def __init__( self, filePath ):

		super( MicroMelee, self ).__init__( filePath )

		self.gameId = 'GALE01'
		self.imageName = 'Micro Melee Test Disc'
		self.isMelee = '02'
		self.gameVersion = '02'

	def buildFromVanilla( self, vanillaDiscPath ):

		""" Builds a new micro-sized disc from a vanilla NTSC 1.02 game disc.
			Could be done via xdelta patch, but this saves space. Avoiding files' 
			.getData() to prevent having to open the source disc multiple times. """

		tic = time.clock()

		# Load the vanilla game disc
		vanillaDisc = Disc( vanillaDiscPath )
		vanillaDisc.loadGameCubeMediaFile()

		# Display update progress at 0%
		discBuildMsg = 'Gathering data for test disc:'
		self.updateProgressDisplay( discBuildMsg, 0, 0, 100 )

		dataCopiedSinceLastUpdate = 0
		totalFiles = len( vanillaDisc.files )
		# tic = time.clock()
		# defaultStageExtId = self.checkDefaultStage()
		# defaultStageIntId = vanillaDisc.dol.getIntStageIdFromExt( defaultStageExtId )
		# defaultStage = vanillaDisc.dol.getStageFilename( defaultStageIntId )[1]
		# toc = time.clock()
		# print 'Time to check default stage:', toc-tic
		# print 'default stage:', defaultStage
		# return
		
		# Get the vanilla data for all files we'd like to copy over
		with open( vanillaDiscPath, 'rb' ) as vanillaFile:
			for i, fileObj in enumerate( vanillaDisc.files.itervalues() ):
				# Skip unnecessary files
				if fileObj.filename.startswith( 'GmRegend' ): # Congratulation Screens (1-Player mode)
					continue
				# elif fileObj.filename.startswith( 'Gr' ) and not fileObj.filename == 'GrSh.dat': # All stages except Temple
				# 	continue
				elif fileObj.filename.endswith( '.mth' ): # Video files
					continue
				elif fileObj.filename.startswith( 'Ty' ): # Trophies
					if fileObj.filename.startswith( 'TyDatai' ): pass # Needed to boot to match
					else: continue

				# Get the original file's data, and add the file to this new disc
				vanillaFile.seek( fileObj.offset )
				fileObj.data = vanillaFile.read( fileObj.size )
				fileObj.source = 'self'
				self.files[fileObj.isoPath] = fileObj

				# Update progress
				#totalDataCopied += fileObj.size
				dataCopiedSinceLastUpdate += fileObj.size
				dataCopiedSinceLastUpdate = self.updateProgressDisplay( discBuildMsg, dataCopiedSinceLastUpdate, i, totalFiles )

		# Display update progress at 100%
		self.updateProgressDisplay( discBuildMsg, 0, 100, 100 )

		# Set up some special conditions for building the disc
		self.isRootFolder = True # Prevent the buildNewDisc method from referencing an original disc when "re"-building
		origPadding = globalData.settings.get( 'General Settings', 'paddingBetweenFiles' )
		globalData.settings.set( 'General Settings', 'paddingBetweenFiles', '0x10000' ) # Add a bit more padding between files, so it doesn't have to be rebuilt as often
		
		# Build a new disc (overwriting existing file, if present)
		self.buildNewDisc( buildMsg='Building the Micro Melee testing disc:' )

		# Restore the special conditions
		self.isRootFolder = False # Restore to normal so the disc can be rebuilt as normal
		globalData.settings.set( 'General Settings', 'paddingBetweenFiles', origPadding )

		toc = time.clock()
		print 'Time to build micro melee:', toc-tic

	def buildNewDisc( self, newFilePath='', buildMsg='Building the Micro Melee testing disc:' ):

		""" Overriding this to ensure disc name is preserved, even after rebuilds. """
		
		# Temporarily disable the backup-on-rebuild feature
		origBackupSetting = globalData.checkSetting( 'backupOnRebuild' ) # May be a bool or BooleanVar
		globalData.setSetting( 'backupOnRebuild', False )

		returnCode = super( MicroMelee, self ).buildNewDisc( self.filePath, buildMsg )
		
		# Restore the backup-on-rebuild feature
		globalData.setSetting( 'backupOnRebuild', origBackupSetting )

		return returnCode

	# def checkDefaultStage( self ):

	# 	""" Loads the Asset Test mod in order to check what the default stage for asset testing is set to. """

	# 	# Parse the Core Codes library for the codes needed for testing
	# 	parser = CodeLibraryParser()
	# 	modsFilePath = globalData.paths['coreCodes']
	# 	parser.includePaths = [ os.path.join(modsFilePath, '.include'), os.path.join(globalData.scriptHomeFolder, '.include') ]
	# 	parser.processDirectory( modsFilePath )

	# 	# Customize the code mod to load the given stage
	# 	assetTest = parser.getModByName( 'Asset Test' )
	# 	if assetTest:
	# 		return assetTest.getConfiguration( "Stage" )
	# 	else:
	# 		printStatus( 'Unable to find the Asset Test mod in the Core Codes library!', warning=True )
	# 		return -1

	def testStage( self, stageObj ):
		
		""" Method to set up the Micro Melee disc to boot directly to the given stage file. """

		# Replace Temple with the given stage
		# templeFile = self.files[self.gameId + '/GrSh.dat']
		# self.replaceFile( templeFile, stageObj )

		# Get the internal stage ID and disc filename
		externalStageId = stageObj.externalId
		internalStageId = self.dol.getIntStageIdFromExt( externalStageId )
		stageFilename = self.dol.getStageFileName( internalStageId )[1]

		# Replace the file in the disc
		stageObj = copy.deepcopy( stageObj ) # Don't modify the original file!
		isoPath = self.gameId + '/' + stageFilename
		if isoPath in self.files:
			fileToReplace = self.files[isoPath]
			self.replaceFile( fileToReplace, stageObj )
		else:
			stageObj.isoPath = isoPath
			self.addFiles( [stageObj] )

		# Parse the Core Codes library for the codes needed for testing
		parser = CodeLibraryParser()
		modsFilePath = globalData.paths['coreCodes']
		parser.includePaths = [ os.path.join(modsFilePath, '.include'), os.path.join(globalData.scriptHomeFolder, '.include') ]
		parser.processDirectory( modsFilePath )

		# Customize the Asset Test mod to load the given stage
		codesToInstall = []
		assetTest = parser.getModByName( 'Asset Test' )
		if not assetTest:
			msg( 'Unable to find the Asset Test mod in the Core Codes library!', warning=True )
			return
		assetTest.configure( "Stage", externalStageId )
		codesToInstall.append( assetTest )
		
		# Add Enable OSReport Print on Crash, if enabled
		if globalData.checkSetting( 'alwaysEnableCrashReports' ):
			osReport = parser.getModByName( 'Enable OSReport Print on Crash' )
			if osReport:
				codesToInstall.append( osReport )
			else:
				printStatus( 'Unable to find the Enable OSReport Print on Crash mod in the Core Codes library!', warning=True )
		
		# Get the music table struct and the default song ID
		# grGroundParamStruct = stageObj.getStructByLabel( 'grGroundParam' )
		# musicTableOffset = grGroundParamStruct.getValues( 'Music_Table_Pointer' )
		# musicTableStruct = stageObj.getStruct( musicTableOffset )
		musicTableStruct = stageObj.getMusicTableStruct()
		songId = musicTableStruct.getValues()[1]

		# Check if we can enable audio (if the music file is present)
		# musicFile = self.getMusicFile( songId )
		# if musicFile:
		# 	assetTest.configure( "Stage", externalStageId )

		# Restore the DOL's data to vanilla and then install the necessary codes
		self.restoreDol()
		self.installCodeMods( codesToInstall )
		self.save()

		# Engage emulation
		#self.runInEmulator()
		globalData.dolphinController.start( self )

	def testCharacter( self, charObj ):
		
		""" Method to set up the Micro Melee disc to boot directly to a match with the given character file. """
		
		# Replace the appropriate character file
		charObj = copy.deepcopy( charObj ) # Don't modify the original file!
		isoPath = self.gameId + '/' + charObj.buildDiscFileName()
		fileToReplace = self.files.get( isoPath )
		if not fileToReplace:
			msg( 'Unable to find the character file in the disc to replace.' )
			return
		elif charObj.extCharId == -1:
			msg( 'Unable to determine the internal character ID for ' + charObj.filename )
			return
		self.replaceFile( fileToReplace, charObj )

		# Parse the Core Codes library for the codes needed for testing
		parser = CodeLibraryParser()
		modsFilePath = globalData.paths['coreCodes']
		parser.includePaths = [ os.path.join(modsFilePath, '.include'), os.path.join(globalData.scriptHomeFolder, '.include') ]
		parser.processDirectory( modsFilePath )

		# Customize the Asset Test mod to load the given character
		codesToInstall = []
		assetTest = parser.getModByName( 'Asset Test' )
		if not assetTest:
			msg( 'Unable to find the Asset Test mod in the Core Codes library!', warning=True )
			return
		assetTest.configure( "Player 1 Character", charObj.extCharId )
		assetTest.configure( "P1 Costume ID", charObj.getCostumeId() )
		codesToInstall.append( assetTest )

		# Restore the DOL's data to vanilla and then install the necessary codes
		self.restoreDol()
		self.installCodeMods( codesToInstall )
		self.save()

		# Engage emulation
		#self.runInEmulator()
		globalData.dolphinController.start( self )