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
import Tkinter as Tk
from Tkinter import TclError
from PIL import Image, ImageTk
from FileSystem import hsdStructures

# Internal dependencies
import globalData
from basicFunctions import isNaN, msg, printStatus, uHex
from guiSubComponents import ToolTip, VerticalScrolledFrame


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
		# Create the new tab for the given file
		newTab = TexturesEditorTab( self, fileObj )
		self.add( newTab, text=fileObj.filename )

		# Populate and switch to the new tab
		newTab.populate()
		self.select( newTab )

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

	def __init__( self, parent, fileObj ):
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
		#self.datTextureTree.bind( '<<TreeviewSelect>>', self.onTextureTreeSelect )
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
		ttk.Label( datFileDetails, textvariable=self.datFilesizeText, width=23 )
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
		if self.root.nametowidget( self.imageManipTabs.select() ) != self.textureTreeImagePane:
			self.imageManipTabs.select( self.textureTreeImagePane )
		self.imageManipTabs.tab( self.palettePane, state='disabled' )
		self.imageManipTabs.tab( self.modelPropertiesPane, state='disabled' )
		self.imageManipTabs.tab( self.texturePropertiesPane, state='disabled' )

		# Clear the repositories for storing image data (used to prevent garbage collected)
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
		printStatus( 'Scanning File....' )

		self.file.initialize()
		
		texturesInfo = self.file.identifyTextures()
		texturesFound = totalTextureSpace = 0
		filteredTexturesInfo = []

		if self.rescanPending(): return

		elif texturesInfo: # i.e. textures were found
			texturesInfo.sort( key=lambda infoTuple: infoTuple[0] ) # Sorts the textures by file offset
			#dumpImages = generalBoolSettings['dumpPNGs'].get()
			loadingImage = globalData.gui.imageBank( 'loading' )
			
			for imageDataOffset, imageHeaderOffset, paletteDataOffset, paletteHeaderOffset, width, height, imageType, mipmapCount in texturesInfo:
				# Ignore textures that don't match the user's filters
				if not self.passesImageFilters( imageDataOffset, width, height, imageType ):
					if imageDataOffset in priorityTargets: pass # Overrides the filter
					else:
						continue

				# Initialize a structure for the image data (this will be stored in the file and accessed later)
				imageDataLength = hsdStructures.ImageDataBlock.getDataLength( width, height, imageType ) # Returns an int (counts in bytes)
				imageDataStruct = self.file.initDataBlock( hsdStructures.ImageDataBlock, imageDataOffset, imageHeaderOffset, dataLength=imageDataLength )
				imageDataStruct.imageHeaderOffset = imageHeaderOffset
				imageDataStruct.paletteDataOffset = paletteDataOffset # Ad hoc way to locate palettes in files with no palette data headers
				imageDataStruct.paletteHeaderOffset = paletteHeaderOffset
				filteredTexturesInfo.append( (imageDataOffset, width, height, imageType, imageDataLength) )

				totalTextureSpace += imageDataLength
				texturesFound += 1

				# Highlight any textures that need to stand out
				tags = []
				if width > 1024 or width % 2 != 0 or height > 1024 or height % 2 != 0: tags.append( 'warn' )
				if mipmapCount > 0: tags.append( 'mipmap' )

				# Add this texture to the DAT Texture Tree tab, using the thumbnail generated above
				try:
					self.datTextureTree.insert( '', 'end', 									# '' = parent/root, 'end' = insert position
						iid=str( imageDataOffset ),
						image=loadingImage,
						values=(
							uHex(0x20 + imageDataOffset) + '\n('+uHex(imageDataLength)+')', 	# offset to image data, and data length
							(str(width)+' x '+str(height)), 								# width and height
							'_'+str(imageType)+' ('+imageFormats[imageType]+')' 			# the image type and format
						),
						tags=tags
					)
				except TclError:
					print( hex(imageDataOffset) + ' already exists!' )
					continue
				#print uHex( 0x20+imageDataOffset ), ' | ', constructTextureFilename(globalDatFile, str(imageDataOffset))

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
		self.datFilesizeText.set( "File Size:  {:,} bytes".format(self.file.headerInfo['filesize']) )
		self.totalTextureSpaceText.set( "Total Texture Size:  {:,} b".format(totalTextureSpace) )
		self.texturesFoundText.set( 'Textures Found:  ' + str(texturesFound) )
		self.texturesFilteredText.set( 'Filtered Out:  ' + str(texturesFound-len( filteredTexturesInfo )) )

		if self.rescanPending(): return

		if filteredTexturesInfo:
			# tic = time.clock()
			# if 0: # Disabled, until this process can be made more efficient
			# 	#print 'using multiprocessing decoding'

			# 	# Start a loop for the GUI to watch for updates (such updates should not be done in a separate thread or process)
			# 	Gui.thumbnailUpdateJob = Gui.root.after( Gui.thumbnailUpdateInterval, Gui.updateTextureThumbnail )

			# 	# Start up a separate thread to handle and wait for the image rendering process
			# 	renderingThread = Thread( target=startMultiprocessDecoding, args=(filteredTexturesInfo, globalDatFile, Gui.textureUpdateQueue, dumpImages) )
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

	def renderTextureData( self, imageDataOffset, width, height, imageType, imageDataLength, allowImageDumping=True ):

		""" Decodes image data from the globally loaded DAT file at a given offset and creates an image out of it. This then
			stores/updates the full image and a preview/thumbnail image (so that they're not garbage collected) and displays it in the GUI.
			The image and its info is then displayed in the DAT Texture Tree tab's treeview (does not update the Dat Texture Tree subtabs).

			allowImageDumping is False when this function is used to 're-load' image data,
			(such as after importing a new texture, or modifying the palette of an existing one), 
			so that image modifications don't overwrite texture dumps. """

		#tic = time.clock()

		problemWithImage = False

		try:
			textureImage = self.file.getTexture( imageDataOffset, width, height, imageType, imageDataLength, getAsPilImage=True )

		except Exception as errMessage:
			print( 'Unable to make out a texture for data at ' + uHex(0x20+imageDataOffset) )
			print( errMessage )
			problemWithImage = True

		# toc = time.clock()
		# print 'time to decode image for', hex(0x20+imageDataOffset) + ':', toc-tic

		# Store the full image (or error image) so it's not garbage collected, and generate the preview thumbnail.
		if problemWithImage:
			# The error image is already 64x64, so it doesn't need to be resized for the thumbnail.
			errorImage = globalData.gui.imageBank( 'noImage' )
			self.datTextureTree.fullTextureRenders[imageDataOffset] = errorImage
			self.datTextureTree.textureThumbnails[imageDataOffset] = errorImage
		else:
			# if allowImageDumping and generalBoolSettings['dumpPNGs'].get():
			# 	textureImage.save( buildTextureDumpPath(globalDatFile, imageDataOffset, imageType, '.png') )

			self.datTextureTree.fullTextureRenders[imageDataOffset] = ImageTk.PhotoImage( textureImage )
			textureImage.thumbnail( (64, 64), Image.ANTIALIAS )
			self.datTextureTree.textureThumbnails[imageDataOffset] = ImageTk.PhotoImage( textureImage )

		# If this item has already been added to the treeview, update the preview thumbnail of the texture.
		iid = str( imageDataOffset )
		if self.datTextureTree.exists( iid ):
			self.datTextureTree.item( iid, image=self.datTextureTree.textureThumbnails[imageDataOffset] )

		if not problemWithImage: return True
		else: return False

	def openDatDestination( self, event ):

		""" This is only called by pressing Enter/Return on the top file path display/entry of
			the DAT Texture Tree tab. Verifies given the path and loads the file for viewing. """

		filepath = self.datDestination.get().replace( '"', '' )

		# if pathIsFromDisc( filepath ):
		# 	iid = filepath.lower()
		# 	loadFileWithinDisc( iid )
		# else:
		# 	fileHandler( [filepath] )

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
		currentTab = globalData.gui.root.nametowidget( self.imageManipTabs.select() )

		# Update the main display with the texture's stored image.
		drawTextureToMainDisplay( iid )

		# Collect info on the texture
		imageDataOffset, imageDataLength, width, height, imageType = parseTextureDetails( iid )
		imageDataStruct = globalDatFile.structs.get( imageDataOffset )
		if imageDataStruct:
			imageDataHeaderOffsets = imageDataStruct.getParents()

		# Determine whether to enable and update the Palette tab.
		if imageType == 8 or imageType == 9 or imageType == 10:
			# Enable the palette tab and prepare the data displayed on it.
			self.imageManipTabs.tab( 1, state='normal' )
			populatePaletteTab( int(iid), imageDataLength, imageType )
		else:
			# No palette for this texture. Check the currently viewed tab, and if it's the Palette tab, switch to the Image tab.
			if currentTab == self.palettePane:
				self.imageManipTabs.select( self.textureTreeImagePane )
			self.imageManipTabs.tab( self.palettePane, state='disabled' )

		wraplength = self.imageManipTabs.winfo_width() - 20	
		lackOfUsefulStructsDescription = ''
		effectTextureRange = getattr( globalDatFile, 'effTexRange', (-1, -1) ) # Only relevant with effects files and some stages

		# Check if this is a file that doesn't have image data headers :(
		if (0x1E00, 'MemSnapIconData') in globalDatFile.rootNodes: # The file is LbMcSnap.usd or LbMcSnap.dat (Memory card banner/icon file from SSB Melee)
			lackOfUsefulStructsDescription = 'This file has no known image data headers, or other structures to modify.'

		elif (0x4E00, 'MemCardIconData') in globalDatFile.rootNodes: # The file is LbMcGame.usd or LbMcGame.dat (Memory card banner/icon file from SSB Melee)
			lackOfUsefulStructsDescription = 'This file has no known image data headers, or other structures to modify.'

		elif (0, 'SIS_MenuData') in globalDatFile.rootNodes: # SdMenu.dat/.usd
			lackOfUsefulStructsDescription = 'This file has no known image data headers, or other structures to modify.'

		elif imageDataOffset >= effectTextureRange[0] and imageDataOffset <= effectTextureRange[1]:
			# e2eHeaderOffset = imageDataStruct.imageHeaderOffset
			# textureCount = struct.unpack( '>I', globalDatFile.getData(e2eHeaderOffset, 4) )[0]

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
		populateModelTab( imageDataHeaderOffsets, wraplength )

		# Enable and update the Properties tab
		self.imageManipTabs.tab( self.texturePropertiesPane, state='normal' )
		populateTexPropertiesTab( wraplength, width, height, imageType )

	def summonContextMenu( self, event ):
		contextMenu = textureMenuOptions( globalData.gui.root, tearoff=False )
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