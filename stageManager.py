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
import os
import ttk
import time
import struct
import pyglet
import tkFileDialog
import Tkinter as Tk

from binascii import hexlify
from collections import OrderedDict
from PIL import Image, ImageTk, ImageDraw, ImageFont

# Internal dependencies
import globalData

from renderEngine import RenderEngine
from FileSystem import StageFile
from FileSystem.hsdStructures import MapMusicTable, MapPointTypesArray
from basicFunctions import uHex, hex2rgb, humansize, msg, printStatus, reverseDictLookup
from guiSubComponents import (
	LabelButton, cmsg, exportSingleTexture, getColoredShape, importGameFiles, exportSingleFileWithGui, 
	importSingleFileWithGui, importSingleTexture, getNewNameFromUser, BasicWindow, ToolTip, 
	ToolTipEditor, ToolTipButton, HexEditEntry, ColorSwatch, VerticalScrolledFrame, NeoTreeview )
from audioManager import AudioControlModule
from textureEditing import TexturesEditor


class StageSwapTable( object ):

	""" Data table for 20XX HP's Stage Engine. This table is 0x5D0 bytes long, and located at 
		the 'tableOffset' value below. It is composed of 31 entries, each 0x30 bytes long. 

		Each entry is of this form:
			B	0x0: Stage name (ASCII; only used as identifier in this table)
			B	0x8: New Stage ID; SSS, page 1
			B	0x9: New Stage ID; SSS, page 2
			B	0xA: New Stage ID; SSS, page 3
			B	0xB: New Stage ID; SSS, page 4
			B	0xC: Stage Flags; SSS, page 1
			B	0xD: Stage Flags; SSS, page 2
			B	0xE: Stage Flags; SSS, page 3
			B	0xF: Stage Flags; SSS, page 4
			I	0x10: RAM Pointer for Byte Replacement; SSS, page 1
			I	0x14: RAM Pointer for Byte Replacement; SSS, page 2
			I	0x18: RAM Pointer for Byte Replacement; SSS, page 3
			I	0x1C: RAM Pointer for Byte Replacement; SSS, page 4
			B	0x20: Byte Replacement at Pointer Address; SSS, page 1
			B	0x21: Byte Replacement at Pointer Address; SSS, page 2
			B	0x22: Byte Replacement at Pointer Address; SSS, page 3
			B	0x23: Byte Replacement at Pointer Address; SSS, page 4
			I	0x24: Random Byte Replacements at Pointer Address (if above is 0xFF); SSS, page 2
			I	0x28: Random Byte Replacements at Pointer Address (if above is 0xFF); SSS, page 3
			I	0x2C: Random Byte Replacements at Pointer Address (if above is 0xFF); SSS, page 4 
	"""

	stageOffsets = { # Key = internalStageId, value=tableEntryOffset
		0x0C: 	0x0,	# Fountain of Dreams
		0x10: 	0x30,	# Pokemon Stadium
		0x02:	0x60,	# Peach's Castle
		0x04:	0x90,	# Kongo Jungle
		0x08:	0xC0,	# Brinstar
		0x0E:	0xF0,	# Corneria
		0x0A:	0x120,	# Yoshi's Story
		0x14:	0x150,	# Onett
		0x12:	0x180,	# Mute City
		0x03:	0x1B0,	# Rainbow Cruise
		0x05:	0x1E0,	# Jungle Japes
		0x06:	0x210,	# Great Bay
		0x07:	0x240,	# Hyrule Temple
		0x09:	0x270,	# Brinstar Depths
		0x0B:	0x2A0,	# Yoshi's Island
		0x0D:	0x2D0,	# Green Greens
		0x15:	0x300,	# Fourside
		0x18:	0x330,	# Mushroom Kingdom I
		0x19:	0x360,	# Mushroom Kingdom II
		0x0F:	0x3C0,	# Venom
		0x11:	0x3F0,	# Poke Floats
		0x13:	0x420,	# Big Blue
		0x16:	0x450,	# Icicle Mountain
		0x1B:	0x4B0,	# Flatzone
		0x1C:	0x4E0,	# Dream Land (N64)
		0x1D:	0x510,	# Yoshi's Island (N64)
		0x1E:	0x540,	# Kongo Jungle (N64)
		0x24:	0x570,	# Battlefield
		0x25:	0x5A0	# Final Destination
	}

	def __init__( self ):
		# Get the DOL, and check for a file in the disc filesystem specifically for the stage swap table
		self.dol = globalData.disc.dol
		self.sstFile = globalData.disc.files.get( globalData.disc.gameId + '/StageSwapTable.bin' )

		if self.sstFile: # Newer versions of 20XX
			self.tableOffset = 0x0
		else:
			self.tableOffset = 0x3F8C80 # Offset/location within the DOL

	def getEntryValues( self, internalStageId ):

		""" Gets all values for a given stage ID. This includes data for each SSS page. 
			Returns 28 values; 0x28 bytes of data (doesn't get stage name identifier). """

		# Get the offset, data, and values for this entry
		entryOffset = self.stageOffsets[internalStageId]
		dataOffset = self.tableOffset + entryOffset + 8

		if self.sstFile:
			entryData = self.sstFile.getData( dataOffset, 0x28 )
		else:
			entryData = self.dol.getData( dataOffset, 0x28 )

		return struct.unpack( '>BBBBBBBBIIIIBBBBBBBBBBBBBBBB', entryData )

	def getEntryInfo( self, internalStageId, page ):

		""" Retrieves the values for a given stage, for a given page. 
			The provided page value is expected to be a 1-indexed int. """

		# Get the offset, data, and values for this entry
		values = self.getEntryValues( internalStageId )

		# Index the returned values for the given page
		page -= 1 # Count 0-indexed
		newStageId = values[page] # External Stage ID
		stageFlags = values[page+4]
		byteReplacePointer = values[page+8]
		byteReplacement = values[page+12]

		if page == 0: # No random byte values for first SSS page
			randomByteValues = ( 0, 0, 0, 0 )
		else:
			randomByteValuesIndex = 12 + ( 4 * page )
			randomByteValues = tuple( values[randomByteValuesIndex:randomByteValuesIndex+4] )

		return newStageId, stageFlags, byteReplacePointer, byteReplacement, randomByteValues

	def setEntryInfo( self, internalStageId, page, newStageId, stageFlags, byteReplacePointer, byteReplacement, randomByteValues ):

		""" Sets the values for a given stage, for a given page. 
			The provided page value is expected to be 1-indexed. """
		
		# Get the values for this entry
		values = self.getEntryValues( internalStageId )
		newValues = list( values )

		page -= 1 # Count 0-indexed
		newValues[page] = newStageId
		newValues[page+4] = stageFlags
		newValues[page+8] = byteReplacePointer
		newValues[page+12] = byteReplacement

		if page == 0:
			# Make sure not trying to use byte replacement on first page of SSS
			assert byteReplacement != 0xFF, 'Invalid Stage Swap Table values; cannot use random byte values on SSS page 1.'
		else:
			randomByteValuesIndex = 12 + ( 4 * page )
			newValues[randomByteValuesIndex:randomByteValuesIndex+4] = randomByteValues

		# Check if this is actually new (changed data)
		if values == tuple( newValues ):
			globalData.gui.updateProgramStatus( 'No changes to submit to the Stage Swap Table' )
		else:
			# Calculate the offset for the data, and pack the values to bytes
			entryOffset = self.stageOffsets[internalStageId]
			dataOffset = self.tableOffset + entryOffset + 8
			newData = struct.pack( '>BBBBBBBBIIIIBBBBBBBBBBBBBBBB', *newValues ) # Using '*' to expand the list into pack's args

			# Build a user message
			stageName = globalData.internalStageIds[internalStageId]
			updateMsg = 'Stage Swap Table updated for {} icon slot, on page {}'.format( stageName, page+1 )

			# Determine the file to update, and set the data packed above
			if self.sstFile:
				fileToModify = self.sstFile
			else:
				fileToModify = self.dol
			fileToModify.setData( dataOffset, newData )

			# Remember this change, and update the program's status bar
			if updateMsg not in fileToModify.unsavedChanges:
				fileToModify.unsavedChanges.append( updateMsg )
			globalData.gui.updateProgramStatus( updateMsg )

	def determineStageFiles( self, internalStageId, page, byteReplacePointer, byteReplacement, randomByteValues ):

		""" Determines the stage filenames that are expected to be loaded for a given stage icon on the Stage Select Screen. 
			Used to determine the filenames to search for in the disc, to populate the Variations treeview and other GUI elements. 

			Returns two values:
				- An int; DOL offset of the filename string that will be used for stage file loading
				- A list; of all filenames that may be loaded by the currently selected icon. """

		# Get the filename and its offset
		dolFilenameOffset, dolStageFilename = self.dol.getStageFileName( internalStageId )
		if dolFilenameOffset == -1:
			return -1, ()

		# Check for 20XX random neutrals
		if page == 1 and internalStageId in ( 0xC, 0x24, 0x25, 0x1C, 0x10, 0xA ): # FoD, Battlefield, FD, DreamLand, Stadium, Yoshi's Story
			filenames = []
			for char in '0123456789abcde': # F reserved for random stage
				if internalStageId == 0x10: # Pokemon Stadium; use .usd file extension
					filenames.append( 'GrP{}.usd'.format(char) )
				else:
					filenames.append( '{}.{}at'.format(dolStageFilename[:-4], char) )

		# One variation; no byte replacements
		elif byteReplacePointer == 0:
			if dolStageFilename == 'GrNSr.0at': # Not changed by stage swap table?!
				dolStageFilename = 'GrNSr.1at'
			
			filenames = [dolStageFilename]

		# Multiple variations; byte(s) will be replaced in the stage filename
		else:
			# Get the DOL offset of the byte to be replaced
			dolByteReplaceOffset = self.dol.offsetInDOL( byteReplacePointer ) # Convert from a RAM address to a DOL offset
			relativeOffset = dolByteReplaceOffset - dolFilenameOffset

			if byteReplacement == 0xFF:
				filenames = []
				for byte in randomByteValues:
					if byte == 0: continue
					newFilename = dolStageFilename[:relativeOffset] + chr( byte ) + dolStageFilename[relativeOffset+1:]
					filenames.append( newFilename )
			else:
				newFilename = dolStageFilename[:relativeOffset] + chr( byteReplacement ) + dolStageFilename[relativeOffset+1:]
				filenames = [newFilename]

		return dolFilenameOffset, filenames


class ScrollArrows( object ):

	""" These are for scrolling the canvases which contain the stage icons for each SSS page. """

	def __init__( self, canvas ):
		self.canvas = canvas
		canvas.scrollPosition = 0
		canvas.scrollHeight = 300
		self.scrollAmount = 150 # Positive values scroll up; negative scrolls down

		# Get/create the arrow images
		downArrowImage = getColoredShape( 'arrowDown', '#7077ac', getAsPilImage=True )
		downArrowImageHovered = getColoredShape( 'arrowDown', '#8089ff', getAsPilImage=True )

		# Copy and flip them to create the up arrows
		upArrowImage = downArrowImage.transpose( Image.FLIP_TOP_BOTTOM )
		upArrowImageHovered = downArrowImageHovered.transpose( Image.FLIP_TOP_BOTTOM )

		# Convert these into a type of image Tkinger can display
		self.downArrowImage = ImageTk.PhotoImage( downArrowImage )
		self.downArrowImageHovered = ImageTk.PhotoImage( downArrowImageHovered )
		self.upArrowImage = ImageTk.PhotoImage( upArrowImage )
		self.upArrowImageHovered = ImageTk.PhotoImage( upArrowImageHovered )
		
		self.addDownArrow()
		self.upArrowId = None
		
		# Add the arrow button click and hover event handlers
		canvas.tag_bind( 'downArrow', '<1>', lambda event: self.scrollItems(-self.scrollAmount) )
		canvas.tag_bind( 'downArrow', '<Enter>', self.downArrowHovered )
		canvas.tag_bind( 'downArrow', '<Leave>', self.downArrowUnhovered )
		canvas.tag_bind( 'upArrow', '<1>', lambda event: self.scrollItems(self.scrollAmount) )
		canvas.tag_bind( 'upArrow', '<Enter>', self.upArrowHovered )
		canvas.tag_bind( 'upArrow', '<Leave>', self.upArrowUnhovered )
		canvas.yview_scroll = self.onMouseWheelScroll

	def addUpArrow( self ): self.upArrowId = self.canvas.create_image( 600, 10, image=self.upArrowImage, anchor='ne', tags='upArrow' )
	def addDownArrow( self ): self.downArrowId = self.canvas.create_image( 600, 140, image=self.downArrowImage, anchor='se', tags='downArrow' )
	def removeUpArrow( self ):
		self.canvas.delete( self.upArrowId )
		self.upArrowId = None
		self.canvas['cursor'] = ''
	def removeDownArrow( self ):
		self.canvas.delete( self.downArrowId )
		self.downArrowId = None
		self.canvas['cursor'] = ''

	def downArrowHovered( self, event ):
		self.canvas['cursor'] = 'hand2'
		self.canvas.itemconfigure( self.downArrowId, image=self.downArrowImageHovered )
	def downArrowUnhovered( self, event ):
		self.canvas['cursor'] = ''
		self.canvas.itemconfigure( self.downArrowId, image=self.downArrowImage )

	def upArrowHovered( self, event ):
		self.canvas['cursor'] = 'hand2'
		self.canvas.itemconfigure( self.upArrowId, image=self.upArrowImageHovered )
	def upArrowUnhovered( self, event ):
		self.canvas['cursor'] = ''
		self.canvas.itemconfigure( self.upArrowId, image=self.upArrowImage )

	def scrollItems( self, distance ):

		""" Negative scrollPosition means the icons are moving up. """

		newScrollPosition = self.canvas.scrollPosition + distance

		if newScrollPosition >= 0: # Upper scroll bounds reached
			distance -= newScrollPosition # Subtract however much it was overshot
			self.removeUpArrow()

		elif newScrollPosition <= -self.canvas.scrollHeight: # Lower scroll bounds reached
			distance += abs( newScrollPosition + self.canvas.scrollHeight )
			self.removeDownArrow()

		else: # Not hitting a boundary; make sure both scroll arrows are present
			if not self.canvas.find_withtag( 'upArrow' ):
				self.addUpArrow()
			if not self.canvas.find_withtag( 'downArrow' ):
				self.addDownArrow()

		self.canvas.move( 'icons', 0, distance )
		self.canvas.move( 'selectionBorder', 0, distance )
		self.canvas.scrollPosition += distance

	def onMouseWheelScroll( self, amount, units ):
		# Multiply the amount a bit, since it will be 4 for each mouseWheel movement. And reverse it
		self.scrollItems( amount * -6 )


class MusicToolTip( ToolTip ):

	""" Subclass of the ToolTip class in order to provide an ACM (Audio Control Module), 
		for controlling or editing music selections, which behaves like a hoverable tooltip. 
		Also, unlike with the tooltip class, this module will wait a second before 
		disappearing, and should not disappear if the user's mouse is over it. 
		
		Note that the ACM used here shares the same Audio Engine as the main program GUI, 
		meaning that music played from these tooltip modules will first stop other music. """

	def __init__( self, master, valueIndex, mainTab, *args, **kwargs ):
		ToolTip.__init__( self, master, *args, **kwargs )

		self.valueIndex = valueIndex
		self.mainTab = mainTab
		self.acm = None 	# Audio Control Module

	def _hasText(self):
		return True # Makes sure the module thinks the tooltip (entry) is worth showing

	def leave(self, event=None):

		""" Instead of the usual tooltip behavior of unscheduling the creation method 
			(if it's queued) and destroying the window, we first wait a second to destroy it. """

		self._unschedule()
		self.master.after( 1000, self.queueHide )

	def queueHide(self):

		""" Overriding this method to first see if the entry widget is being 
			hovered over or is focused, implying the user intends to use it. """

		# Check if the tooltip window exists
		if not self._tipwindow:
			return
		elif self.mousedOver():
			return

		self._hide()

	def mousedOver( self ):

		# Get the widget currently beneath the mouse
		x, y = self.master.winfo_pointerxy()
		hoveredWidget = globalData.gui.root.winfo_containing( x, y )

		if not hoveredWidget:
			return False
		elif hoveredWidget == self._tipwindow:
			return True

		# Traverse upwards in the widget heirarchy
		parent = hoveredWidget.master
		while parent:
			if parent == self._tipwindow:
				return True
			parent = parent.master # Will eventually become '' after root

		return False

	def create_contents( self ):
		# Get the music ID and associated audio file
		musicId = self.getMusicId()
		musicFile = globalData.disc.getMusicFile( musicId )

		self.acm = AudioControlModule( self._tipwindow, self.mainTab.audioEngine, musicFile )
		self.acm.pack( side='left' )
		self.acm.bind( "<Leave>", self.leave, '+' ) # Hide again when user leaves the module

		LabelButton(self._tipwindow, 'configButton', self.edit, 'Edit' ).pack( side='left', padx=6 )

	def getMusicId( self ):

		""" Accesses the currently selected file's music table struct (for the music table 
			entry currently selected) and gets the music ID to be used for this tooltip. """

		# Get the index of the currently selected table entry, and the values for just this particular entry
		entryIndex = self.mainTab.getMusicTableEntryIndex()
		values = self.mainTab.musicTableStruct.getEntryValues( entryIndex )
		musicId = values[self.valueIndex]

		return musicId
	
	def edit( self, event=None ):

		""" Called by the 'Edit' button on the tooltip. Prompts the user 
			with a new window for choosing a new track for this song slot. """

		if not self.mainTab.musicTableStruct: # Failsafe; might not be possible
			globalData.gui.updateProgramStatus( 'No stage is selected', warning=True )
			return

		SongChooser( self.mainTab, self.valueIndex, self.getMusicId() )
		self._hide()

	def _show(self):
		# Hide any other tooltips currently shown
		for toolTip in self.mainTab.toolTips.itervalues():
			if toolTip._tipwindow and toolTip != self:
				toolTip._unschedule()
				toolTip._hide()

		if self._opts['state'] == 'disabled' or not self._hasText():
			self._unschedule()
			print( 'state disabled. unscheduling ' + str(self.valueIndex) )
			return
		if not self._tipwindow:
			self._tipwindow = Tk.Toplevel(self.master)
			# hide the window until we know the geometry
			self._tipwindow.withdraw()
			self._tipwindow.wm_overrideredirect(1)

			if self._tipwindow.tk.call("tk", "windowingsystem") == 'aqua':
				self._tipwindow.tk.call("::tk::unsupported::MacWindowStyle", "style", self._tipwindow._w, "help", "none")

			self.create_contents()
			self._tipwindow.update_idletasks()
			# x, y = self.coords()
			# self._tipwindow.wm_geometry("+%d+%d" % (x, y))
			# self._tipwindow.deiconify()
			#print 'deiconify after creation', self.valueIndex
		#else:
			#print 'deiconify', self.valueIndex
		x, y = self.coords()
		self._tipwindow.wm_geometry("+%d+%d" % (x, y))
		self._tipwindow.deiconify()

	def _hide(self):
		#print 'hiding', self.valueIndex
		tw = self._tipwindow
		#self._tipwindow = None
		if tw:
			#tw.destroy()
			#print 'withdraw'
			tw.withdraw()


class SongChooser( BasicWindow ):

	def __init__( self, stageTab, valueIndex, initialSelection=-1 ):

		BasicWindow.__init__( self, globalData.gui.root, "Song Chooser", resizable=True )
		self.stageTab = stageTab
		self.valueIndex = valueIndex # Index into the music table structure, relative to table entry
		self.lineDict = {} # Tracks which song is on which line; key=lineNumber, value=musicFileObj

		# Create the listbox, with a scrollbar
		scrollbar = Tk.Scrollbar( self.window, )
		self.listbox = Tk.Listbox( self.window, width=40, height=20, exportselection=0, activestyle='none', yscrollcommand=scrollbar.set )
		self.listbox.bind( '<<ListboxSelect>>', self.selectionChanged )
		self.listbox.grid( column=0, row=0, sticky='ns', padx=(6, 0) )
		scrollbar.config( command=self.listbox.yview )
		scrollbar.grid( column=1, row=0, sticky='ns', padx=(0, 6) )

		# Construct a list of music file objects from the disc; start with vanilla songs
		musicFiles = []
		for musicId in range( 0, 0x62 ):
			musicFile = globalData.disc.getMusicFile( musicId )
			if not musicFile: continue
			
			# Exclude fanfare (victory) audio clips and other short tracks most likely not wanted for music
			elif musicFile.size < 0xF0000 or musicFile.filename == 'howto.hps':
				if musicFile.filename not in ( '10.hps', 'inis2_02.hps' ): # Allow this track through (both are for MK2 Finale)
					#print ' - skipping', hex(musicId), '|', musicFile.filename, '-', musicFile.longDescription
					continue

			musicFiles.append( musicFile )
			
		# Add Hex Tracks if this is 20XX
		if stageTab.stageSwapTable:
			# Hex track number doesn't correspond to music ID, so tracks 0x30-0x62 haven't been included yet either
			for musicId in range( 0x10030, 0x10100 ):
				musicFile = globalData.disc.getMusicFile( musicId )
				if musicFile:
					musicFiles.append( musicFile )

		# Populate the listbox
		self.listbox.insert( 'end', 'None' )
		self.lineDict[0] = None
		lineToSelect = -1
		for musicFile in musicFiles:
			if musicFile.longDescription:
				self.listbox.insert( 'end', musicFile.longDescription )
			else:
				self.listbox.insert( 'end', 'No description (' + musicFile.filename + ')' )

			self.lineDict[len(self.lineDict)] = musicFile

			if musicFile.musicId == initialSelection:
				lineToSelect = len( self.lineDict ) - 1

		# Create an ACM for this window
		self.acm = AudioControlModule( self.window, self.stageTab.audioEngine )
		self.acm.grid( column=0, columnspan=2, row=1, pady=4 )
		self.listbox.bind( '<Double-1>', self.acm.playAudio )

		# Select the current/initially set song
		if lineToSelect != -1:
			self.listbox.selection_set( lineToSelect )
			self.acm.audioFile = self.lineDict[lineToSelect]

		buttonsCell = ttk.Frame( self.window )
		ttk.Button( buttonsCell, text='Select', command=self.selectSong ).grid( column=0, row=1, padx=10 )
		ttk.Button( buttonsCell, text='Cancel', command=self.close ).grid( column=1, row=1, padx=10 )
		buttonsCell.grid( column=0, columnspan=2, row=2, pady=4 )

		self.window.columnconfigure( 0, weight=1 )
		self.window.columnconfigure( (1,2), weight=0 )
		self.window.rowconfigure( 'all', weight=1 )

	def selectionChanged( self, event ):

		""" Changes the file currently assigned to the ACM. """

		lineNumber = self.listbox.curselection()[0]
		self.acm.audioFile = self.lineDict[lineNumber]

	def selectSong( self ):

		""" Confirms the current selection, and sets the song's music ID in the stage file. 
			If Main Music or Alt. Main Music are changed, also update Sudden Death and Alt. 
			Sudden Death Music to be the same (this is the probable usual case, and can still 
			be changed independantly afterwards if the user wishes. """

		# Get the song ID and name
		lineNumber = self.listbox.curselection()[0]
		musicFile = self.lineDict[lineNumber]
		if musicFile:
			musicId = musicFile.musicId
			newSongName = musicFile.longDescription
		else:
			musicId = -1
			newSongName = 'None'

		# Get the index of the currently selected music table entry
		entryIndex = self.stageTab.getMusicTableEntryIndex()

		# Get the name of the target music selection, and its GUI label widget (the one displaying name info, not the description label)
		if self.valueIndex == 1:
			targetMusic = 'Main Music and Sudden Death Music'
			labels = ( self.stageTab.mainMusicLabel, self.stageTab.suddenDeathMusicLabel )
			toolTips = ( self.stageTab.toolTips['mainMusic'], self.stageTab.toolTips['suddenMusic'] )
		elif self.valueIndex == 2:
			targetMusic = 'Alt. Music and Sudden Death Alt. Music'
			labels = ( self.stageTab.altMusicLabel, self.stageTab.altSuddenDeathLabel )
			toolTips = ( self.stageTab.toolTips['altMusic'], self.stageTab.toolTips['altSuddenMusic'] )
		elif self.valueIndex == 3:
			targetMusic = 'Sudden Death Music'
			labels = ( self.stageTab.suddenDeathMusicLabel, )
			toolTips = ( self.stageTab.toolTips['suddenMusic'], )
		elif self.valueIndex == 4:
			targetMusic = 'Sudden Death Alt. Music'
			labels = ( self.stageTab.altSuddenDeathLabel, )
			toolTips = ( self.stageTab.toolTips['altSuddenMusic'], )
		else:
			raise Exception( 'Invalid valueIndex given to Song Chooser module: ' + str(self.valueIndex) )

		# Construct a description for the change (for file.unsavedChanges, and for the program status bar)
		origSongName = labels[0]['text'].split( '|' )[-1].strip()
		userMessage = '{} of Music Table entry {} updated from {} to {}'.format(targetMusic, entryIndex+1, origSongName, newSongName)

		# Update the value in the file structure
		if self.valueIndex == 1 or self.valueIndex == 2: # Update both the main/alt music and the super sudden death main/alt music
			self.stageTab.musicTableStruct.setEntryValue( entryIndex, self.valueIndex, musicId ) # Ignores extra steps which will be handled below
			self.stageTab.selectedStage.updateStructValue( self.stageTab.musicTableStruct, self.valueIndex+2, musicId, userMessage, 'Music updated', entryIndex=entryIndex )
		else:
			self.stageTab.selectedStage.updateStructValue( self.stageTab.musicTableStruct, self.valueIndex, musicId, userMessage, 'Music updated', entryIndex=entryIndex )

		# Update the GUI
		globalData.gui.updateProgramStatus( userMessage )
		for label in labels:
			#label['text'] = '0x{:X} | {}'.format( musicId, newSongName )
			label['text'] = uHex( musicId ) + ' | ' + newSongName
		
		# Destroy the music control module (it may just be hidden). This will cause it to be recreated on next mouse-over
		for toolTip in toolTips:
			if toolTip._tipwindow:
				toolTip._tipwindow.destroy()
				toolTip._tipwindow = None

		# Close this Song Chooser interface
		self.close()


class StageManager( ttk.Frame ):

	""" Info viewer and editor interface for stages in SSBM. """

	stageTextureOffsets = { # Key=internalStageId, value=( icon, previewText, insignia )
		0x02: ( 0xE2C0, 0x3C840, 0x2EB40 ), # Princess Peach's Castle
		0x03: ( 0xF2E0, 0x3E0C0, 0x2EB40 ), # Rainbow Cruise
		0x04: ( 0x10300, 0x3F940, 0x2F340 ), # Kongo Jungle
		0x05: ( 0x11320, 0x411C0, 0x2F340 ), # Jungle Japes
		0x06: ( 0x12340, 0x42A40, 0x2FB40 ), # Great Bay
		0x07: ( 0x13360, 0x442C0, 0x2FB40 ), # Hyrule Temple
		0x08: ( 0x14380, 0x45B40, 0x30340 ), # Brinstar
		0x09: ( 0x153A0, 0x473C0, 0x30340 ), # Brinstar Depths
		0x0A: ( 0x163C0, 0x48C40, 0x30B40 ), # Yoshi's Story
		0x0B: ( 0x173E0, 0x4A4C0, 0x30B40 ), # Yoshi's Island
		0x0C: ( 0x18400, 0x4BD40, 0x31340 ), # Fountain of Dreams
		0x0D: ( 0x19420, 0x4D5C0, 0x31340 ), # Green Greens
		0x0E: ( 0x1A440, 0x4EE40, 0x31B40 ), # Corneria
		0x0F: ( 0x1B460, 0x506C0, 0x31B40 ), # Venom
		0x10: ( 0x1C480, 0x51F40, 0x32340 ), # Pokemon Stadium
		0x11: ( 0x1D4A0, 0x537C0, 0x32340 ), # Poke Floats
		0x12: ( 0x1E4C0, 0x55040, 0x32B40 ), # Mute City
		0x13: ( 0x1F4E0, 0x568C0, 0x32B40 ), # Big Blue
		0x14: ( 0x20500, 0x58140, 0x33340 ), # Onett
		0x15: ( 0x21520, 0x599C0, 0x33340 ), # Fourside
		0x16: ( 0x24580, 0x5E340, 0x33B40 ), # Icicle Mountain
		#0x17: ( 0x, 0x, 0x ), # Unused?
		0x18: ( 0x22540, 0x5B240, 0x2EB40 ), # Mushroom Kingdom
		0x19: ( 0x23560, 0x5CAC0, 0x2EB40 ), # Mushroom Kingdom II
		#0x1A: ( 0x, 0x, 0x ), # Akaneia (Deleted Stage)
		0x1B: ( 0x255A0, 0x5FBC0, 0x34340 ), # Flat Zone
		0x1C: ( 0x28600, 0x64540, 0x31340 ), # Dream Land (N64)
		0x1D: ( 0x29120, 0x65DC0, 0x30B40 ), # Yoshi's Island (N64)
		0x1E: ( 0x29C40, 0x67640, 0x2F340 ), # Kongo Jungle (N64)
		0x24: ( 0x265C0, 0x61440, 0x34B40 ), # Battlefield
		0x25: ( 0x275E0, 0x62CC0, 0x35340 ), # Final Destination
	}

	def __init__( self, parent, mainGui ):

		ttk.Frame.__init__( self, parent ) #, padding="11 0 0 11" ) # Padding order: Left, Top, Right, Bottom.

		# Add this tab to the main GUI
		mainGui.mainTabFrame.add( self, text=' Stage Manager ' )

		# Create the primary set of tabs for the Stage Manager interface
		# mainGui.style.configure( 'TNotebook', configure={"tabmargins": [2, 5, 2, 0]}, borderwidth=0 )
		# mainGui.style.configure( 'TNotebook.Tab', configure={
		# 														"borderwidth": 0,
		# 														"bordercolor" : 'blue',
		# 														"darkcolor" : 'blue',
		# 														"lightcolor" : 'blue',
		# 														"padding": [5, 1], 
		# 														"background": 'blue'
		# 													} )
		# "TNotebook": {
        #       "configure": {"tabmargins": [2, 5, 2, 0]},
        #       "borderwidth": 0
        #      }
		# "TNotebook.Tab": {
        #           "configure": {
        #                         "borderwidth": 0,
        #                         "bordercolor" : BG_COLOUR,
        #                         "darkcolor" : BG_COLOUR,
        #                         "lightcolor" : BG_COLOUR,
        #                         "padding": [5, 1], "background": BG_COLOUR
        #                         }
        #           }
		mainGui.style.configure( 'TNotebook', borderwidth=4 )
		mainGui.style.configure( 'TNotebook.Tab', borderwidth=4 )
		self.tabManager = ttk.Notebook( self,  )
		self.tabManager.pack( fill='both', expand=1 )

		# Create the SSS tab as the main tab of the above notebook
		sssTabFrame = ttk.Frame( self, borderwidth=0 )
		self.tabManager.add( sssTabFrame, text='Stage Selection' )

		self.selectedStage = None
		self.selectedStageSlotId = -1	# Internal Stage ID for the vanilla slot, not necessarily the stage the slot is set to load
		self.musicTableStruct = None
		self.stageSwapTable = None # For use with 20XX
		self.audioEngine = mainGui.audioEngine
		self.toolTips = {}
		padding = 6

		# Add SSS page tabs
		self.pagesNotebook = ttk.Notebook( sssTabFrame )
		self.pagesNotebook.grid( column=0, row=0, pady=12 )

		variationsLabelFrame = ttk.Frame( sssTabFrame ) # Padding order: Left, Top, Right, Bottom.
		ttk.Label( variationsLabelFrame, text='- -  Variations  - -', foreground='blue' ).grid( column=0, row=0, pady=4 )
		treeScroller = Tk.Scrollbar( variationsLabelFrame )
		self.variationsTreeview = ttk.Treeview( variationsLabelFrame, selectmode='browse', show='tree', columns=('filename'), yscrollcommand=treeScroller.set, height=7 )
		self.variationsTreeview.column( '#0', width=200 )
		self.variationsTreeview.column( 'filename', width=90 )
		self.variationsTreeview.tag_configure( 'fileNotFound', foreground='red' )
		self.variationsTreeview.tag_configure( 'warning', foreground='#A0A000' ) # Shade of yellow
		self.variationsTreeview.grid( column=0, row=1, sticky='ns' )
		treeScroller.config( command=self.variationsTreeview.yview )
		treeScroller.grid( column=1, row=1, sticky='ns' )
		variationsLabelFrame.grid( column=1, row=0, padx=padding, pady=padding )

		# Add treeview event handlers
		self.variationsTreeview.bind( '<<TreeviewSelect>>', self.stageVariationSelected )
		# self.variationsTreeview.bind( '<Double-1>', onFileTreeDoubleClick )
		#self.variationsTreeview.bind( "<3>", self.createContextMenu ) # Right-click

		# Construct the right-hand side of the interface, the info panels
		row1 = ttk.Frame( sssTabFrame )
		
		# Basic Info
		basicLabelFrame = ttk.LabelFrame( row1, text='  Basic Info  ', labelanchor='n', padding=8 )
		ttk.Label( basicLabelFrame, text=('RSSS Name:\n'
										'File Size:\n'
										'Init Function:\n'
										'OnGo Function:') ).grid( column=0, row=0, padx=(0, 5) )
		self.basicInfoLabel = ttk.Label( basicLabelFrame, width=25 )
		self.basicInfoLabel.grid( column=1, row=0 )
		ttk.Button( basicLabelFrame, text='Edit Properties', width=24, command=self.editBasicProperties ).grid( column=0, columnspan=2, row=1, pady=(3, 0) )
		basicLabelFrame.grid( column=0, row=0, padx=(padding, 0), pady=padding )

		# Stage Swap Details
		fileLoadLabelFrame = ttk.LabelFrame( row1, text='  20XX HP Stage Swap Details  ', labelanchor='n', padding=8 )
		ttk.Label( fileLoadLabelFrame, text=('Orig. Internal Stage ID:\n'
											'New Internal Stage ID:\n'
											'New External Stage ID:\n'
											'Filename Offset:\n'
											'Byte Replacement Offset:\n'
											'Byte Replacement:\n'
											'Stage Flags:') ).grid( column=0, row=0, padx=(0, 5) )
		self.stageSwapDetailsLabel = ttk.Label( fileLoadLabelFrame, width=38 )
		self.stageSwapDetailsLabel.grid( column=1, row=0 )
		self.editStageSwapDetailsBtn = ttk.Button( fileLoadLabelFrame, text='Edit', width=8, command=self.editSwapDetails )
		self.editStageSwapDetailsBtn.place( anchor='se', relx=1, rely=1 )
		fileLoadLabelFrame.grid( column=1, columnspan=2, row=0, padx=0, pady=padding )

		# Controls (basic functions like import/export)
		#emptyWidget = Tk.Frame( relief='flat' ) # This is used as a simple workaround for the labelframe, so we can have no text label with no label gap.
		#self.controlsFrame = ttk.Labelframe( row1, labelwidget=emptyWidget, padding=(20, 4) )
		self.controlsFrame = ttk.LabelFrame( row1, text='  Stage File Operations  ', labelanchor='n', padding=8 )
		ttk.Button( self.controlsFrame, text='Export', command=self.exportStage ).grid( column=0, row=0, padx=4, pady=4 )
		ttk.Button( self.controlsFrame, text='Import', command=self.importStage ).grid( column=1, row=0, padx=4, pady=4 )
		ttk.Button( self.controlsFrame, text='Delete', command=self.deleteStage ).grid( column=0, row=2, padx=4, pady=4 )
		ttk.Button( self.controlsFrame, text='Add Variation', command=self.addStageVariation ).grid( column=1, row=2, padx=4, ipadx=7, pady=4 )
		ttk.Button( self.controlsFrame, text='Test', command=self.testStage ).grid( column=0, row=3, padx=4, pady=4 )
		ttk.Button( self.controlsFrame, text='Rename', command=self.renameStage ).grid( column=1, row=3, padx=4, pady=4 )
		rsssBtn = ttk.Button( self.controlsFrame, text='Rename RSSS Name', command=self.renameRsssName )
		ToolTip( rsssBtn, 'Name shown on the\nRandom Stage Select Screen.', justify='center' )
		rsssBtn.grid( column=0, columnspan=2, row=4, padx=4, pady=4, ipadx=9 )
		self.controlsFrame.grid( column=3, row=0, padx=(0, padding), pady=padding )

		row1.grid( column=0, columnspan=2, row=1, sticky='nsew' )
		row1.columnconfigure( 'all', weight=1 )
		row1.rowconfigure( 'all', weight=1 )
		row2 = ttk.Frame( sssTabFrame )

		# Music (entry selector and edit button)
		musicLabelFrame = ttk.LabelFrame( row2, text='  Music Table  ', labelanchor='n', padding=8 )
		ttk.Label( musicLabelFrame, text='Music Table Entry: ' ).grid( column=0, row=0 )
		self.musicTableEntry = Tk.StringVar()
		self.musicTableOptionMenu = ttk.OptionMenu( musicLabelFrame, self.musicTableEntry, '', *[], command=self.selectMusicTableEntry )
		self.musicTableOptionMenu['state'] = 'disabled'
		self.musicTableOptionMenu.grid( column=0, columnspan=2, row=1, pady=(0, 8) )
		#ttk.Button( musicLabelFrame, text='TEST', command=self.test ).place( anchor='ne', relx=1.0, rely=0 )

		# Music (song labels)
		ttk.Label( musicLabelFrame, text='External Stage ID:' ).grid( column=0, row=2, padx=(0, 5), sticky='w' )
		self.extStageIdLabel = ttk.Label( musicLabelFrame, width=50 )
		self.extStageIdLabel.grid( column=1, row=2, sticky='w' )
		ttk.Label( musicLabelFrame, text='Main Music:' ).grid( column=0, row=3, padx=(0, 5), sticky='w' )
		self.mainMusicLabel = ttk.Label( musicLabelFrame )
		self.toolTips['mainMusic'] = MusicToolTip( self.mainMusicLabel, 1, self, delay=500, location='e' )
		self.mainMusicLabel.grid( column=1, row=3, sticky='w' )
		ttk.Label( musicLabelFrame, text='Alt. Music:' ).grid( column=0, row=4, padx=(0, 5), sticky='w' )
		self.altMusicLabel = ttk.Label( musicLabelFrame )
		self.toolTips['altMusic'] = MusicToolTip( self.altMusicLabel, 2, self, delay=500, location='e' )
		self.altMusicLabel.grid( column=1, row=4, sticky='w' )
		ttk.Label( musicLabelFrame, text='Sudden Death Music:' ).grid( column=0, row=5, padx=(0, 5), sticky='w' )
		self.suddenDeathMusicLabel = ttk.Label( musicLabelFrame )
		self.toolTips['suddenMusic'] = MusicToolTip( self.suddenDeathMusicLabel, 3, self, delay=500, location='e' )
		self.suddenDeathMusicLabel.grid( column=1, row=5, sticky='w' )
		ttk.Label( musicLabelFrame, text='Sudden Death Alt. Music:' ).grid( column=0, row=6, padx=(0, 5), sticky='w' )
		self.altSuddenDeathLabel = ttk.Label( musicLabelFrame )
		self.toolTips['altSuddenMusic'] = MusicToolTip( self.altSuddenDeathLabel, 4, self, delay=500, location='e' )
		self.altSuddenDeathLabel.grid( column=1, row=6, sticky='w' )

		# Music (behavior and alt music chance)
		ttk.Label( musicLabelFrame, text='Music Behavior:' ).grid( column=0, row=7, padx=(0, 5), sticky='w' )
		self.songBehaviorLabel = ttk.Label( musicLabelFrame )
		self.toolTips['musicBehaviorEditor'] = ToolTipButton( self.songBehaviorLabel, self, delay=500, location='e', width=4 )
		self.songBehaviorToolTipText = Tk.StringVar()
		self.toolTips['musicBehavior'] = ToolTip( self.songBehaviorLabel, textvariable=self.songBehaviorToolTipText, delay=500, wraplength=350, location='e', offset=55 )
		self.songBehaviorLabel.grid( column=1, row=7, sticky='w' )
		ttk.Label( musicLabelFrame, text='Alt. Music % Chance:' ).grid( column=0, row=8, padx=(0, 5), sticky='w' )
		self.altMusicChanceLabel = ttk.Label( musicLabelFrame )
		self.toolTips['altChanceEditor'] = ToolTipEditor( self.altMusicChanceLabel, self, delay=500, location='e', width=4 )
		self.altMusicChanceLabel.grid( column=1, row=8, sticky='w' )
		musicLabelFrame.grid( column=0, columnspan=2, row=1, padx=(35, 0), pady=padding, sticky='ew' )

		# Preview Text
		previewTextLabelFrame = ttk.LabelFrame( row2, text='  Preview Text  ', labelanchor='n', padding=8 )
		self.previewTextCanvas = Tk.Canvas( previewTextLabelFrame, width=224, height=56, borderwidth=0, highlightthickness=0 )
		self.previewTextCanvas.image = None # Used to store an image for this canvas, to prevent garbage collection
		self.previewTextCanvas.pilImage = None
		def noScroll( arg1, arg2 ): pass
		self.previewTextCanvas.yview_scroll = noScroll
		self.previewTextCanvas.grid( column=0, columnspan=3, row=0, pady=(2, 6) )
		ttk.Label( previewTextLabelFrame, text='Top Text:' ).grid( column=0, row=1 )
		self.previewTextTopTextEntry = ttk.Entry( previewTextLabelFrame, width=22 )
		self.previewTextTopTextEntry.bind( '<Return>', self.generatePreviewText )
		self.previewTextTopTextEntry.grid( column=1, columnspan=2, row=1, pady=3 )
		ttk.Label( previewTextLabelFrame, text='Bottom Text:' ).grid( column=0, row=2 )
		self.previewTextBottomTextEntry = ttk.Entry( previewTextLabelFrame, width=22 )
		self.previewTextBottomTextEntry.bind( '<Return>', self.generatePreviewText )
		self.previewTextBottomTextEntry.grid( column=1, columnspan=2, row=2, pady=3 )
		previewBtn = ttk.Button( previewTextLabelFrame, text='Preview Texture', command=self.generatePreviewText )
		previewBtn.grid( column=0, columnspan=2, row=3, pady=3, ipadx=7 )
		ToolTip( previewBtn, text='Generates a new texture from the text entered above. Does not automatically save the texture to file; for that, hit Save.' )
		saveBtn = ttk.Button( previewTextLabelFrame, text='Save', command=self.savePreviewText )
		saveBtn.grid( column=2, row=3, pady=3 )
		ToolTip( saveBtn, text='Saves the texture shown above to the current stage select screen file.' )
		exportBtn = ttk.Button( previewTextLabelFrame, text='Export', command=self.exportPreviewText )
		exportBtn.grid( column=0, columnspan=2, row=4, pady=3 )
		ToolTip( exportBtn, text='Export the texture shown above to an external PNG/TPL file.' )
		importBtn = ttk.Button( previewTextLabelFrame, text='Import', command=self.importPreviewText )
		importBtn.grid( column=2, row=4, pady=3 )
		ToolTip( importBtn, text='Import an external PNG/TPL file to the current stage select screen file.' )
		previewTextLabelFrame.grid( columnspan=2, column=2, row=1, padx=35, pady=padding, sticky='ew' )

		row2.grid( column=0, columnspan=2, row=2, sticky='nsew' )
		row2.columnconfigure( 'all', weight=1 )
		row2.rowconfigure( 'all', weight=1 )
		
		# Configure window resize behavior
		sssTabFrame.columnconfigure( 0, weight=3 )
		sssTabFrame.columnconfigure( 1, weight=1 )
		sssTabFrame.rowconfigure( 0, weight=0 )
		sssTabFrame.rowconfigure( 1, weight=1 )
		sssTabFrame.rowconfigure( 2, weight=1 )

	def test( self ):
		importGameFiles( multiple=False )
		importGameFiles( multiple=True )

	def clear( self ):

		""" Clears and resets this tab's GUI contents. """

		self.selectedStage = None

		# Delete the current items in the canvases notebook
		for tab in self.pagesNotebook.winfo_children():
			tab.destroy()
		
		# Delete the current items in the stage variations treeview
		for item in self.variationsTreeview.get_children():
			self.variationsTreeview.delete( item )

		# Clear labels
		self.basicInfoLabel['text'] = ''
		self.stageSwapDetailsLabel['text'] = ''

		# Clear the preview text canvas
		self.previewTextCanvas.delete( 'all' )
		self.previewTextCanvas.image = None
		self.previewTextCanvas.pilImage = None

		# Disable the controls for stages until a stage is selected
		self.editStageSwapDetailsBtn['state'] = 'disabled'
		for widget in self.controlsFrame.winfo_children():
			widget['state'] = 'disabled'

		self.clearMusicSection()

		# Empty the text entry widgets for Preview Text
		self.previewTextTopTextEntry.delete( 0, 'end' )
		self.previewTextBottomTextEntry.delete( 0, 'end' )

	def clearMusicSection( self ):
		# Clear labels
		self.basicInfoLabel['text'] = ''
		self.extStageIdLabel['text'] = ''
		self.mainMusicLabel['text'] = ''
		self.altMusicLabel['text'] = ''
		self.suddenDeathMusicLabel['text'] = ''
		self.altSuddenDeathLabel['text'] = ''
		self.songBehaviorLabel['text'] = ''
		self.altMusicChanceLabel['text'] = ''

		# Clear the music dropdown menu
		self.musicTableOptionMenu['state'] = 'disabled'
		self.musicTableOptionMenu.set_menu( None )
		self.musicTableOptionMenu._variable.set( '' )

	def getRsssName( self, stageSlotId ):

		""" Gets the name for this stage used on the Random Stage Select Screen. """

		# Construct the filename to pull the string from
		if self.stageSwapTable: # Means it's 20XX
			canvas = self.getCurrentCanvas()
			filename = '/SdMenu.{}sd'.format( canvas.pageNumber )
		else:
			filename = '/SdMenu.usd'

		sisFile = globalData.disc.files.get( globalData.disc.gameId + filename )

		return sisFile.getStageMenuName( stageSlotId )

	def updateBasicInfo( self, stageFile ):
		
		rsssName = self.getRsssName( self.selectedStageSlotId ).encode( 'utf8' )
		readableSize = humansize( stageFile.size )

		self.basicInfoLabel['text'] = '{}\n{}\n{:X}\n{:X}'.format( rsssName, readableSize, stageFile.initFunction, stageFile.onGoFunction )

	def editBasicProperties( self ):
		
		""" Creates a new tab in the Textures Editor interface for the given file. """
		
		# Create the new tab for the given file
		stageFile = self.getSelectedStage()
		if not stageFile:
			msg( 'Please first select a stage to edit!', 'No Stage Selected', warning=True )
			return
		
		self.addStageFileTab( stageFile )

	def addStageFileTab( self, stageFile ):

		""" Adds a new tab for the given stage file to the Stage Manager interface, 
			or switches to an existing tab if that file is already open. """

		# Check if a tab has already been created/added for this file
		for windowName in self.tabManager.tabs()[1:]: # Skips first 'Stage Selection' tab
			tab = globalData.gui.root.nametowidget( windowName )

			if tab.file == stageFile: # Found it!
				self.tabManager.select( tab )
				break

		else: # Loop above didn't break; mod not found
			# Create a new tab for this file and populate it
			newTab = StagePropertyEditor( self, stageFile )
			self.tabManager.add( newTab, text=stageFile.filename )

			# Switch to the new tab
			self.tabManager.select( newTab )

	def updateSwapDetails( self, newIntStageId, newExtStageId, iFilenameOffset, byteReplacePointer, byteReplacement, randByteReplacements, stageFlags ):

		""" Assesses values from the 20XX Stage Stap Table, and filenames from the DOL, to construct 
			strings to be displayed in the GUI for the Stage Swap Details information display panel. """
		
		# Create a string for the original stage to load
		origStageName = globalData.internalStageIds[self.selectedStageSlotId]
		filename = self.dol.getStageFileName( self.selectedStageSlotId )[1]
		origBaseStage = '0x{:X} | {} ({})'.format( self.selectedStageSlotId, origStageName, filename )
		
		# Create a string for the new stage to load
		# Check if the new stage is the same as the original stage (no file swap on the base stage)
		if self.selectedStageSlotId == newIntStageId or newIntStageId == 0:
			newBaseStage = '0x{:X} | {} (same)'.format( newIntStageId, origStageName ) # Use the same file description as above
		elif newIntStageId == 0x1A: # i.e. external stage ID 0x15, Akaneia (a deleted stage)
			newBaseStage = '0x1A | Akaneia (deleted stage)'
		elif newIntStageId == 0x16: # i.e. external stage ID 0x1A, Icicle Mountain (anticipating no hacked stages of this); switch to current Target Test stage
			newBaseStage = '0x16 | Current Target Test stage'
		else:
			# Use the internal ID to get the new stage name and file name
			stageName = globalData.internalStageIds.get( newIntStageId, 'Unknown' )
			#filename = globalData.stageFileNames.get( newIntStageId, 'Unknown' )
			filename = self.dol.getStageFileName( newIntStageId )[1]
			if stageName == 'Unknown':
				print( 'Unable to find a stage name for internal stage ID ' + hex(newIntStageId) )
			elif filename == 'Unknown':
				print( 'Unable to find a stage filename for internal stage ID ' + hex(newIntStageId) )
			newBaseStage = '0x{:X} | {} ({})'.format( newIntStageId, stageName, filename )

		# Check for stKind (external stage ID description)
		if newExtStageId == 0:
			stkindString = 'N/A (no swap)'
		else:
			stkindDescription = globalData.externalStageIds.get( newExtStageId, 'Unidentified Ext. ID' )
			stkindString = '0x{:X} | {}'.format( newExtStageId, stkindDescription )

		# Create a string for the filename offset
		sFilenameOffset = '0x{:X} | 0x{:X}'.format( self.dol.offsetInRAM(iFilenameOffset), iFilenameOffset )

		# Create a string for the byte replacement offset and values
		if byteReplacePointer == 0:
			sByteReplaceOffset = 'N/A'
			byteReplacement = 'N/A'
		else:
			dolByteReplaceOffset = self.dol.offsetInDOL( byteReplacePointer ) # Convert from a RAM address to a DOL offset
			sByteReplaceOffset = '0x{:X} | 0x{:X}'.format( byteReplacePointer, dolByteReplaceOffset )
			relativeOffset = dolByteReplaceOffset - iFilenameOffset

			if relativeOffset < 0 or relativeOffset >= len( filename ):
				warningMsg = 'Invalid stage swap parameters detected for {}! Byte replacement offset: {}  Filename offset: {}'.format( filename, sByteReplaceOffset, sFilenameOffset )
				globalData.gui.updateProgramStatus( warningMsg, warning=True )
				byteReplacement = 'Invalid definition'
			else:
				origByte = filename[relativeOffset]
				if byteReplacement == 0xFF:
					newByte = ' / '.join( [chr(byte) for byte in randByteReplacements if byte != 0] )
				else:
					newByte = chr( byteReplacement )
				byteReplacement = '{} - > {}'.format( origByte, newByte )
		
		# Create a string for the stage flags
		if stageFlags == 0:
			stageFlags = 'None'
		else:
			stageFlags = uHex( stageFlags )

		self.stageSwapDetailsLabel['text'] = '\n'.join( (origBaseStage, newBaseStage, stkindString, sFilenameOffset, sByteReplaceOffset, byteReplacement, stageFlags) )

	def getTextureOffset( self, intStageId, icon=False, previewText=False, insignia=False ):

		""" Gets offsets of the textures specified, adjusting them depending on whether this is 20XX or Vanilla Melee. """

		offsets = []
		iconOffset, previewTextOffset, insigniaOffset = self.stageTextureOffsets[intStageId]

		if icon:
			offsets.append( iconOffset )
		if previewText:
			offsets.append( previewTextOffset )
		if insignia:
			offsets.append( insigniaOffset )
		assert offsets, 'Invalid usage of getTextureOffset(); no targets given.'
		
		# Check for the 20XX stage swap table to determine offset adjustments
		# if self.stageSwapTable: # Has a custom icon which shifts the other texture offsets
		# 	dataShift = 0x420
		# else: # Vanilla file/offsets
		# 	dataShift = -0x20 # Removes displacement of the file header

		# Check the cursor icon to see if icon offsets need adjusting
		canvas = self.getCurrentCanvas()
		cursorIconData = canvas.sssFile.getStruct( 0xDEA0 ) # Offset relative to data section
		assert cursorIconData, 'Unable to initialize a structure for the cursor texture; unrecognized file.'
		if cursorIconData.length == 0x400: # Vanilla file/offsets
			dataShift = -0x20 # Removes displacement of the file header
		else: # Has a custom icon which shifts the other texture offsets
			dataShift = 0x420
		offsets = [ o + dataShift for o in offsets ]

		return offsets

	def addStageSelectCanvas( self, pageName, filename ):

		""" Adds a representation for a Stage Select Screen to the Stage Manager interface. 
			These are added to the notebook widget in the top-left of the main Stage Selection tab. """

		# Create a new tab/frame for this page and add it to the notebook
		newTab = ttk.Frame( self.pagesNotebook )
		self.pagesNotebook.add( newTab, text=pageName )

		# Create the canvas and set up some data containers
		newTab.canvas = canvas = Tk.Canvas( newTab, width=640, height=150, borderwidth=0, highlightthickness=0 )
		canvas.sssFile = sssFile = globalData.disc.files.get( globalData.disc.gameId + '/' + filename )
		assert sssFile, 'Unable to get the {} file from the disc filesystem!'.format( filename )
		canvas.create_image( 0, 0, image=globalData.gui.imageBank('sssBg'), anchor='nw', tags='bg' )
		canvas.pageName = pageName.strip()
		try:
			canvas.pageNumber = int( pageName.split()[-1] )
		except: # e.g. for 'Vanilla SSS'
			canvas.pageNumber = 1
		canvas.iconImages = {} # Used to store the images, to prevent garbage collection
		canvas.iconCanvasIds = {} # key=canvasIconIid, value=internalStageSlotId
		canvas.pack()

		# Init the stage select screen file (separate data groups, build pointer and offset lists, etc.)
		# tic = time.clock()
		sssFile.initialize()
		# toc = time.clock()
		# print 'time to initialize:', toc - tic
		
		# Add the first two rows (Icicle Mountain through Flat Zone)
		#tic = time.clock()
		x = 50
		y = 47
		for internalStageId in ( 0x16, 2, 4, 6, 0xA, 0xC, 0xE, 3, 5, 7, 0xB, 0xD, 0xF, 0x1B ):
			#iconTextureOffset = self.stageTextureOffsets[internalStageId][0] + dataShift
			iconTextureOffset = self.getTextureOffset( internalStageId, icon=True )[0]
			canvas.iconImages[internalStageId] = sssFile.getTexture( iconTextureOffset, 64, 56, 9, 0xE00 )
			canvasId = canvas.create_image( x, y, image=canvas.iconImages[internalStageId], anchor='nw', tags='icons' )
			canvas.iconCanvasIds[canvasId] = internalStageId

			# Adjust coordinates for next row
			if internalStageId == 0x16: # First icon (Icicle Mountain) placed; move to top row
				y = 17
			elif internalStageId == 0xE: # Corneria placed; switch to bottom row
				y = 77 # 60 px below top row
			elif internalStageId == 0xF: # Venom placed; switch back to middle row
				y = 47

			if internalStageId == 0xE: # Corneria placed; switch to bottom row
				x = 118
			else: # Progress right-ward
				x += 68 # Assuming 4 px between icons

		# Load the next two rows off-canvas ()
		x = 118
		y = 167 # 150 px below the above set (17 px padding above/below rows)
		for internalStageId in ( 0x8, 0x14, 0x12, 0x10, 0x18, 0x9, 0x15, 0x13, 0x11, 0x19 ):
			#iconTextureOffset = self.stageTextureOffsets[internalStageId][0] + dataShift
			iconTextureOffset = self.getTextureOffset( internalStageId, icon=True )[0]
			canvas.iconImages[internalStageId] = sssFile.getTexture( iconTextureOffset, 64, 56, 9, 0xE00 )
			canvasId = canvas.create_image( x, y, image=canvas.iconImages[internalStageId], anchor='nw', tags='icons' )
			canvas.iconCanvasIds[canvasId] = internalStageId

			# Adjust coordinates for next row
			if internalStageId == 0x18: # MKI placed; switch to bottom row
				y = 227 # 60 px below above row
				x = 118
			else: # Progress right-ward
				x += 68 # Assuming 4 px between icons
		
		# Load the final, single row
		x = 192
		y = 349 # 300 px below the first set (49 px padding above/below rows)
		for internalStageId in ( 0x24, 0x25, 0x1C, 0x1D, 0x1E ):
			#iconTextureOffset = self.stageTextureOffsets[internalStageId][0] + dataShift
			iconTextureOffset = self.getTextureOffset( internalStageId, icon=True )[0]

			if internalStageId == 0x24 or internalStageId == 0x25: # Resize Battlefield and FD, since that's how they appear in-game
				origImage = sssFile.getTexture( iconTextureOffset, 64, 56, 9, 0xE00, getAsPilImage=True )
				resizedImage = origImage.resize( (48, 48), Image.ANTIALIAS )
				canvas.iconImages[internalStageId] = ImageTk.PhotoImage( resizedImage )
			else:
				canvas.iconImages[internalStageId] = sssFile.getTexture( iconTextureOffset, 48, 48, 9, 0x900 )

			canvasId = canvas.create_image( x, y, image=canvas.iconImages[internalStageId], anchor='nw', tags='icons' )
			canvas.iconCanvasIds[canvasId] = internalStageId

			# Adjust coordinates for next row
			x += 52 # Assuming 4 px between icons

		# Add click and hover event handlers
		canvas.tag_bind( 'icons', '<1>', self.iconClicked )
		canvas.tag_bind( 'icons', '<Enter>', self.iconHovered )
		canvas.tag_bind( 'icons', '<Leave>', self.iconUnhovered )

		# Add a right-click context menu
		canvas.menu = Tk.Menu( globalData.gui.root, tearoff=False )
		canvas.menu.add_command( label='Export icon texture', underline=0, command=self.exportIconTexture )
		canvas.menu.add_command( label='Import icon texture', underline=0, command=self.importIconTexture )
		canvas.tag_bind( 'icons', '<3>', self.iconRightClicked )

		# Add arrows and scroll wheel support for traversing the icons
		ScrollArrows( canvas )

		# toc = time.clock()
		# print 'time to populate', filename, 'canvas:', toc-tic

	# Icon hover (mousein/mouseout) events for stage icons on the SSS canvas
	def iconHovered( self, event ): self.pagesNotebook['cursor'] = 'hand2'
	def iconUnhovered( self, event ): self.pagesNotebook['cursor'] = ''

	def loadVanillaStageLists( self ):
		self.clear()

		self.addStageSelectCanvas( '  Vanilla SSS  ', 'MnSlMap.usd' )
		#self.addStageSelectCanvas( '  Other  ' )

		# Get the DOL file
		self.dol = globalData.disc.dol
		self.stageSwapTable = None

	def load20XXStageLists( self ):

		""" Load stage info from the currently loaded disc into this tab. """

		self.clear()

		# Create the page canvases
		for pageName in ( '  SSS Page 1  ', '  SSS Page 2  ', '  SSS Page 3  ', '  SSS Page 4  ' ):
			pageFileName = 'MnSlMap.{}sd'.format( pageName.split()[-1] )
			self.addStageSelectCanvas( pageName, pageFileName )

		# Get the DOL file
		self.dol = globalData.disc.dol
		self.stageSwapTable = StageSwapTable()

	def iconRightClicked( self, event ):

		""" Determines the stage icon that was right-clicked on, store it, and summons the right-click context menu. """

		canvas = event.widget
		itemId = canvas.find_closest( event.x, event.y )[0]
		self.stageRightClickedOn = canvas.iconCanvasIds[itemId] # Internal Stage ID
		canvas.menu.post( event.x_root, event.y_root )

	def exportIconTexture( self ):

		""" Export the displayed stage icon texture to an external PNG/TPL file, 
			while prompting the user on where they'd like to save it. 
			Updates the default directory to search in when opening or exporting files. 
			Also handles updating the GUI with the operation's success/failure status. """

		# Determine a filename default/suggestion
		internalStageId = self.stageRightClickedOn
		if globalData.disc.is20XX:
			filename = '{} icon slot (page {}).png'.format( globalData.internalStageIds[internalStageId], canvas.pageNumber )
		else:
			filename = '{} icon slot.png'.format( globalData.internalStageIds[internalStageId] )

		# Get the image
		iconTextureOffset = self.getTextureOffset( internalStageId, icon=True )[0]
		canvas = self.getCurrentCanvas()
		if internalStageId in ( 0x24, 0x25, 0x1C, 0x1D, 0x1E ):
			texture = canvas.sssFile.getTexture( iconTextureOffset, 48, 48, 9, 0x900, getAsPilImage=True )
		else:
			texture = canvas.sssFile.getTexture( iconTextureOffset, 64, 56, 9, 0xE00, getAsPilImage=True )

		exportSingleTexture( filename, texture, imageType=9 )
	
	def importIconTexture( self ):

		""" Imports a stage icon texture over the icon that was last right-clicked on. 
			Also handles updating the GUI with the operation's success/failure status. """

		internalStageId = self.stageRightClickedOn
		if internalStageId in ( 0x1C, 0x1D, 0x1E ): # These icons are smaller
			imagePath = importSingleTexture( "Choose an icon texture of 48x48 to import" )
		else:
			imagePath = importSingleTexture( "Choose an icon texture of 64x56 to import" )

		# The above will return an empty string if the user canceled
		if not imagePath: return ''

		canvas = self.getCurrentCanvas()
		sssFile = canvas.sssFile
		textureName = globalData.internalStageIds[internalStageId]

		# Load the icon texture and set it in the SSS file
		imageDataOffset = self.getTextureOffset( internalStageId, icon=True )[0]
		returnCode, _, _ = sssFile.setTexture( imageDataOffset, imagePath=imagePath, textureName='{} icon texture'.format(textureName) ) # Will also record the change

		if returnCode == 0:
			# Get the new texture data, so we can show it in the GUI
			if internalStageId == 0x24 or internalStageId == 0x25: # Resize Battlefield and FD, since that's how they appear in-game
				origImage = sssFile.getTexture( imageDataOffset, 64, 56, 9, 0xE00, getAsPilImage=True )
				resizedImage = origImage.resize( (48, 48), resample=globalData.checkSetting('resampleFilter') )
				canvas.iconImages[internalStageId] = ImageTk.PhotoImage( resizedImage )

			elif internalStageId in ( 0x1C, 0x1D, 0x1E ):
				canvas.iconImages[internalStageId] = sssFile.getTexture( imageDataOffset, 48, 48, 9, 0x900 )
			else:
				canvas.iconImages[internalStageId] = sssFile.getTexture( imageDataOffset, 64, 56, 9, 0xE00 )

			# Update the image in the canvas
			itemId = self.getCanvasIconId( canvas, internalStageId )
			canvas.itemconfig( itemId, image=canvas.iconImages[internalStageId] )

			selectedTabId = self.pagesNotebook.select() # This will be a tab ID, not the actual widget
			tabName = self.pagesNotebook.tab( selectedTabId, 'text' ).strip()
			globalData.gui.updateProgramStatus( '{} icon texture updated in the {} file ({}), at offset 0x{:X}'.format(textureName, tabName, sssFile.filename, 0x20+imageDataOffset), success=True )

		elif returnCode == 1:
			globalData.gui.updateProgramStatus( 'Unable to set the icon texture; unable to find palette information', error=True )
		elif returnCode == 2:
			globalData.gui.updateProgramStatus( 'Unable to set the icon texture; the new image data is too large', error=True )
		elif returnCode == 3:
			globalData.gui.updateProgramStatus( 'Unable to set the icon texture; the new palette data is too large', error=True )
		else:
			globalData.gui.updateProgramStatus( 'Unable to set the icon texture due to an unknown error', error=True )

	def iconClicked( self, event ):

		""" Initial method called when a canvas stage icon is clicked on. Determines and 
			sets the internal stage ID of the icon that was clicked on, and calls the main
			stage selection method. """
		
		globalData.gui.updateProgramStatus( '' )

		# Determine which canvas item was clicked on, and use that to look up the stage
		canvas = event.widget
		iconIid = canvas.find_closest( event.x, event.y )[0]

		self.selectStage( canvas, iconIid )

	def getCanvasIconId( self, canvas, internalStageId ):

		""" Canvas IDs are the IDs assigned to images, lines, and other items added to the 
			canvases. This returns an ID for the stage icon image for a given internal stage ID. """

		for canvasIconIid, intStageId in canvas.iconCanvasIds.items():
			if intStageId == internalStageId:
				return canvasIconIid
		else:
			raise Exception( 'Unable to find a canvas icon ID for internal stage ID 0x{:X}.'.format(self.selectedStageSlotId) )

	def selectStage( self, canvas, iconIid=None ):
		
		""" Moves the selection border to the new icon, clears the Variations list, and calls the appropriate click method. """

		# Remove any pre-existing selection border (from all canvases)
		for tab in self.pagesNotebook.winfo_children():
			tab.canvas.delete( 'selectionBorder' )

		# Get the canvas item id of the currently selected stage
		if not iconIid:
			iconIid = self.getCanvasIconId( canvas, self.selectedStageSlotId )

		self.selectedStageSlotId = canvas.iconCanvasIds.get( iconIid, None )
		if not self.selectedStageSlotId:
			return

		# Highlight the newly selected icon
		selectionCoords = canvas.coords( iconIid )
		borderWidth = 3
		newX = selectionCoords[0] - borderWidth
		newY = selectionCoords[1] - borderWidth
		if self.selectedStageSlotId in ( 0x24, 0x25, 0x1C, 0x1D, 0x1E ): # These icons are 48x48 in size
			canvas.create_rectangle( newX, newY, newX+53, newY+53, outline='gold', width=borderWidth, tags='selectionBorder' )
		else:
			canvas.create_rectangle( newX, newY, newX+69, newY+61, outline='gold', width=borderWidth, tags='selectionBorder' )
		
		# Delete the current items in the stage variations treeview
		for item in self.variationsTreeview.get_children():
			self.variationsTreeview.delete( item )

		# Empty the text entry widgets for Preview Text
		# self.previewTextTopTextEntry.delete( 0, 'end' )
		# self.previewTextBottomTextEntry.delete( 0, 'end' )

		# Call the main click event handler
		if self.stageSwapTable:
			self.clicked20XXIcon( canvas )
		else:
			self.clickedVanillaIcon( canvas )

	def getVariationDisplayName( self, stageFile, pageNumber ):

		# if pageNumber == 1:
		# 	useShortNames = True
		# else:
		# 	useShortNames = False
		
		if stageFile.isRandomNeutral():
			#displayName = stageFile.getDescription( inConvenienceFolder=useShortNames, updateInternalRef=False )
			displayName = stageFile.shortDescription
		# elif stageFile.filename[2] == 'T': # Target Test stage
		# 	displayName = stageFile.longDescription
		elif stageFile.longDescription:
			displayName = stageFile.longDescription
		else:
			displayName = ' - - '

		return displayName

	def clickedVanillaIcon( self, canvas ):
		# Find the stage file string in the DOL for the selected stage
		dolFilenameOffset, dolStageFilename = self.dol.getStageFileName( self.selectedStageSlotId )
		if dolFilenameOffset == -1:
			globalData.gui.updateProgramStatus( 'Unable to determine a stage file name for stage ID 0x{:X}!'.format(self.selectedStageSlotId), warning=True )
			return
		
		isoPath = globalData.disc.gameId + '/' + dolStageFilename
		stageFile = globalData.disc.files.get( isoPath )
		if stageFile:
			displayName = self.getVariationDisplayName( stageFile, 1 )
			self.variationsTreeview.insert( '', 'end', text=displayName, values=(dolStageFilename, isoPath) )
		else:
			self.variationsTreeview.insert( '', 'end', text='- No File -', values=(dolStageFilename, isoPath), tags='fileNotFound' )
			
		self.stageSwapDetailsLabel['text'] = '0x{:X}\nN/A (no swap)\nN/A (no swap)\nN/A\nN/A\nN/A\nN/A'.format( self.selectedStageSlotId )

		# Set the Preview Text image
		previewTextureOffset = self.getTextureOffset( self.selectedStageSlotId, previewText=True )[0]
		newPreviewImage = canvas.sssFile.getTexture( previewTextureOffset, 224, 56, 0, 0x1880, getAsPilImage=True )
		self.updatePreviewImage( newPreviewImage )

		# Select the first item in the treeview by default (which will also call the selection method, stageVariationSelected)
		variationIids = self.variationsTreeview.get_children()
		if len( variationIids ) > 0:
			firstItem = variationIids[0]
			self.variationsTreeview.focus( firstItem )
			self.variationsTreeview.selection_set( firstItem )

	def clicked20XXIcon( self, canvas ):

		""" Check the 20XX Stage Engine system to determine what file(s) this icon may load, and populate the GUI with information. """

		# Get information from the Stage Swap Table on what file(s) this icon/stage slot should load
		newExtStageId, stageFlags, byteReplacePointer, byteReplacement, randomByteValues = self.stageSwapTable.getEntryInfo( self.selectedStageSlotId, canvas.pageNumber )

		# Get the Internal Stage ID of the stage to be loaded
		if newExtStageId == 0: # No change; this will be the currently selected stage slot
			newIntStageId = self.selectedStageSlotId
		else:
			newIntStageId = self.dol.getIntStageIdFromExt( newExtStageId )
			if newIntStageId == 0x16: # i.e. external stage ID 0x1A, Icicle Mountain (anticipating no hacked stages of this); switch to current Target Test stage
				print( 'Unsupported; target test stage filename undetermined' )
				self.stageVariationUnselected()
				return

		dolFilenameOffset, filenames = self.stageSwapTable.determineStageFiles( newIntStageId, canvas.pageNumber, byteReplacePointer, byteReplacement, randomByteValues )

		# Populate the variations treeview with the file names (and descriptions) determined above
		gameId = globalData.disc.gameId
		pathsAdded = set() # Watches for duplicates
		for filename in filenames:
			isoPath = gameId + '/' + filename
			stageFile = globalData.disc.files.get( isoPath )

			if stageFile:
				displayName = self.getVariationDisplayName( stageFile, canvas.pageNumber )

				if isoPath in pathsAdded:
					self.variationsTreeview.insert( '', 'end', text=displayName +' (duplicate)', values=(filename, isoPath), tags='warning' )
				else:
					self.variationsTreeview.insert( '', 'end', text=displayName, values=(filename, isoPath) )
			else:
				self.variationsTreeview.insert( '', 'end', text='- No File -', values=(filename, isoPath), tags='fileNotFound' ) # No need to check for dups; not possible
			
			pathsAdded.add( isoPath )

		# Update text shown in the 'Stage Swap Details' panel
		self.updateSwapDetails( newIntStageId, newExtStageId, dolFilenameOffset, byteReplacePointer, byteReplacement, randomByteValues, stageFlags )

		# Set the Preview Text image
		previewTextureOffset = self.getTextureOffset( self.selectedStageSlotId, previewText=True )[0]
		newPreviewImage = canvas.sssFile.getTexture( previewTextureOffset, 224, 56, 0, 0x1880, getAsPilImage=True )
		self.updatePreviewImage( newPreviewImage )

		# Select the first item in the treeview by default (which will also call the selection method, stageVariationSelected)
		variationIids = self.variationsTreeview.get_children()
		if len( variationIids ) > 0:
			firstItem = variationIids[0]
			self.variationsTreeview.focus( firstItem )
			self.variationsTreeview.selection_set( firstItem )

	def getSelectedStage( self ):

		""" Gets the stage variation currently selected in the "Variations" file list, as a stage file object. """

		iidSelectionsTuple = self.variationsTreeview.selection()
		if len( iidSelectionsTuple ) != 1: # May happen if no stage is selected
			return None

		isoPath = self.variationsTreeview.item( iidSelectionsTuple[0], 'values' )[1] # Values tuple is (filename, isoPath)

		return globalData.disc.files.get( isoPath )

	def getCurrentCanvas( self ):

		""" Gets the canvas from the currently selected SSS tab. """

		selectedTabId = self.pagesNotebook.select() # This will be a tab ID, not the actual widget
		selectedTab = globalData.gui.root.nametowidget( selectedTabId )

		return selectedTab.canvas

	def stageVariationUnselected( self ):

		""" Called when a non-existant stage from the Variations treeview (a stage file that doesn't exist in the disc) 
			is clicked on. Clears or resets GUI elements specific to a stage file. """

		self.selectedStage = None

		self.clearMusicSection()

		# Disable the controls for stages until a stage is selected
		for widget in self.controlsFrame.winfo_children():
			if widget['text'] == 'Add Variation':
				widget['state'] = 'normal'
			else:
				widget['state'] = 'disabled'

	def stageVariationSelected( self, event ):

		""" This is called when a user clicks on a file selection in the "Variations" file list display,
			and it is also automatically called after a stage icon is clicked on, in order to load the
			first file in the list by default. """

		stageFile = self.getSelectedStage()

		# Check whether this is the same stage that was already selected (to prevent unncessary work)
		if not stageFile:
			self.stageVariationUnselected()
			return
		# elif stageFile == self.selectedStage: # This was already selected
		# 	return
		else:
			self.selectedStage = stageFile

		# Initialize the file (parse it for data structures)
		stageFile.initialize()

		# Show some basic info
		self.updateBasicInfo( stageFile )

		# Get song info from the music table struct and update the GUI with it
		self.updateMusicTableInterface( stageFile )

		# Enable the stage control buttons
		if self.stageSwapTable: # Means it's 20XX
			self.editStageSwapDetailsBtn['state'] = 'normal'
			canvas = self.getCurrentCanvas()

			for widget in self.controlsFrame.winfo_children():
				# Disable the Add Variation button if this stage is maxed out on slots; all else enabled
				if widget['text'] == 'Add Variation' and not self.allowAddingVariations( stageFile, canvas ):
					widget['state'] = 'disabled'
				else:
					widget['state'] = 'normal'

		else: # Is vanilla Melee
			self.editStageSwapDetailsBtn['state'] = 'disabled'
			
			for widget in self.controlsFrame.winfo_children():
				if widget['text'] == 'Add Variation':
					widget['state'] = 'disabled'
				else:
					widget['state'] = 'normal'

	def getMusicTableEntryIndex( self ):

		""" Returns the index of the currently selected music table entry (0-indexed),
			parsed from the string of the music table dropdown widget. """

		currentSelection = self.musicTableEntry.get()
		return int( currentSelection.split()[1] ) - 1

	def updateMusicTableInterface( self, stageFile ):
		
		""" Gets/stores the given stage's music table struct, creates the Table Entry dropdown list,
			calls the method to populate the song labels, and updates their ACM tooltips. """

		# Get song info from the music table struct
		self.musicTableStruct = stageFile.getMusicTableStruct()
		values = self.musicTableStruct.getValues()
		valuesPerEntry = len( values ) / self.musicTableStruct.entryCount

		# Build the list of options for the Music Table entry list dropdown
		options = []
		for i in range( self.musicTableStruct.entryCount ):
			# Pick out the external stage ID names to get the names for each entry
			externalId = values[i*valuesPerEntry]
			externalIdName = globalData.externalStageIds.get( externalId, 'Unknown External ID' )
			options.append( 'Entry {} | {}'.format(i+1, externalIdName) )

		# Update the dropdown menu with the above options
		self.musicTableOptionMenu['state'] = 'normal'
		self.musicTableOptionMenu.set_menu( options[0], *options ) # Using * to expand the list into the arguments input

		# Select the first entry in the table by default, and populate the Music Table fields in the GUI
		self.selectMusicTableEntry( options[0] )

		# Update the audio files attached to the tooltip ACMs (Audio Control Modules)
		# for tooltip in self.toolTips.values():
		# 	if isinstance( tooltip, MusicToolTip ):
		# 		tooltip.updateAcm()
	
	def selectMusicTableEntry( self, selectedOption ):

		""" Updates information displayed in the Music Table pane. Called by the user selecting an entry 
			from the dropdown menu, as well as by the method called when a stage variation is selected. """

		# Get the index of the currently selected table entry, and the values for just this particular entry
		entryIndex = int( selectedOption.split()[1] ) - 1 # Switching back to 0-indexed self.musicTableEntry
		values = self.musicTableStruct.getEntryValues( entryIndex )
		songBehavior = values[5]

		# Display this entry's external stage ID
		self.extStageIdLabel['text'] = uHex( values[0] )

		# Convert the song IDs to names and update the respective labels
		valueIndex = 1
		toolTips = { 1: self.toolTips['mainMusic'], 2: self.toolTips['altMusic'], 3: self.toolTips['suddenMusic'], 4: self.toolTips['altSuddenMusic'] }
		for label in ( self.mainMusicLabel, self.altMusicLabel, self.suddenDeathMusicLabel, self.altSuddenDeathLabel ):
			songId = values[valueIndex]
			toolTip = toolTips[valueIndex]

			if songId == -1:
				label['text'] = '-1 | None'
				toolTip._opts['state'] = 'normal'

				# Remove the audio file from the ACM, so it doesn't play a past-selected song
				if toolTip.acm:
					toolTip.acm.audioFile = None

			elif songBehavior == 8 and ( valueIndex == 2 or valueIndex == 4 ): # Dealing with disabled alt music
				label['text'] = 'N/A (not used by this behavior)'
				toolTip._opts['state'] = 'disabled'

			else:
				#songName = globalData.musicIdNames.get( songId )
				musicFile = globalData.disc.getMusicFile( songId )

				if musicFile:
					if musicFile.longDescription:
						label['text'] = uHex( songId ) + ' | ' + musicFile.longDescription
					else:
						label['text'] = uHex( songId ) + ' | Unknown Track'
				else:
					label['text'] = uHex( songId ) + ' | Not Found in the Disc!'

				# Update the tooltip's ACM, so it plays the correct file
				if toolTip.acm:
					toolTip.acm.audioFile = musicFile
				toolTip._opts['state'] = 'normal'

			valueIndex += 1
		
		# Update the song behavior label and tooltip with the above info
		unknownIdString = 'Unknown (Behavior ID: ' + uHex(songBehavior) + ')' # Used as default text if the below 'get' fails
		self.songBehaviorLabel['text'] = uHex( songBehavior ) + ' | ' + self.musicTableStruct.enums['Song_Behavior'].get( songBehavior, unknownIdString )
		self.songBehaviorToolTipText.set( self.musicTableStruct.songBehaviorDescriptions.get( songBehavior, 'N/A' ) )

		# Update the Alt. Music % Chance label
		if songBehavior > 1 and songBehavior < 8:
			self.altMusicChanceLabel['text'] = '{}%'.format( values[6] )
		else:
			self.altMusicChanceLabel['text'] = 'N/A (Not used by this behavior)'

	def updatePreviewImage( self, newImage ):

		""" Updates the stage preview text canvas display. Called when the user selects a stage 
			(in which case the image is pulled from the SSS file), or to display an image created 
			by the generatePreviewText() method. """

		# Clear the canvas
		self.previewTextCanvas.delete( 'all' )

		# Add the new image
		self.previewTextCanvas.image = ImageTk.PhotoImage( newImage )
		self.previewTextCanvas.pilImage = newImage
		self.previewTextCanvas.create_image( 0, 0, image=self.previewTextCanvas.image, anchor='nw' )
	
	def generatePreviewText( self, event=None ):

		""" Generates new preview text, based on the text input in the Entry fields. """

		# Load the fonts to use
		topTextFontSize = 17
		bottomTextFontSize = 39
		try:
			# Construct the font paths
			topTextFontPath = os.path.join( globalData.paths['fontsFolder'], 'Palatino Linotype, Bold.ttf' )
			bottomTextFontPath = os.path.join( globalData.paths['fontsFolder'], 'A-OTF Folk Pro, Bold.otf' )

			# Load the fonts
			topTextFont = ImageFont.FreeTypeFont( topTextFontPath, topTextFontSize )
			bottomTextFont = ImageFont.FreeTypeFont( bottomTextFontPath, bottomTextFontSize )
		except Exception as err:
			print( 'Unable to load fonts for preview text: ' + str(err) )
			globalData.gui.updateProgramStatus( 'Unable to load fonts for preview text!', error=True )
			return

		# Get the text to be written
		topText = self.previewTextTopTextEntry.get()
		bottomText = self.previewTextBottomTextEntry.get()

		# Define width for the initial image (creating it wider than needed so it can be later squished, to make it look more like the vanilla text)
		widthBuffer = 50 # This is used to prevent the text from being cut off when transformed (sheared for italicising). This is later cropped off
		imageWidth = 269 + widthBuffer # Space excluding the width buffer is ~20 wider than the finished texture

		# Increase the width of the image to accommodate more characters (to an extent); the image will later be squished more horizontally to overcome this
		width, height = bottomTextFont.getsize( bottomText )
		sizeDiff = width - imageWidth + widthBuffer + 40 # Extra 20 to ensure there's at least a small band between the text and edge of the texture
		if sizeDiff >= 200:
			imageWidth += 240
		elif sizeDiff > 0:
			imageWidth += sizeDiff

		# If still too wide, reduce the font size of the bottom text
		while width >= imageWidth - widthBuffer - 5:
			bottomTextFontSize -= 1
			bottomTextFont = ImageFont.FreeTypeFont( bottomTextFontPath, bottomTextFontSize )
			width, height = bottomTextFont.getsize( bottomText )

		# Create the initial image
		newTexture = Image.new( 'L', (imageWidth, 56), 'black' )
		imgDrawing = ImageDraw.Draw( newTexture )
		
		# Draw the bottom text (twice, so it's a bit bolder) and apply a shear to italicize it
		xCoord = ( imageWidth/2 - width/2 ) + 18
		imgDrawing.text( (xCoord, 33-height/2), bottomText, 'white', font=bottomTextFont )
		imgDrawing.text( (xCoord, 33-height/2), bottomText, 'white', font=bottomTextFont )
		transformMatrix = ( 1, .5, 0, 0, 1, 0 )
		newTexture = newTexture.transform( (imageWidth, 56), Image.AFFINE, data=transformMatrix, resample=Image.BICUBIC )

		# Crop off the width buffer
		newTexture = newTexture.crop( (widthBuffer/2, 0, imageWidth-widthBuffer/2, 56) )

		# Horizontally squish the texture down to its final size
		newTexture = newTexture.resize( (224, 56), resample=Image.BICUBIC )

		width, height = topTextFont.getsize( topText )
		
		# Adjust the font size of the top text if it's too wide
		addKerning = False
		if width >= 224:
			while width >= 224:
				topTextFontSize -= 1
				topTextFont = ImageFont.FreeTypeFont( os.path.join( globalData.paths['fontsFolder'], 'Palatino Linotype, Bold.ttf'), topTextFontSize )
				width, height = topTextFont.getsize( topText )

		# If the top text isn't already quite wide, add 1px to the kerning
		elif width < 210:
			# Check how much width would be required with the new kerning
			width = 0
			relCharPositions = [ 0 ]
			for char in topText:
				charWidth = topTextFont.getsize( char )[0]
				nextCharPosition = width + charWidth + 1
				relCharPositions.append( nextCharPosition )
				width += charWidth + 1

			width -= 1 # Ignore kerning after last character
			if width < 210:
				addKerning = True

		imgDrawing = ImageDraw.Draw( newTexture )
		imgDrawing.fontmode
		if addKerning:
			# print 'writing top text with kerning'
			# Write the top text with increased kerning
			startingPosition = 112 - width / 2
			for char, relPosition in zip( topText, relCharPositions ):
				imgDrawing.text( (startingPosition+relPosition, 1), char, 'white', font=topTextFont )
		else:
			# print 'writing top text without kerning'
			#width, height = topTextFont.getsize( topText )
			imgDrawing.text( (112-width/2, 1), topText, 'white', font=topTextFont )

		self.updatePreviewImage( newTexture )

		if globalData.gui:
			globalData.gui.updateProgramStatus( 'Displaying generated preview. Click "Save" to save it to the SSS file' )

	def savePreviewText( self ):

		""" Saves the currently displayed preview text image to the SSS file. """

		# Make sure there is an image to save
		if not self.previewTextCanvas.pilImage:
			globalData.gui.updateProgramStatus( 'No texture to save. Choose a stage to begin' )
			return

		# Get the target SSS file
		canvas = self.getCurrentCanvas()
		sssFile = canvas.sssFile

		# Get the offset for the preview texture and set it in the SSS file
		imageDataOffset = self.getTextureOffset( self.selectedStageSlotId, previewText=True )[0]
		returnCode, _, _ = sssFile.setTexture( imageDataOffset, self.previewTextCanvas.pilImage, textureName='Preview text texture' ) # Will also record the change

		if returnCode == 0:
			selectedTabId = self.pagesNotebook.select() # This will be a tab ID, not the actual widget
			tabName = self.pagesNotebook.tab( selectedTabId, 'text' ).strip()
			globalData.gui.updateProgramStatus( 'Preview text texture updated in the {} file ({}), at offset 0x{:X}'.format(tabName, sssFile.filename, 0x20+imageDataOffset), success=True )

		else: # Probably don't need to be too specific; low chance of problems here
			globalData.gui.updateProgramStatus( 'Unable to set the preview text texture', error=True )

	def exportPreviewText( self ):

		""" Export the currently shown stage preview text texture to an external PNG/TPL file, 
			while prompting the user on where they'd like to save it. 
			Updates the default directory to search in when opening or exporting files. 
			Also handles updating the GUI with the operation's success/failure status. """

		# Make sure there is an image to export
		if not self.previewTextCanvas.pilImage:
			globalData.gui.updateProgramStatus( 'No texture to export. Choose a stage to begin' )
			return

		exportSingleTexture( "Stage preview text.png", self.previewTextCanvas.pilImage, imageType=0 )

	def importPreviewText( self ):

		""" Prompts the user for a texture to import, and then updates it in the GUI and saves it to the current SSS file. """
		
		if not self.selectedStage:
			msg( 'No stage file is selected!' )
			return

		# Prompt the user for an image file to import
		imagePath = importSingleTexture( "Choose an icon texture of 224x56 to import" )

		# The above will return an empty string if the user canceled
		if not imagePath: return ''

		# Load the texture as a PIL image
		try:
			newImage = Image.open( imagePath )
		except Exception as err:
			globalData.gui.updateProgramStatus( 'Unable to open the texture due to an unrecognized error. Check the log for details', error=True )
			print( 'Unable to load image for preview text; {}'.format(err) )
			return

		# Ensure the image isn't too large (at least by dimensions)
		if not newImage.size == ( 224, 56 ):
			globalData.gui.updateProgramStatus( 'Invalid texture size. The preview text texture should be 224x56 pixels', warning=True )
			msg( 'The preview text texture should be 224x56 pixels.', 'Invalid texture size.' )
			return

		self.updatePreviewImage( newImage )
		self.savePreviewText()

	def exportStage( self ):
		if self.selectedStage:
			exportSingleFileWithGui( self.selectedStage )
		else: # Failsafe (the button should be disabled in this case)
			msg( 'No stage file is selected!' )

	def importStage( self ):

		""" Prompts the user for an external/standalone file to import, 
			and then replaces the currently selected file with that file. 
			If no file is selected, and a file can't be found to load, this 
			will instead add a new file to the disc. """

		selection = self.variationsTreeview.selection()

		# Make sure there is only 1 stage selected (failsafe; shouldn't be possible?)
		if len( selection ) == 0:
			msg( 'No stage file is selected!' )
			return
		elif len( selection ) > 1:
			msg( 'Please only select one file to import.' )
			return

		if self.selectedStage:
			# A single, existing file is selected; replace it
			success = importSingleFileWithGui( self.selectedStage )
			
			# At least make sure it's a stage
			# if not self.selectedStage.__class__ == StageFile:
			# 	msg( 'The imported file does not appear to be a stage file!', 'Invalid Import', warning=True )
			# 	globalData.gui.updateProgramStatus( 'Invalid import; operation aborted', warning=True )
			# 	self.selectedStage = None
			# 	return

			stageObj = self.selectedStage
		else:
			# Attempt to get the file object
			isoPath = self.variationsTreeview.item( selection[0], 'values' )[1]
			stageObj = globalData.disc.files.get( isoPath )

			if stageObj: # Failsafe; not sure how this could happen
				print( 'selectedStage=None while attempting to import a stage' )
				success = importSingleFileWithGui( stageObj )

			else: # No file by this name in the disc; it's probably a random neutral stage slot selected. User probably wants to add a new file to disc
				stageObj = self.getStageFileToAddToDisc( isoPath )
				if stageObj:
					success = True

		if success:
			self.updateGuiForNewlyAddedStage( stageObj, selection )

		# If 20XX, check if the SST is configured to load this new stage
		#if globalData.disc.is20XX:

	def updateGuiForNewlyAddedStage( self, stageObj, selection=None ):

		""" Handles updating elements in each tab in the program (if present) to accomodate 
			a new stage being added to the disc (also works for imports/replacements). 
			Also prompts the user to rename the new stage. """

		# Update the name shown in the Variations treeview
		if selection:
			canvas = self.getCurrentCanvas()
			displayName = self.getVariationDisplayName( stageObj, canvas.pageNumber )
			self.variationsTreeview.item( selection[0], text=displayName, tags=() )

		# Show the new file in the Disc File Tree
		if globalData.gui.discTab:
			globalData.gui.discTab.loadDisc( updateStatus=False, preserveTreeState=True )
			globalData.gui.discTab.isoFileTree.item( stageObj.isoPath, tags='changed' )

		# Update the Disc Details Tab
		detailsTab = globalData.gui.discDetailsTab
		if detailsTab:
			detailsTab.isoFileCountText.set( "{:,}".format(len(globalData.disc.files)) )
			#detailsTab # todo: disc size as well

		# Simulate clicking on the same stage variation, to reload its info display
		self.selectedStage = None # Allows the current stage to be reloaded in the GUI
		self.variationsTreeview.event_generate( '<<TreeviewSelect>>' )

		# Prompt the user to choose a new name for this stage slot
		returnCode = self.renameStage( updateProgramStatus=False )

		# Assuming no problems above, update program status with success
		if returnCode == 0:
			globalData.gui.updateProgramStatus( 'Stage added successfully' )

	def getStageFileToAddToDisc( self, newIsoPath ):

		""" Prompts the user for a new file to add to the disc, initilizes it, and adds it to the disc filesystem. 
			Returns the new stage object if successful, or None otherwise. """

		 # No file by this name in the disc; it's probably a random neutral stage slot selected. User probably wants to add a new file to disc
		fileTypeOptions = [ ('Stage files', '*.dat *.usd *.0at *.1at *.2at *.3at *.4at *.5at *.6at *.7at *.8at *.9at *.aat *.bat *.cat *.dat *.eat'),
							('All files', '*.*') ]
		# Need to add a new file to the disc
		newFilePath = importGameFiles( title='Choose a stage file to add to the disc.', fileTypeOptions=fileTypeOptions )
						
		# The above will return an empty string if the user canceled
		if not newFilePath: return None

		# Initialize the new file
		try:
			newFileObj = StageFile( None, -1, -1, newIsoPath, extPath=newFilePath, source='file' )
			newFileObj.getData()
		except Exception as err:
			print( 'Exception during file load; ' + str(err) )
			globalData.gui.updateProgramStatus( 'Unable to load file; ' + str(err), error=True )
			return None

		globalData.disc.addFiles( [newFileObj] )

		return newFileObj

	def allowAddingVariations( self, stageFile, canvas ):

		""" Used to determine whether the 'Add Variation' button should be enabled/disabled. """

		if stageFile.isRandomNeutral():
			if self.variationsTreeview.tag_has( 'fileNotFound' ):
				return True
			else:
				return False
		elif canvas.pageNumber == 1: # Random byte value replacements (mode 0xFF) not supported on first page
			return False
		elif len( self.variationsTreeview.get_children() ) == 4: # For other pages, only up to 4 variations supported
			return False
		else:
			return True

	def addStageVariation( self ):

		""" Called by the main control button. Adds a new stage variation for the currently selected stage slot/icon.
			Will add to the first empty slot (if there is one). """

		# Get the potential isoPaths for this stage slot
		variationIids = self.variationsTreeview.get_children()
		if not variationIids: # Failsafe; not possible?
			msg( 'No variations for this stage are available!' )
			return

		# Look for the first available open slot
		for iid in variationIids:
			isoPath = self.variationsTreeview.item( iid, 'values' )[1]
			stageObj = globalData.disc.files.get( isoPath )
			if not stageObj:
				print( 'Unused isoPath (first unused variation slot): ' + isoPath )
				break

		else: # Loop above didn't break; all slots are filled
			if stageObj.isRandomNeutral():
				msg( 'There are no open random neutral slots for this stage. You will need to import over or delete an existing variation.', 'No open stage slots' )
			else:
				msg( 'There are no open slots for this stage. You will need to import over or delete '
					 'an existing variation. Or modify the stage Swap Details to allow for more variations '
					 '(multiple variations for non-random-neutral stages are only available for pages 2 through 4).', 'No open stage slots' )
			globalData.gui.updateProgramStatus( "No empty slots available", warning=True )

			return

		# Prompt the user to choose a new stage file, and add it to the disc
		newStage = self.getStageFileToAddToDisc( isoPath )

		if newStage:
			# Change selection to the targeted slot (mainly so .rename works) and scroll so it's visible
			self.variationsTreeview.selection_set( iid )
			self.variationsTreeview.see( iid )

			# Update GUI elements across the program, and prompt the user to enter a new stage name
			self.updateGuiForNewlyAddedStage( newStage, (iid,) )

	def renameStage( self, updateProgramStatus=True ):

		""" Prompts the user for a new stage name (description stored in the CSS or yaml file 
			descriptions file), and sets it for the stage currently selected in the Variations treeview. """

		if not self.selectedStage: # Failsafe (the button should be disabled in such a case)
			msg( 'No stage file is selected!' )
			return 0
		elif self.selectedStage.isRandomNeutral():
			charLimit = 31 # Max space in CSS file
		else:
			charLimit = 42 # Somewhat arbitrary limit
		
		# Prompt the user to enter a new name, and validate it
		defaultText = self.selectedStage.longDescription
		newName = getNewNameFromUser( charLimit, None, 'Enter a new stage name:', defaultText )

		if not newName:
			if updateProgramStatus:
				globalData.gui.updateProgramStatus( 'Name update canceled' )
			return 0

		# Save the new name to file (CSS or yaml descriptions file)
		returnCode = self.selectedStage.setDescription( newName )

		if returnCode != 0 and not updateProgramStatus:
			return returnCode

		# Check the return code and update the operation status in the GUI
		if returnCode == 0:
			# Success. Update the new name in the treeview on this tab, as well as in the Disc File Tree
			self.renameTreeviewItem( self.selectedStage.isoPath, newName ) # No error if not currently displayed
			if globalData.gui.discTab:
				globalData.gui.discTab.isoFileTree.item( self.selectedStage.isoPath, values=(newName, 'file'), tags='changed' )

			if updateProgramStatus:
				if self.selectedStage.isRandomNeutral():
					globalData.gui.updateProgramStatus( 'Stage name updated in the CSS file', success=True )
				else:
					globalData.gui.updateProgramStatus( 'Stage name updated in the {}.yaml config file'.format(globalData.disc.gameId), success=True )

		elif returnCode == 1:
			globalData.gui.updateProgramStatus( 'Unable to update stage name in the {}.yaml config file'.format(globalData.disc.gameId), error=True )
		elif returnCode == 2:
			globalData.gui.updateProgramStatus( "Unable to update CSS with stage name; couldn't find the CSS file in the disc", error=True )
		elif returnCode == 3:
			globalData.gui.updateProgramStatus( "Unable to update CSS with stage name; couldn't save the name to the CSS file", error=True )
		else:
			msg( 'An unrecognized return code was given from .setDescription(): ' + str(returnCode) )

		return returnCode

	def renameRsssName( self ):

		""" Prompts the user for a new stage name to display on the Random Stage Select Screen (RSSS). 
			This is then set in both the SdMenu._sd and SdSlChr._sd files. The SdMenu file is used 
			when a player accesses the RSSS from the main menus, while the SdSlChr file is used when 
			a player accesses the RSSS by navigating from the CSS (by clicking on the rules at the top). """

		if not self.selectedStage: # Failsafe (the button should be disabled in such a case)
			msg( 'No stage file is selected!' )
			return 0
			
		# Construct the filename which contains the stage name strings
		if self.stageSwapTable: # Means it's 20XX
			canvas = self.getCurrentCanvas()
			filename = 'SdMenu.{}sd'.format( canvas.pageNumber )
			filename2 = 'SdSlChr.{}sd'.format( canvas.pageNumber )
		else:
			filename = 'SdMenu.usd'
			filename2 = 'SdSlChr.usd'

		# Get the Sd files
		sisFile = globalData.disc.files.get( globalData.disc.gameId + '/' + filename )
		sisFile2 = globalData.disc.files.get( globalData.disc.gameId + '/' + filename2 )
		
		# Prompt the user to enter a new name, and validate it
		currentName = sisFile.getStageMenuName( self.selectedStageSlotId )
		newName = getNewNameFromUser( 24, None, 'Enter a new RSSS stage name:', currentName, isMenuText=True ) # 28 = char limit; 0x38 bytes / 2

		if not newName:
			globalData.gui.updateProgramStatus( 'Name update canceled' )
			return 0

		# Save the new name to file
		if newName != currentName:
			sisFile.setStageMenuName( self.selectedStageSlotId, newName )
			sisFile2.setStageMenuName( self.selectedStageSlotId, newName )
			self.updateBasicInfo( self.selectedStage )
			globalData.gui.updateProgramStatus( 'Stage name updated in {} and {}'.format(filename, filename2), success=True )

	def renameTreeviewItem( self, targetIsoPath, newName ):

		""" Renames an item in the Variations treeview with the given name. 
			Should fail silently if the given isoPath isn't found. """

		iidFound = False # Track duplicates that may arise

		for iid in self.variationsTreeview.get_children():
			isoPath = self.variationsTreeview.item( iid, 'values' )[1]

			if isoPath == targetIsoPath:
				if iidFound:
					self.variationsTreeview.item( iid, text=newName + ' (duplicate)' )
				else:
					self.variationsTreeview.item( iid, text=newName )
					iidFound = True

	def deleteStage( self ):
		
		# if not self.selectedStage: # Failsafe (the button should be disabled in such a case)
		# 	msg( 'No stage file is selected!' )
		# 	return
		
		# Check for a selected item in the Variations treeview
		iidSelectionsTuple = self.variationsTreeview.selection()
		if len( iidSelectionsTuple ) != 1: # Failsafe; shouldn't be possible?
			return None
		iid = iidSelectionsTuple[0]

		# Get the selected file object from the disc
		isoPath = self.variationsTreeview.item( iid, 'values' )[1] # Values tuple is (filename, isoPath)
		stageObj = globalData.disc.files.get( isoPath )
		
		if stageObj:
			# Remove the file from the disc
			globalData.disc.removeFiles( [stageObj] )

			# Update random neutral stage name in MnSlChr
			if stageObj.isRandomNeutral():
				stageObj.setDescription( 'Custom {}'.format(stageObj.randomNeutralId) )

			# Update the GUI
			self.stageVariationUnselected()
			self.variationsTreeview.item( iid, text='- No File -', tags='fileNotFound' )
			globalData.gui.updateProgramStatus( '{} removed from the disc'.format(stageObj.filename) )

			# Update the Disc File Tree Tab
			discTab = globalData.gui.discTab
			if discTab:
				discTab.isoFileTree.delete( stageObj.isoPath )
			
			# Update the Disc Details Tab
			detailsTab = globalData.gui.discDetailsTab
			if detailsTab:
				detailsTab.isoFileCountText.set( "{:,}".format(len(globalData.disc.files)) )
				#detailsTab # todo: disc size as well

	def updateSongBehavior( self ):

		""" Called from the popup Edit button. """

		origText = self.songBehaviorLabel['text']
		initialValue = int( origText.split('|')[0] )

		# Prompt with a set of radio buttons to choose a new behavior. Blocks until the window is closed
		chooserWindow = MusicBehaviorEditor( initialValue )
		newValue = chooserWindow.selectedBehavior.get()

		# Return if no change was made
		if newValue == initialValue:
			return

		# Get the index of the currently selected table entry
		entryIndex = self.getMusicTableEntryIndex()

		# Create a string to describe this change
		origBehaviorName = origText.split( '|' )[1].strip()
		newBehaviorName = self.musicTableStruct.enums['Song_Behavior'].get( newValue )
		userMessage = 'Music Behavior of Music Table entry {} updated from {} to {}.'.format(entryIndex+1, origBehaviorName, newBehaviorName)

		# Update the value in the file and structure
		self.selectedStage.updateStructValue( self.musicTableStruct, 5, newValue, userMessage, 'Song behavior updated', entryIndex=entryIndex )

		# Update the GUI
		psuedoEntryName = 'Entry {}|'.format( entryIndex + 1 ) # Don't need to feed it the whole selection name, just the entry index
		self.selectMusicTableEntry( psuedoEntryName ) # Repopulates the Music Table interface.
		globalData.gui.updateProgramStatus( userMessage )
	
	def updateAltMusicChance( self, newValue ):

		""" Called from the hovering entry widget; newValue should already be validated. """

		# Get the index of the currently selected table entry
		entryIndex = self.getMusicTableEntryIndex()

		# Create a string to describe this change
		origValue = self.altMusicChanceLabel['text']
		formattedNewValue = '{}%'.format( newValue )
		userMessage = 'Alt. Music % Chance of Music Table entry {} updated from {} to {}.'.format(entryIndex+1, origValue, formattedNewValue)

		# Update the value in the file and structure
		self.selectedStage.updateStructValue( self.musicTableStruct, 6, newValue, userMessage, 'Alt music % chance updated', entryIndex=entryIndex )

		# Update the GUI
		globalData.gui.updateProgramStatus( userMessage )
		self.altMusicChanceLabel['text'] = formattedNewValue

	def testStage( self ):

		""" Initialize a Micro Melee build, add the selected stage to it 
			(and necessary codes), and boot it up in Dolphin. """

		if not self.selectedStage:
			msg( 'No stage file is selected!' )
			return

		# Get the micro melee disc object
		microMelee = globalData.getMicroMelee()
		if not microMelee: return # User may have canceled the vanilla melee disc prompt

		microMelee.testStage( self.selectedStage )

	def editSwapDetails( self ):

		""" Prompt the user with a simple GUI to modify values in the 20XX Stage Engine system, 
			to determine what file(s) a specific SSS icon may load. This is called from the 'Edit' 
			button in the Stage Swap details box, so it should only be possible when a stage is 
			selected and the button is enabled. """

		# Determine the currently selected SSS tab and canvas, and create a Stage Swap Editor gui instance
		canvas = self.getCurrentCanvas()
		StageSwapEditor( self, self.selectedStageSlotId, canvas )


class StageSwapEditor( BasicWindow ):

	""" GUI for modifying 20XX's Stage Swap Table in the DOL. """

	illegalChars = ( '\t', '\n', '-', '\\', '/', ':', '*', '?', '<', '>', '|', ' ', ';', '"' ) # For byte replacements or within stage file names

	def __init__( self, stageManagerTab, internalStageId, canvas ):

		# Initialize the basic window
		stageName = globalData.internalStageIds.get( internalStageId, 'Unknown' )
		BasicWindow.__init__( self, globalData.gui.root, "    Stage Swap Editor - {}, {}".format(canvas.pageName, stageName), unique=True )

		self.stageManagerTab = stageManagerTab
		self.wrapLen = 500 # Wrap length for long text strings
		self.internalStageId = internalStageId
		self.canvas = canvas
		notesForeground = '#444454'

		# Get the current values for this SSS and stage
		newExtStageId, stageFlags, byteReplacePointer, byteReplacement, randomByteValues = self.stageManagerTab.stageSwapTable.getEntryInfo( internalStageId, canvas.pageNumber )
		#newIntStageId = self.stageManagerTab.dol.getIntStageIdFromExt( newExtStageId )
		newStageName = globalData.externalStageIds.get( newExtStageId, 'Unknown' )
		self.newExtStageId = newExtStageId

		# Display the original stage info (internal stage ID and name)
		self.mainFrame = ttk.Frame( self.window )
		ttk.Label( self.mainFrame, text='Original Icon Slot - Stage Name / Internal ID:' ).grid( column=0, row=0, padx=6, pady=4 )
		ttk.Label( self.mainFrame, text='{} / 0x{:X}'.format(stageName, internalStageId) ).grid( column=1, row=0, padx=6, pady=4 )

		# Display the NEW stage info (internal stage ID and name), and a dropdown to change it
		ttk.Label( self.mainFrame, text='New - Stage Name / Internal ID / External ID:' ).grid( column=0, row=1, padx=6, pady=4 )

		# Get the Internal Stage ID of the stage to be loaded
		if newExtStageId == 0: # No change; this will be the currently selected stage slot
			newIntStageId = internalStageId
		else:
			newIntStageId = self.stageManagerTab.dol.getIntStageIdFromExt( newExtStageId )
			if newIntStageId == 0x16: # i.e. external stage ID 0x1A, Icicle Mountain (anticipating no hacked stages of this); switch to current Target Test stage
				print( 'Unsupported; target test stage filename undetermined' )
				return -1, ()

		if newExtStageId == 0:
			defaultOption = 'N/A (No swap)'
		else:
			defaultOption = '{} / 0x{:X} / 0x{:X}'.format( newStageName, newIntStageId, newExtStageId )
		self.extStageChoice = Tk.StringVar( value=defaultOption )
		ttk.Label( self.mainFrame, textvariable=self.extStageChoice ).grid( column=0, row=2, padx=6, pady=4 )
		ttk.Button( self.mainFrame, text='Change Stage to Load', command=self.chooseNewExtStageId ).grid( column=1, row=1, padx=6, pady=4, ipadx=7 )
		ttk.Button( self.mainFrame, text='Reset (No Stage Change)', command=lambda: self.updateWithNewExtStageId(0) ).grid( column=1, row=2, padx=6, pady=4, ipadx=7 )

		# Get the original stage file name for this stage slot from the DOL, and check other files that may be loaded by this slot
		dolFilenameOffset, _ = self.stageManagerTab.stageSwapTable.determineStageFiles( newIntStageId, canvas.pageNumber, byteReplacePointer, byteReplacement, randomByteValues )
		self.dolStageFilename = dolStageFilename = self.stageManagerTab.dol.data[dolFilenameOffset:dolFilenameOffset+10].split( '\x00' )[0].decode( 'ascii' )
		
		# Add .dat/.usd file extensions if needed; check country code to determine which to use
		if '.' in dolStageFilename:
			ext = ''
		else:
			if globalData.disc.countryCode == 1: # Banner file encoding = latin_1
				ext = '.usd'
			else: # Banner file encoding = shift_jis
				ext = '.dat'
			dolStageFilename += ext

		ttk.Label( self.mainFrame, foreground=notesForeground, text=("The stage to load above should be the 'base stage' of the "
									"stage you wish to load, i.e. the stage it was designed to go over or which it was based on.\n\n"
									"Each icon on the Stage Select Screen normally corresponds to a specific file name string in the "
									"game executable (the DOL) to become part of a disc file path. That string and its location "
									"are shown below."), wraplength=self.wrapLen ).grid( column=0, columnspan=2, row=3, padx=6, pady=4 )

		ttk.Label( self.mainFrame, text='Original DOL Filename to be Loaded:' ).grid( column=0, row=4, padx=6, pady=4 )
		self.stageToLoadVar = Tk.StringVar( value=dolStageFilename )
		ttk.Label( self.mainFrame, textvariable=self.stageToLoadVar ).grid( column=1, row=4, padx=6, pady=4 )

		ttk.Label( self.mainFrame, text='Filename Location (RAM Address | DOL Offset):' ).grid( column=0, row=5, padx=6, pady=4 )
		self.filenameRamAddress = self.stageManagerTab.dol.offsetInRAM( dolFilenameOffset )
		self.stageToLoadLocationVar = Tk.StringVar( value='0x{:X} | 0x{:X}'.format(self.filenameRamAddress, dolFilenameOffset) )
		ttk.Label( self.mainFrame, textvariable=self.stageToLoadLocationVar ).grid( column=1, row=5, padx=6, pady=4 )
		self.mainFrame.pack()

		self.nameEntryFrame = ttk.Frame( self.window )

		ttk.Label( self.nameEntryFrame, foreground=notesForeground, text=("20XX's Stage Engine code may modify the above filename and load a "
									'different stage by changing a single character at a particular address. That new filename will then be '
									'loaded instead. To configure this feature, replace a single character in the filename below with a single '
									'underscore ("_"). Or, change the character back to the original (as seen above) to disable this feature.'), wraplength=self.wrapLen ).grid( column=0, columnspan=2, row=0, padx=6, pady=4 )

		# Create a text entry field for modifing the filename string
		validationCommand = globalData.gui.root.register( self.nameEntryModified )
		self.nameModEntry = ttk.Entry( self.nameEntryFrame, width=10, justify='center', validate='key', validatecommand=(validationCommand, '%s', '%P') )
		self.nameModEntry.grid( column=0, row=1, padx=6, pady=4, sticky='e' )
		self.nameModEntryExt = Tk.StringVar()
		ttk.Label( self.nameEntryFrame, textvariable=self.nameModEntryExt ).grid( column=1, row=1, padx=6, pady=4, sticky='w' ) # Displays file extension
		self.setNameEntryFrame( byteReplacePointer, ext )
		self.nameEntryFrame.pack()

		# Add prompt to use a random byte value
		self.useRandoByteValuesFrame = ttk.Frame( self.window )
		self.useRandomByteValue = Tk.BooleanVar()
		self.useRandoByteValuesFrame.pack()

		# Add widgets for the byte value replacement(s)
		self.byteValuesFrame = ttk.Frame( self.window )
		self.populateByteValuesFrame( byteReplacePointer, byteReplacement, randomByteValues )
		self.byteValuesFrame.pack()

		# Add Stage Flags
		stageFlagsFrame = ttk.Frame( self.window )
		ttk.Label( stageFlagsFrame, text='Stage Flags:' ).pack( side='left' )
		self.stageFlagsEntry = ttk.Entry( stageFlagsFrame, width=6, justify='center' )
		self.stageFlagsEntry.insert( 'end', '0x'+hex(stageFlags)[2:].upper() )
		self.stageFlagsEntry.pack( side='left', padx=6 )
		helpBtn = ttk.Label( stageFlagsFrame, text='?', foreground='#445', cursor='hand2' )
		helpBtn.pack( side='left', padx=10 )
		helpBtn.bind( '<1>', self.showStageFlagsHelp )
		stageFlagsFrame.pack( pady=(4, 10) )

		buttonFrame = ttk.Frame( self.window )
		ttk.Button( buttonFrame, text='Submit Changes', command=self.submitChanges ).grid( column=0, row=0, padx=6, ipadx=10 )
		ttk.Button( buttonFrame, text='Cancel', command=self.close ).grid( column=1, row=0, padx=6 )
		buttonFrame.pack( pady=(4, 6) )

	def setNameEntryFrame( self, byteReplacePointer, ext ):

		""" Sets the stage file name displayed in the name modification entry widget (e.g. GrNBa.0at or GrNBa._at). """

		# Remove any text that might be in the widget
		self.nameModEntry.delete( 0, 'end' )

		if byteReplacePointer == 0:
			underscoreIndex = -1
			modifiedFileName = self.dolStageFilename
		else:
			underscoreIndex = byteReplacePointer - self.filenameRamAddress
			modifiedFileName = self.dolStageFilename[:underscoreIndex] + '_' + self.dolStageFilename[underscoreIndex+1:]

		# Insert the new name and update the file extension display
		self.nameModEntry.insert( 'end', modifiedFileName )
		self.nameModEntryExt.set( ext )

	def populateByteValuesFrame( self, byteReplacePointer, byteReplacement, randomByteValues ):

		""" Populates widgets for the 'Use Random Byte Value' radio buttons, and text entry widgets 
			for entering random byte/character changes in the filename string (including buttons to 
			add or remove random bytes/characters). """

		# Clear the associated frames to create new widgets
		for widget in self.useRandoByteValuesFrame.winfo_children() + self.byteValuesFrame.winfo_children():
			widget.destroy()
		
		# Don't add any byte replacement widgets/options if the feature isn't turned on
		if byteReplacePointer == 0:
			return

		ttk.Label( self.useRandoByteValuesFrame, text='Use Random Byte Value:' ).grid( column=0, row=0, padx=6, pady=4 )
		ttk.Radiobutton( self.useRandoByteValuesFrame, text='Yes', variable=self.useRandomByteValue, value=True, command=self.useRandoByteToggled ).grid( column=1, row=0, padx=6, pady=4 )
		ttk.Radiobutton( self.useRandoByteValuesFrame, text='No', variable=self.useRandomByteValue, value=False, command=self.useRandoByteToggled ).grid( column=2, row=0, padx=6, pady=4 )

		self.useRandomByteValue.set( False )

		# Add a label explaining the upcoming byte entry widgets
		if self.canvas.pageNumber == 1:
			for widget in self.useRandoByteValuesFrame.winfo_children():
				widget['state'] = 'disabled'
			ttk.Label( self.byteValuesFrame, text='Random Byte Values cannot be used on the first Stage Select Screen.\n'
												'The character omitted above will be changed as follows:', wraplength=self.wrapLen ).grid( column=0, columnspan=6, row=0, padx=6, pady=4 )
		elif byteReplacement == 0xFF:
			self.useRandomByteValue.set( True )
			ttk.Label( self.byteValuesFrame, text='The character omitted above will be randomly changed as follows:' ).grid( column=0, columnspan=6, row=0, padx=6, pady=4 )
		else:
			ttk.Label( self.byteValuesFrame, text='The character omitted above will be changed as follows:' ).grid( column=0, columnspan=6, row=0, padx=6, pady=4 )

		entryValidation = globalData.gui.root.register( self.byteEntryUpdated )
		
		# Determine where the underscore should be
		underscoreIndex = byteReplacePointer - self.filenameRamAddress

		# Add the byte entry widgets
		if byteReplacement == 0xFF:
			# Determine whether to add remove buttons, based on the number of non-0 values
			addRemoveButtons = ( randomByteValues.count(0) < 3 )

			# There may be up to 4 random byte values; add them in a 2x2 grid
			x, y = 0, 1
			for value in randomByteValues:
				if value == 0:
					btn = ttk.Button( self.byteValuesFrame, text='+', width=5, command=self.addRandomByteValue )
					btn.grid( column=x, row=y, columnspan=3, padx=6, pady=4 )
					ToolTip( btn, text='Add random byte' )
					break
				char = chr( value )
				entry = Tk.Entry( self.byteValuesFrame, width=3, justify='center', highlightbackground='#b7becc', borderwidth=1, 
									relief='flat', highlightthickness=1, validate='key', validatecommand=(entryValidation, '%P', '%W') )
				entry.insert( 'end', char )
				entry.grid( column=x, row=y, padx=8, pady=4, sticky='e' )
				x += 1
				moddedStageName = self.dolStageFilename[:underscoreIndex] + char + self.dolStageFilename[underscoreIndex+1:]
				ttk.Label( self.byteValuesFrame, text=' -> {}'.format(moddedStageName) ).grid( column=x, row=y, padx=0, pady=4 )
				x += 1

				if addRemoveButtons:
					#btn = ttk.Button( self.byteValuesFrame, text='-', width=3, command=self.removeRandomByteValue, style='red.TButton' )
					btn = ttk.Button( self.byteValuesFrame, text='-', width=3, style='red.TButton' )
					btn.bind( '<1>', self.removeRandomByteValue )
					btn.grid( column=x, row=y, padx=8, pady=4, sticky='w' )
					ToolTip( btn, text='Remove this random byte' )
					x += 1

				# Switch to the next row after the second set of widgets (for the second random byte value) is added
				if x == 6:
					x = 0
					y = 2
		else:
			char = chr( byteReplacement )
			entry = Tk.Entry( self.byteValuesFrame, width=3, justify='center', highlightbackground='#b7becc', borderwidth=1, 
									relief='flat', highlightthickness=1, validate='key', validatecommand=(entryValidation, '%P', '%W') )
			entry.insert( 'end', char )
			entry.grid( column=0, row=1, padx=6, pady=4, sticky='e' )
			moddedStageName = self.dolStageFilename[:underscoreIndex] + char + self.dolStageFilename[underscoreIndex+1:]
			ttk.Label( self.byteValuesFrame, text=' -> {}'.format(moddedStageName) ).grid( column=1, row=1, padx=6, pady=4, sticky='w' )

	def useRandoByteToggled( self ):

		""" Repopulates the GUI input for the byte replacement value and random byte replacement values. """

		byteReplacePointer = self.getByteReplacePointer()
		byteReplacement, randomByteValues = self.getByteReplacementValues()

		# Repopulate the frames containing the random byte values
		if self.useRandomByteValue.get():
			# If newly toggling to True, add a random byte value to ensure there are at least two
			self.addRandomByteValue()
		else:
			self.populateByteValuesFrame( byteReplacePointer, byteReplacement, randomByteValues )

	def getByteReplacePointer( self, nameModEntryText='' ):
		# Get the offset of the byte to be replaced, relative to the start of the filename in the DOL
		if not nameModEntryText:
			nameModEntryText = self.nameModEntry.get()
		relNameOffset = nameModEntryText.find( '_' )

		if relNameOffset == -1:
			return 0
		else:
			return self.filenameRamAddress + relNameOffset

	def getByteReplacementValues( self ):

		""" Returns the byte replacement value, and a tuple of random byte replacements (which will be four zeros if not used). """

		usingRandomByteValue = self.useRandomByteValue.get()
		values = []

		for widget in self.byteValuesFrame.winfo_children():
			if widget.winfo_class() == 'Entry':
				widgetContents = widget.get()
				try:
					stringValue = widgetContents[0] # Will raise an error if no character is present
					stringValue.encode( 'ascii' ) # Will raise an error if not an ASCII character
					intValue = ord( stringValue )
					if not usingRandomByteValue:
						return intValue, (0, 0, 0, 0)
					values.append( intValue )
				except Exception as err:
					print( 'getByteReplacementValues() was unable to convert character to value: {}; {}'.format(widgetContents, err) )

		# Ensure there are 4 values
		zeroesToAdd = 4 - len( values )
		values.extend( [0] * zeroesToAdd )

		if usingRandomByteValue:
			return 0xFF, tuple( values )

		else: # No value was found above. Determine a default value from the original file name
			modifiedName = self.nameModEntry.get()
			relNameOffset = modifiedName.find( '_' )

			# Default to the value for the character '0' if no underscore is found
			if relNameOffset == -1:
				return 0x30, tuple( values )
			else:
				return ord( self.dolStageFilename[relNameOffset] ), tuple( values )

	def addRandomByteValue( self ):

		""" Called by one of the 'Add' buttons in the random byte values frame, to add a 
			new value. Repopulates the frame with a new 0x30 value included. """

		byteReplacePointer = self.getByteReplacePointer()
		byteReplacement, randomByteValues = self.getByteReplacementValues()

		newValues = []
		newValueAdded = False
		for value in randomByteValues:
			if value == 0 and not newValueAdded:
				newValues.append( 0x30 ) # Adding an arbitrary value for a default (must be non-0); 0x30 = ascii character '0'
				newValueAdded = True
			else:
				newValues.append( value )
		
		self.populateByteValuesFrame( byteReplacePointer, byteReplacement, newValues )

	def removeRandomByteValue( self, event ):

		""" Called by one of the 'Remove' buttons in the random byte values frame, to remove that value. 
			Repopulates the frame without the value from the associated entry widget. """

		values = []
		lastValue = -1
		
		for widget in self.byteValuesFrame.winfo_children():
			widgetClass = widget.winfo_class()
			if widgetClass == 'Entry':
				widgetContents = widget.get()
				try:
					stringValue = widgetContents[0] # Will raise an error if no character is present
					stringValue.encode( 'ascii' ) # Will raise an error if not an ASCII character
					lastValue = ord( stringValue )
				except Exception as err:
					print( 'removeRandomByteValue() was unable to convert character to value: {}; {}'.format(widgetContents, err) )
			elif widgetClass == 'TButton' and lastValue != -1:
				# Ignore this value if this was the 'Remove' button that was clicked
				if widget != event.widget:
					values.append( lastValue )
				lastValue = -1

		# if lastValue != -1:
		# 	values.append( lastValue )

		# Ensure there are 4 values
		zeroesToAdd = 4 - len( values )
		values.extend( [0] * zeroesToAdd )

		# Repopulate the random byte values frame with the above collected values
		byteReplacePointer = self.getByteReplacePointer()
		self.populateByteValuesFrame( byteReplacePointer, 0xFF, values )

	def nameEntryModified( self, oldString, newString ):

		""" Validates text input into the filename entry/modification field, whether entered by the user 
			or programmatically. Makes sure there are no illegal characters, that the entered text is 
			ASCII, and rebuilds part of the GUI if an underscore was added or removed."""

		# Do nothing if there's incomplete input (the program may be trying to write to the field)
		if not oldString or not newString:
			return True

		try:
			# Check for illegal characters
			for char in newString:
				if char in self.illegalChars:
					raise Exception( 'Illegal character detected' )

			# Make sure the string is purely ASCII
			newString.encode( 'ascii' )
		except:
			return False

		# Validation passed; check for an underscore in the new and old strings
		oldUnderscoreIndex = oldString.find( '_' )
		newUnderscoreIndex = newString.find( '_' )
		oldUnderscoreFound = ( oldUnderscoreIndex != -1 )
		newUnderscoreFound = ( newUnderscoreIndex != -1 )

		# Rebuild the Byte Replacement frames with new widgets if the underscore was just added, removed, or moved
		if oldUnderscoreFound and not newUnderscoreFound: # The underscore was newly removed
			# Clear the associated frames to create new widgets
			for widget in self.useRandoByteValuesFrame.winfo_children() + self.byteValuesFrame.winfo_children():
				widget.destroy()
		elif newUnderscoreFound and not oldUnderscoreFound or oldUnderscoreIndex != newUnderscoreIndex: # The underscore was newly added or moved
			# Determine default values for the following, and rebuild the lower portion of the GUI with them included
			byteReplacePointer = self.getByteReplacePointer( newString )
			byteReplacement, randomByteValues = self.getByteReplacementValues()
			
			self.populateByteValuesFrame( byteReplacePointer, byteReplacement, randomByteValues )

		return True

	def byteEntryUpdated( self, newString, widgetName ):

		""" Validates text input into the byte replacement field(s), whether entered by the user or programmatically. 
			Makes sure there are no illegal characters, that the entered text is as most 1 character long, and is ASCII. 
			Also updates text widgets that may be present and paired with the entry (which may not be present during 
			initial creation of the GUI. """

		if not newString: return True
		elif len( newString ) > 1: return False

		# Check that the character can be encoded
		try:
			char = newString[0]
			char.encode( 'ascii' ) # Will raise an error if not an ASCII character
			value = ord( char )
			if char in self.illegalChars:
				raise Exception( 'Illegal character for stage name string.' )
			failedEncoding = False
		except Exception as err:
			print( 'Unable to convert character to value: {}; {}'.format(newString[0], err) )
			failedEncoding = True
		
		# Look for a label widget paired with this entry, and update it if found
		labelIsNext = False
		for widget in self.byteValuesFrame.winfo_children():
			if labelIsNext: # Update the label's filename text
				moddedStageName = self.nameModEntry.get().replace( '_', newString[0] )
				widget['text'] = ' -> {}'.format( moddedStageName )
				break
			elif widget == globalData.gui.root.nametowidget( widgetName ):
				if failedEncoding:
					widget['highlightcolor'] = '#f05555'
					widget['highlightbackground'] = '#f05555'
					break
				else:
					widget['highlightcolor'] = '#0099f0'
					widget['highlightbackground'] = '#b7becc'
				labelIsNext = True
		
		return True

	def chooseNewExtStageId( self ):

		""" Prompts the user to choose a new stage for this icon slot to swap to. Called by the "Change" button in the GUI. """

		selectionWindow = ExternalStageIdChooser()

		if selectionWindow.stageId == -1: # User canceled
			return

		self.updateWithNewExtStageId( selectionWindow.stageId )

	def updateWithNewExtStageId( self, extStageId ):

		""" Updates the GUI with a new external stage ID, setting all labels and entry fields with new default values. """

		# Get the Internal Stage ID of the stage to be loaded
		if extStageId == 0: # No change; this will be the currently selected stage slot
			newIntStageId = self.internalStageId
			descriptiveText = 'N/A (No swap)'
		else:
			newIntStageId = self.stageManagerTab.dol.getIntStageIdFromExt( extStageId )
			if newIntStageId == 0x16: # i.e. external stage ID 0x1A, Icicle Mountain (anticipating no hacked stages of this); switch to current Target Test stage
				print( 'Unsupported; target test stage filename undetermined' )
				return
			
			newStageName = globalData.externalStageIds.get( extStageId, 'Unknown' )
			descriptiveText = '{} / 0x{:X} / 0x{:X}'.format( newStageName, newIntStageId, extStageId )

		# Update the text displaying the new stage to load
		self.newExtStageId = extStageId
		self.extStageChoice.set( descriptiveText )

		# Set up some default values to refresh the GUI with
		byteReplacePointer = 0
		byteReplacement = 0
		randomByteValues = ( 0, 0, 0, 0 )

		# Update the original (DOL) stage name and offset (and internal ram address)
		dolFilenameOffset, _ = self.stageManagerTab.stageSwapTable.determineStageFiles( newIntStageId, self.canvas.pageNumber, byteReplacePointer, byteReplacement, randomByteValues )
		self.dolStageFilename = self.stageManagerTab.dol.data[dolFilenameOffset:dolFilenameOffset+10].split( '\x00' )[0].decode( 'ascii' )
		displayedStageFilename = self.dolStageFilename
		if '.' in displayedStageFilename:
			ext = ''
		else:
			if globalData.disc.countryCode == 1: # Banner file encoding = latin_1
				ext = '.usd'
			else: # Banner file encoding = shift_jis
				ext = '.dat'
			displayedStageFilename += ext
		self.stageToLoadVar.set( displayedStageFilename )
		
		# Update the internal RAM address and displayed address/offset
		self.filenameRamAddress = self.stageManagerTab.dol.offsetInRAM( dolFilenameOffset )
		self.stageToLoadLocationVar.set( '0x{:X} | 0x{:X}'.format(self.filenameRamAddress, dolFilenameOffset) )

		# Update widgets for the stage name/underscore entry, and byte value changes
		self.setNameEntryFrame( byteReplacePointer, ext )
		self.populateByteValuesFrame( byteReplacePointer, byteReplacement, randomByteValues )

	def submitChanges( self ):

		""" Confirms the choices currently set in the GUI, saves them to the DOL, and closes this window. """

		# Get the new external stage ID
		stageFlags = self.stageFlagsEntry.get().strip()
		try:
			stageFlags = int( stageFlags, 16 )
		except:
			msg( 'Unable to convert the given stage flags.', 'Invalid input' )
			return

		# Collect values from the GUI
		byteReplacePointer = self.getByteReplacePointer()
		byteReplacement, randomByteValues = self.getByteReplacementValues()

		# Update the DOL with the data collected by this window, and then close it
		stageName = globalData.internalStageIds.get( self.internalStageId, 'Unknown' )
		self.stageManagerTab.stageSwapTable.setEntryInfo( self.internalStageId, self.canvas.pageNumber, self.newExtStageId, stageFlags, byteReplacePointer, byteReplacement, randomByteValues )
		globalData.gui.updateProgramStatus( 'Stage Swap Table updated for SSS page {}, for the {} icon slot'.format(self.canvas.pageNumber, stageName) )
		self.close()

		# If this window is for the currently selected stage, force a re-select of this stage, to repopulate the GUI with updated information
		if self.stageManagerTab.selectedStageSlotId == self.internalStageId:
			self.stageManagerTab.selectStage( self.canvas )

	def showStageFlagsHelp( self, event ):
		msg( 'Stage flags are an advanced feature, useful for those wanting to write ASM codes for stage mods. '
			 'The byte defined here will be stored at 0x803FA2E5 upon stage selection, which you can then load in your '
			 'code during match initialization.\n\nFor example, say you made one page contain two N64 Dream Lands; you '
			 "could set one to have a stage flag of 0x10 which could mean it doesn't have wind. You would then write "
			 'the ASM code, executed while playing on Dream Land, to check the stage flag value while performing the wind '
			 'logic. This gives a lot of flexibility and power.\n\nDo not use the first three bits of this byte, which '
			 "are used for the custom spawn points code. You may set the value to 0 if you don't intend to use it.", 'Stage Flags Help', self.window )


class ExternalStageIdChooser( BasicWindow ):

	""" Prompts the user with several categorized drop-down lists for selecting a stage.
		This references external stage ID, which will be stored to "self.stageId". 
		This window will block the main interface until a selection is made. """

	def __init__( self ):

		BasicWindow.__init__( self, globalData.gui.root, 'Select a Stage', offsets=(300, 300) )
		self.emptySelection = '---'
		self.stageId = -1

		# Separate the external stage ID dictionary into more manageable chunks
		idList = globalData.externalStageIds.items() # Creates a list of key/value pairs, which will be (externalStageId, stageName)
		self.stageLists = [
			( 'Standard Stages', [ item for item in idList if item[0] >= 0 and item[0] <= 0x20 ] ),
			( 'Target Test Stages', [ item for item in idList if item[0] > 0x20 and item[0] <= 0x3A ] ),
			( 'Adventure Mode', [ item for item in idList if item[0] > 0x3A and item[0] <= 0x51 ] ),
			( 'Classic Mode (VS One)', [ item for item in idList if item[0] > 0x55 and item[0] <= 0x7C ] ),
			( 'Classic Mode (VS Two)', [ item for item in idList if item[0] > 0x7C and item[0] <= 0x9A ] ),
			( 'Classic Mode (Other)', [ item for item in idList if item[0] > 0x9A and item[0] <= 0xB0 ] ),
			( 'All-Star', [ item for item in idList if item[0] > 0xB0 and item[0] <= 0xC9 ] ),
			( 'Event Match', [ item for item in idList if item[0] > 0xC9 and item[0] <= 0x110 ] ),
			( 'Other', [ item for item in idList if item[0] > 0x110 ] )
		]
		self.stageLists[0][1][0] = ( 0, 'N/A' )

		mainFrame = ttk.Frame( self.window )
		ttk.Label( mainFrame, text='Stage Name / External Stage ID:' ).grid( column=1, row=0, padx=6, pady=4 )
		row = 1
		self.listWidgets = []
		for listName, stageList in self.stageLists:
			# Add the list name label
			ttk.Label( mainFrame, text=listName ).grid( column=0, row=row, padx=14, pady=4 )

			# Add the dropdown menu
			options = [ '{} / 0x{:X}'.format(stageName, stageId) if stageId != 0 else 'N/A (No swap) / 0x0' for stageId, stageName in stageList ]
			stageChoice = Tk.StringVar()
			stageIdChooser = ttk.OptionMenu( mainFrame, stageChoice, self.emptySelection, *options, command=self.optionSelected )
			stageIdChooser.grid( column=1, row=row, padx=14, pady=4 )
			stageIdChooser.var = stageChoice
			stageIdChooser.stageList = stageList
			self.listWidgets.append( stageIdChooser )
			row += 1
		mainFrame.pack( pady=(4, 0) )
		
		buttonFrame = ttk.Frame( self.window )
		ttk.Button( buttonFrame, text='Confirm', command=self.close ).grid( column=0, row=0, padx=6 )
		ttk.Button( buttonFrame, text='Cancel', command=self.cancel ).grid( column=1, row=0, padx=6 )
		buttonFrame.pack( pady=(4, 6) )

		# Make this window modal (will not allow the user to interact with main GUI until this is closed)
		self.window.grab_set()
		globalData.gui.root.wait_window( self.window )

	def optionSelected( self, selectedOption ):

		""" Called when the user changes the current selection in any of the
			drop-down lists. Sets the currently selected stage ID, and clears 
			(un-sets) the other drop-down lists. """

		# Get the stage ID by itself
		stageId = selectedOption.split( '/' )[1]
		self.stageId = int( stageId.strip(), 16 )

		# Figure out which list widget this selection is from, and blank out the rest
		for widget in self.listWidgets:
			if self.stageId < widget.stageList[0][0] or self.stageId > widget.stageList[-1][0]:
				widget.var.set( self.emptySelection )

	def cancel( self ):
		self.stageId = -1
		self.close()


class MusicBehaviorEditor( BasicWindow ):

	""" Prompts the user with several options for stage music 
		behavior for the currently selected music table entry. """

	def __init__( self, initialValue ):

		BasicWindow.__init__( self, globalData.gui.root, 'Select a Music Behavior', offsets=(300, 300) )

		self.initialValue = initialValue
		self.selectedBehavior = Tk.IntVar( value=initialValue )

		for index, behavior in MapMusicTable.enums['Song_Behavior'].items():
			# Add the radio button to the GUI
			btn = ttk.Radiobutton( self.window, text=behavior, value=index, variable=self.selectedBehavior )
			btn.grid( column=0, columnspan=2, row=index, sticky='w', pady=3, padx=(25, 15) )

			# Add a tooltip description
			description = MapMusicTable.songBehaviorDescriptions[index]
			ToolTip( btn, text=description, delay=700, wraplength=500 )
		
		#buttonFrame = ttk.Frame( self.window )
		# ttk.Button( self.window, text='Confirm', command=self.close ).grid( column=0, row=index+1, padx=6 )
		# ttk.Button( self.window, text='Cancel', command=self.cancel ).grid( column=1, row=index+1, padx=6 )
		#buttonFrame.pack( pady=(4, 6) )

		# Make this window modal (will not allow the user to interact with main GUI until this is closed)
		self.window.grab_set()
		globalData.gui.root.wait_window( self.window )


class StagePropertyEditor( ttk.Frame ):

	# Define some headers to organize the properties into groups in the UI
	propertyGroups = {
		0x8: 'Default Camera',
		0x4C: 'Pause Camera',
		0x68: 'Fixed Camera',
		0xB8: 'Off-Screen Bubble Colors'
	}

	def __init__( self, parent, stageFile ):
		ttk.Frame.__init__( self, parent )

		stageFile.initialize()
		self.file = stageFile
		self.grGroundParam = stageFile.getStructByLabel( 'grGroundParam' )

		# Add the headlines
		ttk.Label( self, text='Basic Stage Properties  (grGroundParam)' ).grid( column=0, row=0, pady=12 )
		ttk.Label( self, text='Model Groups  (GObjs Array)' ).grid( column=1, columnspan=2, row=0 )
		
		# Collect general properties
		propertyValues = self.grGroundParam.getValues()
		if not propertyValues:
			msg( message='Unable to get stage properties for {}. Most likely there was a problem initializing the file.', 
				 title='Unable to get Struct Values', 
				 parent=globalData.gui,
				 error=True )
			return

		# Create the properties table for Stage Properties
		structTable = VerticalScrolledFrame( self )
		offset = 0
		row = 0
		for name, formatting, value in zip( self.grGroundParam.fields, self.grGroundParam.formatting[1:], propertyValues ):
			propertyName = name.replace( '_', ' ' ).replace( 'Pause ', '' ).replace( 'Fixed Camera ', '' )
			absoluteFieldOffset = self.grGroundParam.offset + offset

			# Skip item stuff for now
			if offset >= 0x68 and offset < 0xB8:
				if formatting == 'H':
					offset += 2
				else:
					offset += 4
				row += 1
				continue

			if not name:
				propertyName = 'Unknown 0x{:X}'.format( offset )
			
			# Add a section header if appropriate
			if offset in self.propertyGroups:
				sectionName = self.propertyGroups[offset]
				ttk.Label( structTable.interior, text=sectionName ).grid( columnspan=3, column=0, row=row, padx=(50, 10), pady=(14, 6) )
				row += 1

			verticalPadding = ( 0, 0 )

			fieldLabel = ttk.Label( structTable.interior, text=propertyName + ':', wraplength=200, justify='center' )
			fieldLabel.grid( column=0, row=row, padx=(25, 10), sticky='e', pady=verticalPadding )
			if formatting == 'I':
				typeName = 'Integer'
			else:
				typeName = 'Float'
			ToolTip( fieldLabel, text='Offset in struct: 0x{:X}\nOffset in file: 0x{:X}\nType: {}'.format(offset, 0x20 + absoluteFieldOffset, typeName), delay=300 )

			# Add an editable field for the raw hex data
			hexEntry = HexEditEntry( structTable.interior, self.file, absoluteFieldOffset, 4, formatting, propertyName, width=11 )
			rawData = self.grGroundParam.data[offset:offset+4]
			hexData = hexlify(rawData).upper()
			hexEntry.insert( 0, hexData )
			hexEntry.grid( column=1, row=row, pady=verticalPadding )

			# Add a value entry or color swatch widget
			if offset >= 0xB8:
				hexEntry.colorSwatchWidget = ColorSwatch( structTable.interior, hexData, hexEntry )
				hexEntry.colorSwatchWidget.grid( column=2, row=row, pady=verticalPadding, padx=(5, 15) )
			else:
				# Add an editable field for this field's actual decoded value (and attach the hex edit widget for later auto-updating)
				valueEntry = HexEditEntry( structTable.interior, self.file, absoluteFieldOffset, 4, formatting, propertyName, valueEntry=True, width=15 )
				valueEntry.set( value )
				valueEntry.hexEntryWidget = hexEntry
				hexEntry.valueEntryWidget = valueEntry
				valueEntry.grid( column=2, row=row, pady=verticalPadding, padx=(5, 15) )

			offset += 4
			row += 1

		structTable.grid( column=0, row=1, rowspan=3, sticky='nsew' )
		structTable.columnconfigure( 'all', weight=1 )
		
		# Model Parts Tree start
		treeWrapper = ttk.Frame( self ) # Contains just the treeview and its scroller
		scrollbar = Tk.Scrollbar( treeWrapper )
		self.modelPartsTree = NeoTreeview( treeWrapper, columns=('offset'), yscrollcommand=scrollbar.set )
		#self.modelPartsTree.heading( '#0', anchor='center', text='Group' ) # , command=lambda: treeview_sort_column(self.modelPartsTree, 'file', False)
		self.modelPartsTree.column( '#0', anchor='center', minwidth=80, stretch=1, width=90 ) # "#0" is implicit in the columns definition above.
		self.modelPartsTree.heading( 'offset', anchor='center', text='Offset' )
		self.modelPartsTree.column( 'offset', anchor='w', minwidth=60, stretch=1, width=60 )
		self.modelPartsTree.tag_configure( 'changed', foreground='red' )
		self.modelPartsTree.tag_configure( 'changesSaved', foreground='#292' ) # The 'save' green color
		self.modelPartsTree.grid( column=0, row=0, sticky='nsew' )
		self.modelPartsTree.bind( '<<TreeviewSelect>>', self.onModelPartSelect )
		self.modelPartsTree.bind( '<Double-1>', self.onModelPartDoubleClick ) # The above should also happen first by default
		scrollbar.config( command=self.modelPartsTree.yview )
		scrollbar.grid( column=1, row=0, sticky='ns' )
		treeWrapper.rowconfigure( 'all', weight=1 )
		treeWrapper.grid( column=1, row=1, rowspan=2, sticky='nsew', padx=15, ipadx=3 )

		# Initialize the map head struct and the GObjs array
		gobjsArray = self.file.getGObjs()

		# Populate the treeview
		for i, entryValues in gobjsArray.iterateEntries():
			# Skip the General Points entry
			#if i == 0: continue

			gobjName = 'Group ' + str( i+1 )
			gobjValues = [ uHex(0x20+entryValues[0]), i ] + list( entryValues )

			self.modelPartsTree.insert( '', 'end', str(entryValues[0]), text=gobjName, values=gobjValues )

		# Set the program status. This may be overridden with any warnings from render engine or shader initialization below
		printStatus( 'Ready' )

		# Model display panel
		self.engine = RenderEngine( self, (440, 300), True, background=globalData.gui.defaultSystemBgColor, borderwidth=0, relief='groove' )
		self.engine.grid( column=2, row=1, sticky='nsew', padx=(0, 15) )
		self.engine.camera.updateFrustum( zNear=10, zFar=3000 )

		# Set a default camera step size (for movement speed) and position
		self.engine.camera.focalDistance = 200
		self.engine.camera.rotationX = 80
		self.engine.camera.updatePosition()
		self.engine.camera.updateOrientation()

		# Model parts controls
		modelPartsControls = ttk.Frame( self )
		self.showBones = Tk.BooleanVar( value=False )
		ttk.Checkbutton( modelPartsControls, text='Bones', variable=self.showBones, command=self.toggleBones ).grid( column=0, row=0, padx=(0, 20) )
		ttk.Button( modelPartsControls, text='View', command=self.viewModel, state='disabled' ).grid( column=1, row=0, padx=2 )
		ttk.Button( modelPartsControls, text='Info', command=self.viewModelInfo ).grid( column=1, row=1, padx=2 )
		ttk.Button( modelPartsControls, text='Import', command=self.importModelGroup, state='disabled' ).grid( column=2, row=0, padx=2 )
		ttk.Button( modelPartsControls, text='Add', command=self.addModelGroup, state='disabled' ).grid( column=2, row=1, padx=2 )
		ttk.Button( modelPartsControls, text='Export', command=self.exportModelGroup, state='disabled' ).grid( column=3, row=0, padx=2 )
		ttk.Button( modelPartsControls, text='Delete', command=self.deleteModelGroup, state='disabled' ).grid( column=3, row=1, padx=2 )
		ttk.Button( modelPartsControls, text='Edit Textures', command=self.editTextures ).grid( column=1, columnspan=3, row=2, padx=2, ipadx=22, pady=(3, 0) )
		modelPartsControls.grid( column=2, row=2, padx=(0, 10), pady=9, ipady=3 )

		# General points controls
		generalPointsFrame = ttk.Labelframe( self, text='  General Points  ' )
		ttk.Button( generalPointsFrame, text='Blastzones', command=self.adjustBlastzones, width=26 ).grid( column=0, row=0, padx=6, pady=3 )
		ttk.Button( generalPointsFrame, text='Camera Limits', command=self.adjustCameraLimits, width=26 ).grid( column=1, row=0, padx=6, pady=3 )
		ttk.Button( generalPointsFrame, text='Player Spawn Points', command=self.adjustPlayerSpawns, width=26 ).grid( column=0, row=1, padx=6, pady=3 )
		ttk.Button( generalPointsFrame, text='Item Spawns', command=self.adjustItemSpawns, width=26 ).grid( column=1, row=1, padx=6, pady=3 )
		targetsButton = ttk.Button( generalPointsFrame, text='Target Positions', command=self.ajustTargetPositions, width=30 )
		targetsButton.grid( column=0, columnspan=2, row=2, ipadx=4, pady=(0, 7) )
		#ttk.Button( generalPointsFrame, text='Add New General Point', command=self.addNewGeneralPoint ).grid( column=0, row=5, ipadx=4 ) #todo
		generalPointsFrame.columnconfigure( 'all', weight=1 )
		generalPointsFrame.rowconfigure( 'all', weight=1 )
		generalPointsFrame.grid( column=1, columnspan=2, row=3, ipadx=25, ipady=8, pady=20 )

		# Disable the Targets button if this isn't a Target Test stage
		if not self.file.filename.startswith( 'GrT' ):
			targetsButton.config( state='disabled' )

		# self.columnconfigure( 0, weight=1 )
		# self.columnconfigure( 1, weight=1 )
		# self.columnconfigure( 2, weight=2 )
		# self.rowconfigure( 0, weight=0 )
		# self.rowconfigure( 1, weight=1 )
		# self.rowconfigure( 2, weight=1 )
		# self.rowconfigure( 3, weight=1 )

		self.columnconfigure( 'all', weight=1 )
		self.columnconfigure( 2, weight=2 )
		self.rowconfigure( 'all', weight=1 )
		self.rowconfigure( 0, weight=0 )

	def onModelPartSelect( self, event ):

		""" Attempts to render each joint currently selected in the render window. """
		
		# Get the current selection
		iidSelectionsTuple = self.modelPartsTree.selection()
		if not iidSelectionsTuple: # Failsafe; not possible?
			return

		# Clear current rendered objects
		self.engine.clearRenderings( False )

		# Check if the first group is selected
		showBones = self.showBones.get()
		if iidSelectionsTuple[0] == self.modelPartsTree.get_children()[0]:
			# Turn on bone rendering if it's disabled (the first group is only bones)
			if not showBones:
				self.showBones.set( True )
				showBones = True

		# Get the selected joint object(s)
		for iid in iidSelectionsTuple:
			joint = self.file.getStruct( int(iid) )
			
			# Check if this is a skeleton root joint
			if joint.flags & 2:
				skeleton = self.engine.loadSkeleton( joint, showBones )
			else:
				skeleton = None # Use rudimentary transforms for joints in renderJoint()

			# tic = time.clock()
			self.engine.renderJoint( joint, showBones=showBones, skeleton=skeleton )
			# toc = time.clock()
			# print( 'Render time: ' + str(toc-tic) )

		self.engine.separateBatches()

	def toggleBones( self ):
		self.engine.showPart( 'bones', self.showBones.get(), 'edge' )

	def viewModel( self ): pass
	def viewModelInfo( self ):

		""" Gets totals for each primitive group and other info on 
			this model part, and reports it to the user. """

		# Get the current selection
		iidSelectionsTuple = self.modelPartsTree.selection()
		if not iidSelectionsTuple: # Failsafe; not possible?
			msg( 'No model parts are selected!', 'Nothing to Report, Captain' )
			return

		primTotals = self.engine.getPrimitiveTotals()

		# Count Joints/DObjs/PObjs
		structTotals = OrderedDict([ ('Joints', 0), ('Display Objects (DObj)', 0), ('Polygon Objects (PObj)', 0) ])
		texturesProcessed = {}
		geomDataProcessed = {}
		for iid in iidSelectionsTuple:
			joint = self.file.getStruct( int(iid) )
			self._countStructs( joint, structTotals, texturesProcessed, geomDataProcessed )

		# Calculate total texture space
		# totalTextureSpace = 0
		# imageDataStruct = globalData.fileStructureClasses['ImageDataBlock']
		# texturesInfo = self.file.identifyTextures()
		# for info in texturesInfo:
		# 	totalTextureSpace += imageDataStruct.getDataLength( *info[4:7] )
		totalTextureSpace = sum( texturesProcessed.values() )
		geoDataSize = sum( geomDataProcessed.values() )

		# Build the string to report to the user
		lines = []
		lines.append( 'Vertex Lists: {}\n'.format(len(self.engine.vertexLists)) )
		for name, (groupCount, totalPrimitives) in primTotals.items():
			lines.append( '{: <16} -  Groups: {: <6}Total: {}'.format(name, groupCount, totalPrimitives) )
		lines.append( '\nObject Counts:' )
		lines.append( '    Joints (JObj):          {}'.format(structTotals['Joints']) )
		lines.append( '    Display Objects (DObj): {}'.format(structTotals['Display Objects (DObj)']) )
		lines.append( '    Polygon Objects (PObj): {}'.format(structTotals['Polygon Objects (PObj)']) )
		lines.append( '\nTotal Geometry Data:  {}  ({:,} bytes)'.format(humansize(geoDataSize), geoDataSize) )
		lines.append( 'Total Texture Data:  {}  ({:,} bytes)'.format(humansize(totalTextureSpace), totalTextureSpace) )

		# Report the above string to the user
		cmsg( '\n'.join(lines), 'Model Groups Info', 'left' )

	def _countStructs( self, struct, structTotals, texturesProcessed, geomDataProcessed ):

		""" Recursively scans the given struct for child/sibling structs to get a total 
			count of each of joints, DOBjs, and PObjs, along with other geometry data. """

		if struct.__class__.__name__ == 'JointObjDesc':
			structTotals['Joints'] += 1

			# Check for a child struct
			child = struct.initChild( 'JointObjDesc', 2 )
			if child:
				self._countStructs( child, structTotals, texturesProcessed, geomDataProcessed )

			# Check for a 'next' (sibling) struct
			next = struct.initChild( 'JointObjDesc', 3 )
			if next:
				self._countStructs( next, structTotals, texturesProcessed, geomDataProcessed )

			# Check for a DObj struct
			dobj = struct.initChild( 'DisplayObjDesc', 4 )
			if dobj:
				self._countStructs( dobj, structTotals, texturesProcessed, geomDataProcessed )

		elif struct.__class__.__name__ == 'DisplayObjDesc':
			structTotals['Display Objects (DObj)'] += 1

			# Check for a 'next' (sibling) struct
			next = struct.initChild( 'DisplayObjDesc', 1 )
			if next:
				self._countStructs( next, structTotals, texturesProcessed, geomDataProcessed )

			# Check for a texture
			try:
				mobj = struct.initChild( 'MaterialObjDesc', 2 )
				tobj = mobj.initChild( 'TextureObjDesc', 2 )
				imgHeader = tobj.initChild( 'ImageObjDesc', 21 )
				imgData = imgHeader.initChild( 'ImageDataBlock', 0 )

				# Remember the size of this texture if it's unique
				if imgData.offset not in texturesProcessed:
					width, height, imageType = imgHeader.getValues()[1:4]
					texturesProcessed[imgData.offset] = imgData.getDataLength( width, height, imageType )
			except Exception as err:
				pass

			# Check for a PObj struct
			pobj = struct.initChild( 'PolygonObjDesc', 3 )
			if pobj:
				self._countStructs( pobj, structTotals, texturesProcessed, geomDataProcessed )

		elif struct.__class__.__name__ == 'PolygonObjDesc':
			structTotals['Polygon Objects (PObj)'] += 1

			vAttrArray = struct.initChild( 'VertexAttributesArray', 2 )
			if vAttrArray and vAttrArray.offset not in geomDataProcessed:
				geomDataProcessed[vAttrArray.offset] = vAttrArray.getBranchSize()

			displayList = struct.initChild( 'DisplayListBlock', 5 )
			assert displayList.length != -1, 'display list data block invalid size'
			geomDataProcessed[displayList.offset] = displayList.length

			# Check for a 'next' (sibling) struct
			next = struct.initChild( 'PolygonObjDesc', 1 )
			if next:
				self._countStructs( next, structTotals, texturesProcessed, geomDataProcessed )

	def importModelGroup( self ):

		""" Called by the Import button below the model groups. Prompts the user 
			for a file to load, then decodes it and replaces the currently selected joint. """

		# Get the current selection
		iidSelectionsTuple = self.modelPartsTree.selection()
		if not iidSelectionsTuple:
			msg( 'No model parts are selected!', 'Nothing to Report, Captain' )
			return
		elif len( iidSelectionsTuple ) != 1:
			msg( 'Please only select one model group to replace.', 'Invalid Selection' )
			return

		# Prompt the user to choose a file to import
		filepath = tkFileDialog.askopenfilename(
			title="Choose a model file to open (replaces current selection).",
			parent=self.winfo_toplevel(),
			initialdir=globalData.getLastUsedDir( 'model' ),
			filetypes=[('Model data files', '*.dae *.fbx *.obj *.stl'), ('DAT files', '*.dat *.usd'), ('All files', '*.*')]
		)
		
		# The above will return an empty string if the user canceled
		if filepath: # This will be empty if the user canceled
			globalData.gui.updateProgramStatus( 'Operation canceled' )
			return
		
		# Clear current rendered objects
		self.engine.clearRenderings()

		#pyglet.model.load( filepath )

	def exportModelGroup( self ):

		""" Called by the Export button below the model groups. Prompts the user 
			for a select a destination folder and filename to export the currently selected joint. """
		
		# Get the current selection
		iidSelectionsTuple = self.modelPartsTree.selection()
		if not iidSelectionsTuple:
			msg( 'No model parts are selected!', 'Nothing to Report, Captain' )
			return

		# Prompt for a place to save the file
		savePath = tkFileDialog.asksaveasfilename(
			title="Where would you like to export the file?",
			parent=self.winfo_toplevel(),
			initialdir=globalData.getLastUsedDir( 'model' ),
			initialfile=self.file.filename,
			defaultextension=self.file.ext[1:], # Removing dot
			filetypes=[('Model data files', '*.dae *.fbx *.obj *.stl'), ('DAT files', '*.dat *.usd'), ('All files', '*.*')]
		)

		# The above will return an empty string if the user canceled
		if not savePath:
			globalData.gui.updateProgramStatus( 'Operation canceled' )
			return ''

		# Update the default directory to start in when opening or exporting files
		globalData.setLastUsedDir( savePath, 'model' )

		#parentJoint = self.file.getStruct( int(iidSelectionsTuple[0]) )
		structs = self.file.getBranch( int(iidSelectionsTuple[0]) )
		print( 'unsorted' )
		print( [ '{}; {}'.format(s.offset, s.length) for s in structs] )

		structs.sort( key=lambda s: s.offset)
		
		print( 'sorted' )
		print( [ hex( 0x20 + s.offset) for s in structs] )


	def addModelGroup( self ): pass
	def deleteModelGroup( self ): pass

	def editTextures( self ):

		""" Loads up this stage in the Textures Editor interface. """

		# Load the tab if it's not already present
		mainGui = globalData.gui
		if not mainGui.texturesTab:
			mainGui.texturesTab = TexturesEditor( mainGui.mainTabFrame, mainGui )

		# Switch to the tab
		mainGui.mainTabFrame.select( mainGui.texturesTab )
		
		# Add a tab for the current file and populate it
		mainGui.playSound( 'menuSelect' )
		mainGui.texturesTab.addTab( self.file )

	def onModelPartDoubleClick( self, event ): pass
	
	def adjustBlastzones( self ):
		# Create the rendering window and hide everything but the target
		rw = StageModelViewer( self.file, dimensions=(940, 600) )
		rw.toggleCamLimits( False )
		rw.togglePlayerSpawns( False )
		rw.toggleItemSpawns( False )

	def adjustCameraLimits( self ):
		# Create the rendering window and hide everything but the target
		rw = StageModelViewer( self.file, dimensions=(940, 600) )
		rw.toggleBlastzones( False )
		rw.togglePlayerSpawns( False )
		rw.toggleItemSpawns( False )

	def adjustPlayerSpawns( self ):
		# Create the rendering window and hide everything but the target
		rw = StageModelViewer( self.file, dimensions=(940, 600) )
		rw.toggleBlastzones( False )
		rw.toggleCamLimits( False )
		rw.toggleItemSpawns( False )

	def adjustItemSpawns( self ):
		# Create the rendering window and hide everything but the target
		rw = StageModelViewer( self.file, dimensions=(940, 600) )
		rw.toggleBlastzones( False )
		rw.toggleCamLimits( False )
		rw.togglePlayerSpawns( False )

	def ajustTargetPositions( self ): pass
	#def addNewGeneralPoint( self ): pass


class StageModelViewer( BasicWindow ):

	""" A window to view and edit various basic stage properties, including 
		blastzone/camera positions, item/player spawn points, and more. """
	
	def __init__( self, stageFile, dimensions, **kwargs ):
		self.file = stageFile
		
		windowTitle = 'Stage Editor - ' + stageFile.filename
		resizable = True
		controlPanelWidth = 270
		engineDimensions = ( dimensions[0] - controlPanelWidth, dimensions[1] ) # Make some space for the side control panel

		# Set up the main window
		if not BasicWindow.__init__( self, 
			globalData.gui.root, 
			windowTitle, 
			offsets=(120, 60), 
			resizable=resizable,
			dimensions=dimensions,
			minsize=(400, 300),
			unique=True, 
			**kwargs 
		):
			return # If the above returned false, it displayed an existing window, so we should exit here
		
		self.engine = RenderEngine( self.window, engineDimensions, resizable )
		self.engine.pack( side='left', expand=True, fill='both' )

		self.showBlastZones = Tk.BooleanVar( value=True )
		self.showCamLimits = Tk.BooleanVar( value=True )
		self.showCollisions = Tk.BooleanVar( value=True )
		self.showPlayerSpawns = Tk.BooleanVar( value=True )
		self.showItemSpawns = Tk.BooleanVar( value=True )

		ttk.Checkbutton( self.engine, text='Blastzones', variable=self.showBlastZones, command=self.toggleBlastzones ).place( relx=1.0, rely=.07, anchor='e', x=-10 )
		ttk.Checkbutton( self.engine, text='Camera Limits', variable=self.showCamLimits, command=self.toggleCamLimits ).place( relx=1.0, rely=.14, anchor='e', x=-10 )
		ttk.Checkbutton( self.engine, text='Collisions', variable=self.showCollisions, command=self.toggleCollisions ).place( relx=1.0, rely=.21, anchor='e', x=-10 )
		ttk.Checkbutton( self.engine, text='Player Spawns', variable=self.showPlayerSpawns, command=self.togglePlayerSpawns ).place( relx=1.0, rely=.28, anchor='e', x=-10 )
		ttk.Checkbutton( self.engine, text='Item Spawns', variable=self.showItemSpawns, command=self.toggleItemSpawns ).place( relx=1.0, rely=.35, anchor='e', x=-10 )

		self.sidePanelControls = ttk.Frame( self.window )
		self.sidePanelControls.pack( side='left', expand=True, fill='both' )
		
		self.renderBlastzones()
		self.renderCameraLimits()
		self.renderCollisions()
		
		# Add a frame to contain the Player/Item spawn dropdowns and their edit fields
		row = len( self.sidePanelControls.winfo_children() )
		self.singlePointEditFrame = ttk.Frame( self.sidePanelControls )
		self.singlePointEditFrame.grid( column=0, columnspan=2, row=row, pady=(20, 3), padx=10 )

		self.renderSpawnPoints()
		self.determineDefaultZoom()

	def toggleBlastzones( self, visible=None ):
		if visible != None:
			self.showBlastZones.set( visible )
		self.engine.showPart( 'blastzone', self.showBlastZones.get(), 'edge' )

	def toggleCamLimits( self, visible=None ):
		if visible != None:
			self.showCamLimits.set( visible )
		self.engine.showPart( 'camera', self.showCamLimits.get(), 'edge' )

	def toggleCollisions( self, visible=None ):
		if visible != None:
			self.showCollisions.set( visible )
		self.engine.showPart( 'collision', self.showCollisions.get(), 'quad' )

	def togglePlayerSpawns( self, visible=None ):
		if visible != None:
			self.showPlayerSpawns.set( visible )
		self.engine.showPart( 'playerSpawns', self.showPlayerSpawns.get(), 'vertex' )

	def toggleItemSpawns( self, visible=None ):
		if visible != None:
			self.showItemSpawns.set( visible )
		self.engine.showPart( 'itemSpawns', self.showItemSpawns.get(), 'vertex' )

	def close( self ):
		# Stop the rendering and destroy the Pyglet window/canvas instance
		self.engine.stop()

		# Destroy this window (plus other window cleanup)
		super( StageModelViewer, self ).close()

	def renderBlastzones( self ):
		topLeftJoint, bottomRightJoint = self._renderRectangle( 151, 152, 'Blast-Zone', (255, 0, 0, 255), ('blastzone',) )
		if not topLeftJoint or not bottomRightJoint:
			return

		self._addCoordsEditor( 'Blastzone Positions:', topLeftJoint, bottomRightJoint, self.redrawBlastzones )

	def renderCameraLimits( self ):
		topLeftJoint, bottomRightJoint = self._renderRectangle( 149, 150, 'Camera Limit', (200, 200, 200, 255), ('camera',) )
		if not topLeftJoint or not bottomRightJoint:
			return

		self._addCoordsEditor( 'Camera Limit Positions:', topLeftJoint, bottomRightJoint, self.redrawCameraLimits )

	def _addCoordsEditor( self, name, topLeftJoint, bottomRightJoint, callback ):

		row = len( self.sidePanelControls.winfo_children() )
		ttk.Label( self.sidePanelControls, text=name ).grid( column=0, columnspan=2, row=row, pady=(20, 3), padx=10 )

		# Left blastzone
		ttk.Label( self.sidePanelControls, text='Left:' ).grid( column=0, row=row+1, pady=2, padx=(5, 5) )
		valueOffset = topLeftJoint.offset + 0x2C
		valueEntry = HexEditEntry( self.sidePanelControls, self.file, valueOffset, 4, 'f', 'Left blastzone coordinate', valueEntry=True, width=9 )
		valueEntry.set( topLeftJoint.getValues('Translation_X') )
		valueEntry.grid( column=1, row=row+1, pady=2, padx=(5, 20) )
		valueEntry.callback = callback # Called to update the display when the above is modified

		# Top blastzone
		ttk.Label( self.sidePanelControls, text='Top:' ).grid( column=0, row=row+2, pady=2, padx=(5, 5) )
		valueOffset = topLeftJoint.offset + 0x30
		valueEntry = HexEditEntry( self.sidePanelControls, self.file, valueOffset, 4, 'f', 'Top blastzone coordinate', valueEntry=True, width=9 )
		valueEntry.set( topLeftJoint.getValues('Translation_Y') )
		valueEntry.grid( column=1, row=row+2, pady=2, padx=(5, 20) )
		valueEntry.callback = callback # Called to update the display when the above is modified

		# Right blastzone
		ttk.Label( self.sidePanelControls, text='Right:' ).grid( column=0, row=row+3, pady=2, padx=(5, 5) )
		valueOffset = bottomRightJoint.offset + 0x2C
		valueEntry = HexEditEntry( self.sidePanelControls, self.file, valueOffset, 4, 'f', 'Right blastzone coordinate', valueEntry=True, width=9 )
		valueEntry.set( bottomRightJoint.getValues('Translation_X') )
		valueEntry.grid( column=1, row=row+3, pady=2, padx=(5, 20) )
		valueEntry.callback = callback # Called to update the display when the above is modified

		# Bottom blastzone
		ttk.Label( self.sidePanelControls, text='Bottom:' ).grid( column=0, row=row+4, pady=2, padx=(5, 5) )
		valueOffset = bottomRightJoint.offset + 0x30
		valueEntry = HexEditEntry( self.sidePanelControls, self.file, valueOffset, 4, 'f', 'Bottom blastzone coordinate', valueEntry=True, width=9 )
		valueEntry.set( bottomRightJoint.getValues('Translation_Y') )
		valueEntry.grid( column=1, row=row+4, pady=2, padx=(5, 20) )
		valueEntry.callback = callback # Called to update the display when the above is modified

	def redrawBlastzones( self, event ):
		self.engine.removePart( 'blastzone', 'edge' )
		self._renderRectangle( 151, 152, 'Blast-Zone', (255, 0, 0, 255), ('blastzone',) )

	def redrawCameraLimits( self, event ):
		self.engine.removePart( 'camera', 'edge' )
		self._renderRectangle( 149, 150, 'Camera Limit', (200, 200, 200, 255), ('camera',) )

	def redrawPoints( self, event ):
		self.engine.removePart( 'playerSpawns', 'vertex' )
		self.engine.removePart( 'itemSpawns', 'vertex' )
		self._renderPoints()

	def _renderRectangle( self, pointType1, pointType2, name, color, tags=() ):

		""" Renders a pair of general points as a rectangular area (4 edges). 
			This is similar to a quad, but with no fill area. 
			Returns the top-left and bottom-right joints which define the rectangle. """

		# Parse the map head and get blast zone coordinates
		topLeftJoints = self.file.getGeneralPoint( pointType1 )
		bottomRightJoints = self.file.getGeneralPoint( pointType2 )

		# Check that we only found one of each point, just in case there's something crazy out there
		if not topLeftJoints:
			printStatus( 'Unable to find any Top-Left {} general points!'.format(name), error=True )
			return None, None
		elif not bottomRightJoints:
			printStatus( 'Unable to find any Bottom-Right {} general points!'.format(name), error=True )
			return None, None
		if len( topLeftJoints ) > 1:
			printStatus( 'Found multiple Top-Left {} general points!'.format(name), warning=True )
		if len( bottomRightJoints ) > 1:
			printStatus( 'Found multiple Bottom-Right {} general points!'.format(name), warning=True )
		
		# Build four edges in 3D space from the two general points
		tlJoint, brJoint = topLeftJoints[0], bottomRightJoints[0]
		x1 = tlJoint.getValues( 'Translation_X' )
		y1 = tlJoint.getValues( 'Translation_Y' )
		x2 = brJoint.getValues( 'Translation_X' )
		y2 = brJoint.getValues( 'Translation_Y' )
		self.engine.addEdge( (x1,y1,0,x2,y1,0), color=color, tags=tags, thickness=3 )
		self.engine.addEdge( (x2,y1,0,x2,y2,0), color=color, tags=tags, thickness=3 )
		self.engine.addEdge( (x2,y2,0,x1,y2,0), color=color, tags=tags, thickness=3 )
		self.engine.addEdge( (x1,y2,0,x1,y1,0), color=color, tags=tags, thickness=3 )

		return tlJoint, brJoint

	def renderCollisions( self ):
		
		# Get the structures defining the stage's spot, links, and areas
		self.collStruct = self.file.getStructByLabel( 'coll_data' )
		spotTableOffset, linkTableOffset, areaTableOffset = self.collStruct.getChildren()
		self.spotTable = self.file.getStruct( spotTableOffset )
		self.linkTable = self.file.getStruct( linkTableOffset )
		self.areaTable = self.file.getStruct( areaTableOffset )

		self.vertices = self.spotTable.getVertices()
		self.collisionLinks = self.linkTable.getFaces() # A list of CollissionSurface objects
		self.areas = self.areaTable.getAreas()

		self._extrudeCollisionLinks()

	def _extrudeCollisionLinks( self ):

		""" Extrudes each collision link (which are initially 2D lines/edges), turning them into 3D faces. """

		self.collVertices = []
		z = 8 # The actual thickness will be double this value
		origVerticesLength = len( self.vertices )

		for link in self.collisionLinks:
			# Perform some validation
			link.validIndices = True
			if link.points[0] < 0 or link.points[0] >= origVerticesLength: link.validIndices = False
			if link.points[1] < 0 or link.points[1] >= origVerticesLength: link.validIndices = False
			for pointIndex in link.allSpotIndices[2:]:
				if pointIndex < -1 or pointIndex >= origVerticesLength:
					print( 'Link {} refereneces a non-existant point (index {})'.format(link.index, pointIndex) )
					break
			link.origPoints = link.points
			if not link.validIndices: continue

			# Convert the two points (spots) to 4 quad vertices
			v1 = self.vertices[ link.points[0] ]
			v2 = self.vertices[ link.points[1] ]
			vertices = [ v1.x,v1.y,-z, v2.x,v2.y,-z, v2.x,v2.y,z, v1.x,v1.y,z ]
			
			# Determine a color based on its collision physics type and create the quad
			link.colorByPhysics()
			color = hex2rgb( link.fill + 'FF' )
			link.renderObj = self.engine.addQuad( vertices, color=color, colors=(), tags=('collision',) )
			link.renderObj.collLink = link

	def _renderPoints( self ):

		""" Renders general points for player and item spawns in the window, 
			and returns two list of names for all of these points found. """

		pointGroups = self.file.mapHead.getGeneralPoints()
		playerSpawns = []
		itemSpawns = []

		# Collect points of certain types
		for groupIndex, group in enumerate( pointGroups ):
			for jointIndex, pointType, pointName, coords, scale in group:
				if pointName.startswith( 'Player' ):
					playerSpawns.append( pointName )

					color = self.colorByVertType( pointType )
					vertex = self.engine.addVertex( (coords[0], coords[1], 0), color, ('playerSpawns', pointType), self.showPlayerSpawns.get(), 5 )

				elif pointName.startswith( 'Item' ):
					itemSpawns.append( pointName )

					color = self.colorByVertType( pointType )
					vertex = self.engine.addVertex( (coords[0], coords[1], 0), color, ('itemSpawns', pointType), self.showItemSpawns.get(), 5 )

		return playerSpawns, itemSpawns

	def renderSpawnPoints( self ):

		""" Searches the stage's general points and adds the point-selection 
			drop-down menus to the render window's control panel. """

		playerSpawns, itemSpawns = self._renderPoints()

		# Add an interface to edit Player Spawn/Respawn points
		if playerSpawns:
			textVar = Tk.StringVar() # Required to init the optionmenu
			dropdown = ttk.OptionMenu( self.singlePointEditFrame, textVar, playerSpawns[0], *playerSpawns, command=self.playerSpawnOptionSelected, direction='above' )
			dropdown.grid( column=0, columnspan=2, row=0, pady=3, padx=10 )
		
			self._addPointCoordEditors( playerSpawns[0], 1 )
		else:
			label = ttk.Label( self.singlePointEditFrame, text='No player spawns set!' )
			label.grid( column=0, columnspan=2, row=0, pady=3, padx=10 )

		# Add an interface to edit Item Spawn points
		if itemSpawns:
			textVar = Tk.StringVar() # Required to init the optionmenu
			dropdown = ttk.OptionMenu( self.singlePointEditFrame, textVar, itemSpawns[0], *itemSpawns, command=self.itemSpawnOptionSelected, direction='below' )
			dropdown.grid( column=0, columnspan=2, row=3, pady=(12, 3), padx=10 )
		
			self._addPointCoordEditors( itemSpawns[0], 4 )
		else:
			label = ttk.Label( self.singlePointEditFrame, text='No item spawns set!' )
			label.grid( column=0, columnspan=2, row=3, pady=(12, 3), padx=10 )

	def colorByVertType( self, pointType ):

		if pointType == 0 or pointType == 4: # Player 1 Spawn or Respawn
			color = ( 248, 0, 0, 255 ) # Red

		elif pointType == 1 or pointType == 5: # Player 2 Spawn or Respawn
			color = ( 0, 104, 232, 255 ) # Blue

		elif pointType == 2 or pointType == 6: # Player 3 Spawn or Respawn
			color = ( 232, 144, 0, 255 ) # Orange

		elif pointType == 3 or pointType == 7: # Player 4 Spawn or Respawn
			color = ( 16, 216, 56, 255 ) # Green

		elif pointType >= 127 and pointType <= 146: # Item Spawns
			spawnIndex = pointType - 127
			brightness = 255 - ( spawnIndex * 13 ) # Higher index = lower brightness
			color = ( brightness, brightness, brightness, 255 )
		else:
			color = ( 128, 128, 128, 255 )

		return color

	def playerSpawnOptionSelected( self, newOption ):
		# Destroy the label & entry widgets on the 1st and 2nd rows
		row1Widgets = self.singlePointEditFrame.grid_slaves( row=1 )
		row2Widgets = self.singlePointEditFrame.grid_slaves( row=2 )
		for widget in row1Widgets + row2Widgets:
			widget.destroy()

		# Add new widgets for the target point
		self._addPointCoordEditors( newOption, 1 )

	def itemSpawnOptionSelected( self, newOption ):
		# Destroy the label & entry widgets on the 4th and 5th rows
		row1Widgets = self.singlePointEditFrame.grid_slaves( row=4 )
		row2Widgets = self.singlePointEditFrame.grid_slaves( row=5 )
		for widget in row1Widgets + row2Widgets:
			widget.destroy()

		# Add new widgets for the target point
		self._addPointCoordEditors( newOption, 4 )

	def _addPointCoordEditors( self, targetPointName, row ):

		""" Adds two entry fields to display (and allow editing for) the 
			given point's X and Y coordinates. """

		# Convert the given point name (string) to the point type enum
		typeDict = MapPointTypesArray.enums['Point_Type']
		pointType = reverseDictLookup( typeDict, targetPointName )

		# Get the point's JObj and x/y coords
		joint = self.file.getGeneralPoint( pointType )[0] #todo allow editing multiple at once
		x = joint.getValues( 'Translation_X' )
		y = joint.getValues( 'Translation_Y' )

		# X coord
		ttk.Label( self.singlePointEditFrame, text='X:' ).grid( column=0, row=row, pady=2, padx=(5, 5) )
		valueOffset = joint.offset + 0x2C
		valueEntry = HexEditEntry( self.singlePointEditFrame, self.file, valueOffset, 4, 'f', targetPointName+' x-coord', valueEntry=True, width=15 )
		valueEntry.set( x )
		valueEntry.grid( column=1, row=row, pady=2, padx=(5, 20) )
		valueEntry.pointType = pointType
		valueEntry.callback = self.redrawPoints # Called to update the display when the above is modified
		
		# Y coord
		ttk.Label( self.singlePointEditFrame, text='Y:' ).grid( column=0, row=row+1, pady=2, padx=(5, 5) )
		valueOffset = joint.offset + 0x30
		valueEntry = HexEditEntry( self.singlePointEditFrame, self.file, valueOffset, 4, 'f', targetPointName+' y-coord', valueEntry=True, width=15 )
		valueEntry.set( y )
		valueEntry.grid( column=1, row=row+1, pady=2, padx=(5, 20) )
		valueEntry.pointType = pointType
		valueEntry.callback = self.redrawPoints # Called to update the display when the above is modified

	def determineDefaultZoom( self ):

		""" Sets the default/original zoom level of the renderer. Based on the size of the 
			stage's blast-zones if they are set to be visible. If they are not visible, the 
			camera limits are used if they are visible. If neither of these are set to be 
			visible, the stage's collisions are used. """

		coords = []

		if self.showBlastZones.get():
			for edge in self.engine.edges:
				if 'blastzone' not in edge.tags:
					continue

				coords.extend( edge.vertices[1][:2] ) # X/Y coords for the first point
				coords.extend( edge.vertices[1][3:5] ) # X/Y coords for the second point

		elif self.showCamLimits.get():
			for edge in self.engine.edges:
				if 'camera' not in edge.tags:
					continue

				coords.extend( edge.vertices[1][:2] ) # X/Y coords for the first point
				coords.extend( edge.vertices[1][3:5] ) # X/Y coords for the second point

		else: # Base off of collision links (all X/Y coords are already available in the spot table)
			coords = self.spotTable.values

		maxCoord = max( [abs(value) for value in coords] )
		zOffset = maxCoord * 1.4

		self.engine.camera.position.z = zOffset
		self.engine.camera.focalDistance = zOffset