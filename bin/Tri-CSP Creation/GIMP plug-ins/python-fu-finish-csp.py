#!/usr/bin/env python

# Created by DRGN of Smashboards (Daniel R. Cappel)
version = 2.3

# For console interaction:
# image = gimp.image_list()[0]

from gimpfu import gimp, pdb, register, main
from gimpfu import PF_STRING, PF_BOOL, RGBA_IMAGE, BACKGROUND_FILL


def saveToFile( image, layer, outputFolder, filename ):

	""" This will save only the given layer (not the full image) to a new PNG file. """

	# Indicate that the process has started.
	gimp.progress_init( "Saving to '" + outputFolder + "'..." )

	try:
		# Save as PNG
		pdb.file_png_save2( image, layer, outputFolder + "\\" + filename + ".png", "raw_filename", 0, 9, 0, 0, 0, 0, True, True, 0 )
						# (image, drawable, filename, raw_filename, interlace, compression, bkgd, gama, offs, phys, time, comment, svtrans)
	except Exception as err:
		pdb.gimp_progress_set_text( "Unexpected error: " + str(err) )
		gimp.message( "Unexpected error: " + str(err) )


def addBackground( image, initialComposite, layerType, shadowOpacity, highResMultiplier ):

	""" Creates a new shadow layer below the given initialComposite layer. """

	# Duplicate the original layer and move it to the shadow position.
	compositeCopy = initialComposite.copy()
	pdb.gimp_image_insert_layer(image, compositeCopy, None, 1)
	compositeCopy.translate( (-10 * highResMultiplier), (10 * highResMultiplier) )

	# Select the alpha channel of the duplicated layer, and create a new layer for the shadow.
	pdb.gimp_image_select_item(image, 0, compositeCopy) # Alpha to Selection
	shadowLayer = gimp.Layer(image, "The shadow", image.width, image.height, layerType, 100, 0) # Image type 1 = RGBA
	pdb.gimp_image_insert_layer(image, shadowLayer, None, 2)

	# Fill the selection to the new layer. This method prevents any colors from the duplicated layer from persisting.
	pdb.gimp_edit_fill(shadowLayer, 0) # Fill with foreground (set before calling this function)
	pdb.gimp_selection_none(image)
	pdb.gimp_layer_set_opacity(shadowLayer, shadowOpacity)

	# Remove the no-longer-needed duplicated layer.
	pdb.gimp_image_remove_layer(image, compositeCopy)


def finish_csp( image, tdrawable, outputFolder, filename, saveRef, saveWithPalette ):
	# Check for a selection area to use for cropping.
	selectionExists, x1, y1, x2, y2 = pdb.gimp_selection_bounds( image )

	if not selectionExists:
		pdb.gimp_message( 'Operation aborted. To begin, you must first select a region to crop to, or select the whole image (Ctrl-A).' )
		return
	
	# Disable history recording, so the plug-in's actions can be undone in one step.
	pdb.gimp_image_undo_group_start( image )

	# Crop the image based on the current selection (emulates the 'Fit Canvas to Selection' function).
	# (This method must be used because GIMP's standard crop feature will delete layer portions 
	# that are outside of the canvas area, which are needed during later layer moves.)
	new_width = x2 - x1
	new_height = y2 - y1
	pdb.gimp_image_resize(image, new_width, new_height, 0, 0)
	pdb.gimp_selection_none(image)

	# If more than one layer is present, merge what is visible into one layer, and delete the rest.
	# (This is necessary because if other layers are present, even if not visible, GIMP will take
	# their colors into account when generating a palette for the image.)
	numOfLayers = len(image.layers)
	if numOfLayers > 1:
		initialComposite = pdb.gimp_image_merge_visible_layers(image, 0)
		for layer in image.layers:
			if not layer.name == initialComposite.name:
				pdb.gimp_image_remove_layer(image, layer)
	else:
		initialComposite = image.active_layer

	# If the initial image already had a palette. Abort the script.
	if pdb.gimp_drawable_is_indexed(initialComposite):
		pdb.gimp_message('The image already has a palette. Operation aborted.')
		pdb.gimp_image_undo_group_end(image)
		return

	# The '_image_resize' method done earlier doesn't seem to handle the last two parameters correctly
	# (which is why they're set at 0), so this step below compensates for it by moving the layer.
	initialComposite.translate(-x1, -y1)

	highResMultiplier = int( round( new_width / 136.0 ) ) # Multiplier to keep the shadow relative offset proportional to the CSP size

	# Create a _6 type image (a PNG with regular transparency and shadow) alongside the paletted _9 image.
	if saveRef == True:
		# Create the shadow (from the game: (0, 0, 0, 96); 96/255*100=37.6)
		gimp.set_foreground(0, 0, 0) # Will be the shadow color.
		addBackground( image, initialComposite, RGBA_IMAGE, 37.6, highResMultiplier ) # 65.5?

		# Save the finished layer to a PNG file.
		if outputFolder and filename:
			# Merge the shadow created above with a copy of the main composite image
			finalCopy = initialComposite.copy()
			pdb.gimp_image_insert_layer(image, finalCopy, None, 1)
			mergedWithShadow = pdb.gimp_image_merge_down(image, finalCopy, 1)

			# Save the new copy+shadow (this will ignore the other composite layer)
			saveToFile(image, mergedWithShadow, outputFolder, filename)

			# Delete the copy with the shadow if a paletted image is requested
			if saveWithPalette:
				pdb.gimp_image_remove_layer(image, mergedWithShadow)
				initialComposite.name = 'Finished CSP'
			else:
				pdb.gimp_image_remove_layer(image, initialComposite)
				mergedWithShadow.name = 'Finished CSP'

	if saveWithPalette:
		# Create the palette for the image and add in the replacement colors (lime green and magenta).
		pdb.gimp_image_convert_indexed(image, 0, 0, 254, False, False, 'New_Palette')
									# (image, dither_type, palette_type, num_cols, alpha_dither, remove_unused, palette)
												# Dither types:
														# 0 = None
														# 1 = Floyd-Steinberg error diffusion
														# 2 = Floyd-Steinberg error diffusion with reduced bleeding
														# 3 = dithering based on pixel location ('Fixed' dithering)
		colormap = pdb.gimp_image_get_colormap(image)[1]
		colormap = colormap + (0, 255, 0, 255, 0, 255) # Add lime green and magenta, respectively.
		pdb.gimp_image_set_colormap(image, len(colormap), colormap)

		# Create the character's shadow.
		gimp.set_foreground(0, 255, 0) # For a lime green shadow.
		addBackground( image, initialComposite, 5, 100, highResMultiplier ) # Image type 5 = INDEXEDA (GIMP doesn't actually recognize the latter form)

		# Add a magenta background.
		bgLayer = gimp.Layer(image, 'Background', image.width, image.height, 5, 100, 0)
		pdb.gimp_image_insert_layer(image, bgLayer, None, 2)
		gimp.set_background(255, 0, 255)
		pdb.gimp_edit_fill(bgLayer, BACKGROUND_FILL) # Fill with background (magenta)

		# Merge the layers and save the image to a PNG file.
		if outputFolder and filename:
			mergedWithShadow = pdb.gimp_image_merge_visible_layers(image, 1)
			saveToFile(image, mergedWithShadow, outputFolder, filename + ' _9')

	# Reactivate history recording.
	pdb.gimp_image_undo_group_end(image)


register(
		"finish_csp",                                                                      # Name to register for calling this plug-in
		("Creates a finished, paletted CSP from an RGBA image; crops the image, "          # Long description / help message
			"adds a shadow, creates a palette, and saves to a file.\n\nTo use this, "
			"first create a selection for the area you would like to crop to. For "
			"CSPs, the size should be 136x188."),
		"Create a finished, paletted CSP from an RGBA image.",                             # Short info (tooltips, etc.)
		"DRGN (Daniel R. Cappel)",                                                         # Author
		"Public Commons",                                                                  # Copyright
		"Dec. 2014",                                                                       # Creation time
		"<Image>/CS_Ps/_Add Shadow and Save",
		"*",                 # Color space. Setting to "*" means any are accepted, and will force requirement of an open image before script can be called.
		[
				(PF_STRING, "outputFolder", "Output directory", ""),
				(PF_STRING, "filename", "File name", "(File extension not required)"),
				(PF_BOOL, "saveRef", "Save as type __6 (RGBA32)", True),
				(PF_BOOL, "saveWithPalette", "Create as type __9 (Paletted)", True)
		],
		[],
		finish_csp)			# Name of the function to call in this script

main()