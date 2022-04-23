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
import urlparse
import Tkinter as Tk

from string import hexdigits
from binascii import hexlify
from subprocess import Popen, PIPE
from collections import OrderedDict

# Internal Dependencies
import globalData
from basicFunctions import createFolders, removeIllegalCharacters, roundTo32, toHex, validHex, msg, printStatus
from guiSubComponents import cmsg


ConfigurationTypes = { 	'int8':   'b',	'uint8':   'B',	'mask8':   'B',
						'int16': '>h',	'uint16': '>H',	'mask16': '>H',
						'int32': '>i',	'uint32': '>I',	'mask32': '>I',
						'float': '>f' }


def regionsOverlap( regionList ):

	""" Checks selected custom code regions to make sure they do not overlap one another. """

	overlapDetected = False

	# Compare each region to every other region
	for i, ( regionStart, regionEnd, regionName ) in enumerate( regionList, start=1 ):

		# Loop over the remaining items in the list (starting from second entry on first iteration, third entry from second iteration, etc),
		# so as not to compare to itself, or make any repeated comparisons.
		for nextRegionStart, nextRegionEnd, nextRegionName in regionList[i:]:
			# Check if these two regions overlap by any amount
			if nextRegionStart < regionEnd and regionStart < nextRegionEnd: # The regions overlap by some amount.
				overlapDetected = True

				dol = globalData.disc.dol
				rS = dol.dolOffset( regionStart )
				rE = dol.dolOffset( regionEnd )
				nrs = dol.dolOffset( nextRegionStart )
				nre = dol.dolOffset( nextRegionEnd )

				# Determine the names of the overlapping regions, and report this to the user
				msg( 'Warning! One or more regions enabled for custom code overlap each other. The first overlapping areas detected '
					 'are {} and {}; i.e. (0x{:X}, 0x{:X}) and (0x{:X}, 0x{:X}). '.format( regionName, nextRegionName, rS, rE, nrs, nre ) + \
					 '(There may be more; resolve this case and try again to find others.) '
					 '\n\nThese regions cannot be used in tandem. In the Code-Space Options window, please choose other regions, '
					 'or deselect one of the regions that uses one of the areas shown above.', 'Region Overlap Detected' )
				break

		if overlapDetected: break

	return overlapDetected


class CodeChange( object ):

	""" Represents a single code change to be made to the game, such 
		as a single code injection or static (in-place) overwrite. """

	def __init__( self, mod, changeType, offset, origCode, rawCustomCode, annotation='' ):

		self.mod = mod
		self.type = changeType		# String; one of 'static', 'injection', 'standalone', or 'gecko'
		self.length = -1
		self.offset = offset		# String; may be a DOL offset or RAM address. Should be interpreted by one of the DOL normalization methods
		self.isAssembly = False
		self.syntaxInfo = []		# A list of lists. Each sub-list is of the form [ offset, length, syntaxType, codeLine, names ]
		self._origCode = origCode
		self._origCodePreprocessed = False
		self.rawCode = rawCustomCode
		self.preProcessedCode = ''
		self.processStatus = -1
		self.anno = annotation

	@property
	def origCode( self ):

		""" Original code may have been provided with the defined mod (particularly, within the MCM format), 
			however it's not expected to be available from the AMFS format. This method will retrieve it from 
			a vanilla DOL if that is available. """

		# If no original hexcode, try to get it from the vanilla disc
		if not self._origCode:
			if not self.offset:
				return ''

			# Get the DOL file
			try:
				dol = globalData.getVanillaDol()
			except Exception as err:
				printStatus( 'Unable to get DOL data; {}'.format(err.message), warning=True )
				return ''

			# Normalize the offset string, and get the target file data
			dolOffset, error = dol.normalizeDolOffset( self.offset )
			if error:
				self.mod.parsingError = True
				self.mod.errors.append( error )
				return ''

			# Determine the amount of code to get
			if self.type == 'injection':
				length = 4
			else:
				length = self.getLength()
				if length == -1 or self.processStatus != 0:
					return '' # Specific errors should have already been recorded

			# Get the DOL data as a hex string
			origData = dol.getData( dolOffset, length )
			self._origCode = hexlify( origData ).upper()

			self._origCodePreprocessed = True

		# Pre-process the original code to remove comments and whitespace
		if self._origCode and not self._origCodePreprocessed:
			filteredLines = []
			for line in self._origCode.splitlines():
				line = line.split( '#' )[0].strip()
				if not line: continue

				filteredLines.append( ''.join(line.split()) ) # Removes whitespace from this line
			filteredOriginal = ''.join( filteredLines )

			# Validate the string to make sure it's only a hex string of the game's original code
			if not validHex( filteredOriginal ):
				msg( 'Problem detected while parsing "' + self.mod.name + '" in the mod library file "'
					+ os.path.basename( self.mod.path ) + '" (index ' + str(self.mod.fileIndex+1) + '). '
					'There is an invalid (non-hex) original hex value found:\n\n' + filteredOriginal, 'Incorrect Mod Formatting (Error Code 04.2)' )
				self.mod.parsingError = True
				self.mod.errors.append( 'Invalid original hex value for code to be installed at ' + self.offset )
				self._origCode = ''
			else:
				self._origCode = filteredOriginal

			self._origCodePreprocessed = True

		return self._origCode

	@origCode.setter
	def origCode( self, code ):
		self._origCode = code
		self._origCodePreprocessed = False

	def getLength( self ):

		if self.length == -1:
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
	
	def evaluate( self, reevaluate=False ):

		""" Checks for special syntaxes and configurations, ensures configuration options are present and 
			configured correctly, and assembles source code if it's not already in hex form. Reevaluation 
			of custom code can be important if the code is changed, or the mod is saved to a new location 
			(which could potentially change import directories). """

		if not reevaluate and self.processStatus != -1:
			return self.processStatus

		#rawCustomCode = '\n'.join( customCode ).strip() # Collapses the list of collected code lines into one string, removing leading & trailing whitespace
		self.processStatus, self.length, codeOrErrorNote, self.syntaxInfo, self.isAssembly = globalData.codeProcessor.evaluateCustomCode( self.rawCode, self.mod.includePaths, self.mod.configurations )

		# if self.syntaxInfo:
		# 	processStatus, length, codeOrErrorNote2, syntaxInfo, isAssembly = globalData.codeProcessor.evaluateCustomCode( self.rawCode, self.mod.includePaths, self.mod.configurations )
		
		# 	print '\nevaluation comparison: ({})'.format( self.mod.name )
		# 	print 'status:', self.processStatus, processStatus
		# 	print 'isAssembly:', self.isAssembly, isAssembly
		# 	print 'len:', hex(self.length), hex(length)
		# 	print 'origFormat:', codeOrErrorNote
		# 	print 'newFormat :', codeOrErrorNote2
		# 	print 'origSyntaxInfo:', self.syntaxInfo
		# 	print 'newSyntaxInfo :', syntaxInfo

		# if self.isAssembly:
		# 	print self.mod.name, 'has ASM'

		if self.processStatus == 0:
			self.preProcessedCode = codeOrErrorNote

		# Store a message for the user on the cause
		elif self.processStatus == 1:
			self.mod.assemblyError = True
			if self.type == 'standalone':
				self.mod.stateDesc = 'Assembly error with SF "{}"'.format( self.offset )
				self.mod.errors.append( 'Assembly error with SF "{}":\n{}'.format(self.offset, codeOrErrorNote) )
			elif self.type == 'gecko':
				address = self.rawCustomCode.lstrip()[:8]
				self.mod.stateDesc = 'Assembly error with gecko code change at {}'.format( address )
				self.mod.errors.append( 'Assembly error with gecko code change at {}:\n{}'.format(address, codeOrErrorNote) )
			else:
				self.mod.stateDesc = 'Assembly error with custom code change at {}'.format( self.offset )
				self.mod.errors.append( 'Assembly error with custom code change at {}:\n{}'.format(self.offset, codeOrErrorNote) )
		elif self.processStatus == 2:
			self.mod.parsingError = True
			self.mod.stateDesc = 'Missing include file: {}'.format(codeOrErrorNote)
			self.mod.errors.append( 'Missing include file: {}'.format(codeOrErrorNote) )
			#self.mod.missingIncludes.append( preProcessedCustomCode ) # todo: implement a way to show these to the user (maybe warning icon & interface)
		elif self.processStatus == 3:
			self.mod.parsingError = True
			if not self.mod.configurations:
				self.mod.stateDesc = 'Unable to find configurations'
				self.mod.errors.append( 'Unable to find configurations' )
			else:
				self.mod.stateDesc = 'Configuration option not found: {}'.format(codeOrErrorNote)
				self.mod.errors.append( 'Configuration option not found: {}'.format(codeOrErrorNote) )
		elif self.processStatus == 4:
			self.mod.parsingError = True
			self.mod.stateDesc = 'Configuration option "{}" missing type parameter'.format( codeOrErrorNote )
			self.mod.errors.append( 'Configuration option "{}" missing type parameter'.format(codeOrErrorNote) )
		elif self.processStatus == 5:
			self.mod.parsingError = True
			self.mod.stateDesc = 'Unrecognized configuration option type: {}'.format(codeOrErrorNote)
			self.mod.errors.append( 'Unrecognized configuration option type: {}'.format(codeOrErrorNote) )

		if self.processStatus != 0:
			self.preProcessedCode = ''
			print( 'Error parsing code change at', self.offset, '  Error code: {}; {}'.format( self.processStatus, self.mod.stateDesc ) )

		return self.processStatus

	def finalizeCode( self, targetAddress ):

		""" Performs final code processing for custom code, just before saving it to the DOL or codes file. 
			The save location for the code as well as addresses for any standalone functions it might 
			require should already be known by this point, so custom syntaxes can now be resolved. User 
			configuration options are also now saved into the custom code. """

		self.evaluate()

		if self.mod.errors:
			msg( 'Unable to process custom code for {}; {}'.format(self.mod.name, '\n'.join(self.mod.errors)), 'Error During Pre-Processing', warning=True )
			return 5, ''

		if not self.syntaxInfo:
			returnCode = 0
			finishedCode = self.preProcessedCode
		else:
			returnCode, finishedCode = globalData.codeProcessor.resolveCustomSyntaxes2( targetAddress, self )

		if returnCode != 0 and returnCode != 100: # In cases of an error, 'finishedCode' will include specifics on the problem
			if len( self.rawCode ) > 250: # Prevent a very long user message
				codeSample = self.rawCode[:250] + '\n...'
			else:
				codeSample = self.rawCode
			errorMsg = 'Unable to process custom code for {}:\n\n{}\n\n{}'.format( self.mod.name, codeSample, finishedCode )
			msg( errorMsg, 'Error Resolving Custom Syntaxes' )
		elif not finishedCode or not validHex( finishedCode ): # Failsafe; definitely not expected
			msg( 'There was an unknown error while processing the following custom code for {}:\n\n{}'.format(self.mod.name, self.rawCode), 'Error During Final Code Processing', warning=True )
			returnCode = 6

		return returnCode, finishedCode


class CodeMod( object ):

	""" Container for all of the information on a code-related game mod. May be sourced from 
		code stored in the standard MCM format, or the newer ASM Mod Folder Structure (AMFS). """

	def __init__( self, name, auth='', desc='', srcPath='', isAmfs=False ):

		self.name = name
		self.auth = auth				# Author(s)
		self.desc = desc				# Description
		self.data = OrderedDict([])		# Keys=revision, values=list of "CodeChange" objects
		self.path = srcPath				# Root folder path that contains this mod
		self.type = 'static'
		self.state = 'disabled'
		self.category = ''
		self.stateDesc = ''				# Describes reason for the state. Shows as a text status on the mod in the GUI
		self.configurations = OrderedDict([])		# Will be a dict of option dictionaries.	  Required keys: type, value
																		# Optional keys: annotation, default, range, mask, members, hidden
		self.isAmfs = isAmfs
		self.isMini = False				# todo; replace this and above bool with a storeFormat Enum if this format is kept
		self.webLinks = []				# A list of tuples, with each of the form ( URL, comment )
		self.fileIndex = -1				# Position within a .txt file; used only with MCM formatted mods (non-AMFS)
		self.includePaths = []
		self.currentRevision = ''		# Switch this to set the default revision used to add or get code changes
		#self.guiModule = None

		self.assemblyError = False
		self.parsingError = False
		#self.missingIncludes = []		# Include filesnames detected to be required by the assembler
		self.errors = []

	# def setState( self, newState, statusText='', updateControlPanelCounts=True ):

	# 	if self.state == newState:
	# 		return

	# 	self.state = newState
	# 	try:
	# 		self.guiModule.setState( newState, statusText, updateControlPanelCounts=updateControlPanelCounts )
	# 	except:
	# 		pass # May not be currently displayed in the GUI

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

	def preProcessCustomCode( self, customCode, annotation ):

		if annotation: # Don't need to probe to get one; just make sure we have a string
			if isinstance( customCode, list ):
				customCode = '\n'.join( customCode ).strip()
		else:
			if not customCode:
				return '', ''

			# Collapse the list of collected code lines into one string, removing leading & trailing whitespace
			if isinstance( customCode, list ):
				firstLine = customCode[0]
				customCode = '\n'.join( customCode ).strip()
			else:
				firstLine = customCode.splitlines()[0]
				customCode = customCode.strip()

			if firstLine.lstrip().startswith( '#' ):
				annotation = firstLine.strip( '# ' )

		return customCode, annotation

	def addStaticOverwrite( self, offsetString, customCode, origCode='', annotation='' ):
		# Collapse the list of collected code lines into one string, removing leading & trailing whitespace
		# if isinstance( customCode, list ):
		# 	customCode = '\n'.join( customCode ).strip()
		customCode, annotation = self.preProcessCustomCode( customCode, annotation )

		# Add the code change
		codeChange = CodeChange( self, 'static', offsetString, origCode, customCode, annotation )
		self.data[self.currentRevision].append( codeChange )

		return codeChange

	def addInjection( self, offsetString, customCode, origCode='', annotation='' ):
		# Collapse the list of collected code lines into one string, removing leading & trailing whitespace
		# if isinstance( customCode, list ):
		# 	customCode = '\n'.join( customCode ).strip()
		customCode, annotation = self.preProcessCustomCode( customCode, annotation )

		# Add the code change
		codeChange = CodeChange( self, 'injection', offsetString, origCode, customCode, annotation )
		self.data[self.currentRevision].append( codeChange )

		if self.type == 'static': # 'static' is the only type that 'injection' can override.
			self.type = 'injection'

		return codeChange

	def addGecko( self, customCode, annotation='' ):

		""" This is for Gecko codes that could not be converted into strictly static 
			overwrites and/or injection mods. These will require the Gecko codehandler. """
			
		# Collapse the list of collected code lines into one string, removing leading & trailing whitespace
		# if isinstance( customCode, list ):
		# 	customCode = '\n'.join( customCode ).strip()
		customCode, annotation = self.preProcessCustomCode( customCode, annotation )

		# Add the code change
		codeChange = CodeChange( self, 'gecko', '', '', customCode, annotation )
		self.data[self.currentRevision].append( codeChange )

		self.type = 'gecko'

		return codeChange

	def addStandalone( self, standaloneName, standaloneRevisions, customCode, annotation='' ):
		# Collapse the list of collected code lines into one string, removing leading & trailing whitespace
		# if isinstance( customCode, list ):
		# 	customCode = '\n'.join( customCode ).strip()
		customCode, annotation = self.preProcessCustomCode( customCode, annotation )

		# Add the code change for each revision that it was defined for
		codeChange = CodeChange( self, 'standalone', standaloneName, '', customCode, annotation )
		for revision in standaloneRevisions:
			if revision not in self.data:
				self.data[revision] = []
			self.data[revision].append( codeChange )

		codeChange.evaluate()

		# Save this SF in the global dictionary
		if codeChange.processStatus == 0 and standaloneName not in globalData.standaloneFunctions:
			globalData.standaloneFunctions[standaloneName] = ( -1, codeChange )

		self.type = 'standalone'

		return codeChange

	def _parseCodeForStandalones( self, codeChange, requiredFunctions, missingFunctions ):

		""" Recursive helper function for getRequiredStandaloneFunctionNames(). Checks 
			one particular code change (injection/overwrite) for standalone functions. """

		for syntaxOffset, length, syntaxType, codeLine, names in codeChange.syntaxInfo:

			if syntaxType == 'sbs' and '<' in codeLine and '>' in codeLine: # Special Branch Syntax; one name expected
				newFunctionNames = ( codeLine.split( '<' )[1].split( '>' )[0], ) # Second split prevents capturing comments following on the same line.

			elif syntaxType == 'sym': # These lines could have multiple names
				newFunctionNames = []
				for fragment in codeLine.split( '<<' ):
					if '>>' in fragment: # A symbol (function name) is in this string segment.
						newFunctionNames.append( fragment.split( '>>' )[0] )
			else: continue

			for functionName in newFunctionNames:
				# Skip this function if it has already been analyzed
				if functionName in requiredFunctions:
					continue

				requiredFunctions.append( functionName )

				# Recursively check for more functions that this function may reference
				functionMapping = globalData.standaloneFunctions.get( functionName )
				if functionMapping:
					codeChange = functionMapping[1] # First item is function address (if allocated; -1 if not)
					self._parseCodeForStandalones( codeChange, requiredFunctions, missingFunctions )
				elif functionName not in missingFunctions:
					missingFunctions.append( functionName )

		return requiredFunctions, missingFunctions

	def getRequiredStandaloneFunctionNames( self ):
		
		""" Gets the names of all standalone functions a particular mod requires. 
			Returns a list of these function names, as well as a list of any missing functions. """

		functionNames = []
		missingFunctions = []

		# This loop will be over a list of tuples (code changes) for a specific game version.
		for codeChange in self.getCodeChanges():
			if codeChange.type != 'gecko': #todo allow gecko codes to have SFs
				codeChange.evaluate()
				if codeChange.syntaxInfo:
					self._parseCodeForStandalones( codeChange, functionNames, missingFunctions )

		return functionNames, missingFunctions # functionNames will also include those that are missing

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
		# 		return option
		# else:
		# 	raise Exception( '{} not found in configuration options.'.format(name) )

		return self.configurations[name]

	def getConfigValue( self, name ):
		return self.configurations[name]['value']

	@staticmethod
	def parseConfigValue( optionType, value ):

		""" Normalizes value input that may be a hex/decimal string or an int/float literal
			to an int or float. The source value type may not be consistent due to
			varying sources (i.e. from an MCM format file or AMFS config/json file). """

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

	def assembleErrorMessage( self, includeStateDesc=False ):
		
		errorMsg = []

		if includeStateDesc:
			errorMsg.append( self.stateDesc + '\n' )

		if self.parsingError:
			errorMsg.append( 'Parsing Errors Detected: Yes' )
		else:
			errorMsg.append( 'Parsing Errors Detected: No' )

		if self.assemblyError:
			errorMsg.append( 'Assembly Errors Detected: Yes\n' )
		else:
			errorMsg.append( 'Assembly Errors Detected: No\n' )
		
		errorMsg.extend( self.errors )

		return '\n'.join( errorMsg )

	def validateWebLink( self, origUrlString ):

		""" Validates a given URL (string), partly based on a whitelist of allowed domains. 
			Returns a urlparse object if the url is valid, or None (Python default) if it isn't. """

		try:
			potentialLink = urlparse.urlparse( origUrlString )
		except Exception as err:
			print( 'Invalid link detected for "{}": {}'.format(self.name, err) )
			return

		# Check the domain against the whitelist. netloc will be something like "youtube.com" or "www.youtube.com"
		if potentialLink.scheme and potentialLink.netloc.split('.')[-2] in ( 'smashboards', 'github', 'youtube' ):
			return potentialLink

		elif not potentialLink.scheme:
			print( 'Invalid link detected for "{}" (no scheme): {}'.format(self.name, origUrlString) )
		else:
			print( 'Invalid link detected for "{}" (domain not allowed): {}'.format(self.name, origUrlString) )

	def buildModString( self, reevaluateCodeChanges=False ):

		""" Builds a string to store/share this mod in MCM's normal code format. 
			If this mod is a Gecko code, this method will create a MCM-Gecko format string that is
			a slight variant of a normal Gecko code (as one would see in a Dolphin INI file). This 
			variant exists so that a Gecko code may have several variants for different revisions. """

		# Collect lines for title, description, and web links
		if self.name:
			headerLines = [ self.name ]
		else:
			headerLines = [ 'This Mod Needs a Title!' ]
		if self.desc:
			headerLines.append( self.desc )
		if self.webLinks:
			for urlString, comments in self.webLinks: # Comments should still have the '#' character prepended
				if not comments:
					headerLines.append( '<{}>'.format(urlString) )
				elif comments.lstrip()[0] == '#':
					headerLines.append( '<{}>{}'.format(urlString, comments) )
				else:
					headerLines.append( '<{}> # {}'.format(urlString, comments) )

		# Add configuration definitions
		if self.configurations:
			headerLines.append( 'Configurations:' )

			for name, definition in self.configurations.items(): # ConfigurationTypes
				# Collect optional keys
				comment = definition.get( 'annotation', '' )
				valueRange = definition.get( 'range', '' )
				mask = definition.get( 'mask', '' )
				members = definition.get( 'members', '' )

				titleLine = '    {} {} = {}'.format( definition['type'], name, definition['value'] ) # Current value will be set as default!

				if valueRange:
					titleLine += '; {}-{}'.format( valueRange[0], valueRange[1] )
				elif mask:
					titleLine += ' (0x{:X})'.format( mask )

				if comment:
					titleLine += ' ' + comment.lstrip()
				headerLines.append( titleLine )
				
				for components in members:
					if len( components ) == 2:
						name, value = components
						headerLines.append( '        {}: {}'.format(value, name) )
					else:
						name, value, comment = components
						headerLines.append( '        {}: {} {}'.format(value, name, comment.lstrip()) )
		
		if self.auth:
			headerLines.append( '[' + self.auth + ']' )
		else:
			headerLines.append( '[??]' )

		codeChangesHeader = 'Revision ---- DOL Offset ---- Hex to Replace ---------- ASM Code -'
		addChangesHeader = False
		codeChangeLines = []

		for revision, codeChanges in self.data.items():
			addVersionHeader = True

			for change in codeChanges:
				# newHex = change.rawCode
				# if newHex.startswith( '0x' ):
				# 	newHex = newHex[2:] # Don't want to replace all instances
				newHex = change.rawCode.strip()
				if not newHex:
					continue

				if change.type in ( 'static', 'injection' ):
					change.evaluate( reevaluateCodeChanges )
					addChangesHeader = True
				
					# Get the offset
					if change.offset:
						offset = change.offset.replace( '0x', '' )
					else:
						offset = '1234' # Placeholder; needed so the mod can still be parsed/re-loaded

					# Get the original hex (vanilla game code)
					if change.origCode:
						originalHex = ''.join( change.origCode.split() ).replace( '0x', '' )
						if not validHex( originalHex ):
							msg( 'There is missing or invalid Original Hex code\nfor some ' + revision + ' changes.' )
							return ''
					else:
						codeLength = change.getLength()
						if codeLength == -1:
							originalHex = '00000000' # Placeholder
						else:
							originalHex = '00' * codeLength

					# Create the beginning of the line (revision header, if needed, with dashes).
					headerLength = 13
					if addVersionHeader:
						lineHeader = revision + ' ' + ('-' * ( headerLength - 1 - len(revision) )) # extra '- 1' for the space after revision
						addVersionHeader = False
					else: lineHeader = '-' * headerLength

					# Build a string for the offset portion
					numOfDashes = 8 - len( offset )
					dashes = '-' * ( numOfDashes / 2 ) # if numOfDashes is 1 or less (including negatives), this will be an empty string
					if numOfDashes % 2 == 0: # If the number of dashes left over is even (0 is even)
						offsetString = dashes + ' ' + '0x' + offset + ' ' + dashes
					else: # Add an extra dash at the end (the int division above rounds down)
						offsetString = dashes + ' ' + '0x' + offset + ' ' + dashes + '-'

					# Build a string for a standard (short) static overwrite
					if change.type == 'static' and len( originalHex ) <= 16 and newHex.splitlines()[0].split('#')[0] != '': # Last check ensures there's actually code, and not just comments/whitespace
						codeChangeLines.append( lineHeader + offsetString + '---- ' + originalHex + ' -> ' + newHex )

					# Long static overwrite
					elif change.type == 'static':
						prettyHex = globalData.codeProcessor.beautifyHex( originalHex )
						codeChangeLines.append( lineHeader + offsetString + '----\n\n' + prettyHex + '\n\n -> \n\n' + newHex + '\n' )

					# Injection mod
					else:
						codeChangeLines.append( lineHeader + offsetString + '---- ' + originalHex + ' -> Branch\n\n' + newHex + '\n' )

				elif change.type == 'gecko':
					if addVersionHeader: codeChangeLines.append( revision + '\n' + newHex + '\n' )
					else: codeChangeLines.append( newHex + '\n' )

				elif change.type == 'standalone':
					functionName = change.offset

					# Check that a function name was given, and then convert the ASM to hex if necessary.
					if functionName == '':
						msg( 'A standalone function among the ' + revision + ' changes is missing a name.' )
						return ''
					elif ' ' in functionName:
						msg( 'Function names may not contain spaces. Please rename those for ' + revision + ' and try again.' )
						return ''

					# Add the name wrapper and version identifier
					functionName = '<' + functionName + '> ' + revision

					# Assemble the line string with the original and new hex codes.
					codeChangeLines.append( functionName + '\n' + newHex + '\n' )
					
		if addChangesHeader:
			headerLines.append( codeChangesHeader )

		return '\n'.join( headerLines + codeChangeLines )

	def formatAsGecko( self, vanillaDol, createForGCT ):

		""" Formats a mod's code into Gecko code form. Note that this is the 'true' or original Gecko code format
			(as Dolphin would use), not the MCM-Gecko variant. If this is for an INI file, human-readable mod-name/author headers and 
			whitespace are included. If this is for a GCT file, it'll just be pure hex data (though returned as a string). """

		containsSpecialSyntax = False
		codeChanges = []

		for codeChange in self.data[vanillaDol.revision]:
			codeChange.evaluate() # Ensure code length has been determined

			# Check for special syntaxes; only one kind can be adapted for use by Gecko codes (references to SFs)
			if codeChange.syntaxInfo or codeChange.type == 'standalone': # Not supported for Gecko codes
				containsSpecialSyntax = True
				break
			
			elif codeChange.type == 'static':
				
				# Determine the Gecko operation code
				if codeChange.length == 1:
					opCode = 0
					filling = '000000'
				elif codeChange.length == 2:
					opCode = 2
					filling = '0000'
				elif codeChange.length == 4:
					opCode = 4
					filling = ''
				else:
					opCode = 6
					filling = toHex( codeChange.length, 8 ) # Pads a hex string to 8 characters long (extra characters added to left side)

				ramAddress = vanillaDol.normalizeRamAddress( codeChange.offset )[0]
				if ramAddress > 0x81000000:
					opCode += 1
				
				ramAddress = ramAddress & 0x1FFFFFF # Mask out base address
				firstWord = '{:02X}{:06X}'.format( opCode, ramAddress )

				if createForGCT:
					codeChanges.append( firstWord + filling + codeChange.preProcessedCode )

				elif codeChange.length > 4:
					sByteCount = toHex( codeChange.length, 8 ) # Pads a hex string to 8 characters long (extra characters added to left side)
					beautifiedHex = globalData.codeProcessor.beautifyHex( codeChange.preProcessedCode )
					codeChanges.append( firstWord + ' ' + sByteCount + '\n' + beautifiedHex )
				else:
					codeChanges.append( firstWord + ' ' + filling + codeChange.preProcessedCode )

			elif codeChange.type == 'injection':
				opCode = codeChange.preProcessedCode[-8:][:-6].lower() # Of the last instruction
				ramAddress = vanillaDol.normalizeRamAddress( codeChange.offset )[0]
				sRamAddress = toHex( ramAddress, 6 ) # Pads a hex string to 6 characters long (extra characters added to left side)
				
				# todo: +1 to opcode if address > 0x81000000
				# if ramAddress > 0x81000000:
				# 	opCode += 1

				if createForGCT:
					# Check the last instruction; it may be a branch placeholder, which may be removed
					if opCode in ( '48', '49', '4a', '4b', '00' ):
						codeChange.preProcessedCode = codeChange.preProcessedCode[:-8]
						codeChange.length -= 4

					# Determine the line count and the final bytes that need to be appended
					quotient, remainder = divmod( codeChange.length, 8 ) # 8 = the final bytes per line
					sLineCount = toHex( quotient + 1, 8 )
					if remainder == 0: # The remainder is how many bytes extra there will be after the 'quotient' number of lines above
						codeChange.preProcessedCode += '6000000000000000'
					else:
						codeChange.preProcessedCode += '00000000'

					codeChanges.append( 'C2{}{}{}'.format(sRamAddress, sLineCount, codeChange.preProcessedCode) )

				else: # Creating a human-readable INI file
					# Check the last instruction; it may be a branch placeholder, which may be removed
					if opCode in ( '48', '49', '4a', '4b', '00' ):
						beautifiedHex = globalData.codeProcessor.beautifyHex( codeChange.preProcessedCode[:-8] )
						codeChange.length -= 4
					else:
						beautifiedHex = globalData.codeProcessor.beautifyHex( codeChange.preProcessedCode )

					# Determine the line count and the final bytes that need to be appended
					quotient, remainder = divmod( codeChange.length, 8 ) # 8 represents the final bytes per line
					sLineCount = toHex( quotient + 1, 8 )
					if remainder == 0: # The remainder is how many bytes extra there will be after the 'quotient' number of lines above
						beautifiedHex += '\n60000000 00000000'
					else:
						beautifiedHex += ' 00000000'

					codeChanges.append( 'C2{} {}\n{}'.format(sRamAddress, sLineCount, beautifiedHex ) )

			elif codeChange.type == 'gecko': # Not much going to be needed here!
				if createForGCT:
					codeChanges.append( codeChange.preProcessedCode )
				else: # Creating a human-readable INI file
					codeChanges.append( globalData.codeProcessor.beautifyHex( codeChange.preProcessedCode ) )

		if containsSpecialSyntax:
			return ''
		elif createForGCT:
			return ''.join( codeChanges )
		else:
			return '${} [{}]\n{}'.format( self.name, self.auth, '\n'.join(codeChanges) )

	def saveInGeckoFormat( self, savePath ):

		codeString = self.formatAsGecko( globalData.getVanillaDol(), False )
		if not codeString:
			return False

		try:
			with open( savePath, 'a' ) as geckoFile:
				geckoFile.write( codeString )
		except:
			return False

		return True

	def saveInMcmFormat( self, savePath='', showErrors=True ):

		""" Saves this mod to a text file in MCM's basic mod format. 
			If the given file path already contains mods, the mod of the
			current index (self.fileIndex) will be replaced. Or, if the 
			current index is -1, this mod will be added to the end of it. """
		
		# Set this mod's save location so that subsequent saves will automatically go to this same place
		# Do this first in any case, in case this method fails
		self.isAmfs = False
		if savePath:
			self.path = savePath

		# Rebuild the include paths list, using this new file for one of the paths
		modsFolderIncludePath = os.path.join( globalData.getModsFolderPath(), '.include' )
		rootFolderIncludePath = os.path.join( globalData.scriptHomeFolder, '.include' )
		self.includePaths = [ os.path.dirname(self.path), modsFolderIncludePath, rootFolderIncludePath ]

		# Append this mod to the end of the target Mod Library text file (could be a new file, or an existing one).
		try:
			modString = self.buildModString( reevaluateCodeChanges=True )

			try:
				# Get contents of an existing file
				with open( self.path, 'r' ) as modFile:
					fileContents = modFile.read()
					
				if fileContents and self.fileIndex == -1: # Add to the end of the file
					# Get the file index for this mod and prepend a separator
					self.fileIndex = len( fileContents.split( '-==-' ) )
					modString = fileContents + '\n\n\n\t-==-\n\n\n' + modString

				elif fileContents: # Replace the given index
					mods = fileContents.split( '-==-' )
					
					# Replace the old mod, reformat the space in-between mods, and recombine the file's text.
					mods[self.fileIndex] = modString
					mods = [code.strip() for code in mods] # Removes the extra whitespace around mod strings.
					modString = '\n\n\n\t-==-\n\n\n'.join( mods )
				else:
					self.fileIndex = 0

				# Save the mod to the file.
				with open( self.path, 'w' ) as modFile:
					modFile.write( modString )

			except IOError: # The file doesn't exist
				# Open in append mode to create a new one
				with open( self.path, 'a' ) as modFile:
					modFile.write( modString )
				self.fileIndex = 0

		except Exception as err:
			print( 'Unable to save {} in MCM format; {}'.format(self.name, err) )
			if showErrors:
				msg( 'Unable to save {} in MCM format; {}'.format(self.name, err), 'Unable to save!', error=True )

			return False

		return True

	def saveInAmfsFormat( self, savePath='' ):

		""" Saves this mod to a text file in the ASM Mod Folder Structure (AMFS) format. """

		# Set this mod's save location so that subsequent saves will automatically go to this same place
		# Do this first in any case, in case this method fails
		self.isAmfs = True
		self.fileIndex = -1
		if savePath:
			self.path = savePath

		# Rebuild the include paths list, using this new file for one of the paths
		modsFolderIncludePath = os.path.join( globalData.getModsFolderPath(), '.include' )
		rootFolderIncludePath = os.path.join( globalData.scriptHomeFolder, '.include' )
		self.includePaths = [ self.path, modsFolderIncludePath, rootFolderIncludePath ]

		# Create the folder(s) if it doesn't exist
		createFolders( self.path )

		# Build the JSON file data
		jsonData = {
			'codes': [
				{
					'name': self.name,
					'authors': [name.strip() for name in self.auth.split(',') ],
					'description': self.desc.splitlines(),
					'category': self.category,
					'build': []
				}
			]
		}
		
		# Add configuration definitions if present
		if self.configurations:
			jsonData['codes'][0]['configurations'] = self.configurations

		# Set an overall revision if there are only changes for one available
		if len( self.data ) == 1:
			jsonData['codes'][0]['revision'] = self.data.keys()[0]

		# Add web links
		if self.webLinks:
			jsonData['codes'][0]['webLinks'] = []
			for item in self.webLinks:
				jsonData['codes'][0]['webLinks'].append( item )

		# Build the list of code change dictionaries
		for revision, changes in self.data.items():
			for change in changes:
				change.evaluate( reevaluate=True )
				changeDict = {}
				
				# Check for a simple annotation to add
				#annotation = ''
				#newHex = change.rawCode.strip()
				# if newHex.startswith( '0x' ):
				# 	newHex = newHex[2:] # Don't want to replace all instances
				# if newHex:
				# 	annotation, newHex = self.splitAnnotation( newHex )
				# 	if annotation:
				# 		changeDict['annotation'] = annotation
				if change.anno:
					changeDict['annotation'] = change.anno
				
				if change.type == 'static' and change.length <= 16: # Standard (Short) Static Overwrite
					changeDict['type'] = 'replace'
					changeDict['address'] = change.offset
					changeDict['value'] = change.rawCode.strip()
					addSourceFile = False

				elif change.type == 'static': # Long Static Overwrite
					changeDict['type'] = 'replaceCodeBlock'
					changeDict['address'] = change.offset
					addSourceFile = True

				elif change.type == 'injection': # Code Injection
					changeDict['type'] = 'inject'
					changeDict['address'] = change.offset
					addSourceFile = True

				elif change.type == 'standalone': # Standalone Function
					changeDict['type'] = 'standalone'
					changeDict['name'] = change.offset
					addSourceFile = True

				# elif change.type == 'gecko': # Gecko Codes
				# 	changeDict['type'] = 'gecko'
				# 	addSourceFile = True

				else: # Failsafe; shouldn't happen
					print( 'AMFS save method encountered an unexpected change type: ' + change.type )
					continue

				if addSourceFile:
					# Create a file name for the assembly or bin file
					fileName = self.filenameForChange( change )
					sourcePath = os.path.join( self.path, fileName ) # No extension

					# Create the file(s)
					success = self.writeCustomCodeFiles( change, sourcePath )
					if not success:
						continue

					changeDict['sourceFile'] = sourcePath + '.asm'

				# Add a revision if dealing with multiple of them
				if len( self.data ) > 1:
					changeDict['revision'] = revision

				#buildList.append( changeDict )
				jsonData['codes'][0]['build'].append( changeDict )

		# Save the codes.json file
		try:
			jsonPath = os.path.join( self.path, 'codes.json' )
			with open( jsonPath, 'w' ) as jsonFile:
				json.dump( jsonData, jsonFile, indent=4 )
		except Exception as err:
			print( 'Unable to create "codes.json" file; ' )
			print( err )
			return False

		return True

	def writeCustomCodeFiles( self, change, sourcePath, longHeader=False ):

		""" An assembly (.asm) file should be saved if the custom code is assembly, or 
			the code could not be pre-processed. Successfully pre-processed code may have 
			custom syntax still within it, in which case it is saved to a text file. Or it 
			is saved to a binary file if it is finished, purely-hex data. If longHeader is 
			True, it's assumed the file header (and the assembly file itself) are both required. 
			And if the assembly file is created but the custom code within it is raw hex, 
			there is no need to create the binary file. """

		if longHeader:
			header = ( '####################################\n'
					   '# Address: ' + change.offset + '\n'
					   '# Author: ' + self.auth + '\n'
					   '####################################\n\n' )
		else:
			header = '# To be inserted at ' + change.offset + '\n\n'

		# Check if the original source code should be saved
		saveSource = False
		if change.isAssembly or not change.preProcessedCode:
			saveSource = True
		else:
			# Check if there are any comments that would be lost
			for line in change.rawCode:
				if '#' in line:
					saveSource = True
					break

		# Create a source file for this custom code
		if saveSource:
			try:
				with open( sourcePath + '.asm', 'w' ) as sourceFile:
					sourceFile.write( header )
					sourceFile.write( change.rawCode.strip() )
			except Exception as err:
				print( 'Unable to create "' + sourcePath + '.asm"' )
				print( err )
				return False
		
		# Save successfully assembled code (if custom syntax isn't required)
		if change.preProcessedCode:
			if change.syntaxInfo: # Contains custom syntax; cannot yet be fully assembled
				# Save a text file with the pre-processed code
				try:
					with open( sourcePath + '.txt', 'w' ) as sourceFile:
						sourceFile.write( header )
						sourceFile.write( change.preProcessedCode )
				except Exception as err:
					print( 'Unable to create "' + sourcePath + '.txt"' )
					print( err )
					return False
			elif not longHeader:
				# Save a binary file with just hex data
				try:
					binData = bytearray.fromhex( change.preProcessedCode )
					with open( sourcePath + '.bin', 'wb' ) as sourceFile:
						sourceFile.write( binData )
				except Exception as err:
					print( 'Unable to create "' + sourcePath + '.bin"' )
					print( err )
					return False

		return True

	def miniFormatSupported( self ):

		changes = self.data.values()[0]

		if not self.name:
			return False, 'Unable to save this mod with no name!'
		elif len( self.data ) != 1:
			return False, 'Unsupported number of revision changes to save as standalone file.'
		elif len( changes ) != 1:
			return False, 'Unsupported number of code changes to save as standalone file.'
		elif self.configurations:
			return False, 'Configurations unsupported with standalone SO/IM file.'
		else:
			return True, ''

	def saveAsStandaloneFile( self ):

		""" Saves this mod as a single static overwrite or injection. 
			Does not support multiple revisions/changes or configurations. """

		# Get the lists of code changes for each revision
		revisions = self.data.values()
		assert len( revisions ) == 1, 'Invalid number of revisions for saving as a standalone file: ' + str( len(revisions) )

		# Get the code changes
		changes = revisions[0]
		assert len( changes ) == 1, 'Invalid number of changes for saving as a standalone file: ' + str( len(changes) )

		# Create the source and/or binary files
		return self.writeCustomCodeFiles( changes[0], os.path.splitext(self.path)[0], True )

	# def splitAnnotation( self, customCode ):

	# 	""" Check for a comment on the first line of the custom code, 
	# 		and if present, use that for the annotation. """

	# 	newHex = customCode.strip().splitlines()
	# 	firstLine = newHex[0]

	# 	if '#' in firstLine:
	# 		if firstLine.startswith( '#' ):
	# 			annotation = firstLine.lstrip( '# ' )
	# 			newHex = '\n'.join( newHex[1:] )
	# 		else:
	# 			newHex[0], annotation = firstLine.split( '#' )
	# 			annotation = annotation.lstrip()
	# 			newHex = '\n'.join( newHex )
	# 	else:
	# 		annotation = ''
	# 		newHex = customCode

	# 	return annotation, newHex

	def filenameForChange( self, change ):

		""" Creates a file name from the annotation, removing illegal 
			characters. Or, if an annotation is not available, creates 
			one based on the change type and address of the code change. 
			The file extension is not included. """

		cType = change.type
		address = change.offset
		anno = change.anno

		if anno:
			if len( anno ) > 42:
				name = anno[:39] + '...'
			elif anno:
				name = anno

			name = removeIllegalCharacters( name, '' )

		else: # No annotation available
			if cType == 'static':
				name = 'Static overwrite at {}'.format( address )
			elif cType == 'injection':
				name = 'Code injection at {}'.format( address )
			elif cType == 'standalone':
				name = "SA, '{}'".format( address )
			else:
				name = 'Unknown code change at {}'.format( address )

		return name


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
		self.includePaths = []
		self.modNames = set()
		self.codeMods = []

	def processDirectory( self, folderPath ):

		""" Starting point for processing a Code Library. Recursively processes sub-folders. """

		parentFolderPath, thisFolderName = os.path.split( folderPath )
		parentFolderName = os.path.split( parentFolderPath )[1]
		itemsInDir = os.listdir( folderPath ) # May be files or folders
		includePaths = [ folderPath ] + self.includePaths

		# Check if this folder is a mod in AMFS format
		if 'codes.json' in itemsInDir:
			self.parseAmfs( folderPath, includePaths, parentFolderName )
			return

		# Check if there are any items in this folder to be processed exclusively (item starting with '+')
		for item in itemsInDir:
			if item.startswith( '+' ):
				itemsInDir = [ item ]
				break

		for item in itemsInDir:
			if self.stopToRescan:
				break
			elif item.startswith( '!' ) or item.startswith( '.' ):
				continue # User can optionally exclude these folders from parsing
			
			itemPath = os.path.normpath( os.path.join(folderPath, item) )
			ext = os.path.splitext( item )[1].lower()

			# Process sub-folders. Recursive fun!
			if os.path.isdir( itemPath ):
				self.processDirectory( itemPath )

			# Process MCM format files
			elif ext == '.txt':
				# Collect all mod definitions from this file
				self.parseModsLibraryFile( itemPath, includePaths )

			# Process standalone .asm/.s files as their own mod
			elif ext == '.asm':
				self.parseMinimalFormatInjection( item, itemPath, includePaths, thisFolderName )
			elif ext == '.s':
				self.parseMinimalFormatOverwrite( item, itemPath, includePaths, thisFolderName )

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
	def containsConfiguration( codeLine ):

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

		category = os.path.basename( filepath )[:-4]

		# Open the text file and get its contents, creating a list of raw chunks of text for each mod
		with open( filepath, 'r' ) as modFile:
			mods = modFile.read().split( '-==-' )

		# Parse each chunk of text for each mod, to get its info and code changes
		for fileIndex, modString in enumerate( mods ):

			if modString.strip() == '' or modString.lstrip()[0] == '!':
				continue # Skip this mod.
			elif self.stopToRescan:
				break
			
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
			configurationDict = {}
			configurationName = ''

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
							mod.name = line
						continue # Also skip further processing of empty strings if the name hasn't been set yet
						
					if line.startswith( '<' ) and line.endswith( '>' ):
						potentialLink = line[1:-1].replace( '"', '' ) # Removes beginning/ending angle brackets and double quotes
						mod.webLinks.append( (potentialLink, lineComments) ) # Will be validated on GUI creation

					elif line.startswith( '[' ) and line.endswith( ']' ):
						mod.auth = line.split(']')[0].replace( '[', '' )
						basicInfoCollected = True
						collectingConfigurations = False
						
						if configurationDict:
							#mod.configurations.append( configurationDict )
							mod.configurations[configurationName] = configurationDict

					elif line.lower().startswith( 'configurations:' ):
						collectingConfigurations = True

					elif collectingConfigurations:
						try:
							if '=' in line: # name/type header for a new option
								# Store a previously collected option
								if configurationDict:
									mod.configurations[configurationName] = configurationDict

								# Parse out the option name and type
								typeName, valueInfo = line.split( '=' )
								typeNameParts = typeName.split() # Splitting on whitespace
								configurationDict = {}
								configurationName = ' '.join( typeNameParts[1:] )
								configurationDict['type'] = typeNameParts[0]

								# Validate the type
								if configurationDict['type'] not in ConfigurationTypes:
									raise Exception( 'unsupported option type' )

								# Check for and parse value ranges
								if ';' in valueInfo:
									# Separate the default value and range
									defaultValue, rangeString = valueInfo.split( ';' )
									defaultValue = defaultValue.strip()

									# Parse range
									if '-' not in rangeString:
										raise Exception( 'No "-" separator in range string' )
									start, end = rangeString.split( '-' )
									configurationDict['range'] = ( start, end )

								elif '(' in valueInfo: # A mask is present
									valueInfo, maskInfo = valueInfo.split( '(' )
									if valueInfo.strip():
										defaultValue = valueInfo.strip()
									else:
										defaultValue = '0'
									configurationDict['mask'] = int( maskInfo.replace(')', ''), 16 )

								elif valueInfo.strip():
									defaultValue = valueInfo.strip()

								else:
									defaultValue = '0'

								configurationDict['default'] = defaultValue
								configurationDict['value'] = defaultValue
								configurationDict['annotation'] = lineComments

							# Process enumerations/members of an existing option
							elif configurationDict and ':' in line:
								# Add the members list if not already present
								members = configurationDict.get( 'members' )
								if not members:
									configurationDict['members'] = []

								# Save the name, value, and comment from this line
								value, name = line.split( ':' )
								# if '0x' in value:
								# 	value = int( value, 16 )
								# else:
								# 	value = int( value )
								configurationDict['members'].append( [name.strip(), value.strip(), lineComments] )

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

						elif totalValues > 2: # Could be a standard static overwrite (1-liner), long static overwrite, or an injection mod
							origHex = ''.join( hexCodes[1].replace('0x', '').split() ) # Remove whitespace
							newHex = hexCodes[2]

							if newHex.lower() == 'branch':
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

	def parseMinimalFormatOverwrite( self, item, sourceFile, includePaths, category ):

		""" Creates a mod from a single, standalone .s file. """

		# Create the mod object
		modName = os.path.splitext( item )[0].strip() # i.e. filename without extension
		mod = CodeMod( modName, 'TBD', '', sourceFile, True )
		mod.isMini = True
		mod.setCurrentRevision( 'NTSC 1.02' ) # Assumption time #todo (optionally add param to header)
		mod.desc = 'Static overwrite from standalone file "{}"'.format( sourceFile )
		mod.includePaths = includePaths
		mod.category = category
		
		# Read the file for info and the custom code
		returnCode, address, author, customCode, anno = self.getCustomCodeFromFile( sourceFile, mod, True, modName )

		if author:
			mod.auth = author

		# Check for errors
		if returnCode == 0 and not address:
			mod.parsingError = True
			mod.stateDesc = 'Missing address for "{}"'.format( sourceFile )
			mod.errors.append( 'Unable to find an address' )

		mod.addStaticOverwrite( address, customCode, '', anno )
		self.storeMod( mod )

	def parseMinimalFormatInjection( self, item, sourceFile, includePaths, category ):

		""" Creates a mod from a single, standalone .asm file. """

		# Create the mod object
		modName = os.path.splitext( item )[0].strip() # i.e. filename without extension
		mod = CodeMod( modName, 'TBD', '', sourceFile, True )
		mod.isMini = True
		mod.setCurrentRevision( 'NTSC 1.02' ) # Assumption time #todo (optionally add param to header)
		mod.desc = 'Injection from standalone file "{}"'.format( sourceFile )
		mod.includePaths = includePaths
		mod.category = category
		
		# Read the file for info and the custom code
		returnCode, address, author, customCode, anno = self.getCustomCodeFromFile( sourceFile, mod, True, modName )

		if author:
			mod.auth = author

		# Check for errors
		if returnCode == 0 and not address:
			mod.parsingError = True
			mod.stateDesc = 'Missing address for "{}"'.format( sourceFile )
			mod.errors.append( 'Unable to find an address' )
			
		mod.addInjection( address, customCode, '', anno )
		self.storeMod( mod )

	def storeMod( self, mod ):

		""" Store the given mod, and perfom some basic validation on it. """
		
		if not mod.data:
			mod.state = 'unavailable'
			mod.stateDesc = 'Missing mod data'
			mod.errors.append( 'Missing mod data; may be defined incorrectly' )
		elif mod.name in self.modNames:
			mod.state = 'unavailable'
			mod.stateDesc = 'Duplicate mod'
			mod.errors.append( 'Duplicate mod; more than one by this name in library' )

		self.codeMods.append( mod )
		self.modNames.add( mod.name )

	def parseGeckoCode( self, codeLines ):

		""" Currently only supports Gecko code types 04, 06, and C2. Returns title, newAuthors, 
			description, and codeChanges. 'codeChanges' will be a list of tuples, with each 
			tuple of the form ( changeType, address, customCodeLines ). """

		title = authors = ''
		description = []
		codeChangeTuples = []
		codeBuffer = [ '', -1, '', [], 0 ] # Temp staging area while code lines are collected, before they are submitted to the above codeChangeTuples list.

		# Load the DOL for this revision (if one is not already loaded), for original/vanilla code look-ups
		#vanillaDol = loadVanillaDol( gameRevision )

		for line in codeLines:
			if not line.strip(): continue # Skip whitespace lines

			elif line.startswith( '*' ): # Another form of comment
				description.append( line[1:] )

			elif line.startswith( '$' ) or ( '[' in line and ']' in line ):
				line = line.lstrip( '$' )

				# Sanity check; the buffer should be empty if a new code is starting
				if codeBuffer[0]:
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

			elif codeBuffer[0]: # Multi-line code collection is in-progress
				changeType, totalBytes, ramAddress, _, collectedCodeLength = codeBuffer

				processedHex = ''.join( line.split( '#' )[0].split() ) # Should remove all comments and whitespace
				newHexLength = len( processedHex ) / 2 # Divide by 2 to count by bytes rather than nibbles

				if collectedCodeLength + newHexLength < totalBytes:
					#codeBuffer[3].append( processedHex )
					codeBuffer[3].append( line )
					codeBuffer[4] += newHexLength

				else: # Last line to collect from for this code change
					# Collect the remaining new hex and consolidate it
					#bytesRemaining = totalBytes - collectedCodeLength
					codeBuffer[3].append( line )
					#codeBuffer[3].append( processedHex[:bytesRemaining*2] ) # x2 to count by nibbles
					#rawCustomCode = ''.join( codeBuffer[3] ) # Joins without whitespace
					#customCode = globalData.codeProcessor.beautifyHex( rawCustomCode ) # Formats to 8 byte per line

					# Get the original/vanilla code
					# intRamAddress = int( ramAddress[2:], 16 ) # Trims off leading 0x before conversion
					# dolOffset = dol.offsetInDOL( intRamAddress )
					# if dolOffset == -1: #originalCode = ''
					# 	raise Exception( 'Unable to convert Gecko code; no equivalent DOL offset for {}.'.format(ramAddress) )
					# elif changeType == 'static': # Long static overwrite (06 opcode)
					# 	originalCode = hexlify( dol.getData(dolOffset, totalBytes) )
					# else: # Injection
					# 	originalCode = hexlify( dol.getData(dolOffset, 4) ) # At the injection point

					# Add the finished code change to the list, and reset the buffer
					#codeChangeTuples.append( (changeType, totalBytes, ramAddress, originalCode, customCode, rawCustomCode, 0) )
					codeChangeTuples.append( (changeType, ramAddress, codeBuffer[3]) )
					codeBuffer = [ '', -1, -1, [], 0 ]

			elif line.startswith( '04' ): # A Static Overwrite
				ramAddress = '0x80' + line[2:8]
				customCode = line.replace( ' ', '' )[8:16]

				# Get the vanilla code from the DOL
				# dolOffset = dol.offsetInDOL( int(ramAddress, 16) )
				# if dolOffset == -1: #originalCode = ''
				# 	raise Exception( 'Unable to convert Gecko code; no equivalent DOL offset for {}.'.format(ramAddress) )
				# else: originalCode = hexlify( dol.getData(dolOffset, 4) )

				#codeChangeTuples.append( ('static', 4, ramAddress, originalCode, customCode, customCode, 0) )
				codeChangeTuples.append( ('static', ramAddress, [customCode]) )

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

		return title, authors, '\n'.join( description ), codeChangeTuples

	def parseAmfs( self, folderPath, includePaths, categoryDefault ):

		""" This method is the primary handler of the ASM Mod Folder Structure (AMFS). This will 
			create a mod container object to store the mod's code changes and other data, and 
			step through each code change dictionary in the JSON file's build list. """


		# Open the json file and get its file contents (need to do this early so we can check for a mod category)
		try:
			jsonPath = os.path.join( folderPath, 'codes.json' )
			with open( jsonPath, 'r' ) as jsonFile:
				jsonContents = json.load( jsonFile, object_pairs_hook=OrderedDict )
		except Exception as err:
			errMsg = 'Encountered an error when attempting to open "{}" (likely due to incorrect formatting); {}'.format( jsonPath, err )
			msg( errMsg )
			return

		codeSection = jsonContents.get( 'codes' )
		#primaryCategory = jsonContents.get( 'category', 'Uncategorized' ) # Applies to all in this json's "codes" list
		primaryCategory = jsonContents.get( 'category', categoryDefault ) # Applies to all in this json's "codes" list

		if codeSection:
			for codeset in codeSection:
				name = 'Unknown mod' # In case the JSON doesn't even have this
				mod = None

				try:
					# Get the mod name, and typecast the authors and description lists to strings
					name = codeset['name'].strip()
					authors = ', '.join( codeset['authors'] )
					description = '\n'.join( codeset['description'] )

					# Create the mod object
					mod = CodeMod( name, authors, description, folderPath, True )
					mod.category = codeset.get( 'category', primaryCategory ) # Secondary definition, per-code dict basis
					mod.configurations = codeset.get( 'configurations', OrderedDict([]) )

					# Get paths for .include ASM import statements, and web links
					mod.includePaths = includePaths
					links = codeset.get( 'webLinks', () )
					for item in links:
						if isinstance( item, (tuple, list) ) and len( item ) == 2:
							mod.webLinks.append( item )
						elif isinstance( item, (str, unicode) ): # Assume it's just a url, missing a comment
							mod.webLinks.append( (item, '') )
					
					# Set the revision (region/version) this code is for
					overallRevision = codeset.get( 'revision', '' )
					if overallRevision:
						overallRevision = self.normalizeRegionString( overallRevision )
						mod.setCurrentRevision( overallRevision )

					buildList = codeset.get( 'build' )

					if buildList:
						for codeChangeDict in buildList:
							codeType = codeChangeDict['type'] # Expected; not optional
							annotation = codeChangeDict.get( 'annotation', '' ) # Optional; may not be there

							# Set the revision (region/version) this code is for
							if not overallRevision:
								revision = codeChangeDict.get( 'revision' )
								if revision:
									revision = self.normalizeRegionString( revision )
								else:
									revision = 'NTSC 1.02'
								mod.setCurrentRevision( revision )
							
							if codeType == 'replace': # Static Overwrite; basically an 02/04 Gecko codetype (hex from json)
								mod.addStaticOverwrite( codeChangeDict['address'], codeChangeDict['value'].splitlines(), annotation=annotation )
								#self.parseAmfsReplace( codeChangeDict, mod )

							elif codeType == 'inject': # Standard code injection (hex from file)
								self.parseAmfsInject( codeChangeDict, mod, annotation )

							elif codeType == 'replaceCodeBlock': # Static overwrite of variable length (hex from file)
								self.parseAmfsReplaceCodeBlock( codeChangeDict, mod, annotation )

							elif codeType == 'injectFolder': # Process a folder of .asm files; all as code injections
								self.parseAmfsInjectFolder( codeChangeDict, mod, annotation )

							elif codeType in ( 'branch', 'branchAndLink', 'binary', 'replaceBinary' ):
								mod.parsingError = True
								mod.errors.append( 'The "' + codeType + '" AMFS code type is not supported' )

							elif codeType == 'standalone': # For Standalone Functions
								self.parseAmfsStandalone( codeChangeDict, mod, annotation )

							# elif codeType == 'gecko':
							# 	self.parseAmfsGecko( codeChangeDict, mod, annotation )

							else:
								mod.parsingError = True
								mod.errors.append( 'Unrecognized AMFS code type: ' + codeType )

						self.storeMod( mod )

					else: # Build all subfolders/files
						mod.errors.append( "No 'build' section found in codes.json" )

				except Exception as err:
					if not mod: # Ill-formatted JSON, or missing basic info
						mod = CodeMod( name, '??', 'JSON located at "{}"'.format(jsonPath), folderPath, True )
						mod.category = codeset.get( 'category', primaryCategory ) # Secondary definition, per-code dict basis

					# Store an errored-out shell of this mod, so the user can notice it and know a broken mod was discovered
					mod.parsingError = True
					mod.errors.append( 'Unable to parse codes section; {}'.format(err) )
					self.storeMod( mod )

		else: # Grab everything from the current folder (and subfolders). Assume .s are static overwrites, and .asm are injections
			# Typecast the authors and description lists to strings
			# authors = ', '.join( codeset['authors'] )
			# description = '\n'.join( codeset['description'] )
			
			# mod = CodeMod( codeset['name'], authors, description, fullFolder, True )

			#self.errors.append( "No 'codes' section found in codes.json" ) #todo
			msg( 'No "codes" section found in codes.json for the mod in "{}".'.format(folderPath) )

	def parseSourceFileHeader( self, asmFile ):

		""" Reads and returns the address for a custom code overwrite or injection from a .asm file header. """

		# Parse the first line to get an injection site (offset) for this code
		firstLine = asmFile.readline()
		address = ''
		author = '??'

		# Check for the original 1-line format
		if firstLine.startswith( '#' ) and 'inserted' in firstLine:
			address = firstLine.split()[-1] # Splits by whitespace and gets the resulting last item

			# Parse the second line to check for an author
			secondLine = asmFile.readline()
			if secondLine.startswith( '#' ) and 'Author:' in secondLine:
				author = secondLine.split( ':', 1 )[1].lstrip()

		# Check for the multi-line format
		elif firstLine.startswith( '#######' ):
			while 1:
				line = asmFile.readline()

				if 'Address:' in line:
					address = line.split()[-1]
				elif 'Author:' in line:
					author = line.split( ':', 1 )[1].lstrip()
				elif line.startswith( '#######' ) or not line:
					break # Failsafe; reached the end of the header (or file!) without finding the address

		# Reset read position
		asmFile.seek( 0 )

		return address, author

	def getCustomCodeFromFile( self, fullAsmFilePath, mod, parseHeader=False, annotation='' ):

		""" Gets address, author (if present), and custom code from a given file. This will also collect pre-processed 
			code if it's present, but only if it is newer than the source code file.
			If parseHeader is False, the offset/author in the file header isn't needed because the calling function 
			should already have it from a codeChange dictionary. (If it does need to be parsed, the calling function 
			only had a sourceFile for reference; most likely through a injectFolder code type.) 
				May return these return codes:
					0: Success
					4: Missing source file
					5: Encountered an error reading the source file """

		if not annotation: # Use the file name for the annotation (without file extension)
			annotation = os.path.splitext( os.path.basename(fullAsmFilePath) )[0]

		# Try to get the custom/source code, and the address/offset if needed
		try:
			# Open the file in byte-reading mode (rb). Strings will then need to be encoded.
			with codecs.open( fullAsmFilePath, encoding='utf-8' ) as asmFile: # Using a different read method for UTF-8 encoding
				if parseHeader:
					offset, author = self.parseSourceFileHeader( asmFile )
					#customCode = asmFile.read().encode( 'utf-8' )
					#customCode = '# {}\n{}'.format( annotation, decodedString )
				else:
					offset = ''
					author = ''

					# Collect all of the file contents
					#firstLine = asmFile.readline().encode( 'utf-8' )
					#theRest = asmFile.read().encode( 'utf-8' )

					# Clean up the header line (changing first line's "#To" to "# To")
					# if firstLine.startswith( '#To' ):
					# 	customCode = '# {}\n# {}\n{}'.format( annotation, firstLine.lstrip( '# '), theRest )
					# else:
					# 	customCode = '# {}\n{}\n{}'.format( annotation, firstLine, theRest )
				customCode = asmFile.read().encode( 'utf-8' )

			sourceModifiedTime = os.path.getmtime( fullAsmFilePath )

		except IOError as err: # File couldn't be found
			# baseFilePath = os.path.splitext( fullAsmFilePath )[0]

			# # Check for a text file with pre-processed code with custom syntax
			# if os.path.exists( baseFilePath + '.txt' ):
			# 	return self.getCustomCodeFromFile( baseFilePath + '.txt', mod, parseHeader, annotation )

			# # Check for assembled binary data
			# elif os.path.exists( baseFilePath + '.bin' ):
			# 	with open( baseFilePath + '.bin', 'rb' ) as binaryFile:
			# 		contents = binaryFile.read()

			# 	hexString = hexlify( contents )
			# 	hexString = globalData.codeProcessor.beautifyHex( hexString, 4 )

			# 	return 0, '', '', hexString, '', annotation # Converting from a byte array to a hex string

			# print( err )
			# mod.parsingError = True
			# #mod.state = 'unavailable'
			# mod.stateDesc = 'Missing source files'
			# mod.errors.append( "Unable to find the file " + os.path.basename(fullAsmFilePath) )
			# return 4, '', '', '', '', annotation
			sourceModifiedTime = 0
			offset = ''
			author = ''
			customCode = ''
			
		except Exception as err: # Unknown error
			print( err )
			mod.parsingError = True
			#mod.state = 'unavailable'
			mod.stateDesc = 'File reading error with ' + os.path.basename( fullAsmFilePath )
			mod.errors.append( 'Encountered an error while reading {}: {}'.format(os.path.basename(fullAsmFilePath), err) )
			return 5, '', '', '', '', annotation
	
		# Check if the source code is newer than the assembled binary
		baseFilePath = os.path.splitext( fullAsmFilePath )[0]
		binaryModifiedTime = 0
		foundBin = False
		foundTxt = False
		try:
			binaryModifiedTime = os.path.getmtime( baseFilePath + '.bin' )
			foundBin = True
		except:
			try:
				binaryModifiedTime = os.path.getmtime( baseFilePath + '.txt' )
			except:
				pass
		if sourceModifiedTime > binaryModifiedTime:
			# The source is newer, or the bin/txt files aren't present
			return 0, offset, author, customCode, '', annotation

		# Get the preProcessed code. Check for assembled binary data, and/or for a text file (partially assembled code)
		try:
			with open( baseFilePath + '.bin', 'rb' ) as binaryFile:
				contents = binaryFile.read()
				preProcessedCode = hexlify( contents )

		except IOError as err: # File couldn't be found
			# Open the file in byte-reading mode (rb). Strings will then need to be encoded.
			with codecs.open( baseFilePath + '.txt', encoding='utf-8' ) as asmFile: # Using a different read method for UTF-8 encoding
				preProcessedCode = asmFile.read().encode( 'utf-8' )
		except Exception as err:
			preProcessedCode = ''

		return 0, offset, author, customCode, preProcessedCode, annotation
			
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
			mod.errors.append( 'Injection at {} missing "sourceFile" path'.format(address) )
		if sourceFile and not address:
			mod.errors.append( '{} injection missing its "address" value'.format(sourceFile) )
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

	# def parseAmfsReplace( self, codeChangeDict, mod ):
		
	# 	# Place annotations with the custom code, as a comment
	# 	annotation = codeChangeDict.get( 'annotation' )
	# 	if annotation:
	# 		customCode = [ '# ' + annotation ]
	# 		customCode.extend( codeChangeDict['value'].splitlines() )
	# 	else:
	# 		customCode = codeChangeDict['value'].splitlines()

	# 	mod.addStaticOverwrite( codeChangeDict['address'], customCode )

	def parseAmfsInject( self, codeChangeDict, mod, annotation, sourceFile='' ):

		""" AMFS Injection; custom code sourced from an assembly file. """

		# There will be no codeChangeDict if a source file was provided (i.e. an inject folder is being processed)
		if codeChangeDict:
			address, sourceFile = self.getAddressAndSourceFile( codeChangeDict, mod )
			#fullAsmFilePath = os.path.join( mod.path, sourceFile )
			fullAsmFilePath = '\\\\?\\' + os.path.normpath( os.path.join(mod.path, sourceFile) )
			#annotation = codeChangeDict.get( 'annotation', '' )
		else: # Processing from 'injectFolder'; get address from file
			address = ''
			fullAsmFilePath = sourceFile # This will be a full path in this case
			#annotation = ''

		# Read the file for info and the custom code
		returnCode, address, _, customCode, anno = self.getCustomCodeFromFile( fullAsmFilePath, mod, True, annotation )

		# Check for a missing address
		if returnCode == 0 and not address:
			# Fall back to the codes.json file (todo: always use this?)
			if codeChangeDict:
				address = codeChangeDict.get( 'address', '' )

			if not address:
				mod.parsingError = True
				mod.stateDesc = 'Missing address for "{}"'.format( sourceFile )
				mod.errors.append( 'Unable to find an address for ' + sourceFile )
				return

		mod.addInjection( address, customCode, '', anno )

	def parseAmfsReplaceCodeBlock( self, codeChangeDict, mod, annotation ):

		""" AMFS Long Static Overwrite of variable length. """

		address, sourceFile = self.getAddressAndSourceFile( codeChangeDict, mod )
		fullAsmFilePath = '\\\\?\\' + os.path.normpath( os.path.join(mod.path, sourceFile) )
		#annotation = codeChangeDict.get( 'annotation', '' ) # Optional; may not be there
		
		# Read the file for info and the custom code
		returnCode, _, _, customCode, anno = self.getCustomCodeFromFile( fullAsmFilePath, mod, False, annotation )
		#if returnCode != 0:
			# mod.parsingError = True
			# mod.stateDesc = 'Parsing error; unable to get code from file'
			# mod.errors.append( "Unable to read the 'sourceFile' {}".format(sourceFile) )
		#	return
		
		# Get the custom code's length, and store the info for this code change
		# customCodeLength = getCustomCodeLength( preProcessedCustomCode )
		# mod.data[mod.revision].append( ('static', customCodeLength, offset, origHex, customCode, preProcessedCustomCode) )
		
		#mod.addStaticOverwrite( address, codeChangeDict['value'].splitlines() )
		# codeChange = CodeChange( mod, 'static', address, '', customCode )
		# mod.data[mod.currentRevision].append( codeChange )
		mod.addStaticOverwrite( address, customCode, '', anno )

	def _processAmfsInjectSubfolder( self, fullFolderPath, mod, annotation, isRecursive ):

		""" Recursive helper method to .parseAmfsInjectFolder(). Processes all files/folders in a directory. """

		try:
			for item in os.listdir( fullFolderPath ):
				itemPath = os.path.join( fullFolderPath, item )

				if os.path.isdir( itemPath ) and isRecursive:
					self._processAmfsInjectSubfolder( itemPath, mod, annotation, isRecursive )
				elif itemPath.endswith( '.asm' ):
					self.parseAmfsInject( None, mod, annotation, sourceFile=itemPath )
			
		except WindowsError as err:
			mod.parsingError = True
			mod.errors.append( 'Unable to find the folder "{}"'.format(fullFolderPath) )
			print( err )

	def parseAmfsInjectFolder( self, codeChangeDict, mod, annotation ):
		# Get/construct the root folder path
		sourceFolder = codeChangeDict['sourceFolder']
		sourceFolderPath = os.path.join( mod.path, sourceFolder )

		# Check recursive flag
		isRecursive = codeChangeDict.get( 'isRecursive', -1 )
		if isRecursive == -1: # Flag not found!
			mod.parsingError = True
			mod.errors.append( 'No "isRecursive" flag defined for the {} folder.'.format(sourceFolder) )
			return

		# try:
		self._processAmfsInjectSubfolder( sourceFolderPath, mod, annotation, isRecursive )
		# except WindowsError as err:
		#	# Try again with extended path formatting
		# 	print 'second try for', sourceFolderPath
		# 	self._processAmfsInjectSubfolder( '\\\\?\\' + os.path.normpath(sourceFolderPath), mod, annotation, codeChangeDict['isRecursive'] )

	def parseAmfsStandalone( self, codeChangeDict, mod, annotation ):

		""" Read a Standalone Function from AMFS format. """

		name = codeChangeDict.get( 'name', '' )
		revisions = codeChangeDict.get( 'revisions', ['NTSC 1.02'] )
		sourceFile = codeChangeDict.get( 'sourceFile', '' ) # Relative path

		# Perform some basic validation
		if not name:
			mod.parsingError = True
			if sourceFile:
				sourceFileName = os.path.basename( sourceFile )
				mod.errors.append( 'SF for {} is missing its name property'.format(sourceFileName) )
			else:
				mod.errors.append( 'An SF is missing its name property' )

		# If a sourceFile was provided, construct the full path and get the custom code
		if not sourceFile:
			mod.parsingError = True
			mod.errors.append( 'SF {} is missing its "sourceFile" property'.format(name) )
			customCode = ''
		else:
			fullAsmFilePath = '\\\\?\\' + os.path.normpath( os.path.join(mod.path, sourceFile) )
			_, _, _, customCode, annotation = self.getCustomCodeFromFile( fullAsmFilePath, mod, False, annotation )

		mod.addStandalone( name, revisions, customCode, annotation )

	# def parseAmfsGecko( self, codeChangeDict, mod, annotation ):

	# 	""" Read a Gecko Code from AMFS format. (depricate this?) """

	# 	mod.addGecko(  )


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
				print( 'Missing PowerPC-EABI binaries!' )
				break

	@staticmethod
	def beautifyHex( rawHex, blocksPerLine=2 ):

		""" Rewrites a hex string to something more human-readable, displaying 
			8 bytes per line (2 blocks of 4 bytes, separated by a space). """
		
		assert blocksPerLine > 0, 'Invalid blocksPerLine given to beautifyHex: ' + str( blocksPerLine )

		code = [ rawHex[:8] ] # Start with the first block included, to prevent a check for whitespace in the loop
		divisor = blocksPerLine * 8

		for block in range( 8, len(rawHex), 8 ):

			if block % divisor != 0: # For blocksPerLine of 4, the modulo would be 0, 8, 16, 24, 0, 8...
				code.append( ' ' + rawHex[block:block+8] )
			else:
				code.append( '\n' + rawHex[block:block+8] )
		
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

	def assemble( self, asmCode, beautify=False, includePaths=None, suppressWarnings=False, parseOutput=True, errorLineOffset=0 ):
		
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
					lineNumber, line = line.split( ':', 2 )[1:]
					lineNumber = int( lineNumber ) + errorLineOffset
					errorLines.append( '{}: {}'.format(lineNumber, line) )
					continue
				
				# Condense the file path and rebuild the rest of the string as it was
				lineParts = line.split( ': ', 2 ) # Splits on first 2 occurrances only
				fileName, lineNumber = lineParts[0].rsplit( ':', 1 )
				lineNumber = int( lineNumber ) + errorLineOffset
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
			print( 'Errors detected during disassembly:' )
			print( errors )
			return ( '', errors )
		
		return self.parseDisassemblerOutput( output )

	def parseAssemblerOutput( self, cmdOutput, beautify=False ):

		""" Parses output from the assembler into a hex string. 

			If beautify is False, no whitespace is included; otherwise, the output is formatted 
			into 2 chunks of 4 bytes per line (like a Gecko code), for better readability. """

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
				print( 'Error parsing assembler output on this line:' )
				print( line, '\n' )
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
				print( 'Found empty line during disassembly. problem?' )
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
			print( errors )

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

		# Check if referencing a standalone function (comments should already be filtered out)
		if CodeLibraryParser.isStandaloneFunctionHeader( targetDescriptor ):
			targetFunctionName = targetDescriptor[1:-1] # Removes the </> characters
			targetFunctionAddress = globalData.standaloneFunctions[targetFunctionName][0] # RAM Address
			branchDistance = targetFunctionAddress - ( branchStart )

		else: # Must be a special branch syntax using a RAM address
			branchDistance = int( targetDescriptor, 16 ) - ( branchStart )

		branchDistance += branchAdjustment

		return branchInstruction, branchDistance

	def evaluateCustomCode( self, rawCode, includePaths=None, configurations=None, validateConfigs=True ):
		
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
		codeLines = rawCode.splitlines()
		isAssembly = self.codeIsAssembly( codeLines )

		if isAssembly:
			returnCode, codeLength, preProcessedCode, customSyntaxRanges = self._evaluateAssembly( codeLines, includePaths, configurations, validateConfigs )
		else:
			returnCode, codeLength, preProcessedCode, customSyntaxRanges = self._evaluateHexcode( codeLines, includePaths, configurations, validateConfigs )

		return returnCode, codeLength, preProcessedCode, customSyntaxRanges, isAssembly

	def _evaluateAssembly( self, codeLines, includePaths=None, configurations=None, validateConfigs=True ):

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
						varName, chunk = chunk.split( ']]' ) # Not expecting multiple ']]' delimiters in this chunk

						if validateConfigs:
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
						else:
							optionWidth = 4

						#sectionChunks[i] = chunk.replace( varName + ']]', '0' )
						sectionChunks[i] = '0' + chunk
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
		conversionOutput, errors = self.assemble( codeForAssembler, False, includePaths, True, False, errorLineOffset=-1 )
		
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

	def _evaluateHexcode( self, codeLines, includePaths=None, configurations=None, validateConfigs=True ):

		customSyntaxRanges = []		# List of lists; each of the form [offset, width, type, origCodeLine, optNames]
		preProcessedLines = []
		length = 0

		# Filter out special syntaxes and remove comments
		for rawLine in codeLines:
			# Start off by filtering out comments, and skip empty lines
			codeLine = rawLine.split( '#' )[0].strip()
			if not codeLine: continue

			elif CodeLibraryParser.isSpecialBranchSyntax( codeLine ): # e.g. "bl 0x80001234" or "bl <testFunction>"
				customSyntaxRanges.append( [length, 4, 'sbs', codeLine, ()] )

				# Parse for some psuedo-code (the instruction should be correct, but branch distance will be 0)
				branchInstruction, branchDistance = self.parseSpecialBranchSyntax( codeLine )
				psudoHexCode = self.assembleBranch( branchInstruction, branchDistance )
				preProcessedLines.append( psudoHexCode )
				length += 4
			
			elif '<<' in codeLine and '>>' in codeLine: # Identifies symbols in the form of <<functionName>>
				customSyntaxRanges.append( [length, 4, 'sym', codeLine, CodeLibraryParser.containsPointerSymbol(codeLine)] )
				preProcessedLines.append( '60000000' ) # Could be anything, soo... nop!
				length += 4

			elif '[[' in codeLine and ']]' in codeLine: # Identifies configuration option placeholders

				sectionChunks = codeLine.split( '[[' )
				sectionLength = 0
				
				if validateConfigs: # Use the mod's configuration option to determine option length
					
					# Parse out all option names, and collect their information from the mod's configuration dictionaries
					for chunk in sectionChunks:
						if ']]' in chunk:
							varName, chunk = chunk.split( ']]' )

							# Attempt to get the configuration name (and size if the code is already assembled)
							option = configurations.get( varName )
							if not option:
								return 3, -1, varName, []
							optionType = option.get( 'type' )
							if not optionType:
								return 4, -1, varName, []
							optionWidth = self.getOptionWidth( optionType )
							if optionWidth == -1:
								return 5, -1, optionType, []

							if '|' in varName:
								names = varName.split( '|' )
								names = [ name.strip() for name in names ] # Remove whitespace from start/end of names
							elif '&' in varName:
								names = varName.split( '&' )
								names = [ name.strip() for name in names ] # Remove whitespace from start/end of names
							else:
								names = [ varName ]
							
							customSyntaxRanges.append( [length+sectionLength, optionWidth, 'opt', codeLine, names] )

							# If the custom code following the option is entirely raw hex, get its length
							preProcessedLines.append( '00' * optionWidth )
							sectionLength += optionWidth

						# If other custom code in this line is raw hex, get its length
						if chunk:
							filteredChunk = ''.join( chunk.split() ) # Filtering out whitespace
							sectionLength += len( filteredChunk ) / 2
							preProcessedLines.append( filteredChunk )

				else: # Need to do something a little more involved to predict option length

					""" The following is expecting each group of 4 bytes is separated by whitespace.
						For example: '000000[[SomeVar]]' or '40820008 0000[[SomeVar]]' """

					# Extract names (eliminating whitespace associated with names) and separate hex groups
					names = []
					nameIndex = 0
					for i, chunk in enumerate( sectionChunks ):
						if ']]' in chunk:
							varName, chunk = chunk.split( ']]' )
							names.append( varName )
							sectionChunks[i] = '[[]]' + chunk

					# Recombine the string and split on whitespace
					newLine = ''.join( sectionChunks )
					hexGroups = newLine.split() # Will now have something like [ '000000[[]]' ] or [ '40820008', '0000[[]]' ]

					# Process each hex group
					groupParts = []
					for group in hexGroups:
						# Parse out all option names, and collect their information from the mod's configuration dictionaries
						chunks = group.split( '[[' )
						groupLength = 0
						nameIndex = -1

						for chunk in chunks:
							if ']]' in chunk:
								chunk = chunk.split( ']]' )[1]
								nameIndex = len( groupParts )
								varName = names.pop( 0 )

							if chunk:
								groupLength += len( chunk ) / 2
								groupParts.append( chunk )

						if nameIndex != -1: # Found a name in this group
							# Build the completed group, with predicted option placeholder
							optionWidth = 4 - groupLength
							optPlaceholder = '00' * optionWidth

							# Check for multiple values to be ANDed or ORed together
							if '|' in varName:
								optNames = varName.split( '|' )
								optNames = [ name.strip() for name in optNames ] # Remove whitespace from start/end of names
							elif '&' in varName:
								optNames = varName.split( '&' )
								optNames = [ name.strip() for name in optNames ] # Remove whitespace from start/end of names
							else:
								optNames = [ varName ]
							
							optOffset = length + sectionLength + groupLength
							customSyntaxRanges.append( [optOffset, optionWidth, 'opt', codeLine, optNames] )
							
							groupParts.insert( nameIndex, optPlaceholder )
							sectionLength += groupLength + optionWidth
						else:
							sectionLength += groupLength

					preProcessedLines.append( ''.join(groupParts) )

					#for char in codeLine

				length += sectionLength

			else:
				# Strip out whitespace and store the line
				pureHex = ''.join( codeLine.split() )
				length += len( pureHex ) / 2
				
				preProcessedLines.append( pureHex )

		preProcessedCode = ''.join( preProcessedLines )

		return 0, length, preProcessedCode, customSyntaxRanges

	def preDisassembleRawCode( self, codeLinesList, discardWhitespace=True ):

		""" Used to disassemble hex code to assembly, while preserving special syntax. """

		# Define placeholders for special syntaxes
		compilationPlaceholder = 'DEADBEFE'
		branchMarker = 'stfdu f21,-16642(r13)'

		# if type( codeLinesList ) == str:
		# 	codeLinesList = codeLinesList.splitlines()

		# disassemblyRequired = False
		allSpecialSyntaxes = True
		filteredLines = []
		customSyntax = []
		length = 0

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
				length += 8

			elif CodeLibraryParser.containsPointerSymbol( codeLine ): # Identifies symbols in the form of <<functionName>>
				customSyntax.append( codeLine )
				filteredLines.append( compilationPlaceholder )
				length += 8

			elif '[[' in codeLine and ']]' in codeLine: # Identifies configuration option placeholders
				customSyntax.append( codeLine )
				filteredLines.append( compilationPlaceholder )
				
				# Try to determine the nibble length of the code on this line
				# sectionLength = 0
				# sectionChunks = codeLine.split( '[[' )
				# for chunk in sectionChunks:
				# 	if ']]' in chunk:
				# 		_, chunk = chunk.split( ']]' ) # Not expecting multiple ']]' delimiters in this chunk

				# 	if not chunk: pass
				# 	else:
				# 		filteredChunk = ''.join( chunk.split() ) # Filtering out whitespace
				# 		sectionLength += len( filteredChunk )

				# Round up to closest multiple of 4 bytes
				#length += roundTo32( sectionLength, 8 )
				
				# Eliminate potential whitespace from variable space
				sectionChunks = codeLine.split( '[[' )
				for i, chunk in enumerate( sectionChunks ):
					if ']]' in chunk:
						sectionChunks[i] = chunk.split( ']]' )[1]

				# Split on whitespace to determine word count
				words = ''.join( sectionChunks ).split()
				length += len( words ) * 8

			else:
				# Whether it's hex or not, re-add the line to filteredLines.
				filteredLines.append( codeLine )
				allSpecialSyntaxes = False

				length += len( ''.join(codeLine.split()) )

				# Check whether this line indicates that this code requires conversion.
				# if not disassemblyRequired and validHex( codeLine.replace(' ', '') ):
				# 	disassemblyRequired = True

		length = length / 2 # Convert count from nibbles to bytes

		if allSpecialSyntaxes: # No real processing needed; it will be done when resolving these syntaxes
			if discardWhitespace:
				return ( 0, ''.join(customSyntax), length )
			else:
				return ( 0, '\n'.join(customSyntax), length )

		filteredCode = '\n'.join( filteredLines ) # Joins the lines with linebreaks.

		# If this is hex, convert it to ASM.
		# if disassemblyRequired:
		conversionOutput, errors = self.disassemble( filteredCode, whitespaceNeedsRemoving=True )
		
		if errors:
			cmsg( errors, 'Disassembly Error 02' )
			return ( 2, '', -1 )
		else:
			newCode = conversionOutput
		# else:
		# 	newCode = filteredCode.replace( 'DEADBEFE', 'stfdu f21,-16642(r13)' )

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

		return ( 0, newCode.strip(), length )

	# def resolveCustomSyntaxes( self, thisFunctionStartingOffset, rawCustomCode, preProcessedCustomCode, includePaths=None, configurations=None ):

	# 	""" Replaces any custom branch syntaxes that don't exist in the assembler with standard 'b_ [intDistance]' branches, 
	# 		and replaces function symbols with literal RAM addresses, of where that function will end up residing in memory. 

	# 		This process may require two passes. The first is always needed, in order to determine all addresses and syntax resolutions. 
	# 		The second may be needed for final assembly because some lines with custom syntaxes might need to reference other parts of 
	# 		the whole source code (raw custom code), such as for macros or label branch calculations. 
			
	# 		May return these return codes:
	# 			0: Success (or no processing was needed)
	# 			2: Unable to assemble source code with custom syntaxes
	# 			3: Unable to assemble custom syntaxes (source is in hex form)
	# 			4: Unable to find a configuration option name
	# 			100: Success, and the last instruction is a custom syntax
	# 	"""

	# 	# If this code has no special syntaxes in it, return it as-is
	# 	if '|S|' not in preProcessedCustomCode:
	# 		return ( 0, preProcessedCustomCode )

	# 	debugging = False

	# 	if debugging:
	# 		print '\nResolving custom syntaxes for code stored at', hex( thisFunctionStartingOffset )

	# 	customCodeSections = preProcessedCustomCode.split( '|S|' )
	# 	rawCustomCodeLines = rawCustomCode.splitlines()
	# 	rawCodeIsAssembly = self.codeIsAssembly( rawCustomCodeLines ) # Checking the form of the raw (initial) code input, not the pre-processed code
	# 	#dol = globalData.disc.dol
	# 	resolvedCodeLines = []
	# 	requiresAssembly = False
	# 	#errorDetails = ''
	# 	byteOffset = 0
	# 	returnCode = 0

	# 	# Resolve individual syntaxes to finished assembly and/or hex
	# 	for i, section in enumerate( customCodeSections ):

	# 		if section.startswith( 'sbs__' ): # Something of the form 'bl 0x80001234' or 'bl <function>'; build a branch from this
	# 			section = section[5:] # Removes the 'sbs__' identifier

	# 			if debugging:
	# 				print 'recognized special branch syntax at function offset', hex( byteOffset ) + ':', section

	# 			# if '+' in section:
	# 			# 	section, offset = section.split( '+' ) # Whitespace around the + is fine for int()
	# 			# 	if offset.lstrip().startswith( '0x' ):
	# 			# 		branchAdjustment = int( offset, 16 )
	# 			# 	else: branchAdjustment = int( offset )
	# 			# else: branchAdjustment = 0

	# 			# branchInstruction, targetDescriptor = section.split()[:2] # Get up to two parts max

	# 			# if CodeLibraryParser.isStandaloneFunctionHeader( targetDescriptor ): # The syntax references a standalone function (comments should already be filtered out).
	# 			# 	targetFunctionName = targetDescriptor[1:-1] # Removes the </> characters
	# 			# 	targetFunctionAddress = globalData.standaloneFunctions[targetFunctionName][0] # RAM Address
	# 			# 	#branchDistance = dol.calcBranchDistance( thisFunctionStartingOffset + byteOffset, targetFunctionAddress )
	# 			# 	branchDistance = targetFunctionAddress - ( thisFunctionStartingOffset + byteOffset )

	# 			# 	# if branchDistance == -1: # Fatal error; end the loop
	# 			# 	# 	errorDetails = 'Unable to calculate SF branching distance, from {} to {}.'.format( hex(thisFunctionStartingOffset + byteOffset), hex(targetFunctionAddress) )
	# 			# 	# 	break

	# 			# else: # Must be a special branch syntax using a RAM address
	# 			# 	# startingRamOffset = dol.offsetInRAM( thisFunctionStartingOffset + byteOffset )

	# 			# 	# if startingRamOffset == -1: # Fatal error; end the loop
	# 			# 	# 	errorDetails = 'Unable to determine starting RAM offset, from DOL offset {}.'.format( hex(thisFunctionStartingOffset + byteOffset) )
	# 			# 	# 	break
	# 			# 	#branchDistance = int( targetDescriptor, 16 ) - 0x80000000 - startingRamOffset
	# 			# 	branchDistance = int( targetDescriptor, 16 ) - ( thisFunctionStartingOffset + byteOffset )

	# 			# branchDistance += branchAdjustment
	# 			branchInstruction, branchDistance = self.parseSpecialBranchSyntax( section, thisFunctionStartingOffset + byteOffset )

	# 			# Remember in case reassembly is later determined to be required
	# 			resolvedCodeLines.append( '{} {}'.format(branchInstruction, branchDistance) ) 

	# 			# Replace this line with hex for the finished branch
	# 			if not requiresAssembly: # The preProcessed customCode won't be used if reassembly is required; so don't bother replacing those lines
	# 				customCodeSections[i] = self.assembleBranch( branchInstruction, branchDistance ) # Assembles these arguments into a finished hex string

	# 			# Check if this was the last section
	# 			if i + 1 == len( customCodeSections ):
	# 				returnCode = 100

	# 			byteOffset += 4

	# 		elif section.startswith( 'sym__' ): # Contains a function symbol; something like 'lis r3, (<<function>>+0x40)@h'; change the symbol to an address
	# 			section = section[5:]

	# 			if debugging:
	# 				print 'resolving symbol names in:', section

	# 			#erroredFunctions = set()

	# 			# Determine the RAM addresses for the symbols, and replace them in the line
	# 			for name in CodeLibraryParser.containsPointerSymbol( section ):
	# 				# Get the dol offset and ultimate RAM address of the target function
	# 				targetFunctionAddress = globalData.standaloneFunctions[name][0]
	# 				# ramAddress = dol.offsetInRAM( targetFunctionAddress ) + 0x80000000
					
	# 				# if ramAddress == -1: # Fatal error; probably an invalid function offset was given, pointing to an area outside of the DOL
	# 				# 	erroredFunctions.add( name )

	# 				#address = "0x{0:0{1}X}".format( ramAddress, 8 ) # e.g. 1234 (int) -> '0x800004D2' (string)
	# 				address = "0x{:08X}".format( targetFunctionAddress ) # e.g. 1234 (int) -> '0x800004D2' (string)

	# 				section = section.replace( '<<' + name + '>>', address )

	# 			# if erroredFunctions:
	# 			# 	errorDetails = 'Unable to calculate RAM addresses for the following function symbols:\n\n' + '\n'.join( erroredFunctions )
	# 			# 	break				

	# 			if debugging:
	# 				print '              resolved to:', section

	# 			requiresAssembly = True
	# 			resolvedCodeLines.append( section )

	# 			# Check if this was the last section
	# 			if i + 1 == len( customCodeSections ):
	# 				returnCode = 100

	# 			byteOffset += 4
				
	# 		elif section.startswith( 'opt__' ): # Identifies configuration option placeholders
	# 			section = section[5:]

	# 			#optionPairs = {}
	# 			optionData = []

	# 			# Replace variable placeholders with the currently set option value
	# 			# Check if this section requires assembly, and collect option names/values
	# 			sectionChunks = section.split( '[[' )
	# 			for j, chunk in enumerate( sectionChunks ):
	# 				if ']]' in chunk:
	# 					varName, chunk = chunk.split( ']]' )

	# 					# Seek out the option name and its current value in the configurations list
	# 					# for configuration in configurations:
	# 					# 	if configuration['name'] == varName:
	# 					# 		#currentValue = str( configuration['value'] )
	# 					# 		optionData.append( (configuration['type'], configuration['value']) )
	# 					# 		break
	# 					# else: # Loop above didn't break; variable name not found!
	# 					# 	return ( 4, 'Unable to find the configuration option "{}" in the mod definition.'.format(varName) )
	# 					option = configurations.get( varName )
	# 					if not option:
	# 						return ( 4, 'Unable to find the configuration option "{}" in the mod definition.'.format(varName) )
	# 					optionData.append( (option['type'], option['value']) ) # Existance of type/value already verified

	# 					#sectionChunks[j] = chunk.replace( varName+']]', currentValue )

	# 					# if requiresAssembly: pass
	# 					# elif all( char in hexdigits for char in theRest.replace(' ', '') ): pass
	# 					# else: requiresAssembly = True
						
	# 				if requiresAssembly: pass
	# 				elif all( char in hexdigits for char in chunk.replace(' ', '') ): pass
	# 				else: requiresAssembly = True

	# 			# Reiterate over the chunks to replace the names with values, now that we know whether they should be packed
	# 			for j, chunk in enumerate( sectionChunks ):
	# 				if ']]' in chunk:
	# 					varName, chunk = chunk.split( ']]' )

	# 					if requiresAssembly: # No need to pad the value
	# 						value = optionData.pop( 0 )[-1]
	# 						#sectionChunks[j] = chunk.replace( varName+']]', str(value) )
	# 						sectionChunks[j] = str( value ) + chunk
	# 					else: # Needs to be packed to the appropriate length for the data type
	# 						optionType, value = optionData.pop( 0 )
	# 						# if type( value ) == str: # Need to typecast to int or float
	# 						# 	if optionType == 'float':
	# 						# 		value = float( value )
	# 						# 	elif '0x' in value:
	# 						# 		value = int( value, 16 )
	# 						# 	else:
	# 						# 		value = int( value )
	# 						value = CodeMod.parseConfigValue( optionType, value )
	# 						valueAsBytes = struct.pack( ConfigurationTypes[optionType], value )
	# 						sectionChunks[j] = hexlify( valueAsBytes ) + chunk

	# 			# if not requiresAssembly:
	# 			# 	sectionChunks = [ chunk.replace(' ', '') for chunk in sectionChunks ]
	# 			resolvedCodeLines.append( ''.join(sectionChunks) )
						
	# 			# Check if this was the last section
	# 			if i + 1 == len( customCodeSections ):
	# 				returnCode = 100

	# 			byteOffset += 4

	# 		else: # This code should already be pre-processed hex (assembled, with whitespace removed)
	# 			byteOffset += len( section ) / 2

	# 	#if errorDetails: return ( 1, errorDetails )

	# 	# Assemble the final code using the full source (raw) code
	# 	if requiresAssembly and rawCodeIsAssembly:
	# 		if debugging:
	# 			print 'reassembling resolved code from source (asm) code'

	# 		# Using the original, raw code, remove comments, replace the custom syntaxes, and assemble it into hex
	# 		rawAssembly = []
	# 		for line in rawCustomCodeLines:
	# 			# Start off by filtering out comments and empty lines.
	# 			codeLine = line.split( '#' )[0].strip()
					
	# 			if CodeLibraryParser.isSpecialBranchSyntax( codeLine ) or CodeLibraryParser.containsPointerSymbol( codeLine ) or CodeLibraryParser.containsConfiguration( codeLine ):
	# 				# Replace with resolved code lines
	# 				rawAssembly.append( resolvedCodeLines.pop(0) )
	# 			else:
	# 				rawAssembly.append( codeLine )

	# 		customCode, errors = self.assemble( '\n'.join(rawAssembly), includePaths=includePaths, suppressWarnings=True )

	# 		if errors:
	# 			return ( 2, 'Unable to assemble source code with custom syntaxes.\n\n' + errors )

	# 	elif requiresAssembly: # Yet the raw code is in hex form; need to assemble just the lines with custom syntax
	# 		if debugging:
	# 			print 'assembling custom syntaxes separately from assembled hex'

	# 		# Assemble the resolved lines in one group (doing it this way instead of independently in the customCodeSections loop for less IPC overhead)
	# 		assembledResolvedCode, errors = self.assemble( '\n'.join(resolvedCodeLines), beautify=True, suppressWarnings=True )
	# 		if errors:
	# 			return ( 3, 'Unable to assemble hex code with custom syntaxes.\n\n' + errors )

	# 		resolvedHexCodeLines = assembledResolvedCode.split() # Split on whitespace
	# 		newCustomCodeSections = preProcessedCustomCode.split( '|S|' ) # Need to re-split this, since customCodeSections may have been modified by now
			
	# 		# Add the resolved, assembled custom syntaxes back into the full custom code string
	# 		for i, section in enumerate( newCustomCodeSections ):
	# 			if section[:5] in ( 'sbs__', 'sym__', 'opt__' ):
	# 				newCustomCodeSections[i] = resolvedHexCodeLines.pop( 0 )
	# 				if resolvedHexCodeLines == []: break

	# 		customCode = ''.join( newCustomCodeSections )

	# 	else: # Only hex should remain. Recombine the code lines back into one string. Special Branch Syntaxes have been assembled to hex
	# 		if debugging:
	# 			print 'resolved custom code using the preProcessedCustomCode lines'
			
	# 		for i, section in enumerate( customCodeSections ):
	# 			if section[:5] in ( 'sbs__', 'sym__', 'opt__' ):
	# 				customCodeSections[i] = resolvedCodeLines.pop( 0 ).replace( ' ', '' )
	# 				if resolvedCodeLines == []: break

	# 		customCode = ''.join( customCodeSections )

	# 	return ( returnCode, customCode )

	#def resolveCustomSyntaxes2( self, thisFunctionStartingOffset, rawCustomCode, preProcessedCustomCode, includePaths=None, configurations=None ):

	def resolveCustomSyntaxes2( self, codeAddress, codeChange ):

		""" Performs final code processing on pre-processed code; replaces any custom syntaxes that 
			don't exist in the assembler with standard 'b_ [intDistance]' branches, and replaces function 
			symbols with literal RAM addresses, of where that function will end up residing in memory. 

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

		resolvedLinesForAssembly = []
		requiresAssembly = False
		newHexCodeSections = []
		returnCode = 0
		offset = 0

		# Resolve individual syntaxes to finished assembly and/or hex
		for syntaxOffset, length, syntaxType, codeLine, names in codeChange.syntaxInfo:

			# Check for and collect pre-assembled hex
			if syntaxOffset != offset:
				sectionLength = syntaxOffset - offset
				newHexCodeSections.append( codeChange.preProcessedCode[offset*2:syntaxOffset*2] )
				offset += sectionLength

			if syntaxType == 'sbs': # Something of the form 'bl 0x80001234' or 'bl <function>'; build a branch from this
				branchInstruction, branchDistance = self.parseSpecialBranchSyntax( codeLine, codeAddress + offset )

				# Remember in case reassembly is later determined to be required
				resolvedLinesForAssembly.append( '{} {}'.format(branchInstruction, branchDistance) ) 

				# Add code for this section
				if requiresAssembly:
					newHexCodeSections.append( '48000000' ) # Placeholder
				else:
					# Replace this line with hex for the finished branch
					finishedBranch = self.assembleBranch( branchInstruction, branchDistance )
					newHexCodeSections.append( finishedBranch )

			elif syntaxType == 'sym': # Contains a function symbol; something like 'lis r3, (<<function>>+0x40)@h'; change the symbol to an address
				# Determine the RAM addresses for the symbols, and replace them in the line
				for name in CodeLibraryParser.containsPointerSymbol( codeLine ):
					# Get the dol offset and ultimate RAM address of the target function
					targetFunctionAddress = globalData.standaloneFunctions[name][0]
					address = "0x{:08X}".format( targetFunctionAddress ) # e.g. 1234 (int) -> '0x800004D2' (string)

					codeLine = codeLine.replace( '<<' + name + '>>', address )

				requiresAssembly = True
				resolvedLinesForAssembly.append( codeLine )
				newHexCodeSections.append( '60000000' ) # Placeholder
				
			elif syntaxType == 'opt': # Identifies configuration option placeholders
				#optionPairs = {}
				#optionData = []

				# Replace variable placeholders with the currently set option value (in case re-assembly is needed)
				sectionChunks = codeLine.split( '[[' )
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
						option = codeChange.mod.getConfiguration( varName )
						if not option:
							return ( 4, 'Unable to find the configuration option "{}" in the mod definition.'.format(varName) )
						#optionData.append( (option['type'], option['value']) ) # Existance of type/value already verified

						# if requiresAssembly: pass
						# elif all( char in hexdigits for char in theRest.replace(' ', '') ): pass
						# else: requiresAssembly = True

						optType = option['type']
						optValue = option['value']

						#if codeChange.isAssembly: # No need to pad the value
						#sectionChunks[j] = chunk.replace( varName+']]', str(optValue) )
						sectionChunks[j] = str( optValue ) + chunk
						# else: # Needs to be packed to the appropriate length for the data type
						# 	value = CodeMod.parseConfigValue( optType, optValue )
						# 	valueAsBytes = struct.pack( ConfigurationTypes[optType], value )
						# 	sectionChunks[j] = chunk.replace( varName+']]', hexlify(valueAsBytes) )
					
					if requiresAssembly: pass
					elif all( char in hexdigits for char in chunk.replace(' ', '') ): pass
					else:
						requiresAssembly = True

				# Reiterate over the chunks to replace the names with values, now that we know whether they should be packed
				# for j, chunk in enumerate( sectionChunks ):
				# 	if ']]' in chunk:
				# 		varName, theRest = chunk.split( ']]' )

				# 		if requiresAssembly: # No need to pad the value
				# 			value = optionData.pop( 0 )[-1]
				# 			sectionChunks[j] = chunk.replace( varName+']]', str(value) )
				# 		else: # Needs to be packed to the appropriate length for the data type
				# 			optionType, value = optionData.pop( 0 )
				# 			# if type( value ) == str: # Need to typecast to int or float
				# 			# 	if optionType == 'float':
				# 			# 		value = float( value )
				# 			# 	elif '0x' in value:
				# 			# 		value = int( value, 16 )
				# 			# 	else:
				# 			# 		value = int( value )
				# 			value = CodeMod.parseConfigValue( optionType, value )
				# 			valueAsBytes = struct.pack( ConfigurationTypes[optionType], value )
				# 			sectionChunks[j] = chunk.replace( varName+']]', hexlify(valueAsBytes) )
				
				resolvedLinesForAssembly.append( ''.join(sectionChunks) )

				# Add code for this section
				if requiresAssembly:
					newHexCodeSections.append( '60000000' ) # Placeholder
				else:
					# Replace values in the preProcessed hex string
					#sectionChunks = [ chunk.replace(' ', '') for chunk in sectionChunks ]
					preProcessedHex = codeChange.preProcessedCode[syntaxOffset*2:(syntaxOffset+length)*2]
					newHexValue = int( preProcessedHex, 16 )
					for name in names:
						option = codeChange.mod.getConfiguration( name )
						#optionWidth = self.getOptionWidth( option['type'] )
						# mask = option.get( 'mask', '0x' + 'FF' * optionWidth )
						optType = option['type']
						optValue = CodeMod.parseConfigValue( optType, option['value'] )

						# Combine the value into the preProcessed hex
						newHexValue = newHexValue | optValue
					#newHex = hex( newHexValue )[2:]
					newHex = "{:0{}X}".format( newHexValue, length*2 ) # Casting to string and padding left to [second arg] zeros
					newHexCodeSections.append( newHex )

			else:
				print( 'Unrecognized syntax type!: ', syntaxType )

			offset += length

		# Check if this was the last section
		if syntaxOffset == codeChange.length - length:
			returnCode = 100

		# Assemble the final code using the full source (raw) code
		if requiresAssembly and codeChange.isAssembly:
			# Using the original, raw code: remove comments, replace the custom syntaxes, and assemble it into hex
			rawAssembly = []
			for line in codeChange.rawCode.splitlines():
				# Start off by filtering out comments and empty lines.
				codeLine = line.split( '#' )[0].strip()
				if not codeLine: continue
					
				if CodeLibraryParser.isSpecialBranchSyntax( codeLine ) or CodeLibraryParser.containsPointerSymbol( codeLine ) or CodeLibraryParser.containsConfiguration( codeLine ):
					# Replace with resolved code lines
					rawAssembly.append( resolvedLinesForAssembly.pop(0) )
				else:
					rawAssembly.append( codeLine )

			customCode, errors = self.assemble( '\n'.join(rawAssembly), includePaths=codeChange.mod.includePaths, suppressWarnings=True )

			if errors:
				return ( 2, 'Unable to assemble source code with custom syntaxes.\n\n' + errors )
			else:
				return ( returnCode, customCode )

		# Grab the last code section if present
		if offset != codeChange.length:
			lastSection = codeChange.preProcessedCode[offset*2:]
			newHexCodeSections.append( lastSection )

			sectionLength = len( lastSection ) / 2
			assert offset + sectionLength == codeChange.length, 'Custom code length mismatch detected! \nMod: {}\nEvaluated: {}   Calc. in Code Resolution: {}'.format( codeChange.mod.name, codeChange.length, offset + sectionLength )

		if requiresAssembly: # Yet the user's raw code is in hex form; need to assemble just the lines with custom syntax
			# Assemble the resolved lines in one group (doing it this way instead of independently in the customCodeSections loop for less IPC overhead)
			assembledResolvedCode, errors = self.assemble( '\n'.join(resolvedLinesForAssembly), beautify=True, suppressWarnings=True )
			if errors:
				return ( 3, 'Unable to assemble hex code with custom syntaxes.\n\n' + errors )

			resolvedHexCodeLines = assembledResolvedCode.split() # Split on whitespace
			offset = 0
			i = 0

			# Replace the code section placeholders with the newly assembled lines above
			for syntaxOffset, length, syntaxType, codeLine, names in codeChange.syntaxInfo:
				if syntaxOffset != offset:
					offset += syntaxOffset - offset
					i += 1

				newHexCodeSections[i] = resolvedHexCodeLines.pop( 0 )
				offset += length
				i += 1

			customCode = ''.join( newHexCodeSections )

		else: # All Special Branch Syntaxes should have been assembled and only hex should remain. Combine the new code lines back into one string
			customCode = ''.join( newHexCodeSections )

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
		else:
			useAssembler = True # Last resort, since this will take much longer

		if useAssembler:
			fullInstruction = branchInstruction + ' ' + str( branchDistance ) + '\n' # newLine char prevents an assembly error message.
			branch, errors = self.assemble( fullInstruction )
			if errors or len( branch ) != 8:
				return '60000000' # Failsafe, to prevent dol data from being corrupted with non-hex data
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
			if not all( char in hexdigits for char in ''.join(line.split()) ):
				return True

		if onlySpecialSyntaxes:
			isAssembly = True

		return isAssembly