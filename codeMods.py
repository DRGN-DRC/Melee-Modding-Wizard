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
import time
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
from basicFunctions import createFolders, removeIllegalCharacters, roundTo32, toHex, validHex, msg, printStatus, NoIndent, CodeModEncoder
from guiSubComponents import cmsg


ConfigurationTypes = { 	'int8':   'b',	'uint8':   'B',	'mask8':   'B',
						'int16': '>h',	'uint16': '>H',	'mask16': '>H',
						'int32': '>i',	'uint32': '>I',	'mask32': '>I',
						'float': '>f' }


class CodeChange( object ):

	""" Represents a single code change to be made to the game, such 
		as a single code injection or static (in-place) overwrite. """

	def __init__( self, mod, changeType, offset, origCode, rawCustomCode, annotation='', name='' ):

		self.mod = mod
		self._name = name			# Filename for this code change (without extension)
		self.type = changeType		# String; one of 'static', 'injection', 'standalone', or 'gecko'
		self.length = -1
		self.offset = offset		# String; may be a DOL offset or RAM address. Should be interpreted by one of the DOL normalization methods
		self.isAssembly = False		# Refers to the source/rawCode, not the preProcessedCode
		self.isCached = False		# Whether or not assembled hex code is available (may be a mixed .txt or binary .txt file)
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
				self.mod.errors.add( error )
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
				self.mod.errors.add( 'Invalid original hex value for code to be installed at ' + self.offset )
				self._origCode = ''
			else:
				self._origCode = filteredOriginal

			self._origCodePreprocessed = True

		return self._origCode

	@origCode.setter
	def origCode( self, code ):
		self._origCode = code
		self._origCodePreprocessed = False

	@property
	def name( self ):

		""" This name should be provided from the original file that the code came from. 
			If that is not available (e.g. for a new change), this will create one based 
			on the annotation (removing illegal characters), if available. If there is no 
			annotation, this will create a generic name based on the change type and 
			address of the code change. The file extension is not included. """

		if not self._name:
			address = self.offset
			anno = self.anno

			if anno:
				if len( anno ) > 42:
					name = anno[:39] + '...'
				elif anno:
					name = anno

				self._name = removeIllegalCharacters( name, '' )

			else: # No annotation available
				if self.type == 'static':
					self._name = 'Static overwrite at {}'.format( address )
				elif self.type == 'injection':
					self._name = 'Code injection at {}'.format( address )
				elif self.type == 'standalone':
					self._name = "SA, '{}'".format( address )
				else:
					self._name = 'Unknown code change at {}'.format( address )

		return self._name

	def getLength( self ):

		if self.length == -1:
			self.evaluate()
		
		return self.length
		
	def updateLength( self, newLength ):
		self.length = newLength
		self.origCode = '' # Will otherwise have the wrong amount of data. Will be recollected when needed
	
	def evaluate( self, reevaluate=False, silent=False ):

		""" Checks for special syntaxes and configurations, ensures configuration options are present and 
			configured correctly, and assembles source code if it's not already in hex form. Reevaluation 
			of custom code can be important if the code is changed, or the mod is saved to a new location 
			(which could potentially change import directories). """

		if self.processStatus != -1 and not reevaluate:
			return self.processStatus
		elif reevaluate:
			oldProcessedCode = self.preProcessedCode
		else:
			oldProcessedCode = ''

		#print( 'evaluating {} for {}'.format(self.offset, self.mod.name) )
		self.processStatus, codeLength, codeOrErrorNote, self.syntaxInfo, self.isAssembly = globalData.codeProcessor.evaluateCustomCode( self.rawCode, self.mod.includePaths, self.mod.configurations )

		self.updateLength( codeLength )

		# if self.isAssembly:
		# 	print( self.mod.name + ' includes ASM' )

		if self.processStatus == 0:
			self.preProcessedCode = codeOrErrorNote

			# Check to invalidate the pre-processed code cache
			if reevaluate and self.preProcessedCode != oldProcessedCode:
				self.isCached = False

		# Store a message for the user on the cause
		elif self.processStatus == 1:
			self.mod.assemblyError = True
			if self.type == 'standalone':
				self.mod.stateDesc = 'Assembly error with SF "{}"'.format( self.offset )
				self.mod.errors.add( 'Assembly error with SF "{}":\n{}'.format(self.offset, codeOrErrorNote) )
			elif self.type == 'gecko':
				address = self.rawCode.lstrip()[:8]
				self.mod.stateDesc = 'Assembly error with gecko code change at {}'.format( address )
				self.mod.errors.add( 'Assembly error with gecko code change at {}:\n{}'.format(address, codeOrErrorNote) )
			else:
				self.mod.stateDesc = 'Assembly error with custom code change at {}'.format( self.offset )
				self.mod.errors.add( 'Assembly error with custom code change at {}:\n{}'.format(self.offset, codeOrErrorNote) )
		elif self.processStatus == 2:
			self.mod.parsingError = True
			self.mod.stateDesc = 'Missing include file: {}'.format(codeOrErrorNote)
			self.mod.errors.add( 'Missing include file: {}'.format(codeOrErrorNote) )
			#self.mod.missingIncludes.append( preProcessedCustomCode ) # todo: implement a way to show these to the user (maybe warning icon & interface)
		elif self.processStatus == 3:
			self.mod.parsingError = True
			if not self.mod.configurations:
				self.mod.stateDesc = 'Unable to find configurations'
				self.mod.errors.add( 'Unable to find configurations' )
			else:
				self.mod.stateDesc = 'Configuration option not found: {}'.format(codeOrErrorNote)
				self.mod.errors.add( 'Configuration option not found: {}'.format(codeOrErrorNote) )
		elif self.processStatus == 4:
			self.mod.parsingError = True
			self.mod.stateDesc = 'Configuration option "{}" missing type parameter'.format( codeOrErrorNote )
			self.mod.errors.add( 'Configuration option "{}" missing type parameter'.format(codeOrErrorNote) )
		elif self.processStatus == 5:
			self.mod.parsingError = True
			self.mod.stateDesc = 'Unrecognized configuration option type: {}'.format(codeOrErrorNote)
			self.mod.errors.add( 'Unrecognized configuration option type: {}'.format(codeOrErrorNote) )

		if self.processStatus != 0:
			self.preProcessedCode = ''
			self.isCached = False
			if not silent:
				print( 'Error parsing code change at {}.  Error code: {}; {}'.format(self.offset, self.processStatus, self.mod.stateDesc) )

		return self.processStatus

	def loadPreProcCode( self, preProcessedCode, rawBinary ):

		""" Loads/imports cached or previously assembled (preProcessed) code and skips some steps 
			in the .evaluate() method to reduce work; most notably avoids IPC calls to command 
			line to assemble source code. This is done by loading data from the .bin or .txt files. """

		# Use this as the 'custom code' if there isn't any (no .asm file)
		if not self.rawCode.strip():
			if rawBinary and len( preProcessedCode ) <= 0x100: # This count is in nibbles rather than bytes
				self.rawCode = globalData.codeProcessor.beautifyHex( preProcessedCode, 2 )
			elif rawBinary:
				self.rawCode = globalData.codeProcessor.beautifyHex( preProcessedCode, 4 )
			else:
				self.rawCode = preProcessedCode
		
		# If loading raw binary from a bin file, there's not much needed to do here!
		if rawBinary:
			self.length = len( preProcessedCode ) / 2
			self.syntaxInfo = []
			self.isCached = True
			self.processStatus = 0
			self.preProcessedCode = preProcessedCode

			return 0

		# Loading preProcessed code from a txt file; likely has custom syntaxes mixed in that need to be evaluated
		codeLines = preProcessedCode.splitlines()
		self.isAssembly = globalData.codeProcessor.codeIsAssembly( codeLines )
		
		#assert not self.isAssembly, 'Unexpectedly found ASM when loading preProc code for {}, codeChange 0x{:X}'.format( self.mod.name, self.offset )
		# If assembly is found in this file, it's probably meant to be in the .asm file
		if self.isAssembly:
			print( 'Found assembly in supposedly pre-processed code for "{}"; code change at {}.'.format(self.mod.name, self.offset) )
			self.processStatus = -1
			self.length = -1
			return

		self.processStatus, codeLength, codeOrErrorNote, self.syntaxInfo = globalData.codeProcessor._evaluateHexcode( codeLines, self.mod.includePaths, self.mod.configurations )

		self.updateLength( codeLength )

		if self.processStatus == 0:
			self.preProcessedCode = codeOrErrorNote
			self.isCached = True

		# Store a message for the user on the cause
		elif self.processStatus == 3:
			self.mod.parsingError = True
			if not self.mod.configurations:
				self.mod.stateDesc = 'Unable to find configurations'
				self.mod.errors.add( 'Unable to find configurations' )
			else:
				self.mod.stateDesc = 'Configuration option not found: {}'.format(codeOrErrorNote)
				self.mod.errors.add( 'Configuration option not found: {}'.format(codeOrErrorNote) )
		elif self.processStatus == 4:
			self.mod.parsingError = True
			self.mod.stateDesc = 'Configuration option "{}" missing type parameter'.format( codeOrErrorNote )
			self.mod.errors.add( 'Configuration option "{}" missing type parameter'.format(codeOrErrorNote) )
		elif self.processStatus == 5:
			self.mod.parsingError = True
			self.mod.stateDesc = 'Unrecognized configuration option type: {}'.format(codeOrErrorNote)
			self.mod.errors.add( 'Unrecognized configuration option type: {}'.format(codeOrErrorNote) )

		if self.processStatus != 0:
			self.preProcessedCode = ''
			print( 'Error parsing code change at', self.offset, '  Error code: {}; {}'.format( self.processStatus, self.mod.stateDesc ) )

		return self.processStatus

	def finalizeCode( self, targetAddress, reevaluate=False ):

		""" Performs final code processing for custom code, just before saving it to the DOL or codes file. 
			The save location for the code as well as addresses for any standalone functions it might 
			require should already be known by this point, so custom syntaxes can now be resolved. User 
			configuration options are also now saved into the custom code. """

		self.evaluate( reevaluate )

		if self.mod.errors:
			msg( 'Unable to process custom code for {}; {}'.format(self.mod.name, '\n'.join(self.mod.errors)), 'Error During Pre-Processing', warning=True )
			return 5, ''

		if not self.syntaxInfo:
			returnCode = 0
			finishedCode = self.preProcessedCode
		else:
			returnCode, finishedCode = globalData.codeProcessor.resolveCustomSyntaxes( targetAddress, self )

		if returnCode != 0 and returnCode != 100: # In cases of an error, 'finishedCode' will include specifics on the problem
			if len( self.rawCode ) > 250: # Prevent a very long user message
				codeSample = self.rawCode[:250] + '\n...'
			else:
				codeSample = self.rawCode
			errorMsg = 'Unable to process custom code for {}:\n\n{}\n\n{}'.format( self.mod.name, codeSample, finishedCode )
			msg( errorMsg, 'Error Resolving Custom Syntaxes' )
		elif not finishedCode or not validHex( finishedCode ): # Failsafe; definitely not expected
			msg( 'There was an unknown error while processing the following custom '
				 'code for {}:\n\n{}'.format(self.mod.name, self.rawCode), 'Error During Final Code Processing', warning=True )
			returnCode = 6

		return returnCode, finishedCode


class CodeMod( object ):

	""" Container for all of the information on a code-related game mod. May be sourced from 
		code stored in the standard MCM format, or the newer ASM Mod Folder Structure (AMFS). """

	def __init__( self, name, auth='', desc='', srcPath='', isAmfs=False ):

		self.name = name
		self.auth = auth					# Author(s)
		self.desc = desc					# Description
		self.data = OrderedDict([])			# Keys=revision, values=list of "CodeChange" objects
		self.path = os.path.normpath( srcPath )		# Root folder path that contains this mod
		self.type = 'static'				# An overall type (matches change.types)
		self.state = 'disabled'
		self.category = ''
		self.stateDesc = ''					# Describes reason for the state. Shows as a text status on the mod in the GUI
		self.configurations = OrderedDict([])		# Will be a dict of option dictionaries.	  Required keys: type, value, default
																								# Optional keys: annotation, range, mask, members, hidden
		self.isAmfs = isAmfs
		self.isMini = False					# todo; replace this and above bool with a storeFormat Enum if this format is kept
		self.webLinks = []					# A list of tuples, with each of the form ( URL, comment )
		self.fileIndex = -1					# Position within a .txt file; used only with MCM formatted mods (non-AMFS)
		self.includePaths = []
		self.currentRevision = ''			# Switch this to set the default revision used to add or get code changes
		self.guiModule = None

		self.assemblyError = False
		self.parsingError = False
		#self.missingIncludes = []			# Include filesnames detected to be required by the assembler
		self.errors = set()

	def setState( self, newState, statusText='', updateControlPanelCounts=True ):

		self.state = newState

		if self.guiModule:
			try:
				self.guiModule.setState( newState, statusText, updateControlPanelCounts )
			except:
				pass # May not be currently displayed in the GUI

	def setCurrentRevision( self, revision ):

		""" Creates a new code changes list in the data dictionary, and sets 
			this mod's default revision for getting or adding code changes. """

		if revision not in self.data:
			self.data[revision] = []

		self.currentRevision = revision

	def getCodeChanges( self, forAllRevisions=False, revision='' ):

		""" Gets all code changes required for a mod to be installed. """

		codeChanges = []

		if forAllRevisions:
			for changes in self.data.values():
				codeChanges.extend( changes )

		elif revision:
			# Get code changes that are applicable to all revisions, as well as those applicable to just the requested revision
			codeChanges.extend( self.data.get('ALL', []) )
			codeChanges.extend( self.data.get(revision, []) )

		else:
			# Get code changes that are applicable to all revisions, as well as those applicable to just the currently set revision
			codeChanges.extend( self.data.get('ALL', []) )
			codeChanges.extend( self.data.get(self.currentRevision, []) )

		return codeChanges

	def _normalizeCodeImport( self, customCode, annotation='' ):

		""" Normalize custom code import; ensure it's a string, removing
			leading and trailing whitespace, and create an annotation 
			from the code if one isn't provided. """

		if customCode:
			# Collapse the list of collected code lines into one string, removing leading & trailing whitespace
			if isinstance( customCode, list ):
				customCode = '\n'.join( customCode )
			customCode = customCode.strip()

			# See if we can get an annotation
			if not annotation:
				firstLine = customCode.splitlines()[0].rstrip()

				if firstLine.startswith( '#' ):
					annotation = firstLine.strip( '#' ).lstrip()

		else: # Could still be an empty list. Make sure it's a string
			customCode = ''

		return customCode, annotation

	def addStaticOverwrite( self, offsetString, customCode, origCode='', annotation='', name='' ):
		# Collapse the list of collected code lines into one string, removing leading & trailing whitespace
		customCode, annotation = self._normalizeCodeImport( customCode, annotation )

		# Add the code change
		codeChange = CodeChange( self, 'static', offsetString, origCode, customCode, annotation, name )
		self.data[self.currentRevision].append( codeChange )

		return codeChange

	def addInjection( self, offsetString, customCode, origCode='', annotation='', name='' ):
		# Collapse the list of collected code lines into one string, removing leading & trailing whitespace
		customCode, annotation = self._normalizeCodeImport( customCode, annotation )

		# Add the code change
		codeChange = CodeChange( self, 'injection', offsetString, origCode, customCode, annotation, name )
		self.data[self.currentRevision].append( codeChange )

		if self.type == 'static': # 'static' is the only type that 'injection' can override.
			self.type = 'injection'

		return codeChange

	def addGecko( self, customCode, annotation='', name='' ):

		""" This is for Gecko codes that could not be converted into strictly static 
			overwrites and/or injection mods. These will require the Gecko codehandler. """
			
		# Collapse the list of collected code lines into one string, removing leading & trailing whitespace
		customCode, annotation = self._normalizeCodeImport( customCode, annotation )

		# Add the code change
		codeChange = CodeChange( self, 'gecko', '', '', customCode, annotation, name )
		self.data[self.currentRevision].append( codeChange )

		self.type = 'gecko'

		return codeChange

	def addStandalone( self, standaloneName, standaloneRevisions, customCode, annotation='', name='' ):
		# Collapse the list of collected code lines into one string, removing leading & trailing whitespace
		customCode, annotation = self._normalizeCodeImport( customCode, annotation )

		# Add the code change for each revision that it was defined for
		codeChange = CodeChange( self, 'standalone', standaloneName, '', customCode, annotation, name )
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

	def clearErrors( self ):
		self.assemblyError = False
		self.parsingError = False
		self.stateDesc = ''
		self.errors.clear()

	def validateConfigurations( self ):

		""" Ensures all configurations options include at least 'type', 'value', and 'default' parameters. 
			Removes the configuration option from the dictionary if any of these are missing. """

		assert isinstance( self.configurations, dict ), 'Invalid mod configuration! The configurations property should be a dictionary.'

		badConfigs = []

		for configName, dictionary in self.configurations.items():
			if 'type' not in dictionary:
				self.parsingError = True
				self.stateDesc = 'Configuration option "{}" missing type parameter'.format( configName )
				self.errors.add( 'Configuration option "{}" missing type parameter'.format(configName) )
				badConfigs.append( configName )
			if 'value' not in dictionary:
				self.parsingError = True
				self.stateDesc = 'Configuration option "{}" missing value parameter'.format( configName )
				self.errors.add( 'Configuration option "{}" missing value parameter'.format(configName) )
				badConfigs.append( configName )
			if 'default' not in dictionary:
				self.parsingError = True
				self.stateDesc = 'Configuration option "{}" missing default parameter'.format( configName )
				self.errors.add( 'Configuration option "{}" missing default parameter'.format(configName) )
				badConfigs.append( configName )

		# Remove bad configurations to prevent creating other bugs in the program
		if badConfigs:
			for config in badConfigs:
				del self.configurations[config]

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

		return self.configurations.get( name )

	def getConfigValue( self, name ):
		return self.configurations[name]['value']

	@staticmethod
	def parseConfigValue( optionType, value ):

		""" Normalizes value input that may be a hex/decimal string or an int/float literal
			to an int or float. The source value type may not be consistent due to
			varying sources (i.e. from an MCM format file or AMFS config/json file). """

		if not isinstance( value, (int, float, long) ): # Need to typecast to int or float
			if '0x' in value: # Convert from hex using base 16
				value = int( value, 16 )
			elif optionType == 'float':
				value = float( value )
			else: # Assume decimal value
				value = int( value )

		return value
	
	def restoreConfigDefaults( self ):

		""" Restores all configuration values to the mod's default values. """

		for dictionary in self.configurations.values():
			dictionary['value'] = dictionary['default']

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

	def assessForErrors( self, dol=None, silent=False ):
		
		""" Evaluates this mod's custom code for assembly errors 
			and [optionally] checks for valid DOL offsets. """

		for codeChanges in self.data.values():
			for change in codeChanges:
				# Filter out SAs and Gecko codes
				if change.type == 'standalone' or change.type == 'gecko':
					continue

				# Check if the RAM Address or DOL Offset is valid
				if dol:
					error = dol.normalizeDolOffset( change.offset, 'string' )[1]
					if error:
						self.parsingError = True
						self.errors.add( error )

				# Check for assembly errors
				change.evaluate( True, silent )

	def assessForConflicts( self, silent=False, revision='', dol=None ):

		""" Evaluates this mod's changes to look for internal overwrite conflicts 
			(i.e. more than one change that affects the same code space). 
			Returns True or False on whether a conflict was detected. """

		conflictDetected = False
		modifiedRegions = []

		for change in self.getCodeChanges( revision=revision ):
			# Filter out SAs and Gecko codes
			if change.type == 'standalone' or change.type == 'gecko':
				continue

			# Ensure a RAM address is available or can be determined
			ramAddress, errorMsg = dol.normalizeRamAddress( change.offset )
			if ramAddress == -1:
				if not revision:
					revision = self.currentRevision
				warningMsg = 'Unable to get a RAM Address for the code change at {} ({});{}.'.format( change.offset, revision, errorMsg.split(';')[1] )
				if not silent:
					msg( warningMsg, 'Invalid DOL Offset or RAM Address', warning=True )
				self.stateDesc = 'Invalid Offset or Address'
				self.errors.add( warningMsg )
				break

			if change.type == 'injection':
				addressEnd = ramAddress + 4
			else:
				addressEnd = ramAddress + change.getLength()

			# Check if this change overlaps other regions collected so far
			for regionStart, codeLength in modifiedRegions:
				regionEnd = regionStart + codeLength

				if ramAddress < regionEnd and regionStart < addressEnd: # The regions overlap by some amount.
					conflictDetected = True
					break

			# No overlap, store this region this change affects for the next iterations
			if change.type == 'injection':
				modifiedRegions.append( (ramAddress, 4) )
			else: # Static overwrite
				modifiedRegions.append( (ramAddress, change.length) )
			
			if conflictDetected:
				break

		if conflictDetected:
			# Construct a warning message to the user
			if regionStart == ramAddress:
				dolOffset = dol.normalizeDolOffset( change.offset, 'string' )[0]
				warningMsg = '{} has code that conflicts with itself. More than one code change modifies code at 0x{:X} ({}).'.format( self.name, ramAddress, dolOffset )
			else:
				oldChangeRegion = 'Code Start: 0x{:X},  Code End: 0x{:X}'.format( regionStart, regionEnd )
				newChangeRegion = 'Code Start: 0x{:X},  Code End: 0x{:X}'.format( ramAddress, addressEnd )

				warningMsg = ('{} has code that conflicts with itself. These two code changes '
							'overlap with each other:\n\n{}\n{}').format( self.name, oldChangeRegion, newChangeRegion )
			
			if not silent:
				msg( warningMsg, 'Code Conflicts Detected', warning=True )
			self.stateDesc = 'Code Conflicts Detected'
			self.errors.add( warningMsg )

		return conflictDetected

	def diagnostics( self, level=5, dol=None, silent=True ):

		if not dol and level == 1:
			# Get the DOL file
			try:
				dol = globalData.getVanillaDol()
			except Exception as err:
				if not silent:
					printStatus( 'Unable to get DOL to assess code offsets/addresses; {}'.format(err.message), warning=True )

		self.assessForErrors( dol, silent )

		if dol and level < 5:
			for revision in self.data.keys():
				self.assessForConflicts( silent, revision, dol )

	def validateWebLink( self, origUrlString ):

		""" Validates a given URL (string), partly based on a whitelist of allowed domains. 
			Returns a urlparse object if the url is valid, or None (Python default) if it isn't. """

		try:
			potentialLink = urlparse.urlparse( origUrlString )
		except Exception as err:
			print( 'Invalid link detected for "{}": {}'.format(self.name, err) )
			return

		if not potentialLink.scheme:
			print( 'Invalid link detected for "{}" (no scheme): {}'.format(self.name, origUrlString) )

		elif potentialLink.netloc == 'youtu.be':
			potentialLink.domain = 'youtube'
			return potentialLink

		# Check the domain against the whitelist. netloc will be something like "youtube.com" or "www.youtube.com"
		netlocParts = potentialLink.netloc.split( '.' )
		if netlocParts[-2] not in ( 'smashboards', 'github', 'youtube' ) or netlocParts[-1] != 'com':
			print( 'Invalid link detected for "{}" (domain not allowed): {}'.format(self.name, origUrlString) )

		else:
			potentialLink.domain = netlocParts[-2]
			return potentialLink

	def buildModString( self ):

		""" Builds a string to store/share this mod in MCM's original, text-file code format. 
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
					comment = comment.lstrip()
					if comment.startswith( '#' ):
						titleLine += ' ' + comment
					else:
						titleLine += ' # ' + comment
				headerLines.append( titleLine )

				for components in members:
					if len( components ) == 2:
						name, value = components
						headerLines.append( '        {}: {}'.format(value, name) )
					else:
						name, value, comment = components
						line = '        {}: {}'.format( value, name )
						if comment: # Expected to still have "#" prepended
							line += ' ' + comment.lstrip()
						headerLines.append( line )

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
				newHex = '\n'.join( change.rawCode.strip().splitlines() ) # Normalizes line separators
				if not newHex:
					continue

				if change.type in ( 'static', 'injection' ):
					change.evaluate( True )
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

	def buildGeckoString( self, vanillaDol, createForGCT ):

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

	def sameSaveLocation( self, mod ):

		""" Checks if a given mod has the same save location as this one. """

		if self.isMini and mod.isMini:
			if self.path == mod.path:
				return True

		elif self.isAmfs and mod.isAmfs:
			if self.path == mod.path:
				return True

		else: # MCM format
			if self.fileIndex == mod.fileIndex and self.path == mod.path:
				return True

		return False

	def saveInGeckoFormat( self, savePath ):

		codeString = self.buildGeckoString( globalData.getVanillaDol(), False )
		if not codeString:
			return False

		try:
			with open( savePath, 'a' ) as geckoFile:
				geckoFile.write( codeString )
		except:
			return False

		return True

	def saveInMcmFormat( self, savePath='', showErrors=True, insert=False ):

		""" Saves this mod to a text file in MCM's basic mod format. If the given file path 
			already contains mods, the mod of the current index (self.fileIndex) will be replaced. 
			If 'insert' is True, the mod will be inserted into that position instead (above existing index). 
			If the current index is -1, this mod will be added at the end of the file. """

		# Set this mod's save location so that subsequent saves will automatically go to this same place
		# Do this first in any case, in case this method fails
		self.isMini = False
		self.isAmfs = False
		if savePath:
			self.path = savePath

		# Rebuild the include paths list, using this new file for one of the paths
		modsFolderIncludePath = os.path.join( globalData.getModsFolderPath(), '.include' )
		rootFolderIncludePath = os.path.join( globalData.scriptHomeFolder, '.include' )
		self.includePaths = [ os.path.dirname(self.path), modsFolderIncludePath, rootFolderIncludePath ]

		# Append this mod to the end of the target Mod Library text file (could be a new file, or an existing one).
		try:
			modString = self.buildModString()

			try:
				# Get contents of an existing file
				with open( self.path, 'r' ) as modFile:
					fileContents = modFile.read()
				
				# Add to the end of the file
				if fileContents and self.fileIndex == -1:
					# Get the file index for this mod and prepend a separator
					self.fileIndex = len( fileContents.split( '-==-' ) )
					modString = fileContents + '\n\n\n\t-==-\n\n\n' + modString

				# Insert at the current index (preserves existing mod at that index)
				elif fileContents and insert:
					mods = fileContents.split( '-==-' )
					
					mods = mods[:self.fileIndex] + [modString] + mods[self.fileIndex:]
					mods = [code.strip() for code in mods] # Removes the extra whitespace around mod strings.
					modString = '\n\n\n\t-==-\n\n\n'.join( mods )

					# Update the index of other mods already loaded from this file
					for mod in globalData.codeMods:
						if mod.path == self.path and mod.fileIndex >= self.fileIndex:
							mod.fileIndex += 1

				# Replace the current index
				elif fileContents:
					mods = fileContents.split( '-==-' )
					
					# Replace the old mod, reformat the space in-between mods, and recombine the file's text.
					mods[self.fileIndex] = modString
					mods = [code.strip() for code in mods] # Removes the extra whitespace around mod strings.
					modString = '\n\n\n\t-==-\n\n\n'.join( mods )

				# No prior file contents to save; just save the current mod
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
		self.isMini = False
		self.isAmfs = True
		self.fileIndex = -1
		if savePath:
			self.path = savePath

		# Rebuild the include paths list, using this new file for one of the paths
		modsFolderIncludePath = os.path.join( globalData.getModsFolderPath(), '.include' )
		rootFolderIncludePath = os.path.join( globalData.scriptHomeFolder, '.include' )
		self.includePaths = [ self.path, modsFolderIncludePath, rootFolderIncludePath ]

		# Create the folder(s) if they don't exist
		createFolders( self.path )

		# Build the JSON file data
		jsonData = {
			'codes': [
				OrderedDict( [
					( 'name', self.name ),
					( 'authors', [name.strip() for name in self.auth.split(',') ] ),
					( 'description', self.desc.splitlines() ),
					( 'category', self.category )
				] )
			]
		}

		# Set an overall revision if there are only changes for one available
		if len( self.data ) == 1:
			jsonData['codes'][0]['revision'] = self.data.keys()[0]

		# Add configuration definitions if present
		if self.configurations:
			# Format member lists such that name/value/comments are on the same line for better readability
			configs = {}
			for configName, configDict in self.configurations.items():
				members = configDict.get( 'members' )
				if members:
					configDict['members'] = [ NoIndent(elem) for elem in members ]
				configs[configName] = configDict
			jsonData['codes'][0]['configurations'] = configs

		# Add web links
		if self.webLinks:
			jsonData['codes'][0]['webLinks'] = []
			for item in self.webLinks: # Item should be a tuple of (URL, comment)
				jsonData['codes'][0]['webLinks'].append( item )

		jsonData['codes'][0]['build'] = []
		saveCodeCache = globalData.checkSetting( 'useCodeCache' )

		# Build the list of code change dictionaries
		for revision, changes in self.data.items():
			for change in changes:
				change.evaluate( reevaluate=True )
				changeDict = {}

				# Skip empty/unfinished changes
				if not change.rawCode.strip():
					print( 'No custom code to save for {}, code change {}'.format(self.name, change.offset) )
					continue

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

					# Add PreProc or binary code
					# if not change.syntaxInfo:
					# changeDict['binary'] = change.preProcessedCode

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
					# Create filepaths for the json and for the file write operation
					relativePath = os.path.join( '.', change.name ) # No extension
					fullPath = os.path.join( self.path, change.name ) # No extension

					# Create the file(s)
					success = self.writeCustomCodeFiles( change, fullPath, allowBinary=saveCodeCache )
					if not success:
						continue

					changeDict['sourceFile'] = relativePath + '.asm'

				# Add a revision for this change if dealing with multiple of them
				if len( self.data ) > 1:
					changeDict['revision'] = revision

				jsonData['codes'][0]['build'].append( changeDict )

		# Save the codes.json file
		try:
			jsonPath = os.path.join( self.path, 'codes.json' )
			with open( jsonPath, 'w' ) as jsonFile:
				json.dump( jsonData, jsonFile, cls=CodeModEncoder, indent=4 )
		except Exception as err:
			print( 'Unable to create "codes.json" file; ' )
			print( err )
			return False

		return True

	def constructHeader( self, change, longHeader ):

		if longHeader:
			return ( '####################################\n'
					 '# Address: ' + change.offset + '\n'
					 '# Author:  ' + self.auth + '\n'
					 '####################################\n\n' )
		else:
			return '# To be inserted at ' + change.offset + '\n\n'

	def writeCustomCodeFiles( self, change, sourcePath, longHeader=False, allowBinary=True ):

		""" Used for the AMFS and Mini formats. 
			An assembly (.asm) file should be saved if the custom code is assembly, or 
			the code could not be pre-processed. Successfully pre-processed code may have 
			custom syntax still within it, in which case it is saved to a text file. Or it 
			is saved to a binary file if it is finished, purely-hex data. If longHeader is 
			True, it's assumed the file header (and the assembly file itself) are both required. 
			And if the assembly file is created but the custom code within it is raw hex, 
			there is no need to create the binary file. """

		header = self.constructHeader( change, longHeader )
		forceSavePreProc = False

		# Determine the type of source file to create
		if self.isMini:
			if change.type == 'static':
				extension = '.s'
			else:
				extension = '.asm'

		# Check if the original source code should be saved for AMFS
		elif change.isAssembly or not change.preProcessedCode:
			extension = '.asm'
		else:
			extension = ''

		if extension:
			# Create a source file for this custom code
			try:
				code = change.rawCode.strip()

				with open( sourcePath + extension, 'w' ) as newFile:
					# Save a header only if one isn't already present
					if not code.startswith('##########') and not code.startswith('# To be insert'):
						newFile.write( header )
					newFile.write( code )

			except Exception as err:
				print( 'Unable to create "' + sourcePath + extension + '"' )
				print( err )
				return False

			if not change.preProcessedCode: # Done!
				return True

		elif change.syntaxInfo: # Contains custom syntax; cannot yet be fully assembled
			forceSavePreProc = True
		elif '#' in change.rawCode: # Prevent comments from being lost (no source file in this case)
			forceSavePreProc = True

		if allowBinary or forceSavePreProc:
			success = self.saveCache( change, forceSavePreProc, header, longHeader, sourcePath, True )
		else:
			success = True

		return success

	def saveCache( self, change, forceSavePreProc=False, header='', longHeader=False, sourcePath='', cleanup=False ):

		""" Saves assembled cache files for a code change for faster code installation performance. 
			Saves preProcessed code that includes custom syntaxes mixed in to a code .txt file, or 
			raw binary to a .bin file. Returns True/False on success. """

		if not header:
			header = self.constructHeader( change, longHeader )

		if not sourcePath:
			sourcePath = os.path.join( self.path, change.name ) # No extension

		# Ignore for short changes that reside solely within codes.json
		if self.isAmfs and change.type == 'static' and change.length <= 16:
			return True

		savePreProc = False
		saveBinary = True

		# If the custom code is already pure hex (configs not supported in Mini)
		# then prevent creating a binary file, which would be redundant.
		if self.isMini and not change.isAssembly:
			saveBinary = False

		elif change.syntaxInfo:
			# Can't save binary file (due to custom syntax)
			saveBinary = False

			if change.isAssembly:
				# Save mixed preProcessed code file (.txt)
				savePreProc = True

			elif not cleanup:
				# Nothing left to do
				change.isCached = False
				return False

		# Check to save a pre-processed code file (HEX mixed with comments and/or custom syntax)
		if savePreProc or forceSavePreProc:
			if change.isAssembly:
				if change.syntaxInfo:
					# Mix custom syntax lines back into the pure hex
					try:
						hexString = globalData.codeProcessor.restoreCustomSyntaxInHex( change.preProcessedCode, change.syntaxInfo, change.length )
					except Exception as err:
						print( 'Unable to build PreProcessed code string; {}'.format(err) )
						hexString = ''

				# The preProcessed code is pure hex; no custom syntax used
				elif len( change.preProcessedCode ) <= 0x100: # This count is in nibbles rather than bytes
					hexString = globalData.codeProcessor.beautifyHex( change.preProcessedCode, 2 )
				else:
					hexString = globalData.codeProcessor.beautifyHex( change.preProcessedCode, 4 )
			else:
				hexString = change.rawCode.strip()

			if hexString:
				try:
					with open( sourcePath + '.txt', 'w' ) as newFile:
						# Save a header only if one isn't already present
						if not hexString.startswith('##########') and not hexString.startswith('# To be insert'):
							newFile.write( header )
						newFile.write( hexString )

				except Exception as err:
					print( 'Unable to create "' + sourcePath + '.txt"' )
					print( err )
					change.isCached = False
					return False
		elif cleanup:
			try:
				if os.path.exists( sourcePath + '.txt' ):
					os.remove( sourcePath + '.txt' )
			except Exception as err:
				print( 'Unable to delete {} cache file; {}'.format(sourcePath, err) )

		# Check to save a raw binary/data file
		if saveBinary:
			try:
				binData = bytearray.fromhex( change.preProcessedCode )
				with open( sourcePath + '.bin', 'wb' ) as newFile:
					newFile.write( binData )
			except Exception as err:
				print( 'Unable to create "' + sourcePath + '.bin"' )
				print( err )
				change.isCached = False
				return False
		elif cleanup: # Delete leftover files if not intending to save them
			try:
				if os.path.exists( sourcePath + '.bin' ):
					os.remove( sourcePath + '.bin' )
			except Exception as err:
				print( 'Unable to delete {} cache file; {}'.format(sourcePath, err) )

		change.isCached = True

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

		self.isMini = True
		self.isAmfs = False

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

	# def filenameForChange( self, change ):

	# 	""" Creates a file name from the annotation, removing illegal 
	# 		characters. Or, if an annotation is not available, creates 
	# 		one based on the change type and address of the code change. 
	# 		The file extension is not included. """

	# 	cType = change.type
	# 	address = change.offset
	# 	anno = change.anno

	# 	if anno:
	# 		if len( anno ) > 42:
	# 			name = anno[:39] + '...'
	# 		elif anno:
	# 			name = anno

	# 		name = removeIllegalCharacters( name, '' )

	# 	else: # No annotation available
	# 		if cType == 'static':
	# 			name = 'Static overwrite at {}'.format( address )
	# 		elif cType == 'injection':
	# 			name = 'Code injection at {}'.format( address )
	# 		elif cType == 'standalone':
	# 			name = "SA, '{}'".format( address )
	# 		else:
	# 			name = 'Unknown code change at {}'.format( address )

	# 	return name


class CodeLibraryParser():

	""" The primary component for loading a Code Library. This will identify and parse the 
		standard .txt file mod format, as well as the AMFS structure. The primary .include 
		paths for import statements are also set here. 

		Include path priority during assembly:
			1) The current working directory (implicit; usually the program root folder)
			2) Directory of the mod's code file (or the code's root folder with AMFS)
			3) The current Code Library's ".include" directory
			4) The program root folder's ".include" directory """

	def __init__( self ):

		self.stopToRescan = False
		self.includePaths = []
		self.modNames = set()
		self.codeMods = []

		# Preliminary check for the Gecko codehandler (there's still a try/catch when reading this later)
		if os.path.exists( globalData.paths['codehandler'] ):
			self.codehandlerFound = True
		else:
			self.codehandlerFound = False

	def processDirectory( self, folderPath, includePaths=None ):

		""" Starting point for processing a Code Library. Recursively processes sub-folders. """

		if includePaths:
			self.includePaths = includePaths
		includePaths = [ folderPath ] + self.includePaths # Create a new list, adding the current folder

		# If the given path is actually a text file, parse it exclusively as an MCM library
		if folderPath.lower().endswith( '.txt' ):
			# Collect all mod definitions from this file
			self.parseModsLibraryFile( folderPath, includePaths )
			return

		parentFolderPath, thisFolderName = os.path.split( folderPath )
		parentFolderName = os.path.split( parentFolderPath )[1]
		itemsInDir = os.listdir( folderPath ) # May be files or folders

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
			if codeline == 'PAL' or codeline == 'ALL':
				isGeckoHeader = True

			# All other conditions should include a version number (e.g. '1.02')
			elif '.' in codeline[1:]: # Excludes first character, which may be a period indicating an assembly directive
				# Check for a short version number string (still old formatting), e.g. '1.00', '1.01'
				if len( codeline ) == 4:
					isGeckoHeader = True

				elif 'NTSC' in codeline or 'PAL' in codeline:
					isGeckoHeader = True # Should be the new syntax, e.g. 'NTSC 1.02'

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
									configurationDict['range'] = ( start.strip(), end.strip() )

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
							mod.errors.add( 'Configurations parsing error; {}'.format(err) )
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
					#changeType = 'gecko'

					# Remember the version that subsequent code lines are for
					# mod.setCurrentRevision( self.normalizeRegionString(line) )
					# continue

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
						mod.stateDesc = 'Improper mod formatting'
						mod.errors.add( 'Improper mod formatting' )

					# Empty current temporary data containers for code
					customCode = []
					longStaticOriginal = []
					standaloneName = ''
					standaloneRevisions = []
					changeType = 'static'

				# Check for the divider between long static overwrite original and new code.
				elif line == '->' and changeType == 'longStaticOrig':
					changeType = 'longStaticNew'
					continue

				if isVersionHeader:
					# Remember the version that subsequent code lines are for
					mod.setCurrentRevision( self.normalizeRegionString(headerStringStart) )

					if self.isGeckoCodeHeader( line ):
						changeType = 'gecko'

				elif self.isStandaloneFunctionHeader( line ):
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
					
						offsetString = hexCodes[0].replace( '0x', '' ) # Hex indicator only temporarily removed
						totalValues = len( hexCodes )

						if totalValues == 1: # This is the header for a Long static overwrite (e.g. "1.02 ----- 0x804d4d90 ---"). (hexCodes would actually be just ["0x804d4d90"])
							changeType = 'longStaticOrig'

						elif totalValues == 2: # Should have an offset and an origHex value; e.g. from a line like "1.02 ------ 804D7A4C --- 00000000 ->"
							origHex = ''.join( hexCodes[1].replace('0x', '').split() ) # Remove whitespace

						elif totalValues > 2: # Could be a standard static overwrite (1-liner), long static overwrite, or an injection mod
							origHex = ''.join( hexCodes[1].replace('0x', '').split() ) # Remove whitespace
							newHex = hexCodes[2]

							if newHex.lower() == 'branch':
								changeType = 'injection'
							else:
								customCode.append( newHex + lineComments )

						# Validate the offset/address string and add the hex identifier
						if validHex( offsetString ):
							offsetString = '0x' + offsetString
						else:
							if changeType == 'injection':
								changeDesc = 'code injection'
							elif changeType == 'longStaticOrig':
								changeDesc = 'long static overwrite'
							else:
								changeDesc = 'static overwrite'
							mod.errors.add( 'Invalid (non-hex) offset detected with a ' + changeDesc )

					# Continue collecting code lines
					elif not isVersionHeader:
						if changeType == 'longStaticOrig':
							longStaticOriginal.append( line )

						else: # This may be an empty line/whitespace. Only adds this if there is already custom code accumulating for something.
							customCode.append( rawLine )

			# End of per-line loop for the current mod (all lines have now been gone through).
			# If there is any code left, save it to the last revision's last code change.
			if customCode != [] or standaloneRevisions != []:
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
					mod.stateDesc = 'Improper mod formatting'
					mod.errors.add( 'Improper mod formatting' )

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
		returnCode, address, author, customCode, preProcCode, rawBin, anno = self.getCustomCodeFromFile( sourceFile, mod, True, modName )

		if author:
			mod.auth = author

		# Check for errors
		if returnCode == 0 and not address:
			mod.parsingError = True
			mod.stateDesc = 'Missing address for "{}"'.format( sourceFile )
			mod.errors.add( 'Unable to find an address' )

		codeChange = mod.addStaticOverwrite( address, customCode, '', anno, modName )
		if preProcCode:
			codeChange.loadPreProcCode( preProcCode, rawBin )
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
		returnCode, address, author, customCode, preProcCode, rawBin, anno = self.getCustomCodeFromFile( sourceFile, mod, True, modName )

		if author:
			mod.auth = author

		# Check for errors
		if returnCode == 0 and not address:
			mod.parsingError = True
			mod.stateDesc = 'Missing address for "{}"'.format( sourceFile )
			mod.errors.add( 'Unable to find an address' )

		codeChange = mod.addInjection( address, customCode, '', anno, modName )
		if preProcCode:
			codeChange.loadPreProcCode( preProcCode, rawBin )
		self.storeMod( mod )

	def storeMod( self, mod ):

		""" Store the given mod, and perfom some basic validation on it. """

		if not mod.data:
			mod.stateDesc = 'Missing mod data'
			mod.errors.add( 'Missing mod data; may be defined incorrectly' )
		elif mod.name in self.modNames:
			mod.stateDesc = 'Duplicate mod'
			mod.errors.add( 'Duplicate mod; more than one by this name in library' )
		elif mod.type == 'gecko' and not self.codehandlerFound:
			mod.stateDesc = 'Missing codehandler'
			mod.errors.add( 'The Gecko codehandler.bin file could not be found' )

		self.codeMods.append( mod )
		self.modNames.add( mod.name )

	def parseGeckoCode( self, codeLines ):

		""" Currently only supports Gecko code types 04, 06, and C2. Returns title, newAuthors, 
			description, and codeChanges. 'codeChanges' will be a list of tuples, with each 
			tuple of the form ( changeType, address, codeLength, customCodeLines ). """

		title = authors = ''
		description = []
		codeChangeTuples = []
		codeBuffer = [ '', -1, '', [], 0, '' ] # Temp staging area while code lines are collected before being submitted to the above codeChangeTuples list
		processedHex = ''

		for line in codeLines:
			line = line.strip()
			if not line: continue # Skip whitespace lines

			elif line.startswith( '*' ): # A 'note' (a form of comment) that shows up in the Dolphin GUI for a description
				description.append( line[1:] )
				continue

			elif line.startswith( '$' ) or ( '[' in line and ']' in line ):
				line = line.lstrip( '$' )

				# Sanity check; the buffer should be empty if a new code change is starting
				if codeBuffer[0]:
					changeType, _, ramAddress, lines, codeLength, annotation = codeBuffer
					codeChangeTuples.append( (changeType, ramAddress, codeLength, lines, annotation) )
					print( 'Warning: the Gecko code change for address {:X} appears to be malformed!'.format(ramAddress) )
					codeBuffer = [ '', -1, '', [], 0, '' ]

				if title: # It's already been set, meaning this is another separate code
					break

				elif '[' in line and ']' in line:
					titleParts = line.split( '[', 1 )
					title = titleParts[0].strip()
					authors = titleParts[-1].split( ']' )[0].strip()

				else:
					title = line

				continue

			# Should be raw hex from this point on
			lineParts = line.split( '#', 1 )
			if len( lineParts ) == 2:
				codeOnly, annotation = lineParts
				annotation = annotation.strip()
			else:
				codeOnly = lineParts[0]
				annotation = ''
			processedHex = ''.join( codeOnly.split( '*' )[0].split() ).upper() # Removes all comments and whitespace

			if codeBuffer[0]: # Multi-line code collection is in-progress
				changeType, totalBytes, ramAddress, _, collectedCodeLength, annotation = codeBuffer

				newHexLength = len( processedHex ) / 2 # Divide by 2 to count by bytes rather than nibbles
				codeBuffer[3].append( line )
				codeBuffer[4] += newHexLength

				# Check if this is the last line to collect from for this code change
				if collectedCodeLength + newHexLength >= totalBytes:
					# Add the finished code change to the list, and reset the buffer
					codeChangeTuples.append( (changeType, ramAddress, codeBuffer[4], codeBuffer[3], annotation) )
					codeBuffer = [ '', -1, '', [], 0, '' ]

				continue

			# Processing a line of code for a new code change from this point on
			nib1 = int( line[0], 16 )
			nib2 = int( line[1], 16 )
			if nib1 & 1 == 1: # ba/po bit is set
				raise Exception( 'The ba/po bit is set for this code change (which is not supported): ' + processedHex[:8] )
			opCode = ( (nib1 & 0b1110) << 4 ) + (nib2 & 0b1110)
			if nib2 & 1 == 1: # First bit of address is set
				ramAddress = '0x81' + line[2:8]
			else:
				ramAddress = '0x80' + line[2:8]

			if opCode == 0: # A Static Overwrite (1-byte repeat)
				byteCount = int( processedHex[8:12], 16 ) + 1
				customCode = processedHex[14:16] * byteCount
				codeChangeTuples.append( ('static', ramAddress, byteCount, [customCode], annotation) )

			elif opCode == 2: # A Static Overwrite (half-word repeat)
				halfwordCount = ( int(processedHex[8:12], 16) + 1 )
				customCode = processedHex[12:16] * halfwordCount
				codeChangeTuples.append( ('static', ramAddress, halfwordCount * 2, [customCode], annotation) )

			elif opCode == 4: # A Static Overwrite (4 bytes)
				customCode = processedHex[8:16]
				codeChangeTuples.append( ('static', ramAddress, 4, [customCode], annotation) )

			elif opCode == 6: # A Long Static Overwrite
				# Set up the code buffer, which will be filled with data until it's gathered all the bytes for this change
				totalBytes = int( processedHex[8:16], 16 )
				codeBuffer = [ 'static', totalBytes, ramAddress, [], 0, annotation ]

			elif opCode == 0xC2: # An Injection
				# Set up the code buffer, which will be filled with data until it's gathered all the bytes for this change
				totalBytes = int( processedHex[8:16], 16 ) * 8 # The count in the C2 line is a number of lines, where each line should be 8 bytes
				codeBuffer = [ 'injection', totalBytes, ramAddress, [], 0, annotation ]

			else:
				raise Exception( 'Found an unrecognized Gecko opCode: ' + line.lstrip()[:2].upper() )

		# Check for any lingering code
		if codeBuffer[0]:
			# Add the finished code change to the list
			changeType, _, ramAddress, lines, codeLength, annotation = codeBuffer
			codeChangeTuples.append( (changeType, ramAddress, codeLength, lines, annotation) )
			print( 'Warning: the Gecko code change for address {:X} appears to be malformed!'.format(ramAddress) )

		# Sort the changes by address
		codeChangeTuples.sort( key=lambda codeChange: codeChange[1] )

		# Combine contiguous static overwrites
		condensedChangesList = []
		for codeChange in codeChangeTuples:
			# Add with no adjustments if this is an injection or the first code change
			if codeChange[0] == 'injection' or len( condensedChangesList ) == 0:
				condensedChangesList.append( codeChange )
				continue

			# Add with no adjustments if the last change was an injection
			lastCodeChange = condensedChangesList[-1]
			if lastCodeChange[0] == 'injection':
				condensedChangesList.append( codeChange )
				continue

			# Assessing a static overwrite; check if it's contiguous with last added overwrite
			thisRamAddress, thisCodeLength, thisCodeLines, thisAnnotation = codeChange[1:]
			lastRamAddress, lastCodeLength, lastCodeLines, lastAnnotation = lastCodeChange[1:]
			thisAddress = int( thisRamAddress, 16 )
			lastAddress = int( lastRamAddress, 16 )
			if lastAddress == thisAddress: # Duplicate!
				print( 'Warning: Duplicate address modified by Gecko code: ' + thisRamAddress )
				condensedChangesList.append( codeChange ) # Keep it for now; let the user remove one later
			elif lastAddress + lastCodeLength == thisAddress:
				# This change immediately follows the last and these two can be combined (replacing previous one)
				newCodeLength = lastCodeLength + thisCodeLength
				newCodeLines = lastCodeLines + thisCodeLines
				newAnnotation = ( lastAnnotation + '\n' + thisAnnotation ).strip()
				condensedChangesList[-1] = ( 'static', lastRamAddress, newCodeLength, newCodeLines, newAnnotation )
			else: # Non-contiguous; add this change unmodified
				condensedChangesList.append( codeChange )

		# Reformat static overwrites longer than 4 bytes to 8 bytes per line (2 blocks of 4)
		for i, codeChange in enumerate( condensedChangesList ):
			if codeChange[2] > 4 and codeChange[0] == 'static':
				newLines = []
				for ii, line in enumerate( codeChange[3] ):
					if ii % 2 == 0: # Iteration count is even
						newLines.append( line )
					else:
						newLines[-1] = newLines[-1] + ' ' + line

				codeChange = list( codeChange )
				codeChange[3] = newLines
				condensedChangesList[i] = tuple( codeChange )

		return title, authors, '\n'.join( description ), condensedChangesList

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

		if not codeSection: # Grab everything from the current folder (and subfolders). Assume .s are static overwrites, and .asm are injections
			# Typecast the authors and description lists to strings
			# authors = ', '.join( codeset['authors'] )
			# description = '\n'.join( codeset['description'] )
			
			# mod = CodeMod( codeset['name'], authors, description, fullFolder, True )

			#self.errors.add( "No 'codes' section found in codes.json" ) #todo
			msg( 'No "codes" section found in codes.json for the mod in "{}".'.format(folderPath) )
			return

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
				mod.validateConfigurations()

				# Add paths for .include ASM import statements, and web links
				mod.includePaths = includePaths
				links = codeset.get( 'webLinks', () )
				for item in links:
					if isinstance( item, (tuple, list) ):
						if len( item ) == 2:
							mod.webLinks.append( item )
					elif item != '': # Assume it's just a url without a comment
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

						elif codeType == 'inject': # Standard code injection (hex from file)
							self.parseAmfsInject( codeChangeDict, mod, annotation )

						elif codeType == 'replaceCodeBlock': # Static overwrite of variable length (hex from file)
							self.parseAmfsReplaceCodeBlock( codeChangeDict, mod, annotation )

						elif codeType == 'injectFolder': # Process a folder of .asm files; all as code injections
							self.parseAmfsInjectFolder( codeChangeDict, mod, annotation )

						elif codeType in ( 'branch', 'branchAndLink', 'binary', 'replaceBinary' ):
							mod.parsingError = True
							mod.errors.add( 'The "' + codeType + '" AMFS code type is not supported' )

						elif codeType == 'standalone': # For Standalone Functions
							self.parseAmfsStandalone( codeChangeDict, mod, annotation )

						# elif codeType == 'gecko':
						# 	self.parseAmfsGecko( codeChangeDict, mod, annotation )

						else:
							mod.parsingError = True
							mod.errors.add( 'Unrecognized AMFS code type: ' + codeType )

					self.storeMod( mod )

				else: # Build all subfolders/files
					mod.errors.add( "No 'build' section found in codes.json" )

			except Exception as err:
				if not mod: # Ill-formatted JSON, or missing basic info
					mod = CodeMod( name, '??', 'JSON located at "{}"'.format(jsonPath), folderPath, True )
					mod.category = codeset.get( 'category', primaryCategory ) # Secondary definition, per-code dict basis

				# Store an errored-out shell of this mod, so the user can notice it and know a broken mod is present
				mod.parsingError = True
				mod.errors.add( 'Unable to parse codes section; {}'.format(err) )
				self.storeMod( mod )

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
			if secondLine.startswith( '#' ) and 'author:' in secondLine.lower():
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

		# Get the full path, just without the file extension
		baseFilePath = os.path.splitext( fullAsmFilePath )[0]

		if not annotation:
			# Use the file name for the annotation (without file extension)
			annotation = os.path.basename( baseFilePath )

		# Try to get the custom/source code, and the address/offset if needed
		try:
			# Open the file in byte-reading mode (rb). Strings will then need to be encoded.
			with codecs.open( fullAsmFilePath, encoding='utf-8' ) as asmFile: # Using a different read method for UTF-8 encoding
				if parseHeader:
					offset, author = self.parseSourceFileHeader( asmFile )
				else:
					offset = ''
					author = ''

				# Collect all of the file contents
				customCode = asmFile.read().encode( 'utf-8' )

			sourceModifiedTime = os.path.getmtime( fullAsmFilePath )

		except IOError as err: # File couldn't be found
			sourceModifiedTime = 0
			offset = ''
			author = ''
			customCode = ''

		except Exception as err: # Unknown error
			print( err )
			filename = os.path.basename( fullAsmFilePath )
			mod.parsingError = True
			mod.stateDesc = 'File reading error with ' + filename
			mod.errors.add( 'Encountered an error while reading {}: {}'.format(filename, err) )
			return 5, '', '', '', '', False, annotation

		# Check for preProcessed files (.txt/.bin) and see if the source code is more recent
		if customCode:
			if not globalData.checkSetting( 'useCodeCache' ):
				# No need for reading other source files if skipping code cache
				#print( 'loading source-only for ' + mod.name + ' (cache skipped)' )
				return 0, offset, author, customCode, '', False, annotation

			# Check if the source code is newer than the assembled binary
			binaryModifiedTime = 0
			foundBin = False
			try:
				binaryModifiedTime = os.path.getmtime( baseFilePath + '.bin' )
				foundBin = True
			except:
				try:
					binaryModifiedTime = os.path.getmtime( baseFilePath + '.txt' )
				except:
					pass
			if sourceModifiedTime > binaryModifiedTime:
				print( 'loading source-only for ' + mod.name )
				# The source is newer (and the cached files should be replaced), or the bin/txt files aren't present
				return 0, offset, author, customCode, '', False, annotation
		else:
			# Just check for existance of the binary file
			foundBin = os.path.exists( baseFilePath + '.bin' )

		# Get the preProcessed code. Check for assembled binary data, and/or for a text file (partially assembled code)
		if foundBin:
			try:
				with open( baseFilePath + '.bin', 'rb' ) as binaryFile:
					contents = binaryFile.read()
					#hexString = hexlify( contents )
					#preProcessedCode = globalData.codeProcessor.beautifyHex( hexString, 4 )
					preProcessedCode = hexlify( contents )
				print( 'loading source + preProc.bin for ' + mod.name )
			except Exception as err:
				preProcessedCode = ''
		else:
			# See if we can get pre-processed code from a text file
			try:
				# Open the file in byte-reading mode (rb). Strings will then need to be encoded.
				with open( baseFilePath + '.txt', 'r' ) as preProcFile:
					preProcessedCode = preProcFile.read()
				print( 'loading source + preProc.txt for ' + mod.name )
			except Exception as err:
				preProcessedCode = ''

		# Verify custom code was collected
		if not customCode and not preProcessedCode:
			filename = os.path.basename( baseFilePath ) # Name only; no extension
			mod.parsingError = True
			print( 'Unable to find custom code for ' + filename )
			mod.errors.add( 'Missing custom for "{}"'.format(filename) )

		return 0, offset, author, customCode, preProcessedCode, foundBin, annotation

	def getAddressAndSourceFile( self, codeChangeDict, mod ):

		""" Gets and returns the address and source file for a given code change dictionary. 
			Also records any errors encountered if a value wasn't found. """

		address = codeChangeDict.get( 'address', '' )
		sourceFile = codeChangeDict.get( 'sourceFile', '' ) # Relative path

		if address and sourceFile:
			basename = os.path.basename( sourceFile )
			changeName = os.path.splitext( basename )[0]

			return address, sourceFile, changeName

		# If still here, there was a problem (both values are expected)
		mod.parsingError = True
		mod.stateDesc = 'Parsing error; insufficient code change info'

		# Record an error message for this
		if address and not sourceFile:
			if codeChangeDict['type'] == 'inject':
				mod.errors.add( 'Injection at {} missing "sourceFile" path'.format(address) )
			else:
				mod.errors.add( 'Static overwrite at {} missing "sourceFile" path'.format(address) )
		if sourceFile and not address:
			if codeChangeDict['type'] == 'inject':
				mod.errors.add( '{} injection missing its "address" value'.format(sourceFile) )
			else:
				mod.errors.add( '{} static overwrite missing its "address" value'.format(sourceFile) )
		elif not address and not sourceFile:
			# No specifics available; add a generic message while combining like messages
			for i, errMsg in enumerate( mod.errors ):
				if errMsg.endswith( 'missing "address"/"sourceFile" fields' ):
					#del mod.errors[i]
					mod.errors.remove( errMsg )
					# Parse and increase the number
					num = int( errMsg.split()[0] )
					mod.errors.add( '{} code changes are missing "address"/"sourceFile" fields'.format(num + 1) )
					break
			else: # Above loop didn't break; no prior message like this
				mod.errors.add( '1 code change is missing "address"/"sourceFile" fields' )

		return '', '', ''

	def parseAmfsInject( self, codeChangeDict, mod, annotation, fullAsmFilePath='' ):

		""" AMFS Injection; custom code sourced from an assembly file. """

		parseHeader = True

		# There will be no codeChangeDict if a source file was provided (i.e. an inject folder is being processed)
		if fullAsmFilePath: # Processing from 'injectFolder'; get address from file
			address = ''
			sourceFile = os.path.basename( fullAsmFilePath )
			changeName = ''
		else:
			address, sourceFile, changeName = self.getAddressAndSourceFile( codeChangeDict, mod )
			#fullAsmFilePath = os.path.join( mod.path, sourceFile )
			fullAsmFilePath = '\\\\?\\' + os.path.normpath( os.path.join(mod.path, sourceFile) )
			if address:
				parseHeader = False

		# Read the file for info and the custom code
		returnCode, address, _, customCode, preProcCode, rawBin, anno = self.getCustomCodeFromFile( fullAsmFilePath, mod, parseHeader, annotation )

		# Check for a missing address
		if returnCode == 0 and not address:
			# Fall back to the codes.json file (todo: always use this?)
			if codeChangeDict:
				address = codeChangeDict.get( 'address', '' )

			if not address:
				mod.parsingError = True
				mod.stateDesc = 'Missing address for "{}"'.format( sourceFile )
				mod.errors.add( 'Unable to find an address for ' + sourceFile )
				return

		codeChange = mod.addInjection( address, customCode, '', anno, changeName )
		if preProcCode:
			codeChange.loadPreProcCode( preProcCode, rawBin )

	def parseAmfsReplaceCodeBlock( self, codeChangeDict, mod, annotation ):

		""" AMFS Long Static Overwrite of variable length, with code sourced from a file. """

		address, sourceFile, changeName = self.getAddressAndSourceFile( codeChangeDict, mod )
		fullAsmFilePath = '\\\\?\\' + os.path.normpath( os.path.join(mod.path, sourceFile) )

		# Read the file for info and the custom code
		returnCode, _, _, customCode, preProcCode, rawBin, anno = self.getCustomCodeFromFile( fullAsmFilePath, mod, False, annotation )
		#if returnCode != 0:
			# mod.parsingError = True
			# mod.stateDesc = 'Parsing error; unable to get code from file'
			# mod.errors.add( "Unable to read the 'sourceFile' {}".format(sourceFile) )
		#	return

		# Store the info for this code change
		codeChange = mod.addStaticOverwrite( address, customCode, '', anno, changeName )
		if preProcCode:
			codeChange.loadPreProcCode( preProcCode, rawBin )

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
			mod.errors.add( 'Unable to find the folder "{}"'.format(fullFolderPath) )
			print( err )

	def parseAmfsInjectFolder( self, codeChangeDict, mod, annotation ):
		# Get/construct the root folder path
		sourceFolder = codeChangeDict['sourceFolder']
		sourceFolderPath = os.path.join( mod.path, sourceFolder )

		# Check recursive flag
		isRecursive = codeChangeDict.get( 'isRecursive', -1 )
		if isRecursive == -1: # Flag not found!
			mod.parsingError = True
			mod.errors.add( 'No "isRecursive" flag defined for the {} folder.'.format(sourceFolder) )
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
				mod.errors.add( 'SF for {} is missing its name property'.format(sourceFileName) )
			else:
				mod.errors.add( 'An SF is missing its name property' )

		# If a sourceFile was provided, construct the full path and get the custom code
		if not sourceFile:
			mod.parsingError = True
			mod.errors.add( 'SF {} is missing its "sourceFile" property'.format(name) )
			customCode = ''
			changeName = ''
		else:
			fullAsmFilePath = '\\\\?\\' + os.path.normpath( os.path.join(mod.path, sourceFile) )
			basename = os.path.basename( sourceFile )
			changeName = os.path.splitext( basename )[0]
			_, _, _, customCode, preProcCode, rawBin, annotation = self.getCustomCodeFromFile( fullAsmFilePath, mod, False, annotation )

		codeChange = mod.addStandalone( name, revisions, customCode, annotation, changeName )
		if preProcCode:
			codeChange.loadPreProcCode( preProcCode, rawBin )

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

		""" Rewrites a hex string to something more human-readable, displaying 8 
			bytes per line by default (2 blocks of 4 bytes, separated by a space). """

		assert blocksPerLine > 0, 'Invalid blocksPerLine given to beautifyHex: ' + str( blocksPerLine )

		code = [ rawHex[:8] ] # Start with the first block included, to prevent a check for whitespace in the loop
		divisor = blocksPerLine * 8

		for block in range( 8, len(rawHex), 8 ):

			if block % divisor != 0: # For blocksPerLine of 4, the modulo would be 0, 8, 16, 24, 0, 8...
				code.append( ' ' + rawHex[block:block+8] )
			else:
				code.append( '\n' + rawHex[block:block+8] )

		return ''.join( code ).rstrip()

	@staticmethod
	def restoreCustomSyntaxInHex( hexCode, syntaxInfo, totalLength, blocksPerLine=4 ):

		""" Swap out hex code for the original custom syntax line that it came from. 
			This creates a pre-processed hex string with custom syntax mixed in. """

		newHexCodeSections = []
		offset = 0

		# Resolve individual syntaxes to finished assembly and/or hex
		for syntaxOffset, length, syntaxType, codeLine, _ in syntaxInfo:

			# Check for and collect pre-assembled hex
			if syntaxOffset != offset:
				sectionLength = syntaxOffset - offset
				sectionCode = hexCode[offset*2:syntaxOffset*2]

				if blocksPerLine > 0:
					sectionCode = globalData.codeProcessor.beautifyHex( sectionCode, blocksPerLine )

				newHexCodeSections.append( sectionCode )
				offset += sectionLength

			if syntaxType == 'opt':
				instruction, variable = codeLine.split( ' ', 1 )
				if instruction in ( '.float', '.long', '.word', '.byte' ):
					newHexCodeSections.append( variable )
				else:
					newHexCodeSections.append( codeLine )
			else:
				newHexCodeSections.append( codeLine )
			
			offset += length

		# Grab the last code section if present
		if offset != totalLength:
			lastSection = hexCode[offset*2:]
			sectionLength = len( lastSection ) / 2

			if blocksPerLine > 0:
				lastSection = globalData.codeProcessor.beautifyHex( lastSection, blocksPerLine )

			newHexCodeSections.append( lastSection )
			assert offset + sectionLength == totalLength, 'Custom code length mismatch detected! \nEvaluated: {}   Calc. in Code Resolution: {}'.format( totalLength, offset + sectionLength )

		customCode = '\n'.join( newHexCodeSections )

		return customCode

	def buildAssemblyArgs( self, includePaths, suppressWarnings ):

		""" Constructs command line arguments for the assembler (EABI-AS). """

		args = [
				self.assemblerPath, 				# Path to the assembler binary
				"-mgekko", 							# Generate code for PowerPC Gekko (alternative to '-a32', '-mbig')
				"-mregnames", 						# Allows symbolic names for registers
				'-al', 								# Options for outputting assembled hex and other info to stdout
				'--listing-cont-lines', '100000',	# Sets the maximum number of continuation lines allowable in stdout (basically want this unlimited)
				#'--statistics',					# Prints additional assembly stats within the errors message; todo: will require some extra post processing to present this to the user
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

		""" Gets the branch operand (branch distance), and normalizes it. Essentially, this does two 
			things: strip out the link and absolute flag bits, and normalize the output value, e.g. -0x40 
			instead of 0xffffffc0. This also avoids weird results from EABI and the overhead of IPC. """

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
		
		""" Pre-processes custom code (which may be assembly or hex code) into hex data. This method parses 
			out custom MCM syntaxes and comments, and assembles the code using the PowerPC EABI if it was assembly. 
			Custom syntax information is collected during this process and replaced in the code with hex data placeholders. 
			These placeholders will be replaced with the appropriate instruction later, when the custom code is finalized. 

			Returns: ( returnCode, codeLength, preProcessedCode, customSyntaxRanges, isAssembly )

				Potential return codes:
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

	def resolveCustomSyntaxes( self, codeAddress, codeChange ):

		""" Performs final code processing on pre-processed code; replaces any custom syntaxes that 
			don't exist in the assembler with standard 'b_ [intDistance]' branches, and replaces function 
			symbols with literal RAM addresses, of where that function will end up residing in memory. 

			This process may require two passes. The first is always needed, in order to determine all addresses and syntax resolutions. 
			The second may be needed for final assembly because some lines with custom syntaxes might need to reference other parts of 
			the whole source code (raw custom code), such as for macros or label branch calculations. 

			May return these return codes:
				0: Success (or no processing was needed)
				2: Unable to assemble source (ASM) code with custom syntaxes
				3: Unable to assemble HEX code with custom syntaxes
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

	@staticmethod
	def codeIsAssembly( codeLines ):

		""" Determines whether the given code is pure hex data, or contains assembly or special syntaxes. 
			For purposes of final code processing (resolving custom syntaxes), special syntaxes
			will be resolved to assembly, so they will also count as assembly here. """

		isAssembly = False
		onlySpecialSyntaxes = True
		configSyntaxOnly = True
		foundOtherCharacters = False

		for wholeLine in codeLines:
			# Strip off and ignore comments
			line = wholeLine.split( '#' )[0].strip()
			if line == '': continue

			# Check for custom syntaxes (if one of these syntaxes is matched, it's for the whole line)
			elif CodeLibraryParser.isSpecialBranchSyntax( line ) or CodeLibraryParser.containsPointerSymbol( line ):
				configSyntaxOnly = False

			elif '[[' in line and ']]' in line: # Configuration option

				# Check each chunk (excluding config name) for hex or assembly
				for chunk in line.split( '[[' ):
					if ']]' in chunk: # Contains a config/variable name and maybe other code
						_, chunk = chunk.split( ']]' )
					
					# No config/variable name in this chunk; may be asm or hex.
					# Return True if there are any non-hex characters (meaning assembly was found)
					if not chunk: pass # Empty string
					elif all( char in hexdigits for char in chunk.replace(' ', '') ): # Only hex characters found
						onlySpecialSyntaxes = False
						foundOtherCharacters = True
					else: # Found assembly
						return True

			else:
				onlySpecialSyntaxes = False
				configSyntaxOnly = False

				# Strip whitespace and check for non-hex characters
				if not all( char in hexdigits for char in ''.join(line.split()) ):
					return True

		if onlySpecialSyntaxes:
			if not configSyntaxOnly or foundOtherCharacters:
				isAssembly = True

		return isAssembly