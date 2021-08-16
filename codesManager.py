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
import urlparse
import webbrowser
import tkMessageBox
import Tkinter as Tk
from urlparse import urlparse 	# For validating and security checking URLs

# Internal Dependencies
import globalData
from disc import Disc
from basicFunctions import msg
from codeMods import regionsOverlap, CodeLibraryParser
from guiSubComponents import VerticalScrolledFrame, LabelButton, ToolTip, CodeLibrarySelector, CodeSpaceOptionsWindow, ColoredLabelButton


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
		#self.codeModModules = []
		#self.modNames = set()
		self.isScanning = False
		self.stopToRescan = False

		# Create the control panel
		self.controlPanel = ttk.Frame( self, padding="20 8 20 20" ) # Padding: L, T, R, B

		# Add the button bar
		buttonBar = ttk.Frame( self.controlPanel )
		# Add the Code Library Selection button
		librarySelectionBtn = ColoredLabelButton( buttonBar, 'books', lambda event: CodeLibrarySelector(globalData.gui.root) )
		librarySelectionBtn.pack( side='right', padx=6 )
		self.libraryToolTipText = Tk.StringVar()
		self.libraryToolTipText.set( 'Click to select Code Library.\n\nCurrent library:\n' + globalData.getModsFolderPath() )
		ToolTip( librarySelectionBtn, delay=900, justify='center', location='w', textvariable=self.libraryToolTipText, wraplength=600, offset=-10 )

		# Add the Code Library Selection button
		overwriteOptionsBtn = ColoredLabelButton( buttonBar, 'gear', lambda event: CodeSpaceOptionsWindow(globalData.gui.root) )
		overwriteOptionsBtn.pack( side='right', padx=6 )
		overwriteOptionsTooltip = 'Edit Code-Space Options'
		ToolTip( overwriteOptionsBtn, delay=900, justify='center', location='w', text=overwriteOptionsTooltip, wraplength=600, offset=-10 )
		buttonBar.pack( fill='x', pady=(5, 10) )

		# Begin adding primary buttons
		ttk.Button( self.controlPanel, text='Open this File', command=self.openLibraryFile ).pack( pady=4, padx=6, ipadx=8 )
		ttk.Button( self.controlPanel, text='Open Mods Library Folder', command=self.openModsLibrary ).pack( pady=4, padx=6, ipadx=8 )

		ttk.Separator( self.controlPanel, orient='horizontal' ).pack( pady=7, ipadx=120 )

		# saveButtonsContainer = ttk.Frame( self.controlPanel, padding="0 0 0 0" )
		# saveChangesBtn = ttk.Button( saveButtonsContainer, text='Save', command=saveCodeChanges, state='disabled', width=12 )
		# saveChangesBtn.pack( side='left', padx=6 )
		# saveChangesAsBtn = ttk.Button( saveButtonsContainer, text='Save As...', command=saveAs, state='disabled', width=12 )
		# saveChangesAsBtn.pack( side='left', padx=6 )
		# saveButtonsContainer.pack( pady=4 )

		createFileContainer = ttk.Frame( self.controlPanel, padding="0 0 0 0" )
		ttk.Button( createFileContainer, text='Create INI', command=self.saveIniFile ).pack( side='left', padx=6 )
		ttk.Button( createFileContainer, text='Create GCT', command=self.saveGctFile ).pack( side='left', padx=6 )
		createFileContainer.pack( pady=4 )

		ttk.Separator( self.controlPanel, orient='horizontal' ).pack( pady=7, ipadx=140 )

		restoreDolBtn = ttk.Button( self.controlPanel, text='Restore Original DOL', state='disabled', command=globalData.disc.restoreDol, width=23 )
		restoreDolBtn.pack( pady=4 )
		# importFileBtn = ttk.Button( self.controlPanel, text='Import into ISO', state='disabled', command=importIntoISO, width=23 )
		# importFileBtn.pack( pady=4 )
		exportFileBtn = ttk.Button( self.controlPanel, text='Export DOL', state='disabled', command=self.exportDOL, width=23 )
		exportFileBtn.pack( pady=4 )

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

		# showRegionOptionsBtn = ttk.Button( self.controlPanel, text=' Code-Space Options ', state='disabled', command=ShowOptionsWindow )
		# showRegionOptionsBtn.pack( side='bottom' )

		# Add a label that shows how many code modes are selected on the current tab
		self.installTotalLabel = Tk.StringVar()
		self.installTotalLabel.set( '' )
		ttk.Label( self.controlPanel, textvariable=self.installTotalLabel ).pack( side='bottom', pady=(0, 12) )

		self.bind( '<Configure>', self.alignControlPanel )

	def onTabChange( self, event=None ):
		
		# Check if the Code Manager tab is selected, and thus if any updates are really needed
		if globalData.gui.root.nametowidget( globalData.gui.mainTabFrame.select() ) != self:
			return

		self.emptyModsPanels( self.codeLibraryNotebook )
		self.createModModules()
		self.alignControlPanel()
		self.updateInstalledModsTabLabel()

	def emptyModsPanels( self, notebook ):

		root = globalData.gui.root
		
		for tabName in notebook.tabs():
			tabWidget = root.nametowidget( tabName )

			if tabWidget.winfo_class() == 'TFrame':
				modsPanel = tabWidget.winfo_children()[0]
				for childWidget in modsPanel.interior.winfo_children(): # Avoiding .clear method to avoid resetting scroll position
					childWidget.destroy()
			else:
				self.emptyModsPanels( tabWidget )

	def createModModules( self ):

		currentTab = self.getCurrentLibraryTab()
		if not currentTab: return

		modsPanel = currentTab.winfo_children()[0]

		for mod in modsPanel.mods:
			newModule = ModModule( modsPanel.interior, mod )
			newModule.pack( fill='x', expand=1 )

	def alignControlPanel( self, event=None ):

		""" Updates the alignment/position of the control panel (to the right of mod lists) and the global scroll target. 
			Using this alignment technique rather than just dividing the Code Manager tab into two columns allows the 
			library tabs to span the entire width of the program, rather than just the left side. """

		# Check if the Code Manager tab is selected (and thus if the control panel should be visible)
		if globalData.gui.root.nametowidget( globalData.gui.mainTabFrame.select() ) != self:
			self.controlPanel.place_forget() # Removes the control panel from GUI, without deleting it
			return

		# Get the VerticalScrolledFrame of the currently selected tab.
		currentTab = self.getCurrentLibraryTab()

		if currentTab:
			modsPanel = currentTab.winfo_children()[0]

			# Get the new coordinates for the control panel frame.
			globalData.gui.root.update_idletasks() # Force the GUI to update in order to get correct new widget positions & sizes.
			currentTabWidth = currentTab.winfo_width()

			self.controlPanel.place( in_=currentTab, x=currentTabWidth * .60, width=currentTabWidth * .40, height=modsPanel.winfo_height() )
		else:
			notebookWidth = self.codeLibraryNotebook.winfo_width()
			self.controlPanel.place( in_=self.codeLibraryNotebook, x=notebookWidth * .60, width=notebookWidth * .40, height=self.codeLibraryNotebook.winfo_height() )
			
	def updateInstalledModsTabLabel( self ):

		""" Updates the installed mods count at the bottom of the control panel. """

		currentTab = self.getCurrentLibraryTab()

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

		# Remove the Mods Library selection button from the GUI
		#librarySelectionLabel.place_forget()

		# Delete all mods currently populated in the GUI (by deleting the associated tab),
		# and remove any other current widgets/labels in the main notebook
		for child in self.codeLibraryNotebook.winfo_children():
			child.destroy()

		# Remove any description text ('Click this button to....')
		# for child in modsLibraryTab.mainRow.winfo_children():
		# 	if child.winfo_class() == 'TLabel' and child != librarySelectionLabel:
		# 		child.destroy()

		self.installTotalLabel.set( '' )
		
	def getCurrentLibraryTab( self ):
		
		""" Returns the currently selected tab in the Mods Library tab, or None if one is not selected. 
			The returned widget is the upper-most ttk.Frame in the tab (exists for placement purposes), 
			not the VerticalScrolledFrame. To get that, use .winfo_children()[0] on the returned frame. """

		if self.codeLibraryNotebook.tabs() == ():
			return None

		root = globalData.gui.root
		selectedTab = root.nametowidget( self.codeLibraryNotebook.select() ) # Will be the highest level tab (either a notebook or VerticalScrolledFrame)

		# If the child widget is not a frame, it's a notebook, meaning this represents a directory, and contains more files/tabs within it.
		while selectedTab.winfo_class() != 'TFrame':

			if selectedTab.tabs() == (): return None
			selectedTab = root.nametowidget( selectedTab.select() )
			
		return selectedTab

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

		tic = time.clock()

		# Remember the currently selected tab and its scroll position.
		# currentTab = self.getCurrentLibraryTab()
		# lastSelectedTabFileSource = ''
		# if currentTab:
		# 	frameForBorder = currentTab.winfo_children()[0]
		# 	modsPanelInterior = frameForBorder.winfo_children()[0].interior # frameForBorder -> modsPanel.interior
		# 	lastSelectedTabFileSource = modsPanelInterior.winfo_children()[0].sourceFile # Checking the first mod of the mods panel (should all have same source file)
		# 	sliderYPos = frameForBorder.winfo_children()[0].vscrollbar.get()[0] # .get() returns e.g. (0.49505277044854884, 0.6767810026385225)

		self.libraryFolder = globalData.getModsFolderPath()

		# Validate the current Mods Library folder
		if not os.path.exists( self.libraryFolder ):
			warningMsg = 'Unable to find this code library:\n\n' + self.libraryFolder
			ttk.Label( self.codeLibraryNotebook, text=warningMsg, background='white', wraplength=600, justify='center' ).place( relx=0.3, rely=0.5, anchor='center' )
			ttk.Label( self.codeLibraryNotebook, image=globalData.gui.imageBank('randall'), background='white' ).place( relx=0.3, rely=0.5, anchor='s', y=-20 ) # y not :P
			return

		self.clear()

		self.isScanning = True
		
		# Always parse the Core Code library
		# coreCodesLibraryPath = globalData.paths['coreCodes']
		# self.parser.includePaths = [ os.path.join(coreCodesLibraryPath, '.include'), os.path.join(globalData.scriptHomeFolder, '.include') ]
		# self.parser.processDirectory( coreCodesLibraryPath )

		# Parse the currently selected "main" library
		#if self.libraryFolder != coreCodesLibraryPath:
		self.parser.includePaths = [ os.path.join(self.libraryFolder, '.include'), os.path.join(globalData.scriptHomeFolder, '.include') ]
		self.parser.processDirectory( self.libraryFolder )
		globalData.codeMods = self.parser.codeMods

		self.populateModLibraryTabs()

		# Check once more if another scan is queued. (e.g. if the scan mods button was pressed again while checking for installed mods)
		if self.stopToRescan:
			self.restartScan( playAudio )
		else:
			toc = time.clock()
			print 'library parsing time:', toc - tic

			#totalModsInLibraryLabel.set( 'Total Mods in Library: ' + str(len( self.codeModModules )) ) # todo: refactor code to count mods in the modsPanels instead
			#totalSFsInLibraryLabel.set( 'Total Standalone Functions in Library: ' + str(len( collectAllStandaloneFunctions(self.codeModModules, forAllRevisions=True) )) )

			# realignControlPanel()
			# root.bind_class( 'moduleClickTag', '<1>', modModuleClicked )

			# if dol.data:
			# 	collectAllStandaloneFunctions()
			# 	checkForEnabledCodes()

			self.isScanning = False
			self.stopToRescan = False
			
			if playAudio:
				#playSound( 'menuChange' )
				print 'beep!'

	def restartScan( self, playAudio ):
		time.sleep( .2 ) # Give a moment to allow for current settings to be saved via saveOptions.
		self.isScanning = False
		self.stopToRescan = False
		self.parser.stopToRescan = False
		self.scanCodeLibrary( playAudio )

	def populateModLibraryTabs( self ):

		""" Populates the Code Manager library tabs in the GUI, and checks for installed mods. 
			Creates all needed notebooks and vertical scroll frames, and populates them with code mod modules. """

		notebookWidgets = { '': self.codeLibraryNotebook }
		modsPanels = {}

		# If no mods are present, add a simple message and return
		if not globalData.codeMods:
			ttk.Label( self.codeLibraryNotebook, image=globalData.gui.imageBank('randall'), background='white' ).place( relx=0.3, rely=0.5, anchor='s', y=-20 ) # y not :P
			warningMsg = 'Unable to find code mods in this library:\n\n' + self.libraryFolder
			ttk.Label( self.codeLibraryNotebook, text=warningMsg, background='white', wraplength=600, justify='center' ).place( relx=0.3, rely=0.5, anchor='center' )
			return

		# If a disc is loaded, check if the parsed mods are installed in it
		if globalData.disc:
			#dol = globalData.disc.files[globalData.disc.gameId + '/Start.dol']
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
						#print 'added notebook,', str(notebook) + ', for', pathItem

					parent = notebook

					# Add a vertical scrolled frame to the last notebook
					if i == len( pathParts ) - 1: # Reached the last part (the category)
						placementFrame = ttk.Frame( parent ) # This will be the "currentTab" widget returned from .getCurrentLibraryTab()
						parent.add( placementFrame, text=mod.category )
						modsPanel = VerticalScrolledFrame( placementFrame )
						modsPanel.mods = []
						#print 'adding VSF', modsPanel._name, 'to', placementFrame._name, 'for', thisTabPath + '\\' + mod.category
						modsPanel.place( x=0, y=0, relwidth=.60, relheight=1.0 )
						modsPanels[relPath + '\\' + mod.category] = modsPanel
						#print 'added frame,', mo

			# newModule = ModModule( modsPanel.interior, mod )
			# newModule.pack( fill='x', expand=1 )

			# Store the mod for later; actual modules for the GUI will be created on tab selection
			modsPanel.mods.append( mod )

			# Disable mods with problems
			if mod.assemblyError or mod.parsingError:
				mod.setState( 'unavailable' )

			# if mod.state == 'enabled':
			# 	print mod.name

		# Add messages to the background of any empty notebooks
		for notebook in notebookWidgets.values():
			if not notebook.winfo_children():
				ttk.Label( notebook, image=globalData.gui.imageBank('randall'), background='white' ).place( relx=0.3, rely=0.5, anchor='s', y=-20 ) # y not :P
				warningMsg = 'No code mods found in this folder or cetegory.'
				ttk.Label( notebook, text=warningMsg, background='white', wraplength=600, justify='center' ).place( relx=0.3, rely=0.5, anchor='center' )

	def openLibraryFile( self ): pass
	def openModsLibrary( self ): pass
	def exportDOL( self ): pass

	def saveIniFile( self ): pass
	def saveGctFile( self ): pass

	def selectAllMods( self ): pass
	def deselectAllMods( self ): pass
	def selectWholeLibrary( self ): pass
	def deselectWholeLibrary( self ): pass

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

		# Scan the library for mods to be installed or uninstalled
		for mod in globalData.codeMods:
			#if mod.state == 'unavailable': continue

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

		if modsToInstall:
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


class ModModule( Tk.Frame ):

	""" GUI element and wrapper for CodeMod objects, and host to various GUI-related features. """

	#def __init__( self, parent, modName, modDesc, modAuth, modData, modType, webLinks, *args, **kw ):
	def __init__( self, parent, mod, *args, **kw ):
		Tk.Frame.__init__( self, parent, relief='groove', borderwidth=3, takefocus=True, *args, **kw )

		self.mod = mod
		self.mod.guiModule = self
		self.valWebLinks = [] # These differentiate from the core mod's webLinks, in that these will be validated
		self.statusText = Tk.StringVar()
		self.highlightFadeAnimationId = None # Used for the border highlight fade animation

		moduleWidth = 520 			# Mostly just controls the wraplength of text areas.

		# Set the mod "Length" string
		# if self.type == 'static':
		# 	lengthString = ''
		# else:
		# 	arbitraryGameVersions = []
		# 	for revision, codeChanges in modData.items():
		# 		if revision != 'ALL':
		# 			arbitraryGameVersions.extend( codeChanges )
		# 			break
		# 	if 'ALL' in modData: arbitraryGameVersions.extend( modData['ALL'] )

		# 	length = 0
		# 	for codeChange in arbitraryGameVersions:
		# 		if codeChange[0] != 'static': length += codeChange[1]
		# 	lengthString = '                 Space' + unichr(160) + 'required:' + unichr(160) + uHex(length) # unichr(160) = no-break space

		# Construct the GUI framework.
		#self.config( relief='groove', borderwidth=3, takefocus=True )

		# Row 1: Title, author(s), type, and codelength.
		row1 = Tk.Frame( self )
		Tk.Label( row1, text=mod.name, font=("Times", 11, "bold"), wraplength=moduleWidth-140, anchor='n' ).pack( side='top', padx=(0,36), pady=2 ) # Right-side horizontal padding added for module type image
		#Label( row1, text=' - by ' + modAuth + lengthString, font=("Verdana", 8), wraplength=moduleWidth-160 ).pack( side='top', padx=(0,36) ) #Helvetica
		Tk.Label( row1, text=' - by ' + mod.auth, font=("Verdana", 8), wraplength=moduleWidth-160 ).pack( side='top', padx=(0,36) ) #Helvetica
		row1.pack( side='top', fill='x', expand=1 )

		# Row 2: Description.
		# row2 = Tk.Frame( self )
		# Tk.Label( row2, text=mod.desc, wraplength=moduleWidth-110, padx=8, justify='left' ).pack( side='left', pady=0 )
		# row2.pack( side='top', fill='x', expand=1 )
		Tk.Label( self, text=mod.desc, wraplength=moduleWidth-40, justify='left' ).pack( side='top', fill='x', expand=1, padx=(8, 54) )

		# Row 3: Status text and buttons
		row3 = Tk.Frame( self )

		Tk.Label( row3, textvariable=self.statusText, wraplength=moduleWidth-90, justify='left' ).pack( side='left', padx=35 )

		# Set a background image based on the mod type (indicator on the right-hand side of the mod)
		#typeIndicatorImage = imageBank.get( self.type + 'Indicator' )
		typeIndicatorImage = globalData.gui.imageBank( mod.type + 'Indicator' )
		if typeIndicatorImage:
			bgImage = Tk.Label( self, image=typeIndicatorImage )
			bgImage.place( relx=1, x=-10, rely=0.5, anchor='e' )
		else:
			print 'No image found for "' + mod.type + 'Indicator' + '"!'

		# Set up a left-click event to all current parts of this module (to toggle the code on/off), before adding any of the other clickable elements
		for each in self.winfo_children():
			#frame.bindtags( ('moduleClickTag',) + frame.bindtags() )
			each.bind( '<1>', self.clicked )
			for each in each.winfo_children():
				#label.bindtags( ('moduleClickTag',) + label.bindtags() )
				each.bind( '<1>', self.clicked )

		# Add the edit button
		LabelButton( row3, 'editButton', self.inspectMod, 'Edit or configure this mod' ).pack( side='right', padx=(5, 55), pady=6 )

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

	def setState( self, state, specialStatusText='' ):

		""" Sets the state of the selected module, by adding a label to the module's Row 3 and 
			changing the background color of all associated widgets. """

		stateColor = 'SystemButtonFace' # The default (disabled) colors.
		textColor = '#000'

		if state == 'pendingEnable':
			stateColor = '#aaffaa'
			self.statusText.set( 'Pending Save' )

		elif state == 'pendingDisable':
			stateColor = '#ee9999'
			self.statusText.set( 'Pending Removal' )

		elif state == 'enabled':
			stateColor = '#77cc77'
			self.statusText.set( '' )

		elif state == 'unavailable':
			stateColor = '#cccccc'
			textColor = '#707070'
			#if self.mod.type == 'gecko':
				#if not gecko.environmentSupported:
				# if not 0:
				# 	self.statusText.set( '(Gecko codes are unavailable)' )
				# elif 'EnableGeckoCodes' in overwriteOptions and not overwriteOptions[ 'EnableGeckoCodes' ].get():
				# 	self.statusText.set( '(Gecko codes are disabled)' )
				# else:
				#self.statusText.set( '' )
			if not self.mod.data:
				self.statusText.set( 'No code change data found!' )
			else:
				self.statusText.set( '(Unavailable for your DOL revision)' )

		elif state != 'disabled':
			self.statusText.set( '' )
			raise Exception( 'Invalid mod state given! "' + state + '"' )

		if specialStatusText:
			if state == 'unavailable':
				print self.mod.name, 'made unavailable;', specialStatusText
			self.statusText.set( specialStatusText )

		# Change the overall background color of the module (adjusting the background color of all associated frames and labels)
		self['bg'] = stateColor
		for i, frame in enumerate( self.winfo_children() ):
			frame['bg'] = stateColor
			for j, label in enumerate( frame.winfo_children() ):
				label['bg'] = stateColor
				if not (i == 2 and j == 0): # This will exclude the status label.
					label['fg'] = textColor

		self.mod.state = state
	
	def clicked( self, event ):

		""" Handles click events on mod modules, and toggles their install state 
			(i.e. whether or not it should be installed when the user hits save). """

		# Get the widget of the main frame for the module (i.e. the modModule frame, "self")
		# modState = None
		# mod = event.widget
		# failsafe = 0
		# while not modState:
		# 	mod = mod.master # Move upward through the GUI heirarchy until the mod module is found
		# 	modState = getattr( mod, 'state', None )
		# 	assert failsafe < 3, 'Unable to process click event on modModule; no mod module found.'
		# 	failsafe += 1

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