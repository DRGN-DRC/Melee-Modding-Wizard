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

import os
import ttk
import time
import tkFileDialog
import Tkinter as Tk
from PIL import Image, ImageTk

import globalData
import FileSystem

from ScrolledText import ScrolledText
from basicFunctions import uHex, humansize, msg, getFileMd5


def getWindowGeometry( topLevelWindow ):

	""" Analyzes a Tkinter.Toplevel window to get size and location info, relative to the screen.
		Returns a tuple of ( width, height, distanceFromScreenLeft, distanceFromScreenTop ) """

	try:
		dimensions, topDistance, leftDistance = topLevelWindow.geometry().split( '+' )
		width, height = dimensions.split( 'x' )
		geometry = ( int(width), int(height), int(topDistance), int(leftDistance) )
	except:
		raise ValueError( "Failed to parse window geometry string: " + topLevelWindow.geometry() )

	return geometry


def getColoredShape( imageName, color, getAsPilImage=False, subFolder='' ):

	""" Returns an image of a shape/insignia/design, recolored to the given color. 
		'imageName' should be an image within the "imgs" folder (without extension). 
		The image should be an 8-bit grayscale image (single-channel with no alpha; 
		"8bpc GRAYA" in GIMP). 'color' may be an RGBA tuple, or a common color name 
		string (e.g. 'blue'). 'getAsPilImage' can be set to True if the user would 
		like to get the PIL image instead. """

	# Build the file path
	if subFolder:
		lowerParts = subFolder.split( '/' )
		lowerParts.append( imageName + ".png" )
		imagePath = os.path.join( globalData.paths['imagesFolder'], *lowerParts )
	else:
		imagePath = os.path.join( globalData.paths['imagesFolder'], imageName + ".png" )

	# Open the image as a PIL image object
	shapeMask = Image.open( imagePath )
	if shapeMask.mode != 'L': # These should be pre-converted for better prformance and less storage space
		print( 'Warning: {} is not stored as a single-channel greyscale image (no alpha).'.format(imageName) )
		shapeMask = shapeMask.convert( 'L' )

	# Color the image
	blankImage = Image.new( 'RGBA', shapeMask.size, (0, 0, 0, 0) )
	colorScreen = Image.new( 'RGBA', shapeMask.size, color )
	finishedShape = Image.composite( blankImage, colorScreen, shapeMask )

	if getAsPilImage:
		return finishedShape
	else:
		return ImageTk.PhotoImage( finishedShape )


def exportSingleFileWithGui( fileObj ):

	""" Exports a single file, while prompting the user on where they'd like to save it. 
		Updates the default directory to search in when opening or exporting files. 
		Also handles updating the GUI with the operation's success/failure status. """
	
	# Prompt for a place to save the file.
	fileExt = fileObj.ext[1:] # Removing dot
	savePath = tkFileDialog.asksaveasfilename(
		title="Where would you like to export the file?",
		parent=globalData.gui.root,
		initialdir=globalData.getLastUsedDir(),
		initialfile=fileObj.filename,
		defaultextension=fileExt,
		filetypes=[( fileExt.upper() + " files", '*.' + fileExt.lower() ), ( "All files", "*.*" )] )

	# The above will return an empty string if the user canceled
	if not savePath:
		globalData.gui.updateProgramStatus( 'Operation canceled' )
		return ''

	# Write the file to an external/standalone file
	successful = fileObj.export( savePath )

	# Update the default directory to start in when opening or exporting files
	globalData.setLastUsedDir( savePath, 'auto' )

	if successful:
		globalData.gui.updateProgramStatus( 'File exported successfully.', success=True )
		globalData.gui.playSound( 'menuChange' )
		return savePath
	else:
		globalData.gui.updateProgramStatus( 'Unable to export. Check the error log file for details.', error=True )
		return ''


def importGameFiles( fileExt='', multiple=False, title='', fileTypeOptions=None, category='default' ):

	""" Prompts the user to choose one or more external/standalone files to import. 
		If fileExt is provided, it should be a 3 character file type string (with "." included); 
		it will be used to prioritize (make default) that set of file types among the file type 
		options shown to the user. If fileTypeOptions is provided, it should be a list of tuples, 
		with each tuple of the form (description, fileTypes), as shown with the default list below. """

	# Based on the extension above, set the default filetypes to choose from in the dialog box (the filetype dropdown)
	if not fileTypeOptions:
		fileTypeOptions = [ ('Model/Texture data files', '*.dat *.usd *.lat *.rat'), ('Audio files', '*.hps *.ssm'),
							('System files', '*.bin *.ldr *.dol *.toc'), ('Video files', '*.mth *.thp'), ('All files', '*.*') ]

	# If a file extension was provided, prepend the file type options with it (with a description of "Same type")
	if fileExt:
		# Check if the given file extension exists in the file type options list, and remove it if it is
		for i, (description, fileTypes) in enumerate( fileTypeOptions ):
			extensions = fileTypes.split()
			
			if '*' + fileExt in extensions or ( description == 'Model/Texture data files' and fileExt[-2:] == 'at' ):
				orderedFileTypes = [ (description, fileTypes) ]
				del fileTypeOptions[i]
				break
		else: # Loop above didn't break; the given file extension wasn't found
			orderedFileTypes = [ ('Same type', '*'+fileExt) ]

		# Populate the rest of the possible types to choose from in the dialog box (the filetype dropdown)
		for typeTuple in fileTypeOptions:
			orderedFileTypes.append( typeTuple )
	else:
		orderedFileTypes = fileTypeOptions

	# Set a title if one was not provided
	if not title:
		if multiple:
			title = 'Choose one or more game files to import'
		else:
			title = "Choose a game file to import"

	# Prompt the user to choose a file to import
	defaultDir = globalData.getLastUsedDir( category, fileExt )
	filePaths = tkFileDialog.askopenfilename(
		title=title,
		multiple=multiple,
		initialdir=defaultDir,
		filetypes=orderedFileTypes ) # Should include the appropriate default file types first

	# Update the default directory to start in when importing or exporting files
	if filePaths:
		if multiple: # filePaths will be a tuple
			newDir = os.path.dirname( filePaths[0] )
		else: # filepaths will be a unicode string
			newDir = os.path.dirname( filePaths )

		if newDir != defaultDir: # Update and save the new directory if it's different
			globalData.setLastUsedDir( newDir, category, fileExt )

	else: # The above will return an empty string if the user canceled
		globalData.gui.updateProgramStatus( 'Operation canceled' )

	return filePaths


def importSingleFileWithGui( origFileObj, validate=True ):

	""" Prompts the user to choose an external/standalone file to import, and then 
		replaces the given file in the disc with the chosen file. 
		Updates the default directory to search in when opening or exporting files. 
		Also handles updating the GUI with the operation's success/failure status. 
		Returns True/False on success. """

	newFilePath = importGameFiles( origFileObj.ext )

	# The above will return an empty string if the user canceled
	if not newFilePath: return False

	# Load the new file
	try:
		newFileObj = FileSystem.fileFactory( None, -1, -1, origFileObj.isoPath, extPath=newFilePath, source='file' )
		newFileObj.getData()
	except Exception as err:
		print( 'Exception during file import; {}'.format(err) )
		globalData.gui.updateProgramStatus( 'Unable to replace the file; ' + str(err), error=True )
		return False

	# Check that this is an appropriate replacement file
	if validate:
		if not FileSystem.isValidReplacement( origFileObj, newFileObj ): # Will provide user feedback if untrue
			globalData.gui.updateProgramStatus( 'Invalid file replacement. Operation canceled', warning=True )
			return False

	# Replace the file and update the program status bar
	globalData.disc.replaceFile( origFileObj, newFileObj )
	globalData.gui.updateProgramStatus( 'File Replaced. Awaiting Save' )

	# Color the file in the Disc File Tree if that tab is open
	if globalData.gui.discTab:
		globalData.gui.discTab.isoFileTree.item( newFileObj.isoPath, tags='changed' )

	return True


def importSingleTexture( title='Choose a texture file to import' ):

	# Prompt to select the file to import
	imagePath = tkFileDialog.askopenfilename( # Will return a unicode string (if one file selected), or a tuple
		title=title,
		parent=globalData.gui.root,
		initialdir=globalData.getLastUsedDir( 'dat' ), # Going to assume these files are with a DAT recently worked with
		filetypes=[ ('PNG files', '*.png'), ('TPL files', '*.tpl'), ('All files', '*.*') ],
		multiple=False
		)

	# The above will return an empty string if the user canceled
	if not imagePath:
		# Update the default directory to start in when opening or exporting files
		globalData.setLastUsedDir( imagePath, 'dat' )

	return imagePath


def checkTextLen( text, isMenuText ):

	""" Counts string character length, but counts whitespace for menu text as half a character
		since those takes up half as many bytes as normal menu text characters. """

	if isMenuText:
		# Count the number of whitespace characters (space or linebreak)
		normalChars = len( text )
		whiteChars = len( text.split() ) - 1

		# Count spaces as half a character count
		return normalChars + ( whiteChars / 2.0 )
	else:
		return len( text )


def getNewNameFromUser( charLimit, excludeChars=None, message='Enter a new name:', defaultText='', width=40, isMenuText=False, title='' ):

	""" Creates a basic pop-up window with a text input field to get a name from the user, and
		performs validation on it before allowing the user to continue. """

	nameChecksOut = False
	if not excludeChars:
		excludeChars = ( '\n', '\t', ':', '\\', '/' )

	while not nameChecksOut:
		popupWindow = PopupEntryWindow( globalData.gui.root, message, defaultText, title, width, charLimit=charLimit, isMenuText=isMenuText )
		newName = popupWindow.entryText.replace( '"', '' ).strip()

		if newName == '': break

		# Validate the name length
		if checkTextLen( newName, isMenuText ) > charLimit:
			msg( 'Please specify a name less than {} characters in length.'.format(charLimit) )
			continue
		
		# Exclude some special characters
		for char in excludeChars:
			if char in newName:
				msg( 'Invalid character(s) detected; the name may not include any of these: ' + ', '.join(excludeChars) )
				break # Breaks this loop, but not the while loop
		else: # The above loop didn't break (meaning an invalid character wasn't found)
			# Convert the name to bytes and validate the length (char length may differ for special characters?)
			try:
				nameBytes = bytearray( newName, encoding='utf-8' )

				if isMenuText and checkTextLen( newName, True ) <= charLimit:
					nameChecksOut = True
				elif len( nameBytes ) <= charLimit:
					nameChecksOut = True
				else:
					msg( 'This name must fit into the space of {} bytes. Try shortening the name.'.format(charLimit) )
			except Exception as err:
				msg( 'Unable to encode the new name into {} bytes; {}.\n\nThere may be an invalid character.'.format(charLimit, err) )

	return newName


class BasicWindow( object ):

	""" Basic user window setup. Provides a title, a window with small border framing, size/position 
		configuration, a window frame widget for attaching contents to, and a built-in close method. 

			'dimensions' are window dimentions, which can be supplied as a tuple of (width, height)
			'offsets' relate to window spawning position, which is relative to the main program window,
				and can be supplied as a tuple of (leftOffset, topOffset). 
			'unique' = True forces only one instance of the window to exist. If subsequent calls are
				made to create the window while it already exists, the existing window will be shown. """

	def __init__( self, topLevel, windowTitle='', dimensions='auto', offsets='auto', resizable=False, topMost=True, minsize=(-1, -1), unique=False ):

		# If utilized, unique windows will be referenceable in a dictionary on the topLevel window
		self.uniqueWindowName = self.__class__.__name__ + windowTitle
		if unique:
			assert topLevel, 'Only windows with a parent may be unique!'

			# Bring into view an existing instance of this window, if already present
			if hasattr( topLevel, 'uniqueWindows' ):
				existingWindow = topLevel.uniqueWindows.get( self.uniqueWindowName )
				if existingWindow:
					try:
						# The window already exist. Make sure it's not minimized, and bring it to the foreground
						existingWindow.window.deiconify()
						existingWindow.window.lift()
						return False # Can use this to determine whether child classes using 'unique' should continue with their init method
					except: # Failsafe against bad window name (existing window somehow destroyed without proper clean-up); move on to create new instance
						topLevel.uniqueWindows[self.uniqueWindowName] = None
			else:
				topLevel.uniqueWindows = {}
		
		# No existing window to bring forward; create a new instance
		self.window = Tk.Toplevel( topLevel )
		self.window.title( windowTitle )
		self.window.attributes( '-toolwindow', 1 ) # Makes window framing small, like a toolbox/widget.
		self.window.resizable( width=resizable, height=resizable )
		if topMost:
			self.window.wm_attributes( '-topmost', 1 )

		rootDistanceFromScreenLeft, rootDistanceFromScreenTop = getWindowGeometry( topLevel )[2:]

		# Set the spawning position of the new window (usually such that it's over the program)
		if offsets == 'auto':
			topOffset = rootDistanceFromScreenTop + 180
			leftOffset = rootDistanceFromScreenLeft + 180
		else:
			leftOffset, topOffset = offsets
			topOffset += rootDistanceFromScreenTop
			leftOffset += rootDistanceFromScreenLeft

		# Set/apply the window width/height
		if dimensions == 'auto':
			self.window.geometry( '+{}+{}'.format(leftOffset, topOffset) )
		else:
			width, height = dimensions
			self.window.geometry( '{}x{}+{}+{}'.format(width, height, leftOffset, topOffset) )
		self.window.focus()

		# Apply minimum window sizes, if provided
		if minsize[0] != -1:
			self.window.minsize( width=minsize[0], height=minsize[1] )

		# Override the 'X' close button functionality (cancel methods should also call close when they're done)
		cancelMethod = getattr( self, "cancel", None )
		if cancelMethod and callable( cancelMethod ):
			self.window.protocol( 'WM_DELETE_WINDOW', self.cancel )
		else:
			self.window.protocol( 'WM_DELETE_WINDOW', self.close )
		
		if unique:
			topLevel.uniqueWindows[self.uniqueWindowName] = self

		return True

	def close( self ):
		# Delete reference to this window if it's meant to be a unique instance, and then destroy the window
		topLevel = self.window.master
		if hasattr( topLevel, 'uniqueWindows' ):
			topLevel.uniqueWindows[self.uniqueWindowName] = None
		self.window.destroy()


class CharacterChooser( BasicWindow ):

	""" Prompts the user to choose a character. This references external character ID and 
		costume ID, which will be stored to "self.charId" and "self.costumeId", respectively. 
		This window will block the main interface until a selection is made. """

	def __init__( self, message='', includeSpecialCharacters=False, combineZeldaSheik=False ):

		BasicWindow.__init__( self, globalData.gui.root, 'Select a Character', offsets=(300, 300) )
		
		self.emptySelection = '- - -'
		self.charId = -1
		self.costumeId = -1

		if message: # Optional user message
			ttk.Label( self.window, text=message, wraplength=500 ).pack( padx=14, pady=(6, 0) )

		# Build the initial list to appear in the dropdown
		if includeSpecialCharacters:
			charList = globalData.charList
		else:
			charList = globalData.charList[:0x1A]

		if combineZeldaSheik:
			charList = charList[:0x12] + ['Zelda/Sheik'] + charList[0x14:]
		
		charChoice = Tk.StringVar()
		charDropdown = ttk.OptionMenu( self.window, charChoice, self.emptySelection, *charList, command=self.characterSelected )
		charDropdown.pack( padx=14, pady=(4, 0) )
		
		colorChoice = Tk.StringVar()
		self.colorDropdown = ttk.OptionMenu( self.window, colorChoice, self.emptySelection, self.emptySelection, command=self.colorSelected )
		self.colorDropdown.pack( padx=14, pady=(4, 0) )
		
		buttonFrame = ttk.Frame( self.window )
		ttk.Button( buttonFrame, text='Confirm', command=self.close ).grid( column=0, row=0, padx=6 )
		ttk.Button( buttonFrame, text='Cancel', command=self.cancel ).grid( column=1, row=0, padx=6 )
		buttonFrame.pack( pady=(4, 6) )

		# Make this window modal (will not allow the user to interact with main GUI until this is closed)
		self.window.grab_set()
		globalData.gui.root.wait_window( self.window )

	def characterSelected( self, selectedOption ):

		""" Called when the user changes the current selection. Sets the currently 
			selected character ID, and populates the costume color drop-down. """

		if selectedOption == 'Zelda/Sheik':
			self.charId = 0x13
		else:
			self.charId = globalData.charList.index( selectedOption )

		# Get the character and costume color abbreviations for the chosen character
		charAbbreviation = globalData.charAbbrList[self.charId]
		costumeOptions = globalData.costumeSlots[charAbbreviation]

		# Format the color options with human-readable names
		costumeOptions = [ '{}  ({})'.format(abbr, globalData.charColorLookup.get(abbr, 'N/A')) for abbr in costumeOptions ]

		# Populate the costume color chooser, and set a default option
		self.colorDropdown['state'] = 'normal'
		self.colorDropdown.set_menu( costumeOptions[0], *costumeOptions ) # Using * to expand the list into the arguments input
		self.costumeId = 0 # For Neutral/Nr

	def colorSelected( self, selectedOption ):

		""" Called when the user changes the current selection. Sets the currently 
			selected character ID, and populates the costume color drop-down. """

		if self.charId == -1: return # No character selected

		# Get the character and costume color abbreviations for the chosen character
		charAbbreviation = globalData.charAbbrList[self.charId]
		costumeOptions = globalData.costumeSlots[charAbbreviation]

		self.costumeId = costumeOptions.index( selectedOption.split()[0] )

	def cancel( self ):
		self.charId = -1
		self.costumeId = -1
		self.close()


def cmsg( message, title='', align='center', buttons=None, makeModal=False ):

	""" Simple helper function to display a small, windowed message to the user, with text that can be selected/copied. 
		This will instead print out to console if the GUI has not been initialized. 

		Alignment may be left/center/right. Buttons may be a list of (buttonText, buttonCommand) tuples. 
		If modal, the window will take program focus and not allow it to be returned until the window is closed. """
	
	if globalData.gui:
		CopyableMessageWindow( globalData.gui.root, message, title, align, buttons, makeModal )
	else:
		if title:
			print( '\t' + title + ':' )
		print( message )


class CopyableMessageWindow( BasicWindow ):

	""" Creates a modeless (non-modal) message window that allows the user to copy the presented text. 

		Alignment may be left/center/right. Buttons may be a list of (buttonText, buttonCommand) tuples. 
		If modal, the window will take program focus and not allow it to be returned until the window is closed. """

	def __init__( self, topLevel, message, title='', align='center', buttons=None, makeModal=False ):
		self.guiRoot = topLevel

		BasicWindow.__init__( self, topLevel, title, resizable=True, topMost=False )

		linesInMessage = len( message.splitlines() )
		if linesInMessage > 17: height = 22
		else: height = linesInMessage + 5

		self.messageText = ScrolledText( self.window, relief='groove', wrap='word', height=height )
		self.messageText.insert( '1.0', '\n' + message )
		self.messageText.tag_add( 'All', '1.0', 'end' )
		self.messageText.tag_config( 'All', justify=align )
		self.messageText.pack( fill='both', expand=1 )

		# Add the buttons
		self.buttonsFrame = Tk.Frame(self.window)
		ttk.Button( self.buttonsFrame, text='Close', command=self.close ).pack( side='right', padx=5 )
		if buttons:
			for buttonText, buttonCommand in buttons:
				ttk.Button( self.buttonsFrame, text=buttonText, command=buttonCommand ).pack( side='right', padx=5 )
		ttk.Button( self.buttonsFrame, text='Copy text to Clipboard', command=self.copyText ).pack( side='right', padx=5 )
		self.buttonsFrame.pack( pady=3 )

		if makeModal:
			self.window.grab_set()
			self.guiRoot.wait_window( self.window )

	# Button functions
	def copyText( self ):
		self.guiRoot.clipboard_clear()
		self.guiRoot.clipboard_append( self.messageText.get('1.0', 'end').strip() )


class PopupEntryWindow( BasicWindow ):

	""" Provides a very basic window for just text entry, with Ok/Cancel buttons. 
		The 'validatePath' option, if True, will warn the user if they've entered 
		an invalid file or folder path, and give them a chance to re-enter it. """

	def __init__( self, master, message='', defaultText='', title='', width=100, wraplength=470, makeModal=True, validatePath=False, charLimit=-1, isMenuText=False ):
		BasicWindow.__init__( self, master, title )

		self.entryText = ''
		self.wraplength = wraplength
		self.resultLabel = None
		self.validatePath = validatePath
		self.charLimit = charLimit
		self.isMenuText = isMenuText

		# Display a user message
		self.label = ttk.Label( self.window, text=message, wraplength=wraplength )
		self.label.pack( pady=8 )

		# Add the Entry widget for user input
		if charLimit == -1:
			self.entry = ttk.Entry( self.window, width=width, justify='center' )
			self.entry.pack( padx=8 )
		else: # Also add a label widget to display number of characters entered/remaining
			entryFrame = ttk.Frame( self.window )
			validationCommand = globalData.gui.root.register( self.entryModified )
			self.entry = ttk.Entry( entryFrame, width=width, justify='center', validate='key', validatecommand=(validationCommand, '%P') )
			self.entry.grid( column=1, row=0, padx=(6, 0), pady=4 )
			self.charLimitLabel = ttk.Label( entryFrame )
			self.charLimitLabel.grid( column=2, row=0, padx=6, pady=4 )
			entryFrame.pack( pady=8 )
		self.entry.insert( 'end', defaultText )
		self.entry.bind( '<Return>', self.cleanup )

		# Add the buttons
		buttonsFrame = ttk.Frame( self.window )
		self.okButton = ttk.Button( buttonsFrame, text='Ok', command=self.cleanup )
		self.okButton.pack( side='left', padx=10 )
		ttk.Button( buttonsFrame, text='Cancel', command=self.cancel ).pack( side='left', padx=10 )
		self.window.protocol( 'WM_DELETE_WINDOW', self.cancel ) # Overrides the 'X' close button.
		buttonsFrame.pack( pady=8 )

		# Move focus to this window (for keyboard control), and pause execution of the calling function until this window is closed.
		self.entry.focus_set()
		if makeModal:
			self.window.grab_set()
			master.wait_window( self.window ) # Pauses execution of the calling function until this window is closed.

	def showResult( self, resultText, fontColor ):

		""" Useful for validation messages. Adds a new label below the text entry widget to display a message. """

		if not self.resultLabel:
			self.resultLabel = ttk.Label( self.window, text=resultText, wraplength=self.wraplength, foreground=fontColor, justify='center' )
			self.resultLabel.pack( pady=(0, 8) )
		else:
			self.resultLabel.configure( text=resultText, foreground=fontColor )

	def entryModified( self, newString ):

		""" Updates the character count for the string in the entry field. 
			Must return True to validate the entered text and allow it to be displayed. """

		newStrLen = checkTextLen( newString, self.isMenuText )
		self.charLimitLabel['text'] = '{}/{}'.format( newStrLen, self.charLimit )

		if newStrLen > self.charLimit:
			self.charLimitLabel['foreground'] = '#a34343' # red
		else:
			self.charLimitLabel['foreground'] = '#292' # green

		return True

	def cleanup( self, event='' ):
		self.entryText = self.entry.get()

		if self.validatePath:
			if not os.path.exists( self.entryText.replace('"', '') ):
				self.showResult( "This path doesn't seem to exist!\nPlease check the path and try again.", 'red' )
				self.entryText = ''
				return

		self.close()

	def cancel( self, event='' ):
		self.entryText = ''
		self.close()


class PopupScrolledTextWindow( BasicWindow ):

	""" Creates a modal dialog window with only a multi-line text input box (with scrollbar), and a few buttons.
		Useful for displaying text that the user should be able to select/copy, or for input. """

	def __init__( self, master, message='', defaultText='', title='', width=100, height=8, button1Text='Ok' ):
		BasicWindow.__init__( self, master, windowTitle=title )
		self.entryText = ''

		# Add the explanation text and text input field
		self.label = ttk.Label( self.window, text=message )
		self.label.pack( pady=5 )
		self.entry = ScrolledText( self.window, width=width, height=height )
		self.entry.insert( 'end', defaultText )
		self.entry.pack( padx=5 )

		# Add the confirm/cancel buttons
		buttonsFrame = ttk.Frame( self.window )
		self.okButton = ttk.Button( buttonsFrame, text=button1Text, command=self.cleanup )
		self.okButton.pack( side='left', padx=10 )
		ttk.Button( buttonsFrame, text='Cancel', command=self.cancel ).pack( side='left', padx=10 )
		buttonsFrame.pack( pady=5 )

		# Move focus to this window (for keyboard control), and pause execution of the calling function until this window is closed.
		self.entry.focus_set()
		master.wait_window( self.window ) # Pauses execution of the calling function until this window is closed.

	def cleanup( self, event='' ):
		self.entryText = self.entry.get( '1.0', 'end' ).strip()
		self.window.destroy()

	def cancel( self, event='' ):
		self.entryText = ''
		self.window.destroy()


class VanillaDiscEntry( PopupEntryWindow ):

	""" Provides a basic window specifically for entering a path to a vanilla game disc. 
		Once a path is given it's compared to known MD5 hases to validate it. """

	# MD5 ISO hashes by revision
	ntsc102 = '0e63d4223b01d9aba596259dc155a174'
	ntsc101 = '67136bd167b471e0ad72e98d10cf4356'
	ntsc100 = '3a62f8d10fd210d4928ad37e3816e33c'
	pal100 = 'fde4587067a6775e600a965322563b82'

	def __init__( self, *args, **kwargs ):
		# Set up the main window
		super( VanillaDiscEntry, self ).__init__( *args, makeModal=False, **kwargs )

		# Change the function to be called when hitting Enter in the text field or clicking "OK"
		self.entry.bind( '<Return>', self.validate )
		self.okButton.configure( command=self.validate )

		self.resultLabel = None
		self.window.grab_set()
		self.window.master.wait_window( self.window ) # Pauses execution of the calling function until this window is closed.
	
	def validate( self, event='' ):

		""" Make sure the given path is good (file exists), 
			and that it's to a vanilla NTSC 1.02 game disc. """

		# Prevent this from being called again while this is executing
		self.entry['state'] = 'disabled'
		self.entry.unbind( '<Return>' )

		givenPath = self.entry.get().replace('"', '')
		md5Hash = ''

		try:
			self.showResult( 'Validating disc. This may take a few moments....', 'black' )
			self.resultLabel.update() # Refresh GUI so this is shown before below line is reached
			md5Hash = getFileMd5( givenPath )
		except IOError:
			if os.path.exists( givenPath ):
				result = 'Unable to read the given file.'
			else:
				result = 'Unable to find the given file.'
		except Exception as err:
			result = 'Error;' + str(err)

		if not md5Hash:
			self.showResult( result, 'red' )

		elif md5Hash == self.ntsc102: # Success!
			self.showResult( 'This disc checks out!', '#292' )
			self.resultLabel.update() # Refresh GUI so this is shown before below line is reached
			time.sleep( 3 ) # Give the user a few seconds to read the above message (if they don't that's fine; carry on)
			self.cleanup() # Store the above path and close this window
			return

		# Check for other known vanilla discs
		elif md5Hash == self.ntsc101:
			self.showResult( 'Invalid revision; this appears to be an NTSC 1.01 disc.', 'red' )
		elif md5Hash == self.ntsc100:
			self.showResult( 'Invalid revision; this appears to be an NTSC 1.00 disc.', 'red' )
		elif md5Hash == self.pal100:
			self.showResult( 'Invalid revision; this appears to be a PAL 1.00 disc.', 'red' )
		else:
			self.showResult( "Invalid disc; the hash is not recognized as an NTSC 1.02 disc.", 'red' )
		
		self.entry['state'] = 'normal'
		self.entry.bind( '<Return>', self.validate )


class HexEditEntry( Tk.Entry ):

	""" Used for struct hex and value display and editing. 
		"dataOffsets" will typically be a single int value, but can be a list of offsets. """

	def __init__( self, parent, dataOffsets=None, byteLength=-1, formatting='', updateName='' ):
		Tk.Entry.__init__( self, parent,
			width=byteLength*2+2, 
			justify='center', 
			relief='flat', 
			highlightbackground='#b7becc', 	# Border color when not focused
			borderwidth=1, 
			highlightthickness=1, 
			highlightcolor='#0099f0' )

		self.offsets	= dataOffsets		# May be a single file offset (int), or a list of them
		self.byteLength = byteLength
		self.formatting = formatting
		self.updateName = updateName


class SliderAndEntry( ttk.Frame ):

	def __init__( self, parent, *args, **kwargs ):
		ttk.Frame.__init__( self, parent, *args, **kwargs )


class HexEditDropdown( ttk.OptionMenu ):

	""" Used for struct data display and editing, using a predefined set of choices. Similar to the 
		HexEditEntry class, except that the widget's contents/values must be given during initialization. 
		"options" should be a dictionary, where each key is a string to display as an option in this
		widget, and the corresponding values are the data values to edit/update in the target file.
		"dataOffsets" will typically be a single int value, but can be a list of offsets. """

	def __init__( self, parent, dataOffsets, byteLength, formatting, updateName, options, defaultOption=None, **kwargs ):

		if defaultOption:
			# If the default option given is a value (or non-string), translate it to the string
			if type( defaultOption ) != str:
				for key, value in options.items():
					if value == defaultOption:
						defaultOption = key
						break
				else: # Above loop didn't break; couldn't find the provided value
					raise IOError( 'Invalid default option value for a HexEditDropdown: ' + str(defaultOption) )
		else:
			defaultOption = options.keys()[0]

		# Replace the command, if provided, with a lambda function, so its callback behaves like an Entry widget's
		callBack = kwargs.get( 'command', None )
		if callBack:
			kwargs['command'] = lambda currentString: callBack( self )

		# Create the widget
		self.selectedString = Tk.StringVar()
		ttk.OptionMenu.__init__( self, parent, self.selectedString, defaultOption, *options, **kwargs )

		self.offsets 	= dataOffsets		# May be a single file offset (int), or a list of them
		self.byteLength = byteLength
		self.formatting = formatting
		self.updateName = updateName

		self.options = options				# Dict of the form, key=stringToDisplay, value=dataToSave

	def get( self ): # Overriding the original get method, which would get the string, not the associated value
		return self.options[self.selectedString.get()]


class CodeLibrarySelector( BasicWindow ):

	""" Presents a non-modal pop-up window where the user can select a directory (library) to load code mods from. """

	def __init__( self, rootWindow ):
		if not BasicWindow.__init__( self, rootWindow, 'Code Library Selection', unique=True ): #, offsets=(160, 100)
			return # If the above returned false, it displayed an existing window, so we should exit here
		
		pathsList = globalData.getModsFolderPath( getAll=True )
		pathIndex = int( globalData.checkSetting('codeLibraryIndex') )
		if pathIndex >= len( pathsList ): pathIndex = 0 # Failsafe/default
		self.pathIndexVar = Tk.IntVar( value=pathIndex )
		self.initialLibraryPath = ''

		# Add Radio buttons for each library path option
		self.pathsFrame = ttk.Frame( self.window )
		for i, path in enumerate( pathsList ):
			self.addLibraryOption( i, path )
			if i == pathIndex:
				self.initialLibraryPath = path
		self.pathsFrame.pack( padx=20, pady=(20, 10), expand=True, fill='x' )

		ttk.Button( self.window, text='Add Another Library Path', command=self.addPath ).pack( pady=5, ipadx=10 )

		buttonsFrame = ttk.Frame( self.window )
		self.okButton = ttk.Button( buttonsFrame, text='Ok', command=self.submit )
		self.okButton.pack( side='left', padx=10 )
		ttk.Button( buttonsFrame, text='Cancel', command=self.close ).pack( side='left', padx=10 )
		buttonsFrame.pack( pady=10 )

		# Done creating window. Pause execution of the calling function until this window is closed.
		rootWindow.wait_window( self.window ) # Pauses execution of the calling function until this window is closed.

	def addLibraryOption( self, buttonIndex, path ):

		""" Adds a library option (radio button and label) to the GUI. """

		path = os.path.normpath( path ).replace( '"', '' )
		emptyWidget = Tk.Frame( self.window, relief='flat' ) # This is used as a simple workaround for the labelframe, so we can have no text label with no label gap.
		optionFrame = ttk.Labelframe( self.pathsFrame, labelwidget=emptyWidget, padding=(20, 4) )

		# Disable the radiobutton if the path is invalid, so the user can't select it
		if os.path.exists( path ): state = 'normal'
		else: state = 'disabled'

		radioBtn = ttk.Radiobutton( optionFrame, text=os.path.basename(path), variable=self.pathIndexVar, value=buttonIndex, state=state )
		radioBtn.pack( side='left', padx=(0, 100) )
		removeBtn = ttk.Button( optionFrame, text='-', width=3, command=lambda w=optionFrame: self.removePath(w), style='red.TButton' )
		ToolTip( removeBtn, text='Remove library', delay=1000, bg='#ee9999' )
		removeBtn.pack( side='right' )

		optionFrame.path = path
		optionFrame.pack( expand=True, fill='x' )
		ToolTip( optionFrame, text=path, wraplength=600, delay=1000 )

	def addPath( self ):

		""" Prompts the user for a mod library directory, and adds it to the GUI. """

		# Prompt for a directory to load for the Mods Library.
		newSelection = tkFileDialog.askdirectory(
			parent=self.window,
			title=( 'Choose a folder from which to load your Mods Library.\n\n'
					'All mods you intend to save should be in the same library.' ),
			initialdir=globalData.getLastUsedDir( 'codeLibrary' ),
			mustexist=True )

		if newSelection: # Could be an empty string if the user canceled the operation
			# Make sure this path isn't already loaded
			frameChildren = self.pathsFrame.winfo_children()
			for option in frameChildren:
				if option.path == os.path.normpath( newSelection ):
					return

			self.addLibraryOption( len(frameChildren), newSelection )

			# Select this library
			self.pathIndexVar.set( len(frameChildren) )

	def removePath( self, optionFrameToRemove ):

		""" Removes a library option from the GUI and updates the index values of the remaining radio buttons. """

		selectedIndex = self.pathIndexVar.get()
		passedButtonToRemove = False

		# If this library button was selected, reset the current selection (default to the first library)
		for optionFrame in self.pathsFrame.winfo_children():
			radioBtn = optionFrame.winfo_children()[0]
			btnIndex = radioBtn['value']

			if optionFrame == optionFrameToRemove:
				if btnIndex == selectedIndex:
					self.pathIndexVar.set( 0 )
				elif selectedIndex > btnIndex:
					self.pathIndexVar.set( selectedIndex - 1 ) # Decrement the selected index by 1, since there is one less library

				passedButtonToRemove = True
				continue

			# Update the radio button value for all buttons beyond the one being removed
			if passedButtonToRemove:
				radioBtn['value'] = btnIndex - 1
		
		optionFrameToRemove.destroy() # Should also destroys its children, including the radio button

	def submit( self ):
		# Validate the current selection
		index = self.pathIndexVar.get()
		if index >= len( self.pathsFrame.winfo_children() ):
			msg( 'Invalid Mods Library Selection!' )
			return

		# Collect the paths and combine them into one string
		libraryPaths = []
		for option in self.pathsFrame.winfo_children():
			libraryPaths.append( option.path )
		pathsString = '"' + '","'.join( libraryPaths ) + '"'
		
		# Save the new path(s) to the settings file
		globalData.settings.set( 'General Settings', 'codeLibraryPath', pathsString )
		globalData.settings.set( 'General Settings', 'codeLibraryIndex', str(index) )
		globalData.saveProgramSettings()

		# Set the mod library selector button hover text, and close this window
		codesTab = globalData.gui.codeManagerTab
		if codesTab:
			codeLibraryPath = globalData.getModsFolderPath()
			codesTab.libraryToolTipText.set( 'Select Mods Library.\tCurrent library:\n' + codeLibraryPath )
		self.close()

		# Reload the Mods Library if a different one was selected
		if codesTab and codeLibraryPath != self.initialLibraryPath:
			codesTab.scanCodeLibrary()


class CodeSpaceOptionsWindow( BasicWindow ):

	""" Creates a modeless (non-modal) message window that allows the user to toggle 
		what regions are allowed to be overwritten by custom code. """

	def __init__( self, rootWindow ):
		if not BasicWindow.__init__( self, rootWindow, 'Code-Space Options', unique=True ): # , offsets=(160, 100)
			return # If the above returned false, it displayed an existing window, so we should exit here

		# Check if a disc and DOL have been loaded
		if globalData.disc:
			dol = globalData.disc.dol
			dolRegions = dol.customCodeRegions.keys()
		else:
			dol = None
			dolRegions = []

		#self.window = ttk.Frame( self.window, padding='15 0 15 0' ) # padding order: left, top, right, bottom
		ttk.Label( self.window, text='These are the regions that will be reserved (i.e. may be partially or fully overwritten) for injecting custom code. '
			'It is safest to uninstall all mods that may be installed to a region before disabling it. '
			'For more information on these regions, or to add your own, see the "codeRegionSettings.py" file.', wraplength=550 ).grid( columnspan=4, pady=12, padx=15 )

		# Create the rows for each region option to be displayed.
		row = 1
		padx = 5
		pady = 3
		self.checkboxes = []
		for overwriteOptionName, boolVar in globalData.overwriteOptions.items():
			if dol and overwriteOptionName not in dolRegions:
				print( 'Skipping ' + overwriteOptionName + ' region. Not found in dol regions dict.' )
				continue

			# The checkbox
			checkbox = ttk.Checkbutton( self.window, variable=boolVar, command=lambda regionName=overwriteOptionName: self.checkBoxClicked(regionName) )

			# Title
			ttk.Label( self.window, text=overwriteOptionName ).grid( row=row, column=1, padx=padx, pady=pady )

			# Check the space available with this region
			totalRegionSpace = 0
			if dol:
				tooltipText = []
				for i, region in enumerate( dol.customCodeRegions[overwriteOptionName], start=1 ):
					spaceAvailable = region[1] - region[0]
					totalRegionSpace += spaceAvailable
					tooltipText.append( 'Area ' + str(i) + ': ' + uHex(region[0]) + ' - ' + uHex(region[1]) + '  |  ' + uHex(spaceAvailable) + ' bytes' )

				# Create the label and tooltip for displaying the total region space and details
				regionSizeLabel = ttk.Label( self.window, text=uHex(totalRegionSpace) + '  Bytes', foreground='#777', font="-slant italic" )
				regionSizeLabel.grid( row=row, column=2, padx=padx, pady=pady )
				ToolTip( regionSizeLabel, delay=300, text='\n'.join(tooltipText), location='e', bg='#c5e1eb', follow_mouse=False, wraplength=1000 )

			# Disable regions which are reserved for Gecko codes
			# if overwriteOptions[ 'EnableGeckoCodes' ].get() and ( overwriteOptionName == gecko.codelistRegion or overwriteOptionName == gecko.codehandlerRegion ):
			# 	checkbox['state'] = 'disabled'
			# 	restoreBtn['state'] = 'disabled'
			# 	checkbox.bind( '<1>', self.checkboxDisabledMessage )

			# Attach some info for later use
			checkbox.space = totalRegionSpace
			checkbox.regionName = overwriteOptionName
			#checkbox.restoreBtn = restoreBtn
			checkbox.grid( row=row, column=0, padx=padx, pady=pady )

			self.checkboxes.append( checkbox )

			row += 1
		
		# Add the checkbox to enable Gecko codes
		# if gecko.environmentSupported:
		# 	self.enableGeckoChkBox = ttk.Checkbutton( self.window, text='Enable Gecko Codes', variable=overwriteOptions['EnableGeckoCodes'], command=self.toggleGeckoEngagement )
		# else:
		# 	self.enableGeckoChkBox = ttk.Checkbutton( self.window, text='Enable Gecko Codes', variable=overwriteOptions['EnableGeckoCodes'], command=self.toggleGeckoEngagement, state='disabled' )
		# self.enableGeckoChkBox.grid( columnspan=4, pady=12 )

		# Add the total space label and the Details button to the bottom of the window
		lastRow = ttk.Frame( self.window )
		self.totalSpaceLabel = Tk.StringVar()
		self.calculateSpaceAvailable()
		ttk.Label( lastRow, textvariable=self.totalSpaceLabel ).pack( side='left', padx=11 )
		# detailsLabel = ttk.Label( lastRow, text='Details', foreground='#03f', cursor='hand2' )
		# detailsLabel.pack( side='left', padx=11 )
		# detailsLabel.bind( '<1>', self.extraDetails )
		lastRow.grid( columnspan=4, pady=12 )

		#self.window.pack()

	def checkBoxClicked( self, regionName ):
		# The program's checkbox boolVars (in overwriteOptions) has already been updated by the checkbox. However, the variables in the "settings"
		# object still need to be updated. saveProgramSettings does this, as well as saves the settings to the options file.
		globalData.saveProgramSettings()

		self.calculateSpaceAvailable()
		#checkForPendingChanges( changesArePending=True )
		
		#playSound( 'menuChange' )

	# def toggleGeckoEngagement( self ):

	# 	""" Called by the 'Enable Gecko Codes' checkbox when it changes state. When enabling, and either 
	# 		of the gecko regions are not selected for use, prompt with a usage warning. """

	# 	if overwriteOptions['EnableGeckoCodes'].get() and ( not overwriteOptions[ gecko.codelistRegion ].get() or not overwriteOptions[ gecko.codehandlerRegion ].get() ) :
	# 		if dol.isMelee and ( gecko.codelistRegion == 'DebugModeRegion' or gecko.codehandlerRegion == 'DebugModeRegion'
	# 							or gecko.codelistRegion == 'Debug Mode Region' or gecko.codehandlerRegion == 'Debug Mode Region' ): 
	# 			meleeDetails = ( " Mostly, this just means that you won't be able to use the vanilla Debug Menu (if you're not "
	# 							 "sure what that means, then you're probably not using the Debug Menu, and you can just click yes)." )
	# 		else: meleeDetails = ''

	# 		promptToUser = ( 'Enabling Gecko codes means that the regions assigned for Gecko codes, ' + gecko.codelistRegion + ' and ' + gecko.codehandlerRegion + ', '
	# 			"will be reserved (i.e. may be partially or fully overwritten) for custom code." + meleeDetails + \
	# 			'\n\nWould you like to enable these regions for overwrites in order to use Gecko codes?' )
	# 	else: promptToUser = '' # Just going to use the following function to set some options & states (no prompt to the user)

	# 	self.calculateSpaceAvailable()

	# 	willUserAllowGecko( promptToUser, True, self.window ) # This will also check for pending changes, or for enabled codes (if gecko codes are allowed)
		
	# 	playSound( 'menuChange' )

	# def checkboxDisabledMessage( self, event ):

	# 	""" This will be executed on click events to the checkboxes for the regions assigned to the Gecko codelist and codehandler, since they will be disabled. """

	# 	if overwriteOptions[ 'EnableGeckoCodes' ].get():
	# 		msg( "You currently have Gecko codes enabled, which require use of this region. "
	# 			 "You must uncheck the 'Enable Gecko codes' checkbox if you want to unselect this region.", "Can't let you do that, Star Fox!", self.window )

	def calculateSpaceAvailable( self ):

		if not globalData.disc:
			self.totalSpaceLabel.set( 'Total Space Available:   N/A' )
		else:
			space = 0
			for checkbox in self.checkboxes:
				if globalData.overwriteOptions[checkbox.regionName].get(): space += checkbox.space
			self.totalSpaceLabel.set( 'Total Space Available:   ' + uHex(space) + ' Bytes  (' + humansize(space) + ')' )
	
	# def extraDetails( self, event ):
	# 	msg( 'Each of the region options displayed here may be a single contiguous area in the DOL, or a collection of several areas (see codeRegionSettings.py for '
	# 		'the exact definitions of each region). Regions assigned for the Gecko codehandler and codelist may be changed in the settings.py file under Gecko Configuration. '
	# 		'However, if one of these is a group of areas, only the first contiguous area among the group will be used for the codehandler or codelist.'
	# 		"""\n\nIf Gecko codes are used, you may notice that the "Total Space Available" shown here will be higher than what's reported by the Codes Free Space indicators in the """
	# 		'main program window. That is because the free space indicators do not count space that will be assigned for the Gecko codehandler (' + uHex(gecko.codehandlerLength) + ' bytes), '
	# 		'the codelist wrapper (0x10 bytes), or the codelist.', '', self.window )


class DisguisedEntry( Tk.Entry ):
	
	""" An Entry field that blends into its surroundings until hovered over. """

	def __init__( self, parent=None, respectiveLabel=None, background='SystemButtonFace', *args, **kwargs ):
		self.respectiveLabel = respectiveLabel
		self.bindingsCreated = False

		# Define some colors
		self.initialBgColor = background

		# Create the Entry widget
		Tk.Entry.__init__( self, parent, relief='flat', borderwidth=2, background=background, *args, **kwargs )

		#self['state'] = 'normal'
		self.enableBindings()

		if respectiveLabel:
			self.respectiveLabel.configure( cursor='' )
			self.configure( cursor='' )

	def enableBindings( self ):
		if not self.bindingsCreated:
			self.bind( '<Enter>', self.onMouseEnter, '+' )
			self.bind( '<Leave>', self.onMouseLeave, '+' )
			#self['state'] = 'normal' # State of the Entry widget

			if self.respectiveLabel:
				self.respectiveLabel.bind( '<Enter>', self.onMouseEnter, '+' )
				self.respectiveLabel.bind( '<Leave>', self.onMouseLeave, '+' )
				self.respectiveLabel.bind( '<1>', self.focusThisWid, '+' )
			self.bindingsCreated = True

	# def enableEntry( self ):
	# 	self['state'] = 'normal'
	# 	self.enableBindings()

		if self.respectiveLabel:
			self.respectiveLabel.configure( cursor='hand2' )
			self.configure( cursor='xterm' )

	def disableEntry( self ):
		self['state'] = 'disabled'

		if self.respectiveLabel:
			self.respectiveLabel.configure( cursor='' )
			self.configure( cursor='' )

	# Define the event handlers
	def onMouseEnter( self, event ):
		if self['state'] == 'normal':
			self.config( relief='sunken' )
			if not self['background'] == '#faa': # Don't change the background color if it indicates pending changes to save
				self.config( background='#ffffff' )
	def onMouseLeave( self, event ):
		self.config( relief='flat' )
		if not self['background'] == '#faa': # Don't change the background color if it indicates pending changes to save
			self.config( background=self.initialBgColor )
	def focusThisWid( self, event ):
		if self['state'] == 'normal': self.focus()


class LabelButton( Tk.Label ):

	""" Basically a label that acts as a button, using an image and mouse click/hover events. 
		Expects an RGBA images named '[name].png' and '[name]Gray.png' (if the default image 
		variation doesn't exist, the Gray variation will be used for both default and hover). 
		The latter is used for the default visible state, and the former is used on mouse hover.
		Example uses of this class are for a mod's edit/config buttons and web links. """

	def __init__( self, parent, imageName, callback, hovertext='' ):
		# Get the images needed
		self.defaultImage = globalData.gui.imageBank( imageName + 'Gray', showWarnings=False )
		self.hoverImage = globalData.gui.imageBank( imageName )
		assert self.hoverImage, 'Unable to get the {}Gray web link image.'.format( imageName )
		if not self.defaultImage:
			self.defaultImage = self.hoverImage
		self.callback = callback
		self.toolTip = None
		self.isHovered = False

		# Initialize the label with one of the above images
		Tk.Label.__init__( self, parent, image=self.defaultImage, borderwidth=0, highlightthickness=0, cursor='hand2' )

		# Bind click and mouse hover events
		self.bind( '<1>', self.callback )
		self.bind( '<Enter>', self.hovered )
		self.bind( '<Leave>', self.unhovered )

		if hovertext:
			self.updateHovertext( hovertext )
		
	def hovered( self, event ):
		self['image'] = self.hoverImage
		self.isHovered = True
	def unhovered( self, event ):
		self['image'] = self.defaultImage
		self.isHovered = False

	def updateHovertext( self, newText ):
		if self.toolTip:
			self.toolTipVar.set( newText )
		else:
			self.toolTipVar = Tk.StringVar( value=newText )
			self.toolTip = ToolTip( self, textvariable=self.toolTipVar, delay=700, wraplength=800, justify='center' )


class ColoredLabelButton( LabelButton ):

	""" Like the LabelButton, but uses a single source image which is then 
		programmatically colored for the hover state. """

	def __init__( self, parent, imageName, callback, hovertext='', color='#0099f0' ):

		LabelButton.__init__( self, parent, imageName, callback, hovertext )

		self.imageName = imageName
		self.origHovertext = hovertext
		self.disabled = False
		self.initColor = color
		self.defaultImage = getColoredShape( imageName, 'black' )
		self.hoverImage = getColoredShape( imageName, color )
		self['image'] = self.defaultImage

	def updateColor( self, newColor='', forHoverState=False ):

		# If no new color is specified, assume the user wants to reset it back to the initial color
		if not newColor:
			newColor = self.initColor

		if forHoverState:
			self.hoverImage = getColoredShape( self.imageName, newColor )
		else:
			self.defaultImage = getColoredShape( self.imageName, newColor )

	def updateImage( self, newImage, newColor='', forHoverState=True, forDefaultState=True ):

		""" Updates the image used for the hover and/or default states. """
		
		# If no new color is specified, assume the user wants to reset them back to the initial colors
		if newColor:
			defaultColor = newColor
			hoverColor = newColor
		else:
			defaultColor = 'black'
			hoverColor = self.initColor

		if forHoverState:
			self.hoverImage = getColoredShape( newImage, hoverColor )
		if forDefaultState:
			self.defaultImage = getColoredShape( newImage, defaultColor )

		if self.isHovered:
			self['image'] = self.hoverImage
		else:
			self['image'] = self.defaultImage

	def disable( self, newHoverText='' ):
		self.unbind( '<1>' )
		self.unbind( '<Enter>' ) # Unbinding only the hover callback, not the toolTip Enter method
		if self.toolTip: # Ensure the toolTip still functions (workaround to second unbind arg being broken)
			self.toolTip._id1 = self.bind("<Enter>", self.toolTip.enter, '+')
		self.configure( cursor='' )

		self.updateColor( 'gray' )
		self['image'] = self.defaultImage

		if newHoverText:
			self.updateHovertext( newHoverText )
			
		self.disabled = True

	def enable( self ):
		self.bind( '<1>', self.callback )
		self.bind( '<Enter>', self.hovered, '+' )
		self.configure( cursor='hand2' )

		self.updateColor( 'black' )

		if self.isHovered:
			self['image'] = self.hoverImage
		else:
			self['image'] = self.defaultImage

		self.updateHovertext( self.origHovertext )
		
		self.disabled = False


class Dropdown( ttk.OptionMenu ):

	def __init__( self, parent, options, default='', variable=None, command=None, **kwargs ):

		self.command = command
		if not default:
			default = options[0]
		if not variable:
			variable = Tk.StringVar()

		if command:
			assert callable( command ), 'The given command is not callable! {}'.format( command )
			ttk.OptionMenu.__init__( self, parent, variable, default, *options, command=self.callBack, **kwargs )
		else:
			ttk.OptionMenu.__init__( self, parent, variable, default, *options, **kwargs )

	def callBack( self, newValue ):

		""" Called when the OptionMenu (dropdown) selection is changed. """

		self.command( self, newValue )


class VerticalScrolledFrame( Tk.Frame ):

	""" Provides a simple vertical scrollable area, for space for other widgets. 
		Use the 'interior' attribute to place widgets inside the scrollable area. 
		The outer widget is essentially just a Frame; which can be attached using 
		pack/place/grid geometry managers as normal. """

	def __init__(self, parent, defaultHeight=700, *args, **kw):
		Tk.Frame.__init__(self, parent, *args, **kw)

		# create a canvas object, and a vertical scrollbar for scrolling it
		self.vscrollbar = Tk.Scrollbar( self, orient='vertical' )
		self.vscrollbar.grid( column=1, row=0, sticky='ns' )
		self.canvas = Tk.Canvas( self, bd=0, highlightthickness=0, yscrollcommand=self.vscrollbar.set ) #, height=defaultHeight
		self.canvas.grid( column=0, row=0, sticky='nsew' )
		self.canvas.yview_scroll = self.yview_scroll
		self.vscrollbar.config( command=self.canvas.yview )
		#self.defaultHeight = defaultHeight

		# reset the view
		self.canvas.xview_moveto( 0 )
		self.canvas.yview_moveto( 0 )

		# create a frame inside the canvas which will be scrolled with it
		self.interior = Tk.Frame( self.canvas, relief='ridge' )
		self.interior_id = self.canvas.create_window( 0, 0, window=self.interior, anchor='nw' )
		#self.canvas.config( height=defaultHeight )

		# add resize configuration for the canvas and scrollbar
		self.rowconfigure( 0, weight=1 )
		self.columnconfigure( 0, weight=1 )
		self.columnconfigure( 1, weight=0 ) # Do not resize this column (for the scrollbar)
		#print 'vsf init done'

		# track changes to the canvas and frame width and sync them,
		# also updating the scrollbar
		self.interior.bind( '<Configure>', self.configureCanvas )
		self.canvas.bind( '<Configure>', self.configureInterior )

	def configureCanvas( self, event=None ):
		self.update_idletasks()
		self.configureScrollbar()

		# update the scroll area to match the size of the inner frame
		self.canvas.config( scrollregion=self.canvas.bbox(self.interior_id) )
		
		interiorWidth = self.interior.winfo_reqwidth()
		if interiorWidth != self.canvas.winfo_width():
			# update the canvas' width to fit the inner frame
			self.canvas.config( width=interiorWidth )
		
		if self.canvas.winfo_reqheight() > self.interior.winfo_height():
			self.canvas.config( height=self.interior.winfo_reqheight() )

	def configureInterior( self, event=None ):
		self.update_idletasks()
		self.configureScrollbar()

		canvasWidth = self.canvas.winfo_width()
		if self.interior.winfo_reqwidth() != canvasWidth:
			# update the inner frame's width to fill the canvas
			self.canvas.itemconfigure( self.interior_id, width=canvasWidth )
		
		# if self.interior.winfo_reqheight() != self.canvas.winfo_height():
		# 	# update the inner frame's height to fill the canvas
		# 	self.canvas.itemconfigure(self.interior_id, height=self.canvas.winfo_height())

	def configureScrollbar( self ):
		# Check if a scrollbar is necessary, and add/remove it as needed.
		if self.interior.winfo_height() > self.canvas.winfo_height():
			self.vscrollbar.grid( column=1, row=0, sticky='ns' )
		else:
			# remove the scrollbar and disable scrolling
			try:
				self.vscrollbar.grid_forget()
			except: pass # May have been deleted
			self.canvas.itemconfigure( self.interior_id, width=self.canvas.winfo_width() )

	def yview_scroll( self, number, what ):
		
		""" This is an override of the canvas' native yview_scroll method, 
			so that it only operates while the scrollbar is attached. """
		
		if self.vscrollbar.winfo_manager():
			self.canvas.tk.call( self.canvas._w, 'yview', 'scroll', number, what )

		return 'break'

	def clear( self ):

		""" Clears (destroys) contents, and resets the scroll position to top. """

		for childWidget in self.interior.winfo_children():
			childWidget.destroy()

		# Reset the scrollbar (if there is one displayed) to the top.
		self.canvas.yview_moveto( 0 )


class NeoTreeview( ttk.Treeview, object ):

	def __init__( self, *args, **kwargs ):

		super( NeoTreeview, self ).__init__( *args, **kwargs )

		self.openFolders = []
		self.selectionState = ()
		self.focusState = ''
		self.scrollState = 0.0

		if 'yscrollcommand' in kwargs: # This is a method being passed; get the widget that owns this
			self.scrollbar = kwargs['yscrollcommand'].im_self # Will need to update this in update to Python3
		else:
			self.scrollbar = None

	def getItemsInSelection( self, selectionTuple='', recursive=True, selectAll=False ):

		""" Extends a selection in the treeview, which may contain folders, to include all items within those folders. 
			"iid"s are unique "Item IDentifiers" given to file/folder items in treeview widgets to identify or select them. 
			This will exclude duplicates (in case items inside folders were also chosen). Returns a set of folder Iids and 
			a set of file Iids. If no selectionTuple is given, all items and folders will be returned. """

		fileIids = set()
		folderIids = set()

		# If this is the first-level iteration and no selection was given
		if not selectionTuple:
			if selectAll: # Start with root level items and get everything
				selectionTuple = self.get_children()
			else: # Just extend what is already selected in the treeview
				selectionTuple = self.selection()

		# Separate sets/lists of file/folder isoPaths
		for iid in selectionTuple:
			children = self.get_children( iid )

			# If the item has children, it's a folder
			if children and recursive:
				folderIids.add( iid )

				subFolders, subFiles = self.getItemsInSelection( children, True )
				folderIids.update( subFolders )
				fileIids.update( subFiles )
			elif children:
				folderIids.add( iid )
			else:
				fileIids.add( iid )

		return folderIids, fileIids

	def getOpenFolders( self, openIids=[], parentIid='' ):

		""" Gets the iids of all open folders. """
		
		if not parentIid: # Initial call; iterate over root items
			openIids = []

		# Iterate over children of the given iid. No iteration if not a folder and not root
		for iid in self.get_children( parentIid ):
			if self.item( iid, 'open' ):
				openIids.append( iid )
			openIids = self.getOpenFolders( openIids, iid )

		return openIids

	def saveState( self ):

		""" Store the current state of the treeview, including current 
			open folders, selections, and scroll position. """

		self.openFolders = self.getOpenFolders()

		# Remember the selection, focus, and current scroll position of the treeview
		self.selectionState = self.selection()
		self.focusState = self.focus()
		if self.scrollbar:
			self.scrollState = self.scrollbar.get()[0] # .get() returns e.g. (0.49505277044854884, 0.6767810026385225)

	def restoreState( self ):

		""" Restore a previously stored state of the treeview, including 
			open folders, selections, and scroll position. """
		
		# Open all folders that were previously open
		for folderIid in self.openFolders:
			#if self.exists( folderIid ): # Checking in case it was deleted
			try:
				self.item( folderIid, open=True )
			except: pass # The item may have been deleted, which is fine

		# Set the current selections
		try:
			self.selection_set( self.selectionState )
		except: # Prior selections might not exist
			pass

		# Set scroll position back to what it was
		self.focus( self.focusState )
		if self.scrollbar:
			self.yview_moveto( self.scrollState )

	def addTag( self, iid, tagToAdd ):

		""" Adds the given tag to the given item, while preserving other tags it may have. """
		
		targetFileTags = self.item( iid, 'tags' ) # Returns a tuple
		targetFileTags = list( targetFileTags )
		targetFileTags.append( tagToAdd )

		self.item( iid, tags=targetFileTags )

	def removeTag( self, iid, tagToRemove ):

		""" Removes the given tag from the given item, while preserving other tags it may have. """

		currentTags = list( self.item( iid, 'tags' ) )
		if tagToRemove in currentTags:
			currentTags.remove( tagToRemove )
			self.item( iid, tags=currentTags )


class ToolTip( object ):

	''' 
		This class provides a flexible tooltip widget for Tkinter; it is based on IDLE's ToolTip
		module which unfortunately seems to be broken (at least the version I saw).

		Original author: Michael Lange <klappnase (at) freakmail (dot) de>
		With modifications by Daniel R. Cappel, including:
			new 'remove' method, 'location' option, multi-monitor support, live update of textvariable, and more.
		The original class is no longer available online, however a simplified adaptation can be found here:
			https://github.com/wikibook/python-in-practice/blob/master/TkUtil/Tooltip.py
			
	INITIALIZATION OPTIONS:
	anchor :        where the text should be positioned inside the widget, must be one of "n", "s", "e", "w", "nw" and so on;
					default is "center"
	bd :            borderwidth of the widget; default is 1 (NOTE: don't use "borderwidth" here)
	bg :            background color to use for the widget; default is "lightyellow" (NOTE: don't use "background")
	delay :         time in ms that it takes for the widget to appear on the screen when the mouse pointer has
					entered the parent widget; default is 1200
	offset :        increases distance between the tooltip and parent; default is 0
	fg :            foreground (i.e. text) color to use; default is "black" (NOTE: don't use "foreground")
	follow_mouse :  if set to 1 the tooltip will follow the mouse pointer instead of being displayed
					outside of the parent widget; this may be useful if you want to use tooltips for
					large widgets like listboxes or canvases; default is 0
	font :          font to use for the widget; default is system specific
	justify :       how multiple lines of text will be aligned, must be "left", "right" or "center"; default is "left"
	location :      placement above or below the target (master) widget. values may be 'n', 's' (default), 'e', or 'w'
	padx :          extra space to the left and right within the widget; default is 4
	pady :          extra space above and below the text; default is 2
	relief :        one of "flat", "ridge", "groove", "raised", "sunken" or "solid"; default is "solid"
	state :         must be "normal" or "disabled"; if set to "disabled" the tooltip will not appear; default is "normal"
	text :          the text that is displayed inside the widget
	textvariable :  if set to an instance of Tkinter.StringVar() the variable's value will be used as text for the widget
	width :         width of the widget; the default is 0, which means that "wraplength" will be used to limit the widgets width
	wraplength :    limits the number of characters in each line; default is 200

	WIDGET METHODS:
	configure(**opts) : change one or more of the widget's options as described above; the changes will take effect the
						next time the tooltip shows up; NOTE: 'follow_mouse' cannot be changed after widget initialization
	remove() :          removes the tooltip from the parent widget

	Other widget methods that might be useful if you want to subclass ToolTip:
	enter() :           callback when the mouse pointer enters the parent widget
	leave() :           called when the mouse pointer leaves the parent widget
	motion() :          is called when the mouse pointer moves inside the parent widget if 'follow_mouse' is set to 1 and 
						the tooltip has shown up to continually update the coordinates of the tooltip window
	coords() :          calculates the screen coordinates of the tooltip window
	create_contents() : creates the contents of the tooltip window (by default a Tkinter.Label)

	Ideas gleaned from PySol

	Other Notes:
		If text or textvariable are empty or not specified, the tooltip will not show. '''

	version = '1.7.2'

	def __init__( self, master, text='Your text here', delay=1200, **opts ):
		self.master = master
		self._opts = {'anchor':'center', 'bd':1, 'bg':'lightyellow', 'delay':delay, 'offset':0, 
					  'fg':'black', 'follow_mouse':0, 'font':None, 'justify':'left', 'location':'s', 
					  'padx':4, 'pady':2, 'relief':'solid', 'state':'normal', 'text':text, 
					  'textvariable':None, 'width':0, 'wraplength':200}
		self.configure(**opts)
		self._tipwindow = None
		self._id = None
		self._id1 = self.master.bind("<Enter>", self.enter, '+')
		self._id2 = self.master.bind("<Leave>", self.leave, '+')
		self._id3 = self.master.bind("<ButtonPress>", self.leave, '+')
		self._follow_mouse = 0
		if self._opts['follow_mouse']:
			self._id4 = self.master.bind("<Motion>", self.motion, '+')
			self._follow_mouse = 1

		# Monitor changes to the textvariable, if one is used (for dynamic updates to the tooltip's position)
		if self._opts['textvariable']:
			self._opts['textvariable'].trace( 'w', lambda nm, idx, mode: self.update() )

	def _hasText(self):
		return self._opts['text'] != 'Your text here' or ( self._opts['textvariable'] and self._opts['textvariable'].get() )

	def configure(self, **opts):
		for key in opts:
			if self._opts.has_key(key):
				self._opts[key] = opts[key]
			else:
				raise KeyError( 'KeyError: Unknown option: "%s"' %key )

	def remove(self):
		#self._tipwindow.destroy()
		self.leave()
		self.master.unbind("<Enter>", self._id1)
		self.master.unbind("<Leave>", self._id2)
		self.master.unbind("<ButtonPress>", self._id3)
		if self._follow_mouse:
			self.master.unbind("<Motion>", self._id4)

	##----these methods handle the callbacks on "<Enter>", "<Leave>" and "<Motion>"---------------##
	##----events on the parent widget; override them if you want to change the widget's behavior--##

	def enter(self, event=None):
		self._schedule()

	def leave(self, event=None):
		self._unschedule()
		self._hide()

	def motion(self, event=None):
		if self._tipwindow and self._follow_mouse:
			x, y = self.coords()
			self._tipwindow.wm_geometry("+%d+%d" % (x, y))

	def update(self, event=None):
		tw = self._tipwindow
		if not tw: return

		if not self._hasText():
			self.leave()
		else:
			tw.withdraw()
			tw.update_idletasks() # to make sure we get the correct geometry
			x, y = self.coords()
			tw.wm_geometry("+%d+%d" % (x, y))
			tw.deiconify()

	##------the methods that do the work:---------------------------------------------------------##

	def _schedule(self):
		self._unschedule()
		if self._opts['state'] == 'disabled': return
		self._id = self.master.after(self._opts['delay'], self._show)

	def _unschedule(self):
		id = self._id
		self._id = None
		if id:
			self.master.after_cancel(id)

	def _show(self):
		if self._opts['state'] == 'disabled' or not self._hasText():
			self._unschedule()
			return
		if not self._tipwindow:
			self._tipwindow = tw = Tk.Toplevel(self.master)
			tw.wm_attributes( '-topmost', 1 ) # Makes sure the tooltip is above any other window present
			# hide the window until we know the geometry
			tw.withdraw()
			tw.wm_overrideredirect(1)

			if tw.tk.call("tk", "windowingsystem") == 'aqua':
				tw.tk.call("::tk::unsupported::MacWindowStyle", "style", tw._w, "help", "none")

			self.create_contents()
			tw.update_idletasks()
			x, y = self.coords()
			tw.wm_geometry("+%d+%d" % (x, y))
			tw.deiconify()
		# else:
		# 	print 'deiconify'
		# 	self._tipwindow.deiconify()

	def _hide(self):
		tw = self._tipwindow
		self._tipwindow = None
		if tw:
			tw.destroy()
			# print 'withdraw'
			# tw.withdraw()

	##----these methods might be overridden in derived classes:----------------------------------##

	def coords(self):
		# The tip window must be completely outside the master widget;
		# otherwise when the mouse enters the tip window we get
		# a leave event and it disappears, and then we get an enter
		# event and it reappears, and so on forever :-(
		# or we take care that the mouse pointer is always outside the tipwindow :-)

		tw = self._tipwindow
		twWidth, twHeight = tw.winfo_reqwidth(), tw.winfo_reqheight()
		masterWidth, masterHeight = self.master.winfo_reqwidth(), self.master.winfo_reqheight()
		if 's' in self._opts['location'] or 'e' in self._opts['location']:
			cursorBuffer = 32 # Guestimate on cursor size, to ensure no overlap with it (or the master widget if follow_mouse=False)
		else: cursorBuffer = 2

		# Establish base x/y coords
		if self._follow_mouse: # Sets to cursor coords
			x, y = self.master.winfo_pointerxy()

		else: # Sets to widget top-left screen coords
			x = self.master.winfo_rootx()
			y = self.master.winfo_rooty()

		# Offset the tooltip location from the master (target) widget, so that it is not over the top of it
		if 'w' in self._opts['location'] or 'e' in self._opts['location']:
			if self._follow_mouse:
				if 'w' in self._opts['location']:
					x -= ( twWidth + cursorBuffer )
				else:
					x += cursorBuffer

				# Center y coord relative to the mouse position
				y -= ( twHeight / 2 - 8 )

			else:
				# Place the tooltip completely to the left or right of the target widget
				if 'w' in self._opts['location']:
					x -= ( twWidth + cursorBuffer )

				else: x += masterWidth + cursorBuffer

				# Vertically center tooltip relative to master widget
				y += ( masterHeight / 2 - twHeight / 2 )
				
			# Apply the distance buff
			x += self._opts['offset']

		else: # No horizontal offset, so the tooltip must be placed above or below the target to prevent problems
			if 'n' in self._opts['location']: # place the tooltip above the target
				y -= ( twHeight + cursorBuffer )
				
			else:
				y += cursorBuffer

			# Apply the distance buff
			y += self._opts['offset']

			# Horizontally center tooltip relative to master widget
			x += ( masterWidth / 2 - twWidth / 2 )

		return x, y

	def create_contents(self):
		opts = self._opts.copy()
		for opt in ('delay', 'follow_mouse', 'state', 'location', 'offset'):
			del opts[opt]
		label = Tk.Label(self._tipwindow, **opts)
		label.pack()


class PopupInterface( ToolTip ):

	""" Subclass of the ToolTip class in order to provide pop-up controls, similar to a tooltip,
		except that the controls can be hovered over and interacted with, rather than disappearing immediately. """

	def _hasText( self ):
		return True # Ensures the module thinks the tooltip/interface is worth showing

	def mousedOver( self ):

		""" Checks whether the mouse is currently hovering over this interface. """

		# Get the widget currently beneath the mouse
		try:
			x, y = self.master.winfo_pointerxy()
			hoveredWidget = globalData.gui.root.winfo_containing( x, y )
			if not hoveredWidget: return False # Might have left the GUI altogether

			if hoveredWidget == self._tipwindow:
				return True

			# Traverse upwards in the widget heirarchy
			parent = hoveredWidget.master
			while parent:
				if parent == self._tipwindow:
					return True
				parent = parent.master # Will eventually become '' after root

			return False

		except:
			return False

	def leave( self, event=None ):

		""" Instead of the usual tooltip behavior of unscheduling the creation method 
			(if it's queued) and destroying the window, we first wait a second to destroy it. """

		self._unschedule()
		self.master.after( 1000, self.queueHide )

	def queueHide( self ):

		""" Overriding this method to first see if the entry widget is being 
			hovered over or is focused, implying the user intends to use it. """

		# Check if the tooltip window exists
		if not self._tipwindow:
			return
		elif self.mousedOver():
			return

		self._hide()


class ToolTipEditor( PopupInterface ):

	""" Subclass of the PopupInterface class in order to provide a hoverable 
		tooltip which can be used to enter values. """

	def __init__( self, master, mainTab, *args, **kwargs ):
		super( ToolTipEditor, self ).__init__( master, *args, **kwargs )
		self.mainTab = mainTab

	def create_contents(self):
		entry = Tk.Entry( self._tipwindow, justify='center', width=self._opts['width'] )
		entry.bind( '<Return>', self.valuesSubmitted )
		entry.bind( "<Leave>", self.leave, '+' )
		entry.pack()

	def _show( self ):
		# Hide any other tooltips currently shown
		for toolTip in self.mainTab.toolTips.values():
			if toolTip._tipwindow and toolTip != self:
				toolTip._unschedule()
				toolTip._hide()

		super( ToolTipEditor, self )._show()

	def valuesSubmitted( self, event ):
		# Validate the input
		userInput = event.widget.get()
		try:
			userInput = int( userInput )
		except:
			msg( "The entered value should be a decimal number.", 'Invalid Input' )
			return
		if not userInput >= 0 or not userInput <= 100:
			msg( "The entered value should be between 0 and 100 (inclusive).", 'Invalid Input' )
			return

		# Call the callback to update this data
		self.mainTab.updateAltMusicChance( userInput )


class ToolTipButton( PopupInterface ):

	""" Subclass of the base ToolTip class in order to provide a popup 'Edit' button. 
		Unlike with the tooltip class, this module will wait a second before 
		disappearing, and will not disappear if the user's mouse is over it. """

	def __init__( self, master, mainTab, *args, **kwargs ):
		super( ToolTipButton, self ).__init__( master, *args, **kwargs )
		self.mainTab = mainTab

	def create_contents( self ):
		button = ttk.Button( self._tipwindow, text='Edit', width=6, command=self.mainTab.updateSongBehavior )
		button.bind( "<Leave>", self.leave, '+' )
		button.pack()

	def _show( self ):
		# Hide any other tooltips currently shown
		for toolTip in self.mainTab.toolTips.values():
			if toolTip._tipwindow and toolTip != self:
				toolTip._unschedule()
				toolTip._hide()

		super( ToolTipButton, self )._show()