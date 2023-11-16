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
from FileSystem.disc import Disc
from basicFunctions import reverseDictLookup, msg, printStatus

# Internal Dependencies
import globalData
from FileSystem.charFiles import ActionTable, CharDataFile, SubAction, SubActionEvent
from guiSubComponents import (
	AnimationChooser, BasicWindow, ColoredLabelButton, DDList, FlagDecoder, HexEditEntry, 
	LabelButton, ToggleButton, ToolTip, VerticalScrolledFrame, getNewNameFromUser )


class CharModding( ttk.Notebook ):

	# Icon texture indexes within IfAll.usd
	iconIndices = { 'Ca': 70, 'Dk': 74, 'Fx': 75, 'Gw': 76, 'Kb': 77, 'Kp': 78, 'Lk': 79, 
					'Lg': 80, 'Mr': 81, 'Ms': 82, 'Mt': 83, 'Nn': 87, 'Ns': 84, 'Pe': 85, 
					'Pk': 86, 'Pp': 87, 'Pr': 88, 'Ss': 89, 'Ys': 90, 'Zd': 91, 'Sk': 98, 
					'Fc': 92, 'Cl': 93, 'Dr': 94, 'Fe': 95, 'Pc': 96, 'Gn': 97, 
					
					'Mh': 192, 'Bo': 191, 'Gl': 191, 'Gk': 202, 'Ch': 193, 'Sb': 196 }

	def __init__( self, parent, mainGui ):

		ttk.Notebook.__init__( self, parent )

		# Add this tab to the main GUI, and add drag-and-drop functionality
		mainGui.mainTabFrame.add( self, text=' Character Modding ' )
		mainGui.dnd.bindtarget( self, mainGui.dndHandler, 'text/uri-list' )

		# Add the main selection tab
		self.selectionTab = ttk.Frame( self )
		self.selectionTab.charFile = None
		self.add( self.selectionTab, text=' Character Selection ' )
		self.extSearch = Tk.StringVar( value='.dat' )

		ttk.Label( self.selectionTab, text="Choose the character(s) you'd like to modify:" ).pack( padx=20, pady=20 )

		# Collect character icon images
		self.getIconTexturesInfo()
			
		self.charBtnsTab = ttk.Frame( self.selectionTab )
		self.populateCharButtons()
		self.charBtnsTab.pack( pady=20 )

		self.radioButtonsFrame = None
		self.checkToAddModeButtons()

	def getIconTexturesInfo( self ):

		""" Gets the IfAll file from disc, which contains the icons used on the buttons. 
			Also fetches texture information in order to get said icon textures. """

		if globalData.disc.is20XX:
			self.ifAllFile = globalData.disc.getFile( 'IfAl1.usd' )
		else:
			self.ifAllFile = globalData.disc.getFile( 'IfAll.usd' )
		if self.ifAllFile:
			self.texturesInfo = self.ifAllFile.identifyTextures()
			# print( 'found {} textures'.format(len(self.texturesInfo)) )
			# for i, info in enumerate(self.texturesInfo):
			# 	print( i, hex(info[0] + 0x20) )
		else:
			self.texturesInfo = None

	def checkToAddModeButtons( self ):

		""" Adds the radio mode/selector buttons to choose SDR/PAL character files if this is 20XX. 
			Or removes them if this is not 20XX. """

		# Add Radio buttons to switch to SDR/PAL variations if this is 20XX
		if globalData.disc.is20XX:
			if not self.radioButtonsFrame:
				self.radioButtonsFrame = ttk.Frame( self.selectionTab )
				ttk.Radiobutton( self.radioButtonsFrame, text='Vanilla', value='.dat', variable=self.extSearch, command=self.populateCharButtons ).pack( side='left' )
				ttk.Radiobutton( self.radioButtonsFrame, text='SD Remix', value='.sat', variable=self.extSearch, command=self.populateCharButtons ).pack( side='left' )
				ttk.Radiobutton( self.radioButtonsFrame, text='PAL', value='.pat', variable=self.extSearch, command=self.populateCharButtons ).pack( side='left' )
				self.radioButtonsFrame.pack()

		elif self.radioButtonsFrame:
			self.radioButtonsFrame.destroy()
			self.radioButtonsFrame = None

	def populateCharButtons( self ):

		""" Scans the disc for 'Pl__.dat' files to populate the main tab with character choices. """

		# Remove existing buttons
		for btn in self.charBtnsTab.winfo_children():
			btn.destroy()

		specialCharRow = 1
		column = 0
		row = 0
		for fileObj in globalData.disc.files.values():
			# Filter to just the character data files
			if not isinstance( fileObj, CharDataFile ) or not fileObj.filename.endswith( self.extSearch.get() ):
				continue
			elif fileObj.charAbbr == 'Kb' and 'Cp' in fileObj.filename: # Skip Kirby copy ft data files
				continue

			# Try to get the character's icon texture
			if self.texturesInfo:
				textureIndex = self.iconIndices.get( fileObj.charAbbr, 71 )
				texOffset, _, _, _, texWidth, texHeight, texType, _ = self.texturesInfo[textureIndex]
				icon = self.ifAllFile.getTexture( texOffset, texWidth, texHeight, texType )
			else:
				icon = None

			# Create the button
			button = ttk.Button( self.charBtnsTab, image=icon, text=' ' + fileObj.charName, compound=Tk.LEFT, width=22 )
			button.charFile = fileObj
			button.icon = icon # Stored to prevent garbage collection
			button.bind( '<1>', self.selectCharacter )

			# Place the buttons for special characters (Wireframes, Master Hand, etc.)
			if fileObj.charAbbr in ( 'Bo', 'Gl', 'Mh', 'Ch', 'Gk', 'Sb' ):
				button.grid( column=3, row=specialCharRow, padx=10 )
				specialCharRow += 1
				
			# Place buttons for the normal cast
			else:
				button.grid( column=column, row=row, padx=10 )
				row += 1

				if row >= 9:
					column += 1
					row = 0

	def repopulate( self ):

		""" Reloads data in the GUI from the disc. Should be called when a new disc is loaded. """

		disc = globalData.disc

		# Reload the IfAll file (for icon textures) and re-fetch icon/texture information
		self.getIconTexturesInfo()

		# Make sure we search for .dat files if this isn't 20XX (otherwise, keep previous setting)
		if not disc.is20XX:
			self.extSearch.set( '.dat' )

		# Reload the character buttons (getting updated character files from the disc) and add mode selection
		self.populateCharButtons()
		self.checkToAddModeButtons()

		# Recreate character tabs
		for tabName in self.tabs():
			tabWidget = globalData.gui.root.nametowidget( tabName )
			if tabWidget.charFile:
				newCharFile = disc.getFile( tabWidget.charFile.filename )
				tabWidget.destroy()

				# Recreate the tab if a new character file was found
				if newCharFile:
					self.createCharacterTab( newCharFile )

	def selectCharacter( self, tkEvent ):

		""" Adds a new character to the main Character Modding notebook (if not already added). 
			This includes populating all sub-tabs for that character. """

		# Check if this tab has already been created
		for tabName in self.tabs():
			tabWidget = globalData.gui.root.nametowidget( tabName )
			if tabWidget.charFile and tabWidget.charFile.filename == tkEvent.widget.charFile.filename:
				# Found this tab already exists; select it
				self.select( tabWidget )
				return

		newCharNotebook = self.createCharacterTab( tkEvent.widget.charFile )

		# Switch tabs to this character
		self.select( newCharNotebook )

	def createCharacterTab( self, charFile ):

		""" Creates and returns a new tab (a notebook widget) for a character tab. """
		
		# Create a new character tab and attach the character file for reference
		newCharNotebook = ttk.Notebook( self )
		newCharNotebook.charFile = charFile

		# Name the tab and add it to the notebook
		if charFile.charAbbr == 'Nn': charName = ' Nana'
		elif charFile.charAbbr == 'Pp': charName = ' Popo'
		else: charName = ' ' + newCharNotebook.charFile.charName
		filename = newCharNotebook.charFile.filename
		if filename.endswith( '.sat' ): charName += ' (SDR)'
		elif filename.endswith( '.pat' ): charName += ' (PAL)'
		self.add( newCharNotebook, text=charName )

		# # Add the fighter/character properties tab
		# newTab = CharGeneralEditor( newCharNotebook )
		# newCharNotebook.add( newTab, text=' Character Identity ' ) # General

		# Add the fighter/character properties tab
		newTab = self.buildPropertiesTab( newCharNotebook )
		newCharNotebook.add( newTab, text=' Properties ' )

		# Add the tab for action states editing
		newCharNotebook.subActionEditor = ActionEditor( newCharNotebook )
		newCharNotebook.add( newCharNotebook.subActionEditor, text=' Moves Modding ' )

		return newCharNotebook

	def buildPropertiesTab( self, parent ):
		
		""" Adds General Fighter Properties and Special Character Attributes to a character tab. """
		
		propertiesTab = ttk.Frame( parent )

		ttk.Label( propertiesTab, text='General Fighter Properties' ).grid( column=0, row=0, pady=12 )
		ttk.Label( propertiesTab, text='Special Character Attributes' ).grid( column=1, row=0 )

		# Collect general properties
		propStruct = parent.charFile.getGeneralProperties()
		propertyValues = propStruct.getValues()
		if not propertyValues:
			msg( message='Unable to get fighter properties for {}. Most likely there was a problem initializing the Pl__.dat file.'.format(parent.charFile.charName), 
				 title='Unable to get Struct Values', 
				 parent=globalData.gui,
				 error=True )
			return

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

			fieldLabel = ttk.Label( structTable.interior, text=propertyName + ':', wraplength=200, justify='center' )
			fieldLabel.grid( column=0, row=row, padx=(25, 10), sticky='e', pady=verticalPadding )
			if formatting == 'I':
				typeName = 'Integer'
			else:
				typeName = 'Float'
			ToolTip( fieldLabel, text='Offset in struct: 0x{:X}\nOffset in file: 0x{:X}\nType: {}'.format(offset, 0x20 + absoluteFieldOffset, typeName), delay=300 )

			# Add an editable field for the raw hex data
			hexEntry = HexEditEntry( structTable.interior, parent.charFile, absoluteFieldOffset, fieldByteLength, formatting, propertyName, width=11 )
			rawData = propStruct.data[offset:offset+fieldByteLength]
			hexEntry.insert( 0, hexlify(rawData).upper() )
			hexEntry.grid( column=1, row=row, pady=verticalPadding )
			
			# Add an editable field for this field's actual decoded value (and attach the hex edit widget for later auto-updating)
			valueEntry = HexEditEntry( structTable.interior, parent.charFile, absoluteFieldOffset, fieldByteLength, formatting, propertyName, valueEntry=True, width=15 )
			valueEntry.set( value )
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

		# Create the properties table for Special Character Attributes
		structTable = VerticalScrolledFrame( propertiesTab )
		currentSection = ''
		offset = 0
		row = 0
		for name, formatting, value, note in zip( attrStruct.fields, attrStruct.formatting[1:], propertyValues, attrStruct.notes ):
			propertyName = name.replace( '_', ' ' )

			absoluteFieldOffset = attrStruct.offset + offset
			verticalPadding = ( 0, 0 )

			# Split section and value names, if present
			if '|' in propertyName:
				nextSection, propertyName = propertyName.split( '|', 1 )
				if not propertyName:
					propertyName = 'Unknown 0x{:X}'.format( offset )
			else:
				nextSection = ''
			
			# Add a section header if appropriate
			if nextSection and nextSection != currentSection:
				ttk.Label( structTable.interior, text=nextSection ).grid( columnspan=3, column=0, row=row, padx=(100, 10), pady=(14, 6) )
				currentSection = nextSection
				row += 1

			# Add the property label and a tooltip for it
			fieldLabel = ttk.Label( structTable.interior, text=propertyName + ':', wraplength=200, justify='center' )
			fieldLabel.grid( column=0, row=row, padx=(25, 10), sticky='e', pady=verticalPadding )
			if formatting == 'I':
				typeName = 'Integer'
			else:
				typeName = 'Float'
			toolTipText = 'Offset in struct: 0x{:X}\nOffset in file: 0x{:X}\nType: {}'.format(offset, 0x20 + absoluteFieldOffset, typeName)
			if note:
				toolTipText += '\n\n' + note
			ToolTip( fieldLabel, text=toolTipText, delay=300, wraplength=400 )

			# Add an editable field for the raw hex data
			hexEntry = HexEditEntry( structTable.interior, parent.charFile, absoluteFieldOffset, 4, formatting, propertyName, width=11 )
			rawData = attrStruct.data[offset:offset+4]
			hexEntry.insert( 0, hexlify(rawData).upper() )
			hexEntry.grid( column=1, row=row, pady=verticalPadding )
			
			# Add an editable field for this field's actual decoded value (and attach the hex edit widget for later auto-updating)
			valueEntry = HexEditEntry( structTable.interior, parent.charFile, absoluteFieldOffset, 4, formatting, propertyName, valueEntry=True, width=15 )
			valueEntry.set( value )
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

		# Check each Action Editor tab for changes
		for tabName in self.tabs():
			# Get the character tab
			tabWidget = globalData.gui.root.nametowidget( tabName )

			if not tabWidget.charFile: continue # Skip main selection tab
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


class ActionEditor( ttk.Frame, object ):

	def __init__( self, parent ):
		super( ActionEditor, self ).__init__( parent )

		self.charFile = parent.charFile
		self.actionTable = self.charFile.getActionTable()
		self.subActionStruct = None
		self.lastSelection = -1

		# Add the action table pane's title
		self.tableTitleVar = Tk.StringVar()
		ttk.Label( self, textvariable=self.tableTitleVar ).grid( column=0, columnspan=2, row=0, pady=4 )

		filtersBox = ttk.Frame( self )
		ttk.Checkbutton( filtersBox, text='Attacks', variable=globalData.boolSettings['actionStateFilterAttacks'] ).grid( column=0, row=0, sticky='w' )
		ttk.Checkbutton( filtersBox, text='Movement', variable=globalData.boolSettings['actionStateFilterMovement'] ).grid( column=0, row=1, sticky='w' )
		ttk.Checkbutton( filtersBox, text='Item Related', variable=globalData.boolSettings['actionStateFilterItems'] ).grid( column=1, row=0, sticky='w', padx=(10, 0) )
		ttk.Checkbutton( filtersBox, text='Character Specific', variable=globalData.boolSettings['actionStateFilterCharSpecific'] ).grid( column=1, row=1, sticky='w', padx=(10, 0) )
		ttk.Checkbutton( filtersBox, text='Empty Entries', variable=globalData.boolSettings['actionStateFilterEmpty'] ).grid( column=2, row=0, sticky='w', padx=(8, 0) )
		filtersBox.grid( column=0, columnspan=2, row=1, pady=3 )

		# Attach traces to the filter booleans, to update the GUI even if these are changed in ways besides clicking on the above checkboxes
		globalData.boolSettings['actionStateFilterAttacks'].trace( 'w', self.updateFilters )
		globalData.boolSettings['actionStateFilterMovement'].trace( 'w', self.updateFilters )
		globalData.boolSettings['actionStateFilterItems'].trace( 'w', self.updateFilters )
		globalData.boolSettings['actionStateFilterCharSpecific'].trace( 'w', self.updateFilters )
		globalData.boolSettings['actionStateFilterEmpty'].trace( 'w', self.updateFilters )

		# Add the action table list and its scrollbar
		subActionScrollBar = Tk.Scrollbar( self, orient='vertical' )
		self.subActionList = Tk.Listbox( self, width=44, yscrollcommand=subActionScrollBar.set, 
										activestyle='none', selectbackground='#78F', exportselection=0, font=('Consolas', 9) )
		subActionScrollBar.config( command=self.subActionList.yview )
		self.subActionList.bind( '<<ListboxSelect>>', self.subActionSelected )
		self.subActionList.grid( column=0, row=2, sticky='ns' )
		subActionScrollBar.grid( column=1, row=2, sticky='ns' )

		# Pane for showing subAction events (empty for now)
		ttk.Label( self, text='SubAction Events (a.k.a. ftcmd script):' ).grid( column=2, row=0 )
		scrollPane = VerticalScrolledFrame( self )
		self.displayPane = DDList( scrollPane.interior, 500, 40, item_borderwidth=2, reorder_callback=self.reordered, offset_x=2, offset_y=2, gap=2 )
		self.displayPane.pack( fill='both', expand=True )
		scrollPane.grid( column=2, row=1, rowspan=2, sticky='nsew' )
		self.displayPaneMessage = ttk.Label( self, text='< - Select an Action on\n  the left to begin.', justify='center' )
		self.displayPaneMessage.grid( column=2, row=2, sticky='n', pady=150 )

		# Pane for general info display and editing controls
		infoPane = ttk.Frame( self )
		generalInfoBox = ttk.Labelframe( infoPane, text='  Selected Action  ', padding=(20, 5) )
		self.subActionIndex = Tk.StringVar()
		self.entryOffset = Tk.StringVar()
		ttk.Label( generalInfoBox, textvariable=self.subActionIndex ).pack()
		ttk.Label( generalInfoBox, textvariable=self.entryOffset ).pack()

		flagsFrame = ttk.Frame( generalInfoBox )
		self.subActionFlags = Tk.StringVar()
		ttk.Label( flagsFrame, textvariable=self.subActionFlags ).pack( side='left', padx=4, pady=(7, 0) )
		self.flagsBtn = ColoredLabelButton( flagsFrame, 'flag', self.editFlags, 'Edit Flags for this Action' )
		self.flagsBtn.disable()
		self.flagsBtn.pack( side='left', pady=(7, 0) )
		flagsFrame.pack()

		generalInfoBox.pack( fill='x', expand=True )

		self.eventsFrame = ttk.Labelframe( infoPane, text='  SubAction Events  ', padding=(20, 5) )
		self.subActionEventsOffset = Tk.StringVar()
		self.subActionEventsSize = Tk.StringVar()
		ttk.Label( self.eventsFrame, textvariable=self.subActionEventsOffset ).grid( column=0, columnspan=5, row=0 )
		ttk.Label( self.eventsFrame, textvariable=self.subActionEventsSize ).grid( column=0, columnspan=5, row=1 )
		ColoredLabelButton( self.eventsFrame, 'delete', self.deleteEvent, 'Delete Event', '#f04545' ).grid( column=0, row=2, pady=4, padx=4 )
		ColoredLabelButton( self.eventsFrame, 'expand', self.expandAll, 'Expand All' ).grid( column=1, row=2, pady=4, padx=4 )
		ColoredLabelButton( self.eventsFrame, 'collapse', self.collapseAll, 'Collapse All' ).grid( column=2, row=2, pady=4, padx=4 )
		ColoredLabelButton( self.eventsFrame, 'save', self.saveEventChanges, 'Save Changes\nto Charcter File', '#292' ).grid( column=3, row=2, pady=4, padx=4 )
		insertBtn = LabelButton( self.eventsFrame, 'insert', self.insertEventBefore, 'Insert New Event\n\n(Before selection. Shift-click\nto insert after selection.)' )
		insertBtn.bind( '<Shift-Button-1>', self.insertEventAfter )
		insertBtn.grid( column=4, row=2, pady=4, padx=4 )
		ttk.Button( self.eventsFrame, text='Restore to Vanilla', command=self.restoreEvents ).grid( column=0, columnspan=5, row=3, ipadx=12, pady=4 )
		self.eventsNotice = None
		self.expandInfoBtn = None
		self.eventsFrame.columnconfigure( 'all', weight=1 )
		self.eventsFrame.pack( fill='x', expand=True, pady=42 )
		
		animBox = ttk.Labelframe( infoPane, text='  SubAction Animation  ', padding=(20, 5) )
		self.actionAnimOffset = Tk.StringVar()
		self.actionAnimSize = Tk.StringVar()
		ttk.Label( animBox, textvariable=self.actionAnimOffset ).pack()
		ttk.Label( animBox, textvariable=self.actionAnimSize ).pack()
		ttk.Button( animBox, text='Change Animation', command=self.changeAnimation ).pack( ipadx=12, pady=4 )
		animBox.pack( fill='x', expand=True )

		# ttk.Button( infoPane, text='Test Character', command=self.testCharacter ).pack( pady=(42, 0), ipadx=12 )

		infoPane.grid( column=3, row=1, rowspan=2, sticky='ew', padx=20, pady=0 )

		# Configure row/column stretch and resize behavior
		self.columnconfigure( 0, weight=0 ) # SubAction Events Listbox
		self.columnconfigure( 1, weight=0 ) # Scrollbar
		self.columnconfigure( 2, weight=2 ) # Events display pane
		self.columnconfigure( 3, weight=0 ) # Info display
		self.rowconfigure( 0, weight=0 ) # Titles
		self.rowconfigure( 1, weight=0 ) # Main content
		self.rowconfigure( 2, weight=1 ) # Main content
		
		self.subActionIndex.set( 'Table Index:    ' )
		self.entryOffset.set( 'Entry Offset:    ' )
		self.subActionFlags.set( 'State Flags:    ' )
		self.subActionEventsOffset.set( 'Events Offset:    ' )
		self.subActionEventsSize.set( 'Events Table Size:    ' )
		self.actionAnimOffset.set( 'Animation (AJ) Offset:    ' )
		self.actionAnimSize.set( 'Animation (AJ) Size:    ' )

		self.populate()

	def populate( self ):

		""" Clears the subAction list (if it has anything displayed) and 
			repopulates it with entries from the character's action table. """
		
		self.listboxIndices = {} # Key = listboxIndex (entry in the widget), value = actionTableEntryIndex

		title = '{} Action States Table   (0x{:X}):'.format( self.charFile.filename, self.actionTable.offset + 0x20 )
		self.tableTitleVar.set( title )

		showAttacks = globalData.checkSetting( 'actionStateFilterAttacks' )
		showMovement = globalData.checkSetting( 'actionStateFilterMovement' )
		showItems = globalData.checkSetting( 'actionStateFilterItems' )
		showCharSpecific = globalData.checkSetting( 'actionStateFilterCharSpecific' )
		showEmpty = globalData.checkSetting( 'actionStateFilterEmpty' )

		# Repopulate the subAction list
		self.subActionList.delete( 0, 'end' )
		listboxIndex = 0
		for entryIndex, values in self.actionTable.iterateEntries():
			namePointer = values[0]

			if namePointer == 0:
				if not showEmpty:
					continue
				else:
					gameName, friendlyName = self.getActionName( namePointer, entryIndex )

			else:
				gameName, friendlyName = self.getActionName( namePointer, entryIndex )
				nameStart = gameName[:4]

				# Apply filters and skip unwanted actions
				if not showAttacks:
					if nameStart in ( 'Atta', 'Catc', 'Thro' ) or gameName.startswith( 'DownAttack' ):
						continue
					elif gameName.startswith( 'CliffAttack' ):
						continue
					# Check for certain 'Taro' moves, like Koopa Klaw and Kong Karry
					elif gameName.startswith( 'T' + self.charFile.nickname ):
						continue
					
				if not showMovement:
					if nameStart in ( 'Wall', 'Dama', 'Wait', 'Walk', 'Turn', 'Dash', 'Run', 'RunB', 'Land' ):
						continue
					elif nameStart in ( 'Jump', 'Fall', 'Squa', 'Guar', 'Esca', 'Rebo', 'Down', 'Pass' ):
						if not gameName.startswith( 'DownAttack' ):
							continue
					elif nameStart in ( 'Fura', 'Otto', 'Stop', 'Miss', 'Clif', 'Entr', 'Appe', 'Capt' ):
						if not gameName.startswith( 'CliffAttack' ):
							continue
					# elif friendlyName.startswith( 'Opponent Thrown' ):
					# 	continue

				if not showItems:
					if nameStart in ( 'Ligh', 'Heav', 'Swin', 'Item' ):
						continue

				if not showCharSpecific and entryIndex > 0x126:
					continue
			
			# Add the action to the listbox
			self.subActionList.insert( listboxIndex, ' ' + friendlyName )
			self.listboxIndices[listboxIndex] = entryIndex

			# Color the entry gray if it's a blank entry
			if not namePointer:
				self.subActionList.itemconfigure( listboxIndex, foreground='#6A6A6A' )
			listboxIndex += 1

		# Clear current selection, and then select the same item that was selected before (if it's still present)
		self.subActionList.selection_clear( 0, 'end' )
		listboxIndex = self.getListboxFromActionIndex( self.lastSelection )
		if listboxIndex != -1:
			self.subActionList.selection_set( listboxIndex )
			self.subActionList.see( listboxIndex )

	def getListboxFromActionIndex( self, index ):

		""" Gets and returns the listbox index (item/line index in the GUI's widget)
			for a given entry index in the action states table. """

		return reverseDictLookup( self.listboxIndices, index, -1 )

	def updateFilters( self, name, idx, mode ):

		""" Repopulates action states shown in the left-side listbox, 
			according to the current filters, and saves current settings. 
			Called by the filter checkboxes in the GUI when toggled. """

		self.populate()
		globalData.saveProgramSettings()

	def getActionName( self, namePointer, index, useParenthesis=False ):

		""" Gets the game's symbol name from a given string pointer, and 
			translates it into a more friendly/human-readable name. 
			Returns both the game name and the friendly name. """

		if namePointer == 0:
			index += 1
			if index > 9:
				return '', 'Entry {} (0x{:X})'.format( index, index )
			else:
				return '', 'Entry {}'.format( index )

		else:
			gameName, friendlyName = self.charFile.getFriendlyActionName( None, namePointer, index )

			if friendlyName:
				if useParenthesis:
					friendlyName = '{} ({})'.format( friendlyName, gameName )
				else:
					spaces = ' ' * ( 42 - (len(friendlyName) + len(gameName)) )
					friendlyName = '{}{}{}'.format( friendlyName, spaces, gameName )
			else:
				friendlyName = gameName

			return gameName, friendlyName

	def hasUnsavedChanges( self ):

		""" Checks if the currently selected action has unsaved changes to its subAction events. """

		# If the subAction struct hasn't been initialized/parsed, there's nothing to save
		if not self.subActionStruct:
			return False

		self.subActionStruct.rebuild()

		# If the reconstructed data is identical, there are no changes
		if self.subActionStruct.origData == self.subActionStruct.data:
			return False

		# Check if the difference is simply due to padding
		elif len( self.subActionStruct.origData ) > len( self.subActionStruct.data ):
			excessData = self.subActionStruct.origData[len(self.subActionStruct.data):]
			if any( excessData ): # Returns True if there are any non-zero bytes (meaning it's not padding)
				return True
			else:
				return False # All the extra data is zeroes (more than likely just padding)

		else: # The new data is larger than the original
			return True

	def subActionSelected( self, guiEvent=None, checkForUnsavedChanges=True ):

		""" Parses subAction events and updates the GUI. Called on selection of the subAction list. 
			Note that we track self.lastSelection using the action table index, because the listbox 
			index may change due to filtering.

			Maybe a bug in Tkinter, but this may also be called upon the ListboxSelect of other Listboxes, 
			however it will not have a selection. Also, if debugging and breaking on this method it may appear 
			to be called multiple times upon ListboxSelect, however prints show it only being called once. """

		# Ensure we can get a selection
		selection = self.subActionList.curselection()
		if not selection:
			return
		listBoxIndex = selection[0]

		# Check if the current action selection has changed
		if listBoxIndex == self.getListboxFromActionIndex( self.lastSelection ): # No change!
			return

		# Check for unsaved changes that the user might want to keep
		if checkForUnsavedChanges and self.hasUnsavedChanges():
			proceed = tkMessageBox.askyesno( 'Unsaved Changes Detected', 'It appears there are unsaved changes to the subAction events.\n\nDo you want to discard these changes?' )
			if proceed: # Discard changes
				self.subActionStruct.events = []
				self.subActionStruct.data = self.subActionStruct.origData
				self.subActionStruct.length = -1
			else:
				# Do not proceed; keep the previous selection and do nothing
				self.subActionList.selection_clear( 0, 'end' )
				self.subActionList.selection_set( self.getListboxFromActionIndex(self.lastSelection) )
				return

		# Clear the events display pane and reset the scrollbar
		self.displayPane.delete_all_items()
		self.displayPane.master.master.yview_moveto( 0 )

		# Commiting to this selection. Get information on it
		actionTableIndex = self.listboxIndices[listBoxIndex] # Convert from listbox index to actions table index
		self.lastSelection = actionTableIndex
		namePointer, animOffset, animSize, eventsPointer, flags, _, _, _ = self.actionTable.getEntryValues( actionTableIndex )

		# Update general info display
		self.subActionIndex.set( 'Table Index:  0x{:X}'.format(actionTableIndex) )
		entryOffset = 0x20 + self.actionTable.offset + ( actionTableIndex * 0x18 )
		self.entryOffset.set( 'Entry Offset:  0x{:X}'.format(entryOffset) )
		if animOffset == 0: # Assuming this is supposed to be null/no struct reference, rather than the struct at 0x20
			#self.targetAnimName.set( 'Target Animation:  N/A' )
			self.actionAnimOffset.set( 'Animation (AJ) Offset:  Null' )
			self.actionAnimSize.set( 'Animation (AJ) Size:  N/A' )
		else:
			# Try to get the animation file to see what animation is pointed to
			# ajFile, filename = self.getAnimFile()
			# if ajFile:
			# 	ajFile.initialize()
			# 	for anim in ajFile.animations:
			# 		if anim.offset == animOffset:
			# 			gameName = anim.name.split( '_' )[3]
			# 			if len( gameName ) > 8:
			# 				self.targetAnimName.set( 'Target Animation:\n' + gameName )
			# 			else:
			# 				self.targetAnimName.set( 'Target Animation:  ' + gameName )
			# 			break
			# 	else: # The loop above didn't break
			# 		self.targetAnimName.set( 'Target Animation:\nNot Found!' )
			# else:
			# 	printStatus( 'Unable to find an animation file ({}) in the disc!'.format(filename), warning=True )
			# 	self.targetAnimName.set( 'Target Animation:  N/A' )

			self.actionAnimOffset.set( 'Animation (AJ) Offset:  0x{:X}'.format(0x20+animOffset) )
			self.actionAnimSize.set( 'Animation (AJ) Size:  0x{:X}'.format(animSize) )

		# Update flags display
		self.subActionFlags.set( 'State Flags:  0x{:02X}'.format(flags) )
		self.flagsBtn.enable()

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
				actionName = self.getActionName( namePointer, actionTableIndex )[1]
				printStatus( 'Unable to parse {} subAction (index {}); {}'.format(actionName, actionTableIndex, err) )
				self.subActionEventsSize.set( 'Events Table Size:  N/A' )
				return

		# Show that there are no events to display if there are none (i.e. only has an End of Script event)
		if not self.subActionStruct or ( len(self.subActionStruct.events) == 1 and self.subActionStruct.events[0].id == 0 ):
			if self.displayPaneMessage:
				self.displayPaneMessage['text'] = 'No events'
			else:
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
				helpMessage = self.charFile.getEventNotes( event.id )
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
				break
		
		self.updateExpansionWarning()

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

		""" Saves current subAction event changes to the current file. 
			These changes to the file still need to be saved to disc. """

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
		entryValues = self.actionTable.getEntryValues( self.lastSelection )
		actionName = self.getActionName( entryValues[0], self.lastSelection, useParenthesis=True )[1]
		self.charFile.updateStruct( self.subActionStruct, 'SubAction event data for {} updated'.format(actionName), 'SubAction events updated' )

		globalData.gui.updateProgramStatus( 'These subAction changes have been updated in the character file, but still need to be saved to the disc' )

	def restoreEvents( self ):

		""" Replaces the events (ftcmd script) of the currently selected action 
			with those from a vanilla disc. """

		# Ensure an action is selected
		selection = self.subActionList.curselection()
		if not selection:
			msg( 'No Action is selected!' )
			return
		elif not self.subActionStruct:
			msg( 'This action has no subAction events struct! The action has a null subAction events pointer, or the structure could not be initialized.' )
			return
		listBoxIndex = selection[0]
		actionTableIndex = self.listboxIndices[listBoxIndex] # Convert from listbox index to actions table index

		# Try to initialize the vanilla disc
		vanillaDiscPath = globalData.getVanillaDiscPath()
		if not vanillaDiscPath:
			printStatus( 'Unable to restore the file(s) without a vanilla disc to source from', warning=True )
			return
		vanillaDisc = Disc( vanillaDiscPath )
		vanillaDisc.load()

		# Get the vanilla character data file, and get the original events struct from it
		vCharFile = vanillaDisc.getFile( 'Pl{}.dat'.format(self.charFile.charAbbr) )
		vActionTable = vCharFile.getActionTable()
		vEventsPointer = vActionTable.getEntryValues( actionTableIndex )[3]
		vSubActionStruct = vCharFile.initDataBlock( SubAction, vEventsPointer, vActionTable.offset )
		vStructData = vSubActionStruct.data

		#assert vSubActionStruct.length <= self.subActionStruct.length, 'The vanilla subAction events structure is larger than the existing struct!'
		subActionStructSpace = self.charFile.getStructLength( self.subActionStruct.offset ) # Might be different than the current struct
		if vSubActionStruct.length < subActionStructSpace:
			padding = bytearray( subActionStructSpace - vSubActionStruct.length )
			vStructData.extend( padding )

		# Save the vanilla data to the current struct and update the file
		self.subActionStruct.data = vStructData
		self.subActionStruct.events = []
		namePointer = self.actionTable.getEntryValues( actionTableIndex )[0]
		actionName = self.getActionName( namePointer, actionTableIndex, useParenthesis=True )[1]
		description = '{} subAction events restored to vanilla'.format( actionName )
		self.charFile.updateStruct( self.subActionStruct, description, 'SubAction events restored' )

		# Update the GUI
		self.lastSelection = -1
		self.subActionSelected( checkForUnsavedChanges=False )
		printStatus( description )
		self.updateExpansionWarning()

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
		helpMessage = self.charFile.getEventNotes( window.event.id )
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
			# Add the info button if it's not there
			if not self.expandInfoBtn:
				self.eventsNotice = ttk.Label( self.eventsFrame, text='Expansion required.', foreground='#a34343' )
				self.eventsNotice.grid( column=0, columnspan=4, row=4, pady=4 )
				self.expandInfoBtn = LabelButton( self.eventsFrame, 'question', self.showExpansionInfo, 'Details' )
				self.expandInfoBtn.grid( column=4, row=4 )
		else:
			# Remove the info button if it's there
			if self.expandInfoBtn:
				self.eventsNotice.destroy()
				self.eventsNotice = None
				self.expandInfoBtn.destroy()
				self.expandInfoBtn = None

	def showExpansionInfo( self, guiEvent ):

		""" Displays a pop-up to the user to explain data changes to the DAT file. 
			Called from clicking on the warning label that appears when expanding the 
			DAT file will be needed. """

		# Determine the length of the events struct as it is now
		newLength = 0
		for event in self.subActionStruct.events:
			newLength += event.length

		diff = newLength - self.subActionStruct.length
		msg( ('The data for this structure is larger than the original, which means that saving it '
			'back into the file will require expanding the space at offset 0x{:X}. Data after this '
			'offset will be shifted forward by at least 0x{:X} bytes, and pointers following this '
			'offset will be adjusted accordingly.').format(self.subActionStruct.offset, diff), 'File Expansion Warning', warning=True )

	def getAnimFile( self ):

		""" Returns the respective animation file object for the current 
			character, and the filename of the expected file. """

		disc = globalData.disc
		filename = 'Pl{}AJ.dat'.format( self.charFile.charAbbr )
		return disc.getFile( filename ), filename

	def changeAnimation( self ):

		""" Called by the 'Change Animation' button on the right-side panel. 
			Prompts the user to select an animation (from the AJ file), and then 
			updates the action table with the offset and size of that animation. 
			The action table name/string and the AJ file string must match, and 
			may also be renamed by this function. """

		# Ensure an action is selected
		selection = self.subActionList.curselection()
		if not selection:
			msg( 'No action is selected for editing!', 'Please Select an Action State' )
			return
		listBoxIndex = selection[0]

		# Get the associated animation file
		ajFile, filename = self.getAnimFile()
		if not ajFile:
			msg( 'The animation file for this character was not found in the disc! '
				'The expected file is "{}/{}".'.format(globalData.disc.gameId, filename), 'File Not Found', warning=True )
			return

		# Get the name of the currently selected action
		entryIndex = self.listboxIndices[listBoxIndex] # Convert from listbox index to actions table index
		origNamePointer, ajAnimOffset = self.actionTable.getEntryValues( entryIndex )[:2]
		origGameName, origFriendlyName = self.getActionName( origNamePointer, entryIndex, useParenthesis=True )

		# Prompt the user to choose an animation
		animSelectWindow = AnimationChooser( ajFile, self.charFile, initialSelectionAnimOffset=ajAnimOffset )
		animOffset = animSelectWindow.animOffset
		animGameName = animSelectWindow.gameName
		if animOffset == -1: # User canceled
			return

		# Check that the selected animation is actually new
		if animGameName == origGameName and animOffset == ajAnimOffset:
			msg( 'The action is already using that animation!', 'Animation Already Applied', warning=True )
			return

		# Find the pointer to the action string that matches the target animation's
		for _, values in self.actionTable.iterateEntries():
			namePointer = values[0]
			if namePointer != 0:
				symbol = self.charFile.getString( namePointer ) # e.g. 'PlyCaptain5K_Share_ACTION_AttackS3S_figatree'
				actionName = symbol.split( '_' )[3] # e.g. 'AttackS3S'
				if actionName == animGameName:
					break
		else: # The loop above didn't break; no matching symbol found
			msg( 'Unable to find a string referenced in the action table that matches the target animation.', 'Unable to Swap Animations', error=True )
			printStatus( 'A matching string from the action table could not be found' )
			return

		# Offer to update the action and animation strings
		message = ( 'You may enter a new name for this Action/Animation, or leave it as-is. If you do not change this, The action will appear in '
					"the Action States Table with the same name as your chosen animation. It's recommended to use a name which "
					'does not already appear in the animation file.' ) # todo: add validation to check for existing names
		newName = getNewNameFromUser( len(animGameName), None, message, animGameName, 30, False, 'Enter Action/Animation Name' )
		if not newName: # User canceled
			printStatus( 'Animation swap canceled' )
			return

		# Update the new name/string in the Pl__.dat and AJ files
		if newName != animGameName:
			symbolParts = symbol.rsplit( '_', 2 ) # Results in e.g. ['PlyCaptain5K_Share_ACTION', 'AttackS3S', 'figatree']
			symbolParts[-2] = newName
			newSymbol = '_'.join( symbolParts )
			symbolData = bytearray( newSymbol, encoding='utf-8' )

			# Add padding to clear extra bytes if the new name is smaller
			newNameLen = len( newName )
			if newNameLen < len( animGameName ):
				padding = len( animGameName ) - newNameLen
				symbolData.append( 0 )
				symbolData.extend( [0xFF] * padding )

			# Get the offset of the symbol string in the AJ file
			for anim in ajFile.animations:
				if anim.offset == animOffset:
					anim.initialize()
					anim.name = newSymbol
					ajStringOffset = 0x20 + animOffset + anim.headerInfo['stringTableStart']
					break
			else: # The loop above didn't break; unable to find the animation
				msg( 'Unable to find an animation at offset 0x{:X} in the animation file ({})!'.format(animOffset, ajFile.filename), 'Unable to Swap Animations', error=True )
				printStatus( 'Animation not found in AJ file' )
				return

			# Update the strings in both files
			stringChangeDescription = 'Animation name "{}" changed to "{}"'.format( origGameName, newName )
			self.charFile.updateData( namePointer, symbolData, stringChangeDescription )
			ajFile.updateData( ajStringOffset, symbolData, stringChangeDescription, 'Animation name updated' )

		# Create a user message/description for this change
		if animSelectWindow.friendlyName:
			description = 'Animation for {} changed to {} ({})'.format( origFriendlyName, animSelectWindow.friendlyName, animGameName )
		else:
			description = 'Animation for {} changed to {}'.format( origFriendlyName, animGameName )

		# Update the action table struct values
		self.charFile.updateStructValue( self.actionTable, 0, namePointer, trackChange=False, entryIndex=entryIndex )
		self.charFile.updateStructValue( self.actionTable, 1, animOffset, trackChange=False, entryIndex=entryIndex )
		self.charFile.updateStructValue( self.actionTable, 2, animSelectWindow.animSize, description, 'Animation swapped', entryIndex=entryIndex )

		# Update the GUI
		printStatus( description )
		# if len( animGameName ) > 8:
		# 	self.targetAnimName.set( 'Target Animation:\n' + animGameName )
		# else:
		# 	self.targetAnimName.set( 'Target Animation:  ' + animGameName )
		self.actionAnimOffset.set( 'Animation (AJ) Offset:  0x{:X}'.format(0x20+animSelectWindow.animOffset) )
		self.actionAnimSize.set( 'Animation (AJ) Size:  0x{:X}'.format(animSelectWindow.animSize) )

	def editFlags( self, guiEvent ):
		# Ensure an action is selected
		selection = self.subActionList.curselection()
		if not selection:
			msg( 'No Action is selected!' )
			return
		listBoxIndex = selection[0]

		# Get the index and other info on this action
		index = self.listboxIndices[listBoxIndex] # Convert from listbox index to actions table index
		namePointer = self.actionTable.getEntryValues( index )[0]
		actionName = self.getActionName( namePointer, index, useParenthesis=True )[1]

		FlagDecoder( self.actionTable, 4, index, actionName )

	# def testCharacter( self ):

	# 	""" Initialize a Micro Melee build, add the selected character to it 
	# 		(and necessary codes), and boot it up in Dolphin. """

	# 	# Get the micro melee disc object
	# 	microMelee = globalData.getMicroMelee()
	# 	if not microMelee: return # User may have canceled the vanilla melee disc prompt

	# 	microMelee.testCharacter( self.charFile, supplementaryFiles )


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

		# Add the button to expand this subAction if there are any non-padding fields
		for field in self.event.fields:
			if field != 'Padding':
				self.expandBtn = ToggleButton( headerRow, 'expandArrow', self.toggleState, style=self.labelStyle )
				self.expandBtn.pack( side='left', padx=(12,0), pady=(3, 0) )
				break
		else: # The loop above didn't break; no fields or they're all padding
			self.expandBtn = None

		if self.helpMsg:
			helpBtn = LabelButton( headerRow, 'question', self.showHelp, 'Info', style=self.labelStyle )
			helpBtn.pack( side='right', padx=12, pady=(1, 0) )
		headerRow.pack( fill='x', expand=True )

		if self.expandBtn:
			self.bind( '<Double-Button-1>', self.expandBtn.toggle )
			label.bind( '<Double-Button-1>', self.expandBtn.toggle )
			headerRow.bind( '<Double-Button-1>', self.expandBtn.toggle )

	def toggleState( self, tkEvent=None ):
		if self.expanded:
			self.collapse()
		else:
			self.expand()

	def expand( self ):
		if self.expanded or not self.expandBtn:
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
			self.event.updateValue( widget.index, widget.get() )

			# Change the background color of the widget, to show that changes have been made to it and are pending saving.
			widget.configure( background='#faa' )
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

		windowWidth = 350

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
		ttk.Label( self.window, textvariable=self.helpText, wraplength=windowWidth-24 ).pack( padx=10, pady=(14, 0) )

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

		eventNote = self.charFile.getEventNotes( eventCode )
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