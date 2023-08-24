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

# External dependencies
import ttk
import math
import time
import enum
import tkMessageBox
import Tkinter as Tk
from PIL import Image, ImageTk
from Tkinter import TclError
from binascii import hexlify
from collections import OrderedDict

# Internal dependencies
import globalData
from tplCodec import TplDecoder
from FileSystem import hsdStructures, DatFile, CharCostumeFile, StageFile
from RenderEngine2 import RenderEngine
from basicFunctions import isNaN, validHex, humansize, grammarfyList, msg, copyToClipboard, printStatus, uHex, constructTextureFilename
from guiSubComponents import ( ColoredLabelButton, Dropdown, LabelButton, exportMultipleTextures, getColoredShape, importSingleTexture, 
		BasicWindow, HexEditEntry, EnumOptionMenu, HexEditDropdown, ColorSwatch, 
		MeleeColorPicker, FlagDecoder, ToolTip, VerticalScrolledFrame, ClickText )


imageFormats = { 0:'I4', 1:'I8', 2:'IA4', 3:'IA8', 4:'RGB565', 5:'RGB5A3', 6:'RGBA8', 8:'CI4', 9:'CI8', 10:'CI14x2', 14:'CMPR' }
userFriendlyFormatList = [	'_0 (I4)', '_1 (I8)', 
							'_2 (IA4)', '_3 (IA8)', 
							'_4 (RGB565)', '_5 (RGB5A3)', '_6 (RGBA8)', 
							'_8 (CI4)', '_9 (CI8)', '_10 (CI14x2)', 
							'_14 (CMPR)' ]

class DisplayMode( enum.IntEnum ):
	SelectedOnly = 0
	Related = 1
	All = 2

class TexturesEditor( ttk.Notebook ):

	def __init__( self, parent, mainGui ):
		ttk.Notebook.__init__( self, parent )

		# Add this tab to the main GUI, and add drag-and-drop functionality
		mainGui.mainTabFrame.add( self, text=' Textures Editor ' )
		mainGui.dnd.bindtarget( self, mainGui.dndHandler, 'text/uri-list' )

		# Save some processing by initializing and manipulating these images just once (used for buttons)
		downArrowImage = getColoredShape( 'arrowDown', '#7077ac', getAsPilImage=True )
		downArrowImageHovered = getColoredShape( 'arrowDown', '#8089ff', getAsPilImage=True )
		self.leftArrow = ImageTk.PhotoImage( downArrowImage.rotate(-90) )
		self.leftArrowHovered = ImageTk.PhotoImage( downArrowImageHovered.rotate(-90) )
		self.rightArrow = ImageTk.PhotoImage( downArrowImage.rotate(90) )
		self.rightArrowHovered = ImageTk.PhotoImage( downArrowImageHovered.rotate(90) )

	def addTab( self, fileObj ):

		""" Adds a new tab for the given file to the Textures Editor interface, 
			or switches to an existing tab if that file is already open. """

		# Check if a tab has already been created/added for this file
		for windowName in self.tabs():
			tab = globalData.gui.root.nametowidget( windowName )

			if tab.file == fileObj: # Found it!
				self.select( tab )
				break

		else: # Loop above didn't break; mod not found
			# Create the new tab for the given file
			newTab = TexturesEditorTab( self, fileObj )
			self.add( newTab, text=fileObj.filename )

			# Switch to and populate the new tab
			self.select( newTab )
			newTab.populateTexEditorTab()

	def haltAllScans( self, programClosing=False ):

		""" Used to gracefully stop all ongoing file scans. Without a method like this, 
			if the program's GUI (mainloop) is closed/destroyed, there may be errors from 
			the scan loops acting on a GUI that no longer exists. """

		# Instruct all tabs to stop current scans
		# tabWidgets = []
		for tabName in self.tabs():
			tabWidget = globalData.gui.root.nametowidget( tabName )
			tabWidget.haltScan = True
			# tabWidgets.append( tabWidget )

		# Wait until all tabs have stopped scanning (waits for GUI event loop to iterate and cancel all scan loops)
		# while 1:
		# 	for tab in tabWidgets:
		# 		if tab.scanningFile:
		# 			break
		# 	else: # The loop above didn't break; no tabs are currently scanning
		# 		break # From the while loop

		# # Reset the haltScan flag if the progrom isn't closing
		# if not programClosing:
		# 	for tab in tabWidgets:
		# 		tab.haltScan = False

	def closeCurrentTab( self ):

		""" Removes the currently selected tab. If all tabs are removed, 
			the entire notebook (within main tab interface) should be removed. """

		mainGui = globalData.gui
		currentTab = mainGui.root.nametowidget( self.select() )

		# Close any windows the tab might have open
		if currentTab.renderOptionsWindowIsOpen():
			currentTab.renderOptionsWindow.close()
		try: currentTab.filtersWindow.close()
		except: pass

		# Close the tab itself
		currentTab.destroy()

		# Remove this entire interface (notebook) from the GUI if there are no more tabs
		if not self.tabs():
			# Remove this notebook tab from the main tab interface
			self.destroy()
			mainGui.texturesTab = None

			# Go back to the last-used tab
			mainGui.mainTabFrame.select( mainGui.lastSelectedTab )


class TexturesEditorTab( ttk.Frame ):

	def __init__( self, parent, fileObj=None ):
		ttk.Frame.__init__( self, parent )

		self.tabManager = parent
		self.file = fileObj
		self.texturesInfo = []
		self.scanningFile = False
		self.restartFileScan = False
		self.haltScan = False
		self.imageFilters = {
			'widthFilter': ( '=', '' ),
			'heightFilter': ( '=', '' ),
			'aspectRatioFilter': ( '=', '' ),
			'imageTypeFilter': ( '=', '' ),
			'offsetFilter': ( '=', '' ),
		}
		self.filtersWindow = None
		
		# Top header row | Filepath field and close button
		topRow = ttk.Frame( self, padding="12 12 12 0" ) # Left, Top, Right, Bottom

		ttk.Label( topRow, text=" DAT / USD:" ).pack( side='left' )
		self.datDestination = Tk.StringVar()
		datDestinationLabel = ttk.Entry( topRow, textvariable=self.datDestination )
		datDestinationLabel.bind( '<Return>', self.openNewFile )
		datDestinationLabel.pack( side='left', fill='x', expand=1, padx=12 )

		closeBtn = ttk.Button( topRow, text='X', command=parent.closeCurrentTab, width=4 )
		closeBtn.pack( side='right' )
		ToolTip( closeBtn, text='Close', delay=1000, bg='#ee9999', location='n' )

		topRow.pack( fill='x', side='top' )
		
		# Second row | Frame for the image tree and info pane
		secondRow = ttk.Frame( self, padding="12 12 12 0" ) # Contains the tree and the info pane. Padding order: Left, Top, Right, Bottom.

		# File Tree start
		datTreeScroller = Tk.Scrollbar( secondRow )
		self.datTextureTree = ttk.Treeview( secondRow, columns=('texture', 'dimensions', 'type'), yscrollcommand=datTreeScroller.set )
		self.datTextureTree.heading( '#0', anchor='center', text='Preview' )
		self.datTextureTree.column( '#0', anchor='center', minwidth=104, stretch=0, width=104 ) # "#0" is implicit in columns definition above.
		self.datTextureTree.heading( 'texture', anchor='center', text='Offset  (len)', command=lambda: self.treeview_sort_column('texture', False) )
		self.datTextureTree.column( 'texture', anchor='center', minwidth=80, stretch=0, width=100 )
		self.datTextureTree.heading( 'dimensions', anchor='center', text='Dimensions', command=lambda: self.treeview_sort_column('dimensions', False) )
		self.datTextureTree.column( 'dimensions', anchor='center', minwidth=80, stretch=0, width=100 )
		self.datTextureTree.heading( 'type', anchor='center', text='Texture Type', command=lambda: self.treeview_sort_column('type', False) )
		self.datTextureTree.column( 'type', anchor='center', minwidth=75, stretch=0, width=100 )
		self.datTextureTree.pack( fill='both', side='left' )
		datTreeScroller.config( command=self.datTextureTree.yview )
		datTreeScroller.pack( side='left', fill='y' )
		self.datTextureTree.lastLoaded = None # Used by the 'Prev./Next' file loading buttons on the DAT Texture Tree tab
		self.datTextureTree.bind( '<<TreeviewSelect>>', self.onTextureTreeSelect )
		self.datTextureTree.bind( "<3>", self.summonContextMenu )

		# Create repositories to store image data (needed to prevent garbage collection)
		self.datTextureTree.fullTextureRenders = {}
		self.datTextureTree.textureThumbnails = {}

		# Background widgets for treeview when not populated
		# self.datTextureTreeBg = Tk.Label( self.datTextureTree, image=globalData.gui.imageBank('dndTarget'), borderwidth=0, highlightthickness=0 )
		# self.datTextureTreeBg.place( relx=0.5, rely=0.5, anchor='center' )
		self.datTextureTreeStatusMsg = Tk.StringVar()
		self.datTextureTreeStatusLabel = ttk.Label( self.datTextureTree, textvariable=self.datTextureTreeStatusMsg, background='white' )

		# Item highlighting. The order of the configs below reflects (but does not dictate) the priority of their application
		self.datTextureTree.tag_configure( 'warn', background='#f6c6d7' ) # light red
		self.datTextureTree.tag_configure( 'mipmap', background='#d7e1ff' ) # light blue; same as SA tab 'marked' items

		# File Tree end; beginning texture display pane
		defaultCanvasDimensions = 258 # Default size for the height and width of the texture viewing canvas. 256 + 1px border

		self.imageManipTabs = ttk.Notebook( secondRow )

		self.textureTreeImagePane = Tk.Frame( self.imageManipTabs )
		self.imageManipTabs.add( self.textureTreeImagePane, text=' Image ', sticky='nsew' )

		canvasOptionsPane = ttk.Frame( self.textureTreeImagePane, padding='0 15 0 0' )
		ClickText( canvasOptionsPane, 'Texture Filters', self.adjustTextureFilters ).pack( side='left', padx=7 )
		ttk.Checkbutton( canvasOptionsPane, command=self.updateCanvasGrid, text='Show Grid', variable=globalData.boolSettings['showCanvasGrid'] ).pack( side='left', padx=7 )
		ttk.Checkbutton( canvasOptionsPane, command=self.updateCanvasTextureBoundary, text='Show Texture Boundary', variable=globalData.boolSettings['showTextureBoundary'] ).pack( side='left', padx=7 )
		canvasOptionsPane.pack()

		self.textureDisplayFrame = Tk.Frame( self.textureTreeImagePane ) # The border and highlightthickness for the canvas below must be set to 0, so that the canvas has a proper origin of (0, 0).
		self.textureDisplay = Tk.Canvas( self.textureDisplayFrame, width=defaultCanvasDimensions, height=defaultCanvasDimensions, borderwidth=0, highlightthickness=0 )
		self.textureDisplay.pack( expand=1 ) # fill='both', padx=10, pady=10
		self.updateCanvasGrid( False )

		self.textureDisplay.defaultDimensions = defaultCanvasDimensions
		self.textureDisplayFrame.pack( expand=1 )

		datPreviewPaneBottomRow = Tk.Frame( self.textureTreeImagePane ) # This object uses grid alignment for its children so that they're centered and equally spaced amongst each other.

		self.previousDatButton = ttk.Label( datPreviewPaneBottomRow, image=globalData.gui.imageBank('previousDatButton') )
		self.previousDatButton.grid( column=0, row=0, sticky='e', ipadx=10, pady=(10, 0) )
		self.previousDatText = Tk.StringVar()
		ToolTip( self.previousDatButton, textvariable=self.previousDatText, delay=300, location='n' )

		datFileDetails = ttk.Labelframe( datPreviewPaneBottomRow, text='   File Details   ', labelanchor='n' )
		self.datFilesizeText = Tk.StringVar( value='File Size:  ' )
		ttk.Label( datFileDetails, textvariable=self.datFilesizeText )
		self.totalTextureSpaceText = Tk.StringVar( value='Total Texture Size:  ' )
		ttk.Label( datFileDetails, textvariable=self.totalTextureSpaceText )
		self.texturesFoundText = Tk.StringVar( value='Textures Found:  ' )
		ttk.Label( datFileDetails, textvariable=self.texturesFoundText )
		self.texturesFilteredText = Tk.StringVar( value='Filtered Out:  ' )
		ttk.Label( datFileDetails, textvariable=self.texturesFilteredText )
		for widget in datFileDetails.winfo_children():
			widget.pack( padx=20, pady=0, anchor='w' )
		datFileDetails.grid( column=1, row=0, ipady=4, sticky='ew', padx=(10, 34) )

		self.nextDatButton = ttk.Label( datPreviewPaneBottomRow, image=globalData.gui.imageBank('nextDatButton') )
		self.nextDatButton.grid( column=2, row=0, sticky='w', ipadx=10, pady=(10, 0) )
		self.nextDatText = Tk.StringVar()
		ToolTip( self.nextDatButton, textvariable=self.nextDatText, delay=300, location='n' )

		datPreviewPaneBottomRow.columnconfigure( 0, weight=1 )
		datPreviewPaneBottomRow.columnconfigure( 1, weight=2 )
		datPreviewPaneBottomRow.columnconfigure( 2, weight=1 )
		datPreviewPaneBottomRow.rowconfigure( 0, weight=1 )

		datPreviewPaneBottomRow.pack( side='bottom', fill='x', padx=20, pady=7 )

		# Palette tab
		self.palettePane = ttk.Frame( self.imageManipTabs, padding='16 0 0 0' )
		self.imageManipTabs.add( self.palettePane, text=' Palette ', state='disabled' )

		# Left-side column (canvas and bg color changer button)
		paletteTabLeftSide = Tk.Frame(self.palettePane)
		self.paletteCanvas = Tk.Canvas( paletteTabLeftSide, borderwidth=3, relief='ridge', background='white', width=187, height=405 )
		paletteBgColorChanger = ttk.Label( paletteTabLeftSide, text='Change Background Color', foreground='#00F', cursor='hand2' )
		self.paletteCanvas.paletteEntries = []
		self.paletteCanvas.itemColors = {}
		paletteBgColorChanger.bind( '<1>', self.cyclePaletteCanvasColor )
		self.paletteCanvas.pack( pady=11, padx=0 )
		self.paletteCanvas.entryBorderColor = '#3399ff' # This is the same blue as used for treeview selection highlighting
		paletteBgColorChanger.pack()
		paletteTabLeftSide.grid( column=0, row=0 )

		# Right-side column (palette info)
		paletteDetailsFrame = Tk.Frame(self.palettePane)
		self.paletteDataText = Tk.StringVar( value='Data Offset:' )
		ttk.Label( paletteDetailsFrame, textvariable=self.paletteDataText ).pack(pady=3)
		self.paletteHeaderText = Tk.StringVar( value='Header Offset:' )
		ttk.Label( paletteDetailsFrame, textvariable=self.paletteHeaderText ).pack(pady=3)
		self.paletteTypeText = Tk.StringVar( value='Palette Type:' )
		ttk.Label( paletteDetailsFrame, textvariable=self.paletteTypeText ).pack(pady=3)
		self.paletteMaxColorsText = Tk.StringVar( value='Max Colors:')
		ttk.Label( paletteDetailsFrame, textvariable=self.paletteMaxColorsText ).pack(pady=3)
		self.paletteStatedColorsText = Tk.StringVar( value='Stated Colors:' )
		ttk.Label( paletteDetailsFrame, textvariable=self.paletteStatedColorsText ).pack(pady=3)
		#self.paletteActualColorsText = Tk.StringVar( value='Actual Colors:' ) # todo:reinstate?
		#ttk.Label( paletteDetailsFrame, textvariable=self.paletteActualColorsText ).pack(pady=3)
		paletteDetailsFrame.grid( column=1, row=0, pady=60, sticky='n' )

		self.palettePane.columnconfigure( 0, weight=1 )
		self.palettePane.columnconfigure( 1, weight=2 )
		
		# Add a help button to explain the above
		helpText = ( 'Max Colors is the maximum number of colors this texture has space for with its current texture format.\n\n'
					 'Stated Colors is the number of colors that the palette claims are actually used by the texture (described by the palette data header).\n\n'
					 'The number of colors actually used may still differ from both of these numbers, especially for very old texture hacks.' )
		helpBtn = ttk.Label( self.palettePane, text='?', foreground='#445', cursor='hand2' )
		helpBtn.place( relx=1, x=-17, y=18 )
		helpBtn.bind( '<1>', lambda e, message=helpText: msg(message, 'Palette Properties') )

		# Model parts tab
		self.modelPropertiesPane = VerticalScrolledFrame( self.imageManipTabs )
		self.imageManipTabs.add( self.modelPropertiesPane, text='Model', state='disabled' )
		modelPane = self.modelPropertiesPane.interior
		modelPane.imageDataHeaders = []
		modelPane.nonImageDataHeaders = [] # Not expected
		modelPane.textureStructs = [] # Direct model attachments
		modelPane.headerArrayStructs = [] # Used for animations
		modelPane.unexpectedStructs = []
		#modelPane.materialStructs = [] # no longer needed?
		modelPane.displayObjects = [] # DObjs that the currently selected texture is used on
		modelPane.selectableObjects = [] # DObjs to be shown/selectable in the options window
		modelPane.currentRenders = [] # DObjs that are currently rendered

		# Widgets for model part modifications (hidden state/transparency/colors)
		modelPane.hideJointChkBtn = None
		modelPane.polyDisableChkBtn = None
		modelPane.opacityEntry = None
		modelPane.opacityBtn = None
		modelPane.opacityScale = None
		modelPane.diffusionEntry = None
		modelPane.ambienceEntry = None
		modelPane.highlightsEntry = None
		modelPane.shininessEntry = None

		modelPane.engine = None
		modelPane.renderOptionsBtn = None
		modelPane.partIndex = -1
		modelPane.dobjStringVar = Tk.StringVar()
		# modelPane.showRelatedParts = Tk.BooleanVar( value=True )
		# modelPane.showAllParts = Tk.BooleanVar( value=False )
		modelPane.displayMode = DisplayMode.Related
		modelPane.obscureNonSelected = Tk.BooleanVar( value=True )
		modelPane.autoCameraUpdates = Tk.BooleanVar( value=True )
		modelPane.showBones = Tk.BooleanVar( value=False )
		modelPane.showHighPoly = Tk.BooleanVar( value=True )
		modelPane.highPolyIds = []
		modelPane.lowPolyIds = []
		self.renderOptionsWindow = None

		# Texture properties tab
		self.texturePropertiesPane = VerticalScrolledFrame( self.imageManipTabs )
		self.texturePropertiesPane.flagWidgets = [] # Useful for the Flag Decoder to more easily find widgets that need updating
		self.imageManipTabs.add( self.texturePropertiesPane, text='Properties', state='disabled' )

		self.imageManipTabs.pack( fill='both', expand=1 )
		self.imageManipTabs.bind( '<<NotebookTabChanged>>', self.imageManipTabChanged )

		secondRow.pack( fill='both', expand=1 )

	def imageManipTabChanged( self, event ):

		""" Called when the sub-tabs within this tab ('Image', 'Palette', etc.) are changed. """

		currentTab = globalData.gui.root.nametowidget( event.widget.select() )
		currentTab.focus() # Don't want keyboard/widget focus at any particular place yet
		tabState = self.imageManipTabs.tab( currentTab, 'state' )

		if currentTab == self.modelPropertiesPane and tabState != 'disabled':
			self.populateModelTab()
		elif currentTab == self.texturePropertiesPane and tabState != 'disabled':
			self.populateTexPropertiesTab()

	def openNewFile( self, event=None, path='', newTab=False ):

		""" This is only called by pressing Enter/Return on the top file path display/entry of
			the DAT Texture Tree tab. Verifies given the path and loads the file for viewing. """

		if not path:
			path = self.datDestination.get().replace( '"', '' )

		if path not in globalData.disc.files:
			msg( 'Unable to find "{}" in the disc.'.format(path), 'File Not Found', warning=True )
			return

		if newTab:
			self.tabManager.addTab( globalData.disc.files[path] )
		else:
			# Change the file associated with this tab
			self.file = globalData.disc.files[path]
		
			# Clear and repopulate the tab
			self.clear()
			self.update_idletasks() # Visual indication for the user that the tab is updating (unnecessary?)
			self.populateTexEditorTab()

	def clear( self ):
		# Remove any existing entries in the treeview.
		for item in self.datTextureTree.get_children():
			self.datTextureTree.delete( item )

		# Reset the size of the texture display canvas, and clear its contents (besides the grid)
		self.textureDisplay.configure( width=self.textureDisplay.defaultDimensions, height=self.textureDisplay.defaultDimensions )
		self.textureDisplay.delete( self.textureDisplay.find_withtag('border') )
		self.textureDisplay.delete( self.textureDisplay.find_withtag('texture') )

		# Remove the background label
		self.datTextureTreeStatusLabel.place_forget()

		# Reset scroll position to the top
		self.datTextureTree.yview_moveto( 0 )

		# Disable some tabs by default (within the DAT Texture Tree tab), and if viewing one of them, switch to the Image tab
		self.imageManipTabs.select( 0 )
		self.imageManipTabs.tab( self.palettePane, state='disabled' )
		self.imageManipTabs.tab( self.modelPropertiesPane, state='disabled' )
		self.imageManipTabs.tab( self.texturePropertiesPane, state='disabled' )

		# Remove the render engine, so it will initialize new model skeletons if needed
		modelPane = self.modelPropertiesPane.interior
		if modelPane.engine:
			modelPane.engine.destroy()
		modelPane.engine = None

	def rescanPending( self ):

		""" If restartFileScan or haltScan are set to True, this will gracefully 
			prevent the next loop iteration of the scan loop from starting. 
			If a new scan is desired, this allows the previous scan to start it, 
			so that there are never two scan loops running at once (for this tab). """

		if self.restartFileScan:
			#cancelCurrentRenders() # Should be enabled if multiprocess texture decoding is enabled

			self.scanningFile = False
			self.restartFileScan = False

			# Restart the DAT/DOL file scan
			self.clear()
			self.populateTexEditorTab()

			return True

		elif self.haltScan:
			self.scanningFile = False
			self.restartFileScan = False
			printStatus( 'File scan stopped', warning=True )
			return True

		else:
			return False

	def passesImageFilters( self, imageDataOffset, width, height, imageType ):

		""" Used to pass or filter out textures displayed in the DAT Texture Tree tab when loading files.
			Accessed and controled by the main menu's "Settings -> Adjust Texture Filters" option. """

		aspectRatio = float( width ) / height

		def comparisonPasses( subjectValue, comparator, limitingValue ):
			if comparator == '>' and not (subjectValue > limitingValue): return False
			if comparator == '>=' and not (subjectValue >= limitingValue): return False
			if comparator == '=' and not (subjectValue == limitingValue): return False
			if comparator == '<' and not (subjectValue < limitingValue): return False
			if comparator == '<=' and not (subjectValue <= limitingValue): return False
			return True

		# For each setting, break the value into its respective components (comparator & filter value), and then run the appropriate comparison.
		widthComparator, widthValue = self.imageFilters['widthFilter']
		if widthValue != '' and not isNaN(int(widthValue)):
			if not comparisonPasses( width, widthComparator, int(widthValue) ): return False
		heightComparator, heightValue = self.imageFilters['heightFilter']
		if heightValue != '' and not isNaN(int(heightValue)):
			if not comparisonPasses( height, heightComparator, int(heightValue) ): return False
		aspectRatioComparator, aspectRatioValue = self.imageFilters['aspectRatioFilter']
		if aspectRatioValue != '':
			if ':' in aspectRatioValue:
				numerator, denomenator = aspectRatioValue.split(':')
				aspectRatioValue = float(numerator) / float(denomenator)
			elif '/' in aspectRatioValue:
				numerator, denomenator = aspectRatioValue.split('/')
				aspectRatioValue = float(numerator) / float(denomenator)
			else: aspectRatioValue = float(aspectRatioValue)

		if not isNaN(aspectRatioValue) and not comparisonPasses( aspectRatio, aspectRatioComparator, aspectRatioValue ): return False
		imageTypeComparator, imageTypeValue = self.imageFilters['imageTypeFilter']
		if imageTypeValue != '' and not isNaN(int(imageTypeValue)):
			if not comparisonPasses( imageType, imageTypeComparator, int(imageTypeValue) ): return False
		offsetComparator, offsetValue = self.imageFilters['offsetFilter']
		if offsetValue.startswith('0x') and offsetValue != '' and not isNaN(int(offsetValue, 16)):
				if not comparisonPasses( imageDataOffset + 0x20, offsetComparator, int(offsetValue, 16) ): return False
		elif offsetValue != '' and not isNaN(int(offsetValue)):
				if not comparisonPasses( imageDataOffset + 0x20, offsetComparator, int(offsetValue) ): return False

		return True

	def populateTexEditorTab( self, priorityTargets=(), useCache=False ):
		
		self.scanningFile = True
		# self.datTextureTreeBg.place_forget() # Removes the drag-and-drop image

		# Update the name of the tab, top DAT/USD file path bar, and the Prev./Next buttons
		fileName = self.file.isoPath.split( '/' )[-1]
		self.tabManager.tab( self, text=fileName )
		self.datDestination.set( self.file.isoPath )
		self.updatePrevNextFileButtons()

		tic = time.clock()

		texturesShown = totalTextureSpace = 0
		filteredTexturesInfo = []

		if not useCache:
			# Scan the file for textures
			printStatus( 'Scanning File...' )
			self.texturesInfo = self.file.identifyTextures()

			# Clear the repositories for storing image data (used to prevent garbage collection)
			self.datTextureTree.fullTextureRenders = {}
			self.datTextureTree.textureThumbnails = {}

		if self.rescanPending():
			return

		elif self.texturesInfo: # i.e. textures were found
			loadingImage = globalData.gui.imageBank( 'loading' )
			
			for imageDataOffset, imageHeaderOffset, paletteDataOffset, paletteHeaderOffset, width, height, imageType, maxLOD in self.texturesInfo:
				# Ignore textures that don't match the user's filters
				if not self.passesImageFilters( imageDataOffset, width, height, imageType ):
					if imageDataOffset in priorityTargets:
						pass # Overrides the filter
					else:
						continue

				# Initialize a structure for the image data
				texture = self.file.initTexture( imageDataOffset, imageHeaderOffset, paletteDataOffset, paletteHeaderOffset, width, height, imageType, maxLOD, 0 )
				imageDataLength = texture.imageDataLength
				texturesShown += 1

				filteredTexturesInfo.append( (imageDataOffset, width, height, imageType, imageDataLength, maxLOD, 0) )
				totalTextureSpace += texture.length # Length of the struct (includes all mipmap levels)

				# Highlight any textures that need to stand out
				# tags = []
				# #if width > 1024 or width % 2 != 0 or height > 1024 or height % 2 != 0: tags.append( 'warn' )
				# if width % 2 != 0 or height % 2 != 0: tags.append( 'warn' )
				# if maxLOD > 0: tags.append( 'mipmap' )

				# Add this texture to the DAT Texture Tree tab, using the thumbnail generated above
				try:
					self.datTextureTree.insert( '', 'end', 									# '' = parent/root, 'end' = insert position
						iid=str( imageDataOffset ),
						image=loadingImage
						# values=(
						# 	uHex(0x20 + imageDataOffset) + '\n('+uHex(imageDataLength)+')', 	# offset to image data, and data length
						# 	str(width)+' x '+str(height), 										# width and height
						# 	'_'+str(imageType)+' ('+imageFormats[imageType]+')' 				# the image type and format
						# ),
						# tags=tags
					)
				except TclError:
					print( hex(imageDataOffset) + ' already exists!' )
					continue

				# Add any associated mipmap images, as treeview children
				if maxLOD > 0:
					parent = imageDataOffset

					for i in range( int(maxLOD) ):
						# Adjust the parameters for the next mipmap image
						imageDataOffset += imageDataLength # This is of the last image, not the current imageDataLength below
						width = int( math.ceil(width / 2.0) )
						height = int( math.ceil(height / 2.0) )
						imageDataLength = hsdStructures.ImageDataBlock.getDataLength( width, height, imageType )

						# Create a new structure for this block of data
						self.file.initTexture( imageDataOffset, imageHeaderOffset, paletteDataOffset, paletteHeaderOffset, width, height, imageType, maxLOD, i+1 )

						# Add this texture to the DAT Texture Tree tab, using the thumbnail generated above
						self.datTextureTree.insert( parent, 'end', 									# 'end' = insertion position
							iid=str( imageDataOffset ),
							image=loadingImage
							# values=(
							# 	uHex(0x20 + imageDataOffset) + '\n('+uHex(imageDataLength)+')', 	# offset to image data, and data length
							# 	(str(width)+' x '+str(height)), 									# width and height
							# 	'_'+str(imageType)+' ('+imageFormats[imageType]+')' 				# the image type and format
							# ),
							# tags=tags
						)
						filteredTexturesInfo.append( (imageDataOffset, width, height, imageType, imageDataLength, maxLOD, i+1) )

			# Immediately decode and display any high-priority targets
			if priorityTargets:
				for textureInfo in filteredTexturesInfo:
					if textureInfo[0] not in priorityTargets: continue

					#imageDataOffset, _, _, _, width, height, imageType, _, maxLOD = textureInfo
					#dataBlockStruct = self.file.getStruct( imageDataOffset )

					self.renderTextureData( *textureInfo, useCache=useCache )

		# Update the GUI with some of the file's main info regarding textures
		self.datFilesizeText.set( "File Size:  {} ({:,} bytes)".format(humansize(self.file.size), self.file.size) )
		self.totalTextureSpaceText.set( "Total Texture Size:  {} ({:,} b)".format(humansize(totalTextureSpace), totalTextureSpace) )
		self.texturesFoundText.set( 'Textures Found:  ' + str(len(self.texturesInfo)) )
		self.texturesFilteredText.set( 'Filtered Out:  ' + str(len(self.texturesInfo)-texturesShown) )

		if self.rescanPending():
			return

		elif filteredTexturesInfo:
			# tic = time.clock()
			# if 0: # Disabled, until this process can be made more efficient
			# 	#print 'using multiprocessing decoding'

			# 	# Start a loop for the GUI to watch for updates (such updates should not be done in a separate thread or process)
			# 	globalData.gui.thumbnailUpdateJob = globalData.gui.root.after( globalData.gui.thumbnailUpdateInterval, globalData.gui.updateTextureThumbnail )

			# 	# Start up a separate thread to handle and wait for the image rendering process
			# 	renderingThread = Thread( target=startMultiprocessDecoding, args=(filteredTexturesInfo, self.file, globalData.gui.textureUpdateQueue, dumpImages) )
			# 	renderingThread.daemon = True # Allows this thread to be killed automatically when the program quits
			# 	renderingThread.start()

			# else: # Perform standard single-process, single-threaded decoding
			#print 'using standard, single-process decoding'

			i = 1
			for textureInfo in filteredTexturesInfo:
				# Skip items that should have already been processed
				if imageDataOffset in priorityTargets: continue

				# Update this item
				self.renderTextureData( *textureInfo, useCache=useCache )

				# Update the GUI to show new renders every n textures
				if i % 10 == 0:
					if self.rescanPending(): return
					self.datTextureTree.update()
				i += 1

		self.scanningFile = False

		toc = time.clock()
		print( 'scan time: ' + str(toc - tic) )

		if useCache:
			printStatus( 'Filtering complete', success=True )
		else:
			printStatus( 'File scan complete', success=True )

		if self.datTextureTree.get_children() == (): # Display a message that no textures were found, or they were filtered out.
			if not self.texturesInfo:
				self.datTextureTreeStatusMsg.set( 'No textures were found.' )
			else:
				self.datTextureTreeStatusMsg.set( 'No textures were found that pass your current filters.' )
			self.datTextureTreeStatusLabel.place( relx=0.5, rely=0.5, anchor='center' )

	def renderTextureData( self, imageDataOffset, width=-1, height=-1, imageType=-1, imageDataLength=-1, maxLOD=0, mipLevel=-1, problem=False, useCache=False ):

		""" Decodes image data from the globally loaded DAT file at a given offset and creates an image out of it. 
			This then stores/updates the full image and a preview/thumbnail image (so that they're not garbage 
			collected) and displays it in the GUI. The image and its info is displayed in the DAT Texture Tree 
			tab's treeview (this does not update the Dat Texture Tree subtabs, such as Image, Palette, etc). """

		# If using the cache, there's no need to re-decode texture data (useful when just applying texture filtering)
		if not useCache or imageDataOffset not in self.datTextureTree.textureThumbnails:
			# Store the full image (or error image) so it's not garbage collected, and generate the preview thumbnail.
			if problem:
				# The error image is already 64x64, so it doesn't need to be resized for the thumbnail.
				errorImage = globalData.gui.imageBank( 'noImage' )
				self.datTextureTree.fullTextureRenders[imageDataOffset] = errorImage
				self.datTextureTree.textureThumbnails[imageDataOffset] = errorImage
			else:
				try:
					#tic = time.clock()
					pilImage = self.file.getTexture( imageDataOffset, width, height, imageType, imageDataLength, getAsPilImage=True )
					# toc = time.clock()
					# print 'time to decode image for', hex(0x20+imageDataOffset) + ':', toc-tic

				except Exception as errMessage:
					print( 'Unable to make out a texture for data at 0x{:X}; {}'.format(0x20+imageDataOffset, errMessage) )
					problem = True

				self.datTextureTree.fullTextureRenders[imageDataOffset] = ImageTk.PhotoImage( pilImage )
				pilImage.thumbnail( (64, 64), Image.ANTIALIAS )
				self.datTextureTree.textureThumbnails[imageDataOffset] = ImageTk.PhotoImage( pilImage )

		# Collect texture properties
		if imageType == -1:
			width, height, imageType, _, _, maxLOD, mipLevel = self.file.getTextureInfo( imageDataOffset )
			assert imageType != -1, 'Unable to get texture info for the texture at 0x{:X}'.format( 0x20+imageDataOffset )
		imageDataLength = hsdStructures.ImageDataBlock.getDataLength( width, height, imageType )
		
		# Highlight any textures that need to stand out
		tags = []
		if maxLOD > 0: tags.append( 'mipmap' )
		elif width % 2 != 0 or height % 2 != 0: tags.append( 'warn' )
		
		# Build new strings for the properties
		newValues = (
					uHex(0x20 + imageDataOffset) + '\n('+uHex(imageDataLength)+')', 	# offset to image data, and data length
					(str(width)+' x '+str(height)), 								# width and height
					'_'+str(imageType)+' ('+imageFormats[imageType]+')' 			# the image type and format
					)
		
		# Update the icon and info display
		iid = str( imageDataOffset )
		self.datTextureTree.item( iid, image=self.datTextureTree.textureThumbnails[imageDataOffset], values=newValues, tags=tags )

		# Update any mipmap textures below this one
		if maxLOD > 0 and mipLevel < maxLOD:
			width = int( math.ceil(width / 2.0) )
			height = int( math.ceil(height / 2.0) )
			imageDataOffset += imageDataLength
			imageDataLength = hsdStructures.ImageDataBlock.getDataLength( width, height, imageType )
			mipLevel += 1
			self.renderTextureData( imageDataOffset, width, height, imageType, imageDataLength, maxLOD, mipLevel, problem )
			return

		# Update the texture in the Model tab's 3D rendering, if it's available
		renderEngine = self.modelPropertiesPane.interior.engine
		if renderEngine:
			renderEngine.reloadTexture( imageDataOffset )

	def updatePrevNextFileButtons( self ):

		""" Updates the Next/Previous DAT buttons on the DAT Texture Tree tab. Sets their target file to load,
			their tooltip/pop-up text, and the mouse cursor to appear when hovering over it. 'currentFile' will
			be an iid for the file in the Disc File Tree tab. """
		
		currentFile = self.file.isoPath

		# Determine the previous and next files (isoPaths)
		if globalData.gui.discTab:
			isoFileTree = globalData.gui.discTab.isoFileTree

			# Get the prev. item
			prevItem = isoFileTree.prev( currentFile )
			while prevItem != '' and isoFileTree.item( prevItem, 'values' )[1] != 'file':
				prevItem = isoFileTree.prev( prevItem ) # Skips over any folders.

			# Get the next item
			nextItem = isoFileTree.next( currentFile )
			while nextItem != '' and isoFileTree.item( nextItem, 'values' )[1] != 'file':
				nextItem = isoFileTree.next( nextItem ) # Skips over any folders.

		else: # No disc tab available; use the disc itself
			prevItem = ''
			nextItem = ''
			foundCurrent = False
			for isoPath in globalData.disc.files:
				if foundCurrent:
					nextItem = isoPath
					break
				elif isoPath == currentFile:
					foundCurrent = True
				else:
					prevItem = isoPath

		self.updateFileChangeBtn( self.previousDatButton, prevItem )
		self.updateFileChangeBtn( self.nextDatButton, nextItem )

	def updateFileChangeBtn( self, button, newItem ):

		""" Updates the Next/Prev. File buttons at the bottom of the 'Image' tab. """

		if newItem != '':
			# Bind a new target for the click event
			hoverText = 'Click to load {}\nShift-click to open in a new tab.'.format( newItem )
			button.bind( '<Button-1>', lambda event, item=newItem: self.openNewFile(path=item) )
			button.bind( '<Shift-Button-1>', lambda event, item=newItem: self.openNewFile(path=item, newTab=True) )
			button.config( cursor='hand2' )
		else:
			# Disable the button
			hoverText = 'No more!'
			button.unbind('<Button-1>')
			button.unbind('<Shift-Button-1>')
			button.config( cursor='' )

		# Set the hover text
		if button == self.nextDatButton:
			self.nextDatText.set( hoverText )
		else:
			self.previousDatText.set( hoverText )

	def treeview_sort_column( self, col, reverse ):
		# Create a list of the items, as tuples of (statOfInterest, iid), and sort them
		iids = self.datTextureTree.get_children('')
		if col == 'texture': rowsList = [ (int( self.datTextureTree.set(iid, col).split()[0], 16 ), iid) for iid in iids ]
		#elif col == 'dimensions': rowsList = [( int(self.datTextureTree.set(iid, col).split(' x ')[0]) * int(self.datTextureTree.set(iid, col).split(' x ')[1]), iid ) for iid in iids]
		elif col == 'dimensions':
			# Sort the dimensions category by total image area
			def textureArea( dimensions ):
				width, height = dimensions.split( ' x ' )
				return int( width ) * int( height )
			rowsList = [ (textureArea(self.datTextureTree.set(iid, col)), iid ) for iid in iids ]
		elif col == 'type': rowsList = [ (self.datTextureTree.set(iid, col).replace('_', ''), iid) for iid in iids ]

		# Sort the rows and rearrange the treeview based on the newly sorted list.
		rowsList.sort( reverse=reverse )
		for index, ( _, iid ) in enumerate( rowsList ):
			self.datTextureTree.move( iid, '', index )

		# Set the function call for the next (reversed) sort.
		self.datTextureTree.heading( col, command=lambda: self.treeview_sort_column(col, not reverse) )

	def onTextureTreeSelect( self, event, iid=None ):

		""" Called when a texture is selected in the treeview in 
			order to update tabs on the right side of the GUI. """

		# Ensure there is an iid, or do nothing
		if not iid:
			iid = self.datTextureTree.selection()
			if not iid: return
		iid = iid[-1] # Selects the lowest position item selected in the treeview if multiple items are selected.

		# Update the main display with the texture's stored image.
		imageDataOffset = int( iid )
		self.drawTextureToMainDisplay( imageDataOffset )

		# Stop here if this is not a typical DAT file
		if not isinstance( self.file, DatFile ):
			return

		# Get the texture struct
		texture = self.file.structs[imageDataOffset]

		# Determine whether to enable and update the Palette tab.
		currentTab = globalData.gui.root.nametowidget( self.imageManipTabs.select() )
		if texture.imageType in ( 8, 9, 10 ):
			# Enable the palette tab and prepare the data displayed on it.
			self.imageManipTabs.tab( 1, state='normal' )
			self.populatePaletteTab( imageDataOffset, texture.imageDataLength, texture.imageType )
		else:
			# No palette for this texture. Check the currently viewed tab, and if it's the Palette tab, switch to the Image tab.
			if currentTab == self.palettePane:
				self.imageManipTabs.select( self.textureTreeImagePane )
			self.imageManipTabs.tab( self.palettePane, state='disabled' )

		wraplength = self.imageManipTabs.winfo_width() - 20
		lackOfUsefulStructsDescription = ''

		# Check if this is a file that doesn't have image data headers :(
		if (0x1E00, 'MemSnapIconData') in self.file.rootNodes: # The file is LbMcSnap.usd or LbMcSnap.dat (Memory card banner/icon file from SSB Melee)
			lackOfUsefulStructsDescription = 'This file has no known image data headers or other structures to modify.'

		elif (0x4E00, 'MemCardIconData') in self.file.rootNodes: # The file is LbMcGame.usd or LbMcGame.dat (Memory card banner/icon file from SSB Melee)
			lackOfUsefulStructsDescription = 'This file has no known image data headers or other structures to modify.'

		elif self.file.rootNodes[0][1].startswith( 'SIS_' ): # SdMenu.dat/.usd
			lackOfUsefulStructsDescription = 'This file has no known image data headers or other structures to modify.'

		# elif imageDataOffset >= effectTextureRange[0] and imageDataOffset <= effectTextureRange[1]:
		# 	# e2eHeaderOffset = imageDataStruct.imageHeaderOffset
		# 	# textureCount = struct.unpack( '>I', self.file.getData(e2eHeaderOffset, 4) )[0]

		# 	lackOfUsefulStructsDescription = ( 'Effects files and some stages have unique structuring for some textures, like this one, '
		# 									'which do not have a typical image data header, texture object, or other common structures.' )
		# 	# if textureCount == 1:
		# 	# 	lackOfUsefulStructsDescription += ' This texture is not grouped with any other textures,'
		# 	# elif textureCount == 2:
		# 	# 	lackOfUsefulStructsDescription += ' This texture is grouped with 1 other texture,'
		# 	# else:
		# 	# 	lackOfUsefulStructsDescription += ' This texture is grouped with {} other textures,'.format( textureCount )
		# 	# lackOfUsefulStructsDescription += ' with an E2E header at 0x{:X}.'.format( 0x20+e2eHeaderOffset )

		elif not texture: # Make sure an image data struct exists to check if this might be something like a DOL texture
			lackOfUsefulStructsDescription = (  'This texture does not use the usual image data headers and other associated '
												'structures (TObj/MObj/etc.). These are instead stored end-to-end in this file '
												'with other similar textures.' )

		# See if we can get parent structures for this texture
		if not lackOfUsefulStructsDescription and not texture.getParents():
			lackOfUsefulStructsDescription = 'This file has no known image data headers or other structures to modify.'
		
		# Clear collected structures for this texture (will be collected once needed)
		self.modelPropertiesPane.interior.imageDataHeaders = []

		# If the following string has something, there isn't much customization to be done for this texture
		if lackOfUsefulStructsDescription:
			# Disable the model parts tab, and if on that tab, switch to the Image tab.
			if currentTab == self.modelPropertiesPane:
				self.imageManipTabs.select( self.textureTreeImagePane )
			self.imageManipTabs.tab( self.modelPropertiesPane, state='disabled' )
			
			# Add some info to the texture properties tab
			self.imageManipTabs.tab( self.texturePropertiesPane, state='normal' )
			ttk.Label( self.texturePropertiesPane.interior, text=lackOfUsefulStructsDescription, wraplength=wraplength ).pack( pady=30 )

		else:
			# Enable and update the Model tab
			self.imageManipTabs.tab( self.modelPropertiesPane, state='normal' )
			if currentTab == self.modelPropertiesPane:
				self.populateModelTab( [iid] )

			# Enable and update the Properties tab
			self.imageManipTabs.tab( self.texturePropertiesPane, state='normal' )
			if currentTab == self.texturePropertiesPane:
				self.populateTexPropertiesTab( [iid] )

	def drawTextureToMainDisplay( self, imageDataOffset ):

		""" Updates the main display area (the Image tab of the DAT Texture Tree tab) with a 
			texture's stored full-render image, if it has been rendered, and adjusts GUI size. """
		
		texture = self.file.structs[imageDataOffset]
		textureWidth = texture.width
		textureHeight = texture.height

		# Check for a previously rendered texture image (should exist)
		textureImage = self.datTextureTree.fullTextureRenders.get( imageDataOffset )
		if not textureImage:
			print( 'Unable to get a texture image for ' + hex(imageDataOffset) )
			return # May not have been rendered yet

		# Get the current dimensions of the program.
		self.textureDisplay.update_idletasks() # Ensures the info gathered below is accurate
		programWidth = globalData.gui.root.winfo_width()
		programHeight = globalData.gui.root.winfo_height()
		canvasWidth = self.textureDisplay.winfo_width()
		canvasHeight = self.textureDisplay.winfo_height()

		# Get the total width/height used by everything other than the canvas.
		baseW = globalData.gui.defaultWindowWidth - canvasWidth
		baseH = programHeight - canvasHeight

		# Set the new program and canvas widths. (The +2 allows space for a texture border.)
		if textureWidth > canvasWidth:
			newProgramWidth = baseW + textureWidth + 2
			newCanvasWidth = textureWidth + 2
		else:
			newProgramWidth = programWidth
			newCanvasWidth = canvasWidth

		# Set the new program and canvas heights. (The +2 allows space for a texture border.)
		if textureHeight > canvasHeight:
			newProgramHeight = baseH + textureHeight + 2
			newCanvasHeight = textureHeight + 2
		else:
			newProgramHeight = programHeight
			newCanvasHeight = canvasHeight

		# Apply the new sizes for the canvas and root window.
		self.textureDisplay.configure( width=newCanvasWidth, height=newCanvasHeight ) # Adjusts the canvas size to match the texture.
		globalData.gui.root.geometry( str(newProgramWidth) + 'x' + str(newProgramHeight) )

		# Delete current contents of the canvas, and redraw the grid if it's enabled
		self.textureDisplay.delete( 'all' )
		self.updateCanvasGrid( saveChange=False )

		# Add the texture image to the canvas, and draw the texture boundary if it's enabled
		self.textureDisplay.create_image( newCanvasWidth/2, newCanvasHeight/2, anchor='center', image=textureImage, tags='texture' )
		self.updateCanvasTextureBoundary( saveChange=False )

	def populatePaletteTab( self, imageDataOffset, imageDataLength, imageType ):
		# If a palette entry was previously highlighted/selected, keep it that way
		previouslySelectedEntryOffset = -1
		selectedEntries = self.paletteCanvas.find_withtag( 'selected' )
		if selectedEntries:
			tags = self.paletteCanvas.gettags( selectedEntries[0] )

			# Get the other tag, which will be the entry's file offset
			for tag in tags:
				if tag != 'selected':
					previouslySelectedEntryOffset = int( tag.replace('t', '') ) # 't' included in the first place because the tag cannot be purely a number
					break

		self.paletteCanvas.delete( 'all' )
		self.paletteCanvas.paletteEntries = [] # Storage for the palette square images, so they're not garbage collected. (Using images for their canvas-alpha support.)
		self.paletteCanvas.itemColors = {} # For remembering the associated color within the images (rather than looking up pixel data within the image) and other info, to be passed on to the color picker

		# Try to get info on the palette
		paletteDataOffset, paletteHeaderOffset, paletteLength, paletteType, colorCount = self.file.getPaletteInfo( imageDataOffset )

		if paletteDataOffset == -1: # Couldn't find the data. Set all values to 'not available (n/a)'
			self.paletteDataText.set( 'Data Offset:\nN/A' )
			self.paletteHeaderText.set( 'Header Offset:\nN/A' )
			self.paletteTypeText.set( 'Palette Type:\nN/A' )
			self.paletteMaxColorsText.set( 'Max Colors:\nN/A' )
			self.paletteStatedColorsText.set( 'Stated Colors:\nN/A' )
			#self.paletteActualColorsText.set( 'Actual Colors:\nN/A' )
			return

		# Get the image and palette data
		imageData = self.file.getData( imageDataOffset, imageDataLength )
		paletteData = self.file.getPaletteData( paletteDataOffset=paletteDataOffset, imageData=imageData, imageType=imageType )[0]
		paletteData = hexlify( paletteData ) # At least until the TPL codec is rewritten to operate with bytearrays

		# Update all fields and the palette canvas (to display the color entries).
		self.paletteDataText.set( 'Data Offset:\n' + uHex(paletteDataOffset + 0x20) )
		if paletteHeaderOffset == -1: self.paletteHeaderText.set( 'Header Offset:\nNone' )
		else: self.paletteHeaderText.set( 'Header Offset:\n' + uHex(paletteHeaderOffset + 0x20) )

		if paletteType == 0: self.paletteTypeText.set( 'Palette Type:\n0 (IA8)' )
		if paletteType == 1: self.paletteTypeText.set( 'Palette Type:\n1 (RGB565)' )
		if paletteType == 2: self.paletteTypeText.set( 'Palette Type:\n2 (RGB5A3)' )
		self.paletteMaxColorsText.set( 'Max Colors:\n' + str(self.determineMaxPaletteColors( imageType, paletteLength )) )
		self.paletteStatedColorsText.set( 'Stated Colors:\n' + str(colorCount) )
		#self.paletteActualColorsText.set( 'Actual Colors:\n' + str(len(paletteData)/4) )

		# Create the initial/top offset indicator.
		x = 7
		y = 11
		self.paletteCanvas.create_line( 105, y-3, 120, y-3, 130, y+4, 175, y+4, tags='descriptors' ) # x1, y1, x2, y2, etc....
		self.paletteCanvas.create_text( 154, y + 12, text=uHex(paletteDataOffset + 0x20), tags='descriptors' )

		# Populate the canvas with the palette entries.
		for i in range( 0, len(paletteData), 4 ): # For each palette entry....
			paletteEntry = paletteData[i:i+4]
			entryNum = i/4
			paletteEntryOffset = paletteDataOffset + i/2
			x = x + 12
			rgbaColor = TplDecoder.decodeColor( paletteType, paletteEntry, decodeForPalette=True ) # rgbaColor = ( r, g, b, a )
			
			# Prepare and store an image object for the entry (since .create_rectangle doesn't support transparency)
			paletteSwatch = Image.new( 'RGBA', (8, 8), rgbaColor )
			self.paletteCanvas.paletteEntries.append( ImageTk.PhotoImage(paletteSwatch) )

			# Draw a rectangle for a border; start by checking whether this is a currently selected entry
			if paletteEntryOffset == previouslySelectedEntryOffset: 
				borderColor = self.paletteCanvas.entryBorderColor
				tags = ( 'selected', 't'+str(paletteEntryOffset) )
			else:
				borderColor = 'black'
				tags = 't'+str(paletteEntryOffset)
			self.paletteCanvas.create_line( x-1, y-1, x+8, y-1, x+8, y+8, x-1, y+8, x-1, y-1, fill=borderColor, tags=tags )

			# Draw the image onto the canvas.
			itemId = self.paletteCanvas.create_image( x, y, image=self.paletteCanvas.paletteEntries[entryNum], anchor='nw', tags='entries' )
			self.paletteCanvas.itemColors[itemId] = ( rgbaColor, paletteEntry, paletteEntryOffset, imageDataOffset )

			if x >= 103: # End of the row (of 8 entries); start a new row.
				x = 7
				y = y + 11
				i = i / 4 + 1

				# Check if the current palette entry is a multiple of 32 (4 lines)
				if float( i/float(32) ).is_integer() and i < len( paletteData )/4: # (second check prevents execution after last chunk of 0x40)
					y = y + 6
					self.paletteCanvas.create_line( 105, y-3, 117, y-3, 130, y+4, 176, y+4, tags='descriptors' ) # x1, y1, x2, y2, etc....
					self.paletteCanvas.create_text( 154, y + 12, text=uHex(paletteDataOffset + 0x20 + i*2), tags='descriptors' )

		def onColorClick( event ):
			# Determine which canvas item was clicked on, and use that to look up all entry info
			itemId = event.widget.find_closest( event.x, event.y )[0]
			if itemId not in self.paletteCanvas.itemColors: return # Abort. Probably clicked on a border.
			canvasItemInfo = self.paletteCanvas.itemColors[itemId]
			initialHexColor = ''.join( [ "{0:0{1}X}".format( channel, 2 ) for channel in canvasItemInfo[0] ] )

			MeleeColorPicker( 'Change Palette Color', initialHexColor, paletteType, windowId=itemId, datDataOffsets=canvasItemInfo, targetFile=self.file )

		def onMouseEnter(e): self.paletteCanvas['cursor']='hand2'
		def onMouseLeave(e): self.paletteCanvas['cursor']=''

		self.paletteCanvas.tag_bind( 'entries', '<1>', onColorClick )
		self.paletteCanvas.tag_bind( 'entries', '<Enter>', onMouseEnter )
		self.paletteCanvas.tag_bind( 'entries', '<Leave>', onMouseLeave )

	def determineMaxPaletteColors( self, imageType, paletteStructLength ):

		""" Determines the maximum number of colors that are suppored by a palette. Image type and palette 
			data struct length are both considered, going with the lower limit between the two. """

		if imageType == 8: 		# 4-bit
			maxColors = 16
		elif imageType == 9:	# 8-bit
			maxColors = 256
		elif imageType == 10:	# 14-bit
			maxColors = 16384
		else:
			print( 'Invalid image type given to determineMaxPaletteColors(): ' + str(imageType) )
			return 0

		# The actual structure length available overrides the image's type limitation
		maxColorsBySpace = paletteStructLength / 2
		if maxColorsBySpace < maxColors:
			maxColors = maxColorsBySpace

		return maxColors
	
	def collectStructs( self, iid ):

		""" Collects texture-related structures for use in the Model and Properties tabs. 
			This info is only collected if one of those tabs is selected in order to 
			prevent unnecessary processing and widget creation, and improve performance. """

		# If there are image data headers populated, then this function has already been run for this texture
		modelPane = self.modelPropertiesPane.interior
		if modelPane.imageDataHeaders:
			return
		
		# Get the texture struct and its parents
		imageDataOffset = int( iid )
		texture = self.file.structs[imageDataOffset]

		modelPane.nonImageDataHeaders = [] # Not expected
		modelPane.textureStructs = [] # Direct model attachments
		modelPane.headerArrayStructs = [] # Used for animations
		modelPane.unexpectedStructs = []

		# Double-check that all of the parents are actually image data headers, and get grandparent structs
		for imageHeaderOffset in texture.getParents(): # This should exclude any root/reference node parents (such as a label)
			headerStruct = self.file.initSpecificStruct( hsdStructures.ImageObjDesc, imageHeaderOffset )

			if headerStruct:
				modelPane.imageDataHeaders.append( headerStruct )

				# Check the grandparent structs; expected to be Texture Structs or Image Data Header Arrays
				for grandparentOffset in headerStruct.getParents():
					# Try getting or initializing a Texture Struct
					texStruct = self.file.initSpecificStruct( hsdStructures.TextureObjDesc, grandparentOffset, printWarnings=False )

					if texStruct:
						modelPane.textureStructs.append( texStruct )
					else:
						# Try getting or initializing an Image Header Array Struct
						arrayStruct = self.file.initSpecificStruct( hsdStructures.ImageHeaderArray, grandparentOffset, printWarnings=False )
					
						if arrayStruct:
							modelPane.headerArrayStructs.append( arrayStruct )
						else:
							# Initialize a general struct
							modelPane.unexpectedStructs.append( self.file.getStruct( grandparentOffset ) )
			else:
				# Attempt to initialize it in a generalized way (attempts to identify; returns a general struct if unable)
				modelPane.nonImageDataHeaders.append( self.file.getStruct(imageHeaderOffset) )

		# Get the associated material structs and display objects
		#modelPane.materialStructs = []
		modelPane.displayObjects = []
		for texStruct in modelPane.textureStructs:
			for materialStructOffset in texStruct.getParents():
				materialStruct = self.file.initSpecificStruct( hsdStructures.MaterialObjDesc, materialStructOffset )

				if materialStruct:
					#modelPane.materialStructs.append( materialStruct )

					for displayObjOffset in materialStruct.getParents():
						displayObject = self.file.initSpecificStruct( hsdStructures.DisplayObjDesc, displayObjOffset )

						if displayObject:
							modelPane.displayObjects.append( displayObject )

		#print( 'material structs: ' + str([hex(0x20+obj.offset) for obj in modelPane.materialStructs]) )
		#print( 'displayObj structs: ' + str([hex(0x20+obj.offset) for obj in modelPane.displayObjects]) )

	def populateModelTab( self, iid=None ):

		# Ensure there is an iid, or do nothing
		if not iid:
			iid = self.datTextureTree.selection()
			if not iid: return
		iid = iid[-1] # Selects the lowest position item selected in the treeview if multiple items are selected.

		modelPane = self.modelPropertiesPane.interior
		wraplength = modelPane.winfo_width() - 20
		vertPadding = 8

		# Clear the current contents
		for childWidget in modelPane.winfo_children():
			if not isinstance( childWidget, RenderEngine ):
				childWidget.destroy()

		# Reset the scrollbar (if there is one displayed) to the top.
		self.modelPropertiesPane.canvas.yview_moveto( 0 )

		self.collectStructs( iid )

		# Create a render canvas if any model parts were detected
		if modelPane.displayObjects:
			# Add the rendering widget if it's not present
			if not modelPane.engine:
				self.initializeRenderEngine()
			modelPane.engine.pack( pady=(vertPadding, 4) )

			# Determine a part to show by default
			modelPart = self.determineDefaultPart()

			# Add a button to access the render options, and repopulate the window if it's open
			modelPane.renderOptionsBtn = ColoredLabelButton( modelPane, 'gear', self.showDisplayOptions, 'Display Options' )
			modelPane.renderOptionsBtn.place( anchor='ne', relx=1.0, x=-6, y=6 )
			# if self.renderOptionsWindowIsOpen():
			# 	self.renderOptionsWindow.repopulate()

			if len( modelPane.displayObjects ) == 1:
				# Add a label below the rendering showing the Display Object's name
				ttk.Label( modelPane, text=modelPart.name ).pack( pady=(vertPadding, 4) )
			else:
				# Add a label below the rendering showing the Display Object's name, and controls to swap to other display objects
				dobjSelectionControls = ttk.Frame( modelPane )
				prevDobjBtn = LabelButton( dobjSelectionControls, '', self.renderPrevDobj, 'Previous Display Object' )
				prevDobjBtn.defaultImage = prevDobjBtn['image'] = self.tabManager.leftArrow
				prevDobjBtn.hoverImage = self.tabManager.leftArrowHovered
				prevDobjBtn.pack( side='left' )
				ttk.Label( dobjSelectionControls, textvariable=modelPane.dobjStringVar ).pack( side='left', padx=7 )
				nextDobjBtn = LabelButton( dobjSelectionControls, '', self.renderNextDobj, 'Next Display Object' )
				nextDobjBtn.defaultImage = nextDobjBtn['image'] = self.tabManager.rightArrow
				nextDobjBtn.hoverImage = self.tabManager.rightArrowHovered
				nextDobjBtn.pack( side='left' )
				dobjSelectionControls.pack( pady=(vertPadding, 4) )

		else: # No model parts detected; fall back to text descriptions of what was found
			modelPart = None
			modelPane.currentRenders = []
			if modelPane.engine:
				modelPane.engine.pack_forget()
			if modelPane.renderOptionsBtn:
				modelPane.renderOptionsBtn.destroy()

			# Add a label for image data headers count
			if len( modelPane.imageDataHeaders ) == 1: # todo: make searching work for multiple offsets
				headerCountFrame = ttk.Frame( modelPane )
				ttk.Label( headerCountFrame, text='Model Attachments (Image Data Headers):  {}'.format(len(modelPane.imageDataHeaders)), wraplength=wraplength ).pack( side='left' )
				#PointerLink( headerCountFrame, modelPane.imageDataHeaders[0].offset ).pack( side='right', padx=5 )
				headerCountFrame.pack( pady=(vertPadding*2, 0) )
			else:
				ttk.Label( modelPane, text='Model Attachments (Image Data Headers):  {}'.format(len(modelPane.imageDataHeaders)), wraplength=wraplength ).pack( pady=(vertPadding*2, 0) )

			# Add a notice of non image data header structs, if any.
			if modelPane.nonImageDataHeaders:
				print( 'Non-Image Data Header detected as image data block parent!' )
				if len( modelPane.nonImageDataHeaders ) == 1:
					nonImageDataHeadersText = '1 non-image data header detected:  ' + modelPane.nonImageDataHeaders[0].name
				else:
					structNamesString = grammarfyList( [structure.name for structure in modelPane.nonImageDataHeaders] )
					nonImageDataHeadersText = '{} non-image data headers detected:  {}'.format( len(modelPane.nonImageDataHeaders), structNamesString )
				ttk.Label( modelPane, text=nonImageDataHeadersText, wraplength=wraplength ).pack( pady=(vertPadding, 0) )

			# Add details for Texture Struct or Material Struct attachments
			if len( modelPane.textureStructs ) == 1:
				textStructsText = 'Associated with 1 Texture Struct.'
			else:
				textStructsText = 'Associated with {} Texture Structs.'.format( len(modelPane.textureStructs) )
			ttk.Label( modelPane, text=textStructsText, wraplength=wraplength ).pack( pady=(vertPadding, 0) )
			if len( modelPane.headerArrayStructs ) == 1:
				arrayStructsText = 'Associated with 1 Material Animation.'
			else:
				arrayStructsText = 'Associated with {} Material Animations.'.format( len(modelPane.headerArrayStructs) )
			ttk.Label( modelPane, text=arrayStructsText, wraplength=wraplength ).pack( pady=(vertPadding, 0) )

			if modelPane.unexpectedStructs:
				unexpectedStructsText = 'Unexpected Grandparent Structs: ' + grammarfyList( [structure.name for structure in modelPane.nonImageDataHeaders] )
				ttk.Label( modelPane, text=unexpectedStructsText, wraplength=wraplength ).pack( pady=(vertPadding, 0) )
				
			ttk.Separator( modelPane, orient='horizontal' ).pack( fill='x', padx=24, pady=(vertPadding*2, vertPadding) )

		self.populateMaterialProperties()

		if modelPart:
			self.renderDobj( [modelPart], True )

	def populateMaterialProperties( self ):

		""" Adds controls to edit DObj/MObj properties to the Model tab. 
			This includes everything below the render window except the 
			'Display Object _' label and associated buttons; i.e. model 
			render checkboxes, transparency control and material colors. """
		
		modelPane = self.modelPropertiesPane.interior
		vertPadding = 8

		# Create checkboxes to edit model part visibility
		transparencyPane = ttk.Frame( modelPane )
		jointHidden = Tk.BooleanVar()
		displayListDisabled = Tk.BooleanVar() # Whether or not display list length has been set to 0

		modelPane.hideJointChkBtn = ttk.Checkbutton( transparencyPane, text='Disable Part Rendering (Hide Joint)', variable=jointHidden, command=self.toggleHideJoint )
		modelPane.hideJointChkBtn.var = jointHidden
		modelPane.hideJointChkBtn.grid( column=0, row=0, sticky='w', columnspan=3 )

		modelPane.polyDisableChkBtn = ttk.Checkbutton( transparencyPane, text='Disable Polygon (Display List) Rendering', variable=displayListDisabled, command=self.toggleDisplayListRendering )
		modelPane.polyDisableChkBtn.var = displayListDisabled
		modelPane.polyDisableChkBtn.grid( column=0, row=1, sticky='w', columnspan=3 )

		# Add a help button to explain the controls here
		helpText = ( 'All of these controls will affect all of the model parts (Display Objects) currently selected. Non-selected '
					'parts will appear obscured by default (darkened and under-staturated), which can be toggled by the '
					'"Obscure non-selected parts" option in the Render Options window. You can also open the Render Options window '
					'to see exactly what parts are selected. When the controls at the bottom of this tab appear with an orange border, '
					'that too indicates that multiple model parts are selected and that the controls will edit each of those parts.'
					'\n\nDisabling Part Rendering will set the "Hidden" flag (bit 4) for all of the lowest-level Joint Structures '
					"connected to the currently selected model parts (parents to this texture's Display Object(s)). That will be "
					"just one particular Joint Struct in most cases, however that may be the parent for multiple parts of the model. "
					"To have finer control over which model parts are disabled, consider the Disable Polygon Rendering option."
					"\n\nDisabling Polygon Rendering is achieved by setting the display list data stream size to 0 "
					"""(i.e. each associated Polygon Objects' "Display List Length" value). This is done for """
					"each Polygon Object of each model part (Display Object) currently selected. For finer control, use "
					'the Structural Analysis tab. There, you can even experiment with reducing the length of the list '
					'to some other value between 0 and the original value, in order to render or hide different polygon groups.'
					'\n\nTransparency Control makes the entire model part partially transparent. This uses the '
					'value found in the Material Colors Struct by the same name, while setting multiple flags within '
					"parenting structures. The flags set are 'Render No Z-Update' and 'Render XLU' of the Material Structs "
					"(bits 29 and 30, respectfully), as well as 'XLU' and 'Root XLU' of the Joint Struct (bits 19 and 29). " )
		helpBtn = ttk.Label( transparencyPane, text='?', foreground='#445', cursor='hand2' )
		helpBtn.place( relx=1, x=-17, y=0 )
		helpBtn.bind( '<1>', lambda e, message=helpText: msg(message, 'Disabling Rendering and Transparency') )

		# Create widgets to update Transparency (the material colors struct's alpha property).
		# Note that the Entry and Scale widgets do not update the value; only the Set button can set it.
		ttk.Label( transparencyPane, text='Transparency Control:' ).grid( column=0, row=2, sticky='w', columnspan=3, padx=15, pady=(12, 4) )
		opacityValidationRegistration = globalData.gui.root.register( self.opacityEntryUpdated )
		modelPane.opacityEntry = ttk.Entry( transparencyPane, width=7, justify='center', validate='key', validatecommand=(opacityValidationRegistration, '%P') )
		modelPane.opacityEntry.grid( column=0, row=3 )
		modelPane.opacityBtn = ttk.Button( transparencyPane, text='Set', command=self.setModelTransparencyLevel, width=4 )
		modelPane.opacityBtn.grid( column=1, row=3, padx=4 )
		modelPane.opacityScale = ttk.Scale( transparencyPane, from_=0, to=10, command=self.opacityScaleUpdated )
		modelPane.opacityScale.grid( column=2, row=3, sticky='we' )

		transparencyPane.pack( pady=(vertPadding, 0), expand=True, fill='x', padx=70 )

		transparencyPane.columnconfigure( 0, weight=0 )
		transparencyPane.columnconfigure( 1, weight=0 )
		transparencyPane.columnconfigure( 2, weight=1 )

		# Add widgets for Material Color editing
		ttk.Label( modelPane, text='Material Colors:' ).pack( pady=(vertPadding, 0) )

		colorsPane = ttk.Frame( modelPane )

		# Row 1; Diffusion and Ambience
		ttk.Label( colorsPane, text='Diffusion:' ).grid( column=0, row=0, sticky='e', padx=(24, 0) )
		modelPane.diffusionEntry = HexEditEntry( colorsPane, self.file, -1, 4, 'I', 'Diffusion' ) # Data offset (the -1) will be updated below
		modelPane.diffusionEntry.grid( column=1, row=0, padx=6 )
		ttk.Label( colorsPane, text='Ambience:' ).grid( column=3, row=0, sticky='e', padx=(24, 0) )
		modelPane.ambienceEntry = HexEditEntry( colorsPane, self.file, -1, 4, 'I', 'Ambience' ) # Data offset (the -1) will be updated below
		modelPane.ambienceEntry.grid( column=4, row=0, padx=6 )

		# Row 2; Specular Highlights and Shininess
		ttk.Label( colorsPane, text='Highlights:' ).grid( column=0, row=1, sticky='e', padx=(24, 0) )
		modelPane.highlightsEntry = HexEditEntry( colorsPane, self.file, -1, 4, 'I', 'Specular Highlights' ) # Data offset (the -1) will be updated below
		modelPane.highlightsEntry.grid( column=1, row=1, padx=6 )
		ttk.Label( colorsPane, text='Shininess:' ).grid( column=3, row=1, sticky='e', padx=(24, 0) )
		modelPane.shininessEntry = HexEditEntry( colorsPane, self.file, -1, 4, 'f', 'Shininess', valueEntry=True ) # Data offset (the -1) will be updated below
		modelPane.shininessEntry.grid( column=4, row=1, padx=6 )

		# Add a callback to the above entry widgets, so they update the model render when changed
		modelPane.diffusionEntry.callback = self.refreshRender
		modelPane.ambienceEntry.callback = self.refreshRender
		modelPane.highlightsEntry.callback = self.refreshRender
		modelPane.shininessEntry.callback = self.refreshRender

		colorsPane.pack( pady=(vertPadding, 0), padx=20 )

	def connectMaterialColorControls( self ):

		""" Hooks up the Transparency and color control widgets (ambience, diffusion, etc)
			with to the currently selected model parts (DObjs); sets their target offsets 
			and currently displayed values/colors. """

		modelPane = self.modelPropertiesPane.interior
		wraplength = modelPane.winfo_width() - 20

		# Set initial values for the transparency controls and material colors above, or disable them
		if modelPane.currentRenders:
			firstDisplayObj = modelPane.currentRenders[0]

			# Get a parent Joint Object, and see if its hidden flag is set
			for structureOffset in firstDisplayObj.getParents():
				jointStruct = self.file.initSpecificStruct( hsdStructures.JointObjDesc, structureOffset )
				if jointStruct:
					jointFlags = jointStruct.getValues( specificValue='Joint_Flags' )
					modelPane.hideJointChkBtn.var.set( jointFlags & 0b10000 ) # Checking bit 4
					break
			else: # The loop above didn't break; no joint struct parent found
				modelPane.hideJointChkBtn.configure( state='disabled' )
				ToolTip( modelPane.hideJointChkBtn, '(No parent Joint Object found.)', wraplength=400 )

			# Check the current state of this model part's rendering; get the first Polygon Object, and see if its Display List Blocks/Length attribute is 0
			polygonObjOffset = firstDisplayObj.getValues( specificValue='Polygon_Object_Pointer' )
			polygonObj = self.file.initSpecificStruct( hsdStructures.PolygonObjDesc, polygonObjOffset, firstDisplayObj.offset )

			if polygonObj:
				displayListBlocks = polygonObj.getValues( 'Display_List_Length' )
				modelPane.polyDisableChkBtn.var.set( not bool(displayListBlocks) ) # Resolves to True if the value is 0, False for anything else
			else:
				modelPane.polyDisableChkBtn.var.set( False )
				modelPane.polyDisableChkBtn.configure( state='disabled' )

			# Get the associated material structs
			matStructs = [ dobj.MObj for dobj in modelPane.currentRenders ]

			# If we found display objects, we must have also found material structs; get default values
			#materialStruct = modelPane.materialStructs[modelPane.partIndex]
			materialStruct = matStructs[0]
			matColorsOffset = materialStruct.getValues()[3]
			matColorsStruct = self.file.initSpecificStruct( hsdStructures.MaterialColorObjDesc, matColorsOffset, materialStruct.offset )
			diffusion, ambience, specularHighlights, transparency, shininess = matColorsStruct.getValues()

			# Get all of the offsets that would be required to update material color values for the selected parts
			diffusionHexOffsets = []
			ambienceHexOffsets = []
			highlightsHexOffsets = []
			shininessHexOffsets = []
			for materialStruct in matStructs:
				matColorsStructOffset = materialStruct.getValues( 'Material_Colors_Pointer' )
				diffusionHexOffsets.append( matColorsStructOffset )
				ambienceHexOffsets.append( matColorsStructOffset + 4 )
				highlightsHexOffsets.append( matColorsStructOffset + 8 )
				shininessHexOffsets.append( matColorsStructOffset + 0x10 )

			# Set the transparency slider's value (which will also update the Entry widget's value)
			modelPane.opacityScale.set( transparency * 10 ) # Multiplied by 10 because the slider's range is 0 to 10 (to compensate for trough-click behavior)

			# Add an event handler to forces focus to go to the slider when it's clicked on (dunno why it doesn't do this already).
			# This is necessary for the opacityScaleUpdated function to work properly
			modelPane.opacityScale.bind( '<Button-1>', lambda event: modelPane.opacityScale.focus() )

			# Add these values and color swatches to the GUI
			diffusionHexString = '{0:0{1}X}'.format( diffusion, 8 ) # Avoids the '0x' and 'L' appendages brought on by the hex() function. pads to 8 characters
			ambienceHexString = '{0:0{1}X}'.format( ambience, 8 ) # Avoids the '0x' and 'L' appendages brought on by the hex() function. pads to 8 characters
			highlightsHexString = '{0:0{1}X}'.format( specularHighlights, 8 ) # Avoids the '0x' and 'L' appendages brought on by the hex() function. pads to 8 characters

			# Clear any current values
			modelPane.diffusionEntry

			# Update the hex entry widgets
			modelPane.diffusionEntry.set( diffusionHexString )
			modelPane.diffusionEntry.offsets = diffusionHexOffsets
			modelPane.ambienceEntry.set( ambienceHexString )
			modelPane.ambienceEntry.offsets = ambienceHexOffsets
			modelPane.highlightsEntry.set( highlightsHexString )
			modelPane.highlightsEntry.offsets = highlightsHexOffsets
			modelPane.shininessEntry.set( shininess )
			modelPane.shininessEntry.offsets = shininessHexOffsets

			# print( modelPane.shininessEntry['highlightbackground'] )
			# print( modelPane.shininessEntry['highlightthickness'] )

			# Set or clear borders
			if len( diffusionHexOffsets ) > 1:
				modelPane.diffusionEntry['highlightbackground'] = 'orange'
				#modelPane.diffusionEntry['highlightthickness'] = 1
				modelPane.ambienceEntry['highlightbackground'] = 'orange'
				#modelPane.ambienceEntry['highlightthickness'] = 1
				modelPane.highlightsEntry['highlightbackground'] = 'orange'
				#modelPane.highlightsEntry['highlightthickness'] = 1
				modelPane.shininessEntry['highlightbackground'] = 'orange'
				#modelPane.shininessEntry['highlightthickness'] = 1
			else:
				# modelPane.diffusionEntry['highlightthickness'] = 0
				# modelPane.ambienceEntry['highlightthickness'] = 0
				# modelPane.highlightsEntry['highlightthickness'] = 0
				# modelPane.shininessEntry['highlightthickness'] = 0
				modelPane.diffusionEntry['highlightbackground'] = '#b7becc'
				modelPane.ambienceEntry['highlightbackground'] = '#b7becc'
				modelPane.highlightsEntry['highlightbackground'] = '#b7becc'
				modelPane.shininessEntry['highlightbackground'] = '#b7becc'

			# Update existing color swatches, if already present
			if modelPane.diffusionEntry.colorSwatchWidget:
				if modelPane.diffusionEntry.colorSwatchWidget['state'] == 'disabled':
					modelPane.diffusionEntry.colorSwatchWidget.enable()
					modelPane.ambienceEntry.colorSwatchWidget.enable()
					modelPane.highlightsEntry.colorSwatchWidget.enable()
				modelPane.diffusionEntry.colorSwatchWidget.renderCircle( diffusionHexString )
				modelPane.ambienceEntry.colorSwatchWidget.renderCircle( ambienceHexString )
				modelPane.highlightsEntry.colorSwatchWidget.renderCircle( highlightsHexString )
			else:
				# Color swatches haven't been created yet
				colorsPane = modelPane.diffusionEntry.master

				modelPane.diffusionEntry.colorSwatchWidget = ColorSwatch( colorsPane, diffusionHexString, modelPane.diffusionEntry )
				modelPane.diffusionEntry.colorSwatchWidget.grid( column=2, row=0, padx=(0,2) )
				
				modelPane.ambienceEntry.colorSwatchWidget = ColorSwatch( colorsPane, ambienceHexString, modelPane.ambienceEntry )
				modelPane.ambienceEntry.colorSwatchWidget.grid( column=5, row=0, padx=(0,2) )
				
				modelPane.highlightsEntry.colorSwatchWidget = ColorSwatch( colorsPane, highlightsHexString, modelPane.highlightsEntry )
				modelPane.highlightsEntry.colorSwatchWidget.grid( column=2, row=1, padx=(0,2) )

		else:
			# Disable the render checkbuttons and transparency controls
			modelPane.hideJointChkBtn.configure( state='disabled' )
			modelPane.polyDisableChkBtn.configure( state='disabled' )
			modelPane.opacityEntry.configure( state='disabled' )
			modelPane.opacityBtn.configure( state='disabled' )

			# Disable the Material Color inputs
			modelPane.diffusionEntry.configure( state='disabled' )
			modelPane.ambienceEntry.configure( state='disabled' )
			modelPane.highlightsEntry.configure( state='disabled' )
			modelPane.shininessEntry.configure( state='disabled' )

			# Disable color swatches
			if modelPane.diffusionEntry.colorSwatchWidget:
				modelPane.diffusionEntry.colorSwatchWidget.disable()
				modelPane.ambienceEntry.colorSwatchWidget.disable()
				modelPane.highlightsEntry.colorSwatchWidget.disable()

			# Add a label explaining why these are disabled
			disabledControlsText = ( 'These controls are disabled because no Display Objects or Material Structs are currently selected.' )
									#'If this is part of a texture animation, find the default/starting texture for it and edit the structs for that instead.' )
			ttk.Label( modelPane, text=disabledControlsText, wraplength=wraplength ).pack( pady=(8, 0) )

	def initializeRenderEngine( self ):

		""" Creates a render engine for this tab, sets its frustum to nominal values, 
			and performs some extra processing for models with a skeleton. """
		
		modelPane = self.modelPropertiesPane.interior
		modelPane.engine = RenderEngine( modelPane, (440, 300), False, background=globalData.gui.defaultSystemBgColor, borderwidth=0, relief='groove' )

		# If this is a character file, initialize the model's skeleton and check model part high/low-poly aspects
		if isinstance( self.file, CharCostumeFile ):
			rootJoint = self.file.getSkeletonRoot()
			modelPane.engine.loadSkeleton( rootJoint, modelPane.showBones.get() )

			# Determine high/low-poly model parts
			try:
				# Get the Pl__.dat file
				plFilename = 'Pl' + self.file.charAbbr + '.dat'
				plFile = globalData.disc.getFile( plFilename )

				# Get the part visibility lookup table and parse lookup entries
				lookupTable = plFile.getModelLookupTable()
				visibilityTable = lookupTable.initChild( 'CostumeVisibilityTable', 1 )
				costumeIndex = self.file.getCostumeId()

				modelPane.highPolyIds = visibilityTable.getHighPolyPartIds( costumeIndex )
				modelPane.lowPolyIds = visibilityTable.getLowPolyPartIds( costumeIndex )
			except Exception as err:
				print( 'Unable to get model high/low-poly part IDs; {}'.format(err) )

		# Set frustum limits (near/far rendering limits)
			modelPane.engine.zNear = 1.0; modelPane.engine.zFar = 800
		elif isinstance( self.file, StageFile ):
			modelPane.engine.zNear = 10.0; modelPane.engine.zFar = 4000

			# Attempt to initialize any skeletons
			modelPane.engine.loadStageSkeletons( self.file, modelPane.showBones.get() )
		else:
			modelPane.engine.zNear = 2.5; modelPane.engine.zFar = 1500

	def determineDefaultPart( self ):

		""" Attempts to intelligently determine a model part (DObj) to 
			show by default in the Model tab when a texture is selected. 
			Prioritizes selection for high or low-poly parts depending 
			on the current state of that option. If a part is not found 
			for the current high/low-poly option, the option will be changed. """

		# Get the default part; i.e. the first part used by the selected texture
		modelPane = self.modelPropertiesPane.interior
		modelPane.partIndex = 0
		defaultPart = modelPane.displayObjects[0]

		# Determine whether the user currently has high or low-poly parts selected for display
		if modelPane.showHighPoly.get():
			# Use the default part if it's high-poly
			if defaultPart.id not in modelPane.highPolyIds:
				# Check if a high-poly part is available
				for i, part in enumerate( modelPane.displayObjects ):
					if part.id in modelPane.highPolyIds:
						modelPane.partIndex = i
						return part
				else: # The above loop didn't return; no high-poly part found
					# Switch the high/low-poly part option to low and display the default part
					modelPane.showHighPoly.set( False )
		else:
			# Use the default part if it's low-poly
			if defaultPart.id not in modelPane.lowPolyIds:
				# Check if a low-poly part is available
				for i, part in enumerate( modelPane.displayObjects ):
					if part.id in modelPane.lowPolyIds:
						modelPane.partIndex = i
						return part
				else: # The above loop didn't return; no low-poly part found
					# Switch the high/low-poly part option to high and display the default part
					modelPane.showHighPoly.set( True )

		return defaultPart

	def renderPrevDobj( self, event ):

		""" Called by the 'back' arrow underneath the render window. 
			Switches to the last or previous DObj for rendering. """

		# Decrease the current part (display object) index
		modelPane = self.modelPropertiesPane.interior
		if modelPane.partIndex <= 0:
			modelPane.partIndex = len( modelPane.displayObjects ) - 1
		else:
			modelPane.partIndex -= 1
		
		modelPart = modelPane.displayObjects[modelPane.partIndex]

		# Toggle the showHighPoly option if it would otherwise hide the part
		if isinstance( self.file, CharCostumeFile ):
			if not modelPane.highPolyIds == modelPane.lowPolyIds: # True for some characters, like Wireframes
				showHighPoly = modelPane.showHighPoly.get()
				if showHighPoly and modelPart.id in modelPane.lowPolyIds:
					modelPane.showHighPoly.set( False )
				elif not showHighPoly and modelPart.id in modelPane.highPolyIds:
					modelPane.showHighPoly.set( True )

		self.renderDobj( [modelPart], True )

	def renderNextDobj( self, event ):

		""" Called by the 'next' arrow underneath the render window. 
			Switches to the next or first DObj for rendering. """

		# Increase the current part (display object) index
		modelPane = self.modelPropertiesPane.interior
		if modelPane.partIndex >= len( modelPane.displayObjects ) - 1:
			modelPane.partIndex = 0
		else:
			modelPane.partIndex += 1
		
		modelPart = modelPane.displayObjects[modelPane.partIndex]

		# Toggle the showHighPoly option if it would otherwise hide the part
		if isinstance( self.file, CharCostumeFile ):
			if not modelPane.highPolyIds == modelPane.lowPolyIds: # True for some characters, like Wireframes
				showHighPoly = modelPane.showHighPoly.get()
				if showHighPoly and modelPart.id in modelPane.lowPolyIds:
					modelPane.showHighPoly.set( False )
				elif not showHighPoly and modelPart.id in modelPane.highPolyIds:
					modelPane.showHighPoly.set( True )

		self.renderDobj( [modelPart], True )

	def renderDobj( self, modelParts, updateOptionsWindow=False, updateCamera=True ):
		
		""" Sets one or more model parts to render in the Model tab for the currently 
			selected texture. The model parts given to this function should be DObjs 
			which the currently selected texture is actually a part of or used for. 
			However, this function may add additional model parts (DObj siblings) to 
			provide additional visual context to the user for the rendered scene. """
		
		# Clear current renders
		modelPane = self.modelPropertiesPane.interior
		modelPane.engine.clearRenderings()

		if not modelParts:
			modelPane.dobjStringVar.set( 'No Parts Selected' )
			self.connectMaterialColorControls()
			self.populateTexPropertiesTab()
			return

		# Add a flag for the renderer to dim/obscure certain parts
		obscureNonSelected = modelPane.obscureNonSelected.get()
		allParts = []
		for struct in self.file.structs.values():
			if isinstance( struct, hsdStructures.DisplayObjDesc ):
				allParts.append( struct )

				if not obscureNonSelected or struct in modelParts:
					struct.renderState = 'normal' # todo: make this an enum if more states are added
				else:
					struct.renderState = 'dim'

		if modelParts[0].skeleton:
			if modelPane.displayMode == DisplayMode.SelectedOnly:
				# Show strictly the given parts
				for modelPart in modelParts:
					if self.hideBasedOnPoly( modelPart ):
						continue

					modelPane.engine.renderDisplayObj( modelPart, includeSiblings=False )
				
				modelPane.selectableObjects = modelPane.displayObjects

			elif modelPane.displayMode == DisplayMode.Related:
				modelPane.selectableObjects = []
				for modelPart in modelParts:
					# Use the model's skeleton to find a few near-by parts
					for partOffset in self.findRelatedParts( modelPart ):
						part = self.file.getStruct( partOffset )
						modelPane.selectableObjects.append( part )

						if self.hideBasedOnPoly( part ):
							continue

						modelPane.engine.renderDisplayObj( part, includeSiblings=False )

			else: # All (display everything)
				#modelParts = allParts
				modelPane.selectableObjects = allParts

				for part in allParts:
					if self.hideBasedOnPoly( part ):
						continue
					modelPane.engine.renderDisplayObj( part, includeSiblings=False )

		else:
			# No skeleton to use when positioning various parts; fall back to basic joint transforms only
			for modelPart in modelParts:
				primitives = modelPane.engine.renderDisplayObj( modelPart, includeSiblings=modelPane.displayMode )

				# Update relative position based on parent joint coordinates
				parentJointOffset = next(iter( modelPart.getParents() ))
				parentJoint = self.file.initSpecificStruct( hsdStructures.JointObjDesc, parentJointOffset )
				modelPane.engine.applyJointTransformations( primitives, parentJoint )
			modelPane.selectableObjects = modelPane.displayObjects

		# Remember what parts were last selected to render
		modelPane.currentRenders = modelParts # Excludes "related" parts, or extra parts that are selectable
		# print( 'Current selectable: ' + str([dobj.name for dobj in modelPane.selectableObjects]) )
		# print( 'Current renders: ' + str([dobj.name for dobj in modelPane.currentRenders]) )

		# Align the camera to the object(s)
		if updateCamera and modelPane.autoCameraUpdates.get():
			modelPane.engine.focusCamera( primitive='vertexList' )

		# Update the title string under the render window
		if len( modelPane.displayObjects ) == 1:
			modelPane.dobjStringVar.set( modelParts[0].name )
		elif len( modelParts ) > 1: # Multiple DObjs (with or without siblings) selected for render
			if len( modelParts ) < 4:
				title = 'Display Objects ' + grammarfyList( ['0x{:X}'.format(0x20+obj.offset) for obj in modelParts] )
				modelPane.dobjStringVar.set( title )
			else:
				modelPane.dobjStringVar.set( 'Multiple Parts Selected' )
		else: # Multiple DObjs available, but only one is selected
			selectedPart = modelPane.displayObjects[modelPane.partIndex]
			modelPane.dobjStringVar.set( '{}  ({} of {})'.format(selectedPart.name, modelPane.partIndex+1, len(modelPane.displayObjects)) )

		# Update displayed properties and connections for color input widgets and the Properties tab
		self.connectMaterialColorControls()
		self.populateTexPropertiesTab()

		# Check the box for the appropriate DObj in the render options window if it's open.
		# This feature is only used when this method is called from the Next/Prev. buttons.
		if updateOptionsWindow and self.renderOptionsWindowIsOpen():
			# selectedObj = modelPane.displayObjects[modelPane.partIndex]
			# checkboxStates = self.renderOptionsWindow.checkboxStates

			# for dobjOffset, checkboxVar in checkboxStates.items():
			# 	if dobjOffset == selectedObj.offset:
			# 		checkboxVar.set( True )
			# 	else:
			# 		checkboxVar.set( False )
			# if self.renderOptionsWindowIsOpen():
			self.renderOptionsWindow.repopulate()

	def refreshRender( self, event=None ):

		""" Reload the currently rendered objects to reflect updates to structure properties. """
		
		modelPane = self.modelPropertiesPane.interior
		self.renderDobj( modelPane.currentRenders, updateCamera=False )

	def findRelatedParts( self, targetDObj ):

		""" Searches a model skeleton to find a few model parts that 
			are related to (close proximity to) the given DObj. Also 
			determines which model parts are high or low poly, which 
			are then included or filtered out, based on option toggle. """

		# Get a list of all potentially related display objects
		modelPartOffsets = targetDObj.getSiblings()
		modelParts = [ self.file.structs[o] for o in modelPartOffsets ] # These should all be initialized through the .getSiblings method

		# Check what bones the given DObj is attached to or influenced by
		targetJoints = set( targetDObj.getBoneAttachments() )
		targetBones = set([ bone for bone in targetDObj.skeleton.values() if bone.joint.offset in targetJoints ])

		# Scan the skeleton for parts attached to or near the target bones
		relatedParts = set()
		for part in modelParts:
			boneAttachments = part.getBoneAttachments()

			# Check if this part attaches to the same target bone(s)
			if targetJoints.intersection( boneAttachments ):
				relatedParts.add( part.offset )

			# If related, extend the related parts set to include the parent & children of the target bone(s)
			for bone in targetBones:
				if bone.parent in boneAttachments:
					relatedParts.add( part.offset )
				elif set( bone.children ) & set( boneAttachments ):
					relatedParts.add( part.offset )

		return relatedParts
	
	def hideBasedOnPoly( self, part ):

		""" Determines whether a model part should be visible or hidden, 
			based on whether it's a high or low-poly part. """

		modelPane = self.modelPropertiesPane.interior
		showHighPoly = modelPane.showHighPoly.get()

		# Return False if unable to check or there are no high/low-poly variations
		if not modelPane.highPolyIds:
			return False

		# Skip low-poly parts if they should be hidden
		if showHighPoly and part.id in modelPane.lowPolyIds:
			return True

		# Skip high-poly parts if they should be hidden
		elif not showHighPoly and part.id in modelPane.highPolyIds:
			return True
		
		return False

	def showDisplayOptions( self, event=None ):

		""" Called by the gear icon to the right of the render window. 
			Used to toggle various options for what is to be rendered. """

		modelPane = self.modelPropertiesPane.interior
		self.renderOptionsWindow = ModelTabRenderOptionsWindow( self, modelPane )

	def renderOptionsWindowIsOpen( self ):

		""" If self.renderOptionsWindow is None, the window hasn't 
			been created once yet for this texture editor tab. There's 
			also an occasional occurance where the window has been created 
			but it has lost the .window property after being created. 
			Unsure how or why it happens, but it can! """

		try:
			if self.renderOptionsWindow.window.winfo_exists():
				return True
		except:
			pass

		return False

	def toggleHideJoint( self ):

		""" Toggles the bit flag for 'Hidden' for each parent Joint Struct 
			of the model parts currently selected for rendering. """

		# Check the GUI for the bool determining whether to hide the joint
		modelPane = self.modelPropertiesPane.interior
		hideJoint = modelPane.hideJointChkBtn.var.get()
		modifiedJoints = [] # Tracks which joint flags we've already updated, to reduce redundancy

		# Iterate over the display objects of this texture, get their parent joint objects, and modify their flag
		for displayObj in modelPane.currentRenders:
			parentJointOffsets = displayObj.getParents()

			for parentStructOffset in parentJointOffsets:
				jointStruct = self.file.initSpecificStruct( hsdStructures.JointObjDesc, parentStructOffset )
				if jointStruct and parentStructOffset not in modifiedJoints:
					# Change the bit within the struct values and file data, and record that the change was made
					self.file.updateFlag( jointStruct, 1, 4, hideJoint )
					
					modifiedJoints.append( parentStructOffset )

		if hideJoint:
			printStatus( 'Set the "Hidden" flag on {} Joint objects'.format(len(modifiedJoints)) )
		else:
			printStatus( 'Cleared the "Hidden" flag on {} Joint objects'.format(len(modifiedJoints)) )

	def toggleDisplayListRendering( self ):

		""" Toggles the defined length of the display lists associated 
			with the model parts currently selected for rendering. """

		# Get the bool determining whether to clear the DObj render lists from the GUI
		clearDisplayList = self.modelPropertiesPane.interior.polyDisableChkBtn.var.get()
		structsUpdated = 0

		for displayObj in self.modelPropertiesPane.interior.currentRenders:
			# Get the polygon object of this display object, as well as its siblings
			polygonObjOffset = displayObj.getValues( 'Polygon_Object_Pointer' )
			polygonObj = self.file.initSpecificStruct( hsdStructures.PolygonObjDesc, polygonObjOffset, displayObj.offset )
			polygonSiblingObjs = [ self.file.structs[o] for o in polygonObj.getSiblings() ] # These should all be initialized through the .getSiblings method

			# Process this object and its siblings
			for polygonStruct in polygonSiblingObjs:
				# Get info on this polygon object's display list
				displayListLength, displayListPointer = polygonStruct.getValues()[4:6]
				determinedListLength = self.file.getStructLength( displayListPointer ) / 0x20

				# Check the current display list length (when disabling) to make sure the value can be properly switched back
				if clearDisplayList and displayListLength != determinedListLength:
					msg( 'Warning! The display list length of ' + polygonStruct.name + ' was not the expected calculated value; '
						'The current value is {}, while it was expected to be {}. '.format( displayListLength, determinedListLength ) + \
						"This means if you want to be able to restore this value later, you'll need to write the current value "
						'down, so you can restore it manually in the Structural Analysis tab.', 'Unexpected Display List Length' )

				if clearDisplayList:
					self.file.updateStructValue( polygonStruct, 4, 0 )
				else:
					self.file.updateStructValue( polygonStruct, 4, determinedListLength )
				structsUpdated += 1
		
		if clearDisplayList:
			printStatus( 'The display lists of {} Polygon structs have been cleared'.format(structsUpdated) )
		else:
			printStatus( 'The display lists of {} Polygon structs have been reset to defaults'.format(structsUpdated) )

	def opacityEntryUpdated( self, newValue ):

		""" Handles events from the transparency Entry widget, when its value is changed. 
			This just validates the input, and updates the value on the slider. 
			newValue will initially be a string of a float. """

		# Validate the input and convert it from a string to a decimal integer
		try:
			newValue = float( newValue.replace( '%', '' ) )
		except:
			if newValue == '':
				newValue = 0
			else:
				return False
		if newValue < 0 or newValue > 100:
			return False

		# Set the slider to the current value
		newValue = newValue / 10
		self.modelPropertiesPane.interior.opacityScale.set( newValue )

		return True

	def opacityScaleUpdated( self, newValue ):

		""" Handles events from the transparency Slider widget, when its value is changed. 
			The slider value ranges between 0 and 10, (so that it's intervals when clicking 
			in the trough jump a decent amount). The purpose of this function is just to update 
			the value in the Entry widget. 'newValue' will initially be a string of a float. """

		newValue = round( float(newValue), 2 )
		modelPane = self.modelPropertiesPane.interior

		# If this is not the Entry widget causing a change in the value, update it too
		if globalData.gui.root.focus_get() != modelPane.opacityEntry:
			# Set the entry widget to the current value (temporarily disable the validation function, so it's not called)
			modelPane.opacityEntry.configure( validate='none')
			modelPane.opacityEntry.delete( 0, 'end' )
			modelPane.opacityEntry.insert( 0, str(newValue*10) + '%' )
			modelPane.opacityEntry.configure( validate='key' )

	def setModelTransparencyLevel( self ):

		""" Called by the "Set" button under the Model tab's Transparency Control interface. 
			This will update the transparency for all parts currently selected for rendering. """

		# Get the opacity currently set in the GUI
		modelPane = self.modelPropertiesPane.interior
		opacityValue = modelPane.opacityScale.get() / 10

		# Update the transparency value, and set required flags for this in the Material Struct
		matStructsModified = 0
		for dobj in modelPane.currentRenders:
			materialStruct = dobj.MObj
			if not materialStruct:
				continue

			# Initialize the material color struct
			matColorsOffset = materialStruct.getValues( 'Material_Colors_Pointer' )
			matColorsStruct = self.file.initSpecificStruct( hsdStructures.MaterialColorObjDesc, matColorsOffset, materialStruct.offset )

			if matColorsStruct: # If the Material Struct doesn't have its colors struct, we don't need to worry about modifying it
				# Change the transparency value within the struct values and file data, and record that the change was made
				self.file.updateStructValue( matColorsStruct, -2, opacityValue )

				if opacityValue < 1.0: # Set the required flags (RENDER_NO_ZUPDATE and RENDER_XLU; i.e. bits 29 and 30)
					self.file.updateFlag( materialStruct, 1, 29, True ) # RENDER_NO_ZUPDATE
					self.file.updateFlag( materialStruct, 1, 30, True ) # RENDER_XLU
					matStructsModified += 1
				# else:
				# 	self.file.updateFlag( materialStruct, 1, 29, False )
				# 	self.file.updateFlag( materialStruct, 1, 30, False )

		modifiedJoints = [] # Tracks which joint flags we've already updated, to avoid redundancy
		if opacityValue < 1.0: # Set flags required for this in the Joint Struct(s)

			# Iterate over the display objects of this texture, get their parent joint objects, and modify their flag
			for displayObj in modelPane.currentRenders:
				parentJointOffsets = displayObj.getParents()

				for parentStructOffset in parentJointOffsets:
					jointStruct = self.file.initSpecificStruct( hsdStructures.JointObjDesc, parentStructOffset )
					if jointStruct and parentStructOffset not in modifiedJoints:
						# Change the bit within the struct values and file data, and record that the change was made
						self.file.updateFlag( jointStruct, 1, 19, True ) # XLU
						#self.file.updateFlag( jointStruct, 1, 28, True ) # ROOT_OPA
						self.file.updateFlag( jointStruct, 1, 29, True ) # ROOT_XLU
						
						modifiedJoints.append( parentStructOffset )
		
		printStatus( 'Transparency flags updated across {} material struct(s) and {} joint struct(s)'.format(matStructsModified, len(modifiedJoints)) )

		# Update the current model render to show the new opacity
		self.refreshRender()

	def populateTexPropertiesTab( self, iid=None ):

		""" Populates the Properties tab of the DAT Texture Tree interface. At this point, the pane has already been cleared. """

		# Check if already populated
		propertiesPane = self.texturePropertiesPane.interior
		# if propertiesPane.winfo_children():
		# 	return
		
		# Clear current contents
		self.texturePropertiesPane.clear()
		self.texturePropertiesPane.flagWidgets = [] # Useful for the Flag Decoder to more easily find widgets that need updating

		# Ensure there is an iid, or return (failsafe; there should be one)
		if not iid:
			iid = self.datTextureTree.selection()
			if not iid: return
		iid = iid[-1] # Selects the lowest position item selected in the treeview if multiple items are selected.

		self.collectStructs( iid )

		texStructs = self.modelPropertiesPane.interior.textureStructs
		#matStructs = self.modelPropertiesPane.interior.materialStructs
		matStructs = [ tobj.MObj for tobj in self.modelPropertiesPane.interior.currentRenders ]
		pixStructs = [] # Pixel Processing structures
		wraplength = propertiesPane.winfo_width() - 20
		vertPadding = 10

		# Make sure there are Texture Structs to edit
		if not texStructs:
			noTexStructText = ( 'No Texture Structs found; there are no editable properties. If this texture is part of '
								'a material animation, find the default texture for that animation and edit that instead.' )
			ttk.Label( propertiesPane, text=noTexStructText, wraplength=wraplength ).pack( pady=vertPadding*2 )
			return

		# Collect offsets that we'll need for the HexEditEntries.
		# Also, get the flags data, and check if they're the same across all tex structs for this texture.
		matFlagOffsets = [ matStruct.offset+4 for matStruct in matStructs ]
		texFlagFieldOffsets = []
		pixelProcFlagOffsets = []
		blendingOffsets = []
		wrapModeSoffsets = []
		wrapModeToffsets = []
		reapeatSoffsets = []
		reapeatToffsets = []
		matFlagsData = set()
		texFlagsData = set()
		pixFlagsData = set()
		blendingData = set()
		wrapSData = set()
		wrapTData = set()
		repeatSData = set()
		repeatTData = set()

		# Populate the above lists with the actual hex data from the file
		for texStruct in texStructs:
			texFlagFieldOffsets.append( texStruct.offset + 0x40 )
			wrapModeSoffsets.append( texStruct.offset + 0x34 )
			wrapModeToffsets.append( texStruct.offset + 0x38 )
			reapeatSoffsets.append( texStruct.offset + 0x3C )
			reapeatToffsets.append( texStruct.offset + 0x3D )

			texFlagsData.add( hexlify(texStruct.data[0x40:0x44]) )
			wrapSData.add( hexlify(texStruct.data[0x34:0x38]) )
			wrapTData.add( hexlify(texStruct.data[0x38:0x3C]) )
			repeatSData.add( hexlify(texStruct.data[0x3C:0x3D]) )
			repeatTData.add( hexlify(texStruct.data[0x3D:0x3E]) )
		for matStructure in matStructs:
			matFlagsData.add( hexlify(matStructure.data[0x4:0x8]) )

			# Check if there's a valid pointer to a Pixel Proc. structure, and get flags from it if there is
			if matStructure.offset + 0x14 in self.file.pointerOffsets:
				pixelProcStructOffset = matStructure.getValues()[-1]
				pixProcStruct = self.file.initSpecificStruct( hsdStructures.PixelProcObjDesc, pixelProcStructOffset, matStructure.offset )

				if pixProcStruct:
					pixStructs.append( pixProcStruct )
					pixelProcFlagOffsets.append( pixelProcStructOffset )
					pixFlagsData.add( hexlify(self.file.getData(pixelProcStructOffset, 1)) )

					blendingOffsets.append( pixelProcStructOffset + 4 )
					blendingData.add( ord(self.file.getData(pixelProcStructOffset+4, 1)) )
		displayDifferingDataWarning = False

		# Describe the number of Texture Structs found
		if len( texStructs ) == 1:
			texCountLabel = ttk.Label( propertiesPane, text='These controls will edit 1 set of structures.', wraplength=wraplength )
		else:
			texCountLabelText = 'These controls will edit {} sets of structures.\nTo edit individual structs, use the Structural Analysis tab.'.format( len(texStructs) )
			texCountLabel = ttk.Label( propertiesPane, text=texCountLabelText, wraplength=wraplength )
		texCountLabel.pack( pady=(vertPadding*2, 0) )

		ttk.Separator( propertiesPane, orient='horizontal' ).pack( fill='x', padx=24, pady=(vertPadding*2, 0) )
		flagsFrame = Tk.Frame( propertiesPane )
		
		if len( pixFlagsData ) > 0:
			# Add blending options
			ttk.Label( flagsFrame, text='Blending Mode:' ).grid( column=0, row=0, sticky='e' )
			if len( blendingData ) > 1: # Add a 2 px border around the widget using a Frame (the widget itself doesn't support a border)
				optionMenuBorderFrame = Tk.Frame( flagsFrame, background='orange' )
				blendingMenu = EnumOptionMenu( optionMenuBorderFrame, pixStructs, 4 )
				blendingMenu.pack( padx=2, pady=2 )
				optionMenuBorderFrame.grid( column=1, row=0, columnspan=2, padx=7 )
				displayDifferingDataWarning = True
			else: # Just one struct
				blendingMenu = EnumOptionMenu( flagsFrame, pixStructs[0], 4 )
				blendingMenu.grid( column=1, row=0, columnspan=2, padx=7 )

			# Add widgets for the Pixel Processing Flags label, hex edit Entry, and Flags 'Decode' button
			ttk.Label( flagsFrame, text='Pixel Processing Flags:' ).grid( column=0, row=1, sticky='e' )
			hexEntry = HexEditEntry( flagsFrame, self.file, pixelProcFlagOffsets, 1, 'B', 'Pixel Processing Flags' )
			hexEntry.insert( 0, next(iter(pixFlagsData)).upper() )
			hexEntry.grid( column=1, row=1, padx=7, pady=1 )
			self.texturePropertiesPane.flagWidgets.append( hexEntry )
			if len( pixFlagsData ) > 1:
				hexEntry['highlightbackground'] = 'orange'
				hexEntry['highlightthickness'] = 2
				displayDifferingDataWarning = True
			flagsLabel = ttk.Label( flagsFrame, text='Decode', foreground='#00F', cursor='hand2' )
			flagsLabel.grid( column=2, row=1, pady=0 )
			flagsLabel.bind( '<1>', lambda e, s=pixStructs[0], fO=pixelProcFlagOffsets: FlagDecoder(s, fO, 0) )
		else:
			ttk.Label( flagsFrame, text='Pixel Processing is not used on this texture.', wraplength=wraplength ).grid( column=0, row=0, columnspan=3, pady=(0, vertPadding) )

		# Add widgets for the Render Mode Flags label, hex edit Entry, and Flags 'Decode' button
		ttk.Label( flagsFrame, text='Material Flags:' ).grid( column=0, row=2, sticky='e' )
		hexEntry = HexEditEntry( flagsFrame, self.file, matFlagOffsets, 4, 'I', 'Material Flags' )
		hexEntry.grid( column=1, row=2, padx=7, pady=1 )
		self.texturePropertiesPane.flagWidgets.append( hexEntry )
		if len( matFlagsData ) == 0:
			hexEntry['state'] = 'disabled'
		else:
			hexEntry.insert( 0, next(iter(matFlagsData)).upper() )
			flagsLabel = ttk.Label( flagsFrame, text='Decode', foreground='#00F', cursor='hand2' )
			flagsLabel.grid( column=2, row=2, pady=0 )
			flagsLabel.bind( '<1>', lambda e, s=matStructs[0], fO=matFlagOffsets: FlagDecoder(s, fO, 1) )
		if len( matFlagsData ) > 1:
			hexEntry['highlightbackground'] = 'orange'
			hexEntry['highlightthickness'] = 2
			displayDifferingDataWarning = True

		# Add widgets for the Texture Flags label, hex edit Entry, and Flags 'Decode' button
		ttk.Label( flagsFrame, text='Texture Flags:' ).grid( column=0, row=3, sticky='e' )
		hexEntry = HexEditEntry( flagsFrame, self.file, texFlagFieldOffsets, 4, 'I', 'Texture Flags' )
		hexEntry.grid( column=1, row=3, padx=7, pady=1 )
		self.texturePropertiesPane.flagWidgets.append( hexEntry )
		if len( texFlagsData ) == 0:
			hexEntry['state'] = 'disabled'
		else:
			hexEntry.insert( 0, next(iter(texFlagsData)).upper() )
			flagsLabel = ttk.Label( flagsFrame, text='Decode', foreground='#00F', cursor='hand2' )
			flagsLabel.grid( column=2, row=3 )
			flagsLabel.bind( '<1>', lambda e, s=texStructs[0], fO=texFlagFieldOffsets: FlagDecoder(s, fO, 18) )
		if len( texFlagsData ) > 1:
			hexEntry['highlightbackground'] = 'orange'
			hexEntry['highlightthickness'] = 2
			displayDifferingDataWarning = True

		flagsFrame.pack( pady=(vertPadding*2, 0) )

		# Add Wrap Mode and Repeat Mode
		modesFrame = Tk.Frame( propertiesPane )
		wrapOptions = OrderedDict( [('Clamp', 0), ('Repeat', 1), ('Mirrored', 2), ('Reserved', 3)] )

		# Wrap Mode S
		ttk.Label( modesFrame, text='Wrap Mode S:' ).grid( column=0, row=0, sticky='e' )
		defaultWrapS = int( next(iter(wrapSData)), 16 ) # Gets one of the hex values collected from the struct(s), and then converts it to an int
		if len( wrapSData ) > 1:
			frameBorder = Tk.Frame( modesFrame, background='orange' ) # The optionmenu widget doesn't actually support a border :/
			dropdown = HexEditDropdown( frameBorder, self.file, wrapModeSoffsets, 4, 'I', 'Wrap Mode S', wrapOptions, defaultWrapS )
			dropdown.pack( padx=2, pady=2 )
			frameBorder.grid( column=1, row=0, padx=7, pady=1 )
			displayDifferingDataWarning = True
		else:
			dropdown = HexEditDropdown( modesFrame, self.file, wrapModeSoffsets, 4, 'I', 'Wrap Mode S', wrapOptions, defaultWrapS )
			dropdown.grid( column=1, row=0, padx=7, pady=1 )

		# Wrap Mode T
		ttk.Label( modesFrame, text='Wrap Mode T:' ).grid( column=0, row=1, sticky='e' )
		defaultWrapT = int( next(iter(wrapTData)), 16 ) # Gets one of the hex values collected from the struct(s), and then converts it to an int
		if len( wrapTData ) > 1:
			frameBorder = Tk.Frame( modesFrame, background='orange' ) # The optionmenu widget doesn't actually support a border :/
			dropdown = HexEditDropdown( frameBorder, self.file, wrapModeToffsets, 4, 'I', 'Wrap Mode T', wrapOptions, defaultWrapT )
			dropdown.pack( padx=2, pady=2 )
			frameBorder.grid( column=1, row=1, padx=7, pady=1 )
			displayDifferingDataWarning = True
		else:
			dropdown = HexEditDropdown( modesFrame, self.file, wrapModeToffsets, 4, 'I', 'Wrap Mode T', wrapOptions, defaultWrapT )
			dropdown.grid( column=1, row=1, padx=7, pady=1 )

		# Repeat Mode S
		ttk.Label( modesFrame, text='Repeat Mode S:' ).grid( column=2, row=0, sticky='e', padx=(7, 0) )
		hexEntry = HexEditEntry( modesFrame, self.file, reapeatSoffsets, 1, '?', 'Repeat Mode S' )
		hexEntry.insert( 0, next(iter(repeatSData)).upper() )
		hexEntry.grid( column=3, row=0, padx=7, pady=1 )
		if len( repeatSData ) > 1:
			hexEntry['highlightbackground'] = 'orange'
			hexEntry['highlightthickness'] = 2
			displayDifferingDataWarning = True

		# Repeat Mode T
		ttk.Label( modesFrame, text='Repeat Mode T:' ).grid( column=2, row=1, sticky='e', padx=(7, 0) )
		hexEntry = HexEditEntry( modesFrame, self.file, reapeatToffsets, 1, '?', 'Repeat Mode T' )
		hexEntry.insert( 0, next(iter(repeatTData)).upper() )
		hexEntry.grid( column=3, row=1, padx=7, pady=1 )
		if len( repeatTData ) > 1:
			hexEntry['highlightbackground'] = 'orange'
			hexEntry['highlightthickness'] = 2
			displayDifferingDataWarning = True

		modesFrame.pack( pady=(vertPadding, 0) )

		if displayDifferingDataWarning:
			differingDataLabelText = (  'Warning! Values with an orange border are different across the multiple structures '
										'that these controls will modify; you may want to exercise caution when changing them '
										'here, which would make them all the same.' )
			differingDataLabel = ttk.Label( propertiesPane, text=differingDataLabelText, wraplength=wraplength )
			differingDataLabel.pack( pady=(vertPadding*2, 0) )

		# Get the texture struct
		imageDataOffset = int( iid )
		texture = self.file.structs[imageDataOffset]

		# Add alternative texture sizes
		ttk.Separator( propertiesPane, orient='horizontal' ).pack( fill='x', padx=24, pady=(vertPadding*2, 0) )
		ttk.Label( propertiesPane, text='Alternative Texture Sizes:' ).pack( pady=(vertPadding*2, 0) )
		altImageSizesFrame = Tk.Frame( propertiesPane )
		sizesDict = OrderedDict()
		for i, imageType in enumerate( ( 0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 14 ) ):
			if imageType == texture.imageType:
				continue
			thisSize = hsdStructures.ImageDataBlock.getDataLength( texture.width, texture.height, imageType )
			if thisSize not in sizesDict:
				sizesDict[thisSize] = [ userFriendlyFormatList[i] ]
			else:
				sizesDict[thisSize].append( userFriendlyFormatList[i] )
		row = 0
		for size, formatList in sizesDict.items():
			ttk.Label( altImageSizesFrame, text='  /  '.join( formatList ) ).grid( column=0, row=row, sticky='w' )
			ttk.Label( altImageSizesFrame, text=uHex( size ) ).grid( column=1, row=row, sticky='w', padx=(12, 0) )
			row += 1
		altImageSizesFrame.pack()

	def summonContextMenu( self, event ):
		contextMenu = TexturesContextMenu( globalData.gui.root, self, tearoff=False )
		contextMenu.repopulate()
		contextMenu.post( event.x_root, event.y_root )

	def adjustTextureFilters( self, event ):
		self.filtersWindow = TextureFiltersWindow( self )

	def updateCanvasGrid( self, saveChange=True ):

		"""	Shows/hides the grid behind textures displayed in the DAT Texture Tree's 'Image' tab. """

		if globalData.boolSettings['showCanvasGrid'].get():
			self.textureDisplayFrame.config( highlightbackground='#c0c0c0', highlightcolor='#c0c0c0', highlightthickness=1, borderwidth=0, relief='flat' )

			canvasWidth = int( self.textureDisplay['width'] )
			canvasHeight = int( self.textureDisplay['height'] )
			gridImage = globalData.gui.imageBank( 'canvasGrid' )

			# Tile the image across the canvas
			for y in range( 0, canvasHeight + 20, 20 ): # start, stop, step
				for x in range( 0, canvasWidth + 20, 20 ):
					self.textureDisplay.create_image( x, y, image=gridImage, tags='grid' )
			
			# Make sure any texture present stays above the grid
			if len( self.textureDisplay.find_withtag('texture') ) != 0: 
				self.textureDisplay.tag_lower('grid', 'texture')

		else:
			# Remove the grid
			for item in self.textureDisplay.find_withtag( 'grid' ):
				self.textureDisplay.delete( item )
			self.textureDisplayFrame.config( highlightbackground='#c0c0c0', highlightcolor='#c0c0c0', highlightthickness=0, borderwidth=0, relief='flat' )

		if saveChange: # Update the current selection in the settings file
			globalData.saveProgramSettings()
			
	def updateCanvasTextureBoundary( self, saveChange=True ):
		
		""" Shows or hides the border around textures. """

		if globalData.boolSettings['showTextureBoundary'].get():
			coords = self.textureDisplay.bbox( 'texture' ) # "bounding box" gets the coordinates of the item(s)

			if coords:
				# Expand the north/west borders by 1px, so they're not over the image
				x1, y1, x2, y2 = coords
				self.textureDisplay.create_rectangle( x1 - 1, y1 - 1, x2, y2, outline='blue', tags='border' )
			else:
				self.textureDisplay.delete( self.textureDisplay.find_withtag('border') )
		else:
			self.textureDisplay.delete( self.textureDisplay.find_withtag('border') )

		if saveChange: # Update the current selection in the settings file
			globalData.saveProgramSettings()

	def cyclePaletteCanvasColor( self, event ):

		""" Feature to cycle the background color of the palette canvas through three 
			different colors, for the purpose of better color identification in cases 
			of the alpha channel being used (i.e. when the colors have transparency). """

		if self.paletteCanvas["background"] == 'white':
			# Cycle to gray
			self.paletteCanvas.configure( background='#7F7F7F' )

		elif self.paletteCanvas["background"] == '#7F7F7F':
			# Cycle to black
			self.paletteCanvas.configure( background='black' )
			for item in self.paletteCanvas.find_withtag( 'descriptors' ):
				self.paletteCanvas.itemconfig( item, fill='white' )

		else:
			# Cycle to white
			self.paletteCanvas.configure( background='white' )
			for item in self.paletteCanvas.find_withtag( 'descriptors' ):
				self.paletteCanvas.itemconfig( item, fill='black' )

	def getMipmapLevel( self, iid ):

		if self.datTextureTree.exists( iid ) and 'mipmap' in self.datTextureTree.item( iid, 'tags' ):
			mipLevel = 0

			if self.datTextureTree.parent( iid ): # This item is a child of a parent mipmap texture

				for level in self.datTextureTree.get_children( self.datTextureTree.parent(iid) ):
					mipLevel += 1
					if level == iid:
						break
		else:
			mipLevel = -1

		return mipLevel

	def replaceSingleTexture( self, newImage, imageDataOffset ):

		""" Attempts to replace a texture in the file with the given PIL image. 
			If needed, asks the user if they'd like to resize the given texture, 
			or create more space for it in the file. """

		# Get the texture object
		texture = self.file.structs.get( imageDataOffset )
		if not texture: # Failsafe; unlikely
			printStatus( 'Unable to import; the selected texture object could not be loaded', error=True )
			return

		# Check if there's enough space for the new texture
		if ( texture.width, texture.height ) != newImage.size:
			origImageDataLength = texture.getDataLength( texture.width, texture.height, texture.imageType )
			newImageDataLength = texture.getDataLength( newImage.size[0], newImage.size[1], texture.imageType )

			if tkMessageBox.askyesno( 'Resize texture?', "The dimensions of the texture you're importing don't "
					"match those of the texture you've selected to replace."
					"\n\nThe texture you've selected to replace is {}x{}."
					"\nThe texture you've selected to import is {}x{}."
					"\n\nWould you like to resize the texture you're importing to match "
					"the selected texture?".format(texture.width, texture.height, newImage.size[0], newImage.size[1])
				):
				newImage = newImage.resize( (texture.width, texture.height), resample=globalData.checkSetting('resampleFilter') )

			elif newImageDataLength > origImageDataLength: # User declined the resize offering above and more space is needed
				# lengthDiff = newImageDataLength - origImageDataLength
				# if not tkMessageBox.askyesno( 'Expand data space?', "The texture you're importing requires more "
				# 		"space in the file than what's available. Would you like to expand the space in the file "
				# 		"for this texture? This will increase the file size by {} ({:,} bytes).".format(humansize(lengthDiff), lengthDiff)
				# 	):
				# 	printStatus( 'Operation aborted', warning=True )
				# 	return
				printStatus( "The given image's dimensions are too large", error=True )
				msg( "The texture you're importing requires more space in "
					"the file than what's available. ", 'Not enough space' )
				return

		# Get the disc file and save the image data to it
		try:
			returnCode, origLimit, newLimit = self.file.setTexture( imageDataOffset, newImage, texture )
		except Exception as err:
			returnCode = -1
			msg( 'An error occurred importing the texture; {}'.format(err), 'Import Error', error=True )

		# Update the new texture's icon in the GUI
		self.renderTextureData( texture.offset, problem=returnCode )
		self.drawTextureToMainDisplay( texture.offset )

		# Give a warning or success message
		if returnCode == -1:
			printStatus( 'Error: {}'.format(err), error=True )
		elif returnCode == 0:
			printStatus( 'Texture imported successfully', success=True )
		elif returnCode == 1:
			printStatus( 'Unable to import; palette information could not be found for the selected texture(s)', error=True )
		# elif returnCode == 2: # Failsafe; not possible?
		# 	printStatus( "The given image's dimensions are too large", error=True )
		# 	msg( 'The given image is too large. The banner '
		# 		'image should be 96x32 pixels.', 'Invalid Dimensions', warning=True )
		# elif returnCode == 3:
		else: #todo: clean up
			printStatus( 'Unable to import; an unexpected error occurred '
				'(return code: {}, l1: 0x{:X}, l2: 0x{:X})'.format(returnCode, origLimit, newLimit), error=True )
			# msg( 'Unable to import; an unexpected error occurred '
			# 	'(return code: {}, l1: 0x{:X}, l2: 0x{:X})'.format(returnCode, origLimit, newLimit), error=True )

	def _replaceTextures( self, textureObjects, newImage, completedEncodings, selectedIid, allowResizing=False ):
		
		""" A helper function to self.replaceMultipleTextures(). """

		successCount = 0

		for texture in textureObjects:
			returnCode = -1

			try:
				# Check if we've already encoded this data
				encodingSignature = ( texture.width, texture.height, texture.imageType )
				preEncodedTexture = completedEncodings.get( encodingSignature )

				# Save the new texture to the file
				if preEncodedTexture:
					returnCode = self.file.setPreEncodedTexture( texture.offset, preEncodedTexture )[0]
				elif allowResizing:
					resizedImage = newImage.resize( (texture.width, texture.height), resample=globalData.checkSetting('resampleFilter') )
					returnCode = self.file.setTexture( texture.offset, resizedImage, texture )[0]
				else:
					returnCode = self.file.setTexture( texture.offset, newImage, texture )[0]

			except Exception as err:
				print( 'An error occurred importing the texture to 0x{:X}; {}'.format(0x20+texture.offset, err) )

			# Track successes and store completed encodings to avoid repeating work
			if returnCode == 0:
				if not preEncodedTexture:
					completedEncodings[encodingSignature] = texture
				successCount += 1

			# Update the new texture's icon and main image display in the GUI
			self.renderTextureData( texture.offset, problem=returnCode )
			if texture.offset == selectedIid:
				self.drawTextureToMainDisplay( texture.offset )

		return successCount

	def _expansionRequired( self, newImage, uniqueDims, texture ):

		""" Check if the imported texture (newImage) is larger than any of the selected textures. """
		
		newLength = texture.getDataLength( newImage.size[0], newImage.size[1], texture.imageType )

		for ( width, height, imageType ) in uniqueDims:
			origLength = texture.getDataLength( width, height, imageType )

			if newLength > origLength: # More space is needed
				return True
		else:
			# The loop above didn't break; no texture spaces are too small
			return False

	def replaceMultipleTextures( self, newImage, imageDataOffsets ):

		""" This will offer the user to resize the texture being imported if 
			it doesn't match all of the in-file texture dimensions exactly. """

		selectedTextureObjects = []
		structsNotFound = [] # Failsafe; not expected
		uniqueDims = set()
		completedEncodings = {} # Key=tuple(width, height, imageType, paletteType), value=(imageData, paletteData)
		successCount = 0
		
		# Collect the textures to be replaced, and number of unique texture dimensions
		for offset in imageDataOffsets:
			texture = self.file.structs.get( offset )

			if texture:
				selectedTextureObjects.append( texture )
				uniqueDims.add( (texture.width, texture.height, texture.imageType) )
			else:
				structsNotFound.append( offset )

		# Make sure at least one texture can be replaced
		if not selectedTextureObjects: # Failsafe; unlikely
			printStatus( 'Unable to import; the selected texture objects could not be loaded', error=True )
			missingStructs = [ uHex(offset) for offset in structsNotFound ]
			print( 'These structs could not be found or initialized in the file: {}'.format(missingStructs) )
			return

		# Warn the user if there are textures with differing dimensions
		if len( uniqueDims ) > 1:
			allowResize = tkMessageBox.askyesno( 'Resize texture?', "The dimensions of the textures you've "
				"selected to replace are not all the same. Would you like to resize the texture you're "
				"importing to match each selected texture?" )
				
			if allowResize:
				successCount += self._replaceTextures( selectedTextureObjects, newImage, completedEncodings, imageDataOffsets[0], allowResizing=True )
			
			elif self._expansionRequired( newImage, uniqueDims, texture ): # User declined the resize offering above and more space is needed
				# lengthDiff = newImageDataLength - origImageDataLength
				# if not tkMessageBox.askyesno( 'Expand data space?', "The texture you're importing requires more "
				# 		"space in the file than what's available. Would you like to expand the space in the file "
				# 		"for this texture? This will increase the file size by {} ({:,} bytes).".format(humansize(lengthDiff), lengthDiff)
				# 	):
				# 	printStatus( 'Operation aborted', warning=True )
				# 	return
				#printStatus( "The given image's dimensions are too large", error=True )

				# Create a list of textures that can be replaced
				textureObjects = []
				for texture in selectedTextureObjects:
					requiredSpace = texture.getDataLength( newImage.size[0], newImage.size[1], texture.imageType )
					existingSpace = texture.getDataLength( texture.width, texture.height, texture.imageType )
					
					if requiredSpace <= existingSpace:
						textureObjects.append( texture )
				
				if not textureObjects:
					# No imports can be completed
					printStatus( "The given image's dimensions are too large", error=True )
					msg( "The texture you're importing requires more space in the file than what's available "
						"for the textures you've selected.", 'Not enough space' )
					return
				else:
					# Some of the textures may be able to be imported, but not all. Warn the user!
					msg( "The texture you're importing requires more space in the file than what's available, "
						"and it cannot be used to replace some or all of "
						"the selected textures.", 'Not enough space' )

				# Replace all textures where there is enough space
				successCount += self._replaceTextures( textureObjects, newImage, completedEncodings, imageDataOffsets[0] )

			else: # No extra space needed; no special procedures needed
				successCount += self._replaceTextures( selectedTextureObjects, newImage, completedEncodings, imageDataOffsets[0] )

			# Give a warning or success message
			# if returnCode == 1:
			# 	msg( 'The given image does not have the correct dimensions. The banner image should be 96x32 pixels.', 'Invalid Dimensions', warning=True )
			# elif returnCode == 0:
			# 	printStatus( 'Banner texture imported', success=True )
		
		else: # All dimensions of the selected in-file textures are the same
			# Check if more file space is needed, and offer to resize the given texture if it is
			texture = selectedTextureObjects[0] # Any sample will do, since they're all the same
			if ( texture.width, texture.height ) != newImage.size:
				origImageDataLength = texture.getDataLength( texture.width, texture.height, texture.imageType )
				newImageDataLength = texture.getDataLength( newImage.size[0], newImage.size[1], texture.imageType )

				if newImageDataLength > origImageDataLength:
					if tkMessageBox.askyesno( 'Resize texture?', "The dimensions of the texture you're "
						"importing don't match those of the textures you've selected to replace."
						"\n\nThe textures you've selected to replace are {}x{}.".format( texture.width, texture.height ) + \
						"\nThe texture you've selected to import is {}x{}.".format( newImage.size[0], newImage.size[1] ) + \
						"\n\nWould you like to resize the texture you're importing to match the selected textures?" ):
					
						newImage = newImage.resize( (texture.width, texture.height), resample=globalData.checkSetting('resampleFilter') )

					else: # Oh noes!

					# if _expansionRequired:
					# elif self._expansionRequired( newImage, uniqueDims, texture ): # User declined the resize offering above and more space is needed
					# 	# lengthDiff = newImageDataLength - origImageDataLength
					# 	# if not tkMessageBox.askyesno( 'Expand data space?', "The texture you're importing requires more "
					# 	# 		"space in the file than what's available. Would you like to expand the space in the file "
					# 	# 		"for this texture? This will increase the file size by {} ({:,} bytes).".format(humansize(lengthDiff), lengthDiff)
					# 	# 	):
					# 	# 	printStatus( 'Operation aborted', warning=True )
					# 	# 	return

						printStatus( "The given image's dimensions are too large", error=True )
						msg( "The texture you're importing requires more "
							"space in the file than what's available. ", 'Not enough space' )
						return
		
			# Save the image data to the disc file
			successCount += self._replaceTextures( selectedTextureObjects, newImage, completedEncodings, imageDataOffsets[0] )
			
		# Update the program's status bar
		if len( imageDataOffsets ) == successCount:
			printStatus( 'All selected textures replaced successfully', success=True )
		elif successCount == 0:
			printStatus( 'The selected textures could not be replaced', error=True )
		else:
			failCount = len( imageDataOffsets ) - successCount
			printStatus( '{} textures were replaced, however {} texture replacements failed'.format(successCount, failCount), warning=True )


class TexturesContextMenu( Tk.Menu, object ):

	def __init__( self, parent, texturesTab, tearoff=True, *args, **kwargs ):
		super( TexturesContextMenu, self ).__init__( parent, tearoff=tearoff, *args, **kwargs )
		self.open = False
		self.texturesTab = texturesTab

	def repopulate( self ):

		""" This method will be called every time the submenu is displayed. """

		# Clear all current population
		self.delete( 0, 'last' )
		self.lastItem = ''

		# Check if anything is currently selected
		self.iids = self.texturesTab.datTextureTree.selection() # Returns a tuple of iids, or an empty string if nothing is selected.
		self.selectionCount = len( self.iids )

		if self.iids:																								# Keyboard shortcuts:
			self.lastItem = self.iids[-1] # Selects the lowest position item selected in the treeview.
			self.add_command( label='Export Selected Texture(s)', underline=0, command=self.exportSelectedTextures )				# E
			self.add_command( label='Export All', underline=7, command=self.exportAllTextures )										# A
			self.add_command( label='Import Texture', underline=0, command=self.importTexture )										# I
			self.add_separator()
			#self.add_command( label='Blank Texture (Zero-out)', underline=0, command=blankTextures )								# B
			#self.add_command(label='Disable (Prevents Rendering)', underline=0, command=disableTextures )
			if self.selectionCount > 1:
				self.add_command( label='Copy Offsets to Clipboard', underline=0, command=self.textureOffsetToClipboard )			# C
				self.add_command( label='Copy Dolphin Hashes to Clipboard', underline=13, command=self.dolphinHashToClipboard )		# H
			else:
				#self.add_command( label='Show in Structural Analysis', underline=0, command=self.showTextureInStructAnalysisTab )	# S
				self.add_command( label='Copy Offset to Clipboard', underline=0, command=self.textureOffsetToClipboard )			# C
				self.add_command( label='Copy Dolphin Hash to Clipboard', underline=13, command=self.dolphinHashToClipboard )		# H
		else:
			self.add_command( label='Export All', underline=7, command=self.exportAllTextures )										# A

	def exportSelectedTextures( self ):
		if len( self.texturesTab.datTextureTree.get_children() ) == 0:
			msg( 'You need to first open a file that you would like to export textures from.'
				 '\n\n(If you have loaded a file, either there were no textures found, or '
				 'you have texture filters blocking your results.)' )
		else:
			exportMultipleTextures( self.texturesTab )

	def exportAllTextures( self ):
		if len( self.texturesTab.datTextureTree.get_children() ) == 0:
			msg( 'You need to first open a file that you would like to export textures from.'
				 '\n\n(If you have loaded a file, either there were no textures found, or '
				 'you have texture filters blocking your results.)' )
		else:
			exportMultipleTextures( self.texturesTab, exportAll=True )

	def importTexture( self ):

		""" Prompts the user to select a single external file to import, 
			and replaces the currently selected texture(s) in this game file. """

		# Prompt the user to import one texture
		imagePath = importSingleTexture( "Choose a texture file (PNG or TPL) to replace the currently selected texture(s)" )
		if not imagePath: # The above will return an empty string if the user canceled
			return ''
		
		# Load the texture as a PIL image
		try:
			newImage = Image.open( imagePath )
		except Exception as err:
			printStatus( 'Unable to open the texture due to an unrecognized error. Check the log for details', error=True )
			print( 'Unable to load image for preview text; {}'.format(err) )
			return

		if len( self.iids ) > 1:
			imageDataOffsets = [ int(iid) for iid in self.iids ]
			self.texturesTab.replaceMultipleTextures( newImage, imageDataOffsets )
		else: # Only replacing one texture (one texture selected)
			self.texturesTab.replaceSingleTexture( newImage, int(self.iids[0]) )

	def showTextureInStructAnalysisTab( self ):
		# Set the selected item in DAT Texture Tree, so that it's clear which image is being operated on
		self.texturesTab.datTextureTree.selection_set( self.lastItem )
		self.texturesTab.datTextureTree.focus( self.lastItem )

		# Make sure the current iid is the start of a structure (may not be in the case of particle effects)
		structOffset = int( self.lastItem )
		if not self.lastItem in self.texturesTab.file.structureOffsets:
			structOffset = self.texturesTab.file.getPointerOwner( structOffset, True )

		# Add the texture's data block instances to the tree and show them
		#showStructInStructuralAnalysis( structOffset )
		
		# Switch to the SA tab
		#Gui.mainTabFrame.select( Gui.savTab )

	def textureOffsetToClipboard( self ):
		self.texturesTab.datTextureTree.selection_set( self.iids ) 	# Highlights the item(s)
		self.texturesTab.datTextureTree.focus( self.iids[0] ) 		# Sets keyboard focus to the first item

		# Get the offsets of all of the items selected
		offsets = []
		for iid in self.iids:
			offsets.append( uHex(int(iid)) )

		copyToClipboard( ', '.join(offsets) )

	def dolphinHashToClipboard( self ):
		self.texturesTab.datTextureTree.selection_set( self.iids ) 	# Highlights the item(s)
		self.texturesTab.datTextureTree.focus( self.iids[0] ) 		# Sets keyboard focus to the first item

		# Get the hashes of all of the items selected
		hashedFileNames = []
		for iid in self.iids:
			imageDataOffset = int( iid )
			texture = self.texturesTab.file.structs.get( imageDataOffset )
			mipLevel = self.texturesTab.getMipmapLevel( iid )
			hashedFileNames.append( constructTextureFilename(texture, mipLevel) )

		copyToClipboard( ', '.join(hashedFileNames) )


class TextureFiltersWindow( BasicWindow ):

	def __init__( self, editorTab ):

		BasicWindow.__init__( self, globalData.gui.root, 'Texture Filters', offsets=(450, 200), unique=True )

		self.editorTab = editorTab
		imageFilters = editorTab.imageFilters

		ttk.Label(self.window, text='Only show textures that meet this criteria:').pack(padx=10, pady=4)

		widthTuple = imageFilters['widthFilter']
		row1 = Tk.Frame(self.window)
		ttk.Label(row1, text='Width: ').pack(side='left')
		self.widthComparator = Tk.StringVar()
		self.widthComparator.set( widthTuple[0] )
		Tk.OptionMenu(row1, self.widthComparator, '<', '<=', '=', '>', '>=').pack(side='left')
		self.widthValue = Tk.StringVar()
		self.widthValue.set( widthTuple[1] )
		Tk.Entry(row1, textvariable=self.widthValue, width=6).pack(side='left')
		row1.pack(padx=10, pady=4)

		heightTuple = imageFilters['heightFilter']
		row2 = Tk.Frame(self.window)
		ttk.Label(row2, text='Height: ').pack(side='left')
		self.heightComparator = Tk.StringVar()
		self.heightComparator.set( heightTuple[0] )
		Tk.OptionMenu(row2, self.heightComparator, '<', '<=', '=', '>', '>=').pack(side='left')
		self.heightValue = Tk.StringVar()
		self.heightValue.set( heightTuple[1] )
		Tk.Entry(row2, textvariable=self.heightValue, width=6).pack(side='left')
		row2.pack(padx=10, pady=4)

		aspectRatioTuple = imageFilters['aspectRatioFilter']
		row3 = Tk.Frame(self.window)
		ttk.Label(row3, text='Aspect Ratio: ').pack(side='left')
		self.aspectRatioComparator = Tk.StringVar()
		self.aspectRatioComparator.set( aspectRatioTuple[0] )
		Tk.OptionMenu(row3, self.aspectRatioComparator, '<', '<=', '=', '>', '>=').pack(side='left')
		self.aspectRatioValue = Tk.StringVar()
		self.aspectRatioValue.set( aspectRatioTuple[1] )
		Tk.Entry(row3, textvariable=self.aspectRatioValue, width=6).pack(side='left')
		row3.pack(padx=10, pady=4)

		imageTypeTuple = imageFilters['imageTypeFilter']
		row4 = Tk.Frame(self.window)
		ttk.Label(row4, text='Texture Type: ').pack(side='left')
		self.imageTypeComparator = Tk.StringVar()
		self.imageTypeComparator.set( imageTypeTuple[0] )
		Tk.OptionMenu(row4, self.imageTypeComparator, '<', '<=', '=', '>', '>=').pack(side='left')
		self.imageTypeValue = Tk.StringVar()
		self.imageTypeValue.set( imageTypeTuple[1] )
		Tk.Entry(row4, textvariable=self.imageTypeValue, width=6).pack(side='left')
		row4.pack(padx=10, pady=4)

		offsetTuple = imageFilters['offsetFilter']
		row5 = Tk.Frame(self.window)
		ttk.Label(row5, text='Offset: ').pack(side='left')
		self.offsetComparator = Tk.StringVar()
		self.offsetComparator.set( offsetTuple[0] )
		Tk.OptionMenu(row5, self.offsetComparator, '<', '<=', '=', '>', '>=').pack(side='left')
		self.offsetValue = Tk.StringVar()
		self.offsetValue.set( offsetTuple[1] )
		Tk.Entry(row5, textvariable=self.offsetValue, width=10).pack(side='left')
		row5.pack(padx=10, pady=4)

		# The buttons
		btnFrame = Tk.Frame(self.window)
		ttk.Button( btnFrame, text='Apply', command=self.apply ).pack( side='right', padx=5 )
		ttk.Button( btnFrame, text='Clear',command=self.clear ).pack( side='left', padx=5 )
		ttk.Button( btnFrame, text='Close', command=self.close ).pack( side='right', padx=5 )
		btnFrame.pack( pady=(5, 7) )

	def apply( self ):

		""" Update the image filters dictionary for the current tab and rescan the file. """

		imageFilters = self.editorTab.imageFilters
		unsavedSettings = []

		# For each setting, if the value is a number or blank, update the value and its comparitor in the program and settings file.
		width = self.widthValue.get().replace(',', '')
		if not isNaN(width) or width == '':
			imageFilters['widthFilter'] = ( self.widthComparator.get(), width )
		else: unsavedSettings.append( 'width' )
		height = self.heightValue.get().replace(',', '')
		if not isNaN(height) or height == '':
			imageFilters['heightFilter'] = ( self.heightComparator.get(), height )
		else: unsavedSettings.append( 'height' )

		aspectRatio = self.aspectRatioValue.get()
		try:
			# Make sure that the aspect ratio can be converted to a number.
			if ':' in aspectRatio:
				numerator, denomenator = aspectRatio.split(':')
				convertedAspectRatio = float(numerator) / float(denomenator)
			elif '/' in aspectRatio:
				numerator, denomenator = aspectRatio.split('/')
				convertedAspectRatio = float(numerator) / float(denomenator)
			elif aspectRatio != '': convertedAspectRatio = float(aspectRatio)

			if aspectRatio == '' or not isNaN( convertedAspectRatio ):	
				imageFilters['aspectRatioFilter'] = ( self.aspectRatioComparator.get(), aspectRatio )
			else: unsavedSettings.append( 'aspect ratio' )
		except:
			unsavedSettings.append( 'aspect ratio' )

		imageType = self.imageTypeValue.get().replace('_', '')
		if not isNaN(imageType) or imageType == '':
			imageFilters['imageTypeFilter'] = ( self.imageTypeComparator.get(), imageType ) # str(int()) is in case the value was in hex
		else: unsavedSettings.append( 'texture type' )
		offset = self.offsetValue.get().replace(',', '')
		if (validHex(offset) and not isNaN(int(offset,16))) or offset == '':
			imageFilters['offsetFilter'] = ( self.offsetComparator.get(), offset )
		else: unsavedSettings.append( 'offset' )

		if unsavedSettings:
			msg('The filters for ' + grammarfyList( unsavedSettings ) + ' could not set. The '
				'entries must be a number or left blank, with the exception of aspect ratio, '
				'which may be a number, fraction, float, or a ratio like "4:3".')
			self.lift()

		self.editorTab.clear()
		self.editorTab.populateTexEditorTab( useCache=True )

	def clear( self ):
		
		""" Sets all values back to default for the current tab and this window. """

		self.editorTab.imageFilters = {
			'widthFilter': ( '=', '' ),
			'heightFilter': ( '=', '' ),
			'aspectRatioFilter': ( '=', '' ),
			'imageTypeFilter': ( '=', '' ),
			'offsetFilter': ( '=', '' ),
		}

		self.widthComparator.set( '=' )
		self.widthValue.set( '' )
		self.heightComparator.set( '=' )
		self.heightValue.set( '' )
		self.aspectRatioComparator.set( '=' )
		self.aspectRatioValue.set( '' )
		self.imageTypeComparator.set( '=' )
		self.imageTypeValue.set( '' )
		self.offsetComparator.set( '=' )
		self.offsetValue.set( '' )


class ModelTabRenderOptionsWindow( BasicWindow ):

	stylesAdded = False

	def __init__( self, editorTab, modelPane ):

		# Create some custom styles for this some of this window's widgets
		if not self.stylesAdded:
			style = globalData.gui.style
			style.configure( 'Red.TCheckbutton', foreground='#EC7328' )
			style.configure( 'Blue.TCheckbutton', foreground='#698DCF' )
			style.configure( 'Red.TRadiobutton', foreground='#EC7328' )
			style.configure( 'Blue.TRadiobutton', foreground='#698DCF' )
			self.stylesAdded = True

		file = modelPane.displayObjects[0].dat
		windowTitle = 'Render Options ({})'.format( file.filename )

		if not BasicWindow.__init__( self, globalData.gui.root, windowTitle, resizable=True, unique=True ):
			return # Unique window already exists; bringing that back into view now instead of creating a new window

		self.editorTab = editorTab
		self.modelPane = modelPane

		self.infoText = Tk.StringVar( value='The selected texture is used by the\nmodel on these parts:' )
		ttk.Label( self.window, textvariable=self.infoText, justify='center' ).grid( column=0, row=0, columnspan=2, pady=(6, 2) )

		# Add selection for Display Objects
		self.partCheckboxesFrame = VerticalScrolledFrame( self.window, maxHeight=400 )
		self.partCheckboxesFrame.grid( column=0, row=1, columnspan=2, sticky='nsew', pady=6, padx=10 )
		self.populate()

		ttk.Separator( self.window, orient='horizontal' ).grid( column=0, row=2, columnspan=2, sticky='ew', padx=42, pady=(6, 12) )

		# showAllBtn = ttk.Checkbutton( self.window, text='Show all model parts', variable=self.modelPane.showAllParts, command=self.showAllCheckboxClicked )
		# showAllBtn.grid( column=0, row=3, columnspan=2, padx=20 )

		# self.showRelatedBtn = ttk.Checkbutton( self.window, text='Show related parts (DObj siblings)', variable=self.modelPane.showRelatedParts, command=self.checkboxClicked )
		# self.showRelatedBtn.grid( column=0, row=4, columnspan=2, padx=20 )
		#self.updateRelatedBtn()

		options = [ 'Show Selected Only', 'Show Related Parts', 'Show All' ]
		self.modeDropdown = Dropdown( self.window, options, options[self.modelPane.displayMode], command=self.modeUpdated )
		self.modeDropdown.grid( column=0, row=3, columnspan=2, padx=20 )

		obscureBtn = ttk.Checkbutton( self.window, text='Obscure non-selected parts', variable=self.modelPane.obscureNonSelected, command=self.editorTab.refreshRender )
		obscureBtn.grid( column=0, row=4, columnspan=2, padx=20 )

		self.showHighPolyBtn = ttk.Radiobutton( self.window, text='High-poly', variable=self.modelPane.showHighPoly, value=True, command=self.updatePolyRender, style='Red.TRadiobutton' )
		self.showHighPolyBtn.grid( column=0, row=5, padx=8, sticky='e' )
		self.showLowPolyBtn = ttk.Radiobutton( self.window, text='Low-poly', variable=self.modelPane.showHighPoly, value=False, command=self.updatePolyRender, style='Blue.TRadiobutton' )
		self.showLowPolyBtn.grid( column=1, row=5, padx=8, sticky='w' )
		self.updatePolyBtns()

		showBonesBtn = ttk.Checkbutton( self.window, text='Show model bones', variable=self.modelPane.showBones, command=self.toggleBonesVisibility )
		showBonesBtn.grid( column=0, row=6, columnspan=2, padx=20 )

		cameraBtn = ttk.Checkbutton( self.window, text='Auto-update camera', variable=self.modelPane.autoCameraUpdates )
		cameraBtn.grid( column=0, row=7, columnspan=2, padx=20 )

		# Select/deselect all buttons
		lowerButtonsFrame = ttk.Frame( self.window )
		ttk.Button( lowerButtonsFrame, text='Select all', command=self.selectAll ).pack( side='left', padx=5 )
		ttk.Button( lowerButtonsFrame, text='Deselect all', command=self.deselectAll ).pack( side='left', padx=5 )
		lowerButtonsFrame.grid( column=0, row=8, columnspan=2, pady=12 )

		# Configure resize behavior (only the VSF should change size)
		self.window.columnconfigure( 'all', weight=1 )
		self.window.rowconfigure( 'all', weight=0 )
		self.window.rowconfigure( 1, weight=1 )

	# def updateRelatedBtn( self ):
		
	# 	""" Updates appearance of the 'Show related' checkbox/option, 
	# 		which is overridden by the 'Show all' option. """

	# 	if self.modelPane.showAllParts.get():
	# 		self.showRelatedBtn.config( state='disabled' )
	# 	else:
	# 		self.showRelatedBtn.config( state='enabled' )

	def populate( self ):

		""" Adds a checkbox for each Display Object that may be displayed. """

		self.checkboxStates = {} # key=DObjOffset, value=BooleanVar (for whether this dobj should be visible)
		self.transformedRenders = {} # key=DObjOffset, value=True/False (for whether it has joint transforms applied)

		#selectedObj = self.modelPane.displayObjects[self.modelPane.partIndex]
		#asteriskedParts = [ dobj.offset for dobj in self.modelPane.displayObjects ]

		if self.modelPane.displayMode == DisplayMode.SelectedOnly:
			self.infoText.set( 'The selected texture is used by\nthe model on these parts:' )

			# modelParts = self.modelPane.displayObjects

		elif self.modelPane.displayMode == DisplayMode.Related:
			self.infoText.set( '* The selected texture is used by\nthe model on these parts.' )

			# modelParts = self.editorTab.findRelatedParts( selectedObj )
			# modelParts = [ self.editorTab.file.getStruct(offset) for offset in modelParts ]
		
		else: # All
			self.infoText.set( '* The selected texture is used by\nthe model on these parts.' )

			# Get a list of all of the DObjs in the file
			# modelParts = []
			# for struct in self.editorTab.file.structs.values():
			# 	if isinstance( struct, hsdStructures.DisplayObjDesc ):
			# 		modelParts.append( struct )

		# Sort by DObj index, if available
		modelParts = self.modelPane.selectableObjects
		modelParts.sort( key=lambda part: part.id )

		# Add checkboxes to the interface for each Display Object
		row = 0
		for dobj in modelParts:
			#if dobj.offset == selectedObj.offset:
			if dobj in self.modelPane.currentRenders:
				boolVar = Tk.BooleanVar( value=True )
			else:
				boolVar = Tk.BooleanVar( value=False )

			self.checkboxStates[dobj.offset] = boolVar

			if dobj.id in self.modelPane.highPolyIds:
				style = 'Red.TCheckbutton'
			elif dobj.id in self.modelPane.lowPolyIds:
				style = 'Blue.TCheckbutton'
			else:
				style = 'TCheckbutton'

			if dobj.id == -1:
				title = ' ' + dobj.name
			else:
				title = ' {}: {}'.format( dobj.id, dobj.name )

			btn = ttk.Checkbutton( self.partCheckboxesFrame.interior, text=title, variable=boolVar, command=self.checkboxClicked, style=style )
			btn.grid( column=0, row=row, sticky='w', padx=(6, 0) )

			# Add an asterisk if the current texture is attached to this model part
			if self.modelPane.displayMode != DisplayMode.SelectedOnly and dobj in self.modelPane.displayObjects:
				ttk.Label( self.partCheckboxesFrame.interior, text='*' ).grid( column=1, row=row, sticky='w', padx=0 )

			row += 1

	def repopulate( self ):

		""" Clears the current list of checkboxes, and then adds a 
			checkbox for each Display Object that may be displayed. 
			Use this to update the window if it's left open. """
		
		self.partCheckboxesFrame.clear()
		self.populate()
		#self.updateRelatedBtn()
		self.updatePolyBtns()
		self.window.geometry( '' ) # Updates the window size

	# def showAllCheckboxClicked( self ):
	# 	#self.updateRelatedBtn()
	# 	self.checkboxClicked()

	def modeUpdated( self, widget, newValue ):

		""" Called when the display mode dropdown is changed. """

		newModeIndex = widget.options.index( newValue )
		self.modelPane.displayMode = newModeIndex

		# Check if one of the 'current' DObjs (texture attached to it) is currently selected
		# for dobjOffset, checkboxVar in self.checkboxStates.items():
		# 	dobj = self.editorTab.file.getStruct( dobjOffset )
		# 	if dobj in self.modelPane.displayObjects:
		# 		defaultObj = dobj
		# 		self.modelPane.partIndex = self.modelPane.displayObjects.index( dobj )
		# 		break
		# else: # The loop above didn't break; no default selected
		# 	defaultObj = self.modelPane.displayObjects[0]
		# 	self.modelPane.partIndex = 0

		defaultObj = self.modelPane.displayObjects[self.modelPane.partIndex]

		# if self.modelPane.displayMode == DisplayMode.SelectedOnly:
		# 	self.editorTab.renderDobj( [defaultObj] )
		# elif self.modelPane.displayMode == DisplayMode.Related:
		# 	self.editorTab.renderDobj( [defaultObj] )
		# else: # All
		self.editorTab.renderDobj( [defaultObj] )

		self.repopulate()

	def updatePolyRender( self ):
		
		""" Called when the 'Show high/low poly' radio buttons/option are updated. 
			Selects model parts that use the currently selected texture and match 
			the current high/low poly type. """

		partsToSelect = []

		for dobjOffset, checkboxVar in self.checkboxStates.items():
			dobj = self.editorTab.file.getStruct( dobjOffset )

			if dobj not in self.modelPane.displayObjects:
				checkboxVar.set( False )
			elif self.editorTab.hideBasedOnPoly( dobj ):
				checkboxVar.set( False )
			else:
				checkboxVar.set( True )
				partsToSelect.append( dobj )

		self.editorTab.renderDobj( partsToSelect )

	def updatePolyBtns( self ):
		
		""" Updates appearance of the 'Show high/low poly' radio buttons/option, 
			which isn't used if this isn't for a character costume file. """

		if isinstance( self.editorTab.file, CharCostumeFile ):
			self.showHighPolyBtn.config( state='enabled' )
			self.showLowPolyBtn.config( state='enabled' )
		else:
			self.showHighPolyBtn.config( state='disabled' )
			self.showLowPolyBtn.config( state='disabled' )

	def checkboxClicked( self ):

		""" Updates the render when one of the checkboxes is clicked on. """

		# engine = self.modelPane.engine
		# showRelatedParts = self.modelPane.showRelatedParts.get()
		# allowCameraUpdate = self.modelPane.autoCameraUpdates.get()

		# Check what structs are already available in the render window
		# renderedStructs = set()
		# for object in engine.vertexLists:
		# 	renderedStructs.update( object.tags )

		# Check what parts need to be shown/rendered or hidden
		# partsToShow = []
		# partsToHide = []
		enabledObjects = []
		#singleSelectedDobj = -1
		#indexUpdated = False
		#for dobjIndex, dobj in enumerate( self.modelPane.displayObjects ):
		for dobjOffset, checkboxVar in self.checkboxStates.items():
			dobj = self.editorTab.file.getStruct( dobjOffset )
			#dobjSiblings = dobj.getSiblings()[:] # Making a copy, since we might edit it

			# Show parts currently selected by the checkboxes
			#if self.checkboxStates[dobj.offset].get():
			if checkboxVar.get():
				# if showRelatedParts:
				# 	partsToShow.extend( dobjSiblings )
				# else:
				# 	partsToShow.append( dobj.offset )

					# Collect siblings to hide if they're visible
					# dobjSiblings.remove( dobj.offset )
					# partsToHide.extend( dobjSiblings )

				# Remember some details to update the title below the render window
				enabledObjects.append( dobj )
				#singleSelectedDobj = dobjIndex
			# else:
			# 	partsToHide.extend( dobjSiblings )

			# Set the DObj index to the first selected part
			# if not indexUpdated:
			# 	self.modelPane.partIndex = dobjIndex
			# 	indexUpdated = True
				if dobj in self.modelPane.displayObjects:
					self.modelPane.partIndex = self.modelPane.displayObjects.index( dobj )

		self.editorTab.renderDobj( enabledObjects )

		# Hide everything by default
		#engine.showAll( visible=False, primitive='vertexList' )

		# Apply joint transformations only if there are multiple parts being displayed
		# for offset in partsToShow:
		# 	if len( enabledObjects ) == 1:
		# 		if offset in renderedStructs:
		# 			# Already rendered; check if it has joint transformations applied
		# 			if self.transformedRenders.get( offset, False ):
		# 				engine.removePart( offset, 'vertexList' )
		# 			else:
		# 				engine.showPart( offset, True, 'vertexList' )
		# 				continue

		# 		self._renderPart( offset )

		# 	else: # Multiple parts to render. Joint translations should be applied
		# 		if offset in renderedStructs:
		# 			if self.transformedRenders.get( offset, False ):
		# 				engine.showPart( offset, True, 'vertexList' )
		# 				continue
		# 			else:
		# 				engine.removePart( offset, 'vertexList' )

		# 		self._renderPart( offset, applyTransformations=True )

		# Adjust the camera, based on whether there is just one object or multiple to focus on
		# if allowCameraUpdate:
		# 	engine.focusCamera( tags=partsToShow, primitive='vertexList', skipRotationReset=False )

		# Update the title string under the render window
		# if len( enabledObjects ) == 0:
		# 	self.modelPane.dobjStringVar.set( 'No Parts Selected' )
		# elif len( enabledObjects ) == 1:
		# 	self.modelPane.dobjStringVar.set( enabledObjects[0].name )
		# 	self.modelPane.partIndex = singleSelectedDobj
		# elif len( enabledObjects ) < 4:
		# 	title = 'Display Objects ' + grammarfyList( ['0x{:X}'.format(0x20+obj.offset) for obj in enabledObjects] )
		# 	self.modelPane.dobjStringVar.set( title )
		# else:
		# 	self.modelPane.dobjStringVar.set( 'Multiple Selected' )

	def selectAll( self ):

		""" Conditionally selects parts that should be visible (by poly type) and updates the render window. """

		#[ boolVar.set(True) for boolVar in self.checkboxStates.values() ]
		for dobjOffset, checkboxVar in self.checkboxStates.items():
			dobj = self.editorTab.file.getStruct( dobjOffset )

			if self.editorTab.hideBasedOnPoly( dobj ):
				checkboxVar.set( False )
			else:
				checkboxVar.set( True )

		self.checkboxClicked()

	def deselectAll( self ):

		""" Unconditionally deselects all parts and clears the render window. """

		[ boolVar.set(False) for boolVar in self.checkboxStates.values() ]

		self.editorTab.renderDobj( [] )

	def toggleBonesVisibility( self ):

		""" Toggles the visibility state of bones in the renderer, and updates it. """

		showBones = self.modelPane.showBones.get()
		self.modelPane.engine.showPart( 'bones', showBones, 'edge' )

