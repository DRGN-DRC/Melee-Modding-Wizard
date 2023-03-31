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
import tkMessageBox
import Tkinter as Tk
from PIL import Image, ImageTk
from Tkinter import TclError
from binascii import hexlify
from collections import OrderedDict

# Internal dependencies
import globalData
from tplCodec import TplDecoder
from FileSystem import hsdStructures, DatFile
from basicFunctions import isNaN, humansize, grammarfyList, msg, copyToClipboard, printStatus, uHex, constructTextureFilename
from guiSubComponents import ( exportMultipleTextures, importSingleTexture, 
		HexEditEntry, EnumOptionMenu, HexEditDropdown, ColorSwatch, MeleeColorPicker, 
		FlagDecoder, ToolTip, VerticalScrolledFrame )


imageFormats = { 0:'I4', 1:'I8', 2:'IA4', 3:'IA8', 4:'RGB565', 5:'RGB5A3', 6:'RGBA8', 8:'CI4', 9:'CI8', 10:'CI14x2', 14:'CMPR' }
userFriendlyFormatList = [	'_0 (I4)', '_1 (I8)', 
							'_2 (IA4)', '_3 (IA8)', 
							'_4 (RGB565)', '_5 (RGB5A3)', '_6 (RGBA8)', 
							'_8 (CI4)', '_9 (CI8)', '_10 (CI14x2)', 
							'_14 (CMPR)' ]


class TexturesEditor( ttk.Notebook ):

	def __init__( self, parent, mainGui ):
		ttk.Notebook.__init__( self, parent )

		# Add this tab to the main GUI, and add drag-and-drop functionality
		mainGui.mainTabFrame.add( self, text=' Textures Editor ' )
		mainGui.dnd.bindtarget( self, mainGui.dndHandler, 'text/uri-list' )

	def addTab( self, fileObj ):

		""" Creates a new tab in the Textures Editor interface for the given file. """
		
		# Create the new tab for the given file
		newTab = TexturesEditorTab( self, fileObj )
		self.add( newTab, text=fileObj.filename )

		# Switch to and populate the new tab
		self.select( newTab )
		newTab.populate()

	def haltAllScans( self, programClosing=False ):

		""" Used to gracefully stop all ongoing file scans. Without a method like this, 
			if the program's GUI (mainloop) is closed/destroyed, there may be errors from 
			the scan loops acting on a GUI that no longer exists. """

		# Instruct all tabs to stop current scans
		tabWidgets = []
		for tabName in self.tabs():
			tabWidget = globalData.gui.root.nametowidget( tabName )
			tabWidget.haltScan = True
			tabWidgets.append( tabWidget )

		# Wait until all tabs have stopped scanning (waits for GUI event loop to iterate and cancel all scan loops)
		while 1:
			for tab in tabWidgets:
				if tab.scanningFile:
					break
			else: # The loop above didn't break; no tabs are currently scanning
				break # From the while loop

		# Reset the haltScan flag if the progrom isn't closing
		if not programClosing:
			for tab in tabWidgets:
				tab.haltScan = False

	def closeCurrentTab( self ):

		""" Removes the currently selected tab. If all tabs are removed, 
			the entire notebook (within main tab interface) should be removed. """

		mainGui = globalData.gui
		currentTab = mainGui.root.nametowidget( self.select() )
		currentTab.destroy()

		if not self.tabs():
			# Remove this tab from the main tab interface
			self.destroy()
			mainGui.texturesTab = None

			# Most likely the Disc File Tree was last used, so let's go back to that
			if mainGui.discTab:
				mainGui.mainTabFrame.select( mainGui.discTab )


class TexturesEditorTab( ttk.Frame ):

	def __init__( self, parent, fileObj=None ):
		ttk.Frame.__init__( self, parent )

		self.file = fileObj
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
		
		# Top header row | Filepath field and close button
		topRow = ttk.Frame( self, padding="12 12 12 0" ) # Left, Top, Right, Bottom

		ttk.Label( topRow, text=" DAT / USD:" ).pack( side='left' )
		self.datDestination = Tk.StringVar()
		datDestinationLabel = ttk.Entry( topRow, textvariable=self.datDestination )
		datDestinationLabel.bind( '<Return>', self.openDatDestination )
		datDestinationLabel.pack( side='left', fill='x', expand=1, padx=12 )

		if fileObj.source == 'disc':
			self.datDestination.set( fileObj.isoPath )
		elif fileObj.source == 'file':
			self.datDestination.set( fileObj.extPath )

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
		self.datTextureTreeBg = Tk.Label( self.datTextureTree, image=globalData.gui.imageBank('dndTarget'), borderwidth=0, highlightthickness=0 )
		self.datTextureTreeBg.place( relx=0.5, rely=0.5, anchor='center' )
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
		ttk.Checkbutton( canvasOptionsPane, command=self.updateCanvasGrid, text='Show Grid', variable=globalData.boolSettings['showCanvasGrid'] ).pack(side='left', padx=7)
		ttk.Checkbutton( canvasOptionsPane, command=self.updateCanvasTextureBoundary, text='Show Texture Boundary', variable=globalData.boolSettings['showTextureBoundary'] ).pack(side='left', padx=7)
		canvasOptionsPane.pack()

		self.textureDisplayFrame = Tk.Frame( self.textureTreeImagePane ) # The border and highlightthickness for the canvas below must be set to 0, so that the canvas has a proper origin of (0, 0).
		self.textureDisplay = Tk.Canvas( self.textureDisplayFrame, width=defaultCanvasDimensions, height=defaultCanvasDimensions, borderwidth=0, highlightthickness=0 )
		self.textureDisplay.pack( expand=1 ) # fill='both', padx=10, pady=10
		self.updateCanvasGrid( False )

		self.textureDisplay.defaultDimensions = defaultCanvasDimensions
		self.textureDisplayFrame.pack( expand=1 )

		datPreviewPaneBottomRow = Tk.Frame( self.textureTreeImagePane ) # This object uses grid alignment for its children so that they're centered and equally spaced amongst each other.

		self.previousDatButton = ttk.Label( datPreviewPaneBottomRow, image=globalData.gui.imageBank('previousDatButton') )
		self.previousDatButton.grid( column=0, row=0, ipadx=5, pady=(10, 0), sticky='e' )
		self.previousDatText = Tk.StringVar()
		ToolTip( self.previousDatButton, textvariable=self.previousDatText, delay=300, location='n' )

		datFileDetails = ttk.Labelframe( datPreviewPaneBottomRow, text='  File Details  ', labelanchor='n' )
		self.datFilesizeText = Tk.StringVar()
		self.datFilesizeText.set( 'File Size:  ' )
		ttk.Label( datFileDetails, textvariable=self.datFilesizeText )
		self.totalTextureSpaceText = Tk.StringVar()
		self.totalTextureSpaceText.set( 'Total Texture Size:  ' )
		ttk.Label( datFileDetails, textvariable=self.totalTextureSpaceText )
		self.texturesFoundText = Tk.StringVar()
		self.texturesFoundText.set( 'Textures Found:  ' )
		ttk.Label( datFileDetails, textvariable=self.texturesFoundText )
		self.texturesFilteredText = Tk.StringVar()
		self.texturesFilteredText.set( 'Filtered Out:  ' )
		ttk.Label( datFileDetails, textvariable=self.texturesFilteredText )
		for widget in datFileDetails.winfo_children():
			widget.pack( padx=20, pady=0, anchor='w' )
		datFileDetails.grid( column=1, row=0, ipady=4 )

		self.nextDatButton = ttk.Label( datPreviewPaneBottomRow, image=globalData.gui.imageBank('nextDatButton') )
		self.nextDatButton.grid( column=2, row=0, ipadx=5, pady=(10, 0), sticky='w' )
		self.nextDatText = Tk.StringVar()
		ToolTip( self.nextDatButton, textvariable=self.nextDatText, delay=300, location='n' )

		datPreviewPaneBottomRow.columnconfigure( 0, weight=1 )
		datPreviewPaneBottomRow.columnconfigure( 1, weight=1 )
		datPreviewPaneBottomRow.columnconfigure( 2, weight=1 )
		datPreviewPaneBottomRow.rowconfigure( 0, weight=1 )

		datPreviewPaneBottomRow.pack( side='bottom', pady=7, fill='x' )

		# Palette tab
		self.palettePane = ttk.Frame( self.imageManipTabs, padding='16 0 0 0' )
		self.imageManipTabs.add( self.palettePane, text=' Palette ', state='disabled' )
		self.imageManipTabs.bind( '<<NotebookTabChanged>>', self.imageManipTabChanged )

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
		self.modelPropertiesPane.interior.imageDataHeaders = []
		self.modelPropertiesPane.interior.nonImageDataHeaders = [] # Not expected
		self.modelPropertiesPane.interior.textureStructs = [] # Direct model attachments
		self.modelPropertiesPane.interior.headerArrayStructs = [] # Used for animations
		self.modelPropertiesPane.interior.unexpectedStructs = []
		self.modelPropertiesPane.interior.materialStructs = []
		self.modelPropertiesPane.interior.displayObjects = []
		self.modelPropertiesPane.interior.hideJointChkBtn = None
		self.modelPropertiesPane.interior.polyDisableChkBtn = None
		self.modelPropertiesPane.interior.opacityEntry = None
		self.modelPropertiesPane.interior.opacityBtn = None
		self.modelPropertiesPane.interior.opacityScale = None

		# Texture properties tab
		self.texturePropertiesPane = VerticalScrolledFrame( self.imageManipTabs )
		self.texturePropertiesPane.flagWidgets = [] # Useful for the Flag Decoder to more easily find widgets that need updating
		self.imageManipTabs.add( self.texturePropertiesPane, text='Properties', state='disabled' )

		self.imageManipTabs.pack( fill='both', expand=1 )

		secondRow.pack( fill='both', expand=1 )
		
	def clearDatTab( self, restoreBackground=False ):
		# Remove any existing entries in the treeview.
		for item in self.datTextureTree.get_children():
			self.datTextureTree.delete( item )

		# Reset the size of the texture display canvas, and clear its contents (besides the grid)
		self.textureDisplay.configure( width=self.textureDisplay.defaultDimensions, height=self.textureDisplay.defaultDimensions )
		self.textureDisplay.delete( self.textureDisplay.find_withtag('border') )
		self.textureDisplay.delete( self.textureDisplay.find_withtag('texture') )

		# Add or remove the background drag-n-drop image
		# if restoreBackground:
		# 	self.datTextureTreeBg.place( relx=0.5, rely=0.5, anchor='center' )
		# else: # This function removes them by default
		# 	self.datTextureTreeBg.place_forget()
		self.datTextureTreeStatusLabel.place_forget()

		# Reset the values on the Image tab.
		self.datFilesizeText.set( 'File Size:  ' )
		self.totalTextureSpaceText.set( 'Total Texture Size:  ' )
		self.texturesFoundText.set( 'Textures Found:  ' )
		self.texturesFilteredText.set( 'Filtered Out:  ' )

		# Disable some tabs by default (within the DAT Texture Tree tab), and if viewing one of them, switch to the Image tab
		self.imageManipTabs.select( 0 )
		self.imageManipTabs.tab( self.palettePane, state='disabled' )
		self.imageManipTabs.tab( self.modelPropertiesPane, state='disabled' )
		self.imageManipTabs.tab( self.texturePropertiesPane, state='disabled' )

		# Clear the repositories for storing image data (used to prevent garbage collection)
		self.datTextureTree.fullTextureRenders = {}
		self.datTextureTree.textureThumbnails = {}

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
			self.clearDatTab()
			self.populate()

			return True

		elif self.haltScan:
			self.scanningFile = False
			self.restartFileScan = False
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

	def populate( self, priorityTargets=() ):
		
		self.scanningFile = True
		self.datTextureTreeBg.place_forget() # Removes the drag-and-drop image

		printStatus( 'Scanning File...' )
		
		texturesInfo = self.file.identifyTextures()
		texturesFound = totalTextureSpace = 0
		filteredTexturesInfo = []

		if self.rescanPending():
			return

		elif texturesInfo: # i.e. textures were found
			loadingImage = globalData.gui.imageBank( 'loading' )
			
			for imageDataOffset, imageHeaderOffset, paletteDataOffset, paletteHeaderOffset, width, height, imageType, mipmapCount in texturesInfo:
				# Ignore textures that don't match the user's filters
				if not self.passesImageFilters( imageDataOffset, width, height, imageType ):
					if imageDataOffset in priorityTargets: pass # Overrides the filter
					else:
						continue

				# Initialize a structure for the image data (this will be stored in the file and accessed later)
				# imageDataLength = hsdStructures.ImageDataBlock.getDataLength( width, height, imageType ) # Returns an int (counts in bytes)
				# imageDataStruct = self.file.initDataBlock( hsdStructures.ImageDataBlock, imageDataOffset, imageHeaderOffset, dataLength=imageDataLength )
				# imageDataStruct.imageHeaderOffset = imageHeaderOffset
				# imageDataStruct.paletteDataOffset = paletteDataOffset # Ad hoc way to locate palettes in files with no palette data headers
				# imageDataStruct.paletteHeaderOffset = paletteHeaderOffset
				# imageDataStruct.width = width
				# imageDataStruct.height = height
				# imageDataStruct.imageType = imageType
				# imageDataStruct.imageDataLength = imageDataLength

				texture = self.file.initTexture( imageDataOffset, imageHeaderOffset, paletteDataOffset, paletteHeaderOffset, width, height, imageType, mipmapCount )
				imageDataLength = texture.imageDataLength

				filteredTexturesInfo.append( (imageDataOffset, width, height, imageType, imageDataLength) )
				totalTextureSpace += texture.length
				texturesFound += 1

				# Highlight any textures that need to stand out
				tags = []
				#if width > 1024 or width % 2 != 0 or height > 1024 or height % 2 != 0: tags.append( 'warn' )
				if width % 2 != 0 or height % 2 != 0: tags.append( 'warn' )
				if mipmapCount > 0: tags.append( 'mipmap' )

				# Add this texture to the DAT Texture Tree tab, using the thumbnail generated above
				try:
					self.datTextureTree.insert( '', 'end', 									# '' = parent/root, 'end' = insert position
						iid=str( imageDataOffset ),
						image=loadingImage,
						values=(
							uHex(0x20 + imageDataOffset) + '\n('+uHex(imageDataLength)+')', 	# offset to image data, and data length
							str(width)+' x '+str(height), 										# width and height
							'_'+str(imageType)+' ('+imageFormats[imageType]+')' 				# the image type and format
							#imageDataOffset, imageDataLength, width, height, imageType			# storing the above for easy access later
						),
						tags=tags
					)
				except TclError:
					print( hex(imageDataOffset) + ' already exists!' )
					continue

				# Add any associated mipmap images, as treeview children
				if mipmapCount > 0:
					parent = imageDataOffset

					for i in range( mipmapCount ):
						# Adjust the parameters for the next mipmap image
						imageDataOffset += imageDataLength # This is of the last image, not the current imageDataLength below
						width = int( math.ceil(width / 2.0) )
						height = int( math.ceil(height / 2.0) )
						imageDataLength = hsdStructures.ImageDataBlock.getDataLength( width, height, imageType )

						# Add this texture to the DAT Texture Tree tab, using the thumbnail generated above
						self.datTextureTree.insert( parent, 'end', 									# 'end' = insertion position
							iid=str( imageDataOffset ),
							image=loadingImage,
							values=(
								uHex(0x20 + imageDataOffset) + '\n('+uHex(imageDataLength)+')', 	# offset to image data, and data length
								(str(width)+' x '+str(height)), 								# width and height
								'_'+str(imageType)+' ('+imageFormats[imageType]+')' 			# the image type and format
							),
							tags=tags
						)
						filteredTexturesInfo.append( (imageDataOffset, width, height, imageType, imageDataLength) )

			# Immediately decode and display any high-priority targets
			if priorityTargets:
				for textureInfo in texturesInfo:
					if textureInfo[0] not in priorityTargets: continue

					imageDataOffset, _, _, _, width, height, imageType, _ = textureInfo
					dataBlockStruct = self.file.getStruct( imageDataOffset )

					self.renderTextureData( imageDataOffset, width, height, imageType, dataBlockStruct.length )

		# Update the GUI with some of the file's main info regarding textures
		self.datFilesizeText.set( "File Size:  {} ({:,} bytes)".format(humansize(self.file.size), self.file.size) )
		self.totalTextureSpaceText.set( "Total Texture Size:  {} ({:,} b)".format(humansize(totalTextureSpace), totalTextureSpace) )
		self.texturesFoundText.set( 'Textures Found:  ' + str(texturesFound) )
		self.texturesFilteredText.set( 'Filtered Out:  ' + str(texturesFound-len( filteredTexturesInfo )) )

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
			for imageDataOffset, width, height, imageType, imageDataLength in filteredTexturesInfo:
				# Skip items that should have already been processed
				if imageDataOffset in priorityTargets: continue

				# Update this item
				self.renderTextureData( imageDataOffset, width, height, imageType, imageDataLength )

				# Update the GUI to show new renders every n textures
				if i % 10 == 0:
					if self.rescanPending(): return
					self.datTextureTree.update()
				i += 1

		self.scanningFile = False

			# toc = time.clock()
			# print 'image rendering time:', toc - tic

		printStatus( 'File Scan Complete', success=True )

		if self.datTextureTree.get_children() == (): # Display a message that no textures were found, or they were filtered out.
			if not texturesFound:
				self.datTextureTreeStatusMsg.set( 'No textures were found.' )
			else:
				self.datTextureTreeStatusMsg.set( 'No textures were found that pass your current filters.' )
			self.datTextureTreeStatusLabel.place( relx=0.5, rely=0.5, anchor='center' )

	def renderTextureData( self, imageDataOffset, width=-1, height=-1, imageType=-1, imageDataLength=-1, problem=False ):

		""" Decodes image data from the globally loaded DAT file at a given offset and creates an image out of it. This then
			stores/updates the full image and a preview/thumbnail image (so that they're not garbage collected) and displays it in the GUI.
			The image and its info is then displayed in the DAT Texture Tree tab's treeview (does not update the Dat Texture Tree subtabs). """

		#tic = time.clock()
		if not problem:
			try:
				pilImage = self.file.getTexture( imageDataOffset, width, height, imageType, imageDataLength, getAsPilImage=True )

			except Exception as errMessage:
				print( 'Unable to make out a texture for data at ' + uHex(0x20+imageDataOffset) )
				print( errMessage )
				problem = True

		# toc = time.clock()
		# print 'time to decode image for', hex(0x20+imageDataOffset) + ':', toc-tic

		# Store the full image (or error image) so it's not garbage collected, and generate the preview thumbnail.
		if problem:
			# The error image is already 64x64, so it doesn't need to be resized for the thumbnail.
			errorImage = globalData.gui.imageBank( 'noImage' )
			self.datTextureTree.fullTextureRenders[imageDataOffset] = errorImage
			self.datTextureTree.textureThumbnails[imageDataOffset] = errorImage
		else:
			self.datTextureTree.fullTextureRenders[imageDataOffset] = ImageTk.PhotoImage( pilImage )
			pilImage.thumbnail( (64, 64), Image.ANTIALIAS )
			self.datTextureTree.textureThumbnails[imageDataOffset] = ImageTk.PhotoImage( pilImage )

		# If this item is in the treeview, update the preview thumbnail/icon and the image details of the texture
		iid = str( imageDataOffset )
		if self.datTextureTree.exists( iid ):
			# Collect texture properties
			if imageType == -1:
				width, height, imageType = self.file.getTextureInfo( imageDataOffset )[:3]
				assert imageType != -1, 'Unable to get texture info for the texture at 0x{:X}'.format( 0x20+imageDataOffset )
			imageDataLength = hsdStructures.ImageDataBlock.getDataLength( width, height, imageType )
			
			# Build new strings for the properties
			newValues = (
						uHex(0x20 + imageDataOffset) + '\n('+uHex(imageDataLength)+')', 	# offset to image data, and data length
						(str(width)+' x '+str(height)), 								# width and height
						'_'+str(imageType)+' ('+imageFormats[imageType]+')' 			# the image type and format
						)
			
			# Update the icon and info display
			self.datTextureTree.item( iid, image=self.datTextureTree.textureThumbnails[imageDataOffset], values=newValues )

		if not problem: return True
		else: return False

	def openDatDestination( self, event ):

		""" This is only called by pressing Enter/Return on the top file path display/entry of
			the DAT Texture Tree tab. Verifies given the path and loads the file for viewing. """

		path = self.datDestination.get().replace( '"', '' )

		if path in globalData.disc.files:
			# Change the file associated with this tab
			self.file = globalData.disc.files[path]
		
			# Restart the DAT/DOL file scan
			self.clearDatTab()
			self.populate()

		else:
			msg( 'Unable to find "{}" in the disc.'.format(path), 'File Not Found', warning=True )

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

	def onTextureTreeSelect( self, event, iid='' ):
		# Ensure there is an iid, or do nothing
		if not iid:
			iid = self.datTextureTree.selection()
			if not iid: return
		iid = iid[-1] # Selects the lowest position item selected in the treeview if multiple items are selected.

		# Update the main display with the texture's stored image.
		self.drawTextureToMainDisplay( iid )

		# Stop here if this is not a typical DAT file
		if not isinstance( self.file, DatFile ):
			return

		# Get the texture struct
		imageDataOffset = int( iid )
		imageDataStruct = self.file.structs.get( imageDataOffset )
		width, height, imageType = imageDataStruct.width, imageDataStruct.height, imageDataStruct.imageType
		if imageDataStruct:
			imageDataHeaderOffsets = imageDataStruct.getParents()

		# Determine whether to enable and update the Palette tab.
		currentTab = globalData.gui.root.nametowidget( self.imageManipTabs.select() )
		if imageType == 8 or imageType == 9 or imageType == 10:
			# Enable the palette tab and prepare the data displayed on it.
			self.imageManipTabs.tab( 1, state='normal' )
			self.populatePaletteTab( imageDataOffset, imageDataStruct.imageDataLength, imageType )
		else:
			# No palette for this texture. Check the currently viewed tab, and if it's the Palette tab, switch to the Image tab.
			if currentTab == self.palettePane:
				self.imageManipTabs.select( self.textureTreeImagePane )
			self.imageManipTabs.tab( self.palettePane, state='disabled' )

		wraplength = self.imageManipTabs.winfo_width() - 20
		lackOfUsefulStructsDescription = ''
		effectTextureRange = getattr( self.file, 'effTexRange', (-1, -1) ) # Only relevant with effects files and some stages

		# Check if this is a file that doesn't have image data headers :(
		if (0x1E00, 'MemSnapIconData') in self.file.rootNodes: # The file is LbMcSnap.usd or LbMcSnap.dat (Memory card banner/icon file from SSB Melee)
			lackOfUsefulStructsDescription = 'This file has no known image data headers, or other structures to modify.'

		elif (0x4E00, 'MemCardIconData') in self.file.rootNodes: # The file is LbMcGame.usd or LbMcGame.dat (Memory card banner/icon file from SSB Melee)
			lackOfUsefulStructsDescription = 'This file has no known image data headers, or other structures to modify.'

		elif (0, 'SIS_MenuData') in self.file.rootNodes: # SdMenu.dat/.usd
			lackOfUsefulStructsDescription = 'This file has no known image data headers, or other structures to modify.'

		elif imageDataOffset >= effectTextureRange[0] and imageDataOffset <= effectTextureRange[1]:
			# e2eHeaderOffset = imageDataStruct.imageHeaderOffset
			# textureCount = struct.unpack( '>I', self.file.getData(e2eHeaderOffset, 4) )[0]

			lackOfUsefulStructsDescription = ( 'Effects files and some stages have unique structuring for some textures, like this one, '
											'which do not have a typical image data header, texture object, or other common structures.' )
			# if textureCount == 1:
			# 	lackOfUsefulStructsDescription += ' This texture is not grouped with any other textures,'
			# elif textureCount == 2:
			# 	lackOfUsefulStructsDescription += ' This texture is grouped with 1 other texture,'
			# else:
			# 	lackOfUsefulStructsDescription += ' This texture is grouped with {} other textures,'.format( textureCount )
			# lackOfUsefulStructsDescription += ' with an E2E header at 0x{:X}.'.format( 0x20+e2eHeaderOffset )

		elif not imageDataStruct: # Make sure an image data struct exists to check if this might be something like a DOL texture
			lackOfUsefulStructsDescription = (  'There are no image data headers or other structures associated '
												'with this texture. These are stored end-to-end in this file with '
												'other similar textures.' )

		elif not imageDataHeaderOffsets:
			lackOfUsefulStructsDescription = 'This file has no known image data headers, or other structures to modify.'

		self.texturePropertiesPane.clear()
		self.texturePropertiesPane.flagWidgets = [] # Useful for the Flag Decoder to more easily find widgets that need updating

		# If the following string has something, there isn't much customization to be done for this texture
		if lackOfUsefulStructsDescription:
			# Disable the model parts tab, and if on that tab, switch to the Image tab.
			if currentTab == self.modelPropertiesPane:
				self.imageManipTabs.select( self.textureTreeImagePane )
			self.imageManipTabs.tab( self.modelPropertiesPane, state='disabled' )
			
			# Add some info to the texture properties tab
			self.imageManipTabs.tab( self.texturePropertiesPane, state='normal' )
			ttk.Label( self.texturePropertiesPane.interior, text=lackOfUsefulStructsDescription, wraplength=wraplength ).pack( pady=30 )

			return # Nothing more to say about this texture

		# Enable and update the Model tab
		self.imageManipTabs.tab( self.modelPropertiesPane, state='normal' )
		self.populateModelTab( imageDataHeaderOffsets, wraplength )

		# Enable and update the Properties tab
		self.imageManipTabs.tab( self.texturePropertiesPane, state='normal' )
		self.populateTexPropertiesTab( wraplength, width, height, imageType )

	def drawTextureToMainDisplay( self, iid ):

		""" Updates the main display area (the Image tab of the DAT Texture Tree tab) with a 
			texture's stored full-render image, if it has been rendered, and adjusts GUI size. """
		
		# Get the texture struct and pull info on the texture
		imageDataOffset = int( iid )
		imageDataStruct = self.file.structs.get( imageDataOffset )
		textureWidth = imageDataStruct.width
		textureHeight = imageDataStruct.height
		textureImage = self.datTextureTree.fullTextureRenders.get( imageDataOffset )
		if not textureImage:
			print( 'Unable to get a texture image for ' + hex(imageDataOffset) )
			return # May not have been rendered yet

		# Get the current dimensions of the program.
		self.textureDisplay.update() # Ensures the info gathered below is accurate
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

	def populateModelTab( self, imageDataHeaderOffsets, wraplength ):
		modelPane = self.modelPropertiesPane.interior
		vertPadding = 10

		# Clear the current contents
		self.modelPropertiesPane.clear()

		modelPane.imageDataHeaders = []
		modelPane.nonImageDataHeaders = [] # Not expected
		modelPane.textureStructs = [] # Direct model attachments
		modelPane.headerArrayStructs = [] # Used for animations
		modelPane.unexpectedStructs = []

		# Double-check that all of the parents are actually image data headers, and get grandparent structs
		for imageHeaderOffset in imageDataHeaderOffsets: # This should exclude any root/reference node parents (such as a label)
			headerStruct = self.file.initSpecificStruct( hsdStructures.ImageObjDesc, imageHeaderOffset )

			if headerStruct:
				modelPane.imageDataHeaders.append( headerStruct )

				# Check the grandparent structs; expected to be Texture Structs or Image Data Header Arrays
				for grandparentOffset in headerStruct.getParents():
					texStruct = self.file.initSpecificStruct( hsdStructures.TextureObjDesc, grandparentOffset, printWarnings=False )

					# Try getting or initializing a Texture Struct
					if texStruct:
						modelPane.textureStructs.append( texStruct )
					else:
						arrayStruct = self.file.initSpecificStruct( hsdStructures.ImageHeaderArray, grandparentOffset, printWarnings=False )
					
						# Try getting or initializing an Image Header Array Struct
						if arrayStruct:
							modelPane.headerArrayStructs.append( arrayStruct )
						else:
							# Initialize a general struct
							modelPane.unexpectedStructs.append( self.file.getStruct( grandparentOffset ) )
			else:
				# Attempt to initialize it in a generalized way (attempts to identify; returns a general struct if unable)
				modelPane.nonImageDataHeaders.append( self.file.getStruct(imageHeaderOffset) )

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

		# Get the associated material structs and display objects
		modelPane.materialStructs = []
		modelPane.displayObjects = []
		for texStruct in modelPane.textureStructs:
			for materialStructOffset in texStruct.getParents():
				materialStruct = self.file.initSpecificStruct( hsdStructures.MaterialObjDesc, materialStructOffset )

				if materialStruct:
					modelPane.materialStructs.append( materialStruct )

					for displayObjOffset in materialStruct.getParents():
						displayObject = self.file.initSpecificStruct( hsdStructures.DisplayObjDesc, displayObjOffset )

						if displayObject: 
							modelPane.displayObjects.append( displayObject )

		# Display controls to adjust this texture's model transparency
		# Set up the transparency control panel and initialize the control variables
		transparencyPane = ttk.Frame( modelPane )
		jointHidden = Tk.BooleanVar()
		displayListDisabled = Tk.BooleanVar() # Whether or not display list length has been set to 0

		modelPane.hideJointChkBtn = ttk.Checkbutton( transparencyPane, text='Disable Joint Rendering', variable=jointHidden, command=self.toggleHideJoint )
		modelPane.hideJointChkBtn.var = jointHidden
		modelPane.hideJointChkBtn.grid( column=0, row=0, sticky='w', columnspan=3 )
		modelPane.polyDisableChkBtn = ttk.Checkbutton( transparencyPane, text='Disable Polygon (Display List) Rendering', variable=displayListDisabled, command=self.toggleDisplayListRendering )
		modelPane.polyDisableChkBtn.var = displayListDisabled
		modelPane.polyDisableChkBtn.grid( column=0, row=1, sticky='w', columnspan=3 )
		ttk.Label( transparencyPane, text='Transparency Control:' ).grid( column=0, row=2, sticky='w', columnspan=3, padx=15, pady=(3, 4) )
		opacityValidationRegistration = globalData.gui.root.register( self.opacityEntryUpdated )
		modelPane.opacityEntry = ttk.Entry( transparencyPane, width=7, justify='center', validate='key', validatecommand=(opacityValidationRegistration, '%P') )
		modelPane.opacityEntry.grid( column=0, row=3 )
		modelPane.opacityBtn = ttk.Button( transparencyPane, text='Set', command=self.setModelTransparencyLevel, width=4 )
		modelPane.opacityBtn.grid( column=1, row=3, padx=4 )
		modelPane.opacityScale = ttk.Scale( transparencyPane, from_=0, to=10, command=self.opacityScaleUpdated )
		modelPane.opacityScale.grid( column=2, row=3, sticky='we' )

		transparencyPane.pack( pady=(vertPadding, 0), expand=True, fill='x', padx=20 )

		transparencyPane.columnconfigure( 0, weight=0 )
		transparencyPane.columnconfigure( 1, weight=0 )
		transparencyPane.columnconfigure( 2, weight=1 )

		# Add a help button for texture/model disablement and transparency
		helpText = ( 'Disabling Joint Rendering will set the "Hidden" flag (bit 4) for all of the lowest-level Joint Structures '
					"connected to the selected texture (parents to this texture's Display Object(s)). That will be just "
					"one particular Joint Struct in most cases, however that may be the parent for multiple parts of the model. "
					"To have finer control over which model parts are disabled, consider the Disable Polygon Rendering option."
					"\n\nDisabling Polygon Rendering is achieved by setting the display list data stream size to 0 "
					"""(i.e. each associated Polygon Objects' "Display List Length"/"Display List Blocks" value). This is """
					"done for each Polygon Object of each Display Object associated with this texture. For finer control, use "
					'the Structural Analysis tab. There, you can even experiment with reducing the length of the list '
					'to some other value between 0 and the original value, to render or hide different polygon groups.'
					'\n\nTransparency Control makes the entire model part that this texture is attached to partially transparent. '
					'This uses the value found in the Material Colors Struct by the same name, while setting multiple flags '
					"within parenting structures. The flags set are 'Render No Z-Update' and 'Render XLU' of the Material Structs "
					"(bits 29 and 30, respectfully), as well as 'XLU' and 'Root XLU' of the Joint Struct (bits 19 and 29). " )
		helpBtn = ttk.Label( transparencyPane, text='?', foreground='#445', cursor='hand2' )
		helpBtn.place( relx=1, x=-17, y=0 )
		helpBtn.bind( '<1>', lambda e, message=helpText: msg(message, 'Disabling Rendering and Transparency') )

		# Add widgets for Material Color editing
		ttk.Separator( modelPane, orient='horizontal' ).pack( fill='x', padx=24, pady=(vertPadding*2, vertPadding) )
		ttk.Label( modelPane, text='Material Colors:' ).pack( pady=(vertPadding, 0) )

		colorsPane = ttk.Frame( modelPane )

		# Row 1; Diffusion and Ambience
		ttk.Label( colorsPane, text='Diffusion:' ).grid( column=0, row=0, sticky='e' )
		#diffusionEntry = HexEditEntry( colorsPane, -1, 4, 'I', 'Diffusion' ) # Data offset (the -1) will be updated below
		diffusionEntry = HexEditEntry( colorsPane, self.file, -1, 4, 'I', 'Diffusion' ) # Data offset (the -1) will be updated below
		diffusionEntry.grid( column=1, row=0, padx=6 )
		ttk.Label( colorsPane, text='Ambience:' ).grid( column=3, row=0, sticky='e' )
		ambienceEntry = HexEditEntry( colorsPane, self.file, -1, 4, 'I', 'Ambience' ) # Data offset (the -1) will be updated below
		ambienceEntry.grid( column=4, row=0, padx=6 )

		# Row 2; Specular Highlights and Shininess
		ttk.Label( colorsPane, text='Highlights:' ).grid( column=0, row=1, sticky='e', padx=(12, 0) )
		highlightsEntry = HexEditEntry( colorsPane, self.file, -1, 4, 'I', 'Specular Highlights' ) # Data offset (the -1) will be updated below
		highlightsEntry.grid( column=1, row=1, padx=6 )
		ttk.Label( colorsPane, text='Shininess:' ).grid( column=3, row=1, sticky='e', padx=(12, 0) )
		shininessEntry = HexEditEntry( colorsPane, self.file, -1, 4, 'f', 'Shininess', valueEntry=True ) # Data offset (the -1) will be updated below
		shininessEntry.grid( column=4, row=1, padx=6 )

		colorsPane.pack( pady=(vertPadding, 0), expand=True, fill='x', padx=20 )
		
		print( 'material structs: ' + str([hex(0x20+obj.offset) for obj in modelPane.materialStructs]) )
		print( 'displayObj structs: ' + str([hex(0x20+obj.offset) for obj in modelPane.displayObjects]) )

		# Set initial values for the transparency controls and material colors above, or disable them
		if modelPane.displayObjects:
			firstDisplayObj = modelPane.displayObjects[0]

			# Get a parent Joint Object, and see if its hidden flag is set
			for structureOffset in firstDisplayObj.getParents():
				jointStruct = self.file.initSpecificStruct( hsdStructures.JointObjDesc, structureOffset )
				if jointStruct:
					jointFlags = jointStruct.getValues( specificValue='Joint_Flags' )
					jointHidden.set( jointFlags & 0b10000 ) # Checking bit 4
					break
			else: # The loop above didn't break; no joint struct parent found
				modelPane.hideJointChkBtn.configure( state='disabled' )
				ToolTip( modelPane.hideJointChkBtn, '(No parent Joint Object found.)', wraplength=400 )

			# Check the current state of this model part's rendering; get the first Polygon Object, and see if its Display List Blocks/Length attribute is 0
			polygonObjOffset = firstDisplayObj.getValues( specificValue='Polygon_Object_Pointer' )
			polygonObj = self.file.initSpecificStruct( hsdStructures.PolygonObjDesc, polygonObjOffset, firstDisplayObj.offset )

			if polygonObj:
				displayListBlocks = polygonObj.getValues( 'Display_List_Length' )
				displayListDisabled.set( not bool(displayListBlocks) ) # Resolves to True if the value is 0, False for anything else
			else:
				displayListDisabled.set( False )
				modelPane.polyDisableChkBtn.configure( state='disabled' )

			# If we found display objects, we must have also found material structs; get its values
			materialStruct = modelPane.materialStructs[0]
			matColorsOffset = materialStruct.getValues()[3]
			matColorsStruct = self.file.initSpecificStruct( hsdStructures.MaterialColorObjDesc, matColorsOffset, materialStruct.offset )
			diffusion, ambience, specularHighlights, transparency, shininess = matColorsStruct.getValues()

			# Get all of the offsets that would be required to update the material color values
			diffusionHexOffsets = []
			ambienceHexOffsets = []
			highlightsHexOffsets = []
			shininessHexOffsets = []
			for materialStruct in modelPane.materialStructs:
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

			diffusionEntry.insert( 0, diffusionHexString )
			diffusionEntry.offsets = diffusionHexOffsets
			diffusionEntry.colorSwatch = ColorSwatch( colorsPane, diffusionHexString, diffusionEntry )
			diffusionEntry.colorSwatch.grid( column=2, row=0, padx=(0,2) )
			
			ambienceEntry.insert( 0, ambienceHexString )
			ambienceEntry.offsets = ambienceHexOffsets
			ambienceEntry.colorSwatch = ColorSwatch( colorsPane, ambienceHexString, ambienceEntry )
			ambienceEntry.colorSwatch.grid( column=5, row=0, padx=(0,2) )
			
			highlightsEntry.insert( 0, highlightsHexString )
			highlightsEntry.offsets = highlightsHexOffsets
			highlightsEntry.colorSwatch = ColorSwatch( colorsPane, highlightsHexString, highlightsEntry )
			highlightsEntry.colorSwatch.grid( column=2, row=1, padx=(0,2) )
			
			shininessEntry.insert( 0, shininess )
			shininessEntry.offsets = shininessHexOffsets

			# Add bindings for input submission
			# diffusionEntry.bind( '<Return>', updateEntryHex )
			# ambienceEntry.bind( '<Return>', updateEntryHex )
			# highlightsEntry.bind( '<Return>', updateEntryHex )
			# shininessEntry.bind( '<Return>', updateEntryHex )
		else:
			# Disable the render checkbuttons and transparency controls
			modelPane.hideJointChkBtn.configure( state='disabled' )
			modelPane.polyDisableChkBtn.configure( state='disabled' )
			modelPane.opacityEntry.configure( state='disabled' )
			modelPane.opacityBtn.configure( state='disabled' )

			# Disable the Material Color inputs
			diffusionEntry.configure( state='disabled' )
			ambienceEntry.configure( state='disabled' )
			highlightsEntry.configure( state='disabled' )
			shininessEntry.configure( state='disabled' )

			# Add a label explaining why these are disabled
			disabledControlsText = ('These controls are disabled because no Display Objects or Material Structs are directly associated with this texture. '
									'If this is part of a texture animation, find the default/starting texture for it and edit the structs for that instead.' )
			ttk.Label( modelPane, text=disabledControlsText, wraplength=wraplength ).pack( pady=(vertPadding, 0) )

	def toggleHideJoint( self ):

		""" Toggles the bit flag for 'Hidden' for each parent Joint Struct of the texture currently selected 
			in the DAT Texture Tree tab (last item in the selection if multiple items are selected). """

		# Get the bool determining whether to hide the joint from the GUI
		hideJoint = self.modelPropertiesPane.interior.hideJointChkBtn.var.get()
		modifiedJoints = [] # Tracks which joint flags we've already updated, to reduce redundancy

		# Iterate over the display objects of this texture, get their parent joint objects, and modify their flag
		for displayObj in self.modelPropertiesPane.interior.displayObjects:
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

		""" Toggles the defined length of the display lists associated with the currently texture currently selected 
			in the DAT Texture Tree tab (last item in the selection if multiple items are selected). """

		# Get the bool determining whether to clear the DObj render lists from the GUI
		clearDisplayList = self.modelPropertiesPane.interior.polyDisableChkBtn.var.get()
		structsUpdated = 0

		for displayObj in self.modelPropertiesPane.interior.displayObjects:
			# Get the polygon object of this display object, as well as its siblings
			polygonObjOffset = displayObj.getValues( 'Polygon_Object_Pointer' )
			polygonObj = self.file.initSpecificStruct( hsdStructures.PolygonObjDesc, polygonObjOffset, displayObj.offset )
			polygonSiblingObjs = [ self.file.structs[o] for o in polygonObj.getSiblings() ] # These should all be initialized through the .getSiblings method

			# Process this object and its siblings
			for polygonStruct in [polygonObj] + polygonSiblingObjs:
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

	def setModelTransparencyLevel( self ):

		""" Calling function of the "Set" button under the Model tab's Transparency Control. """

		opacityValue = self.modelPropertiesPane.interior.opacityScale.get() / 10

		# Update the transparency value, and set required flags for this in the Material Struct
		matStructsModified = 0
		for materialStruct in self.modelPropertiesPane.interior.materialStructs:
			matColorsOffset = materialStruct.getValues( 'Material_Colors_Pointer' )
			matColorsStruct = self.file.initSpecificStruct( hsdStructures.MaterialColorObjDesc, matColorsOffset, materialStruct.offset )

			if matColorsStruct: # If the Material Struct doesn't have its colors struct, we probably don't need to worry about modifying it
				# Change the transparency value within the struct values and file data, and record that the change was made
				self.file.updateStructValue( matColorsStruct, -2, opacityValue )

				if opacityValue < 1.0: # Set the required flags (RENDER_NO_ZUPDATE and RENDER_XLU; i.e. bits 29 and 30)
					self.file.updateFlag( materialStruct, 1, 29, True ) # RENDER_NO_ZUPDATE
					self.file.updateFlag( materialStruct, 1, 30, True ) # RENDER_XLU
					matStructsModified += 1
				# else:
				# 	self.file.updateFlag( materialStruct, 1, 29, False )
				# 	self.file.updateFlag( materialStruct, 1, 30, False )

		if opacityValue < 1.0: # Set flags required for this in the Joint Struct(s)
			modifiedJoints = [] # Tracks which joint flags we've already updated, to reduce redundancy

			# Iterate over the display objects of this texture, get their parent joint objects, and modify their flag
			for displayObj in self.modelPropertiesPane.interior.displayObjects:
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

	def opacityScaleUpdated( self, newValue ):

		""" Handles events from the transparency Slider widget, when its value is changed. 
			The slider value ranges between 0 and 10, (so that it's intervals when clicking 
			in the trough jump a decent amount). The purpose of this function is just to update 
			the value in the Entry widget. 'newValue' will initially be a string of a float. """

		newValue = round( float(newValue), 2 )

		# If this is not the Entry widget causing a change in the value, update it too
		if globalData.gui.root.focus_get() != self.modelPropertiesPane.interior.opacityEntry:
			# Set the entry widget to the current value (temporarily disable the validation function, so it's not called)
			self.modelPropertiesPane.interior.opacityEntry.configure( validate='none')
			self.modelPropertiesPane.interior.opacityEntry.delete( 0, 'end' )
			self.modelPropertiesPane.interior.opacityEntry.insert( 0, str(newValue*10) + '%' )
			self.modelPropertiesPane.interior.opacityEntry.configure( validate='key' )

	def populateTexPropertiesTab( self, wraplength, width, height, thisImageType ):

		""" Populates the Properties tab of the DAT Texture Tree interface. At this point, the pane has already been cleared. """

		propertiesPane = self.texturePropertiesPane.interior
		texStructs = self.modelPropertiesPane.interior.textureStructs
		matStructs = self.modelPropertiesPane.interior.materialStructs
		pixStructs = [] # Pixel Processing structures
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
		ttk.Label( flagsFrame, text='Render Mode Flags:' ).grid( column=0, row=2, sticky='e' )
		hexEntry = HexEditEntry( flagsFrame, self.file, matFlagOffsets, 4, 'I', 'Render Mode Flags' )
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

		# Add alternative texture sizes
		ttk.Separator( propertiesPane, orient='horizontal' ).pack( fill='x', padx=24, pady=(vertPadding*2, 0) )
		ttk.Label( propertiesPane, text='Alternative Texture Sizes:' ).pack( pady=(vertPadding*2, 0) )
		altImageSizesFrame = Tk.Frame( propertiesPane )
		sizesDict = OrderedDict()
		for i, imageType in enumerate( ( 0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 14 ) ):
			thisSize = hsdStructures.ImageDataBlock.getDataLength( width, height, imageType )
			if imageType == thisImageType: continue

			if not thisSize in sizesDict:
				sizesDict[thisSize] = [userFriendlyFormatList[i]]
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

	def imageManipTabChanged( self, event ):

		""" Called when the sub-tabs within this tab ('Image', 'Palette', etc.) are changed.
			Main purpose is simply to prevent the first widget from gaining immediate focus. """

		currentTab = globalData.gui.root.nametowidget( event.widget.select() )
		currentTab.focus() # Don't want keyboard/widget focus at any particular place yet

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
			mipmapLevel = 0

			if self.datTextureTree.parent( iid ): # This item is a child of a parent mipmap texture

				for level in self.datTextureTree.get_children( self.datTextureTree.parent(iid) ):
					mipmapLevel += 1
					if level == iid:
						break
		else:
			mipmapLevel = -1

		return mipmapLevel

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
				newImage = newImage.resize( (texture.width, texture.height) )

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
		if returnCode == 0:
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
					resizedImage = newImage.resize( (texture.width, texture.height) )
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
		fileStructs = self.file.structs
		uniqueDims = set()
		completedEncodings = {} # Key=tuple(width, height, imageType, paletteType), value=(imageData, paletteData)
		successCount = 0
		
		# Collect the textures to be replaced, and number of unique texture dimensions
		for offset in imageDataOffsets:
			texture = fileStructs.get( offset )

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
				# Resize the new image to match each texture it's replacing
				# for texture in selectedTextureObjects:
				# 	encodingSignature = ( texture.width, texture.height, texture.imageType )

				# 	try:
				# 		# Check if we've already encoded this data
				# 		preEncodedTexture = completedEncodings.get( encodingSignature )

				# 		if preEncodedTexture:
				# 			returnCode = self.file.setPreEncodedTexture( texture.offset, preEncodedTexture )[0]
				# 		else:
				# 			resizedImage = newImage.resize( (texture.width, texture.height) )
				# 			returnCode, imageData, paletteData = self.file.setTexture( texture.offset, resizedImage )
				# 	except Exception as err:
				# 		print( 'An unexpected error occurred importing the texture; {}'.format(err) )

				# 	if returnCode == 0:
				# 		if not preEncodedTexture:
				# 			completedEncodings[encodingSignature] = texture
				# 		successCount += 1

				# 	# Update the new texture's icon in the GUI
				# 	self.renderTextureData( texture.offset, problem=returnCode )
				# 	if texture.offset == imageDataOffsets[0]:
				# 		self.drawTextureToMainDisplay( texture.offset )
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
				# requiredSpace = texture.getDataLength( newImage.size[0], newImage.size[1], texture.imageType )
				# for texture in selectedTextureObjects:
				# 	encodingSignature = ( texture.width, texture.height, texture.imageType )

				# 	try:
				# 		# Check how much space is available to this texture
				# 		existingSpace = texture.getDataLength( texture.width, texture.height, texture.imageType )

				# 		if requiredSpace <= existingSpace:
				# 			returnCode, imageData, paletteData = self.file.setTexture( texture.offset, newImage )
				# 		else:
				# 			returnCode = 2
				# 	except Exception as err:
				# 		print( 'An unexpected error occurred importing the texture at 0x{:X}; {}'.format(texture.offset, err) )

				# 	if returnCode == 0:
				# 		completedEncodings[(texture.width, texture.height, texture.imageType)] = ( imageData, paletteData )
				# 		successCount += 1

				# 	# Update the new texture's icon in the GUI
				# 	self.renderTextureData( texture.offset, problem=returnCode )
				# 	if texture.offset == imageDataOffsets[0]:
				# 		self.drawTextureToMainDisplay( texture.offset )
						
				successCount += self._replaceTextures( textureObjects, newImage, completedEncodings, imageDataOffsets[0] )

			else: # No extra space needed; no special procedures needed
				# for texture in selectedTextureObjects:
				# 	encodingSignature = ( texture.width, texture.height, texture.imageType )

				# 	try:
				# 		returnCode, imageData, paletteData = self.file.setTexture( texture.offset, newImage )
				# 	except Exception as err:
				# 		print( 'An unexpected error occurred importing the texture; {}'.format(err) )
						
				# 	if returnCode == 0:
				# 		completedEncodings[(texture.width, texture.height, texture.imageType)] = ( imageData, paletteData )
				# 		successCount += 1

				# 	# Update the new texture's icon in the GUI
				# 	self.renderTextureData( texture.offset, problem=returnCode )
				# 	if texture.offset == imageDataOffsets[0]:
				# 		self.drawTextureToMainDisplay( texture.offset )

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
					
						newImage = newImage.resize( (texture.width, texture.height) )

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
			# for texture in selectedTextureObjects:
			# 	try:
			# 		returnCode, imageData, paletteData = self.file.setTexture( texture.offset, newImage )
			# 	except Exception as err:
			# 		print( 'An unexpected error occurred importing the texture; {}'.format(err) )
				
			# 	if returnCode == 0:
			# 		completedEncodings[(texture.width, texture.height, texture.imageType)] = ( imageData, paletteData )
			# 		successCount += 1

			# 	# Update the new texture's icon in the GUI
			# 	self.renderTextureData( texture.offset, problem=returnCode )
			# 	if texture.offset == imageDataOffsets[0]:
			# 		self.drawTextureToMainDisplay( texture.offset )

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
			mipmapLevel = self.texturesTab.getMipmapLevel( iid )
			hashedFileNames.append( constructTextureFilename(texture, mipmapLevel) )

		copyToClipboard( ', '.join(hashedFileNames) )
