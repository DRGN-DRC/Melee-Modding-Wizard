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

import json
import struct
import globalData

from collections import OrderedDict

from fileBases import FileBase
from hsdFiles import DatFile
from hsdStructures import StructBase, TableStruct, DataBlock
from basicFunctions import msg, uHex, roundTo32


class CharFileBase( object ):

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
					'Gl': 0x1C, 'Gk': 0x1D, 'Ch': 0x1E, 'Sb': 0x1F, 'Nn': 0x0E } # Excludes 0x20 (Solo Popo)

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
	def charName( self ):
		if not self._charName and self.extCharId >= 0:
			if self.extCharId >= len( globalData.charList ):
				self._charName = 'Unidentified'
			else:
				self._charName = globalData.charList[self.extCharId]
		return self._charName


class CharDataFile( CharFileBase, DatFile ):

	""" Pl__.dat (ftData_) """

	specialAttrNames = {}
	
	def __init__( self, *args, **kwargs ):
		super( CharDataFile, self ).__init__( *args, **kwargs )

		self._intCharId = -2
		self._extCharId = -2
		self._charAbbr = ''
		self._charName = ''

	def getCharAbbr( self ):

		# Ensure root nodes and the string table have been parsed
		self.initialize()

		rootNodeName = self.rootNodes[0][1]
		return self.charAbbrs[rootNodeName[6:]] # Removes ftData from the string

	def validate( self ):

		""" Verifies whether this is actually a character data file by checking the string table. 
			This will also initialize the file and retrieve its file data. """

		self.initialize()
		rootNodeName = self.rootNodes[0][1]

		if not rootNodeName.startswith( 'ftData' ):
			raise Exception( "Invalid character data file; no 'ftData...' symbol node found." )

	def hintRootClasses( self ):
		dataTableOffset = self.rootNodes[0][0]
		self.structs[dataTableOffset] = 'FighterDataTable'

	def getDescription( self ):
		
		# Attempt to get the character name this file is for
		charName = globalData.charNameLookup.get( self.charAbbr, '' )
		if not charName:
			self._longDescription = 'Unknown ({}) data file'.format( self.charAbbr )
		elif charName.endswith( 's' ):
			self._longDescription = charName + "' data file"
		else:
			self._longDescription = charName + "'s data file"

		# First two are for 20XX files
		if self.ext[1] == 'p':
			self._shortDescription = 'PAL Data file'
			self._longDescription.replace( 'data', 'PAL data' )
		elif self.ext[1] == 's':
			self._shortDescription = 'SDR Data file'
			self._longDescription.replace( 'data', 'SDR data' )
		else:
			self._shortDescription = 'Data file'

	def getAttributeNames( self ):

		""" Read the JSON file containing attribute names, if it has not already been read, 
			and return the attribute names and formatting for this character. """
		
		if not self.specialAttrNames:
			if self.specialAttrNames == 'ERR': # Prevent multiple reports of the error if there's something wrong
				return ''

			# Open the Properties.json file and get its file contents
			try:
				jsonPath = globalData.paths['properties']
				with open( jsonPath, 'r' ) as jsonFile:
					jsonContents = json.load( jsonFile )
					self.specialAttrNames = jsonContents['specialAttributes']
			except Exception as err:
				self.specialAttrNames = 'ERR'
				errMsg = 'Encountered an error when attempting to open "{}" (likely due to incorrect formatting); {}'.format( jsonPath, err )
				msg( errMsg )
				return ''

		# Get and return the attribute names/formats for this character
		return self.specialAttrNames.get( self.charAbbr )

	def getGeneralProperties( self ):

		self.initialize()

		# Get the root fighter data table
		fighterTableOffset = self.rootNodes[0][0] # Root nodes is a list of tuples, each of the form ( structOffset, string )
		ftDataTable = self.initSpecificStruct( FighterDataTable, fighterTableOffset )

		# Get and return the general properties struct
		propertiesPointer = ftDataTable.getValues()[0]
		return self.initDataBlock( GeneralFighterProperties, propertiesPointer, fighterTableOffset, dataLength=0x184 )

	def getSpecialAttributes( self ):

		self.initialize()

		# Get the root fighter data table
		fighterTableOffset = self.rootNodes[0][0] # Root nodes is a list of tuples, each of the form ( structOffset, string )
		ftDataTable = self.initSpecificStruct( FighterDataTable, fighterTableOffset )

		# Get and return the special attributes struct
		attributesPointer = ftDataTable.getValues()[1]
		propStruct = self.initDataBlock( SpecialCharacterAttributes, attributesPointer, fighterTableOffset )

		# Cast what we're going to edit to lists, so we can use item assignment
		propFieldNames = list( propStruct.fields )
		propFormatting = list( propStruct.formatting[1:] ) # Excludes '>' character

		# Update field names and formatting for this struct if info on it is available
		attrInfo = self.getAttributeNames()
		if attrInfo:
			offsetsFound = set()
			for offset, name, attrType in attrInfo[1:]: # Excludes first entry (character name)
				# Validate the offset
				try:
					offset = int( offset, 16 )
				except:
					msg( 'An invalid offset was found in the Properties.json file for "{}": {}. This should be a hexadecimal number.'.format(name, offset), 'Invalid Attribute Offset', warning=True )
					continue
				if offset % 4 != 0:
					msg( 'An invalid offset was found in the Properties.json file for "{}": {}. These values should be a multiple of 4.'.format(name, offset), 'Invalid Attribute Offset', warning=True )
					continue
				elif offset in offsetsFound:
					msg( 'A duplicate offset was found in the Properties.json file for "{}": {}'.format(name, offset), 'Duplicate Attribute Offset', warning=True )
					continue
				else:
					offsetsFound.add( offset )
					valueIndex = offset / 4
					if valueIndex >= len( propStruct.fields ):
						msg( 'An invalid offset was found in the Properties.json file for "{}": {}. The offset is beyond the range of the special attributes structure.'.format(name, offset), 'Invalid Attribute Offset', warning=True )
						continue

				# Validate the attribute type
				if attrType not in ( 'I', 'f' ):
					msg( 'An invalid attribute type was found in the Properties.json file for "{}": {}. These should either be "I" or "f" for integers and floats, respectively.'.format(name, offset), 'Invalid Attribute Type', warning=True )
					continue

				# Update the field name and format identifier for this entry
				propFieldNames[valueIndex] = name
				propFormatting[valueIndex] = attrType

			# Re-cast and replace the original struct fields and formatting
			propStruct.fields = tuple( propFieldNames )
			propStruct.formatting = '>' + ''.join( propFormatting )

			# Re-unpack values since we've modified the attribute types
			propStruct.values = ()
			propStruct.getValues()
		
		return propStruct

	def getActionTable( self ):

		self.initialize()

		# Get the root fighter data table
		fighterTableOffset = self.rootNodes[0][0] # Root nodes is a list of tuples, each of the form ( structOffset, string )
		ftDataTable = self.initSpecificStruct( FighterDataTable, fighterTableOffset )

		# Get and return the action table
		actionTablePointer = ftDataTable.getValues()[3]
		return self.getStruct( actionTablePointer )


class FighterDataTable( StructBase ):

	""" Primary/root table for character data files (Pl__.dat). """

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Fighter Data Table ' + uHex( 0x20 + args[1] )
		self.formatting = '>IIIIIIIIIIIIIIIIIIIIIIII'
		self.fields = ( 'Common_Attributes_Pointer',
						'Special_Attributes_Pointer',
						'Model_Lookup_Tables_Pointer',
						'Fighter_Action_Table_Pointer',
						'Dynamic_Action_Behaviors_Pointer',		# 0x10
						'Demo_Fighter_Action_Table_Pointer',
						'Demo_Dynamic_Action_Behaviors_Pointer',
						'Model_Part_Animations_Pointer',
						'Shield_Pose_Container_Pointer',		# 0x20
						'Idle_Action_Chances_Pointer',
						'Wait_Idle_Action_Chances_Pointer',
						'Physics_Pointer',
						'Hurtboxes_Pointer',					# 0x30
						'Center_Bubble_Pointer',
						'Coin_Collision_Spheres_Pointer',
						'Camera_Box_Pointer',
						'Item_Pickup_Params_Pointer',			# 0x40
						'Environment_Collision_Pointer',
						'Articles_Pointer',
						'Common_Sound_Effect_Table_Pointer',
						'JostleBox_Pointer',					# 0x50
						'Fighter_Bone_Table_Pointer',
						'Fighter_IK_Pointer',
						'Metal_Model_Pointer'
					)
		self.length = 0x60
		self.structDepth = ( 2, 0 )
		self._siblingsChecked = True
		self.childClassIdentities = { 0: 'GeneralFighterProperties', 1: 'SpecialCharacterAttributes', 3: 'ActionTable' }


class GeneralFighterProperties( DataBlock ):

	""" Describes common/basic properties which all characters have 
		(first struct referenced in Pl__.dat files' fighter data tables). """
		
	flags = { 'Weight_Dependent_Throw_Flags': OrderedDict([
				( '1<<0', 'FThrow' ),	# 1
				( '1<<1', 'BThrow' ),	# 2
				( '1<<2', 'UThrow' ),	# 4
				( '1<<3', 'DThrow' ),	# 8
		]) }

	def __init__( self, *args, **kwargs ):
		DataBlock.__init__( self, *args, **kwargs )

		self.name = 'General Fighter Properties ' + uHex( 0x20 + args[1] )
		self.formatting = '>ffffffffffffffffffffffIfffffffffffffffIffIfffffffffffffffffffffffffffffffffffffffffffffffffIffffBBH'
		self.fields = ( 'Walk_Starting_Speed',
						'Walk_Acceleration',
						'Max_Walking_Speed',
						'Walk_Animation_Speed',
						'Mid_Walk_Point',					# 0x10
						'Fast_Walk_Speed',

						'Friction',

						'Dash_Starting_Speed',
						'StopTurn_Initial_Speed_A',			# 0x20
						'StopTurn_Initial_Speed_B',
						'Max_Run_Speed',
						'Run_Animation_Scaling',
						'Dash_Lockout_Direction',			# 0x30
						'Dash_Duration_Before_Run',

						'Jump_Startup_Lag_(Frames)',
						'Initial_Horizontal_Jump_Velocity',
						'Initial_Vertical_Jump_Velocity',	# 0x40
						'Ground-to-Air_Jump_Momentum_Multiplier',
						'Max_Shorthop_Horizontal_Velocity',
						'Max_Shorthop_Vertical_Velocity',
						'Double_Jump_Vertical_Multiplier',	# 0x50
						'Double_Jump_Horizontal_Multiplier',

						'Number_of_Jumps', # Int
						'Gravity',
						'Terminal_Velocity',				# 0x60
						'Aerial_Speed',
						'Aerial_Friction',
						'Max_Aerial_Horizontal_Speed',
						'Air_Friction',						# 0x70
						'FastFall_Terminal_Velocity',
						'TiltTurn_Forced_Velocity',

						'Jab2_Window',
						'Jab3_Window',						# 0x80
						'Frames_to_Change_Direction_on_Standing_Turn',
						'Weight',
						'Model_Scaling',
						'Shield_Size',						# 0x90
						'Shield_Break_Initial_Velocity',
						'Rapid_Jab_Window', # Int
						'Clank_Speed_Multiplier',
						'Hit-by-Item_Flag',					# 0xA0
						'Unknown_0xA4', # Int
						'Ledge_Jump_Horizontal_Velocity',
						'Ledge_Jump_Vertical_Velocity',
						'Item_Throw_Velocity',				# 0xB0
						'Item_Throw_Damage_Scaling',
						'Run_Side_Special_Momentum',
						
						'Egg_Size',
						'Egg_Hurtbox',						# 0xC0
						'Egg_Hurtbox_X',
						'Egg_Hurtbox_Y',
						'Egg_Hurtbox_Z',

						'Unknown_0xD0',						# 0xD0
						'Unknown_0xD4',
						'Egg_Hurtbox_Radius',
						'Kirby_Neutral_Special_Star_Swallow_Damage',
						'Kirby_Neutral_Special_Star_Damage',	# 0xE0

						'Normal_Landing_Lag',
						'Nair_Landing_Lag',
						'Fair_Landing_Lag',
						'Bair_Landing_Lag',					# 0xF0
						'Uair_Landing_Lag',
						'Dair_Landing_Lag',

						'Victory_Screen_Model_Scale',
						'Wall_Tech_X',						# 0x100
						'Wall_Jump_Horizontal_Velocity',
						'Wall_Jump_Vertical_Velocity',
						'Ceiling_Tech_X_Direction',
						'Unknown_0x110',					# 0x110

						'Left_Bunny_Hood_X',
						'Left_Bunny_Hood_Y',
						'Left_Bunny_Hood_Z',
						'Right_Bunny_Hood_X',				# 0x120
						'Right_Bunny_Hood_Y',
						'Right_Bunny_Hood_Z',
						'Bunny_Hood_Size',

						'Flower_X',							# 0x130
						'Flower_Y',
						'Flower_Z',
						'Flower_Size',
						'Screw_Attack_Upward_Knockback',	# 0x140
						'Screw_Attack_Effect_Size',
						'Unknown_0x148',
						'Bubble_Ratio',

						'Freeze_Offset_1',					# 0x150
						'Freeze_Offset_2',
						'Freeze_Escape_Height',
						'Freeze_Escape_X_Momentum',
						'Frozen_Size',						# 0x160

						'WarpStar_Hitbox_Scaling',
						'Unknown_0x168',
						'Camera_Zoom_Target_Bone', # Int
						'Magnified_X_Sway',					# 0x170
						'Magnified_Y_Sway',
						'Magnified_Z_Sway',
						'Footstool_Y_Offset',
						'Weight_Dependent_Throw_Flags',		# 0x180
						'Padding',
						'Padding'
					)
		self.length = 0x184
		self.structDepth = ( 3, 0 )
		# self._siblingsChecked = True
		# self._childrenChecked = True
		
	# def validated( self, *args, **kwargs ): return True
	# def getSiblings( self, nextOnly=False ): return []
	# def isSibling( self, offset ): return False
	# def getChildren( self, includeSiblings=True ): return []
	# def initDescendants( self ): return


class SpecialCharacterAttributes( DataBlock ):

	""" Describes special properties specific to only one character 
		(second struct referenced in Pl__.dat files' fighter data tables). 
		
		Field names and correct formatting is defined in bin/Properties.json
		and should be updated when this struct is requested by charDat.getSpecialAttributes(). """

	def __init__( self, *args, **kwargs ):
		DataBlock.__init__( self, *args, **kwargs )

		self.name = 'Special Character Attributes ' + uHex( 0x20 + self.offset )

		# Build the formatting string and fields tuple based on the length of the struct
		self.length = self.dat.getStructLength( self.offset )
		self.formatting = '>' + 'f' * ( self.length / 4 )
		fieldOffsets = [ (i * 4) for i in range(len(self.formatting)-1) ]
		self.fields = tuple( 'Unknown 0x' + hex( o )[2:].upper().rstrip( 'L' ) for o in fieldOffsets )

		self.structDepth = ( 3, 0 )
	# 	self._siblingsChecked = True
	# 	self._childrenChecked = True
		
	# def validated( self, *args, **kwargs ): return True
	# def getSiblings( self, nextOnly=False ): return []
	# def isSibling( self, offset ): return False
	# def getChildren( self, includeSiblings=True ): return []
	# def initDescendants( self ): return


class ActionTable( TableStruct ):

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Action Table ' + uHex( 0x20 + args[1] )
		self.formatting = '>IIIIBHBI'
		self.fields = ( 'Action_Name_Pointer',
						'Animation_Offset',			# Offset into the AJ files
						'Animation_Size',
						'SubAction_Events_Pointer',
						'SubAction_ID',				# 0x10 (byte)
						'Flags',					# 0x11 (halfword)
						'Internal_Character_ID',	# 0x13 (byte)
						'Padding'					# ARAM animation pointer placeholder (used when loaded into RAM)
					)
		self.length = 0x18
		self.childClassIdentities = {}
		self._childrenChecked = True
		tableLength = self.dat.getStructLength( args[1] )
		self.entryCount = tableLength // self.length

		# Reinitialize this as a Table Struct to duplicate this entry struct for all enties in this table
		TableStruct.__init__( self )
		#super( ActionTable, self ).__init__( self ) # probably should use this instead


class SubAction( DataBlock ):

	eventDesc = { # Defines [EventID]: ( name, length, valueNames, bitmasks )
		0: ( 'End of Script', 4, (), () ),

	}

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'SubAction ' + uHex( 0x20 + args[1] )
		# self.length = self.dat.getStructLength( self.offset )
		# self.formatting = '>' + 'B' * self.length
		self.events = []

	# def parse( self ):

	# 	position = 0
	# 	byte = self.data[0]

	# 	while byte:


	def rebuild( self ):
		pass


class CharAnimFile( CharFileBase, FileBase ):

	""" Character animation files (Pl__AJ.dat files); i.e. Ply[charAbbr]5K_Share_ACTION_Wait1_figatree 
		This file format is just a container/list of DAT files, where each DAT is an animation. 
		These sub-files are stored end-to-end (with no header to define said list), but aligned to 0x20 bytes. """

	def __init__( self, *args, **kwargs ):
		super( CharAnimFile, self ).__init__( *args, **kwargs )

		self.animations = [] # A list of DAT file objects for the contents of this file
		self.animNames = [] # Animation names (symbols) matching the above files
		
		self._intCharId = -2
		self._extCharId = -2
		self._charAbbr = ''
		self._charName = ''

	def validate( self ):

		""" Verifies whether this is actually a character animation file by 
			checking the first animation file symbol. """
			
		# Make sure file data has been loaded
		self.getData()

		# Get the size of this animation
		headerData = self.getData( 0, 0x14 )
		animSize, rtStart, rtEntryCount, rootNodeCount, referenceNodeCount = struct.unpack( '>5I', headerData )

		if rootNodeCount != 1:
			raise Exception( 'Invalid character animation file; root node count is not 1.' )
		elif referenceNodeCount != 0:
			raise Exception( 'Invalid character animation file; reference node count is not 0.' )

		# Get the name of this animation (the symbol). Simpler method than initializing the file
		nameOffset = 0x20 + rtStart + ( rtEntryCount * 4 ) + 8
		stringLength = 0x20 + animSize - nameOffset
		symbol = self.getString( nameOffset, stringLength )

		if not symbol.startswith( 'Ply' ) or '_ACTION_' not in symbol:
			raise Exception( 'Invalid character animation file; invalid symbol name: {}'.format(symbol) )

	def initialize( self ):

		""" Parse out the file's individual DAT files within, and collect information on them. """

		if self.animations:
			return # This file has already been initialized!
			
		# Make sure file data has been loaded
		self.getData()

		readOffset = 0

		# Create a DAT file for each animation
		while 1:
			# Get the size of this animation
			headerData = self.getData( readOffset, 0xC )
			if len( headerData ) != 0xC:
				break # Reached the end of the file
			animSize, rtStart, rtEntryCount = struct.unpack( '>3I', headerData )

			# Create a DAT file for this animation and attach its data
			anim = DatFile( None, readOffset, animSize, self.filename )
			anim.data = self.getData( readOffset, animSize )

			# Get the name of this animation (the symbol). Simpler method than initializing the file
			nameOffset = readOffset + 0x20 + rtStart + ( rtEntryCount * 4 ) + 8
			stringLength = readOffset + animSize - nameOffset
			anim.name = self.getString( nameOffset, stringLength )
			self.animNames.append( anim.name )

			self.animations.append( anim )

			# Calculate offset of next animation (round up to nearest 0x20 bytes)
			readOffset += roundTo32( animSize )

	def getCharAbbr( self ):

		# Ensure root nodes and the string table have been parsed
		self.initialize()

		symbol = self.animations[0].name
		symbolBase = symbol[3:].split( '_' )[0] # Remove 'Ply' and everything after first underscore

		return symbolBase.replace( '5K', '' )

	def getDescription( self ):
		
		# Attempt to get the character name this file is for
		charName = globalData.charNameLookup.get( self.charAbbr, '' )
		if not charName:
			self._shortDescription = 'Unknown ({})'.format( self.charAbbr )
			self._longDescription = self._shortDescription
			return

		self._shortDescription = 'Animation data'
		if charName.endswith( 's' ):
			self._longDescription = charName + "' animation data"
		else:
			self._longDescription = charName + "'s animation data"


class CharIdleAnimFile( CharFileBase, FileBase ):

	""" Character idle animation files (Pl__DViWaitAJ.dat files); i.e. ftDemoViWaitMotionFile[charAbbr]
		This file format is basically a DAT file contained within another DAT file. Both have a header 
		and string table, but the outer archive/DAT file has no relocation table. """

	def __init__( self, *args, **kwargs ):
		super( CharIdleAnimFile, self ).__init__( *args, **kwargs )

		self.animations = []
		self.animNames = []
		
		self._intCharId = -2
		self._extCharId = -2
		self._charAbbr = ''
		self._charName = ''


class CharCostumeFile( CharFileBase, DatFile ):

	""" Character model & texture files (costumes); i.e. Ply[charAbbr]5KBu_Share_joint """
	
	def __init__( self, *args, **kwargs ):
		super( CharCostumeFile, self ).__init__( *args, **kwargs )

		self._intCharId = -2
		self._extCharId = -2
		self._charAbbr = ''
		self._charName = ''
		self._colorAbbr = ''

	@property
	def colorAbbr( self ):
		if not self._colorAbbr:
			self._colorAbbr = self.getColorAbbr()
		return self._colorAbbr

	def validate( self ):

		""" Verifies whether this is actually a character costume file by checking the string table. 
			This will also initialize the file and retrieve its file data. """

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
			print( 'Unrecognized root node name, "{}" from {}'.format(rootNodeName, self.filename) )
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
			print( 'Unrecognized root node name, "{}" from {}'.format(rootNodeName, self.filename) )
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

		# Check the costume color
		colorKey = self.colorAbbr
		color = globalData.charColorLookup.get( colorKey, '' )
		assert color, 'Unable to get a color look-up from ' + colorKey

		# Assemble the costume color string
		self._shortDescription = color + ' costume'
		if self.ext == '.lat' or colorKey == 'Rl': self._shortDescription += " ('L' alt)" # For 20XX
		elif self.ext == '.rat' or colorKey == 'Rr': self._shortDescription += " ('R' alt)"

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

	def getSkeleton( self ):
		
		# Ensure root nodes and the string table have been parsed
		self.initialize()

		firstNodeOffset, firstNodeString = self.rootNodes[0]
		assert firstNodeString.endswith( 'Share_joint' ), 'Unable to get skeleton; incorrect root node string encountered: ' + firstNodeString

		# Get the skeleton struct (should be the first child joint/bone of the first root node)
		jointClass = globalData.fileStructureClasses['JointObjDesc']
		rootBone = self.initSpecificStruct( jointClass, firstNodeOffset )
		skeletonStructOffset = rootBone.getValues( 'Child_Pointer' )
		
		return self.initSpecificStruct( jointClass, skeletonStructOffset )
