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
import math
import codecs
import psutil
import struct
import win32gui
import subprocess
import win32process
import tkFileDialog
import Tkinter as Tk

from ruamel import yaml
from shutil import copy
from binascii import hexlify
from ScrolledText import ScrolledText
from PIL import ImageGrab

# Internal dependencies
import globalData
import FileSystem.hsdStructures as hsdStructures

from FileSystem.disc import Disc
from codeMods import CodeLibraryParser
from basicFunctions import msg, uHex, cmdChannel, printStatus, humansize
from guiSubComponents import BasicWindow, ColoredLabelButton, VerticalScrolledFrame, cmsg, Dropdown, getNewNameFromUser, LabelButton


#class NumberConverter( BasicWindow ):


class ImageDataLengthCalculator( BasicWindow ):

	def __init__( self, root ):
		BasicWindow.__init__( self, root, 'Image Data Length Calculator' )

		# Set up the input elements
		# Width
		ttk.Label( self.window, text='Width:' ).grid( column=0, row=0, padx=5, pady=2, sticky='e' )
		self.widthEntry = ttk.Entry( self.window, width=5, justify='center' )
		self.widthEntry.grid( column=1, row=0, padx=5, pady=2 )
		# Height
		ttk.Label( self.window, text='Height:' ).grid( column=0, row=1, padx=5, pady=2, sticky='e' )
		self.heightEntry = ttk.Entry( self.window, width=5, justify='center' )
		self.heightEntry.grid( column=1, row=1, padx=5, pady=2 )
		# Input Type
		ttk.Label( self.window, text='Image Type:' ).grid( column=0, row=2, padx=5, pady=2, sticky='e' )
		self.typeEntry = ttk.Entry( self.window, width=5, justify='center' )
		self.typeEntry.grid( column=1, row=2, padx=5, pady=2 )
		# Result Multiplier
		ttk.Label( self.window, text='Result Multiplier:' ).grid( column=0, row=3, padx=5, pady=2, sticky='e' )
		self.multiplierEntry = ttk.Entry( self.window, width=5, justify='center' )
		self.multiplierEntry.insert( 0, '1' ) # Default
		self.multiplierEntry.grid( column=1, row=3, padx=5, pady=2 )

		# Bind the event listeners for calculating the result
		for inputWidget in [ self.widthEntry, self.heightEntry, self.typeEntry, self.multiplierEntry ]:
			inputWidget.bind( '<KeyRelease>', self.calculateResult )

		# Set the output elements
		ttk.Label( self.window, text='Required File or RAM space:' ).grid( column=0, row=4, columnspan=2, padx=20, pady=5 )
		# In hex bytes
		self.resultEntryHex = ttk.Entry( self.window, width=20, justify='center' )
		self.resultEntryHex.grid( column=0, row=5, padx=5, pady=5 )
		ttk.Label( self.window, text='bytes (hex)' ).grid( column=1, row=5, padx=5, pady=5 )
		# In decimal bytes
		self.resultEntryDec = ttk.Entry( self.window, width=20, justify='center' )
		self.resultEntryDec.grid( column=0, row=6, padx=5, pady=5 )
		ttk.Label( self.window, text='(decimal)' ).grid( column=1, row=6, padx=5, pady=5 )

	def calculateResult( self, event ):
		try:
			widthValue = self.widthEntry.get()
			if not widthValue: return
			elif '0x' in widthValue: width = int( widthValue, 16 )
			else: width = int( widthValue )

			heightValue = self.heightEntry.get()
			if not heightValue: return
			elif '0x' in heightValue: height = int( heightValue, 16 )
			else: height = int( heightValue )

			typeValue = self.typeEntry.get()
			if not typeValue: return
			elif '0x' in typeValue: _type = int( typeValue, 16 )
			else: _type = int( typeValue )

			multiplierValue = self.multiplierEntry.get()
			if not multiplierValue: return
			elif '0x' in multiplierValue: multiplier = int( multiplierValue, 16 )
			else: multiplier = float( multiplierValue )

			# Calculate the final amount of space required.
			imageDataLength = hsdStructures.ImageDataBlock.getDataLength( width, height, _type )
			finalSize = int( math.ceil(imageDataLength * multiplier) ) # Can't have fractional bytes, so we're rounding up

			self.resultEntryHex.delete( 0, 'end' )
			self.resultEntryHex.insert( 0, uHex(finalSize) )
			self.resultEntryDec.delete( 0, 'end' )
			self.resultEntryDec.insert( 0, humansize(finalSize) )
		except:
			self.resultEntryHex.delete( 0, 'end' )
			self.resultEntryHex.insert( 0, 'Invalid Input' )
			self.resultEntryDec.delete( 0, 'end' )


class AsmToHexConverter( BasicWindow ):

	""" Tool window to convert assembly to hex and vice-verca. """

	def __init__( self, mod=None ):
		BasicWindow.__init__( self, globalData.gui.root, 'ASM <-> HEX Converter', offsets=(160, 100), resizable=True, topMost=False, minsize=(460, 350) )

		# Display info and a few controls
		topRow = ttk.Frame( self.window )
		ttk.Label( topRow, text=('This assembles PowerPC assembly code into raw hex,\nor disassembles raw hex into PowerPC assembly.'
			#"\n\nNote that this functionality is also built into the entry fields for new code in the 'Add New Mod to Library' interface. "
			#'So you can use your assembly source code in those fields and it will automatically be converted to hex during installation. '
			'\nComments preceded with "#" will be ignored.'), wraplength=480 ).grid( column=0, row=0, rowspan=4 )

		ttk.Label( topRow, text='Beautify Hex:' ).grid( column=1, row=0 )
		options = [ '1 Word Per Line', '2 Words Per Line', '3 Words Per Line', '4 Words Per Line', '5 Words Per Line', '6 Words Per Line', 'No Whitespace' ]
		Dropdown( topRow, options, default=options[1], command=self.beautifyChanged ).grid( column=1, row=1 )

		self.assembleSpecialSyntax = Tk.BooleanVar( value=False )
		ttk.Checkbutton( topRow, text='Assemble Special Syntax', variable=self.assembleSpecialSyntax ).grid( column=1, row=2, pady=5 )

		self.assemblyDetectedLabel = ttk.Label( topRow, text='Assembly Detected:      ' ) # Leave space for true/false string
		self.assemblyDetectedLabel.grid( column=1, row=3 )

		topRow.grid( column=0, row=0, padx=40, pady=(7, 7), sticky='ew' )
		
		# Configure the top row, so it expands properly on window-resize
		topRow.columnconfigure( 0, weight=1, minsize=400 )
		topRow.columnconfigure( 0, weight=1 )

		self.lengthString = Tk.StringVar( value='' )
		self.mod = mod
		self.syntaxInfo = []
		self.isAssembly = False
		self.blocksPerLine = 2

		# Create the header row
		headersRow = ttk.Frame( self.window )
		ttk.Label( headersRow, text='ASM' ).grid( row=0, column=0, sticky='w' )
		ttk.Label( headersRow, textvariable=self.lengthString ).grid( row=0, column=1 )
		ttk.Label( headersRow, text='HEX' ).grid( row=0, column=2, sticky='e' )
		headersRow.grid( column=0, row=1, padx=40, pady=(7, 0), sticky='ew' )

		# Configure the header row, so it expands properly on window-resize
		headersRow.columnconfigure( 'all', weight=1 )

		# Create the text entry fields and center conversion buttons
		entryFieldsRow = ttk.Frame( self.window )
		self.sourceCodeEntry = ScrolledText( entryFieldsRow, width=30, height=20 )
		self.sourceCodeEntry.grid( rowspan=2, column=0, row=0, padx=5, pady=7, sticky='news' )
		ttk.Button( entryFieldsRow, text='->', command=self.asmToHexCode ).grid( column=1, row=0, pady=30, sticky='s' )
		ttk.Button( entryFieldsRow, text='<-', command=self.hexCodeToAsm ).grid( column=1, row=1, pady=30, sticky='n' )
		self.hexCodeEntry = ScrolledText( entryFieldsRow, width=30, height=20 )
		self.hexCodeEntry.grid( rowspan=2, column=2, row=0, padx=5, pady=7, sticky='news' )
		entryFieldsRow.grid( column=0, row=2, sticky='nsew' )
		
		# Configure the above columns, so that they expand proportionally upon window resizing
		entryFieldsRow.columnconfigure( 0, weight=1 )
		entryFieldsRow.columnconfigure( 1, weight=0 ) # No weight to this row, since it's just the buttons
		entryFieldsRow.columnconfigure( 2, weight=1 )
		entryFieldsRow.rowconfigure( 'all', weight=1 )

		bottomRow = ttk.Frame( self.window )

		# Add the assembly time display (as an Entry widget so we can select text from it)
		self.assemblyTimeDisplay = Tk.Entry( bottomRow, width=25, borderwidth=0 )
		self.assemblyTimeDisplay.configure( state="readonly" )
		self.assemblyTimeDisplay.grid( column=0, row=0, sticky='w', padx=(25, 0) )

		# Determine the include paths to be used here, and add a button at the bottom of the window to display them
		self.detectContext()
		ttk.Button( bottomRow, text='View Include Paths', command=self.viewIncludePaths ).grid( column=1, row=0, ipadx=7 )
		#ttk.Button( bottomRow, text='Save Hex to File', command=self.saveHexToFile ).grid( column=2, row=0, ipadx=7, sticky='e', padx=40 )
		buttonsFrame = ttk.Frame( bottomRow )
		ColoredLabelButton( buttonsFrame, 'saveToFile', self.saveHexToFile, 'Save Hex to File' ).pack( side='right', padx=8 )
		ColoredLabelButton( buttonsFrame, 'saveToClipboard', self.copyHexToClipboard, 'Copy Hex to Clipboard' ).pack( side='right', padx=8 )
		buttonsFrame.grid( column=2, row=0, ipadx=7, sticky='e', padx=40 )
		bottomRow.grid( column=0, row=3, pady=(2, 6), sticky='ew' )
		bottomRow.columnconfigure( 'all', weight=1 )

		# Add the assembly time display (as an Entry widget so we can select text from it)
		# self.assemblyTimeDisplay = Tk.Entry( self.window, width=25, borderwidth=0 )
		# self.assemblyTimeDisplay.configure( state="readonly" )
		# self.assemblyTimeDisplay.place( x=10, rely=1.0, y=-27 )

		# # Determine the include paths to be used here, and add a button at the bottom of the window to display them
		# self.detectContext()
		# ttk.Button( self.window, text='View Include Paths', command=self.viewIncludePaths ).grid( column=0, row=3, pady=(2, 6), ipadx=7 )
		# ttk.Button( self.window, text='Save Hex to File', command=self.saveHexToFile ).place( relx=1.0, rely=1.0, x=-150, y=-31 )

		# Configure this window's expansion as a whole, so that only the text entry row can expand when the window is resized
		self.window.columnconfigure( 0, weight=1 )
		self.window.rowconfigure( 0, weight=0 )
		self.window.rowconfigure( 1, weight=0 )
		self.window.rowconfigure( 2, weight=1 )
		self.window.rowconfigure( 3, weight=0 )

	def updateAssemblyTimeDisplay( self, textInput ):
		self.assemblyTimeDisplay.configure( state="normal" )
		self.assemblyTimeDisplay.delete( 0, 'end' )
		self.assemblyTimeDisplay.insert( 0, textInput )
		self.assemblyTimeDisplay.configure( state="readonly" )

	def asmToHexCode( self ):
		# Clear the hex code field and info labels
		self.hexCodeEntry.delete( '1.0', 'end' )
		self.updateAssemblyTimeDisplay( '' )
		self.lengthString.set( 'Length: ' )
		self.assemblyDetectedLabel['text'] = 'Assembly Detected:      '

		# Get the ASM to convert
		asmCode = self.sourceCodeEntry.get( '1.0', 'end' )

		# Evaluate the code and pre-process it (scan it for custom syntaxes and assemble everything else)
		tic = time.clock()
		results = globalData.codeProcessor.evaluateCustomCode( asmCode, self.includePaths, validateConfigs=False )
		returnCode, codeLength, hexCode, self.syntaxInfo, self.isAssembly = results
		toc = time.clock()

		# Check for errors (hexCode should include warnings from the assembler)
		if returnCode not in (0, 100):
			cmsg( hexCode, 'Assembly Error' )
			return

		# Swap back in custom sytaxes
		if self.syntaxInfo and not self.assembleSpecialSyntax.get():
			hexCode = globalData.codeProcessor.restoreCustomSyntaxInHex( hexCode, self.syntaxInfo, codeLength, self.blocksPerLine )

		# Beautify and insert the new hex code
		elif self.blocksPerLine > 0:
			hexCode = globalData.codeProcessor.beautifyHex( hexCode, blocksPerLine=self.blocksPerLine )

		self.hexCodeEntry.insert( 'end', hexCode )

		# Update the code length display
		self.lengthString.set( 'Length: ' + uHex(codeLength) )
		if self.isAssembly:
			self.assemblyDetectedLabel['text'] = 'Assembly Detected: True '
		else:
			self.assemblyDetectedLabel['text'] = 'Assembly Detected: False'

		# Update the assembly time display with appropriate units
		assemblyTime = round( toc - tic, 9 )
		if assemblyTime > 1:
			units = 's' # In seconds
		else:
			assemblyTime = assemblyTime * 1000
			if assemblyTime > 1:
				units = 'ms' # In milliseconds
			else:
				assemblyTime = assemblyTime * 1000
				units = 'us' # In microseconds
		self.updateAssemblyTimeDisplay( 'Assembly Time:  {} {}'.format(assemblyTime, units) )

	def hexCodeToAsm( self ):
		# Delete the current assembly code, and clear the assembly time label
		self.sourceCodeEntry.delete( '1.0', 'end' )
		self.updateAssemblyTimeDisplay( '' )
		self.assemblyDetectedLabel['text'] = 'Assembly Detected:      '

		# Get the HEX code to disassemble
		hexCode = self.hexCodeEntry.get( '1.0', 'end' )
		
		# Evaluate the code and pre-process it (scan it for custom syntaxes)
		results = globalData.codeProcessor.evaluateCustomCode( hexCode, self.includePaths, validateConfigs=False )
		returnCode, codeLength, hexCode, self.syntaxInfo, self.isAssembly = results
		if returnCode != 0:
			self.lengthString.set( 'Length: ' )
			return
		
		# Disassemble the code into assembly
		#returnCode, asmCode, codeLength = globalData.codeProcessor.preDisassembleRawCode( hexCode, discardWhitespace=False )
		asmCode, errors = globalData.codeProcessor.disassemble( hexCode )
		if errors:
			cmsg( errors, 'Disassembly Error' )
			return

		if self.syntaxInfo and not self.assembleSpecialSyntax.get():
			asmCode = self.restoreCustomSyntaxInAsm( asmCode )

		# Replace the current assembly code
		self.sourceCodeEntry.insert( 'end', asmCode )

		# Update the code length display
		self.lengthString.set( 'Length: ' + uHex(codeLength) )
		if self.isAssembly:
			self.assemblyDetectedLabel['text'] = 'Assembly Detected: True '
		else:
			self.assemblyDetectedLabel['text'] = 'Assembly Detected: False'

	def restoreCustomSyntaxInAsm( self, asmLines ):

		""" Swap out assembly code for the original custom syntax line that it came from. """

		# Build a new list of ( offset, wordString ) so we can separate words included on the same line
		specialWords = []
		for offset, length, syntaxType, codeLine, names in self.syntaxInfo:
			if syntaxType == 'sbs' or syntaxType == 'sym':
				specialWords.append( (offset, length, syntaxType, codeLine) )
			else:
				# Extract names (eliminating whitespace associated with names) and separate hex groups
				sectionChunks = codeLine.split( '[[' )
				for i, chunk in enumerate( sectionChunks ):
					if ']]' in chunk:
						varName, chunk = chunk.split( ']]' )
						sectionChunks[i] = '[[]]' + chunk

				# Recombine the string and split on whitespace
				newLine = ''.join( sectionChunks )
				hexGroups = newLine.split() # Will now have something like [ '000000[[]]' ] or [ '40820008', '0000[[]]' ]

				# Process each hex group
				nameIndex = 0
				groupParts = []
				for group in hexGroups:
					if ']]' in group:
						specialWords.append( (offset, length, syntaxType, group.replace('[[]]', '[['+names[nameIndex]+']]')) )
						nameIndex += 1

		newLines = []
		offset = 0

		for line in asmLines.splitlines():
			if specialWords and offset + 4 > specialWords[0][0]:
				info = specialWords.pop( 0 )
				if info[2] == 'opt':
					length = info[1]
					if length == 4:
						newLines.append( '.long ' + info[3] )
					elif length == 2:
						newLines.append( '.word ' + info[3] )
					else:
						newLines.append( '.byte ' + info[3] )
				else:
					newLines.append( info[3] )
			else:
				newLines.append( line )
			offset += 4

		return '\n'.join( newLines )

	def detectContext( self ):

		""" This window should use the same .include context for whatever mod it was opened with. 
			If an associated mod is not found, fall back on the default import directories. """

		if self.mod:
			self.includePaths = self.mod.includePaths
		else:
			libraryFolder = globalData.getModsFolderPath()
			self.includePaths = [ os.path.join(libraryFolder, '.include'), os.path.join(globalData.scriptHomeFolder, '.include') ]

	def viewIncludePaths( self ):

		""" Build and display a message to the user on assembly context and current paths. """

		# Build the message to show the user
		paths = [ os.getcwd() + '          <- Current Working Directory' ]
		paths.extend( self.includePaths )
		paths = '\n'.join( paths )

		message =	( 'Assembly context (for ".include" file imports) has the following priority:'
					  "\n\n1) The current working directory (usually the program root folder)"
					  "\n2) Directory of the mod's code file (or the code's root folder with AMFS)"
					  """\n3) The current Code Library's ".include" directory"""
					  """\n4) The program root folder's ".include" directory""" )

		if self.mod:
			message += ( '\n\n\nThis instance of the converter is using assembly context for .include file imports based on {}. '
					 'The exact paths are as follows:\n\n{}'.format( self.mod.name, paths ) )
		else:
			message += ( '\n\n\nThis instance of the converter is using default assembly context for .include file imports. '
					 'The exact paths are as follows:\n\n' + paths )

		cmsg( message, 'Include Paths', 'left' )

	def saveHexToFile( self, event=None ):

		""" Prompts the user for a save location, and then saves the hex code to file as binary. """

		# Get the hex code and remove whitespace
		hexCode = self.hexCodeEntry.get( '1.0', 'end' )
		hexCode = ''.join( hexCode.split() )

		if not hexCode:
			msg( 'No hex code to save!', 'No Hex Code', warning=True )
			return

		savePath = tkFileDialog.asksaveasfilename(
			title="Where would you like to export the file?",
			parent=self.window,
			initialdir=globalData.getLastUsedDir(),
			initialfile='Bin.bin',
			defaultextension='bin',
			filetypes=[( "Binary files", '*.bin' ), ( "Data archive files", '*.dat' ), ( "All files", "*.*" )] )

		# The above will return an empty string if the user canceled
		if not savePath:
			globalData.gui.updateProgramStatus( 'File save canceled' )
			return

		# Save the hex code to file as binary
		try:
			with open( savePath, 'wb' ) as binFile:
				binFile.write( bytearray.fromhex(hexCode) )

			globalData.gui.updateProgramStatus( 'File saved to "{}"'.format(savePath) )

		except IOError as e: # Couldn't create the file (likely a permission issue)
			msg( 'Unable to create "' + savePath + '" file! This is likely due to a permissions issue. You might try saving to somewhere else.', 'Error' )
			globalData.gui.updateProgramStatus( 'Unable to save; could not create the file at the destination' )

		except ValueError as e: # Couldn't convert the hex to a bytearray
			msg( 'Unable to convert the hex to binary; you may want to check for illegal characters.', 'Error' )
			globalData.gui.updateProgramStatus( 'Unable to save; hex string could not be converted to bytearray' )

	def copyHexToClipboard( self, event=None ):
		hexCode = self.hexCodeEntry.get( '1.0', 'end' )
		
		globalData.gui.root.clipboard_clear()
		globalData.gui.root.clipboard_append( hexCode )

	def _flushBuffer( self, pureHexBuffer, newLines ):

		""" Helper method to the beautify update method below; this dumps hex code 
			that has been collected so far into the newLines list (properly formatted). """

		if pureHexBuffer:
			# Combine the hex collected so far into one string, and beautify it if needed
			pureHex = ''.join( pureHexBuffer )
			if self.blocksPerLine > 0:
				pureHex = globalData.codeProcessor.beautifyHex( pureHex, blocksPerLine=self.blocksPerLine )

			# Store hex and clear the hex buffer
			newLines.append( pureHex )
			pureHexBuffer = []

		return pureHexBuffer, newLines

	def beautifyChanged( self, widget, newValue ):

		""" Called when the Beautify Hex dropdown option is changed.
			Reformats the HEX output to x number of words per line. """

		# Parse the current dropdown option for a block count
		try:
			self.blocksPerLine = int( newValue.split()[0] )
		except:
			self.blocksPerLine = 0

		# Get hex code currently displayed if there is any
		hexCode = self.hexCodeEntry.get( '1.0', 'end' )
		if not hexCode: return

		# Clear the hex code field and info labels
		self.hexCodeEntry.delete( '1.0', 'end' )
		
		newLines = []
		pureHexBuffer = []
		customSyntaxFound = False

		for rawLine in hexCode.splitlines():
			# Start off by filtering out comments, and skip empty lines
			codeLine = rawLine.split( '#' )[0].strip()
			if not codeLine: continue

			elif CodeLibraryParser.isSpecialBranchSyntax( codeLine ): # e.g. "bl 0x80001234" or "bl <testFunction>"
				customSyntaxFound = True
			
			elif CodeLibraryParser.containsPointerSymbol( codeLine ): # Identifies symbols in the form of <<functionName>>
				customSyntaxFound = True

			elif '[[' in codeLine and ']]' in codeLine: # Identifies configuration option placeholders
				customSyntaxFound = True
			else:
				customSyntaxFound = False

			if customSyntaxFound:
				pureHexBuffer, newLines = self._flushBuffer( pureHexBuffer, newLines )
				newLines.append( codeLine )
			else:
				# Strip out whitespace and store the line
				pureHex = ''.join( codeLine.split() )
				pureHexBuffer.append( pureHex )

		newLines = self._flushBuffer( pureHexBuffer, newLines )[1]

		# Collapse the code lines to a string and reinsert it into the text widget
		hexCode = '\n'.join( newLines )
		self.hexCodeEntry.insert( 'end', hexCode )


class CodeLookup( BasicWindow ):

	def __init__( self ):
		BasicWindow.__init__( self, globalData.gui.root, 'Code Lookup', resizable=True, minsize=(520, 300) )

		pady = 6

		mainFrame = ttk.Frame( self.window )
		controlPanel = ttk.Frame( mainFrame )

		# Set up offset/address input
		ttk.Label( controlPanel, text='Enter a DOL Offset or RAM Address:' ).grid( column=0, row=0, columnspan=2, padx=5, pady=(25, pady) )
		validationCommand = globalData.gui.root.register( self.locationUpdated )
		self.location = Tk.Entry( controlPanel, width=13, 
				justify='center', 
				relief='flat', 
				highlightbackground='#b7becc', 	# Border color when not focused
				borderwidth=1, 
				highlightthickness=1, 
				highlightcolor='#0099f0', 
				validate='key', 
				validatecommand=(validationCommand, '%P') )
		self.location.grid( column=0, row=1, columnspan=2, padx=5, pady=pady )
		self.location.bind( "<KeyRelease>", self.initiateSearch )

		ttk.Label( controlPanel, text='Function Name:' ).grid( column=0, row=2, columnspan=2, padx=30, pady=(pady, 0), sticky='w' )
		self.name = Tk.Text( controlPanel, width=40, height=3, state="disabled" )
		self.name.grid( column=0, row=3, columnspan=2, sticky='ew', padx=5, pady=pady )

		ttk.Label( controlPanel, text='DOL Offset:' ).grid( column=0, row=4, padx=5, pady=pady )
		self.dolOffset = Tk.Entry( controlPanel, width=24, borderwidth=0, state="disabled" )
		self.dolOffset.grid( column=1, row=4, sticky='w', padx=(7, 0) )

		ttk.Label( controlPanel, text='RAM Address:' ).grid( column=0, row=5, padx=5, pady=pady )
		self.ramAddr = Tk.Entry( controlPanel, width=24, borderwidth=0, state="disabled" )
		self.ramAddr.grid( column=1, row=5, sticky='w', padx=(7, 0) )

		ttk.Label( controlPanel, text='Length:' ).grid( column=0, row=6, padx=5, pady=pady )
		self.length = Tk.Entry( controlPanel, width=8, borderwidth=0, state="disabled" )
		self.length.grid( column=1, row=6, sticky='w', padx=(7, 0) )

		ttk.Label( controlPanel, text='Includes\nCustom Code:', justify='center' ).grid( column=0, row=7, padx=5, pady=pady )
		self.hasCustomCode = Tk.StringVar()
		ttk.Label( controlPanel, textvariable=self.hasCustomCode ).grid( column=1, row=7, sticky='w', padx=(7, 0) )

		controlPanel.grid( column=0, row=0, rowspan=2, padx=4, sticky='n' )

		ttk.Label( mainFrame, text='Function Code:' ).grid( column=1, row=0, padx=42, pady=2, sticky='ew' )
		self.code = ScrolledText( mainFrame, width=28, state="disabled" )
		self.code.grid( column=1, row=1, rowspan=2, sticky='nsew', padx=(12, 0) )

		mainFrame.pack( expand=True, fill='both' )

		# Configure this window's resize behavior
		mainFrame.columnconfigure( 0, weight=0 )
		mainFrame.columnconfigure( 1, weight=1 )
		mainFrame.rowconfigure( 0, weight=0 )
		mainFrame.rowconfigure( 1, weight=1 )

		# Get and load a DOL file for reference
		if globalData.disc:
			self.dol = globalData.disc.dol
			self.dolIsVanilla = False
			gameId = globalData.disc.gameId
		else:
			# Get the vanilla disc path
			vanillaDiscPath = globalData.getVanillaDiscPath()
			if not vanillaDiscPath: # todo: add warning here
				return
			vanillaDisc = Disc( vanillaDiscPath )
			vanillaDisc.loadGameCubeMediaFile()
			gameId = vanillaDisc.gameId

			self.dol = vanillaDisc.dol
			self.dolIsVanilla = True
		self.dol.load()
		
		# Collect function symbols info from the map file
		symbolMapPath = os.path.join( globalData.paths['maps'], gameId + '.map' )
		with open( symbolMapPath, 'r' ) as mapFile:
			self.symbols = mapFile.read()
		self.symbols = self.symbols.splitlines()

	def updateEntry( self, widget, textInput ):
		widget.configure( state="normal" )
		widget.delete( 0, 'end' )
		widget.insert( 0, textInput )
		widget.configure( state="readonly" )

	def updateScrolledText( self, widget, textInput ):

		""" For Text or ScrolledText widgets. """

		widget.configure( state="normal" )
		widget.delete( 1.0, 'end' )
		widget.insert( 1.0, textInput )
		widget.configure( state="disabled" )

	# def clearControlPanel( self ):
		
	# 	self.dolOffset.configure( state="normal" )
	# 	self.dolOffset.delete( 0, 'end' )
	# 	self.dolOffset.configure( state="readonly" )
	# 	self.ramAddr.configure( state="normal" )
	# 	self.ramAddr.delete( 0, 'end' )
	# 	self.ramAddr.configure( state="readonly" )
	# 	self.length.configure( state="normal" )
	# 	self.length.delete( 0, 'end' )
	# 	self.length.configure( state="readonly" )
		
	def locationUpdated( self, locationString ):

		""" Validates text input into the offset/address entry field, whether entered 
			by the user or programmatically. Ensures there are only hex characters.
			If there are hex characters, this function will deny them from being entered. """

		try:
			if not locationString: # Text erased
				return True

			# Attempt to convert the hex string to decimal
			int( locationString, 16 )

			return True
		except:
			return False

	def initiateSearch( self, event ):

		locationString = self.location.get().strip().lstrip( '0x' )

		# Get both the DOL offset and RAM address
		cancelSearch = False
		try:
			if len( locationString ) == 8 and locationString.startswith( '8' ):
				address = int( locationString, 16 )
				offset = self.dol.offsetInDOL( address )

				if address > self.dol.maxRamAddress:
					cancelSearch = True
			else:
				offset = int( locationString, 16 )
				address = self.dol.offsetInRAM( offset )

				if offset < 0x100:
					cancelSearch = True
		except:
			cancelSearch = True

		if cancelSearch:
			self.updateScrolledText( self.name, '' )
			self.updateScrolledText( self.code, '' )
			self.updateEntry( self.dolOffset, '' )
			self.updateEntry( self.ramAddr, '' )
			self.updateEntry( self.length, '' )
			self.hasCustomCode.set( '' )
			return

		elif offset == -1:
			self.updateScrolledText( self.name, '' )
			self.updateScrolledText( self.code, '{} not found in the DOL'.format(self.location.get().strip()) )
			self.updateEntry( self.dolOffset, '' )
			self.updateEntry( self.ramAddr, '' )
			self.updateEntry( self.length, '' )
			self.hasCustomCode.set( '' )
			return

		# Look up info on this function in the map file
		for i, line in enumerate( self.symbols ):
			line = line.strip()
			if not line or line.startswith( '.' ):
				continue

			# Parse the line (split on only the first 4 instances of a space)
			functionStart, length, _, _, symbolName = line.split( ' ', 4 )
			functionStart = int( functionStart, 16 )
			length = int( length, 16 )

			# Check if this is the target function
			if address >= functionStart and address < functionStart + length:
				dolFunctionStart = self.dol.offsetInDOL( functionStart )
				break

		else: # Above loop didn't break; symbol not found
			self.updateScrolledText( self.name, '' )
			self.updateScrolledText( self.code, 'Unable to find {} in the map file'.format(self.location.get().strip()) )
			self.updateEntry( self.dolOffset, '' )
			self.updateEntry( self.ramAddr, '' )
			self.updateEntry( self.length, '' )
			self.hasCustomCode.set( 'N/A' )
			return

		self.updateScrolledText( self.name, symbolName )
		self.updateEntry( self.dolOffset, uHex(dolFunctionStart) + ' - ' + uHex(dolFunctionStart+length) )
		self.updateEntry( self.ramAddr, uHex(functionStart) + ' - ' + uHex(functionStart+length) )
		self.updateEntry( self.length, uHex(length) )

		# Get the target function as a hex string
		functionCode = self.dol.getData( dolFunctionStart, length )
		hexCode = hexlify( functionCode )
	
		# Disassemble the code into assembly
		asmCode, errors = globalData.codeProcessor.disassemble( hexCode )
		if errors:
			self.updateScrolledText( self.code, 'Disassembly Error:\n\n' + errors )
		else:
			self.updateScrolledText( self.code, asmCode )

		# Update text displaying whether this is purely vanilla code
		if self.dolIsVanilla:
			self.hasCustomCode.set( 'No' )
		else: # todo
			self.hasCustomCode.set( 'Unknown' )


class TriCspCreator( object ):

	def __init__( self ):

		self.config = {}
		self.gimpDir = ''
		self.gimpExe = ''

		# Analyze the version of GIMP installed, and check for needed plugins
		self.determineGimpPath()
		gimpVersion = self.getGimpProgramVersion()
		pluginDir = self.getGimpPluginDirectory( gimpVersion )
		createCspScriptVersion = self.getScriptVersion( pluginDir, 'python-fu-create-tri-csp.py' )
		finishCspScriptVersion = self.getScriptVersion( pluginDir, 'python-fu-finish-csp.py' )
		
		# Print out version info
		print ''
		print '            Version info:'
		print ''
		print '  GIMP:                    ', gimpVersion
		print '  create-tri-csp script:   ', createCspScriptVersion
		print '  finish-csp script:       ', finishCspScriptVersion
		print ''
		print 'GIMP executable directory: ', self.gimpDir
		print 'GIMP Plug-ins directory:   ', pluginDir
		print ''

		# Update installed scripts (then no need to check version)
		# todo

		# Delete old GIMP .pyc plugins (I don't think GIMP will automatically re-build them if the scripts are updated)
		# todo
		
		# Load the CSP Configuration file, and assemble other needed paths
		try:
			self.triCspFolder = globalData.paths['triCsps']
			self.pluginsFolder = os.path.join( self.triCspFolder, 'GIMP plug-ins' )
			configFilePath = os.path.join( self.triCspFolder, 'CSP Configuration.yml' )

			# Read the config file (this method should allow for utf-8 encoding, and preserve comments when saving/dumping back to file)
			with codecs.open( configFilePath, 'r', encoding='utf-8' ) as stream:
				self.config = yaml.load( stream, Loader=yaml.RoundTripLoader )

			self.settingsFiles = [
				os.path.join( self.triCspFolder, 'Debugger.ini' ),
				os.path.join( self.triCspFolder, 'Dolphin.ini' ),
				os.path.join( self.triCspFolder, 'GFX.ini' )
			]
		except IOError: # Couldn't find the configuration file
			msg( "Couldn't find the CSP config file at " + configFilePath, warning=True )
		except Exception as err: # Problem parsing the file
			msg( 'There was an error while parsing the yaml config file:\n\n{}'.format(err) )

	def determineGimpPath( self ):

		""" Determines the absolute file path to the GIMP console executable 
			(the exe filename varies based on program version). """

		dirs = ( "C:\\Program Files\\GIMP 2\\bin", "{}\\Programs\\GIMP 2\\bin".format(os.environ['LOCALAPPDATA']) )
		
		# Check for the GIMP program folder
		for directory in dirs:
			if os.path.exists( directory ):
				break
		else:
			msg( 'GIMP does not appear to be installed; unable to find program folder among these paths:\n\n' + '\n'.join(dirs) )
			self.gimpDir = ''
			self.gimpExe = ''
			return
		
		# Check the files in the program folder for a 'console' executable
		for fileOrFolderName in os.listdir( directory ):
			if fileOrFolderName.startswith( 'gimp-console' ) and fileOrFolderName.endswith( '.exe' ):
				self.gimpDir = directory
				self.gimpExe = fileOrFolderName
				return

		else: # The loop above didn't break; unable to find the exe
			msg( 'Unable to find the GIMP console executable in "{}".'.format(directory) )
			self.gimpDir = ''
			self.gimpExe = ''
			return

	def getGimpProgramVersion( self ):
		_, versionText = cmdChannel( '"{}\{}" --version'.format(self.gimpDir, self.gimpExe) )
		return versionText.split()[-1]
		
	def getGimpPluginDirectory( self, gimpVersion ):

		""" Checks known directory paths for GIMP versions 2.8 and 2.10. If both appear 
			to be installed, we'll check the version of the executable that was found. """

		userFolder = os.path.expanduser( '~' ) # Resolves to "C:\Users\[userName]"
		v8_Path = os.path.join( userFolder, '.gimp-2.8\\plug-ins' )
		v10_Path = os.path.join( userFolder, 'AppData\\Roaming\\GIMP\\2.10\\plug-ins' )

		if os.path.exists( v8_Path ) and os.path.exists( v10_Path ):
			# Both versions seem to be installed. Use Gimp's version to decide which to use
			major, minor, _ = gimpVersion.split( '.' )
			if major != '2':
				return ''
			if minor == '8':
				return v8_Path
			else: # Hoping this path is good for other versions as well
				return v10_Path

		elif os.path.exists( v8_Path ): return v8_Path
		elif os.path.exists( v10_Path ): return v10_Path
		else: return ''

	def getScriptVersion( self, pluginDir, scriptFile ):

		""" Scans the given script (a filename) for a line like "version = 2.2\n" and parses it. """

		scriptPath = os.path.join( pluginDir, scriptFile )

		if os.path.exists( scriptPath ):
			with open( scriptPath, 'r' ) as script:
				for line in script:
					line = line.strip()

					if line.startswith( 'version' ) and '=' in line:
						return line.split( '=' )[-1].strip()
			
		return '-1'

	def createSideImage( self, microMelee, charId, costumeId, charExtension ):

		""" Installs code mods to the given Micro Melee disc image required for capturing CSP images, 
			and then launches Dolphin to collect a screenshot of a specific character costume. """

		# Get target action states and frames for the screenshots
		try:
			characterDict = self.config[charId]
			actionState = characterDict['actionState']
			targetFrame = characterDict['frame']
			faceLeft = characterDict.get( 'faceLeft', False )
			grounded = characterDict.get( 'grounded', False )
			camX = characterDict['camX']
			camY = characterDict['camY']
			camZ = characterDict['camZ']
			targetFrameId = targetFrame >> 16 # Just need the first two bytes of the float for this
		except KeyError as err:
			msg( 'Unable to find CSP "{}" info for character ID 0x{:X} in "CSP Configuration.yml".'.format(err.message, charId), 'CSP Config Error' )
			return ''

		# Replace the character in the Micro Melee disc with the 20XX skin
		origFile = microMelee.files[microMelee.gameId + '/' + microMelee.constructCharFileName(charId, costumeId, 'dat')]
		newFile = globalData.disc.files[globalData.disc.gameId + '/' + globalData.disc.constructCharFileName(charId, costumeId, charExtension)]
		microMelee.replaceFile( origFile, newFile )

		# Copy over Nana too, if ICies are selected
		if charId == 0xE: # Ice Climbers
			colorAbbr = globalData.costumeSlots['Nn'][costumeId]
			origFile = microMelee.files[microMelee.gameId + '/PlNn' + colorAbbr + '.dat' ]
			newFile = globalData.disc.files[globalData.disc.gameId + '/PlNn' + colorAbbr + '.' + charExtension]
			microMelee.replaceFile( origFile, newFile )

		# Parse the Core Codes library for the codes needed for booting to match and setting up a pose
		coreCodes = CodeLibraryParser()
		coreCodesFolder = globalData.paths['coreCodes']
		coreCodes.includePaths = [ os.path.join(coreCodesFolder, '.include'), os.path.join(globalData.scriptHomeFolder, '.include') ]
		coreCodes.processDirectory( coreCodesFolder )
		codesToInstall = []

		# Customize the Asset Test mod to load the chosen characters/costumes
		assetTest = coreCodes.getModByName( 'Asset Test' )
		if not assetTest:
			msg( 'Unable to find the Asset Test mod in the Core Codes library!', warning=True )
			return ''
		assetTest.configure( "Player 1 Character", charId )
		assetTest.configure( "P1 Costume ID", costumeId )
		assetTest.configure( "Player 2 Character", charId )
		assetTest.configure( "P2 Costume ID", costumeId )
		if charId == 0x13: # Special case for Sheik (for different lighting direction)
			assetTest.configure( "Stage", 3 ) # Selecting Pokemon Stadium
		else:
			assetTest.configure( "Stage", 32 ) # Selecting FD
		if faceLeft:
			assetTest.configure( 'P1 Facing Direction', -1 )
			assetTest.configure( 'P2 Facing Direction', -1 )
		else:
			assetTest.configure( 'P1 Facing Direction', 1 )
			assetTest.configure( 'P2 Facing Direction', 1 )
		codesToInstall.append( assetTest )

		# Parse the Pose Codes
		poseCodes = CodeLibraryParser()
		poseCodesFolder = globalData.paths['triCsps']
		poseCodes.includePaths = [ os.path.join(poseCodesFolder, '.include'), os.path.join(globalData.scriptHomeFolder, '.include') ]
		poseCodes.processDirectory( poseCodesFolder )
		
		# Check for a pose code specific to this character in the Pose Codes file
		poseCodeName = globalData.charList[charId] + ' Pose Code'
		poseCode = poseCodes.getModByName( poseCodeName )

		if poseCode:
			codesToInstall.append( poseCode )
		else: # No specific, custom code for this character; use the general approach

		# Configure code for setting the appropriate action state
		# if charId == 1: # DK
		# 	actionStateMod = coreCodes.getModByName( 'DK CSP Double-Jump' )
		# 	if not actionStateMod:
		# 		msg( 'Unable to find the DK CSP Double-Jump mod in the Core Codes library!', warning=True )
		# 		return
		#if charId == 1 or charId == 6: # DK or Link
			# actionStateMod = coreCodes.getModByName( 'Force Jump for CSP' )
			# if not actionStateMod:
			# 	msg( 'Unable to find the Force Jump mod in the Core Codes library!', warning=True )
			# 	return
			# codesToInstall.append( actionStateMod )

			# actionStateMod = coreCodes.getModByName( 'Enter Action State On Match Start' )
			# if not actionStateMod:
			# 	msg( 'Unable to find the Enter Action State On Match Start mod in the Core Codes library!', warning=True )
			# 	return
			# actionStateMod.configure( 'Action State ID', actionState )
			# actionStateMod.configure( 'Start Frame', 0 )

			# codesToInstall.append( coreCodes.getModByName('Zero-G Mode') )
		# else:
			actionStateMod = coreCodes.getModByName( 'Enter Action State On Match Start' )
			if not actionStateMod:
				msg( 'Unable to find the Enter Action State On Match Start mod in the Core Codes library!', warning=True )
				return ''

		# Convert the pose target frame to an int start frame
		# startFrame = struct.unpack( '>f', struct.pack('>I', targetFrame) )[0]
		# if startFrame <= 5:
		# 	startFrame = 0
		# else:
		# 	startFrame = int( startFrame - 5 )
		
			actionStateMod.configure( 'Action State ID', actionState )
			actionStateMod.configure( 'Start Frame', 0 )

			codesToInstall.append( actionStateMod )

			# If the move should be done in the air, apply a code so they hover on spawn
			if grounded:
				# Increase delay to start the move so the characters have time to fall to the ground
				actionStateMod.configure( 'Delay', 102 ) # Default is 72
			else:
				codesToInstall.append( coreCodes.getModByName('Zero-G Mode') )
		
		# Customize Action State Freeze
		actionStateFreeze = coreCodes.getModByName( 'Action State Freeze' )
		if not actionStateFreeze:
			msg( 'Unable to find the Action State Freeze mod in the Core Codes library!', warning=True )
			return ''
		actionStateFreeze.configure( 'Action State ID', actionState )
		actionStateFreeze.configure( 'Frame ID', targetFrameId )
		codesToInstall.append( actionStateFreeze )

		codesToInstall.append( coreCodes.getModByName('Modified Camera Info Flag Initialization') )
		codesToInstall.append( coreCodes.getModByName('Standard Pause Camera in Dev-Mode Match') )
		codesToInstall.append( coreCodes.getModByName('Disable Pause HUD') )

		# Configure the camera
		cameraMod = coreCodes.getModByName( 'CSP Camera' )
		cameraMod.configure( 'X Coord', camX )
		cameraMod.configure( 'Y Coord', camY )
		cameraMod.configure( 'Z Coord', camZ )
		codesToInstall.append( cameraMod )

		# Configure the camera pause time
		pauseMod = coreCodes.getModByName( 'Auto-Pause' )
		pauseMod.configure( 'Target Frame', 252 ) # 72 (to leave entry platform) + 180 (max anim time)
		codesToInstall.append( pauseMod )

		# Shut down all instances of Dolphin to ensure the disc can be saved to
		dc = globalData.dolphinController
		dc.stopAllDolphinInstances()

		# Restore the disc's DOL data to vanilla and then install the necessary codes
		if not microMelee.restoreDol( countAsNewFile=False ):
			return ''
		microMelee.installCodeMods( codesToInstall )
		microMelee.save()

		# Engage emulation
		dc.start( microMelee )

		time.sleep( 5 )
		screenshotPath = dc.getScreenshot( charExtension )

		# Stop emulation
		dc.stop()

		return screenshotPath

	def createTriCsp( self, leftImagePath, centerImagePath, rightImagePath, charConfigDict, outputPath, saveHighRes ):
		
		""" Construct a gimp-script command-line argument and send it to GIMP to create a finished Tri-CSP image.
			The GIMP options used are as follows:
				-d = "--no-data", prevents loading of brushes, gradients, palettes, patterns, ...
				-f = "--no-fonts", prevents loading of fonts
				-i = "--no-interface", prevents loading of main GUI
				-g = "--gimprc", applies setting preferences from a file (must be a full path). In this case, it's just used to prevent exporting a color profile
				-b "" specifies a script-fu command to be run in gimp """

		printStatus( 'Compositing CSP Image...', forceUpdate=True )

		# Assemble needed paths and replace backslashes
		gimpExePath = os.path.join( self.gimpDir, self.gimpExe )
		gimprcPath = os.path.join( self.triCspFolder, 'gimprcTCC' ).replace( '\\', '/' )
		leftImagePath = leftImagePath.replace( '\\', '/' )
		centerImagePath = centerImagePath.replace( '\\', '/' )
		rightImagePath = rightImagePath.replace( '\\', '/' )
		outputPath = outputPath.replace( '\\', '/' )
		
		# Convert the boolean flags to strings
		if charConfigDict['reverseSides']: reverseSidesFlag = '1'
		else: reverseSidesFlag = '0'
		if saveHighRes: saveHighResFlag = '1'
		else: saveHighResFlag = '0'

		# Construct the list of CSP configuration arguments and cast them to a string
		try:
			configArgsList = [
				charConfigDict['threshold'], 
				charConfigDict['centerImageXOffset'], charConfigDict['centerImageYOffset'], charConfigDict['centerImageScaling'], 
				charConfigDict['sideImagesXOffset'], charConfigDict['sideImagesYOffset'], charConfigDict['sideImagesScaling']
			]
		except KeyError as err:
			raise Exception( 'Missing CSP configuration: ' + err.message )
		configurationArgs = [ str(arg) for arg in configArgsList ]

		command = (
			#'start /B /D "{}"'.format( gimpExeFolder ) # Starts a new process. /B prevents creating a new window, and /D sets the working directory
			'"{}" -d -f -i -g "{}"'.format( gimpExePath, gimprcPath ) # Call the gimp executable with the arguments described above
			+ ' -b "(python-fu-create-tri-csp 1' # Extra param, "1", to run in NON-INTERACTIVE mode
			' \\"' + leftImagePath + '\\"'
			' \\"' + centerImagePath + '\\"'
			' \\"' + rightImagePath + '\\"'
			' \\"\\" \\"\\"' # Mask image path & Config file path (not used here)
			' \\"' + outputPath + '\\"'
			#+ ' '.join( configurationArgs ) + ' ' + reverseSidesFlag + ' ' + saveHighResFlag + ' 0)" -b "(gimp-quit 0)"'
			' {} {} {} 0)" -b "(gimp-quit 0)"'.format( ' '.join( configurationArgs ), reverseSidesFlag, saveHighResFlag )
		)

		# Send the command to the Tri-CSP creator script and parse its output
		stderr = cmdChannel( command, returnStderrOnSuccess=True )[1]
		returnCode, errMsg = self.parseScriptOutput( stderr )
		if returnCode != 0:
			msg( 'There was an error in creating the Tri-CSP:\n\n' + errMsg, 'Tri-CSP Creator Error' )
			globalData.gui.updateProgramStatus( 'Error during Tri-CSP creation', error=True )

		return returnCode

	def parseScriptOutput( self, stderr ):

		""" Can't get normal exit/return codes from python-fu scripts, 
			so instead we'll parse custom messages from stderr. """

		for line in stderr.splitlines():
			if line.startswith( 'Create Tri-CSP-Warning: Return Code:' ): # e.g. "Create Tri-CSP-Warning: Return Code: 1: Some error happened"
				returnCode, message = line.split( ':' )[2:]
				return ( int(returnCode), message.strip() )
		else: # The above loop didn't break; Unknown error
			return ( -1, stderr )


class DolphinController( object ):

	""" Wrapper the Dolphin emulator, to handle starting/stopping 
		the game, file I/O, and option configuration. """

	def __init__( self ):
		self._exePath = ''
		self._rootFolder = ''
		self._userFolder = ''
		self.process = None

	@property
	def exePath( self ):

		""" Set up initial filepaths. This should be done just once, on the first path request. 
			This is not done in the init method because program settings were not loaded then. """

		if self._exePath:
			return self._exePath
		
		self._exePath = globalData.getEmulatorPath()
		if not self._exePath:
			self._rootFolder = ''
			self._userFolder = ''
			return ''

		self._rootFolder = os.path.dirname( self._exePath )
		self._userFolder = os.path.join( self._rootFolder, 'User' )

		# Make sure that Dolphin is in 'portable' mode
		portableFile = os.path.join( self._rootFolder, 'portable.txt' )
		if not os.path.exists( portableFile ):
			print 'Dolphin is not in portable mode! Attempting to create portable.txt'
			try:
				with open( portableFile, 'w' ) as newFile:
					pass
			except:
				msg( "Dolphin is not in portable mode, and 'portable.txt' could not be created. Be sure that this program "
					 "has write permissions in the Dolphin root directory.", 'Non-portable Dolphin', globalData.gui.root, warning=True )
				return

		if not os.path.exists( self._userFolder ):
			self.start( '' ) # Will open, create the user folder, and close? todo: needs testing
			# time.sleep( 4 )
			# self.stop()

		return self._exePath

	@property
	def rootFolder( self ):
		if not self._rootFolder:
			self.exePath
		return self._rootFolder

	@property
	def userFolder( self ):
		if not self._userFolder:
			self.exePath
		return self._userFolder

	# @property
	# def screenshotFolder( self ):
	# 	return os.path.join( self.userFolder, 'ScreenShots' )

	@property
	def isRunning( self ):
		if not self.process: # Hasn't been started
			return False

		return ( self.process.poll() == None ) # None means the process is still running; anything else is an exit code

	def getVersion( self ):
		
		if not self.exePath:
			return '' # User may have canceled the prompt

		returnCode, output = cmdChannel( '{} --version'.format(self.exePath) )

		if returnCode == 0:
			return output
		else:
			return 'N/A'

	def backupAndReplaceSettings( self, fileList ):

		""" Backs up current Dolphin settings files, and replaces them with the given files. """

		settingsFolder = os.path.join( self.userFolder, 'Config' )

		for filepath in fileList:
			origFile = os.path.join( settingsFolder, os.path.basename(filepath) )
			# debuggerSettingsFile = os.path.join( settingsFolder, 'Debugger.ini' )
			# dolphinSettingsFile = os.path.join( settingsFolder, 'Dolphin.ini' )
			# gfxSettingsFile = os.path.join( settingsFolder, 'GFX.ini' )
			try:
				# os.rename( debuggerSettingsFile, debuggerSettingsFile + '.bak' )
				# os.rename( dolphinSettingsFile, dolphinSettingsFile + '.bak' )
				os.rename( origFile, origFile + '.bak' )
			except WindowsError: # Likely the backup files already exist
				pass # Keep the old backup files; do not replace

			# Copy over the Dolphin settings files for CSP creation
			# copy( cspCreator.debuggerSettingsFile, debuggerSettingsFile )
			# copy( cspCreator.dolphinSettingsFile, dolphinSettingsFile )
			copy( filepath, origFile )

	def restoreSettings( self, fileList ):
		
		""" Restores Dolphin settings previously backed-up, replacing them with the original files. """

		settingsFolder = os.path.join( self.userFolder, 'Config' )
		
		for filepath in fileList:
			origFile = os.path.join( settingsFolder, os.path.basename(filepath) )
			os.remove( origFile )
			os.rename( origFile + '.bak', origFile )
	
	def start( self, discObj ):

		""" Starts running an instance of Dolphin with the given disc. 
			'--exec' loads the specified file. (Using '--exec' because '/e' is incompatible with Dolphin 5+, while '-e' is incompatible with Dolphin 4.x)
			'--batch' will prevent dolphin from unnecessarily scanning game/ISO directories, and will shut down Dolphin when the game is stopped. """

		if not self.exePath:
			return # User may have canceled the prompt

		# Make sure there are no prior instances of Dolphin running
		self.stopAllDolphinInstances()
		
		printStatus( 'Booting {} in emulator....'.format(discObj.gameId) )

		# Construct the command with the disc filepath and send it to Dolphin
		if globalData.checkSetting( 'runDolphinInDebugMode' ):
			command = '"{}" --debugger --exec="{}"'.format( self.exePath, discObj.filePath )
		else:
			command = '"{}" --batch --exec="{}"'.format( self.exePath, discObj.filePath )
		self.process = subprocess.Popen( command, stderr=subprocess.STDOUT, creationflags=0x08000000 )

	def stop( self ):

		""" Stop an existing Dolphin process that was spawned from this controller. """

		if self.isRunning:
			self.process.terminate()
			time.sleep( 2 )

	def stopAllDolphinInstances( self ):
		self.stop()

		# Check for other running instances of Dolphin
		processFound = False
		for process in psutil.process_iter():
			if process.name() == 'Dolphin.exe':
				process.terminate()
				processFound = True
				printStatus( 'Stopped an older Dolphin process not started by this module' )
		
		if processFound:
			time.sleep( 2 )

	# def getLatestScreenshot( self, gameId ):
	# 	screenshotFolder = os.path.join( self.userFolder, 'ScreenShots', gameId )

	def getSettings( self, settingsDict ):

		""" Read the main Dolphin settings file and graphics settings 
			file to collect and return current settings. """

		# Check the general settings file
		settingsFilePath = os.path.join( self.userFolder, 'Config', 'Dolphin.ini' )
		with open( settingsFilePath, 'r' ) as settingsFile:
			for line in settingsFile.readlines():
				if not '=' in line: continue

				name, value = line.split( '=' )
				name = name.strip()
				value = value.strip()

				if name in settingsDict:
					settingsDict['name'] = value
		
		# Check the general settings file
		settingsFilePath = os.path.join( self.userFolder, 'Config', 'GFX.ini' )
		with open( settingsFilePath, 'r' ) as settingsFile:
			for line in settingsFile.readlines():
				if not '=' in line: continue

				name, value = line.split( '=' )
				name = name.strip()
				value = value.strip()

				if name in settingsDict:
					settingsDict['name'] = value

		return settingsDict
	
	def setSettings( self, settingsDict ):

		""" Open the main Dolphin settings file and graphics settings 
			and change settings to those given. """

		# Read the general settings file
		settingsFilePath = os.path.join( self.userFolder, 'Config', 'Dolphin.ini' )
		with open( settingsFilePath, 'r' ) as settingsFile:
			fileContents = settingsFile.read()
		
		with open( settingsFilePath, 'w' ) as settingsFile:
			for line in fileContents.readlines():
				if not '=' in line: continue

				name, _ = line.split( '=' )
				name = name.strip()

				newValue = settingsDict.get( name )
				if newValue:
					settingsFile.write( '{} = {}'.format(name, newValue) )
				else:
					settingsFile.write( line )
					
		# Read the graphics settings file
		settingsFilePath = os.path.join( self.userFolder, 'Config', 'GFX.ini' )
		with open( settingsFilePath, 'r' ) as settingsFile:
			fileContents = settingsFile.read()
		
		with open( settingsFilePath, 'w' ) as settingsFile:
			for line in fileContents.readlines():
				if not '=' in line: continue

				name, _ = line.split( '=' )
				name = name.strip()

				newValue = settingsDict.get( name )
				if newValue:
					settingsFile.write( '{} = {}'.format(name, newValue) )
				else:
					settingsFile.write( line )

	def getScreenshot( self, charExtension ):

		""" Seeks out the Dolphin rendering window, waits for the game to start, takes
			a screenshot, and then gets/returns the filepath to that screenshot. """

		# Update program status and construct a file save/output path
		if charExtension[0] == 'l':
			side = 'left'
		else:
			side = 'right'
		printStatus( 'Generating {}-side screenshot...'.format(side), forceUpdate=True )
		savePath = os.path.join( globalData.paths['tempFolder'], side + '.png' )

		# Seek out the Dolphin rendering window and wait for the game to pause
		try:
			renderWindow = self.getDolphinRenderWindow()
			windowDeviceContext = win32gui.GetWindowDC( renderWindow )
		except Exception as err:
			printStatus( 'Unable to target the Dolphin render window; {}'.format(err), error=True )
			return ''

		timeout = 30
		bgColor = 0

		print 'Waiting for game start...'
		while bgColor == 0:
			try:
				# Sample a pixel on the other side of the black bar
				bgColor = win32gui.GetPixel( windowDeviceContext, 314, 60 ) # Must measure a ways below the title bar and edge
			except Exception as err:
				# With normal operation, the method may raise an exception 
				# if the window can't be found or is minimized.
				if err.args[0] != 0:
					raise err

			if timeout < 0:
				printStatus( 'Timed out while waiting for the game to start', error=True )
				return ''

			time.sleep( 1 )
			timeout -= 1

		# Start-up detected. The character should be posed, and game paused
		# todo: edit to work on multiple monitors. code here: https://github.com/python-pillow/Pillow/issues/1547
		print 'Game start detected.'
		dimensions = win32gui.GetWindowRect( renderWindow )
		image = ImageGrab.grab( dimensions )
		image.save( savePath )

		# Validate image dimensions
		if image.width != 1920 or image.height != 1080:
			printStatus( 'Invalid dimensions for {}-side screenshot: {}x{}'.format(side, image.width, image.height), error=True )
			return ''

		return savePath

	def _windowEnumsCallback( self, windowId, processList ):

		""" Helper for EnumWindows to search for the Dolphin render window. 
			There will be multiple threads under the current process ID, but 
			it's expected to be the only 'Enabled' window with a parent. """

		processId = win32process.GetWindowThreadProcessId( windowId )[1]

		# Check if this has the target process ID, and is a child (i.e. has a parent)
		if processId == self.process.pid and win32gui.IsWindowEnabled( windowId ):
			# Parse the title to determine if it's the render window
			title = win32gui.GetWindowText( windowId )

			# Parse the title. Will be just "Dolphin" until the game is done booting
			if title == 'Dolphin' or ( 'Dolphin' in title and '|' in title ):
				processList.append( windowId )
				return False
		
		return True

	def getDolphinRenderWindow( self ):

		""" Searches all windows which share the current Dolphin process ID 
			and finds/returns the main render window. """

		if not self.isRunning:
			raise Exception( 'Dolphin is not running.' )

		processList = []
		try:
			win32gui.EnumWindows( self._windowEnumsCallback, processList )
		except Exception as err:
			# With normal operation, the callback will return False
			# and EnumWindows will raise an exception.
			if err.args[0] != 0:
				raise err

		if not processList:
			raise Exception( 'no processes found' )
		elif len( processList ) != 1:
			raise Exception( 'too many processes found' )

		return processList[0]


class SisTextEditor( BasicWindow ):

	""" Tool window to view and edit pre-made game text in Sd___.dat files. """

	def __init__( self, sisFile ):
		BasicWindow.__init__( self, globalData.gui.root, 'SIS Text Editor', resizable=True, topMost=False, minsize=(380, 350) )

		self.sisFile = sisFile

		# Get pointers for the text structures
		sisFile.initialize()
		self.sisTable = sisFile.initGenericStruct( 0, structDepth=(3, 0), asPointerTable=True )
		sisTablePointers = self.sisTable.getValues()

		# Add header string and a spacer
		totalTextStructs = len( sisTablePointers ) - 2 # Skip first two structures
		symbol = ', '.join( [node[1] for node in sisFile.rootNodes] ).encode( 'utf8' )
		header = '\t\tEditing {}\n\t\tTotal Strings:  {}\n\t\tRoot Symbol:    {}\n\n      SIS Index:     Offset:'.format( self.sisFile.filename, totalTextStructs, symbol )
		ttk.Label( self.window, text=header ).grid( column=0, row=0, sticky='w', pady=(10, 4) )
		ttk.Separator( self.window ).grid( column=0, row=1, sticky='ew', padx=20 )

		# Build the main window interface
		mainFrame = VerticalScrolledFrame( self.window )

		for sisIndex in range( 2, len(sisTablePointers[:500]) ):

			frame = ttk.Frame( mainFrame.interior )

			# Line number and file offset
			structOffset = sisTablePointers[sisIndex] + 0x20
			label = ttk.Label( frame, text='{}              0x{:X}'.format(sisIndex, structOffset) )
			label.pack( side='left' )

			# Text string
			text = sisFile.getText( sisIndex )
			label = ttk.Label( frame, text=text )
			label.pack( side='left', padx=25 )

			# Edit button
			editButton = LabelButton( frame, 'editButton', self.editText )
			editButton.sisIndex = sisIndex
			editButton.origText = text
			editButton.label = label
			editButton.pack( side='right', pady=6 )

			frame.pack( fill='x', expand=True, padx=40, ipadx=40 )

		mainFrame.grid( column=0, row=2, sticky='nsew' )

		# Display Next/Previous buttons if there are too many to display
		if totalTextStructs > 500:
			ttk.Label( self.window, text='Too many text structs to display!' ).grid( column=0, row=3, sticky='ew', padx=(20, 80) ) #todo

		# Configure space-fill and resize behavior
		self.window.columnconfigure( 'all', weight=1 )
		self.window.rowconfigure( 0, weight=0 )
		self.window.rowconfigure( 1, weight=0 )
		self.window.rowconfigure( 2, weight=1 )
		self.window.rowconfigure( 3, weight=0 )

	def editText( self, event ):

		""" Prompts the user to enter a new string, and updates it in the SIS file. """

		buttonWidget = event.widget
		newText = getNewNameFromUser( 1000, None, 'Enter new text:', buttonWidget.origText )

		if newText and newText != buttonWidget.origText:
			endBytes = self.determineEndBytes( buttonWidget.sisIndex )
			description = 'Text string in {} (SIS ID {}) changed to {}'.format( self.sisFile.filename, buttonWidget.sisIndex, newText )
			self.sisFile.setText( buttonWidget.sisIndex, newText, description, endBytes )

			# Update the label in this window showing the edited text
			buttonWidget.label['text'] = newText

	def determineEndBytes( self, sisIndex ):

		""" Rudimentary method to attempt to determine what end bytes should follow the string. 
			Only considered text opcodes that precede the text. If you want to add start/end 
			tags/opcodes mid-string, you'll have to do it manually for now. (Increase the text 
			string data space by renaming to a longer-than needed string beforehand.) """

		textStruct = self.sisFile.getTextStruct( sisIndex )
		
		# Parse the text struct's data for the text string
		endBytes = bytearray( 1 ) # Starts with 1 null byte
		byte = textStruct.data[0]
		position = 0
		while byte: # Breaks on byte value of 0, or no byte remaining
			if byte == 0x5: # Text Pause; the next short is for this opCode
				position += 3
			elif byte == 0x6: # Fade-in; the next 2 shorts are for this opCode
				position += 5
			elif byte == 0x7: # Offset; the next 2 shorts are for this opCode
				position += 5
			elif byte == 0xA: # Kerning (was SCALING); the next 2 shorts are for this opCode
				position += 5
				endBytes.insert( 0, 0x0B )
			elif byte == 0xC: # Color; the next 3 bytes are for this opCode
				position += 4
				endBytes.insert( 0, 0x0D )
			elif byte == 0xE: # Scaling (was SET_TEXTBOX); the next 2 shorts are for this opCode
				position += 5
				endBytes.insert( 0, 0x0F )
			# elif byte == 0x10: # Centered. Does not seem to be complimented by RESET_CENTERED
			# 	position += 1
			elif byte == 0x12: # Left align
				position += 1
				endBytes.insert( 0, 0x13 )
			elif byte == 0x14: # Right align
				position += 1
				endBytes.insert( 0, 0x15 )
			# elif byte == 0x16: # Kerning
			# 	position += 1
			# 	endBytes.insert( 0, 0x17 )
			elif byte == 0x18: # Fitting
				position += 1
				endBytes.insert( 0, 0x19 )
			elif byte == 0x20: # Regular characters (from DOL)
				position += 2
				break
			elif byte == 0x40: # Special characters (from this file)
				position += 2
				break
			else:
				position += 1
			
			byte = textStruct.data[position]

		return endBytes