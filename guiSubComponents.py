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
import sys
import ttk
import time
import struct
import tkFont
import random
import webbrowser
import tkFileDialog
import Tkinter as Tk

from binascii import hexlify
from tkColorChooser import askcolor
from PIL import Image, ImageTk, ImageDraw, ImageOps

# Internal dependencies
import globalData
import FileSystem

from ScrolledText import ScrolledText
from basicFunctions import ( createFolders, grammarfyList, printStatus, 
							uHex, humansize, validHex, rgb2hex, hex2rgb, msg, getFileMd5, 
							validHex, constructTextureFilename )
from tplCodec import TplEncoder, TplDecoder


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
		newDir = os.path.normpath( newDir )

		if newDir != defaultDir: # Update and save the new directory if it's different
			globalData.setLastUsedDir( newDir, category, fileExt )

	else: # The above will return an empty string if the user canceled
		globalData.gui.updateProgramStatus( 'Operation canceled' )

	return filePaths


def importSingleFileWithGui( origFileObj, validate=True, title='' ):

	""" Prompts the user to choose an external/standalone file to import, and then 
		replaces the given file in the disc with the chosen file. 
		Updates the default directory to search in when opening or exporting files. 
		Also handles updating the GUI with the operation's success/failure status. 
		Returns True/False on success. """

	newFilePath = importGameFiles( origFileObj.ext, title=title )

	# Check if the user canceled; in which case the above will return an empty string
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
	globalData.gui.updateProgramStatus( 'File replaced. Awaiting save' )

	# Color the file in the Disc File Tree if that tab is open
	if globalData.gui.discTab:
		globalData.gui.discTab.isoFileTree.item( newFileObj.isoPath, tags='changed' )

	return True


def exportSingleTexture( defaultFilename, texture=None, fileObj=None, textureOffset=-1, imageType=-1 ):

	""" Exports a single texture, while prompting the user on where they'd like to save it. 
		The 'defaultFilename' argument should include a file extension (typically .png). 
		The 'texture' argument should be a PIL image, or a fileObject plus texture offset must be given. 
		Updates the default directory to search in when opening or exporting files. 
		Also handles updating the GUI with the operation's success/failure status. """

	# Get and validate the export format to be used.
	exportFormat = globalData.checkSetting( 'textureExportFormat' ).lower().replace( '.', '' )
	if exportFormat != 'png' and exportFormat != 'tpl':
		msg( 'The default export format setting (textureExportFormat) is invalid! '
			 'The format must be PNG or TPL. Check the settings.ini file to resolve this.' )
		return

	# Set up the drop-down list to save the file as a certain type
	if exportFormat == 'png': filetypes = [('PNG files', '*.png'), ('TPL files', '*.tpl'), ("All files", "*.*")]
	else: filetypes = [('TPL files', '*.tpl'), ('PNG files', '*.png'), ("All files", "*.*")]

	# Prompt for a place to save the file. (Excluding defaultextension arg to give user more control, as it may silently append ext in some cases)
	savePath = tkFileDialog.asksaveasfilename(
		title="Where would you like to export the file?",
		parent=globalData.gui.root,
		initialdir=globalData.getLastUsedDir( 'png' ),
		initialfile=defaultFilename,
		filetypes=filetypes )

	# The above will return an empty string if the user canceled
	if not savePath:
		return ''

	# Update the default directory to start in when opening or exporting files.
	globalData.setLastUsedDir( directoryPath, 'png' )

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
		#texture = texture.convert( 'RGBA' ) # Returns a modified image without affecting the original

		if imageType == -1:
			imageType = 0 #todo
			# Determine the image type
			# texture = texturesTab.file.structs.get( imageDataOffset )
			# width, height, imageType = texture.width, texture.height, texture.imageType

		newImage = TplEncoder( '', texture, imageType )
		# newImage.imageDataArray = texture.getdata()
		# newImage.rgbaPaletteArray = texture.getpalette()

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


def exportMultipleTextures( texturesTab, exportAll=False ):

	""" Exports some (what's selected) or all textures from the DAT Texture Tree of a specific file. """

	# Get a list of the items in the treeview to export
	datTextureTree = texturesTab.datTextureTree
	if exportAll:
		iidSelectionsTuple = datTextureTree.get_children()
	else:
		iidSelectionsTuple = datTextureTree.selection()

	# Make sure there are textures selected to export, and a file loaded to export from
	if not iidSelectionsTuple or not texturesTab.file:
		msg( 'No texture is selected.' )
		return

	# Get and validate the export format to be used.
	exportFormat = globalData.checkSetting( 'textureExportFormat' ).lower().replace( '.', '' )
	if exportFormat != 'png' and exportFormat != 'tpl':
		msg( 'The default export format setting (textureExportFormat) is invalid! '
			 'The format must be PNG or TPL. Check the settings.ini file to resolve this.' )
		return

	directoryPath = ''
	textureFilename = ''
	problemFiles = []
	workingFile = 1

	if len( iidSelectionsTuple ) == 1:
		# Get the texture struct and construct a default filename
		imageDataOffset = int( iidSelectionsTuple[0] )
		texture = texturesTab.file.structs.get( imageDataOffset )
		mipLevel = texturesTab.getMipmapLevel( iidSelectionsTuple[0] )
		defaultFilename = constructTextureFilename( texture, mipLevel )

		# Set up the drop-down list to save the file as a certain type
		if exportFormat == 'png': filetypes = [('PNG files', '*.png'), ('TPL files', '*.tpl'), ("All files", "*.*")]
		else: filetypes = [('TPL files', '*.tpl'), ('PNG files', '*.png'), ("All files", "*.*")]

		validExt = False
		while not validExt:
			# Prompt for a filename, and a place to save the file.
			savePath = tkFileDialog.asksaveasfilename(
				title="Where would you like to export the file?",
				initialdir=globalData.getLastUsedDir( 'png' ),
				initialfile=defaultFilename,
				defaultextension='.' + exportFormat,
				filetypes=filetypes )

			# Check the extension to see if it's valid (or just exit the loop if cancel was pressed).
			exportFormat = savePath[-3:].lower()
			if exportFormat == 'png' or exportFormat == 'tpl' or savePath == '': validExt = True
			else: msg( 'Textures may only be exported in PNG or TPL format.' )

		# If a path was given, get the directory chosen for the file
		if savePath:
			directoryPath = os.path.dirname( savePath )
			textureFilename = os.path.basename( savePath )

	else: # Multiple textures selected for export
		# Instead of having the user choose a file name and save location, have them choose just the save location.
		directoryPath = tkFileDialog.askdirectory(
			title='Where would you like to save these textures?',
			initialdir=globalData.getLastUsedDir( 'png' ),
			parent=globalData.gui.root,
			mustexist=True )

	if not directoryPath: # The dialog box was canceled
		return
	
	tic = time.time()
	#Gui.programStatus.set( 'Exporting Texture ' + str(workingFile) + '....' )

	for iid in iidSelectionsTuple:
		# Set us up the GUI
		printStatus( 'Exporting Texture ' + str(workingFile) + '...' )
		workingFile += 1

		# Collect data/info on this texture
		imageDataOffset = int( iid )
		texture = texturesTab.file.structs[imageDataOffset]
		width, height, imageType = texture.width, texture.height, texture.imageType
		imageData = texturesTab.file.getData( imageDataOffset, texture.imageDataLength )

		# Construct a filepath/location to save the image to
		if textureFilename: # May be a custom name from the user if only one texture is being exported.
			savePath = directoryPath + '/' + textureFilename
		else:
			mipLevel = texturesTab.getMipmapLevel( iid )
			savePath = directoryPath + '/' + constructTextureFilename( texture, mipLevel ) + '.' + exportFormat

		# Collect the palette data, if needed
		if imageType == 8 or imageType == 9 or imageType == 10:
			paletteData, paletteType = texturesTab.file.getPaletteData( imageDataOffset, imageData=imageData, imageType=imageType )
			if not paletteData:
				msg( 'A color palette could not be found for the texture at offset ' + uHex(0x20+imageDataOffset) + '. This texture will be skipped.' )
				continue
		else:
			paletteData = ''
			paletteType = None

		try: # Save the file to be exported
			if exportFormat == 'tpl':
				tplImage = TplEncoder( imageType=imageType, paletteType=paletteType )
				tplImage.width = width
				tplImage.height = height
				tplImage.encodedImageData = imageData
				tplImage.encodedPaletteData = paletteData
				tplImage.createTplFile( savePath )

			elif exportFormat == 'png': # Decode the image data
				pngImage = TplDecoder( '', (width, height), imageType, paletteType, imageData, paletteData )
				pngImage.deblockify()
				pngImage.createPngFile( savePath, creator='MMW - v' + globalData.programVersion )

		except Exception as err:
			print( 'Error during texture decoding/saving: {}'.format(err) )
			problemFiles.append( os.path.basename(savePath) )

	# Finished with file export/creation loop.
	print( 'time to complete exports: ' + str(time.time()-tic) )

	# Update the default directory to start in when opening or exporting files.
	globalData.setLastUsedDir( os.path.dirname(savePath), category='png' )

	# Give an error message for any problems encountered.
	if problemFiles:
		msg( "There was an unknown problem while exporting these files:\n\n" + '\n'.join(problemFiles), 'Export Error', error=True )
		successfulExports = len( iidSelectionsTuple ) - len( problemFiles )
		printStatus( 'Export Error; {} textures exported of {}'.format( successfulExports, len(iidSelectionsTuple)), error=True )
	else:
		printStatus( 'Export Successful', success=True )


def importSingleTexture( title='Choose a texture file to import (PNG or TPL)' ):

	# Prompt to select the file to import
	imagePath = tkFileDialog.askopenfilename( # Will return a unicode string (if one file selected), or a tuple
		title=title,
		parent=globalData.gui.root,
		initialdir=globalData.getLastUsedDir( 'png' ),
		filetypes=[ ('PNG files', '*.png'), ('TPL files', '*.tpl'), ('All files', '*.*') ],
		multiple=False
		)

	# The above will return an empty string if the user canceled
	if imagePath:
		# Update the default directory to start in when opening or exporting files
		globalData.setLastUsedDir( imagePath, 'png' )

	return imagePath


def importMultipleTextures():

	""" Prompt the user to select one or more textures from their system, 
		and return a list of those filepaths. """
		
	# Prompt to select the file(s) to import.
	textureFilepaths = tkFileDialog.askopenfilename( # Will return a unicode string (if one file selected), or a tuple
		title="Choose one or more texture files to import (PNG or TPL).",
		initialdir=globalData.getLastUsedDir( 'png' ),
		filetypes=[ ('PNG files', '*.png'), ('TPL files', '*.tpl'), ('All files', '*.*') ],
		multiple=True
	)

	if textureFilepaths:
		# Normalize the input into list form
		if not isinstance( textureFilepaths, list ) and not isinstance( textureFilepaths, tuple ): 
			textureFilepaths = [textureFilepaths]

		# Update the default directory to start in when opening or exporting files.
		globalData.setLastUsedDir( os.path.dirname(textureFilepaths[0]), 'png' )

		return textureFilepaths


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
		self.windowName = windowTitle
		if unique:
			assert topLevel, 'Only windows with a parent may be unique!'

			# Bring into view an existing instance of this window, if already present
			if hasattr( topLevel, 'uniqueWindows' ):
				existingWindow = topLevel.uniqueWindows.get( self.windowName )
				if existingWindow:
					try:
						# The window already exist. Make sure it's not minimized, and bring it to the foreground
						existingWindow.window.deiconify()
						existingWindow.window.lift()
						return False # Can use this to determine whether child classes using 'unique' should continue with their init method
					except: # Failsafe against bad window name (existing window somehow destroyed without proper clean-up); move on to create new instance
						topLevel.uniqueWindows[self.windowName] = None
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
			topLevel.uniqueWindows[self.windowName] = self

		return True

	def close( self ):
		# Delete reference to this window if it's meant to be a unique instance, and then destroy the window
		topLevel = self.window.master
		if hasattr( topLevel, 'uniqueWindows' ):
			topLevel.uniqueWindows[self.windowName] = None
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

	def __init__( self, animFile, charFile, message='', initialSelectionAnimOffset=-1 ):

		BasicWindow.__init__( self, globalData.gui.root, 'Select an Animation', offsets=(300, 150), resizable=True )
		
		self.listboxIndices = {} # Key = listboxIndex, value = ( anim.offset, gameName, friendlyName, anim.size )
		self.animOffset = -1
		self.gameName = ''
		self.friendlyName = ''
		self.animSize = -1
		self.currentAnimOffset = initialSelectionAnimOffset

		# Copy the current action state filters (use them as defaults rather than also changing the main program filters)
		self.showAttacks = Tk.BooleanVar()
		self.showMovement = Tk.BooleanVar()
		self.showItems = Tk.BooleanVar()
		self.showCharSpecific = Tk.BooleanVar()
		self.showAttacks.set( globalData.checkSetting('actionStateFilterAttacks') )
		self.showMovement.set( globalData.checkSetting('actionStateFilterMovement') )
		self.showItems.set( globalData.checkSetting('actionStateFilterItems') )
		self.showCharSpecific.set( globalData.checkSetting('actionStateFilterCharSpecific') )

		if message: # Optional user message
			ttk.Label( self.window, text=message, wraplength=500 ).grid( column=0, columnspan=2, row=0 )

		# Initialize the character files if it has not already been done
		self.animFile = animFile
		self.charFile = charFile
		animFile.initialize()
		charFile.initialize()
		
		filtersBox = ttk.Frame( self.window )
		ttk.Checkbutton( filtersBox, text='Attacks', variable=self.showAttacks, command=self.populate ).grid( column=0, row=0, sticky='w' )
		ttk.Checkbutton( filtersBox, text='Movement', variable=self.showMovement, command=self.populate ).grid( column=0, row=1, sticky='w' )
		ttk.Checkbutton( filtersBox, text='Item Related', variable=self.showItems, command=self.populate ).grid( column=1, row=0, sticky='w', padx=(10, 0) )
		ttk.Checkbutton( filtersBox, text='Character Specific', variable=self.showCharSpecific, command=self.populate ).grid( column=1, row=1, sticky='w', padx=(10, 0) )
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

	def populate( self ):

		""" Clears the subAction list (if it has anything displayed) and 
			repopulates it with entries from the character's action table. """

		showAttacks = self.showAttacks.get()
		showMovement = self.showMovement.get()
		showItems = self.showItems.get()
		showCharSpecific = self.showCharSpecific.get()

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
		self.listboxIndices = {} # Key = listboxIndex, value = ( anim.offset, gameName, friendlyName, anim.size )
		listboxIndex = 0
		newSelectionIndex = None
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

			# Check if this entry should be selected (was previously selected by the user)
			if self.animOffset == anim.offset:
				newSelectionIndex = listboxIndex
			
			# Color the animation currently set
			if self.currentAnimOffset == anim.offset:
				self.subActionList.itemconfigure( listboxIndex, background='#aeeaae' ) # Light green color
				
			listboxIndex += 1

		# Clear current selection, and then select the same item that was selected before (if it's still present)
		self.subActionList.selection_clear( 0, 'end' )
		if newSelectionIndex:
			self.subActionList.selection_set( newSelectionIndex )
			self.subActionList.see( newSelectionIndex )

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


class GeneralHelpWindow( BasicWindow ):

	proTips = {
		1: ( "Did you know that you can drag-and-drop files directly onto "
			"the program icon (the .exe file) or the GUI to open them?" ),

		2: ( "For CSPs (Character Select Portraits), if you're trying to mimic "
			"the game's original CSP shadows, they are 10px down and 10px to the left." ),

		3: ( "When working in GIMP and opting to use a palette, it's important that you delete "
			"ALL hidden and unused layers BEFORE generating a palette for your texture. "
			"This is because if other layers are present, even if not visible, GIMP "
			"will take their colors into consideration to generate the palette. (If you have a lot of "
			"layers, a simple option is to create a 'New from Visible' layer, and then copy it "
			"to a new, blank image before creating the palette.)" ),

		4: ( "Did you know that if you hold SHIFT while right-clicking on a file in Windows, "
			"there appears a context menu option called 'Copy as path'? This will copy the "
			"file's full path into your clipboard, so you can then easily paste "
			"it into one of this program's text fields, when needed." ),

		5: ( "Use the boost to chase!" ),

		6: ( "You don't have to close this program in order to run your disc in Dolphin (the disc file will not "
			'be write-locked). Tthough you do need to stop emulation if you want to save changes to the disc.' ),

		7: ( "Have you ever noticed those dotted lines at the top of the 'Open Recent' "
			"and 'Tools' menus? Try clicking on one sometime! It will turn the menu into a window for fast-access." ),

		8: ( "If you click on one of the 'Disc Shortcuts' before loading a disc, the program will load the "
			"last disc that you've used, and then jump to the appropriate section. They're two shortcuts in one!" ),

		9: ( "When MMW builds a disc from a root folder of files, it can build a ISO that's a good amount smaller than the "
			"standard disc size of ~1.35 GB (1,459,978,240 bytes). Useful if you want to add more or larger files. However, "
			"this is option, and can be enabled or disabled by the 'paddingBetweenFiles' setting. This can be set to a specific "
			"value, which MMW will attempt to honor, or to 'auto' to pad the disc to the standard size." ),

		10: ( "DODONGO DISLIKES SMOKE." ),

		11: ( 'You can actually modify the amount of empty space, or "padding", present between files in your ISO. A small '
			'amount of padding allows for more files or total data in the same size ISO. While more padding allows you to '
			'replace/import larger files without having to rebuild the disc.' ),

		12: ( "This program has a lot of lesser-known but very useful features, some of which aren't easily found "
			"by browsing the GUI. Check out the Program Usage.txt to find them all." )

		# 15: ( "Did you notice the cheese in the toilet? It's in every level." ),

		# 2: ( "There are multiple useful behaviors you can call upon when importing textures:"
		# 	"\n- When viewing the contents of a disc on the 'Disc File Tree' tab. The imported "
		# 	"texture's destination will be determined by the file's name. For example, "
		# 	'the file "MnSlMap.usd_0x38840_2.png" would be imported into the disc in the file "MnSlMap.usd" '
		# 	"at offset 0x38840. This can be very useful for bulk importing many textures at once."
		# 	"\n- Navigate to a specific texture in the 'DAT Texture Tree' tab, select a texture, and you "
		# 	'can import a texture to replace it with without concern for how the file is named.' ),

		# 8: ( 'A quick and easy way to view file structures relating to a given texture is to use '
		# 	'the "Show in Structural Analysis" feature, found by right-clicking on a texture.' ),

		#17: ( '' ),
		#18: ( '' ),
		#19: ( '' ),
		#20: ( "IT'S A SECRET TO EVERYBODY." ),
	}

	def __init__( self, *args, **kwargs ):
		# Set up the main window
		if not BasicWindow.__init__( self, globalData.gui.root, *args, unique=True, **kwargs ):
			return # If the above returned false, it displayed an existing window, so we should exit here

		divider = globalData.gui.imageBank( 'helpWindowDivider' )

		label = ttk.Label( self.window, text='- =  The Melee Workshop  = -', foreground='#00F', cursor='hand2' )
		label.bind( '<1>', self.gotoWorkshop )
		label.pack( pady=4 )

		gridSection = Tk.Frame( self.window )
		ttk.Label( gridSection, image=divider ).grid( column=0, row=0, columnspan=2 )
		label = ttk.Label( gridSection, text='Read Up on Program Usage', foreground='#00F', cursor='hand2', justify='center' )
		label.bind( '<1>', self.viewManual )
		label.grid( column=0, row=1 )
		ttk.Label( gridSection, text='Read the MMW Manual for usage documentation on this program', justify='center' ).grid( column=1, row=1 )

		ttk.Label( gridSection, image=divider ).grid( column=0, row=2, columnspan=2 )
		label = ttk.Label( gridSection, text='The Melee Workshop\nDiscord Server', foreground='#00F', cursor='hand2', justify='center' )
		label.bind( '<1>', self.gotoDiscord )
		label.grid( column=0, row=3 )
		ttk.Label( gridSection, text='Chat with other modders on a variety of modding subjects', justify='center' ).grid( column=1, row=3 )

		ttk.Label( gridSection, image=divider ).grid( column=0, row=4, columnspan=2 )
		label = ttk.Label( gridSection, text="MMW's Official Thread", foreground='#00F', cursor='hand2', justify='center' )
		label.bind( '<1>', self.gotoOfficialThread )
		label.grid( column=0, row=5 )
		ttk.Label( gridSection, text='Questions, feature requests, and other discussion on '
			'this program can be posted here', justify='center' ).grid( column=1, row=5 )

		ttk.Label( gridSection, image=divider ).grid( column=0, row=6, columnspan=2 )
		label = ttk.Label( gridSection, text='How to Hack Any Texture', foreground='#00F', cursor='hand2', justify='center' )
		label.bind( '<1>', self.gotoHowToHackAnyTexture )
		label.grid( column=0, row=7 )
		ttk.Label( gridSection, text="If for some reason your texture doesn't "
			"appear in this program, then you can fall back onto this thread", justify='center' ).grid( column=1, row=7 )

		ttk.Label( gridSection, image=divider ).grid( column=0, row=8, columnspan=2 )
		label = ttk.Label( gridSection, text='OP of Melee Hacks and You', foreground='#00F', cursor='hand2', justify='center' )
		label.bind( '<1>', self.gotoMeleeHacksAndYou )
		label.grid( column=0, row=9 )
		ttk.Label( gridSection, text='The first post in this thread contains many '
			'resources on all subjects to help you get started', justify='center' ).grid( column=1, row=9 )

		ttk.Label( gridSection, image=divider ).grid( column=0, row=10, columnspan=2 )

		for label in gridSection.grid_slaves( column=1 ):
			label.config( wraplength=220 )

		for label in gridSection.winfo_children():
			label.grid_configure( ipady=4, padx=7 )

		gridSection.pack( padx=4 )

		tipIndex = random.randint( 1, len(self.proTips) )
		ttk.Label( self.window, text='Random Pro-tip: ' + self.proTips[tipIndex], wraplength=380 ).pack( padx=4, pady=12 )

	def gotoWorkshop( self, event ):
		webbrowser.open( 'http://smashboards.com/forums/melee-workshop.271/' )

	def viewManual( self, event=None ): # May take a click event from the help window click binding
		try:
			readMeFilePath = os.path.join( globalData.scriptHomeFolder, 'MMW Manual.txt' )
			os.startfile( readMeFilePath )
		except:
			msg( "Couldn't find the 'MMW Manual.txt' file!", 'File not found', self.window )

	def gotoDiscord( self, event ):
		webbrowser.open( 'https://discord.gg/rBxF8hFbrX' )
	def gotoOfficialThread( self, event ):
		webbrowser.open( 'https://smashboards.com/threads/melee-modding-wizard-beta-v0-9-4.517823/' )
	def gotoHowToHackAnyTexture( self, event ):
		webbrowser.open( 'http://smashboards.com/threads/how-to-hack-any-texture.388956/' )
	def gotoMeleeHacksAndYou( self, event ):
		webbrowser.open( 'http://smashboards.com/threads/melee-hacks-and-you-updated-5-21-2015.247119/#post-4917885' )


class SupportWindow( BasicWindow ):

	def __init__( self, *args, **kwargs ):
		# Set up the main window
		if not BasicWindow.__init__( self, globalData.gui.root, 'Support MMW', *args, unique=True, **kwargs ):
			return # If the above returned false, it displayed an existing window, so we should exit here

		mainCanvas = Tk.Canvas( self.window, bg='#101010', width=640, height=394, borderwidth=0, highlightthickness=0 )

		# Create and attach the background
		mainCanvas.create_image( 0, 0, image=globalData.gui.imageBank('support'), anchor='nw' )

		# Create rectangles over the image to use as buttons
		mainCanvas.create_rectangle( 291, 218, 362, 239, outline="", tags=('paypalLink', 'link') )
		mainCanvas.create_rectangle( 355, 285, 438, 304, outline="", tags=('patreonLink', 'link') )

		# Bind a click event on the buttons to hyperlinks
		mainCanvas.tag_bind( 'paypalLink', '<1>', self.gotoPaypal )
		mainCanvas.tag_bind( 'patreonLink', '<1>', self.gotoPatreon )

		# Bind mouse hover events for buttons, for the cursor
		mainCanvas.tag_bind( 'link', '<Enter>', self.changeCursorToHand )
		mainCanvas.tag_bind( 'link', '<Leave>', self.changeCursorToArrow )

		mainCanvas.pack( pady=0, padx=0 )

	def gotoPaypal( self, event ): webbrowser.open( r'https://www.paypal.com/donate/?business=K95AJCMZDR7CG&no_recurring=0&item_name=Support+like+this+helps+to+tell+me+that+the+time+and+effort+put+into+MMW+are+worth+it%21+Thank+you+so+much%21&currency_code=USD' )
	def gotoPatreon( self, event ): webbrowser.open( r'https://www.patreon.com/drgn' )

	def changeCursorToHand( self, event ): self.window.config( cursor='hand2' )
	def changeCursorToArrow( self, event ): self.window.config( cursor='' )


class AboutWindow( BasicWindow ):

	def __init__( self, *args, **kwargs ):
		# Set up the main window
		if not BasicWindow.__init__( self, globalData.gui.root, 'About MMW', *args, unique=True, **kwargs ):
			return # If the above returned false, it displayed an existing window, so we should exit here

		# Create the canvas
		aboutCanvas = Tk.Canvas( self.window, bg='#101010', width=350, height=247 )
		aboutCanvas.pack()

		# Define a few images
		aboutCanvas.bannerImage = globalData.gui.imageBank( 'pannerBanner' ) # 604x126
		aboutCanvas.hoverOverlayImage = globalData.gui.imageBank('hoverOverlay')
		aboutCanvas.blankBoxImage = ImageTk.PhotoImage( Image.new('RGBA', (182, 60)) ) # Sits behind the main background (same size/position as bgbg).

		# Attach the images to the canvas
		aboutCanvas.create_image( 88, 98, image=globalData.gui.imageBank('bgbg'), anchor='nw' ) # Sits behind the main background (182x60).
		aboutCanvas.create_image( 10, 123, image=aboutCanvas.bannerImage, anchor='w', tags='r2lBanners' )
		aboutCanvas.create_image( 340, 123, image=aboutCanvas.bannerImage, anchor='e', tags='l2rBanners' )
		foregroundObject = aboutCanvas.create_image( 2, 2, image=globalData.gui.imageBank('bg'), anchor='nw' ) # The main background, the mask (350x247).

		# Define and attach the text to the canvas
		windowFont = tkFont.Font( family='MS Serif', size=11, weight='normal' )
		aboutCanvas.create_text( 207, 77, text='C r e a t e d   b y', fill='#d4d4ef', font=windowFont )
		aboutCanvas.create_text( 207, 174, text='Version ' + globalData.programVersion, fill='#d4d4ef', font=windowFont )
		aboutCanvas.create_text( 207, 204, text='Written in Python v' + sys.version.split()[0] + '\nand tKinter v' + str( Tk.TkVersion ), 
											justify='center', fill='#d4d4ef', font=windowFont )

		# Create a "button", and bind events for the mouse pointer, and for going to my profile page on click.
		aboutCanvas.create_image( 82, 98, image=aboutCanvas.blankBoxImage, activeimage=aboutCanvas.hoverOverlayImage, anchor='nw', tags='profileLink' )
		aboutCanvas.tag_bind( 'profileLink', '<1>', self.gotoProfile )
		aboutCanvas.tag_bind( 'profileLink', '<Enter>', self.changeCursorToHand )
		aboutCanvas.tag_bind( 'profileLink', '<Leave>', self.changeCursorToArrow )

		# v Creates an infinite "revolving" image between the two background elements.
		try:
			i = 0
			while self.window:
				if i == 0:
					aboutCanvas.create_image( 614, 123, image=aboutCanvas.bannerImage, anchor='w', tags='r2lBanners' )
					aboutCanvas.create_image( 340 - 604, 123, image=aboutCanvas.bannerImage, anchor='e', tags='l2rBanners' )
					aboutCanvas.tag_lower( 'r2lBanners', foregroundObject ) # Update the layer order to keep the foreground on top.
					aboutCanvas.tag_lower( 'l2rBanners', foregroundObject ) # Update the layer order to keep the foreground on top.
				i += 1
				aboutCanvas.move( 'r2lBanners', -1, 0 )
				aboutCanvas.move( 'l2rBanners', 1, 0 )
				time.sleep( .14 ) # Value in seconds
				aboutCanvas.update()

				if i == 604: # Reached pannerBanner image width; delete the first banner, so the canvas isn't infinitely long
					aboutCanvas.delete( aboutCanvas.find_withtag('r2lBanners')[0] )
					aboutCanvas.delete( aboutCanvas.find_withtag('l2rBanners')[0] )
					i = 0
		except: # Once the window is closed, the while loop will likely exit gracefully. But there's still a race condition
			pass

	def gotoProfile( self, event ): webbrowser.open( 'http://smashboards.com/members/drgn.21936/' )
	def changeCursorToHand( self, event ): self.window.config( cursor='hand2' )
	def changeCursorToArrow( self, event ): self.window.config( cursor='' )


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


class DataEntryWidgetBase( object ):

	""" Provides a few common methods for various data entry widgets for updating 
		the data that has been input to them into their respective file. """

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

	def updateFileHex( self, newHex ):

		""" Validates widget input, checks if it's new/different from what's in the file, 
			and updates the data in the file if it differs. Also triggers updating of any paired widgets. 
			Returns False if there was an error or problem with the update. """

		# Validate the input
		if not validHex( newHex ):
			msg( 'The entered text is not valid hexadecimal!' )
			return False

		# Confirm whether updating is necessary by checking if this is actually new data for any of the offset locations
		if type( self.offsets ) == list:
			for offset in self.offsets:
				currentFileHex = hexlify( self.fileObj.getData(offset, self.byteLength) ).upper()
				if currentFileHex != newHex: # Found a difference
					break
			else: # The loop above didn't break; no change found
				return True # No change to be updated
		else: # The offsets attribute is just a single value (the usual case)
			currentFileHex = hexlify( self.fileObj.getData(self.offsets, self.byteLength) ).upper()
			if currentFileHex == newHex:
				return True # No change to be updated

		# Get the data as a bytearray, and check for other GUI components that may need to be updated
		newData = bytearray.fromhex( newHex )

		if len( newData ) != self.byteLength: # Due to the zfill above, this should only happen if the hex entry is too long
			msg( 'The new value must be {} characters ({} bytes) long.'.format(self.byteLength*2, self.byteLength) )
			return False

		elif self.valueEntryWidget and self.formatting:
			# Check that the appropriate value can be decoded from this hex (if formatting is available)
			try:
				decodedValue = struct.unpack( '>' + self.formatting, newData )[0]
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
				return False

			# Update the data shown in the neighboring, decoded value widget
			self.valueEntryWidget.set( decodedValue )
			self.valueEntryWidget.configure( background='#faa' )

		# Change the background color of the widget, to show that changes have been made to it and are pending saving.
		self.configure( background='#faa' )

		# If this entry has a color swatch associated with it, redraw it
		if self.colorSwatchWidget:
			self.colorSwatchWidget.renderCircle( newHex )

		# Update the hex shown in the widget (in case the user-entered value was zfilled; i.e. was not long enough)
		self.delete( 0, 'end' )
		self.insert( 0, newHex )

		self.updateDataInFile( newData )

		globalData.gui.updateProgramStatus( self.updateName + ' updated' )

		return True

	def updateFileValue( self, newValue ):

		""" Validates widget input, checks if it's new/different from what's in the file, 
			and updates the data in the file if it differs. Also triggers updating of any paired widgets. 
			Returns False if there was an error or problem with the update. """

		# Validate the entered value by making sure it can be correctly encoded
		try:
			if self.formatting == 'f':
				newHex = hexlify( struct.pack( '>f', float(newValue) ) ).upper()
			else:
				newHex = hexlify( struct.pack( '>' + self.formatting, int(newValue) ) ).upper()
		except Exception as err:
			# Construct and display an error message for the user
			dataTypes = { 	'?': 'a boolean', 'b': 'a signed character', 'B': 'an unsigned character', 	# 1-byte
							'h': 'a signed short (halfword)', 'H': 'an unsigned short',				# 2-bytes
							'i': 'a signed integer', 'I': 'an unsigned integer', 'f': 'a float' } # 4-bytes
			if self.formatting in dataTypes:
				msg( 'The entered value is invalid for {} value.'.format( dataTypes[self.formatting] ) )
			else: # I tried
				msg( 'The entered value is invalid.' )
			print( 'Error encountered packing value entry data; {}'.format(err) )
			return False

		# Confirm whether updating is necessary by checking if this is actually new data for any of the offset locations
		if type( self.offsets ) == list:
			for offset in self.offsets:
				currentFileHex = hexlify( self.fileObj.getData(offset, self.byteLength) ).upper()
				if currentFileHex != newHex: # Found a difference
					break
			else: # The loop above didn't break; no change found
				return True # No change to be updated
		else: # The offsets attribute is just a single value (the usual case)
			currentFileHex = hexlify( self.fileObj.getData(self.offsets, self.byteLength) ).upper()
			if currentFileHex == newHex:
				return True # No change to be updated

		# Change the background color of the widget, to show that changes have been made to it and are pending saving.
		if self.__class__ == HexEditDropdown:
			self.configure( style='Edited.TMenubutton' )
		else:
			self.configure( background='#faa' )

		# Update the data shown in the neiboring widget
		if self.hexEntryWidget:
			self.hexEntryWidget.delete( 0, 'end' )
			self.hexEntryWidget.insert( 0, newHex )
			self.hexEntryWidget.configure( background='#faa' )

		# Replace the data in the file for each location
		newData = bytearray.fromhex( newHex )
		self.updateDataInFile( newData )

		globalData.gui.updateProgramStatus( self.updateName + ' updated' )

		return True


class HexEditEntry( Tk.Entry, DataEntryWidgetBase ):

	""" Used for displaying some hex data or some value to the user for editing. 
		"dataOffsets" will typically be a single int value, but may also be a list of offsets. """

	def __init__( self, parent, targetFile, dataOffsets, byteLength, formatting, updateName='', valueEntry=False, width=-1 ):
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

		# Auto-determine width of the widget if not explicitly set
		if width == -1:
			width = ( byteLength * 2 ) + 2
		
		# Create the base component of the widget
		Tk.Entry.__init__( self, parent,
			width=width, 
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
		self.callback = None

		if valueEntry:
			self.bind( '<Return>', self.updateValue )
		else:
			self.bind( '<Return>', self.updateHexData )

	def set( self, value ):
		
		if self.formatting == 'f': # Round floats to 9 decimal places
			value = round( value, 9 )

		self.delete( 0, 'end' )
		self.insert( 0, value )

	def updateValue( self, event=None, value=None ):
		if value is None:
			value = self.get()
		completedSuccessfully = self.updateFileValue( value )

		# Run the callback if there were no problems above
		if self.callback and completedSuccessfully:
			self.callback( event )

	def updateHexData( self, event=None, hexData=None ):
		if not hexData:
			hexData = self.get().zfill( self.byteLength * 2 ).upper() # Pads the string with zeroes to the left if not enough characters
		completedSuccessfully = self.updateFileHex( hexData )

		# Run the callback if there were no problems above
		if self.callback and completedSuccessfully:
			self.callback( event )


class EnumOptionMenu( ttk.OptionMenu ):

	def __init__( self, parent, structures, fieldIndex ):
		self.structures = structures
		self.fieldIndex = fieldIndex

		if type( structures ) == list:
			structure = structures[0]
		else: # It's just one structure object
			structure = structures

		# Get the current value of the enumeration
		self.currentEnum = structure.getValues()[fieldIndex]
		self.fieldName = structure.fields[fieldIndex]

		# Enumerations must be provided by the structure class
		self.enumerations = structure.enums[self.fieldName] # Retrieves a dictionary of the form key=enumInt, value=enumNameString
		self.optionNames = self.enumerations.values()
		defaultOption = self.enumerations[self.currentEnum]
		textVar = Tk.StringVar() # Required to init the optionmenu

		ttk.OptionMenu.__init__( self, parent, textVar, defaultOption, *self.optionNames, command=self.optionSelected )

	def optionSelected( self, newOption ):
		# Convert the option name to the enumeration value
		newEnum = self.optionNames.index( newOption )

		if newEnum == self.currentEnum:
			return # Nothing to do here

		# Replace the data in the file and structure for each one
		updateName = self.fieldName.replace( '\n', ' ' )
		descriptionOfChange = updateName + ' modified in ' + self.structures[0].dat.fileName
		if type( self.structures ) == list:
			for structure in self.structures:
				structure.dat.updateStructValue( structure, self.fieldIndex, newEnum, descriptionOfChange )
		else: # The offsets attribute is just a single struct (the usual case)
			self.structures[0].dat.updateStructValue( self.structures, self.fieldIndex, newEnum, descriptionOfChange )

		printStatus( updateName + ' Updated' )


class ColorSwatch( ttk.Label, DataEntryWidgetBase ):

	""" Creates a circular image (on a label widget), to show a color example and allow for editing it.
		hexColor should be an 8 character hex string of RRGGBBAA """

	def __init__( self, parent, hexColor, hexEntryWidget ):
		# Create the label itself and bind the click even handler to it
		ttk.Label.__init__( self, parent, cursor='hand2' )

		# Create the image swatch that will be displayed, and attach it to self to prevent garbage collection
		self.colorMask = globalData.gui.imageBank( 'colorSwatch', getAsPilImage=True )
		self.renderCircle( hexColor )
		
		# Optional widgets that this may be paired with
		self.hexEntryWidget = hexEntryWidget
		self.valueEntryWidget = None		# Used by HexEditEntry widgets for values
		self.colorSwatchWidget = None		# Not used by this widget (keep to prevent errors)

		self.bind( '<1>', self.editColor )

	def renderCircle( self, hexColor ):

		""" Creates a colored image for this widget (a colored circle icon).
			Can also be used to update the displayed color for this widget 
			programmatically. Does not update the associated hexEntryWidget. """

		# Convert the hex string provided to an RGBA values list
		fillColor = hex2rgb( hexColor )

		# Create a new, 160x160 px, blank image
		swatchImage = Image.new( 'RGBA', (160, 160), (0, 0, 0, 0) )

		# Draw a circle of the given color on the new image
		drawable = ImageDraw.Draw( swatchImage )
		drawable.ellipse( (10, 10, 150, 150), fill=fillColor )

		# Scale down the image. It's created larger, and then scaled down to 
		# create anti-aliased edges (it would just be a hexagon otherwise).
		swatchImage.thumbnail( (16, 16), Image.ANTIALIAS )

		# Overlay the highlight/shadow mask on top of the above color (for a depth effect)
		swatchImage.paste( self.colorMask, (0, 0), self.colorMask )

		# Store the image to prevent from being garbage collected, and set it as the current image
		self.swatchImage = ImageTk.PhotoImage( swatchImage )
		self.configure( image=self.swatchImage )

	def editColor( self, event ):

		""" Called when the user clicks on the widget to edit the current color. 
			Presents the user with a color chooser window, and then updates this 
			widget as well as an associated hexEntryWidget. """

		nibbleLength = self.hexEntryWidget.byteLength * 2

		# Create a window where the user can choose a new color
		colorPicker = MeleeColorPicker( 'Modifying ' + self.hexEntryWidget.updateName, initialColor=self.hexEntryWidget.get() )
		globalData.gui.root.wait_window( colorPicker.window ) # Wait for the above window to close before proceeding

		# Get the new color hex and make sure it's new (if it's not, the operation was canceled, or there's nothing to be done anyway)
		if colorPicker.initialColor != colorPicker.currentHexColor:
			if len( colorPicker.currentHexColor ) != nibbleLength:
				msg( 'The value generated from the color picker (' + colorPicker.currentHexColor + ') does not match the byte length requirement of the destination.' )
			else:
				# Update the data in the file with the entry's data, and redraw the color swatch
				newHex = colorPicker.currentHexColor.zfill( nibbleLength ).upper() # Pads the string with zeroes to the left if not enough characters
				self.hexEntryWidget.updateHexData( hexData=newHex )

	def disable( self ):
		self['state'] = 'disabled'
		self['cursor'] = ''
		self.unbind( '<1>' )
		
	def enable( self ):
		self['state'] = 'normal'
		self['cursor'] = 'hand2'
		self.bind( '<1>', self.editColor )


class SliderAndEntry( ttk.Frame ):

	def __init__( self, parent, *args, **kwargs ):
		ttk.Frame.__init__( self, parent, *args, **kwargs )


class HexEditDropdown( ttk.OptionMenu, DataEntryWidgetBase ):

	""" Used for struct data display and editing, using a predefined set of choices. Similar to the 
		HexEditEntry class, except that the widget's contents/values must be given during initialization. 
		"options" should be a dictionary, where each key is a string to display as an option in this
		widget, and the corresponding values are the data values to edit/update in the target file.
		"dataOffsets" will typically be a single int value, but can be a list of offsets. """

	def __init__( self, parent, targetFile, dataOffsets, byteLength, formatting, updateName, options, defaultOption=None, **kwargs ):

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
		# callBack = kwargs.get( 'command', None )
		# if callBack:
		#	kwargs['command'] = lambda currentString: callBack( self )
		kwargs['command'] = self.updateValue

		# Create the widget
		self.selectedString = Tk.StringVar()
		ttk.OptionMenu.__init__( self, parent, self.selectedString, defaultOption, *options, **kwargs )

		self.fileObj	= targetFile
		self.offsets 	= dataOffsets		# May be a single file offset (int), or a list of them
		self.byteLength = byteLength
		self.formatting = formatting
		self.updateName = updateName

		self.options = options				# Dict of the form, key=stringToDisplay, value=dataToSave
		
		# Optional widgets that this may be paired with
		self.hexEntryWidget = None			# Used by HexEditEntry widgets for hex data
		self.valueEntryWidget = None		# Used by HexEditEntry widgets for values
		self.colorSwatchWidget = None

	def updateValue( self, event=None, value=None ):
		if value is None:
			value = self.get()
		self.updateFileValue( value )

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
		ToolTip( removeBtn, text='Remove library', delay=1000, bg='#ee9999', location='n' )
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


class FlagDecoder( BasicWindow ):

	""" Used to view and modify DAT file structure flags, and the individual bits associated to them. """

	def __init__( self, structure, fieldAndValueIndex, entryIndex=-1, displayName='' ):
		# Store the given arguments
		self.structure = structure
		self.fieldAndValueIndex = fieldAndValueIndex
		self.entryIndex = entryIndex # For data table structs

		# Collect info on these flags
		fieldName = structure.fields[fieldAndValueIndex]
		structFlagsDict = getattr( structure, 'flags', {} ) # Returns an empty dict if one is not found.
		self.individualFlagNames = structFlagsDict.get( fieldName ) # Will be 'None' if these flags aren't defined in the structure's class
		self.flagFieldLength = struct.calcsize( structure.formatting[fieldAndValueIndex+1] )

		# Determine a name to identify these specific flags
		if displayName:
			self.name = displayName
		else:
			self.name = structure.name = ', ' + fieldName.replace( '_', ' ' ).replace( '\n', ' ' )

		# Create a string for iterating bits
		self.allFlagsValue = structure.getValues()[fieldAndValueIndex] # Single value representing all of the flags
		self.bitString = format( self.allFlagsValue, 'b' ).zfill( self.flagFieldLength * 8 ) # Adds padding to the left to fill out to n*8 bits

		# Determine the window spawn position (if this will be a long list, spawn the window right at the top of the main GUI)
		if self.individualFlagNames and len( self.individualFlagNames ) > 16: spawnHeight = 0
		elif not self.individualFlagNames and len( self.bitString ) > 16: spawnHeight = 0
		else: spawnHeight = 180

		# Generate the basic window
		if not BasicWindow.__init__( self, globalData.gui.root, 'Flag Decoder  -  ' + displayName, offsets=(180, spawnHeight), unique=True ):
			return # If the above returned false, it displayed an existing window, so we should exit here

		# Define some fonts to use
		self.fontNormal = tkFont.Font( size=11 )
		self.boldFontLarge = tkFont.Font( weight='bold', size=14 )
		self.boldFontNormal = tkFont.Font( weight='bold', size=12 )

		self.drawWindowContents()

	def drawWindowContents( self ):
		# Display a break-down of all of the actual bits from the flag value
		self.bitsGrid = ttk.Frame( self.window )
		byteStringsList = [ self.bitString[i:i+8] for i in range(0, len(self.bitString), 8) ] # A list, where each entry is a string of 8 bits
		for i, byteString in enumerate( byteStringsList ): # Add the current byte as both hex and binary
			ttk.Label( self.bitsGrid, text='{0:02X}'.format(int( byteString, 2 )), font=self.boldFontLarge ).grid( column=i, row=0, ipadx=4 )
			ttk.Label( self.bitsGrid, text=byteString, font=self.boldFontLarge ).grid( column=i, row=1, ipadx=4 )
		ttk.Label( self.bitsGrid, text=' ^ bit {}'.format(len(self.bitString) - 1), font=self.fontNormal ).grid( column=0, row=2, sticky='w', ipadx=4 )
		ttk.Label( self.bitsGrid, text='bit 0 ^ ', font=self.fontNormal ).grid( column=len(byteStringsList)-1, row=2, sticky='e', ipadx=4 )
		self.bitsGrid.pack( pady=(10, 0), padx=10 )

		# Iterate over the bits or flag enumerations and show the status of each one
		self.flagTable = ttk.Frame( self.window )
		row = 0
		if self.individualFlagNames: # This will be a definition (ordered dictionary) from the structure's class.
			for bitMapString, bitName in self.individualFlagNames.items():
				baseValue, shiftAmount = bitMapString.split( '<<' )
				shiftAmount = int( shiftAmount )

				# Mask out the bits unrelated to this property
				bitMask = int( baseValue ) << shiftAmount

				ttk.Label( self.flagTable, text=bitMapString, font=self.fontNormal ).grid( column=0, row=row )

				# Set up the checkbox variable, and add the flag name to the GUI
				var = Tk.IntVar()
				if self.flagsAreSet( bitMask, shiftAmount ):
					var.set( 1 )
					ttk.Label( self.flagTable, text=bitName, font=self.boldFontNormal ).grid( column=1, row=row, padx=14 )
				else:
					var.set( 0 )
					ttk.Label( self.flagTable, text=bitName, font=self.fontNormal ).grid( column=1, row=row, padx=14 )

				chkBtn = ttk.Checkbutton( self.flagTable, variable=var )
				chkBtn.var = var
				chkBtn.row = row
				chkBtn.bitMask = bitMask
				chkBtn.shiftAmount = shiftAmount
				chkBtn.grid( column=2, row=row )
				chkBtn.bind( '<1>', self.toggleBits ) # Using this instead of the checkbtn's 'command' argument so we get an event (and widget reference) passed

				row += 1

		else: # Undefined bits/properties
			for i, bit in enumerate( reversed(self.bitString) ):
				# Add the bit number and it's value
				ttk.Label( self.flagTable, text='Bit {}:'.format(i), font=self.fontNormal ).grid( column=0, row=row )

				# Add the flag(s) name and value
				var = Tk.IntVar()
				if bit == '1':
					var.set( 1 )
					ttk.Label( self.flagTable, text='Set', font=self.boldFontNormal ).grid( column=1, row=row, padx=6 )
				else:
					var.set( 0 )
					ttk.Label( self.flagTable, text='Not Set', font=self.fontNormal ).grid( column=1, row=row, padx=6 )

				chkBtn = ttk.Checkbutton( self.flagTable, variable=var )
				chkBtn.var = var
				chkBtn.row = row
				chkBtn.bitMask = 1 << i
				chkBtn.shiftAmount = i
				chkBtn.grid( column=2, row=row )
				chkBtn.bind( '<1>', self.toggleBits ) # Using this instead of the checkbtn's 'command' argument so we get an event (and widget reference) passed

				row += 1

		self.flagTable.pack( pady=20, padx=20 )

	def flagsAreSet( self, bitMask, bitNumber ):

		""" Can check a mask of one or multiple bits (i.e. 0x1000 or 0x1100 ), except 
			when checking for a bitMask of 0, which only checks one specific bit. """

		if bitMask == 0: # In this case, this flag will be considered 'True' or 'On' if the bit is 0
			return not ( 1 << bitNumber ) & self.allFlagsValue
		else:
			return ( bitMask & self.allFlagsValue ) == bitMask

	def toggleBits( self, event ):
		# Get the widget's current value and invert it (since this method is called before the widget can update the value on its own)
		flagIsToBeSet = not event.widget.var.get()

		# For flags whose 'True' or 'On' case is met when the bit value is 0, invert whether the flags should be set to 1 or 0
		bitMask = event.widget.bitMask
		if bitMask == 0:
			flagIsToBeSet = not flagIsToBeSet
			bitMask = 1 << event.widget.shiftAmount

		# Set or unset all of the bits for this flag
		if flagIsToBeSet:
			self.allFlagsValue = self.allFlagsValue | bitMask # Sets all of the masked bits in the final value to 1
		else:
			self.allFlagsValue = self.allFlagsValue & ~bitMask # Sets all of the masked bits in the final value to 0 (~ operation inverts bits)

		# Rebuild the bit string and update the window contents
		self.updateBitBreakdown()
		self.updateFlagRows()

		# Change the flag value in the file
		self.updateFlagsInFile()

		return 'break' # Prevents propagation of this event (the checkbutton's own event handler won't even fire)

	def updateBitBreakdown( self ):

		""" Updates the flag strings of hex and binary, and then redraws them in the GUI. """

		# Update the internal strings
		self.bitString = format( self.allFlagsValue, 'b' ).zfill( self.flagFieldLength * 8 ) # Adds padding to the left to fill out to n*8 bits
		byteStringsList = [ self.bitString[i:i+8] for i in range(0, len(self.bitString), 8) ] # A list, where each entry is a string of 8 bits

		# Update the GUI
		for i, byteString in enumerate( byteStringsList ):
			# Update the hex display for this byte
			hexDisplayLabel = self.bitsGrid.grid_slaves( column=i, row=0 )[0]
			hexDisplayLabel['text'] = '{0:02X}'.format( int(byteString, 2) )

			# Update the binary display for this byte
			binaryDisplayLabel = self.bitsGrid.grid_slaves( column=i, row=1 )[0]
			binaryDisplayLabel['text'] = byteString

	def updateFlagRows( self ):

		""" Checks all flags/rows to see if the flag needs to be updated. All of 
			them need to be checked because some flags may affect multiple flags/rows. """

		for checkboxWidget in self.flagTable.grid_slaves( column=2 ):
			flagNameLabel = self.flagTable.grid_slaves( column=1, row=checkboxWidget.row )[0]

			# Set the boldness of the font, and the state of the checkbox
			if self.flagsAreSet( checkboxWidget.bitMask, checkboxWidget.shiftAmount ):
				flagNameLabel['font'] = self.boldFontNormal
				checkboxWidget.var.set( 1 )
			else:
				flagNameLabel['font'] = self.fontNormal
				checkboxWidget.var.set( 0 )

	def updateFlagsInFile( self ):

		""" Updates the combined value of the currently set flags in the file's data and in entry fields in the main program window. 
			This [unfortunately] needs to rely on a search methodology to target entry field widgets that need updating, 
			because they can be destroyed and re-created (thus, early references to existing widgets can't be trusted). """

		# Convert the value to a bytearray and save it to the struct
		#newHex = '{0:0{1}X}'.format( self.allFlagsValue, self.flagFieldLength*2 ) # Formats as hex; pads up to n zeroes (second arg)
		#flagsData = struct.pack( self.structure.formatting[self.fieldAndValueIndex+1], self.allFlagsValue )
		datFile = self.structure.dat
		descriptionOfChange = self.name + ' flags updated'
		datFile.updateStructValue( self.structure, self.fieldAndValueIndex, self.allFlagsValue, descriptionOfChange, 'Action state flags updated', entryIndex=self.entryIndex )

		# Update the field entry widgets in the Structural Analysis tab, if it's currently showing this set of flags
		# structTable = getattr( globalData.gui.structurePropertiesFrame, 'structTable', None )
		# if structTable:
		# 	# Get the offset of the structure shown in the panel (offset of the first field entry), to see if it's the same as the one we're editing
		# 	firstFieldOffsets = structTable.grid_slaves( column=1, row=0 )[0].offsets # Should never be a list when generated here
		# 	if firstFieldOffsets == self.structure.offset:
		# 		# Set the value of the entry widget, and trigger its bound update function (which will handle everything from validation through data-saving)
		# 		hexEntryWidget = structTable.grid_slaves( column=1, row=self.fieldAndValueIndex )[0]
		# 		self.updateWidget( hexEntryWidget, newHex )

		# Update the actual data in the file for each offset
		#flagName = self.structure.fields[self.fieldAndValueIndex].replace( '_', ' ' ).replace( '\n', ' ' )
		# descriptionOfChange = flagName + ' modified in ' + globalDatFile.filename
		# newData = bytearray.fromhex( newHex )
		# if type( self.fieldOffsets ) == list:
		# 	for offset in self.fieldOffsets:
		# 		globalDatFile.updateData( offset, newData, descriptionOfChange )
		# else: # This is expected to be for an entry on the Structural Analysis tab
		# 	globalDatFile.updateData( self.fieldOffsets, newData, descriptionOfChange )

		printStatus( descriptionOfChange )


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

	def __init__( self, parent, maxHeight=-1, *args, **kw ):
		Tk.Frame.__init__( self, parent, *args, **kw )

		# create a canvas object, and a vertical scrollbar for scrolling it
		self.vscrollbar = Tk.Scrollbar( self, orient='vertical' )
		self.vscrollbar.grid( column=1, row=0, sticky='ns' )
		self.canvas = Tk.Canvas( self, bd=0, highlightthickness=0, yscrollcommand=self.vscrollbar.set )
		self.canvas.grid( column=0, row=0, sticky='nsew' )
		self.canvas.yview_scroll = self.yview_scroll
		self.vscrollbar.config( command=self.canvas.yview )
		self.maxHeight = maxHeight

		# reset the view
		self.canvas.xview_moveto( 0 )
		self.canvas.yview_moveto( 0 )

		# create a frame inside the canvas which will be scrolled with it
		self.interior = Tk.Frame( self.canvas, relief='ridge' )
		self.interior_id = self.canvas.create_window( 0, 0, window=self.interior, anchor='nw' )

		# add resize configuration for the canvas and scrollbar
		self.rowconfigure( 0, weight=1 )
		self.columnconfigure( 0, weight=1 )
		self.columnconfigure( 1, weight=0 ) # Do not resize this column (for the scrollbar)

		# track changes to the canvas and frame width and sync them,
		# also updating the scrollbar
		self.interior.bind( '<Configure>', self.configureCanvas )
		self.canvas.bind( '<Configure>', self.configureInterior )

	def configureCanvas( self, event=None ):

		""" Called when the interior frame's size is changed. """

		self.update_idletasks()
		self.configureScrollbar()

		# update the scroll area to match the size of the inner frame
		self.canvas.config( scrollregion=self.canvas.bbox(self.interior_id) )

		interiorWidth = self.interior.winfo_reqwidth()
		if interiorWidth != self.canvas.winfo_width():
			# update the canvas' width to fit the inner frame
			self.canvas.config( width=interiorWidth )

		# match the canvas height to the height of the interior frame
		interiorHeight = self.interior.winfo_reqheight()
		if self.maxHeight != -1 and interiorHeight > self.maxHeight:
			interiorHeight = self.maxHeight
		if self.canvas.winfo_reqheight() != interiorHeight:
			self.canvas.config( height=interiorHeight )

	def configureInterior( self, event=None ):

		""" Called when the canvas' size is changed, which should 
			coincide with changes to the parent (the whole widget). """

		self.update_idletasks()
		self.configureScrollbar()

		canvasWidth = self.canvas.winfo_width()
		if self.interior.winfo_reqwidth() != canvasWidth:
			# update the inner frame's width to fill the canvas
			self.canvas.itemconfigure( self.interior_id, width=canvasWidth )
		
		# canvasHeight = self.canvas.winfo_height()
		# if self.interior.winfo_reqheight() != canvasHeight:
		# 	# update the inner frame's height to fill the canvas
		# 	self.canvas.itemconfigure( self.interior_id, height=canvasHeight )

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


class MeleeColorPicker( object ):

	windows = {} # Used to track multiple windows for multiple palette entries. New windows will be added with a windowId = palette entry's canvas ID
	recentColors = [] # Colors stored as tuples of (r, g, b, a)
	windowSpawnOffset = 0

	def __init__( self, title='Color Converter', initialColor='ACACAC7F', defaultTplFormat=5, windowId='', datDataOffsets=(), targetFile=None ):
		self.title = title
		self.initialColor = initialColor.upper()
		self.currentHexColor = self.initialColor
		self.currentRGBA = hex2rgb( self.initialColor )
		self.tplHex = TplEncoder.encodeColor( defaultTplFormat, self.currentRGBA )
		self.windowId = windowId
		self.datDataOffsets = datDataOffsets # ( rgbaColor, paletteEntry, paletteEntryOffset, imageDataOffset ) | paletteEntry is the original palette color hex
		self.file = targetFile
		self.lastUpdatedColor = ''	# Used to prevent unncessary/redundant calls to update the displayed texture

		if self.windowId in self.windows: pass
		else:
			self.createWindow( defaultTplFormat )

			# If windowId, remember it so it can be referenced later (by deiconify)
			if self.windowId: self.windows[self.windowId] = self

		self.window.deiconify()

	def createWindow( self, defaultTplFormat ):
		self.window = Tk.Toplevel( globalData.gui.root )
		self.window.title( self.title )
		self.window.attributes( '-toolwindow', 1 ) # Makes window framing small, like a toolbox/widget.
		self.window.resizable( width=False, height=False )
		self.window.wm_attributes( '-topmost', 1 )
		self.window.protocol( 'WM_DELETE_WINDOW', self.cancel ) # Overrides the 'X' close button.

		# Calculate the spawning position of the new window
		rootDistanceFromScreenLeft, rootDistanceFromScreenTop = getWindowGeometry( globalData.gui.root )[2:]
		newWindowX = rootDistanceFromScreenLeft + 180 + self.windowSpawnOffset
		newWindowY = rootDistanceFromScreenTop + 180 + self.windowSpawnOffset
		self.window.geometry( '+' + str(newWindowX) + '+' + str(newWindowY) )
		self.windowSpawnOffset += 30
		if self.windowSpawnOffset > 150: self.windowSpawnOffset = 15

		# Populate the window
		mainFrame = Tk.Frame( self.window )

		# Show any remembered colors
		if self.recentColors:
			self.recentColorImages = []
			self.itemColors = {}
			if len( self.recentColors ) < 13: canvasHeight = 19
			else: canvasHeight = 38

			ttk.Label( mainFrame, text='Recent Colors:' ).pack( anchor='w', padx=16, pady=4 )
			self.colorsCanvas = Tk.Canvas( mainFrame, borderwidth=2, relief='ridge', background='white', width=197, height=canvasHeight )
			self.colorsCanvas.pack( pady=4 )

			x = 10
			y = 9
			for i, rgbaColor in enumerate( reversed(self.recentColors) ):
				# Prepare and store an image object for the color
				colorSwatchImage = Image.new( 'RGBA', (8, 8), rgbaColor )
				colorSwatchWithBorder = ImageOps.expand( colorSwatchImage, border=1, fill='black' )
				self.recentColorImages.append( ImageTk.PhotoImage(colorSwatchWithBorder) )

				# Draw the image onto the canvas.
				itemId = self.colorsCanvas.create_image( x, y, image=self.recentColorImages[i], anchor='nw', tags='swatches' )
				self.itemColors[itemId] = rgbaColor

				x += 16
				if i == 11: # Start a new line
					x = 10
					y += 16

			self.colorsCanvas.tag_bind( 'swatches', '<1>', self.restoreColor )
			def onMouseEnter(e): self.colorsCanvas['cursor']='hand2'
			def onMouseLeave(e): self.colorsCanvas['cursor']=''
			self.colorsCanvas.tag_bind( 'swatches', '<Enter>', onMouseEnter )
			self.colorsCanvas.tag_bind( 'swatches', '<Leave>', onMouseLeave )

		# RGB Channels
		ttk.Label( mainFrame, text='Choose the RGB Channel values:' ).pack( anchor='w', padx=16, pady=4 )
		curtainFrame = Tk.Frame( mainFrame, borderwidth=2, relief='ridge', width=250, height=50, cursor='hand2' )
		whiteCurtain = Tk.Frame( curtainFrame, bg='white', width=25, height=50 )
		whiteCurtain.pack( side='left' )

		focusColorsFrame = Tk.Frame( curtainFrame, width=200, height=50 )
		# Combine the initial color with the defalt background color, to simulate alpha on the colored frame (since Frames don't support alpha)
		bgColor16Bit = globalData.gui.root.winfo_rgb( focusColorsFrame['bg'] )
		self.nativeBgColor = ( bgColor16Bit[0]/256, bgColor16Bit[1]/256, bgColor16Bit[2]/256 ) # Reduce it to an 8-bit colorspace
		newColors = []
		alphaBlending = round( self.currentRGBA[-1] / 255.0, 2 )
		for i, colorChannel in enumerate( self.nativeBgColor ):
			newColors.append( int(round( (alphaBlending * self.currentRGBA[i]) + (1-alphaBlending) * colorChannel )) )
		originalColorBg = rgb2hex( newColors )
		if self.getLuminance( originalColorBg + 'ff' ) > 127: fontColor = 'black'
		else: fontColor = 'white'
		self.originalColor = Tk.Frame( focusColorsFrame, bg=originalColorBg, width=200, height=25 )
		Tk.Label( self.originalColor, text='Original Color', bg=originalColorBg, foreground=fontColor ).pack()
		self.currentRgbDisplay = Tk.Frame( focusColorsFrame, width=200, height=25 ) # , bg='#ACACAC'
		Tk.Label( self.currentRgbDisplay, text='New Color' ).pack()
		focusColorsFrame.pack( side='left' )
		for frame in [ self.originalColor, self.currentRgbDisplay ]:
			frame.pack()
			frame.pack_propagate( False )
			frame.bind( '<1>', self.pickRGB )
			frame.winfo_children()[0].bind( '<1>', self.pickRGB )

		blackCurtain = Tk.Frame( curtainFrame, bg='black', width=25, height=50 )
		blackCurtain.pack( side='left' )
		curtainFrame.pack( padx=5, pady=4 )
		curtainFrame.pack_propagate( False )
		for frame in curtainFrame.winfo_children(): frame.pack_propagate( False )

		# Alpha Channel
		ttk.Label( mainFrame, text='Choose the Alpha Channel value:' ).pack( anchor='w', padx=16, pady=4 )
		alphaRowFrame = Tk.Frame( mainFrame )
		self.alphaEntry = ttk.Entry( alphaRowFrame, width=3 )
		self.alphaEntry.pack( side='left', padx=4 )
		self.alphaEntry.bind( '<KeyRelease>', self.alphaUpdated )
		self.alphaSlider = ttk.Scale( alphaRowFrame, orient='horizontal', from_=0, to=255, length=260, command=self.alphaUpdated )
		self.alphaSlider.pack( side='left' , padx=4 )
		alphaRowFrame.pack( padx=5, pady=4 )

		# Color Value Conversions
		ttk.Label( mainFrame, text='Color Space Comparisons:' ).pack( anchor='w', padx=16, pady=4 )
		colorEntryFieldsFrame = Tk.Frame( mainFrame )

		# RGBA (decimal and hex forms)
		ttk.Label( colorEntryFieldsFrame, text='RGBA:' ).grid( column=0, row=0, padx=5 )
		self.rgbaStringVar = Tk.StringVar()
		self.rgbaEntry = ttk.Entry( colorEntryFieldsFrame, textvariable=self.rgbaStringVar, width=16, justify='center' )		
		self.rgbaEntry.grid( column=1, row=0, padx=5 )
		self.rgbaEntry.bind( '<KeyRelease>', self.rgbaEntryUpdated )
		ttk.Label( colorEntryFieldsFrame, text='RGBA Hex:' ).grid( column=2, row=0, padx=5, pady=5 )
		self.hexColorStringVar = Tk.StringVar()
		self.rgbaHexEntry = ttk.Entry( colorEntryFieldsFrame, textvariable=self.hexColorStringVar, width=10, justify='center' )
		self.rgbaHexEntry.grid( column=3, row=0, padx=5 )
		self.rgbaHexEntry.bind( '<KeyRelease>', self.hexEntryUpdated )

		# TPL Formats
		ttk.Label( colorEntryFieldsFrame, text='TPL Format:' ).grid( column=0, row=1, padx=5 )
		self.tplFormat = Tk.StringVar()
		if 'Palette' in self.title: # Limit the selection of formats to just those used for palettes.
			formatList = [ '_3 (IA8)', '_4 (RGB565)', '_5 (RGB5A3)', '_6 (RGBA8)' ]
		else: formatList = [ '_0 (I4)', '_1 (I8)', '_2 (IA4)', '_3 (IA8)', '_4 (RGB565)', '_5 (RGB5A3)', '_6 (RGBA8)' ]

		self.tplFormat.set( formatList[defaultTplFormat] )
		self.tplFormatOptionMenu = ttk.OptionMenu( colorEntryFieldsFrame, self.tplFormat, formatList[defaultTplFormat], *formatList, command=self.updateColorDisplays )
		self.tplFormatOptionMenu.grid( column=1, row=1, padx=5, pady=5 )
		if 'Palette' in self.title: self.tplFormatOptionMenu['state'] = 'disabled'

		self.tplFormatStringVar = Tk.StringVar()
		self.tplFormatEntry = ttk.Entry( colorEntryFieldsFrame, textvariable=self.tplFormatStringVar, width=13, justify='center' )
		self.tplFormatEntry.grid( column=2, columnspan=2, row=1, padx=5, sticky='w' )
		self.tplFormatEntry.bind( '<KeyRelease>', self.tplEntryUpdated )

		colorEntryFieldsFrame.pack( padx=5, pady=4 )

		self.updateColorDisplays( updateImage=False )
		#self.alphaSlider.set( self.currentRGBA[-1] )

		# Buttons! For use when this isn't just a comparison tool, but being used as a color picker to replace a value in a game/file
		if self.title != 'Color Converter':
			buttonsFrame = Tk.Frame( mainFrame )
			ttk.Button( buttonsFrame, text='Submit', command=self.submit ).pack( side='left', ipadx=4, padx=20 )
			ttk.Button( buttonsFrame, text='Cancel', command=self.cancel ).pack( side='left', ipadx=4, padx=20 )
			buttonsFrame.pack( pady=8 )

		mainFrame.pack()

		self.updateEntryBorders( None )
		self.window.bind( '<FocusIn>', self.updateEntryBorders ) # Allows for switching between multiple open windows to move the highlighting around

	def getLuminance( self, hexColor ):
		r, g, b, a = hex2rgb( hexColor )
		return ( r*0.299 + g*0.587 + b*0.114 ) * a/255
		#return ( r+r + g+g+g + b )/6 * a/255 # a quicker but less accurate calculation
		#return math.sqrt( .299 * r**2 + .587 * g**2 + .114 * b**2 ) *a/255 / 255

	def getTextureEditorTab( self ):

		""" Scans the Texture Editor interface for a tab using the same file as this window. """

		if not globalData.gui.texturesTab:
			return None

		for tabName in globalData.gui.texturesTab.tabs():
			tabWidget = globalData.gui.root.nametowidget( tabName )

			if tabWidget.file == self.file:
				return tabWidget

		else: # Tab not found
			return None

	def updateEntryBorders( self, event ):
		
		""" For use with the Change Palette Color inspection window from a texture's Palette tab. 
			This updates the border color of palette entries to indicate whether they're selected. """

		texturesTab = self.getTextureEditorTab()
		
		if texturesTab and 'Palette' in self.title:
			paletteCanvas = texturesTab.paletteCanvas

			# If any items are currently selected, change their border color back to normal
			for item in paletteCanvas.find_withtag( 'selected' ):
				paletteCanvas.itemconfig( item, fill='black' )
				paletteCanvas.dtag( item, 'selected' ) # Removes this tag from the canvas item

			# Use the paletteEntryOffset tag to locate the border item (getting its canvas ID)
			if self.datDataOffsets != ():
				paletteEntryOffset = self.datDataOffsets[2]
				paletteTag = 't' + str( paletteEntryOffset )
				borderIids = paletteCanvas.find_withtag( paletteTag )
				if borderIids:
					paletteCanvas.itemconfig( borderIids[0], fill=paletteCanvas.entryBorderColor, tags=('selected', paletteTag) )

	def updateColorDisplays( self, updateImage=True, setAlphaEntry=True ):
		
		""" Updates the visual representation, alpha value/slider, and colorspace Entry values. """

		currentTplFormat = int( self.tplFormat.get().split()[0][1:] )
		if currentTplFormat in [ 0, 1, 4 ]: alphaSupported = False
		else: alphaSupported = True

		# Combine the newly selected color with the default background color, to simulate alpha on the colored frame (since Frames don't support transparency)
		newColors = []
		alphaBlending = round( self.currentRGBA[-1] / 255.0, 2 )
		for i, color in enumerate( self.nativeBgColor ):
			newColors.append( int(round( (alphaBlending * self.currentRGBA[i]) + (1-alphaBlending) * color )) )
		currentColorLabel = self.currentRgbDisplay.winfo_children()[0]
		currentColorBg = rgb2hex( newColors )
		self.currentRgbDisplay['bg'] = currentColorBg
		currentColorLabel['bg'] = currentColorBg
		if self.getLuminance( currentColorBg + 'ff' ) > 127: currentColorLabel['fg'] = 'black'
		else: currentColorLabel['fg'] = 'white'

		# Set the alpha components of the GUI
		self.preventNextSliderCallback = True # Prevents an infinite loop where the programmatic setting of the slider causes another update for this function
		self.alphaEntry['state'] = 'normal'
		self.alphaSlider.state(['!disabled'])
		currentAlphaLevel = self.currentRGBA[-1]

		if not alphaSupported: # These formats do not support alpha; max the alpha channel display and disable the widgets
			self.alphaEntry.delete( 0, 'end' )
			self.alphaEntry.insert( 0, '255' )
			self.alphaSlider.set( 255 )
			self.alphaEntry['state'] = 'disabled'
			self.alphaSlider.state(['disabled'])
		elif setAlphaEntry: # Prevents moving the cursor position if the user is typing into this field
			self.alphaEntry.delete( 0, 'end' )
			self.alphaEntry.insert( 0, str(currentAlphaLevel) ) #.lstrip('0')
			self.alphaSlider.set( currentAlphaLevel )
		else: self.alphaSlider.set( currentAlphaLevel ) # User entered a value into the alphaEntry; don't modify that

		# Set the RGBA fields
		if alphaSupported:
			self.rgbaStringVar.set( ', '.join([ str(channel) for channel in self.currentRGBA ]) )
			self.hexColorStringVar.set( self.currentHexColor )
		else:
			self.rgbaStringVar.set( ', '.join([ str(channel) for channel in self.currentRGBA[:-1] ]) )
			self.hexColorStringVar.set( self.currentHexColor[:-2] )

		# Set the TPL Entry field
		self.tplHex = TplEncoder.encodeColor( currentTplFormat, self.currentRGBA )
		if currentTplFormat < 6:
			self.tplFormatStringVar.set( self.tplHex.upper() )
		elif currentTplFormat == 6: # In this case, the value will actually be a tuple of the color parts
			self.tplFormatStringVar.set( self.tplHex[0].upper() + ' | ' + self.tplHex[1].upper() )
		else: self.tplFormatStringVar.set( 'N/A' )

		if 'Palette' in self.title and updateImage:
			# Validate the encoded color
			if len( self.tplHex ) != 4 or not validHex( self.tplHex ):
				msg( 'The newly generated color was not two bytes!' )

			else:
				self.updateTexture( self.tplHex )

	def pickRGB( self, event ):
		try: rgbValues, hexColor = askcolor( initialcolor='#'+self.currentHexColor[:-2], parent=self.window )
		except: rgbValues, hexColor = '', ''

		if rgbValues:
			# Get the current alpha value, and combine it with the colors chosen above.
			currentAlphaLevel = int( round(self.alphaSlider.get()) )

			self.currentRGBA = ( rgbValues[0], rgbValues[1], rgbValues[2], currentAlphaLevel )
			self.currentHexColor = hexColor.replace('#', '').upper() + "{0:0{1}X}".format( currentAlphaLevel, 2 )
			self.updateColorDisplays()

	def alphaUpdated( self, event ):
		if self.preventNextSliderCallback:
			self.preventNextSliderCallback = False
			return
		
		if isinstance( event, str ): # Means this was updated from the slider widget
			newAlphaValue = int( float(event) )
			setAlphaEntry = True
		else: # Updated from the Entry widget
			newAlphaValue = int( round(float( event.widget.get() )) )
			setAlphaEntry = False

		self.currentRGBA = self.currentRGBA[:-1] + ( newAlphaValue, )
		self.currentHexColor = self.currentHexColor[:-2] + "{0:0{1}X}".format( newAlphaValue, 2 )
		self.updateColorDisplays( setAlphaEntry=setAlphaEntry )

	def rgbaEntryUpdated( self, event ):
		# Parse and validate the input
		channels = event.widget.get().split( ',' )
		channelsList = []
		parsingError = False

		for channelValue in channels:
			try:
				newInt = int( float(channelValue) )
				if newInt > -1 and newInt < 256: channelsList.append( newInt )
			except: 
				parsingError = True
				break
		else: # Got through the above loop with no break. Still got one more check.
			if len( channelsList ) != 4:
				parsingError = True

		if parsingError:
			if event.keysym == 'Return': # User hit the "Enter" key in a confused attempt to force an update
				msg( 'The input should be in the form, "r, g, b, a", where each value is within the range of 0 - 255.', 'Invalid input or formatting.' )

		else: # Everything checks out, update the color and GUI
			self.currentRGBA = tuple( channelsList )
			self.currentHexColor = ''.join( [ "{0:0{1}X}".format( channel, 2 ) for channel in self.currentRGBA ] )
			self.updateColorDisplays()

	def hexEntryUpdated( self, event ):
		# Parse and validate the input
		inputStr = event.widget.get()
		channelsList = hex2rgb( inputStr )

		if not channelsList:
			if event.keysym == 'Return': # User hit the "Enter" key in a confused attempt to force an update
				msg( 'The input should be in the form, "RRGGBBAA", where each value is within the hexadecimal range of 00 - FF.', 'Invalid input or formatting.' )

		else: # Everything checks out, update the color and GUI
			self.currentRGBA = tuple( channelsList )
			self.currentHexColor = ''.join( [ "{0:0{1}X}".format( channel, 2 ) for channel in self.currentRGBA ] )
			self.updateColorDisplays()

	def tplEntryUpdated( self, event ):
		tplHex = self.tplFormatStringVar.get().replace('0x', '').replace('|', '')
		nibbleCount = { 0:1, 1:2, 2:2, 3:4, 4:4, 5:4, 6:8, 8:1, 9:2, 10:4, 14:1 } # How many characters should be present in the string
		currentTplFormat = int( self.tplFormat.get().split()[0][1:] )

		if len( tplHex ) == nibbleCount[currentTplFormat] and validHex( tplHex ):
			self.currentRGBA = TplDecoder.decodeColor( currentTplFormat, tplHex )
			self.currentHexColor = ''.join( [ "{0:0{1}X}".format( channel, 2 ) for channel in self.currentRGBA ] )
			self.updateColorDisplays()

	def restoreColor( self, event ):
		item = event.widget.find_closest( event.x, event.y )[0]
		self.currentRGBA = self.itemColors[item]
		self.currentHexColor = ''.join( [ "{0:0{1}X}".format( channel, 2 ) for channel in self.currentRGBA ] )
		self.updateColorDisplays()

	def updateRecentColors( self ):
		# If the current color is already in the list, remove it, and add the color to the start of the list.
		for i, colorTuple in enumerate( self.recentColors ):
			if colorTuple == self.currentRGBA:
				self.recentColors.pop( i )
				break
		self.recentColors.append( self.currentRGBA )

		# Keep the list under a certain size
		while len( self.recentColors ) > 24:
			self.recentColors.pop( 0 )

	def updateTexture( self, paletteEntryHex, canceling=False ):
		
		""" Updates palette colors for a texture and re-renders it for 
			the icon and main display (in the Image tab). """

		texturesTab = self.getTextureEditorTab()
		
		if self.datDataOffsets != () and self.file and texturesTab:
			if paletteEntryHex == self.lastUpdatedColor:
				return

			try:
				# Replace the color in the image or palette data
				_, _, paletteEntryOffset, imageDataOffset = self.datDataOffsets
				self.file.updateData( paletteEntryOffset, bytearray.fromhex(paletteEntryHex), 'Palette entry modified', trackChange=False )
				
				# Load the new data for the updated texture and display it
				imageDataStruct = self.file.structs[imageDataOffset]
				width, height, imageType = imageDataStruct.width, imageDataStruct.height, imageDataStruct.imageType
				imageDataLength = imageDataStruct.getDataLength( width, height, imageType )
				texturesTab.renderTextureData( imageDataOffset, width, height, imageType, imageDataLength )

				# Update the Image and Palette tabs
				texturesTab.drawTextureToMainDisplay( imageDataOffset )
				texturesTab.populatePaletteTab( imageDataOffset, imageDataLength, imageType )

				self.lastUpdatedColor = paletteEntryHex
				if canceling:
					printStatus( 'Color edit canceled; the color has been reverted back to the original' )
				else:
					printStatus( 'Palette color updated' )

			except Exception as err:
				printStatus( 'Unable to update the palette color; {}'.format(err) )

	def submit( self ):
		self.updateRecentColors()
		if ( 'Palette' in self.title ) and self.file:
			self.file.unsavedChanges.append( 'Palette color ' + self.initialColor + ' changed to ' + self.currentHexColor + '.' )
		self.close()

	def cancel( self ):
		# If the window was being used to update a palette color, revert the color back to the original
		if 'Palette' in self.title:
			self.updateTexture( self.datDataOffsets[1], True )

		self.currentHexColor = self.initialColor
		self.close()

	def close( self ):
		self.window.destroy()
		if self.windowId:
			del self.windows[self.windowId]


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

		# If this item was selected, move selection to the next item
		if item.selected and index < len( self._list_of_items ):
			newSelectedItem = self._list_of_items[index]
			self._on_item_selected(newSelectedItem)
		
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