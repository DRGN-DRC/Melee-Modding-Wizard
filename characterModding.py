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
import ttk
import Tkinter as Tk

from binascii import hexlify
from basicFunctions import msg

# Internal Dependencies
import globalData
from FileSystem.charFiles import CharDataFile
from guiSubComponents import DDList, HexEditEntry, ToolTip, VerticalScrolledFrame


class CharModding( ttk.Notebook ):

	# Icon texture indexes within IfAll.usd
	iconIndices = { 'Ca': 70, 'Dk': 74, 'Fx': 75,'Gw': 76, 'Kb': 77, 'Kp': 78, 'Lk': 79,
					'Lg': 80, 'Mr': 81, 'Ms': 82, 'Mt': 83, 'Ns': 84, 'Pe': 85, 'Pk': 86,
					'Pp': 87, 'Pr': 88, 'Ss': 89, 'Ys': 90, 'Zd': 91, 'Sk': 98, 'Fc': 92,
					'Cl': 93, 'Dr': 94, 'Fe': 95, 'Pc': 96, 'Gn': 97, 
					
					'Mh': 192, 'Bo': 191, 'Gl': 191, 'Gk': 202, 'Ch': 193, 'Sb': 196 }

	def __init__( self, parent, mainGui ):

		ttk.Notebook.__init__( self, parent ) #, padding="11 0 0 11" ) # Padding order: Left, Top, Right, Bottom.

		# Add this tab to the main GUI, and add drag-and-drop functionality
		mainGui.mainTabFrame.add( self, text=' Character Modding ' )
		mainGui.dnd.bindtarget( self, mainGui.dndHandler, 'text/uri-list' )

		# Add the main selection tab
		selectionTab = ttk.Frame( self )
		selectionTab.charFile = None
		self.add( selectionTab, text=' Character Selection ' )

		ttk.Label( selectionTab, text="Choose the character(s) you'd like to modify:" ).pack( padx=20, pady=20 )

		# Collect character icon images
		if globalData.disc.is20XX:
			ifAllFile = globalData.disc.getFile( 'IfAl1.usd' )
		else:
			ifAllFile = globalData.disc.getFile( 'IfAll.usd' )
		if ifAllFile:
			texturesInfo = ifAllFile.identifyTextures()
			# print( 'found {} textures'.format(len(texturesInfo)) )
			# for i, info in enumerate(texturesInfo):
			# 	print( i, hex(info[0] + 0x20) )
		else:
			texturesInfo = None

		# Check for 'Pl__.dat' files to populate the main tab with character choices
		self.charBtnsTab = ttk.Frame( selectionTab )
		specialCharRow = 1
		column = 0
		row = 0
		for fileObj in globalData.disc.files.values():
			# Filter to just the character data files
			# if not len(fileObj.filename) == 8 or not fileObj.filename.startswith( 'Pl' ):
			# 	continue
			if not isinstance( fileObj, CharDataFile ) or not fileObj.filename.endswith( '.dat' ):
				continue
			elif fileObj.charAbbr == 'Nn': # Skip Nana
				continue

			# Get the character name
			# character = globalData.charNameLookup.get( fileObj.filename[2:4], '' )
			# if not character:
			# 	continue

			# Try to get the character's icon texture
			# extCharId = fileObj.extCharId
			if texturesInfo:
				textureIndex = self.iconIndices.get( fileObj.charAbbr, 71 )
				texOffset, _, _, _, texWidth, texHeight, texType, _ = texturesInfo[textureIndex]
				icon = ifAllFile.getTexture( texOffset, texWidth, texHeight, texType )
			else:
				icon = None

			button = ttk.Button( self.charBtnsTab, image=icon, text=' '+fileObj.charName, compound=Tk.LEFT, width=22 )
			button.charFile = fileObj
			button.icon = icon # Stored to prevent garbage collection
			button.bind( '<1>', self.addCharacterTab )

			if fileObj.charAbbr in ( 'Bo', 'Gl', 'Mh', 'Ch', 'Gk', 'Sb' ):
				button.grid( column=3, row=specialCharRow, padx=10 )
				specialCharRow += 1
			else:
				button.grid( column=column, row=row, padx=10 )
				row += 1

				if row >= 9:
					column += 1
					row = 0

		self.charBtnsTab.pack( pady=20 )

	def repopulate( self ):
		pass

	def addCharacterTab( self, event ):

		""" Adds a new character to the main Character Modding notebook (if not already added). 
			This includes populating all sub-tabs for that character. """

		# Check if this tab has already been created
		for tabName in self.tabs():
			tabWidget = globalData.gui.root.nametowidget( tabName )
			if tabWidget.charFile and tabWidget.charFile.filename == event.widget.charFile.filename:
				# Found this tab already exists; select it
				self.select( tabWidget )
				return
		
		# Create a new character tab and add it to the character modder notebook
		newChar = ttk.Notebook( self )
		newChar.charFile = event.widget.charFile
		self.add( newChar, text=newChar.charFile.charName )

		# Add the fighter/character properties tab
		propTab = self.buildPropertiesTab( newChar )
		newChar.add( propTab, text=' Properties ' )

		# Add the fighter/character properties tab
		propTab = SubActionEditor( newChar )
		newChar.add( propTab, text=' Moves (SubAction) Editor ' )

		# Switch tabs to this character
		self.select( newChar )

	def buildPropertiesTab( self, parent ):
		
		""" Adds General Fighter Properties and Special Character Attributes to a character tab. """
		
		propertiesTab = ttk.Frame( parent )

		ttk.Label( propertiesTab, text='General Fighter Properties' ).grid( column=0, row=0, pady=10 )
		ttk.Label( propertiesTab, text='Special Character Attributes' ).grid( column=1, row=0 )

		# Collect general properties
		propStruct = parent.charFile.getGeneralProperties()
		propertyValues = propStruct.getValues()
		if not propertyValues:
			msg( message='Unable to get fighter properties for {}. Most likely there was a problem initializing the Pl__.dat file.', 
				 title='Unable to get Struct Values', 
				 parent=globalData.gui,
				 error=True )

		# Create the properties table for Fighter Properties
		structTable = VerticalScrolledFrame( propertiesTab )
		offset = 0
		row = 0
		for name, propType, value in zip( propStruct.fields, propStruct.formatting[1:], propertyValues ):
			propertyName = name.replace( '_', ' ' )
			absoluteFieldOffset = 0x20 + propStruct.offset + offset
			if offset == 0x180:
				fieldByteLength = 1
			else:
				fieldByteLength = 4
			
			# Add a little bit of spacing before some items to group similar or related properties
			if offset in (0x18, 0x1C, 0x38, 0x58, 0x7C, 0xBC, 0xD0, 0xE4, 0xFC, 0x114, 0x130, 0x150, 0x164 ):
				verticalPadding = ( 10, 0 )
			else:
				verticalPadding = ( 0, 0 )

			fieldLabel = ttk.Label( structTable.interior, text=propertyName + ':', wraplength=200 )
			fieldLabel.grid( column=0, row=row, padx=(25, 10), sticky='e', pady=verticalPadding )
			if propType == 'I':
				typeName = 'Integer'
			else:
				typeName = 'Float'
			ToolTip( fieldLabel, text='Offset in struct: 0x{:X}\nOffset in file: 0x{:X}\nType: {}'.format(offset, absoluteFieldOffset, typeName), delay=300 )

			# Add an editable field for the raw hex data
			hexEntry = HexEditEntry( structTable.interior, parent.charFile, absoluteFieldOffset, fieldByteLength, propType, propertyName )
			rawData = propStruct.data[offset:offset+fieldByteLength]
			hexEntry.insert( 0, hexlify(rawData).upper() )
			hexEntry.grid( column=1, row=row, pady=verticalPadding )
			
			# Add an editable field for this field's actual decoded value (and attach the hex edit widget for later auto-updating)
			valueEntry = HexEditEntry( structTable.interior, parent.charFile, absoluteFieldOffset, fieldByteLength, propType, propertyName, valueEntry=True )
			valueEntry.insert( 0, value )
			valueEntry.hexEntryWidget = hexEntry
			hexEntry.valueEntryWidget = valueEntry
			valueEntry.grid( column=2, row=row, pady=verticalPadding, padx=(5, 20) )

			if offset == 0x180:
				break # The only things next are padding

			offset += 4
			row += 1

		structTable.grid( column=0, row=1, sticky='nsew' )

		# Collect special attributes
		attrStruct = parent.charFile.getSpecialAttributes()
		propertyValues = attrStruct.getValues()
		if not propertyValues:
			msg( message='Unable to get character attributes for {}. Most likely there was a problem initializing the Pl__.dat file.', 
				 title='Unable to get Struct Values', 
				 parent=globalData.gui,
				 error=True )

		# Create the properties table for Character Attributes
		structTable = VerticalScrolledFrame( propertiesTab )
		offset = 0
		row = 0
		for name, propType, value in zip( attrStruct.fields, attrStruct.formatting[1:], propertyValues ):
			propertyName = name.replace( '_', ' ' )
			absoluteFieldOffset = 0x20 + attrStruct.offset + offset
			if offset == 0x180:
				fieldByteLength = 1
			else:
				fieldByteLength = 4
			
			# Add a little bit of spacing before some items to group similar or related properties
			# if offset in (0x16, 0x60):
			# 	verticalPadding = ( 10, 0 )
			# else:
			verticalPadding = ( 0, 0 )

			fieldLabel = ttk.Label( structTable.interior, text=propertyName + ':', wraplength=200 )
			fieldLabel.grid( column=0, row=row, padx=(25, 10), sticky='e', pady=verticalPadding )
			if propType == 'I':
				typeName = 'Integer'
			else:
				typeName = 'Float'
			ToolTip( fieldLabel, text='Offset in struct: 0x{:X}\nOffset in file: 0x{:X}\nType: {}'.format(offset, absoluteFieldOffset, typeName), delay=300 )

			# Add an editable field for the raw hex data
			hexEntry = HexEditEntry( structTable.interior, parent.charFile, absoluteFieldOffset, fieldByteLength, propType, propertyName )
			rawData = attrStruct.data[offset:offset+fieldByteLength]
			hexEntry.insert( 0, hexlify(rawData).upper() )
			hexEntry.grid( column=1, row=row, pady=verticalPadding )
			
			# Add an editable field for this field's actual decoded value (and attach the hex edit widget for later auto-updating)
			valueEntry = HexEditEntry( structTable.interior, parent.charFile, absoluteFieldOffset, fieldByteLength, propType, propertyName, valueEntry=True )
			valueEntry.insert( 0, value )
			valueEntry.hexEntryWidget = hexEntry
			hexEntry.valueEntryWidget = valueEntry
			valueEntry.grid( column=2, row=row, pady=verticalPadding, padx=(5, 20) )

			offset += 4
			row += 1

		structTable.grid( column=1, row=1, sticky='nsew' )

		# Configure row/column stretch and resize behavior
		propertiesTab.columnconfigure( 'all', weight=1 )
		propertiesTab.rowconfigure( 1, weight=1 ) # Do not expand top row

		return propertiesTab

	# def buildSubActionsTab( self, parent ):
		
	# 	""" Adds the subAction editor to a character tab. """
		
	# 	subActionsTab = ttk.Frame( parent )

	# 	actionTable = parent.charFile.getActionTable()
	# 	title = parent.charFile.filename + ' Action Table Entries - ' + hex( actionTable.offset + 0x20 )
	# 	#self.subActions = {}

	# 	lines = []
	# 	for i, values in actionTable.iterateEntries():
	# 		actionName = parent.charFile.getString( values[0] )
	# 		offset = actionTable.entryIndexToOffset( i )
	# 		lines.append( '\t{} | {} - {}'.format(i, uHex(offset + 0x20), actionName) )


	# 	subActionScrollBar = Tk.Scrollbar( subActionsTab, orient='vertical' )
	# 	self.subActionList = Tk.Listbox( subActionsTab, yscrollcommand=subActionScrollBar.set )
	# 	subActionScrollBar.config( command=self.subActionList.yview )
	# 	for i, values in actionTable.iterateEntries():
	# 		#self.subActions[i] = values
	# 		actionName = parent.charFile.getString( values[0] )
	# 		# label = ttk.Label( self.subActionList.interior, text=actionName )
	# 		# label.index = i
	# 		# label.pack()
	# 		self.subActionList.insert( i, actionName )

	# 	self.subActionList.grid( column=0, row=0, sticky='nsew' )
	# 	subActionScrollBar.grid( column=1, row=0, sticky='ns' )

	# 	return subActionsTab


class SubActionEditor( ttk.Frame, object ):

	def __init__( self, parent ):
		super( SubActionEditor, self ).__init__( parent )

		self.actionTable = parent.charFile.getActionTable()
		self.charFile = parent.charFile
		title = self.charFile.filename + ' Action Table Entries - ' + hex( self.actionTable.offset + 0x20 )

		ttk.Label( self, text=title ).grid( columnspan=2, column=0, row=0 )

		subActionScrollBar = Tk.Scrollbar( self, orient='vertical' )
		self.subActionList = Tk.Listbox( self, yscrollcommand=subActionScrollBar.set )
		subActionScrollBar.config( command=self.subActionList.yview )
		for i, values in self.actionTable.iterateEntries():
			if values[0] == 0:
				actionName = 'Entry ' + str(i+1)
			else:
				actionName = parent.charFile.getString( values[0] ).split( 'ACTION_' )[1].split( '_figatree' )[0]
			self.subActionList.insert( i, actionName )
		self.subActionList.bind('<<ListboxSelect>>', self.subActionSelected )

		self.subActionList.grid( column=0, row=1, sticky='nsew' )
		subActionScrollBar.grid( column=1, row=1, sticky='ns' )

		# Pane for showing subAction events
		ttk.Label( self, text='Event Display:' ).grid( column=2, row=0 )
		self.displayPane = DDList( self, 450, 600 )
		self.displayPane.grid( column=2, row=1, sticky='nsew' )

		# Pane for general info display
		infoPane = ttk.Frame( self )
		emptyWidget = Tk.Frame( relief='flat' ) # This is used as a simple workaround for the labelframe, so we can have no text label with no label gap.
		generalInfoBox = ttk.Labelframe( infoPane, labelwidget=emptyWidget, padding=(20, 4) )
		self.subActionIndex = Tk.StringVar( value='SubAction Table Index:' )
		self.subActionId = Tk.StringVar( value='SubAction ID:' )
		self.subActionFlags = Tk.StringVar( value='SubAction Flags:' )
		self.subActionAnimOffset = Tk.StringVar( value='Animation Offset:' )
		self.subActionAnimSize = Tk.StringVar( value='Animation Size:' )
		self.subActionEventsOffset = Tk.StringVar( value='Events Offset:' )
		ttk.Label( generalInfoBox, textvariable=self.subActionIndex ).pack()
		ttk.Label( generalInfoBox, textvariable=self.subActionId ).pack()
		ttk.Label( generalInfoBox, textvariable=self.subActionFlags ).pack()
		ttk.Label( generalInfoBox, textvariable=self.subActionAnimOffset ).pack()
		ttk.Label( generalInfoBox, textvariable=self.subActionAnimSize ).pack()
		ttk.Label( generalInfoBox, textvariable=self.subActionEventsOffset ).pack()
		generalInfoBox.pack( fill='x', expand=True )
		infoPane.grid( column=3, row=1, sticky='nsew' )

		# Configure row/column stretch and resize behavior
		self.columnconfigure( 0, weight=1 ) # SubAction Listbox
		self.columnconfigure( 1, weight=0 ) # Scrollbar
		self.rowconfigure( 1, weight=1 )
		self.rowconfigure( 3, weight=1 )

	def subActionSelected( self, event ):

		# Get the subAction index and values from the subaction entry
		index = self.subActionList.curselection()[0]
		entry = self.actionTable.getEntryValues( index )
		print( entry )
		
		# Update general info display
		self.subActionId.set( 'SubAction Table Index: 0x{:X}'.format(index) )
		self.subActionId.set( 'SubAction ID: 0x{:X}'.format(entry[4]) )
		self.subActionFlags.set( 'SubAction Flags: 0x{:X}'.format(entry[5]) )
		self.subActionAnimOffset.set( 'Animation Offset: 0x{:X}'.format(0x20+entry[1]) )
		self.subActionAnimSize.set( 'Animation Size: 0x{:X}'.format(entry[2]) )
		self.subActionEventsOffset.set( 'Events Offset: 0x{:X}'.format(0x20+entry[3]) )

		# Update the subAction events display list
		#eventsData = self.charFile.