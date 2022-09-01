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
import bitstring
import Tkinter as Tk

from binascii import hexlify
from basicFunctions import msg, printStatus

# Internal Dependencies
import globalData
from FileSystem.charFiles import CharDataFile, SubAction
from guiSubComponents import ColoredLabelButton, DDList, HexEditEntry, LabelButton, ToggleButton, ToolTip, VerticalScrolledFrame


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

		ttk.Label( propertiesTab, text='General Fighter Properties' ).grid( column=0, row=0, pady=12 )
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
		for name, formatting, value in zip( propStruct.fields, propStruct.formatting[1:], propertyValues ):
			propertyName = name.replace( '_', ' ' )
			absoluteFieldOffset = propStruct.offset + offset
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
			if formatting == 'I':
				typeName = 'Integer'
			else:
				typeName = 'Float'
			ToolTip( fieldLabel, text='Offset in struct: 0x{:X}\nOffset in file: 0x{:X}\nType: {}'.format(offset, 0x20 + absoluteFieldOffset, typeName), delay=300 )

			# Add an editable field for the raw hex data
			hexEntry = HexEditEntry( structTable.interior, parent.charFile, absoluteFieldOffset, fieldByteLength, format, propertyName )
			rawData = propStruct.data[offset:offset+fieldByteLength]
			hexEntry.insert( 0, hexlify(rawData).upper() )
			hexEntry.grid( column=1, row=row, pady=verticalPadding )
			
			# Add an editable field for this field's actual decoded value (and attach the hex edit widget for later auto-updating)
			valueEntry = HexEditEntry( structTable.interior, parent.charFile, absoluteFieldOffset, fieldByteLength, format, propertyName, valueEntry=True )
			valueEntry.insert( 0, value )
			valueEntry.hexEntryWidget = hexEntry
			hexEntry.valueEntryWidget = valueEntry
			valueEntry.grid( column=2, row=row, pady=verticalPadding, padx=(5, 20) )

			if offset == 0x180:
				break # Only padding follows this

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
		for name, formatting, value in zip( attrStruct.fields, attrStruct.formatting[1:], propertyValues ):
			propertyName = name.replace( '_', ' ' )
			absoluteFieldOffset = attrStruct.offset + offset
			verticalPadding = ( 0, 0 )

			if offset == 0x180:
				fieldByteLength = 1
			else:
				fieldByteLength = 4

			fieldLabel = ttk.Label( structTable.interior, text=propertyName + ':', wraplength=200 )
			fieldLabel.grid( column=0, row=row, padx=(25, 10), sticky='e', pady=verticalPadding )
			if formatting == 'I':
				typeName = 'Integer'
			else:
				typeName = 'Float'
			ToolTip( fieldLabel, text='Offset in struct: 0x{:X}\nOffset in file: 0x{:X}\nType: {}'.format(offset, 0x20 + absoluteFieldOffset, typeName), delay=300 )

			# Add an editable field for the raw hex data
			hexEntry = HexEditEntry( structTable.interior, parent.charFile, absoluteFieldOffset, fieldByteLength, format, propertyName )
			rawData = attrStruct.data[offset:offset+fieldByteLength]
			hexEntry.insert( 0, hexlify(rawData).upper() )
			hexEntry.grid( column=1, row=row, pady=verticalPadding )
			
			# Add an editable field for this field's actual decoded value (and attach the hex edit widget for later auto-updating)
			valueEntry = HexEditEntry( structTable.interior, parent.charFile, absoluteFieldOffset, fieldByteLength, format, propertyName, valueEntry=True )
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


class SubActionEditor( ttk.Frame, object ):

	def __init__( self, parent ):
		super( SubActionEditor, self ).__init__( parent )

		self.actionTable = parent.charFile.getActionTable()
		self.charFile = parent.charFile

		# Add the action table pane's title
		title = '{} Action Table  (0x{:X})'.format( self.charFile.filename, self.actionTable.offset + 0x20 )
		ttk.Label( self, text=title ).grid( columnspan=2, column=0, row=0, pady=4 )

		# Add the action table list and its scrollbar
		subActionScrollBar = Tk.Scrollbar( self, orient='vertical' )
		self.subActionList = Tk.Listbox( self, yscrollcommand=subActionScrollBar.set, activestyle='none', selectbackground='#78F' )
		subActionScrollBar.config( command=self.subActionList.yview )
		for i, values in self.actionTable.iterateEntries():
			gameName = self.getSubActionName( values[0], i )
			translatedName = self.charFile.subActionTranslations.get( gameName, gameName ) # Defaults to gameName if translation not found
			self.subActionList.insert( i, '  ' + translatedName )
		self.subActionList.bind( '<<ListboxSelect>>', self.subActionSelected )
		self.subActionList.grid( column=0, row=1, sticky='nsew' )
		subActionScrollBar.grid( column=1, row=1, sticky='ns' )

		# Pane for showing subAction events (empty for now)
		ttk.Label( self, text='Event Display:' ).grid( column=2, row=0 )
		scrollPane = VerticalScrolledFrame( self )
		self.displayPane = DDList( scrollPane.interior, 500, 40, item_borderwidth=2, offset_x=2, offset_y=2, gap=2 )
		self.displayPaneMessage = None
		self.displayPane.pack( fill='both', expand=True )
		scrollPane.grid( column=2, row=1, sticky='nsew' )

		# Pane for general info display
		infoPane = ttk.Frame( self )
		emptyWidget = Tk.Frame( relief='flat' ) # This is used as a simple workaround for the labelframe, so we can have no text label with no label gap.
		generalInfoBox = ttk.Labelframe( infoPane, labelwidget=emptyWidget, padding=(20, 5) )
		self.subActionId = Tk.StringVar( value='SubAction ID:' )
		self.subActionIndex = Tk.StringVar( value='SubAction Table Index:' )
		self.subActionSize = Tk.StringVar( value='SubAction Table Size:' )
		self.subActionFlags = Tk.StringVar( value='SubAction Flags:' )
		self.subActionAnimOffset = Tk.StringVar( value='Animation Offset:' )
		self.subActionAnimSize = Tk.StringVar( value='Animation Size:' )
		self.subActionEventsOffset = Tk.StringVar( value='Events Offset:' )
		ttk.Label( generalInfoBox, textvariable=self.subActionId ).pack()
		ttk.Label( generalInfoBox, textvariable=self.subActionIndex ).pack()
		ttk.Label( generalInfoBox, textvariable=self.subActionSize ).pack()
		ttk.Label( generalInfoBox, textvariable=self.subActionFlags ).pack()
		ttk.Label( generalInfoBox, textvariable=self.subActionAnimOffset ).pack()
		ttk.Label( generalInfoBox, textvariable=self.subActionAnimSize ).pack()
		ttk.Label( generalInfoBox, textvariable=self.subActionEventsOffset ).pack()
		generalInfoBox.pack( fill='x', expand=True )
		
		flagsBox = ttk.Labelframe( infoPane, text=' SubAction Flags ', padding=(20, 5) )
		ttk.Label( flagsBox, text='TEST' ).pack()
		flagsBox.pack( fill='x', expand=True, pady=20 )

		buttonsFrame = ttk.Frame( infoPane )
		ColoredLabelButton( buttonsFrame, 'delete', None, 'Delete Event', '#f04545' ).grid( column=0, row=0, pady=4, padx=4 )
		# ColoredLabelButton( buttonsFrame, 'save', None, 'Expand All' ).grid( column=1, row=0, pady=4, padx=4 )
		# ColoredLabelButton( buttonsFrame, 'save', None, 'Collapse All' ).grid( column=1, row=0, pady=4, padx=4 )
		ColoredLabelButton( buttonsFrame, 'save', None, 'Save Changes', '#292' ).grid( column=1, row=0, pady=4, padx=4 )
		ColoredLabelButton( buttonsFrame, 'insert', None, 'Insert New Event' ).grid( column=2, row=0, pady=4, padx=4 )
		buttonsFrame.columnconfigure( 'all', weight=1 )
		buttonsFrame.pack( fill='x', expand=True, pady=20 )

		infoPane.grid( column=3, row=1, padx=20, pady=10 )

		# Configure row/column stretch and resize behavior
		self.columnconfigure( 0, weight=1 ) # SubAction Listbox
		self.columnconfigure( 1, weight=0 ) # Scrollbar
		self.columnconfigure( 2, weight=2 ) # Events display pane
		self.columnconfigure( 3, weight=0 ) # Info display
		self.rowconfigure( 0, weight=0 )
		self.rowconfigure( 1, weight=1 )

	def getSubActionName( self, namePointer, index ):
		if namePointer == 0:
			return 'Entry ' + str( index + 1 )
		else:
			return self.charFile.getString( namePointer ).split( 'ACTION_' )[1].split( '_figatree' )[0]

	def subActionSelected( self, event ):

		# Get the subAction index and values from the subaction entry
		selection = self.subActionList.curselection()
		if not selection:
			return
		index = selection[0]
		entry = self.actionTable.getEntryValues( index )
		
		# Update general info display
		self.subActionId.set( 'SubAction ID:  0x{:X}'.format(entry[4]) )
		self.subActionIndex.set( 'SubAction Table Index:  0x{:X}'.format(index) )
		self.subActionFlags.set( 'SubAction Flags:  0x{:X}'.format(entry[5]) )
		self.subActionAnimOffset.set( 'Animation Offset:  0x{:X}'.format(0x20+entry[1]) )
		self.subActionAnimSize.set( 'Animation Size:  0x{:X}'.format(entry[2]) )
		self.subActionEventsOffset.set( 'Events Offset:  0x{:X}'.format(0x20+entry[3]) )

		# Clear the events display pane
		self.displayPane.delete_all_items()

		# Update the subAction events display list
		try:
			subActionStruct = self.charFile.initDataBlock( SubAction, entry[3], self.actionTable.offset )
			subActionStruct.parse()
			self.subActionSize.set( 'SubAction Table Size:  0x{:X}'.format(subActionStruct.getLength()) )
		except Exception as err:
			subActionName = self.getSubActionName( entry[0], index )
			printStatus( 'Unable to parse {} subAction (index {}); {}'.format(subActionName, index, err) )
			self.subActionSize.set( 'SubAction Table Size:  N/A' )
			return

		# Show that there are no events to display if there are none (i.e. only has an End of Script event)
		if len( subActionStruct.events ) == 1 and subActionStruct.events[0].id == 0:
			if not self.displayPaneMessage:
				self.displayPaneMessage = ttk.Label( self, text='No events' )
				self.displayPaneMessage.grid( column=2, row=1, sticky='n', pady=150 )
		else:
			if self.displayPaneMessage:
				self.displayPaneMessage.destroy()
				self.displayPaneMessage = None

			# Populate the events display pane
			self.displayPane.update_width()
			for event in subActionStruct.events:
				# Exit on End of Script event
				if event.id == 0:
					break

				# Create a GUI module for the event
				item = self.displayPane.create_item()
				helpMessage = self.charFile.eventNotes.get( '0x{:02X}'.format(event.id), '' )
				eM = EventModule( item, event, self.displayPane, helpMessage )
				eM.pack( fill='both', expand=True )

				# Add the GUI module to the display panel
				self.displayPane.add_item( item )
				#eM.lastIndex = self.displayPane._position[item]
			self.displayPane.master.master.event_generate( '<Configure>' )


class EventModule( ttk.Frame, object ):

	def __init__( self, parentItem, event, displayPane, helpMessage ):
		super( EventModule, self ).__init__( parentItem )

		self.name = event.name
		self.event = event
		self.expanded = False
		self.ddList = displayPane
		#self.lastIndex = -1
		self.helpMsg = helpMessage

		headerRow = ttk.Frame( self )
		label = ttk.Label( headerRow, text=self.name )
		label.pack( side='left', padx=(12,0), pady=(4,0) )
		
		if self.event.fields:
			self.expandBtn = ToggleButton( headerRow, 'expandArrow', self.toggleState )
			self.expandBtn.pack( side='left', padx=(12,0), pady=(3, 0) )

		if self.helpMsg:
			helpBtn = LabelButton( headerRow, 'question', self.showHelp, 'Info' )
			helpBtn.pack( side='right', padx=12, pady=(1, 0) )
		headerRow.pack( fill='x', expand=True )

		if self.event.fields:
			label.bind( '<Double-Button-1>', self.expandBtn.toggle )
			headerRow.bind( '<Double-Button-1>', self.expandBtn.toggle )
			self.bind( '<Double-Button-1>', self.expandBtn.toggle )
		
	def toggleState( self, tkEvent=None ):

		# Check if the item has been moved (user just wants to drag-and-drop)
		# currentIndex = self.ddList._position[self.master]
		# if self.lastIndex != currentIndex:
		# 	self.lastIndex = currentIndex
		# 	return

		# Not moved. Toggle state
		if self.expanded:
			self.contract()
		else:
			self.expand()

	def expand( self ):
		# Construct the event details labels
		containingFrame = ttk.Frame( self )
		index = 0

		for valueName, value in zip( self.event.fields, self.event.values ):
			if valueName == 'Padding':
				index += 1
				continue

			title = ttk.Label( containingFrame, text=valueName + ' :' )
			title.grid( column=0, row=index )
			if self.event.fields:
				title.bind( '<Double-Button-1>', self.expandBtn.toggle )

			entry = Tk.Entry( containingFrame, width=12, justify='center', relief='flat', 
				highlightbackground='#b7becc', 	# Border color when not focused
				borderwidth=1, highlightthickness=1, highlightcolor='#78F' )
			entry.bind( '<Return>', self.updateValue )
			entry.index = index
			entry.insert( 0, value )
			entry.grid( column=1, row=index, padx=15 )
			index += 1

		containingFrame.pack( anchor='w', padx=(42,0), pady=(4,6) )
		if self.event.fields:
			containingFrame.bind( '<Double-Button-1>', self.expandBtn.toggle )

		# Adjust height of the widget
		item = self.master
		item.update_idletasks()
		currentHeight = item.winfo_height()
		targetHeight = currentHeight + containingFrame.winfo_reqheight()

		self.ddList.update_item_height( item, targetHeight )

		self.expanded = True

	def updateValue( self, event ):
		widget = event.widget

		try:
			self.event.updateValue( widget.index, widget.get() )
		except bitstring.CreationError as err:
			if err.startswith( 'bool token' ):
				message = 'A ' + err
			else:
				message = message[0].upper() + message[1:]
			msg( message, 'Invalid Value', warning=True )
		except Exception as err:
			msg( err, 'Value Encoding Error', error=True )

	def contract( self ):

		item = self.master

		for widget in self.winfo_children()[1:]:
			widget.destroy()

		self.ddList.update_item_height( item, self.ddList._item_height )

		self.expanded = False

	def showHelp( self, event ):
		title, message = self.helpMsg.split( '|' )
		msg( message, title )

