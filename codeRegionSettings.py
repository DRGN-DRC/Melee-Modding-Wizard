#!/usr/bin/python
# This Python file uses the following encoding: utf-8

# Written in Python v2.7.12 by DRGN of SmashBoards (Daniel R. Cappel).
version = 5.0

from collections import OrderedDict


# The value below affects the Code Offset Converter in the Tools tab. If set to False, the search will be much slower, but 
# will also have a little better chance of finding a match.
#quickSearch = True

# globalFontSize can set the default size of the program's font, even apart from your system's (OS dependant) settings.
# Negative values indicate pixel size, while positive values are standard font points.
#globalFontSize = -12

# So far, the value below is only used for determining a default revision when adding new code changes for a mod in the Mod Construction tab.
#defaultRevision = 'NTSC 1.02' # Should follow the revision string convention of "[region] [version]"

# The following will ensure that the mod "Enable OSReport Print on Crash" is always installed in your game, as
# long as it's also found in your Mods Library. Change this to False if you don't want this behavior.
#alwaysEnableCrashReports = True

# Below are hex ranges that indicate safe areas (free space) for custom code. Between each set of parenthesis, you have the start of a region, followed 
# by the end of that region. You may add new regions, as long as you follow the same formatting that you see here.
#
# (I recommend making a copy of this file or the line(s) you modify, in case you make a mistake or
# would like to undo it later. Then, you can just comment out the back-up line(s) by preceding it with a '#'.)
#
# Remember that each entry needs to be followed by a comma, except for the last one.
# If you'd like to remove all of these regions, you still need to preserve the variable here;
# just make it equal to an empty pair of brackets, i.e. "commonCodeRegions = {}"
#
# You may also add regions. Just be sure that you know what you're doing and have tested the region, and that no regions overlap with one another!
customCodeRegions = OrderedDict([

	# The regions in this first list are the same between all game revisions, hence "ALL" specified for the code region.
	( 'ALL|Common Code Regions', [ ( 0x2C8, 0x398 ), ( 0x39C, 0x498 ), ( 0x4E4, 0x598 ), ( 0x5CC, 0x698 ),			# 0xD0,  0xFC,  0xB4, 0xCC 	= 0x34C
								 ( 0x6CC, 0x798 ), ( 0x8CC, 0x998 ), ( 0x99C, 0xA98 ), ( 0xACC, 0xB98 ),			# 0xCC,  0xCC,  0xFC, 0xCC 	= 0x360
								 ( 0xBCC, 0xE98 ), ( 0xECC, 0xF98 ), ( 0xFCC, 0x1098 ), (0x10CC, 0x1198 ),			# 0x2CC, 0xCC,  0xCC, 0xCC 	= 0x530
								 ( 0x1220, 0x1298 ), ( 0x1308, 0x1398 ), ( 0x1408, 0x1498 ), ( 0x1508, 0x1598 ),	# 0x78,  0x90,  0x90, 0x90 	= 0x228
								 ( 0x15F0, 0x1698 ), ( 0x16CC, 0x1898 ), ( 0x18CC, 0x1998 ), ( 0x19CC, 0x1E98 ),	# 0xA8,  0x1CC, 0xCC, 0x4CC = 0x80C
								 ( 0x1ECC, 0x1F98 ), ( 0x1FCC, 0x2098 ), ( 0x20CC, 0x2198 ) ] ),					# 0xCC,  0xCC,  0xCC 		= 0x264
																														# Total space of above:  0x1874 Bytes

	( 'NTSC 1.02|20XXHP 4.07 Regions', [ ( 0x18DCC0, 0x197B30 ), 		# Tournament Mode Region 	(0x9E70)
									#	 ( 0x32B96C, 0x32C208 ),		# Area 4 of USB/MCC 		(0x89C)		< Can be included if you remove the PAL FSM List
										 ( 0x32C998, 0x332834 ), 		# Extra USB/MCC Region 		(0x5E9C)
										 ( 0x39063C, 0x3907F4 ),		# Area 5 of USB/MCC 		(0x1B8)
										 ( 0x407540, 0x408F00 ), ] ),	# Aux Code Regions 			(0x19C0)
																				# Total space = 0x11884 Bytes (Or 0x12120 if you add Area 4 of MCC)

																								#______________
	( 'NTSC 1.02|20XXHP 5.0 Regions', [ ( 0x39C, 0x498 ), ( 0x8CC, 0x998 ), ( 0x9CC, 0xA98 ),		#          \
										( 0xECC, 0xF98 ), ( 0xFCC, 0x1098 ), ( 0x1308, 0x1398 ),	  #         \_____ Common Code Regions (0x87C bytes)
										( 0x1508, 0x1598 ), ( 0x15CC, 0x1698 ), ( 0x18CC, 0x1998 ),	    #       |
										( 0x1ECC, 0x1F98 ), ( 0x20CC, 0x2198 ),					#______________|
										( 0x18DCC0, 0x197B30 ), 				# Tournament Mode Region 	(0x9E70)
										#( 0x2254C0, 0x225644 ),				# Not much space
										#( 0x329584, 0x329640 ),				# Not much space
										#( 0x32A8E8, 0x32A9A0 ),				# Not much space
										#( 0x32B96C, 0x32C208 ),				# Area 4 of USB/MCC 		(0x89C)		< Can be included if you remove the PAL FSM List (which is currently empty)
	 									( 0x32C998, 0x332834 ), 				# Extra USB/MCC Region 		(0x5E9C)
										#( 0x39063C, 0x3907F4 ), ] ),			# Area 5 of USB/MCC 		(0x1B8)
										( 0x39063C, 0x39078C ), ] ),			# Area 5 of USB/MCC 		(0x150) # Ended early for space for codes with static location
																						# Total space = 0x10740 Bytes (Or 0x10FDC if you add Area 4 of MCC)

	# The following regions are used for the multiplayer tournament mode (which of course will no longer be functional if you use this space). 
	# If you use this space, you may want to add a code that prevents people from accessing this mode so that the game doesn't crash when someone tries to use it.
	# ( 'NTSC 1.02|Tournament Mode Region, P1', [ ( 0x18DCC0, 0x18E8C0 ) ] ), 	# Total space: 0xC00
	# ( 'NTSC 1.01|Tournament Mode Region, P1', [ ( 0x18D674, 0x18E274 ) ] ), 	# Total space: 0xC00
	# ( 'NTSC 1.00|Tournament Mode Region, P1', [ ( 0x18CDC0, 0x18D9C0 ) ] ), 	# Total space: 0xC00
	# ( 'PAL 1.00|Tournament Mode Region, P1', [ ( 0x18E804, 0x18F404 ) ] ), 		# Total space: 0xC00
	# # These regions are part of one contiguous space, and are separated here so that the 
	# # Aux Code Regions can remain vanilla, allowing use of the "Enable OSReport Print on Crash" code.
	# ( 'NTSC 1.02|Tournament Mode Region, P2', [ ( 0x18E8C0, 0x197B30 ) ] ), 	# Total space: 0x9270
	# ( 'NTSC 1.01|Tournament Mode Region, P2', [ ( 0x18E274, 0x1974E4 ) ] ), 	# Total space: 0x9270
	# ( 'NTSC 1.00|Tournament Mode Region, P2', [ ( 0x18D9C0, 0x196DE4 ) ] ), 	# Total space: 0x9424
	# ( 'PAL 1.00|Tournament Mode Region, P2', [ ( 0x18F404, 0x1986A0 ) ] ), 		# Total space: 0x929C

	( 'NTSC 1.02|Tournament Mode Region', [ ( 0x18DCC0, 0x197B30 ) ] ), 	# Total space: 0x9E70
	( 'NTSC 1.01|Tournament Mode Region', [ ( 0x18D674, 0x1974E4 ) ] ), 	# Total space: 0x9E70
	( 'NTSC 1.00|Tournament Mode Region', [ ( 0x18CDC0, 0x196DE4 ) ] ), 	# Total space: 0xA024
	( 'PAL 1.00|Tournament Mode Region', [ ( 0x18E804, 0x1986A0 ) ] ), 		# Total space: 0x9E9C
	# The tournament mode regions for versions other than 1.02 have not yet been tested. Please let me know the results if you test them.

	# The regions below are for the unused 'USB Screenshot' feature, described here:
	# http://smashboards.com/threads/the-dol-mod-topic.326347/page-11#post-19130116
	# More accurately known as parts of the "MCC Regions" (Dolphin OS Multi-Channel Communication API)
	
	# If these are used for custom code, then the following changes also need to be made: 
	# 0x1a1b64 --> 60000000, 0x1a1c50 --> 60000000 (nops branch links to these regions; these are DOL addresses for v1.02)
	# MCM will handle the nops above for you if these regions are used, so these notes are just mentioned here in case you want to do something manually.
	( 'NTSC 1.02|Screenshot Regions', [ ( 0x22545c, 0x225644 ), ( 0x329428, 0x329640 ), ( 0x32a890, 0x32a9a0 ), ( 0x32b96c, 0x32c208 ), ( 0x39063c, 0x3907f4 ) ] ),
	( 'NTSC 1.01|Screenshot Regions', [ ( 0x224cd4, 0x224ebc ), ( 0x328750, 0x328968 ), ( 0x329bb8, 0x329cc8 ), ( 0x32ac94, 0x32B530 ), ( 0x38f95c, 0x38fb14 ) ] ),
	( 'NTSC 1.00|Screenshot Regions', [ ( 0x22414c, 0x224334 ), ( 0x327b00, 0x327d18 ), ( 0x328f68, 0x329078 ), ( 0x32a044, 0x32A8E0 ), ( 0x38e778, 0x38e930 ) ] ),
	( 'PAL 1.00|Screenshot Regions', [ ( 0x2272cc, 0x2274b4 ), ( 0x329704, 0x32991c ), ( 0x32AB6C, 0x32AC7C ), ( 0x32BC48, 0x32C4E4 ), ( 0x390564, 0x39071c ) ] ),
								# Space:		0x1e8 					0x218 					0x110 					0x89c 					0x1b8 				= 0xF64 Bytes Total

	# The following is commented out because it seems to cause crashing. Perhaps another nop is needed. More testing required.
	# The code here relates to playing MTH files, so if you don't need those, this may work for you.
	# ( 'NTSC 1.02|Screenshot Regions', [ ( 0x32C998, 0x332834 ) ] ), # Total space: 0x5E9C Bytes
	# ( 'NTSC 1.01|Screenshot Regions', [ ( 0x32BCB8, 0x331B54 ) ] ),
	# ( 'NTSC 1.00|Screenshot Regions', [ ( 0x32B068, 0x330F04 ) ] ),
	# ( 'PAL 1.00|Screenshot Regions', [ ( 0x32CC78, 0x332B14 ) ] ),

	# The regions below are used for the game's vanilla Debug Menu, which of course will no longer be functional if you use this space.
	# The Debug Mode itself (DbLevel) may still work to some extent, but you would at least need a new method to enter it.
	( 'NTSC 1.02|Debug Mode Region', [ ( 0x3f7124, 0x3fac20 ) ] ), # Total space: 0x3AFC (same for all game versions)
	( 'NTSC 1.01|Debug Mode Region', [ ( 0x3f6444, 0x3f9f40 ) ] ),
	( 'NTSC 1.00|Debug Mode Region', [ ( 0x3f5294, 0x3f8d90 ) ] ),
	( 'PAL 1.00|Debug Mode Region', [ ( 0x3f7ecc, 0x3fbae8 ) ] ),

	# These are unused areas containing text used for debugging the game, and have been tested to be safe for overwriting.
	# However, they will disable the use of OS Report features, such as in the useful "Enable OSReport Print on Crash" code.
	# CrazyHand places the FSM Engine and FSM Entries directly after this region.
	( 'NTSC 1.02|Aux Code Regions', [ ( 0x407540, 0x4088B0 ) ] ), # Total space: 0x1370
	( 'NTSC 1.01|Aux Code Regions', [ ( 0x406860, 0x407BD0 ) ] ),
	( 'NTSC 1.00|Aux Code Regions', [ ( 0x405580, 0x4068F0 ) ] ),
	( 'PAL 1.00|Aux Code Regions', [ ( 0x408400, 0x409770 ) ] ),

	# The following regions are only for use with extended NTSC 1.02 SSBM DOLs
	# Part 1 of Data Section 8
	# ( 'NTSC 1.02|Gecko Code Handler Storage', [ ( 0x4385E0, 0x4395E0 ) ] ), # 0x1000
	# # Part 2 of Data Section 8
	# ( 'NTSC 1.02|Gecko Code List Storage', [ ( 0x4395E0, 0x446EE0 ) ] ), # 0xD900

])


# The Gecko hook (set below) intercepts the game's normal execution to point to the Gecko Codehandler with a standard branch.
# Warning: do not change the hook offsets unless you've first fully uninstalled all Gecko codes from your game.
# Otherwise, the old hook will still remain in your game, and your game will not run unless you manually remove it.
#
# If the regions used for the codelist or codehandler are changed, the next time you open the program and game/DOL,
# any previously installed Gecko codes will not be detected (because the program will be looking in the new region for 
# them), however their code will still be present in the same place as they were before. So you will need to reselect
# and save the mods that you'd like to be installed. And if you want the code in the old regions to be retuned the game's
# original/vanilla hex, use the "Restore" buttons found in the Code-Space Options window (located in the Mods Library tab).
# 
# Note that if Gecko codes are used, the codelist/codehandler will be placed at the start of their respective region,
# defined below. As you can see in the customCodeRegions definitions above, a single region may be one contiguous area, 
# or a collection of several areas. However, any region set for the Gecko codelist or codehandler will only use the first 
# area if there are multiple. The extra space left over in that region may still be used for standard injection mod code 
# and/or standalone functions.
# geckoConfiguration = {
# 	'hookOffsets': { 'NTSC 1.02': 0x3738E0, 'NTSC 1.01': 0x372c00, 'NTSC 1.00': 0x371a2c, 'PAL 1.00': 0x3737e4 },
# 	'codehandlerRegion': 'Tournament Mode Region, P1', # If Gecko codes are used, the codehandler will be placed at the start of this region (must exist in customCodeRegions)
# 	'codelistRegion': 'Tournament Mode Region, P2' # If Gecko codes are used, the codelist will be placed at the start of this region (must exist in customCodeRegions)
# }
# Recommended defaults:
#	Tournament Mode Region, P2 for the codelist, because it is the largest contiguous area
#	Tournament Mode Region, P1 for the codehandler (Aux Code Regions is a good alternative, but you will lose use of the "Enable OSReport Print on Crash" code)
