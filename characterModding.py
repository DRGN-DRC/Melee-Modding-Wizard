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
import tkMessageBox
import Tkinter as Tk

from binascii import hexlify
from basicFunctions import msg, printStatus

# Internal Dependencies
import globalData
from FileSystem.charFiles import CharDataFile, SubAction, SubActionEvent
from guiSubComponents import BasicWindow, ClickText, ColoredLabelButton, DDList, HexEditEntry, LabelButton, ToggleButton, ToolTip, VerticalScrolledFrame, getWindowGeometry


class CharModding( ttk.Notebook ):

	# Icon texture indexes within IfAll.usd
	iconIndices = { 'Ca': 70, 'Dk': 74, 'Fx': 75,'Gw': 76, 'Kb': 77, 'Kp': 78, 'Lk': 79,
					'Lg': 80, 'Mr': 81, 'Ms': 82, 'Mt': 83, 'Ns': 84, 'Pe': 85, 'Pk': 86,
					'Pp': 87, 'Pr': 88, 'Ss': 89, 'Ys': 90, 'Zd': 91, 'Sk': 98, 'Fc': 92,
					'Cl': 93, 'Dr': 94, 'Fe': 95, 'Pc': 96, 'Gn': 97, 
					
					'Mh': 192, 'Bo': 191, 'Gl': 191, 'Gk': 202, 'Ch': 193, 'Sb': 196 }

	def __init__( self, parent, mainGui ):

		ttk.Notebook.__init__( self, parent )

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
			if not isinstance( fileObj, CharDataFile ) or not fileObj.filename.endswith( '.dat' ):
				continue
			elif fileObj.charAbbr == 'Nn': # Skip Nana
				continue

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

	def addCharacterTab( self, tkEvent ):

		""" Adds a new character to the main Character Modding notebook (if not already added). 
			This includes populating all sub-tabs for that character. """

		# Check if this tab has already been created
		for tabName in self.tabs():
			tabWidget = globalData.gui.root.nametowidget( tabName )
			if tabWidget.charFile and tabWidget.charFile.filename == tkEvent.widget.charFile.filename:
				# Found this tab already exists; select it
				self.select( tabWidget )
				return
		
		# Create a new character tab and add it to the character modder notebook
		newCharNotebook = ttk.Notebook( self )
		newCharNotebook.charFile = tkEvent.widget.charFile
		self.add( newCharNotebook, text=newCharNotebook.charFile.charName )

		# # Add the fighter/character properties tab
		# newTab = CharGeneralEditor( newCharNotebook )
		# newCharNotebook.add( newTab, text=' General ' )

		# Add the fighter/character properties tab
		newTab = self.buildPropertiesTab( newCharNotebook )
		newCharNotebook.add( newTab, text=' Properties ' )

		# Add the fighter/character properties tab
		newCharNotebook.subActionEditor = SubActionEditor( newCharNotebook )
		newCharNotebook.add( newCharNotebook.subActionEditor, text=' Moves (SubAction) Editor ' )

		# Switch tabs to this character
		self.select( newCharNotebook )

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

	def hasUnsavedChanges( self ):

		modifiedCharacters = []

		for tabName in self.tabs():
			# Get the character tab
			tabWidget = globalData.gui.root.nametowidget( tabName )
			if not tabWidget.charFile: continue # Skip main selection tab

			# Check the SubAction tab for changes
			elif tabWidget.subActionEditor.hasUnsavedChanges():
				modifiedCharacters.append( tabWidget.charFile.filename )

		return modifiedCharacters


class CharGeneralEditor( ttk.Frame, object ):

	def __init__( self, parent ):
		super( CharGeneralEditor, self ).__init__( parent )

		self.charFile = parent.charFile

		# Add the CSP display
		cspFrame = ttk.Frame( self )
		self.cspIndex = 0
		self.cspLabel = ttk.Label( cspFrame, relief='raised', borderwidth=3 )
		self.cspLabel.image = None
		self.cspLabel.grid( columnspan=4, column=0, row=0 )
		self.updateCsp( 0 )

		# Buttons for CSP display
		ColoredLabelButton( cspFrame, 'expandArrowState1', self.prevCostume, 'Previous Costume' ).grid( column=0, row=1 )
		ttk.Button( cspFrame, text='Import' ).grid( column=1, row=1 )
		ttk.Button( cspFrame, text='Export' ).grid( column=2, row=1 )
		ColoredLabelButton( cspFrame, 'expandArrowState2', self.nextCostume, 'Next Costume' ).grid( column=3, row=1 )
		cspFrame.grid( column=0, row=0, sticky='nw' )

	def prevCostume( self, tkEvent ):
		pass

	def nextCostume( self, tkEvent ):
		pass

	def updateCsp( self, newIndex ):
		# Get the next or previous CSP image
		cssFile = globalData.disc.css
		cspImage = cssFile.getCsp( self.charFile.extCharId, newIndex )

		# Update the GUI
		self.cspLabel.configure( image=cspImage )
		self.cspLabel.image = cspImage # Storing to prevent garbage collection


class SubActionEditor( ttk.Frame, object ):

	def __init__( self, parent ):
		super( SubActionEditor, self ).__init__( parent )

		# Add the action table pane's title
		self.tableTitleVar = Tk.StringVar()
		ttk.Label( self, textvariable=self.tableTitleVar ).grid( column=0, columnspan=2, row=0, pady=4 )

		ClickText( self, 'Edit Filters', self.showFilterOptions ).grid( column=0, columnspan=2, row=1 )

		# Add the action table list and its scrollbar
		subActionScrollBar = Tk.Scrollbar( self, orient='vertical' )
		self.subActionList = Tk.Listbox( self, width=46, yscrollcommand=subActionScrollBar.set, 
			activestyle='none', selectbackground='#78F', exportselection=0 ) #, font=('Consolas', 9)
		subActionScrollBar.config( command=self.subActionList.yview )
		self.subActionList.bind( '<<ListboxSelect>>', self.subActionSelected )
		self.subActionList.grid( column=0, row=2, sticky='nsew' )
		subActionScrollBar.grid( column=1, row=2, sticky='ns' )

		# Pane for showing subAction events (empty for now)
		ttk.Label( self, text='Event Display:' ).grid( column=2, row=0 )
		scrollPane = VerticalScrolledFrame( self )
		self.displayPane = DDList( scrollPane.interior, 500, 40, item_borderwidth=2, reorder_callback=self.reordered, offset_x=2, offset_y=2, gap=2 )
		self.displayPaneMessage = None
		self.displayPane.pack( fill='both', expand=True )
		scrollPane.grid( column=2, row=1, rowspan=2, sticky='nsew' )

		# Pane for general info display
		infoPane = ttk.Frame( self )
		emptyWidget = Tk.Frame( relief='flat' ) # This is used as a simple workaround for the labelframe, so we can have no text label with no label gap.
		generalInfoBox = ttk.Labelframe( infoPane, labelwidget=emptyWidget, padding=(20, 5) )
		self.subActionIndex = Tk.StringVar()
		self.subActionAnimOffset = Tk.StringVar()
		self.subActionAnimSize = Tk.StringVar()
		self.subActionEventsOffset = Tk.StringVar()
		self.subActionEventsSize = Tk.StringVar()
		ttk.Label( generalInfoBox, textvariable=self.subActionIndex ).pack()
		ttk.Label( generalInfoBox, textvariable=self.subActionAnimOffset ).pack( pady=(7, 0) )
		ttk.Label( generalInfoBox, textvariable=self.subActionAnimSize ).pack()
		ttk.Label( generalInfoBox, textvariable=self.subActionEventsOffset ).pack( pady=(7, 0) )
		ttk.Label( generalInfoBox, textvariable=self.subActionEventsSize ).pack()
		generalInfoBox.pack( fill='x', expand=True )
		
		flagsBox = ttk.Labelframe( infoPane, text=' SubAction Flags ', padding=(20, 5) )
		self.subActionFlags = Tk.StringVar()
		ttk.Label( flagsBox, textvariable=self.subActionFlags ).pack()
		flagsBox.pack( fill='x', expand=True, pady=20 )

		buttonsFrame = ttk.Frame( infoPane )
		ColoredLabelButton( buttonsFrame, 'delete', self.deleteEvent, 'Delete Event', '#f04545' ).grid( column=0, row=0, pady=4, padx=4 )
		ColoredLabelButton( buttonsFrame, 'expand', self.expandAll, 'Expand All' ).grid( column=1, row=0, pady=4, padx=4 )
		ColoredLabelButton( buttonsFrame, 'collapse', self.collapseAll, 'Collapse All' ).grid( column=2, row=0, pady=4, padx=4 )
		ColoredLabelButton( buttonsFrame, 'save', self.saveEventChanges, 'Save Changes\nto Charcter File', '#292' ).grid( column=3, row=0, pady=4, padx=4 )
		insertBtn = LabelButton( buttonsFrame, 'insert', self.insertEventBefore, 'Insert New Event\n\n(Before selection. Shift-click\nto insert after selection.)' )
		insertBtn.bind( '<Shift-Button-1>', self.insertEventAfter )
		insertBtn.grid( column=4, row=0, pady=4, padx=4 )
		#ttk.Button( buttonsFrame, text='Restore to Vanilla', command=self.restoreEvents )
		buttonsFrame.columnconfigure( 'all', weight=1 )
		buttonsFrame.pack( fill='x', expand=True, pady=20 )

		self.noteStringFrame = ttk.Frame( infoPane )
		self.noteStringVar = Tk.StringVar()
		ttk.Label( self.noteStringFrame, textvariable=self.noteStringVar, foreground='#a34343' ).pack( side='left', pady=0 )
		self.expandInfoBtn = None
		self.noteStringFrame.pack( fill='x', expand=True, pady=0 )

		infoPane.grid( column=3, row=1, rowspan=2, sticky='ew', padx=20, pady=0 )

		# Configure row/column stretch and resize behavior
		self.columnconfigure( 0, weight=1 ) # SubAction Listbox
		self.columnconfigure( 1, weight=0 ) # Scrollbar
		self.columnconfigure( 2, weight=2 ) # Events display pane
		self.columnconfigure( 3, weight=0 ) # Info display
		self.rowconfigure( 0, weight=0 ) # Titles
		self.rowconfigure( 1, weight=0 ) # Main content
		self.rowconfigure( 2, weight=1 ) # Main content

		self.populate( parent.charFile )

	def populate( self, newCharFile ):

		""" Clears the subAction list (if it has anything displayed) and 
			repopulates it with entries from the character's action table. """
		
		self.charFile = newCharFile
		self.actionTable = newCharFile.getActionTable()
		self.subActionStruct = None
		self.lastSelection = -1
		self.listboxIndices = {} # Key = listboxIndex, value = eventIndex

		title = '{} Action Table  (0x{:X})'.format( self.charFile.filename, self.actionTable.offset + 0x20 )
		self.tableTitleVar.set( title )

		# Repopulate the subAction list
		self.subActionList.delete( 0, 'end' )
		listboxIndex = 0
		for entryIndex, values in self.actionTable.iterateEntries():
			subActionName = self.getSubActionName( values[0], entryIndex )

			self.subActionList.insert( entryIndex, '  ' + subActionName.replace(' (', '    (') )
			self.listboxIndices[listboxIndex] = entryIndex

			if subActionName.startswith( 'Entry' ):
				self.subActionList.itemconfigure( listboxIndex, foreground='#6A6A6A' )
			listboxIndex += 1

		# Clear the events display pane
		self.displayPane.delete_all_items()

		# Clear general info display
		self.subActionIndex.set( 'SubAction Table Index:  ' )
		self.subActionAnimOffset.set( 'Animation (AJ) Offset:  ' )
		self.subActionAnimSize.set( 'Animation (AJ) Size:  ' )
		self.subActionEventsOffset.set( 'Events Offset:  ' )
		self.subActionEventsSize.set( 'Events Table Size:  ' )

		# Clear flags display
		self.subActionFlags.set( 'SubAction Flags:  ' )

	def showFilterOptions( self, guiEvent ):
		
		menu = Tk.Menu( self )
		menu.add_checkbutton( label='Attacks', underline=0, variable=globalData.boolSettings['subActionFilterAttacks'], command=self.updateFilters )
		menu.add_checkbutton( label='Movement', underline=0, variable=globalData.boolSettings['subActionFilterAttacks'], command=self.updateFilters )
		menu.add_checkbutton( label='Item Related', underline=0, variable=globalData.boolSettings['subActionFilterAttacks'], command=self.updateFilters )
		menu.add_checkbutton( label='Character Specific', underline=0, variable=globalData.boolSettings['subActionFilterAttacks'], command=self.updateFilters )

		# Determine spawn coordinates and display the menu
		rootDistanceFromScreenLeft, rootDistanceFromScreenTop = getWindowGeometry( globalData.gui.root )[2:]
		menu.post( rootDistanceFromScreenLeft+160, rootDistanceFromScreenTop+180 )

	def updateFilters( self ):

		globalData.saveProgramSettings()

	def getSubActionName( self, namePointer, index ):
		if namePointer == 0:
			return 'Entry ' + str( index + 1 )
		else:
			gameName = self.charFile.getString( namePointer ).split( 'ACTION_' )[1].split( '_figatree' )[0] # e.g. 'WallDamage'
			translatedName = self.charFile.subActionTranslations.get( gameName )

			if translatedName:
				#spaces = ' ' * ( 40 - (len(translatedName) + len(gameName)) )
				spaces = '     '
				return '{}{}{}'.format( translatedName, spaces, gameName )
			else:
				return gameName

	def hasUnsavedChanges( self ):
		# If the subAction struct hasn't been initialized/parsed, there's nothing to save
		if not self.subActionStruct:
			return False

		self.subActionStruct.rebuild()

		return ( self.subActionStruct.origData != self.subActionStruct.data )

	def subActionSelected( self, guiEvent ):

		""" Parses subAction events and updates the GUI. Called on selection of the subAction list. 
		
			Maybe a bug in Tkinter, but this may also be called upon the ListboxSelect of other Listboxes, 
			however it will not have a selection. Also, if debugging and breaking on this method it may appear 
			to be called multiple times upon ListboxSelect, however prints show it only being called once. """

		# Get the subAction index and values from the subaction entry
		selection = self.subActionList.curselection()
		if not selection:
			return
		index = selection[0]
		if index == self.lastSelection: # No change!
			return

		# Check for unsaved changes that the user might want
		if self.hasUnsavedChanges():
			proceed = tkMessageBox.askyesno( 'Unsaved Changes Detected', 'It appears there are unsaved changes with these events.\n\nDo you want to discard these changes?' )
			if proceed: # Discard changes
				self.subActionStruct.events = []
				self.subActionStruct.data = self.subActionStruct.origData
				self.subActionStruct.length = -1
			else:
				# Do not proceed; keep the previous selection and do nothing
				self.subActionList.selection_clear( 0, 'end' )
				self.subActionList.selection_set( self.lastSelection )
				return

		# Clear the events display pane
		self.displayPane.delete_all_items()
		
		# Commiting to this selection
		self.lastSelection = index
		index = self.listboxIndices[index] # Convert from listbox index to events table index
		namePointer, animOffset, animSize, eventsPointer, flags, _, _, _ = self.actionTable.getEntryValues( index )
		
		# Update general info display
		self.subActionIndex.set( 'SubAction Table Index:  0x{:X}'.format(index) )
		if animOffset == 0: # Assuming this is supposed to be null/no struct reference, rather than the struct at 0x20
			self.subActionAnimOffset.set( 'Animation (AJ) Offset:  Null' )
			self.subActionAnimSize.set( 'Animation (AJ) Size:  N/A' )
		else:
			self.subActionAnimOffset.set( 'Animation (AJ) Offset:  0x{:X}'.format(0x20+animOffset) )
			self.subActionAnimSize.set( 'Animation (AJ) Size:  0x{:X}'.format(animSize) )

		# Update flags display
		self.subActionFlags.set( 'SubAction Flags:  0x{:X}'.format(flags) )

		# Set the subActionStruct (and parse it) and the Events Offset/Size display
		if eventsPointer == 0: # Assuming this is supposed to be null/no struct reference, rather than the struct at 0x20
			self.subActionStruct = None
			self.subActionEventsOffset.set( 'Events Offset:  Null' )
			self.subActionEventsSize.set( 'Events Table Size:  N/A' )
		else:
			self.subActionEventsOffset.set( 'Events Offset:  0x{:X}'.format(0x20+eventsPointer) )

			# Get the subAction events structure and parse it
			try:
				self.subActionStruct = self.charFile.initDataBlock( SubAction, eventsPointer, self.actionTable.offset )
				self.subActionStruct.parse()
				self.subActionStruct.origData = self.subActionStruct.data
				self.subActionEventsSize.set( 'Events Table Size:  0x{:X}'.format(self.subActionStruct.getLength()) )
			except Exception as err:
				self.subActionStruct = None
				subActionName = self.getSubActionName( namePointer, index )
				printStatus( 'Unable to parse {} subAction (index {}); {}'.format(subActionName, index, err) )
				self.subActionEventsSize.set( 'Events Table Size:  N/A' )
				return

		# Show that there are no events to display if there are none (i.e. only has an End of Script event)
		if not self.subActionStruct or ( len(self.subActionStruct.events) == 1 and self.subActionStruct.events[0].id == 0 ):
			if not self.displayPaneMessage:
				self.displayPaneMessage = ttk.Label( self, text='No events' )
				self.displayPaneMessage.grid( column=2, row=2, sticky='n', pady=150 )
		else:
			if self.displayPaneMessage:
				self.displayPaneMessage.destroy()
				self.displayPaneMessage = None

			# Populate the events display pane
			self.displayPane.update_width()
			for event in self.subActionStruct.events:
				# Exit on End of Script event
				if event.id == 0:
					break

				# Create a GUI module for the event
				item = self.displayPane.create_item()
				helpMessage = self.charFile.eventNotes.get( '0x{:02X}'.format(event.id), '' )
				eM = EventModule( item, event, self.displayPane, helpMessage )
				eM.pack( fill='both', expand=True )
				item.eventModule = eM # Useful for the expand/collapse methods below

				# Add the GUI module to the display panel
				self.displayPane.add_item( item )

	def deleteEvent( self, guiEvent ):
		# Sanity checks; ensure there's something to delete and the GUI is still in sync (just in case)
		if len( self.displayPane._list_of_items ) == 0:
			return
		elif self.subActionStruct.events[-1].id == 0: # Last item is End of Script (not shown in GUI)
			assert len( self.displayPane._list_of_items ) == len( self.subActionStruct.events ) - 1, 'Mismatch between self.subActionStruct.events and GUI!'
		else:
			assert len( self.displayPane._list_of_items ) == len( self.subActionStruct.events ), 'Mismatch between self.subActionStruct.events and GUI!'

		# Check for a selected item and delete it from the GUI and the events list structure
		for i, item in enumerate( self.displayPane._list_of_items ):
			if item.selected:
				self.subActionStruct.deleteEvent( i )
				self.displayPane.delete_item( item )
				self.updateExpansionWarning()
				break

	def expandAll( self, guiEvent ):
		for item in self.displayPane._list_of_items:
			eM = item.eventModule
			
			# Use the method on the expand/collapse button to expand
			if eM.expandBtn and not eM.expanded:
				eM.expandBtn.toggle()

	def collapseAll( self, guiEvent ):
		for item in self.displayPane._list_of_items:
			eM = item.eventModule
			
			# Use the method on the expand/collapse button to collapse
			if eM.expanded: # No need to check for button; can't be expanded without it
				eM.expandBtn.toggle()

	def saveEventChanges( self, guiEvent ):
		if not self.subActionStruct:
			globalData.gui.updateProgramStatus( 'No subAction events struct has been loaded' )
			return
		
		# Construct a new bytearray for .data based on the current events
		self.subActionStruct.rebuild()
		if self.subActionStruct.origData == self.subActionStruct.data:
			globalData.gui.updateProgramStatus( 'No subAction data needs to be saved' )
			return
		self.subActionStruct.origData = self.subActionStruct.data

		# Save this new data to the file
		entry = self.actionTable.getEntryValues( self.lastSelection )
		subActionName = self.getSubActionName( entry[0], self.lastSelection )
		self.charFile.updateStruct( self.subActionStruct, 'SubAction event data for {} updated'.format(subActionName) )

		globalData.gui.updateProgramStatus( 'These subAction changes have been updated in the character file, but still need to be saved to the disc' )

	def reordered( self ):

		""" This is called on drag-and-drop reordering of the GUI's event modules, 
			and subsequently updates the order of events in the file structure. """
		
		# Determine the ordering change (these haven't been cleared by the time this is called)
		oldIndex = self.displayPane._index_of_selected_item
		newIndex = self.displayPane._index_of_empty_container

		# Move the event to the new index
		event = self.subActionStruct.events.pop( oldIndex )
		self.subActionStruct.events.insert( newIndex, event )

	def insertEventBefore( self, guiEvent ):
		# Get the index to insert above
		for i, item in enumerate( self.displayPane._list_of_items ):
			if item.selected:
				index = i
				break
		else: # No selected item
			index = 0

		self.insertEvent( index )

	def insertEventAfter( self, guiEvent ):
		# Get the index to insert above
		for i, item in enumerate( self.displayPane._list_of_items ):
			if item.selected:
				index = i + 1
				break
		else: # No selected item
			index = len( self.displayPane._list_of_items )

		self.insertEvent( index )

	def insertEvent( self, index ):
		# Prompt the user for the kind of event to add
		window = EventChooser( self.charFile, index )
		if not window.event: # User canceled
			return
		
		# Create a GUI module for the event
		item = self.displayPane.create_item()
		helpMessage = self.charFile.eventNotes.get( '0x{:02X}'.format(window.event.id), '' )
		eM = EventModule( item, window.event, self.displayPane, helpMessage, True )
		eM.pack( fill='both', expand=True )
		item.eventModule = eM # Useful for the expand/collapse methods below

		# Add the GUI module to the display panel and select it
		self.displayPane.add_item( item, index )
		self.displayPane._on_item_selected( item )

		# Add the event to the subAction/events data struct
		window.event.modified = True # Flag that its data needs to be packed
		self.subActionStruct.events.insert( index, window.event )

		# Expand the selection if editable fields are present (using the method on the expand/collapse button to expand)
		if eM.expandBtn:
			eM.expandBtn.toggle()

		self.updateExpansionWarning()

	def updateExpansionWarning( self ):

		""" Adds (or removes) the label warning about the subAction events structure 
			needing more file space, along with the button to provide details. """

		# Determine the length of the events struct as it is now
		newLength = 0
		for event in self.subActionStruct.events:
			newLength += event.length

		if newLength > self.subActionStruct.length:
			self.noteStringVar.set( 'Expansion required.' )

			# Add the info button if it's not there
			if not self.expandInfoBtn:
				self.expandInfoBtn = LabelButton( self.noteStringFrame, 'question', self.showExpansionInfo, 'Details' )
				self.expandInfoBtn.pack( side='right' )
		else:
			self.noteStringVar.set( '' )
			
			# Remove the info button if it's there
			if self.expandInfoBtn:
				self.expandInfoBtn.destroy()
				self.expandInfoBtn = None

	def showExpansionInfo( self, guiEvent ):
		# Determine the length of the events struct as it is now
		newLength = 0
		for event in self.subActionStruct.events:
			newLength += event.length

		diff = newLength - self.subActionStruct.length
		msg( ('The data for this structure is larger than the original, which means that saving '
			'it back into the file will require expanding the space at offset 0x{:X}. Data after '
			'this offset will be shifted forward by 0x{:X} bytes, and pointers following this '
			'offset will be recalculated.').format(self.subActionStruct.offset, diff), 'File Expansion Warning', warning=True )


class EventModule( ttk.Frame, object ):

	def __init__( self, parentItem, event, displayPane, helpMessage, newItem=False ):
		
		if newItem:
			# Define a slightly different appearance for new items
			globalData.gui.style.configure( 'NewEventItem.TFrame', background='#d7f0d7' )
			globalData.gui.style.configure( 'NewEventItem.TLabel', background='#d7f0d7' )

			self.frameStyle = 'NewEventItem.TFrame'
			self.labelStyle = 'NewEventItem.TLabel'
		else:
			self.frameStyle = None
			self.labelStyle = None
		
		super( EventModule, self ).__init__( parentItem, style=self.frameStyle )

		self.name = event.name
		self.event = event
		self.expanded = False
		self.ddList = displayPane
		self.helpMsg = helpMessage

		# Add the title, expand button, and info button
		headerRow = ttk.Frame( self, style=self.frameStyle )
		label = ttk.Label( headerRow, text=self.name, font=('Palatino Linotype', 11, 'bold'), style=self.labelStyle )
		label.pack( side='left', padx=(12,0), pady=(4,0) )
		
		if self.event.fields:
			self.expandBtn = ToggleButton( headerRow, 'expandArrow', self.toggleState, style=self.labelStyle )
			self.expandBtn.pack( side='left', padx=(12,0), pady=(3, 0) )
		else:
			self.expandBtn = None

		if self.helpMsg:
			helpBtn = LabelButton( headerRow, 'question', self.showHelp, 'Info', style=self.labelStyle )
			helpBtn.pack( side='right', padx=12, pady=(1, 0) )
		headerRow.pack( fill='x', expand=True )

		# Bind button release events to check for event drag-and-drop reordering
		#parentItem.bind_class( parentItem._tag, "<ButtonRelease-1>", self.dropped )

		if self.event.fields:
			self.bind( '<Double-Button-1>', self.expandBtn.toggle )
			label.bind( '<Double-Button-1>', self.expandBtn.toggle )
			headerRow.bind( '<Double-Button-1>', self.expandBtn.toggle )
		
	def toggleState( self, tkEvent=None ):
		if self.expanded:
			self.collapse()
		else:
			self.expand()

	def expand( self ):
		if self.expanded or not self.event.fields:
			return

		# Construct the event details labels
		containingFrame = ttk.Frame( self, style=self.frameStyle )
		index = 0

		for valueName, value in zip( self.event.fields, self.event.values ):
			if valueName == 'Padding':
				index += 1
				continue

			title = ttk.Label( containingFrame, text=valueName + ' :', style=self.labelStyle )
			title.grid( column=0, row=index, padx=15 )
			if self.event.fields:
				title.bind( '<Double-Button-1>', self.expandBtn.toggle )

			entry = Tk.Entry( containingFrame, width=12, justify='center', relief='flat', 
				highlightbackground='#b7becc', # Border color when not focused
				borderwidth=1, highlightthickness=1, highlightcolor='#78F' )
			entry.bind( '<Return>', self.updateValue )
			entry.index = index
			entry.insert( 0, value )
			entry.grid( column=1, row=index )
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

	def updateValue( self, tkEvent ):
		widget = tkEvent.widget

		try:
			self.tkEvent.updateValue( widget.index, widget.get() )

			# Change the background color of the widget, to show that changes have been made to it and are pending saving.
			self.configure( background='#faa' )
		except bitstring.CreationError as err:
			if err.startswith( 'bool token' ):
				message = 'A ' + err
			else:
				message = message[0].upper() + message[1:]
			msg( message, 'Invalid Value', warning=True )
		except Exception as err:
			msg( err, 'Value Encoding Error', error=True )

	def collapse( self ):
		if not self.expanded:
			return

		item = self.master

		for widget in self.winfo_children()[1:]:
			widget.destroy()

		self.ddList.update_item_height( item, self.ddList._item_height )

		self.expanded = False

	def showHelp( self, tkEvent ):
		title, message = self.helpMsg.split( '|' )
		msg( message, title )


class EventChooser( BasicWindow ):

	def __init__( self, charFile, index=None ):

		windowWidth = 320

		BasicWindow.__init__( self, globalData.gui.root, 'Add Event', resizable=True, minsize=(windowWidth, 600) )

		self.charFile = charFile
		self.event = None

		ttk.Label( self.window, text='Choose the type of event to add:' ).pack( pady=12 )
		
		# Add the events list and its scrollbar
		eventsListFrame = ttk.Frame( self.window )
		eventsScrollBar = Tk.Scrollbar( eventsListFrame, orient='vertical' )
		self.eventsList = Tk.Listbox( eventsListFrame, yscrollcommand=eventsScrollBar.set, activestyle='none', selectbackground='#78F' )
		eventsScrollBar.config( command=self.eventsList.yview )
		for eventId in range( 1, 0x3C ):
			eventName = SubAction.eventDesc[eventId][0]
			self.eventsList.insert( eventId, '{}    (0x{:02X} | 0x{:02X})'.format(eventName, eventId, eventId * 4) )
		self.eventsList.bind( '<<ListboxSelect>>', self.eventSelected )
		self.eventsList.grid( column=0, row=1, sticky='nsew' )
		eventsScrollBar.grid( column=1, row=1, sticky='ns' )
		eventsListFrame.pack( fill='both', expand=True, padx=8 )
		
		eventsListFrame.columnconfigure( 0, weight=1 )
		eventsListFrame.columnconfigure( 1, weight=0 ) # Scrollbar
		eventsListFrame.rowconfigure( 1, weight=1 )

		self.helpText = Tk.StringVar()
		ttk.Label( self.window, textvariable=self.helpText, wraplength=windowWidth-20 ).pack( padx=10, pady=(14, 0) )

		buttonsFrame = ttk.Frame( self.window )
		ttk.Button( buttonsFrame, text='Cancel', command=self.cancel ).pack( side='left', padx=20 )
		ttk.Button( buttonsFrame, text='Submit', command=self.submit ).pack( side='left', padx=20 )
		buttonsFrame.pack( expand=False, pady=14 )

		# Make this window modal (will not allow the user to interact with main GUI until this is closed)
		self.window.grab_set()
		globalData.gui.root.wait_window( self.window )

	def getEventCode( self ):
		# Get the selection and its index
		selection = self.eventsList.curselection()
		if not selection:
			return None
		else:
			return selection[0] + 1 # Need to add 1 since EoS event is excluded from list

	def eventSelected( self, guiEvent ):

		""" Pulls from the CharDataTranslations.json file, which also contains notes on events purposes. """

		eventCode = self.getEventCode()
		if not eventCode: return

		eventNote = self.charFile.eventNotes.get( '0x{:02X}'.format(eventCode), '' )
		if eventNote:
			self.helpText.set( eventNote.split( '|' )[1] ) # Removes title
		else:
			self.helpText.set( '' )

	def cancel( self ):
		self.event = None
		self.close()

	def submit( self ):
		eventCode = self.getEventCode()
		if not eventCode: return

		# Create an event object
		eventDesc = SubAction.eventDesc[eventCode]
		length = eventDesc[1]
		eventData = bytearray( length )
		self.event = SubActionEvent( eventCode, eventDesc[0], length, eventDesc[2], eventDesc[3], eventData )
		
		self.close()