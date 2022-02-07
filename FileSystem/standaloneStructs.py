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

import struct

import globalData
from basicFunctions import uHex


class StandaloneStruct( object ):

	""" Base class to represents an abstract structure NOT within a HAL DAT file. """

	# __slots__ = ( 'dat', 'offset', 'data', 'name', 'label', 'fields', 'length', 'entryCount', 'formatting',
	# 			  'parents', 'siblings', 'children', 'values', 'branchSize', 'childClassIdentities',
	# 			  '_parentsChecked', '_siblingsChecked', '_childrenChecked', '_branchInitialized' )

	def __init__( self, hostFile, offset, entryCount=-1 ):

		self.host 			= hostFile				# Host DAT File object
		self.offset 		= offset
		self.data			= ()					# Will become a bytearray
		self.name 			= 'Standalone Struct ' + uHex( 0x20 + offset )
		#self.label 			= hostFile.getStructLabel( dataSectionOffset ) # From the DAT's string table
		self.fields			= ()
		self.length			= -1
		self.entryCount 	= entryCount			# Used with array & table structures; -1 means it's not an array/table
		self.formatting		= ''
		self.parents 		= set()					# Set of integers (offsets of other structs)
		self.siblings 		= [] 					# List of integers (offsets of other structs)
		self.children 		= [] 					# List of integers (offsets of other structs)
		self.values 		= () 					# Actual decoded values (ints/floats/etc) of the struct's data
		#self.branchSize 	= -1
		#self.childClassIdentities = {}

		# self._parentsChecked = False
		# self._siblingsChecked = False
		# self._childrenChecked = False
		# self._branchInitialized = False
		#self.changesNeedSaving = False				# Indicates that some of the decoded values have been changed

	def getData( self, dataOffset=0, dataLength=-1 ):

		""" Gets and returns binary data for this structure (also storing it to .data for future use). 
			If no arguments are given, the whole structure's data is returned. 
			If only an offset is given, the data length is assumed to be 1. """

		if not self.data:
			assert self.offset > 0, 'Invalid offset for {}: {}'.format( self.name, self.offset )
			assert self.length > 0, 'Invalid length for {}: {}'.format( self.name, self.length )
			self.data = self.host.getData( self.offset, self.length )
				
		# Return all of the data if no args were given
		if dataOffset == 0 and dataLength == -1:
			return self.data

		# Assume data length of 1 if it's still -1
		if dataLength == -1:
			dataLength = 1

		return self.data[ dataOffset:dataOffset+dataLength ]

	def getValues( self, specificValue='' ):

		""" Unpacks the data for this structure, according to the struct's formatting.
			Only unpacks on the first call (returns the same data after that). Returns a tuple. """

		if not self.values:
			self.values = struct.unpack( self.formatting, self.getData() )

		if not specificValue:
			return self.values

		# Perform some validation on the input
		elif not self.fields:
			print 'Unable to get a specific value; struct lacks known fields.'
			return None
		elif specificValue not in self.fields:
			print 'Unable to get a specific value; field name not found.'
			return None

		# Get a specific value by field name
		else:
			fieldIndex = self.fields.index( specificValue )
			return self.values[fieldIndex]


class StageInfoTable( StandaloneStruct ):

	""" These are located in the DOL (one for each stage). Referenced by a pointer 
		table at 803DFEDC / 0x3DCEDC, which is indexed by internal stage IDs. """

	def __init__( self, hostFile, offset ):
		StandaloneStruct.__init__( self, hostFile, offset )

		self.name = 'Stage Info Table ' + uHex( 0x20 + offset )
		self.formatting = '>IIIIIIIIIIIII'
		self.fields = ( 'Internal_Stage_ID',
						'Map_GObj_Functions_Pointer',
						'Stage_Filename_String_Pointer',
						'StageInit_Function_Pointer',
						'Unknown_Function_Pointer',			# 0x10
						'OnLoad_Function_Pointer',
						'OnGo_Function_Pointer',
						'Unknown_Function_Pointer',
						'Unknown_Function_Pointer',			# 0x20
						'Unknown_Function_Pointer',
						'Unknown_Int32',
						'MovingCollisionPointsInitialize_Pointer',
						'MovingCollisionPointsInitialize_Count' # 0x30
					)
		self.length = 0x34


class DebugMenuItem( StandaloneStruct ):

	def __init__( self, hostFile, offset, ramAddress, parentMenuOffset ):
		StandaloneStruct.__init__( self, hostFile, offset )

		if hostFile.filename.endswith( '.dol' ):
			self.name = 'Line Item ' + uHex( offset )
		else:
			self.name = 'Line Item ' + uHex( 0x20 + offset )
		self.formatting = '>IIIIIIff'
		self.fields = ( 'Type',
						'Target_Function',
						'Text_Pointer',
						'Text_Table_Pointer',
						'Left-Right_Value_Pointer',
						'Submenu_Pointer',
						'Left-Right_Count',
						'Left-Right_Value_Increment'
					)
		self.length = 0x20

		self.address = ramAddress
		self.parentMenu = parentMenuOffset # Offset of the parent menu item table
		self.leftRightStrings = []

		# Get the structs data & values, and hold onto the values as properties
		( self.itemType,
		  self.targetFunction,
		  self.textPointer,
		  self.textTablePointer,
		  self.leftRightValPointer,
		  self.submenuPointer,
		  self.leftRightCount,
		  self.leftRightValIncrement ) = self.getValues()

		if self.textPointer == 0:
			self.text = ''
		else:
			self.text = self.getString( self.textPointer )

		if self.itemType == 2: # Left/Right String List
			self.buildStringList()
			self.text += ' ' + self.leftRightStrings[0] # Picking an arbitrary default

	def getExternalData( self, ramAddress, dataLength=-1 ):

		""" Gets and returns binary data from one of two files. 
			If only an offset is given, the data length is assumed to be 1. """

		# Assume data length of 1 if it's still -1
		if dataLength == -1:
			dataLength = 1

		# Determine the file and offset of the target data by the RAM address
		dol = globalData.disc.dol
		dataOffset = dol.offsetInDOL( ramAddress )
		if dataOffset == -1: # Target data must reside in the CSS file
			targetFile = globalData.disc.files[globalData.disc.gameId + '/MnSlChr.0sd']
			dataOffset = ramAddress - 0x80BEC720 - 0x20 # Get an offset relative to the data section
		else:
			targetFile = dol

		return targetFile.getData( dataOffset, dataLength )

	def getString( self, ramAddress ):
		return self.getExternalData( ramAddress, 0x40 ).split( '\x00' )[0].decode( 'utf-8' )

	def buildStringList( self ):

		""" For item type 2, follows the pointer to the strings' pointer table, and parses it.
			The string pointer table is a list of pointers to individual strings. """
		
		# Get the bytes forming the list of pointers
		stringCount = int( self.leftRightCount )
		pointerData = self.getExternalData( self.textTablePointer, 4*stringCount )

		# Unpack the data to pointer values
		pointerList = struct.unpack( '>{}I'.format(stringCount), pointerData )

		self.leftRightStrings = [ self.getString(pointer) for pointer in pointerList ]

