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


# External GUI dependencies
import ttk
import Tkinter as Tk

# Internal dependencies
import globalData
from basicFunctions import humansize
from guiSubComponents import HexEditDropdown, VerticalScrolledFrame


class StageManager( ttk.Frame ):

	""" Info viewer and editor interface for stages in SSBM. """

	def __init__( self, parent, mainGui ):

		ttk.Frame.__init__( self, parent ) #, padding="11 0 0 11" ) # Padding order: Left, Top, Right, Bottom.
		mainGui.mainTabFrame.add( self, text=' Stage Manager ' )
		self.selectedStage = None

		# Construct the left-hand side of the interface, the file list
		treeScroller = Tk.Scrollbar( self )
		self.stageListTree = ttk.Treeview( self, selectmode='browse', columns=('filename'), show='tree', yscrollcommand=treeScroller.set )
		self.stageListTree.grid( column=0, row=0, sticky='nsew' )
		treeScroller.config( command=self.stageListTree.yview )
		treeScroller.grid( column=1, row=0, sticky='ns' )

		# Add treeview event handlers
		self.stageListTree.bind( '<<TreeviewSelect>>', self.onFileTreeSelect )
		# self.stageListTree.bind( '<Double-1>', onFileTreeDoubleClick )
		#self.stageListTree.bind( "<3>", self.createContextMenu ) # Right-click

		# Construct the right-hand side of the interface, the info panels
		stageInfoPane = ttk.Frame( self )
		self.stageSystemLabel = ttk.Label( stageInfoPane )
		self.stageSystemLabel.pack( anchor='w' )
		self.stagesInStageSystemLabel = ttk.Label( stageInfoPane )
		self.stagesInStageSystemLabel.pack( anchor='w' )
		self.totalStagesLabel = ttk.Label( stageInfoPane )
		self.totalStagesLabel.pack( anchor='w' )

		basicLabelFrame = ttk.LabelFrame( stageInfoPane, text='  Basic Info  ', labelanchor='n', padding=(0, 4) )
		self.basicInfoLabel = ttk.Label( basicLabelFrame )
		self.basicInfoLabel.pack()
		basicLabelFrame.pack()
		stageInfoPane.grid( column=2, row=0, sticky='n' )
		
		musicLabelFrame = ttk.LabelFrame( stageInfoPane, text='  Music  ', labelanchor='n', padding=(0, 4) )
		ttk.Label( musicLabelFrame, text='Music Table Entry: ' ).grid( column=0, row=0 )
		self.musicTableEntry = Tk.StringVar()
		ttk.OptionMenu( musicLabelFrame, self.musicTableEntry, '', [], command=self.changeMusicEntry ).grid( column=1, row=0 )
		self.musicInfoLabel = ttk.Label( musicLabelFrame )
		self.musicInfoLabel.grid( column=0, row=1, columnspan=2 )
		musicLabelFrame.pack()
		stageInfoPane.grid( column=2, row=0, sticky='n' )
		
		self.columnconfigure( 0, weight=1 )
		self.columnconfigure( 1, weight=0 )
		self.columnconfigure( 2, weight=1 )
		self.rowconfigure( 'all', weight=1 )

	def clear( self ):

		""" Clears this tab's GUI contents. """

		
		# Delete the current items in the tree
		for item in self.stageListTree.get_children():
			self.stageListTree.delete( item )

		# Clear labels
		self.stageSystemLabel['text'] = 'Stage System:'
		self.stagesInStageSystemLabel['text'] = 'Stages in Stage System:'
		self.totalStagesLabel['text'] = 'Total Stages:'

		self.basicInfoLabel['text'] = ( 'Stage ID (Internal):  \n'
										'File Size:  \n'
										'General Points:  \n'
										'GObjs:  ' )
		self.musicInfoLabel['text'] = ( 'Stage ID (External):  \n'
										'Background Music:\n\n'
										'Alt. Background Music:\n\n'
										'SSD Background Music:\n\n'
										'SSD Alt. Background Music:\n\n'
										'Song Behavior: '
										'Alt. Music % Chance: '
									  )

	def loadStageList( self ):

		""" Load stage info from the currently loaded disc into this tab. """

		self.clear()

		# Get the list of stages from the disc
		self.stages = []
		for fileObj in globalData.disc.files.values():
			if fileObj.__class__.__name__ == 'StageFile':
				self.stages.append( fileObj )

		# Add labels along the left for the stages found above
		for stageFile in self.stages:
			parent = ''

			# Check for Target Test stages (second case in parenthesis is for Luigi's, which ends in 0at in 20XX; last case is for the "TEST" stage)
			if stageFile.filename[2] == 'T' and ( stageFile.ext == '.dat' or stageFile.filename == 'GrTLg.0at' ) and stageFile.filename != 'GrTe.dat':
				# Create a folder for target test stage files (if not already created)
				if not self.stageListTree.exists( 't' ):
					self.stageListTree.insert( parent, 'end', iid='t', text=' Vanilla Target Test', image=globalData.gui.imageBank('folderIcon') )
				parent = 't'

			elif stageFile.filename[2:5] in globalData.onePlayerStages: # For 1-Player modes,like 'Adventure'
				if not self.stageListTree.exists( '1p' ):
					self.stageListTree.insert( parent, 'end', iid='1p', text=' 1-Player Mode', image=globalData.gui.imageBank('folderIcon') )
				parent = '1p'

			elif stageFile.isRandomNeutral():
				# Modern versions of 20XX (4.06+) have multiple variations of each neutral stage, the 'Random Neutrals' (e.g. GrSt.0at through GrSt.eat)
				iid = stageFile.shortName.lower()

				# Add the convenience folder if not already added
				if not self.stageListTree.exists( iid ):
					# if stageFile.shortName == 'GrP': # For Stadium
					# 	folderName = ' {}_.usd'.format( stageFile.shortName )
					# else: folderName = ' {}._at'.format( stageFile.shortName )
					self.stageListTree.insert( parent, 'end', iid=iid, text=' ' + stageFile.longName + ' (RN)', image=globalData.gui.imageBank('folderIcon') )
				parent = iid
			#parent = globalData.gui.discTree.determineStageFileTreePlacement( self.stageListTree, stageFile, '' )
			
			# Get the name for this item
			if stageFile.description:
				# print '-'
				# print type(stageFile.description), stageFile.description
				# print type(stageFile.description.encode( 'utf-8' ))
				# print stageFile.description.encode( 'utf-8' )
				#stageName = '{}   ({})'.format(stageFile.description, stageFile.filename)
				stageName = stageFile.description
			else:
				stageName = 'Undefined'
				
			# Add the file to the treeview
			self.stageListTree.insert( parent, 'end', iid=stageFile.isoPath, text=stageName, values=(stageFile.filename,) )

		# Update labels in the info pane on the right
		if globalData.disc.is20XX:
			self.stageSystemLabel['text'] = 'Stage System:  20XX HP'
		else:
			self.stageSystemLabel['text'] = 'Stage System:  Vanilla'
		self.stagesInStageSystemLabel['text'] = 'Stages in Stage System:  '
		self.totalStagesLabel['text'] = 'Total Stages:  {}'.format( len(self.stages) )

	def onFileTreeSelect( self, event ):

		""" Called when an item (file or folder) in the Disc File Tree is selected. Iterates over 
			the selected items, calculates total file(s) size, and displays it in the GUI. """

		iidSelectionsTuple = self.stageListTree.selection()
		print 'selection:', iidSelectionsTuple
		if len( iidSelectionsTuple ) != 1:
			return

		# Attempts to get the associated stage object and initialize it (parse it for data structures)
		isoPath = iidSelectionsTuple[0]
		stageFile = globalData.disc.files.get( isoPath )
		if not stageFile:
			return # This was probably a folder that was clicked on
		stageFile.initialize()

		# Collect some basic info
		filesize = stageFile.headerInfo['filesize']
		mapHeadStruct = stageFile.getStructByLabel( 'map_head' )
		self.basicInfoLabel['text'] = ( 'Stage ID (Internal):  \n'
										'File Size:  {}\n'
										'General Points:  {}\n'
										'GObjs:  {}'.format(humansize(filesize), mapHeadStruct.values[1], mapHeadStruct.values[3]) )

		# Get Music info
		grGroundParamStruct = stageFile.getStructByLabel( 'grGroundParam' )
		musicTableOffset = grGroundParamStruct.getValues( 'Music_Table_Pointer' )
		self.musicTableStruct = stageFile.getStruct( musicTableOffset )
		print self.musicTableStruct.values[0]
		# extStageId = self.musicTableStruct.get
		
		# Set the music values found above in the GUI
		self.musicInfoLabel['text'] = ( 'Stage ID (External):  {}\n'
										'Background Music:\n\t\n'
										'Alt. Background Music:\n\n'
										'SSD Background Music:\n\n'
										'SSD Alt. Background Music:\n\n'
										'Song Behavior: '
										'Alt. Music % Chance: '
									  ).format( self.musicTableStruct.values[0] )
		

		# self.selectedStage = stageFile

	def changeMusicEntry( self ):

		print 'test', self.musicTableEntry.get()