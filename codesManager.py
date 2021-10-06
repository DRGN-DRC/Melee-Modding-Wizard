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
import os
import ttk
import time
import struct
import urlparse
import webbrowser
import tkMessageBox
import Tkinter as Tk
from urlparse import urlparse 	# For validating and security checking URLs

# Internal Dependencies
import globalData
from disc import Disc
from basicFunctions import msg, openFolder, validHex
from codeMods import ConfigurationTypes, regionsOverlap, CodeLibraryParser
from guiSubComponents import (
	exportSingleFileWithGui, VerticalScrolledFrame, LabelButton, ToolTip, CodeLibrarySelector, 
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
		self.stopToRescan = False
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
			print 'already selected'
			return

		# Prevent focus on the tabs themselves (prevents appearance of selection box)
		# currentTab = globalData.gui.root.nametowidget( self.codeLibraryNotebook.select() )
		# currentTab.focus()
		#print 'tab changed; called with event:', event
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
		if not currentTab: return

		modsPanel = currentTab.winfo_children()[0]
		foundMcmFormatting = False

		for mod in modsPanel.mods:
			ModModule( modsPanel.interior, mod ).pack( fill='x', expand=1 )

			if not mod.isAmfs:
				foundMcmFormatting = True

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
			return

		#print 'aligning control panel; called with event:', (event)

		if not currentTab:
			currentTab = self.getCurrentTab()

		if currentTab:
			# Get the VerticalScrolledFrame of the currently selected tab
			modsPanel = currentTab.winfo_children()[0]

			# Get the new coordinates for the control panel frame
			globalData.gui.root.update_idletasks() # Force the GUI to update in order to get correct new widget positions & sizes.
			currentTabWidth = currentTab.winfo_width()

			self.controlPanel.place( in_=currentTab, x=currentTabWidth * .60, width=currentTabWidth * .40, height=modsPanel.winfo_height() )
		else:
			# Align and place according to the main library notebook instead
			notebookWidth = self.codeLibraryNotebook.winfo_width()
			self.controlPanel.place( in_=self.codeLibraryNotebook, x=notebookWidth * .60, width=notebookWidth * .40, height=self.codeLibraryNotebook.winfo_height() )
			
	def updateInstalledModsTabLabel( self, currentTab=None ):

		""" Updates the installed mods count at the bottom of the control panel. """

		if not currentTab:
			currentTab = self.getCurrentTab()
			if not currentTab:
				print '.updateInstalledModsTabLabel() unable to get a current tab.'
				return

		# Get the widget providing scrolling functionality (a VerticalScrolledFrame widget), and its children mod widgets
		scrollingFrame = currentTab.winfo_children()[0]
		scrollingFrameChildren = scrollingFrame.interior.winfo_children()

		# Count the mods enabled or selected for installation
		enabledMods = 0
		for modModule in scrollingFrameChildren:
			if modModule.mod.state == 'enabled' or modModule.mod.state == 'pendingEnable':
				enabledMods += 1

		self.installTotalLabel.set( 'Enabled on this tab:  {} / {}'.format(enabledMods, len( scrollingFrameChildren )) )

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

	def _reattachTabChangeHandler( self, notebook ):

		""" Even though the onTabChange event handler is unbound in .scanCodeLibrary(), several 
			events will still be triggered, and will linger until the GUI's thread can get back 
			to them. When that happens, if the tab change handler has been re-binded, the handler 
			will be called for each event (even if they occurred while the handler was not binded. 
			
			Thus, this method should be called after idle tasks from the main gui (which includes 
			the tab change events) have finished. """

		print 'reattaching for', notebook

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
		self.stopToRescan = False
		self.parser.stopToRescan = False
		self.scanCodeLibrary( playAudio )

	def scanCodeLibrary( self, playAudio=True ):

		""" The main method to scan (parse) a code library, and then call the methods to scan the DOL and 
			populate this tab with the mods found. Also defines half of the paths used for .include statements. 
			The other two .include import paths (CWD and the folder housing each mod text file) will be prepended
			to the lists seen here. """

		# If this scan is triggered while it is already running, queue/wait for the previous iteration to cancel and re-run
		if self.isScanning:
			self.stopToRescan = True
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
			warningMsg = 'Unable to find this code library:\n\n' + self.libraryFolder
			ttk.Label( self.codeLibraryNotebook, text=warningMsg, background='white', wraplength=600, justify='center' ).place( relx=0.3, rely=0.5, anchor='center' )
			ttk.Label( self.codeLibraryNotebook, image=globalData.gui.imageBank('randall'), background='white' ).place( relx=0.3, rely=0.5, anchor='s', y=-20 ) # y not :P
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

		self.populateCodeLibraryTabs( targetCategory, sliderYPos )

		# Check once more if another scan is queued. (e.g. if the scan mods button was pressed again while checking for installed mods)
		if self.stopToRescan:
			self.restartScan( playAudio )
		else:
			toc = time.clock()
			print 'library parsing time:', toc - tic

			#totalModsInLibraryLabel.set( 'Total Mods in Library: ' + str(len( self.codeModModules )) ) # todo: refactor code to count mods in the modsPanels instead
			#totalSFsInLibraryLabel.set( 'Total Standalone Functions in Library: ' + str(len( collectAllStandaloneFunctions(self.codeModModules, forAllRevisions=True) )) )

			self.isScanning = False
			self.stopToRescan = False

			# Wait to let tab change events fizzle out before reattaching the onTabChange event handler
			#self.update_idletasks()
			self.after_idle( self._reattachTabChangeHandler, self.codeLibraryNotebook )
			#self.onTabChange( forceUpdate=True ) # Make sure it's called at least once
			# self.after_idle( self.TEST, 'test1' ) # called in-order
			# self.after_idle( self.TEST, 'test2' )
			self.after_idle( self.onTabChange, None, True )

			if playAudio:
				#playSound( 'menuChange' )
				print 'beep!'

	# def TEST( self, string ):
	# 	print string

	def populateCodeLibraryTabs( self, targetCategory='', sliderYPos=0 ):

		""" Creates ModModule objects for the GUI, as well as vertical scroll frames/Notebook 
			widgets needed to house them, and checks for installed mods to set module states. """

		notebookWidgets = { '': self.codeLibraryNotebook }
		modsPanels = {}
		modPanelToScroll = None

		# If no mods are present, add a simple message and return
		if not globalData.codeMods:
			ttk.Label( self.codeLibraryNotebook, image=globalData.gui.imageBank('randall'), background='white' ).place( relx=0.3, rely=0.5, anchor='s', y=-20 ) # y not :P
			warningMsg = 'Unable to find code mods in this library:\n\n' + self.libraryFolder
			ttk.Label( self.codeLibraryNotebook, text=warningMsg, background='white', wraplength=600, justify='center' ).place( relx=0.3, rely=0.5, anchor='center' )
			return

		# If a disc is loaded, check if the parsed mods are installed in it
		if globalData.disc:
			globalData.disc.dol.checkForEnabledCodes( globalData.codeMods )

		#print '\tThese mods detected as installed:'

		for mod in globalData.codeMods:
			if mod.isAmfs: # Its source path is already a directory
				modParentFolder = mod.path
			else:
				modParentFolder = os.path.dirname( mod.path )
			
			# Get a path for this mod, relative to the library root (display core codes as relative to root as well)
			if mod.isAmfs and os.path.dirname( modParentFolder ) == globalData.paths['coreCodes']:
				relPath = ''
			elif modParentFolder == globalData.paths['coreCodes']: # For the "Core Codes.txt" file
				relPath = ''
			else:
				relPath = os.path.relpath( modParentFolder, self.libraryFolder )
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
						# print 'adding notebook', notebook._name, 'to', parent._name, 'for', thisTabPath
						notebookWidgets[thisTabPath] = notebook

					parent = notebook

					# Add a vertical scrolled frame to the last notebook
					if i == len( pathParts ) - 1: # Reached the last part (the category)
						placementFrame = ttk.Frame( parent ) # This will be the "currentTab" widget returned from .getCurrentTab()
						parent.add( placementFrame, text=mod.category )

						# Create and add the mods panel (placement frame above needed so we can .place() the mods panel)
						modsPanel = VerticalScrolledFrame( placementFrame )
						modsPanel.mods = []
						#print 'adding VSF', modsPanel._name, 'to', placementFrame._name, 'for', thisTabPath + '\\' + mod.category
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
			# 	print mod.name

		# If a previous tab and scroll position are desired, set them here
		if modPanelToScroll:
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
				ttk.Label( notebook, image=globalData.gui.imageBank('randall'), background='white' ).place( relx=0.3, rely=0.5, anchor='s', y=-20 ) # y not :P
				warningMsg = 'No code mods found in this folder or cetegory.'
				ttk.Label( notebook, text=warningMsg, background='white', wraplength=600, justify='center' ).place( relx=0.3, rely=0.5, anchor='center' )

	def _updateScrollPosition( self, modPanel, sliderYPos ):
		print 'updating scroll position'
		self.update_idletasks()
		modPanel.canvas.yview_moveto( sliderYPos )

	def autoSelectCodeRegions( self ):

		""" If 20XX is loaded, this attempts to recognize its version and select the appropriate custom code regions. """

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

	def saveIniFile( self ): pass
	def saveGctFile( self ): pass

	def selectAllMods( self, event ):
		currentTab = self.getCurrentTab()

		for mod in currentTab.winfo_children()[0].mods:
			if mod.state == 'pendingDisable': mod.setState( 'enabled' )
			elif mod.state == 'disabled': mod.setState( 'pendingEnable' )

		#playSound( 'menuChange' )

	def deselectAllMods( self, event ):
		currentTab = self.getCurrentTab()

		for mod in currentTab.winfo_children()[0].mods:
			if mod.state == 'pendingEnable': mod.setState( 'disabled' )
			elif mod.state == 'enabled': mod.setState( 'pendingDisable' )

		#playSound( 'menuChange' )

	def selectWholeLibrary( self, event ):

		for tab in self.getAllTabs():
			for mod in tab.winfo_children()[0].mods:
				if mod.state == 'pendingDisable': mod.setState( 'enabled' )
				elif mod.state == 'disabled': mod.setState( 'pendingEnable' )

	def deselectWholeLibrary( self, event ):

		for tab in self.getAllTabs():
			for mod in tab.winfo_children()[0].mods:
				if mod.state == 'pendingEnable': mod.setState( 'disabled' )
				elif mod.state == 'enabled': mod.setState( 'pendingDisable' )

	def saveCodeChanges( self ):

		""" Collects input from the GUI (user's choices on what mods should be enabled/disabled), 
			and calls the appropriate disc methods for code mod installation and saving. If only 
			code un-installations are required, those are performed on the DOL as-is. If code 
			installations (with or without un-installations) are requested, the whole DOL will be 
			restored to vanilla, and then only the requested codes will be installed to it. """

		# Update the GUI
		#clearSummaryTab() # Clears the summary tab's lists of installed mods/SFs.
		#programStatus.set( 'Gathering Preliminary Data...' )

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
		
		# if modsToUninstall:
		# 	globalData.gui.updateProgramStatus( 'Uninstalling {} codes'.format(len(modsToUninstall)) )
		# 	modsNotUninstalled = globalData.disc.uninstallCodeMods( modsToUninstall, vanillaDisc )
		# 	modUninstallCount = modUninstallCount - len( modsNotUninstalled )
		# else:
		# 	modUninstallCount = 0
		
		# Make sure the DOL has been initialized (header parsed and properties determined)
		globalData.disc.dol.load()

		if newModsToInstall:
			globalData.disc.restoreDol()

			globalData.gui.updateProgramStatus( 'Installing {} codes'.format(len(modsToInstall)) )
			modsNotInstalled = globalData.disc.installCodeMods( modsToInstall )
			modInstallCount = len( modsToInstall ) - len( modsNotInstalled )

		elif modsToUninstall:
			globalData.gui.updateProgramStatus( 'Uninstalling {} codes'.format(len(modsToUninstall)) )
			modsNotUninstalled = globalData.disc.uninstallCodeMods( modsToUninstall )
			modUninstallCount = len( modsToUninstall ) - len( modsNotUninstalled )

		else:
			print 'no code changes to be made'

		# if geckoCodesToInstall:
		# 	globalData.updateProgramStatus( 'Installing {} Gecko codes'.format(len(geckoCodesToInstall)) )
		# 	geckoCodesNotInstalled = globalData.disc.installGeckoCodes( geckoCodesToInstall )

		# if modsNotUninstalled or modsNotInstalled or geckoCodesNotInstalled:
		# 	problematicMods = modsNotUninstalled + modsNotInstalled + geckoCodesNotInstalled

		# 	msg( '{} code mods installed. However, these mods could not be installed:\n\n{}'.format(len(), '\n'.join(problematicMods)) )

		# Build a message to be displayed in the program's status bar
		statusMsg = ''
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
		if statusMsg:
			globalData.gui.updateProgramStatus( statusMsg )

		return 0

	def askRestoreDol( self ):

		""" Prompts the user to ensure they know what they're doing, and to confirm the action. """

		if not globalData.disc:
			msg( 'No disc has been loaded!' )
			return
		
		dol = globalData.disc.dol
		
		restoreConfirmed = tkMessageBox.askyesno( 'Restoration Confirmation', 'This will replace the currently loaded DOL to a '
												'vanilla ' + dol.revision + ' DOL (loaded from your chosen vanilla disc). Free '
												'space regions reserved for custom code (under Code-Space Options) will still '
												'be zeroed-out. This process does not preserve a copy of the current DOL, '
												'and any current changes will be lost.\n\nAre you sure you want to do this?' )

		# See if we can get a reference to vanilla DOL code
		vanillaDiscPath = globalData.getVanillaDiscPath()
		if not vanillaDiscPath: # User canceled path input
			printStatus( 'Unable to restore the DOL; no vanilla disc available for reference', warning=True )
			return

		# Restore the DOL and re-scan for installed codes
		globalData.disc.restoreDol( vanillaDiscPath )
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
			print 'No image found for "' + mod.type + 'Indicator' + '"!'

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
			print 'Invalid link detected for "{}": {}'.format( self.mod.name, err )
			return

		# Check the domain against the whitelist. netloc will be something like "youtube.com" or "www.youtube.com"
		if potentialLink.scheme and potentialLink.netloc.split('.')[-2] in ( 'smashboards', 'github', 'youtube' ):
			return potentialLink

		elif not potentialLink.scheme:
			print 'Invalid link detected for "{}" (no scheme): {}'.format( self.mod.name, potentialLink )
		else:
			print 'Invalid link detected for "{}" (domain not allowed): {}'.format( self.mod.name, potentialLink )

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
				print self.mod.name, 'made unavailable;', statusText
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

		print 'not yet implemented'

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
					#print optionName, start, '-', end
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
	