#!/usr/bin/env python

# Created by DRGN of Smashboards (Daniel R. Cappel)
version = 2.1

# For console interaction/testing:
# image = gimp.image_list()[0]
# drawable = pdb.gimp_image_get_active_drawable(image)
# pdb.python_fu_create_tri_csp(image, drawable)

# Other notes:
# print will output to stdout (visible in CMD console)
# pdb.gimp_message() outputs to stderr by default (visible in GIMP Python Console, and Error Log; may also show in GUI status bar?)
# pdb.gimp_message may be UTF-8
# pdb.gimp_message() output can be changed via pdb.gimp_message_set_handler(handler); MESSAGE-BOX (0), CONSOLE (1), ERROR-CONSOLE (2)

# Return Code messages:
#	0: The operation completed successfully.
#	1: Unable to find the configuration file at "{}".
#	2: Source file not found # todo; checks not yet implemented
#	3: Invalid screenshot dimensions (not 1920x1080)

import os

from collections import OrderedDict
from gimpfu import pdb, register, main
from gimpfu import PF_STRING, PF_INT, PF_FLOAT, PF_BOOL, WHITE_FILL


def removeBackground( image, drawable, threshold, mask ):
	
	# Verify image dimensions
	width = drawable.width
	height = drawable.height
	if drawable.name == 'Left Alt' or drawable.name == 'Right Alt':
		if width != 1920 or height != 1080:
			pdb.gimp_message( 'Return Code: 3: Invalid dimensions for {}: {}x{}'.format(drawable.name, width, height) )
			return None

	pdb.gimp_item_set_visible( drawable, True )
	proportionedFeathering = int( round(width / 660.0) ) # Scales with image size; 1 for ~640, while 3 for ~1980
	addBorder = False

	# Set the context settings for the seed-fill selection, and then perform the background selection.
	pdb.gimp_context_set_antialias( 1 )
	pdb.gimp_context_set_feather( 0 )
	pdb.gimp_context_set_feather_radius( 0, 0 ) # x, y
	pdb.gimp_context_set_sample_merged( 1 ) # Determines if seed comparison is by drawable (0) or by visible area (1).
	pdb.gimp_context_set_sample_criterion( 0 )
		# ^ Accepts the following:    SELECT-CRITERION-COMPOSITE (0), 
									# SELECT-CRITERION-R (1), 
									# SELECT-CRITERION-G (2), 
									# SELECT-CRITERION-B (3), 
									# SELECT-CRITERION-H (4), 
									# SELECT-CRITERION-S (5), 
									# SELECT-CRITERION-V (6)
	pdb.gimp_context_set_sample_transparent( 1 ) # Determines whether transparent areas will be selected.

	# Make sure the image has an alpha channel (screenshots from Dolphin probably will, but not necessarily from other sources)
	pdb.gimp_layer_add_alpha( drawable )

	# Check if the image has already had its background removed
	topLeftCornerPixel = pdb.gimp_drawable_get_pixel( drawable, 0, 0 )[1]
	if topLeftCornerPixel[-1] == 0:
		pdb.gimp_item_set_visible( drawable, False )
		return drawable # If the upper-left pixel is already transparent, no processing is required
	
	# A mask was supplied; use that to determine transparency
	if mask:
		pdb.gimp_item_set_visible( drawable, False )
		pdb.gimp_item_set_visible( mask, True )

		pdb.gimp_image_select_item( image, 2, mask ) # Selection by alpha channel; mode of 2 = CHANNEL-OP-REPLACE
		pdb.gimp_selection_invert( image )

		pdb.gimp_item_set_visible( mask, False )
		pdb.gimp_item_set_visible( drawable, True )

		pdb.gimp_edit_clear( drawable )

	else:
		# Determine what color background needs to be removed (taking multiple samples in case a character obscures some of the top edge)
		for x, y in ( (5, 5), (386, 5), (960, 5), (1534, 5), (1915, 5) ):
			pixelSample = pdb.gimp_drawable_get_pixel( drawable, x, y )[1]
			if pixelSample == ( 255, 0, 255, 255 ):
				foundMagenta = True
				break
		else: # The loop above didn't break; magenta not found
			foundMagenta = False

		if foundMagenta:
			pdb.gimp_context_set_sample_threshold_int( int(float(threshold)) ) # Controls what is considered a similar color for the seed-fill (0<x<1).
			magenta = ( 255, 0, 255 )

			# Remove black bars from the sides of the image if they're present.
			if topLeftCornerPixel == ( 0, 0, 0, 255 ): # Opaque, pure black
				pdb.gimp_image_select_contiguous_color( image, 0, drawable, 0, 0 )
				pdb.gimp_image_select_rectangle( image, 0, 0, 0, 86, 32 ) # removes frame counters
				pdb.gimp_selection_grow( image, 1 )
				pdb.gimp_edit_clear( drawable )

			# Remove black bar on right
			topRightCornerPixel = pdb.gimp_drawable_get_pixel( drawable, width - 1, 0 )[1]
			if topRightCornerPixel == ( 0, 0, 0, 255 ):
				pdb.gimp_image_select_contiguous_color( image, 0, drawable, width - 1, 0 )
				pdb.gimp_image_select_rectangle( image, 0, width - 86, 0, 86, 32 ) # removes frame counters
				pdb.gimp_selection_grow( image, 1 )
				pdb.gimp_edit_clear( drawable )

			# Erase the last line in the image (which likely has an impure magenta coloring)
			pdb.gimp_image_select_rectangle(image, 2, 0, height - 1, width, 1)
			pdb.gimp_edit_clear( drawable )

			# Select and remove the magenta (or other color) background areas
			pdb.gimp_image_select_color( image, 2, drawable, magenta )
			pdb.gimp_selection_grow( image, 1 )

			pdb.plug_in_colortoalpha( image, drawable, magenta )

		else: # Remove a fully-black background
			# Readjust the threshold; should be much smaller if using contiguous fill and without magenta
			threshold = int( float(threshold) ) / 10
			pdb.gimp_context_set_sample_threshold_int( threshold ) # Controls what is considered a similar color for the seed-fill (0<x<1).
			
			pdb.gimp_image_select_contiguous_color( image, 2, drawable, 0, 0 )
			pdb.gimp_selection_grow( image, 1 )
			pdb.plug_in_colortoalpha( image, drawable, (0, 0, 0) )

	if addBorder:
		# Create a 1px black border
		borderLayer = pdb.gimp_layer_new( image, width, height, 1, 'Border', 100, 0 ) # last two args: opacity, mode
		pdb.gimp_image_insert_layer( image, borderLayer, None, 0 )
		pdb.gimp_image_select_item( image, 0, drawable ) # Selection by alpha channel
		pdb.gimp_edit_fill( borderLayer, WHITE_FILL )
		pdb.gimp_invert( borderLayer )
		pdb.gimp_selection_shrink( image, 2 )
		pdb.gimp_edit_clear( borderLayer )
		pdb.gimp_selection_none( image )

		# Combine the layers
		drawable = pdb.gimp_image_merge_down( image, borderLayer, 2 )
	else:
		pdb.gimp_selection_feather( image, proportionedFeathering )
		pdb.gimp_edit_clear( drawable )
		pdb.gimp_edit_clear( drawable )

	pdb.gimp_selection_none( image )

	pdb.gimp_item_set_visible( drawable, False )

	return drawable


def parseConfigurationFile( configFilePath ):
	with open( configFilePath, 'r' ) as configFile:
		configContents = configFile.read()

	configuration = OrderedDict([ ('threshold', None), ('centerImageXOffset', None), ('centerImageYOffset', None), ('centerImageScaling', None),
						('sideImagesXOffset', None), ('sideImagesYOffset', None), ('sideImagesScaling', None), ('reverseSides', False) ])

	for line in configContents.splitlines():
		if line.startswith( '#' ): continue

		if ':' in line:
			parameter, value = line.split(':')
			parameter = parameter.strip()

			if parameter in configuration:
				if 'Scaling' in line: configuration[parameter] = float( value )
				elif 'reverse' in line: 
					if value.strip()[0:1].lower() == 't':
						configuration[parameter] = True
					else: configuration[parameter] = False
				else: configuration[parameter] = int( value )

	return configuration


def create_tri_csp( leftImagePath, centerImagePath, rightImagePath, 
	maskImagePath, configFilePath, outputPath, threshold, 
	centerImageXOffset, centerImageYOffset, centerImageScaling, 
	sideImagesXOffset, sideImagesYOffset, sideImagesScaling, 
	reverseSides, createHighRes, showFinished ):
	
	# Normalize the filepath inputs
	leftImagePath = leftImagePath.replace('"','')
	centerImagePath = centerImagePath.replace('"','')
	rightImagePath = rightImagePath.replace('"','')
	maskImagePath = maskImagePath.replace('"','')
	configFilePath = configFilePath.replace('"','')
	outputPath = outputPath.replace('"','')

	if configFilePath:
		if os.path.exists( configFilePath.replace('\\', '/') ): # Override the other values if a config file was provided
			configuration = parseConfigurationFile( configFilePath )
			threshold = configuration['threshold']
			centerImageXOffset = configuration['centerImageXOffset']
			centerImageYOffset = configuration['centerImageYOffset']
			centerImageScaling = configuration['centerImageScaling']
			sideImagesXOffset = configuration['sideImagesXOffset']
			sideImagesYOffset = configuration['sideImagesYOffset']
			sideImagesScaling = configuration['sideImagesScaling']
			reverseSides = configuration['reverseSides']
		else:
			print 'Unable to find the configuration file at "{}".'.format(configFilePath)
			pdb.gimp_message( 'Return Code: 1: Unable to find the configuration file at "{}".'.format(configFilePath) )
			return

	# Manage variables for handling the given files
	leftFilename = os.path.split( leftImagePath )[1]
	leftFilenameNoExt = os.path.splitext( leftFilename )[0]
	centerFilename = os.path.split( centerImagePath )[1]
	centerFilenameNoExt = os.path.splitext( centerFilename )[0]
	outputFolder, rightFilename = os.path.split( rightImagePath )
	rightFilenameNoExt = os.path.splitext( rightFilename )[0]

	# Initialize the image workspace object with the first screenshot; subsequent screenshots are loaded and added as layers
	image = pdb.gimp_file_load( leftImagePath, leftImagePath )

	# To create a proper undo state, duplicate the current working image to a new instance, then temporarily disable history recording
	#image = pdb.gimp_image_duplicate( initialImage )
	#pdb.gimp_image_undo_group_start( image )
	frozen = pdb.gimp_image_undo_freeze( image )

	leftImageLayer = image.active_layer
	centerImageLayer = pdb.gimp_file_load_layer( image, centerImagePath )
	pdb.gimp_image_insert_layer( image, centerImageLayer, None, 0 )
	rightImageLayer = pdb.gimp_file_load_layer( image, rightImagePath )
	pdb.gimp_image_insert_layer( image, rightImageLayer, None, 2 )

	# Load the image mask, if one was provided
	if os.path.exists( maskImagePath ):
		mask = pdb.gimp_file_load_layer( image, maskImagePath )
		pdb.gimp_image_insert_layer( image, mask, None, 3 )

		mask.name = 'Background Mask'
		pdb.gimp_item_set_visible( mask, False )
	else: mask = ''

	# Name the layers
	leftImageLayer.name = 'Left Alt'
	centerImageLayer.name = 'Vanilla'
	rightImageLayer.name = 'Right Alt'

	# Make all layers invisible (to prevent conflicts in background removal function)
	pdb.gimp_item_set_visible( leftImageLayer, False )
	pdb.gimp_item_set_visible( centerImageLayer, False )
	pdb.gimp_item_set_visible( rightImageLayer, False )

	# Remove the background from the images
	if mask:
		mask = removeBackground( image, mask, threshold, '' )
		if not mask: return
	leftImageLayer = removeBackground( image, leftImageLayer, threshold, mask )
	if not leftImageLayer: return
	centerImageLayer = removeBackground( image, centerImageLayer, threshold, mask )
	if not centerImageLayer: return
	rightImageLayer = removeBackground( image, rightImageLayer, threshold, mask )
	if not rightImageLayer: return

	# Re-enable layer visibility
	pdb.gimp_item_set_visible( leftImageLayer, True )
	pdb.gimp_item_set_visible( centerImageLayer, True )
	pdb.gimp_item_set_visible( rightImageLayer, True )

	# Scale and align the layers [ WARNING! Changing the width/height values below will change the result of your config files. ]
	# highResCSPWidth = 680 # This is 5x vanilla width of 136
	# highResCSPHeight = 940 # 5 x 188
	highResCSPWidth = 544 # This is 4x vanilla width of 136
	highResCSPHeight = 752 # 4 x 188
	# highResCSPWidth = 408 # This is 3x vanilla width of 136
	# highResCSPHeight = 564 # 3 x 188

	# Scale the images
	if centerImageScaling != 1:
		centerImageLayer.scale( int(centerImageLayer.width * centerImageScaling), int(centerImageLayer.height * centerImageScaling) )
	if sideImagesScaling != 1:
		leftImageLayer.scale( int(leftImageLayer.width * sideImagesScaling), int(leftImageLayer.height * sideImagesScaling) )
		rightImageLayer.scale( int(rightImageLayer.width * sideImagesScaling), int(rightImageLayer.height * sideImagesScaling) )

	# Horizontally flip the appropriate side image
	if reverseSides:
		pdb.gimp_item_transform_flip_simple( rightImageLayer, 0, True, 0 )
	else:
		pdb.gimp_item_transform_flip_simple( leftImageLayer, 0, True, 0 )

	# Align the images according to the given offsets
	centerImageLayer.set_offsets( centerImageXOffset, centerImageYOffset ) # centerLayerXDiff/2, -(centerLayerYDiff/2)
	leftImageLayer.set_offsets( sideImagesXOffset, sideImagesYOffset )
	rightImageLayer.set_offsets( highResCSPWidth - rightImageLayer.width - sideImagesXOffset, sideImagesYOffset )

	# Extend the top of the canvas, to prevent layer clipping during the merge operation below
	pdb.gimp_image_resize( image, image.width, image.height + 60, 0, 60)

	# Combine the layers (now unnecessary, but must be kept so that new CSPs will exactly match CSPs previously created)
	finalComposite = pdb.gimp_image_merge_visible_layers( image, 1 ) # 1 = merge_type, CLIP-TO-IMAGE

	# Set a specific output path if one was given, otherwise, use the folder of the right side image
	filename = leftFilenameNoExt + '_' + centerFilenameNoExt + '_' + rightFilenameNoExt
	if outputPath:
		if os.path.isdir( outputPath ):
			outputFolder = outputPath
		else:
			outputFolder, filename = os.path.split( outputPath )
			filename = os.path.splitext( filename )[0]

	if createHighRes:
		filename = filename + '_highRes'
		pdb.gimp_image_select_rectangle( image, 0, 0, 60, highResCSPWidth, highResCSPHeight ) # (required for finish-csp function)

	else: # Create the vanilla sized CSP
		pdb.gimp_image_resize( image, image.width, highResCSPHeight, 0, -60 )
		image.scale( 480, 188 )

		pdb.gimp_image_select_rectangle( image, 0, 0, 0, 136, 188 ) # (required for finish-csp function)

	# Reactivate history recording, so the plug-in's actions can be undone in one step.
	#pdb.gimp_image_undo_group_end( image )
	if frozen: pdb.gimp_image_undo_thaw( image )

	# Create a shadow for the finished image and save it.
	pdb.python_fu_finish_csp( image, finalComposite, outputFolder, filename, True, False)

	# Delete this image (and all associated layers) to free resources, unless the user wants to see it
	if showFinished:
		pdb.gimp_display_new( image ) # When this is destroyed or closed, it will also delete the underlying image object.
		#pdb.gimp_displays_flush()
	else:
		pdb.gimp_image_delete( image )

	pdb.gimp_progress_set_text( 'Process complete!' )

	pdb.gimp_message( 'Return Code: 0: The operation completed successfully.' )


register(
		"python_fu_create_tri_csp",										# Name to register for calling this plug-in
		"Create a 3-image CSP from three in-game screenshots.", 		# Short info (tooltips, etc.)
		"Create a 3-image CSP from three in-game screenshots.", 		# Long description / help message
		"DRGN (Daniel R. Cappel)",										# Author
		"Creative Commons",												# Copyright
		"March 2017",													# Creation time
		"<Toolbox>/CS_Ps/Create _Tri-CSP",								# Menu path
		"",					# Image Types. Setting to "*" means any are accepted, and will force requirement of an open image before script can be called.
		[
				( PF_STRING, 'leftImagePath', 'Left-Alt Filepath:', "" ),
				( PF_STRING, 'centerImagePath', 'Center Image Filepath:', '' ),
				( PF_STRING, 'rightImagePath', 'Right-Alt Filepath:', '' ),

				( PF_STRING, 'maskImagePath', 'Background Mask:', '' ),
				( PF_STRING, 'configFilePath', 'Configuration File:', '' ),
				( PF_STRING, 'outputPath', 'Output (folder or full path):', '' ),

				( PF_INT, 'threshold', "Background Selection Threshold:", 40 ),

				( PF_INT, 'centerImageXOffset', "Center Image X Offset:", 0 ),
				( PF_INT, 'centerImageYOffset', "Center Image Y Offset:", 0 ),
				( PF_FLOAT, 'centerImageScaling', "Center Image Scaling:", 1.0 ),

				( PF_INT, 'sideImagesXOffset', "Side Images X Offset:", 0 ),
				( PF_INT, 'sideImagesYOffset', "Side Images Y Offset:", 0 ),
				( PF_FLOAT, 'sideImagesScaling', "Side Images Scaling:", 1.0 ),

				#( PF_OPTION, 'colorChoiceIndex', '("Magenta", "Black")' )
				( PF_BOOL, "reverseSides", "Horizontallay Flip Side Images:", False ),
				( PF_BOOL, "saveHighRes", "Create in High-Res:", False ),
				( PF_BOOL, "showFinished", "Show the Finished Product:", False )
		],
		[],
		create_tri_csp )		# Name of the function to call in this script

main()