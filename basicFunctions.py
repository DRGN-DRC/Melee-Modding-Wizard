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
import re
import math
import time
import json
import errno
import struct
import hashlib
import subprocess
import globalData
import tkMessageBox

from string import hexdigits
from collections import OrderedDict as _OrderedDict

from _ctypes import PyObj_FromPtr  # see https://stackoverflow.com/a/15012814/355230


# Conversion solutions:
# 		int 			-> 		bytes objects 		struct.pack( )
# 		byte string 	-> 		int					struct.unpack( )
# 		byte string 	-> 		hex string			''.encode( 'hex' )
#		bytes object	->		text string			obj.decode()
# 		bytearray 		-> 		hex string			hexlify( input )
# 		hex string 		-> 		bytearray			bytearray.fromhex( input )
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
	else: return '0x' + hex( integer )[2:].upper().rstrip( 'L' ) # Twice as fast as .format()


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


def intToRgb( integer ):

	""" Converts a single-integer, 24-bit color to an RGB tuple. """

	r = integer >> 16
	g = ( integer & 0xFF00 ) >> 8
	b = integer & 0xFF

	return ( r, g, b )


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


def dictReverseLookup( dict, value, defaultValue=None ):

	""" Looks up a key in a dictionary for a given value. 
		Returns the first match, so naturally this assumes unique values. 
		Returns None or the given default value if the value isn't found. """

	try:
		key = next( k for k, v in dict.items() if v == value )
		return key
	except:
		return defaultValue


def humansize( nbytes ):

	""" Converts a file size in bytes to a human-readable string. 
		e.g. 1408822364 -> '1.31 GB' """
	
	isNegative = False

	if nbytes == 0: return '0 B'
	elif nbytes < 0:
		isNegative = True
		nbytes = abs( nbytes )

	suffixes = [ 'B', 'KB', 'MB', 'GB', 'TB', 'PB' ]

	i = 0
	while nbytes >= 1024 and i < len(suffixes)-1:
		nbytes /= 1024.
		i += 1
	f = ('%.2f' % nbytes).rstrip('0').rstrip('.')

	if isNegative:
		f = '-' + f

	return '%s %s' % (f, suffixes[i])


def humantime( seconds ):

	""" Converts a time interval in seconds to a human-readable string. 
		e.g. 86461 -> '1 day, 1 minute, and 1 second' """

	result = []
	intervals = (
		('weeks', 604800),  # 60 * 60 * 24 * 7
		('days', 86400),    # 60 * 60 * 24
		('hours', 3600),    # 60 * 60
		('minutes', 60),
		('seconds', 1),
		)

	if seconds <= 0:
		return '0 seconds'

	for name, count in intervals:
		value = seconds // count # Floor division; rounds down to full int
		if value:
			seconds -= value * count
			if value == 1:
				name = name.rstrip('s')
			result.append( "{} {}".format(int(value), name) )

	if len( result ) == 2:
		return '{} and {}'.format( result[0], result[1] )
	else:
		commaJoined = ', '.join( result )

		# Replace the last comma and space with an 'and'
		li = commaJoined.rsplit( ', ', 1 )
		return ', and '.join( li )


def grammarfyList( theList ):
	
	""" Converts a list to a human-readable string. For example: 
		the list [apple, pear, banana] becomes the string 'apple, pear, and banana' """

	if len( theList ) == 1:
		return str( theList[0] )
	elif len( theList ) == 2:
		return str( theList[0] ) + ' and ' + str( theList[1] )
	else:
		return ', '.join( theList[:-1] ) + ', and ' + str( theList[-1] )


def removeIllegalCharacters( string, replaceChar='-' ):
	
	""" Removes characters illegal in a Windows file path. """

	return ''.join( [replaceChar if c in ( '\\', '/', ':', '*', '?', '"', '<', '>', '|' ) else c for c in string] )


def findAll( stringToLookIn, subString, charIncrement=2 ):
	
	""" Finds ALL instances of a string or bytearray in another string or bytearray, 
		and returns their indices. Use charIncrement to determine how many characters 
		(or bytes if the arguments are bytearrays) to move forward before the next match. """

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


def openFolder( folderPath, fileToSelect='', showWarnings=True ):

	""" Opens a folder for the user. Optionally, can also select/highlight a specific file in the folder, 
		using the 'fileToSelect' arg; however, using this feature is much slower. """

	folderPath = os.path.abspath( folderPath ) # Turns relative to absolute paths, and normalizes them (switches / for \, etc.)

	if not os.path.exists( folderPath ):
		if showWarnings:
			msg( 'Unable to find this folder: \n\n{}'.format(folderPath), 'Folder Not Found', globalData.gui.root, error=True )

	elif not fileToSelect: # Fast method, but cannot select files
		os.startfile( folderPath )

	elif not os.path.exists( folderPath + '\\' + fileToSelect ):
		os.startfile( folderPath )

		if showWarnings:
			msg( 'Unable to find this file: \n\n{}'.format(fileToSelect), 'File Not Found', globalData.gui.root, error=True )

	else: # Slow method, but can select/highlight items in the folder
		try:
			command = '"C:\\Windows\\explorer.exe" /select, \"{}\\{}\"'.format( folderPath, fileToSelect )
			outputStream = subprocess.check_output( command, shell=False, stderr=subprocess.STDOUT, creationflags=0x08000000 )
			errMsg = ''

		except subprocess.CalledProcessError as err:
			errMsg = 'Process exit code: {}'.format( err.returncode )
			if err.output:
				errMsg += '; {}'.format( err.output)

		except Exception as err:
			errMsg = 'IPC error; {}'.format( err )

		if errMsg and showWarnings:
			msg( 'There was an error in attempting to open this folder: "{}"\n\n{}'.format(folderPath, errMsg), globalData.gui.root, error=True )


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
		'parent' will default to the global GUI root if not provided.
		May be decorated with warning/error=True. """

	if globalData.gui: # Display a pop-up message

		# Define the parent window to appear over
		if not parent:
			parent = globalData.gui.root

		if error: tkMessageBox.showerror( message=message, title=title, parent=parent )
		elif warning: tkMessageBox.showwarning( message=message, title=title, parent=parent )
		else: tkMessageBox.showinfo( message=message, title=title, parent=parent )

	else: # Write to stdout
		if error: print( 'ERROR! ' + message )
		elif warning: print( 'Warning! ' + message )
		else: print( message )


def printStatus( message, warning=False, error=False, success=False, forceUpdate=False ):

	""" Displays a short message at the bottom of the GUI (in the status bar), 
		or prints out to console if the GUI has not been initialized. 
		May be decorated with warning/error/success=True. """

	if globalData.gui: # Display a pop-up message
		globalData.gui.updateProgramStatus( message, warning, error, success, forceUpdate )
		print( 'printStatus mirror: ' + message )

	else: # Write to stdout
		if error: print( 'ERROR! ' + message )
		elif warning: print( 'Warning! ' + message )
		else: print( message )


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


def cmdChannel( command, standardInput=None, shell=False, returnStderrOnSuccess=False ):
	
	""" IPC (Inter-Process Communication) to command line. Blocks; i.e will not return until the 
		process is complete. shell=True gives access to all shell features/commands, such dir or copy. 
		creationFlags=0x08000000 prevents creation of a console for the process. 
		Returns ( returnCode, stdoutData ) if successful, else ( returnCode, stderrData ). """

	try:
		process = subprocess.Popen( command, shell=shell, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=0x08000000 )
		stdoutData, stderrData = process.communicate( input=standardInput )
	except Exception as err:
		return ( -1, 'The subprocess command failed; ' + str(err) )

	if process.returncode == 0 and returnStderrOnSuccess:
		return ( process.returncode, stderrData )
	elif process.returncode == 0:
		return ( process.returncode, stdoutData )
	else:
		print( 'IPC error (exit code {}):'.format( process.returncode ) )
		print( stderrData )
		return ( process.returncode, stderrData )


def saveAndShowTempFileData( fileData, filename ):

	""" Saves binary to a new temporary file, and opens it in the user's hex editor of choice. """

	# Get the file path to the hex editor (prompts user if needed and validates the path)
	hexEditorPath = globalData.getHexEditorPath()
	if not hexEditorPath: return # User may have canceled the prompt

	# Create the temporary file path, and any folders that might be needed
	tempFilePath = os.path.join( globalData.paths['tempFolder'], filename )
	createFolders( os.path.split(tempFilePath)[0] )

	# Save the file data to a temporary file.
	try:
		with open( tempFilePath, 'wb' ) as newFile:
			newFile.write( fileData )
	except Exception as err: # Failsafe; pretty unlikely
		printStatus( 'Error creating temporary file for {}! {}'.format(filename, err), error=True )
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


class ListDict(_OrderedDict):

	""" This is used to allow for 'inserting' entries into an ordered dictionary. 
		todo: start using 'move_to_end' method when switching to Python 3 (shouldn't need this class at that point)

		By:     jarydks
		Source: https://gist.github.com/jaredks/6276032
	"""

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


class NoIndent(object):

	""" Value wrapper for the CodeModEncoder below; used to combine some aspects of 
		JSON output to single lines for better readability. """

	def __init__(self, value):
		if not isinstance(value, (list, tuple)):
			raise TypeError('Only lists and tuples can be wrapped')
		self.value = value

class CodeModEncoder(json.JSONEncoder):

	""" Custom JSON encoder for saving codes.json files for AMFS format code-based mods. 
		Allows mod configuration option members (name/value/comment lists) to be output 
		in a more compact way for better human readability (one line for each member). 
		
		By:     martineau
		Source: https://stackoverflow.com/questions/42710879/write-two-dimensional-list-to-json-file
	"""

	FORMAT_SPEC = '@@{}@@'  # Unique string pattern of NoIndent object ids.
	regex = re.compile(FORMAT_SPEC.format(r'(\d+)'))  # compile(r'@@(\d+)@@')

	def __init__(self, **kwargs):
		# Keyword arguments to ignore when encoding NoIndent wrapped values.
		ignore = {'cls', 'indent'}

		# Save copy of any keyword argument values needed for use here.
		self._kwargs = {k: v for k, v in kwargs.items() if k not in ignore}
		super(CodeModEncoder, self).__init__(**kwargs)

	def default(self, obj):
		return (self.FORMAT_SPEC.format(id(obj)) if isinstance(obj, NoIndent)
					else super(CodeModEncoder, self).default(obj))

	def iterencode(self, obj, **kwargs):
		format_spec = self.FORMAT_SPEC  # Local var to expedite access.

		# Replace any marked-up NoIndent wrapped values in the JSON repr
		# with the json.dumps() of the corresponding wrapped Python object.
		for encoded in super(CodeModEncoder, self).iterencode(obj, **kwargs):
			match = self.regex.search(encoded)
			if match:
				id = int(match.group(1))
				no_indent = PyObj_FromPtr(id)
				json_repr = json.dumps(no_indent.value, **self._kwargs)
				# Replace the matched id string with json formatted representation
				# of the corresponding Python object.
				encoded = encoded.replace(
							'"{}"'.format(format_spec.format(id)), json_repr)

			yield encoded