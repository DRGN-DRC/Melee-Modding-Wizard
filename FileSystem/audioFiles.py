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

from __future__ import print_function # Use print with (); preparation for moving to Python 3

import os
import math
import struct
from string import hexdigits

# Internal dependencies
import globalData
from fileBases import FileBase
from basicFunctions import msg, cmdChannel, allAreEqual


class MusicFile( FileBase ):

	""" For HPS files. """
	
	def __init__( self, *args, **kwargs ):
		FileBase.__init__( self, *args, **kwargs )

		self.externalWavFile = ''
		self.sampleRate = -1
		self.channels = -1
		#self.channelMetaData = [] 	# A list of metadata values for each channel
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
				print( 'Unable to determine musicId without the host disc.' )

		return self._musicId

	@musicId.setter
	def musicId( self, newValue ):
		self._musicId = newValue

	def validate( self ):

		""" Verifies whether this is actually an HPS file by checking for the magic word. """

		headerData = self.getData( 0, 0x10 )
		if not headerData[:8] == ' HALPST\x00':
			raise Exception( 'Invalid HPS file; magic word "HALPST" not found.' )
	
	def readHeader( self ):

		""" Read the header for the magic word (first 8 bytes), sample rate (next 4 bytes), and number of channels (next 4 bytes). """

		# Header:
		#   0: Magic number
		# 0x8: Sample Rate
		# 0xC: Number of channels
		headerData = self.getData( 0, 0x10 )
		assert headerData[:8] == ' HALPST\x00', 'Invalid HPS magic word! This does not appear to be an HPS file.'
		self.sampleRate, self.channels = struct.unpack( '>II', headerData[8:] )
		if self.channels != 2: print( 'Found an HPS file that does not have 2 tracks!', self.filename )

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
		# for channel in range( self.channels ):
		# 	offset = 0x10 + ( channel * 0x38 )
		# 	values = list( struct.unpack('>HHIII', self.data[offset:offset+0x10]) )
		# 	values.extend( struct.unpack('>HHHH', self.data[offset+0x30:offset+0x38]) )
		# 	# print 'loop flag :', values[0]
		# 	# print 'format    :', values[1]
		# 	# print 'StartAddr :', values[2]
		# 	# print 'EndAddr   :', hex(values[3])
		# 	# print 'CurrentAdr:', values[4]
		# 	# print 'gain      :', values[5]
		# 	# print 'pScale    :', values[6]
		# 	# print 'initSH1   :', values[7]
		# 	# print 'initSH2   :', values[8]
		# 	# print 'byteCount :', hex(( values[3] - values[4] ) / 2)
		# 	# print 'loopStart :', values[2] - values[4], hex(values[2] - values[4])
		# 	# print ''
		# 	self.channelMetaData.append( values )

		# Compare like values (not needed; just looking for descrepencies)
		# Upon testing, looks like just pScale has differing values between channels
		# names = [ 'loop flag', 'format', 'StartAddr', 'EndAddr', 'CurrentAdr', 'gain', 'pScale', 'initSH1', 'initSH2' ]
		# i = 0
		# for likeValues in zip( *self.channelMetaData ):
		# 	if not allAreEqual( likeValues ):
		# 		print( 'Found differing channel metadata!' )
		# 		print( names[i] )
		# 		print( likeValues )
		# 	i += 1

	def readBlocks( self ):

		""" Reads through the data blocks of the file to determine 
			track length (self.duration) and the loop point. """

		# Ensure the file header has be read
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

		loops = False
		dataLengths = []
		#blockLengths = []
		totalDataBytes = 0.0
		self.blockOffsets = []

		while True:
			blockLength, dataLength, nextBlockOffset = struct.unpack( '>IIi', self.data[blockOffset:blockOffset+0xC] )
			self.blockOffsets.append( blockOffset )
			#blockLengths.append( blockLength )
			dataLengths.append( dataLength )
			totalDataBytes += dataLength

			# Look for a loop-back point or another end to the data
			if nextBlockOffset == -1: # No looping!
				break
			elif nextBlockOffset < blockOffset:
				loops = True
				break
			elif nextBlockOffset + 0xC > self.size:
				print( 'Invalid next-block offset!: ' + hex(nextBlockOffset + 0xC) )
				break
			else:
				blockOffset = nextBlockOffset

		# print '\n', len( self.blockOffsets ), 'total blocks'
		# print 'block offsets:', [ hex(o) for o in self.blockOffsets ]
		# print 'block lengths:', [ hex(o) for o in blockLengths ]
		# print 'data lengths:', [ hex(o) for o in dataLengths ]
		# print 'total block length:', sum( blockLengths )
		# print 'total data length :', sum( dataLengths )
		# print 'final block offset:', hex(self.blockOffsets[-1])

		# Calculate track duration
		compressionRatio = 1.75 * 1000
		self.duration = math.ceil( totalDataBytes / self.channels / self.sampleRate * compressionRatio )

		if loops:
			# Determine how much data will be excluded by the loop
			excludedDataLen = 0.0
			for offset, dataLength in zip( self.blockOffsets, dataLengths ):
				if offset == nextBlockOffset: # Found the loop block
					break
				excludedDataLen += dataLength

			# Calculate the duration of the excluded data
			if excludedDataLen == 0: # Loops back to the first block
				self.loopPoint = 0
			else:
				self.loopPoint = math.ceil( excludedDataLen / self.channels / self.sampleRate * compressionRatio )
		else:
			self.loopPoint = -1

	# def setLoopPoint( self, point ):

	# 	""" Sets the given loop point (time position, in milliseconds) to the 
	# 		nearest data block offset. Returns an exit code for success/failure:
	# 			0: Success
	# 			1: Unable to set the loop point; the value is too high
	# 			2: Unable to set the loop point; file data ended prematurely """

	# 	# Approximate the amount of data to skip for the loop
	# 	compressionRatio = 1.75 * 1000
	# 	estimatedDataLength = point / compressionRatio * self.sampleRate * 2

	# 	if estimatedDataLength >= self.size - 0x20:
	# 		print( 'The given loop point is too high; beyond data blocks' )
	# 		return 1

	# 	# Calculate the offset of the first block
	# 	blockOffset = 0x10 + ( self.channels * 0x38 ) # Typically 0x80 in a 2-channel file

	# 	loops = False
	# 	totalDataBytes = 0
	# 	loopBlockOffset = -1

	# 	while True:
	# 		blockLength, dataLength, nextBlockOffset = struct.unpack( '>IIi', self.data[blockOffset:blockOffset+0xC] )
	# 		blockStart = totalDataBytes
	# 		totalDataBytes += dataLength

	# 		# Check if the loop point is within this block (if it hasn't already been determined)
	# 		if estimatedDataLength <= totalDataBytes and loopBlockOffset > -1:
	# 			# Check if we're closer to the start of this block or the next
	# 			toBlockStart = estimatedDataLength - blockStart
	# 			toBlockEnd = totalDataBytes - estimatedDataLength
	# 			if toBlockStart <= toBlockEnd:
	# 				loopBlockOffset = blockOffset
	# 			else:
	# 				loopBlockOffset = nextBlockOffset

	# 		# Look for a loop-back point or another end to the data
	# 		if nextBlockOffset == -1: # No looping!
	# 			break
	# 		elif nextBlockOffset < blockOffset:
	# 			loops = True
	# 			break
	# 		elif nextBlockOffset + 0xC > self.size:
	# 			print( 'Invalid next-block offset!: ' + hex(nextBlockOffset + 0xC) )
	# 			break
	# 		else:
	# 			blockOffset = nextBlockOffset

	# 	if loopBlockOffset == -1: # Failsafe; shouldn't happen, even with a bad given point
	# 		print( 'Unable to set a loop point; unable to find a data block that would contain it! The file data may be incomplete or corrupt.' )
	# 		return 2



	# 	return self._isHexTrack
		
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

		self._shortDescription = description
		self._longDescription = description

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
		returnCode, _ = cmdChannel( [meleeMediaExe, tempInputFilepath, outputPath] )
		if returnCode != 0:
			print( 'Unable to convert', self.filename, 'to wav format.' )
			return ''

		# Delete the temporary HPS file
		os.remove( tempInputFilepath )

		# toc = time.clock()
		# print 'time to get as wav:', toc-tic

		self.externalWavFile = outputPath

		return outputPath