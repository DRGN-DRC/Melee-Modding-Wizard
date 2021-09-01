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

""" Basic/general-purpose helper functions for any scripts. """

import os
import math
import time
import errno
import struct
import hashlib
import subprocess
import globalData
import tkMessageBox

from string import hexdigits
from collections import OrderedDict as _OrderedDict
#from guiSubComponents import CopyableMessageWindow
#import guiSubComponents

# Conversion solutions:
# 		int 			-> 		bytes objects 		struct.pack( )
# 		byte string 	-> 		int:				struct.unpack( )
# 		byte string 	-> 		hex string 			''.encode( 'hex' )
# 		bytearray 		-> 		hex string:			hexlify( input )
# 		hex string 		-> 		bytearray: 			bytearray.fromhex( input )
# 		text string 	-> 		bytearray			init bytearray, then use .extend( string ) method on it
#
# 		Note that a file object's .read() method returns a byte-string of unknown encoding, which will be 
# 		locally interpreted as it's displayed. It should be properly decoded to a standard to be operated on.
#
# 		Note 2: In python 2, bytes objects are an alias for str objects; they are not like bytearrays.


def roundTo32( x, base=32 ):
	
	""" Rounds up to nearest increment of [base] (default: 32 or 0x20). """
	
	return int( base * math.ceil(float(x) / base) )


def allAreEqual( iterator ):

	""" Checks whether all values in an array are the same. """

	iterator = iter( iterator )
	try:
		first = next( iterator )
	except StopIteration:
		return True

	return all( first == x for x in iterator )


def uHex( integer ):

	""" Quick conversion to have a 'hex()' function which displays uppercase characters. """

	if integer > -10 and integer < 10: return str( integer ) # 0x not required
	else: return '0x' + hex( integer )[2:].upper() # Twice as fast as .format


def toHex( number, padTo ):
	
	""" Casts an int to a hex string, and pads the result (zeros out)
		to n characters (nibbles), the second parameter. """
	
	return "{0:0{1}X}".format( number, padTo )


def toInt( input ):
	
	""" Converts a 1, 2, or 4 bytes or bytearray object to an unsigned integer. """

	byteLength = len( input )

	if byteLength == 1: return struct.unpack( '>B', input )[0]		# big-endian unsigned char (1 byte)
	elif byteLength == 2: return struct.unpack( '>H', input )[0]	# big-endian unsigned short (2 bytes)
	elif byteLength == 4: return struct.unpack( '>I', input )[0]	# big-endian unsigned int (4 bytes)
	else:
		raise Exception( 'Invalid number of bytes given to toInt:', byteLength )


def toBytes( input, byteLength=4, cType='' ):
	
	""" Converts an int to a bytes object of customizable size (byte/halfword/word). """

	if not cType: # Assume a big-endian unsigned value of some byte length
		if byteLength == 1: cType = '>B'		# big-endian unsigned char (1 byte)
		elif byteLength == 2: cType = '>H'		# big-endian unsigned short (2 bytes)
		elif byteLength == 4: cType = '>I'		# big-endian unsigned int (4 bytes)
		else:
			raise Exception( 'toBytes was not able to convert the ' + str(type(input)) + ' type' )

	return struct.pack( cType, input )


def validHex( offset ):

	""" Accepts a string. Returns Boolean. Whitespace will result in a False """

	offset = offset.replace( '0x', '' )
	if offset == '': return False

	return all( char in hexdigits for char in offset )


def floatToHex( input ):

	""" Converts a float value to a hexadecimal string. """
	
	#dec = Decimal( input )
	floatBytes = struct.pack( '<f', input )
	intValue = struct.unpack( '<I', floatBytes )[0]

	return '0x' + hex( intValue )[2:].upper()


def humansize( nbytes ):

	""" Rewrites file sizes for human readability. 
		e.g. 1408822364 -> 1.31 GB """
	
	if nbytes == 0: return '0 B'

	suffixes = [ 'B', 'KB', 'MB', 'GB', 'TB', 'PB' ]

	i = 0
	while nbytes >= 1024 and i < len(suffixes)-1:
		nbytes /= 1024.
		i += 1
	f = ('%.2f' % nbytes).rstrip('0').rstrip('.')

	return '%s %s' % (f, suffixes[i])


def grammarfyList( theList ):
	
	""" Converts a list to a human-readable string. For example: 
		the list [apple, pear, banana, melon] becomes the string 'apple, pear, banana, and melon' """

	if len( theList ) == 1:
		return str( theList[0] )
	elif len( theList ) == 2:
		return str( theList[0] ) + ' and ' + str( theList[1] )
	else:
		return ', '.join( theList[:-1] ) + ', and ' + str( theList[-1] )


def findAll( stringToLookIn, subString, charIncrement=2 ):
	
	""" Finds ALL instances of a string in another string, and returns their indices. """

	matches = []
	i = stringToLookIn.find( subString )
	while i >= 0:
		matches.append( i )
		i = stringToLookIn.find( subString, i + charIncrement ) # Change 2 to 1 if not going by bytes.
	return matches


def readableArray( offsetArray ):

	""" Simple function to return an array of offsets to a human readable string. 
		Also adds the 0x20 file header offset to each offset. """

	return [ uHex(0x20+offset) for offset in offsetArray ]


def openFolder( folderPath ):
	normedPath = os.path.abspath( folderPath ) # Turns relative to absolute paths, and normalizes them (switches / for \, etc.)

	if os.path.exists( normedPath ):
		os.startfile( normedPath )
	else: 
		msg( 'Could not find this folder: \n\n' + normedPath )


def createFolders( folderPath ):
	try:
		os.makedirs( folderPath )

		# Primitive failsafe to prevent race condition
		attempt = 0
		while not os.path.exists( folderPath ):
			time.sleep( .3 )
			if attempt > 10:
				raise Exception( 'Unable to create folder: ' + folderPath )
			attempt += 1

	except OSError as error: # Python >2.5
		if error.errno == errno.EEXIST and os.path.isdir( folderPath ):
			pass
		else: raise


def msg( message, title='', parent=None, warning=False, error=False ):

	""" Displays a short, windowed message to the user, or prints 
		out to console if the GUI has not been initialized. 
		May be decorated with warning/error=True. """

	if globalData.gui: # Display a pop-up message

		if not parent:
			parent = globalData.gui.root

		if error: tkMessageBox.showerror( message=message, title=title, parent=parent )
		elif warning: tkMessageBox.showwarning( message=message, title=title, parent=parent )
		else: tkMessageBox.showinfo( message=message, title=title, parent=parent )

	else: # Write to stdout
		if error: print 'ERROR! ' + message
		elif warning: print 'Warning! ' + message
		else: print message


def printStatus( message, warning=False, error=False, success=False ):

	""" Displays a short status message at the bottom of the GUI, 
		or prints out to console if the GUI has not been initialized. 
		May be decorated with warning/error/success=True. """

	if globalData.gui: # Display a pop-up message
		globalData.gui.updateProgramStatus( message, warning, error, success )

	else: # Write to stdout
		if error: print 'ERROR! ' + message
		elif warning: print 'Warning! ' + message
		else: print message


# def cmsg( *args, **kwargs ):

# 	""" Simple function to display a small, windowed message to the user, which can be selected and copied. 
# 		This will instead print out to console if the GUI has not been initialized. 
# 		With 1 argument provided, this simply displays a message with no window title. 
# 		2nd optional argument adds a window title. 
# 		3rd may be a string to change alignment (left/center/right). 
# 		4th may be a list of (buttonText, buttonCommand) tuples 
# 		5th may be a bool indicating whether the window should be modal """
	
# 	if globalData.gui:
# 		guiSubComponents.CopyableMessageWindow( globalData.gui.root, *args, **kwargs )
# 	else:
# 		if len( args ) > 1:
# 			print '\t', args[1] + ':'
# 		print args[0]


def copyToClipboard( text ):

	""" Copies the given text to the user's clipboard. """

	globalData.gui.root.clipboard_clear()
	globalData.gui.root.clipboard_append( text )


def cmdChannel( command, standardInput=None, shell=False ):
	
	""" IPC (Inter-Process Communication) to command line. Blocks (will not return until the process 
		is complete.) shell=True gives access to all shell features/commands, such dir or copy. 
		creationFlags=0x08000000 prevents creation of a console for the process. """

	process = subprocess.Popen( command, shell=shell, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=0x08000000 )
	stdoutData, stderrData = process.communicate( input=standardInput )

	if process.returncode == 0:
		return ( process.returncode, stdoutData )
	else:
		print 'IPC error (exit code {}):'.format( process.returncode )
		print stderrData
		return ( process.returncode, stderrData )


def saveAndShowTempFileData( fileData, filename ):

	""" Saves binary to a new temporary file, and opens it in the user's hex editor of choice. """

	hexEditorPath = globalData.getHexEditorPath() # Will also validate the path
	if not hexEditorPath: return # User may have canceled the prompt

	# Create the temporary file path, and any folders that might be needed
	tempFilePath = os.path.join( globalData.paths['tempFolder'], filename )
	createFolders( os.path.split(tempFilePath)[0] )

	# Save the file data to a temporary file.
	try:
		with open( tempFilePath, 'wb' ) as newFile:
			newFile.write( fileData )
	except Exception as err: # Pretty unlikely
		print 'Error creating temporary file for {}!'.format( filename )
		print err
		return

	# Open the temp file in the hex editor
	command = '"{}" "{}"'.format( hexEditorPath, tempFilePath )
	subprocess.Popen( command, stderr=subprocess.STDOUT, creationflags=0x08000000 )


def getFileMd5( filePath, blocksize=65536 ): # todo: use blake2b instead for perf boost when switching to Python3
	currentHash = hashlib.md5()

	with open( filePath, "rb" ) as targetFile:
		for block in iter(lambda: targetFile.read(blocksize), b""):
			currentHash.update(block)

	return currentHash.hexdigest()


class ListDict(_OrderedDict): # todo: need to start using to 'move_to_end' method when switching to Python 3

	# By jarydks
	# Source: https://gist.github.com/jaredks/6276032

	def __insertion(self, link_prev, key_value):
		key, value = key_value
		if link_prev[2] != key:
			if key in self:
				del self[key]
			link_next = link_prev[1]
			self._OrderedDict__map[key] = link_prev[1] = link_next[0] = [link_prev, link_next, key]
		dict.__setitem__(self, key, value)

	def insert_after(self, existing_key, key_value):
		self.__insertion(self._OrderedDict__map[existing_key], key_value)

	def insert_before(self, existing_key, key_value):
		self.__insertion(self._OrderedDict__map[existing_key][0], key_value)