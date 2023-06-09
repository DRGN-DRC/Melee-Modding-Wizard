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

import time
import math
import pyglet
import win32api
import Tkinter as Tk

from operator import add, mul
from collections import OrderedDict

# Disable a few options for increased performance
pyglet.options['debug_gl'] = True
pyglet.options['audio'] = ( 'silent', )
#pyglet.options['shadow_window'] = False
pyglet.options['search_local_libs'] = False

from pyglet import gl
from pyglet.window import key, Projection3D
from pyglet.window import Window as pygletWindow
from pyglet.app.base import EventLoop
from pyglet.graphics import Group, TextureGroup
from pyglet.window.event import WindowEventLogger

import globalData


class RenderEngine( Tk.Frame ):

	""" This module creates a pyglet rendering environment (a window), and embeds
		it into a Tkinter frame for incorporation into the larger GUI. """
	
	def __init__( self, parent, dimensions=(640, 480), resizable=False, **kwargs ):

		self.width = dimensions[0]
		self.height = dimensions[1]

		Tk.Frame.__init__( self, parent, **kwargs )

		# Create a Tkinter canvas to hold the Pyglet window's canvas
		self.canvas = Tk.Canvas( self, width=self.width, height=self.height, borderwidth=0, highlightthickness=0 )
		self.canvas.pack()

		# Interpret a background color for the Pyglet canvas; check for a given background color, or default to black
		backgroundColor = kwargs.get( 'background', 'black' )
		self.bgColor = list( globalData.gui.root.winfo_rgb(backgroundColor) ) # Returns (r, g, b) with 16 bit color depth
		self.bgColor = tuple( [v/65536.0 for v in self.bgColor] + [1] ) # Convert to 0-1 range and add an alpha channel

		# Create an invisible Pyglet window (cannot create a Pyglet canvas without a window)
		display = pyglet.canvas.get_display()
		screen = display.get_default_screen()
		config = screen.get_matching_configs( gl.Config(double_buffer=True, depth_size=8, alpha_size=8, samples=4) )[0]
		self.window = pygletWindow( display=display, config=config, width=self.width, height=self.height, resizable=resizable, visible=False )
		self.fov = 60; self.znear = 0.1; self.zfar = 3000
		self.window.projection = Projection3D( self.fov, self.znear, self.zfar )
		self.window.on_draw = self.on_draw
		self.bind( '<Expose>', self.refresh )
		openGlVersion = self.window.context._info.get_version().split()[0]
		# print( 'Rendering with OpenGL version {}'.format(openGlVersion) )

		# Set the pyglet parent window to be the tkinter canvas
		GWLP_HWNDPARENT = -8
		pyglet_handle = self.window.canvas.hwnd
		win32api.SetWindowLong( pyglet_handle, GWLP_HWNDPARENT, self.canvas.winfo_id() )

		# Set up the OpenGL context
		self.window.switch_to()
		gl.glClearColor( *self.bgColor )

		gl.glClearDepth( 1.0 ) # Depth buffer setup
		gl.glEnable( gl.GL_DEPTH_TEST ) # Do depth comparisons and enable depth testing
		gl.glDepthFunc( gl.GL_LEQUAL ) # The type of depth testing to do

		gl.glEnable( gl.GL_ALPHA_TEST )
		gl.glEnable( gl.GL_BLEND )
		gl.glBlendFunc( gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA )
		
		#gl.glCullFace( gl.GL_BACK )
		gl.glDisable( gl.GL_CULL_FACE ) # Enabled by default
		#gl.glPolygonMode( gl.GL_FRONT_AND_BACK, gl.GL_LINE ) # Enable for wireframe mode (need to reset line widths)

		gl.glEnable( gl.GL_TEXTURE_2D )
		gl.glTexParameteri( gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR )
		gl.glTexParameteri( gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR )

		try: # Anti-aliasing
			gl.glEnable( gl.GL_LINE_SMOOTH )
			gl.glEnable( gl.GL_POLYGON_SMOOTH )
			gl.glEnable( gl.GL_MULTISAMPLE )
			gl.glEnable( gl.GL_MULTISAMPLE_ARB )
		except pyglet.gl.GLException:
			print( 'Warning: Anti-aliasing is not supported on this computer.' )
			print( 'Rendering with OpenGL version {}'.format(openGlVersion) )

		self.clearRenderings()
		self.resetView()

		# Set up event handling for controls
		#self.window._enable_event_queue = True
		self.window.on_mouse_drag = self.on_mouse_drag
		#self.window.on_key_press = self.on_key_press
		#self.window.on_mouse_scroll = self.on_mouse_scroll2 	# doesn't work!?
		self.window.on_mouse_scroll = self.on_mouse_scroll
		self.master.bind( "<MouseWheel>", self.on_mouse_scroll )
		self.master.bind( '<KeyPress>', self.on_key_press2 )
		#self.master.bind( "<1>", self.window.activate() ) # Move focus to the parent when clicked on

		if resizable:
			self.tic = time.time()
			self.bind( "<Configure>", self.resizeViewport )

		# Start the render event loop using Tkinter's main event loop
		self.window.updateRequired = True
		if not pyglet.app.event_loop.is_running:
			pyglet.app.event_loop = CustomEventLoop( self.winfo_toplevel() )
			pyglet.app.event_loop.run()

		# Move focus to the parent window (will be the pyglet window by default)
		self.master.after( 1, lambda: self.master.focus_force() )

	def clearRenderings( self ):

		# for obj in self.getObjects():
		# 	obj.delete()

		self.vertices = []
		self.edges = []
		self.triangles = []
		self.quads = []
		self.vertexLists = []
		self.textures = {}

		self.window.updateRequired = True

	def resetView( self ):
		self.rotation_X = 0
		self.rotation_Y = 0

		self.translation_X = 0.0
		self.translation_Y = 0.0
		self.translation_Z = 0.0

		self.window.updateRequired = True

	def focusCamera( self, tags=None, primitive=None, skipRotationReset=False ):

		""" Resets the camera and centers it on the object with the given tag. 
			The tag and primitive arguments may be given to filter to targets. """

		if not skipRotationReset:
			self.resetView()

		xCoords = []
		yCoords = []
		zCoords = []

		# Check if tags is an iterable or a single item
		if tags:
			if hasattr( tags, '__iter__' ):
				tags = set( tags )
			else: # Is not an iterable
				tags = set( [tags] )

		# Find all of the x/y/z coordinates of the target object(s)
		for obj in self.getObjects( primitive ):
			if not tags or tags & set( obj.tags ):
				if obj.__class__ == Vertex:
					xCoords.append( obj.x )
					yCoords.append( obj.y )
					zCoords.append( obj.z )
				else:
					# Iterate over the vertices by individual coordinates
					coordsIter = iter( obj.vertices[1] )
					coordsList = [ coordsIter ] * 3
					for x, y, z in zip( *coordsList ):
						xCoords.append( x )
						yCoords.append( y )
						zCoords.append( z )

		# Set defaults and exit if no coordinates could be collected
		if not xCoords or not yCoords or not zCoords:
			self.translation_X = 0
			self.translation_Y = 0
			self.translation_Z = -10
			return

		# Calculate new camera X/Y coords
		maxX = max( xCoords )
		maxY = max( yCoords )
		maxZ = max( zCoords )
		x = ( maxX + min(xCoords) ) / 2.0
		y = ( maxY + min(yCoords) ) / 2.0
		z = ( maxZ + min(zCoords) ) / 2.0

		# Determine depth (zoom level); try to get the entire model part/group in the frame
		xSpan = maxX - x
		ySpan = maxY - y
		zSpan = maxZ - z
		if xSpan > ySpan:
			# Use x-axis to determine zoom level
			if zSpan > xSpan:
				zOffset = zSpan * 1.6
			else:
				zOffset = xSpan * 1.5
		else:
			# Use y-axis to determine zoom level
			if zSpan > ySpan:
				zOffset = zSpan * 1.6
			else:
				zOffset = ySpan * 1.7

		# Set the new camera position
		self.translation_X = -x
		self.translation_Y = -y
		self.translation_Z = -z - abs( zOffset )

	def resizeViewport( self, event ):

		""" Updates the tkinter canvas and pyglet rendering canvas 
			when the Tkinter frame is resized. """
		
		self.width = event.width
		self.height = event.height

		self.canvas['width'] = self.width
		self.canvas['height'] = self.height

		# Update the pyglet rendering canvas
		self.window.switch_to()
		gl.glViewport( 0, 0, self.width, self.height )
		self.window._update_view_location( self.width, self.height )

		self.window.updateRequired = True

	def refresh( self, event ):

		""" Tells the render engine to update/redraw the display canvas at its next opportunity. 
			This is bound to the <Expose> Tkinter event, which will occur whenever at least 
			some part of the program or widget becomes visible after having been covered up 
			by another window or widget. """

		self.window.updateRequired = True

	def addVertex( self, vertices, color=(128, 128, 128, 255), tags=(), show=True, size=4 ):

		if len( vertices ) != 3:
			print( 'Incorrect number of coordinates given to create a vertex: ' + str(vertices) )
			return None

		vertex = Vertex( vertices, color, tags, show, size )
		self.vertices.append( vertex )

		self.window.updateRequired = True

		return vertex

	def addEdge( self, vertices, color=None, colors=(), tags=(), show=True, thickness=2 ):

		""" Translates given points into a series of edges (lines) to be batch-rendered. 
			The given vertices should contain 6 values (2 sets of x/y/z coords). """

		if len( vertices ) != 6:
			print( 'Incorrect number of coordinates given to create an edge: ' + str(vertices) )
			return None

		edge = Edge( vertices, color, colors, tags, show, thickness )
		self.edges.append( edge )

		self.window.updateRequired = True

		return edge

	def addEdges( self, edgePoints, color=None, colors=(), tags=(), show=True, thickness=2 ):

		""" Translates given points into a series of data points (edges) to be batch-rendered. 
			The edgePoints arg should be a list of tuples, where each tuple contains 6 values 
			(2 sets of x/y/z coords). """

		for vertices in edgePoints:
			if len( vertices ) != 6:
				print( 'Incorrect number of points given to create an edge: ' + str(vertices) )
				continue

			edge = Edge( vertices, color, colors, tags, show, thickness )
			self.edges.append( edge )

		self.window.updateRequired = True

	def addQuad( self, vertices, color=None, colors=(), tags=(), show=True ):

		if len( vertices ) != 12:
			print( 'Incorrect number of points given to create a quad: ' + str(vertices) )
			return None

		quad = Quad( vertices, color, colors, tags, show )
		self.quads.append( quad )

		self.window.updateRequired = True

		return quad
	
	def addVertexLists( self, vertexLists, textures, dobj='', pobj='', polygonGroup=None ):

		""" Adds one or more entries of a display list. Each display list entry contains 
			one or more primitives of the same type (e.g. edge/triangle strip/etc)."""
		
		for vertexList in vertexLists:
			if dobj and pobj:
				vertexList.tags = ( dobj, pobj )
			if textures:
				vertexList.textureGroup = self._addTextureGroup( textures, polygonGroup )
			self.vertexLists.append( vertexList )

			# self.window.updateRequired = True
			# self.canvas.update()

		self.window.updateRequired = True
	
	def addPrimitives( self, primitives ):

		""" Add one or more pre-initialized primitives without coords validation. """

		if not primitives:
			return

		unknownObjects = []

		for prim in primitives:
			if isinstance( prim, Vertex ):
				self.vertices.append( prim )
			elif isinstance( prim, Edge ):
				self.edges.append( prim )
			elif isinstance( prim, Triangle ):
				self.triangles.append( prim )
			elif isinstance( prim, Quad ):
				self.quads.append( prim )
			elif isinstance( prim, VertexList ):
				self.vertexLists.append( prim )
			else:
				unknownObjects.append( prim )

		if unknownObjects:
			print( 'Unable to add unknown, non-primitive objects!:'.format(unknownObjects) )

		self.window.updateRequired = True

	def renderJoint( self, joint, parent=None, showBones=False ):

		""" Recursively scans the given joint and all child/next joints for 
			Display Objects and Polygon Objects. Breaks down Polygon Objects 
			into primitives and renders them to the display. """

		primitives = []

		# Check for a child joint to render
		childJoint = joint.initChild( 'JointObjDesc', 2 )
		if childJoint:
			# Render child joints and collect their primitives in order to apply transformations
			primitives.extend( self.renderJoint(childJoint, joint, showBones) )

		# Check for a 'next' (sibling) joint to render
		nextJoint = joint.initChild( 'JointObjDesc', 3 )
		if nextJoint:
			if not parent:
				parent = joint
			self.renderJoint( nextJoint, parent, showBones )

		# Check for a display object and polygon object to render
		dobj = joint.DObj
		if dobj:
			primitives.extend( self.renderDisplayObj(dobj) )

		# Apply joint transformations for this joint's meshes as well as its children
		transformationValues = joint.getValues()[5:14] # 9 values; 3 for each of rotation/scale/translation
		for primitive in primitives:
			primitive.rotate( *transformationValues[:3] )
			primitive.scale( *transformationValues[3:6] )
			primitive.translate( *transformationValues[6:] )

		# Add a vertex to represent this joint
		xyzCoords = transformationValues[6:]
		primitives.append( self.addVertex( xyzCoords, (255, 0, 0, 255), ('bones',), showBones ) )

		# Track the largest +/- x values to adjust the camera zoom
		xCoordAbs = -abs( xyzCoords[0] ) * 1.4
		if xCoordAbs < self.translation_Z and xCoordAbs > -self.zfar:
			self.translation_Z = xCoordAbs

		# Connect a line between the current joint and its parent joint
		if parent:
			# Parent vertices will be added by the calling method's transformation step(s)
			edge = self.addEdge( (0,0,0) + xyzCoords, colors=((0,255,0,255), (0,0,255,255)), tags=('bones',), show=showBones )
			primitives.append( edge )

		# Update the display to show current progress
		self.canvas.update()

		return primitives
	
	def renderDisplayObj( self, parentDobj, includeSiblings=True ):

		""" Parses and renders the given Display Object (DObj) and 
			all of its siblings. """

		primitives = []

		if includeSiblings:
			dobjOffsets = parentDobj.getSiblings()
		else:
			dobjOffsets = [ parentDobj.offset ]

		try:
			# Iterate over this DObj (and its siblings, if enabled)
			for offset in dobjOffsets:
				dobj = parentDobj.dat.getStruct( offset )

				# Check for a polygon object to render
				pobj = dobj.PObj
				if not pobj:
					continue

				# Check for textures (usually just one, but there can be more)
				textures = self.collectTextures( dobj )

				# Iterate over this PObj and its siblings
				for pobjOffset in pobj.getSiblings():
					pobj = dobj.dat.getStruct( pobjOffset )

					# Create some additional rendering context for these polygons
					#pGroup = PolygonGroup( pobj )

					# Parse out primitives for this mesh
					pobjPrimitives = pobj.decodeGeometry()
					self.addVertexLists( pobjPrimitives, textures, offset, pobjOffset, None )
					primitives.extend( pobjPrimitives )

		# except AttributeError:
		# 	pass # This is fine; likely a DObj that doesn't have a PObj
		except Exception as err:
			if dobj and pobj:
				print( 'Unable to render {}; {}'.format(pobj.name, err) )
			elif dobj:
				print( 'Unable to render {}; {}'.format(dobj.name, err) )
			else:
				print( 'Unable to render {}; {}'.format(parentDobj.name, err) )

		return primitives
	
	def applyJointTransformations( self, primitives, parentJoint ):

		""" Recursively moves through all Joint struct parents until no more 
			are found, and applies all of their transformation values to the 
			given primitives. """

		rotation = [ 0, 0, 0 ]
		scale = [ 1.0, 1.0, 1.0 ]
		translation = [ 0, 0, 0 ]

		jointClass = globalData.fileStructureClasses['JointObjDesc']

		# Ascend the Joint structures tree while accumulating transformation values
		while parentJoint:
			# Gather the current transform values
			transformationValues = parentJoint.getValues()[5:14] # 9 values; 3 for each of rotation/scale/translation
			rotation = list( map(add, rotation, transformationValues[:3]) )
			scale = list( map(mul, scale, transformationValues[3:6]) )
			translation = list( map(add, translation, transformationValues[6:]) )
			
			# Check for another parent joint
			parentJointOffset = next(iter( parentJoint.getParents() ))
			parentJoint = parentJoint.dat.initSpecificStruct( jointClass, parentJointOffset )
		
		# Apply the cumulated transforms
		for primitive in primitives:
			primitive.rotate( *rotation )
			primitive.scale( *scale )
			primitive.translate( *translation )
	
	def collectTextures( self, dobj ):

		""" Collects all textures attached to the given Display Object (DObj), 
			following all '_Next' pointers in the Texture Object(s). 
			Returns a list of texture objects (file structs), to be decoded later. """

		tobj = None
		textures = []

		try:
			# Check for a texture object (TObj)
			mobj = dobj.initChild( 'MaterialObjDesc', 2 )
			tobj = mobj.initChild( 'TextureObjDesc', 2 )

			while tobj:
				# Get basic info on the texture
				imgHeader = tobj.initChild( 'ImageObjDesc', 21 )
				imageDataOffset, width, height, imageType, mipmapFlag, minLOD, maxLOD = imgHeader.getValues()

				# Check for palette info
				paletteHeader = tobj.initChild( 'PaletteObjDesc', 22 )
				if paletteHeader:
					paletteDataOffset = paletteHeader.getValues()[0]
					paletteHeaderOffset = paletteHeader.offset
				else:
					paletteDataOffset = -1
					paletteHeaderOffset = -1
				
				# Initialize a structure for the image data
				texture = dobj.dat.initTexture( imageDataOffset, imgHeader.offset, paletteDataOffset, paletteHeaderOffset, width, height, imageType, maxLOD, 0 )
				texture.tobj = tobj
				texture.mobj = mobj
				textures.append( texture )

				# Check for siblings
				tobj = tobj.initChild( 'TextureObjDesc', 1 )
		
		except AttributeError:
			pass # This is fine; likely a DObj that doesn't have a MObj/TObj

		except Exception as err:
			if mobj and tobj:
				print( 'Unable to get a texture from {}; {}'.format(tobj.name, err) )
			elif mobj:
				print( 'Unable to get a texture from {}; {}'.format(mobj.name, err) )
			else:
				print( 'Unable to get a texture from {}; {}'.format(dobj.name, err) )

		return textures

	def _addTextureGroup( self, textures, polygonGroup ):

		""" Converts the given texture objects (file structures) to 
			textures for pyglet and stores them into texture groups. """

		# Use the first texture data offset as an ID
		firstTextureOffset = textures[0].offset
		
		textureGroup = self.textures.get( firstTextureOffset )

		if not textureGroup:
			# Create a pyglet TextureGroup object and store it
			textureGroup = HSD_Texture( textures, polygonGroup )
			self.textures[firstTextureOffset] = textureGroup
		
		return textureGroup

	# def on_key_press( self, *args ):

	# 	#print( 'pressed ' + str(symbol) )
	# 	if not args:
	# 		return
	# 	symbol, modifiers = args

	# 	if symbol == key.R:
	# 		print( 'resetting' )
	# 		self.resetView()
	# 	elif symbol == key.LEFT:
	# 		print('The left arrow key was pressed.')
	# 	elif symbol == key.ENTER:
	# 		print('The enter key was pressed.')

	# 	self.window.updateRequired = True

	def on_key_press2( self, event ):

		print( 'pressed ' + event.keysym )
		symbol = event.keysym.lower()

		if symbol == 'r':
			print( 'resetting' )
			self.resetView()
		elif symbol == key.LEFT:
			print('The left arrow key was pressed.')
		elif symbol == key.ENTER:
			print('The enter key was pressed.')

		self.window.updateRequired = True

	def on_mouse_scroll( self, event ):

		""" Move the camera in and out (toward/away) from the rendered model. """

		if event.delta > 0: # zoom in
			self.translation_Z *= .95
		elif event.delta < 0: # zoom out
			self.translation_Z *= 1.05

		self.window.updateRequired = True

	# def on_mouse_scroll2( self, *args ):

	# 	print('zoom2' )
	# 	print(args)

	def on_mouse_drag( self, *args ):

		""" Handles mouse input for rotation and panning of the scene. 
			buttons = Bitwise combination of the mouse buttons currently pressed. 
			modifiers = Bitwise combination of any keyboard modifiers currently active. """

		# Grab the event arguments (excluding x and y coords)
		#print('dragged')
		if not args:
			return
		dx, dy, buttons, modifiers = args[2:]

		if buttons == 1: # Left-click button held
			self.rotation_X += dx / 2.0
			self.rotation_Y -= dy / 2.0
		elif buttons == 4: # Right-click button held
			# Translate as a function of zoom level
			# self.translation_X += dx / 2.0
			# self.translation_Y += dy / 2.0
			self.translation_X += self.translation_Z * 0.004 * -dx
			self.translation_Y += self.translation_Z * 0.004 * -dy
		# else: Multiple buttons held; do nothing and 
		# wait 'til the user gets their act together. :P

		self.window.updateRequired = True

	def on_draw( self ):

		""" Renders all primitives to the display. """

		try:
			# Clear the screen
			gl.glClear( gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT )
			
			# Set the projection matrix to a perspective projection and apply translation (camera pan)
			gl.glMatrixMode( gl.GL_PROJECTION )
			gl.glLoadIdentity()
			gl.gluPerspective( self.fov, float(self.width) / self.height, self.znear, self.zfar )
			gl.glTranslatef( self.translation_X, self.translation_Y, self.translation_Z )

			# Set up the modelview matrix and apply mouse rotation input transformations
			gl.glMatrixMode( gl.GL_MODELVIEW )
			gl.glLoadIdentity()
			gl.glRotatef( self.rotation_Y, 1, 0, 0 )
			gl.glRotatef( self.rotation_X, 0, 1, 0 )
			
			# Render a batch for each set of objects that have been added
			if self.vertices:
				batch = pyglet.graphics.Batch()
				for vertex in self.vertices:
					vertex.render( batch )
				batch.draw()
			if self.edges:
				batch = pyglet.graphics.Batch()
				for edge in self.edges:
					edge.render( batch )
				batch.draw()
			if self.triangles:
				batch = pyglet.graphics.Batch()
				for triangle in self.triangles:
					triangle.render( batch )
				batch.draw()
			if self.quads:
				batch = pyglet.graphics.Batch()
				for quad in self.quads:
					quad.render( batch )
				batch.draw()
			if self.vertexLists:
				batch = pyglet.graphics.Batch()
				for vList in self.vertexLists:
					vList.render( batch )
				batch.draw()

		except Exception as err:
			print( 'An error occurred during rendering: {}'.format(err) )

	def getObjects( self, primitive=None ):

		""" Fetches all primitives of the given type (vertex/edge/triangle/quad). """

		# Confine the search to improve performance
		if primitive == 'vertex':
			objects = self.vertices
		elif primitive == 'edge':
			objects = self.edges
		elif primitive == 'triangle':
			objects = self.triangles
		elif primitive == 'quad':
			objects = self.quads
		elif primitive == 'vertexList':
			objects = self.vertexLists
		else:
			if primitive:
				print( 'Warning; unrecognized primitive: ' + str(primitive) )
			objects = self.vertices + self.edges + self.triangles + self.quads + self.vertexLists

		return objects
	
	def getPrimitiveTotals( self ):
		
		""" Collects totals for the number of each type of vertexList 
			and primitive among vertexLists being rendered. 
			Returns a dict of key=primType, value=[groupCount, primCount] """
		
		totals = OrderedDict( [ 
			('Vertices', [0, 0]), ('Lines', [0, 0]), ('Line Strips', [0, 0]), 
			('Triangles', [0, 0]), ('Triangle Strips', [0, 0]), ('Triangle Fans', [0, 0]), 
			('Quads', [0, 0])
		] )
		
		for primitive in self.vertexLists:
			if primitive.type == gl.GL_POINTS:
				totals['Vertices'][0] += 1
				totals['Vertices'][1] += len( primitive.vertices[1] )
			elif primitive.type == gl.GL_LINES:
				totals['Lines'][0] += 1
				lineCount = len( primitive.vertices[1] ) / 2
				totals['Lines'][1] += lineCount
				totals['Vertices'][1] += lineCount * 2
			elif primitive.type == gl.GL_LINE_STRIP:
				totals['Line Strips'][0] += 1
				lineCount = ( len(primitive.vertices[1]) - 2 ) / 2 # -2 for degenerate vertices
				totals['Line Strips'][1] += lineCount
				totals['Vertices'][1] += lineCount - 1 # +1 vertex, but -2 for degenerate vertices
			elif primitive.type == gl.GL_TRIANGLES:
				totals['Triangles'][0] += 1
				triangleCount = len( primitive.vertices[1] ) / 3
				totals['Triangles'][1] += triangleCount
				totals['Vertices'][1] += len( primitive.vertices[1] )
				totals['Lines'][1] += len( primitive.vertices[1] )
			elif primitive.type == gl.GL_TRIANGLE_STRIP:
				totals['Triangle Strips'][0] += 1
				triangleCount = len( primitive.vertices[1] ) - 4 # Subtract initial 2 point and 2 degenerate vertices
				totals['Triangle Strips'][1] += triangleCount
				totals['Vertices'][1] += triangleCount + 2
				totals['Lines'][1] += ( triangleCount * 2 ) + 1
			elif primitive.type == gl.GL_TRIANGLE_FAN:
				totals['Triangle Fans'][0] += 1
				triangleCount = len( primitive.vertices[1] ) - 4 # Subtract initial 2 point and 2 degenerate vertices
				totals['Triangle Fans'][1] += triangleCount
				totals['Vertices'][1] += triangleCount + 2
				totals['Lines'][1] += ( triangleCount * 2 ) + 1
			elif primitive.type == gl.GL_QUADS:
				totals['Quads'][0] += 1
				quadCount = len( primitive.vertices[1] ) / 4
				totals['Quads'][1] += quadCount
				totals['Vertices'][1] += len( primitive.vertices[1] )
				totals['Lines'][1] += len( primitive.vertices[1] )

		return totals

	def showPart( self, tag, visible, primitive=None ):

		""" Toggles the visibility for all primitives with a specified tag. 
			A primitive type may be given to improve performance. """

		for obj in self.getObjects( primitive ):
			if tag in obj.tags:
				obj.show = visible

		self.window.updateRequired = True

	def showAll( self, visible=True, primitive=None ):

		""" Toggles the visibility for all primitives with a specified tag. 
			A primitive type may be given to improve performance. """

		for obj in self.getObjects( primitive ):
			obj.show = visible

		self.window.updateRequired = True

	def removePart( self, tag, primitive=None ):

		""" Removes objects with the given tag from this render instance. 
			A primitive type may be given to improve performance. """

		if primitive == 'vertex':
			newObjList = []
			for obj in self.vertices:
				if tag not in obj.tags:
					newObjList.append( obj )
			self.vertices = newObjList

		elif primitive == 'edge':
			newObjList = []
			for obj in self.edges:
				if tag not in obj.tags:
					newObjList.append( obj )
			self.edges = newObjList

		elif primitive == 'triangle':
			newObjList = []
			for obj in self.triangles:
				if tag not in obj.tags:
					newObjList.append( obj )
			self.triangles = newObjList

		elif primitive == 'quad':
			newObjList = []
			for obj in self.quads:
				if tag not in obj.tags:
					newObjList.append( obj )
			self.quads = newObjList

		elif primitive == 'vertexList':
			newObjList = []
			for obj in self.vertexLists:
				if tag not in obj.tags:
					newObjList.append( obj )
			self.vertexLists = newObjList

		else:
			if primitive:
				print( 'Warning; unrecognized primitive: ' + str(primitive) )

			self.vertices = []
			self.edges = []
			self.triangles = []
			self.quads = []
			self.vertexLists = []

			for obj in self.getObjects( primitive ):
				if tag not in obj.tags:
					if isinstance( obj, Vertex ):
						self.vertices.append( obj )
					elif isinstance( obj, Edge ):
						self.edges.append( obj )
					elif isinstance( obj, Triangle ):
						self.triangles.append( obj )
					elif isinstance( obj, Quad ):
						self.quads.append( obj )
					elif isinstance( obj, VertexList ):
						self.vertexLists.append( obj )

		self.window.updateRequired = True

	def stop( self ):

		""" Setting this flag on the render window allows the event loop end peacefully, 
			so it doesn't try to update anything that doesn't exist and crash. """

		self.window.has_exit = True


class CustomEventLoop( EventLoop ):

	""" We can't use pyglet's native event loop without interfering with Tkinter's. 
		So we'll create a modified one that will be goverened by Tkinter. """

	def __init__( self, root ):
		super( CustomEventLoop, self ).__init__()
		self.root = root
	
	def run( self ):

		""" Begin processing events, scheduled functions and window updates.
			Performs the usual pyglet startup. However, while this method would 
			normally block as the pyglet event loop runs, we will instead queue 
			updates (pyglet event loop steps) and then return. """

		self.has_exit = False
		self._legacy_setup()

		# platform_event_loop = pyglet.app.platform_event_loop
		# platform_event_loop.start()
		# self.dispatch_event('on_enter')

		self.is_running = True

		# Schedule pyglet updates in Tkinter's event loop
		self.root.after( 0, self.step )

	def step( self ):

		# Track whether there are any windows left to update
		queueNextStep = False

		for window in pyglet.app.windows:
			# Shut down any windows wanting to exit
			if window.has_exit:
				window.close()
				continue
			
			queueNextStep = True

			# Skip redraws if there haven't been any changes
			if not window.updateRequired:
				continue

			# Skip this window if the user isn't interacting with it
			# if not window._mouse_in_window:
			# 	continue

			# Set keyboard focus to this window if the mouse is over it
			# if window._mouse_in_window:
			# 	window.activate()

			# Set context/render focus to this window
			window.switch_to()

			# Queue handling mouse input and drawing (updating) the canvas
			# window.dispatch_event( 'on_mouse_drag' )	# still fires dragged without this
			#window.dispatch_event( 'on_key_press' )
			window.dispatch_event( 'on_draw' )
			#window.dispatch_pending_events()	# still fires dragged without this
			#window.dispatch_events()	# still fires dragged without this
			
			# Swap the display buffers to show the rendered image
			window.flip()

			# Set the flag indicating redraws are no longer required
			window.updateRequired = False

		# Re-queue for the next frame
		if queueNextStep:
			self.root.after( 17, self.step )
		else:
			self.stop()

	def stop( self ):

		""" The typical end to the pyglet 'run' method. """

		self.is_running = False
		self.has_exit = True

		# self.dispatch_event('on_exit')
		# platform_event_loop = pyglet.app.platform_event_loop
		# platform_event_loop.stop()


class Primitive:

	@staticmethod
	def interpretColors( pointCount, color, colors ):

		""" Checks a primitive's color and colors arguments. A single given color 
			takes priority and will be used for all vertices if provided. If no color 
			and no colors are given, vertex colors will default to gray. """

		defaultColor = ( 128, 128, 128, 255 )

		try:
			if color:
				# A single color was given
				assert len( color ) == 4, 'the given color should be an RGBA tuple.'
				colors = color * pointCount
			elif not colors:
				# No color(s) given; default to gray
				colors = defaultColor * pointCount
			elif len( colors ) == 1:
				# A single color given; copy it for all points
				assert len( colors[0] ) == 4, 'the given color should be an RGBA tuple.'
				colors = ( colors[0], ) * pointCount
			elif pointCount != len( colors ):
				# Ehh?
				print( 'Warning! Unexpected number of colors given to primitive: ' + str(colors) )
				assert len( colors[0] ) == 4, 'the given color should be an RGBA tuple.'
				colors = ( colors[0], ) * pointCount
			else:
				# Number of colors matches number of points
				flattenedList = []
				for color in colors:
					assert len( color ) == 4, 'the given colors should all be RGBA tuples.'
					flattenedList.extend( color )
				colors = flattenedList
		except Exception as err:
			print( 'Invalid color(s) given to create a primitive; {}'.format(err) )
			colors = defaultColor * pointCount

		return colors
	
	def scale( self, scaleX, scaleY, scaleZ ):

		""" Modifies the size (scaling) of the primitive's coordinates by the given amount. """

		if self.__class__ == Vertex:
			self.x *= scaleX
			self.y *= scaleY
			self.z *= scaleZ
		else:
			newCoords = []
			coordsIter = iter( self.vertices[1] )
			coordsList = [ coordsIter ] * 3
			
			for x, y, z in zip( *coordsList ):
				newCoords.extend( (x*scaleX, y*scaleY, z*scaleZ) )

			self.vertices = ( self.vertices[0], newCoords )

	def translate( self, translateX, translateY, translateZ ):

		""" Modifies an array of point coordinates by their respective 
			translation amount (linear movement, parallel to one axis). """

		if self.__class__ == Vertex:
			if translateX:
				self.x += translateX
			if translateY:
				self.y += translateY
			if translateZ:
				self.z += translateZ
		else:
			coords = self.vertices[1]
			newCoords = []

			# Iterate over the coords in sets of z/y/z coordinates
			coordsIter = iter( coords )
			coordsList = [ coordsIter ] * 3
			for x, y, z in zip( *coordsList ):
				newCoords.append( x + translateX )
				newCoords.append( y + translateY )
				newCoords.append( z + translateZ )

			# Assign the new coordinates to the primitive
			self.vertices = ( self.vertices[0], newCoords )

	def rotate( self, rotationX, rotationY, rotationZ ):

		""" Rotates the primitive's vertex coordinates around each axis by the given angle amounts (in radians). """

		# Do nothing if all rotation amounts are zero
		if not rotationX and not rotationY and not rotationZ:
			return

		# Compute sin and cos values to make a rotation matrix
		cos_x, sin_x = math.cos( rotationX ), math.sin( rotationX )
		cos_y, sin_y = math.cos( rotationY ), math.sin( rotationY )
		cos_z, sin_z = math.cos( rotationZ ), math.sin( rotationZ )

		# Generate a 3D rotation matrix from angles around the X, Y, and Z axes
		rotation_matrix = [
			[cos_y * cos_z, -cos_x * sin_z + sin_x * sin_y * cos_z, sin_x * sin_z + cos_x * sin_y * cos_z], # X-axis rotation
			[cos_y * sin_z, cos_x * cos_z + sin_x * sin_y * sin_z, -sin_x * cos_z + cos_x * sin_y * sin_z], # Y-axis rotation
			[-sin_y, sin_x * cos_y, cos_x * cos_y] # Z-axis rotation
		]

		# Multiply the rotation matrix with each vertices' coordinates
		if self.__class__ == Vertex:
			originalCoords = ( self.x, self.y, self.z )
			rotatedCoords = self._matrixMultiply( rotation_matrix, originalCoords )
			self.x, self.y, self.z = rotatedCoords
		else:
			newCoords = []
			coordsIter = iter( self.vertices[1] )
			coordsList = [ coordsIter ] * 3

			for point in zip( *coordsList ):
				rotatedCoords = self._matrixMultiply( rotation_matrix, point )
				newCoords.extend( rotatedCoords )

			self.vertices = ( self.vertices[0], newCoords )

	def _matrixMultiply( self, matrix, vertex ):

		""" Multipies a 3x3 matrix with a vertex to transform it. """

		coordCount = len( vertex )
		result = [ 0.0 ] * coordCount

		for i in range( len(matrix) ):
			for j in range( coordCount ):
				result[i] += matrix[i][j] * vertex[j]

		return result


class Vertex( Primitive ):

	def __init__( self, coords, color=(0, 0, 0, 255), tags=(), show=True, size=4 ):
		# Position
		if coords:
			self.x = coords[0]
			self.y = coords[1]
			self.z = coords[2]
		else:
			self.x = 0
			self.y = 0
			self.z = 0

		# Texture coordinates
		self.s = 0
		self.t = 0

		self.color = color
		self.tags = tags
		self.show = show
		self.size = size		# For rendering appearance size
	
	def render( self, batch ):
		if self.show:
			gl.glPointSize( self.size )
			batch.add( 1, gl.GL_POINTS, None, ('v3f/static', (self.x, self.y, self.z)), ('c4B/static', self.color) )


class Edge( Primitive ):

	def __init__( self, vertices, color=None, colors=(), tags=(), show=True, thickness=2 ):
		self.vertices = ( 'v3f/static', vertices )
		self.vertexColors = ( 'c4B/static', self.interpretColors( 2, color, colors ) )
		self.tags = tags
		self.show = show
		self.thickness = thickness
	
	def render( self, batch ):
		if self.show:
			gl.glLineWidth( self.thickness )
			batch.add( 2, gl.GL_LINES, None, self.vertices, self.vertexColors )


class Triangle( Primitive ):

	def __init__( self, vertices, color=None, colors=(), tags=(), show=True ):
		self.vertices = ( 'v3f/static', vertices )
		self.vertexColors = ( 'c4B/static', self.interpretColors( 3, color, colors ) )
		self.normals = ( 'n3f/static', [] )
		self.tags = tags
		self.show = show
	
	def render( self, batch ):
		if self.show:
			batch.add( 3, gl.GL_TRIANGLES, None, self.vertices, self.vertexColors )


class Quad( Primitive ):

	def __init__( self, vertices, color=None, colors=(), tags=(), show=True ):
		self.vertices = ( 'v3f/static', vertices )
		self.vertexColors = ( 'c4B/static', self.interpretColors( 4, color, colors ) )
		self.normals = ( 'n3f/static', [] )
		self.tags = tags
		self.show = show
	
	def render( self, batch ):
		if self.show:
			batch.add( 4, gl.GL_QUADS, None, self.vertices, self.vertexColors )


class VertexList( Primitive ):

	def __init__( self, primitiveType, tags=(), show=True ):
		self.type = self.interpretPrimType( primitiveType )
		self.vertices = ( 'v3f/static', [] )
		self.vertexColors = ( 'c4B/static', [] )
		self.texCoords = ( 't2f/static', [] )
		self.normals = ( 'n3f/static', [] )

		self.textureGroup = None
		self.envelopeIndex = -1
		self.vertexCount = 0
		self.tags = tags
		self.show = show

	def finalize( self ):

		""" Validates vertex colors and texture coordinates if they're present, 
			or adds them if they're not. And adds degenerate vertices if needed. """

		self.vertexCount = len( self.vertices[1] ) / 3

		# Validate vertex colors or add them if not present
		if len( self.vertexColors[1] ) / 4 != self.vertexCount:
			self.vertexColors = ( self.vertexColors[0], [255, 255, 255, 255] * self.vertexCount )

		# Validate vertex texture coordinates or add them if not present
		if len( self.texCoords[1] ) / 2 != self.vertexCount:
			self.texCoords = ( self.texCoords[0], [0.0, 0.0] * self.vertexCount )

		if self.type == gl.GL_LINE_STRIP or self.type == gl.GL_TRIANGLE_STRIP:
			self.addDegenerates()

	def interpretPrimType( self, primType ):

		""" Translates a primitive type for a display list vertex group/list 
			into an OpenGL primitive type. """

		if primType == 0xB8: primitiveType = gl.GL_POINTS
		elif primType == 0xA8: primitiveType = gl.GL_LINES
		elif primType == 0xB0: primitiveType = gl.GL_LINE_STRIP
		elif primType == 0x90: primitiveType = gl.GL_TRIANGLES
		elif primType == 0x98: primitiveType = gl.GL_TRIANGLE_STRIP
		elif primType == 0xA0: primitiveType = gl.GL_TRIANGLE_FAN
		elif primType == 0x80: primitiveType = gl.GL_QUADS
		# 0x88 == gl.GL_QUAD_STRIP?
		else: # Failsafe
			print( 'Warning! Invalid primitive type: 0x{:X}'.format(primType) )
			primitiveType = gl.GL_POINTS

		return primitiveType
	
	def addDegenerates( self ):

		""" The purpose of degenerate vertices in a strip is to act as separators between segments. 
			By repeating the first and last vertices of a segment, a degenerate triangle (or line) 
			with zero area (or length) is created, which effectively skips over the degenerate 
			vertex and disconnects the segments. """

		# Repeat the first three coordinates at the start
		self.vertices[1].insert( 0, self.vertices[1][2] )
		self.vertices[1].insert( 0, self.vertices[1][2] )
		self.vertices[1].insert( 0, self.vertices[1][2] )
		
		# Repeat the last three coordinates at the end
		self.vertices[1].extend( self.vertices[1][-3:] )

		self.vertexCount += 2
		
		# Repeat the first color at the start
		self.vertexColors[1].insert( 0, self.vertexColors[1][3] )
		self.vertexColors[1].insert( 0, self.vertexColors[1][3] )
		self.vertexColors[1].insert( 0, self.vertexColors[1][3] )
		self.vertexColors[1].insert( 0, self.vertexColors[1][3] )
		
		# Repeat the last color at the end
		self.vertexColors[1].extend( self.vertexColors[1][-4:] )

		# Repeat the first texture coords at the start
		self.texCoords[1].insert( 0, self.texCoords[1][1] )
		self.texCoords[1].insert( 0, self.texCoords[1][1] )
		
		# Repeat the last texture coords at the end
		self.texCoords[1].extend( self.texCoords[1][-2:] )

	def render( self, batch ):
		if self.show:
			batch.add( self.vertexCount, self.type, self.textureGroup, self.vertices, self.vertexColors, self.texCoords )


class HSD_Texture( TextureGroup ):

	def __init__( self, textures, parent=None ):
		self.parent = parent

		# Use the first texture in the textures list by default
		self.index = 0
		self.textures = textures # A list of texture objects (file structs)
		self.texture = self._convertTexObject( textures[0] )
		self.pygletConversions = { textures[0].offset: self.texture }

		self._setTexProperties()

	def _setTexProperties( self ):
		tobj = self.textures[self.index].tobj
		tobjValues = tobj.getValues()
		self.wrapModeS = tobjValues[13]
		self.wrapModeT = tobjValues[14]
		self.repeatS = tobjValues[15]
		self.repeatT = tobjValues[16]

		if self.wrapModeS == 0:
			self.wrapModeS = gl.GL_CLAMP
		elif self.wrapModeS == 1:
			self.wrapModeS = gl.GL_REPEAT
		elif self.wrapModeS == 2:
			self.wrapModeS = gl.GL_REPEAT
		if self.wrapModeT == 0:
			self.wrapModeT = gl.GL_CLAMP
		elif self.wrapModeT == 1:
			self.wrapModeT = gl.GL_REPEAT
		elif self.wrapModeT == 2:
			self.wrapModeT = gl.GL_REPEAT

	def _convertTexObject( self, textureObj ):

		""" Decodes the given texture (struct) object and convert it to a pyglet image. """

		# Decode the texture
		width, height = textureObj.width, textureObj.height
		pilImage = textureObj.dat.getTexture( textureObj.offset, width, height, textureObj.imageType, textureObj.imageDataLength, getAsPilImage=True )
		
		# Convert it for use with pyglet
		#pygletImage = pyglet.image.ImageData( width, height, 'RGBA', pilImage.tobytes(), pitch=-pilImage.width * 4 )
		pygletImage = pyglet.image.ImageData( width, height, 'RGBA', pilImage.tobytes() )
		texture = pygletImage.get_texture()
		# texture.anchor_x = width / 2
		# texture.anchor_y = height / 2

		return texture
	
	def changeTextureIndex( self, index ):

		""" Switches the current texture to a different one 
			in this group, converting it if needed. """

		assert index >= 0 and index < len( self.textures ), 'Texture group index out of range! {}'.format( index )

		self.index = index
		textureObj = self.textures[index]
		pygletTexture = self.pygletConversions.get( textureObj.offset )

		# Check if this has already been decoded/converted
		if not pygletTexture:
			pygletTexture = self._convertTexObject( textureObj )
			self.pygletConversions[textureObj.offset] = pygletTexture

		self.texture = pygletTexture
		self._setTexProperties()
	
	def set_state( self ):
		#gl.glEnable( self.texture.target )
		gl.glBindTexture( self.texture.target, self.texture.id )

		gl.glTexParameteri( gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, self.wrapModeS )
		gl.glTexParameteri( gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, self.wrapModeT )

	def unset_state( self ):
		#gl.glDisable( self.texture.target )
		pass


class PolygonGroup( Group ):

	def __init__( self, pobj, parent=None ):
		self.parent = parent

		# Parse the flags to configure polygon properties
		flags = pobj.getValues( 'Polygon_Flags' )
		if flags & 1<<14 and flags & 1<<15:
			self.cullMode = gl.GL_FRONT_AND_BACK
		elif flags & 1<<14:
			self.cullMode = gl.GL_FRONT
		elif flags & 1<<15:
			self.cullMode = gl.GL_BACK
		else:
			self.cullMode = -1

		# if flags & 1:
		# 	self.windingOrder = gl.GL_CCW # Counter-clockwise
		# else:
		# 	self.windingOrder = gl.GL_CW # Clockwise
	
	def set_state( self ):
		# if self.cullMode == -1:
		# 	gl.glDisable( gl.GL_CULL_FACE )
		# else:
		# 	gl.glEnable( gl.GL_CULL_FACE )
		# 	gl.glCullFace( self.cullMode )

		# gl.glFrontFace( self.windingOrder )
		pass

	def unset_state( self ):
		pass