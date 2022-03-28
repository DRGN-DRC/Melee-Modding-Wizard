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

from __future__ import print_function # Use print with (); preparation for moving to Python 3

# External Dependencies
import os
import ttk
import time
import struct
import urlparse
import webbrowser
import tkMessageBox
import tkFileDialog
import Tkinter as Tk
from urlparse import urlparse 	# For validating and security checking URLs

# Internal Dependencies
import globalData
from FileSystem.dol import RevisionPromptWindow
from basicFunctions import msg, printStatus, openFolder, validHex
from codeMods import CodeMod, ConfigurationTypes, regionsOverlap, CodeLibraryParser
from guiSubComponents import (
	cmsg, exportSingleFileWithGui, VerticalScrolledFrame, LabelButton, ToolTip, CodeLibrarySelector, 
	CodeSpaceOptionsWindow, ColoredLabelButton, BasicWindow, DisguisedEntry
)


class CodeManagerTab( ttk.Frame ):

	""" GUI to install/uninstall code mods from the currently loaded disc. """

	def __init__( self, parent, mainGui ):
		ttk.Frame.__init__( self, parent )

		# Add this tab to the main GUI, and add drag-and-drop functionality
		mainGui.mainTabFrame.add( self, text=' Code Manager ' )
		mainGui.dnd.bindtarget( self, mainGui.dndHandler, 'text/uri-list' )
		
		# Create the notebook that code module tabs (categories) will be attached to
		self.codeLibraryNotebook = ttk.Notebook( self )
		self.codeLibraryNotebook.pack( fill='both', expand=1, pady=7 )
		self.codeLibraryNotebook.bind( '<<NotebookTabChanged>>', self.onTabChange )

		self.parser = CodeLibraryParser()
		self.libraryFolder = ''
		self.isScanning = False
		self.lastTabSelected = None		# Used to prevent redundant onTabChange calls

		# Create the control panel
		self.controlPanel = ttk.Frame( self, padding="20 8 20 20" ) # Padding: L, T, R, B

		# Add the button bar and the Code Library Selection button
		buttonBar = ttk.Frame( self.controlPanel )
		librarySelectionBtn = ColoredLabelButton( buttonBar, 'books', lambda event: CodeLibrarySelector(globalData.gui.root) )
		librarySelectionBtn.pack( side='right', padx=6 )
		self.libraryToolTipText = Tk.StringVar()
		self.libraryToolTipText.set( 'Click to select Code Library.\n\nCurrent library:\n' + globalData.getModsFolderPath() )
		ToolTip( librarySelectionBtn, delay=900, justify='center', location='w', textvariable=self.libraryToolTipText, wraplength=600, offset=-10 )

		# Add the Settings button
		overwriteOptionsBtn = ColoredLabelButton( buttonBar, 'gear', lambda event: CodeSpaceOptionsWindow(globalData.gui.root) )
		overwriteOptionsBtn.pack( side='right', padx=6 )
		overwriteOptionsTooltip = 'Edit Code-Space Options'
		ToolTip( overwriteOptionsBtn, delay=900, justify='center', location='w', text=overwriteOptionsTooltip, wraplength=600, offset=-10 )
		buttonBar.pack( fill='x', pady=(5, 20) )

		# Begin adding primary buttons
		self.openMcmFileBtn = ttk.Button( self.controlPanel, text='Open this File', command=self.openLibraryFile, state='disabled' )
		self.openMcmFileBtn.pack( pady=4, padx=6, ipadx=8 )
		ttk.Button( self.controlPanel, text='Open Mods Library Folder', command=self.openLibraryFolder ).pack( pady=4, padx=6, ipadx=8 )

		ttk.Separator( self.controlPanel, orient='horizontal' ).pack( pady=7, ipadx=120 )

		createFileContainer = ttk.Frame( self.controlPanel, padding="0 0 0 0" )
		ttk.Button( createFileContainer, text='Create INI', command=self.saveIniFile ).pack( side='left', padx=6 )
		ttk.Button( createFileContainer, text='Create GCT', command=self.saveGctFile ).pack( side='left', padx=6 )
		createFileContainer.pack( pady=4 )

		ttk.Separator( self.controlPanel, orient='horizontal' ).pack( pady=7, ipadx=140 )

		self.restoreBtn = ttk.Button( self.controlPanel, text='Restore Vanilla DOL', state='disabled', command=self.askRestoreDol, width=23 )
		self.restoreBtn.pack( pady=4 )
		self.exportBtn = ttk.Button( self.controlPanel, text='Export DOL', state='disabled', command=self.exportDOL, width=23 )
		self.exportBtn.pack( pady=4 )

		ttk.Separator( self.controlPanel, orient='horizontal' ).pack( pady=7, ipadx=120 )

		selectBtnsContainer = ttk.Frame( self.controlPanel, padding="0 0 0 0" )
		selectBtnsContainer.selectAllBtn = ttk.Button( selectBtnsContainer, text='Select All', width=12 )
		selectBtnsContainer.selectAllBtn.pack( side='left', padx=6, pady=0 )
		ToolTip( selectBtnsContainer.selectAllBtn, delay=600, justify='center', text='Shift-Click to select\nwhole library' )
		selectBtnsContainer.selectAllBtn.bind( '<Button-1>', self.selectAllMods )
		selectBtnsContainer.selectAllBtn.bind( '<Shift-Button-1>', self.selectWholeLibrary )
		selectBtnsContainer.deselectAllBtn = ttk.Button( selectBtnsContainer, text='Deselect All', width=12 )
		selectBtnsContainer.deselectAllBtn.pack( side='left', padx=6, pady=0 )
		ToolTip( selectBtnsContainer.deselectAllBtn, delay=600, justify='center', text='Shift-Click to deselect\nwhole library' )
		selectBtnsContainer.deselectAllBtn.bind( '<Button-1>', self.deselectAllMods )
		selectBtnsContainer.deselectAllBtn.bind( '<Shift-Button-1>', self.deselectWholeLibrary )
		selectBtnsContainer.pack( pady=4 )

		ttk.Button( self.controlPanel, text=' Rescan for Mods ', command=self.scanCodeLibrary ).pack( pady=4 )

		# Add a label that shows how many code modes are selected on the current tab
		self.installTotalLabel = Tk.StringVar()
		self.installTotalLabel.set( '' )
		ttk.Label( self.controlPanel, textvariable=self.installTotalLabel ).pack( side='bottom' )

		self.bind( '<Configure>', self.alignControlPanel )

	def updateControls( self ):

		""" Set button enable/disable states. """

		self.restoreBtn['state'] = 'normal'
		self.exportBtn['state'] = 'normal'

	def onTabChange( self, event=None, forceUpdate=False ):

		""" Called whenever the selected tab in the library changes, or when a new tab is added. """
		
		# Check if the Code Manager tab is selected, and thus if any updates are really needed
		if not forceUpdate and globalData.gui.root.nametowidget( globalData.gui.mainTabFrame.select() ) != self:
			return

		currentTab = self.getCurrentTab()

		if not forceUpdate and self.lastTabSelected == currentTab:
			print( 'already selected;', self.controlPanel.winfo_manager(), self.controlPanel.winfo_ismapped() )
			return

		# Prevent focus on the tabs themselves (prevents appearance of selection box)
		# currentTab = globalData.gui.root.nametowidget( self.codeLibraryNotebook.select() )
		# currentTab.focus()
		print( 'tab changed; called with event:', event )
		#time.sleep(2)

		# Remove existing ModModules, and only add those for the currently selected tab
		self.emptyModsPanels()
		self.createModModules( currentTab )

		self.alignControlPanel( currentTab=currentTab )
		self.updateInstalledModsTabLabel( currentTab )

		self.lastTabSelected = currentTab

	def emptyModsPanels( self, notebook=None ):

		""" Destroys all GUI elements (ModModules) for all Code Library tabs. """

		root = globalData.gui.root

		if not notebook:
			notebook = self.codeLibraryNotebook
		
		for tabName in notebook.tabs():
			tabWidget = root.nametowidget( tabName )

			if tabWidget.winfo_class() == 'TFrame':
				modsPanel = tabWidget.winfo_children()[0]
				for childWidget in modsPanel.interior.winfo_children(): # Avoiding .clear method to avoid resetting scroll position
					childWidget.destroy()
			else:
				self.emptyModsPanels( tabWidget )
		
		self.lastTabSelected = None # Allows the next onTabChange to proceed if this was called independently of it

	def createModModules( self, currentTab ):

		""" Creates GUI elements (ModModules) and populates them in the Code Library tab currently in view. """

		#currentTab = self.getCurrentTab()
		# if not currentTab: 
		# 	print( 'no current tab; skipping module creation' )
		# 	return

		modsPanel = currentTab.winfo_children()[0]
		foundMcmFormatting = False
		#print( 'creating modules' )

		for mod in modsPanel.mods:
			module = ModModule( modsPanel.interior, mod )
			module.pack( fill='x', expand=1 )
			#module.event_generate( '<Configure>' )

			if not mod.isAmfs:
				foundMcmFormatting = True

		#modsPanel.event_generate( '<Configure>' )

		# Enable or disable the 'Open this file' button
		if foundMcmFormatting:
			self.openMcmFileBtn['state'] = 'normal'
		else:
			self.openMcmFileBtn['state'] = 'disabled'

	def alignControlPanel( self, event=None, currentTab=None ):

		""" Updates the alignment/position of the control panel (to the right of mod lists) and the global scroll target. 
			Using this alignment technique rather than just dividing the Code Manager tab into two columns allows the 
			library tabs to span the entire width of the program, rather than just the left side. """

		# Check if the Code Manager tab is selected (and thus if the control panel should be visible)
		if globalData.gui.root.nametowidget( globalData.gui.mainTabFrame.select() ) != self:
			self.controlPanel.place_forget() # Removes the control panel from GUI, without deleting it
			#print( 'removing control panel' )
			return

		#print( 'aligning control panel; called with event:', (event) )

		if not currentTab:
			currentTab = self.getCurrentTab()

		if currentTab:
			# Get the VerticalScrolledFrame of the currently selected tab
			modsPanel = currentTab.winfo_children()[0]

			# Get the new coordinates for the control panel frame
			globalData.gui.root.update_idletasks() # Force the GUI to update in order to get correct new widget positions & sizes.
			currentTabWidth = currentTab.winfo_width()

			#print( 'placing control panel with current tab' )
			self.controlPanel.place( in_=currentTab, x=currentTabWidth * .60, width=currentTabWidth * .40, height=modsPanel.winfo_height() )
		else:
			# Align and place according to the main library notebook instead
			#print( 'placing control panel with topLevel notebook' )
			notebookWidth = self.codeLibraryNotebook.winfo_width()
			self.controlPanel.place( in_=self.codeLibraryNotebook, x=notebookWidth * .60, width=notebookWidth * .40, height=self.codeLibraryNotebook.winfo_height() )
			
	def updateInstalledModsTabLabel( self, currentTab=None ):

		""" Updates the installed mods count at the bottom of the control panel. """

		if not currentTab:
			currentTab = self.getCurrentTab()
			if not currentTab:
				print( '.updateInstalledModsTabLabel() unable to get a current tab.' )
				return

		# Get the widget providing scrolling functionality (a VerticalScrolledFrame widget), and its children mod widgets
		scrollingFrame = currentTab.winfo_children()[0]
		scrollingFrameChildren = scrollingFrame.interior.winfo_children()

		# Count the mods enabled or selected for installation
		thisTabSelected = 0
		for modModule in scrollingFrameChildren:
			if modModule.mod.state == 'enabled' or modModule.mod.state == 'pendingEnable':
				thisTabSelected += 1

		# Check total selected mods
		librarySelected = 0
		for mod in globalData.codeMods:
			if mod.state == 'enabled' or mod.state == 'pendingEnable':
				librarySelected += 1

		self.installTotalLabel.set( 'Enabled on this tab:   {} / {}\nEnabled in library:   {} / {}'.format(thisTabSelected, len(scrollingFrameChildren), librarySelected, len(globalData.codeMods)) )

	def clear( self ):

		""" Clears code mod data containers and the Code Manager tab's GUI (removes buttons and deletes mod modules) """
		
		# Clear data containers for code mod info
		self.parser.codeMods = []
		self.parser.modNames.clear()
		globalData.codeMods = []
		globalData.standaloneFunctions = {}

		# Delete all mod modules currently populated in the GUI (by deleting the associated tab),
		# and remove any other current widgets/labels in the main notebook
		for child in self.codeLibraryNotebook.winfo_children():
			child.destroy()

		self.installTotalLabel.set( '' )

		self.lastTabSelected = None # Allows the next onTabChange to proceed if this was called independently of it

	def _reattachTabChangeHandler( self, notebook ):

		""" Even though the onTabChange event handler is unbound in .scanCodeLibrary(), several 
			events will still be triggered, and will linger until the GUI's thread can get back 
			to them. When that happens, if the tab change handler has been re-binded, the handler 
			will be called for each event (even if they occurred while the handler was not binded. 
			
			Thus, this method should be called after idle tasks from the main gui (which includes 
			the tab change events) have finished. """

		notebook.bind( '<<NotebookTabChanged>>', self.onTabChange )
		
	def getCurrentTab( self ):
		
		""" Returns the currently selected tab in the Mods Library tab, or None if one is not selected. 
			The returned widget is the upper-most ttk.Frame in the tab (exists for placement purposes), 
			not the VerticalScrolledFrame. To get that, use .winfo_children()[0] on the returned frame. """

		if self.codeLibraryNotebook.tabs() == ():
			return None

		root = globalData.gui.root
		selectedTab = root.nametowidget( self.codeLibraryNotebook.select() ) # Will be the highest level tab (either a notebook or placementFrame)

		# If the child widget is not a frame, it's a notebook, meaning this represents a directory, and contains more files/tabs within it.
		while selectedTab.winfo_class() != 'TFrame':

			if selectedTab.tabs() == (): return None
			selectedTab = root.nametowidget( selectedTab.select() )
			
		return selectedTab

	def getAllTabs( self, notebook=None, tabsList=None ):

		""" Returns all Code Library tabs. This will be a list of all of the upper-most ttk.Frame 
			widgets in the tabs (exists for placement purposes), not the VerticalScrolledFrame. """

		root = globalData.gui.root

		if not notebook:
			notebook = self.codeLibraryNotebook
			tabsList = []
		
		for tabName in notebook.tabs():
			tabWidget = root.nametowidget( tabName )

			if tabWidget.winfo_class() == 'TFrame':
				tabsList.append( tabWidget )
			else: # It's a notebook; we have to go deeper
				self.getAllTabs( tabWidget, tabsList )
		
		return tabsList

	def selectCodeLibraryTab( self, targetTabWidget, notebook=None ):

		""" Recursively selects all tabs/sub-tabs within the Code Library required to ensure the given target tab is visible. """

		if not notebook: # Initial condition; top-level search start
			notebook = self.codeLibraryNotebook
			self.lastTabSelected = None
		else:
			# Minimize calls to onTabChange by unbinding the event handler (which will fire throughout this method)
			notebook.unbind( '<<NotebookTabChanged>>' )

		root = globalData.gui.root
		found = False

		for tabName in notebook.tabs():
			tabWidget = root.nametowidget( tabName ) # This will be the tab's frame widget (placementFrame).

			# Check if this is the target tab, if not, check if the target tab is in a notebook sub-tab of this tab
			if tabWidget == targetTabWidget: found = True
			elif tabWidget.winfo_class() == 'TNotebook': # If it's actually a tab full of mods, the class will be "Frame"
				# Check whether this notebook is empty. If not, scan it.
				if tabWidget.tabs() == (): continue # Skip this tab.
				else: found = self.selectCodeLibraryTab( targetTabWidget, tabWidget )

			if found: # Select the current tab
				notebook.select( tabWidget )

				# If no 'last tab' is stored, this is the lowest-level tab
				if not self.lastTabSelected:
					self.lastTabSelected = tabWidget
				break

		# Wait to let tab change events fizzle out before reattaching the onTabChange event handler
		if notebook != self.codeLibraryNotebook:
			self.after_idle( self._reattachTabChangeHandler, notebook )

		return found

	def restartScan( self, playAudio ):
		time.sleep( .2 ) # Give a moment to allow for current settings to be saved via saveOptions.
		self.isScanning = False
		self.parser.stopToRescan = False
		self.scanCodeLibrary( playAudio )

	def scanCodeLibrary( self, playAudio=True ):

		""" The main method to scan (parse) a code library, and then call the methods to scan the DOL and 
			populate this tab with the mods found. Also defines half of the paths used for .include statements. 
			The other two .include import paths (CWD and the folder housing each mod text file) will be prepended
			to the lists seen here. """

		# If this scan is triggered while it is already running, queue/wait for the previous iteration to cancel and re-run
		if self.isScanning:
			self.parser.stopToRescan = True
			return

		self.isScanning = True

		# Minimize calls to onTabChange by unbinding the event handler (which will fire throughout this method; especially in .clear)
		self.codeLibraryNotebook.unbind( '<<NotebookTabChanged>>' )

		tic = time.clock()

		# Remember the currently selected tab and its scroll position.
		currentTab = self.getCurrentTab()
		if currentTab:
			targetCategory = currentTab.master.tab( currentTab, option='text' )
			modsPanel = currentTab.winfo_children()[0]
			sliderYPos = modsPanel.vscrollbar.get()[0] # .get() returns e.g. (0.49505277044854884, 0.6767810026385225)
		else:
			targetCategory = ''
			sliderYPos = 0

		self.libraryFolder = globalData.getModsFolderPath()

		# Validate the current Mods Library folder
		if not os.path.exists( self.libraryFolder ):
			warningMsg = 'Unable to find this code library:\n\n' + self.libraryFolder + '\n\nClick on the books icon in the top right to select a library.'
			ttk.Label( self.codeLibraryNotebook, text=warningMsg, background='white', wraplength=600, justify='center' ).place( relx=0.3, rely=0.5, anchor='s' )
			ttk.Label( self.codeLibraryNotebook, image=globalData.gui.imageBank('randall'), background='white' ).place( relx=0.3, rely=0.5, anchor='n', y=10 ) # y not :P
			self.isScanning = False
			return

		self.clear()
		
		# Always parse the Core Code library
		# coreCodesLibraryPath = globalData.paths['coreCodes']
		# self.parser.includePaths = [ os.path.join(coreCodesLibraryPath, '.include'), os.path.join(globalData.scriptHomeFolder, '.include') ]
		# self.parser.processDirectory( coreCodesLibraryPath )

		# Parse the currently selected "main" library
		#if self.libraryFolder != coreCodesLibraryPath:
		self.parser.includePaths = [ os.path.join(self.libraryFolder, '.include'), os.path.join(globalData.scriptHomeFolder, '.include') ]
		self.parser.processDirectory( self.libraryFolder )
		globalData.codeMods = self.parser.codeMods

		# Add the mods parsed above to the GUI
		if globalData.codeMods:
			self.populateCodeLibraryTabs( targetCategory, sliderYPos )

		else: # If no mods are present, add a simple message for the user
			warningMsg = 'Unable to find code mods in this library:\n\n' + self.libraryFolder
			ttk.Label( self.codeLibraryNotebook, text=warningMsg, background='white', wraplength=600, justify='center' ).place( relx=0.3, rely=0.5, anchor='s' )
			ttk.Label( self.codeLibraryNotebook, image=globalData.gui.imageBank('randall'), background='white' ).place( relx=0.3, rely=0.5, anchor='n', y=10 ) # y not :P

		# Check once more if another scan is queued. (e.g. if the scan mods button was pressed again while checking for installed mods)
		if self.parser.stopToRescan:
			self.restartScan( playAudio )
		else:
			toc = time.clock()
			print( 'library parsing time:', toc - tic )

			#totalModsInLibraryLabel.set( 'Total Mods in Library: ' + str(len( self.codeModModules )) ) # todo: refactor code to count mods in the modsPanels instead
			#totalSFsInLibraryLabel.set( 'Total Standalone Functions in Library: ' + str(len( collectAllStandaloneFunctions(self.codeModModules, forAllRevisions=True) )) )

			self.isScanning = False

			# Wait to let tab change events fizzle out before reattaching the onTabChange event handler
			#self.update_idletasks()
			self.after_idle( self._reattachTabChangeHandler, self.codeLibraryNotebook )
			#self.onTabChange( forceUpdate=True ) # Make sure it's called at least once
			# self.after_idle( self.TEST, 'test1' ) # called in-order
			# self.after_idle( self.TEST, 'test2' )
			self.after_idle( self.onTabChange, None, True )

			if playAudio:
				#playSound( 'menuChange' )
				print( 'beep!' )

	# def TEST( self, string ):
	# 	print string

	def populateCodeLibraryTabs( self, targetCategory='', sliderYPos=0 ):

		""" Creates ModModule objects for the GUI, as well as vertical scroll frames/Notebook 
			widgets needed to house them, and checks for installed mods to set module states. """

		notebookWidgets = { '': self.codeLibraryNotebook }
		modsPanels = {}
		modPanelToScroll = None

		# If a disc is loaded, check if the parsed mods are installed in it
		if globalData.disc:
			globalData.disc.dol.checkForEnabledCodes( globalData.codeMods )

		#print( '\tThese mods detected as installed:' )

		for mod in globalData.codeMods:
			# if mod.isAmfs: # Its source path is already a directory
			# 	parentFolderPath = mod.path
			# else:
			parentFolderPath = os.path.dirname( mod.path )
			parentFolderName = os.path.split( parentFolderPath )[1]
			#srcFileExt = os.path.splitext( mod.path )[1].lower()
			
			# Get a path for this mod, relative to the library root (display core codes as relative to root as well)
			#if mod.isAmfs and os.path.dirname( parentFolderPath ) == globalData.paths['coreCodes']:
			if mod.isAmfs and parentFolderPath == globalData.paths['coreCodes']:
				relPath = ''
			# elif mod.isAmfs and srcFileExt in ( '.asm', '.s' ):
			# 	relPath = os.path.relpath( parentFolderPath, self.libraryFolder )
			elif parentFolderPath == globalData.paths['coreCodes']: # For the "Core Codes.txt" file
				relPath = ''
			elif parentFolderName == mod.category:
				relPath = ''
			else:
				relPath = os.path.relpath( parentFolderPath, self.libraryFolder )
				if relPath == '.': relPath = ''

			modsPanel = modsPanels.get( relPath + '\\' + mod.category )

			# Add parent notebooks, if needed, and/or get the parent for this mod
			if not modsPanel:
				parent = self.codeLibraryNotebook
				tabPathParts = []
				pathParts = relPath.split( '\\' )

				for i, pathItem in enumerate( pathParts ):
					tabPathParts.append( pathItem )
					thisTabPath = '\\'.join( tabPathParts )
					notebook = notebookWidgets.get( thisTabPath )

					# Add a new notebook, if needed
					if not notebook:
						# Create a new tab for this folder or category name
						notebook = ttk.Notebook( parent, takefocus=False )
						notebook.bind( '<<NotebookTabChanged>>', self.onTabChange )
						parent.add( notebook, text=pathItem, image=globalData.gui.imageBank('folderIcon'), compound='left' )
						# print( 'adding notebook', notebook._name, 'to', parent._name, 'for', thisTabPath )
						notebookWidgets[thisTabPath] = notebook

					parent = notebook

					# Add a vertical scrolled frame to the last notebook
					if i == len( pathParts ) - 1: # Reached the last part (the category)
						placementFrame = ttk.Frame( parent ) # This will be the "currentTab" widget returned from .getCurrentTab()
						parent.add( placementFrame, text=mod.category )

						# Create and add the mods panel (placement frame above needed so we can .place() the mods panel)
						modsPanel = VerticalScrolledFrame( placementFrame )
						modsPanel.mods = []
						#print( 'adding VSF', modsPanel._name, 'to', placementFrame._name, 'for', thisTabPath + '\\' + mod.category )
						modsPanel.place( x=0, y=0, relwidth=.60, relheight=1.0 )
						modsPanels[relPath + '\\' + mod.category] = modsPanel

						# If this is the target panel, Remember it to set its vertical scroll position after all mod modules have been added
						if targetCategory == mod.category:
							modPanelToScroll = modsPanel

			# If this tab is going to be immediately visible/selected, add its modules now
			if targetCategory == mod.category:
				ModModule( modsPanel.interior, mod ).pack( fill='x', expand=1 )

			# Store the mod for later; actual modules for the GUI will be created on tab selection
			modsPanel.mods.append( mod )

			# Disable mods with problems
			if mod.assemblyError or mod.parsingError:
				mod.setState( 'unavailable' )

			# if mod.state == 'enabled':
			# 	print( mod.name )

		# If a previous tab and scroll position are desired, set them here
		if modPanelToScroll:
			self.lastTabSelected = None # Allows the next onTabChange to proceed if this was called independently of it
			self.selectCodeLibraryTab( modPanelToScroll.master )

			# Update idle tasks so the modPanel's height and scroll position calculate correctly
			# modPanelToScroll.update_idletasks()
			# modPanelToScroll.canvas.yview_moveto( sliderYPos )
			#self.after_idle( lambda y=sliderYPos: modPanelToScroll.canvas.yview_moveto( y ) )
			self.after_idle( self._updateScrollPosition, modPanelToScroll, sliderYPos )

			self.updateInstalledModsTabLabel( modPanelToScroll.master )

		# Add messages to the background of any empty notebooks
		for notebook in notebookWidgets.values():
			if not notebook.winfo_children():
				warningMsg = 'No code mods found in this folder or category.'
				ttk.Label( notebook, text=warningMsg, background='white', wraplength=600, justify='center' ).place( relx=0.3, rely=0.5, anchor='s' )
				ttk.Label( notebook, image=globalData.gui.imageBank('randall'), background='white' ).place( relx=0.3, rely=0.5, anchor='n', y=10 ) # y not :P

	def _updateScrollPosition( self, modPanel, sliderYPos ):
		print( 'updating scroll position' )
		self.update_idletasks()
		modPanel.canvas.yview_moveto( sliderYPos )

	def autoSelectCodeRegions( self ):

		""" If 20XX is loaded, this attempts to recognize its version and select the appropriate custom code regions. """

		if not globalData.disc:
			return

		# Check if the loaded DOL is 20XX and get its version
		dol = globalData.disc.dol
		if not dol.is20XX:
			return
		v20XX = dol.is20XX.replace( '+', '' ) # Strip from 4.07+/4.07++

		# Get the version as major.minor and construct the code regions name
		majorMinor = '.'.join( v20XX.split('.')[:2] ) # Excludes version.patch if present (e.g. 5.0.0)
		customRegions = '20XXHP {} Regions'.format( majorMinor )

		# Check if the current overwrite options match up with the version of 20XX loaded
		foundTargetRegions = False
		regions = []
		for name, boolVar in globalData.overwriteOptions.iteritems():
			if boolVar.get(): regions.append( name )
			if name == customRegions: foundTargetRegions = True

		if not foundTargetRegions:
			print( 'Unable to auto-select custom code regions; unsupported 20XX version: {}'.format(v20XX) )
			return

		# Check that only the one target region is selected
		if not regions == [customRegions]:
			reselectRegions = tkMessageBox.askyesno( 'Enable Dedicated Region?', 'The game being loaded appears to be for the 20XX Hack Pack, v{}. '
													'Would you like to enable the custom code regions specifically for this mod ({})?'
													"\n\nIf you're unsure, click yes.".format(v20XX, customRegions) )
			if reselectRegions:
				# Disable all regions
				for boolVar in globalData.overwriteOptions.itervalues():
					boolVar.set( False )

				# Enable the appropriate region
				boolVar = globalData.overwriteOptions.get( customRegions )
				if boolVar:
					boolVar.set( True )
				else:
					msg( 'Unable to enable custom code regions for {}; that region could not be '
						 'found among the configurations in the codeRegionSettings.py file.', 'Custom Code Regions Load Error', error=True )

				# Remember these settings
				globalData.saveProgramSettings()

	def openLibraryFile( self ):

		""" Checks if the current tab has a mod written in MCM's format, 
			and opens it in the user's default text editing program if there is. """

		# Check if the current tab has a mod written in MCM's format
		currentTab = self.getCurrentTab()

		for mod in currentTab.winfo_children()[0].mods:
			if not mod.isAmfs:
				webbrowser.open( mod.path )
				break
		else:
			msg( "No text file mods (those written in MCM's standard format) were found in this tab. "
				 "These appear to be in AMFS format (ASM Mod Folder Structure), "
				 "which should open to a folder.", 'No MCM Style Mods Found', globalData.gui.root )

	def openLibraryFolder( self ):
		openFolder( self.libraryFolder )

	def exportDOL( self ):
		if globalData.disc:
			exportSingleFileWithGui( globalData.disc.dol )
		else:
			msg( 'No disc has been loaded!' )

	def saveGctFile( self ):

		""" Simple wrapper for the 'Save GCT' button. Creates a Gecko Code Type file
			using a tweak of the function used for creating INI files. """

		self.saveIniFile( createForGCT=True )

	def saveIniFile( self, createForGCT=False ):

		# Check whether there are any mods selected
		for mod in globalData.codeMods:
			if mod.state == 'enabled' or mod.state == 'pendingEnable': break
		else: # The loop above didn't break, meaning there are none selected
			msg( 'No mods are selected!' )
			return

		# Decide on a default file name for the GCT file
		if globalData.disc and globalData.disc.gameId:
			initialFilename = globalData.disc.gameId
		else:
			initialFilename = 'Codes'

		# Set the file type & description
		if createForGCT:
			fileExt = '.gct'
			fileTypeDescription = "Gecko Code Type files"
		else:
			fileExt = '.ini'
			fileTypeDescription = "Code Initialization files"

		# Get a save filepath from the user
		targetFile = tkFileDialog.asksaveasfilename(
			title="Where would you like to save the {} file?".format( fileExt[1:].upper() ),
			initialdir=globalData.getLastUsedDir(),
			initialfile=initialFilename,
			defaultextension=fileExt,
			filetypes=[ (fileTypeDescription, fileExt), ("All files", "*") ]
			)
		if targetFile == '':
			return # No filepath; user canceled
		
		# Remember current settings
		targetFileDir = os.path.split( targetFile )[0].encode('utf-8').strip()
		globalData.setLastUsedDir( targetFileDir )

		# Get the revision desired for this codeset
		if globalData.disc:
			dolRevision = globalData.disc.dol.revision
		else: # Not yet known; prompt the user for it
			revisionWindow = RevisionPromptWindow( 'Choose the region and game version that this codeset is for:', 'NTSC', '02' )

			# Check the values gained from the user prompt (empty strings mean they closed or canceled the window)
			if not revisionWindow.region or not revisionWindow.version:
				return

			dolRevision = revisionWindow.region + ' ' + revisionWindow.version

		# Load the DOL for this revision (if one is not already loaded).
		# This may be needed for formatting the code, in order to calculate RAM addresses
		# vanillaDol = globalData.getVanillaDol()
		# if not vanillaDol: return
		try:
			vanillaDol = globalData.getVanillaDol()
		except Exception as err:
			printStatus( 'Unable to create the {} file; {}'.format(fileExt[1:].upper(), err.message) )
			return False

		#if vanillaDol.revision != dolRevision: # todo

		# Get and format the individual mods
		geckoFormattedMods = []
		missingTargetRevision = []
		containsSpecialSyntax = []
		for mod in globalData.codeMods:
			if mod.state == 'enabled' or mod.state == 'pendingEnable':
				if dolRevision in mod.data:
					geckoCodeString = mod.formatAsGecko( vanillaDol, createForGCT )

					if geckoCodeString == '':
						containsSpecialSyntax.append( mod.name )
					else:
						geckoFormattedMods.append( geckoCodeString )

						# Update the mod's status (appearance) so the user knows what was saved
						mod.setState( 'enabled', 'Saved to ' + fileExt[1:].upper() )
				else:
					missingTargetRevision.append( mod.name )

		# Save the text string to a GCT/INI file if any mods were able to be formatted
		if geckoFormattedMods:
			if createForGCT:
				# Save the hex code string to the file as bytes
				hexString = '00D0C0DE00D0C0DE' + ''.join( geckoFormattedMods ) + 'F000000000000000'
				with open( targetFile, 'wb' ) as newFile:
					newFile.write( bytearray.fromhex(hexString) )
			else:
				# Save as human-readable text
				with open( targetFile, 'w' ) as newFile:
					newFile.write( '\n\n'.join(geckoFormattedMods) )
			printStatus( fileExt[1:].upper() + ' file created' )

		# Notify the user of any codes that could not be included
		warningMessage = ''
		if missingTargetRevision:
			warningMessage = ( "The following mods could not be included because they do not contain "
						"code changes for the DOL revision you've selected:\n\n" + '\n'.join(missingTargetRevision) )
		if containsSpecialSyntax:
			warningMessage += ( "\n\nThe following mods could not be included because they contain special syntax (such as Standalone Functions or "
						"RAM symbols) which are not currently supported in " + fileExt[1:].upper() + " file creation:\n\n" + '\n'.join(containsSpecialSyntax) )

		if warningMessage:
			cmsg( warningMessage.lstrip(), 'Warning' )

	def selectAllMods( self, event ):
		currentTab = self.getCurrentTab()

		for mod in currentTab.winfo_children()[0].mods:
			if mod.state == 'pendingDisable': mod.setState( 'enabled' )
			elif mod.state == 'disabled': mod.setState( 'pendingEnable' )

		self.updateInstalledModsTabLabel( currentTab )
		#playSound( 'menuChange' )

	def deselectAllMods( self, event ):
		currentTab = self.getCurrentTab()

		for mod in currentTab.winfo_children()[0].mods:
			if mod.state == 'pendingEnable': mod.setState( 'disabled' )
			elif mod.state == 'enabled': mod.setState( 'pendingDisable' )

		self.updateInstalledModsTabLabel( currentTab )
		#playSound( 'menuChange' )

	def selectWholeLibrary( self, event ):

		for tab in self.getAllTabs():
			for mod in tab.winfo_children()[0].mods:
				if mod.state == 'pendingDisable': mod.setState( 'enabled' )
				elif mod.state == 'disabled': mod.setState( 'pendingEnable' )

		self.updateInstalledModsTabLabel()
		#playSound( 'menuChange' )

	def deselectWholeLibrary( self, event ):

		for tab in self.getAllTabs():
			for mod in tab.winfo_children()[0].mods:
				if mod.state == 'pendingEnable': mod.setState( 'disabled' )
				elif mod.state == 'enabled': mod.setState( 'pendingDisable' )

		self.updateInstalledModsTabLabel()
		#playSound( 'menuChange' )

	def saveCodeChanges( self ):

		""" Collects input from the GUI (user's choices on what mods should be enabled/disabled), 
			and calls the appropriate disc methods for code mod installation and saving. If only 
			code un-installations are required, those are performed on the DOL as-is. If code 
			installations (with or without un-installations) are requested, the whole DOL will be 
			restored to vanilla, and then only the requested codes will be installed to it. 
			
			May return with these codes:
			
				0: Success; all selected codes installed or uninstalled
				1: Unable to restore the DOL (likely no vanilla disc reference)
				2: One or more selected codes could not installed or uninstalled
				3: No selected codes could be installed or uninstalled	"""

		modsToInstall = []
		modsToUninstall = []
		geckoCodesToInstall = []
		newModsToInstall = False

		# Scan the library for mods to be installed or uninstalled
		for mod in globalData.codeMods:
			if mod.state == 'pendingDisable':
				modsToUninstall.append( mod )
			
			elif mod.state == 'pendingEnable':
				if mod.type == 'gecko':
					# Attempt to convert it to standard static overwrites and injections
					newCodeChanges = []
					try:
						for codeChange in mod.getCodeChanges():
							if codeChange.type == 'gecko':
								# Prepend artificial title/author, for the parser
								customCode = codeChange.rawCode.splitlines()
								customCode.insert( 0, '$TitlePlaceholder' )
								codeChanges = self.parser.parseGeckoCode( customCode, globalData.disc.dol )[-1]
								newCodeChanges.extend( codeChanges )
							else:
								newCodeChanges.append( codeChange )
						# If no errors above, replace the mod's changes with those gathered above
						mod.data[mod.currentRevision] = newCodeChanges
					except:
						# Unable to convert it; install it as a Gecko code
						geckoCodesToInstall.append( mod )
						continue

				modsToInstall.append( mod )
				newModsToInstall = True

			elif mod.state == 'enabled':
				modsToInstall.append( mod )
		
		modsNotUninstalled = []
		modsNotInstalled = []
		geckoCodesNotInstalled = []
		modInstallCount = 0
		modUninstallCount = 0
		
		# Make sure the DOL has been initialized (header parsed and properties determined)
		globalData.disc.dol.load()

		# Install or uninstall selected code mods
		if newModsToInstall:
			if not globalData.disc.restoreDol( countAsNewFile=False ):
				globalData.gui.updateProgramStatus( 'Unable to save code changes; the vanilla or source DOL could not be restored', warning=True )
				return 1

			globalData.gui.updateProgramStatus( 'Installing {} codes'.format(len(modsToInstall)) )

			modsNotInstalled = globalData.disc.installCodeMods( modsToInstall )
			modInstallCount = len( modsToInstall ) - len( modsNotInstalled )
			modUninstallCount = len( modsToUninstall )

			if modInstallCount == 0: # None could be installed
				globalData.gui.updateProgramStatus( 'No code mods could be installed' )
				return 3

		elif modsToUninstall: # If installing new mods, all mods selected for uninstall will automatically be excluded
			globalData.gui.updateProgramStatus( 'Uninstalling {} codes'.format(len(modsToUninstall)) )

			modsNotUninstalled = globalData.disc.uninstallCodeMods( modsToUninstall )
			modUninstallCount = len( modsToUninstall ) - len( modsNotUninstalled )

			if modUninstallCount == 0: # None could be uninstalled
				globalData.gui.updateProgramStatus( 'No code mods could be uninstalled' )
				return 3

		else:
			print( 'no code changes to be made' )

		# if geckoCodesToInstall:
		# 	globalData.updateProgramStatus( 'Installing {} Gecko codes'.format(len(geckoCodesToInstall)) )
		# 	geckoCodesNotInstalled = globalData.disc.installGeckoCodes( geckoCodesToInstall )

		# if modsNotUninstalled or modsNotInstalled or geckoCodesNotInstalled:
		# 	problematicMods = modsNotUninstalled + modsNotInstalled + geckoCodesNotInstalled

		# 	msg( '{} code mods installed. However, these mods could not be installed:\n\n{}'.format(len(), '\n'.join(problematicMods)) )

		# Build a message to be displayed in the program's status bar
		statusMsg = ''
		returnCode = 0
		if modUninstallCount > 0:
			if modUninstallCount == 1: statusMsg = '1 code mod uninstalled'
			else: statusMsg = '{} code mods uninstalled'.format( modUninstallCount )
		if modInstallCount > 0:
			if statusMsg: statusMsg += '. '
			if modInstallCount == 1: statusMsg += '1 code mod installed'
			else: statusMsg += '{} code mods installed'.format( modInstallCount )
		if modsNotUninstalled or modsNotInstalled:
			if statusMsg: statusMsg += '. '
			statusMsg += '{} mod change(s) failed'.format( len(modsNotUninstalled + modsNotInstalled) )
			returnCode = 2
		if statusMsg:
			globalData.gui.updateProgramStatus( statusMsg )

		return returnCode

	def askRestoreDol( self ):

		""" Prompts the user to ensure they know what they're doing, and to confirm the action. """

		if not globalData.disc:
			msg( 'No disc has been loaded!' )
			return
		
		dol = globalData.disc.dol
		
		restoreConfirmed = tkMessageBox.askyesno( 'Restoration Confirmation', 'This will replace the currently loaded DOL to a '
												'vanilla ' + dol.revision + ' DOL (loaded from your chosen vanilla disc). Free '
												'space regions reserved for custom code (under Code-Space Options) will still '
												'be zeroed-out when saving. This process does not preserve a copy of the current DOL, '
												'and any current changes will be lost.\n\nAre you sure you want to do this?' )
		if not restoreConfirmed:
			globalData.gui.updateProgramStatus( 'Restoration canceled' )
			return

		# See if we can get a reference to vanilla DOL code
		# vanillaDiscPath = globalData.getVanillaDiscPath()
		# if not vanillaDiscPath: # User canceled path input
		# 	printStatus( 'Unable to restore the DOL; no vanilla disc available for reference', warning=True )
		# 	return

		# Restore the DOL and re-scan for installed codes
		if globalData.disc.restoreDol():
			globalData.disc.dol.checkForEnabledCodes( globalData.codeMods )

			globalData.gui.updateProgramStatus( 'Restoration Successful' )


class ModModule( Tk.Frame, object ):

	""" GUI element and wrapper for CodeMod objects, and host to various GUI-related features. """

	def __init__( self, parent, mod, *args, **kw ):
		super( ModModule, self ).__init__( parent, relief='groove', borderwidth=3, takefocus=True, *args, **kw )

		self.mod = mod
		mod.guiModule = self

		self.valWebLinks = [] # These differentiate from the core mod's webLinks, in that these will be validated
		self.statusText = Tk.StringVar()
		self.highlightFadeAnimationId = None # Used for the border highlight fade animation

		moduleWidth = 520 			# Mostly just controls the wraplength of text areas.

		# Row 1: Title and author(s)
		Tk.Label( self, text=mod.name, font=("Times", 11, "bold"), wraplength=moduleWidth-140, anchor='n' ).pack( side='top', padx=(0,36), pady=2 ) # Right-side horizontal padding added for module type image
		self.authorLabel = Tk.Label( self, text=' - by ' + mod.auth, font=("Verdana", 8), wraplength=moduleWidth-160, fg='#555' ) #Helvetica
		self.authorLabel.pack( side='top', padx=(0,36) )

		# Row 2: Description
		Tk.Label( self, text=mod.desc, wraplength=moduleWidth-40, justify='left' ).pack( side='top', fill='x', expand=1, padx=(8, 54) )

		# Row 3: Status text and buttons
		row3 = Tk.Frame( self )

		self.statusLabel = Tk.Label( row3, textvariable=self.statusText, wraplength=moduleWidth-90, justify='left' )
		self.statusLabel.pack( side='left', padx=35 )

		# Set a background image based on the mod type (indicator on the right-hand side of the mod)
		typeIndicatorImage = globalData.gui.imageBank( mod.type + 'Indicator' )
		if typeIndicatorImage:
			bgImage = Tk.Label( self, image=typeIndicatorImage )
			bgImage.place( relx=1, x=-10, rely=0.5, anchor='e' )
		else:
			print( 'No image found for "' + mod.type + 'Indicator' + '"!' )

		# Set up a left-click event to all current parts of this module (to toggle the code on/off), before adding any of the other clickable elements
		self.bind( '<1>', self.clicked )
		for each in self.winfo_children():
			each.bind( '<1>', self.clicked )
			for widget in each.winfo_children():
				widget.bind( '<1>', self.clicked )

		# Add the edit and configure buttons
		LabelButton( row3, 'editButton', self.inspectMod, "Edit this mod's code" ).pack( side='right', padx=(5, 55), pady=6 )
		if mod.configurations:
			LabelButton( row3, 'configButton', self.configureMod, "Configure this mod's settings" ).pack( side='right', padx=5, pady=6 )

		# Validate web page links and create buttons for them
		for origUrlString, comments in mod.webLinks: # Items in this list are tuples of (urlString, comments)
			urlObj = self.parseUrl( origUrlString )
			if not urlObj: continue # A warning will have been given in the above method if this wasn't successfully parsed
			self.valWebLinks.append( (urlObj, comments) )

			# Build the button's hover text
			domain = urlObj.netloc.split('.')[-2] # The netloc string will be e.g. "youtube.com" or "www.youtube.com"
			url = urlObj.geturl()
			hovertext = 'Go to the {}{} page...\n{}'.format( domain[0].upper(), domain[1:], url ) # Capitalizes first letter of domain
			if comments:
				hovertext += '\n\n' + comments.lstrip( ' #' )

			# Add the button with its url attached
			icon = LabelButton( row3, domain + 'Link', self.openWebPage, hovertext )
			icon.url = url
			icon.pack( side='right', padx=5, pady=6 )

		# Add a warnings info button if there are problems with this mod
		if self.mod.parsingError or self.mod.assemblyError or self.mod.errors:
			LabelButton( row3, 'warningsButton', self.showProblems, "View parsing or assembly errors" ).pack( side='right', padx=5, pady=6 )

		row3.pack( side='top', fill='x', expand=1 )

		# Initialize the GUI module's state with the mod's core state
		self.setState( self.mod.state, self.mod.stateDesc )

	def openWebPage( self, event ):

		""" Called by a web link button, to open an internet page for this mod. """

		page = event.widget.url
		webbrowser.open( page )
		
	def parseUrl( self, origUrlString ):

		""" Validates a given URL (string), partly based on a whitelist of allowed domains. 
			Returns a urlparse object if the url is valid, or None (Python default) if it isn't. """

		try:
			potentialLink = urlparse( origUrlString )
		except Exception as err:
			print( 'Invalid link detected for "{}": {}'.format(self.mod.name, err) )
			return

		# Check the domain against the whitelist. netloc will be something like "youtube.com" or "www.youtube.com"
		if potentialLink.scheme and potentialLink.netloc.split('.')[-2] in ( 'smashboards', 'github', 'youtube' ):
			return potentialLink

		elif not potentialLink.scheme:
			print( 'Invalid link detected for "{}" (no scheme): {}'.format(self.mod.name, potentialLink) )
		else:
			print( 'Invalid link detected for "{}" (domain not allowed): {}'.format(self.mod.name, potentialLink) )

	def setState( self, state, statusText='' ):

		""" Sets the state of the selected module, by adding a label to the module's Row 3 and 
			changing the background color of all associated widgets. """

		textColor = '#000'

		if state == 'pendingEnable':
			stateColor = '#b3f2b3' # Light green
			if not statusText:
				statusText = 'Pending Save'

		elif state == 'pendingDisable':
			stateColor = '#f2b3b3' # Light red
			if not statusText:
				statusText = 'Pending Removal'

		elif state == 'enabled':
			stateColor = '#89d989' # Green

		elif state == 'disabled':
			stateColor = 'SystemButtonFace' # The default widget background color

		elif state == 'unavailable':
			stateColor = '#cccccc' # Light Grey
			textColor = '#707070' # Grey

		else:
			self.statusText.set( '' )
			raise Exception( 'Invalid mod state given! "' + state + '"' )

		if statusText:
			if state == 'unavailable':
				print( self.mod.name, 'made unavailable;', statusText )
			self.statusText.set( statusText )
		else:
			self.statusText.set( '' )

		# Change module background and text colors (adjusting the background color of all associated frames and labels)
		self['bg'] = stateColor
		for widget in self.winfo_children():
			widget['bg'] = stateColor

			if widget.winfo_class() == 'Label' and widget != self.authorLabel:
				widget['fg'] = textColor
			else: # Frame
				for label in widget.winfo_children():
					label['bg'] = stateColor
					if label != self.statusLabel:
						label['fg'] = textColor

		self.mod.state = state

		# Update the enabled count in the control panel
		currentTab = self.master.master.master.master # self -> modsPanel.interior -> modsPanel -> VerticalScrolledFrame -> mainTabFrame
		globalData.gui.codeManagerTab.updateInstalledModsTabLabel( currentTab )
	
	def clicked( self, event ):

		""" Handles click events on mod modules to toggle their install state 
			(i.e. whether or not it should be installed when the user hits save). """

		# Do nothing if this mod is unavailable
		if self.mod.state == 'unavailable':
			return

		# Toggle the state of the module
		# Offer a warning if the user is trying to disable the crash printout code
		if self.mod.name == "Enable OSReport Print on Crash" and globalData.checkSetting( 'alwaysEnableCrashReports' ) \
			and (self.mod.state == 'pendingEnable' or self.mod.state == 'enabled'):
				if not tkMessageBox.askyesno( 'Confirm Disabling Crash Printout', 'This mod is very useful for debugging crashes '
											'and is therefore enabled by default. You can easily disable this behavior by opening the '
											'"settings.py" file in a text editor and setting the option "alwaysEnableCrashReports" '
											'to False, or by removing the "Enable OSReport Print on Crash" code from your library '
											"(or comment it out so it's not picked up by MCM).\n\nAre you sure you'd like to disable this mod?" ):
					return # Return if the user hit "No" (they don't want to disable the mod)

		if self.mod.state == 'pendingEnable': state = 'disabled'
		elif self.mod.state == 'pendingDisable':
			# if self.mod.type == 'gecko' and not overwriteOptions[ 'EnableGeckoCodes' ].get():
			# 	msg( 'This mod includes a Gecko code, which are disabled.' )
			# 	return # Exits now; don't change the state or check for changes
			# else: 
			state = 'enabled'
		elif self.mod.state == 'enabled': state = 'pendingDisable'
		elif self.mod.state == 'disabled': state = 'pendingEnable'
		else: state = 'disabled' # Failsafe reset.
		
		#playSound( 'menuChange' )

		self.setState( state )
		#checkForPendingChanges()
		
	def inspectMod( self, event, mod=None ):

		""" Load a mod from the Mods Library tab into the Mod Construction tab. """

		print( 'not yet implemented' )

		# if not mod: # Was called by the button. Get the mod from the event object
		# 	mod = event.widget.master.master

		# # Select the Mod Construction tab and get the currently existing tabs
		# mainNotebook.select( constructionTab )

		# # Check if the selected mod already exists (and select that if it does)
		# for tab in constructionNotebook.tabs():
		# 	tabName = constructionNotebook.tab( tab, 'text' )
		# 	if tabName != mod.name: continue

		# 	tabWidget = root.nametowidget( tab )
		# 	existingModConstructor = tabWidget.winfo_children()[0]

		# 	if existingModConstructor.sourceFile == mod.sourceFile: # Make sure the library wasn't changed (and it's not just a mod by the same name)
		# 		constructionNotebook.select( tab )
		# 		break

		# else: # Loop above didn't break; mod not found
		# 	# Create a new tab for the Mod Construction tab, and create a new construction module within it.
		# 	newTab = ttk.Frame( constructionNotebook )
		# 	constructionNotebook.add( newTab, text=mod.name )
		# 	ModConstructor( newTab, mod ).pack( fill='both', expand=1 )

		# 	# Bring the new tab into view for the user.
		# 	constructionNotebook.select( newTab )

	def showProblems( self, event ):

		""" Called by clicking on the warning icon/button. """

		errorMsg = []

		if self.mod.parsingError:
			errorMsg.append( 'Parsing Errors Detected: Yes' )
		else:
			errorMsg.append( 'Parsing Errors Detected: No' )

		if self.mod.assemblyError:
			errorMsg.append( 'Assembly Errors Detected: Yes\n' )
		else:
			errorMsg.append( 'Assembly Errors Detected: No\n' )
		
		errorMsg.extend( self.mod.errors )

		cmsg( '\n'.join(errorMsg), 'Warning', 'left' )

	def configureMod( self, event ):
		
		# Check for non-hidden configuration options
		configurations = []
		for optionName, optionDict in self.mod.configurations.items():
			if 'hidden' in optionDict:
				continue
			else:
				configurations.append( (optionName, optionDict) )

		# Just give a message to the user and exit if there are no public configurations
		if not configurations:
			msg( "All of this mod's configuration options are hidden."
				 "\nYou'll need to view the mod's source to edit or unhide them.", 'All Options are Hidden' )
			return

		CodeConfigWindow( self.mod, configurations )


class ModConstructor( Tk.Frame ):

	def __init__( self, parent, mod=None, *args, **kw ): # Prepare the GUI.
		Tk.Frame.__init__( self, parent, *args, **kw )
		
		self.saveStatus = Tk.StringVar()
		self.saveStatus.set( '' )
		self.dolVariations = []
		self.undoableChanges = False 		# Flipped for changes that 'undo' doesn't work on. Only reverted by save operation.
		self.gameVersionsNotebook = None

		if mod: # This mod is being added (edited) from the Mods Library tab.
			name = mod.name
			auth = mod.auth
			self.type = mod.type
			modDescription = mod.desc
			self.sourceFile = mod.sourceFile
			self.fileIndex = mod.fileIndex
			self.webLinks = mod.webLinks
			self.includePaths = mod.includePaths

		else: # This is a new mod.
			name = ''
			auth = ''
			self.type = ''
			modDescription = ''
			self.sourceFile = ''
			self.fileIndex = -1
			self.webLinks = []
			self.includePaths = [ os.path.join(getModsFolderPath(), '.include'), os.path.join(scriptHomeFolder, '.include') ]

		if mod:
			self.mod = mod
		else:
			self.mod = CodeMod( 'New Mod' )

		# Top buttons row
		self.buttonsFrame = Tk.Frame( self )
		self.saveStatusLabel = ttk.Label( self.buttonsFrame, textvariable=self.saveStatus )
		self.saveStatusLabel.pack( side='left', padx=12 )
		ttk.Button( self.buttonsFrame, text='Close', command=self.closeMod, width=6 ).pack( side='right', padx=6 )
		ttk.Button( self.buttonsFrame, text='Info', command=self.analyzeMod, width=6 ).pack( side='right', padx=6 )
		ttk.Button( self.buttonsFrame, text='Import Gecko Code', command=self.importGeckoCode ).pack( side='right', padx=6, ipadx=6 )
		self.buttonsFrame.pack( fill='x', expand=0, padx=20, pady=12, ipadx=6, anchor='ne' )

		# Title and Author
		row1 = Tk.Frame( self )
		ttk.Label( row1, text='Title:' ).pack( side='left', padx=3 )
		self.titleEntry = ttk.Entry( row1, width=56 )
		self.titleEntry.insert( 0, name )
		self.titleEntry.pack( side='left' )
		self.initUndoHistory( self.titleEntry, name )
		ttk.Label( row1, text='Author(s):' ).pack( side='left', padx=(22, 3) )
		self.authorsEntry = ttk.Entry( row1, width=36 )
		self.authorsEntry.insert( 0, auth )
		self.authorsEntry.pack( side='left' )
		self.initUndoHistory( self.authorsEntry, auth )
		row1.pack( padx=20, pady=0, anchor='n' )

		# Starting row 2, with Description
		row2 = Tk.Frame( self )
		descColumn = Tk.Frame( row2 ) # Extra frame so we can stack two items vertically in this grid cell in a unique way
		ttk.Label( descColumn, text='\t\tDescription:' ).pack( anchor='w' )
		self.descScrolledText = ScrolledText( descColumn, width=75, height=6, wrap='word', font='TkTextFont' )
		self.descScrolledText.insert( 'end', modDescription )
		self.descScrolledText.pack( fill='x', expand=True ) # todo: still not actually expanding. even removing width above doesn't help
		self.initUndoHistory( self.descScrolledText, modDescription )
		descColumn.grid( column=0, row=0 )

		# Add the mod-change adder
		lineAdders = ttk.Labelframe(row2, text='  Add a type of code change:  ', padding=5)
		ttk.Button( lineAdders, width=3, text='+', command=lambda: self.addCodeChangeModule( 'static' ) ).grid( row=0, column=0 )
		ttk.Label( lineAdders, width=21, text='Static Overwrite' ).grid( row=0, column=1 )
		ttk.Button( lineAdders, width=3, text='+', command=lambda: self.addCodeChangeModule( 'injection' ) ).grid( row=1, column=0 )
		ttk.Label( lineAdders, width=21, text='Injection Mod' ).grid( row=1, column=1 )
		ttk.Button(lineAdders, width=3, text='+', command=lambda: self.addCodeChangeModule( 'gecko' )).grid(row=2, column=0)
		ttk.Label(lineAdders, width=21, text='Gecko/WiiRD Code').grid(row=2, column=1)
		ttk.Button( lineAdders, width=3, text='+', command=lambda: self.addCodeChangeModule( 'standalone' ) ).grid( row=3, column=0 )
		ttk.Label( lineAdders, width=21, text='Standalone Function' ).grid( row=3, column=1 )
		lineAdders.grid( column=1, row=0 )

		# Add the web links
		if self.webLinks:
			self.webLinksFrame = ttk.Labelframe( row2, text='  Web Links:  ', padding=(0, 0, 0, 8) ) # padding = left, top, right, bottom
			for urlObj, comments in self.webLinks:
				self.addWebLink( urlObj, comments )

			# Add the "Edit" button
			# addBtn = ttk.Label( row2, text='Edit', foreground='#03f', cursor='hand2' )
			# addBtn.bind( '<1>', lambda e, frame=self.webLinksFrame: WebLinksEditor(frame) )
			# addBtn.place( anchor='s', relx=.937, rely=1.0, y=4 )

			self.webLinksFrame.grid( column=2, row=0 )

		row2.pack( fill='x', expand=True, padx=20, pady=(7, 0), anchor='n' )
		
		# Configure the description/code-changes row, so it centers itself and expands properly on window-resize
		row2.columnconfigure( 0, weight=3 )
		row2.columnconfigure( (1, 2), weight=1 )

		# Add the game version tabs and code changes to this module.
		if mod:
			for dolRevision in mod.data: # dolRevision should be a string like 'NTSC 1.00'
				for codeChange in mod.data[dolRevision]:
					changeType, customCodeLength, offset, originalCode, customCode, _ = codeChange

					self.addCodeChangeModule( changeType, customCodeLength, offset, originalCode, customCode, dolRevision )

	def initUndoHistory( self, widget, initialValue ):

		""" Adds several attributes and event handlers to the given widget, for undo/redo history tracking. """

		widget.undoStateTimer = None
		
		# Create the first undo state for this widget
		widget.undoStates = [initialValue]
		widget.savedContents = initialValue
		widget.undoStatesPosition = 0 # Index into the above list, for traversal of multiple undos/redos

		# Provide this widget with event handlers for CTRL-Z, CTRL-Y
		widget.bind( "<Control-z>", self.undo )
		widget.bind( "<Control-y>", self.redo )
		widget.bind( "<Control-Shift-y>", self.redo )

		widget.bind( '<KeyRelease>', self.queueUndoStatesUpdate )

	def initializeVersionNotebook( self ):
		
		""" Creates the notebook used to house code changes, with tabs for each game revision the mod may apply to. """

		def gotoWorkshop(): webbrowser.open( 'http://smashboards.com/forums/melee-workshop.271/' )
		def shareButtonClicked():
			modString = self.buildModString()
			thisModName = constructionNotebook.tab( self.master, option='text' )
			if modString != '': cmsg( '\n\n\t-==-\n\n' + modString, thisModName, 'left', (('Go to Melee Workshop', gotoWorkshop),) )

		# Show the Share / Submit buttons
		ttk.Button( self.buttonsFrame, text='Share', command=shareButtonClicked, width=7 ).pack( side='right', padx=6 )
		ttk.Button( self.buttonsFrame, text='Save As', command=self.saveModToLibraryAs, width=8 ).pack( side='right', padx=6 )
		ttk.Button( self.buttonsFrame, text='Save', command=self.saveModToLibrary, width=7 ).pack( side='right', padx=6 )
		offsetView = settings.get( 'General Settings', 'offsetView' ).lstrip()[0].lower()
		if offsetView.startswith( 'd' ): buttonText = 'Display RAM Addresses'
		else: buttonText = 'Display DOL Offsets'
		self.offsetViewBtn = ttk.Button( self.buttonsFrame, text=buttonText, command=self.switchOffsetDisplayType )
		self.offsetViewBtn.pack( side='right', padx=6, ipadx=6 )

		self.gameVersionsNotebook = ttk.Notebook( self )
		self.gameVersionsNotebook.pack( fill='both', expand=1, anchor='n', padx=12, pady=6 )

		# New hex field label
		self.gameVersionsNotebook.newHexLabel = Tk.StringVar()
		self.gameVersionsNotebook.newHexLabel.set( '' )
		ttk.Label( self.gameVersionsNotebook, textvariable=self.gameVersionsNotebook.newHexLabel ).place( anchor='e', y=9, relx=.84 )

		# Add the version adder tab.
		versionChangerTab = Tk.Frame( self.gameVersionsNotebook )
		self.gameVersionsNotebook.add( versionChangerTab, text=' + ' )

		# Check what original DOLs are available (in the "Original DOLs" folder)
		self.dolVariations = listValidOriginalDols()
		self.dolVariations.append( 'ALL' )

		if len( self.dolVariations ) == 1: # Only 'ALL' is present
			ttk.Label( versionChangerTab, text='No DOLs were found in the "Original DOLs" folder.\nRead the "ReadMe.txt" file found there for more information.' ).pack( pady=15, anchor='center' )

		else: # i.e. Some [appropriately named] dols were found in the dols folder
			ttk.Label( versionChangerTab, text='Choose the game revision you would like to add changes for:\n(These are based on what you have in the "Original DOLs" folder.)' ).pack( pady=15, anchor='center' )
			verChooser = Tk.StringVar()
			verChooser.set( self.dolVariations[0] )

			ttk.OptionMenu( versionChangerTab, verChooser, self.dolVariations[0], *self.dolVariations ).pack()

			def addAnotherVersion():
				tabName = 'For ' + verChooser.get()

				if getTabByName( self.gameVersionsNotebook, tabName ) == -1: # Tab not found.
					self.addGameVersionTab( verChooser.get(), True )

					# Select the newly created tab.
					self.gameVersionsNotebook.select( root.nametowidget(getTabByName( self.gameVersionsNotebook, tabName )) )
				else: msg( 'A tab for that game revision already exists.' )

			ttk.Button( versionChangerTab, text=' Add ', command=addAnotherVersion ).pack( pady=15 )

	def addGameVersionTab( self, dolRevision, codeChangesListWillBeEmpty ):
		# If this is the first code change, add the game version notebook.
		if not self.gameVersionsNotebook: self.initializeVersionNotebook()

		# Decide on a default revision if one is not set, and determine the game version tab name
		if not dolRevision:
			# This is an empty/new code change being added by the user. Determine a default tab (revision) to add it to.
			if len( self.gameVersionsNotebook.tabs() ) == 1: # i.e. only the version adder tab (' + ') exists; no code changes have been added to this notebook yet
				# Attempt to use the revision of the currently loaded DOL
				if dol.revision in self.dolVariations:
					gameVersionTabName = 'For ' + dol.revision

				else:
					# Attempt to use a default set in the settingsFile, or 'NTSC 1.02' if one is not set there.
					defaultRev = getattr( settingsFile, 'defaultRevision', 'NTSC 1.02' ) # Last arg = default in case defaultRevision doesn't exist (old settings file)

					if defaultRev in self.dolVariations:
						gameVersionTabName = 'For ' + defaultRev

					else: gameVersionTabName = 'For ' + self.dolVariations[0]

			else: # A tab for code changes already exists. Check the name of the currently selected tab and add to that.
				gameVersionTabName = self.gameVersionsNotebook.tab( self.gameVersionsNotebook.select(), "text" )

			dolRevision = gameVersionTabName[4:] # Removes 'For '

		else: # This code change is being populated automatically (opened from the Library tab for editing)
			gameVersionTabName = 'For ' + dolRevision

		# Add a new tab for this game version if not already present, and define its GUI parts to attach code change modules to.
		versionTab = getTabByName( self.gameVersionsNotebook, gameVersionTabName )

		if versionTab != -1: # Found an existing tab by that name. Add this code change to that tab
			codeChangesListFrame = versionTab.winfo_children()[0]

		else: # Create a new version tab, and add this code change to that
			versionTab = Tk.Frame( self.gameVersionsNotebook )
			indexJustBeforeLast = len( self.gameVersionsNotebook.tabs() ) - 1
			self.gameVersionsNotebook.insert( indexJustBeforeLast, versionTab, text=gameVersionTabName )
			
			# Attempt to move focus to the tab for the currently loaded DOL revision, or to this tab if that doesn't exist.
			tabForCurrentlyLoadedDolRevision = 'For ' + dol.revision
			if dol.revision and tabForCurrentlyLoadedDolRevision in getTabNames( self.gameVersionsNotebook ):
				self.gameVersionsNotebook.select( getTabByName(self.gameVersionsNotebook, tabForCurrentlyLoadedDolRevision) )
			else: self.gameVersionsNotebook.select( versionTab )

			# Add the left-hand column for the code changes
			codeChangesListFrame = VerticalScrolledFrame2( versionTab )
			codeChangesListFrame.pack( side='left', fill='both', expand=0, padx=3, pady=4 )

			# Add the right-hand column, the new hex field (shared for all code changes)
			newHexFieldContainer = Tk.Frame( versionTab )
			newHexFieldContainer['bg'] = 'orange'
			self.attachEmptyNewHexField( versionTab, codeChangesListWillBeEmpty )
			newHexFieldContainer.pack( side='left', fill='both', expand=1, padx=0 )

			# Load a dol for this game version, for the offset conversion function to reference max offsets/addresses, and for dol section info
			loadVanillaDol( dolRevision ) # Won't be repeatedly loaded; stored in memory once loaded for the first time

		return dolRevision, versionTab

	def attachEmptyNewHexField( self, versionTab, codeChangesListWillBeEmpty ):
		codeChangesListFrame, newHexFieldContainer = versionTab.winfo_children()

		self.clearNewHexFieldContainer( newHexFieldContainer )

		newHexField = ScrolledText( newHexFieldContainer, relief='ridge' )
		if codeChangesListWillBeEmpty:
			newHexField.insert( 'end', '\n\tStart by selecting a\n\t     change to add above ^.' )
		else:
			newHexField.insert( 'end', '\n\t<- You may select a code change\n\t     on the left, or add another\n\t       change from the list above ^.' )
		newHexField.pack( fill='both', expand=1, padx=2, pady=1 )

		# Add an event handler for the newHexField. When the user clicks on it, this will autoselect the first code change module if there is only one and it's unselected
		def removeHelpText( event, codeChangesListFrame ):
			#event.widget.unbind( '<1>' ) # Remove this event handler
			codeChangeModules = codeChangesListFrame.interior.winfo_children()

			# Check if there's only one code change module and it hasn't been selected
			if len( codeChangeModules ) == 1 and codeChangeModules[0]['bg'] == 'SystemButtonFace':
				innerFrame = codeChangeModules[0].winfo_children()[0]
				innerFrame.event_generate( '<1>' ) # simulates a click event on the module in order to select it
		newHexField.bind( '<1>', lambda e: removeHelpText( e, codeChangesListFrame ) )

	def addCodeChangeModule( self, changeType, customCodeLength=0, offset='', originalHex='', newHex='', dolRevision='' ):
		if not dolRevision: # This is a brand new (blank) code change being added.
			self.undoableChanges = True
			self.updateSaveStatus( True )

		# Create a new notebook for game versions, and/or a tab for this specific revision, if needed.
		dolRevision, versionTab = self.addGameVersionTab( dolRevision, False )
		codeChangesListFrame, newHexFieldContainer = versionTab.winfo_children()

		# Create the GUI's frame which will hold/show this code change
		codeChangeModule = Tk.Frame( codeChangesListFrame.interior, relief='ridge', borderwidth=3 )
		codeChangeModule.pack( fill='both', expand=1, padx=0, pady=0 )
		codeChangeModule['bg'] = 'SystemButtonFace'

		# Process the offset value, based on the type of code change and current File/RAM offset display mode
		processedOffset = offset.replace('<', '').replace('>', '') # Angle bracket removal for function names.
		if ( changeType == 'static' or changeType == 'injection' ) and processedOffset:
			vanillaDol = loadVanillaDol( dolRevision, False ) # This will report any errors it has

			if not validHex( processedOffset.replace( '0x', '' ) ):
				msg( 'Warning! Invalid hex was detected in the offset value, "' + offset + '".' )

			elif vanillaDol: # Applicable offset for further processing, and Original DOL reference successfully loaded
				# Convert the offset value based on the current offset view mode (to display offsets as DOL Offsets or RAM Addresses)
				offsetView = settings.get( 'General Settings', 'offsetView' ).lstrip()[0].lower()
				if offsetView.startswith( 'd' ): # d for 'dolOffset'; indicates that the value should be shown as a DOL Offset
					computedOffset = normalizeDolOffset( processedOffset, dolObj=vanillaDol, returnType='string' ) # Converts to a DOL Offset
				else: # The value should be shown as a RAM address
					computedOffset = normalizeRamAddress( processedOffset, dolObj=vanillaDol, returnType='string' )

				# If there was an error processing the offset, preserve the original value
				if computedOffset != -1: # Error output of normalization functions above should be an int regardless of returnType
					processedOffset = computedOffset

		# Add the passed arguments as properties for this code change [frame] object.
		codeChangeModule.changeType = changeType
		codeChangeModule.newHexLabelText = ''
		codeChangeModule.customCodeLength = Tk.StringVar()
		codeChangeModule.customCodeLength.set( '(' + uHex(customCodeLength) + ' bytes)' )

		# Begin creating the inner part of the module.
		innerFrame = Tk.Frame( codeChangeModule ) # Used to create a thicker, orange border.
		innerFrame.pack( fill='both', expand=0, padx=2, pady=1 )

		# Top row; Change type, custom code length, and remove button
		topRow = Tk.Frame( innerFrame )
		topRow.pack( fill='x', padx=6, pady=4 )
		ttk.Label( topRow, text='Type:' ).pack( side='left' )
		ttk.Label( topRow, text=presentableModType( changeType, changeType=True ), foreground='#03f' ).pack( side='left' )
		ttk.Button( topRow, text='Remove', command=lambda: self.removeCodeChange(codeChangeModule) ).pack( side='right' )
		updateBtn = ttk.Button( topRow, image=imageBank['updateArrow'], command=lambda: self.updateModule( codeChangesListFrame.master, codeChangeModule, userActivated=True ) )
		updateBtn.pack( side='right', padx=12 )
		ToolTip( updateBtn, 'Use this button to update the byte count of custom code, or, once an offset is given, use it to look up and set the original '
							'hex value. For static overwrites, both an offset and custom code must be provided to get the original hex value '
							'(so that it can be determined how many bytes to look up, since static overwrites can be any length).', delay=1000, wraplength=400, follow_mouse=1 )
		ttk.Label( topRow, textvariable=codeChangeModule.customCodeLength ).pack( side='left', padx=5 )

		# Bottom row; offset and orig hex / injection site / function name
		bottomRow = Tk.Frame( innerFrame )

		# The offset
		if changeType == 'static' or changeType == 'injection':
			ttk.Label( bottomRow, text='Offset:' ).pack( side='left', padx=7 )
			codeChangeModule.offset = ttk.Entry( bottomRow, width=11 )
			codeChangeModule.offset.insert( 0, processedOffset )
			codeChangeModule.offset.pack( side='left', padx=7 )
			self.initUndoHistory( codeChangeModule.offset, processedOffset )
			codeChangeModule.offset.offsetEntry = True # Flag used in undo history feature

		# The original hex, injection site, and function name fields (also labels for the shared new hex field)
		if changeType == 'static':
			ttk.Label( bottomRow, text='Original Hex:' ).pack( side='left', padx=7 )
			codeChangeModule.originalHex = ttk.Entry( bottomRow, width=11 )
			codeChangeModule.originalHex.insert( 0, originalHex )
			codeChangeModule.originalHex.pack( side='left', padx=7, fill='x', expand=1 )
			self.initUndoHistory( codeChangeModule.originalHex, originalHex )

			codeChangeModule.newHexLabelText = 'New Hex:'

		elif changeType == 'injection':
			ttk.Label( bottomRow, text='Original Hex at\nInjection Site:' ).pack( side='left', padx=7 )
			codeChangeModule.originalHex = ttk.Entry( bottomRow, width=11 )
			codeChangeModule.originalHex.insert( 0, originalHex )
			codeChangeModule.originalHex.pack( side='left', padx=7 )
			self.initUndoHistory( codeChangeModule.originalHex, originalHex )

			codeChangeModule.newHexLabelText = 'Injection Code:'

		elif changeType == 'standalone':
			ttk.Label( bottomRow, text='Function Name:' ).pack( side='left', padx=7 )
			codeChangeModule.offset = ttk.Entry( bottomRow )
			codeChangeModule.offset.insert( 0, processedOffset )
			codeChangeModule.offset.pack( side='left', fill='x', expand=1, padx=7 )
			self.initUndoHistory( codeChangeModule.offset, processedOffset )

			codeChangeModule.newHexLabelText = 'Function Code:'

		elif changeType == 'gecko':
			codeChangeModule.newHexLabelText = 'Gecko Code:'

		bottomRow.pack( fill='x', expand=1, pady=4 )

		# Attach a newHex entry field (this will be attached to the GUI on the fly when a module is selected)
		newHexValue = newHex.replace( '|S|', '' )
		codeChangeModule.newHexField = ScrolledText( newHexFieldContainer, relief='ridge' )
		codeChangeModule.newHexField.insert( 'end', newHexValue )
		self.initUndoHistory( codeChangeModule.newHexField, newHexValue )

		# Bind a left-click event to this module (for selecting it radio-button style).
		innerFrame.bind( '<1>', self.codeChangeSelected )
		for frame in innerFrame.winfo_children():
			frame.bind( '<1>', self.codeChangeSelected )
			for widget in frame.winfo_children():
				if widget.winfo_class() != 'TButton' and widget.winfo_class() != 'TEntry': # Exclude binding from the remove button and input fields.
					widget.bind( '<1>', self.codeChangeSelected )
		
	def removeCodeChange( self, codeChangeModule ):
		versionTab = root.nametowidget( self.gameVersionsNotebook.select() )

		# Reset the newHex field if it is set for use by the currently selected module.
		if codeChangeModule['bg'] == 'orange':
			# Detach the previously selected module's newHex field
			newHexFieldContainer = versionTab.winfo_children()[1]
			self.clearNewHexFieldContainer( newHexFieldContainer )

			self.attachEmptyNewHexField( versionTab, False )

		# Delete the code change module, and update the save status
		codeChangeModule.destroy()
		self.undoableChanges = True
		self.updateSaveStatus( True )

		# If this is the last code change, remove this version tab from the notebook
		codeChangesListFrame = codeChangeModule.master
		if codeChangesListFrame.winfo_children() == []:
			versionTab.destroy()

			# If this is the last version tab, remove the Share and Save buttons, and the code changes container (notebook)
			if len( self.gameVersionsNotebook.tabs() ) == 1:
				self.gameVersionsNotebook.destroy()
				self.gameVersionsNotebook = None
				for widget in self.buttonsFrame.winfo_children()[-4:]: # Selects only the last (left-most) 4 buttons added
					widget.destroy()
			else:
				self.gameVersionsNotebook.select( self.gameVersionsNotebook.tabs()[0] ) # Select the first tab.

	def importGeckoCode( self ):
		# Prompt the user to enter the Gecko code
		userMessage = "Copy and paste your Gecko code here.\nCurrently, only opCodes 04, 06, and C2 are supported."
		entryWindow = PopupScrolledTextWindow( root, title='Gecko Codes Import', message=userMessage, width=55, height=22, button1Text='Import' )
		if not entryWindow.entryText: return

		# Get the revision for this code
		if dol.revision:
			dolRevision = dol.revision
		else: # Prompt the user for it
			revisionWindow = RevisionPromptWindow( labelMessage='Choose the region and game version that this code is for.', regionSuggestion='NTSC', versionSuggestion='02' )

			# Check the values gained from the user prompt (empty strings mean they closed or canceled the window)
			if not revisionWindow.region or not revisionWindow.version: return
			else: 
				dolRevision = revisionWindow.region + ' ' + revisionWindow.version

		# Parse the gecko code input and create code change modules for the changes
		title, newAuthors, description, codeChanges = parseGeckoCode( dolRevision, entryWindow.entryText )

		# Set the mod's title and description, if they have not already been set
		if not self.getInput( self.titleEntry ): 
			self.titleEntry.insert( 0, title )
			self.updateTabName()
		if description:
			if self.getInput( self.descScrolledText ): # If there is already some content, add a line break before the new description text
				self.descScrolledText.insert( 'end', '\n' )
			self.descScrolledText.insert( 'end', description )

		# Add any authors not already added
		currentAuthors = [ name.strip() for name in self.getInput( self.authorsEntry ).split(',') if name != '' ]
		for name in newAuthors.split( ',' ):
			if name.strip() not in currentAuthors: 
				currentAuthors.append( name.strip() )
		self.authorsEntry.delete( 0, 'end' )
		self.authorsEntry.insert( 'end', ', '.join(currentAuthors) )

		# Add the new code change modules
		for changeType, customCodeLength, offset, originalCode, customCode, _ in codeChanges:
			self.addCodeChangeModule( changeType, customCodeLength, offset, originalCode, customCode, dolRevision )

		# Mark that these changes have not been saved yet, and update the status display
		self.undoableChanges = True
		self.updateSaveStatus( True )

		playSound( 'menuChange' )

	def getCurrentlySelectedModule( self, versionTab ):
		# Get the modules' parent frame widget for the currently selected version tab.
		codeChangesListFrame = versionTab.winfo_children()[0].interior

		# Loop over the child widgets to search for the currently selected code change module
		for codeChangeModule in codeChangesListFrame.winfo_children():
			if codeChangeModule['bg'] != 'SystemButtonFace': return codeChangeModule
		else: return None

	def clearNewHexFieldContainer( self, newHexFieldContainer ): # Ensures all newHex fields are detached from the GUI.
		for widget in newHexFieldContainer.winfo_children():
			if widget.winfo_manager(): widget.pack_forget()

	def codeChangeSelected( self, event ):
		# Get the modules (parent frames) for the current/previously selected code change modules.
		versionTab = root.nametowidget( self.gameVersionsNotebook.select() )

		# Deselect any previously selected module
		previouslySelectedModule = self.getCurrentlySelectedModule( versionTab )
		if previouslySelectedModule: previouslySelectedModule['bg'] = 'SystemButtonFace'

		# Get the frame widget of the code change module that was selected and change its border color.
		codeChangeModule = event.widget
		while not hasattr( codeChangeModule, 'changeType' ): codeChangeModule = codeChangeModule.master
		codeChangeModule['bg'] = 'orange'

		# Detach the previously selected module's newHex field
		newHexFieldContainer = versionTab.winfo_children()[1]
		self.clearNewHexFieldContainer( newHexFieldContainer )

		# Attach the newHex field of the newly selected code change module (all newHex widgets share the same parent)
		codeChangeModule.newHexField.pack( fill='both', expand=1, padx=2, pady=1 )
		codeChangeModule.newHexField.focus_set() # Ensures that keypresses will go to the newly attached text field, not the old one

	def updateTabName( self ):
		# The timeout above is done, update the tab for this mod.
		newTitle = self.titleEntry.get()

		# Get the tab containing this mod; move up the GUI heirarchy until the notebook's tab (a TFrame in this case) is found.
		tabFrame = self.titleEntry.master
		while tabFrame.winfo_class() != 'TFrame': tabFrame = tabFrame.master

		# Modify the tab's title
		if newTitle.strip() == '': newTitle = 'New Mod'
		if len( newTitle ) > 40: newTitle = newTitle[:40].rstrip() + '...'
		constructionNotebook.tab( tabFrame, text=newTitle )

	def updateModule( self, versionTab, codeChangeModule, userActivated=False ):

		""" Updates the module's code length and original hex values. """

		changeType = codeChangeModule.changeType

		# Update the module's code length display
		newHex = codeChangeModule.newHexField.get( '1.0', 'end' ).strip()
		customCodeLength = getCustomCodeLength( newHex, preProcess=True, includePaths=self.includePaths )
		codeChangeModule.customCodeLength.set( '(' + uHex(customCodeLength) + ' bytes)' )

		# Make sure there is something to update; Gecko modules and SFs don't have an 'originalHex' or 'offset' field to update.
		if changeType == 'gecko' or changeType == 'standalone':
			return

		offsetString = codeChangeModule.offset.get().replace( '0x', '' ).strip()

		# Update the original hex value
		codeChangeModule.originalHex.delete( 0, 'end' )
		if ( changeType == 'static' or changeType == 'injection' ) and offsetString != '':
			if not validHex( offsetString.replace( '0x', '' ) ): msg( 'Invalid offset hex.' )
			else:
				# Determine the length of data to get from the vanilla DOL.
				byteCountToRead = 0
				if changeType == 'injection': byteCountToRead = 4
				elif changeType == 'static' and newHex != '': byteCountToRead = customCodeLength

				if byteCountToRead > 0:
					# Load a dol for reference if one is not already loaded (there may be no dol currently loaded)
					revision = self.gameVersionsNotebook.tab( versionTab, "text" )[4:]
					vanillaDol = loadVanillaDol( revision )

					# If the given offset is a RAM address, convert it to a DOL offset
					dolOffset = -1
					if len( offsetString ) == 8 and offsetString.startswith('8'): # 0x has already been removed (always assumed to be a hex value)
						offset = int( offsetString[1:], 16 )
						if offset >= 0x3100:
							if offset < vanillaDol.maxRamAddress: dolOffset = offsetInDOL( offset, vanillaDol.sectionInfo )
							else: codeChangeModule.originalHex.insert( 0, 'Address is too big' )
						else: codeChangeModule.originalHex.insert( 0, 'Address is too small' )
					else: 
						offset = int( offsetString, 16 )
						if offset >= 0x100:
							if offset < vanillaDol.maxDolOffset: dolOffset = offset
							else: codeChangeModule.originalHex.insert( 0, 'Offset is too big' )
						else: codeChangeModule.originalHex.insert( 0, 'Offset is too small' )

					# Get the original hex data, and update the GUI with the value.
					if dolOffset != -1:
						codeChangeModule.originalHex.insert( 0, vanillaDol.data[dolOffset*2:(dolOffset+byteCountToRead)*2].upper() )

	def queueUndoStatesUpdate( self, event ):
		widget = event.widget

		# Ignore certain keys which won't result in content changes. todo: Could probably add some more keys to this
		if event.keysym in ( 'Shift_L', 'Shift_R', 'Control_L', 'Control_R', 'Alt_L', 'Alt_R', 'Caps_Lock', 'Left', 'Up', 'Right', 'Down', 'Home', 'End', 'Num_Lock' ):
			return

		# Cancel any pending undo state; instead, wait until there is a sizable state/chunk of data to save
		if widget.undoStateTimer: widget.after_cancel( widget.undoStateTimer )

		# Start a new timer, to grab all changes within a certain time for one undo state
		widget.undoStateTimer = widget.after( 800, lambda w=widget: self.addUndoState(w) )

	def addUndoState( self, widget ):

		""" This is responsible for adding new undo/redo states to the undoStates list.
			If this is called and the widget's contents are the same as the current history state,
			then non-editing keys were probably pressed, such as an arrow key or CTRL/SHIFT/etc, in
			which case this method will just exit without creating a new state. """

		if widget.undoStateTimer: # This method may have been called before this fired. Make sure it doesn't fire twice!
			widget.after_cancel( widget.undoStateTimer )
		widget.undoStateTimer = None

		# Get what's currently in the input field
		if widget.winfo_class() == 'Text': # Includes ScrolledText widgets
			currentContents = widget.get( '1.0', 'end' ).strip().encode( 'utf-8' )
		else: # Pulling from an Entry widget
			currentContents = widget.get().strip().encode( 'utf-8' )

		# Check if the widget's contents have changed since the last recorded undo state. If they haven't, there's nothing more to do here.
		if currentContents == widget.undoStates[widget.undoStatesPosition]: # Comparing against the current history state
			return

		# Discard any [potential redo] history beyond the current position
		widget.undoStates = widget.undoStates[:widget.undoStatesPosition + 1]

		# Add the new current state to the undo history, and set the current history position to it
		widget.undoStates.append( currentContents )
		widget.undoStatesPosition = len( widget.undoStates ) - 1

		# Limit the size of the undo list (commented out due to currently irreconcilable issues (index out of range) with savedContents/undoPosition) todo: fix?
		# if len( widget.undoStates ) > 10:
		# 	widget.undoStates = widget.undoStates[-10:] # Forgets the earliest states

		# Check if this is a code modification offset (DOL Offset or RAM Address); Adds some special processing
		if getattr( widget, 'offsetEntry', False ):
			versionTab = root.nametowidget( self.gameVersionsNotebook.select() )
			codeChangeModule = widget.master
			while not hasattr( codeChangeModule, 'changeType' ): codeChangeModule = codeChangeModule.master
			self.updateModule( versionTab, codeChangeModule )

		# If this is the mod title, also update the name of this tab
		elif widget == self.titleEntry: self.updateTabName()

		# Update the save status
		if currentContents != widget.savedContents:
			self.updateSaveStatus( True )
		else: # Can't be sure of changes, so perform a more thorough check
			self.updateSaveStatus( self.changesArePending() )

	def undo( self, event ):
		widget = event.widget

		# If changes are pending addition to the widget's undo history, process them immediately before proceeding
		if widget.undoStateTimer: self.addUndoState( widget )

		# Decrement the current position within the undo history
		if widget.undoStatesPosition > 0:
			widget.undoStatesPosition -= 1
			self.restoreUndoState( widget )

		return 'break' # Meant to prevent the keypresses that triggered this from propagating to other events

	def redo( self, event ):
		widget = event.widget

		# If changes are pending addition to the widget's undo history, process them immediately before proceeding
		if widget.undoStateTimer: self.addUndoState( widget )

		# Increment the current position within the undo history
		if widget.undoStatesPosition < len( widget.undoStates ) - 1:
			widget.undoStatesPosition += 1
			self.restoreUndoState( widget )

		return 'break' # Meant to prevent the keypresses that triggered this from propagating to other events

	def restoreUndoState( self, widget ):
		newContents = widget.undoStates[widget.undoStatesPosition]

		# Update the contents of the widget
		if widget.winfo_class() == 'Text':
			entryPoint = '1.0'
		else: entryPoint = 0
		widget.delete( entryPoint, 'end' )
		widget.insert( 'end', newContents )

		# If there's a difference between the current input and the saved state, there are certainly pending changes.
		if newContents != widget.savedContents:
			self.updateSaveStatus( True )
		else: # Can't be sure of changes, so perform a more thorough check
			self.updateSaveStatus( self.changesArePending() )

	def getInput( self, widget ): # Gets a text or entry widget's current input while forcing undo history updates.
		# If changes are pending addition to the widget's undo history, process them immediately before proceeding
		if widget.undoStateTimer: self.addUndoState( widget )

		if widget.winfo_class() == 'Text': # Includes ScrolledText widgets
			return widget.get( '1.0', 'end' ).strip().encode( 'utf-8' )
		else: # Pulling from an Entry widget
			return widget.get().strip().encode( 'utf-8' )

	def widgetHasUnsavedChanges( self, widget ):
		currentContents = self.getInput( widget )

		# Compare the current contents to what was last saved
		if currentContents != widget.savedContents:
			return True
		else:
			return False

	def changesArePending( self ):
		if self.undoableChanges: # This is a flag for changes that have been made which "undo" can't be used for
			return True

		# Check all current code change modules for changes
		if self.gameVersionsNotebook:
			for windowName in self.gameVersionsNotebook.tabs()[:-1]: # Ignores versionChangerTab.
				versionTab = root.nametowidget( windowName )
				codeChangesListFrame = versionTab.winfo_children()[0].interior
				for codeChangeModule in codeChangesListFrame.winfo_children():
					# Check the 'New Hex' (i.e. new asm/hex code) field
					if self.widgetHasUnsavedChanges( codeChangeModule.newHexField ):
						return True

					# Get module label and Entry input field widgets
					innerFrame = codeChangeModule.winfo_children()[0]
					bottomFrameChildren = innerFrame.winfo_children()[1].winfo_children()

					# Check widgets which have undo states for changes
					for widget in bottomFrameChildren:
						if getattr( widget, 'undoStates', False ) and self.widgetHasUnsavedChanges( widget ):
							return True

		# Check the title/author/description for changes
		for widget in ( self.titleEntry, self.authorsEntry, self.descScrolledText ):
			if self.widgetHasUnsavedChanges( widget ): return True

		return False

	def updateSaveStatus( self, changesPending, message='' ):
		if changesPending:
			if not message: message = 'Unsaved'
			self.saveStatusLabel['foreground'] = '#a34343' # Shade of red
		else:
			self.saveStatusLabel['foreground'] = '#292' # Shade of green

		self.saveStatus.set( message )

	def buildModString( self ):

		""" Builds a string to store/share this mod in MCM's usual code format. """

		# Get the text input for the title and author(s)
		title = self.getInput( self.titleEntry )
		if title == '': title = 'This Mod Needs a Title!'
		authors = self.getInput( self.authorsEntry )
		if authors == '': authors = '??'

		# Validate the text input to make sure it's only basic ASCII
		for subject in ('title', 'authors'):
			stringVariable = eval( subject ) # Basically turns the string into one of the variables created above
			if not isinstance( stringVariable, str ):
				typeDetected = str(type(stringVariable)).replace("<type '", '').replace("'>", '')
				msg('The input needs to be ASCII, however ' + typeDetected + \
					' was detected in the ' + subject + ' string.', 'Input Error')
				return ''

		# Add the description and any web links (basically parsed with descriptions, so they're included together)
		description = '\n' + self.getInput( self.descScrolledText ).encode( 'ascii', 'ignore' ) # The encode filters out any non-ascii characters. todo: warn user?
		webLinksLines = []
		for urlObj, comments in self.webLinks: # Comments should still have the '#' character prepended
			webLinksLines.append( '<{}>{}'.format(urlObj.geturl(), comments) )
		if webLinksLines: description += '\n' + '\n'.join( webLinksLines )
		if description == '\n': description = '' # Remove the line break if a description is not present.
		modString = ['\n' + title + description + '\n[' + authors + ']']

		codeChangesHeader = 'Revision ---- DOL Offset ---- Hex to Replace ---------- ASM Code -'
		addChangesHeader = False

		if self.gameVersionsNotebook:
			# Gather information from each game version tab
			for windowName in self.gameVersionsNotebook.tabs()[:-1]: # Ignores versionChangerTab.
				versionTab = root.nametowidget( windowName )
				codeChangesListFrame = versionTab.winfo_children()[0].interior
				revision = self.gameVersionsNotebook.tab( versionTab, option='text' )[4:]
				addVersionHeader = True

				# Iterate the codeChanges for this game version
				for codeChangeModule in codeChangesListFrame.winfo_children():
					changeType = codeChangeModule.changeType

					# Saves the new hex field (if this module is selected), and updates the module's code length and original hex values
					self.updateModule( versionTab, codeChangeModule )

					# Get the newHex input.
					newHex = self.getInput( codeChangeModule.newHexField )
					if newHex.startswith('0x'): newHex = newHex[2:] # Don't want to replace all instances

					if changeType == 'static' or changeType == 'injection':
						addChangesHeader = True

						# Get the offset and original (vanilla game code) hex inputs. Remove whitespace & hex identifiers.
						offset = ''.join( self.getInput(codeChangeModule.offset).split() ).replace('0x', '')
						originalHex = ''.join( self.getInput(codeChangeModule.originalHex).split() ).replace('0x', '')

						# Check that inputs have been given, and then convert the ASM to hex if necessary.
						if offset == '' or newHex == '':
							msg( 'There are offset or new code values missing\nfor some ' + revision + ' changes.' )
							self.gameVersionsNotebook.select( windowName )
							return ''
						elif originalHex == '' or not validHex( originalHex ):
							msg( 'There are Original Hex values missing or invalid among the ' + revision + ' changes, and new values could not be determined. An offset may be incorrect.' )
							return ''

						# Create the beginning of the line (revision header, if needed, with dashes).
						headerLength = 13
						if addVersionHeader:
							lineHeader = revision + ' ' + ('-' * ( headerLength - 1 - len(revision) )) # extra '- 1' for the space after revision
							addVersionHeader = False
						else: lineHeader = '-' * headerLength

						# Build a string for the offset portion
						numOfDashes = 8 - len( offset )
						dashes = '-' * ( numOfDashes / 2 ) # if numOfDashes is 1 or less (including negatives), this will be an empty string
						if numOfDashes % 2 == 0: # If the number of dashes left over is even (0 is even)
							offsetString = dashes + ' ' + '0x' + offset + ' ' + dashes
						else: # Add an extra dash at the end (the int division above rounds down)
							offsetString = dashes + ' ' + '0x' + offset + ' ' + dashes + '-'

						# Build a string for a standard (short) static overwrite
						if changeType == 'static' and len(originalHex) <= 16 and newHex.splitlines()[0].split('#')[0] != '': # Last check ensures there's actually code, and not just comments/whitespace
							modString.append( lineHeader + offsetString + '---- ' + originalHex + ' -> ' + newHex )

						# Long static overwrite
						elif changeType == 'static':
							modString.append( lineHeader + offsetString + '----\n\n' + customCodeProcessor.beautifyHex(originalHex) + '\n\n -> \n\n' + newHex + '\n' )

						# Injection mod
						else:
							modString.append( lineHeader + offsetString + '---- ' + originalHex + ' -> Branch\n\n' + newHex + '\n' )

					elif changeType == 'gecko':
						if addVersionHeader: modString.append( revision + '\n' + newHex + '\n' )
						else: modString.append( newHex + '\n' )

					elif changeType == 'standalone':
						functionName = self.getInput( codeChangeModule.offset )

						# Check that a function name was given, and then convert the ASM to hex if necessary.
						if functionName == '':
							msg( 'A standalone function among the ' + revision + ' changes is missing a name.' )
							self.gameVersionsNotebook.select( windowName )
							return ''
						elif ' ' in functionName:
							msg( 'Function names may not contain spaces. Please rename those for ' + revision + ' and try again.' )
							self.gameVersionsNotebook.select( windowName )
							return ''

						# Add the name wrapper and version identifier
						functionName = '<' + functionName + '> ' + revision

						# Assemble the line string with the original and new hex codes.
						modString.append( functionName + '\n' + newHex + '\n' )

		if addChangesHeader:
			modString.insert( 1, codeChangesHeader ) # Inserts right after the initial title/author/description string

		return '\n'.join( modString )

	def _getRequiredStandaloneFunctionNames( self ):
		
		""" Gets the names of all standalone functions this mod requires. """

		if not self.gameVersionsNotebook or not self.gameVersionsNotebook.tabs(): # Latter check is a failsafe; not expected
			return [], []

		functionNames = set()
		missingFunctions = set()

		# Iterate over each game revision
		for windowName in self.gameVersionsNotebook.tabs()[:-1]: # Ignores versionChangerTab.
			versionTab = root.nametowidget( windowName )
			codeChangesListFrame = versionTab.winfo_children()[0].interior

			# Iterate the codeChanges for this game version
			for codeChangeModule in codeChangesListFrame.winfo_children():
				# Get the code for this code change, and pre-process it
				newHex = self.getInput( codeChangeModule.newHexField )
				preProcessedCustomCode = customCodeProcessor.preAssembleRawCode( newHex, self.includePaths )[1]

				functionNames, missingFunctions = parseCodeForStandalones( preProcessedCustomCode, functionNames, missingFunctions )

				# If the current code change module is a standalone function, make sure it's not in the set of "missing" SFs
				if codeChangeModule.changeType == 'standalone' and missingFunctions:
					thisFunctionName = self.getInput( codeChangeModule.offset )
					missingFunctions.remove( thisFunctionName )

		return list( functionNames ), list( missingFunctions ) # functionNames will also include those that are missing

	def saveModToLibraryAs( self ):

		""" Saves a mod to a new location. Wrapper for the saveModToLibrary method. """

		# Remember the original values for save location (in case they need to be restored), and then clear them
		originalSourceFile = self.sourceFile
		originalFileIndex = self.fileIndex
		originalMajorChanges = self.undoableChanges

		# Clear the save location properties for this mod. This forces the save function to default to creating a new file
		self.sourceFile = ''
		self.fileIndex = -1
		self.undoableChanges = True

		# Attempt to save the mod
		saveSuccedded = self.saveModToLibrary()

		# If the save failed, restore the previous save location & status
		if not saveSuccedded:
			self.sourceFile = originalSourceFile
			self.fileIndex = originalFileIndex
			self.undoableChanges = originalMajorChanges

	def saveModToLibrary( self ):
		# Make sure there are changes to be saved
		if not self.changesArePending():
			self.updateSaveStatus( False, 'No Changes to be Saved' )
			self.saveStatusLabel['foreground'] = '#333' # Shade of gray
			return

		# Confirm that this mod (if this is something from the Mod Library tab) is not currently installed
		modInstalled = False
		if self.sourceFile and self.fileIndex != -1:

			for mod in genGlobals['allMods']:
				# Compare by file and file position
				if mod.fileIndex == self.fileIndex and mod.sourceFile == self.sourceFile:
					# Double-check that this is the correct mod by name
					if mod.name != self.getInput( self.titleEntry ):
						userConfirmedEquivalency = tkMessageBox.askyesno( 'Confirm Mod Equivalency', 'Is this the same mod as "' + mod.name + '" in the Mods Library? ', parent=root )

						if not userConfirmedEquivalency:
							# Mod save location lost; inform the user and prepare to save this as a new mod.
							msg( "The Mods Library reference to the mod being edited has been lost (likely due to a duplicate mod, or manual modification/reordering of "
								'the Mods Library after opening this mod in the Mod Construction tab). Without verification of this reference, the original '
								'save location of this mod cannot be certain. To prevent the overwrite of a different mod, this must be saved as a new mod.' )
							self.saveModToLibraryAs()
							return

					# Equivalent mod found. Check whether it's installed in a game disc/DOL
					if mod.state == 'enabled' or mod.state == 'pendingDisable':
						modInstalled = True
					
					break

		if modInstalled:
			msg( 'Mods must be uninstalled from your game before modifying them.' )
			self.updateSaveStatus( True, 'Unable to Save' )
			return False

		modString = self.buildModString() # This will also immediately update any pending undo history changes

		if not modString: # Failsafe, assuming the method above will report any possible errors
			self.updateSaveStatus( True, 'Unable to Save' )
			return False

		saveSuccessful = False
		userCanceled = False

		# Prompt for a file to save to if no source file is defined. (Means this was newly created in the GUI, or this is a 'SaveAs' operation)
		if self.sourceFile == '':
			targetFile = tkFileDialog.askopenfilename(
				title="Choose the file you'd like to save the mod to (it will be appended to the end).",
				initialdir=getModsFolderPath(),
				filetypes=[ ('Text files', '*.txt'), ('all files', '*.*') ]
				)

			if not targetFile:
				userCanceled = True
			else:
				# Append this mod to the end of the target Mod Library text file (could be a new file, or an existing one).
				try:
					if os.path.exists( targetFile ):
						# Set this mod's save location so that subsequent saves will automatically go to this same place, and check if a separator is needed.
						self.sourceFile = targetFile
						with open( targetFile, 'r') as modFile:
							fileContents = modFile.read()
						if fileContents:
							self.fileIndex = len( fileContents.split( '-==-' ) )
							modString = '\n\n\n\t-==-\n\n' + modString # Prepends a separator to this mod.
						else: self.fileIndex = 0

						# Save the mod to the file.
						with open( targetFile, 'a' ) as libraryFile:
							libraryFile.write( modString )
						saveSuccessful = True
				except Exception as err:
					print( 'Unable to save the mod to the library file:' )
					print( err )

				# Rebuild the include paths list, using this new file for one of the paths
				modsFolderIncludePath = os.path.join( getModsFolderPath(), '.include' )
				self.includePaths = [ os.path.dirname(targetFile), modsFolderIncludePath, os.path.join(scriptHomeFolder, '.include') ]

		else: # A source file is already defined.
			if self.fileIndex == -1: msg( "The index (file position) for this mod could not be determined. Try using 'Save As' to save this mod to the end of a file." )
			else:
				targetFile = self.sourceFile

				# Make sure the target file can be found, then replace the mod within it with the new version.
				if not os.path.exists( targetFile ):
					msg( 'Unable to locate the Library file:\n\n' + targetFile )

				else: 
					try:
						# Pull the mods from their library file, and separate them.
						with open( targetFile, 'r') as modFile:
							mods = modFile.read().split( '-==-' )

						# Replace the old mod, reformat the space in-between mods, and recombine the file's text.
						mods[self.fileIndex] = modString
						mods = [code.strip() for code in mods] # Removes the extra whitespace around mod strings.
						completedFileText = '\n\n\n\t-==-\n\n\n'.join( mods )

						with open( targetFile, 'w' ) as libraryFile:
							libraryFile.write( completedFileText )

						saveSuccessful = True
					except: pass

		if saveSuccessful:
			# Iterate over all code change modules to update their save state history (saved contents updated to match current undo history index)
			for windowName in self.gameVersionsNotebook.tabs()[:-1]: # Ignores versionChangerTab.
				versionTab = root.nametowidget( windowName )
				codeChangesListFrame = versionTab.winfo_children()[0].interior

				# Iterate the codeChanges for this game version
				for codeChangeModule in codeChangesListFrame.winfo_children():
					if getattr( codeChangeModule.newHexField, 'undoStates', None ): # May return an empty list, in which case the contents haven't been modified
						# Update the 'New Hex' (i.e. new asm/hex code) field
						codeChangeModule.newHexField.savedContents = codeChangeModule.newHexField.get( '1.0', 'end' ).strip().encode( 'utf-8' )

					# Get module label and Entry input field widgets
					innerFrame = codeChangeModule.winfo_children()[0]
					bottomFrameChildren = innerFrame.winfo_children()[1].winfo_children()

					# Update those widgets (which have undo states) with changes
					for widget in bottomFrameChildren:
						if getattr( widget, 'undoStates', False ):
							widget.savedContents = widget.get().strip().encode( 'utf-8' )

			# Update the saved contents for the standard input fields
			for widget in ( self.titleEntry, self.authorsEntry, self.descScrolledText ):
				if getattr( widget, 'undoStates', None ): # May return an empty list, in which case the contents haven't been modified
					if widget.winfo_class() == 'Text': # Includes ScrolledText widgets
						widget.savedContents = widget.get( '1.0', 'end' ).strip().encode( 'utf-8' )
					else: # Pulling from an Entry widget
						widget.savedContents = widget.get().strip().encode( 'utf-8' )

			# Update the flag used for tracking other undoable changes
			self.undoableChanges = False

			# Give an audio cue and update the GUI
			playSound( 'menuSelect' )
			self.updateSaveStatus( False, 'Saved To Library' )

			# Reload the library to get the new or updated codes.
			scanModsLibrary( playAudio=False )

		else:
			if userCanceled:
				self.updateSaveStatus( True, 'Operation Canceled' )
			else:
				self.updateSaveStatus( True, 'Unable to Save' )
		
		return saveSuccessful

	def analyzeMod( self ):

		""" Collects information on this mod, and shows it to the user in a pop-up text window. """ # todo: switch to joining list of strings for efficiency

		# Assemble the header text
		analysisText = 'Info for "' + self.getInput( self.titleEntry ) + '"'
		analysisText += '\nProgram Classification: ' + self.type
		if os.path.isdir( self.sourceFile ):
			analysisText += '\nSource Folder: ' + self.sourceFile
		elif os.path.exists( self.sourceFile ):
			analysisText += '\nSource File: ' + self.sourceFile
			analysisText += '\nPosition in file: ' + str( self.fileIndex )
		else:
			analysisText += '\nSource: Unknown! (The source path could not be found)'

		availability = []
		totalCodeChanges = 0
		changeTypeTotals = {}

		# Check for all code changes (absolute total, and totals per type).
		if self.gameVersionsNotebook:
			for windowName in self.gameVersionsNotebook.tabs()[:-1]: # Skips tab used for adding revisions
				versionTab = root.nametowidget( windowName ) # Gets the actual widget for this tab

				availability.append( self.gameVersionsNotebook.tab( versionTab, option='text' )[4:] )
				codeChangesListFrame = versionTab.winfo_children()[0].interior
				codeChangeModules = codeChangesListFrame.winfo_children()
				totalCodeChanges += len( codeChangeModules )

				# Count the number of changes for each change type, and get the standalone functions required
				for codeChange in codeChangeModules:
					if codeChange.changeType not in changeTypeTotals: changeTypeTotals[codeChange.changeType] = 1
					else: changeTypeTotals[codeChange.changeType] += 1
		
		# Construct strings for what code change types are present, and their counts
		analysisText += '\nCode changes available for ' + grammarfyList( availability ) + '\n\nCode Changes (across all game versions):'
		for changeType in changeTypeTotals:
			analysisText += '\n - ' + presentableModType( changeType ) + 's: ' + str( changeTypeTotals[changeType] )

		# Check for required SFs
		requiredStandaloneFunctions, missingFunctions = self._getRequiredStandaloneFunctionNames()
		if not requiredStandaloneFunctions: analysisText += '\n\nNo Standalone Functions required.'
		else:
			analysisText += '\n\nRequired Standalone Functions:\n' + '\n'.join( requiredStandaloneFunctions )

			if missingFunctions: 
				analysisText += '\n\nThese functions are required, but are not packaged with this mod:\n' + '\n'.join( missingFunctions )

		analysisText += '\n\n\tInclude Paths:\n' + '\n'.join( self.includePaths )

		# Present the analysis to the user in a new window
		cmsg( analysisText, 'Info for "' + self.getInput( self.titleEntry ) + '"', 'left' )

	def switchOffsetDisplayType( self ):

		""" Goes through each of the code changes, and swaps between displaying offsets as DOL offsets or RAM addresses. 
			These are still tracked as strings, so they will be saved in the chosen form in the library files as well. """

		# Toggle the saved variable and the button text (and normalize the string since this is exposed to users in the options.ini file)
		offsetView = settings.get( 'General Settings', 'offsetView' ).lstrip().lower()
		if offsetView.startswith( 'd' ):
			offsetView = 'ramAddress'
			buttonText = 'Display DOL Offsets'
		else:
			offsetView = 'dolOffset'
			buttonText = 'Display RAM Addresses'
		self.offsetViewBtn['text'] = buttonText

		# Iterate over the tabs for each game version
		for tabWindowName in self.gameVersionsNotebook.tabs()[:-1]: # Skips tab for adding revisions
			versionTab = root.nametowidget( tabWindowName )
			revision = self.gameVersionsNotebook.tab( versionTab, option='text' )[4:]
			codeChangesListFrame = versionTab.winfo_children()[0].interior
			codeChangeModules = codeChangesListFrame.winfo_children()

			# Iterate over the code change modules for this game version
			for i, module in enumerate( codeChangeModules, start=1 ):
				if module.changeType == 'static' or module.changeType == 'injection':
					# Get the current value
					origOffset = module.offset.get().strip().replace( '0x', '' )

					# Validate the input
					if not validHex( origOffset ):
						if len( self.gameVersionsNotebook.tabs() ) > 2: # Be specific with the revision
							msg( 'Invalid hex detected for the offset of code change {} of {}: "{}".'.format(i, revision, module.offset.get().strip()), 'Invalid Offset Characters' )
						else: # Only one revision to speak of
							msg( 'Invalid hex detected for the offset of code change {}: "{}".'.format(i, module.offset.get().strip()), 'Invalid Offset Characters' )
						continue

					# Convert the value
					if offsetView == 'dolOffset':
						newOffset = normalizeDolOffset( origOffset, dolObj=originalDols[revision], returnType='string' )
					else: newOffset = normalizeRamAddress( origOffset, dolObj=originalDols[revision], returnType='string' )

					# Validate the converted ouput value
					if newOffset == -1: continue # A warning would have been given to the user from the above normalization function

					# Display the value
					module.offset.delete( 0, 'end' )
					module.offset.insert( 0, newOffset )

		# Remember the current display option
		settings.set( 'General Settings', 'offsetView', offsetView )
		saveOptions()

	def closeMod( self ):
		# If there are unsaved changes, propt whether the user really wants to close.
		if self.saveStatusLabel['foreground'] == '#a34343':
			sureToClose = tkMessageBox.askyesno( 'Unsaved Changes', "It looks like this mod may have some changes that haven't been saved to your library. Are you sure you want to close it?" )
			if not sureToClose: return

		self.master.destroy()

	def addWebLink( self, urlObj, comments, modChanged=True ):
		
		url = urlObj.geturl()
		domain = urlObj.netloc.split( '.' )[-2] # i.e. 'smashboards' or 'github'
		destinationImage = imageBank[ domain + 'Link' ]
		
		# Add an image for this link
		imageLabel = ttk.Label( self.webLinksFrame, image=destinationImage )
		imageLabel.urlObj = urlObj
		imageLabel.comments = comments
		imageLabel.pack()

		# Add hover tooltips
		hovertext = 'The {}{} page...\n{}'.format( domain[0].upper(), domain[1:], url )
		if comments: hovertext += '\n\n' + comments
		ToolTip( imageLabel, hovertext, delay=700, wraplength=800, justify='center' )

		# if modChanged: # If false, this is being called during initialization
		# 	self.undoableChanges = True


class WebLinksEditor( BasicWindow ):

	""" Tool window to add/remove web links in the Mod Construction tab. """

	def __init__( self, webLinksFrame ):
		BasicWindow.__init__( self, globalData.gui.root, 'Web Links Editor', offsets=(160, 100), resizable=True, topMost=False )

		ttk.Label( self.window, text=('Web links are useful sources of information, or links to places of discussion.'
			'\nCurrent valid destinations are SmashBoards, GitHub, and YouTube.'), wraplength=480 ).grid( columnspan=3, column=0, row=0, padx=40, pady=10 )

		# Iterate over the widgets in the 'Web Links' frame in the other window, to create new widgets here based on them
		row = 1
		for label in webLinksFrame.winfo_children():
			# Get info from this label widget
			url = label.urlObj.geturl()
			domain = label.urlObj.netloc.split( '.' )[-2] # i.e. 'smashboards' or 'github'
			destinationImage = imageBank[ domain + 'Link' ]

			# Can't clone the label, so make a new one
			imageLabel = ttk.Label( self.window, image=destinationImage )
			imageLabel.grid( column=0, row=row )

			# Add a text field entry for the URL
			urlEntry = ttk.Entry( self.window, width=70 )
			urlEntry.insert( 0, url )
			urlEntry.grid( column=1, row=row, sticky='ew' )

			# Add the comment below this, if there is one, and the button to add/edit them
			if label.comments:
				# Add the add/edit comment button
				commentsBtn = Tk.Button( self.window, text='Edit Comment', anchor='center' )
				commentsBtn.grid( column=2, row=row, padx=14, pady=5 )

				# Add the comment
				commentLabel = ttk.Label( self.window, text=label.comments.lstrip(' #') )
				commentLabel.grid( column=1, row=row+1, sticky='new' )

				# Add the remove button
				removeBtn = Tk.Button( self.window, text='-', width=2 )
				ToolTip( removeBtn, 'Remove', delay=700 )
				removeBtn.grid( column=3, row=row, padx=(0, 14) )
				row += 2
			else:
				# Add the add/edit comment button
				commentsBtn = Tk.Button( self.window, text='Add Comment', anchor='center' )
				commentsBtn.grid( column=2, row=row, padx=14, pady=5 )

				# Add the remove button
				removeBtn = Tk.Button( self.window, text='-', width=2 )
				ToolTip( removeBtn, 'Remove', delay=700 )
				removeBtn.grid( column=3, row=row, padx=(0, 14) )
				row += 1
		
		# Add the 'Add' and 'OK / Cancel' buttons
		buttonsFrame = ttk.Frame( self.window )
		ttk.Button( buttonsFrame, text='OK' ).pack( side='left', padx=(0, 15) )
		ttk.Button( buttonsFrame, text='Cancel', command=self.close ).pack( side='right' )
		buttonsFrame.grid( columnspan=4, column=0, row=row, pady=14 )
		addBtn = Tk.Button( self.window, text='Add Link', width=12 )
		addBtn.grid( columnspan=2, column=2, row=row )

		# Allow the grid to resize
		self.window.columnconfigure( 0, weight=1, minsize=46 )
		self.window.columnconfigure( 1, weight=3 )
		#self.window.columnconfigure( (2, 3), weight=1 )
		self.window.columnconfigure( 2, weight=1, minsize=120 )
		self.window.columnconfigure( 3, weight=1, minsize=35 )
		self.window.rowconfigure( 'all', weight=1 )


class CodeConfigWindow( BasicWindow ):

	""" Provides a user interface (a new window, created by clicking on a mod config buttton) 
		for viewing or changing a mod's configuration options. """

	def __init__( self, mod, configurations ):
		# Found some public config options; create the configuration window
		super( CodeConfigWindow, self ).__init__( globalData.gui.root, mod.name + ' - Configuration', resizable=True, minsize=(450, 100) )

		self.mod = mod
		#self.skipValidation = False
		self.allowSliderUpdates = True
		sepPad = 7 # Separator padding
		vPad = ( 8, 0 ) # Vertical padding
		validationCommand = globalData.gui.root.register( self.entryUpdated )

		self.optionsFrame = VerticalScrolledFrame( self.window )
		
		ttk.Separator( self.optionsFrame.interior, orient='horizontal' ).grid( column=0, columnspan=3, row=0, pady=vPad[0], sticky='ew', padx=sepPad )

		# Add rows for each option to be displayed
		row = 1
		for optionName, optionDict in configurations:
			
			# Check the type and data width
			optType = optionDict.get( 'type' )
			currentValue = optionDict.get( 'value' )
			if not optType or currentValue == None: # Failsafe; should have been validated by now
				globalData.gui.updateProgramStatus( '{} missing critical configuration details!'.format(optionName) )
				continue

			# Optional parameters
			optRange = optionDict.get( 'range' )
			optMembers = optionDict.get( 'members' )
			optComment = optionDict.get( 'annotation' )

			# Add the option name, with a comment/annotation if one is available
			nameLabel = ttk.Label( self.optionsFrame.interior, text=optionName ) #  + u'  \N{BLACK DOWN-POINTING TRIANGLE}'
			nameLabel.grid( column=0, row=row, sticky='w', padx=28 )

			# Add a hover tooltip to the name
			details = 'Type:  {}\nDefault value:  {}'.format( optType, optionDict['default'] )
			if optComment:
				optComment += '\n' + details
			else:
				optComment = details
			ToolTip( nameLabel, text=optComment.lstrip( '# ' ), wraplength=400, delay=800 )

			# Add a control widget
			#if len( optMembers ) == 2 and : # Create an On/Off toggle
			#elif # Create a color chooser
			if optMembers: # Create a dropdown menu
				# Format options for the dropdown
				options, default, comments = self.formatDropdownOptions( optMembers, optType, currentValue )

				inputWidget = ttk.OptionMenu( self.optionsFrame.interior, Tk.StringVar(), default, *options )
				if comments:
					ToolTip( inputWidget, text='\n'.join(comments), wraplength=250 )

			elif optType == 'float': # Create float value entry
				inputWidget = DisguisedEntry( self.optionsFrame.interior, width=8, validate='key', justify='right' )

			else: # Create a standard value entry (int/uint)
				inputWidget = DisguisedEntry( self.optionsFrame.interior, width=8, validate='key', justify='right' )

			# Add the input widget to the interface and give it its initial value
			inputWidget.option = optionName
			inputWidget.optType = optType
			if inputWidget.winfo_class() == 'TMenubutton': # This is actually the OptionMenu (dropdown) widget
				inputWidget.grid( column=2, row=row, sticky='e', padx=28 )
			else: # Entry
				inputWidget.optRange = optRange
				inputWidget.insert( 0, currentValue )
				inputWidget.slider = None
				inputWidget.configure( validatecommand=(validationCommand, '%P', '%W') )
				inputWidget.grid( column=2, row=row, sticky='e', padx=46, ipadx=10 )

				# Add a slider if a range was provided
				if optRange:
					#start, end = optRange
					start, end = mod.parseConfigValue( optType, optRange[0] ), mod.parseConfigValue( optType, optRange[1] )
					currentValue = mod.parseConfigValue( optType, currentValue )
					#print( optionName, start, '-', end )
					slider = ttk.Scale( self.optionsFrame.interior, from_=start, to=end, length=180, value=currentValue )
					slider.configure( command=lambda v, w=inputWidget: self.sliderUpdated(v, w) )
					slider.grid( column=1, row=row, padx=(14, 7), sticky='ew' )

					inputWidget.optRange = ( start, end )
					inputWidget.slider = slider

			ttk.Separator( self.optionsFrame.interior, orient='horizontal' ).grid( column=0, columnspan=3, row=row+1, pady=vPad[0], sticky='ew', padx=sepPad )
			row += 2
		
		self.optionsFrame.grid( column=0, row=0, pady=vPad, padx=40, ipadx=0, sticky='nsew' )

		self.optionsFrame.interior.rowconfigure( 'all', weight=1 )
		self.optionsFrame.interior.columnconfigure( 0, weight=1 )
		self.optionsFrame.interior.columnconfigure( 1, weight=2 )
		self.optionsFrame.interior.columnconfigure( 2, weight=1 )
		
		# Add the bottom row of buttons
		buttonsFrame = ttk.Frame( self.window )
		ttk.Button( buttonsFrame, text='OK', command=self.confirmChanges ).grid( column=0, row=0, padx=9 )
		ttk.Button( buttonsFrame, text='Reset to Defaults', command=self.setToDefaults ).grid( column=1, row=0, padx=9, ipadx=5 )
		ttk.Button( buttonsFrame, text='Cancel', command=self.close ).grid( column=2, row=0, padx=9 )
		buttonsFrame.grid( column=0, row=1, pady=10, padx=12, ipadx=12 )

		# Add resize capability (should allow buttons to always be visible, and instead force resize of the optionFrame)
		self.window.rowconfigure( 0, weight=1 )
		self.window.rowconfigure( 1, weight=0 )
		self.window.columnconfigure( 'all', weight=1 )

	# def getOptionWidth( self, optionType ):

	# 	if optionType.endswith( '32' ) or optionType == 'float':
	# 		return 4
	# 	elif optionType.endswith( '16' ):
	# 		return 2
	# 	elif optionType.endswith( '8' ):
	# 		return 1
	# 	else:
	# 		return -1

	def formatDropdownOptions( self, members, optType, initValue ):

		""" Returns a list of formatted options for a dropdown menu, 
			along with a default option and a list of comments. """

		options = []
		comments = []
		default = '' # Initial default selection for the dropdown
		initValue = self.mod.parseConfigValue( optType, initValue ) # Normalize for the comparison

		for opt in members: # List of [name, value] or [name, value, comment]
			name = opt[0].strip()
			value = self.mod.parseConfigValue( optType, opt[1] )
			options.append( '{}  |   {}'.format(value, name) )

			if value == initValue:
				default = '{}  |   {}'.format(value, name)

			if len( opt ) == 3 and opt[-1] != '':
				comment = opt[2].lstrip( '# ' )
				comments.append( '{}: {}'.format(name, comment) )

		if not default:
			default = '{}  |   Unlisted Selection!'.format( initValue )

		return options, default, comments

	def validEntryValue( self, widget, inputString ):

		""" Returns True/False on whether or not the given string is a valid value 
			input for the given input widget; tests string to int/float casting, 
			value ranges (if available), and value to bytes packing. """

		try:
			value = self.mod.parseConfigValue( widget.optType, inputString )

			# Make sure it's within range
			if widget.optRange:
				if value < widget.optRange[0]:
					raise Exception( 'value is less than lower range limit' )
				if value > widget.optRange[1]:
					raise Exception( 'value is greater than upper range limit' )

			# Validate the value with the type (make sure it's packable into the alloted space; e.g. 256 can't be packed to one byte)
			struct.pack( ConfigurationTypes[widget.optType], value )
			
			# Update an associated slider if present
			if widget.slider:
				# Prevent slider from updating Entry to prevent infinite loop
				self.allowSliderUpdates = False
				widget.slider.set( value )
				self.allowSliderUpdates = True

			return True

		except Exception as err:
			globalData.gui.updateProgramStatus( 'Invalid value entry detected; {}'.format(err) )
			return False

	def entryUpdated( self, newString, widgetName ):

		""" Run some basic validation on the input and color the widget text red if invalid. 
			Must return True to validate the entered text and allow it to be displayed. """

		widget = globalData.gui.root.nametowidget( widgetName )

		if self.validEntryValue( widget, newString ):
			widget['foreground'] = '#292' # Green
		else:
			widget['foreground'] = '#a34343' # Red

		return True

	def sliderUpdated( self, value, entryWidget ):

		""" Called when a slider is updated in order to update its associated Entry widget. """

		if not self.allowSliderUpdates: # Can be turned off to preven updating associated Entry widget
			return

		# Temporarily disable validation
		entryWidget.configure( validate='none' )
		entryWidget.delete( 0, 'end' )

		if entryWidget.optType == 'float':
			entryWidget.insert( 0, value )
		else:
			entryWidget.insert( 0, int(float( value )) )
		entryWidget['foreground'] = '#292' # Green

		#self.skipValidation = False
		entryWidget.configure( validate='key' )

	def confirmChanges( self ):

		""" Validates input in all input widgets"""

		changesToSave = {} # Store them until all input has been validated (user may still cancel after notification of invalid input)

		# Iterate over input widgets in column 2
		for widget in self.optionsFrame.interior.grid_slaves( column=2 ):
			widgetClass = widget.winfo_class()
			if widgetClass == 'TSeparator':
				continue

			# Update values from dropdown (OptionMenu) widgets
			if widgetClass == 'TMenubutton':
				sValue = widget._variable.get().split( '|' )[0]
				currentValue = int( sValue )
			elif widgetClass == 'Entry':
				currentValue = widget.get()

				# Validate the current input value
				if not self.validEntryValue( widget, currentValue ):
					msg( 'The value entry for {} appears to be invalid. Please double-check it and try again.'.format(widget.option), 'Invalid Value Detected' )
					break
			else:
				raise Exception( 'Unexpected input widget class: {}'.format(widgetClass) )

			changesToSave[widget.option] = currentValue

		else: # The loop above didn't break; all values validated. Time to save changes and close
			for optionName, value in changesToSave.items():
				self.mod.configurations[optionName]['value'] = value

			self.close()

	def setToDefaults( self ):

		""" Reset current values in the mod's configuration to default settings, 
			and update the GUI to reflect this. """

		# Iterate over input widgets in column 2
		for widget in self.optionsFrame.interior.grid_slaves( column=2 ):
			widgetClass = widget.winfo_class()
			if widgetClass == 'TSeparator':
				continue

			optionDict = self.mod.configurations[widget.option]
			defaultValue = optionDict['default']

			# Update the current value in the mod's configuration
			optionDict['value'] = defaultValue

			# Update values from dropdown (OptionMenu) widgets
			if widgetClass == 'TMenubutton':
				members = optionDict.get( 'members', [] )
				default = self.formatDropdownOptions( members, widget.optType, defaultValue )[1]
				widget._variable.set( default )

			elif widgetClass == 'Entry':
				# Temporarily disable validation and set the default value in the widget
				#self.skipValidation = True
				widget.configure( validate='none' )
				widget.delete( 0, 'end' )
				widget.insert( 0, defaultValue )

				# Change the font back to normal and re-enable validation
				widget['foreground'] = 'black'
				#self.skipValidation = False
				widget.configure( validate='key' )

				if widget.slider:
					defaultValue = self.mod.parseConfigValue( widget.optType, defaultValue )
					widget.slider.set( defaultValue )
	