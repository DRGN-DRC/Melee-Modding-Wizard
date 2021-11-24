#!/usr/bin/env python

# Created by DRGN of Smashboards (Daniel R. Cappel)
version = 1.5

# For console interaction/testing:
# image = gimp.image_list()[0]
# drawable = pdb.gimp_image_get_active_drawable(image)
# pdb.python_fu_create_tri_csp(image, drawable)


import os

from collections import OrderedDict
from gimpfu import pdb, register, main
from gimpfu import PF_STRING, PF_INT, PF_FLOAT, PF_BOOL, WHITE_FILL


def removeBackground( image, drawable, colorToRemove, threshold, mask ):
	width = drawable.width
	height = drawable.height
	pdb.gimp_item_set_visible( drawable, True )

	#originalLayerPosition = pdb.gimp_image_get_item_position( image, drawable )
	proportionedFeathering = int( round(width / 660.0) ) # scales to image size; 1 for ~640, while 3 for ~1980

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
	pdb.gimp_context_set_sample_threshold_int( int(float(threshold)) ) # Controls what is considered a similar color for the seed-fill (0<x<1).
	pdb.gimp_context_set_sample_transparent( 1 ) # Determines whether transparent areas will be selected.


	if colorToRemove == (0, 0, 0):
		pdb.python_fu_remove_bg( image, drawable ) # Not a native function

	else:
		# Remove black bars from the sides of the image if they're present.
		topLeftCornerPixel = pdb.gimp_drawable_get_pixel( drawable, 0, 0 )[1]
		if topLeftCornerPixel[-1] == 0:
			pdb.gimp_item_set_visible( drawable, False )
			return drawable # If the upper-left pixel is already transparent, no processing is required

		if topLeftCornerPixel == ( 0, 0, 0, 255 ): # Opaque, pure black
			pdb.gimp_image_select_contiguous_color( image, 0, drawable, 0, 0 )
			pdb.gimp_image_select_rectangle( image, 0, 0, 0, 86, 32 ) # removes frame counters
			pdb.gimp_selection_grow( image, 1 )
			pdb.gimp_edit_clear( drawable )

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
		if mask == '':
			pdb.gimp_image_select_color( image, 2, drawable, colorToRemove )
			pdb.gimp_selection_grow( image, 1 )

			pdb.plug_in_colortoalpha( image, drawable, colorToRemove )

		else: # A mask was supplied
			pdb.gimp_item_set_visible( drawable, False )
			pdb.gimp_item_set_visible( mask, True )
			#pdb.gimp_image_select_color( image, 2, mask, colorToRemove )
			pdb.gimp_image_select_item( image, 2, mask ) # Selection by alpha channel; mode of 2 = CHANNEL-OP-REPLACE
			pdb.gimp_selection_invert( image )
			pdb.gimp_item_set_visible( mask, False )
			pdb.gimp_item_set_visible( drawable, True )

			#pdb.plug_in_colortoalpha( image, drawable, colorToRemove )

			#pdb.gimp_selection_shrink( image, 5 )
			pdb.gimp_edit_clear( drawable )

		if not addBorder:
			pdb.gimp_selection_feather( image, proportionedFeathering )
			pdb.gimp_edit_clear( drawable )
			pdb.gimp_edit_clear( drawable )

		pdb.gimp_selection_none( image )

	if addBorder:
		# Create a 1px black border
		borderLayer = pdb.gimp_layer_new( image, width, height, 1, 'Border', 100, 0 ) # last two args: opacity, mode
		pdb.gimp_image_insert_layer( image, borderLayer, None, 0 )
		#gimp.set_background( (0, 0, 0) )
		#pdb.gimp_edit_fill( borderLayer, BACKGROUND_FILL ) # Fill with background
		pdb.gimp_image_select_item( image, 0, drawable ) # Selection by alpha channel
		pdb.gimp_edit_fill( borderLayer, WHITE_FILL )
		pdb.gimp_invert( borderLayer )
		pdb.gimp_selection_shrink( image, 2 )
		pdb.gimp_edit_clear( borderLayer )
		pdb.gimp_selection_none( image )

		# Combine the layers
		drawable = pdb.gimp_image_merge_down( image, borderLayer, 2 )

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

	potentialBgColors = { 0: (255, 0, 255), 1: (0, 0, 0) } # Magenta and Black RGB
	colorToRemove = potentialBgColors[0]
	
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
			print 'Invalid config filepath!'
			return

	# Manage variables for handling the given files
	leftFilename = os.path.split( leftImagePath )[1]
	leftFilenameNoExt = os.path.splitext( leftFilename )[0]
	centerFilename = os.path.split( centerImagePath )[1]
	centerFilenameNoExt = os.path.splitext( centerFilename )[0]
	outputFolder, rightFilename = os.path.split( rightImagePath )
	rightFilenameNoExt = os.path.splitext( rightFilename )[0]

	if os.path.isdir( outputPath.replace('\\', '/') ): outputFolder = outputPath
	#else: outputFolder = ''

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

	# Remove the magenta background from the images
	if mask: mask = removeBackground( image, mask, colorToRemove, threshold, '' )
	leftImageLayer = removeBackground( image, leftImageLayer, colorToRemove, threshold, mask )
	centerImageLayer = removeBackground( image, centerImageLayer, colorToRemove, threshold, mask )
	rightImageLayer = removeBackground( image, rightImageLayer, colorToRemove, threshold, mask )

	# Re-enable layer visibility
	pdb.gimp_item_set_visible( leftImageLayer, True )
	pdb.gimp_item_set_visible( centerImageLayer, True )
	pdb.gimp_item_set_visible( rightImageLayer, True )

	#pdb.gimp_message( 'Background removal complete. Beginning positioning and scaling.' )

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

	filename = leftFilenameNoExt + '_' + centerFilenameNoExt + '_' + rightFilenameNoExt

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


register(
		"python_fu_create_tri_csp",										# Name to register for calling this plug-in
		"Create a 3-image CSP from three in-game screenshots.", 		# Short info (tooltips, etc.)
		"Create a 3-image CSP from three in-game screenshots.", 		# Long description / help message
		"DRGN (Daniel R. Cappel)",										# Author
		"Creative Commons",												# Copyright
		"March 2017",													# Creation time
		"<Toolbox>/CS_Ps/Create _Tri-CSP",
		"",                 # Color space. Setting to "*" means any are accepted, and will force requirement of an open image before script can be called.
		[
				( PF_STRING, 'leftImagePath', 'Left-Alt Filepath:', "" ),
				( PF_STRING, 'centerImagePath', 'Center Image Filepath:', '' ),
				( PF_STRING, 'rightImagePath', 'Right-Alt Filepath:', '' ),

				( PF_STRING, 'maskImagePath', 'Background Mask:', '' ),
				( PF_STRING, 'configFilePath', 'Configuration File:', '' ),
				( PF_STRING, 'outputPath', 'Output Folder:', '' ),

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