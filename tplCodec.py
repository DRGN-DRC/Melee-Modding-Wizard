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

import os, sys
import struct, time
import png, subprocess 	# Used for png reading/writing, and command-line communication

#from PIL import Image
from itertools import chain
from string import hexdigits
from binascii import hexlify

# Find the best implementation of StringIO available on this platform (used to treat raw binary data as a file).
try: from cStringIO import StringIO # Preferred for performance.
except: from StringIO import StringIO

#from basicFunctions import toInt

# These paths cannot be left as relative, because drag-n-drop functionality with the main program (when opening) may change the active working directory.
scriptHomeFolder = os.path.abspath( os.path.dirname(sys.argv[0]) ) # Can't use __file__ after freeze
pathToPngquant = os.path.join( scriptHomeFolder, 'bin', 'pngquant.exe' )


class missingType( Exception ): pass
class noPalette( Exception ): pass


# def loadTextureFile( filePath ):

# 	# If the imported file is in TPL format, convert it to PNG
# 	if filePath[-4:] == '.tpl':
# 		# Get image dimensions
# 		with open( filepath, 'rb' ) as binaryFile:
# 			binaryFile.seek( 0xC )
# 			imageHeaderAddress = toInt( binaryFile.read(4) )

# 		newImage = TplDecoder( filePath, (origWidth, origHeight), origImageType )
# 		newFilePath = destinationFolder + newFileName + '.tpl'
# 		newImage.createPngFile( newFilePath, creator='DTW - v' + programVersion )


class CodecBase( object ): # The functions here in CodecBase are inherited by both of the encoder/decoder classes.

	""" Provides file reading and palette generation methods to the primary encoding and decoding classes. """

	version = 3.0
	
	blockDimensions = { # Defines the block width and height, in texels (pixels, basically), respectively, for each image type.
		0: (8,8), 1: (8,4), 2: (8,4), 3: (4,4), 4: (4,4), 5: (4,4), 6: (4,4), 8: (8,8), 9: (8,4), 10: (4,4), 14: (8,8) } 
		# For type 14, it's technically 8x8 pixels with 2x2 sub-blocks

	def __init__( self, filepath, imageType, paletteType, maxPaletteColors, paletteQuality ):
		self.filepath = filepath
		self.imageType = imageType
		self.paletteType = paletteType
		self.paletteColorCount = 0
		self.paletteQuality = paletteQuality # 1=slow, 3=pngquant default, 11=fast & rough
		self.originalPaletteColorCount = 0
		self.maxPaletteColors = maxPaletteColors
		self.paletteRegenerated = False
		self.rgbaPixelArray = [] 					# Will always be RGBA tuples, even for paletted images.

		# Required after initialization if it's an image to be decoded
		self.encodedImageData = bytearray()
		self.encodedPaletteData = bytearray()
		
		# Required after initialization if it's an image to be encoded
		self.imageDataArray = [] # May be palette indices or RGBA tuples (depending on image type)
		self.rgbaPaletteArray = [] # List of RGBA tuples

	def cmdChannel( self, command, standardInput=None ):
		
		""" IPC (Inter-Process Communication) to command line. 
			shell=True gives access to all shell features, which 
			is required in this case (for the piping, I assume). """
		
		process = subprocess.Popen( command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=0x08000000 )
		stdout_data, stderr_data = process.communicate( input=standardInput )

		if process.returncode == 0:
			return ( process.returncode, stdout_data )
		else: 
			return ( process.returncode, stderr_data )

	def readImageData( self ):

		""" Reads the given image file to collect basic properties and image and/or palette data. """

		if self.imageType == None:
			raise missingType( 'No image type was provided or determined.' )

		# Based on the file type, open the file and deconstruct it into its required components.
		fileFormat = os.path.splitext( self.filepath )[1].lower()
		if fileFormat == '.tpl': self.fromTplFile()
		elif fileFormat == '.png': self.fromPngFile()
		else:
			raise IOError( "Unsupported file type." )

	def determinePaletteEncoding( self, imageProperties ):

		""" Determines the type of encoding that should be used if this texture 
			is to be written into the game. First checks some image properties, 
			but if they are indeterminable, the palette colors will be analyzed. """

		# If no palette type was provided, analyze the file and/or palette entries to determine what the type and encoding should be.
		if imageProperties['greyscale'] == 'True':
			self.paletteType = 0
		elif imageProperties['alpha'] == 'False':
			self.paletteType = 1
		else: # Image is RGBA, which doesn't necessarily mean it's actually utilizing all of the channels.
			for paletteEntry in self.rgbaPaletteArray:
				if paletteEntry[3] != 255:
					self.paletteType = 2
					break
			else: # The loop above didn't break; continue the investigation with a greyscale check on the palette.
				for paletteEntry in self.rgbaPaletteArray:
					r, g, b, _ = paletteEntry
					if r != g or g != b:
						self.paletteType = 1
						break
				else: # The loop above didn't break; the image is greyscale
					self.paletteType = 0

	def generatePalette( self ):

		""" Opens a command-line interface to pngquant with a command to create 
			a new palette with the required color count. """

		# Send pngquant the current file
		if self.filepath:
			exitCode, cmdOutput = self.cmdChannel( '"{}" --speed {} {} -- <"{}"'.format(pathToPngquant, self.paletteQuality, self.maxPaletteColors, self.filepath) )
														 # Above ^: --speed is a speed/quality balance. 1=slow, 3=default, 11=fast & rough
		# No file available, send pngquant the PIL image using the stdin buffer
		elif self.pilImage:
			# Save the PIL image into a buffer so it can be sent to pngquant's stdin
			pilInputBuffer = StringIO()
			self.pilImage.save( pilInputBuffer, 'png' )
			stdin = pilInputBuffer.getvalue()

			exitCode, cmdOutput = self.cmdChannel( '"{}" --speed {} {} - '.format(pathToPngquant, self.paletteQuality, self.maxPaletteColors), standardInput=stdin )
														 # Above ^: --speed is a speed/quality balance. 1=slow, 3=default, 11=fast & rough
			pilInputBuffer.close()

		else: # :O
			raise IOError( "No filepath or PIL image provided to the TPL Codec's generatePalette method." )

		if exitCode == 0: # Success
			# Connect to the output buffer (stdout)
			fileBuffer = StringIO( cmdOutput )

			pngImage = png.Reader( fileBuffer )
			pngImageInfo = pngImage.read()
			self.channelsPerPixel = pngImageInfo[3]['planes']
			self.rgbaPaletteArray = pngImage.palette( alpha='force' ) # 1D list
			self.paletteColorCount = len( self.rgbaPaletteArray )

			# Determine palette encoding. This and the following operation (collecting image/palette data) 
			# must be done before closing the file buffer due to a generator function.
			if self.paletteType == None:
				self.determinePaletteEncoding( pngImageInfo[3] )

			print( 'new palette generated, of size: ' + str(self.paletteColorCount) )
			print( 'new palette type: ' + str(self.paletteType) )

			# Collect the image data (multidimensional array of indices)
			self.collectImageDataIndices( pngImageInfo[2] )
			
			fileBuffer.close()

		else:
			print( 'pngquant exit code: ' + str( exitCode ) )
			print( 'pngquant error: ' + cmdOutput.strip() )
			raise SystemError( 'An error occurred during palette generation.' )

	def collectImageDataIndices( self, paletteData ):

		""" Flushes current image data and repopulates it with indices into the current palette. """

		self.imageDataArray = []
		self.rgbaPixelArray = []

		for row in paletteData:
			for index in row:
				self.imageDataArray.append( index )
				self.rgbaPixelArray.append( self.rgbaPaletteArray[index] )

	def fromPngFile( self ):
		pngImage = png.Reader( filename=self.filepath )

		# If the file is not a valid PNG, the png module will raise a FormatError exception.
		try:
			pngImageInfo = pngImage.read()
		except png.ChunkError as err:
			# This may be due to a bug in GIMP (Details: https://smashboards.com/threads/dat-texture-wizard-current-version-6-0.373777/post-24014857)
			# Attempt to re-read the file, being more lenient with errors
			if 'Checksum error in iCCP chunk' in str( err ): # Expecting a string like "ChunkError: Checksum error in iCCP chunk: 0xE94B8A86 != 0xEDF8F065."
				print( 'Encountered a bad iCCP chunk. Ignoring it.' )
				pngImageInfo = pngImage.read( lenient=True ) # With lenient=True, checksum failures will raise warnings rather than exceptions
			else:
				print( 'The TPL codec ran into an unrecognized error reading the given file.' )
				raise Exception( err )
		except:
			raise

		self.width, self.height = pngImageInfo[0], pngImageInfo[1]
		self.channelsPerPixel = pngImageInfo[3]['planes']

		# Arrange the image data into a 1D list, with one tuple for each pixel.
		if 'palette' in pngImageInfo[3]:

			self.rgbaPaletteArray = pngImage.palette( alpha='force' ) # 1D list
			self.originalPaletteColorCount = len( self.rgbaPaletteArray ) # Useful to remember in case the palette is regenerated.
			self.paletteColorCount = self.originalPaletteColorCount

			# If the palette is too large, generate a smaller one
			if self.paletteColorCount > self.maxPaletteColors:
				self.generatePalette()
				self.paletteRegenerated = True

			elif self.paletteType == None:
				self.determinePaletteEncoding( pngImageInfo[3] )

			# Collect the image data (multidimensional array of indices)
			if len( self.imageDataArray ) == 0:
				self.collectImageDataIndices( pngImageInfo[2] )

		# If a palette is not present, but the intended encoding needs one, generate it
		elif self.imageType in ( 8, 9, 10 ):
			self.generatePalette()

		# Collect pixels from the image data into the image data pixel array
		else:
			lxrange = range # This localizes the range function, so that each call doesn't have to look through the local, then global, and then built-in function lists.

			for row in pngImageInfo[2]:
				for pixelValues in lxrange( 0, len(row), self.channelsPerPixel ):
					# Create a tuple for each pixel to contain all of its values. (May be just one luminosity value (L), luminosity+alpha (LA), RGB, or RGBA.)
					values = row[pixelValues:pixelValues+self.channelsPerPixel]
					if self.channelsPerPixel == 1:
						pixel = ( values, values, values, 255 )
					elif self.channelsPerPixel == 2:
						pixel = ( values[0], values[0], values[0], values[1] )
					elif self.channelsPerPixel == 3:
						pixel = ( values[0], values[1], values[2], 255 )
					else:
						pixel = ( values[0], values[1], values[2], values[3] )
						
					self.imageDataArray.append( pixel )

			self.rgbaPixelArray = self.imageDataArray

	def fromTplFile( self ):
		# Open the file and get the image attributes and pixel data.
		with open( self.filepath , 'rb' ) as binaryFile:
			if binaryFile.read(4).encode('hex') != '0020af30': raise IOError( "The TPL file has an invalid signature." )
			binaryFile.seek( 0xC )
			imageHeaderAddress = int( binaryFile.read(4).encode('hex'), 16 ) # Todo: use unpack to unpack several values at once instead
			paletteHeaderAddress = int( binaryFile.read(4).encode('hex'), 16 )
			
			binaryFile.seek( paletteHeaderAddress )
			self.paletteColorCount = int( binaryFile.read(2).encode('hex'), 16 )
			binaryFile.seek( 4, 1 ) # Seek from the current location (option from second argument).
			self.paletteType = int( binaryFile.read(2).encode('hex'), 16 )
			paletteDataLength = self.paletteColorCount * 2 # In bytes.
			paletteDataOffset = int( binaryFile.read(4).encode('hex'), 16 )
			binaryFile.seek( paletteDataOffset )
			self.encodedPaletteData = bytearray( binaryFile.read(paletteDataLength) )

			binaryFile.seek( imageHeaderAddress )
			self.height = int( binaryFile.read(2).encode('hex'), 16 )
			self.width = int( binaryFile.read(2).encode('hex'), 16 )
			self.imageType = int( binaryFile.read(4).encode('hex'), 16 )
			imageDataOffset = int( binaryFile.read(4).encode('hex'), 16 )

			binaryFile.seek( imageDataOffset )
			self.encodedImageData = bytearray( binaryFile.read() )

	#def fromPilImage( self, ):

	@staticmethod # This allows this function to be called externally from this class, without initializing it. e.g. CodecBase.parseFilename()
	def parseFilename( filepath ): # Returns ( textureType, offset, sourceFile ), or empty strings if these are not found.
		filename = os.path.basename( filepath ) # The filepath argument could also just be a file name instead.
		
		if '_' not in filename: return ( -1, -1, '' )
		else:
			def validOffset( offset ): # Accepts a string.
				offset = offset.replace( '0x', '' )
				if offset == '': return False
				return all(char in hexdigits for char in offset) # Returns Boolean

			filenameComponents = os.path.splitext( filename )[0].split('_') # Excludes file extension.
			lenFilenameComponents = len( filenameComponents )
			imageType = filenameComponents[-1]

			# Texture type validation.
			if not validOffset( imageType ): imageType = -1
			else:
				imageType = int( imageType, 16 )

				# Compensate for incorrect decimal conversion to hex (i.e. cases of _10 and _14).
				if imageType == 16: imageType = 10
				elif imageType == 20: imageType = 14

				if imageType not in [0,1,2,3,4,5,6,8,9,10,14]: imageType = -1

			# Offset validation.
			if imageType == -1 or lenFilenameComponents == 1: offset = -1
			else: 
				offset = filenameComponents[-2]
				if not offset.startswith('0x') or not validOffset( offset ): offset = -1
				else: offset = int( offset, 16 )

			# Source file validation.
			if offset == -1 or lenFilenameComponents < 3: sourceFile = ''
			else: sourceFile = filenameComponents[-3]

			return ( imageType, offset, sourceFile ) # Returns a tuple of ( int, int, str )


														# ==========================
														# -= Decoder begins here. =-
														# ==========================

class TplDecoder( CodecBase ):

	""" Converts TPL data to PNG format. Can return just the image and palette data, or create a PNG file.

		Pass a filepath to get data from a file, or pass image data (and palette data if needed) to work with 
		raw data instead. imageType and imageDimensions are also mandatory. """

	def __init__( self, filepath='', imageDimensions=(0, 0), imageType=None, paletteType=None, encodedImageData='', encodedPaletteData='', maxPaletteColors=256, paletteQuality=3 ):
		
		super( TplDecoder, self ).__init__( filepath, imageType, paletteType, maxPaletteColors, paletteQuality )
		
		self.encodedImageData = encodedImageData
		self.encodedPaletteData = encodedPaletteData
		self.width, self.height = imageDimensions
		self.pilImage = None

		# If the filepath is not empty, get the data from a file
		if filepath:
			self.readImageData()
			
			if os.path.splitext( filepath )[1].lower() == '.tpl':
				self.deblockify()

	def deblockify( self ):

		""" Removes the block structure from the TPL image format, and returns a standard/linear, row-by-row pattern of pixels,
			each as a list of RGBA, ( r, g, b, a ), tuples. """

		imageWidth, imageHeight = self.width, self.height
		imageType = self.imageType
		blockWidth, blockHeight = self.blockDimensions[ imageType ]

		# Unpack specific formats to an array of half-words for simpler processing
		if imageType in ( 3, 4, 5, 6, 10 ): # Unpack these as 2 bytes per value (half-words)
			encodedImageData = struct.unpack( '>{}H'.format(len(self.encodedImageData)/2), self.encodedImageData )
		elif imageType == 0 or imageType == 8: # Unpack these as 2 values per byte
			encodedImageData = list( chain.from_iterable((byte >> 4, byte & 0b1111) for byte in self.encodedImageData) )
		else: # These formats can work with the source data directly (the encoded data, which is a bytearray)
			encodedImageData = self.encodedImageData

		if imageType in ( 8, 9, 10 ):

			if not self.encodedPaletteData: raise noPalette('No palette provided for palette type image.')
			elif self.paletteType == None: raise missingType('No palette type was provided or determined.')

			# Turn the palette data into a dictionary for quick referencing.
			paletteCount = len( self.encodedPaletteData ) / 2
			unpackedPalette = struct.unpack( '>{}H'.format(paletteCount), self.encodedPaletteData ) # Will return a tuple of values
			
			if self.paletteType == 0: # IA8	| Alpha with transparency: AAAAAAAAIIIIIIII
				self.rgbaPaletteArray = [ (v&255, v&255, v&255, v>>8) for v in unpackedPalette ]

			elif self.paletteType == 1: # RGB565 | Color; no transparency: RRRRRGGGGGGBBBBB
				self.rgbaPaletteArray = []
				for value in unpackedPalette:
					r = ( value >> 11 ) * 8
					g = ( value >> 5 & 0b111111 ) * 4
					b = ( value & 0b11111 ) * 8
					self.rgbaPaletteArray.append( (r, g, b, 255) )

			else: # Type 2, RGB5A3 | Color, and may have shallow, 3-bit transparency
				self.rgbaPaletteArray = []
				for value in unpackedPalette:
					# Check the top-bit (bit 15) to determine the encoding
					if value & 0x8000: # Top bit is set; has no transparency
						# The bit packing format is 1RRRRRGGGGGBBBBB
						r = ( value >> 10 & 0b11111 ) * 8
						g = ( value >> 5 & 0b11111 ) * 8
						b = ( value & 0b11111 ) * 8
						self.rgbaPaletteArray.append( (r, g, b, 255) )
					else:
						# The bit packing format is 0AAARRRRGGGGBBBB
						r = ( value >> 8 & 0b1111 ) * 17
						g = ( value >> 4 & 0b1111 ) * 17
						b = ( value & 0b1111 ) * 17
						a = ( value >> 12 ) * 32
						self.rgbaPaletteArray.append( (r, g, b, a) )

			self.rgbaPixelArray = [0] * ( imageWidth * imageHeight )

		# Create an empty list matching the number of pixels, so new values can be assigned to it non-linearly.
		self.imageDataArray = [0] * ( imageWidth * imageHeight )
		readPosition = 0

		if imageType == 0:

			# I4 (Intensity 4-bit)
			# Low bit-depth grayscale without transparency
			
			for y in range( 0, imageHeight, blockHeight ): # Iterates the image's blocks, vertically. (last argument is step size)
				for x in range( 0, imageWidth, blockWidth ): # Iterates the image's blocks, horizontally.
					for row in range( y, y + blockHeight ): # Iterates block rows, while tracking absolute image row position.
						for column in range( x, x + blockWidth ): # Iterates block columns/x-axis, while tracking absolute image column position.

							# Skip pixels outside the image's visible area
							if row >= imageHeight or column >= imageWidth:
								readPosition += 1
								continue

							# Decode the pixel value | IIII
							intensity = encodedImageData[readPosition] * 0x11
							self.imageDataArray[row * imageWidth + column] = ( intensity, intensity, intensity, 255 )
							readPosition += 1

		elif imageType == 1:

			# I8 (Intensity 8-bit)
			# Grayscale without transparency

			for y in range( 0, imageHeight, blockHeight ): # Iterates the image's blocks, vertically. (last argument is step size)
				for x in range( 0, imageWidth, blockWidth ): # Iterates the image's blocks, horizontally.
					for row in range( y, y + blockHeight ): # Iterates block rows, while tracking absolute image row position.
						for column in range( x, x + blockWidth ): # Iterates block columns/x-axis, while tracking absolute image column position.

							# Skip pixels outside the image's visible area
							if row >= imageHeight or column >= imageWidth:
								readPosition += 1
								continue

							# Decode the pixel value | IIIIIIII
							intensity = encodedImageData[readPosition]
							self.imageDataArray[row * imageWidth + column] = ( intensity, intensity, intensity, 255 )
							readPosition += 1

		elif imageType == 2:

			# IA4 (Intensity Alpha 4-bit)
			# Low bit-depth grayscale with transparency

			for y in range( 0, imageHeight, blockHeight ): # Iterates the image's blocks, vertically. (last argument is step size)
				for x in range( 0, imageWidth, blockWidth ): # Iterates the image's blocks, horizontally.
					for row in range( y, y + blockHeight ): # Iterates block rows, while tracking absolute image row position.
						for column in range( x, x + blockWidth ): # Iterates block columns/x-axis, while tracking absolute image column position.

							# Skip pixels outside the image's visible area
							if row >= imageHeight or column >= imageWidth:
								readPosition += 1
								continue

							# Decode the pixel value | AAAAIIII
							pixelValue = encodedImageData[readPosition]
							intensity = ( pixelValue & 0b1111 ) * 0x11
							self.imageDataArray[row * imageWidth + column] = ( intensity, intensity, intensity, ( pixelValue >> 4 ) * 0x11 )
							readPosition += 1

		elif imageType == 3:

			# IA8 (Intensity Alpha 8-bit). This is also type 0 for palettes
			# Grayscale with transparency

			for y in range( 0, imageHeight, blockHeight ): # Iterates the image's blocks, vertically. (last argument is step size)
				for x in range( 0, imageWidth, blockWidth ): # Iterates the image's blocks, horizontally.
					for row in range( y, y + blockHeight ): # Iterates block rows, while tracking absolute image row position.
						for column in range( x, x + blockWidth ): # Iterates block columns/x-axis, while tracking absolute image column position.

							# Skip pixels outside the image's visible area
							if row >= imageHeight or column >= imageWidth:
								readPosition += 1
								continue

							# Decode the pixel value | AAAAAAAAIIIIIIII
							pixelValue = encodedImageData[readPosition]
							intensity = pixelValue & 0b11111111
							self.imageDataArray[row * imageWidth + column] = ( intensity, intensity, intensity, pixelValue >> 8 )
							readPosition += 1

		elif imageType == 4:

			# RGB565. This is also type 1 for palettes, and used in CMPR
			# Low bit-depth color without transparency

			for y in range( 0, imageHeight, blockHeight ): # Iterates the image's blocks, vertically. (last argument is step size)
				for x in range( 0, imageWidth, blockWidth ): # Iterates the image's blocks, horizontally.
					for row in range( y, y + blockHeight ): # Iterates block rows, while tracking absolute image row position.
						for column in range( x, x + blockWidth ): # Iterates block columns/x-axis, while tracking absolute image column position.

							# Skip pixels outside the image's visible area
							if row >= imageHeight or column >= imageWidth:
								readPosition += 1
								continue

							# Decode the pixel value | RRRRRGGGGGGBBBBB
							pixelValue = encodedImageData[readPosition]
							r = ( pixelValue >> 11 ) * 8
							g = ( pixelValue >> 5 & 0b111111 ) * 4
							b = ( pixelValue & 0b11111 ) * 8
							self.imageDataArray[row * imageWidth + column] = ( r, g, b, 255 )
							readPosition += 1

		elif imageType == 5:

			# RGB5A3. This is also type 2 for palettes
			# Low bit-depth color with or without transparency (based on top bit)

			for y in range( 0, imageHeight, blockHeight ): # Iterates the image's blocks, vertically. (last argument is step size)
				for x in range( 0, imageWidth, blockWidth ): # Iterates the image's blocks, horizontally.
					for row in range( y, y + blockHeight ): # Iterates block rows, while tracking absolute image row position.
						for column in range( x, x + blockWidth ): # Iterates block columns/x-axis, while tracking absolute image column position.

							# Skip pixels outside the image's visible area
							if row >= imageHeight or column >= imageWidth:
								readPosition += 1
								continue

							# Decode the pixel value; check the top-bit (bit 15) to determine the encoding
							pixelValue = encodedImageData[readPosition]
							if pixelValue & 0x8000: # Top bit is set; has no transparency
								# The bit packing format is 1RRRRRGGGGGBBBBB
								r = ( pixelValue >> 10 & 0b11111 ) * 8
								g = ( pixelValue >> 5 & 0b11111 ) * 8
								b = ( pixelValue & 0b11111 ) * 8
								a = 255
							else:
								# The bit packing format is 0AAARRRRGGGGBBBB
								r = ( pixelValue >> 8 & 0b1111 ) * 17
								g = ( pixelValue >> 4 & 0b1111 ) * 17
								b = ( pixelValue & 0b1111 ) * 17
								a = ( pixelValue >> 12 ) * 32
							self.imageDataArray[row * imageWidth + column] = ( r, g, b, a )
							readPosition += 1

		elif imageType == 6:

			# RGBA8 / RGBA32
			# Full color with transparency

			for y in range( 0, imageHeight, blockHeight ): # Iterates the image's blocks, vertically. (last argument is step size)
				for x in range( 0, imageWidth, blockWidth ): # Iterates the image's blocks, horizontally.
					for row in range( y, y + blockHeight ): # Iterates block rows, while tracking absolute image row position.
						for column in range( x, x + blockWidth ): # Iterates block columns/x-axis, while tracking absolute image column position.

							# Skip pixels outside the image's visible area
							if row >= imageHeight or column >= imageWidth:
								readPosition += 1
								continue

							# Decode the pixel value. Fetch two half-words for all of the values
							# Half-word 1: AAAAAAAARRRRRRRR 	Half-word 2: GGGGGGGGBBBBBBBB
							alphaAndRed = encodedImageData[readPosition]
							greenAndBlue = encodedImageData[readPosition+16] # Grabbing from 32 bytes ahead, after the block of AR data
							r = alphaAndRed & 0b11111111
							g = greenAndBlue >> 8
							b = greenAndBlue & 0b11111111
							a = alphaAndRed >> 8
							self.imageDataArray[row * imageWidth + column] = ( r, g, b, a )
							readPosition += 1

					if row - y == 3 and column - x == 3: 
						# Skip reading the next 32 bytes, because it's the green and blue color data to pixels that have already been read above.
						readPosition += 16

		elif imageType == 8:

			# Uses a color palette, which may use IA8, RGB565, or RGB5A3
			# Uses 4 bits per palette index (max of 16 colors in the palette)

			for y in range( 0, imageHeight, blockHeight ): # Iterates the image's blocks, vertically. (last argument is step size)
				for x in range( 0, imageWidth, blockWidth ): # Iterates the image's blocks, horizontally.
					for row in range( y, y + blockHeight ): # Iterates block rows, while tracking absolute image row position.
						for column in range( x, x + blockWidth ): # Iterates block columns/x-axis, while tracking absolute image column position.

							# Skip pixels outside the image's visible area
							if row >= imageHeight or column >= imageWidth:
								readPosition += 1
								continue

							# Decode the pixel value | IIII
							paletteIndex = encodedImageData[readPosition]
							linearPixelIndex = row * imageWidth + column
							self.imageDataArray[linearPixelIndex] = paletteIndex
							self.rgbaPixelArray[linearPixelIndex] = self.rgbaPaletteArray[paletteIndex]
							readPosition += 1

		elif imageType == 9 or imageType == 10:
			
			# Uses a color palette, which may use IA8, RGB565, or RGB5A3
			# The difference between types 9 and 10 is the max size of the palette;
			# Type 9 uses 8 bits per palette index (max of 256 colors in the palette)
			# Type 10 uses 14 bits per palette index (max of 16,384 colors in the palette)

			for y in range( 0, imageHeight, blockHeight ): # Iterates the image's blocks, vertically. (last argument is step size)
				for x in range( 0, imageWidth, blockWidth ): # Iterates the image's blocks, horizontally.
					for row in range( y, y + blockHeight ): # Iterates block rows, while tracking absolute image row position.
						for column in range( x, x + blockWidth ): # Iterates block columns/x-axis, while tracking absolute image column position.

							# Skip pixels outside the image's visible area
							if row >= imageHeight or column >= imageWidth:
								readPosition += 1
								continue
							
							linearPixelIndex = row * imageWidth + column
							paletteIndex = encodedImageData[readPosition]
							self.imageDataArray[linearPixelIndex] = paletteIndex
							self.rgbaPixelArray[linearPixelIndex] = self.rgbaPaletteArray[paletteIndex]
							readPosition += 1

		else:
			
			# Type 14 (CMPR)
			# Compressed image format, using micro-palettes and RGB565 for color data

			lint = int # Create a local instance of these two functions for quicker lookups
			lround = round
			for y in range( 0, imageHeight, 8 ): # Iterates the image's blocks, vertically. (last argument is step size)
				for x in range( 0, imageWidth, 8 ): # Iterates the image's blocks, horizontally.

					# CMPR textures actually have sub-blocks. 4 sub-blocks in each block. iterate over those here.
					for subBlockRow in range( 2 ): # Iterates sub-block rows
						for subBlockColumn in range( 2 ): # Iterates sub-block columns/x-axis

							rowTotal = 4 * subBlockRow + y
							columnTotal = 4 * subBlockColumn + x

							# Get the first two palette color values
							p0Value = struct.unpack( '>H', encodedImageData[readPosition:readPosition+2] )[0]
							p1Value = struct.unpack( '>H', encodedImageData[readPosition+2:readPosition+4] )[0]

							# Decode the first two palette entries, which are in RGB565 (RRRRRGGGGGGBBBBB)
							RGBA0 = ( ( p0Value >> 11 ) * 8, ( p0Value >> 5 & 0b111111 ) * 4, ( p0Value & 0b11111 ) * 8, 255 )
							RGBA1 = ( ( p1Value >> 11 ) * 8, ( p1Value >> 5 & 0b111111 ) * 4, ( p1Value & 0b11111 ) * 8, 255 )
							
							# Define the second two palette color entries
							if p0Value > p1Value:
								RGBA2 = ( lint(lround((RGBA0[0] * 2 + RGBA1[0]) /3.0)), lint(lround((RGBA0[1] * 2 + RGBA1[1]) /3.0)), lint(lround((RGBA0[2] * 2 + RGBA1[2]) /3.0)), 255 )
								RGBA3 = ( lint(lround((RGBA0[0] + RGBA1[0] * 2) /3.0)), lint(lround((RGBA0[1] + RGBA1[1] * 2) /3.0)), lint(lround((RGBA0[2] + RGBA1[2] * 2) /3.0)), 255 )
							else:
								RGBA2 = ( lint(lround((RGBA0[0] + RGBA1[0]) /2.0)), lint(lround((RGBA0[1] + RGBA1[1]) /2.0)), lint(lround((RGBA0[2] + RGBA1[2]) /2.0)), 255 )
								RGBA3 = ( 0, 0, 0, 0 )

							subBlockPalette = ( RGBA0, RGBA1, RGBA2, RGBA3 )
							readPosition += 4
							
							for row in range( rowTotal, rowTotal + 4 ):
								# Skip rows that aren't part of the visible dimensions
								if row >= imageHeight:
									readPosition += 1
									continue

								indicesByte = encodedImageData[readPosition]
								readPosition += 1

								# bitsIndex = 6
								# for column in range( columnTotal, columnTotal + 4 ):
								# 	if column >= imageWidth: # Skip columns that aren't part of the visible dimensions
								# 		bitsIndex -= 2
								# 		continue

								# 	pixIndex = indicesByte >> bitsIndex & 0b11
								# 	self.imageDataArray[row * imageWidth + column] = subBlockPalette[pixIndex]
								# 	bitsIndex -= 2

								# Could use another loop for the following, but we can easily omit it in this case to reduce overhead and improve performance
								linearPixelIndex = row * imageWidth + columnTotal

								if columnTotal >= imageWidth: continue
								self.imageDataArray[linearPixelIndex] = subBlockPalette[indicesByte >> 6 & 0b11]
								
								if columnTotal + 1 >= imageWidth: continue
								self.imageDataArray[linearPixelIndex + 1] = subBlockPalette[indicesByte >> 4 & 0b11]

								if columnTotal + 2 >= imageWidth: continue
								self.imageDataArray[linearPixelIndex + 2] = subBlockPalette[indicesByte >> 2 & 0b11]
								
								if columnTotal + 3 >= imageWidth: continue
								self.imageDataArray[linearPixelIndex + 3] = subBlockPalette[indicesByte & 0b11]

		# The rgbaPixelArray should be present in all cases (already created above if this is a paletted texture).
		if imageType not in ( 8, 9, 10 ):
			self.rgbaPixelArray = self.imageDataArray

	@staticmethod # This allows this function to be called externally from this class, without initializing it. e.g. TplDecoder.decodeColor()
	def decodeColor( imageType, hexEntry, decodeForPalette=False ):
		pixelValue = int( hexEntry, 16 )

		if decodeForPalette:
			imageType += 3 # These formats are used for both image and palette color data.

		# I4 (Intensity 4-bit)
		# Low bit-depth grayscale without transparency
		# IIII
		if imageType == 0:
			r = g = b = pixelValue * 0x11
			a = 255

		# I8 (Intensity 8-bit)
		# Grayscale without transparency
		# IIIIIIII
		elif imageType == 1:
			r = g = b = pixelValue
			a = 255

		# IA4 (Intensity Alpha 4-bit)
		# Low bit-depth grayscale with transparency
		# AAAAIIII
		elif imageType == 2:
			r = g = b = ( pixelValue & 0b1111 ) * 0x11
			a = ( pixelValue >> 4 ) * 0x11

		# IA8 (Intensity Alpha 8-bit) This is type 0 for palettes
		# Grayscale with transparency
		# AAAAAAAAIIIIIIII
		elif imageType == 3:
			r = g = b = pixelValue & 0b11111111
			a = pixelValue >> 8

		# RGB565 (this is type 1 for palettes, and used for CMPR)
		# Low bit-depth color without transparency
		# RRRRRGGGGGGBBBBB
		elif imageType == 4:
			r = ( pixelValue >> 11 ) * 8
			g = ( pixelValue >> 5 & 0b111111 ) * 4
			b = ( pixelValue & 0b11111 ) * 8
			a = 255

		# RGB5A3 (this is type 2 for palettes)
		# Low bit-depth color with or without transparency (based on top bit)
		elif imageType == 5:
			# Check the top-bit (bit 15) to determine the encoding
			if pixelValue & 0x8000: # Top bit is set; has no transparency
				# The bit packing format is 1RRRRRGGGGGBBBBB
				r = ( pixelValue >> 10 & 0b11111 ) * 8
				g = ( pixelValue >> 5 & 0b11111 ) * 8
				b = ( pixelValue & 0b11111 ) * 8
				a = 255
			else:
				# The bit packing format is 0AAARRRRGGGGBBBB
				r = ( pixelValue >> 8 & 0b1111 ) * 17
				g = ( pixelValue >> 4 & 0b1111 ) * 17
				b = ( pixelValue & 0b1111 ) * 17
				a = ( pixelValue >> 12 ) * 32

		# RGBA8 / RGBA32
		# Full color with transparency
		# AAAAAAAARRRRRRRRGGGGGGGGBBBBBBBB (Note that in the file, the binary data doesn't naturally appear in this sequence.)
		elif imageType == 6:
			r = pixelValue >> 16 & 0b11111111
			g = pixelValue >> 8 & 0b11111111
			b = pixelValue & 0b11111111
			a = pixelValue >> 24

		else:
			raise TypeError( 'This image type is unsupported: ' + str(imageType) + '.' )

		return ( r, g, b, a )

	def createPngFile( self, savePath, creator="DRGN's TPL Codec" ):

		imageFormats = { 0:'I4', 1:'I8', 2:'IA4', 3:'IA8', 4:'RGB565', 5:'RGB5A3', 6:'RGBA8', 8:'CI4', 9:'CI8', 10:'CI14x2', 14:'CMPR' }

		if self.paletteType == None: originalPaletteType = 'N-A'
		else: originalPaletteType = imageFormats[self.paletteType + 3]

		metaData = { 'Original image format': imageFormats[self.imageType], 
					 'Original palette format': originalPaletteType,
					 'Creator': creator }

		if len( self.rgbaPaletteArray ) != 0: #palette = self.rgbaPaletteArray
			# A palette exists. Convert it from a dictionary to a list of tuples.

			with open( savePath, 'wb' ) as newFile:
				pngData = png.Writer( width=self.width, height=self.height, palette=self.rgbaPaletteArray )
				pngData.set_text( metaData )
				pngData.write_array( newFile, self.imageDataArray )
		else: 
			# Convert the pixel array to flat row flat pixel format.
			flattenedArray = []
			for pixel in self.rgbaPixelArray:
				flattenedArray.append( pixel[0] )
				flattenedArray.append( pixel[1] )
				flattenedArray.append( pixel[2] )
				flattenedArray.append( pixel[3] )

			with open( savePath, 'wb' ) as newFile:
				pngData = png.Writer( width=self.width, height=self.height, alpha=True )
				pngData.set_text( metaData )
				pngData.write_array( newFile, flattenedArray )


														# ==========================
														# -= Encoder begins here. =-
														# ==========================

class TplEncoder( CodecBase ):

	""" Converts PNG data to TPL format. Can return just the TPL image and palette data, or create a TPL file.

		Pass a filepath, a PIL image, or raw image and/or palette data.
		The arguments imageDataArray and rgbaPaletteArray expect a 1D list, where each pixel is an RGBA tuple. """

	def __init__( self, filepath='', pilImage=None, imageType=None, paletteType=None, imageDataArray=None, rgbaPaletteArray=None, maxPaletteColors=256, paletteQuality=3 ):
		
		super( TplEncoder, self ).__init__( filepath, imageType, paletteType, maxPaletteColors, paletteQuality )

		# Set data arrays to what's given, or initialize with an empty list
		self.imageDataArray = imageDataArray or [] # Not set in the __init__ declaration because [] is mutable, and would not be created anew each time
		self.rgbaPaletteArray = rgbaPaletteArray or []
		self.pilImage = pilImage

		# Initialize data from a PIL image, if provided
		if pilImage:
			# Convert to RGBA, and collect width/height and image data
			pilImage = pilImage.convert( 'RGBA' )
			self.width, self.height = pilImage.size
			self.imageDataArray = pilImage.getdata()

			# Collect palette data or create one, if needed
			if imageType in ( 8, 9, 10 ):
				self.rgbaPaletteArray = pilImage.getpalette()

				if not self.rgbaPaletteArray:
					self.generatePalette()

		# If the filepath is not empty, get image data from a file
		elif filepath != '':
			self.readImageData()

			if os.path.splitext( filepath )[1].lower() == '.png':
				self.blockify()

	# def resize( self, dimensions ):
	# 	# Decode the image first if it's still in only TPL format
	# 	if self.rgbaPixelArray == []:
	# 		if self.encodedImageData:
	# 			newImg = TplDecoder( '', (self.width, self.height), self.imageType, self.paletteType, self.encodedImageData, self.encodedPaletteData )
	# 		elif self.filepath:
	# 			newImg = TplDecoder( self.filepath, (self.width, self.height), self.imageType, self.paletteType )
	# 			if self.filepath.endswith( 'png' )
	# 			self.encodedImageData = newImg.encodedImageData
	# 			self.encodedPaletteData = newImg.encodedPaletteData
	# 		else: raise SystemError( 'Invalid input; must pass filepath or image data (and palette if required).' )

	# 		newImg.deblockify() # This decodes the image data, to create an rgbaPixelArray.
	# 		self.imageDataArray = newImg.imageDataArray # May be palette indices or RGBA tuples.
	# 		self.rgbaPixelArray = newImg.rgbaPixelArray # Will always be RGBA tuples, even for paletted images.
	# 		self.width, self.height = newImg.width, newImg.height
	# 		self.rgbaPaletteArray = newImg.rgbaPaletteArray
	# 		self.originalPaletteColorCount = newImg.originalPaletteColorCount
	# 		self.paletteColorCount = newImg.paletteColorCount
	# 		self.paletteRegenerated = newImg.paletteRegenerated

	# 	# Resize the image data
	# 	byteStringData = ''.join([chr(pixel[0])+chr(pixel[1])+chr(pixel[2])+chr(pixel[3]) for pixel in self.rgbaPixelArray])
	# 	resizedImage = Image.frombytes( 'RGBA', (self.width, self.height), byteStringData )
	# 	resizedImage.resize( dimensions, resample=Image.LANCZOS )
	# 	self.width, self.height = dimensions[0], dimensions[1]
	# 	resizedImage.show()

	def blockify( self ):

		""" Creates a block structure for the TPL image, with the pixel data encoded in its respective format. """

		imageData = self.imageDataArray
		imageWidth, imageHeight = self.width, self.height
		imageType = self.imageType
		blockWidth, blockHeight = self.blockDimensions[ imageType ]

		if imageType == 8 or imageType == 9 or imageType == 10:
			isPalettedImage = True

			if len( self.rgbaPaletteArray ) == 0: raise noPalette( 'No palette provided for palette type image.' )
			if self.paletteType == None: raise missingType( 'No palette type was provided.' )

			# Convert the palette data from RGBA to the TPL's encoding.
			self.encodedPaletteData = bytearray.fromhex( ''.join([self.encodeColor( self.paletteType, paletteEntry, dataType='palette' ) for paletteEntry in self.rgbaPaletteArray]) )
		else: isPalettedImage = False

		emptyPixel = { 0:'0', 1:'00', 2:'00', 3:'0000', 4:'0000', 5:'0000', 6:'0000', 8:'0', 9:'00', 10:'0000', 14:'0' } # Type 6 pixels are actually composed of two sets of '0000'.
		encodedPixelList = []

		if imageType < 14:
			_6GnB = [] # For image type _6, this will collect the Green & Blue portions of the pixel data for each block.
			for y in range( 0, imageHeight, blockHeight ): # Iterates the image's blocks, vertically. (last arg is iteration step-size)
				for x in range( 0, imageWidth, blockWidth ): # Iterates the image's blocks, horizontally.
					for row in range( y, y + blockHeight ): # Iterates block rows, while tracking absolute image row position.
						for column in range( x, x + blockWidth ): # Iterates block columns/x-axis, while tracking absolute image column position.
							
							if row >= imageHeight or column >= imageWidth: # Checks that this isn't a pixel outside the image's visible area (which will be skipped).
								encodedPixelList.append( emptyPixel[imageType] )
								if imageType == 6: _6GnB.append( '0000' )
								continue

							elif imageType == 6: # For this type, the color data is separated. First is 32 bytes of 'ARARAR...', followed by 32 bytes of 'GBGBGB...'.
								rgbaTuple = imageData[row * imageWidth + column]
								AR, GB = self.encodeColor( imageType, rgbaTuple )
								encodedPixelList.append( AR )
								_6GnB.append( GB )

							# Just need to encode an index (number referencing a color in the palette data)
							elif isPalettedImage:
								if imageType == 8:
									encodedPixelList.append( hex(imageData[row * imageWidth + column])[2:] )
								elif imageType == 9:
									encodedPixelList.append( hex(imageData[row * imageWidth + column])[2:].zfill(2) )

							else:
								rgbaTuple = imageData[row * imageWidth + column]
								encodedPixelList.append( self.encodeColor( imageType, rgbaTuple ) )

					if len( _6GnB ) == 16:
						# Once all of the Alpha and Red color data has been saved to the block, append the collected Green and Blue data to finish it.
						encodedPixelList.extend( _6GnB )
						_6GnB = []

			self.encodedImageData = bytearray.fromhex( ''.join(encodedPixelList) )

		else: # For image type 14 (CMPR)
			#raise TypeError( 'CMPR encoding is unsupported.' )
			tic = time.time()

			self.encodedImageData = bytearray()

			for y in range( 0, imageHeight, 8 ): # Iterates the image's blocks, vertically. (last argument is step size)
				for x in range( 0, imageWidth, 8 ): # Iterates the image's blocks, horizontally.

					# CMPR textures actually have sub-blocks. 4 sub-blocks in each block. iterate over those here.
					for subBlockRow in range( 2 ): # Iterates sub-block rows
						for subBlockColumn in range( 2 ): # Iterates sub-block columns/x-axis

							rowTotal = 4 * subBlockRow + y
							columnTotal = 4 * subBlockColumn + x
							blockPixels = []

							# Get the original 16 pixels/colors for this block
							for row in range( rowTotal, rowTotal + 4 ):
								for column in range( columnTotal, columnTotal + 4 ):
									# Skip pixels that are outside the image's visible area
									if row >= imageHeight or column >= imageWidth:
										continue

									pixel = imageData[row * imageWidth + column] # An RGBA tuple
									blockPixels.append( pixel )

							# Determine new colors to use as a palette to represent the pixels collected above
							p1Value, p2Value, indices, useTransparency = self.quantizeCMPR( blockPixels )

							# Encode the two palette entries, which should be in RGB565 (RRRRRGGGGGGBBBBB) format
							# p1Value = p1[0]/8 << 11 | p1[1]/4 << 5 | p1[2]/8
							# p2Value = p2[0]/8 << 11 | p2[1]/4 << 5 | p2[2]/8

							# # Store the above into 8 bytes
							# if useTransparency:
							# 	# Place the smaller palette entry value first
							# 	if p1Value > p2Value:
							# 		self.encodedImageData.extend( struct.pack('>HHI', p2Value, p1Value, indices) )
							# 	else:
							# 		self.encodedImageData.extend( struct.pack('>HHI', p1Value, p2Value, indices) )
							# else:
							# 	# Place the larger palette entry value first
							# 	if p1Value > p2Value:
							# 		self.encodedImageData.extend( struct.pack('>HHI', p1Value, p2Value, indices) )
							# 	else:
							self.encodedImageData.extend( struct.pack('>HHI', p1Value, p2Value, indices) )
			
			toc = time.time()
			print( 'encoding time: ' + str(toc-tic) )

	@staticmethod # This allows this function to be called externally from this class, without initializing it.
	def encodeColor( imageType, pixel, dataType='image' ):
		if dataType == 'palette': imageType += 3 # These formats are used for both image and palette color data.

		if len(pixel) == 4: r, g, b, a = pixel
		elif len(pixel) == 3:
			r, g, b = pixel
			a = 255
		elif len(pixel) == 2:
			r, a = pixel
			g = b = r
		else:
			r = pixel[0]
			g = b = r
			a = 255

		# I4 (Intensity 4-bit)
		if imageType == 0: hexPixel = hex( r / 0x11 )[2:] # Should only ever be 1 character (1 nibble).

		# I8 (Intensity 8-bit)
		elif imageType == 1: hexPixel = hex( r )[2:].zfill(2)

		# IA4 (Intensity Alpha 4-bit)
		elif imageType == 2: hexPixel = hex( a / 0x11 )[2:] + hex( r / 0x11 )[2:]

		# IA8 (Intensity Alpha 8-bit. This is type 0 for palettes)
		elif imageType == 3: hexPixel = hex( a )[2:].zfill(2) + hex( r )[2:].zfill(2)

		# RGB565 (this is type 1 for palettes, and for CMPR)
		elif imageType == 4: # RRRRRGGGGGGBBBBB
			hexPixel = hex( r/8 << 11 | g/4 << 5 | b/8 )[2:].zfill(4)

		# RGB5A3 (this is type 2 for palettes)
		elif imageType == 5:
			if a < 224: 	# 0AAARRRRGGGGBBBB				(224 is the limit because 1 alpha unit is 32 steps here.)
				# Encode using a 3 bit alpha channel (top-bit will be 0)
				hexPixel = hex( a/32 << 12 | r/0x11 << 8 | g/0x11 << 4 | b/0x11 )[2:].zfill(4)
			else: 			# 1RRRRRGGGGGBBBBB
				# Encode without an alpha channel (setting the top-bit to 1)
				hexPixel = hex( 0b1000000000000000 | r/8 << 10 | g/8 << 5 | b/8 )[2:] # No zfill required, courtesy of Top-bit
		
		# RGBA8 / RGBA32
		elif imageType == 6:
			hexPixel = ( hex( a )[2:].zfill(2) + hex( r )[2:].zfill(2), hex( g )[2:].zfill(2) + hex( b )[2:].zfill(2) )

		else:
			raise TypeError( 'This image type is unsupported: ' + str(imageType) + '.' )

		return hexPixel

	def quantizeCMPR( self, sourceColors ):

		colors = sourceColors[:] # Copy the list to not modify the original

		pointCount = len( colors )
		distance = -1
		maxDistance = 0
		p1Index = -1
		p2Index = -1
		useTransparency = False
		pixelsToIgnore = set()
		
		# Calculate all pairwise distances between the colors in the given colorspace
		for i in range( pointCount ):
			p_1 = colors[i]

			if p_1[3] < 128:
				useTransparency = True
				
				# Ignore sufficiently invisible pixels (~ 90% transparent)
				if p_1[3] < 26:
					pixelsToIgnore.add( p_1 )
					continue

			for j in range( i+1, pointCount ):
				#p_1 = colors[i]
				p_2 = colors[j]

				# Check the alpha channel for transparent pixels
				#if p_1[3] < 128 or p_2[3] < 128:
				if p_2[3] < 128:
					useTransparency = True

					# Ignore sufficiently invisible pixels (~ 90% transparent)
					# if p_1[3] < 26:
					# 	pixelsToIgnore.append( i )
					# 	continue
					if p_2[3] < 26:
						pixelsToIgnore.add( p_2 )
						continue

				#distance = math.sqrt( (p_1[0] - p_2[0])**2 + (p_1[1] - p_2[1])**2 + (p_1[2] - p_2[2])**2 )
				distance = (p_1[0] - p_2[0])**2 + (p_1[1] - p_2[1])**2 + (p_1[2] - p_2[2])**2
				if distance > maxDistance:
					maxDistance = distance
					p1Index = i
					p2Index = j

		# Check if any disntaces were calculated and a selection of colors was made
		if maxDistance == 0:
			p1 = colors[0]
			p2 = colors[15]
			p1Value = int(p1[0])/8 << 11 | int(p1[1])/4 << 5 | int(p1[2])/8
			p2Value = int(p2[0])/8 << 11 | int(p2[1])/4 << 5 | int(p2[2])/8
			if distance == -1:
				# No distance calculations were made; all of the colors are too transparent to matter
				# All indices will point to the transparent palette entry
				#return colors[0], colors[15], 0xFFFFFFFF, useTransparency
				return p1Value, p2Value, 0xFFFFFFFF, useTransparency
			else:
				# All the pixels must be the same
				#return colors[0], colors[15], 0, useTransparency
				return p1Value, p1Value, 0, useTransparency

		# Remove the colors furthest from each other (identified above)
		p2 = colors.pop( p2Index ) # Always a larger index
		p1 = colors.pop( p1Index )

		# Exclude transparent pixels from the following searches
		# if pixelsToIgnore:
		# 	pixelsToIgnore = list( pixelsToIgnore )
		# 	if p1Index in pixelsToIgnore:
		# 		pixelsToIgnore.remove( p1Index )
		# 	if p2Index in pixelsToIgnore:
		# 		pixelsToIgnore.remove( p2Index )
		# 	pixelsToIgnore.sort( reverse=True )
		# 	for i in pixelsToIgnore:
		# 		colors.pop( i )

		# Isolate two clusters of 3 colors as rough endpoints of the occupied area of the colorspace
		distancesToP1 = []
		distancesToP2 = []
		for p in colors:
			if p in pixelsToIgnore:
				continue
			# distancesToP1.append( (p, math.sqrt((p1[0] - p[0])**2 + (p1[1] - p[1])**2 + (p1[2] - p[2])**2)) )
			# distancesToP2.append( (p, math.sqrt((p2[0] - p[0])**2 + (p2[1] - p[1])**2 + (p2[2] - p[2])**2)) )
			distancesToP1.append( (p, (p1[0] - p[0])**2 + (p1[1] - p[1])**2 + (p1[2] - p[2])**2) )
			distancesToP2.append( (p, (p2[0] - p[0])**2 + (p2[1] - p[1])**2 + (p2[2] - p[2])**2) )

		# Get the midpoints of the two groups, which gives us endpoints to draw a line through the colorspace
		if len( distancesToP1 ) >= 2:
			distancesToP1.sort( key=lambda x: x[1] )
			# p1 = np.mean( [ p1, distancesToP1[0][0], distancesToP1[1][0] ], axis=0 )
			r1 = ( p1[0] + distancesToP1[0][0][0] + distancesToP1[1][0][0] ) / 3.0
			g1 = ( p1[1] + distancesToP1[0][0][1] + distancesToP1[1][0][1] ) / 3.0
			b1 = ( p1[2] + distancesToP1[0][0][2] + distancesToP1[1][0][2] ) / 3.0
			p1 = [ r1, g1, b1 ]
		elif distancesToP1: # Just one other color/distance (len(distancesToP1) = 1)
			r1 = ( p1[0] + distancesToP1[0][0][0] ) / 2.0
			g1 = ( p1[1] + distancesToP1[0][0][1] ) / 2.0
			b1 = ( p1[2] + distancesToP1[0][0][2] ) / 2.0
			p1 = [ r1, g1, b1 ]

		if len( distancesToP2 ) >= 2:
			# Sort the above lists to find the colors closest to p1 and p2
			distancesToP2.sort( key=lambda x: x[1] )
			# p2 = np.mean( [ p2, distancesToP2[0][0], distancesToP2[1][0] ], axis=0 )
			r2 = ( p2[0] + distancesToP2[0][0][0] + distancesToP2[1][0][0] ) / 3.0
			g2 = ( p2[1] + distancesToP2[0][0][1] + distancesToP2[1][0][1] ) / 3.0
			b2 = ( p2[2] + distancesToP2[0][0][2] + distancesToP2[1][0][2] ) / 3.0
			p2 = [ r2, g2, b2 ]
		elif distancesToP2: # Just one other color/distance (len(distancesToP2) = 1)
			r2 = ( p2[0] + distancesToP2[0][0][0] ) / 2.0
			g2 = ( p2[1] + distancesToP2[0][0][1] ) / 2.0
			b2 = ( p2[2] + distancesToP2[0][0][2] ) / 2.0
			p2 = [ r2, g2, b2 ]
		
		# Encode the two palette entries, which should be in RGB565 (RRRRRGGGGGGBBBBB) format
		p1Value = int(p1[0])/8 << 11 | int(p1[1])/4 << 5 | int(p1[2])/8
		p2Value = int(p2[0])/8 << 11 | int(p2[1])/4 << 5 | int(p2[2])/8
		
		# Interpolate the latter colors
		if useTransparency:
			# Ensure the smaller value is first
			if p1Value > p2Value:
				RGBA0 = p2
				RGBA1 = p1
				firstValue = p2Value
				secondValue = p1Value
			else:
				RGBA0 = p1
				RGBA1 = p2
				firstValue = p1Value
				secondValue = p2Value

			#p3 = (p1[0] + (1/2)*vx, p1[1] + (1/2)*vy, p1[2] + (1/2)*vz) # 1/2 interpolation
			RGBA2 = tuple(map(lambda x, y: (x + y) / 2, RGBA0, RGBA1))
			RGBA3 = ( 0, 0, 0, 0 )
			
			# Determine the pixel data (indices into the palette)
			#indices = []
			indices = 0
			bitPosition = 30
			for point in sourceColors:
				if point[3] < 128:
					#indices.append( 3 )
					indices += 3 << bitPosition
				else:
					smallestDistance = float( "inf" )
					closestPoint = -1
					for i, cp in enumerate( [RGBA0, RGBA1, RGBA2] ):
						#distance = math.sqrt((point[0]-cp[0])**2 + (point[1]-cp[1])**2 + (point[2]-cp[2])**2) # Use **0.5 instead?
						distance = (point[0]-cp[0])**2 + (point[1]-cp[1])**2 + (point[2]-cp[2])**2
						if distance < smallestDistance:
							smallestDistance = distance
							closestPoint = i
					#indices.append( closestPoint )
					indices += closestPoint << bitPosition
				bitPosition -= 2
		else:
			# Ensure the larger value is first
			if p1Value > p2Value:
				RGBA0 = p1
				RGBA1 = p2
				firstValue = p1Value
				secondValue = p2Value
			else:
				RGBA0 = p2
				RGBA1 = p1
				firstValue = p2Value
				secondValue = p1Value

			# RGBA2 = (p1[0] + (1/3)*vx, p1[1] + (1/3)*vy, p1[2] + (1/3)*vz) # 1/3 interpolation
			# RGBA3 = (p1[0] + (2/3)*vx, p1[1] + (2/3)*vy, p1[2] + (2/3)*vz) # 2/3 interpolation
			# RGBA2 = tuple(map(lambda x, y: (2*x + y) / 3, p1, p2))
			# RGBA3 = tuple(map(lambda x, y: (x + 2*y) / 3, p1, p2))
			RGBA2 = tuple(map(lambda x, y: (2*x + y) / 3, RGBA0, RGBA1))
			RGBA3 = tuple(map(lambda x, y: (x + 2*y) / 3, RGBA0, RGBA1))
			
			# Determine the pixel data (indices into the palette), and pack them into 4 bytes
			#indices = []
			indices = 0
			bitPosition = 30
			for point in sourceColors:
				smallestDistance = float( "inf" )
				closestPoint = -1
				for i, cp in enumerate( [RGBA0, RGBA1, RGBA2, RGBA3] ):
					#distance = math.sqrt((point[0]-cp[0])**2 + (point[1]-cp[1])**2 + (point[2]-cp[2])**2) # Use **0.5 instead?
					distance = (point[0]-cp[0])**2 + (point[1]-cp[1])**2 + (point[2]-cp[2])**2
					if distance < smallestDistance:
						smallestDistance = distance
						closestPoint = i
				#indices.append( closestPoint )
				indices += closestPoint << bitPosition
				bitPosition -= 2

		# Cast all channel values back to ints
		# RGBA0 = [ int(value) for value in RGBA0 ]
		# RGBA1 = [ int(value) for value in RGBA1 ]

		return firstValue, secondValue, indices, useTransparency

	def createTplFile( self, savePath='' ):

		""" Quick method to build and save a simple, single-texture TPL file. 
			See here for details on the format: http://wiki.tockdom.com/wiki/TPL_(File_Format) 
				Possible return codes:
					0: Success; no problems
					1: Error in encoding
					2: Error in saving the file """

		if not savePath:
			savePath = self.filepath[:-6] + '-2' + self.filepath[-6:-4] + '.tpl' # For a quick copy.

		# Process the image data if it has not been done yet.
		try:
			if not self.encodedImageData:
				self.blockify()
		except Exception as err:
			print( 'TPL encoding error: ' + str(err) )
			return 1

		# Encode width/height/image-type integers as hex, and pad the result to n zeros (the second parameter to 'format').
		w = "{0:0{1}X}".format( self.width, 4 )
		h = "{0:0{1}X}".format( self.height, 4 )
		iTyp = "{0:0{1}X}".format( self.imageType, 8 )

		# Construct the TPL header.
		if self.imageType == 8 or self.imageType == 9 or self.imageType == 10:

			paletteDataLength = len( self.encodedPaletteData ) # All of the palette (IA8, RGB565, and RGB5A3) types are 2 bytes per color.
			paletteColorCount = paletteDataLength / 2

			# Generate padding to the palette data, if needed
			if hex(paletteDataLength)[-1] != '0': 
				lenLSD = int(hex(paletteDataLength)[-1], 16) # Least Significant Digit of the length in hex.
				pDataPadding = "{0:0{1}X}".format(0, 32 - lenLSD*2)
			else: pDataPadding = ''
			
			paletteData = hexlify( self.encodedPaletteData ) + pDataPadding
			iHO = "{0:0{1}X}".format( len(paletteData)/2 + 0x20, 8 ) # imageHeaderOffset
			iDO = "{0:0{1}X}".format( len(paletteData)/2 + 0x50, 8 ) # imageDataOffset. 0x20 from the file/palette-data header, 0x30 from the image header & padding.
			c = "{0:0{1}X}".format( paletteColorCount, 4 )
			pType = "{0:0{1}X}".format( self.paletteType, 12 ) # 4 of these 0s are just to fill the area preceding the palette format.

			tplHeader = ('0020AF30000000010000000C' + iHO + \
						 '00000014' + c + pType +'00000020' \
						  + paletteData		# Should be padded to the nearest 0x20 \
						  + h + w + iTyp + iDO + '00000000'
						 '00000000000000010000000100000000'
						 '00000000000000000000000000000000')
		else:
			tplHeader = ('0020AF30000000010000000C00000014' # TPL File ID, Number of Image Tables entries (typically 1), Offset to Image Table....
						 '00000000' +h +w +iTyp +'00000040' 
						 '00000000000000000000000100000001'
						 '00000000000000000000000000000000')

		# testFile = ('0020AF30000000010000000C0000001400000000002000080000000E000000400000000000000000'
		# 	'000000010000000100000000000000000000000000000000CE9A4A695557FEE8AD95420855D52B0AD6BA84717'
		# 	'C7C7C7CC65884302D2D2D2DD6BA84717C7C7C7CC65884302D2D2D2DD6BA84717C7C7C7CC65884302D2D2D2DD6B'
		# 	'A84717C7C7C7CC65884302D2D2D2DCE9A8C717C7C7C56C659842F2D2D2DB5CD6D522655000000CD6D524655000000'
		# 	'C54DBC465C5C5C5CCD4CBC4625353535') # FeNr, 68Connector-Sheath (txt_0219_14.tpl)

		# Convert the hex string to a byte array and write it to a new TPL file.
		try:
			with open( savePath, 'wb' ) as newFile: 
				newFile.write( bytearray.fromhex(tplHeader) + self.encodedImageData )
			return 0

		except Exception as err:
			print( 'Error in saving TPL file: ' + str(err) )
			return 2
