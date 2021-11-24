#!/usr/bin/env python

# Created by DRGN of Smashboards (Daniel R. Cappel)
# Version 1.1

# For console interaction / testing:
# image = gimp.image_list()[0]

from gimpfu import pdb, register, main, PF_BOOL, PF_INT, WHITE_FILL


def remove_background( image, drawable, contiguousMode, addBorder, threshold, hideLayer=True ):
	width = drawable.width
	height = drawable.height
	pdb.gimp_item_set_visible( drawable, True )

	potentialBgColors = { 'magenta': (255, 0, 255), 'black': (0, 0, 0) } # Magenta and Black RGB
	if contiguousMode:
		colorToRemove = pdb.gimp_drawable_get_pixel( drawable, 0, 0 )[1] # Returns RGBA color tuple
	else:
		colorToRemove = potentialBgColors['magenta'] # Black is unsafe with this mode

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

	# Select and remove the background areas
	if contiguousMode:
		pdb.gimp_image_select_contiguous_color( image, 2, drawable, 0, 0 )
	else:
		pdb.gimp_image_select_color( image, 2, drawable, colorToRemove )
	pdb.gimp_selection_grow( image, 1 )
	pdb.plug_in_colortoalpha( image, drawable, colorToRemove )

	if not addBorder:
		proportionedFeathering = int( round(width / 660.0) ) # scales to image size; 1 for ~640, while 3 for ~1980
		pdb.gimp_selection_feather( image, proportionedFeathering )
		pdb.gimp_edit_clear( drawable )
		pdb.gimp_edit_clear( drawable )

	pdb.gimp_selection_none( image )

	if addBorder: # Create a 1px black border
		# Create and add a new layer for the border
		borderLayer = pdb.gimp_layer_new( image, width, height, 1, 'Border', 100, 0 ) # last two args: opacity, mode
		pdb.gimp_image_insert_layer( image, borderLayer, None, 0 )

		# Select the outline of the subject, and create the border
		pdb.gimp_image_select_item( image, 2, drawable ) # Selection by alpha channel
		pdb.gimp_edit_fill( borderLayer, WHITE_FILL )
		pdb.gimp_invert( borderLayer )
		pdb.gimp_selection_shrink( image, 2 )
		pdb.gimp_edit_clear( borderLayer )
		pdb.gimp_selection_none( image )

		# Combine the layers
		drawable = pdb.gimp_image_merge_down( image, borderLayer, 2 )

	if hideLayer:
		pdb.gimp_item_set_visible( drawable, False )


def processLayers( timg, tdrawable, allLayers, addBorder, contiguousMode, threshold ):
	image = timg

	# Temporarily disable history recording, so the plug-in's actions can be undone in one step.
	pdb.gimp_image_undo_group_start( image )

	# Make all layers invisible (to prevent conflicts in background removal function)
	for layer in image.layers:
		pdb.gimp_item_set_visible( layer, False )

	# Disable the all-layers operation flag if there's only 1 (prevents hiding the layer)
	if len( image.layers ) == 1:
		allLayers = False

	if allLayers:
		for drawable in image.layers:
			remove_background( image, drawable, contiguousMode, addBorder, threshold )
	else:
		#remove_background( image, image.active_layer, contiguousMode, addBorder, threshold )
		remove_background( image, tdrawable, contiguousMode, addBorder, threshold, hideLayer=False )

	# Reactivate history recording
	pdb.gimp_image_undo_group_end( image )

	pdb.gimp_progress_set_text( 'Background removal complete!' )
	#pdb.gimp_message( 'Process complete!' )


register(
		"remove_background",														# Name to register for calling this plug-in
		( "Removes a pure-color background around a character or stage.\n\n"		# Long description / help message
			"Contiguous mode uses a procedural color selection process, "
			"starting with the top-left pixel. Non-contiguous mode (recommended "
			"threshold of ~40) selects for only magenta across the layer(s)."
		),
		"Removes the black background around a character or stage.",				# Short info (tooltips, etc.)
		"DRGN (Daniel R. Cappel)",													# Author
		"Creative Commons",															# Copyright
		"June 2020",																# Creation date
		"<Image>/CS_Ps/_Remove Background",
		"*",		# Color mode. Setting to "*" will force requirement of an open image before script can be called (and pass timg, tdrawable).
		[
				( PF_BOOL, "allLayers", "All Layers", True ),
				( PF_BOOL, "addBorder", "Add Border", False ),
				( PF_BOOL, 'contiguousMode', 'Contiguous Mode', True ),
				( PF_INT, 'threshold', "Background Selection Threshold:", 3 ) # Recommend 40 for non-contiguous mode (using magenta)
		],
		[],
		processLayers)			# Name of the function to call in this script

main()