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
import tkFileDialog
import Tkinter as Tk

from binascii import hexlify
from PIL import Image, ImageTk

# Internal dependencies
import globalData
import FileSystem

from ScrolledText import ScrolledText
from basicFunctions import createFolders, grammarfyList, printStatus, reverseDictLookup, uHex, humansize, msg, getFileMd5, validHex
from tplCodec import TplEncoder


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


def exportSingleFileWithGui( fileObj, master=None ):

	""" Exports a single file, while prompting the user on where they'd like to save it. 
		Updates the default directory to search in when opening or exporting files. 
		Also handles updating the GUI with the operation's success/failure status. """

	if not master:
		master = globalData.gui.root
	
	# Prompt for a place to save the file.
	fileExt = fileObj.ext[1:] # Removing dot
	savePath = tkFileDialog.asksaveasfilename(
		title="Where would you like to export the file?",
		parent=master,
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
		globalData.gui.updateProgramStatus( 'File exported successfully', success=True )
		globalData.gui.playSound( 'menuChange' )
		return savePath
	else:
		globalData.gui.updateProgramStatus( 'Unable to export. Check the error log file for details', error=True )
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


def exportSingleTexture( defaultFilename, texture=None, fileObj=None, textureOffset=-1 ):

	""" Exports a single texture, while prompting the user on where they'd like to save it. 
		The 'defaultFilename' argument should include a file extension (typically .png). 
		The 'texture' argument should be a PIL image, or a fileObject plus texture offset must be given. 
		Updates the default directory to search in when opening or exporting files. 
		Also handles updating the GUI with the operation's success/failure status. """	

	# Prompt for a place to save the file. (Excluding defaultextension arg to give user more control, as it may silently append ext in some cases)
	savePath = tkFileDialog.asksaveasfilename(
		title="Where would you like to export the file?",
		parent=globalData.gui.root,
		initialdir=globalData.getLastUsedDir( 'dat' ), # Assuming this texture will be saved with its dat
		initialfile=defaultFilename,
		filetypes=[( "PNG files", '*.png' ), ("TPL files", '*.tpl' ), ( "All files", "*.*" )] )

	# The above will return an empty string if the user canceled
	if not savePath: return ''

	# Update the default directory to start in when opening or exporting files.
	globalData.setLastUsedDir( directoryPath, 'dat' )

	# Make sure folders exist for the chosen destination
	directoryPath = os.path.dirname( savePath ) # Used at the end of this function
	createFolders( directoryPath )

	# Get the texture if it wasn't provided
	if not texture:
		if not fileObj or textureOffset == -1:
			raise Exception( 'Invalid input to exportSingleTexture; no texture or fileObj/textureOffset provided.' )

		texture = fileObj.getTexture( textureOffset, getAsPilImage=True )

	# Convert the image into TPL format or save it as-is
	if savePath.lower().endswith( '.tpl' ):
		texture = texture.convert( 'RGBA' ) # Returns a modified image without affecting the original

		newImage = TplEncoder( '', texture.size, 0 )
		newImage.imageDataArray = texture.getdata()
		newImage.rgbaPaletteArray = texture.getpalette()

		returnCode = newImage.createTplFile( savePath )
	else:
		try:
			texture.save( savePath )
			returnCode = 0
		except ValueError as err:
			returnCode = 3
			print( 'ValueError during PIL image saving: ' + str(err) )
		except IOError as err:
			print( 'IOError during PIL image saving: ' + str(err) )
			returnCode = 2
		except Exception as err: # For everything else
			print( 'Exception during PIL image saving: ' + str(err) )
			returnCode = -1

	if returnCode == 0:
		globalData.gui.updateProgramStatus( 'File exported successfully', success=True )
	elif returnCode == 1:
		msg( 'Unable to export due to a TPL encoding error. Check the error log file for details.', 'Export Error' )
		globalData.gui.updateProgramStatus( 'Unable to encode the TPL image. Check the error log file for details', error=True )
	elif returnCode == 2:
		msg( 'Unable to save the image file. Be sure that this program has write permissions to the destination.', 'Export Error' )
		globalData.gui.updateProgramStatus( 'Unable to save the image file. Be sure that this program has write permissions to the destination', error=True )
	elif returnCode == 3:
		msg( 'Unable to save the PIL image. This may be due to an unsupported image file format. Try using a different file extension.', 'Export Error' )
		globalData.gui.updateProgramStatus( 'Unable to export. This may be due to an unsupported image file extension', error=True )
	else: # Failsafe; not expected to be possible
		msg( 'Unable to export the image due to an unknown error. Check the error log file for details.', 'Export Error' )
		globalData.gui.updateProgramStatus( 'Unable to export the image due to an unknown error', error=True )

	return returnCode

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
		self.className = self.__class__.__name__
		if unique:
			assert topLevel, 'Only windows with a parent may be unique!'

			# Bring into view an existing instance of this window, if already present
			if hasattr( topLevel, 'uniqueWindows' ):
				existingWindow = topLevel.uniqueWindows.get( self.className )
				if existingWindow:
					try:
						# The window already exist. Make sure it's not minimized, and bring it to the foreground
						existingWindow.window.deiconify()
						existingWindow.window.lift()
						return False # Can use this to determine whether child classes using 'unique' should continue with their init method
					except: # Failsafe against bad window name (existing window somehow destroyed without proper clean-up); move on to create new instance
						topLevel.uniqueWindows[self.className] = None
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

		# Override the 'X' close button functionality (all cancel methods should also call close when they're done)
		cancelMethod = getattr( self, "cancel", None )
		if cancelMethod and callable( cancelMethod ):
			self.window.protocol( 'WM_DELETE_WINDOW', self.cancel )
		else:
			self.window.protocol( 'WM_DELETE_WINDOW', self.close )
		
		if unique:
			topLevel.uniqueWindows[self.className] = self

		return True

	def close( self ):
		# Delete reference to this window if it's meant to be a unique instance, and then destroy the window
		topLevel = self.window.master
		if hasattr( topLevel, 'uniqueWindows' ):
			topLevel.uniqueWindows[self.className] = None
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


class CharacterColorChooser( BasicWindow ):

	""" Prompts the user to choose a color slot for a given character. This references external character ID and 
		costume ID, the latter of which will be returned when this window closes. 
		This window will block the main interface until a selection is made. """

	def __init__( self, charId, message='', master=None ):

		if not master:
			master = globalData.gui.root

		BasicWindow.__init__( self, master, 'Select a Character Color Slot', offsets=(300, 300) )
		
		self.emptySelection = '- - -'
		self.charId = charId # External ID
		self.costumeId = -1

		if message: # Optional user message
			ttk.Label( self.window, text=message, wraplength=500 ).pack( padx=14, pady=(12, 0) )
		
		# Get the character and costume color abbreviations for the chosen character
		charAbbreviation = globalData.charAbbrList[self.charId]
		self.costumeSlots = globalData.costumeSlots[charAbbreviation]

		# Format the color options with human-readable names
		costumeOptions = [ '{}  ({})'.format(abbr, globalData.charColorLookup.get(abbr, 'N/A')) for abbr in self.costumeSlots ]
		
		colorChoice = Tk.StringVar()
		self.colorDropdown = ttk.OptionMenu( self.window, colorChoice, self.emptySelection, *costumeOptions, command=self.colorSelected )
		self.colorDropdown.pack( pady=(4, 0) )

		buttonFrame = ttk.Frame( self.window )
		ttk.Button( buttonFrame, text='Confirm', command=self.close ).grid( column=0, row=0, padx=6 )
		ttk.Button( buttonFrame, text='Cancel', command=self.cancel ).grid( column=1, row=0, padx=6 )
		buttonFrame.pack( padx=20, pady=(4, 12) )

		# Make this window modal (will not allow the user to interact with main GUI until this is closed)
		self.window.grab_set()
		globalData.gui.root.wait_window( self.window )

	def colorSelected( self, selectedOption ):

		""" Called when the user changes the current selection. Sets the currently 
			selected character ID, and populates the costume color drop-down. """

		self.costumeId = self.costumeSlots.index( selectedOption.split()[0] )
		self.close()

	def cancel( self ):
		self.costumeId = -1
		self.close()


class AnimationChooser( BasicWindow ):

	""" Prompts the user to choose an animation (names taken from a given Pl__AJ.dat file). 
		This window will block the main interface until a selection is made. """

	def __init__( self, animFile, charFile, message='' ):

		BasicWindow.__init__( self, globalData.gui.root, 'Select an Animation', offsets=(300, 150), resizable=True )
		
		self.listboxIndices = {} # Key = listboxIndex, value = animationIndex
		self.animOffset = -1
		self.gameName = ''
		self.friendlyName = ''
		self.animSize = -1

		if message: # Optional user message
			ttk.Label( self.window, text=message, wraplength=500 ).grid( column=0, columnspan=2, row=0 )

		# Initialize the character files if it has not already been done
		self.animFile = animFile
		self.charFile = charFile
		animFile.initialize()
		charFile.initialize()
		
		filtersBox = ttk.Frame( self.window )
		ttk.Checkbutton( filtersBox, text='Attacks', variable=globalData.boolSettings['actionStateFilterAttacks'], command=self.updateFilters ).grid( column=0, row=0, sticky='w' )
		ttk.Checkbutton( filtersBox, text='Movement', variable=globalData.boolSettings['actionStateFilterMovement'], command=self.updateFilters ).grid( column=0, row=1, sticky='w' )
		ttk.Checkbutton( filtersBox, text='Item Related', variable=globalData.boolSettings['actionStateFilterItems'], command=self.updateFilters ).grid( column=1, row=0, sticky='w', padx=(10, 0) )
		ttk.Checkbutton( filtersBox, text='Character Specific', variable=globalData.boolSettings['actionStateFilterCharSpecific'], command=self.updateFilters ).grid( column=1, row=1, sticky='w', padx=(10, 0) )
		#ttk.Checkbutton( filtersBox, text='Empty Entries', variable=globalData.boolSettings['actionStateFilterEmpty'], command=self.updateFilters ).grid( column=2, row=0, sticky='w', padx=(8, 0) )
		filtersBox.grid( column=0, columnspan=2, row=1, pady=4 )

		# Add the action table list and its scrollbar
		subActionScrollBar = Tk.Scrollbar( self.window, orient='vertical' )
		self.subActionList = Tk.Listbox( self.window, width=44, height=30, yscrollcommand=subActionScrollBar.set, 
										activestyle='none', selectbackground='#78F', exportselection=0, font=('Consolas', 9) )
		self.populate()
		subActionScrollBar.config( command=self.subActionList.yview )
		self.subActionList.bind( '<<ListboxSelect>>', self.animationSelected )
		self.subActionList.grid( column=0, row=2, sticky='ns' )
		subActionScrollBar.grid( column=1, row=2, sticky='ns' )

		buttonFrame = ttk.Frame( self.window )
		ttk.Button( buttonFrame, text='Confirm', command=self.close ).grid( column=0, row=0, padx=6 )
		ttk.Button( buttonFrame, text='Cancel', command=self.cancel ).grid( column=1, row=0, padx=6 )
		buttonFrame.grid( column=0, columnspan=2, row=3, pady=4 )

		self.window.columnconfigure( 0, weight=1 )
		self.window.rowconfigure( 1, weight=1 )

		# Make this window modal (will not allow the user to interact with main GUI until this is closed)
		self.window.grab_set()
		globalData.gui.root.wait_window( self.window )

	def updateFilters( self ):

		""" Repopulates action states shown in the left-side listbox, 
			according to the current filters, and saves current settings. 
			Called by the filter checkboxes in the GUI when toggled. """

		self.populate()
		globalData.saveProgramSettings()

	def populate( self ):

		""" Clears the subAction list (if it has anything displayed) and 
			repopulates it with entries from the character's action table. """

		# Remember the current (soon to be previous) selection
		selection = self.subActionList.curselection()
		if selection:
			lastSelectedEntry = self.listboxIndices.get( selection[0], (-1, '', '', -1) )
		else:
			lastSelectedEntry = (-1, '', '', -1)
		
		self.listboxIndices = {} # Key = listboxIndex, value = animationIndex

		showAttacks = globalData.checkSetting( 'actionStateFilterAttacks' )
		showMovement = globalData.checkSetting( 'actionStateFilterMovement' )
		showItems = globalData.checkSetting( 'actionStateFilterItems' )
		showCharSpecific = globalData.checkSetting( 'actionStateFilterCharSpecific' )

		# Build a list of the character-specific action names
		self.charSpecificActions = []
		actionTable = self.charFile.getActionTable()
		for entryIndex, values in actionTable.iterateEntries():
			if entryIndex < 0x127: continue
			
			namePointer = values[0]
			if namePointer != 0:
				symbol = self.charFile.getString( namePointer ) # e.g. 'PlyCaptain5K_Share_ACTION_AttackS3S_figatree'
				actionName = symbol.split( '_' )[3] # e.g. 'AttackS3S'
				self.charSpecificActions.append( actionName )

		# Repopulate the subAction list
		self.subActionList.delete( 0, 'end' )
		listboxIndex = 0
		for anim in self.animFile.animations:
			gameName, friendlyName = self.animFile.getFriendlyActionName( anim.name )
			nameStart = gameName[:4]

			# Apply filters and skip unwanted actions
			if not showAttacks:
				if nameStart in ( 'Atta', 'Catc', 'Thro' ) or gameName.startswith( 'DownAttack' ):
					continue
				elif gameName.startswith( 'CliffAttack' ):
					continue
				
				# Check for certain 'Taro' moves, like Koopa Klaw and Kong Karry
				if gameName.startswith( 'T' + self.animFile.nickname ):
					continue
				
			if not showMovement:
				if nameStart in ( 'Wall', 'Dama', 'Wait', 'Walk', 'Turn', 'Dash', 'Run', 'RunB', 'Land' ):
					continue
				elif nameStart in ( 'Jump', 'Fall', 'Squa', 'Guar', 'Esca', 'Rebo', 'Down', 'Pass' ):
					if not gameName.startswith( 'DownAttack' ):
						continue
				elif nameStart in ( 'Fura', 'Otto', 'Stop', 'Miss', 'Clif', 'Entr', 'Appe', 'Capt' ):
					if not gameName.startswith( 'CliffAttack' ):
						continue

			if not showItems:
				if nameStart in ( 'Ligh', 'Heav', 'Swin', 'Item' ):
					continue

			if not showCharSpecific and gameName in self.charSpecificActions:
				continue

			# Add the action to the listbox
			if friendlyName:
				spaces = ' ' * ( 42 - (len(friendlyName) + len(gameName)) )
				line = ' {}{}{}'.format( friendlyName, spaces, gameName )
				self.subActionList.insert( listboxIndex, line )
			else:
				self.subActionList.insert( listboxIndex, ' ' + gameName )
			self.listboxIndices[listboxIndex] = ( anim.offset, gameName, friendlyName, anim.size )
			listboxIndex += 1

		# Clear current selection, and then select the same item that was selected before (if it's still present)
		self.subActionList.selection_clear( 0, 'end' )
		if lastSelectedEntry[0] != -1 and lastSelectedEntry in self.listboxIndices.values():
			listboxIndex = reverseDictLookup( self.listboxIndices, lastSelectedEntry )
			self.subActionList.selection_set( listboxIndex )
			self.subActionList.see( listboxIndex )

	def animationSelected( self, guiEvent ):

		""" Called when the user changes the current selection. Sets the currently 
			selected character ID, and populates the costume color drop-down. """
		
		selection = self.subActionList.curselection()
		if not selection:
			return

		self.animOffset, self.gameName, self.friendlyName, self.animSize = self.listboxIndices.get( selection[0], (-1, '', '', -1) )

	def cancel( self ):
		self.animOffset = -1
		self.gameName = ''
		self.friendlyName = ''
		self.animSize = -1
		self.close()


def cmsg( message, title='', align='center', buttons=None, makeModal=False, parent=None ):

	""" Simple helper function to display a small, windowed message to the user, with text that can be selected/copied. 
		This will instead print out to console if the GUI has not been initialized. 

		Alignment may be left/center/right. Buttons may be a list of (buttonText, buttonCommand) tuples. 
		If modal, the window will take program focus and not allow it to be returned until the window is closed. """
	
	if globalData.gui:
		# Define the parent window to appear over
		if not parent:
			parent = globalData.gui.root
		CopyableMessageWindow( parent, message, title, align, buttons, makeModal )
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
		self.buttonsFrame = Tk.Frame( self.window )
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
		self.label.pack( padx=8, pady=8 )

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
		#self.window.destroy()
		self.close()

	def cancel( self, event='' ):
		self.entryText = ''
		#self.window.destroy()
		self.close()


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

	""" Used for struct hex or value display and editing. 
		"dataOffsets" will typically be a single int value, but may also be a list of offsets. """

	def __init__( self, parent, targetFile, dataOffsets, byteLength, formatting, updateName='', valueEntry=False ):
		# Determine if the target data has already been modified, and set this widget's background color accordingly
		if type( dataOffsets ) == list:
			for offset in dataOffsets:
				if offset in targetFile.offsetsModified:
					bgColor = '#faa'
					break
			else: # The loop above didn't break; offset not found
				bgColor = '#fff'
		elif dataOffsets in targetFile.offsetsModified:
			bgColor = '#faa'
		else:
			bgColor = '#fff'
		
		Tk.Entry.__init__( self, parent,
			width=byteLength*2+2, 
			justify='center', 
			relief='flat', 
			background=bgColor,
			highlightbackground='#b7becc', 	# Border color when not focused
			borderwidth=1, 
			highlightthickness=1, 
			highlightcolor='#0099f0' )

		self.fileObj	= targetFile
		self.offsets	= dataOffsets		# May be a single file offset (int), or a list of them
		self.byteLength = byteLength
		self.formatting = formatting
		
		if updateName:
			self.updateName = updateName.replace( '\n', ' ' )
		elif type( dataOffsets ) == list:
			offsets = [uHex(0x20+o) for o in dataOffsets] # Cast to uppercase string and adjust for header offset
			self.updateName = 'Offsets ' + grammarfyList( offsets )
		else:
			self.updateName = 'Offset ' + uHex( 0x20 + dataOffsets )

		# Optional widgets that this may be paired with
		self.hexEntryWidget = None			# Used by HexEditEntry widgets for hex data
		self.valueEntryWidget = None		# Used by HexEditEntry widgets for values
		self.colorSwatchWidget = None

		if valueEntry:
			self.bind( '<Return>', self.updateValue )
		else:
			self.bind( '<Return>', self.updateHex )

	def updateDataInFile( self, newData ):
		
		""" Replaces the data in the file for each offset location. """

		if type( self.offsets ) == list:
			for offset in self.offsets:
				updateName = 'Offset ' + uHex( 0x20 + offset )
				descriptionOfChange = updateName + ' modified in ' + self.fileObj.filename
				self.fileObj.updateData( offset, newData, descriptionOfChange )
		else:
			# The offsets attribute is just a single value (the usual case)
			descriptionOfChange = self.updateName + ' modified in ' + self.fileObj.filename
			self.fileObj.updateData( self.offsets, newData, descriptionOfChange )

	def updateHex( self, event ):

		""" Validates widget input, checks if it's new/different from what's in the file, 
			and updates the data in the file if it differs. Also triggers updating of any paired widgets. """

		# Validate the input
		newHex = self.get().zfill( self.byteLength * 2 ).upper() # Pads the string with zeroes to the left if not enough characters
		if not validHex( newHex ):
			msg( 'The entered text is not valid hexadecimal!' )
			return

		# Confirm whether updating is necessary by checking if this is actually new data for any of the offset locations
		if type( self.offsets ) == list:
			for offset in self.offsets:
				currentFileHex = hexlify( self.fileObj.getData(offset, self.byteLength) ).upper()
				if currentFileHex != newHex: # Found a difference
					break
			else: # The loop above didn't break; no change found
				return # No change to be updated
		else: # The offsets attribute is just a single value (the usual case)
			currentFileHex = hexlify( self.fileObj.getData(self.offsets, self.byteLength) ).upper()
			if currentFileHex == newHex:
				return # No change to be updated

		# Get the data as a bytearray, and check for other GUI compoenents that may need to be updated
		newData = bytearray.fromhex( newHex )
		decodedValue = None

		if len( newData ) != self.byteLength: # Due to the zfill above, this should only happen if the hex entry is too long
			msg( 'The new value must be {} characters ({} bytes) long.'.format(self.byteLength*2, self.byteLength) )
			return
		elif self.valueEntryWidget and self.formatting:
			# Check that the appropriate value can be decoded from this hex (if formatting is available)
			try:
				decodedValue = struct.unpack( '>' + self.formatting, newData )
			except Exception as err:
				# Construct and display an error message for the user
				dataTypes = { 	'?': 'a boolean', 'b': 'a signed character', 'B': 'an unsigned character', 	# 1-byte
								'h': 'a signed short (halfword)', 'H': 'an unsigned short',				# 2-bytes
								'i': 'a signed integer', 'I': 'an unsigned integer', 'f': 'a float' } # 4-bytes
				if self.formatting in dataTypes:
					expectedLength = struct.calcsize( self.formatting )
					msg( 'The entered value is invalid for {} value (should be {} byte(s) long).'.format( dataTypes[self.formatting], expectedLength ) )
				else: # I tried
					msg( 'The entered value is invalid.' )
				print( 'Error encountered unpacking hex entry data; {}'.format(err) )
				return

		# Change the background color of the widget, to show that changes have been made to it and are pending saving.
		self.configure( background='#faa' )

		# If this entry has a color swatch associated with it, redraw it
		if self.colorSwatchWidget:
			self.colorSwatchWidget.renderCircle( newHex )

		# Add the widget to a list, to keep track of what widgets need to have their background restored to white when saving.
		# global editedDatEntries
		# editedDatEntries.append( widget )

		# Update the hex shown in the widget (in case the user-entered value was zfilled; i.e. was not long enough)
		self.delete( 0, 'end' )
		self.insert( 0, newHex )

		# Update the data shown in the neighboring, decoded value widget
		if decodedValue:
			self.valueEntryWidget.delete( 0, 'end' )
			self.valueEntryWidget.insert( 0, decodedValue )
			self.valueEntryWidget.configure( background='#faa' )
			#editedDatEntries.append( self.valueEntryWidget )

		self.updateDataInFile( newData )

		globalData.gui.updateProgramStatus( self.updateName + ' updated' )

	def updateValue( self, event ):

		""" Validates widget input, checks if it's new/different from what's in the file, 
			and updates the data in the file if it differs. Also triggers updating of any paired widgets. """

		# if event.__class__ == HexEditDropdown:
		# 	widget = event
		# else:
		# 	widget = event.widget

		# Validate the entered value by making sure it can be correctly encoded
		try:
			formatting = self.formatting

			if formatting == 'f':
				newHex = hexlify( struct.pack( '>f', float(self.get()) ) ).upper()
			else:
				newHex = hexlify( struct.pack( '>' + formatting, int(self.get()) ) ).upper()
		except Exception as err:
			# Construct and display an error message for the user
			dataTypes = { 	'?': 'a boolean', 'b': 'a signed character', 'B': 'an unsigned character', 	# 1-byte
							'h': 'a signed short (halfword)', 'H': 'an unsigned short',				# 2-bytes
							'i': 'a signed integer', 'I': 'an unsigned integer', 'f': 'a float' } # 4-bytes
			if formatting in dataTypes:
				msg( 'The entered value is invalid for {} value.'.format( dataTypes[formatting] ) )
			else: # I tried
				msg( 'The entered value is invalid.' )
			print( 'Error encountered packing value entry data; {}'.format(err) )
			return

		# Confirm whether updating is necessary by checking if this is actually new data for any of the offset locations
		if type( self.offsets ) == list:
			for offset in self.offsets:
				currentFileHex = hexlify( self.fileObj.getData(offset, self.byteLength) ).upper()
				if currentFileHex != newHex: # Found a difference
					break
			else: # The loop above didn't break; no change found
				return # No change to be updated
		else: # The offsets attribute is just a single value (the usual case)
			currentFileHex = hexlify( self.fileObj.getData(self.offsets, self.byteLength) ).upper()
			if currentFileHex == newHex:
				return # No change to be updated

		# Change the background color of the widget, to show that changes have been made to it and are pending saving.
		# if event.__class__ == HexEditDropdown:
		# 	self.configure( style='Edited.TMenubutton' )
		# else:
		self.configure( background='#faa' )

		# Add the widget to a list, to keep track of what widgets need to have their background restored to white when saving.
		# global editedDatEntries
		# editedDatEntries.append( self )

		# Update the data shown in the neiboring widget
		if self.hexEntryWidget:
			self.hexEntryWidget.delete( 0, 'end' )
			self.hexEntryWidget.insert( 0, newHex )
			self.hexEntryWidget.configure( background='#faa' )
			#editedDatEntries.append( hexEntryWidget )

		# Replace the data in the file for each location
		newData = bytearray.fromhex( newHex )
		self.updateDataInFile( newData )

		globalData.gui.updateProgramStatus( self.updateName + ' updated' )


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


class ClickText( ttk.Label ):

	""" Clickable text/label, colored blue with a hover cursor to indicate to the user it's clickable. """
	
	def __init__( self, parent, text, callback, *args, **kwargs ):

		# Initialize the label with one of the above images
		ttk.Label.__init__( self, parent, text=text, foreground='#00F', cursor='hand2', *args, **kwargs )

		self.callback = callback

		self.bind( '<1>', callback )


class LabelButton( ttk.Label ):

	""" Basically a label that acts as a button, using an image and mouse click/hover events. 
		Expects RGBA images named '[name].png' and '[name]Gray.png' (if the default image 
		variation doesn't exist, the Gray variation will be used for both default and hover). 
		The latter is used for the default visible state, and the former is used on mouse hover.
		Example uses of this class are for a mod's edit/config buttons and web links. """

	def __init__( self, parent, imageName, callback, hovertext='', *args, **kwargs ):
		# Get the images needed
		if imageName:
			self.defaultImage = globalData.gui.imageBank( imageName + 'Gray', showWarnings=False )
			self.hoverImage = globalData.gui.imageBank( imageName )
			assert self.hoverImage, 'Unable to get the {}Gray button image.'.format( imageName )
			if not self.defaultImage:
				self.defaultImage = self.hoverImage
		else:
			self.defaultImage = None
			self.hoverImage = None
		self.callback = callback
		self.toolTip = None
		self.isHovered = False

		# Initialize the label with one of the above images
		ttk.Label.__init__( self, parent, image=self.defaultImage, cursor='hand2', *args, **kwargs )

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
			

class ToggleButton( ttk.Label ):

	""" Similar to a LabelButton, but toggles between states on click (indicated by images). 
		Expects RGBA images named '[name]State1.png' and '[name]State2.png' (if the default image 
		variation doesn't exist, the Gray variation will be used for both default and hover). 
		The latter is used for the default visible state, and the former is used on mouse hover.
		Example uses of this class are for a mod's edit/config buttons and web links. """

	def __init__( self, parent, imageName, callback, hovertext='', *args, **kwargs ):
		# Get the images needed
		self.imageState1 = globalData.gui.imageBank( imageName + 'State1', showWarnings=False )
		self.imageState2 = globalData.gui.imageBank( imageName + 'State2', showWarnings=False )
		assert self.imageState1, 'Unable to get the {}State1 button image.'.format( imageName )
		assert self.imageState2, 'Unable to get the {}State2 button image.'.format( imageName )
		self.callback = callback
		self.toolTip = None
		self.enabled = False

		# Initialize the label with one of the above images
		ttk.Label.__init__( self, parent, image=self.imageState1, cursor='hand2', *args, **kwargs )

		# Bind click event
		self.bind( '<1>', self.toggle )

		if hovertext:
			self.updateHovertext( hovertext )

	def toggle( self, event=None ):
		if self.enabled:
			self.configure( image=self.imageState1 )
			self.enabled = False
		else:
			self.configure( image=self.imageState2 )
			self.enabled = True

		#self.enabled = not self.enabled
		self.callback()

	def updateHovertext( self, newText ):
		if self.toolTip:
			self.toolTipVar.set( newText )
		else:
			self.toolTipVar = Tk.StringVar( value=newText )
			self.toolTip = ToolTip( self, textvariable=self.toolTipVar, delay=700, wraplength=800, justify='center' )


class ColoredLabelButton( LabelButton ):

	""" Like the LabelButton, but uses a single source image which is then 
		programmatically colored for the hover state. The image should be an 8-bit 
		grayscale image (single-channel with no alpha; "8bpc GRAY" in GIMP)."""

	def __init__( self, parent, imageName, callback, hovertext='', color='#0099f0' ):

		LabelButton.__init__( self, parent, None, callback, hovertext )

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

		if not default:
			default = options[0]
		if not variable:
			variable = Tk.StringVar()
		self.command = command

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

	def __init__( self, parent, defaultHeight=700, *args, **kw ):
		Tk.Frame.__init__( self, parent, *args, **kw )

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

		# Set the current selections and set scroll position back to what it was
		try:
			self.selection_set( self.selectionState )
			self.focus( self.focusState )
			if self.scrollbar:
				self.yview_moveto( self.scrollState )
		except: # Prior selections might not exist
			pass

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


class DDListItem( ttk.Frame ):

	""" Used with the DDList class to create a list interface with drag-and-drop ordering capability. """

	def __init__(self, master, value, width, height, selection_handler=None, drag_handler=None, drop_handler=None, **kwargs):

		kwargs.setdefault("class_", "DDListItem")
		ttk.Frame.__init__(self, master, **kwargs)
		
		self._x = None
		self._y = None
		
		self._width = width
		self._height = height

		self._tag = "item%s"%id(self)
		self._value = value

		self._selection_handler = selection_handler
		self._drag_handler = drag_handler
		self._drop_handler = drop_handler

	@property
	def x(self):
		return self._x
		
	@property
	def y(self):
		return self._y
		
	@property
	def width(self):
		return self._width

	@property
	def height(self):
		return self._height

	@property
	def value(self):
		return self._value
		
	def init(self, container, x, y):
		self._x = x
		self._y = y

		self.place(in_=container, x=x, y=y, width=self._width, height=self._height)

		self.bind_class(self._tag, "<ButtonPress-1>", self._on_selection, '+')
		self.bind_class(self._tag, "<B1-Motion>", self._on_drag, '+')
		self.bind_class(self._tag, "<ButtonRelease-1>", self._on_drop, '+')

		self._add_bindtag(self)
		
		# Python3 compatibility: dict.values() return a view
		list_of_widgets = list(self.children.values())
		while len(list_of_widgets) != 0:
			widget = list_of_widgets.pop()
			list_of_widgets.extend(widget.children.values())
			
			self._add_bindtag(widget)
	
	def _add_bindtag(self, widget):
		bindtags = widget.bindtags()
		if self._tag not in bindtags:
			widget.bindtags((self._tag,) + bindtags)

	def _on_selection(self, event):
		self.tkraise() # Show on top of other widgets

		self._move_lastx = event.x_root
		self._move_lasty = event.y_root
		
		if self._selection_handler:
			self._selection_handler(self)

	def _on_drag(self, event):
		self.master.update_idletasks()
		
		cursor_x = self._x + event.x
		cursor_y = self._y + event.y

		self._x += event.x_root - self._move_lastx
		self._y += event.y_root - self._move_lasty

		self._move_lastx = event.x_root
		self._move_lasty = event.y_root

		self.place_configure(x=self._x, y=self._y)

		if self._drag_handler:
			self._drag_handler( self, cursor_x, cursor_y)

	def _on_drop(self, event):
		if self._drop_handler:
			self._drop_handler()
			
	def set_position(self, x,y):
		self._x = x
		self._y = y
		self.place_configure(x =x, y =y)
		
	def move(self, dx, dy):
		self._x += dx
		self._y += dy

		self.place_configure(x =self._x, y =self._y)

class DDList( ttk.Frame ):

	""" Used to create a list interface with drag-and-drop ordering capability. 
		Originally created by Miguel Martinez. Modified to allow width/height 
		resizing after initialization and items added, as well as other features.

		Source: https://code.activestate.com/recipes/580717-sortable-megawidget-in-tkinter-like-the-sortable-w/ """

	def __init__(self, master, item_width, item_height, item_relief=None, item_borderwidth=None, item_padding=None, item_style=None, reorder_callback=None, offset_x=0, offset_y=0, gap=0, **kwargs):
		kwargs["width"] = item_width + offset_x*2
		kwargs["height"] = offset_y*2

		ttk.Frame.__init__(self, master, **kwargs)

		self._item_borderwidth = item_borderwidth
		self._item_relief = item_relief
		self._item_padding = item_padding
		self._item_style = item_style
		self._item_width = item_width
		self._item_height = item_height
		
		self.reorder_callback = reorder_callback

		self._offset_x = offset_x
		self._offset_y = offset_y

		self._left = offset_x
		self._top = offset_y
		self._right = offset_x + self._item_width
		self._bottom = offset_y

		self._gap = gap

		self._index_of_selected_item = None
		self._index_of_empty_container = None

		self._list_of_items = []
		self._position = {}

		globalData.gui.style.configure( 'SeletectedItem.TFrame', background='#78F', relief='flat' )
		globalData.gui.style.configure( 'NonSeletectedItem.TFrame', relief='groove' )

		self.master.bind( '<Configure>', self.update_width, '+' )

	def update_width(self, event=None):
		containerWidth = self.master.winfo_width()

		self._item_width = containerWidth - ( self._offset_x * 2 )
		for item in self._list_of_items:
			item.width = self._item_width
			item.place_configure(width=item.width)

		self._right = self._offset_x + self._item_width

		self.configure( width=containerWidth )

	def update_item_height(self, item, newHeight):

		# Adjust the height of this item
		difference = newHeight - item._height
		item._height = newHeight
		item.configure(height=newHeight)
		item.place_configure(height=newHeight)
		
		# Adjust positions of items below this one
		index = self._position[item] + 1
		if index < len( self._list_of_items ):
			for item in self._list_of_items[index:]:
				item._move_lasty = difference
				item.move(0, difference)
		
		# Adjust the height of this item list (container)
		self._bottom += difference
		self.configure(height=self._bottom+self._offset_y)

	def create_item(self, value=None, **kwargs):
		
		if self._item_relief is not None:
			kwargs.setdefault("relief", self._item_relief)
		
		if self._item_borderwidth is not None:
			kwargs.setdefault("borderwidth", self._item_borderwidth)
		
		if self._item_style is not None:
			kwargs.setdefault("style", self._item_style)
		else:
			kwargs.setdefault("style", 'NonSeletectedItem.TFrame')
		
		if self._item_padding is not None:
			kwargs.setdefault("padding", self._item_padding)

		item = DDListItem(self.master, value, self._item_width, self._item_height, self._on_item_selected, self._on_item_dragged, self._on_item_dropped, **kwargs)
		item.selected = False

		return item

	def configure_items(self, **kwargs):
		for item in self._list_of_items:
			item.configure(**kwargs)

	def add_item(self, item, index=None):
		if index is None:
			index = len(self._list_of_items)
		else:
			if not -len(self._list_of_items) < index < len(self._list_of_items):
				raise ValueError("Item index out of range")

			for i in range(index, len(self._list_of_items)):
				_item = self._list_of_items[i]
				_item.move(0, self._item_height + self._gap)
				
				self._position[_item] += 1
		
		x = self._offset_x
		y = self._offset_y + index * (self._item_height + self._gap)

		self._list_of_items.insert(index, item)
		self._position[item] = index

		item.init(self, x,y)

		if len(self._list_of_items) == 1:
			self._bottom += self._item_height
		else:
			self._bottom += self._item_height + self._gap
			
		self.configure(height=self._bottom+self._offset_y)

		return item

	def delete_item(self, index):
		
		if isinstance(index, DDListItem):
			index = self._position[index]
		else:
			if not -len(self._list_of_items) < index < len(self._list_of_items):
				raise ValueError("Item index out of range")

		item = self._list_of_items.pop(index)
		shrinkAmount = item._height + self._gap
		value = item.value

		del self._position[item]

		item.destroy()
		
		for i in range(index, len(self._list_of_items)):
			_item = self._list_of_items[i]
			_item.move(0, -shrinkAmount)
			self._position[_item] -= 1
		
		if len(self._list_of_items) == 0:
			self._bottom = self._offset_y
		else:
			self._bottom -= shrinkAmount

		self.configure(height=self._bottom+self._offset_y)
		
		return value

	del_item = delete_item

	def delete_all_items(self):
		
		for item in self._list_of_items:
			item.destroy()

		self._list_of_items = []
		self._position = {}

		self._bottom = self._offset_y
		self.configure(height=self._bottom+self._offset_y)
	
	def pop(self):
		return self.delete_item(-1)
		
	def shift(self):
		return self.delete_item(0)
		
	def append(self, item):
		self.add_item(item)
		
	def unshift(self, item):
		self.add_item(0, item)
		
	def get_item(self, index):
		return self._list_of_items[index]

	def get_value(self, index):
		return self._list_of_items[index].value

	def _on_item_selected(self, item):

		for _item in self._list_of_items:
			if self._item_style is not None:
				_item.configure(style=self._item_style)
			elif _item == item:
				_item.configure(style='SeletectedItem.TFrame')
				_item.selected = True
			else:
				_item.configure(style='NonSeletectedItem.TFrame')
				_item.selected = False

		self._index_of_selected_item = self._position[item]
		self._index_of_empty_container = self._index_of_selected_item

	def _on_item_dragged(self, item, x, y):

		if self._left < x < self._right and self._top < y < self._bottom:

			# Determine the current hovered index
			distance_from_top = self._offset_y
			for hovered_index, _item in enumerate( self._list_of_items ):
				distance_from_top += _item.height + self._gap
				if y < distance_from_top:
					remainder = distance_from_top - y
					break
			else:
				remainder = distance_from_top - y

			if remainder < item.height and hovered_index != self._index_of_empty_container:
				if hovered_index > self._index_of_empty_container:
					for index in range(self._index_of_empty_container+1, hovered_index+1, 1):
						_item = self._get_item_of_virtual_list(index)
						_item.move(0, -(item.height+self._gap))
				else:
					for index in range(self._index_of_empty_container-1, hovered_index-1, -1):
						_item = self._get_item_of_virtual_list(index)
						_item.move(0, item.height+self._gap)

				self._index_of_empty_container = hovered_index

	def _get_item_of_virtual_list(self, index):
		if self._index_of_empty_container == index:
			raise Exception("No item in index: %s"%index)
		else:
			if self._index_of_empty_container != self._index_of_selected_item:
				if index > self._index_of_empty_container:
					index -= 1

				if index >= self._index_of_selected_item:
					index += 1
			item = self._list_of_items[index]
			return item

	def _on_item_dropped(self):
		
		item = self._list_of_items.pop(self._index_of_selected_item)
		self._list_of_items.insert(self._index_of_empty_container, item)
		
		# Calculate new coordinates for the item being dropped
		x = self._offset_x
		y = self._offset_y
		for _item in self._list_of_items:
			if _item == item:
				break
			y += _item.height + self._gap
		
		item.set_position(x,y)

		lowerIndex = min( self._index_of_selected_item, self._index_of_empty_container )
		higherIndex = max( self._index_of_selected_item, self._index_of_empty_container )
		
		for i in range(lowerIndex, higherIndex+1):
			item = self._list_of_items[i]
			self._position[item] = i

		# Call reorder callback if this item's index has changed
		if self._index_of_selected_item != self._index_of_empty_container and self.reorder_callback:
			self.reorder_callback()

		self._index_of_empty_container = None
		self._index_of_selected_item = None