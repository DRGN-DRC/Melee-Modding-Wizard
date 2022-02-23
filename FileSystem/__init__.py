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

# DTW's Structural Analysis tab or the following thread/post are useful for more details on structures:
# 		https://smashboards.com/threads/melee-dat-format.292603/post-21913374

import dol		# Not imported like the rest to prevent cyclic import
from .audioFiles import *
from .charFiles import *
from .fileBases import *
from .hsdFiles import *
from .hsdStructures import *


def registerStructureClasses():
	
	# Register structure classes
	for name, obj in inspect.getmembers( hsdStructures ):
		if inspect.isclass( obj ) and issubclass( obj, (StructBase,) ):
			globalData.fileStructureClasses[name] = obj

	for name, obj in inspect.getmembers( charFiles ):
		if inspect.isclass( obj ) and issubclass( obj, (StructBase,) ):
			globalData.fileStructureClasses[name] = obj


def fileFactory( *args, **kwargs ):

	""" Parse out the file name from isoPath, and use that to 
		determine what class to initialize the file as. If the keyword 
		argument "trustNames" is given, filenames will be trusted to 
		determine what kind of file to initialize as. """

	trustyFilenames = kwargs.pop( 'trustNames', None ) # Also removes it from kwargs
	filepath, ext = os.path.splitext( args[3] )
	filename = os.path.basename( filepath ) # Without extension

	# Attempt to determine by file type
	if ext == '.dol':
		return dol.Dol( *args, **kwargs )

	elif ext == '.bin':
		return FileBase( *args, **kwargs )

	elif ext == '.hps':
		return MusicFile( *args, **kwargs )

	elif filename.startswith( 'opening' ) and ext == '.bnr': # May support openingUS.bnr, openingEU.bnr, etc. in the future
		return BannerFile( *args, **kwargs )

	elif ext in ( '.mth', '.ssm', '.sem', '.ini' ):
		return FileBase( *args, **kwargs )

	# If this is initializing an external/standalone file, we may not be able to trust the file name
	elif not trustyFilenames and kwargs.get( 'extPath' ) and kwargs.get( 'source' ) == 'file': # A slower but more thorough check.

		try:
			# Assume it's a DAT file by this point
			fileObj = DatFile( *args, **kwargs )
			fileObj.initialize()
			symbol = fileObj.stringDict.values()[0]

			if 'map_head' in fileObj.stringDict.values():
				return StageFile( *args, **kwargs )

			elif len( fileObj.stringDict ) == 1 and symbol.startswith( 'SIS_' ):
				return SisFile( *args, **kwargs )

			elif fileObj.rootNodes[0][1].startswith( 'ftData' ):
				return CharDataFile( *args, **kwargs )

			elif len( fileObj.stringDict ) == 1 and symbol.startswith( 'Ply' ) and '_ACTION_' in symbol:
				return CharAnimFile( *args, **kwargs )

			elif fileObj.rootNodes[0][1].endswith( '_Share_joint' ): # Indexing a list of tuples
				return CharCostumeFile( *args, **kwargs )

			elif 'MnSelectChrDataTable' in fileObj.stringDict.values():
				return CssFile( *args, **kwargs )
			else:
				return fileObj

		except Exception as err:
			message = 'Unrecognized file:' + kwargs['extPath'] + '\n' + str( err )
			printStatus( message, error=True )
			
			return FileBase( *args, **kwargs )

	else: # A fast check that doesn't require reading/parsing the file (ideal if the file name can be trusted)
		
		if filename.startswith( 'Gr' ):
			return StageFile( *args, **kwargs )

		elif filename.startswith( 'Sd' ):
			return SisFile( *args, **kwargs )

		# Character costume files; excludes 'PlBo.dat'/'PlCa.dat'/etc. and character animation files
		elif filename.startswith( 'Pl' ):

			if len( filename ) == 4 and filename[-2:] != 'Co': # Pl__.dat, excluding PlCo.dat
				charFile = CharDataFile( *args, **kwargs )
				charFile._charAbbr = filename[2:4] # Save some work later

				return charFile
		
			elif len( filename ) == 6:
				if filename[-2:] == 'AJ':
					charFile = CharAnimFile( *args, **kwargs )
					charFile._charAbbr = filename[2:4] # Save some work later
					
					return charFile
				elif filename[2:6] == 'KbCp':
					pass # Oh, Kirby.... (these are copy powers; ftData)
				else:
					charFile = CharCostumeFile( *args, **kwargs )
					charFile._charAbbr = filename[2:4] # Save some work later
					charFile._colorAbbr = filename[4:6]

					return charFile

		elif filename.startswith( 'MnSlChr' ):
			return CssFile( *args, **kwargs )

		return DatFile( *args, **kwargs )


def isValidReplacement( origFileObj, newFileObj ):

	""" Attempts to determine if two files could be valid replacements for one another. """

	# First, a simple check on file class
	fileMismatch = False
	if origFileObj.__class__ != newFileObj.__class__:
		fileMismatch = True

	# If the files (which are the same class) are a sub-class of DAT files....
	elif issubclass( origFileObj.__class__, (DatFile,) ):
		orig20xxVersion = globalData.disc.is20XX

		# Initialize the files so we can get their string dictionaries (and make sure they're not corrupted)
		try:
			origFileObj.initialize()
			origFileStrings = sorted( origFileObj.stringDict.values() )
		except: # The file appears to be corrupted
			origFileStrings = [] # Should still check on the second file
		try:
			newFileObj.initialize()
			newFileStrings = sorted( newFileObj.stringDict.values() )
		except:
			# The file appears to be corrupted; cannot compare further, so just warn the user now
			if not tkMessageBox.askyesno( 'File Corruption Warning', "The file you're importing, {}, could not be initialized, which means "
											"it may be corrupted.\n\nAre you sure you want to continue?".format(newFileObj.filename) ):
				return False
			else:
				return True
		
		# Compare the files' string dictionaries. They're sorted into the same order above (we only care that the same ones exist)
		if origFileStrings != newFileStrings:
			fileMismatch = True
			
		# If the file being imported is the CSS. Check if it's for the right game version
		#elif issubclass( origFileObj, (CssFile,) ):
		elif origFileObj.__class__.__name__ == 'CssFile' and orig20xxVersion:

			# Check if this is a version of 20XX, and if so, get its main build number
			#orig20xxVersion = globalData.disc.is20XX
			if orig20xxVersion:
				if 'BETA' in orig20xxVersion: origMainBuildNumber = int( orig20xxVersion[-1] )
				else: origMainBuildNumber = int( orig20xxVersion[0] )
			else: origMainBuildNumber = 0

			#cssfileSize = os.path.getsize( newExternalFilePath )
			#proposed20xxVersion = globalDiscDetails['is20XX']
			proposed20xxVersion = globalData.disc.get20xxVersion( newFileObj.getData() )
			if proposed20xxVersion:
				if 'BETA' in proposed20xxVersion: proposedMainBuildNumber = int( proposed20xxVersion[-1] )
				else: proposedMainBuildNumber = int( proposed20xxVersion[0] )
			else: proposedMainBuildNumber = 0

			if orig20xxVersion == '3.02': pass # Probably all CSS files will work for this, even the extended 3.02.01 or 4.0x+ files

			elif newFileObj.size < 0x3A3BCD: # importing a vanilla CSS over a 20XX CSS
				if not tkMessageBox.askyesno( 'Warning! 20XX File Version Mismatch', """The CSS file you're """ + 'importing, "' + newFileObj.filename + """", is for a standard copy """
											'of Melee (or a very early version of 20XX), and will not natively work for post-v3.02 versions of 20XX. Alternatively, you can extract '
											"textures from this file and import them manually if you'd like.\n\nAre you sure you want to continue with this import?" ):
					return False

			elif origMainBuildNumber != proposedMainBuildNumber: # These are quite different versions
				if not tkMessageBox.askyesno( 'Warning! 20XX File Version Mismatch', """The CSS file you're """ + 'importing, "' + newFileObj.filename + """", was """
											'not designed for to be used with this version of 20XX and may not work. Alternatively, you can extract '
											"textures from this file and import them manually if that's what you're after.\n\nAre you sure you want to continue with this import?" ):
					return False

	# Check file extension as a last resort
	elif origFileObj.ext != newFileObj.ext:
		fileMismatch = True

	if fileMismatch: # Return false if the user doesn't OK this mismatch
		if not tkMessageBox.askyesno( 'File Mismatch Warning', "The file you're importing, {}, doesn't appear to be a valid replacement "
										"for {}.\n\nAre you sure you want to do this?".format(newFileObj.filename, origFileObj.filename) ):
			return False
		# else return True, below
	
	return True
