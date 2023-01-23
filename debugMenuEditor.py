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

import ttk
import Tkinter as Tk

import globalData
import FileSystem.standaloneStructs as standaloneStructs


class DebugMenuEditor( ttk.Frame ):

	# This is a definition for menu line items in a more human-readable form
	friendlyTypes = { 
		0: '0 (Text only)', 
		1: '1 (Submenu)', 
		2: '2 (Left/Right String List)',
		3: '3 (Left/Right Int List)', 
		8: '8 (Left/Right Float List)', 
		9: '9 (End of List)'
	}

	def __init__( self, parent, mainGui ):

		ttk.Frame.__init__( self, parent ) #, padding="11 0 0 11" ) # Padding order: Left, Top, Right, Bottom.
		
		# Add this tab to the main GUI
		mainGui.mainTabFrame.add( self, text=' Debug Menu Editor ' )

		self.menuItems = {} # key = start offset of a menu/screen, value = list of menuItem objects
		self.defaultWidth = 0

		# Set variables for the info panel
		self.lineVar = Tk.StringVar( value=' '*self.defaultWidth )
		self.offsetVar = Tk.StringVar()
		self.typeVar = Tk.StringVar()
		self.parentMenuVar = Tk.StringVar()
		self.submenuVar = Tk.StringVar()
		self.submenuLabelVar = Tk.StringVar( value='Submenu: ' )
		self.targetFunctionVar = Tk.StringVar()

		# Bottom Row
		self.optionsCountVar = Tk.StringVar()
		self.optionsIncreaseVar = Tk.StringVar()
		self.optionsCurItemVar = Tk.StringVar()
		self.optionsListPointerVar = Tk.StringVar()
		self.textPointer = Tk.StringVar()
		self.optionsTexts = Tk.StringVar()

		# Create the left-hand info column
		leftColumn = ttk.Frame( self )

		infoPanel = ttk.LabelFrame( leftColumn, text=' Menu Item Info ' )
		padx = 15
		ttk.Label( infoPanel, text='Line: ' ).grid( column=0, row=0, padx=padx, sticky='e', pady=(4, 0) )
		ttk.Label( infoPanel, textvariable=self.lineVar ).grid( column=1, row=0, sticky='w', pady=(4, 0) )
		ttk.Label( infoPanel, text='Offset: ' ).grid( column=0, row=1, padx=padx, sticky='e' )
		ttk.Label( infoPanel, textvariable=self.offsetVar ).grid( column=1, row=1, sticky='w' )
		ttk.Label( infoPanel, text='Type: ' ).grid( column=0, row=2, padx=padx, sticky='e' )
		ttk.Label( infoPanel, textvariable=self.typeVar ).grid( column=1, row=2, sticky='w' )
		ttk.Label( infoPanel, text='Target Function: ' ).grid( column=0, row=3, padx=padx, sticky='e' )
		ttk.Label( infoPanel, textvariable=self.targetFunctionVar ).grid( column=1, row=3, sticky='w' )
		ttk.Label( infoPanel, text='String Offset: ' ).grid( column=0, row=4, padx=padx, sticky='e' )
		ttk.Label( infoPanel, textvariable=self.textPointer ).grid( column=1, row=4, sticky='w' )

		ttk.Label( infoPanel, text='Parent Menu: ' ).grid( column=0, row=5, padx=padx, sticky='e', pady=(12, 0) )
		ttk.Label( infoPanel, textvariable=self.parentMenuVar ).grid( column=1, row=5, sticky='w', pady=(12, 0) )
		ttk.Label( infoPanel, textvariable=self.submenuLabelVar ).grid( column=0, row=6, padx=padx, sticky='e' )
		ttk.Label( infoPanel, textvariable=self.submenuVar ).grid( column=1, row=6, sticky='w' )
		infoPanel.pack( pady=20, fill='x', expand=1, ipadx=8, ipady=6 )

		# Left/Right Menu Item Options (bottom info panel)
		leftRightOptionsPanel = ttk.LabelFrame( leftColumn, text=' Left/Right Menu Item Options ' )
		ttk.Label( leftRightOptionsPanel, text='Option Count:' ).grid( column=0, row=0, padx=padx, sticky='e', pady=(4, 0) )
		ttk.Label( leftRightOptionsPanel, textvariable=self.optionsCountVar ).grid( column=1, row=0, sticky='w', pady=(4, 0) )
		ttk.Label( leftRightOptionsPanel, text='Value Increment:' ).grid( column=0, row=1, padx=padx, sticky='e' )
		ttk.Label( leftRightOptionsPanel, textvariable=self.optionsIncreaseVar ).grid( column=1, row=1, sticky='w' )
		ttk.Label( leftRightOptionsPanel, text='Current Value Offset:' ).grid( column=0, row=2, padx=padx, sticky='e' )
		ttk.Label( leftRightOptionsPanel, textvariable=self.optionsCurItemVar ).grid( column=1, row=2, sticky='w' )
		ttk.Label( leftRightOptionsPanel, text='String Table Offset:' ).grid( column=0, row=3, padx=padx, sticky='e' )
		ttk.Label( leftRightOptionsPanel, textvariable=self.optionsListPointerVar ).grid( column=1, row=3, sticky='w' )

		ttk.Label( leftRightOptionsPanel, text='String Options Text:' ).grid( column=0, row=4, pady=(8, 0) )
		ttk.Label( leftRightOptionsPanel, textvariable=self.optionsTexts, wraplength=270 ).grid( column=0, columnspan=2, row=5, sticky='ew' )
		leftRightOptionsPanel.pack( pady=20, fill='x', expand=1, ipadx=8, ipady=6 )

		leftColumn.grid( column=0, row=0, sticky='ew', padx=(26, 18) )
		
		menuDisplayBorder = Tk.Frame( self, background='black' ) # Adds space between top and left side of the text lines and the edge (via padx/pady below)
		self.menuDisplay = Tk.Text( menuDisplayBorder, background='black', foreground='white', borderwidth=0, width=60, height=28 )
		self.menuDisplay.tag_configure( 'itemType0', foreground='green' )
		self.menuDisplay.tag_configure( 'selected', background='#334033' )
		self.menuDisplay.tag_bind( 'menuItem', '<Button-1>', self.menuDisplayClicked )
		self.menuDisplay.tag_bind( 'menuItem', '<Double-1>', self.menuDisplayDoubleClicked )
		self.menuDisplay.bind( "<Key>", lambda e: "break" ) # Prevents key strokes from propagating
		self.menuDisplay.bind( "<Double-1>", lambda e: "break" ) # Prevents double-clicks from propagating
		self.menuDisplay.pack( padx=(16, 70), pady=(16, 16) )
		self.backButton = ttk.Label( menuDisplayBorder, image=mainGui.imageBank('bButton'), text='Back', compound='left', background='black', foreground='white', cursor='hand2' )
		self.backButton.bind( '<Button-1>', self.backUpOneMenu )
		menuDisplayBorder.grid( column=1, row=0, rowspan=2, pady=35 )

		# Configure resizing behavior
		self.columnconfigure( 0, weight=1, minsize=350 )
		self.columnconfigure( 1, weight=2 )

	def clearDisplay( self ):

		""" Clears the main text display, as well as the information panel below it. """

		self.menuDisplay.delete( '1.0', 'end' )
		
		# Menu Item Info
		self.lineVar.set( ' '*self.defaultWidth )
		self.offsetVar.set( '' )
		self.typeVar.set( '' )
		self.targetFunctionVar.set( '' )
		self.textPointer.set( '' )
		self.parentMenuVar.set( '' )
		self.submenuVar.set( '' )

		# Left/Right Menu Item Options
		self.optionsCountVar.set( '' )
		self.optionsIncreaseVar.set( '' )
		self.optionsCurItemVar.set( '' )
		self.optionsListPointerVar.set( '' )
		self.optionsTexts.set( '' )

	def formatPointer( self, ramAddress ):

		""" Takes an int RAM address and formats it into a human-readable address/DOL offset string. 
				e.g. 2147558213 -> '80012345 | 0xEF25 (DOL)' """

		if ramAddress == 0:
			return 'N/A'
		elif ramAddress > 0x80BEC720: # This address is where the CSS file is loaded into RAM
			fileAbbr = 'CSS'
			relOffset = ramAddress - 0x80BEC720
		else:
			fileAbbr = 'DOL'
			dol = globalData.disc.dol
			relOffset = dol.offsetInDOL( ramAddress )

		return '{:X} | 0x{:X} ({})'.format( ramAddress, relOffset, fileAbbr )

	def loadTopLevel( self ):

		""" The initial load function for this module. Loads file data and the top-level menu item. """

		self.menuItems = {}
		self.topTableOffset = 0x803FA4E0 	# i.e. DOL offset 0x3F74E0

		self.displayMenuTable( self.topTableOffset, self.topTableOffset )

	def parseMenu( self, tableAddress, parentMenuOffset ):

		""" Parses all lines for one menu screen/table. """

		self.menuItems[tableAddress] = []
		
		# Determine the file and offset of the target data by the RAM address
		dol = globalData.disc.dol
		offset = dol.offsetInDOL( tableAddress )
		if offset == -1: # Target data must reside in the CSS file
			hostFile = globalData.disc.files[globalData.disc.gameId + '/MnSlChr.0sd']
			offset = tableAddress - 0x80BEC720 - 0x20 # Get an offset relative to the data section
		else:
			hostFile = dol
		ramAddress = tableAddress

		# Iterate over the lines for this table and create DebugMenuItem objects
		while offset < tableAddress + 0x360: # The range is a failsafe; should exit from the break
			menuItem = standaloneStructs.DebugMenuItem( hostFile, offset, ramAddress, parentMenuOffset )
			self.menuItems[tableAddress].append( menuItem )

			if menuItem.itemType == 9:
				break
			offset += 0x20
			ramAddress += 0x20

	def displayMenuTable( self, tableAddress, parentMenuOffset ):

		""" Loads the menu display widget with lines defined at the given table offset. """

		#assert tableAddress != 0, 'Submenu item is missing a submenu pointer!'
		if tableAddress == 0: # Occurs in a few submenu selections that instead only execute a custom function
			return

		self.clearDisplay()

		menuItemList = self.menuItems.get( tableAddress, None )
		if not menuItemList:
			self.parseMenu( tableAddress, parentMenuOffset )
			menuItemList = self.menuItems[tableAddress]

		for line, item in enumerate( menuItemList, start=1 ):
			if item.itemType == 0:
				self.menuDisplay.insert( 'end', item.text + '\n', ('menuItem', 'itemType0') )
			else:
				self.menuDisplay.insert( 'end', item.text + '\n', ('menuItem') )

		self.currentMenu = tableAddress

		# Place the back button if this is not the top-level menu
		if tableAddress != self.topTableOffset:
			self.backButton.place( relx=1.0, x=-10, y=4, anchor='ne' )
		else:
			self.backButton.place_forget()

	def menuDisplayClicked( self, event ):

		""" Highlights the selected line, and shows info on it in the information panel. """

		# Translate the current mouse coodinates into a text index
		index = event.widget.index( "@%s,%s" % (event.x, event.y) )
		lineNumber = int( index.split( '.' )[0] )

		# Color the background for the selected line
		self.menuDisplay.tag_remove( "selected", "1.0", "end" ) # Clear from all rows
		self.menuDisplay.tag_add( 'selected', '%s.0' % lineNumber, '%s.end' % lineNumber )

		# Get data for the currently selected line for the current menu
		menuItem = self.menuItems[self.currentMenu][lineNumber-1]

		# Update display of Line, Offset, and Type information
		self.lineVar.set( lineNumber )
		self.offsetVar.set( self.formatPointer(menuItem.address) )
		if menuItem.itemType == 1 and menuItem.submenuPointer == 8: # A custom line item in 20XX
			self.typeVar.set( '1 (Infographic)' )
		else:
			self.typeVar.set( self.friendlyTypes[menuItem.itemType] )
		
		# Set Parent Menu display
		if self.currentMenu == self.topTableOffset:
			self.parentMenuVar.set( 'N/A (Top-level)')
		else:
			self.parentMenuVar.set( self.formatPointer(menuItem.parentMenu) )

		# Set Submenu display
		if menuItem.itemType == 1 and menuItem.submenuPointer == 8: # A custom line item in 20XX
			self.submenuLabelVar.set( 'Target File: ' )
			asciiHalfword = menuItem.data[0x1A:0x1C].decode() # Last two bytes of what is normally the left/right string list count
			self.submenuVar.set( 'IfCom{}.dat'.format(asciiHalfword) )
		else:
			self.submenuLabelVar.set( 'Submenu: ' )
			self.submenuVar.set( self.formatPointer(menuItem.submenuPointer) )

		# Target function
		self.targetFunctionVar.set( self.formatPointer(menuItem.targetFunction) )

		# Option Count
		if menuItem.itemType in ( 2, 3, 8 ):
			self.optionsCountVar.set( float(menuItem.leftRightCount) )
		else:
			self.optionsCountVar.set( 'N/A' )

		# Value Increment
		if menuItem.itemType in ( 3, 8 ):
			self.optionsIncreaseVar.set( float(menuItem.leftRightValIncrement) )
		else:
			self.optionsIncreaseVar.set( 'N/A' )
		
		# Options text pointer (to a table of pointers to strings). Only applies to type 2, 3, 8
		self.optionsCurItemVar.set( self.formatPointer(menuItem.leftRightValPointer) )

		# Options text pointer (to a table of pointers to strings). Only applies to type 2
		self.optionsListPointerVar.set( self.formatPointer(menuItem.textTablePointer) )

		self.textPointer.set( self.formatPointer(menuItem.textPointer) )

		# Text Strings List
		if menuItem.itemType == 2:
			self.optionsTexts.set( ', '.join(menuItem.leftRightStrings) )
		else:
			self.optionsTexts.set( 'N/A' )

	def menuDisplayDoubleClicked( self, event ):
		# Translate the current mouse coodinates into a text index
		index = event.widget.index( "@%s,%s" % (event.x, event.y) )
		lineNumber = int( index.split( '.' )[0] )

		# Do nothing (return) if this line isn't for a submenu
		currentMenu = self.menuItems[self.currentMenu]
		selectedItem = currentMenu[lineNumber-1]
		if selectedItem.itemType != 1: return

		# Clear the display and create the new menu
		parentMenuAddress = currentMenu[0].address
		self.displayMenuTable( selectedItem.submenuPointer, parentMenuAddress )

	def backUpOneMenu( self, event ):
		firstItemInCurrentMenu = self.menuItems[self.currentMenu][0]
		self.displayMenuTable( firstItemInCurrentMenu.parentMenu, None )