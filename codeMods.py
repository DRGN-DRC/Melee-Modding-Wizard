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

# External Dependencies
import os
import json
import codecs
import Tkinter as Tk

from string import hexdigits
from binascii import hexlify
from subprocess import Popen, PIPE

# Internal Dependencies
import globalData
from basicFunctions import toHex, validHex, msg
from guiSubComponents import cmsg


CustomizationTypes = { 'int8': '>b', 'uint8': '>B', 'int16': '>h', 'uint16': '>H', 'int32': '>i', 'uint32': '>I', 'float': '>f' }


# def getCustomCodeLength( customCode, preProcess=False, includePaths=None, customizations=None ):

# 	""" Returns a byte count for custom code (though it is first calculated here in terms of nibbles. Custom syntaxes may be included.
# 		Processing is simplest with hex strings (without whitespace), though input can be ASM if preProcess=True.

# 		Example inputs:
# 			'3C60801A60634340'
# 				or
# 			'3C60801A60634340|S|sbs__b <someFunction>|S|3C60801A48006044' <- includes some special branch syntax. """

# 	if preProcess: # The input is assembly and needs to be assembled into hexadecimal, or it has whitespace that needs removal
# 		customCode = globalData.codeProcessor.preAssembleRawCode( customCode, includePaths )[1]

# 	if '|S|' in customCode: # Indicates a special syntax is present
# 		length = 0
# 		for section in customCode.split( '|S|' ):
# 			if section.startswith( 'sbs__' ) or section.startswith( 'sym__' ) or section.startswith( 'opt__' ):
# 				#length += 8 # expected to be 4 bytes once assembled

# 			# elif section.startswith( 'opt__' ): # Contains customization options (bracketed variable name(s), e.g. '[[Some Var]]')
# 			# 	# Replace variable placeholders with zeros
# 			# 	sectionChunks = section.split( '[[' )
# 			# 	for i, chunk in sectionChunks:
# 			# 		if ']]' in chunk:
# 			# 			varName = chunk.split( ']]' )[0]
# 			# 			sectionChunks[i] = chunk.replace( ']]', '0' )
# 				length += getCustomSectionLength( section )

# 			else:
# 				length += len( section )
# 	else:
# 		length = len( customCode )

# 	return length / 2


def getCustomSectionLength( section ):

	""" Similar to the function above for getting code length, but specific to lines with custom syntax. """

	section = section[5:] # Removing the special syntax identifier (e.g. 'sbs__')
	instruction = section.split()[0]

	if instruction == '.set': return 0
	elif instruction == '.byte': return 1
	elif instruction == '.hword': return 2
	else: return 4


def regionsOverlap( regionList ):

	""" Checks selected custom code regions to make sure they do not overlap one another. """

	overlapDetected = False

	# Compare each region to every other region.
	for i, ( regionStart, regionEnd ) in enumerate( regionList, start=1 ):
		#regionStart, regionEnd = regionEndPoints

		# Loop over the remaining items in the list (starting from second entry on first iteration, third entry from second iteration, etc),
		# so as not to compare to itself, or make any repeated comparisons.
		for nextRegionStart, nextRegionEnd in regionList[i:]:
			# Check if these two regions overlap by any amount
			if nextRegionStart < regionEnd and regionStart < nextRegionEnd: # The regions overlap by some amount.
				overlapDetected = True

				# Determine the names of the overlapping regions, and report this to the user
				msg( 'Warning! One or more regions enabled for custom code overlap each other. The first overlapping areas detected '
					 'are (' + hex(regionStart) + ', ' + hex(regionEnd) + ') and (' + hex(nextRegionStart) + ', ' + hex(nextRegionEnd) + '). '
					 '(There may be more; resolve this case and try again to find others.) '
					 '\n\nThese regions cannot be used in tandem. In the Code-Space Options window, please choose other regions, '
					 'or deselect one of the regions that uses one of the areas shown above.', 'Region Overlap Detected' )
				break

		if overlapDetected: break

	return overlapDetected


class CodeChange( object ):

	def __init__( self, mod, changeType, offset, origCode, rawCustomCode, preProcessedCode, returnCode=-1 ):

		self.mod = mod
		self.type = changeType
		self.length = -1
		self.offset = offset			# May be a DOL offset or RAM address. Should be interpreted by one of the DOL normalization methods
		self.origCode = origCode
		self.rawCode = rawCustomCode
		self.preProcessedCode = preProcessedCode
		self.processStatus = returnCode

	def getLength( self, includePaths=None ):

		if self.length == -1:
			#preProcessedCode = self.getPreProcessedCode()
			#self.length = getCustomCodeLength( preProcessedCode, includePaths=includePaths )

			#self.length = globalData.codeProcessor.checkCodeLength( self.rawCode, includePaths=includePaths )
			self.evaluate()
		
		return self.length
	
	# def getPreProcessedCode( self ):

	# 	""" Assembles source code if it's not already in hex form, and checks for assembly errors. """

	# 	if self.processStatus != -1:
	# 		return self.preProcessedCode

	# 	#rawCustomCode = '\n'.join( customCode ).strip() # Collapses the list of collected code lines into one string, removing leading & trailing whitespace
	# 	returnCode, preProcessedCustomCode = globalData.codeProcessor.preAssembleRawCode( self.rawCode, self.mod.includePaths, suppressWarnings=True )
	# 	# returnCode = 0
	# 	# preProcessedCustomCode = ''

	# 	self.preProcessedCode = preProcessedCustomCode
	# 	self.processStatus = returnCode

	# 	if returnCode == 0:
	# 		return preProcessedCustomCode

	# 	# Store a message for the user on the cause
	# 	elif returnCode == 1:
	# 		self.mod.assemblyError = True
	# 		self.mod.stateDesc = 'Compilation placeholder detected'
	# 		self.mod.errors.append( 'Compilation placeholder detected with code change for {}'.format(self.offset) )
	# 	elif returnCode == 2:
	# 		self.mod.assemblyError = True
	# 		self.mod.stateDesc = 'Assembly error (code starting with {})'.format( self.rawCode[:8] )
	# 		self.mod.errors.append( 'Assembly error with custom code change at {}'.format(self.offset) )
	# 	elif returnCode == 3:
	# 		self.mod.parsingError = True
	# 		self.mod.stateDesc = 'Missing include file: ' + preProcessedCustomCode
	# 		self.mod.errors.append( 'Missing include file {}'.format(preProcessedCustomCode) )
	# 		self.mod.missingIncludes.append( preProcessedCustomCode ) # todo: implement a way to show these to the user (maybe warning icon & interface)

	# 	return ''
	
	def evaluate( self ):

		""" Assembles source code if it's not already in hex form, checks for assembly errors, and
			ensures customization options are present and configured correctly (parsed from codes.json). """

		if self.processStatus != -1:
			return self.processStatus

		#rawCustomCode = '\n'.join( customCode ).strip() # Collapses the list of collected code lines into one string, removing leading & trailing whitespace
		self.processStatus, self.length, codeOrErrorNote, self.syntaxInfo = globalData.codeProcessor.evaluateCustomCode( self.rawCode, self.mod.includePaths, self.mod.customizations )
		
		# returnCode = 0
		# preProcessedCustomCode = ''
		#self.processStatus = returnCode
		if self.processStatus == 0:
			self.preProcessedCode = codeOrErrorNote

		# Store a message for the user on the cause
		elif self.processStatus == 1:
			self.mod.assemblyError = True
			self.mod.stateDesc = 'Assembly error with custom code change at {}'.format( self.offset )
			self.mod.errors.append( 'Assembly error with custom code change at {}:\n{}'.format(self.offset, codeOrErrorNote) )
		elif self.processStatus == 2:
			self.mod.parsingError = True
			self.mod.stateDesc = 'Missing include file: ' + codeOrErrorNote
			self.mod.errors.append( 'Missing include file: {}'.format(codeOrErrorNote) )
			#self.mod.missingIncludes.append( preProcessedCustomCode ) # todo: implement a way to show these to the user (maybe warning icon & interface)
		elif self.processStatus == 3:
			self.mod.parsingError = True
			self.mod.stateDesc = 'Customization option not found: ' + codeOrErrorNote
			self.mod.errors.append( 'Customization option not found: {}'.format(codeOrErrorNote) )
		elif self.processStatus == 4:
			self.mod.parsingError = True
			self.mod.stateDesc = 'Customization option "{}" missing type parameter'.format( codeOrErrorNote )
			self.mod.errors.append( 'Customization option "{}" missing type parameter'.format(codeOrErrorNote) )
		elif self.processStatus == 5:
			self.mod.parsingError = True
			self.mod.stateDesc = 'Unrecognized customization option type: ' + codeOrErrorNote
			self.mod.errors.append( 'Unrecognized customization option type: {}'.format(codeOrErrorNote) )

		return self.processStatus

	def finalizeCode( self, targetAddress ):

		""" Performs final code processing for custom code, just before saving it to the DOL or codes file. 
			The save location for the given code as well as addresses for any standalone functions it might 
			require should already be known by this point, so custom syntaxes can now be resolved. User 
			customization options are also saved to the code. """

		self.evaluate()

		returnCode, finishedCode = globalData.codeProcessor.resolveCustomSyntaxes( targetAddress, self.rawCode, self.preProcessedCode, self.mod.includePaths, self.mod.customizations )

		""" resolveCustomSyntaxes may return these return codes:
				0: Success (or no processing was needed)
				2: Unable to assemble source code with custom syntaxes
				3: Unable to assemble custom syntaxes (source is in hex form)
				4: Unable to find a customization option name
				100: Success, and the last instruction is a custom syntax """

		if returnCode != 0 and returnCode != 100: # In cases of an error, finishedCode will include specifics on the problem
			errorMsg = 'Unable to process custom code for {}:\n\n{}\n\n{}'.format( self.mod.name, self.rawCode, finishedCode )
			msg( errorMsg, 'Error Resolving Custom Syntaxes' )
		elif not finishedCode or not validHex( finishedCode ): # Failsafe; definitely not expected
			msg( 'There was an unknown error while processing the following custom code for {}:\n\n{}'.format(self.mod.name, self.rawCode), 'Error During Final Code Processing' )

		return returnCode, finishedCode


class CodeMod( object ):

	""" Container for all of the information on a code-related game mod. May be for code stored in
		the standard MCM format, or the ASM Mod Folder Structure (AMFS). """

	def __init__( self, name, auth='', desc='', srcPath='', isAmfs=False ):

		self.name = name
		self.auth = auth
		self.desc = desc
		self.data = {} 					# A dictionary that will be populated by lists of "CodeChange" objects
		self.path = srcPath				# Root folder path that contains this mod
		self.type = 'static'
		self.state = 'disabled'
		self.stateDesc = ''				# Describes reason for the state. Shows as a text status on the mod in the GUI
		self.customizations = {}		# Will be a dict of option dictionaries			required keys: name, type, value
																						# optional keys: default, members, 
		self.isAmfs = isAmfs
		self.webLinks = []
		self.fileIndex = -1				# Used only with MCM formatted mods (non-AMFS)
		self.includePaths = []
		self.currentRevision = ''		# Switch this to set the default revision used to add or get code changes
		self.guiModule = None

		self.assemblyError = False
		self.parsingError = False
		#self.missingVanillaHex = False
		self.missingIncludes = []		# Include filesnames detected to be required by the assembler
		self.errors = []

	def setState( self, newState ):

		if self.state == newState:
			return

		self.state = newState
		if self.guiModule:
			self.guiModule.setState( newState )

	def setCurrentRevision( self, revision ):

		""" Creates a new code changes list in the data dictionary, and sets 
			this mod's default revision for getting or adding code changes. """

		if revision not in self.data:
			self.data[revision] = []

		self.currentRevision = revision

	def getCodeChanges( self, forAllRevisions=False ):

		""" Gets all code changes required for a mod to be installed. """

		codeChanges = []

		if forAllRevisions:
			for changes in self.data.values():
				codeChanges.extend( changes )
		else:
			# Get code changes that are applicable to all revisions, as well as those applicable to just the currently loaded revision
			codeChanges.extend( self.data.get('ALL', []) )
			codeChanges.extend( self.data.get(self.currentRevision, []) )

		return codeChanges

	#def preProcessCode( self, customCode ):
	# def getPreProcessedCode( self, codeChange ):

	# 	""" Assembles source code if it's not already in hex form, and checks for assembly errors. """

	# 	if codeChange.preProcessedCode:
	# 		print 'recalling from previously pre-processed code'
	# 		return codeChange.processStatus, codeChange.preProcessedCode

	# 	#rawCustomCode = '\n'.join( customCode ).strip() # Collapses the list of collected code lines into one string, removing leading & trailing whitespace
	# 	returnCode, preProcessedCustomCode = globalData.codeProcessor.preAssembleRawCode( codeChange.rawCode, self.includePaths, suppressWarnings=True )
	# 	# returnCode = 0
	# 	# preProcessedCustomCode = ''

	# 	codeChange.preProcessedCode = preProcessedCustomCode
	# 	codeChange.processStatus = returnCode

	# 	if returnCode != 0:
	# 		# Store a message for the user on the cause
	# 		if returnCode == 1:
	# 			self.assemblyError = True
	# 			self.stateDesc = 'Compilation placeholder detected'
	# 		elif returnCode == 2:
	# 			self.assemblyError = True
	# 			self.stateDesc = 'Assembly error (code starting with {})'.format( codeChange.rawCode[:8] )
	# 		elif returnCode == 3:
	# 			self.parsingError = True
	# 			self.stateDesc = 'Missing include file: ' + preProcessedCustomCode
	# 			self.missingIncludes.append( preProcessedCustomCode ) # todo: implement a way to show these to the user (maybe warning icon & interface)

	# 			return returnCode, ''

	# 	return returnCode, preProcessedCustomCode

	# def finalCodeProcessing( self, ramAddress, codeChange ):

	# 	""" Performs final code processing for custom code, just before saving it to the DOL or codes file. 
	# 		The save location for the given code, as well as address for any standalone functions it might 
	# 		require, should already be known by this point, so custom syntaxes can now be resolved. """

	# 	preProcessedCustomCode = codeChange.getPreProcessedCode()

	# 	returnCode, finishedCode = globalData.codeProcessor.resolveCustomSyntaxes( ramAddress, codeChange.rawCode, preProcessedCustomCode, self.includePaths, options=self.customizations )

	# 	""" resolveCustomSyntaxes may return these return codes:
	# 			0: Success (or no processing was needed)
	# 			2: Unable to assemble source code with custom syntaxes
	# 			3: Unable to assemble custom syntaxes (source is in hex form)
	# 			100: Success, and the last instruction is a custom syntax """

	# 	if returnCode != 0 and returnCode != 100: # In cases of an error, finishedCode will include specifics on the problem
	# 		errorMsg = 'Unable to process custom code for {}:\n\n{}\n\n{}'.format( self.name, codeChange.rawCode, finishedCode )
	# 		msg( errorMsg, 'Error Resolving Custom Syntaxes' )
	# 	elif not finishedCode or not validHex( finishedCode ): # Failsafe; definitely not expected
	# 		msg( 'There was an unknown error while processing the following custom code for {}:\n\n{}'.format(self.name, codeChange.rawCode), 'Error During Final Code Processing' )

	# 	return returnCode, finishedCode

	def addStaticOverwrite( self, offsetString, customCodeLines, origCode='' ):
		# Pre-process custom code
		rawCustomCode = '\n'.join( customCodeLines ).strip() # Collapses the list of collected code lines into one string, removing leading & trailing whitespace
		#returnCode, preProcessedCode = self.preProcessCode( customCodeLines )

		#codeChange = ( 'static', -1, offsetString, origCode, rawCustomCode, preProcessedCode, returnCode )
		codeChange = CodeChange( self, 'static', offsetString, origCode, rawCustomCode, '' )
		self.data[self.currentRevision].append( codeChange )

	# def addShortStatic( self, offsetString, origHex, customCode ):
	# 	# Pre-process custom code
	# 	rawCustomCode = '\n'.join( customCode ).strip() # Collapses the list of collected code lines into one string, removing leading & trailing whitespace
	# 	returnCode, preProcessedCode = self.preProcessCode( customCode )

	# 	codeChange = ( 'static', -1, offsetString, origHex, rawCustomCode, preProcessedCode, returnCode )

	def addInjection( self, offsetString, customCode, origCode='' ):
		# Pre-process custom code
		rawCustomCode = '\n'.join( customCode ).strip() # Collapses the list of collected code lines into one string, removing leading & trailing whitespace
		#returnCode, preProcessedCode = self.preProcessCode( customCode )

		# Add the code change
		#codeChange = ( 'injection', -1, offsetString, origCode, rawCustomCode, preProcessedCode, returnCode )
		codeChange = CodeChange( self, 'injection', offsetString, origCode, rawCustomCode, '' )
		self.data[self.currentRevision].append( codeChange )

		if self.type == 'static': # 'static' is the only type that 'injection' can override.
			self.type = 'injection'

	def addGecko( self, customCode ):

		""" This is for Gecko codes that could not be converted into strictly 
			static overwrites and/or injection mods. Will need the Gecko codehandler for these. """
			
		#rawCustomCode = globalData.codeProcessor.beautifyHex( ''.join(customCode) ) # Formats to 8 byte per line
		#returnCode, preProcessedCode = self.preProcessCode( customCode )
		# for line in customCode:
		# 	rawLine, comments = line.split( '#' )
		# 	rawHex = ''.join( rawLine.split() ) # Strips out whitespace
		rawCustomCode = '\n'.join( customCode ).strip() # Collapses the list of collected code lines into one string, removing leading & trailing whitespace

		#codeChange = ( 'gecko', -1, '', '', rawCustomCode, preProcessedCode, returnCode )
		codeChange = CodeChange( self, 'gecko', '', '', rawCustomCode, '' )
		self.data[self.currentRevision].append( codeChange )

		self.type = 'gecko'

	def addStandalone( self, standaloneName, standaloneRevisions, customCode ):
		# Pre-process custom code
		rawCustomCode = '\n'.join( customCode ).strip() # Collapses the list of collected code lines into one string, removing leading & trailing whitespace
		#returnCode, preProcessedCode = self.preProcessCode( customCode )

		#codeChange = ( 'standalone', -1, standaloneName, '', rawCustomCode, preProcessedCode, returnCode )
		codeChange = CodeChange( self, 'standalone', standaloneName, '', rawCustomCode, '' )
		#preProcessedCode = codeChange.getPreProcessedCode()
		
		# Add this change for each revision that it was defined for
		for revision in standaloneRevisions:
			if revision not in self.data:
				self.data[revision] = []
			self.data[revision].append( codeChange )

		codeChange.evaluate()

		if codeChange.processStatus == 0 and standaloneName not in globalData.standaloneFunctions:
			#globalData.standaloneFunctions[standaloneName] = ( -1, rawCustomCode, preProcessedCode )
			globalData.standaloneFunctions[standaloneName] = ( -1, codeChange )

		self.type = 'standalone'

	def _parseCodeForStandalones( self, preProcessedCode, requiredFunctions, missingFunctions ):

		""" Recursive helper function for getRequiredStandaloneFunctionNames(). Checks 
			one particular code change (injection/overwrite) for standalone functions. """

		if '|S|' in preProcessedCode:
			for section in preProcessedCode.split( '|S|' ):

				if section.startswith( 'sbs__' ) and '<' in section and '>' in section: # Special Branch Syntax; one name expected
					newFunctionNames = ( section.split( '<' )[1].split( '>' )[0], ) # Second split prevents capturing comments following on the same line.

				elif section.startswith( 'sym__' ): # Assume could have multiple names
					newFunctionNames = []
					for fragment in section.split( '<<' ):
						if '>>' in fragment: # A symbol (function name) is in this string segment.
							newFunctionNames.append( fragment.split( '>>' )[0] )
				else: continue

				for functionName in newFunctionNames:
					if functionName in requiredFunctions: continue # This function has already been analyzed

					requiredFunctions.add( functionName )

					# Recursively check for more functions that this function may reference
					if functionName in globalData.standaloneFunctions:
						codeChange = globalData.standaloneFunctions[functionName][1]
						self._parseCodeForStandalones( codeChange.preProcessedCode, requiredFunctions, missingFunctions )
					else:
						missingFunctions.add( functionName )

		return requiredFunctions, missingFunctions

	def getRequiredStandaloneFunctionNames( self ):
		
		""" Gets the names of all standalone functions a particular mod requires. 
			Returns a list of these function names, as well as a list of any missing functions. """

		functionNames = set()
		missingFunctions = set()

		# This loop will be over a list of tuples (code changes) for a specific game version.
		for codeChange in self.getCodeChanges():
			if codeChange.type != 'gecko': #todo allow gecko codes to have SFs
				#preProcessedCode = codeChange.getPreProcessedCode()
				codeChange.evaluate()
				functionNames, missingFunctions = self._parseCodeForStandalones( codeChange.preProcessedCode, functionNames, missingFunctions )

		return list( functionNames ), list( missingFunctions ) # functionNames will also include those that are missing

	def customize( self, name, value ):

		""" Changes a given customization option to the given value. """

		# for option in self.customizations:
		# 	if option['name'] == name:
		# 		option['value'] = value
		# 		break
		# else:
		# 	raise Exception( '{} not found in customization options.'.format(name) )

		self.customizations[name]['value'] = value

	def getCustomization( self, name ):

		""" Gets the currently-set customization option for a given option name. """

		# for option in self.customizations:
		# 	if option['name'] == name:
		# 		return option['value']
		# else:
		# 	raise Exception( '{} not found in customization options.'.format(name) )

		return self.customizations[name]['value']


class CodeLibraryParser():

	""" The primary component for loading a Code Library. Will identify and parse the standard .txt file mod format, 
		as well as the AMFS structure. The primary .include paths for import statements are also set here. 

		Include Path Priority:
			1) The current working directory (usually the MCM root folder)
			2) Directory of the mod's code file (or the code's root folder with AMFS)
			3) The current Mods Library's ".include" directory
			4) The MCM root folder's ".include" directory """

	def __init__( self ):

		#self.modModulesParent = None
		self.stopToRescan = False
		self.codeMods = []
		self.modNames = set()
		#self.errors = []
		#self.includePaths = [ os.path.join(folderPath, '.include'), os.path.join(globalData.scriptHomeFolder, '.include') ]
		self.includePaths = []

		# Build the list of paths for .include script imports (this will be prepended by the folder housing each mod text file)
		# self.codeLibraryPath = globalData.checkSetting( 'codeLibrary' )
		# self.defaultIncludePaths = [ os.path.join(self.codeLibraryPath, '.include'), os.path.join(globalData.scriptHomeFolder, '.include') ]

	def processDirectory( self, folderPath ):

		#self.codeLibraryPath = folderPath
		# self.defaultIncludePaths = [ os.path.join(folderPath, '.include'), os.path.join(globalData.scriptHomeFolder, '.include') ]

		#self.codeMods = []
		itemsInDir = os.listdir( folderPath ) # May be files or folders
		includePaths = [ folderPath ] + self.includePaths
		#totalCreated = len( self.codeMods )
		#somethingCreated = False

		# Check if this is AMFS
		if 'codes.json' in itemsInDir:
			self.parseAmfs( folderPath, includePaths )
			return

		# Check if there are any items in this folder to be processed exclusively (item starting with '+')
		for item in itemsInDir:
			if item.startswith( '+' ):
				itemsInDir = [item]
				break

		for item in itemsInDir:
			if self.stopToRescan:
				break
			elif item.startswith( '!' ) or item.startswith( '.' ): 
				continue # User can optionally exclude these folders from parsing
			# else:
			# 	processItemInDir( folderPath, parentNotebook, item )
			# 	somethingCreated = True
			
			itemPath = os.path.normpath( os.path.join(folderPath, item) )

			if os.path.isdir( itemPath ):
				self.processDirectory( itemPath ) # Recursive fun!

			elif item.lower().endswith( '.txt' ):
				# Add all mod definitions from this file to the GUI
				#mods = 
				self.parseModsLibraryFile( itemPath, includePaths )

				#globalData.codeMods.extend( mods )

				# if totalCreated != len( self.codeMods ):
				# 	somethingCreated = True

		# if not somethingCreated:
		# 	# Nothing to be pulled from this folder. Add a label to convey this.
		# 	Label( parentNotebook, text='No text files found here.', bg='white' ).place( relx=.5, rely=.5, anchor='center' )
		# 	ttk.Label( parentNotebook, image=imageBank['randall'], background='white' ).place( relx=0.5, rely=0.5, anchor='n', y=15 )

	def getModByName( self, name ):

		for mod in self.codeMods:
			if mod.name == name:
				return mod
		else: # The above loop didn't break; couldn't find the mod
			return None

	@staticmethod
	def normalizeRegionString( revisionString ):
		
		""" Ensures consistency in revision strings. Should produce something like 'NTSC 1.02', 'PAL 1.00', etc., or 'ALL'. """

		revisionString = revisionString.upper()
		if 'ALL' in revisionString: return 'ALL'

		# Check for a game/dol version
		verIdPosition = revisionString.find( '.' )
		if verIdPosition == -1: ver = '1.00' # The default assumption
		else: ver = revisionString[verIdPosition-1:verIdPosition+3]

		# Check for the region
		if 'PAL' in revisionString: region = 'PAL '
		else: region = 'NTSC ' # The default assumption

		return region + ver
	
	@staticmethod
	def isStandaloneFunctionHeader( targetDescriptor ):

		""" Identifies a string representing a standalone function. Usually a text line for a mod description 
			header, but may also be used to help recognize the latter half (i.e. target descriptor) of a 
			special branch syntax (such as the '<ShineActionState>' from 'bl <ShineActionState>').
			Comments should already have been removed by this point. """

		if targetDescriptor.startswith('<') and '>' in targetDescriptor and not ' ' in targetDescriptor.split( '>' )[:1]:
			return True
		else:
			return False

	@staticmethod
	def isGeckoCodeHeader( codeline ):
		
		""" Should return True for short header lines such as '1.02', 'PAL', 'ALL', etc (old syntaxes), 
			or 'NTSC 1.02', 'PAL 1.00', etc (new syntaxes) """

		if codeline == '': return False

		isGeckoHeader = False
		if len( codeline ) < 10 and not '<' in codeline:
			codeline = codeline.upper()

			# Check for the old formatting first ('PAL'), or a header designating a Gecko code for all revisions ('ALL')
			if codeline == 'PAL' or codeline == 'ALL': isGeckoHeader = True

			# All other conditions should include a version number (e.g. '1.02')
			elif '.' in codeline[1:]: # Excludes first character, which may be a period indicating an assembly directive
				# Check for a short version number string (still old formatting), e.g. '1.00', '1.01'
				if len( codeline ) == 4: isGeckoHeader = True

				elif 'NTSC' in codeline or 'PAL' in codeline: isGeckoHeader = True # Should be the new syntax, e.g. 'NTSC 1.02'

		return isGeckoHeader

	@staticmethod
	def isSpecialBranchSyntax( code ):

		""" Identifies syntaxes such as "bl 0x800948a8" or "bl <functionName>". 
			Comments should already have been removed by this point. """

		lineParts = code.split()

		if code.lower().startswith( 'b' ) and len( lineParts ) == 2:
			targetDescriptor = lineParts[1]
			if targetDescriptor.startswith('0x8') and len( targetDescriptor ) == 10: return True # Using a RAM address
			elif CodeLibraryParser.isStandaloneFunctionHeader( targetDescriptor ): return True # Using a function name
			
		return False

	@staticmethod
	def containsPointerSymbol( codeLine ): # Comments should already be excluded

		""" Returns a list of names, but can also just be evaluated as True/False. """

		symbolNames = []

		if '<<' in codeLine and '>>' in codeLine:
			for block in codeLine.split( '<<' )[1:]: # Skips first block (will never be a symbol)
				if '>>' in block:
					for potentialName in block.split( '>>' )[:-1]: # Skips last block (will never be a symbol)
						if potentialName != '' and ' ' not in potentialName: 
							symbolNames.append( potentialName )
		
		return symbolNames

	@staticmethod
	def containsCustomization( codeLine ):

		optionNames = []
		
		if '[[' in codeLine and ']]' in codeLine:
			sectionChunks = codeLine.split( '[[' )

			for chunk in sectionChunks:
				if ']]' in chunk:
					optionNames.append( chunk.split(']]')[0] )

		return optionNames

	def parseModsLibraryFile( self, filepath, includePaths ):

		""" Parses mods in the standard MCM format, which reads a single text 
			file and creates mod objects out of the mods found. """

		#geckoCodesAllowed = overwriteOptions[ 'EnableGeckoCodes' ].get()
		category = os.path.basename( filepath )[:-4]

		# Open the text file and get its contents, creating a list of raw chunks of text for each mod
		with open( filepath, 'r' ) as modFile:
			mods = modFile.read().split( '-==-' )

		# Parse each chunk of text for each mod, to get its info and code changes
		for fileIndex, modString in enumerate( mods ):

			if modString.strip() == '' or modString.lstrip()[0] == '!':
				continue # Skip this mod.
			# elif modsLibraryNotebook.stopToRescan:
			# 	break
			
			basicInfoCollected = False
			collectingCustomizations = False
			
			mod = CodeMod( '', srcPath=filepath )
			mod.fileIndex = fileIndex
			mod.desc = [] # Will be transformed into the expected string later
			mod.includePaths = includePaths
			mod.category = category

			# Create some temporary data containers
			origHex = newHex = ''
			offsetString = ''
			customCode = []
			longStaticOriginal = []
			standaloneName = ''
			standaloneRevisions = []
			changeType = 'static'
			customizationOption = {}

			# Iterate over the text/code lines for this mod
			for rawLine in modString.splitlines():
				# Filter out "hard" comments; these will be completely ignored (not collected) by the parser
				if '##' in rawLine:
					rawLine = rawLine.split( '##' )[0].strip()

				# Separate lines of description or code text from comments
				if '#' in rawLine:
					lineParts = rawLine.split( '#' )

					# Check if this line is a url containing a fragment identifier
					if lineParts[0].lstrip().startswith( '<' ):
						# Look for the ending '>' character. Put everything to the left of it into 'line', and everything else should be a comment
						for i, part in enumerate( lineParts, start=1 ):
							if part.rstrip().endswith( '>' ):
								line = '#'.join( lineParts[:i] ).strip()
								lineComments = ' #' + '#'.join( lineParts[i:] )
								break
						else: # No ending '>'; guess this wasn't a url
							line = lineParts[0].strip() # Remove whitespace from start and end of line
							lineComments = ' #' + '#'.join( lineParts[1:] )
					else:
						line = lineParts[0].strip() # Remove whitespace from start and end of line
						lineComments = ' #' + '#'.join( lineParts[1:] )
				else:
					line = rawLine.strip()
					lineComments = ''

				if not basicInfoCollected: # The purpose of this flag is to avoid all of the extra checks in this block once this info is collected.
					# Capture the first non-blank, non-commented line for the name of the mod.
					if not mod.name:
						if line:
							mod.name = rawLine
						continue # Also skip further processing of empty strings if the name hasn't been set yet
						
					if line.startswith( '<' ) and line.endswith( '>' ):
						potentialLink = line[1:-1].replace( '"', '' ) # Removes beginning/ending angle brackets
						mod.webLinks.append( (potentialLink, lineComments) ) # Will be validated on GUI creation

					elif line.startswith( '[' ) and line.endswith( ']' ):
						mod.auth = line.split(']')[0].replace( '[', '' )
						basicInfoCollected = True
						collectingCustomizations = False
						
						if customizationOption:
							mod.customizations.append( customizationOption )

					elif line.lower().startswith( 'customizations:' ):
						collectingCustomizations = True

					elif collectingCustomizations:
						try:
							if '=' in line: # name/type header for a new option
								# Store a previously collected option
								if customizationOption:
									mod.customizations.append( customizationOption )
								customizationOption = {}

								# Parse out the option name and type
								typeName, valueInfo = line.split( '=' )
								typeNameParts = typeName.split() # Splitting on whitespace
								customizationOption['name'] = ' '.join( typeNameParts[1:] )
								customizationOption['type'] = typeNameParts[0]

								# Validate the type
								if customizationOption['type'] not in CustomizationTypes:
									raise Exception( 'unsupported option type' )

								# Check for value ranges
								if ';' in valueInfo:
									defaultValue, rangeString = valueInfo.split( ';' )
									customizationOption['default'] = defaultValue.strip()
									customizationOption['range'] = rangeString.strip()
								elif valueInfo.strip():
									customizationOption['default'] = valueInfo.strip()
								customizationOption['value'] = customizationOption['default']
								customizationOption['description'] = lineComments

							# Process enumerations/members of an existing option
							elif customizationOption and ':' in line:
								# Add the members list if not already present
								members = customizationOption.get( 'members' )
								if not members:
									customizationOption['members'] = []

								value, name = line.split( ':' )
								if lineComments:
									customizationOption['members'].append( [name.strip(), value.strip(), lineComments] )
								else:
									customizationOption['members'].append( [name.strip(), value.strip()] )

						except Exception as err:
							mod.parsingError = True
							mod.stateDesc = 'Customizations parsing error; {}'.format(err)
							mod.errors.append( 'Customizations parsing error; {}'.format(err) )
							continue

					else: # Assume all other lines are more description text
						mod.desc.append( rawLine )

					continue

				elif ( line.startswith('Version') or line.startswith('Revision') ) and 'Hex to Replace' in line: # Presense of this line is optional
					continue
				
				# If this is reached, the name, description, and author have been parsed. Begin code parsing
				isVersionHeader = False
				headerStringStart = '' # May contain the current revision (e.g. "NTSC 1.02")

				# Check if this is the start of a new code change
				if '---' in line:
					headerStringStart = line.split('---')[0].rstrip().replace(' ', '') # Left-hand strip of whitespace has already been done
					if headerStringStart: # i.e. it's not an empty string
						isVersionHeader = True

				# Check if it's a Gecko codes header (the version or revision should be the only thing on that line), but don't set that flag yet
				elif self.isGeckoCodeHeader( line ):
					isVersionHeader = True
					headerStringStart = line

				# If this is a header line (marking the start of a new code change), check for lingering collected codes that must first be added to the previous code change.
				if ( isVersionHeader or '---' in line or self.isStandaloneFunctionHeader(line) ) and customCode != []:
					if changeType == 'injection':
						mod.addInjection( offsetString, customCode, origHex )
					elif changeType == 'gecko':
						mod.addGecko( customCode )
					elif changeType == 'standalone':
						mod.addStandalone( standaloneName, standaloneRevisions, customCode )
					elif changeType == 'longStaticNew':
						mod.addStaticOverwrite( offsetString, customCode, '\n'.join(longStaticOriginal) )
					elif changeType == 'static':
						mod.addStaticOverwrite( offsetString, customCode, origHex )
					else:
						mod.parsingError = True
						#mod.state = 'unavailable'
						mod.stateDesc = 'Parsing error; improper mod formatting'
						mod.errors.append( 'Parsing error; improper mod formatting' )

					# Empty current temporary data containers for code
					customCode = []
					longStaticOriginal = []
					standaloneName = ''
					standaloneRevisions = []
					changeType = 'static'

				# elif line == '->': # Divider between long static overwrite original and new code.
				# 	if isLongStaticOriginal and longStaticOriginal != []:
				# 		isLongStaticOriginal = False
				# 		isLongStaticNew = True
				elif line == '->' and changeType == 'longStaticOrig':
					changeType = 'longStaticNew'
					continue

				if isVersionHeader:
					# Remember the version that subsequent code lines are for
					# currentRevision = self.normalizeRegionString( headerStringStart )
					# if currentRevision not in mod.data: mod.data[currentRevision] = []
					mod.setCurrentRevision( self.normalizeRegionString(headerStringStart) )

					if self.isGeckoCodeHeader( line ):
						# isGeckoCode = True # True for just this code change, not necessarily for the whole mod, like the variable below
						# mod.type = 'gecko'
						changeType = 'gecko'

				elif self.isStandaloneFunctionHeader( line ):
					#mod.type = 'standalone'
					changeType = 'standalone'
					standaloneName, revisionIdentifiers = line.lstrip()[1:].split( '>' )

					# Parse content after the header (on the same line) to see if they are identifiers for what game version to add this for.
					if revisionIdentifiers.strip() == '':
						standaloneRevisions = [ 'ALL' ]
					else:
						for revision in revisionIdentifiers.split( ',' ):
							thisRevision = self.normalizeRegionString( revision )

							if thisRevision == 'ALL': # Override any versions that might already be accumulated, and set the list to just ALL
								standaloneRevisions = [ 'ALL' ]
								break

							else: standaloneRevisions.append( thisRevision )
					continue

				if mod.currentRevision != '' or standaloneRevisions != []: # At least one of these should be set, even for subsequent lines that don't have a version header.
					if line and '---' in line: # Ensures the line isn't blank, and it is the start of a new code change definition
						hexCodes = [ item.strip() for item in line.replace('->', '--').split('-') if item ] # Breaks down the line into a list of values.
						if isVersionHeader: hexCodes.pop(0) # Removes the revision indicator.
					
						offsetString = hexCodes[0]
						totalValues = len( hexCodes )

						if totalValues == 1: # This is the header for a Long static overwrite (e.g. "1.02 ----- 0x804d4d90 ---"). (hexCodes would actually be just ["0x804d4d90"])
							#isLongStaticOriginal = True
							changeType = 'longStaticOrig'

						elif totalValues == 2: # Should have an offset and an origHex value; e.g. from a line like "1.02 ------ 804D7A4C --- 00000000 ->"
							origHex = ''.join( hexCodes[1].replace('0x', '').split() ) # Remove whitespace

							# if not validHex( origHex ): # This is the game's original code, so it should just be hex.
							# 	msg( 'Problem detected while parsing "' + mod.name + '" in the mod library file "' 
							# 		+ os.path.basename( filepath ) + '" (index ' + str(fileIndex+1) + ').\n\n'
							# 		'There is an invalid (non-hex) original hex value: ' + origHex, 'Incorrect Mod Formatting (Error Code 04.2)' )
							# 	mod.parsingError = True
							# 	customCode = []
							# 	break

						elif totalValues > 2: # Could be a standard static overwrite (1-liner), long static overwrite, or an injection mod
							origHex = ''.join( hexCodes[1].replace('0x', '').split() ) # Remove whitespace
							newHex = hexCodes[2]

							if newHex.lower() == 'branch':
								# isInjectionCode = True # Will later be switched back off, which is why this is separate from the modType variable below
								# if mod.type == 'static': mod.type = 'injection' # 'static' is the only type that 'injection' can override.
								changeType = 'injection'
								
							else: 
								# If the values exist and are valid, add a codeChange tuple to the current game version changes list.
								# if not validHex( offsetString.replace( '0x', '' ) ): # Should just be a hex offset.
								# 	msg( 'Problem detected while parsing "' + mod.name + '" in the mod library file "' 
								# 		+ os.path.basename( filepath ) + '" (index ' + str(fileIndex+1) + ').\n\n'
								# 		'There is an invalid (non-hex) offset value: ' + offsetString, 'Incorrect Mod Formatting (Error Code 04.1)' )
								# 	mod.parsingError = True
								# 	customCode = []
								# 	break
								# elif not validHex( origHex ): # This is the game's original code, so it should just be hex.
								# 	msg( 'Problem detected while parsing "' + mod.name + '" in the mod library file "' 
								# 		+ os.path.basename( filepath ) + '" (index ' + str(fileIndex+1) + ').\n\n'
								# 		'There is an invalid (non-hex) original hex value: ' + origHex, 'Incorrect Mod Formatting (Error Code 04.2)' )
								# 	mod.parsingError = True
								# 	customCode = []
								# 	break
								# else:
								customCode.append( newHex + lineComments )

						if not offsetString.startswith( '0x' ):
							offsetString = '0x' + offsetString

					elif not isVersionHeader:
						#if isLongStaticOriginal:
						if changeType == 'longStaticOrig':
							longStaticOriginal.append( line )

						else: # This may be an empty line/whitespace. Only adds this if there is already custom code accumulating for something.
							customCode.append( rawLine )

			# End of per-line loop for the current mod (all lines have now been gone through).
			# If there is any code left, save it to the last revision's last code change.
			if customCode != [] or standaloneRevisions != []:
				# rawCustomCode = '\n'.join( customCode ).strip()
				# returnCode, preProcessedCustomCode = globalData.codeProcessor.preAssembleRawCode( customCode, includePaths, suppressWarnings=True )

				# if returnCode == 0 and preProcessedCustomCode:
				# 	customCodeLength = getCustomCodeLength( preProcessedCustomCode )

				# 	if isInjectionCode: 	modData[currentRevision].append( ( 'injection', customCodeLength, offsetString, origHex, rawCustomCode, preProcessedCustomCode ) )
				# 	elif isGeckoCode: 		modData[currentRevision].append( ( 'gecko', customCodeLength, '', '', rawCustomCode, preProcessedCustomCode ) )
				# 	elif standaloneName:
				# 		for revision in standaloneRevisions:
				# 			if revision not in modData: modData[revision] = []
				# 			modData[revision].append( ( 'standalone', customCodeLength, standaloneName, '', rawCustomCode, preProcessedCustomCode ) )
				# 	elif isLongStaticNew:
				# 		modData[currentRevision].append( ( 'static', customCodeLength, offsetString, '\n'.join(longStaticOriginal), rawCustomCode, preProcessedCustomCode ) )
				# 	else: # standard static (1-liner)
				# 		# if not origHex or not newHex:
				# 		# 	cmsg( '\nProblem detected while parsing "' + mod.name + '" in the mod library file "' 
				# 		# 		+ os.path.basename( filepath ) + '" (index ' + str(fileIndex+1) + ').\n\n'
				# 		# 		'One of the inputs for a static overwrite (origHex or newHex) were found to be empty, which means that '
				# 		# 		'the mod is probably not formatted correctly.', 'Incorrect Mod Formatting (Error Code 04.4)' )
				# 		# 	mod.parsingError = True
				# 		# 	customCode = []
				# 		# 	break
				# 		# elif getCustomCodeLength( origHex ) != customCodeLength:
				# 		# 	cmsg( '\nProblem detected while parsing "' + mod.name + '" in the mod library file "' 
				# 		# 		+ os.path.basename( filepath ) + '" (index ' + str(fileIndex+1) + ').\n\n'
				# 		# 		'Inputs for static overwrites (the original code and custom code) should be the same '
				# 		# 		'length. Original code:\n' + origHex + '\n\nCustom code:\n' + newHex, 'Incorrect Mod Formatting (Error Code 04.3)' )
				# 		# 	mod.parsingError = True
				# 		# 	customCode = []
				# 		# 	break
				# 		# else:
				# 		modData[currentRevision].append( ( 'static', customCodeLength, offsetString, origHex, rawCustomCode, preProcessedCustomCode ) )

				# elif returnCode == 2:
				# 	mod.assemblyError = True
				# elif returnCode == 3:
				# 	mod.missingIncludes = True
				
				if changeType == 'injection':
					mod.addInjection( offsetString, customCode, origHex )
				elif changeType == 'gecko':
					mod.addGecko( customCode )
				elif changeType == 'standalone':
					mod.addStandalone( standaloneName, standaloneRevisions, customCode )
				elif changeType == 'longStaticNew':
					mod.addStaticOverwrite( offsetString, customCode, '\n'.join(longStaticOriginal) )
				elif changeType == 'static':
					mod.addStaticOverwrite( offsetString, customCode, origHex )
				else:
					mod.parsingError = True
					#mod.state = 'unavailable'
					mod.stateDesc = 'Parsing error; improper mod formatting'
					mod.errors.append( 'Parsing error; improper mod formatting' )

			# If codes were found for the current mod, create a gui element for it and populate it with the mod's details.
			#if not modsLibraryNotebook.stopToRescan: # This might be queued in order to halt and restart the scan
				# Create a new module in the GUI, both for user interaction and data storage
				# newModModule = ModModule( modModulesParent, modName, '\n'.join(mod.desc).strip(), mod.auth, modData, modType, webLinks )
				# newModModule.pack( fill='x', expand=1 )
				# newModModule.sourceFile = filepath
				# newModModule.fileIndex = fileIndex
				# newModModule.includePaths = includePaths
				# genGlobals['allMods'].append( newModModule )

				# # Set the mod widget's status and add it to the global allModNames list
				# if modData == {}: newModModule.setState( 'unavailable', specialStatusText='Missing mod data.' )
				# elif mod.parsingError: newModModule.setState( 'unavailable', specialStatusText='Error detected during parsing.' )
				# elif assemblyError: newModModule.setState( 'unavailable', specialStatusText='Error during assembly' )
				# elif missingIncludes: newModModule.setState( 'unavailable', specialStatusText='Missing include file: ' + preProcessedCustomCode )
				# else:
				# 	# No problems detected so far. Check if this is a duplicate mod, and add it to the list of all mods if it's not
				# 	if modName in genGlobals['allModNames']:
				# 		newModModule.setState( 'unavailable', specialStatusText='Duplicate Mod' )
				# 	else:
				# 		genGlobals['allModNames'].add( modName )

				# 	if mod.type == 'gecko' and not geckoCodesAllowed:
				# 		newModModule.setState( 'unavailable' )
				# 	elif settingsFile.alwaysEnableCrashReports and modName == "Enable OSReport Print on Crash":
				# 		newModModule.setState( 'pendingEnable' )

			mod.desc = '\n'.join( mod.desc )

			# if not mod.data:
			# 	mod.state = 'unavailable'
			# 	mod.stateDesc = 'Missing mod data'
			# elif mod.name in self.modNames:
			# 	mod.state = 'unavailable'
			# 	mod.stateDesc = 'Duplicate Mod'

			# globalData.codeMods.append( mod )
			# # self.modNames.add( mod.name )
			# self.modNames.add( mod.name )

			self.storeMod( mod )

		# 	collectedMods.append( mod )

		# return collectedMods

	def storeMod( self, mod ):

		""" Store the given mod, and perfom some basic validation on it. """
		
		if not mod.data:
			mod.state = 'unavailable'
			mod.stateDesc = 'Missing mod data'
			mod.errors.append( 'Missing mod data; may be defined incorrectly')
		elif mod.name in self.modNames:
			mod.state = 'unavailable'
			mod.stateDesc = 'Duplicate mod'
			mod.errors.append( 'Duplicate mod; more than one by this name in library')

		self.codeMods.append( mod )
		self.modNames.add( mod.name )
				
	def parseGeckoCode( self, codeLines, dol ):

		""" Returns a tuple of 'title', 'author(s)', and the mod's code changes'.
			The code changes list is in the same format as those parsed by codes in MCM's
			usual format, and created internally as 'ModModule' modData dictionary entries. """

		title = authors = ''
		description = []
		codeChanges = []		# A Codechange = a tuple of ( changeType, customCodeLength, offset, originalCode, customCode, preProcessedCustomCode )
		codeBuffer = [ '', -1, '', [], 0 ] # Temp staging area while code lines are collected, before they are submitted to the above codeChanges list.

		# Load the DOL for this revision (if one is not already loaded), for original/vanilla code look-ups
		#vanillaDol = loadVanillaDol( gameRevision )

		for line in codeLines:
			if not line.strip(): continue # Skip whitespace lines

			elif line.startswith( '*' ): # [Another?] form of comment
				description.append( line[1:] )

			elif line.startswith( '$' ) or ( '[' in line and ']' in line ):
				line = line.lstrip( '$' )

				# Sanity check; the buffer should be empty if a new code is starting
				if codeBuffer:
					# print 'Warning! Gecko code parsing ran into an error or an invalid code!'
					# print 'The code buffer was not emptied before a new code was encountered.'
					# codeBuffer = []
					raise Exception( 'Code buffer not emptied before new code was encountered.' )

				if title: # It's already been set, meaning this is another separate code
					break

				elif '[' in line and ']' in line:
					titleParts = line.split( '[' )
					authors = titleParts[-1].split( ']' )[0]

					title = '['.join( titleParts[:-1] )
				else:
					title = line

			elif codeBuffer: # Multi-line code collection is in-progress
				changeType, customCodeLength, ramAddress, _, collectedCodeLength = codeBuffer

				newHex = ''.join( line.split( '#' )[0].split() ) # Should remove all comments and whitespace
				newHexLength = len( newHex ) / 2 # Divide by 2 to count by bytes rather than nibbles

				if collectedCodeLength + newHexLength < customCodeLength:
					codeBuffer[3].append( newHex )
					codeBuffer[4] += newHexLength

				else: # Last line to collect from for this code change
					# Collect the remaining new hex and consolidate it
					bytesRemaining = customCodeLength - collectedCodeLength
					codeBuffer[3].append( newHex[:bytesRemaining*2] ) # x2 to count by nibbles
					rawCustomCode = ''.join( codeBuffer[3] ) # no whitespace
					#rawCustomCode = ''.join( codeLines[1:] )
					customCode = globalData.codeProcessor.beautifyHex( rawCustomCode ) # Formats to 8 byte per line

					# Get the original/vanilla code
					intRamAddress = int( ramAddress[2:], 16 ) # Trims off leading 0x before conversion
					dolOffset = dol.offsetInDOL( intRamAddress )
					if dolOffset == -1: #originalCode = ''
						raise Exception( 'Unable to convert Gecko code; no equivalent DOL offset for {}.'.format(ramAddress) )
					elif changeType == 'static': # Long static overwrite (06 opcode)
						originalCode = hexlify( dol.getData(dolOffset, customCodeLength) )
					else: # Injection
						originalCode = hexlify( dol.getData(dolOffset, 4) ) # At the injection point

					# Add the finished code change to the list, and reset the buffer
					codeChanges.append( (changeType, customCodeLength, ramAddress, originalCode, customCode, rawCustomCode, 0) )
					#codeChanges.append( (changeType, customCodeLength, ramAddress, '', customCode, rawCustomCode, 0) )
					codeBuffer = [ '', -1, -1, [], 0 ]

			elif line.startswith( '04' ): # A Static Overwrite
				ramAddress = '0x80' + line[2:8]
				customCode = line.replace( ' ', '' )[8:16]

				# Get the vanilla code from the DOL
				dolOffset = dol.offsetInDOL( int(ramAddress, 16) )
				if dolOffset == -1: #originalCode = ''
					raise Exception( 'Unable to convert Gecko code; no equivalent DOL offset for {}.'.format(ramAddress) )
				else: originalCode = hexlify( dol.getData(dolOffset, 4) )

				codeChanges.append( ('static', 4, ramAddress, originalCode, customCode, customCode, 0) )
				#codeChanges.append( ('static', 4, ramAddress, '', customCode, customCode, 0) )

			elif line.startswith( '06' ): # A Long Static Overwrite
				ramAddress = '0x80' + line[2:8]
				totalBytes = int( line.replace( ' ', '' )[8:16], 16 )

				# Set up the code buffer, which will be filled with data until it's gathered all the bytes
				codeBuffer = [ 'static', totalBytes, ramAddress, [], 0 ]

			elif line.upper().startswith( 'C2' ): # An Injection
				ramAddress = '0x80' + line[2:8]
				totalBytes = int( line.replace( ' ', '' )[8:16], 16 ) * 8 # The count in the C2 line is a number of lines, where each line should be 8 bytes

				# Set up the code buffer, which will be filled with data until it's gathered all the bytes
				codeBuffer = [ 'injection', totalBytes, ramAddress, [], 0 ]

			else:
				raise Exception( 'Found an unrecognized Gecko opcode: ' + line.lstrip()[:2].upper() )

		return title, authors, '\n'.join( description ), codeChanges

	def parseAmfs( self, folderPath, includePaths ):

		""" This method is the primary handler of the ASM Mod Folder Structure (AMFS). This will 
			create a mod container object to store the mod's code changes and other data, and 
			step through each code change dictionary in the JSON file's build list. """
			
		# Open the json file and get its file contents (need to do this early so we can check for a mod category)
		try:
			with open( os.path.join(folderPath, 'codes.json'), 'r' ) as jsonFile:
				jsonContents = json.load( jsonFile )
		except Exception as err:
			errMsg = 'Encountered an error when attempting to open "{}" (likely due to incorrect formatting); {}'.format( os.path.join(folderPath, 'codes.json'), err )
			msg( errMsg )
			return

		codeSection = jsonContents.get( 'codes' )
		primaryCategory = jsonContents.get( 'category', 'Uncategorized' ) # Applies to all in this json's "codes" list

		if codeSection:
			for codeset in codeSection:
				# Typecast the authors and description lists to strings
				authors = ', '.join( codeset['authors'] )
				description = '\n'.join( codeset['description'] )

				# Create the mod object
				mod = CodeMod( codeset['name'], authors, description, folderPath, True )
				mod.category = codeset.get( 'category', primaryCategory ) # Secondary definition, per-code dict basis
				mod.customizations = codeset.get( 'customizations', {} )

				# Set the revision (region/version) this code is for
				revision = codeset.get( 'revision' )
				if revision:
					revision = self.normalizeRegionString( revision ) # Normalize it
				else:
					revision = 'NTSC 1.02'
				mod.setCurrentRevision( revision )

				# Get paths for .include ASM import statements, and web links
				mod.includePaths = includePaths
				links = codeset.get( 'webLinks', () )
				for item in links:
					if isinstance( item, (tuple, list) ) and len( item ) == 2:
						mod.webLinks.append( item )
					elif isinstance( item, (str, unicode) ): # Assume it's just a url, missing a comment
						mod.webLinks.append( (item, '') )

				buildSet = codeset.get( 'build' )

				if buildSet:
					for codeChangeDict in buildSet:
						codeType = codeChangeDict['type']
						
						if codeType == 'replace': # Static Overwrite; basically an 04 Gecko codetype (hex from json)
							# self.parseAmfsReplace( codeChangeDict, mod )
							# if mod.assemblyError or mod.missingVanillaHex or mod.missingIncludes: break
							# customCode = codeChangeDict['value']
							# offset = codeChangeDict['address']
							mod.addStaticOverwrite( codeChangeDict['address'], codeChangeDict['value'].splitlines() )

						elif codeType == 'inject': # Standard code injection
							self.parseAmfsInject( codeChangeDict, mod )
							# if mod.assemblyError or mod.parsingError or mod.missingVanillaHex or mod.missingIncludes: break
							# elif mod.type == 'static': mod.type = 'injection' # 'static' is the only type that 'injection' can override.

						elif codeType == 'replaceCodeBlock': # Static overwrite of variable length (hex from file)
							self.parseAmfsReplaceCodeBlock( codeChangeDict, mod )
							# if mod.assemblyError or mod.missingVanillaHex or mod.missingIncludes: break

						elif codeType == 'branch' or codeType == 'branchAndLink':
							mod.errors.append( 'The ' + codeType + ' AMFS code type is not yet supported' )

						elif codeType == 'injectFolder':
							self.parseAmfsInjectFolder( codeChangeDict, mod )
							# if mod.assemblyError or mod.parsingError or mod.missingVanillaHex or mod.missingIncludes: break
							# elif mod.type == 'static': mod.type = 'injection' # 'static' is the only type that 'injection' can override.

						elif codeType == 'replaceBinary':
							mod.errors.append( 'The replaceBinary AMFS code type is not yet supported' )

						elif codeType == 'binary':
							mod.errors.append( 'The binary AMFS code type is not yet supported' )

						else:
							mod.errors.append( 'Unrecognized AMFS code type: ' + codeType )

					# Create a new code module, and add it to the GUI
					#self.buildCodeModule( mod )
					
					# Disable the mod for certain cases
					# if not mod.data:
					# 	mod.state = 'unavailable'
					# 	mod.stateDesc = 'Missing mod data'
					# elif mod.name in self.modNames:
					# 	mod.state = 'unavailable'
					# 	mod.stateDesc = 'Duplicate Mod'

					# globalData.codeMods.append( mod )
					# self.modNames.add( mod.name )

					self.storeMod( mod )

				else: # Build all subfolders/files
					mod.errors.append( "No 'build' section found in codes.json" )

		else: # Grab everything from the current folder (and subfolders). Assume .s are static overwrites, and .asm are injections
			# Typecast the authors and description lists to strings
			# authors = ', '.join( codeset['authors'] )
			# description = '\n'.join( codeset['description'] )
			
			# mod = CodeMod( codeset['name'], authors, description, fullFolder, True )

			#self.errors.append( "No 'codes' section found in codes.json" ) #todo
			msg( 'No "codes" section found in codes.json for the mod in "{}".'.format(folderPath) )

	# def buildCodeModule( self, mod ):

	# 	""" Builds a code module for the GUI, sets its status, and adds it to the interface. """

	# 	# Create a new module in the GUI, both for user interaction and data storage
	# 	newModModule = ModModule( self.modModulesParent, mod.name, mod.desc, mod.auth, mod.data, mod.type, mod.webLinks )
	# 	newModModule.pack( fill='x', expand=1 )
	# 	newModModule.sourceFile = mod.path
	# 	newModModule.fileIndex = 0
	# 	newModModule.includePaths = mod.includePaths
	# 	genGlobals['allMods'].append( newModModule )

	# 	# Set the mod widget's status and add it to the global allModNames list
	# 	if mod.data == {}: newModModule.setState( 'unavailable', specialStatusText='Missing mod data.' )
	# 	elif mod.parsingError: newModModule.setState( 'unavailable', specialStatusText='Error detected during parsing.' )
	# 	elif mod.missingVanillaHex: newModModule.setState( 'unavailable', specialStatusText='Unable to get vanilla hex' )
	# 	elif mod.assemblyError: newModModule.setState( 'unavailable', specialStatusText='Error during assembly' )
	# 	elif mod.missingIncludes: newModModule.setState( 'unavailable', specialStatusText='Missing include file: ' + mod.missingIncludes )
	# 	else:
	# 		# No problems detected so far. Check if this is a duplicate mod, and add it to the list of all mods if it's not
	# 		if mod.name in genGlobals['allModNames']:
	# 			newModModule.setState( 'unavailable', specialStatusText='Duplicate Mod' )
	# 		else:
	# 			genGlobals['allModNames'].add( mod.name )

	# 		if mod.type == 'gecko' and not overwriteOptions[ 'EnableGeckoCodes' ].get():
	# 			newModModule.setState( 'unavailable' )
	# 		elif settingsFile.alwaysEnableCrashReports and mod.name == "Enable OSReport Print on Crash":
	# 			newModModule.setState( 'pendingEnable' )

	# 	if self.errors:
	# 		print '\nFinal errors:', '\n'.join( self.errors )

	# def parseAmfsReplace( self, codeChangeDict, mod ):

	# 	""" AMFS Static Overwrite of 4 bytes; custom hex code sourced from json file. """

	# 	# Pre-process the custom code (make sure there's no whitespace, and/or assemble it)
	# 	customCode = codeChangeDict['value']
	# 	returnCode, preProcessedCustomCode = globalData.codeProcessor.preAssembleRawCode( customCode, mod.includePaths, suppressWarnings=True )
	# 	if returnCode in ( 1, 2 ):
	# 		mod.assemblyError = True
	# 		self.errors.append( "Encountered a problem while assembling a 'replace' code change" )
	# 		return
	# 	elif returnCode == 3: # Missing an include file
	# 		mod.missingIncludes = preProcessedCustomCode # The custom code string will be the name of the missing include file
	# 		self.errors.append( "Unable to find this include file: " + preProcessedCustomCode )
	# 		return
		
	# 	# Get the offset of the code change, and the original code at that location
	# 	offset = codeChangeDict['address']
	# 	# dolOffset = normalizeDolOffset( offset, dolObj=mod.vanillaDol )
	# 	# origHex = getVanillaHex( dolOffset, revision=mod.revision, suppressWarnings=False )
	# 	# if not origHex:
	# 	# 	mod.missingVanillaHex = True
	# 	# 	self.errors.append( "Unable to get original code for a 'replace' code change" )
	# 	# 	return

	# 	# Preserve the annotation using a comment
	# 	annotation = codeChangeDict.get( 'annotation', None )
	# 	if annotation:
	# 		customCode += ' # ' + annotation

	# 	mod.data[mod.currentRevision].append( ('static', 4, offset, '', customCode, preProcessedCustomCode, returnCode) )

	def readInjectionAddressHeader( self, asmFile ):

		""" Reads and returns the address for a custom code overwrite or injection from a .asm file header. """

		# Parse the first line to get an injection site (offset) for this code
		headerLine = asmFile.readline()

		# Check for the original 1-line format
		if headerLine.startswith( '#' ) and 'inserted' in headerLine:
			return headerLine.split()[-1] # Splits by whitespace and gets the resulting last item

		# Check for the multi-line format
		elif headerLine.startswith( '#######' ):
			while 1:
				line = asmFile.readline()
				if 'Address:' in line:
					return line.split()[2]
				elif line.startswith( '#######' ) or not line:
					return -1 # Failsafe; reached the end of the header (or file!) without finding the address

	def getCustomCodeFromFile( self, fullAsmFilePath, mod, parseOffset=False, annotation='' ):

		""" Gets custom code from a given file and pre-processes it (removes whitespace, and/or assembles it). 
			If parseOffset is False, the offset in the file header isn't needed because the calling function 
			already has it from a codeChange dictionary. (If it does need to be parsed, the calling function 
			only had a sourceFile for reference (most likely through a injectFolder code type).) 
				May return these return codes:
				->	0: Success
					1: Compilation placeholder or branch marker detected in original code
					2: Error during assembly
					3: Include file(s) could not be found
				->	4: Missing source file
				->	5: Encountered an error reading the source file """

		if not annotation: # Use the file name for the annotation (without file extension)
			annotation = os.path.splitext( os.path.basename(fullAsmFilePath) )[0]
		
		# Get the custom code, and the address/offset if needed
		try:
			# Open the file in byte-reading mode (rb). Strings will then need to be encoded.
			with codecs.open( fullAsmFilePath, encoding='utf-8' ) as asmFile: # Using a different read method for UTF-8 encoding
				if parseOffset:
					offset = self.readInjectionAddressHeader( asmFile )
					decodedString = asmFile.read().encode( 'utf-8' )
					customCode = '# {}\n{}'.format( annotation, decodedString )
				else:
					offset = ''

					# Collect all of the file contents
					firstLine = asmFile.readline().encode( 'utf-8' )
					theRest = asmFile.read().encode( 'utf-8' )

					# Clean up the header line (changing first line's "#To" to "# To")
					if firstLine.startswith( '#To' ):
						customCode = '# {}\n# {}\n{}'.format( annotation, firstLine.lstrip( '# '), theRest )
					else:
						customCode = '# {}\n{}\n{}'.format( annotation, firstLine, theRest )

		except IOError as err: # File couldn't be found
			print err
			mod.parsingError = True
			#mod.state = 'unavailable'
			mod.stateDesc = 'Missing source files'
			mod.errors.append( "Unable to find the file " + os.path.basename(fullAsmFilePath) )
			return 4, '', ''
			
		except Exception as err: # Unknown error
			print err
			mod.parsingError = True
			#mod.state = 'unavailable'
			mod.stateDesc = 'File reading error with ' + annotation
			mod.errors.append( 'Encountered an error while reading {}: {}'.format(os.path.basename(fullAsmFilePath), err) )
			return 5, '', ''

		return 0, offset, customCode
			
		# Pre-process the custom code (make sure there's no whitespace, and/or assemble it)
		# returnCode, preProcessedCustomCode = globalData.codeProcessor.preAssembleRawCode( customCode, [os.path.dirname(fullAsmFilePath)] + mod.includePaths, suppressWarnings=True )

		# # Check for errors
		# if returnCode == 0:
		# 	return 0, offset, customCode, preProcessedCustomCode

		# elif returnCode in ( 1, 2 ):
		# 	mod.assemblyError = True
		# 	#mod.state = 'unavailable'
		# 	mod.stateDesc = 'Assembly error'
		# 	mod.errors.append( 'Encountered a problem while assembling ' + os.path.basename(fullAsmFilePath) )

		# elif returnCode == 3: # Missing an include file
		# 	mod.missingIncludes = preProcessedCustomCode # The custom code string will be the name of the missing include file
		# 	#mod.state = 'unavailable'
		# 	mod.stateDesc = 'Missing include file: ' + preProcessedCustomCode
		# 	mod.errors.append( 'Unable to find this include file: ' + preProcessedCustomCode )

		# else: # Wut? Not expected!
		# 	mod.assemblyError = True
		# 	#mod.state = 'unavailable'
		# 	mod.stateDesc = 'Assembly error'
		# 	mod.errors.append( 'Assembly error; preAssembleRawCode return code: ' + returnCode )
		
		# return returnCode, '', '', ''

	def getAddressAndSourceFile( self, codeChangeDict, mod ):

		""" Gets and returns the address and source file for a given code change dictionary. 
			Also records any errors encountered if a value wasn't found. """

		address = codeChangeDict.get( 'address', '' )
		sourceFile = codeChangeDict.get( 'sourceFile', '' ) # Relative path

		if address and sourceFile:
			return address, sourceFile

		# If still here, there was a problem (both values are expected)
		mod.parsingError = True
		#mod.state = 'unavailable'
		mod.stateDesc = 'Parsing error; insufficient code change info'

		# Record an error message for this
		if address and not sourceFile:
			mod.errors.append( 'Injection at {} missing "sourceFile"'.format(address) )
		if not address and sourceFile:
			mod.errors.append( '{} injection missing its "address" field'.format(sourceFile) )
		elif not address and not sourceFile:
			# Combine like messages
			for i, errMsg in enumerate( mod.errors ):
				if errMsg.endswith( 'missing "address"/"sourceFile" fields' ):
					del mod.errors[i]
					# Parse and increase the number
					num = int( errMsg.split()[0] )
					mod.errors.append( '{} injections are missing "address"/"sourceFile" fields'.format(num + 1) )
					break
			else: # Above loop didn't break; no prior message like this
				mod.errors.append( '1 injection is missing "address"/"sourceFile" fields' )

		return '', ''

	def parseAmfsInject( self, codeChangeDict, mod, sourceFile='' ):

		""" AMFS Injection; custom code sourced from an assembly file. """

		if not sourceFile:
			address, sourceFile = self.getAddressAndSourceFile( codeChangeDict, mod )
			fullAsmFilePath = os.path.join( mod.path, sourceFile )
			annotation = codeChangeDict.get( 'annotation', '' )
		else: # No codeChangeDict if a source file was provided (this is an inject folder being processed)
			address = ''
			fullAsmFilePath = sourceFile # This will be a full path in this case
			annotation = ''

		# Get the custom code from the ASM file and pre-process it (make sure there's no whitespace, and/or assemble it)
		#returnCode, address, customCode, preProcessedCustomCode = self.getCustomCodeFromFile( fullAsmFilePath, mod, True, annotation )

		returnCode, address, customCode = self.getCustomCodeFromFile( fullAsmFilePath, mod, True, annotation )

		# Check for errors
		if returnCode != 0:
			return # Errors have already been recorded and reported
		elif not address:
			mod.parsingError = True
			mod.stateDesc = 'Missing address for "{}"'.format( sourceFile )
			mod.errors.append( 'Unable to find an address for ' + sourceFile )
			return

		# Normalize the offset of the code change, and get the game's original code at that location
		# dolOffset = normalizeDolOffset( address, dolObj=mod.vanillaDol )
		# origHex = getVanillaHex( dolOffset, revision=mod.revision, suppressWarnings=False )
		# if not origHex:
		# 	mod.missingVanillaHex = True
		# 	mod.errors.append( 'Unable to find vanilla hex for {}. Found in {}.'.format(address, sourceFile) )
		# 	return

		# Get the custom code's length, and store the info for this code change
		# customCodeLength = getCustomCodeLength( preProcessedCustomCode )
		# if customCodeLength == 4:
		# 	#mod.data[mod.revision].append( ('static', customCodeLength, address, origHex, customCode, preProcessedCustomCode) )
		# 	codeChange = CodeChange( mod, 'static', address, '', customCode, preProcessedCustomCode, returnCode )
		# else:
		# 	#mod.data[mod.revision].append( ('injection', customCodeLength, address, origHex, customCode, preProcessedCustomCode) )
		# 	codeChange = CodeChange( mod, 'injection', address, '', customCode, preProcessedCustomCode, returnCode )

		codeChange = CodeChange( mod, 'static', address, '', customCode, '' )
		codeChange.evaluate()

		if codeChange.length > 4:
			codeChange.type = 'injection'
			if mod.type == 'static':
				mod.type = 'injection'

		#codeChange.length = customCodeLength
		mod.data[mod.currentRevision].append( codeChange )

	def parseAmfsReplaceCodeBlock( self, codeChangeDict, mod ):

		""" AMFS Long Static Overwrite of variable length. """

		# Pre-process the custom code (make sure there's no whitespace, and/or assemble it)
		# sourceFile = codeChangeDict.get( 'sourceFile', '' ) # Expected to be there. Relative path
		# if not sourceFile:
		# 	mod.parsingError = True
		# 	mod.stateDesc = 'Parsing error; missing source file'
		# 	mod.errors.append( 'Injection at {} missing "sourceFile"'.format(address) )
		# 	return
		address, sourceFile = self.getAddressAndSourceFile( codeChangeDict, mod )
		fullAsmFilePath = '\\\\?\\' + os.path.normpath( os.path.join(mod.path, sourceFile) )
		annotation = codeChangeDict.get( 'annotation', '' ) # Optional; may not be there
		
		# Get the custom code from the ASM file and pre-process it (make sure there's no whitespace, and/or assemble it)
		returnCode, _, customCode = self.getCustomCodeFromFile( fullAsmFilePath, mod, False, annotation )
		if returnCode != 0: return

		# Get the offset of the code change, and the original code at that location
		#offset = codeChangeDict.get( 'address', '' )
		# dolOffset = normalizeDolOffset( offset, dolObj=mod.vanillaDol )
		# origHex = getVanillaHex( dolOffset, revision=mod.revision, suppressWarnings=False )
		# if not origHex:
		# 	mod.missingVanillaHex = True
		# 	mod.errors.append( 'Unable to find vanilla hex for ' + offset )
		# 	return
		
		# Get the custom code's length, and store the info for this code change
		# customCodeLength = getCustomCodeLength( preProcessedCustomCode )
		# mod.data[mod.revision].append( ('static', customCodeLength, offset, origHex, customCode, preProcessedCustomCode) )
		
		#mod.addStaticOverwrite( address, codeChangeDict['value'].splitlines() )
		codeChange = CodeChange( mod, 'static', address, '', customCode, '' )
		mod.data[mod.currentRevision].append( codeChange )

	def processAmfsInjectSubfolder( self, fullFolderPath, mod, isRecursive ):

		""" Processes all files/folders in a directory """

		try:
			for item in os.listdir( fullFolderPath ):
				itemPath = os.path.join( fullFolderPath, item )

				if os.path.isdir( itemPath ) and isRecursive:
					self.processAmfsInjectSubfolder( itemPath, mod, isRecursive )
				elif itemPath.endswith( '.asm' ):
					self.parseAmfsInject( None, mod, sourceFile=itemPath )
			
		except WindowsError as err:
			mod.parsingError = True
			mod.errors.append( 'Unable to find the folder "{}"'.format(fullFolderPath) )
			print err

	def parseAmfsInjectFolder( self, codeChangeDict, mod ):
		# Get/construct the root folder path
		sourceFolder = codeChangeDict['sourceFolder']
		sourceFolderPath = os.path.join( mod.path, sourceFolder )

		# try:
		self.processAmfsInjectSubfolder( sourceFolderPath, mod, codeChangeDict['isRecursive'] )
		# except WindowsError as err:
		#	# Try again with extended path formatting
		# 	print 'second try for', sourceFolderPath
		# 	self.processAmfsInjectSubfolder( '\\\\?\\' + os.path.normpath(sourceFolderPath), mod, codeChangeDict['isRecursive'] )

		
class CommandProcessor( object ):

	""" Assembler/disassembler to translate between assembly and bytecode (hex/binary machine code). 
		Uses the PowerPC Embedded Application Binary Interface (EABI) binary utilities. """

	def __init__( self ):
		executablesFolder = globalData.paths['eabi']

		# Construct paths to the binaries and for temporary files
		self.assemblerPath = os.path.join( executablesFolder, 'powerpc-eabi-as.exe' )
		self.linkerPath = os.path.join( executablesFolder, 'powerpc-eabi-ld.exe' )
		self.objcopyPath = os.path.join( executablesFolder, 'powerpc-eabi-objcopy.exe' )
		self.disassemblerPath = os.path.join( executablesFolder, 'vdappc.exe' )

		self.tempBinFile = os.path.join( globalData.paths['tempFolder'], 'code.bin' )

		# Validate the EABI file paths
		for path in ( self.assemblerPath, self.linkerPath, self.objcopyPath, self.disassemblerPath ):
			if not os.path.exists( path ):
				print 'Missing PowerPC-EABI binaries!'
				break

	@staticmethod
	def beautifyHex( rawHex ):

		""" Rewrites a hex string to something more human-readable, 
			displaying 8 bytes per line (2 blocks of 4 bytes, separated by a space). """

		code = []

		for block in xrange( 0, len(rawHex), 8 ):

			# Check whether this is the first or second block (set of 4 bytes or 8 nibbles)
			if block % 16 == 0: # Checks if evenly divisible by 16, meaning first block
				code.append( rawHex[block:block+8] + ' ' )
			else:
				code.append( rawHex[block:block+8] + '\n' )
		
		return ''.join( code ).rstrip()

	def buildAssemblyArgs( self, includePaths, suppressWarnings ):

		""" Constructs command line arguments for the assembler (EABI-AS). """

		args = [
				self.assemblerPath, 				# Path to the assembler binary
				"-mgekko", 							# Generate code for PowerPC Gekko (alternative to '-a32', '-mbig')
				"-mregnames", 						# Allows symbolic names for registers
				'-al', 								# Options for outputting assembled hex and other info to stdout
				'--listing-cont-lines', '100000',	# Sets the maximum number of continuation lines allowable in stdout (basically want this unlimited)
				#'--statistics',					# Prints additional assembly stats within the errors message; todo: will require some extra post processing
			]

		if suppressWarnings:
			args.append( '--no-warn' )

		# Set include directories, if requested
		if includePaths:
			for path in includePaths:
				args.extend( ('-I', path) ) # Need a -I for each path to add

		# Set object file output to 'nul', to prevent creation of the usual "a.out" elf object file
		args.extend( ('-o', 'nul') )

		return args

	def assemble( self, asmCode, beautify=False, includePaths=None, suppressWarnings=False, parseOutput=True ):
		
		""" IPC interface to EABI-AS. Assembles the given code, returns the result, 
			and cleans up any errors messages that may be present. """

		# Pass the assembly code to the assembler using stdin. Creation flags prevent generation of a GUI window
		args = self.buildAssemblyArgs( includePaths, suppressWarnings )
		assemblyProcess = Popen( args, stdin=PIPE, stdout=PIPE, stderr=PIPE, creationflags=0x08000000 )
		output, errors = assemblyProcess.communicate( input=asmCode + '\n' ) # Extra ending linebreak prevents a warning from assembler

		if errors:
			# Post-process the error message by removing the first line (which just says 'Assembler messages:') and redundant input form notices
			errorLines = []
			for line in errors.splitlines()[1:]:
				if line.startswith( '{standard input}:' ):
					errorLines.append( line.split( '}:', 1 )[1] )
					continue
				
				# Condense the file path and rebuild the rest of the string as it was
				lineParts = line.split( ': ', 2 ) # Splits on first 2 occurrances only
				fileName, lineNumber = lineParts[0].rsplit( ':', 1 )
				errorLines.append( '{}:{}: {}'.format(os.path.basename(fileName), lineNumber, ': '.join(lineParts[1:])) )

			errors = '\n'.join( errorLines )
			
			if suppressWarnings:
				return ( '', errors )
			else:
				cmsg( errors, 'Assembler Warnings' )

		if parseOutput:
			return self.parseAssemblerOutput( output, beautify=beautify )
		else:
			return ( output, errors )

	def disassemble( self, hexCode, whitespaceNeedsRemoving=False ):

		if whitespaceNeedsRemoving:
			hexCode = ''.join( hexCode.split() )

		# Create a temp file to send to the vdappc executable (doesn't appear to accept stdin)
		try:
			with open( self.tempBinFile, 'wb' ) as binFile:
				binFile.write( bytearray.fromhex(hexCode) )

		except IOError as e: # Couldn't create the file
			msg( 'Unable to create "' + self.tempBinFile + '" temp file for decompiling!', 'Error' )
			return ( '', e )

		except ValueError as e: # Couldn't convert the hex to a bytearray
			return ( '', e )

		# Give the temp file to vdappc and get its output
		process = Popen( [self.disassemblerPath, self.tempBinFile, "0"], stdout=PIPE, stderr=PIPE, creationflags=0x08000000 )
		output, errors = process.communicate() # creationFlags suppresses cmd GUI rendering

		if errors:
			print 'Errors detected during disassembly:'
			print errors
			return ( '', errors )
		
		return self.parseDisassemblerOutput( output )

	def parseAssemblerOutput( self, cmdOutput, beautify=False ):
		#tic = time.time()
		errors = ''
		code = []
		for line in cmdOutput.splitlines()[1:]: # Excludes first header line ('GAS Listing   [filename] [page _]')
			if not line: continue # Ignores empty lines
			elif 'GAS LISTING' in line and 'page' in line: continue # Ignores page headers
			elif line.startswith( '****' ): continue # Ignores warning lines

			lineMinusAsm = line.split( '\t' )[0] # ASM commands are separated by a tab. 
			lineParts = lineMinusAsm.split() # Will usually be [ lineNumber, codeOffset, hexCode ]
			linePartsCount = len( lineParts )

			if not lineParts[0].isdigit(): # Assuming there must be at least one lineParts item at this point, considering 'if not line: continue'
				print 'Error parsing assembler output on this line:'
				print line, '\n'
				code = []
				errors = 'Problem detected while parsing assembly process output:\n' + cmdOutput
				break
			elif linePartsCount == 1: continue # This must be just a label
			else:
				hexCode = lineParts[-1]

			if not beautify:
				code.append( hexCode )

			else: # Add line breaks and spaces for readability
				if code:
					lastBlockLength = len( code[-1] )
					while lastBlockLength != 9 and hexCode != '': # Last part isn't a full 4 bytes; add to that
						code[-1] += hexCode[:9 - lastBlockLength]
						hexCode = hexCode[9 - lastBlockLength:] # Add the remaining to the next block (unless the last still isn't filled)
						lastBlockLength = len( code[-1] )

				if hexCode:
					if len( code ) % 2 == 0: # An even number of blocks have been added (0 is even)
						code.append( '\n' + hexCode )
					else: code.append( ' ' + hexCode )

		# ( ''.join( code ).lstrip(), errors )
		# toc = time.time()
		# print 'asm output parsing time:', toc - tic

		return ( ''.join(code).lstrip(), errors ) # Removes first line break if present

	def parseBranchHex( self, hexCode ):

		""" Gets the branch operand (branch distance), and normalizes it. Avoids weird results from EABI.
			Essentially, this does two things: strip out the link and absolute flag bits,
			and normalize the output value, e.g. -0x40 instead of 0xffffffc0. """

		# Mask out bits 26-32 (opcode), bit 25 (sign bit) and bits 1 & 2 (branch link and absolute value flags)
		intValue = int( hexCode, 16 )
		branchDistance = intValue & 0b11111111111111111111111100

		# Check the sign bit 0x2000000, i.e. 0x10000000000000000000000000
		if intValue & 0x2000000:
			# Sign bit is set; this is a negative number.
			return hex( -( 0x4000000 - branchDistance ) )
		else:
			return hex( branchDistance )

	def parseDisassemblerOutput( self, cmdOutput ):
		code = []
		errors = ''

		for line in cmdOutput.splitlines():
			if not line:
				print 'Found empty line during disassembly. problem?'
				continue # Ignores empty lines

			lineParts = line.split() # Expected to be [ codeOffset, hexCode, instruction, *[operands] ]

			if len( lineParts ) < 3:
				errors = 'Problem detected while parsing disassembly process output:\n' + cmdOutput
				break

			codeOffset, hexCode, instruction = lineParts[:3]
			operands = lineParts[3:]

			if not validHex( codeOffset.replace(':', '') ): # Error
				errors = 'Problem detected while parsing disassembly process output:\n' + cmdOutput
				break

			elif operands and '0x' in operands[0]: # Apply some fixes
				if instruction == '.word' and len( hexCode ) > 4: # Convert to .long if this is more than 4 characters (2 bytes)
					lineParts[2] = '.long'
				elif instruction in ( 'b', 'bl', 'ba', 'bla' ):
					lineParts[3] = self.parseBranchHex( hexCode )

			code.append( ' '.join(lineParts[2:]) ) # Grabs everything from index 2 onward (all assembly command parts)

		if errors:
			code = []
			print errors

		return ( '\n'.join(code), errors )

	# def checkCodeLength( self, customCode, includePaths=None, suppressWarnings=False ):

	# # 	newLines = []

	# # 	# Filter out special syntaxes and remove comments
	# # 	for rawLine in customCode.splitlines():
	# # 		# Start off by filtering out comments
	# # 		codeLine = rawLine.split( '#' )[0].strip()

	# # 		#if 

		
	# # 	args = self.buildAssemblyArgs( includePaths, suppressWarnings )
	# # 	assemblyProcess = Popen( args, stdin=PIPE, stdout=PIPE, stderr=PIPE, creationflags=0x08000000 )
	# # 	output, errors = assemblyProcess.communicate( input=customCode + '\n' ) # Extra ending linebreak prevents a warning from assembler

	# #def preAssembleRawCode( self, codeLinesList, includePaths=None, discardWhitespace=True, suppressWarnings=False ):

	# 	""" This method takes assembly or hex code, filters out custom MCM syntaxes and comments, and assembles the code 
	# 		using the PowerPC EABI if it was assembly. Once that is done, the custom syntaxes are added back into the code, 
	# 		which will be replaced (compiled to hex) later. If the option to include whitespace is enabled, then the resulting 
	# 		code will be formatted with spaces after every 4 bytes and line breaks after every 8 bytes (like a Gecko code). 
	# 		The 'includePaths' option specifies a list of [full/absolute] directory paths for .include imports. 

	# 		Return codes from this method are:
	# 			0: Success
	# 			1: Compilation placeholder or branch marker detected in original code
	# 			2: Error during assembly
	# 			3: Include file(s) could not be found
	# 	"""

	# 	# Define placeholders for special syntaxes
	# 	# compilationPlaceholder = 'stfdu f21,-16642(r13)' # Equivalent of 'deadbefe' (doesn't actually matter what this is, but must be in ASM in case of conversion)
	# 	# branchMarker = 'DEADBEFE'

	# 	isAssembly = False
	# 	#allSpecialSyntaxes = True
	# 	filteredLines = []
	# 	#customSyntax = []
	# 	#isAssembly = True
	# 	length = 0

	# 	if type( codeLinesList ) != list:
	# 		codeLinesList = codeLinesList.splitlines()

	# 	# Filter out special syntaxes and remove comments
	# 	for rawLine in codeLinesList:
	# 		# Start off by filtering out comments
	# 		codeLine = rawLine.split( '#' )[0].strip()

	# 		# if compilationPlaceholder in codeLine or branchMarker in codeLine:
	# 		# 	# This should be a very rare problem, so I'm not going to bother with suppressing this
	# 		# 	msg( 'There was an error while assembling this code (compilation placeholder detected):\n\n' + '\n'.join(codeLinesList), 'Assembly Error 01' )
	# 		# 	return ( 1, '' )

	# 		if CodeLibraryParser.isSpecialBranchSyntax( codeLine ): # e.g. "bl 0x80001234" or "bl <testFunction>"
	# 			# Store the original command.
	# 			# if discardWhitespace: customSyntax.append( '|S|sbs__' + codeLine + '|S|' ) # Add parts for internal processing
	# 			# else: customSyntax.append( codeLine ) # Keep the finished string human-readable

	# 			# # Add a placeholder for compilation (important for other branch calculations). It will be replaced with the original command after the code is assembled to hex.
	# 			# filteredLines.append( compilationPlaceholder )

	# 			filteredLines.append( 'b 0' )
	# 			length += 4

	# 		#elif CodeLibraryParser.containsPointerSymbol( codeLine ): # Identifies symbols in the form of <<functionName>>
	# 			# Store the original command.
	# 			# if discardWhitespace: customSyntax.append( '|S|sym__' + codeLine + '|S|' ) # Add parts for internal processing
	# 			# else: customSyntax.append( codeLine ) # Keep the finished string human-readable

	# 			# # Add a placeholder for compilation (important for other branch calculations). It will be replaced with the original command after the code is assembled to hex.
	# 			# filteredLines.append( compilationPlaceholder )
				
	# 			# for name in CodeLibraryParser.containsPointerSymbol( section ):
	# 			# 	section.replace( '<<' + name + '>>', '0x80000000' )
	# 			# filteredLines.append( section )

	# 		elif '<<' in codeLine and '>>' in codeLine:
	# 			sectionChunks = codeLine.split( '<<' )
	# 			for block in sectionChunks[1:]: # Skips first block (will never be a symbol)
	# 				if '>>' in block:
	# 					for potentialName in block.split( '>>' )[:-1]: # Skips last block (will never be a symbol)
	# 						if potentialName != '' and ' ' not in potentialName: 
	# 							symbolNames.append( potentialName )

	# 			if sectionChunks[0] in ( 'b', 'bl', 'bla' ): # Ignore these as assembly, since they can be assembled internally
	# 				length += 4
	# 			else:
	# 				isAssembly = True

	# 		elif '[[' in codeLine and ']]' in codeLine: # Identifies customization option placeholders
	# 			# Store the original command.
	# 			# if discardWhitespace: customSyntax.append( '|S|opt__' + codeLine + '|S|' ) # Add parts for internal processing
	# 			# else: customSyntax.append( codeLine ) # Keep the finished string human-readable

	# 			# # Add a placeholder for compilation (important for other branch calculations). It will be replaced with the original command after the code is assembled to hex.
	# 			# filteredLines.append( compilationPlaceholder )
				
	# 			sectionChunks = section.split( '[[' )

	# 			for chunk in sectionChunks:
	# 				if ']]' in chunk:
	# 					varName, theRest = chunk.split( ']]' )[0] # Not expecting multiple ']]' sets in this chunk

	# 					codeLine.replace( '[[' + varName + ']]', '0' )

	# 					if validHex( theRest.replace(' ', '') ):
	# 						length += len( theRest.replace(' ', '') ) / 2
	# 					else:
	# 						isAssembly = True

	# 				elif validHex( codeLine.replace(' ', '') ):
	# 					length += len( codeLine.replace(' ', '') ) / 2
	# 				else:
	# 					isAssembly = True

	# 		else:
	# 			# Whether it's hex or not, re-add the line to filteredLines.
	# 			filteredLines.append( codeLine )
	# 			#allSpecialSyntaxes = False

	# 			# Check whether this line indicates that this code requires conversion.
	# 			if not isAssembly and codeLine != '' and not validHex( codeLine.replace(' ', '') ):
	# 				isAssembly = True
					
	# 			if codeLine == '': pass
	# 			elif not isAssembly and not validHex( codeLine.replace(' ', '') ):
	# 				isAssembly = True

	# 	# if allSpecialSyntaxes: # No real processing needed; it will be done when resolving these syntaxes
	# 	# 	if discardWhitespace:
	# 	# 		return ( 0, ''.join(customSyntax) )
	# 	# 	else:
	# 	# 		return ( 0, '\n'.join(customSyntax) )

	# 	if isAssembly:
	# 		filteredCode = '\n'.join( filteredLines ) # Joins the filtered lines with linebreaks.
	# 		conversionOutput, errors = self.assemble( filteredCode, beautify=False, includePaths=includePaths, suppressWarnings=suppressWarnings )
			
	# 		if errors:
	# 			# If suppressWarnings is True, there shouldn't be warnings in the error text; but there may still be actual errors reported
	# 			if not suppressWarnings:
	# 				cmsg( errors, 'Assembly Error 02' )
	# 			return -1

	# 		return len( conversionOutput.strip() ) / 2
	# 	else:
	# 		return length

	def getOptionWidth( self, optionType ):

		if optionType.endswith( '32' ) or optionType == 'float':
			return 4
		elif optionType.endswith( '16' ):
			return 2
		elif optionType.endswith( '8' ):
			return 1
		else:
			return -1

	def evaluateCustomCode( self, codeLinesList, includePaths=None, customizations=None ):

		# Convert the input into a list of lines
		codeLinesList = codeLinesList.splitlines()

		if self.codeIsAssembly( codeLinesList ):
			return self._evaluateAssembly( codeLinesList, includePaths, customizations )
		else:
			return self._evaluateHexcode( codeLinesList, includePaths, customizations )

	def _evaluateAssembly( self, codeLinesList, includePaths, customizations ):
		
		""" This method takes assembly or hex code, parses out custom MCM syntaxes and comments, and assembles the code 
			using the PowerPC EABI if it was assembly. Once that is done, the custom syntaxes are added back into the code, 
			which will be replaced (compiled to hex) later. If the option to include whitespace is enabled, then the resulting 
			code will be formatted with spaces after every 4 bytes and line breaks after every 8 bytes (like a Gecko code). 
			The 'includePaths' option specifies a list of [full/absolute] directory paths for .include imports. 

			Return codes from this method are:
				0: Success
				1: Error during assembly
				2: Include file(s) could not be found
				3: Customization option not found
				4: Customization option missing type parameter
				5: Unrecognized customization option type
		"""

		#assemblyRequired = False
		customSyntaxRanges = []

		# In case assembly is required
		linesForAssembler = [ 'start:' ]

		# In case assembly is NOT required
		# hexLines = []
		# length = 0

		# if type( codeLinesList ) != list:
		# 	codeLinesList = codeLinesList.splitlines()

		# print 'Raw code input:'
		# print codeLinesList

		# Filter out special syntaxes and remove comments
		labelIndex = 0
		for rawLine in codeLinesList:
			# Start off by filtering out comments, and skip empty lines
			codeLine = rawLine.split( '#' )[0].strip()
			if not codeLine: continue

			if codeLine == '.align 2': # Replace the align directive with an alternative, which can't be calculated alongside the .irp instruction
				linesForAssembler.extend( ['padding = (3 - (.-start-1) & 3)', '.if padding', '  .zero padding', '.endif'] )
				#assemblyRequired = True

			elif CodeLibraryParser.isSpecialBranchSyntax( codeLine ): # e.g. "bl 0x80001234" or "bl <testFunction>"
				customSyntaxRanges.append( [-1, 4, 'sbs__'+codeLine] )
				
				# In case assembly is NOT required
				# hexLines.append( 'sbs__'+codeLine )
				# length += 4
				
				# In case assembly is required
				linesForAssembler.append( 'OCL_{}:b 0'.format(labelIndex) ) # Collecting in case we need assembler
				labelIndex += 1
				
			elif '<<' in codeLine and '>>' in codeLine: # Identifies symbols in the form of <<functionName>>
				customSyntaxRanges.append( [-1, 4, 'sym__'+codeLine] )

				# Replace custom address symbols with a temporary value placeholder
				sectionChunks = codeLine.split( '<<' )
				printoutCodeLine = codeLine
				for block in sectionChunks[1:]: # Skips first block (will never be a symbol)
					if '>>' in block:
						for potentialName in block.split( '>>' )[:-1]: # Skips last block (will never be a symbol)
							if potentialName != '' and ' ' not in potentialName:
								printoutCodeLine = printoutCodeLine.replace( '<<' + potentialName + '>>', '0x80000000' )

				# Check if this line is just a branch
				# if assemblyRequired: pass
				# elif sectionChunks[0] in ( 'b', 'bl', 'bla' ): # Ignore these as assembly, since they can be assembled internally
				# 	# In case assembly is NOT required
				# 	hexLines.append( 'sym__'+codeLine )
				# 	length += 4
				# else: # Abandon calculating length ourselves; get it from assembler
				# 	assemblyRequired = True
				
				# In case assembly is required
				linesForAssembler.append( 'OCL_{}:{}'.format(labelIndex, printoutCodeLine) )
				labelIndex += 1

			elif '[[' in codeLine and ']]' in codeLine: # Identifies customization option placeholders
				#customSyntaxes.append( '|S|opt__' + codeLine + '|S|' )

				# Gather all placeholders (option names), and make sure they exist in one of the option dictionaries

				# Parse out all option names, and collect their information from the mod's customization dictionaries
				sectionChunks = codeLine.split( '[[' )
				#optionInfo = [] # Will be a list of tuples, of the form (optionName, optionType)
				#lineOffset = 0
				#syntaxRanges = []
				for i, chunk in enumerate( sectionChunks ):
					if ']]' in chunk:
						varName, theRest = chunk.split( ']]' ) # Not expecting multiple ']]' delimiters in this chunk

						# Attempt to get the customization name (and size if the code is already assembled)
						for option in customizations:
							optionName = option.get( 'name' )
							optionType = option.get( 'type' )
							if optionName == varName:
								if not optionType:
									return 4, -1, optionName, []
								optionWidth = self.getOptionWidth( optionType )
								if optionWidth == -1:
									return 5, -1, optionType, []
								break
						else: # The loop above didn't break; option not found
							return 3, -1, varName, []
						#optionInfo.append( (length, '[[' + varName + ']]', optionWidth) )
						sectionChunks[i] = chunk.replace( varName + ']]', '0' )

						# If the custom code following the option is entirely raw hex (or an empty string), get its length
						# if assemblyRequired: pass
						# elif all( char in hexdigits for char in theRest.replace(' ', '') ):
						# 	theRestLength = len( theRest.replace(' ', '') ) / 2
						# 	length += optionWidth + theRestLength
						# 	#lineOffset += optionWidth + theRestLength
						# 	customSyntaxRanges.append( [length, optionWidth, 'opt__'+codeLine] )
						# else:
						# 	assemblyRequired = True

						#customSyntaxRanges.append( [length, optionWidth, 'opt__'+codeLine] )

					# If other custom code in this line is raw hex, get its length
					# elif assemblyRequired: pass
					# elif all( char in hexdigits for char in chunk.replace(' ', '') ):
					# 	chunkLength = len( chunk.replace(' ', '') ) / 2
					# 	length += chunkLength
					# 	#lineOffset += chunkLength
					# else: # Abandon calculating length ourselves; get it from assembler
					# 	assemblyRequired = True

				# Replace collected option names for placeholder values
				#newCodeLine = codeLine
				#if assemblyRequired:
					# newCodeLine = codeLine
					# for ( _, optionName, _ ) in optionInfo:
					# 	newCodeLine = newCodeLine.replace( optionName, '0' )
				customSyntaxRanges.append( [-1, optionWidth, 'opt__'+codeLine] )

				#else: # Apart from the option placeholder, the line is raw hex; need to look up types for value sizes
				# 	for ( length, optionName, optionWidth ) in optionInfo:
				# 		#newCodeLine = codeLine.replace( optionName, '00' * optionWidth )
				# 		customSyntaxRanges.append( [length, optionWidth, 'opt__'+codeLine] )
					#hexLines.append( 'opt__'+codeLine )

				# Create a line in case assembler is needed
				# newCodeLine = codeLine
				# for ( _, optionName, _ ) in optionInfo:
				# 	newCodeLine = newCodeLine.replace( optionName, '0' )
				newCodeLine = ''.join( sectionChunks )

				linesForAssembler.append( 'OCL_{}:{}'.format(labelIndex, newCodeLine) ) # Collecting in case we need assembler
				labelIndex += 1

			else:
				# Check whether this line indicates that this code requires conversion.
				# if assemblyRequired: pass
				# elif all( char in hexdigits for char in codeLine.replace(' ', '') ): # Is in hex form
				# 	hexLines.append( codeLine )
				# 	hexCodeLen = len( codeLine.replace(' ', '') ) / 2
				# 	length += hexCodeLen
				# 	#linesForAssembler.append( '.zero ' + str(hexCodeLen) )
				# else:
				# 	assemblyRequired = True

				# Whether it's hex or not, re-add the current line to hexLines.
				linesForAssembler.append( codeLine )

		# Run the code through the assembler if needed
		#if assemblyRequired and customizationsEnabled:
		#if assemblyRequired:
		# Add assembly to handle the label calculations
		if customSyntaxRanges: # Found custom syntax; add code to pinpoint their offsets
			linesForAssembler.append( '.altmacro' )
			labelOffsets = [ '%OCL_{}-start'.format(i) for i in range(labelIndex) ]
			linesForAssembler.append( '.irp loc, ' + ', '.join(labelOffsets) )
			linesForAssembler.append( '  .print "offset:\\loc"' )
			linesForAssembler.append( '.endr' )

		# Assemble the collected lines, without assembler output parsing in this case (it will be handled in a custom manner below)
		codeForAssembler = '\n'.join( linesForAssembler ) # Joins the filtered lines with line breaks
		conversionOutput, errors = self.assemble( codeForAssembler, False, includePaths, True, False )
		
		if errors:
			# If suppressWarnings is True (above), there shouldn't be warnings in the error text; but there may still be actual errors reported
			cmsg( errors, 'Assembly Error 02' )
			return 1, -1, errors, []

		# If custom syntax was present, parse out their offsets, and/or parse the assembler output in the usual manner
		if customSyntaxRanges: # If custom syntax was found...
			#print 'syntax ranges pre-parse:', customSyntaxRanges
			standardFirstLine = 0
			conversionOutputLines = conversionOutput.splitlines()
			for i, line in enumerate( conversionOutputLines ):
				if line.startswith( 'offset:' ):
					#customSyntaxRanges.append( int(line.split(':')[1]) )
					customSyntaxRanges[i][0] = int(line.split(':')[1])
				elif line.startswith( 'GAS LISTING' ):
					break
				standardFirstLine += 1
			#print 'syntax ranges post-parse:', customSyntaxRanges

			parsedOutput, errors = self.parseAssemblerOutput( '\n'.join(conversionOutputLines[standardFirstLine:]) )
			length = len( parsedOutput ) / 2

		else: # No special syntax, no extra parsing needed
			preProcessedCode, errors = self.parseAssemblerOutput( conversionOutput )
			length = len( preProcessedCode ) / 2

		if errors:
			return 1, -1, errors, []

		# Create the preProcessed string, which is assembled hex code, with the custom syntaxes stripped out and replaced with the original code lines
		elif customSyntaxRanges:
			preProcessedCode = []
			position = 0 # Byte positional offset in the parsed output
			for offset, width, originalLine in customSyntaxRanges:
				#previousHex = parsedOutput[position*2:(position+offset)*2] # Mult. by 2 to count by nibbles
				previousHex = parsedOutput[position*2:offset*2]
				if previousHex: # May be empty (at start, and if custom syntax is back to back)
					preProcessedCode.append( previousHex )
					position += len( previousHex ) / 2
				preProcessedCode.append( originalLine )
				position += width
			if position != length: # Add final section
				preProcessedCode.append( parsedOutput[position*2:] ) # Mult. by 2 to count by nibbles
			
			# print 'Pre-processed code:'
			# print preProcessedCode

			preProcessedCode = '|S|'.join( preProcessedCode )

		# else: # The original custom code is already in hex form
		# 	preProcessedCode = '|S|'.join( hexLines )
			
			# print 'Pre-processed code:'
			# print hexLines

		# elif assemblyRequired: # Assemble without extra customization option parsing
		# 	filteredCode = '\n'.join( hexLines ) # Joins the filtered lines with linebreaks.
		# 	parsedOutput, errors = self.assemble( filteredCode, False, includePaths, suppressWarnings, True ) # Assembly output parsing enabled
			
		# 	if errors:
		# 		# If suppressWarnings is True, there shouldn't be warnings in the error text; but there may still be actual errors reported
		# 		if not suppressWarnings:
		# 			cmsg( errors, 'Assembly Error 02' )
		# 		return -1

		# 	return len( parsedOutput.strip() ) / 2

		# else: # No assembly required
		# 	return length

		return 0, length, preProcessedCode, customSyntaxRanges

	def _evaluateHexcode( self, codeLinesList, includePaths=None, customizations=None ):

		""" This method takes assembly or hex code, parses out custom MCM syntaxes and comments, and assembles the code 
			using the PowerPC EABI if it was assembly. Once that is done, the custom syntaxes are added back into the code, 
			which will be replaced (compiled to hex) later. If the option to include whitespace is enabled, then the resulting 
			code will be formatted with spaces after every 4 bytes and line breaks after every 8 bytes (like a Gecko code). 
			The 'includePaths' option specifies a list of [full/absolute] directory paths for .include imports. 

			Return codes from this method are:
				0: Success
				1: Error during assembly
				2: Include file(s) could not be found
				3: Customization option not found
				4: Customization option missing type parameter
				5: Unrecognized customization option type
		"""

		#assemblyRequired = False
		customSyntaxRanges = []

		# In case assembly is required
		#linesForAssembler = [ 'start:' ]
		linesRequiringAssembly = []

		# In case assembly is NOT required
		preProcessedLines = []
		length = 0

		# print 'Raw code input:'
		# print codeLinesList

		# Filter out special syntaxes and remove comments
		#labelIndex = 0
		for rawLine in codeLinesList:
			# Start off by filtering out comments, and skip empty lines
			codeLine = rawLine.split( '#' )[0].strip()
			if not codeLine: continue

			# if codeLine == '.align 2': # Replace the align directive with an alternative, which can't be calculated alongside the .irp instruction
			# 	linesForAssembler.extend( ['padding = (3 - (.-start-1) & 3)', '.if padding', '  .zero padding', '.endif'] )
			# 	assemblyRequired = True

			if CodeLibraryParser.isSpecialBranchSyntax( codeLine ): # e.g. "bl 0x80001234" or "bl <testFunction>"
				customSyntaxRanges.append( [length, 4, 'sbs__'+codeLine] )
				
				# In case assembly is NOT required
				preProcessedLines.append( 'sbs__'+codeLine )
				length += 4
				
				# In case assembly is required
				# linesForAssembler.append( 'OCL_{}:b 0'.format(labelIndex) ) # Collecting in case we need assembler
				# labelIndex += 1
				
			elif '<<' in codeLine and '>>' in codeLine: # Identifies symbols in the form of <<functionName>>
				customSyntaxRanges.append( [length, 4, 'sym__'+codeLine] )

				# Replace custom address symbols with a temporary value placeholder
				# sectionChunks = codeLine.split( '<<' )
				# printoutCodeLine = codeLine
				# for block in sectionChunks[1:]: # Skips first block (will never be a symbol)
				# 	if '>>' in block:
				# 		for potentialName in block.split( '>>' )[:-1]: # Skips last block (will never be a symbol)
				# 			if potentialName != '' and ' ' not in potentialName:
				# 				printoutCodeLine = printoutCodeLine.replace( '<<' + potentialName + '>>', '0x80000000' )

				# Check if this line is just a branch
				# if assemblyRequired: pass
				# if not sectionChunks[0] in ( 'b', 'bl', 'bla' ): # Ignore these as assembly, since they can be assembled internally
				# 	linesRequiringAssembly.append( codeLine )

				preProcessedLines.append( 'sym__'+codeLine )
				length += 4
				# else: # Abandon calculating length ourselves; get it from assembler
				# 	assemblyRequired = True
				
				# In case assembly is required
				# linesForAssembler.append( 'OCL_{}:{}'.format(labelIndex, printoutCodeLine) )
				# labelIndex += 1

			elif '[[' in codeLine and ']]' in codeLine: # Identifies customization option placeholders
				#customSyntaxes.append( '|S|opt__' + codeLine + '|S|' )
				thisLineOffset = length
				assemblyRequired = False
				newRanges = []

				# Gather all placeholders (option names), and make sure they exist in one of the option dictionaries

				# Parse out all option names, and collect their information from the mod's customization dictionaries
				sectionChunks = codeLine.split( '[[' )
				#optionInfo = [] # Will be a list of tuples, of the form (optionName, optionType)
				#lineOffset = 0
				#syntaxRanges = []
				for chunk in sectionChunks:
					if ']]' in chunk:
						varName, theRest = chunk.split( ']]' ) # Not expecting multiple ']]' delimiters in this chunk

						# Attempt to get the customization name (and size if the code is already assembled)
						for option in customizations:
							optionName = option.get( 'name' )
							optionType = option.get( 'type' )
							if optionName == varName:
								if not optionType:
									return 4, -1, optionName, []
								optionWidth = self.getOptionWidth( optionType )
								if optionWidth == -1:
									return 5, -1, optionType, []
								break
						else: # The loop above didn't break; option not found
							return 3, -1, varName, []
						#optionInfo.append( (length, '[[' + varName + ']]', optionWidth) )
						#customSyntaxRanges.append( [length, optionWidth, 'opt__'+codeLine] )
						newRanges.append( [length, optionWidth, 'opt__'+codeLine] )

						# If the custom code following the option is entirely raw hex (or an empty string), get its length
						if assemblyRequired: pass
						elif all( char in hexdigits for char in theRest.replace(' ', '') ):
							#customSyntaxRanges.append( [length, optionWidth, 'opt__'+codeLine] )
							theRestLength = len( theRest.replace(' ', '') ) / 2
							length += optionWidth + theRestLength
							#lineOffset += optionWidth + theRestLength
						else:
							assemblyRequired = True

						#customSyntaxRanges.append( [length, optionWidth, 'opt__'+codeLine] )

					# If other custom code in this line is raw hex, get its length
					elif assemblyRequired: pass
					elif all( char in hexdigits for char in chunk.replace(' ', '') ):
						chunkLength = len( chunk.replace(' ', '') ) / 2
						length += chunkLength
						#lineOffset += chunkLength
					else: # Abandon calculating length ourselves; get it from assembler
						assemblyRequired = True

				# Replace collected option names for placeholder values
				#newCodeLine = codeLine
				if assemblyRequired:
					# newCodeLine = codeLine
					# for ( _, optionName, _ ) in optionInfo:
					# 	newCodeLine = newCodeLine.replace( optionName, '0' )

					#linesRequiringAssembly.append( codeLine )

					# Reset offsets in newRanges (to the start of this line), and add them to the full list
					newRanges = [ [thisLineOffset, w, l] for _, w, l in newRanges ]
					# customSyntaxRanges.extend( newRanges )

				# else: # Apart from the option placeholder, the line is raw hex; need to look up types for value sizes
				# # 	for ( length, optionName, optionWidth ) in optionInfo:
				# # 		#newCodeLine = codeLine.replace( optionName, '00' * optionWidth )
				# # 		customSyntaxRanges.append( [length, optionWidth, 'opt__'+codeLine] )
				# 	hexLines.append( 'opt__'+codeLine )

				preProcessedLines.append( 'opt__'+codeLine )
				customSyntaxRanges.extend( newRanges )

				# Create a line in case assembler is needed
				# newCodeLine = codeLine
				# for ( _, optionName, _ ) in optionInfo:
				# 	newCodeLine = newCodeLine.replace( optionName, '0' )

				# linesForAssembler.append( 'OCL_{}:{}'.format(labelIndex, newCodeLine) ) # Collecting in case we need assembler
				# labelIndex += 1

			else:
				# Check whether this line indicates that this code requires conversion.
				# if assemblyRequired: pass
				# elif all( char in hexdigits for char in codeLine.replace(' ', '') ): # Is in hex form
				# 	hexLines.append( codeLine )
				pureHex = ''.join( codeLine.split() ) # Removes whitespace
				hexCodeLen = len( pureHex ) / 2
				length += hexCodeLen
					#linesForAssembler.append( '.zero ' + str(hexCodeLen) )
				# else:
				# 	assemblyRequired = True

				# # Whether it's hex or not, re-add the current line to hexLines.
				# linesForAssembler.append( codeLine )
				preProcessedLines.append( pureHex )

		# Run the code through the assembler if needed
		#if assemblyRequired and customizationsEnabled:
		# if assemblyRequired:
		# 	# Add assembly to handle the label calculations
		# 	linesForAssembler.append( '.altmacro' )
		# 	labelOffsets = [ '%OCL_{}-start'.format(i) for i in range(labelIndex) ]
		# 	linesForAssembler.append( '.irp loc, ' + ', '.join(labelOffsets) )
		# 	linesForAssembler.append( '  .print "offset:\\loc"' )
		# 	linesForAssembler.append( '.endr' )

		# 	codeForAssembler = '\n'.join( linesForAssembler ) # Joins the filtered lines with line breaks
		# 	conversionOutput, errors = self.assemble( codeForAssembler, False, includePaths, True, False ) # No assembly output parsing
			
		# 	if errors:
		# 		# If suppressWarnings is True, there shouldn't be warnings in the error text; but there may still be actual errors reported
		# 		#if not suppressWarnings:
		# 		cmsg( errors, 'Assembly Error 02' )
		# 		return 1, -1, errors, []

		# 	# Parse the assembly output for customization offsets
		# 	#customSyntaxRanges = []
		# 	conversionOutputLines = conversionOutput.splitlines()
		# 	standardFirstLine = 0
		# 	for i, line in enumerate( conversionOutputLines ):
		# 		if line.startswith( 'offset:' ):
		# 			#customSyntaxRanges.append( int(line.split(':')[1]) )
		# 			customSyntaxRanges[i][0] = int(line.split(':')[1])
		# 		elif line.startswith( 'GAS LISTING' ):
		# 			break
		# 		standardFirstLine += 1

		# 	# line = 0
		# 	# for syntaxRange in customSyntaxRanges:
		# 	# 	originalLine = syntaxRange[-1]
			
		# 	parsedOutput, errors = self.parseAssemblerOutput( '\n'.join(conversionOutputLines[standardFirstLine:]) )
		# 	length = len( parsedOutput.strip() ) / 2

		# 	if errors:
		# 		return 1, -1, errors, []

		# 	# Create the preProcessed string, which is assembled hex code, with the custom syntaxes stripped out and replaced with the original code lines
		# 	preProcessedCode = []
		# 	position = 0 # Byte positional offset in the parsed output
		# 	for offset, width, originalLine in customSyntaxRanges:
		# 		#previousHex = parsedOutput[position*2:(position+offset)*2] # Mult. by 2 to count by nibbles
		# 		previousHex = parsedOutput[position*2:offset*2]
		# 		if previousHex: # May be empty (at start, and if custom syntax is back to back)
		# 			preProcessedCode.append( previousHex )
		# 			position += len( previousHex ) / 2
		# 		preProcessedCode.append( originalLine )
		# 		position += width
		# 	if position != length: # Add final section
		# 		preProcessedCode.append( parsedOutput[position*2:] ) # Mult. by 2 to count by nibbles
			
		# 	# print 'Pre-processed code:'
		# 	# print preProcessedCode

		# 	preProcessedCode = '|S|'.join( preProcessedCode )

		# else: # The original custom code is already in hex form
		if customSyntaxRanges: # Found custom syntax; add delimiters for future processing
			#print 'syntax ranges (from raw hex eval):', customSyntaxRanges
			preProcessedCode = '|S|'.join( preProcessedLines )
		else:
			preProcessedCode = ''.join( preProcessedLines )
			
			# print 'Pre-processed code:'
			# print hexLines

		# elif assemblyRequired: # Assemble without extra customization option parsing
		# 	filteredCode = '\n'.join( hexLines ) # Joins the filtered lines with linebreaks.
		# 	parsedOutput, errors = self.assemble( filteredCode, False, includePaths, suppressWarnings, True ) # Assembly output parsing enabled
			
		# 	if errors:
		# 		# If suppressWarnings is True, there shouldn't be warnings in the error text; but there may still be actual errors reported
		# 		if not suppressWarnings:
		# 			cmsg( errors, 'Assembly Error 02' )
		# 		return -1

		# 	return len( parsedOutput.strip() ) / 2

		# else: # No assembly required
		# 	return length

		return 0, length, preProcessedCode, customSyntaxRanges
	
	def evaluateCustomCode2( self, codeLinesList, includePaths=None, customizations=None ):

		""" This method takes assembly or hex code, parses out custom MCM syntaxes and comments, and assembles the code 
			using the PowerPC EABI if it was assembly. Once that is done, the custom syntaxes are added back into the code, 
			which will be replaced (compiled to hex) later. If the option to include whitespace is enabled, then the resulting 
			code will be formatted with spaces after every 4 bytes and line breaks after every 8 bytes (like a Gecko code). 
			The 'includePaths' option specifies a list of [full/absolute] directory paths for .include imports. 

			Return codes from this method are:
				0: Success
				1: Error during assembly
				2: Include file(s) could not be found
				3: Customization option not found
				4: Customization option missing type parameter
				5: Unrecognized customization option type
		"""

		assemblyRequired = False
		customSyntaxRanges = []

		# In case assembly is required
		linesForAssembler = [ 'start:' ]

		# In case assembly is NOT required
		hexLines = []
		length = 0

		if type( codeLinesList ) != list:
			codeLinesList = codeLinesList.splitlines()

		# print 'Raw code input:'
		# print codeLinesList

		# Filter out special syntaxes and remove comments
		labelIndex = 0
		for rawLine in codeLinesList:
			# Start off by filtering out comments, and skip empty lines
			codeLine = rawLine.split( '#' )[0].strip()
			if not codeLine: continue

			if codeLine == '.align 2': # Replace the align directive with an alternative, since .align can't be calculated alongside the .irp instruction
				linesForAssembler.extend( ['padding = (3 - (.-start-1) & 3)', '.if padding', '  .zero padding', '.endif'] )
				assemblyRequired = True

			elif CodeLibraryParser.isSpecialBranchSyntax( codeLine ): # e.g. "bl 0x80001234" or "bl <testFunction>"
				customSyntaxRanges.append( [length, 4, 'sbs__'+codeLine] )
				
				# In case assembly is NOT required
				hexLines.append( 'sbs__'+codeLine )
				length += 4
				
				# In case assembly is required
				linesForAssembler.append( 'OCL_{}:b 0'.format(labelIndex) ) # Collecting in case we need assembler
				labelIndex += 1
				
			elif '<<' in codeLine and '>>' in codeLine: # Identifies symbols in the form of <<functionName>>
				customSyntaxRanges.append( [length, 4, 'sym__'+codeLine] )

				# Replace custom address symbols with a temporary value placeholder
				sectionChunks = codeLine.split( '<<' )
				printoutCodeLine = codeLine
				for block in sectionChunks[1:]: # Skips first block (will never be a symbol)
					if '>>' in block:
						for potentialName in block.split( '>>' )[:-1]: # Skips last block (will never be a symbol)
							if potentialName != '' and ' ' not in potentialName:
								printoutCodeLine = printoutCodeLine.replace( '<<' + potentialName + '>>', '0x80000000' )

				# Check if this line is just a branch
				if assemblyRequired: pass
				elif sectionChunks[0] in ( 'b', 'bl', 'bla' ): # Ignore these as assembly, since they can be assembled internally
					# In case assembly is NOT required
					hexLines.append( 'sym__'+codeLine )
					length += 4
				else: # Abandon calculating length ourselves; get it from assembler
					assemblyRequired = True
				
				# In case assembly is required
				linesForAssembler.append( 'OCL_{}:{}'.format(labelIndex, printoutCodeLine) )
				labelIndex += 1

			elif '[[' in codeLine and ']]' in codeLine: # Identifies customization option placeholders
				#customSyntaxes.append( '|S|opt__' + codeLine + '|S|' )

				# Gather all placeholders (option names), and make sure they exist in one of the option dictionaries

				# Parse out all option names, and collect their information from the mod's customization dictionaries
				sectionChunks = codeLine.split( '[[' )
				optionInfo = [] # Will be a list of tuples, of the form (optionName, optionType)
				#lineOffset = 0
				#syntaxRanges = []
				for chunk in sectionChunks:
					if ']]' in chunk:
						varName, theRest = chunk.split( ']]' ) # Not expecting multiple ']]' delimiters in this chunk

						# Attempt to get the customization name (and size if the code is already assembled)
						for option in customizations:
							optionName = option.get( 'name' )
							optionType = option.get( 'type' )
							if optionName == varName:
								if not optionType:
									return 4, -1, optionName, []
								optionWidth = self.getOptionWidth( optionType )
								if optionWidth == -1:
									return 5, -1, optionType, []
								break
						else: # The loop above didn't break; option not found or it's invalid
							return 3, -1, varName, []
						optionInfo.append( (length, '[[' + varName + ']]', optionWidth) )

						# If the custom code following the option is entirely raw hex (or an empty string), get its length
						if assemblyRequired: pass
						elif all( char in hexdigits for char in theRest.replace(' ', '') ):
							theRestLength = len( theRest.replace(' ', '') ) / 2
							length += optionWidth + theRestLength
							#lineOffset += optionWidth + theRestLength
							customSyntaxRanges.append( [length, optionWidth, 'opt__'+codeLine] )
						else:
							assemblyRequired = True

						#customSyntaxRanges.append( [length, optionWidth, 'opt__'+codeLine] )

					# If other custom code in this line is raw hex, get its length
					elif assemblyRequired: pass
					elif all( char in hexdigits for char in chunk.replace(' ', '') ):
						chunkLength = len( chunk.replace(' ', '') ) / 2
						length += chunkLength
						#lineOffset += chunkLength
					else: # Abandon calculating length ourselves; get it from assembler
						assemblyRequired = True

				# Replace collected option names for placeholder values
				#newCodeLine = codeLine
				if assemblyRequired:
					# newCodeLine = codeLine
					# for ( _, optionName, _ ) in optionInfo:
					# 	newCodeLine = newCodeLine.replace( optionName, '0' )
					customSyntaxRanges.append( [-1, optionWidth, 'opt__'+codeLine] )

				else: # Apart from the option placeholder, the line is raw hex; need to look up types for value sizes
				# 	for ( length, optionName, optionWidth ) in optionInfo:
				# 		#newCodeLine = codeLine.replace( optionName, '00' * optionWidth )
				# 		customSyntaxRanges.append( [length, optionWidth, 'opt__'+codeLine] )
					hexLines.append( 'opt__'+codeLine )

				# Create a line in case assembler is needed
				newCodeLine = codeLine
				for ( _, optionName, _ ) in optionInfo:
					newCodeLine = newCodeLine.replace( optionName, '0' )

				linesForAssembler.append( 'OCL_{}:{}'.format(labelIndex, newCodeLine) ) # Collecting in case we need assembler
				labelIndex += 1

			else:
				# Check whether this line indicates that this code requires conversion.
				if assemblyRequired: pass
				elif all( char in hexdigits for char in codeLine.replace(' ', '') ): # Is in hex form
					hexLines.append( codeLine )
					hexCodeLen = len( codeLine.replace(' ', '') ) / 2
					length += hexCodeLen
					#linesForAssembler.append( '.zero ' + str(hexCodeLen) )
				else:
					assemblyRequired = True

				# Whether it's hex or not, re-add the current line to hexLines.
				linesForAssembler.append( codeLine )

		# Run the code through the assembler if needed
		#if assemblyRequired and customizationsEnabled:
		if assemblyRequired:
			# Add assembly to handle the label calculations
			linesForAssembler.append( '.altmacro' )
			labelOffsets = [ '%OCL_{}-start'.format(i) for i in range(labelIndex) ]
			linesForAssembler.append( '.irp loc, ' + ', '.join(labelOffsets) )
			linesForAssembler.append( '  .print "offset:\\loc"' )
			linesForAssembler.append( '.endr' )

			codeForAssembler = '\n'.join( linesForAssembler ) # Joins the filtered lines with line breaks
			conversionOutput, errors = self.assemble( codeForAssembler, False, includePaths, True, False ) # No assembly output parsing
			
			if errors:
				# If suppressWarnings is True, there shouldn't be warnings in the error text; but there may still be actual errors reported
				#if not suppressWarnings:
				cmsg( errors, 'Assembly Error 02' )
				return 1, -1, errors, []

			# Parse the assembly output for customization offsets
			#customSyntaxRanges = []
			conversionOutputLines = conversionOutput.splitlines()
			standardFirstLine = 0
			for i, line in enumerate( conversionOutputLines ):
				if line.startswith( 'offset:' ):
					#customSyntaxRanges.append( int(line.split(':')[1]) )
					customSyntaxRanges[i][0] = int(line.split(':')[1])
				elif line.startswith( 'GAS LISTING' ):
					break
				standardFirstLine += 1

			# line = 0
			# for syntaxRange in customSyntaxRanges:
			# 	originalLine = syntaxRange[-1]
			
			parsedOutput, errors = self.parseAssemblerOutput( '\n'.join(conversionOutputLines[standardFirstLine:]) )
			length = len( parsedOutput.strip() ) / 2

			if errors:
				return 1, -1, errors, []

			# Create the preProcessed string, which is assembled hex code, with the custom syntaxes stripped out and replaced with the original code lines
			preProcessedCode = []
			position = 0 # Byte positional offset in the parsed output
			for offset, width, originalLine in customSyntaxRanges:
				#previousHex = parsedOutput[position*2:(position+offset)*2] # Mult. by 2 to count by nibbles
				previousHex = parsedOutput[position*2:offset*2]
				if previousHex: # May be empty (at start, and if custom syntax is back to back)
					preProcessedCode.append( previousHex )
					position += len( previousHex ) / 2
				preProcessedCode.append( originalLine )
				position += width
			if position != length: # Add final section
				preProcessedCode.append( parsedOutput[position*2:] ) # Mult. by 2 to count by nibbles
			
			# print 'Pre-processed code:'
			# print preProcessedCode

			preProcessedCode = '|S|'.join( preProcessedCode )

		else: # The original custom code is already in hex form
			preProcessedCode = '|S|'.join( hexLines )
			
			# print 'Pre-processed code:'
			# print hexLines

		# elif assemblyRequired: # Assemble without extra customization option parsing
		# 	filteredCode = '\n'.join( hexLines ) # Joins the filtered lines with linebreaks.
		# 	parsedOutput, errors = self.assemble( filteredCode, False, includePaths, suppressWarnings, True ) # Assembly output parsing enabled
			
		# 	if errors:
		# 		# If suppressWarnings is True, there shouldn't be warnings in the error text; but there may still be actual errors reported
		# 		if not suppressWarnings:
		# 			cmsg( errors, 'Assembly Error 02' )
		# 		return -1

		# 	return len( parsedOutput.strip() ) / 2

		# else: # No assembly required
		# 	return length

		return 0, length, preProcessedCode, customSyntaxRanges

	def preAssembleRawCode( self, codeLinesList, includePaths=None, discardWhitespace=True, suppressWarnings=False ):

		""" This method takes assembly or hex code, filters out custom MCM syntaxes and comments, and assembles the code 
			using the PowerPC EABI if it was assembly. Once that is done, the custom syntaxes are added back into the code, 
			which will be replaced (compiled to hex) later. If the option to include whitespace is enabled, then the resulting 
			code will be formatted with spaces after every 4 bytes and line breaks after every 8 bytes (like a Gecko code). 
			The 'includePaths' option specifies a list of [full/absolute] directory paths for .include imports. 

			Return codes from this method are:
				0: Success
				1: Compilation placeholder or branch marker detected in original code
				2: Error during assembly
				3: Include file(s) could not be found
		"""

		# Define placeholders for special syntaxes
		compilationPlaceholder = 'stfdu f21,-16642(r13)' # Equivalent of 'deadbefe' (doesn't actually matter what this is, but must be in ASM in case of conversion)
		branchMarker = 'DEADBEFE'

		needsConversion = False
		allSpecialSyntaxes = True
		filteredLines = []
		customSyntax = []

		if type( codeLinesList ) != list:
			codeLinesList = codeLinesList.splitlines()

		# Filter out special syntaxes and remove comments
		for rawLine in codeLinesList:
			# Start off by filtering out comments
			codeLine = rawLine.split( '#' )[0].strip()

			if compilationPlaceholder in codeLine or branchMarker in codeLine:
				# This should be a very rare problem, so I'm not going to bother with suppressing this
				msg( 'There was an error while assembling this code (compilation placeholder detected):\n\n' + '\n'.join(codeLinesList), 'Assembly Error 01' )
				return ( 1, '' )

			elif CodeLibraryParser.isSpecialBranchSyntax( codeLine ): # e.g. "bl 0x80001234" or "bl <testFunction>"
				# Store the original command.
				if discardWhitespace: customSyntax.append( '|S|sbs__' + codeLine + '|S|' ) # Add parts for internal processing
				else: customSyntax.append( codeLine ) # Keep the finished string human-readable

				# Add a placeholder for compilation (important for other branch calculations). It will be replaced with the original command after the code is assembled to hex.
				filteredLines.append( compilationPlaceholder )

			elif CodeLibraryParser.containsPointerSymbol( codeLine ): # Identifies symbols in the form of <<functionName>>
				# Store the original command.
				if discardWhitespace: customSyntax.append( '|S|sym__' + codeLine + '|S|' ) # Add parts for internal processing
				else: customSyntax.append( codeLine ) # Keep the finished string human-readable

				# Add a placeholder for compilation (important for other branch calculations). It will be replaced with the original command after the code is assembled to hex.
				filteredLines.append( compilationPlaceholder )

			elif '[[' in codeLine and ']]' in codeLine: # Identifies customization option placeholders
				# Store the original command.
				if discardWhitespace: customSyntax.append( '|S|opt__' + codeLine + '|S|' ) # Add parts for internal processing
				else: customSyntax.append( codeLine ) # Keep the finished string human-readable

				# Add a placeholder for compilation (important for other branch calculations). It will be replaced with the original command after the code is assembled to hex.
				filteredLines.append( compilationPlaceholder )

			else:
				# Whether it's hex or not, re-add the line to filteredLines.
				filteredLines.append( codeLine )
				allSpecialSyntaxes = False

				# Check whether this line indicates that this code requires conversion.
				if not needsConversion and codeLine != '' and not validHex( codeLine.replace(' ', '') ):
					needsConversion = True

		if allSpecialSyntaxes: # No real processing needed; it will be done when resolving these syntaxes
			if discardWhitespace:
				return ( 0, ''.join(customSyntax) )
			else:
				return ( 0, '\n'.join(customSyntax) )

		filteredCode = '\n'.join( filteredLines ) # Joins the filtered lines with linebreaks.

		# If this is ASM, convert it to hex.
		if needsConversion:
			conversionOutput, errors = self.assemble( filteredCode, beautify=True, includePaths=includePaths, suppressWarnings=suppressWarnings )
			
			if errors:
				# If suppressWarnings is True, there shouldn't be warnings in the error text; but there may still be actual errors reported
				if not suppressWarnings:
					cmsg( errors, 'Assembly Error 02' )

				# Parse the error message for missing include files
				missingIncludeFile = ''
				for line in errors.splitlines():
					splitLine = line.split( "Error: can't open" )
					if len( splitLine ) == 2 and line.endswith( "No such file or directory" ):
						missingIncludeFile = splitLine[1].split( 'for reading:' )[0].strip()
						break

				if missingIncludeFile:
					return ( 3, missingIncludeFile )
				else:
					return ( 2, '' )

			else:
				newCode = conversionOutput.strip()
		else:
			newCode = filteredCode.replace( 'stfdu f21,-16642(r13)', 'DEADBEFE' ).strip()

		# If any special commands were filtered out, add them back in.
		if newCode and customSyntax:
			# The code should be in hex at this point, with whitespace
			commandArray = newCode.split() # Split by whitespace

			commandLineArray = []
			specialBranchIndex = 0

			if discardWhitespace:
				for command in commandArray:

					# Add the previously saved special command(s).
					if command == branchMarker: 
						commandLineArray.append( customSyntax[specialBranchIndex] )
						specialBranchIndex += 1

					# Add just this command to this line.
					else: commandLineArray.append( command )

				newCode = ''.join( commandLineArray ).strip()

			else: # Add some extra formatting for the user.
				skip = False
				i = 1
				for command in commandArray:
					if skip:
						skip = False
						i += 1
						continue

					# Add the previously saved special command(s).
					if command == branchMarker: # This line was a special syntax
						commandLineArray.append( customSyntax[specialBranchIndex] )
						specialBranchIndex += 1

					# Add this command and the next on the same line if neither is a special syntax.
					elif i < len( commandArray ) and commandArray[i] != 'DEADBEFE':
						commandLineArray.append( command + ' ' + commandArray[i] )
						skip = True

					# Add just this command to this line.
					else: commandLineArray.append( command )

					i += 1

				newCode = '\n'.join( commandLineArray ).strip()

		elif discardWhitespace:
			newCode = ''.join( newCode.split() )

		return ( 0, newCode )

	def preDisassembleRawCode( self, codeLinesList, discardWhitespace=True ):
		# Define placeholders for special syntaxes
		compilationPlaceholder = 'DEADBEFE'
		branchMarker = 'stfdu f21,-16642(r13)'

		if type( codeLinesList ) == str:
			codeLinesList = codeLinesList.splitlines()

		# Filter out the special branch syntax, and remove comments.
		needsConversion = False
		allSpecialSyntaxes = True
		filteredLines = []
		customSyntax = []
		for rawLine in codeLinesList:
			# Remove comments and skip empty lines
			codeLine = rawLine.split( '#' )[0].strip()
			if codeLine == '': continue

			elif compilationPlaceholder in codeLine or branchMarker in codeLine:
				msg( 'There was an error while disassembling this code (compilation placeholder detected):\n\n' + codeLinesList, 'Disassembly Error 01' )
				return ( 1, '' )

			# Store original command, and add a placeholder for compilation (it will be replaced with the original command after the code is assembled to hex)
			if CodeLibraryParser.isSpecialBranchSyntax( codeLine ): # e.g. "bl 0x80001234" or "bl <testFunction>"
				customSyntax.append( codeLine )
				filteredLines.append( compilationPlaceholder )

			elif CodeLibraryParser.containsPointerSymbol( codeLine ): # Identifies symbols in the form of <<functionName>>
				customSyntax.append( codeLine )
				filteredLines.append( compilationPlaceholder )

			elif '[[' in codeLine and ']]' in codeLine: # Identifies customization option placeholders
				customSyntax.append( codeLine )
				filteredLines.append( compilationPlaceholder )

			else:
				# Whether it's hex or not, re-add the line to filteredLines.
				filteredLines.append( codeLine )
				allSpecialSyntaxes = False

				# Check whether this line indicates that this code requires conversion.
				if not needsConversion and validHex( codeLine.replace(' ', '') ):
					needsConversion = True

		if allSpecialSyntaxes: # No real processing needed; it will be done when resolving these syntaxes
			if discardWhitespace:
				return ( 0, ''.join(customSyntax) )
			else:
				return ( 0, '\n'.join(customSyntax) )

		filteredCode = '\n'.join( filteredLines ) # Joins the lines with linebreaks.

		# If this is hex, convert it to ASM.
		if needsConversion:
			conversionOutput, errors = self.disassemble( filteredCode, whitespaceNeedsRemoving=True )
			
			if errors:
				cmsg( errors, 'Disassembly Error 02' )
				return ( 2, '' )
			else:
				newCode = conversionOutput
		else:
			newCode = filteredCode.replace( 'DEADBEFE', 'stfdu f21,-16642(r13)' )

		# If any special commands were filtered out, add them back in.
		if newCode != '' and customSyntax != []:
			# The code is in assembly, with commands separated by line
			commandArray = newCode.splitlines()
			commandLineArray = []
			specialBranchIndex = 0

			if discardWhitespace:
				for command in commandArray:

					# Add the previously saved special command(s).
					if command == branchMarker: 
						commandLineArray.append( customSyntax[specialBranchIndex] )
						specialBranchIndex += 1

					# Add just this command to this line.
					else: commandLineArray.append( command )

				newCode = ''.join( commandLineArray )

			else: # Add some extra formatting for the user.
				# Replace special syntax placeholders with the previously saved special command(s)
				for command in commandArray:
					if command == branchMarker: # This line was a special syntax
						commandLineArray.append( customSyntax[specialBranchIndex] )
						specialBranchIndex += 1

					# Add just this command to this line.
					else: commandLineArray.append( command )

				newCode = '\n'.join( commandLineArray )
		elif discardWhitespace:
			newCode = ''.join( newCode.split() )

		# Replace a few choice ASM commands with an alternate syntax
		#newCode = newCode.replace( 'lwz r0,0(r1)', 'lwz r0,0(sp)' ).replace( 'lwz r0,0(r2)', 'lwz r0,0(rtoc)' )

		return ( 0, newCode.strip() )

	def resolveCustomSyntaxes( self, thisFunctionStartingOffset, rawCustomCode, preProcessedCustomCode, includePaths=None, options=None ):

		""" Replaces any custom branch syntaxes that don't exist in the assembler with standard 'b_ [intDistance]' branches, 
			and replaces function symbols with literal RAM addresses, of where that function will end up residing in memory. 

			This process may require two passes. The first is always needed, in order to determine all addresses and syntax resolutions. 
			The second may be needed for final assembly because some lines with custom syntaxes might need to reference other parts of 
			the whole source code (raw custom code), such as for macros or label branch calculations. 
			
			May return these return codes:
				0: Success (or no processing was needed)
				2: Unable to assemble source code with custom syntaxes
				3: Unable to assemble custom syntaxes (source is in hex form)
				4: Unable to find a customization option name
				100: Success, and the last instruction is a custom syntax
		"""

		# If this code has no special syntaxes in it, return it as-is
		if '|S|' not in preProcessedCustomCode:
			return ( 0, preProcessedCustomCode )

		debugging = False

		if debugging:
			print '\nResolving custom syntaxes for code stored at', hex( thisFunctionStartingOffset )

		customCodeSections = preProcessedCustomCode.split( '|S|' )
		rawCustomCodeLines = rawCustomCode.splitlines()
		rawCodeIsAssembly = self.codeIsAssembly( rawCustomCodeLines ) # Checking the form of the raw (initial) code input, not the pre-processed code
		#dol = globalData.disc.dol
		resolvedAsmCodeLines = []
		requiresAssembly = False
		#errorDetails = ''
		byteOffset = 0
		returnCode = 0

		# Resolve individual syntaxes to finished assembly and/or hex
		for i, section in enumerate( customCodeSections ):

			if section.startswith( 'sbs__' ): # Something of the form 'bl 0x80001234' or 'bl <function>'; build a branch from this
				section = section[5:] # Removes the 'sbs__' identifier

				if debugging:
					print 'recognized special branch syntax at function offset', hex( byteOffset ) + ':', section

				if '+' in section:
					section, offset = section.split( '+' ) # Whitespace around the + should be fine for int()
					if offset.lstrip().startswith( '0x' ):
						branchAdjustment = int( offset, 16 )
					else: branchAdjustment = int( offset )
				else: branchAdjustment = 0

				branchInstruction, targetDescriptor = section.split()[:2] # Get up to two parts max

				if CodeLibraryParser.isStandaloneFunctionHeader( targetDescriptor ): # The syntax references a standalone function (comments should already be filtered out).
					targetFunctionName = targetDescriptor[1:-1] # Removes the </> characters
					targetFunctionAddress = globalData.standaloneFunctions[targetFunctionName][0] # RAM Address
					#branchDistance = dol.calcBranchDistance( thisFunctionStartingOffset + byteOffset, targetFunctionAddress )
					branchDistance = targetFunctionAddress - ( thisFunctionStartingOffset + byteOffset )

					# if branchDistance == -1: # Fatal error; end the loop
					# 	errorDetails = 'Unable to calculate SF branching distance, from {} to {}.'.format( hex(thisFunctionStartingOffset + byteOffset), hex(targetFunctionAddress) )
					# 	break

				else: # Must be a special branch syntax using a RAM address
					# startingRamOffset = dol.offsetInRAM( thisFunctionStartingOffset + byteOffset )

					# if startingRamOffset == -1: # Fatal error; end the loop
					# 	errorDetails = 'Unable to determine starting RAM offset, from DOL offset {}.'.format( hex(thisFunctionStartingOffset + byteOffset) )
					# 	break
					#branchDistance = int( targetDescriptor, 16 ) - 0x80000000 - startingRamOffset
					branchDistance = int( targetDescriptor, 16 ) - ( thisFunctionStartingOffset + byteOffset )

				branchDistance += branchAdjustment

				# Remember in case reassembly is later determined to be required
				resolvedAsmCodeLines.append( '{} {}'.format(branchInstruction, branchDistance) ) 

				# Replace this line with hex for the finished branch
				if not requiresAssembly: # The preProcessed customCode won't be used if reassembly is required; so don't bother replacing those lines
					customCodeSections[i] = self.assembleBranch( branchInstruction, branchDistance ) # Assembles these arguments into a finished hex string

				# Check if this was the last section
				if i + 1 == len( customCodeSections ):
					returnCode = 100

				byteOffset += 4

			elif section.startswith( 'sym__' ): # Contains a function symbol; something like 'lis r3, (<<function>>+0x40)@h'; change the symbol to an address
				section = section[5:]

				if debugging:
					print 'resolving symbol names in:', section

				#erroredFunctions = set()

				# Determine the RAM addresses for the symbols, and replace them in the line
				for name in CodeLibraryParser.containsPointerSymbol( section ):
					# Get the dol offset and ultimate RAM address of the target function
					targetFunctionAddress = globalData.standaloneFunctions[name][0]
					# ramAddress = dol.offsetInRAM( targetFunctionAddress ) + 0x80000000
					
					# if ramAddress == -1: # Fatal error; probably an invalid function offset was given, pointing to an area outside of the DOL
					# 	erroredFunctions.add( name )

					#address = "0x{0:0{1}X}".format( ramAddress, 8 ) # e.g. 1234 (int) -> '0x800004D2' (string)
					address = "0x{:08X}".format( targetFunctionAddress ) # e.g. 1234 (int) -> '0x800004D2' (string)

					section = section.replace( '<<' + name + '>>', address )

				# if erroredFunctions:
				# 	errorDetails = 'Unable to calculate RAM addresses for the following function symbols:\n\n' + '\n'.join( erroredFunctions )
				# 	break				

				if debugging:
					print '              resolved to:', section

				requiresAssembly = True
				resolvedAsmCodeLines.append( section )

				# Check if this was the last section
				if i + 1 == len( customCodeSections ):
					returnCode = 100

				byteOffset += 4
				
			elif section.startswith( 'opt__' ): # Identifies customization option placeholders
				section = section[5:]

				#optionPairs = {}
				optionData = []

				# Replace variable placeholders with the currently set option value
				# Check if this section requires assembly, and collect option names/values
				sectionChunks = section.split( '[[' )
				for j, chunk in enumerate( sectionChunks ):
					if ']]' in chunk:
						varName, theRest = chunk.split( ']]' )

						# Seek out the option name and its current value in the customizations list
						for customization in options:
							if customization['name'] == varName:
								#currentValue = str( customization['value'] )
								optionData.append( (customization['type'], customization['value']) )
								break
						else: # Loop above didn't break; variable name not found!
							return ( 4, 'Unable to find the customization option "{}" in the mod definition.'.format(varName) )

						#sectionChunks[j] = chunk.replace( varName+']]', currentValue )

						if requiresAssembly: pass
						elif all( char in hexdigits for char in theRest.replace(' ', '') ): pass
						else: requiresAssembly = True
						
					elif requiresAssembly: pass
					elif all( char in hexdigits for char in chunk.replace(' ', '') ): pass
					else: requiresAssembly = True

				# Reiterate over the chunks to replace the names with values, now that we know whether they should be packed
				for j, chunk in enumerate( sectionChunks ):
					if ']]' in chunk:
						varName, theRest = chunk.split( ']]' )

						if requiresAssembly: # No need to pad the value
							value = optionData.pop( 0 )[-1]
							sectionChunks[j] = chunk.replace( varName+']]', str(value) )
						else: # Needs to be packed to the appropriate length for the data type
							optionType, value = optionData.pop( 0 )
							if '0x' in value:
								value = int( value, 16 )
							else:
								value = int( value )
							valueAsBytes = struct.pack( CustomizationTypes[optionType], value )
							sectionChunks[j] = chunk.replace( varName+']]', hexlify(valueAsBytes) )

				resolvedAsmCodeLines.append( ''.join(sectionChunks) )
						
				# Check if this was the last section
				if i + 1 == len( customCodeSections ):
					returnCode = 100

				byteOffset += 4

			else: # This code should already be pre-processed hex (assembled, with whitespace removed)
				byteOffset += len( section ) / 2

		#if errorDetails: return ( 1, errorDetails )

		# Assemble the final code using the full source (raw) code
		if requiresAssembly and rawCodeIsAssembly:
			if debugging:
				print 'reassembling resolved code from source (asm) code'

			# Using the original, raw code, remove comments, replace the custom syntaxes, and assemble it into hex
			rawAssembly = []

			for line in rawCustomCodeLines:
				# Start off by filtering out comments and empty lines.
				codeLine = line.split( '#' )[0].strip()
					
				if CodeLibraryParser.isSpecialBranchSyntax( codeLine ) or CodeLibraryParser.containsPointerSymbol( codeLine ) or CodeLibraryParser.containsCustomization( codeLine ):
					# Replace with resolved code lines
					rawAssembly.append( resolvedAsmCodeLines.pop(0) )
				else:
					rawAssembly.append( codeLine )

			customCode, errors = self.assemble( '\n'.join(rawAssembly), includePaths=includePaths, suppressWarnings=True )

			if errors:
				return ( 2, 'Unable to assemble source code with custom syntaxes.\n\n' + errors )

		elif requiresAssembly: # Yet the raw code is in hex form
			if debugging:
				print 'assembling custom syntaxes separately from assembled hex'

			# Assemble the resolved lines in one group (doing it this way instead of independently in the customCodeSections loop for less IPC overhead)
			assembledResolvedCode, errors = self.assemble( '\n'.join(resolvedAsmCodeLines), beautify=True, suppressWarnings=True )
			resolvedHexCodeLines = assembledResolvedCode.split()
			newCustomCodeSections = preProcessedCustomCode.split( '|S|' ) # Need to re-split this, since customCodeSections may have been modified by now

			if errors:
				return ( 3, 'Unable to assemble hex code with custom syntaxes.\n\n' + errors )
			else:
				# Add the resolved, assembled custom syntaxes back into the full custom code string
				for i, section in enumerate( newCustomCodeSections ):
					if section.startswith( 'sbs__' ) or section.startswith( 'sym__' ):
						newCustomCodeSections[i] = resolvedHexCodeLines.pop( 0 )
						if resolvedHexCodeLines == []: break

				customCode = ''.join( newCustomCodeSections )

		else: # Recombine the code lines back into one string. Special Branch Syntaxes have been assembled to hex
			if debugging:
				print 'resolved custom code using the preProcessedCustomCode lines'

			customCode = ''.join( customCodeSections )

		return ( returnCode, customCode )

	def assembleBranch( self, branchInstruction, branchDistance ):

		""" Basic method to quickly assemble branch binary (b/ba/bl/bal) instructions. 
			If another kind of branch is needed, this will use the assembler to do it. """

		branchInstruction = branchInstruction.lower().strip() # Normalize to lower-case without whitespace
		useAssembler = False

		# Determine whether the branch instruction is known (and set required flags) or if it needs to be sent to pyiiasmh for evaluation.
		if branchInstruction == 'b': pass
		elif branchInstruction == 'ba': # Interpret the address as absolute
			branchDistance += 2
		elif branchInstruction == 'bl': # Store the link register
			branchDistance += 1
		elif branchInstruction == 'bal' or branchInstruction == 'bla': # Interpret the address as absolute and store the link register
			branchDistance += 3
		else: useAssembler == True # Last resort, since this will take much longer

		if useAssembler:
			fullInstruction = branchInstruction + ' ' + str( branchDistance ) + '\n' # newLine char prevents an assembly error message.
			branch, errors = self.assemble( fullInstruction )
			if errors or len( branch ) != 8:
				return '48000000' # Failsafe, to prevent dol data from being corrupted with non-hex data
		else:
			# Determine if the branch is going forward or backward in RAM, and determine the appropriate op-code to use
			if branchDistance >= 0x1000000:
				opCode = '49'
				branchDistance -= 0x1000000
			elif branchDistance <= -0x1000000:
				opCode = '4A'
				branchDistance += 0x2000000
			elif branchDistance < 0:
				opCode = '4B'
				branchDistance += 0x1000000
			else:
				opCode = '48'
			
			# Return the hex for a hard (unconditional) branch
			branch = "{}{:06X}".format( opCode, branchDistance ) # Pads the value portion to 6 characters

		return branch

	# @staticmethod
	# def calcBranchDistance( fromDOL, toDOL ):
	# 	start = offsetInRAM( fromDOL, dol.sectionInfo )
	# 	end = offsetInRAM( toDOL, dol.sectionInfo )

	# 	if start == -1:
	# 		msg( 'Invalid input for branch calculation: "from" value (' + hex(fromDOL) + ') is out of range.' )
	# 		return -1
	# 	elif end == -1:
	# 		msg( 'Invalid input for branch calculation: "to" value (' + hex(toDOL) + ') is out of range.' ) #.\n\nTarget DOL Offset: ' + hex(toDOL) )
	# 		return -1
	# 	else:
	# 		return end - start

	@staticmethod
	def codeIsAssembly( codeLines ):

		""" For purposes of final code processing (resolving custom syntaxes), special syntaxes
			will be resolved to assembly, so they will also count as assembly here. """

		isAssembly = False
		onlySpecialSyntaxes = True

		for wholeLine in codeLines:
			# Strip off and ignore comments
			line = wholeLine.split( '#' )[0].strip()
			if line == '': continue

			elif CodeLibraryParser.isSpecialBranchSyntax( line ) or CodeLibraryParser.containsPointerSymbol( line ) or ('[[' in line and ']]' in line):
				continue # These will later be resolved to assembly
			
			onlySpecialSyntaxes = False

			if not validHex( ''.join(line.split()) ): # Whitespace is excluded from the check
				isAssembly = True
				break

		if onlySpecialSyntaxes:
			isAssembly = True

		return isAssembly