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

from fileBases import DatFile
from hsdStructures import StructBase


class MexRootData( StructBase ):

	def __init__( self, *args, **kwargs ):
		StructBase.__init__( self, *args, **kwargs )

		self.name = 'Root Data Table 0x{:X}'.format( 0x20 + self.offset )
		self.formatting = '>IIIIIIIIIIIIII'
		self.fields = ( 'Metadata',
						'Menu Table',
						'Fighter Data',
						'Fighter Functions',
						'SSM Table',
						'Music Table',
						'Effect Table',
						'Item Table',
						'Kirby Data',
						'Kirby Functions',
						'Stage Data',
						'Stage Functions',
						'Scene Data',
						'Misc. Data' )
		self.length = 0x38
		self.structDepth = ( 2, 0 )
		self._siblingsChecked = True
		#self.childClassIdentities = { 3: 'VertexAttributesArray', 6: 'VertexAttributesArray' }

	def validated( self ): # Temporary override until childClassIdentities is updated
		return True


class MexData( DatFile ):

	def getVersion( self ):

		self.initialize()

		# Get the root data table
		rootTableOffset = self.rootNodes[0][0]
		rootDataTable = self.initSpecificStruct( MexRootData, rootTableOffset )

		# Get the metadata struct
		metaStructPointer = rootDataTable.getValues()[0]
		metaDataStruct = self.getStruct( metaStructPointer )

		# Read version bytes and return ( majorVersion, minorVersion )
		return struct.unpack( '>BB', metaDataStruct.data[:2] )