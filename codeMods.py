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
import struct
import codecs
import Tkinter as Tk

from string import hexdigits
from binascii import hexlify
from subprocess import Popen, PIPE

# Internal Dependencies
import globalData
from basicFunctions import toHex, validHex, msg
from guiSubComponents import cmsg


ConfigurationTypes = { 'int8': 'b', 'uint8': 'B', 'int16': '>h', 'uint16': '>H', 'int32': '>i', 'uint32': '>I', 'float': '>f' }


# def getCustomCodeLength( customCode, preProcess=False, includePaths=None, configurations=None ):

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

# 			# elif section.startswith( 'opt__' ): # Contains configuration options (bracketed variable name(s), e.g. '[[Some Var]]')
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


# def getCustomSectionLength( section ): # depricating (currently in dol.py)

# 	""" Similar to the function above for getting code length, but specific to lines with custom syntax. """

# 	section = section[5:] # Removing the special syntax identifier (e.g. 'sbs__')
# 	instruction = section.split()[0]

# 	if instruction == '.set': return 0
# 	elif instruction == '.byte': return 1
# 	elif instruction == '.hword': return 2
# 	else: return 4


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

	""" Represents a single code change to be made to the game, such 
		as a single code injection or static (in-place) overwrite. """

	def __init__( self, mod, changeType, offset, origCode, rawCustomCode, preProcessedCode, returnCode=-1 ):

		self.mod = mod
		self.type = changeType
		self.length = -1
		self.offset = offset		# String; may be a DOL offset or RAM address. Should be interpreted by one of the DOL normalization methods
		self.isAssembly = False
		self.syntaxInfo = []		# A list of lists. Each sub-list is of the form [ offset, optionWidth, originalLine, name ]
		self._origCode = origCode
		self.rawCode = rawCustomCode
		self.preProcessedCode = preProcessedCode
		self.processStatus = returnCode

	@property
	def origCode( self ):

		""" Original code may have been provided with the defined mod (particularly, within the MCM format), 
			however it's not expected to be available from the AMFS format. This method will retrieve it from 
			a vanilla DOL if that is available. """

		if not self._origCode:
			# Retrieve the vanilla disc path
			vanillaDiscPath = globalData.getVanillaDiscPath()
			if not vanillaDiscPath: # User canceled path input
				printStatus( 'Unable to get DOL data; no vanilla disc available for reference', error=True )
				return
			
			# Load the vanilla disc
			vanillaDisc = Disc( vanillaDiscPath )
			vanillaDisc.load()

			# Get the DOL file, normalize the offset string, and get the target file data
			dol = vanillaDisc.dol
			dolOffset = dol.normalizeDolOffset( self.offset )
			self._origCode = dol.getData( dolOffset, self.getLength() )

		return self._origCode

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
			ensures configuration options are present and configured correctly (parsed from codes.json). """

		if self.processStatus != -1:
			return self.processStatus

		#rawCustomCode = '\n'.join( customCode ).strip() # Collapses the list of collected code lines into one string, removing leading & trailing whitespace
		self.processStatus, self.length, codeOrErrorNote, self.syntaxInfo, self.isAssembly = globalData.codeProcessor.evaluateCustomCode( self.rawCode, self.mod.includePaths, self.mod.configurations )
		
		if self.syntaxInfo:
			processStatus, length, codeOrErrorNote2, syntaxInfo, isAssembly = globalData.codeProcessor.evaluateCustomCode2( self.rawCode, self.mod.includePaths, self.mod.configurations )
		
			print '\nevaluation comparison: ({})'.format( self.mod.name )
			print 'status:', self.processStatus, processStatus
			print 'isAssembly:', self.isAssembly, isAssembly
			print 'len:', hex(self.length), hex(length)
			print codeOrErrorNote
			print codeOrErrorNote2
			print self.syntaxInfo
			print syntaxInfo

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
			self.mod.stateDesc = 'Configuration option not found: ' + codeOrErrorNote
			self.mod.errors.append( 'Configuration option not found: {}'.format(codeOrErrorNote) )
		elif self.processStatus == 4:
			self.mod.parsingError = True
			self.mod.stateDesc = 'Configuration option "{}" missing type parameter'.format( codeOrErrorNote )
			self.mod.errors.append( 'Configuration option "{}" missing type parameter'.format(codeOrErrorNote) )
		elif self.processStatus == 5:
			self.mod.parsingError = True
			self.mod.stateDesc = 'Unrecognized configuration option type: ' + codeOrErrorNote
			self.mod.errors.append( 'Unrecognized configuration option type: {}'.format(codeOrErrorNote) )

		if self.processStatus != 0:
			print 'Error parsing code change at', self.offset
			print 'Error code: {}; {}'.format( self.processStatus, self.mod.stateDesc )

		return self.processStatus

	def finalizeCode( self, targetAddress ):

		""" Performs final code processing for custom code, just before saving it to the DOL or codes file. 
			The save location for the given code as well as addresses for any standalone functions it might 
			require should already be known by this point, so custom syntaxes can now be resolved. User 
			configuration options are also now saved to the code. """

		self.evaluate()

		returnCode, finishedCode = globalData.codeProcessor.resolveCustomSyntaxes( targetAddress, self.rawCode, self.preProcessedCode, self.mod.includePaths, self.mod.configurations )

		""" resolveCustomSyntaxes may have these return codes:
				0: Success (or no processing was needed)
				2: Unable to assemble source code with custom syntaxes
				3: Unable to assemble custom syntaxes (source is in hex form)
				4: Unable to find a configuration option name
				100: Success, and the last instruction is a custom syntax """

		if returnCode != 0 and returnCode != 100: # In cases of an error, 'finishedCode' will include specifics on the problem
			if len( self.rawCode ) > 250: # Prevent a very long user message
				codeSample = self.rawCode[:250] + '\n...'
			else:
				codeSample = self.rawCode
			errorMsg = 'Unable to process custom code for {}:\n\n{}\n\n{}'.format( self.mod.name, codeSample, finishedCode )
			msg( errorMsg, 'Error Resolving Custom Syntaxes' )
		elif not finishedCode or not validHex( finishedCode ): # Failsafe; definitely not expected
			msg( 'There was an unknown error while processing the following custom code for {}:\n\n{}'.format(self.mod.name, self.rawCode), 'Error During Final Code Processing' )

		return returnCode, finishedCode


class CodeMod( object ):

	""" Container for all of the information on a code-related game mod. May be sourced from 
		code stored in the standard MCM format, or the newer ASM Mod Folder Structure (AMFS). """

	def __init__( self, name, auth='', desc='', srcPath='', isAmfs=False ):

		self.name = name
		self.auth = auth
		self.desc = desc
		self.data = {} 					# A dictionary that will be populated by lists of "CodeChange" objects
		self.path = srcPath				# Root folder path that contains this mod
		self.type = 'static'
		self.state = 'disabled'
		self.stateDesc = ''				# Describes reason for the state. Shows as a text status on the mod in the GUI
		self.configurations = {}		# Will be a dict of option dictionaries			required keys: name, type, value
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
		#self.missingIncludes = []		# Include filesnames detected to be required by the assembler
		self.errors = []

	def setState( self, newState ):

		if self.state == newState:
			return

		self.state = newState
		try:
			self.guiModule.setState( newState )
		except:
			pass # May not be currently displayed in the GUI

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

	def configure( self, name, value ):

		""" Changes a given configuration option to the given value. """

		# for option in self.configurations:
		# 	if option['name'] == name:
		# 		option['value'] = value
		# 		break
		# else:
		# 	raise Exception( '{} not found in configuration options.'.format(name) )

		self.configurations[name]['value'] = value

	def getConfiguration( self, name ):

		""" Gets the currently-set configuration option for a given option name. """

		# for option in self.configurations:
		# 	if option['name'] == name:
		# 		return option['value']
		# else:
		# 	raise Exception( '{} not found in configuration options.'.format(name) )

		return self.configurations[name]['value']

	@staticmethod
	def parseConfigValue( optionType, value ):

		""" Normalizes value input that may be a hex/decimal string or an int/float literal
			to an int or float. The source value type may not be consistent due to
			varying sources (i.e. from an MCM format file or AMFS config file). """

		if type( value ) == str: # Need to typecast to int or float
			if optionType == 'float':
				value = float( value )
			elif '0x' in value: # Convert from hex using base 16
				value = int( value, 16 )
			else: # Assume decimal value
				value = int( value )

		return value

	# def backupConfiguration( self ): #todo; may be required during mod installation detection
	# def restoreConfiguration( self ):


class CodeLibraryParser():

	""" The primary component for loading a Code Library. Will identify and parse the standard .txt file mod format, 
		as well as the AMFS structure. The primary .include paths for import statements are also set here. 

		Include Path Priority:
			1) The current working directory (usually the program root folder)
			2) Directory of the mod's code file (or the code's root folder with AMFS)
			3) The current Code Library's ".include" directory
			4) The program root folder's ".include" directory """

	def __init__( self ):

		self.stopToRescan = False
		self.codeMods = []
		self.modNames = set()
		self.includePaths = []

	def processDirectory( self, folderPath ):

		itemsInDir = os.listdir( folderPath ) # May be files or folders
		includePaths = [ folderPath ] + self.includePaths

		# Check if this folder is a mod in AMFS format
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
			
			itemPath = os.path.normpath( os.path.join(folderPath, item) )

			if os.path.isdir( itemPath ):
				self.processDirectory( itemPath ) # Recursive fun!

			elif item.lower().endswith( '.txt' ):
				# Collect all mod definitions from this file
				self.parseModsLibraryFile( itemPath, includePaths )

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
			header, however this is also used to help recognize the latter half (target descriptor) of a 
			special branch syntax such as the '<ShineActionState>' from 'bl <ShineActionState>'.
			Comments should already have been removed by this point. """

		if targetDescriptor.startswith( '<' ) and '>' in targetDescriptor and not ' ' in targetDescriptor.split( '>' )[:1]:
			return True
		else:
			return False

	@staticmethod
	def isGeckoCodeHeader( codeline ):
		
		""" Should return True for short header lines such as '1.02', 'PAL', 'ALL', etc (old syntaxes), 
			or 'NTSC 1.02', 'PAL 1.00', etc (new syntaxes). """

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
			This type of syntax is expected to be the only code on the line, and 
			will resolve to one 4-byte instruction once all code allocation is known. 
			Comments should already have been removed by this point. """

		lineParts = code.split()

		if code.lower().startswith( 'b' ) and len( lineParts ) == 2:
			targetDescriptor = lineParts[1]

			if targetDescriptor.startswith( '0x8' ) and len( targetDescriptor ) == 10: return True # Using a RAM address
			elif CodeLibraryParser.isStandaloneFunctionHeader( targetDescriptor ): return True # Using a function name
			
		return False

	@staticmethod
	def containsPointerSymbol( codeLine ): # Comments should already be excluded

		""" A line may contain multiple pointer symbols, but it will always be 
			part of (i.e. treated as) a single assembly instruction (ultimately 
			resolving to 4 bytes).
		
			This returns a list of names, but can also just be evaluated as True/False. """

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
			collectingConfigurations = False
			
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
			customizationName = ''

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
						collectingConfigurations = False
						
						if customizationOption:
							#mod.configurations.append( customizationOption )
							mod.configurations[customizationName] = customizationOption

					elif line.lower().startswith( 'configurations:' ):
						collectingConfigurations = True

					elif collectingConfigurations:
						try:
							if '=' in line: # name/type header for a new option
								# Store a previously collected option
								if customizationOption:
									#mod.configurations.append( customizationOption )
									mod.configurations[customizationName] = customizationOption

								# Parse out the option name and type
								typeName, valueInfo = line.split( '=' )
								typeNameParts = typeName.split() # Splitting on whitespace
								#customizationOption['name'] = ' '.join( typeNameParts[1:] )
								customizationOption = {}
								customizationName = ' '.join( typeNameParts[1:] )
								customizationOption['type'] = typeNameParts[0]

								# Validate the type
								if customizationOption['type'] not in ConfigurationTypes:
									raise Exception( 'unsupported option type' )

								# Check for and parse value ranges
								if ';' in valueInfo:
									defaultValue, rangeString = valueInfo.split( ';' )
									defaultValue = defaultValue.strip()

									# Parse range
									if '-' not in rangeString:
										raise Exception( 'No "-" separator in range string' )
									start, end = rangeString.split( '-' )
									# if customizationOption['type'] == 'float':
									# if '0x' in start:
									# 	start = int( start, 16 )
									# else:
									# 	start = int( start )
									# if customizationOption['type'] == 'float':
									# if '0x' in end:
									# 	end = int( end, 16 )
									# else:
									# 	end = int( end )
									customizationOption['range'] = ( start, end )

								elif valueInfo.strip():
									defaultValue = valueInfo.strip()

								else:
									defaultValue = '0'

								# if '0x' in defaultValue:
								# 	intValue = int( defaultValue, 16 )
								# else:
								# 	intValue = int( defaultValue )
								customizationOption['default'] = defaultValue
								customizationOption['value'] = defaultValue
								customizationOption['annotation'] = lineComments

							# Process enumerations/members of an existing option
							elif customizationOption and ':' in line:
								# Add the members list if not already present
								members = customizationOption.get( 'members' )
								if not members:
									customizationOption['members'] = []

								# Save the name, value, and comment from this line
								value, name = line.split( ':' )
								# if '0x' in value:
								# 	value = int( value, 16 )
								# else:
								# 	value = int( value )
								customizationOption['members'].append( [name.strip(), value.strip(), lineComments] )

						except Exception as err:
							mod.parsingError = True
							mod.stateDesc = 'Configurations parsing error'
							mod.errors.append( 'Configurations parsing error; {}'.format(err) )
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
						mod.stateDesc = 'Improper mod formatting'
						mod.errors.append( 'Improper mod formatting' )

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
					mod.stateDesc = 'Improper mod formatting'
					mod.errors.append( 'Improper mod formatting' )

			mod.desc = '\n'.join( mod.desc )

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
				mod.configurations = codeset.get( 'configurations', {} )

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
						
						if codeType == 'replace': # Static Overwrite; basically an 02/04 Gecko codetype (hex from json)
							mod.addStaticOverwrite( codeChangeDict['address'], codeChangeDict['value'].splitlines() )

						elif codeType == 'inject': # Standard code injection
							self.parseAmfsInject( codeChangeDict, mod )

						elif codeType == 'replaceCodeBlock': # Static overwrite of variable length (hex from file)
							self.parseAmfsReplaceCodeBlock( codeChangeDict, mod )

						elif codeType == 'branch' or codeType == 'branchAndLink':
							mod.errors.append( 'The ' + codeType + ' AMFS code type is not yet supported' )

						elif codeType == 'injectFolder':
							self.parseAmfsInjectFolder( codeChangeDict, mod )

						elif codeType == 'replaceBinary':
							mod.errors.append( 'The replaceBinary AMFS code type is not yet supported' )

						elif codeType == 'binary':
							mod.errors.append( 'The binary AMFS code type is not yet supported' )

						else:
							mod.errors.append( 'Unrecognized AMFS code type: ' + codeType )

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
	def beautifyHex( rawHex, blocksPerLine=2 ):

		""" Rewrites a hex string to something more human-readable, displaying 
			8 bytes per line (2 blocks of 4 bytes, separated by a space). """
		
		assert blocksPerLine > 0, 'Invalid blocksPerLine given to beautifyHex: ' + str( blocksPerLine )

		code = []
		divisor = blocksPerLine * 8

		for block in xrange( 0, len(rawHex), 8 ):

			if block == 0 or block % divisor != 0: # For blocksPerLine of 4, the modulo would be 0, 8, 16, 24, 0, 8...
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

		""" Parses output from the assembler into a hex string. 

			If beautify is False, no whitespace is included; 
			otherwise, the output is formatted into 2 chunks 
			of 4 bytes per line (like a Gecko code), for 
			better readability. """

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

	def getOptionWidth( self, optionType ):

		""" Returns how many bytes a configuration option of the given type is expected to fill. """

		if optionType.endswith( '32' ) or optionType == 'float':
			return 4
		elif optionType.endswith( '16' ):
			return 2
		elif optionType.endswith( '8' ):
			return 1
		else:
			return -1

	def parseSpecialBranchSyntax( self, codeLine, branchStart=-1 ):
		
		if '+' in codeLine:
			codeLine, offset = codeLine.split( '+' ) # Whitespace around the + is fine for int()
			if offset.lstrip().startswith( '0x' ):
				branchAdjustment = int( offset, 16 )
			else: branchAdjustment = int( offset )
		else: branchAdjustment = 0

		branchInstruction, targetDescriptor = codeLine.split()[:2] # Get up to two parts max

		if branchStart == -1:
			return branchInstruction, 0

		if self.isStandaloneFunctionHeader( targetDescriptor ): # The syntax references a standalone function (comments should already be filtered out).
			targetFunctionName = targetDescriptor[1:-1] # Removes the </> characters
			targetFunctionAddress = globalData.standaloneFunctions[targetFunctionName][0] # RAM Address
			#branchDistance = dol.calcBranchDistance( branchStart, targetFunctionAddress )
			branchDistance = targetFunctionAddress - ( branchStart )

			# if branchDistance == -1: # Fatal error; end the loop
			# 	errorDetails = 'Unable to calculate SF branching distance, from {} to {}.'.format( hex(branchStart), hex(targetFunctionAddress) )
			# 	break

		else: # Must be a special branch syntax using a RAM address
			# startingRamOffset = dol.offsetInRAM( branchStart )

			# if startingRamOffset == -1: # Fatal error; end the loop
			# 	errorDetails = 'Unable to determine starting RAM offset, from DOL offset {}.'.format( hex(branchStart) )
			# 	break
			#branchDistance = int( targetDescriptor, 16 ) - 0x80000000 - startingRamOffset
			branchDistance = int( targetDescriptor, 16 ) - ( branchStart )

		branchDistance += branchAdjustment

		return branchInstruction, branchDistance

	def evaluateCustomCode( self, codeLinesList, includePaths=None, configurations=None ):
		
		""" This method takes assembly or hex code, parses out custom MCM syntaxes and comments, and assembles the code 
			using the PowerPC EABI if it was assembly. Once that is done, the custom syntaxes are added back into the code, 
			which will be replaced (compiled to hex) later. If the option to include whitespace is enabled, then the resulting 
			code will be formatted with spaces after every 4 bytes and line breaks after every 8 bytes (like a Gecko code). 
			The 'includePaths' option specifies a list of [full/absolute] directory paths for .include imports. 

			Returns: ( returnCode, codeLength, preProcessedCode, customSyntaxRanges, isAssembly )

			Return codes from this method are:
				0: Success
				1: Error during assembly (or in parsing assembly output)
				2: Include file(s) could not be found 		#todo: check on this
				3: Configuration option not found
				4: Configuration option missing type parameter
				5: Unrecognized configuration option type
		"""

		# Convert the input into a list of lines and check if it's assembly or hex code
		codeLinesList = codeLinesList.splitlines()
		isAssembly = self.codeIsAssembly( codeLinesList )

		if isAssembly:
			returnCode, codeLength, preProcessedCode, customSyntaxRanges = self._evaluateAssembly( codeLinesList, includePaths, configurations )
		else:
			returnCode, codeLength, preProcessedCode, customSyntaxRanges = self._evaluateHexcode( codeLinesList, includePaths, configurations )

		return returnCode, codeLength, preProcessedCode, customSyntaxRanges, isAssembly

		
	def evaluateCustomCode2( self, codeLinesList, includePaths=None, configurations=None ): # for testing
		codeLinesList = codeLinesList.splitlines()
		isAssembly = self.codeIsAssembly( codeLinesList )

		if isAssembly:
			returnCode, codeLength, preProcessedCode, customSyntaxRanges = self._evaluateAssembly2( codeLinesList, includePaths, configurations )
		else:
			returnCode, codeLength, preProcessedCode, customSyntaxRanges = self._evaluateHexcode2( codeLinesList, includePaths, configurations )

		return returnCode, codeLength, preProcessedCode, customSyntaxRanges, isAssembly

	def _evaluateAssembly( self, codeLinesList, includePaths, configurations ):

		linesForAssembler = [ 'start:' ]
		customSyntaxRanges = []

		# if type( codeLinesList ) != list:
		# 	codeLinesList = codeLinesList.splitlines()

		# Filter out special syntaxes and remove comments
		labelIndex = 0
		for rawLine in codeLinesList:
			# Start off by filtering out comments, and skip empty lines
			codeLine = rawLine.split( '#' )[0].strip()
			if not codeLine: continue

			if codeLine == '.align 2': # Replace the align directive with an alternative, which can't be calculated alongside the .irp instruction
				linesForAssembler.extend( ['padding = (3 - (.-start-1) & 3)', '.if padding', '  .zero padding', '.endif'] )

			elif CodeLibraryParser.isSpecialBranchSyntax( codeLine ): # e.g. "bl 0x80001234" or "bl <testFunction>"
				customSyntaxRanges.append( [-1, 4, 'sbs__'+codeLine, ()] )

				linesForAssembler.append( 'OCL_{}:b 0'.format(labelIndex) )
				labelIndex += 1
				
			elif '<<' in codeLine and '>>' in codeLine: # Identifies symbols in the form of <<functionName>>
				customSyntaxRanges.append( [-1, 4, 'sym__'+codeLine, ()] )

				# Replace custom address symbols with a temporary value placeholder
				sectionChunks = codeLine.split( '<<' )
				printoutCodeLine = codeLine
				for block in sectionChunks[1:]: # Skips first block (will never be a symbol)
					if '>>' in block:
						for potentialName in block.split( '>>' )[:-1]: # Skips last block (will never be a symbol)
							if potentialName != '' and ' ' not in potentialName:
								printoutCodeLine = printoutCodeLine.replace( '<<' + potentialName + '>>', '0x80000000' )

				linesForAssembler.append( 'OCL_{}:{}'.format(labelIndex, printoutCodeLine) )
				labelIndex += 1

			elif '[[' in codeLine and ']]' in codeLine: # Identifies configuration option placeholders
				# Parse out all option names, and collect their information from the mod's configuration dictionaries
				sectionChunks = codeLine.split( '[[' )
				#optionInfo = [] # Will be a list of tuples, of the form (optionName, optionType)
				#lineOffset = 0
				#syntaxRanges = []
				names = []
				for i, chunk in enumerate( sectionChunks ):
					if ']]' in chunk:
						varName, theRest = chunk.split( ']]' ) # Not expecting multiple ']]' delimiters in this chunk

						# Attempt to get the configuration name (and size if the code is already assembled)
						# for option in configurations:
						# 	optionName = option.get( 'name' )
						# 	optionType = option.get( 'type' )
						# 	if optionName == varName:
						# 		if not optionType:
						# 			return 4, -1, optionName, []
						# 		optionWidth = self.getOptionWidth( optionType )
						# 		if optionWidth == -1:
						# 			return 5, -1, optionType, []
						# 		break
						# else: # The loop above didn't break; option not found
						# 	return 3, -1, varName, []
						option = configurations.get( varName )
						if not option:
							return 3, -1, varName, []
						optionType = option.get( 'type' )
						if not optionType:
							return 4, -1, varName, []
						optionWidth = self.getOptionWidth( optionType )
						if optionWidth == -1:
							return 5, -1, optionType, []
						#optionInfo.append( (length, '[[' + varName + ']]', optionWidth) )
						sectionChunks[i] = chunk.replace( varName + ']]', '0' )
						names.append( varName )

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
				customSyntaxRanges.append( [-1, optionWidth, 'opt__'+codeLine, names] )

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
				linesForAssembler.append( codeLine )

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
			return 1, -1, errors, []

		elif not customSyntaxRanges: # No special syntax, no extra parsing needed
			preProcessedCode, errors = self.parseAssemblerOutput( conversionOutput )
			if errors:
				return 1, -1, errors, []

			length = len( preProcessedCode ) / 2

		else: # Custom syntax was found...
			# Parse out their offsets, and/or parse the assembler output in the usual manner
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
			if errors:
				return 1, -1, errors, []

			# Create the preProcessed string, which will be assembled hex code with the custom syntaxes stripped out and replaced with the original code lines
			length = len( parsedOutput ) / 2
			preProcessedLines = []
			position = 0 # Byte positional offset in the parsed output
			for offset, width, originalLine, _ in customSyntaxRanges:
				previousHex = parsedOutput[position*2:offset*2] # x2 to count by nibbles
				if previousHex: # May be empty (at start, and if custom syntax is back to back)
					preProcessedLines.append( previousHex )
					position += len( previousHex ) / 2
				preProcessedLines.append( originalLine )
				position += width
			if position != length: # Add final section
				preProcessedLines.append( parsedOutput[position*2:] ) # x2 to count by nibbles

			if len( preProcessedLines ) == 1:
				preProcessedCode = preProcessedLines[0] + '|S|' # Need to make sure this is included
			else:
				preProcessedCode = '|S|'.join( preProcessedLines )

		return 0, length, preProcessedCode, customSyntaxRanges

	def _evaluateHexcode( self, codeLinesList, includePaths=None, configurations=None ):

		customSyntaxRanges = []
		preProcessedLines = []
		length = 0

		# Filter out special syntaxes and remove comments
		for rawLine in codeLinesList:
			# Start off by filtering out comments, and skip empty lines
			codeLine = rawLine.split( '#' )[0].strip()
			if not codeLine: continue

			elif CodeLibraryParser.isSpecialBranchSyntax( codeLine ): # e.g. "bl 0x80001234" or "bl <testFunction>"
				customSyntaxRanges.append( [length, 4, 'sbs__'+codeLine, ()] )
				preProcessedLines.append( 'sbs__'+codeLine )
				length += 4
			
			elif '<<' in codeLine and '>>' in codeLine: # Identifies symbols in the form of <<functionName>>
				customSyntaxRanges.append( [length, 4, 'sym__'+codeLine, ()] )
				preProcessedLines.append( 'sym__'+codeLine )
				length += 4

			elif '[[' in codeLine and ']]' in codeLine: # Identifies configuration option placeholders
				thisLineOffset = length
				isAssembly = False
				newRanges = []
				sectionLength = 0

				# Parse out all option names, and collect their information from the mod's configuration dictionaries
				sectionChunks = codeLine.split( '[[' )
				for chunk in sectionChunks:
					if ']]' in chunk:
						varName, theRest = chunk.split( ']]' ) # Not expecting multiple ']]' delimiters in this chunk

						# Attempt to get the configuration name (and size if the code is already assembled)
						# for option in configurations:
						# 	optionName = option.get( 'name' )
						# 	optionType = option.get( 'type' )
						# 	if optionName == varName:
						# 		if not optionType:
						# 			return 4, -1, optionName, []
						# 		optionWidth = self.getOptionWidth( optionType )
						# 		if optionWidth == -1:
						# 			return 5, -1, optionType, []
						# 		break
						# else: # The loop above didn't break; option not found
						# 	return 3, -1, varName, []
						option = configurations.get( varName )
						if not option:
							return 3, -1, varName, []
						optionType = option.get( 'type' )
						if not optionType:
							return 4, -1, varName, []
						optionWidth = self.getOptionWidth( optionType )
						if optionWidth == -1:
							return 5, -1, optionType, []
						#optionInfo.append( (length, '[[' + varName + ']]', optionWidth) )
						newRanges.append( [length+sectionLength, optionWidth, 'opt__'+codeLine, [varName]] )
						#names.append( varName )

						# If the custom code following the option is entirely raw hex, get its length
						if isAssembly: pass
						elif not theRest:
							sectionLength += optionWidth
						elif all( char in hexdigits for char in theRest.replace(' ', '') ):
							theRestLength = len( theRest.replace(' ', '') ) / 2
							sectionLength += optionWidth + theRestLength
							#lineOffset += optionWidth + theRestLength
						else:
							isAssembly = True

						#customSyntaxRanges.append( [length, optionWidth, 'opt__'+codeLine] )

					# If other custom code in this line is raw hex, get its length
					elif isAssembly or not chunk: pass
					elif all( char in hexdigits for char in chunk.replace(' ', '') ):
						chunkLength = len( chunk.replace(' ', '') ) / 2
						sectionLength += chunkLength
						#lineOffset += chunkLength
					else: # Abandon calculating length ourselves; get it from assembler
						isAssembly = True

				# Replace collected option names for placeholder values
				#newCodeLine = codeLine
				if isAssembly:
					# newCodeLine = codeLine
					# for ( _, optionName, _ ) in optionInfo:
					# 	newCodeLine = newCodeLine.replace( optionName, '0' )

					#linesRequiringAssembly.append( codeLine )

					# Reset offsets in newRanges (to the start of this line), and add them to the full list
					newRanges = [ [thisLineOffset, w, l, n] for _, w, l, n in newRanges ]
					# customSyntaxRanges.extend( newRanges )
					length += 4
				else:
					length += sectionLength

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
				# Strip out whitespace and store the line
				pureHex = ''.join( codeLine.split() )
				length += len( pureHex ) / 2
				
				preProcessedLines.append( pureHex )

		if customSyntaxRanges: # Found custom syntax; add delimiters for future processing
			if len( preProcessedLines ) == 1:
				preProcessedCode = preProcessedLines[0] + '|S|' # Need to make sure this is included
			else:
				preProcessedCode = '|S|'.join( preProcessedLines )

		else:
			preProcessedCode = ''.join( preProcessedLines )

		return 0, length, preProcessedCode, customSyntaxRanges

	def _evaluateAssembly2( self, codeLines, includePaths, configurations ):

		customSyntaxRanges = []		# List of lists; each of the form [offset, width, type, origCodeLine, optNames]
		linesForAssembler = [ 'start:' ]

		# Filter out special syntaxes and remove comments
		labelIndex = 0
		for rawLine in codeLines:
			# Start off by filtering out comments, and skip empty lines
			codeLine = rawLine.split( '#' )[0].strip()
			if not codeLine: continue

			if codeLine == '.align 2': # Replace the align directive with an alternative, which can't be calculated alongside the .irp instruction
				linesForAssembler.extend( ['padding = (3 - (.-start-1) & 3)', '.if padding', '  .zero padding', '.endif'] )

			elif CodeLibraryParser.isSpecialBranchSyntax( codeLine ): # e.g. "bl 0x80001234" or "bl <testFunction>"
				#customSyntaxRanges.append( [-1, 4, 'sbs__'+codeLine, ()] )
				customSyntaxRanges.append( [-1, 4, 'sbs', codeLine, ()] )

				# Parse for some psuedo-code (the instruction should be correct, but branch distance will be 0)
				branchInstruction, branchDistance = self.parseSpecialBranchSyntax( codeLine )
				linesForAssembler.append( 'OCL_{}:{} {}'.format(labelIndex, branchInstruction, branchDistance) )
				labelIndex += 1
				
			elif '<<' in codeLine and '>>' in codeLine: # Identifies symbols in the form of <<functionName>>
				#customSyntaxRanges.append( [-1, 4, 'sym__'+codeLine, ()] )
				customSyntaxRanges.append( [-1, 4, 'sym', codeLine, ()] )

				# Replace custom address symbols with a temporary value placeholder
				sectionChunks = codeLine.split( '<<' )
				#printoutCodeLine = codeLine
				for block in sectionChunks[1:]: # Skips first block (will never be a symbol)
					if '>>' in block:
						for potentialName in block.split( '>>' )[:-1]: # Skips last block (will never be a symbol)
							if potentialName != '' and ' ' not in potentialName:
								codeLine = codeLine.replace( '<<' + potentialName + '>>', '0x80000000' )

				linesForAssembler.append( 'OCL_{}:{}'.format(labelIndex, codeLine) )
				labelIndex += 1

			elif '[[' in codeLine and ']]' in codeLine: # Identifies configuration option placeholders
				# Parse out all option names, and collect their information from the mod's configuration dictionaries
				sectionChunks = codeLine.split( '[[' )
				names = []
				for i, chunk in enumerate( sectionChunks ):
					if ']]' in chunk:
						varName, theRest = chunk.split( ']]' ) # Not expecting multiple ']]' delimiters in this chunk

						# Attempt to get the configuration name (and size if the code is already assembled)
						# for option in configurations:
						# 	optionName = option.get( 'name' )
						# 	optionType = option.get( 'type' )
						# 	if optionName == varName:
						# 		if not optionType:
						# 			return 4, -1, optionName, []
						# 		optionWidth = self.getOptionWidth( optionType )
						# 		if optionWidth == -1:
						# 			return 5, -1, optionType, []
						# 		break
						# else: # The loop above didn't break; option not found
						# 	return 3, -1, varName, []
						option = configurations.get( varName )
						if not option:
							return 3, -1, varName, []
						optionType = option.get( 'type' )
						if not optionType:
							return 4, -1, varName, []
						optionWidth = self.getOptionWidth( optionType )
						if optionWidth == -1:
							return 5, -1, optionType, []
						#optionInfo.append( (length, '[[' + varName + ']]', optionWidth) )
						sectionChunks[i] = chunk.replace( varName + ']]', '0' )
						names.append( varName )

				# Replace collected option names for placeholder values
				#newCodeLine = codeLine
				#if assemblyRequired:
					# newCodeLine = codeLine
					# for ( _, optionName, _ ) in optionInfo:
					# 	newCodeLine = newCodeLine.replace( optionName, '0' )
				customSyntaxRanges.append( [-1, optionWidth, 'opt', codeLine, names] )

				# Recombine line parts (which have value placeholders inserted) and store the line for assembly
				newCodeLine = ''.join( sectionChunks )
				linesForAssembler.append( 'OCL_{}:{}'.format(labelIndex, newCodeLine) )
				labelIndex += 1

			else:
				linesForAssembler.append( codeLine )

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
			return 1, -1, errors, []

		elif not customSyntaxRanges: # No special syntax, no extra parsing needed
			preProcessedCode, errors = self.parseAssemblerOutput( conversionOutput )
			# if errors:
			# 	return 1, -1, errors, []

			# length = len( preProcessedCode ) / 2

		else: # Custom syntax was found...
			# Parse out their offsets, and/or parse the assembler output in the usual manner
			standardFirstLine = 0
			conversionOutputLines = conversionOutput.splitlines()
			for i, line in enumerate( conversionOutputLines ):
				if line.startswith( 'offset:' ):
					#customSyntaxRanges.append( int(line.split(':')[1]) )
					customSyntaxRanges[i][0] = int( line.split(':')[1] )
				elif line.startswith( 'GAS LISTING' ):
					break
				standardFirstLine += 1
			#print 'syntax ranges post-parse:', customSyntaxRanges

			preProcessedCode, errors = self.parseAssemblerOutput( '\n'.join(conversionOutputLines[standardFirstLine:]) )
			# if errors:
			# 	return 1, -1, errors, []

			# Create the preProcessed string, which will be assembled hex code with the custom syntaxes stripped out and replaced with the original code lines
			# length = len( parsedOutput ) / 2
			# preProcessedLines = []
			# position = 0 # Byte positional offset in the parsed output
			# for offset, width, originalLine, _ in customSyntaxRanges:
			# 	previousHex = parsedOutput[position*2:offset*2] # x2 to count by nibbles
			# 	if previousHex: # May be empty (at start, and if custom syntax is back to back)
			# 		preProcessedLines.append( previousHex )
			# 		position += len( previousHex ) / 2
			# 	preProcessedLines.append( originalLine )
			# 	position += width
			# if position != length: # Add final section
			# 	preProcessedLines.append( parsedOutput[position*2:] ) # x2 to count by nibbles

			# if len( preProcessedLines ) == 1:
			# 	preProcessedCode = preProcessedLines[0] + '|S|' # Need to make sure this is included
			# else:
			# 	preProcessedCode = '|S|'.join( preProcessedLines )
			
		if errors:
			return 1, -1, errors, []

		length = len( preProcessedCode ) / 2

		return 0, length, preProcessedCode, customSyntaxRanges

	def _evaluateHexcode2( self, codeLines, includePaths=None, configurations=None ):

		customSyntaxRanges = []		# List of lists; each of the form [offset, width, type, origCodeLine, optNames]
		preProcessedLines = []
		length = 0

		# Filter out special syntaxes and remove comments
		for rawLine in codeLines:
			# Start off by filtering out comments, and skip empty lines
			codeLine = rawLine.split( '#' )[0].strip()
			if not codeLine: continue

			elif CodeLibraryParser.isSpecialBranchSyntax( codeLine ): # e.g. "bl 0x80001234" or "bl <testFunction>"
				#customSyntaxRanges.append( [length, 4, 'sbs__'+codeLine, ()] )
				#preProcessedLines.append( 'sbs__'+codeLine )
				
				customSyntaxRanges.append( [length, 4, 'sbs', codeLine, ()] )

				# Parse for some psuedo-code (the instruction should be correct, but branch distance will be 0)
				branchInstruction, branchDistance = self.parseSpecialBranchSyntax( codeLine )
				psudoHexCode = self.assembleBranch( branchInstruction, branchDistance )
				preProcessedLines.append( psudoHexCode )
				length += 4
			
			elif '<<' in codeLine and '>>' in codeLine: # Identifies symbols in the form of <<functionName>>
				#customSyntaxRanges.append( [length, 4, 'sym__'+codeLine, ()] )
				customSyntaxRanges.append( [length, 4, 'sym', codeLine, ()] )
				#preProcessedLines.append( 'sym__'+codeLine )
				preProcessedLines.append( '60000000' ) # Could be anything, soo... nop!
				length += 4

			elif '[[' in codeLine and ']]' in codeLine: # Identifies configuration option placeholders
				thisLineOffset = length
				#isAssembly = False
				#newRanges = []
				sectionLength = 0
				#lastSyntaxOffset = -1

				# Parse out all option names, and collect their information from the mod's configuration dictionaries
				sectionChunks = codeLine.split( '[[' )
				for chunk in sectionChunks:
					if ']]' in chunk:
						varName, theRest = chunk.split( ']]' ) # Not expecting multiple ']]' delimiters in this chunk

						# Attempt to get the configuration name (and size if the code is already assembled)
						# for option in configurations:
						# 	optionName = option.get( 'name' )
						# 	optionType = option.get( 'type' )
						# 	if optionName == varName:
						# 		if not optionType:
						# 			return 4, -1, optionName, []
						# 		optionWidth = self.getOptionWidth( optionType )
						# 		if optionWidth == -1:
						# 			return 5, -1, optionType, []
						# 		break
						# else: # The loop above didn't break; option not found
						# 	return 3, -1, varName, []
						option = configurations.get( varName )
						if not option:
							return 3, -1, varName, []
						optionType = option.get( 'type' )
						if not optionType:
							return 4, -1, varName, []
						optionWidth = self.getOptionWidth( optionType )
						if optionWidth == -1:
							return 5, -1, optionType, []
						#optionInfo.append( (length, '[[' + varName + ']]', optionWidth) )
						#newRanges.append( [length+sectionLength, optionWidth, 'opt__'+codeLine, [varName]] )
						#names.append( varName )

						# Add another name to the last names list if this option has the same offset as the last syntax
						# if lastSyntaxOffset == length + sectionLength:
						# 	newRanges[-1][-1].append( varName )
						# else:
						# 	lastSyntaxOffset = length + sectionLength
						# 	newRanges.append( [lastSyntaxOffset, optionWidth, 'opt', codeLine, [varName]] )

						if '|' in varName:
							names = varName.split( '|' )
							names = [ name.strip() for name in names ] # Remove whitespace from start/end of names
						else:
							names = [ varName ]
						
						customSyntaxRanges.append( [length+sectionLength, optionWidth, 'opt', codeLine, names] )

						# If the custom code following the option is entirely raw hex, get its length
						#if isAssembly: pass
						if not theRest:
							sectionLength += optionWidth
							preProcessedLines.append( '00' * optionWidth )
						#elif all( char in hexdigits for char in theRest.replace(' ', '') ):
						else:
							filteredChunk = ''.join( chunk.split() ) # Filtering out whitespace
							#theRestLength = len( filteredChunk ) / 2
							sectionLength += optionWidth + len( filteredChunk ) / 2
							preProcessedLines.append( filteredChunk )
							#lineOffset += optionWidth + theRestLength
						# else:
						# 	isAssembly = True

						#customSyntaxRanges.append( [length, optionWidth, 'opt__'+codeLine] )

					# If other custom code in this line is raw hex, get its length
					#elif isAssembly or not chunk: pass
					elif not chunk: pass
					#elif all( char in hexdigits for char in chunk.replace(' ', '') ):
					else:
						#chunkLength = len( chunk.replace(' ', '') ) / 2
						filteredChunk = ''.join( chunk.split() ) # Filtering out whitespace
						sectionLength += len( filteredChunk ) / 2
						preProcessedLines.append( filteredChunk )
						#lineOffset += chunkLength
					# else: # Abandon calculating length ourselves; get it from assembler
					# 	isAssembly = True

				# Replace collected option names for placeholder values
				#newCodeLine = codeLine
				# if isAssembly:
				# 	# newCodeLine = codeLine
				# 	# for ( _, optionName, _ ) in optionInfo:
				# 	# 	newCodeLine = newCodeLine.replace( optionName, '0' )

				# 	#linesRequiringAssembly.append( codeLine )

				# 	# Reset offsets in newRanges (to the start of this line), and add them to the full list
				# 	newRanges = [ [thisLineOffset, w, l, n] for _, w, l, n in newRanges ]
				# 	# customSyntaxRanges.extend( newRanges )
				# 	length += 4
				#else:
				length += sectionLength

				# else: # Apart from the option placeholder, the line is raw hex; need to look up types for value sizes
				# # 	for ( length, optionName, optionWidth ) in optionInfo:
				# # 		#newCodeLine = codeLine.replace( optionName, '00' * optionWidth )
				# # 		customSyntaxRanges.append( [length, optionWidth, 'opt__'+codeLine] )
				# 	hexLines.append( 'opt__'+codeLine )

				#preProcessedLines.append( 'opt__'+codeLine )
				#customSyntaxRanges.extend( newRanges )

				# Create a line in case assembler is needed
				# newCodeLine = codeLine
				# for ( _, optionName, _ ) in optionInfo:
				# 	newCodeLine = newCodeLine.replace( optionName, '0' )

				# linesForAssembler.append( 'OCL_{}:{}'.format(labelIndex, newCodeLine) ) # Collecting in case we need assembler
				# labelIndex += 1

			else:
				# Strip out whitespace and store the line
				pureHex = ''.join( codeLine.split() )
				length += len( pureHex ) / 2
				
				preProcessedLines.append( pureHex )

		# if customSyntaxRanges: # Found custom syntax; add delimiters for future processing
		# 	if len( preProcessedLines ) == 1:
		# 		preProcessedCode = preProcessedLines[0] + '|S|' # Need to make sure this is included
		# 	else:
		# 		preProcessedCode = '|S|'.join( preProcessedLines )

		# else:
		preProcessedCode = ''.join( preProcessedLines )

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

			elif '[[' in codeLine and ']]' in codeLine: # Identifies configuration option placeholders
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

			elif '[[' in codeLine and ']]' in codeLine: # Identifies configuration option placeholders
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

	def resolveCustomSyntaxes( self, thisFunctionStartingOffset, rawCustomCode, preProcessedCustomCode, includePaths=None, configurations=None ):

		""" Replaces any custom branch syntaxes that don't exist in the assembler with standard 'b_ [intDistance]' branches, 
			and replaces function symbols with literal RAM addresses, of where that function will end up residing in memory. 

			This process may require two passes. The first is always needed, in order to determine all addresses and syntax resolutions. 
			The second may be needed for final assembly because some lines with custom syntaxes might need to reference other parts of 
			the whole source code (raw custom code), such as for macros or label branch calculations. 
			
			May return these return codes:
				0: Success (or no processing was needed)
				2: Unable to assemble source code with custom syntaxes
				3: Unable to assemble custom syntaxes (source is in hex form)
				4: Unable to find a configuration option name
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
		resolvedCodeLines = []
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

				# if '+' in section:
				# 	section, offset = section.split( '+' ) # Whitespace around the + is fine for int()
				# 	if offset.lstrip().startswith( '0x' ):
				# 		branchAdjustment = int( offset, 16 )
				# 	else: branchAdjustment = int( offset )
				# else: branchAdjustment = 0

				# branchInstruction, targetDescriptor = section.split()[:2] # Get up to two parts max

				# if CodeLibraryParser.isStandaloneFunctionHeader( targetDescriptor ): # The syntax references a standalone function (comments should already be filtered out).
				# 	targetFunctionName = targetDescriptor[1:-1] # Removes the </> characters
				# 	targetFunctionAddress = globalData.standaloneFunctions[targetFunctionName][0] # RAM Address
				# 	#branchDistance = dol.calcBranchDistance( thisFunctionStartingOffset + byteOffset, targetFunctionAddress )
				# 	branchDistance = targetFunctionAddress - ( thisFunctionStartingOffset + byteOffset )

				# 	# if branchDistance == -1: # Fatal error; end the loop
				# 	# 	errorDetails = 'Unable to calculate SF branching distance, from {} to {}.'.format( hex(thisFunctionStartingOffset + byteOffset), hex(targetFunctionAddress) )
				# 	# 	break

				# else: # Must be a special branch syntax using a RAM address
				# 	# startingRamOffset = dol.offsetInRAM( thisFunctionStartingOffset + byteOffset )

				# 	# if startingRamOffset == -1: # Fatal error; end the loop
				# 	# 	errorDetails = 'Unable to determine starting RAM offset, from DOL offset {}.'.format( hex(thisFunctionStartingOffset + byteOffset) )
				# 	# 	break
				# 	#branchDistance = int( targetDescriptor, 16 ) - 0x80000000 - startingRamOffset
				# 	branchDistance = int( targetDescriptor, 16 ) - ( thisFunctionStartingOffset + byteOffset )

				# branchDistance += branchAdjustment
				branchInstruction, branchDistance = self.parseSpecialBranchSyntax( section, thisFunctionStartingOffset + byteOffset )

				# Remember in case reassembly is later determined to be required
				resolvedCodeLines.append( '{} {}'.format(branchInstruction, branchDistance) ) 

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
				resolvedCodeLines.append( section )

				# Check if this was the last section
				if i + 1 == len( customCodeSections ):
					returnCode = 100

				byteOffset += 4
				
			elif section.startswith( 'opt__' ): # Identifies configuration option placeholders
				section = section[5:]

				#optionPairs = {}
				optionData = []

				# Replace variable placeholders with the currently set option value
				# Check if this section requires assembly, and collect option names/values
				sectionChunks = section.split( '[[' )
				for j, chunk in enumerate( sectionChunks ):
					if ']]' in chunk:
						varName, chunk = chunk.split( ']]' )

						# Seek out the option name and its current value in the configurations list
						# for configuration in configurations:
						# 	if configuration['name'] == varName:
						# 		#currentValue = str( configuration['value'] )
						# 		optionData.append( (configuration['type'], configuration['value']) )
						# 		break
						# else: # Loop above didn't break; variable name not found!
						# 	return ( 4, 'Unable to find the configuration option "{}" in the mod definition.'.format(varName) )
						option = configurations.get( varName )
						if not option:
							return ( 4, 'Unable to find the configuration option "{}" in the mod definition.'.format(varName) )
						optionData.append( (option['type'], option['value']) ) # Existance of type/value already verified

						#sectionChunks[j] = chunk.replace( varName+']]', currentValue )

						# if requiresAssembly: pass
						# elif all( char in hexdigits for char in theRest.replace(' ', '') ): pass
						# else: requiresAssembly = True
						
					if requiresAssembly: pass
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
							# if type( value ) == str: # Need to typecast to int or float
							# 	if optionType == 'float':
							# 		value = float( value )
							# 	elif '0x' in value:
							# 		value = int( value, 16 )
							# 	else:
							# 		value = int( value )
							value = CodeMod.parseConfigValue( optionType, value )
							valueAsBytes = struct.pack( ConfigurationTypes[optionType], value )
							sectionChunks[j] = chunk.replace( varName+']]', hexlify(valueAsBytes) )

				# if not requiresAssembly:
				# 	sectionChunks = [ chunk.replace(' ', '') for chunk in sectionChunks ]
				resolvedCodeLines.append( ''.join(sectionChunks) )
						
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
					rawAssembly.append( resolvedCodeLines.pop(0) )
				else:
					rawAssembly.append( codeLine )

			customCode, errors = self.assemble( '\n'.join(rawAssembly), includePaths=includePaths, suppressWarnings=True )

			if errors:
				return ( 2, 'Unable to assemble source code with custom syntaxes.\n\n' + errors )

		elif requiresAssembly: # Yet the raw code is in hex form; need to assemble just the lines with custom syntax
			if debugging:
				print 'assembling custom syntaxes separately from assembled hex'

			# Assemble the resolved lines in one group (doing it this way instead of independently in the customCodeSections loop for less IPC overhead)
			assembledResolvedCode, errors = self.assemble( '\n'.join(resolvedCodeLines), beautify=True, suppressWarnings=True )
			if errors:
				return ( 3, 'Unable to assemble hex code with custom syntaxes.\n\n' + errors )

			resolvedHexCodeLines = assembledResolvedCode.split() # Split on whitespace
			newCustomCodeSections = preProcessedCustomCode.split( '|S|' ) # Need to re-split this, since customCodeSections may have been modified by now
			
			# Add the resolved, assembled custom syntaxes back into the full custom code string
			for i, section in enumerate( newCustomCodeSections ):
				if section[:5] in ( 'sbs__', 'sym__', 'opt__' ):
					newCustomCodeSections[i] = resolvedHexCodeLines.pop( 0 )
					if resolvedHexCodeLines == []: break

			customCode = ''.join( newCustomCodeSections )

		else: # Only hex should remain. Recombine the code lines back into one string. Special Branch Syntaxes have been assembled to hex
			if debugging:
				print 'resolved custom code using the preProcessedCustomCode lines'
			
			for i, section in enumerate( customCodeSections ):
				if section[:5] in ( 'sbs__', 'sym__', 'opt__' ):
					customCodeSections[i] = resolvedCodeLines.pop( 0 ).replace( ' ', '' )
					if resolvedCodeLines == []: break

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

			# Check for custom syntaxes (if one of these syntaxes is matched, it's for the whole line)
			elif CodeLibraryParser.isSpecialBranchSyntax( line ) or CodeLibraryParser.containsPointerSymbol( line ):
				continue # These will later be resolved to assembly

			elif '[[' in line and ']]' in line: # Configuration option; code before/after these may be hex or asm
				for chunk in line.split( '[[' ):
					if ']]' in chunk: # Contains a config/variable name and maybe other code
						_, chunk = chunk.split( ']]' )

						# Return True if there are any non-hex characters (meaning assembly was found)
						# if not theRest: pass # Empty string
						# elif all( char in hexdigits for char in theRest.replace(' ', '') ): # Only hex characters found
						# 	onlySpecialSyntaxes = False
						# else: # Found assembly
						# 	return True
					
					# No config/variable name in this chunk; may be asm or hex.
					# Return True if there are any non-hex characters (meaning assembly was found)
					if not chunk: pass # Empty string
					elif all( char in hexdigits for char in chunk.replace(' ', '') ): # Only hex characters found
						onlySpecialSyntaxes = False
					else: # Found assembly
						return True

				continue
			
			onlySpecialSyntaxes = False

			# Strip whitespace and check for non-hex characters
			if not validHex( ''.join(line.split()) ):
				return True

		if onlySpecialSyntaxes:
			isAssembly = True

		return isAssembly