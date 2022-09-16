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

# External logic dependencies
from cProfile import label
import os
import time
import copy
from binascii import hexlify
from tkMessageBox import askyesno

# External GUI dependencies
import ttk
import tkFileDialog
import Tkinter as Tk
# from FileSystem.charFiles import CharCostumeFile
# from FileSystem.fileBases import DatFile
# from FileSystem.hsdStructures import DisplayObjDesc, InverseMatrixObjDesc, JointObjDesc

# Internal dependencies
import globalData
from audioManager import AudioManager
from FileSystem import fileFactory, SisFile, MusicFile, CharDataFile, CharAnimFile
from FileSystem.disc import Disc
from basicFunctions import (
		msg, printStatus, copyToClipboard, removeIllegalCharacters, 
		uHex, humansize, createFolders, saveAndShowTempFileData
	)
from guiSubComponents import (
		cmsg,
		exportSingleFileWithGui,
		importSingleFileWithGui,
		getNewNameFromUser,
		DisguisedEntry,
		ToolTip, NeoTreeview
	)
from tools import CharacterColorConverter, SisTextEditor


class DiscTab( ttk.Frame ):

	def __init__( self, parent, mainGui ):

		ttk.Frame.__init__( self, parent ) #, padding="11 0 0 11" ) # Padding order: Left, Top, Right, Bottom.
		
		# Add this tab to the main GUI, and add drag-and-drop functionality
		mainGui.mainTabFrame.add( self, text=' Disc File Tree ' )
		mainGui.dnd.bindtarget( self, mainGui.dndHandler, 'text/uri-list' )

		# Disc shortcut links
		fileTreeColumn = Tk.Frame( self )
		isoQuickLinks = Tk.Frame( fileTreeColumn )
		ttk.Label( isoQuickLinks, text='Disc Shortcuts:' ).pack( side='left', padx=4 )
		ttk.Label( isoQuickLinks, text='System', foreground='#00F', cursor='hand2' ).pack( side='left', padx=4 )
		ttk.Label( isoQuickLinks, text='|' ).pack( side='left', padx=4 )
		ttk.Label( isoQuickLinks, text='Characters', foreground='#00F', cursor='hand2' ).pack( side='left', padx=4 )
		ttk.Label( isoQuickLinks, text='|' ).pack( side='left', padx=4 )
		ttk.Label( isoQuickLinks, text='Menus', foreground='#00F', cursor='hand2' ).pack( side='left', padx=4 )
		ttk.Label( isoQuickLinks, text='|' ).pack( side='left', padx=4 )
		ttk.Label( isoQuickLinks, text='Stages', foreground='#00F', cursor='hand2' ).pack( side='left', padx=4 )
		ttk.Label( isoQuickLinks, text='|' ).pack( side='left', padx=4 )
		ttk.Label( isoQuickLinks, text='Strings', foreground='#00F', cursor='hand2' ).pack( side='left', padx=4 )
		for label in isoQuickLinks.winfo_children():
			if label['text'] != '|': label.bind( '<1>', self.quickLinkClicked )
		isoQuickLinks.pack( pady=1 )

		# File Tree start
		isoFileTreeWrapper = Tk.Frame( fileTreeColumn ) # Contains just the ISO treeview and its scroller (since they need a different packing than the above links).
		self.isoFileScroller = Tk.Scrollbar( isoFileTreeWrapper )
		self.isoFileTree = NeoTreeview( isoFileTreeWrapper, columns=('description'), yscrollcommand=self.isoFileScroller.set )
		self.isoFileTree.heading( '#0', anchor='center', text='File     (Sorted by FST)' ) # , command=lambda: treeview_sort_column(self.isoFileTree, 'file', False)
		self.isoFileTree.column( '#0', anchor='center', minwidth=180, stretch=1, width=230 ) # "#0" is implicit in the columns definition above.
		self.isoFileTree.heading( 'description', anchor='center', text='Description' )
		self.isoFileTree.column( 'description', anchor='w', minwidth=180, stretch=1, width=312 )
		self.isoFileTree.tag_configure( 'changed', foreground='red' )
		self.isoFileTree.tag_configure( 'changesSaved', foreground='#292' ) # The 'save' green color
		self.isoFileTree.pack( side='left', fill='both', expand=1 )
		self.isoFileScroller.config( command=self.isoFileTree.yview )
		self.isoFileScroller.pack( side='left', fill='y' )

		# Add the background image to the file tree
		self.isoFileTreeBg = Tk.Label( self.isoFileTree, image=mainGui.imageBank('dndTarget'), borderwidth=0, highlightthickness=0 )
		self.isoFileTreeBg.place( relx=0.5, rely=0.5, anchor='center' )

		# Add treeview event handlers
		self.isoFileTree.bind( '<<TreeviewSelect>>', self.onFileTreeSelect )
		# self.isoFileTree.bind( '<Double-1>', onFileTreeDoubleClick )
		self.isoFileTree.bind( "<3>", self.createContextMenu ) # Right-click

		isoFileTreeWrapper.pack( fill='both', expand=1 )
		fileTreeColumn.pack( side='left', fill='both', expand=1 )
		#fileTreeColumn.grid( column=0, row=0, sticky='ns' )

				# ISO File Tree end, and ISO Information panel begins here

		isoOpsPanel = ttk.Frame( self, padding='0 9 0 0' ) # Padding order: Left, Top, Right, Bottom.

		self.isoOverviewFrame = Tk.Frame( isoOpsPanel ) # Contains the Game ID and banner image
		self.gameIdText = Tk.StringVar()
		ttk.Label( self.isoOverviewFrame, textvariable=self.gameIdText, font="-weight bold" ).grid( column=0, row=0, padx=2 )
		self.bannerCanvas = Tk.Canvas( self.isoOverviewFrame, width=96, height=32, borderwidth=0, highlightthickness=0 )
		self.bannerCanvas.grid( column=1, row=0, padx=2 ) #, borderwidth=0, highlightthickness=0
		self.bannerCanvas.pilImage = None
		self.bannerCanvas.bannerGCstorage = None
		self.bannerCanvas.canvasImageItem = None
		self.isoOverviewFrame.columnconfigure( 0, weight=1 )
		self.isoOverviewFrame.columnconfigure( 1, weight=1 )
		self.isoOverviewFrame.pack( fill='x', padx=6, pady=11 )

		# Display a short path
		self.isoPathShorthand = Tk.StringVar()
		self.isoPathShorthandLabel = ttk.Label( isoOpsPanel, textvariable=self.isoPathShorthand )
		self.isoPathShorthandLabel.pack()

		# Selected file details
		internalFileDetails = ttk.Labelframe( isoOpsPanel, text='  File Details  ', labelanchor='n' )
		self.isoOffsetText = Tk.StringVar()
		self.isoOffsetText.set( 'Disc Offset: ' )
		ttk.Label( internalFileDetails, textvariable=self.isoOffsetText, width=27, anchor='w' ).pack( padx=15, pady=4 )
		self.internalFileSizeText = Tk.StringVar()
		self.internalFileSizeText.set( 'File Size: ' )
		ttk.Label( internalFileDetails, textvariable=self.internalFileSizeText, width=27, anchor='w' ).pack( padx=15, pady=0 )
		self.internalFileSizeLabelSecondLine = Tk.StringVar()
		self.internalFileSizeLabelSecondLine.set( '' )
		ttk.Label( internalFileDetails, textvariable=self.internalFileSizeLabelSecondLine, width=27, anchor='w' ).pack( padx=15, pady=0 )
		internalFileDetails.pack( padx=15, pady=16, ipady=4 )

		# Primary ISO operation buttons
		self.isoOpsPanelButtons = Tk.Frame( isoOpsPanel )
		ttk.Button( self.isoOpsPanelButtons, text="Export", command=self.exportIsoFiles, state='disabled' ).grid( row=0, column=0, padx=7 )
		ttk.Button( self.isoOpsPanelButtons, text="Import", command=self.importSingleIsoFile, state='disabled' ).grid( row=0, column=1, padx=7 )
		ttk.Button( self.isoOpsPanelButtons, text="Browse Textures", command=self.browseTexturesFromDisc, state='disabled', width=18 ).grid( row=1, column=0, columnspan=2, pady=(7,0) )
		#ttk.Button( self.isoOpsPanelButtons, text="Analyze Structure", command=self.analyzeFileFromDisc, state='disabled', width=18 ).grid( row=2, column=0, columnspan=2, pady=(7,0) )
		self.isoOpsPanelButtons.pack( pady=2 )

		# Add the Magikoopa image
		kamekFrame = Tk.Frame( isoOpsPanel )
		ttk.Label( kamekFrame, image=mainGui.imageBank('magikoopa') ).place( relx=0.5, rely=0.5, anchor='center' )
		kamekFrame.pack( fill='both', expand=1 )

		isoOpsPanel.pack( side='left', fill='both', expand=1 )

	def clear( self ):

		""" Clears the GUI of the currently loaded disc. """

		globalData.disc.unsavedChanges = []
		self.isoFileTreeBg.place_forget() # Removes the background image if present

		# Delete the current items in the tree
		for item in self.isoFileTree.get_children():
			self.isoFileTree.delete( item )

		# If desired, temporarily show the user that all items have been removed (Nice small indication that the iso is actually being loaded)
		#if refreshGui: 
		globalData.gui.root.update_idletasks()

		# Disable buttons in the iso operations panel. They're re-enabled later if all goes well
		for widget in self.isoOpsPanelButtons.winfo_children():
			#if widget.winfo_class() == 'TButton':
				widget.config( state='disabled' ) # Will stay disabled if there are problems loading a disc.

		# Set the GUI's other values back to default.
		self.isoOffsetText.set( 'Disc Offset: ' )
		self.internalFileSizeText.set( 'File Size: ' )
		self.internalFileSizeLabelSecondLine.set( '' )
		
	def updateIids( self, iids ): # Simple function to change the Game ID for all iids in a given list or tuple

		""" Updates the Game ID for all isoPaths/iids in the given list or tuple. """

		disc = globalData.disc
		updatedList = []

		for iid in iids:
			if '/' in iid: updatedList.append( disc.gameId + '/' + '/'.join(iid.split('/')[1:]) )
			else: updatedList.append( iid )

		return tuple( updatedList )

	def loadDisc( self, updateStatus=True, preserveTreeState=False, switchTab=False, updatedFiles=None ):

		""" Clears and repopulates the Disc File Tree. Generally, population of the Disc Details Tab is also called by this.

				- updateStatus: 		Allows or prevents the program status to be updated after this method runs. 
				- preserveTreeState:	Restores the current state of the treeview after reload, including 
										open folders, file/folder selections and focus, and scroll position.
				- switchTab:			
				- updatedFiles:			If provided, this will be a list of iids (isoPaths) that were updated during a save operation.
										These files (and their parent folders) will be highlighted green to indicate changes. """

		if preserveTreeState:
			self.isoFileTree.saveState()

		# Remember the current Game ID in case it has changed (iids collected above will need to be updated before restoration)
		rootItems = self.isoFileTree.get_children()
		if rootItems:
			originalGameId = rootItems[0]
		else:
			originalGameId = globalData.disc.gameId
			
		self.clear()

		if switchTab:
			currentlySelectedTab = globalData.gui.root.nametowidget( globalData.gui.mainTabFrame.select() )
			if currentlySelectedTab != self and currentlySelectedTab != globalData.gui.discDetailsTab:
				globalData.gui.mainTabFrame.select( self ) # Switch to the Disc File Tree tab

		usingConvenienceFolders = globalData.checkSetting( 'useDiscConvenienceFolders' ) # Avoiding having to look this up many times
		disc = globalData.disc
		rootParent = disc.gameId

		# Add the root (GameID) entry
		self.isoFileTree.insert( '', 'end', iid=rootParent, text=' ' + disc.gameId + '  (root)', open=True, image=globalData.gui.imageBank('meleeIcon'), values=('', 'cFolder') )
		
		# Add the disc's files to the Disc File Tree tab
		if usingConvenienceFolders:
			self.isoFileTree.insert( rootParent, 'end', iid=rootParent + '/sys', text=' System files', image=globalData.gui.imageBank('folderIcon'), values=('', 'cFolder') )
		for discFile in disc.files.itervalues():
			self.addFileToFileTree( discFile, usingConvenienceFolders )

		# Enable the GUI's buttons and update other labels
		for widget in self.isoOpsPanelButtons.winfo_children():
			widget.config( state='normal' )
		if updateStatus: globalData.gui.updateProgramStatus( 'Disc Scan Complete' )
			
		# Recreate the prior state of the treeview (open folders, selection/focus, and scroll position)
		if preserveTreeState:
			# Update the file/folder selections and focus iids with the new game Id if it has changed.
			if originalGameId != disc.gameId:
				self.isoFileTree.openFolders = self.updateIids( self.isoFileTree.openFolders )
				self.isoFileTree.selectionState = self.updateIids( self.isoFileTree.selectionState )
				if '/' in self.isoFileTree.focusState:
					self.isoFileTree.focusState = disc.gameId + '/' + '/'.join(self.isoFileTree.focusState.split('/')[1:])

			# Restore state
			self.isoFileTree.restoreState()

		# Highlight recently updated files in green
		if updatedFiles:
			# Update the file iids with the new gameId if it has changed.
			if originalGameId != disc.gameId:
				updatedFiles = self.updateIids( updatedFiles )

			# Add save highlighting tags to the given items
			for iid in updatedFiles:
				if self.isoFileTree.exists( iid ):
					# Add a tag to highlight this item
					self.isoFileTree.item( iid, tags='changesSaved' )

					# Add tags to highlight the parent (folder) items
					parent = self.isoFileTree.parent( iid )
					while parent != disc.gameId:
						self.isoFileTree.item( parent, tags='changesSaved' )
						parent = self.isoFileTree.parent( parent )
						
		# Update the treeview's header text and its function call for the next (reversed) sort.
		self.isoFileTree.heading( '#0', text='File     (Sorted by FST)' )
		# self.isoFileTree.heading( '#0', command=lambda: treeview_sort_column(self.isoFileTree, 'file', False) )
		# self.isoFileTree.heading( '#0', command=self.sortTreeviewItems )

		# if updateDetailsTab:
		# 	self.update_idletasks() # Update the GUI's display (for slightly more instant results)
		# 	globalData.gui.discDetailsTab.loadDiscDetails()

	def addFolderToFileTree( self, isoPath ):

		""" Adds the given folder to the disc file tree, and recursively adds all parent folders it may require. 
			These folders are native to (actually exist in) the disc's file structure, not convenience folders. 
			The isoPath argument should be a disc folder filesystem path, like "GALE01/audio/us" (no file name or ending slash). """

		assert isoPath[-1] != '/', 'Invalid input to addFolderToFileTree(): ' + isoPath

		parent, folderName = os.path.split( isoPath )

		# Make sure the parent exists first (it could also be a folder that needs adding)
		if not self.isoFileTree.exists( parent ):
			self.addFolderToFileTree( parent )

		if folderName == 'audio':
			description = '\t\t --< Music and Sound Effects >--'
			iconImage = globalData.gui.imageBank( 'audioIcon' )
		else: 
			description = ''
			iconImage = globalData.gui.imageBank( 'folderIcon' )
		
		self.isoFileTree.insert( parent, 'end', iid=isoPath, text=' ' + folderName, values=(description, 'nFolder'), image=iconImage )
		
	def addFileToFileTree( self, discFile, usingConvenienceFolders ):

		""" Adds files and any folders they may need to the Disc File Tree, including convenience folders. """

		entryName = discFile.filename

		# Get the parent item that the current item should be added to
		parent = os.path.dirname( discFile.isoPath )

		# Create any native folders (those actually in the disc) that may be needed
		if not self.isoFileTree.exists( parent ):
			self.addFolderToFileTree( parent )

		# Add convenience folders (those not actually in the disc's file system)
		if globalData.disc.isMelee and usingConvenienceFolders:
			# System files
			if entryName in ( 'Boot.bin', 'Bi2.bin', 'ISO.hdr', 'AppLoader.img', 'Start.dol', 'Game.toc' ):
				parent = discFile.isoPath.split( '/' )[0] + '/sys' # Adding to the System Files folder ([GAMEID]/sys)

			# "Hex Tracks"; 20XX's custom tracks, e.g. 01.hps, 02.hps, etc.
			elif discFile.__class__.__name__ == 'MusicFile' and discFile.isHexTrack:
				if not self.isoFileTree.exists( 'hextracks' ):
					self.isoFileTree.insert( parent, 'end', iid='hextracks', text=' Hex Tracks', values=('\t\t --< 20XX Custom Tracks >--', 'cFolder'), image=globalData.gui.imageBank('musicIcon') )
				parent = 'hextracks'

			# Original audio folder
			elif parent.split('/')[-1] == 'audio' and entryName.startswith( 'ff_' ):
				if not self.isoFileTree.exists( 'fanfare' ):
					self.isoFileTree.insert( parent, 'end', iid='fanfare', text=' Fanfare', values=('\t\t --< Victory Audio Clips >--', 'cFolder'), image=globalData.gui.imageBank('audioIcon') )
				parent = 'fanfare'

			# Character Effect files
			elif entryName.startswith( 'Ef' ):
				if not self.isoFileTree.exists( 'ef' ):
					self.isoFileTree.insert( parent, 'end', iid='ef', text=' Ef__Data.dat', values=('\t\t --< Character Graphical Effects >--', 'cFolder'), image=globalData.gui.imageBank('folderIcon') )
				parent = 'ef'
			
			# Congratulations Screens
			elif entryName.startswith( 'GmRegend' ):
				if not self.isoFileTree.exists( 'gmregend' ):
					self.isoFileTree.insert( parent, 'end', iid='gmregend', text=' GmRegend__.thp', values=("\t\t --< 'Congratulation' Screens (1P) >--", 'cFolder'), image=globalData.gui.imageBank('folderIcon') )
				parent = 'gmregend'
			elif entryName.startswith( 'GmRstM' ): # Results Screen Animations
				if not self.isoFileTree.exists( 'gmrstm' ):
					self.isoFileTree.insert( parent, 'end', iid='gmrstm', text=' GmRstM__.dat', values=('\t\t --< Results Screen Animations >--', 'cFolder'), image=globalData.gui.imageBank('folderIcon') )
				parent = 'gmrstm'
			elif globalData.disc.is20XX and entryName.startswith( 'IfCom' ): # 20XX HP Infographics (originally the "Coming Soon" screens)
				if not self.isoFileTree.exists( 'infos' ):
					self.isoFileTree.insert( parent, 'end', iid='infos', text=' IfCom__.dat', values=('\t\t --< Infographics >--', 'cFolder'), image=globalData.gui.imageBank('folderIcon') )
				parent = 'infos'
			elif discFile.__class__.__name__ == 'StageFile':
				if not self.isoFileTree.exists( 'gr' ):
					self.isoFileTree.insert( parent, 'end', iid='gr', text=' Gr__.dat', values=('\t\t --< Stage Files >--', 'cFolder'), image=globalData.gui.imageBank('stageIcon') )
				parent = 'gr'
				
				# Check for Target Test stages (second case in parenthesis is for Luigi's, which ends in 0at in 20XX; last case is for the "TEST" stage)
				if entryName[2] == 'T' and ( discFile.ext == '.dat' or entryName == 'GrTLg.0at' ) and entryName != 'GrTe.dat':
					# Create a folder for target test stage files (if not already created)
					if not self.isoFileTree.exists( 't' ):
						self.isoFileTree.insert( parent, 'end', iid='t', text=' GrT__.dat', values=('\t - Target Test Stages', 'cFolder'), image=globalData.gui.imageBank('folderIcon') )
					parent = 't'
				elif entryName[2:5] in globalData.onePlayerStages: # For 1-Player modes,like 'Adventure'
					if not self.isoFileTree.exists( '1p' ):
						self.isoFileTree.insert( parent, 'end', iid='1p', text='Gr___.___', values=('\t - 1P-Mode Stages', 'cFolder'), image=globalData.gui.imageBank('folderIcon') )
					parent = '1p'
				elif discFile.isRandomNeutral():
					# Modern versions of 20XX (4.06+) have multiple variations of each neutral stage, the 'Random Neutrals' (e.g. GrSt.0at through GrSt.eat)
					iid = discFile.shortName.lower()

					# Add the convenience folder if not already added
					if not self.isoFileTree.exists( iid ):
						if discFile.shortName == 'GrP': # For Stadium
							folderName = ' {}_.usd'.format( discFile.shortName )
						else: folderName = ' {}._at'.format( discFile.shortName )
						self.isoFileTree.insert( 'gr', 'end', iid=iid, text=folderName, values=(discFile.longName + ' (RN)', 'cFolder'), image=globalData.gui.imageBank('folderIcon') )
					parent = iid
			elif discFile.ext == '.mth': # a video file
				if entryName.startswith( 'MvEnd' ): # 1-P Ending Movie
					if not self.isoFileTree.exists('mvend'):
						self.isoFileTree.insert( parent, 'end', iid='mvend', text=' MvEnd__.dat', values=('\t\t --< 1P Mode Ending Movies >--', 'cFolder'), image=globalData.gui.imageBank('folderIcon') )
					parent = 'mvend'
			elif entryName.startswith( 'Pl' ) and entryName != 'PlCo.dat': # Character file
				if not self.isoFileTree.exists( 'pl' ):
					self.isoFileTree.insert( parent, 'end', iid='pl', text=' Pl__.dat', values=('\t\t --< Character Files >--', 'cFolder'), image=globalData.gui.imageBank('charIcon') )
				character = globalData.charNameLookup.get( entryName[2:4], '' )
				if character:
					# Create a folder for the character (and the copy ability files if this is Kirby) if one does not already exist.
					charFolderIid = 'pl' + character.replace(' ', '').replace('[','(').replace(']',')') # Spaces or brackets can't be used in the iid.
					if not self.isoFileTree.exists( charFolderIid ):
						self.isoFileTree.insert( 'pl', 'end', iid=charFolderIid, text=' ' + character, values=('', 'cFolder'), image=globalData.gui.imageBank('folderIcon') )
					if entryName.endswith( 'DViWaitAJ.dat' ):
						discFile.shortDescription = '1P mode wait animation'
						if character.endswith( 's' ):
							discFile.longDescription = character + "' " + discFile.shortDescription
						else:
							discFile.longDescription = character + "'s " + discFile.shortDescription
					parent = charFolderIid
			elif entryName.startswith( 'Sd' ): # Menu text files
				if not self.isoFileTree.exists( 'sd' ):
					self.isoFileTree.insert( parent, 'end', iid='sd', text=' Sd__.dat', values=('\t\t --< UI Text Files >--', 'cFolder'), image=globalData.gui.imageBank('folderIcon') )
				parent = 'sd'
			elif entryName.startswith( 'Ty' ): # Trophy file
				if not self.isoFileTree.exists( 'ty' ):
					self.isoFileTree.insert( parent, 'end', iid='ty', text=' Ty__.dat', values=('\t\t --< Trophies >--', 'cFolder'), image=globalData.gui.imageBank('folderIcon') )
				parent = 'ty'

		# Add the file to the treeview (all files in the treeview should be added with the line below, but may be modified elsewhere)
		if usingConvenienceFolders:
			# Add extra space to indent the name from the parent folder name
			description = '     ' + discFile.shortDescription
		else:
			description = discFile.longDescription
		
		try:
			# The following commented-out code is occasionally used for some ad-hoc testing.

			# altPath = 'GALE01/' + discFile.filename.replace( '.usd', '.dat' )
			# if discFile.filename.endswith( '.usd' ) and altPath in globalData.disc.files:
			# 	print discFile.filename, humansize(discFile.size)
			# if discFile.filename.endswith( '.mth' ):
			# 	print discFile.filename

			# if discFile.__class__.__name__ == 'CharDataFile':

			# if discFile.filename == 'PlCa.dat':# or discFile.filename == 'PlCa.sat':
			# 	table = discFile.getActionTable()
			# 	print 'Fighter Action Tables:'
			# 	print discFile.filename, hex( table.offset + 0x20 )

			# 	for i, values in table.iterateEntries():
			# 		actionName = discFile.getString( values[0] )
			# 		# offsetInTable = table.entryIndexToOffset( i )
			# 		# print '\t', i, ' | ', uHex( offsetInTable + 0x20 ), actionName	# show subAction struct offsets
			# 		print '\t', i, ' | ', uHex( values[3] + 0x20 ), actionName		# show subAction table entry offsets

			# if discFile.filename.endswith( 'AJ.dat') and 'Wait' not in discFile.filename:
			# 	print discFile.filename, hex(discFile.size)

			# if ( discFile.filename.endswith( 'at' ) or  discFile.filename.endswith( 'sd' ) ) and discFile.size > 4000000:
			# 	print( discFile.filename, ': ', hex(discFile.size), discFile.size )

			# if issubclass( discFile.__class__, DatFile ):
			# 	discFile.initialize()
			# 	if discFile.headerInfo and discFile.headerInfo['rtEntryCount'] > 10000:
			# 		print( discFile.filename, ': ', discFile.headerInfo['rtEntryCount'] )

			# if discFile.filename == 'PlZdWh.dat':
			# 	discFile.initialize()
			# 	s1 = discFile.getStruct( 0xAC64 )
			# 	#s1 = discFile.getSkeleton()
			# 	s2 = discFile.getStruct( 0xA9FC )
			# 	structsEquivalent = discFile.structuresEquivalent( s1, s2, False )
			# 	print( '0x{:x} equivalent to 0x{:x}: {}'.format(s1.offset, s2.offset, structsEquivalent) )

			# if issubclass( discFile.__class__, CharCostumeFile ) and not discFile.filename.endswith( 'Nr.dat' ):# and discFile.filename.startswith( 'PlCaGr' ):
			# 	# Check for Nr costume
			# 	defaultCostume = globalData.disc.files.get( 'GALE01/Pl' + discFile.charAbbr + 'Nr.dat' )
			# 	if defaultCostume:
			# 		#structsEquivalent = discFile.structuresEquivalent( defaultCostume.getSkeleton(), discFile.getSkeleton(), True, [DisplayObjDesc] )
			# 		structsEquivalent = discFile.structuresEquivalent( defaultCostume.getSkeleton(), discFile.getSkeleton(), True, None, [JointObjDesc, InverseMatrixObjDesc] )
			# 		print( discFile.charAbbr + discFile.colorAbbr + ' skele equivalent to Nr costume: ' + str(structsEquivalent) )
			
			self.isoFileTree.insert( parent, 'end', iid=discFile.isoPath, text=' ' + entryName, values=(description, 'file') )
		except Exception as err:
			printStatus( u'Unable to add {} to the Disc File Tree; {}'.format(discFile.longDescription, err) )

	def scanDiscItemForStats( self, iidSelectionsTuple, folderContents ):

		""" This is a recursive helper function to get the file size of 
			all files in a given folder, along with total file count. """

		discFiles = globalData.disc.files
		totalFileSize = 0
		fileCount = 0

		for iid in folderContents:
			if iid not in iidSelectionsTuple: # Ensures that nothing is counted twice.
				fileItem = discFiles.get( iid, None )

				if fileItem:
					totalFileSize += int( fileItem.size )
					fileCount += 1
				else: # Must be a folder if not found in the disc's file dictionary
					# Search the inner folder, and add the totals of the children within to the current count.
					folderSize, folderFileCount = self.scanDiscItemForStats( iidSelectionsTuple, self.isoFileTree.get_children(iid) )
					totalFileSize += folderSize
					fileCount += folderFileCount

		return totalFileSize, fileCount

	def quickLinkClicked( self, event ):

		""" Scrolls the treeview in the Disc File Tree tab directly to a specific section.
			If a disc is not already loaded, the most recent disc that has been loaded in
			the program is loaded, and then scrolled to the respective section. """

		discNewlyLoaded = False

		# Load the most recent disc if one is not loaded
		if not globalData.disc: # todo: remove this? may never be the case anymore that this tab exists without a disc being loaded
			# Check that there are any recently loaded discs (in the settings file).
			recentISOs = globalData.getRecentFilesLists()[0] # The resulting list is a list of tuples, of the form (path, dateLoaded)

			if not recentISOs:
				# No recent discs found. Prompt to open one.
				globalData.gui.promptToOpenFile( 'iso' )
				discNewlyLoaded = True

			else: # ISOs found. Load the most recently used one
				recentISOs.sort( key=lambda recentInfo: recentInfo[1], reverse=True )
				pathToMostRecentISO = recentISOs[0][0].replace('|', ':')

				# Confirm the file still exists in the same place
				if os.path.exists( pathToMostRecentISO ):
					# Path validated. Load it. Don't update the details tab yet, since that will incur waiting for the banner animation
					globalData.gui.fileHandler( [pathToMostRecentISO], updateDefaultDirectory=False, updateDetailsTab=False )
					discNewlyLoaded = True

				else: # If the file wasn't found above, prompt if they'd like to remove it from the remembered files list.
					if askyesno( 'Remove Broken Path?', 'The following file could not be found:\n"' + pathToMostRecentISO + '" .\n\nWould you like to remove it from the list of recent files?' ):
						# Update the list of recent ISOs in the settings object and settings file.
						globalData.settings.remove_option( 'Recent Files', pathToMostRecentISO.replace(':', '|') )
						with open( globalData.paths['settingsFile'], 'w') as theSettingsFile: globalData.settings.write( theSettingsFile )
					return

		# Scroll to the appropriate section
		target = event.widget['text']
		self.scrollToSection( target )

		# If the disc was just now loaded, the banner and disc details will still need to be updated.
		# The function to scan the ISO will have deliberately skipped this step during the loading above,
		# so that scrolling will happen without having to wait on the banner animation.
		# if discNewlyLoaded:
		# 	self.isoFileTree.update() # Updates the GUI first so that the scroll position is instanly reflected
		# 	populateDiscDetails()

	def scanDiscForFile( self, searchString, parentToSearch='' ):
		
		""" Recursively searches the given string in all file name portions of iids in the file tree. """

		foundIid = ''

		for iid in self.isoFileTree.get_children( parentToSearch ):
			if iid.split( '/' )[-1].startswith( searchString ):
				return iid

			if self.isoFileTree.item( iid, 'values' )[1] != 'file': # May be "file", "nFolder" (native folder), or "cFolder" (convenience folder)
				foundIid = self.scanDiscForFile( searchString, iid ) # This might be a folder, try scanning its children
				if foundIid: break

		# If looking for one of the header files, but it wasn't found, try for "ISO.hdr" instead (used in place of boot.bin/bi2.bin by discs built by GCRebuilder)
		# if not foundIid and ( searchString == 'boot.bin' or searchString == 'bi2.bin' ):
		# 	foundIid = scanDiscForFile( 'iso.hdr' )

		return foundIid

	def scrollToSection( self, target ):

		""" Used primarily by the 'quick links' at the top of the 
			Disc File Tree to jump to a specific section.
			
			The "target" may be any of the following:
				System
				Characters
				Menus
				Stages
				Or any existing iid/isoPath in the treeview
		"""

		isoFileTreeChildren = self.isoFileTree.get_children()
		if not isoFileTreeChildren: return

		rootParent = isoFileTreeChildren[0]
		#self.isoFileTree.item( rootParent, open=True )
		self.isoFileTree.see( rootParent )
		globalData.gui.root.update()
		indexOffset = 19
		iid = ''

		# Determine the iid of the file to move the scroll position to
		if target == 'System':
			self.isoFileTree.yview_moveto( 0 )
			iid = rootParent + '/Start.dol'

		elif target == 'Characters':
			# Check for the complimentary folder
			if self.isoFileTree.exists( 'pl' ):
				iidTuple = self.isoFileTree.get_children( 'pl' )
				if len( iidTuple ) > 0:
					iid = iidTuple[0]
			else:
				iid = self.scanDiscForFile( 'Pl' ) # previously: 'plgk.dat'

		elif target == 'Menus':
			iid = self.scanDiscForFile( 'MnExtAll.' )
			indexOffset = 14

		elif target == 'Stages':
			# Check for the complimentary folder
			if self.isoFileTree.exists( 'gr' ):
				iidTuple = self.isoFileTree.get_children( 'gr' )
				if len( iidTuple ) > 0:
					iid = iidTuple[0]
			else:
				iid = self.scanDiscForFile( 'Gr' )
				#if not iid: iid = self.scanDiscForFile( 'grcn.dat' )

		elif target == 'Strings':
			# Check for the complimentary folder
			if self.isoFileTree.exists( 'sd' ):
				iidTuple = self.isoFileTree.get_children( 'sd' )
				if len( iidTuple ) > 0:
					iid = iidTuple[0]
			else:
				iid = self.scanDiscForFile( 'Sd' )

		elif self.isoFileTree.exists( target ):
			iid = target

		# If an item target was determined, scroll to it
		if iid:
			targetItemIndex = self.isoFileTree.index( iid ) + indexOffset # Offset applied so that the target doesn't actually end up exactly in the center

			# Target the parent folder if it's in one
			if self.isoFileTree.parent( iid ) == globalData.disc.gameId: # Means the target file is in root, not in a folder
				iidToSelect = iid
			else:
				iidToSelect = self.isoFileTree.parent( iid )

			# Set the current selection and keyboard focus
			self.isoFileTree.selection_set( iidToSelect )
			self.isoFileTree.focus( iidToSelect )
			targetItemSiblings = self.isoFileTree.get_children( self.isoFileTree.parent( iid ) )

			# Scroll to the target section (folders will be opened as necessary for visibility)
			if targetItemIndex > len( targetItemSiblings ): self.isoFileTree.see( targetItemSiblings[-1] )
			else: self.isoFileTree.see( targetItemSiblings[targetItemIndex] )

	def onFileTreeSelect( self, event ):

		""" Called when an item (file or folder) in the Disc File Tree is selected. Iterates over 
			the selected items, calculates total file(s) size, and displays it in the GUI. """

		iidSelectionsTuple = self.isoFileTree.selection()
		if len( iidSelectionsTuple ) == 0:
			return

		discFiles = globalData.disc.files
		totalFileSize = 0
		fileCount = 0

		# Get the collective size of all items currently selected
		for iid in iidSelectionsTuple:
			discFile = discFiles.get( iid, None )

			if discFile:
				totalFileSize += int( discFile.size )
				fileCount += 1
			else: # Must be a folder if not found in the disc's file dictionary
				folderSize, folderFileCount = self.scanDiscItemForStats( iidSelectionsTuple, self.isoFileTree.get_children(iid) )
				totalFileSize += folderSize
				fileCount += folderFileCount

		# Update the Offset and File Size values in the GUI.
		if len( iidSelectionsTuple ) == 1 and discFile: # If there's only one selection and it's a file.
			if discFile.offset == -1: self.isoOffsetText.set( 'Disc Offset:  N/A (External)' ) # Must be a standalone (external) file
			else: self.isoOffsetText.set( 'Disc Offset:  ' + uHex(discFile.offset) )
			self.internalFileSizeText.set( 'File Size:  {0:,} bytes'.format(totalFileSize) ) # Formatting in decimal with thousands delimiter commas
			self.internalFileSizeLabelSecondLine.set( '' )

		else: # A folder or multiple selections
			self.isoOffsetText.set( 'Disc Offset:  N/A' )
			self.internalFileSizeText.set( 'File Size:  {0:,} bytes'.format(totalFileSize) ) # Formatting in decimal with thousands delimiter commas
			self.internalFileSizeLabelSecondLine.set( '    (Totaled from {0:,} files)'.format(fileCount) )

	def getDiscPath( self, isoPath, useConvenienceFolders, includeRoot=True, addDolphinSubs=False ):

		""" Builds a disc path, like isoPath, but includes convenience folders if they are turned on. 
			Only if not using convenience folders may the "sys"/"files" folders be included. """

		if useConvenienceFolders:
			# Scan for 'convenience folders' (those not actually in the disc), and add them to the path; they won't exist in isoPath
			rootIid = self.isoFileTree.get_children()[0]
			isoParts = isoPath.split( '/' )
			pathParts = [ isoParts[-1] ] # Creating a list, starting with just the filename
			parentIid = self.isoFileTree.parent( isoPath )

			while parentIid and parentIid != rootIid: # End at the root/GameID folder (first condition is a failsafe)
				parentFolderText = self.isoFileTree.item( parentIid, 'text' ).strip()

				# for character in ( '\\', '/', ':', '*', '?', '"', '<', '>', '|' ): # Remove illegal characters
				# 	parentFolderText = parentFolderText.replace( character, '-' )
				parentFolderText = removeIllegalCharacters( parentFolderText )
				pathParts.insert( 0, parentFolderText )

				parentIid = self.isoFileTree.parent( parentIid )

			if includeRoot:
				pathParts.insert( 0, isoParts[0] )

			return '/'.join( pathParts )

		elif not includeRoot: # Return the full path, but without the root (GameID)
			pathParts = isoPath.split( '/' )

			# if addDolphinSubs and pathParts[-1] in Disc.systemFiles:
			# 	return 'sys/' + pathParts[-1]
			# elif addDolphinSubs:
			# 	return 'files/' + pathParts[-1]
			# else:
			return '/'.join( pathParts[1:] ) # Just removes the GameID

		# elif addDolphinSubs: # Include root and sys folder for system files
		# 	pathParts = isoPath.split( '/' )

		# 	if pathParts[-1] in Disc.systemFiles:
		# 		return pathParts[0] + '/sys/' + pathParts[-1]
		# 	else:
		# 		return pathParts[0] + '/files/' + pathParts[-1]
		else:
			return isoPath

	def exportItemsInSelection( self, selection, isoBinary, directoryPath, exported, failedExports, addDolphinSubs ):

		""" Basically just a recursive helper function to self.exportIsoFiles(). Passing the open isoBinary 
			file object so that we can get file data from it directly, and avoid opening it multiple times. """

		useConvenienceFolders = globalData.checkSetting( 'useConvenienceFoldersOnExport' )

		for iid in selection: # The iids will be isoPaths and/or folder iids
			# Attempt to get a file for this iid (isoPath)
			fileObj = globalData.disc.files.get( iid )

			if fileObj:
				globalData.gui.updateProgramStatus( 'Exporting File ' + str(exported + failedExports + 1) + '....', forceUpdate=True )

				try:
					# Retrieve the file data.
					if fileObj.source == 'disc':
						# Can perform the getData method ourselves for efficiency, since we have the open isoBinary file object
						assert fileObj.offset != -1, 'Invalid file offset for disc export: -1'
						assert fileObj.size != -1, 'Invalid file size for disc export: -1'
						isoBinary.seek( fileObj.offset )
						datData = isoBinary.read( fileObj.size )
					else: # source == 'file' or 'self'
						datData = fileObj.getData()

					# Construct a file path for saving, and destination folders if they don't exist
					if addDolphinSubs and fileObj.filename in Disc.systemFiles:
						savePath = directoryPath + '/sys/' + self.getDiscPath( fileObj.isoPath, useConvenienceFolders, includeRoot=False )
					elif addDolphinSubs:
						savePath = directoryPath + '/files/' + self.getDiscPath( fileObj.isoPath, useConvenienceFolders, includeRoot=False )
					else:
						savePath = directoryPath + '/' + self.getDiscPath( fileObj.isoPath, useConvenienceFolders, includeRoot=False )
					createFolders( os.path.split(savePath)[0] )

					# Save the data to a new file.
					with open( savePath, 'wb' ) as newFile:
						newFile.write( datData )
					exported += 1

				except:
					failedExports += 1

			else: # Item is a folder.
				print( 'Unable to get this file!: ' + str(iid) )
			# 	exported, failedExports = self.exportItemsInSelection( self.isoFileTree.get_children(iid), iidSelectionsTuple, isoBinary, directoryPath, exported, failedExports )

		return exported, failedExports

	def exportIsoFiles( self, addDolphinSubs=False ):

		""" Called by the Export button and Export File(s) menu option. This doesn't use the disc's 
			normal file export method so that we can include the convenience folders in the save path. """

		# Check that there's something selected to export
		iidSelections = self.isoFileTree.getItemsInSelection()[1] # Extends selection to also include all files within folders that may be selected
		if not iidSelections:
			globalData.gui.updateProgramStatus( 'Hm?' )
			msg( 'Please first select a file or folder to export.' )
			return

		# A disc or root folder path must have been loaded at this point (to populate the GUI); make sure its path is still valid
		elif not os.path.exists( globalData.disc.filePath ):
			if globalData.disc.isRootFolder:
				globalData.gui.updateProgramStatus( 'Export Error. Unable to find the currently loaded root folder path.', error=True )
				msg( "Unable to find the root folder path. Be sure that the path is correct and that the folder hasn't been moved or deleted.", 'Root Folder Not Found' )
			else:
				globalData.gui.updateProgramStatus( 'Export Error. Unable to find the currently loaded disc file path.', error=True )
				msg( "Unable to find the disc image. Be sure that the file path is correct and that the file hasn't been moved or deleted.", 'Disc Not Found' )
			return
		
		iid = next( iter(iidSelections) )
		fileObj = globalData.disc.files.get( iid )

		# Check the selection to determine if a single or multiple files need to be exported
		if len( iidSelections ) == 1 and fileObj:
			# Prompt for a place to save the file, save it, and update the GUI
			exportSingleFileWithGui( fileObj )

		else: # A folder or multiple files are selected to be exported. Prompt for a directory to save them to.
			directoryPath = tkFileDialog.askdirectory(
				title='Where would you like to save these files?',
				parent=globalData.gui.root,
				initialdir=globalData.getLastUsedDir(),
				mustexist=True )

			# The above will return an empty string if the user canceled
			if not directoryPath: return

			exported = 0
			failedExports = 0

			# Not using the disc's file export method so we can include the convenience folders in the save path
			with open( globalData.disc.filePath, 'rb' ) as isoBinary:
				exported, failedExports = self.exportItemsInSelection( iidSelections, isoBinary, directoryPath, exported, failedExports, addDolphinSubs )

			if failedExports == 0:
				globalData.gui.updateProgramStatus( 'Files exported successfully.', success=True )
			elif exported > 0: # Had some exports fail
				globalData.gui.updateProgramStatus( '{} file(s) exported successfully. However, {} file(s) failed to export.'.format(exported, failedExports), error=True )
			else:
				globalData.gui.updateProgramStatus( 'Unable to export.', error=True )

			# Update the default directory to start in when opening or exporting files.
			globalData.setLastUsedDir( directoryPath )
	
	def importSingleIsoFile( self ):

		""" Called by the Import button and Import File(s) menu option. This doesn't use the 
			disc's file export method so we can include the convenience folders in the save path. """

		# Check that there's something selected to export
		iidSelectionsTuple = self.isoFileTree.selection()
		if not iidSelectionsTuple:
			globalData.gui.updateProgramStatus( 'Hm?' )
			msg( 'No file is selected.' )
			return

		elif len( iidSelectionsTuple ) != 1:
			globalData.gui.updateProgramStatus( 'Hm?' )
			msg( 'Please select only one file to replace.' )
			return

		# A disc or root folder path must have been loaded at this point (to populate the GUI); make sure its path is still valid
		elif not os.path.exists( globalData.disc.filePath ):
			if globalData.disc.isRootFolder:
				globalData.gui.updateProgramStatus( 'Import Error. Unable to find the currently loaded root folder path.', error=True )
				msg( "Unable to find the root folder path. Be sure that the path is correct and that the folder hasn't been moved or deleted.", 'Root Folder Not Found' )
			else:
				globalData.gui.updateProgramStatus( 'Import Error. Unable to find the currently loaded disc file path.', error=True )
				msg( "Unable to find the disc image. Be sure that the file path is correct and that the file hasn't been moved or deleted.", 'Disc Not Found' )
			return

		# Get the file object and prompt the user to replace it
		fileObj = globalData.disc.files.get( iidSelectionsTuple[0] )
		importSingleFileWithGui( fileObj )

	def browseTexturesFromDisc( self ):
		print( 'Not yet implemented' )
	def analyzeFileFromDisc( self ):
		print( 'Not yet implemented' )

	def deleteIsoFiles( self, iids ):

		""" Removes (deletes) files from the disc, and from the isoFileTree. Folders will 
			automatically be removed from a disc object if all files within it are removed. 
			Note that the iids which the isoFileTree widget uses are isoPaths. """

		folderIids, fileIids = self.isoFileTree.getItemsInSelection( iids )
		discFiles = globalData.disc.files
		fileObjects = []
		reloadAudioTab = False

		# Make sure there are no system files included
		sysFiles = set( globalData.disc.systemFiles )
		sysFiles = { globalData.disc.gameId + '/' + filename for filename in sysFiles } # Need to add the parent name for comparisons
		if set.intersection( sysFiles, fileIids ):
			msg( 'System files cannot be removed from the disc!', 'Invalid Operation' )
			return

		# Collect file objects for the isoPaths collected above
		for isoPath in fileIids:
			# Collect a file object from the disc for this path, and remove it from the GUI
			fileObj = discFiles.get( isoPath )
			assert fileObj, 'IsoFileTree displays a missing file! ' + isoPath
			fileObjects.append( fileObj )
			self.isoFileTree.delete( isoPath )

			if fileObj.__class__.__name__ == 'MusicFile':
				reloadAudioTab = True

		# Remove the folders from the GUI
		for iid in folderIids:
			try: self.isoFileTree.delete( iid )
			except: pass # May have already been removed alongside a parent folder

		# Remove the files from the disc
		globalData.disc.removeFiles( fileObjects )
		
		# Update the Disc Details Tab
		detailsTab = globalData.gui.discDetailsTab
		if detailsTab:
			detailsTab.isoFileCountText.set( "{:,}".format(len(globalData.disc.files)) )
			#detailsTab # todo: disc size as well

		# Update the Audio Manager tab
		audioTab = globalData.gui.audioManagerTab
		if audioTab and reloadAudioTab:
			audioTab.loadFileList()
		
		if len( fileObjects ) == 1:
			globalData.gui.updateProgramStatus( '1 file removed from the disc' )
		else:
			globalData.gui.updateProgramStatus( '{} files removed from the disc'.format(len(fileObjects)) )
	
	def createContextMenu( self, event ):

		""" Spawns a context menu at the mouse's current location. """

		contextMenu = DiscMenu( globalData.gui.root, tearoff=False )
		contextMenu.repopulate()
		contextMenu.post( event.x_root, event.y_root )

	def determineNewFileInsertionKey( self ):

		""" Determines where new files should be added into the disc file and FST. If the user has a 
			file selected in the GUI (in the Disc File Tree), the new files will be added just before it. 
			If a folder is selected, it's presumed that they would like to add it to the end of that folder. 
			However, since it's likely a convenience folder (one not actually in the disc), the best attempt 
			is to add to the disc before the first file following the folder. """

		targetIid = self.isoFileTree.selection()

		# If there's a current selection in the treeview, use that file as a reference point, and insert the new file above it
		if targetIid:
			targetIid = targetIid[-1] # Simply selects the lowest position item selected (if there are multiple)
			parent = self.isoFileTree.parent( targetIid )
			
			if globalData.checkSetting( 'alwaysAddFilesAlphabetically' ):
				return parent, ''

			# # Remove the last portion of the disc path if it's a file or Convenience Folder
			#fileObj = globalData.disc.files.get( targetIid ) # The iids are isoPaths
			itemType = self.isoFileTree.item( targetIid, 'values' )[1] # May be "file", "nFolder" (native folder), or "cFolder" (convenience folder)
			if itemType == 'file':
				iidToAddBefore = targetIid
			else: # Folder selected
				# Seek out the first file not in this folder
				inFolder = False
				for isoPath in globalData.disc.files.iterkeys():
					parent = self.isoFileTree.parent( isoPath )
					if parent == targetIid:
						inFolder = True
					elif inFolder: # Parent is no longer the target (currently selected) iid
						iidToAddBefore = isoPath
						break
				else: # Loop above didn't break; reached the end
					iidToAddBefore = 'end'

		elif globalData.checkSetting( 'alwaysAddFilesAlphabetically' ):
			parent = globalData.disc.gameId
			iidToAddBefore = ''

		else:
			parent = globalData.disc.gameId
			iidToAddBefore = 'end'

		return parent, iidToAddBefore


class DiscDetailsTab( ttk.Frame ):

	def __init__( self, parent, mainGui ):

		ttk.Frame.__init__( self, parent ) #, padding="11 0 0 11" ) # Padding order: Left, Top, Right, Bottom.
		
		# Add this tab to the main GUI, and add drag-and-drop functionality
		mainGui.mainTabFrame.add( self, text=' Disc Details ' )
		#self.dnd.bindtarget( self.discDetailsTab, lambda event: mainGui.dndHandler( event, 'discTab' ), 'text/uri-list' ) # Drag-and-drop functionality treats this as the discTab
		mainGui.dnd.bindtarget( self, mainGui.dndHandler, 'text/uri-list' )

		self.mainGui = mainGui
		self.bannerFile = None
		
			# Row 1 | Disc file path entry
		self.row1 = ttk.Frame( self, padding=12 )
		ttk.Label( self.row1, text=" ISO / GCM:" ).pack( side='left' )
		self.isoDestination = Tk.StringVar()
		isoDestEntry = ttk.Entry( self.row1, textvariable=self.isoDestination ) #, takefocus=False
		isoDestEntry.pack( side='left', fill='x', expand=1, padx=12 )
		isoDestEntry.bind( '<Return>', self.openIsoDestination )
		self.row1.pack( fill='x' )

			# Row 2, Column 0 & 1 | Game ID
		self.row2 = ttk.Frame( self, padding=0 )
		self.row2.padx = 5
		self.row2.gameIdLabel = ttk.Label( self.row2, text='Game ID:' )
		self.row2.gameIdLabel.grid( column=0, row=0, rowspan=4, padx=self.row2.padx )
		self.gameIdTextEntry = DisguisedEntry( self.row2, respectiveLabel=self.row2.gameIdLabel, 
												background=mainGui.defaultSystemBgColor, textvariable=mainGui.discTab.gameIdText, width=8 )
		self.gameIdTextEntry.grid( column=1, row=0, rowspan=4, padx=self.row2.padx )
		self.gameIdTextEntry.offset = 0
		self.gameIdTextEntry.maxByteLength = 6
		self.gameIdTextEntry.updateName = 'Game ID'
		self.gameIdTextEntry.bind( '<Return>', self.saveBootFileDetails )

			# Row 2, Column 2/3/4 | Game ID break-down
		ttk.Label( self.row2, image=mainGui.imageBank('gameIdBreakdownImage') ).grid( column=2, row=0, rowspan=4, padx=self.row2.padx )
		self.consoleIdText = Tk.StringVar()
		self.gameCodeText = Tk.StringVar()
		self.regionCodeText = Tk.StringVar()
		self.makerCodeText = Tk.StringVar()
		ttk.Label( self.row2, text='Console ID:' ).grid( column=3, row=0, sticky='e', padx=self.row2.padx )
		ttk.Label( self.row2, textvariable=self.consoleIdText, width=3 ).grid( column=4, row=0, sticky='w', padx=self.row2.padx )
		ttk.Label( self.row2, text='Game Code:' ).grid( column=3, row=1, sticky='e', padx=self.row2.padx )
		ttk.Label( self.row2, textvariable=self.gameCodeText, width=3 ).grid( column=4, row=1, sticky='w', padx=self.row2.padx )
		ttk.Label( self.row2, text='Region Code:' ).grid( column=3, row=2, sticky='e', padx=self.row2.padx )
		ttk.Label( self.row2, textvariable=self.regionCodeText, width=3 ).grid( column=4, row=2, sticky='w', padx=self.row2.padx )
		ttk.Label( self.row2, text='Maker Code:' ).grid( column=3, row=3, sticky='e', padx=self.row2.padx )
		ttk.Label( self.row2, textvariable=self.makerCodeText, width=3 ).grid( column=4, row=3, sticky='w', padx=self.row2.padx )

		ttk.Separator( self.row2, orient='vertical' ).grid( column=5, row=0, sticky='ns', rowspan=4, padx=self.row2.padx, pady=6 )

			# Row 2, Column 6 | Banner Image
		self.bannerCanvas2 = Tk.Canvas( self.row2, width=96, height=32, borderwidth=0, highlightthickness=0 )
		self.bannerCanvas2.grid( column=6, row=1, rowspan=2, padx=self.row2.padx )
		self.bannerCanvas2.pilImage = None
		self.bannerCanvas2.bannerGCstorage = None
		self.bannerCanvas2.canvasImageItem = None

		bannerImportExportFrame = ttk.Frame( self.row2 )
		bannerExportLabel = ttk.Label( bannerImportExportFrame, text='Export', foreground='#00F', cursor='hand2' )
		#bannerExportLabel.bind( '<1>', exportBanner )
		bannerExportLabel.pack( side='left' )
		ttk.Label( bannerImportExportFrame, text=' | ' ).pack( side='left' )
		bannerImportLabel = ttk.Label( bannerImportExportFrame, text='Import', foreground='#00F', cursor='hand2' )
		#bannerImportLabel.bind( '<1>', importImageFiles )
		bannerImportLabel.pack( side='left' )
		bannerImportExportFrame.grid( column=6, row=3, padx=self.row2.padx )

		ttk.Separator( self.row2, orient='vertical' ).grid( column=7, row=0, sticky='ns', rowspan=4, padx=self.row2.padx, pady=6 )

			# Row 2, Column 8/9 | Disc Revision, 20XX Version, and Disc Size
		self.isoVersionText = Tk.StringVar()
		#twentyxxVersionText = Tk.StringVar()
		self.isoFileCountText = Tk.StringVar()
		self.isoFilesizeText = Tk.StringVar()
		self.isoFilesizeTextLine2 = Tk.StringVar()
		ttk.Label( self.row2, text='Disc Revision:' ).grid( column=8, row=0, sticky='e', padx=self.row2.padx )
		ttk.Label( self.row2, textvariable=self.isoVersionText ).grid( column=9, row=0, sticky='w', padx=self.row2.padx )
		#ttk.Label( self.row2, text='20XX Version:' ).grid( column=8, row=1, sticky='e', padx=self.row2.padx )
		#ttk.Label( self.row2, textvariable=twentyxxVersionText ).grid( column=9, row=1, sticky='w', padx=self.row2.padx )
		ttk.Label( self.row2, text='Total File Count:' ).grid( column=8, row=2, sticky='e', padx=self.row2.padx )
		ttk.Label( self.row2, textvariable=self.isoFileCountText ).grid( column=9, row=2, sticky='w', padx=self.row2.padx )
		ttk.Label( self.row2, text='Disc Size:' ).grid( column=8, row=3, sticky='e', padx=self.row2.padx )
		ttk.Label( self.row2, textvariable=self.isoFilesizeText ).grid( column=9, row=3, sticky='w', padx=self.row2.padx )
		ttk.Label( self.row2, textvariable=self.isoFilesizeTextLine2 ).grid( column=8, row=4, columnspan=2, sticky='e', padx=self.row2.padx )

		self.row2.pack( padx=15, pady=0, expand=1 )

		# Set cursor hover bindings for the help text
		# previousLabelWidget = ( None, '' )
		# for widget in self.row2.winfo_children(): # Widgets will be listed in the order that they were added to the parent

		# 	if widget.winfo_class() == 'TLabel' and ':' in widget['text']: # Bindings for the preceding Label
		# 		updateName = widget['text'].replace(':', '')
		# 		widget.bind( '<Enter>', lambda event, helpTextName=updateName: setDiscDetailsHelpText(helpTextName) )
		# 		widget.bind( '<Leave>', setDiscDetailsHelpText )
		# 		previousLabelWidget = ( widget, updateName )

		# 	elif previousLabelWidget[0]: # Bindings for the labels displaying the value/info
		# 		widget.bind( '<Enter>', lambda event, helpTextName=previousLabelWidget[1]: setDiscDetailsHelpText(helpTextName) )
		# 		widget.bind( '<Leave>', setDiscDetailsHelpText )
		# 		previousLabelWidget = ( None, '' )

		# 	elif widget.grid_info()['row'] == '4': # For the second label for isoFilesize
		# 		widget.bind( '<Enter>', lambda event: setDiscDetailsHelpText('Disc Size') )
		# 		widget.bind( '<Leave>', setDiscDetailsHelpText )

		# Enable resizing for the above grid columns
		self.row2.columnconfigure( 2, weight=0 ) # Allows the middle column (the actual text input fields) to stretch with the window
		self.row2.columnconfigure( 4, weight=1 )
		self.row2.columnconfigure( 5, weight=0 )
		self.row2.columnconfigure( 6, weight=1 )
		self.row2.columnconfigure( 7, weight=0 )
		self.row2.columnconfigure( 8, weight=1 )
		virtualLabel = ttk.Label( self, text='0,000,000,000 bytes' ) # Used to figure out how much space various fonts/sizes will require
		predictedComfortableWidth = int( virtualLabel.winfo_reqwidth() * 1.2 ) # This should be plenty of space for the total disc size value.
		self.row2.columnconfigure( 9, weight=1, minsize=predictedComfortableWidth )

				# The start of row 3
		self.row3 = Tk.Frame( self ) # Uses a grid layout for its children
		self.shortTitle = Tk.StringVar()
		self.shortMaker = Tk.StringVar()
		self.longTitle = Tk.StringVar()
		self.longMaker = Tk.StringVar()

		borderColor1 = '#b7becc'; borderColor2 = '#0099f0'
		ttk.Label( self.row3, text='Image Name:' ).grid( column=0, row=0, sticky='e' )
		self.gameName1Field = Tk.Text( self.row3, height=3, highlightbackground=borderColor1, highlightcolor=borderColor2, highlightthickness=1, borderwidth=0 )
		gameName1FieldScrollbar = Tk.Scrollbar( self.row3, command=self.gameName1Field.yview ) # This is used instead of just a ScrolledText widget because getattr() won't work on the latter
		self.gameName1Field['yscrollcommand'] = gameName1FieldScrollbar.set
		self.gameName1Field.grid( column=1, row=0, columnspan=2, sticky='ew' )
		gameName1FieldScrollbar.grid( column=3, row=0 )
		self.gameName1Field.offset = 0x20; self.gameName1Field.maxByteLength = 992; self.gameName1Field.updateName = 'Image Name'
		ttk.Label( self.row3, text='992' ).grid( column=4, row=0, padx=5 )
		textWidgetFont = self.gameName1Field['font']

		ttk.Label( self.row3, text='Short Title:' ).grid( column=0, row=1, sticky='e' )
		gameName2Field = Tk.Entry( self.row3, width=32, textvariable=self.shortTitle, highlightbackground=borderColor1, highlightcolor=borderColor2, highlightthickness=1, borderwidth=0, font=textWidgetFont )
		gameName2Field.grid( column=1, row=1, columnspan=2, sticky='w' )
		gameName2Field.offset = 0x1820; gameName2Field.maxByteLength = 32; gameName2Field.updateName = 'Short Title'
		ttk.Label( self.row3, text='32' ).grid( column=4, row=1 )

		ttk.Label( self.row3, text='Short Maker:' ).grid( column=0, row=2, sticky='e' )
		developerField = Tk.Entry( self.row3, width=32, textvariable=self.shortMaker, highlightbackground=borderColor1, highlightcolor=borderColor2, highlightthickness=1, borderwidth=0, font=textWidgetFont )
		developerField.grid( column=1, row=2, columnspan=2, sticky='w' )
		developerField.offset = 0x1840; developerField.maxByteLength = 32; developerField.updateName = 'Short Maker'
		ttk.Label( self.row3, text='32' ).grid( column=4, row=2 )

		ttk.Label( self.row3, text='Long Title:' ).grid( column=0, row=3, sticky='e' )
		fullGameTitleField = Tk.Entry( self.row3, width=64, textvariable=self.longTitle, highlightbackground=borderColor1, highlightcolor=borderColor2, highlightthickness=1, borderwidth=0, font=textWidgetFont )
		fullGameTitleField.grid( column=1, row=3, columnspan=2, sticky='w' )
		fullGameTitleField.offset = 0x1860; fullGameTitleField.maxByteLength = 64; fullGameTitleField.updateName = 'Long Title'
		ttk.Label( self.row3, text='64' ).grid( column=4, row=3 )

		ttk.Label( self.row3, text='Long Maker:' ).grid( column=0, row=4, sticky='e' )
		devOrDescField = Tk.Entry( self.row3, width=64, textvariable=self.longMaker, highlightbackground=borderColor1, highlightcolor=borderColor2, highlightthickness=1, borderwidth=0, font=textWidgetFont )
		devOrDescField.grid( column=1, row=4, columnspan=2, sticky='w' )
		devOrDescField.offset = 0x18a0; devOrDescField.maxByteLength = 64; devOrDescField.updateName = 'Long Maker'
		ttk.Label( self.row3, text='64' ).grid( column=4, row=4 )

		ttk.Label( self.row3, text='Comment:' ).grid( column=0, row=5, sticky='e' )
		self.gameDescField = Tk.Text( self.row3, height=2, highlightbackground=borderColor1, highlightcolor=borderColor2, highlightthickness=1, borderwidth=0 )
		self.gameDescField.grid( column=1, row=5, columnspan=2, sticky='ew' )
		self.gameDescField.offset = 0x18e0; self.gameDescField.maxByteLength = 128; self.gameDescField.updateName = 'Comment'
		self.gameDescField.bind( '<Shift-Return>', self.disallowLineBreaks )
		ttk.Label( self.row3, text='128' ).grid( column=4, row=5 )

		ttk.Label( self.row3, text='Encoding:' ).grid( column=0, row=6, sticky='e' )
		self.encodingFrame = ttk.Frame( self.row3 )
		self.countryCode = Tk.StringVar()
		self.countryCode.set( 'us' ) # This is just a default. Officially set when a disc is loaded
		Tk.Radiobutton( self.encodingFrame, text='English/EU (Latin_1)', variable=self.countryCode, value='us', command=self.reloadBanner ).pack( side='left', padx=(9,6) )
		Tk.Radiobutton( self.encodingFrame, text='Japanese (Shift_JIS)', variable=self.countryCode, value='jp', command=self.reloadBanner ).pack( side='left', padx=6 )
		self.encodingFrame.grid( column=1, row=6, sticky='w' )
		ttk.Label( self.row3, text='Max Characters/Bytes ^  ' ).grid( column=2, row=6, columnspan=3, sticky='e' )

		# Add event handlers for the updating function and help/hover text (also sets x/y padding)
		# children = self.row3.winfo_children()
		# previousWidget = children[0]
		# for widget in children: 
		# 	widget.grid_configure( padx=4, pady=3 )
		# 	updateName = getattr( widget, 'updateName', None )

		# 	if updateName:
		# 		# Cursor hover bindings for the preceding Label
		# 		previousWidget.bind( '<Enter>', lambda event, helpTextName=updateName: setDiscDetailsHelpText(helpTextName) )
		# 		previousWidget.bind( '<Leave>', setDiscDetailsHelpText )

		# 		# Data entry (pressing 'Enter') and cursor hover bindings for the text entry field
		# 		if updateName == 'Image Name':
		# 			widget.bind( '<Return>', self.saveBootFileDetails )
		# 		else:
		# 			widget.bind( '<Return>', self.saveBannerFileDetails )
		# 		widget.bind( '<Enter>', lambda event, helpTextName=updateName: setDiscDetailsHelpText(helpTextName) )
		# 		widget.bind( '<Leave>', setDiscDetailsHelpText )
		# 	previousWidget = widget

		self.row3.columnconfigure( 1, weight=1 ) # Allows the middle column (the actual text input fields) to stretch with the window
		self.row3.pack( fill='both', expand=1, padx=15, pady=4 )

				# The start of row 4
		# self.textHeightAssementWidget = ttk.Label( mainGui.root, text=' \n \n \n ' )
		# self.textHeightAssementWidget.pack( side='bottom' )
		# self.textHeightAssementWidget.update()
		# theHeightOf4Lines = self.textHeightAssementWidget.winfo_height() # A dynamic value for differing system/user font sizes
		# self.textHeightAssementWidget.destroy()

		ttk.Separator( self, orient='horizontal' ).pack( fill='x', expand=1, padx=30 )
		self.row4 = ttk.Frame( self, padding='0 0 0 12' ) # Padding order: Left, Top, Right, Bottom., height=theHeightOf4Lines
		self.discDetailsTabHelpText = Tk.StringVar()
		self.discDetailsTabHelpText.set( "Hover over an item to view information on it.\nPress 'Enter' to submit changes in a text input field before saving." )
		self.helpTextLabel = ttk.Label( self.row4, textvariable=self.discDetailsTabHelpText, wraplength=680 ) #, background='white'
		self.helpTextLabel.pack( expand=1, pady=0 )
		self.row4.pack( expand=1, fill='both' )
		#self.row4.pack_propagate( False )

		# Establish character length validation (for all input fields on this tab), and updates between the GameID labels
		mainGui.discTab.gameIdText.trace( 'w', lambda nm, idx, mode, var=mainGui.discTab.gameIdText: self.validateInput(var, 6) )
		# self.consoleIdText.trace( 'w', lambda nm, idx, mode, var=self.consoleIdText: self.validateInput(var, 1) )
		# self.gameCodeText.trace( 'w', lambda nm, idx, mode, var=self.gameCodeText: self.validateInput(var, 2) )
		# self.regionCodeText.trace( 'w', lambda nm, idx, mode, var=self.regionCodeText: self.validateInput(var, 1) )
		# self.makerCodeText.trace( 'w', lambda nm, idx, mode, var=self.makerCodeText: self.validateInput(var, 2) )

		#gameName1Text.trace( 'w', lambda nm, idx, mode, var=gameName1Text: self.validateInput(var, 992) ) # Validated on saving instead, because it's a ScrolledText
		self.shortTitle.trace( 'w', lambda nm, idx, mode, var=self.shortTitle: self.validateInput(var, 32) )
		self.shortMaker.trace( 'w', lambda nm, idx, mode, var=self.shortMaker: self.validateInput(var, 32) )
		self.longTitle.trace( 'w', lambda nm, idx, mode, var=self.longTitle: self.validateInput(var, 64) )
		self.longMaker.trace( 'w', lambda nm, idx, mode, var=self.longMaker: self.validateInput(var, 64) )

	def validateInput( self, stringVar, maxCharacters ):

		""" Validates character length of user input. """

		enteredValue = stringVar.get()

		# Truncate strings for all fields except Game Id text and the Image Name (which is validated upon saving)
		if len( enteredValue ) > maxCharacters:
			stringVar.set( enteredValue[:maxCharacters] )

		# Update all of the game ID strings
		elif stringVar == self.mainGui.discTab.gameIdText:
			self.consoleIdText.set( '' )
			self.gameCodeText.set( '' )
			self.regionCodeText.set( '' )
			self.makerCodeText.set( '' )
			if len(enteredValue) > 0: self.consoleIdText.set( enteredValue[0] )
			if len(enteredValue) > 1: self.gameCodeText.set( enteredValue[1:3] )
			if len(enteredValue) > 3: self.regionCodeText.set( enteredValue[3] )
			if len(enteredValue) > 4: self.makerCodeText.set( enteredValue[4:7] )
		
	def disallowLineBreaks( self, event ):
		return 'break' # Meant to halt event propagation for certain key presses

	def openIsoDestination( self, event ):

		""" This is only called by pressing Enter/Return on the top file path display/entry of
			the Disc Details tab. Verifies the given path and loads the file for viewing. """

		filepath = self.isoDestination.get().replace( '"', '' )
		self.mainGui.fileHandler( [filepath] )
			
	def loadDiscDetails( self, discSize=0 ):

		""" This primarily updates the Disc Details Tab using information from Boot.bin/ISO.hdr (so a disc should already be loaded); 
			it directly handles updating the fields for disc filepath, gameID (and its breakdown), region and version, image name,
			20XX version (if applicable), and disc file size.

			The disc's country code is also found, which is used to determine the encoding of the banner file.
			A call to update the banner image and other disc details is also made in this function.

			This function also updates the disc filepath on the Disc File Tree tab (and the hover/tooltip text for it). """

		disc = globalData.disc
		discTab = self.mainGui.discTab

		# Set the filepath field in the GUI, and create a shorthand string that will fit nicely on the Disc File Tree tab
		self.isoDestination.set( disc.filePath )
		discTab.isoOverviewFrame.update_idletasks()
		frameWidth = discTab.isoOverviewFrame.winfo_width()
		accumulatingName = ''
		for character in reversed( disc.filePath ):
			accumulatingName = character + accumulatingName
			discTab.isoPathShorthand.set( accumulatingName )
			if discTab.isoPathShorthandLabel.winfo_reqwidth() > frameWidth:
				# Reduce the path to the closest folder (that fits in the given space)
				normalizedPath = os.path.normpath( accumulatingName[1:] )
				if '\\' in normalizedPath: discTab.isoPathShorthand.set( '\\' + '\\'.join( normalizedPath.split('\\')[1:] ) )
				else: discTab.isoPathShorthand.set( '...' + normalizedPath[3:] ) # Filename is too long to fit; show as much as possible
				break
		ToolTip( discTab.isoPathShorthandLabel, disc.filePath, delay=500, wraplength=400, follow_mouse=1 )

		# Look up info within boot.bin (gameID, disc version, and disc region)
		#bootBinData = getFileDataFromDiscTreeAsBytes( iid=scanDiscForFile('boot.bin') )
		# bootBinData = disc.files[disc.gameId + '/Boot.bin'].getData()
		# if not bootBinData: 
		# 	missingFiles.append( 'boot.bin or ISO.hdr' )
		# 	self.gameIdText.set( '' )
		# 	self.isoVersionText.set( '' )
		# 	imageName = ''
		# else:
		# 	gameId = bootBinData[:6].decode( 'ascii' ) # First 6 bytes
		# 	self.gameIdText.set( gameId )
		# 	versionHex = hexlify( bootBinData[7:8] ) # Byte 7
		# 	ntscRegions = ( 'A', 'E', 'J', 'K', 'R', 'W' )
		# 	if gameId[3] in ntscRegions: self.isoVersionText.set( 'NTSC 1.' + versionHex )
		# 	else: self.isoVersionText.set( 'PAL 1.' + versionHex )
		# 	imageName = bootBinData[0x20:0x20 + 0x3e0].split('\x00')[0].decode( 'ascii' ) # Splitting on the first stop byte

		discTab.gameIdText.set( disc.gameId )
		ntscRegions = ( 'A', 'E', 'J', 'K', 'R', 'W' )
		if disc.gameId[3] in ntscRegions:
			self.isoVersionText.set( 'NTSC 1.{0:0{1}}'.format(disc.revision, 2) ) # Converts an int to string, padded to two zeros
		else: self.isoVersionText.set( 'PAL 1.{0:0{1}}'.format(disc.revision, 2) )

		# Get Bi2.bin and check the country code (used to determine encoding for the banner file)
		# bi2Iid = scanDiscForFile( 'bi2.bin' ) # This will try for 'iso.hdr' if bi2 doesn't exist
		# bi2Data = getFileDataFromDiscTreeAsBytes( iid=bi2Iid )
		# if not bi2Data:
		# 	missingFiles.append( 'bi2.bin or ISO.hdr' )
		# else:
		# 	# Depending on which file is used, get the location/offset of where the country code is in the file
		# 	if bi2Iid.endswith( 'iso.hdr' ): countryCodeOffset = 0x458 # (0x440 + 0x18)
		# 	else: countryCodeOffset = 0x18

		# 	# Set the country code
		# 	if toInt( bi2Data[countryCodeOffset:countryCodeOffset+4] ) == 1: self.mainGui.countryCode.set( 'us' )
		# 	else: self.mainGui.countryCode.set( 'jp' )

		if disc.countryCode == 1:
			self.countryCode.set( 'us' )
		else: self.countryCode.set( 'jp' )

		# Remove the existing 20XX version label (the label displayed next to the StringVar, not the StringVar itself), if it's present.
		for widget in self.row2.winfo_children():
			thisWidgets = widget.grid_info()
			if thisWidgets['row'] == '1' and ( thisWidgets['column'] == '8' or thisWidgets['column'] == '9' ):
				widget.destroy()

		# Update the 20XX version label
		if disc.is20XX:
			twentyxxLabel = ttk.Label( self.row2, text='20XX Version:' )
			twentyxxLabel.grid( column=8, row=1, sticky='e', padx=self.row2.padx )
			# twentyxxLabel.bind( '<Enter>', lambda event: setDiscDetailsHelpText('20XX Version') )
			# twentyxxLabel.bind( '<Leave>', setDiscDetailsHelpText )
			twentyxxVersionLabel = ttk.Label( self.row2, text=disc.is20XX )
			twentyxxVersionLabel.grid( column=9, row=1, sticky='w', padx=self.row2.padx )
			# twentyxxVersionLabel.bind( '<Enter>', lambda event: setDiscDetailsHelpText('20XX Version') )
			# twentyxxVersionLabel.bind( '<Leave>', setDiscDetailsHelpText )

		# Load the banner and other info contained within the banner file
		#missingFiles = updateBannerFileInfo( missingFiles, imageName=imageName )
		# bannerIid = scanDiscForFile( 'opening.bnr' )
		# if not bannerIid:
		# 	missingFiles.append( 'opening.bnr' )
		# else:
		# 	global globalBannerFile
		# 	globalBannerFile = hsdFiles.datFileObj( source='disc' )
		# 	fileName = os.path.basename( self.fileTree.item( bannerIid, 'values' )[4] ) # Using isoPath (will probably be all lowercase anyway)
		# 	globalBannerFile.load( bannerIid, fileData=getFileDataFromDiscTreeAsBytes( iid=bannerIid ), fileName=fileName )
		# 	updateBannerFileInfo( imageName=imageName )
		
		self.isoFileCountText.set( "{:,}".format(len(disc.files)) )

		# Get and display the disc's total file size
		if discSize: # i.e. if it's a root folder that's been opened
			isoByteSize = discSize
		else: isoByteSize = os.path.getsize( disc.filePath )
		self.isoFilesizeText.set( "{:,} bytes".format(isoByteSize) )
		self.isoFilesizeTextLine2.set( '(i.e.: ' + "{:,}".format(isoByteSize/1048576) + ' MB, or ' + humansize(isoByteSize) + ')' )

		# Alert the user of any problems detected
		# if missingFiles:
		# 	msg( 'Some details of the disc could not be determined, because the following files could not be found:\n\n' + '\n'.join(missingFiles) )

	def saveBootFileDetails( self, event ):

		""" Takes certain text input from the GUI on the Disc Details Tab and 
			saves it to the 'boot.bin' file within the currently loaded disc. """

		# Cancel if no disc appears to be loaded
		if not globalData.disc: return 'break'

		# Return if the Shift key was held while pressing Enter (going to assume the user wants a line break).
		modifierKeysState = event.state # An int. Check individual bits for mod key status'; http://infohost.nmt.edu/tcc/help/pubs/tkinter/web/event-handlers.html
		shiftDetected = (modifierKeysState & 0x1) != 0 # Checks the first bit of the modifiers
		if shiftDetected: return # Not using "break" on this one in order to allow event propagation

		# Determine what encoding to use for saving text
		if self.countryCode.get() == 'us': encoding = 'latin_1' # Decode assuming English or other European countries
		else: encoding = 'shift_jis' # The country code is 'jp', for Japanese.

		# Get the currently entered text as hex
		if event.widget.winfo_class() == 'TEntry' or event.widget.winfo_class() == 'Entry': 
			inputBytes = event.widget.get().encode( encoding )
		else: inputBytes = event.widget.get( '1.0', 'end' )[:-1].encode( encoding ) # "[:-1]" ignores trailing line break
		newStringHex = hexlify( inputBytes )

		offset = event.widget.offset # In this case, these ARE counting the file header
		maxLength = event.widget.maxByteLength

		# Get the data for Boot.bin
		gameId = globalData.disc.gameId
		targetFile = globalData.disc.files.get( gameId + '/Boot.bin', gameId + '/ISO.hdr' ) # Will fall back on ISO.hdr if Boot.bin is not present
		targetFileData = targetFile.getData()
		if not targetFileData:
			msg( 'Unable to retrieve the Boot.bin file data!' )
			return 'break'

		# Get the hex string of the current value/field in the file, including padding
		currentHex = hexlify( targetFileData[offset:offset+maxLength] )

		# Pad the end of the input string with empty space (up to the max string length), to ensure any other text in the file will be erased
		newPaddedStringHex = newStringHex + ( '0' * (maxLength * 2 - len(newStringHex)) )

		# Check if the value is different from what is already saved.
		if currentHex != newPaddedStringHex:
			updateName = event.widget.updateName # Should be "Game ID" or "Image Name"

			if updateName == 'Game ID' and len( newStringHex ) != maxLength * 2: 
				msg( 'The new value must be ' + str(maxLength) + ' characters long.' )
			elif len( newStringHex ) > maxLength * 2: 
				msg( 'The text must be less than ' + str(maxLength) + ' characters long.' )
			else:
				# Change the background color of the widget, to show that changes have been made to it and are pending saving.
				event.widget.configure( background="#faa" )

				# Add the widget to a list, to keep track of what widgets need to have their background restored to white when saving.
				#editedBannerEntries.append( event.widget )

				# if targetFile == 'opening.bnr':
				# 	descriptionOfChange = updateName + ' modified in ' + globalBannerFile.fileName
				# 	globalBannerFile.updateData( offset, bytearray.fromhex( newPaddedStringHex ), descriptionOfChange )
				# else:
				#global unsavedDiscChanges
				#targetFileData[offset:offset+maxLength] = bytearray.fromhex( newPaddedStringHex )
				# self.isoFileTree.item( targetFileIid, values=('Disc details updated', entity, isoOffset, fileSize, isoPath, 'ram', hexlify(targetFileData)), tags='changed' )
				# unsavedDiscChanges.append( updateName + ' updated.' )
				# targetFile.data = targetFileData
				# globalData.disc.unsavedChanges.append(  )

				globalData.disc.makeChange( targetFile, offset, bytearray.fromhex(newPaddedStringHex), updateName + ' updated.' )
				self.mainGui.discTab.isoFileTree.item( targetFile.isoPath, values=('Disc details updated', 'file'), tags='changed' )

				self.mainGui.updateProgramStatus( updateName + ' updated. Press CRTL-S to save changes to file.' )

		return 'break' # Prevents the 'Return' keystroke that called this from propagating to the widget and creating a line break

	def saveBannerFileDetails( self, event ):

		""" Takes certain text input from the GUI on the Disc Details Tab, and saves it to the 'opening.bnr' file within the currently loaded disc. """

		# Cancel if no banner file appears to be loaded
		if not self.bannerFile: return 'break'

		# Return if the Shift key was held while pressing Enter (going to assume the user wants a line break).
		modifierKeysState = event.state # An int. Check individual bits for mod key status'; http://infohost.nmt.edu/tcc/help/pubs/tkinter/web/event-handlers.html
		shiftDetected = (modifierKeysState & 0x1) != 0 # Checks the first bit of the modifiers
		if shiftDetected: return # Not using "break" on this one in order to allow event propagation

		# Determine what encoding to use for saving text
		if self.countryCode.get() == 'us': encoding = 'latin_1' # Decode assuming English or other European countries
		else: encoding = 'shift_jis' # The country code is 'jp', for Japanese.

		# Get the currently entered text as hex
		if event.widget.winfo_class() == 'TEntry' or event.widget.winfo_class() == 'Entry': 
			inputBytes = event.widget.get().encode( encoding )
		else: inputBytes = event.widget.get( '1.0', 'end' )[:-1].encode( encoding ) # "[:-1]" ignores trailing line break
		newStringHex = hexlify( inputBytes )

		offset = event.widget.offset # In this case, these ARE counting the file header
		maxLength = event.widget.maxByteLength
		#targetFile = event.widget.targetFile # Defines the file this disc detail resides in. Will be a string of either 'opening.bnr' or 'boot.bin'

		# Get the data for the target file (Could be for boot.bin or opening.bnr)
		# if targetFile == 'opening.bnr':
		# 	targetFileData = globalBannerFile.data
		# else: # Updating to boot.bin, which must be from within a disc
		# 	targetFileIid = scanDiscForFile( 'Boot.bin' )
		# 	if not targetFileIid:
		# 		msg( 'Boot.bin could not be found in the disc!' )
		# 		return 'break'
		# 	_, entity, isoOffset, fileSize, isoPath, _, _ = self.fileTree.item( targetFileIid, 'values' )
		# 	targetFileData = getFileDataFromDiscTreeAsBytes( targetFileIid )
		targetFileData = self.bannerFile.getData()
		if not targetFileData:
			msg( 'Unable to retrieve the opening.bnr file data!' )
			return 'break'

		# Get the hex string of the current value/field in the file
		currentHex = hexlify( targetFileData[offset:offset+maxLength] )

		# Pad the end of the input string with empty space (up to the max string length), to ensure any other text in the file will be erased
		newPaddedStringHex = newStringHex + ( '0' * (maxLength * 2 - len(newStringHex)) )

		# Check if the value is different from what is already saved.
		if currentHex != newPaddedStringHex:
			updateName = event.widget.updateName

			if len( newStringHex ) > maxLength * 2: 
				msg( 'The text must be less than ' + str(maxLength) + ' characters long.' )
			else:
				# Change the background color of the widget, to show that changes have been made to it and are pending saving.
				event.widget.configure( background="#faa" )

				# Add the widget to a list, to keep track of what widgets need to have their background restored to white when saving.
				# editedBannerEntries.append( event.widget )

				# if targetFile == 'opening.bnr':
				# 	descriptionOfChange = updateName + ' modified in ' + globalBannerFile.fileName
				# 	globalBannerFile.updateData( offset, bytearray.fromhex( newPaddedStringHex ), descriptionOfChange )
				# else:
				# 	global unsavedDiscChanges
				# 	targetFileData[offset:offset+maxLength] = bytearray.fromhex( newPaddedStringHex )
				# 	self.fileTree.item( targetFileIid, values=('Disc details updated', entity, isoOffset, fileSize, isoPath, 'ram', hexlify(targetFileData)), tags='changed' )
				# 	unsavedDiscChanges.append( updateName + ' updated.' )

				self.mainGui.discTab.isoFileTree.item( self.bannerFile.isoPath, values=('Disc details updated', 'file'), tags='changed' )
				globalData.disc.makeChange( self.bannerFile, offset, bytearray.fromhex(newPaddedStringHex), updateName + ' updated.' )

				self.mainGui.updateProgramStatus( updateName + ' updated. Press CRTL-S to save changes to file.' )

		return 'break' # Prevents the 'Return' keystroke that called this from propagating to the widget and creating a line break

	def reloadBanner( self ): pass

																			#===========================#
																			# ~ ~   Context Menus   ~ ~ #
																			#===========================#

class DiscMenu( Tk.Menu, object ):
	
	""" Main menu item, as well as the context menu for the Disc File Tree. """ # just context menu?

	def __init__( self, parent, tearoff=True, *args, **kwargs ):
		super( DiscMenu, self ).__init__( parent, tearoff=tearoff, *args, **kwargs )
		self.open = False

	def repopulate( self ):

		""" This method will be called every time the submenu is displayed. """

		# Clear all current population
		self.delete( 0, 'last' )

		# Determine the kind of file(s)/folder(s) we're working with, to determine menu options
		self.discTab = globalData.gui.discTab
		self.fileTree = self.discTab.isoFileTree
		self.iidSelectionsTuple = self.fileTree.selection()
		self.selectionCount = len( self.iidSelectionsTuple )
		if self.selectionCount == 1:
			self.fileObj = globalData.disc.files.get( self.iidSelectionsTuple[0] )
			if self.fileObj:
				self.entity = 'file'
				self.entityName = self.fileObj.filename
			else:
				self.entity = 'folder'
				self.entityName = os.path.basename( self.iidSelectionsTuple[0] )
		else:
			self.fileObj = None
			self.entity = ''
			self.entityName = ''
		#lastSeperatorAdded = False

		# Add main import/export options																				# Keyboard shortcuts:
		if self.iidSelectionsTuple:
			# Check if the root (Game ID) is selected
			rootIid = self.fileTree.get_children()[0]
			if self.selectionCount == 1 and self.entityName == rootIid:
				self.add_command( label='Extract Root for Dolphin', underline=0, command=self.extractRootWithNative )					# E
				self.add_command( label='Extract Root with Convenience Folders', underline=0, command=self.extractRootWithConvenience )	# E
			else:
				self.add_command( label='Export File(s)', underline=0, command=self.discTab.exportIsoFiles )							# E
		# 	self.add_command( label='Export Textures From Selected', underline=1, command=exportSelectedFileTextures )					# X

		# Add file-type-specific options if only a single file is selected
		if self.fileObj:
			self.add_command( label='Import File', underline=0, command=self.discTab.importSingleIsoFile )								# I

			if self.fileObj.__class__ == MusicFile:
				self.add_command( label='Listen', underline=0, command=self.listenToMusic )												# L
			elif self.fileObj.__class__ == SisFile:
				self.add_command( label='Browse Strings', underline=7, command=self.openSisTextEditor )									# S
			elif self.fileObj.__class__ == CharAnimFile:
				self.add_command( label='List Animations', command=self.listAnimations )												# S
			elif self.fileObj.__class__ == CharDataFile:
				self.add_command( label='List Action Table Entries', command=self.listActionTableEntries )
		# self.add_command( label='Import Multiple Files', underline=7, command=importMultipleIsoFiles )								# M
		self.add_separator()

		# Add supplemental disc functions
		self.add_command( label='Add File(s) to Disc', underline=0, command=self.addFilesToIso )										# A
		# self.add_command( label='Add Directory of File(s) to Disc', underline=4, command=addDirectoryOfFilesToIso )					# D
		# self.add_command( label='Create Directory', underline=0, command=createDirectoryInIso )										# C
		if self.iidSelectionsTuple:
			if self.selectionCount == 1:

				if self.entity == 'file':
					self.add_command( label='Rename (in disc filesystem)', underline=2, command=self.renameFilesystemEntry )			# N

					if self.fileObj.__class__.__name__ == 'StageFile' and self.fileObj.isRandomNeutral():
						self.add_command( label='Rename Stage Name (in CSS)', underline=2, command=self.renameDescription )				# N
					elif self.fileObj.__class__.__name__ == 'MusicFile' and self.fileObj.isHexTrack:
						self.add_command( label='Rename Music Title (in CSS)', underline=2, command=self.renameDescription )			# N
					else:
						self.add_command( label='Edit Description (in yaml)', underline=5, command=self.renameDescription )				# D

					#if self.fileObj.filename.endswith( 'AJ.dat' ):
				else:
					self.add_command( label='Rename (in disc filesystem)', underline=2, command=self.renameFilesystemEntry )				# N

			self.add_command( label='Remove Selected Item(s)', underline=0, command=self.removeItemsFromIso )							# R
		# 	self.add_command( label='Move Selected to Directory', underline=1, command=moveSelectedToDirectory )						# O

		# Add general file operations
		if self.selectionCount == 1 and self.entity == 'file':
			self.add_separator()
			self.add_command( label='View Hex', underline=5, command=self.viewFileHex )													# H
			#self.add_command( label='Replace Hex', underline=8, command=self.replaceFileHex )											# H
			self.add_command( label='Copy Offset to Clipboard', underline=2, command=self.copyFileOffsetToClipboard )					# P
			# self.add_command( label='Browse Textures', underline=0, command=browseTexturesFromDisc )									# B
			# self.add_command( label='Analyze Structure', underline=5, command=analyzeFileFromDisc )									# Z

			if self.entityName.startswith( 'Pl' ):
				self.add_command( label='Set as CCC Source File', underline=11, command=lambda: self.cccSelectFromDisc( 'source' ) )		# S
				self.add_command( label='Set as CCC Destination File', underline=11, command=lambda: self.cccSelectFromDisc( 'dest' ) )		# D
		
		elif self.selectionCount > 1:
			# Check if all of the items are files
			for iid in self.iidSelectionsTuple:
				#if self.fileTree.item( self.iidSelectionsTuple[0], 'values' )[1] != 'file': break
				fileObj = globalData.disc.files.get( iid )
				if not fileObj: break
			else: # The loop above didn't break; only files here
				self.add_separator()
				self.add_command( label='Copy Offsets to Clipboard', underline=2, command=self.copyFileOffsetToClipboard )				# P
				
		# Check if this is a version of 20XX, and if so, get its main build number
		#orig20xxVersion = globalData.disc.is20XX # This is an empty string if the version is not detected or it's not 20XX

		# Add an option for CSP Trim Colors, if it's appropriate
		# if self.iidSelectionsTuple and orig20xxVersion:
		# 	if 'BETA' in orig20xxVersion:
		# 		majorBuildNumber = int( orig20xxVersion[-1] )
		# 	else: majorBuildNumber = int( orig20xxVersion[0] )

		# 	# Check if any of the selected files are an appropriate character alt costume file
		# 	for iid in self.iidSelectionsTuple:
		# 		entityName = os.path.basename( iid )
		# 		thisEntity = self.fileTree.item( iid, 'values' )[1] # Will be a string of 'file' or 'folder'

		# 		if thisEntity == 'file' and candidateForTrimColorUpdate( entityName, orig20xxVersion, majorBuildNumber ):
		# 			if not lastSeperatorAdded:
		# 				self.add_separator()
		# 				lastSeperatorAdded = True
		# 			self.add_command( label='Generate CSP Trim Colors', underline=0, command=self.prepareForTrimColorGeneration )		# G
		# 			break

	def extractRootWithNative( self ):

		""" Turn off convenience folders before export, if they're enabled. Restores setting afterwards. """

		useConvenienceFolders = globalData.checkSetting( 'useDiscConvenienceFolders' )

		if useConvenienceFolders:
			globalData.setSetting( 'useDiscConvenienceFolders', False )
			self.discTab.exportIsoFiles( addDolphinSubs=True )
			globalData.setSetting( 'useDiscConvenienceFolders', True )
		else: # No need to change the setting
			self.discTab.exportIsoFiles( addDolphinSubs=True )

	def extractRootWithConvenience( self ):

		""" Turn on convenience folders before export, if they're not enabled. Restores setting afterwards. """

		useConvenienceFolders = globalData.checkSetting( 'useDiscConvenienceFolders' )

		if useConvenienceFolders: # No need to change the setting
			self.discTab.exportIsoFiles()
		else:
			globalData.setSetting( 'useDiscConvenienceFolders', True )
			self.discTab.exportIsoFiles()
			globalData.setSetting( 'useDiscConvenienceFolders', False )

	def listenToMusic( self ):

		""" Add the Music Manager tab to the GUI and select it. """

		mainGui = globalData.gui
		
		# Load the audio tab
		if not mainGui.audioManagerTab:
			mainGui.audioManagerTab = AudioManager( mainGui.mainTabFrame, mainGui )
			mainGui.audioManagerTab.loadFileList()

		# Switch to the tab
		mainGui.mainTabFrame.select( mainGui.audioManagerTab )

		# Select the file
		mainGui.audioManagerTab.selectSong( self.fileObj.isoPath )

	def listAnimations( self ):

		self.fileObj.initialize()

		lines = []
		# for symbol in self.fileObj.animNames:
		# 	charName = symbol[3:].split( '_' )[0]
		# 	animName = symbol.split( '_' )[3]
		for anim in self.fileObj.animations:
			charName = anim.name[3:].split( '_' )[0]
			animName = anim.name.split( '_' )[3]
			offset = hex( anim.offset + 0x20 )
			
			lines.append( '{}  -  {}  -  {}'.format(charName, animName, offset) )

		cmsg( '\n'.join(lines), '{} Animation Names'.format(self.fileObj.filename) )

	def listActionTableEntries( self ):
		
		table = self.fileObj.getActionTable()
		title = self.fileObj.filename + ' Action Table Entries - ' + hex( table.offset + 0x20 )

		lines = []
		for i, values in table.iterateEntries():
			actionName = self.fileObj.getString( values[0] )
			offset = table.entryIndexToOffset( i )
			lines.append( '\t{} | {} - {}'.format(i, uHex(offset + 0x20), actionName) )
			
		cmsg( '\n'.join(lines), title )

	def openSisTextEditor( self ):
		SisTextEditor( self.fileObj )

	def addFilesToIso( self ):

		""" Prompts the user for one or more files to add to the disc, and then 
			adds those files to both the internal disc object and the GUI. """

		# Prompt for one or more files to add.
		filepaths = tkFileDialog.askopenfilename(
			title='Choose one or more files (of any format) to add to the disc image.', 
			initialdir=globalData.getLastUsedDir(),
			multiple=True,
			filetypes=[ ('All files', '*.*'), ('Model/Texture data files', '*.dat *.usd *.lat *.rat'), ('Audio files', '*.hps *.ssm'),
						('System files', '*.bin *.ldr *.dol *.toc'), ('Video files', '*.mth *.thp') ]
			)

		if not filepaths: # User may have canceled; filepaths will be empty in that case
			globalData.gui.updateProgramStatus( 'Operation canceled' )
			return
		
		parent, iidToAddBefore = self.discTab.determineNewFileInsertionKey()

		if parent == 'sys':
			msg( 'Directories or files cannot be added to the system files folder.', warning=True )
			return

		# If only one file was selected, offer to modify its name (ignored on multiple files which would probably be tedious)
		if len( filepaths ) == 1:
			dirPath, fileName = os.path.split( filepaths[0] )
			newName = getNewNameFromUser( 30, message='Enter a disc file name:', defaultText=fileName )
			if not newName:
				globalData.gui.updateProgramStatus( 'Operation canceled' )
				return
			#filepaths = ( os.path.join(dirPath, newName), )
		else:
			newName = ''

		preexistingFiles = [] # Strings; absolute file paths
		filenamesTooLong = [] # Strings; absolute file paths
		filesToAdd = [] # These will be file objects

		# Add the files to the file tree, check for pre-existing files of the same name, and prep the files to import
		for filepath in filepaths: # Must be file paths; folders can't be selected by askopenfilename
			# Get the new file's name and size
			fileName = os.path.basename( filepath ).replace( ' ', '_' ).replace( '-', '/' ) # May denote folders in the file name!
			fileNameOnly = fileName.split('/')[-1] # Will be no change from the original string if '/' is not present

			# Construct a new isoPath for this file
			if not iidToAddBefore or iidToAddBefore == 'end':
				newFileIsoPath = parent + '/' + fileName
			else: # iidToAddBefore is an isoPath of an existing file
				isoFolderPath = '/'.join( iidToAddBefore.split('/')[:-1] ) # Remove last fragment
				newFileIsoPath = isoFolderPath + '/' + fileName

			# Exclude files with filenames that are too long
			if len( os.path.splitext(fileNameOnly)[0] ) >= 30:
				filenamesTooLong.append( filepath )
				continue

			# Create folders that may be suggested by the filename (if these folders don't exist, 
			# then the file won't either, so the file-existance check below this wont fail)
			# if '/' in fileName:
			# 	for folderName in fileName.split('/')[:-1]: # Ignore the last part, the file name
			# 		isoPath += '/' + folderName
			# 		iid = isoPath
			# 		if not self.isoFileTree.exists( iid ):
			# 			self.isoFileTree.insert( parent, index, iid=iid, text=' ' + folderName, image=globalData.gui.imageBank('folderIcon') )
			# 		parent = iid

			# Exclude files that already exist in the disc
			#isoPath += '/' + fileNameOnly
			#iid = isoPath
			#if self.fileTree.exists( newFileIsoPath ):
			if newFileIsoPath in globalData.disc.files:
				preexistingFiles.append( fileName )
				continue

			# Create a file object for this file
			try:
				fileSize = int( os.path.getsize(filepath) ) # int() required to convert the value from long to int
				fileObj = fileFactory( None, -1, fileSize, newFileIsoPath, extPath=filepath, source='file' )
				if newName:
					fileObj.isoPath = '/'.join( newFileIsoPath.split('/')[:-1] + [newName] )
					fileObj.filename = newName
			except Exception as err:
				print( 'Unable to initialize {}; {}'.format(filepath, err) )
				continue
			fileObj.insertionKey = iidToAddBefore
			filesToAdd.append( fileObj )

		# Actually add the new file objects to the disc object
		globalData.disc.addFiles( filesToAdd )

		# Show new files in the Disc File Tree
		if self.discTab:
			self.discTab.loadDisc( updateStatus=False, preserveTreeState=True )
			for fileObj in filesToAdd:
				self.fileTree.item( fileObj.isoPath, values=('Adding to disc...', 'file'), tags='changed' )

		# Update the Disc Details Tab
		detailsTab = globalData.gui.discDetailsTab
		if detailsTab:
			detailsTab.isoFileCountText.set( "{:,}".format(len(globalData.disc.files)) )
			#detailsTab # todo: disc size as well

		# Directly notify the user of any excluded files
		notifications = '' # For a pop-up message
		statusBarMsg = ''
		if preexistingFiles:
			notifications += 'These files were skipped, because they already exist in the disc:\n\n' + '\n'.join(preexistingFiles)
			statusBarMsg += '{} pre-existing disc files skipped. '.format( len(preexistingFiles) )
		if filenamesTooLong:
			if notifications: notifications += '\n\n'
			notifications += 'These files were skipped, because their file names are longer than 29 characters:\n\n' + '\n'.join(filenamesTooLong)
			statusBarMsg += '{} files skipped due to long filenames. '.format( len(filenamesTooLong) )
		if notifications:
			msg( notifications, warning=True )

		# If any files were added, scroll to the newly inserted item (so it's visible to the user), and update the pending changes and program status
		if not filesToAdd: # No files added
			globalData.gui.updateProgramStatus( 'No files added. ' + statusBarMsg )
			return
		
		# Scroll to the file(s) added so they're immediately visible to the user (unless a custom location was chosen, thus is probably already scrolled to)
		if not iidToAddBefore or iidToAddBefore == 'end': # iidToAddBefore should be an empty string if the file was added alphanumerically
			self.fileTree.see( filesToAdd[0].isoPath ) # Should be the iid of the topmost item that was added

		# Update the program status message
		if len( filesToAdd ) == 1:
			if statusBarMsg:
				globalData.gui.updateProgramStatus( '{} added. '.format(filesToAdd[0].filename) + statusBarMsg )
			else:
				globalData.gui.updateProgramStatus( '{} added to the disc'.format(filesToAdd[0].filename) )
		else:
			globalData.gui.updateProgramStatus( '{} files added. '.format(len(filesToAdd)) + statusBarMsg )

	def removeItemsFromIso( self ):
		self.discTab.deleteIsoFiles( self.iidSelectionsTuple )

	# def prepareForTrimColorGeneration( self ):

	# 	""" One of the primary methods for generating CSP Trim Colors.

	# 		If only one file is being operated on, the user will be given a prompt to make the final color selection.
	# 		If multiple files are selected, the colors will be generated and selected autonomously, with no user prompts. """

	# 	# Make sure that the disc file can still be located
	# 	if not discDetected(): return

	# 	if self.selectionCount == 1:
	# 		generateTrimColors( self.iidSelectionsTuple[0] )

	# 	else: # Filter the selected files and operate on all alt costume files only, in autonomous mode
	# 		for iid in self.iidSelectionsTuple:
	# 			entityName = os.path.basename( iid )
	# 			thisEntity = self.fileTree.item( iid, 'values' )[1] # Will be a string of 'file' or 'folder'
	
				# Check if this is a version of 20XX, and if so, get its main build number
				#orig20xxVersion = globalData.disc.is20XX # This is an empty string if the version is not detected or it's not 20XX

	# 			if 'BETA' in orig20xxVersion: origMainBuildNumber = int( orig20xxVersion[-1] )
	# 			else: origMainBuildNumber = int( orig20xxVersion[0] )

	# 			if thisEntity == 'file' and candidateForTrimColorUpdate( entityName, orig20xxVersion, origMainBuildNumber ):
	# 				generateTrimColors( iid, True ) # autonomousMode=True means it will not prompt the user to confirm its main color choices

	def renameFilesystemEntry( self ):

		""" Renames the file name in the disc filesystem for the currently selected file. """

		# Prompt the user to enter a new name
		newName = getNewNameFromUser( 30, message='Enter a new filesystem name:', defaultText=self.entityName )
		if not newName:
			globalData.gui.updateProgramStatus( 'Name update canceled' )
			return

		# Reject illegal renames
		basename = os.path.basename( self.fileObj.filename )
		if self.fileObj.filename in globalData.disc.systemFiles:
			msg( 'System files cannot be renamed!', 'Invalid Rename' )
			globalData.gui.updateProgramStatus( 'Unable to rename system files' )
			return
		elif basename in ( 'MnSlChr', 'MnSlMap', 'opening' ):
			if not askyesno( ('These are important system files that are not '
				'expected to have any other name. Renaming them could lead to '
				'unexpected problems. \n\nAre you sure you want to do this?'), 'Warning!' ):
				return
		
		print( 'rename filesystem entry not yet implemented' )
		# Update the file name in the FST
		# oldName = 
		# for entry in globalData.disc.fstEntries: # Entries are of the form [ folderFlag, stringOffset, entryOffset, entrySize, entryName, isoPath ]
		# 	if entry[-2] == 

		# isoPath = self.iidSelectionsTuple[0]

		# self.fileTree.item( isoPath, 'text', newName )

	def renameDescription( self ):
		
		charLimit = 42 # Somewhat arbitrary limit

		if self.fileObj.__class__.__name__ == 'StageFile' and self.fileObj.isRandomNeutral():
			charLimit = 0x1F # Max space in CSS file
		elif self.fileObj.__class__.__name__ == 'MusicFile' and self.fileObj.isHexTrack:
			cssFile = globalData.disc.files.get( globalData.disc.gameId + '/MnSlChr.0sd' )
			if not cssFile:
				msg( "Unable to update CSS with song name; the CSS file (MnSlChr.0sd) could not be found in the disc." )
				globalData.gui.updateProgramStatus( "Unable to update CSS with song name; couldn't find the CSS file in the disc", error=True )
				return
			charLimit = cssFile.checkMaxHexTrackNameLen( self.fileObj.trackId )

		# Prompt the user to enter a new name
		newName = getNewNameFromUser( charLimit, message='Enter a new description:', defaultText=self.fileObj.longDescription )
		if not newName:
			globalData.gui.updateProgramStatus( 'Name update canceled' )
			return

		# Store the new name to file
		returnCode = self.fileObj.setDescription( newName )
		
		if returnCode == 0:
			# Update the new name in the treeview on this tab, as well as in the Stage Manager tab
			if globalData.checkSetting( 'useDiscConvenienceFolders' ):
				# Add extra space to indent the name from the parent folder name
				description = '     ' + self.fileObj.shortDescription
			else:
				description = self.fileObj.longDescription
			globalData.gui.discTab.isoFileTree.item( self.fileObj.isoPath, values=(description, 'file') )
			if globalData.gui.stageManagerTab:
				globalData.gui.stageManagerTab.renameTreeviewItem( self.fileObj.isoPath, newName ) # No error if not currently displayed

			if self.fileObj.__class__.__name__ == 'StageFile' and self.fileObj.isRandomNeutral():
				globalData.gui.updateProgramStatus( 'Stage name updated in the CSS file', success=True )
			elif self.fileObj.__class__.__name__ == 'MusicFile' and self.fileObj.isHexTrack:
				globalData.gui.updateProgramStatus( 'Song name updated in the CSS file', success=True )
			else:
				globalData.gui.updateProgramStatus( 'File name updated in the {}.yaml config file'.format(globalData.disc.gameId), success=True )
		elif returnCode == 1:
			globalData.gui.updateProgramStatus( 'Unable to update name/description in the {}.yaml config file'.format(globalData.disc.gameId), error=True )
		elif returnCode == 2:
			globalData.gui.updateProgramStatus( "Unable to update CSS with the name; couldn't find the CSS file in the disc", error=True )
		elif returnCode == 3:
			globalData.gui.updateProgramStatus( "Unable to update CSS with the name; couldn't save the name to the CSS file", error=True )
		else:
			msg( 'An unrecognized return code was given by .setDescription(): ' + str(returnCode) )

	def viewFileHex( self ):

		""" Gets and displays hex data for a file within a disc in the user's hex editor of choice. """

		# Create a file name with folder names included, so that multiple files of the same name (but from different folders) can be opened.
		isoPath = self.iidSelectionsTuple[0]
		filename = '-'.join( isoPath.split('/')[1:] ) # Excludes the gameId

		# Get the file data, create a temp file with it, and show it in the user's hex editor
		datData = self.fileObj.getData()
		saveAndShowTempFileData( datData, filename )

	#def replaceFileHex( self ):

	def copyFileOffsetToClipboard( self ):
		# Ensure the user knows what's being operated on
		self.fileTree.selection_set( self.iidSelectionsTuple ) 	# Highlights the item(s)
		self.fileTree.focus( self.iidSelectionsTuple[0] ) 		# Sets keyboard focus to the first item

		# Get the offsets of all of the items selected
		offsets = []
		for iid in self.iidSelectionsTuple:
			fileObj = globalData.disc.files.get( iid )
			offsets.append( uHex(fileObj.offset) )

		copyToClipboard( ', '.join(offsets) )

	def cccSelectFromDisc( self, role ):

		""" Add character files from the disc to the CCC tool window. """

		# Check if an instance exists, and create one if it doesn't
		cccWindow = globalData.getUniqueWindow( 'CharacterColorConverter' )
		if not cccWindow:
			cccWindow = CharacterColorConverter()

		# Create a copy of the file (wihtout making a disc copy) to send to the CCC, because it will be modified
		disc = self.fileObj.disc
		self.fileObj.disc = None
		fileCopy = copy.deepcopy( self.fileObj )
		self.fileObj.disc = disc
		fileCopy.disc = disc

		cccWindow.updateSlotRepresentation( fileCopy, role )